from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import json
import os
import numpy as np
import yfinance as yf
from cache import cache
from services.cross_asset import get_cross_asset_moves, get_regime_signal
from services.news_fetcher import fetch_news
from services.ai_client import ask_ai

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "../data/ideas_history.json")
POSITION_SIZE = 10_000  # $ per position for P&L calc

router = APIRouter()

SYSTEM_PROMPT = """You are an expert financial assistant specialising in markets, trading, risk management,
and investment strategy. Give clear, concise, professional answers.
Do not use markdown formatting — plain text only."""

# Curated list of AI models/tools used in finance
AI_FINANCE_MODELS = [
    {
        "name": "TradingAgents",
        "description": "Multi-Agent LLM Financial Trading Framework. Mirrors real trading firms with specialized agents: fundamental analysts, sentiment experts, technical analysts, traders, and risk managers.",
        "github": "https://github.com/TauricResearch/TradingAgents",
        "category": "Agent",
        "tech": "LangGraph · Ollama · OpenAI",
    },
    {
        "name": "FinGPT",
        "description": "Open-Source Financial Large Language Models with full training & fine-tuning pipelines. 18.5K+ stars. Includes FinGPT playground for NLP in finance.",
        "github": "https://github.com/AI4Finance-Foundation/FinGPT",
        "category": "LLM",
        "tech": "HuggingFace · LoRA · LLaMA",
    },
    {
        "name": "FinRL",
        "description": "Financial Reinforcement Learning framework. First open-source RL framework for trading, portfolio optimisation, and backtesting.",
        "github": "https://github.com/AI4Finance-Foundation/FinRL",
        "category": "Quant",
        "tech": "PyTorch · OpenAI Gym · DRL",
    },
    {
        "name": "AI Hedge Fund",
        "description": "AI-powered hedge fund proof of concept with agents modelled after famous investors: Ben Graham, Damodaran, Cathie Wood, Michael Burry, Charlie Munger.",
        "github": "https://github.com/virattt/ai-hedge-fund",
        "category": "Agent",
        "tech": "LangChain · OpenAI · yfinance",
    },
    {
        "name": "FinRobot",
        "description": "Open-Source AI Agent Platform for financial analysis. Features Market Forecasting Agents, Document Analysis Agents, and Trading Strategy Agents.",
        "github": "https://github.com/AI4Finance-Foundation/FinRobot",
        "category": "Agent",
        "tech": "AutoGen · LangChain · GPT-4",
    },
    {
        "name": "Qlib (Microsoft)",
        "description": "AI-oriented Quant investment platform by Microsoft. Supports ML paradigms from supervised learning to RL. Includes RD-Agent for automated R&D.",
        "github": "https://github.com/microsoft/qlib",
        "category": "Quant",
        "tech": "PyTorch · XGBoost · LightGBM",
    },
    {
        "name": "FinMem",
        "description": "Performance-Enhanced LLM Trading Agent with layered memory and character design. Novel framework with Profiling, Memory, and Decision-making modules.",
        "github": "https://github.com/pipiku915/FinMem-LLM-StockTrading",
        "category": "Agent",
        "tech": "GPT-4 · Vector DB · ReAct",
    },
    {
        "name": "Investment Portfolio AI Agent",
        "description": "AI-powered portfolio analysis using ReAct framework. Deep risk assessment, stock profiling, and personalised investment recommendations.",
        "github": "https://github.com/shiv-rna/Investment-Portfolio-AI-Agent",
        "category": "Agent",
        "tech": "LangChain · OpenAI · yfinance",
    },
    {
        "name": "Yahoo Finance LLM Agent",
        "description": "Real-time financial data agent combining OpenAI LLMs, Yahoo Finance, and LangChain. Stock info, financial statements, and conversational analysis.",
        "github": "https://github.com/ojasskapre/yahoo-finance-llm-agent",
        "category": "LLM",
        "tech": "LangChain · OpenAI · yfinance",
    },
    {
        "name": "AgenticTrading",
        "description": "Reframes investment workflow as a multi-agent ecosystem. Autonomous agents with reasoning, tool access, and memory. Standardised communication protocols.",
        "github": "https://github.com/Open-Finance-Lab/AgenticTrading",
        "category": "Agent",
        "tech": "LangGraph · OpenAI · Tools",
    },
    {
        "name": "StockAgent",
        "description": "LLM-based stock trading in simulated real-world environments. Benchmarks different LLMs on realistic trading tasks.",
        "github": "https://github.com/MingyuJ666/Stockagent",
        "category": "Research",
        "tech": "GPT-4 · LLaMA · Simulation",
    },
    {
        "name": "Awesome AI in Finance",
        "description": "Curated list of LLMs, deep learning strategies & tools in financial markets. Includes PIXIU (136K instruction samples) and FinGPT playground.",
        "github": "https://github.com/georgezouq/awesome-ai-in-finance",
        "category": "Resource",
        "tech": "Curated Collection",
    },
]

CATEGORY_COLORS = {
    "Agent":    "#58A6FF",
    "LLM":      "#3FB950",
    "Quant":    "#BC8CFF",
    "Research": "#D29922",
    "Resource": "#8B949E",
}


def fetch_ai_finance_news(limit: int = 8) -> list[dict]:
    tickers = ["MSFT", "GOOGL", "NVDA"]  # AI-heavy companies with relevant news
    seen = set()
    items = []
    for symbol in tickers:
        try:
            news = yf.Ticker(symbol).news or []
            for n in news:
                content = n.get("content", {})
                title = content.get("title", "")
                if not title or title in seen:
                    continue
                # Filter for AI/finance relevance
                lower = title.lower()
                if any(kw in lower for kw in ["ai", "artificial intelligence", "machine learning", "model", "llm", "fintech", "quant", "algorithm"]):
                    seen.add(title)
                    items.append({
                        "title": title,
                        "source": content.get("provider", {}).get("displayName", "Yahoo Finance"),
                        "url": content.get("canonicalUrl", {}).get("url", ""),
                        "published": content.get("pubDate", ""),
                    })
                if len(items) >= limit:
                    return items
        except Exception:
            continue
    return items


class ChatRequest(BaseModel):
    message: str


def _build_market_context() -> str:
    """Build a live market snapshot to inject into every chat message."""
    try:
        moves = get_cross_asset_moves()
        regime = get_regime_signal(moves)
        mkt_lines = "\n".join(
            f"- {m['name']} ({m['symbol']}): price {m['price']}, {m['change_1d']:+.2f}% today, {m['change_5d']:+.2f}% 5d"
            for m in moves
        )
    except Exception:
        mkt_lines = "Market data unavailable."
        regime = {"regime": "Unknown", "vix": "N/A"}

    news_lines = ""
    try:
        news_items = []
        for cat in ["equities_news", "stocks", "forex", "commodities"]:
            news_items += fetch_news(cat, limit=3)
        headlines = list({n["title"]: n for n in news_items}.values())[:10]
        news_lines = "\n".join(f"- {n['title']}" for n in headlines)
    except Exception:
        news_lines = "News unavailable."

    today = date.today().strftime("%B %d, %Y")
    return (
        f"=== LIVE MARKET DATA as of {today} ===\n"
        f"Market regime: {regime['regime']} | VIX: {regime['vix']}\n\n"
        f"Cross-asset prices & moves:\n{mkt_lines}\n\n"
        f"Latest news headlines:\n{news_lines}\n"
        f"=== END LIVE DATA ===\n\n"
        f"Use the live data above to answer questions about current markets. "
        f"Today is {today}. Do not rely on your training knowledge for current prices or recent events."
    )


@router.post("/chat")
def chat(req: ChatRequest):
    market_context = _build_market_context()
    system_with_context = SYSTEM_PROMPT + "\n\n" + market_context
    reply = ask_ai(system_with_context, req.message, timeout=90, json_mode=False)
    return {"reply": reply}


@router.get("/insights")
def get_insights():
    cached = cache.get("ai_insights")
    if cached:
        return cached

    news = fetch_ai_finance_news()
    result = {
        "news": news,
        "models": AI_FINANCE_MODELS,
        "category_colors": CATEGORY_COLORS,
    }
    cache.set("ai_insights", result)
    return result


def _fetch_ideas(prompt_content: str) -> list:
    MACRO_SYSTEM = "You are a macro strategist at a hedge fund. Respond with valid JSON only — no markdown, no extra text."
    raw = ask_ai(MACRO_SYSTEM, prompt_content, timeout=90)
    ideas = json.loads(raw)
    return ideas if isinstance(ideas, list) else []


def _load_history() -> list:
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(ideas: list):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        history = _load_history()
        history = ideas + history  # newest first
        history = history[:30]    # keep last 30
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f)
    except Exception:
        pass


def _get_entry_prices(assets: list[str]) -> dict[str, float]:
    """Fetch current prices as entry prices for newly saved ideas."""
    prices = {}
    for name in assets:
        ticker = resolve_ticker(name)
        if not ticker:
            continue
        try:
            data = yf.download(ticker, period="1d", auto_adjust=True, progress=False)
            closes = data["Close"].dropna()
            if len(closes) >= 1:
                prices[name] = round(float(closes.iloc[-1]), 4)
        except Exception:
            pass
    return prices


def _calculate_pnl(idea: dict) -> dict:
    """For a historical idea, fetch current prices and calculate P&L from entry."""
    entry_date = idea.get("entry_date", "")
    entry_prices = idea.get("entry_prices", {})
    assets = idea.get("assets", [])
    results = []

    for name in assets:
        ticker = resolve_ticker(name)
        entry_price = entry_prices.get(name)
        if not ticker or not entry_price:
            continue
        try:
            data = yf.download(ticker, start=entry_date, auto_adjust=True, progress=False)
            closes = data["Close"].dropna()
            if len(closes) < 1:
                continue
            current_price = float(closes.iloc[-1])
            pct_return = (current_price - entry_price) / entry_price * 100
            dollar_pnl = (pct_return / 100) * POSITION_SIZE
            days_held = len(closes)
            results.append({
                "name": name,
                "ticker": ticker,
                "entry_price": round(entry_price, 4),
                "current_price": round(current_price, 4),
                "pct_return": round(pct_return, 2),
                "dollar_pnl": round(dollar_pnl, 2),
                "days_held": days_held,
                "position_size": POSITION_SIZE,
            })
        except Exception:
            continue
    return {"pnl": results}


@router.get("/trade-ideas")
def get_trade_ideas():
    cached = cache.get("trade_ideas")
    if cached:
        return cached
    try:
        moves = get_cross_asset_moves()
        regime = get_regime_signal(moves)
        today = date.today().strftime("%B %d, %Y")
        today_iso = date.today().isoformat()

        mkt_summary = "\n".join(
            f"- {m['name']}: {m['change_1d']:+.2f}% today, {m['change_5d']:+.2f}% 5d"
            for m in moves
        )

        # Fetch recent news headlines for context
        news_items = []
        for cat in ["equities_news", "crypto", "commodities"]:
            news_items += fetch_news(cat, limit=4)
        headlines = "\n".join(f"- {n['title']}" for n in news_items[:12]) or "No headlines available."

        base = (
            f"Today is {today}. Use ONLY the live data provided below — do not use your training knowledge for current prices or events.\n\n"
            f"Market regime: {regime['regime']}. VIX: {regime['vix']}.\n\n"
            f"Cross-asset moves:\n{mkt_summary}\n\n"
            f"Recent news (these are real headlines from today):\n{headlines}\n\n"
            f"Each idea must have keys: 'theme' (short title), 'thesis' (2 sentences based on the data above), "
            f"'expression' (how to trade it), 'assets' (array of 2-3 common asset names like 'Gold', 'S&P 500', 'Bitcoin'), "
            f"'conviction' ('high'/'medium'/'low'), 'timeframe', 'risk' (main risk).\n"
            f"Respond as a JSON array only."
        )

        short_prompt = base + (
            "\n\nGenerate 3 SHORT-TERM trade ideas (timeframe: 1 day to 2 weeks) "
            "based on the LATEST NEWS and immediate market moves above. "
            "Focus on momentum and news-driven catalysts."
        )

        long_prompt = base + (
            "\n\nGenerate 3 LONG-TERM trade ideas (timeframe: 1 to 6 months) "
            "based on the LATEST NEWS and structural macro themes above. "
            "Focus on fundamental shifts and macro trends."
        )

        short_ideas = _fetch_ideas(short_prompt)
        long_ideas = _fetch_ideas(long_prompt)

        # Tag with entry date and fetch entry prices for future backtesting
        all_new = short_ideas + long_ideas
        for idea in all_new:
            idea["entry_date"] = today_iso
            idea["entry_prices"] = _get_entry_prices(idea.get("assets", []))

        _save_history(all_new)

        result = {
            "regime": regime,
            "short_term": short_ideas,
            "long_term": long_ideas,
            "generated_at": today_iso,
        }
        cache.set("trade_ideas", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-ideas/weekly")
def get_weekly_trade_ideas():
    cached = cache.get("weekly_trade_ideas")
    if cached:
        return cached
    try:
        moves = get_cross_asset_moves()
        regime = get_regime_signal(moves)
        today = date.today().strftime("%B %d, %Y")

        mkt_summary = "\n".join(
            f"- {m['name']}: {m['change_1d']:+.2f}% today, {m['change_5d']:+.2f}% this week"
            for m in moves
        )

        news_items = []
        for cat in ["equities_news", "crypto", "commodities"]:
            news_items += fetch_news(cat, limit=4)
        headlines = "\n".join(f"- {n['title']}" for n in news_items[:12]) or "No headlines available."

        base = (
            f"Today is {today} (weekend). Market regime this week: {regime['regime']}. VIX: {regime['vix']}.\n\n"
            f"This week's cross-asset moves:\n{mkt_summary}\n\n"
            f"News headlines this week:\n{headlines}\n\n"
            f"Each idea must have keys: 'theme' (short title), 'thesis' (2 sentences), "
            f"'expression' (how to trade it), 'assets' (array of 2-3 common asset names like 'Gold', 'S&P 500', 'Bitcoin'), "
            f"'conviction' ('high'/'medium'/'low'), 'timeframe', 'risk' (main risk).\n"
            f"Respond as a JSON array only."
        )

        short_prompt = base + (
            "\n\nGenerate 3 SHORT-TERM trade ideas (timeframe: 1-2 weeks) "
            "based on this week's themes and what to watch next week. "
            "Focus on momentum and catalysts from this week's moves."
        )

        long_prompt = base + (
            "\n\nGenerate 3 LONG-TERM trade ideas (timeframe: 1-6 months) "
            "based on structural macro themes that emerged this week. "
            "Focus on fundamental shifts and multi-week trends."
        )

        short_ideas = _fetch_ideas(short_prompt)
        long_ideas = _fetch_ideas(long_prompt)

        result = {
            "regime": regime,
            "short_term": short_ideas,
            "long_term": long_ideas,
            "generated_at": date.today().isoformat(),
            "is_weekly": True,
        }
        cache.set("weekly_trade_ideas", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-ideas/history")
def get_trade_ideas_history():
    cached = cache.get("trade_ideas_history")
    if cached:
        return cached
    try:
        history = _load_history()
        today_iso = date.today().isoformat()
        past = [i for i in history if i.get("entry_date", today_iso) != today_iso]
        # Limit to 10 most recent to avoid yfinance rate limits / timeouts
        result = []
        for idea in past[:10]:
            pnl_data = _calculate_pnl(idea)
            result.append({**idea, **pnl_data})
        response = {"ideas": result}
        cache.set("trade_ideas_history", response)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Common asset name → ticker mapping for backtest
ASSET_NAME_TO_TICKER: dict[str, str] = {
    "s&p 500": "^GSPC", "s&p": "^GSPC", "spx": "^GSPC", "spy": "SPY",
    "nasdaq": "^IXIC", "qqq": "QQQ", "tech": "XLK",
    "gold": "GC=F", "silver": "SI=F",
    "oil": "CL=F", "crude oil": "CL=F", "wti": "CL=F", "brent": "BZ=F",
    "natural gas": "NG=F",
    "bitcoin": "BTC-USD", "btc": "BTC-USD",
    "ethereum": "ETH-USD", "eth": "ETH-USD",
    "10y treasury": "^TNX", "10-year": "^TNX", "treasuries": "^TNX",
    "bonds": "TLT", "tlt": "TLT", "hy bonds": "HYG", "high yield": "HYG",
    "usd": "DX-Y.NYB", "dollar": "DX-Y.NYB", "dxy": "DX-Y.NYB",
    "eur/usd": "EURUSD=X", "euro": "EURUSD=X",
    "usd/jpy": "USDJPY=X", "yen": "USDJPY=X",
    "gbp/usd": "GBPUSD=X",
    "vix": "^VIX", "volatility": "^VIX",
    "emerging markets": "EEM", "em": "EEM",
    "energy": "XLE", "financials": "XLF", "healthcare": "XLV",
    "real estate": "XLRE", "reit": "XLRE",
    "copper": "HG=F", "wheat": "ZW=F", "corn": "ZC=F",
    "japan": "^N225", "nikkei": "^N225",
    "china": "FXI", "hang seng": "^HSI",
    "europe": "^STOXX50E", "dax": "^GDAXI",
    "uk": "^FTSE", "ftse": "^FTSE",
}

PERIOD_MAP = {"1w": "5d", "1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}


def resolve_ticker(name: str) -> str | None:
    key = name.lower().strip()
    if key in ASSET_NAME_TO_TICKER:
        return ASSET_NAME_TO_TICKER[key]
    # Try partial match
    for k, v in ASSET_NAME_TO_TICKER.items():
        if k in key or key in k:
            return v
    # Assume it might already be a valid ticker
    return name.upper() if len(name) <= 6 else None


@router.get("/backtest")
def backtest_assets(
    assets: str = Query(..., description="Comma-separated asset names from trade idea"),
    period: str = Query("3m", description="1w, 1m, 3m, 6m, 1y"),
):
    yf_period = PERIOD_MAP.get(period, "3mo")
    names = [a.strip() for a in assets.split(",") if a.strip()]

    results = []
    for name in names:
        ticker = resolve_ticker(name)
        if not ticker:
            continue
        try:
            data = yf.download(ticker, period=yf_period, auto_adjust=True, progress=False)
            closes = data["Close"].dropna()
            if len(closes) < 2:
                continue

            prices = closes.values.flatten().astype(float)
            total_return = (prices[-1] - prices[0]) / prices[0] * 100
            daily_returns = np.diff(prices) / prices[:-1] * 100

            # Max drawdown
            peak = prices[0]
            max_dd = 0.0
            for p in prices:
                if p > peak:
                    peak = p
                dd = (p - peak) / peak * 100
                if dd < max_dd:
                    max_dd = dd

            win_rate = float(np.sum(daily_returns > 0) / len(daily_returns) * 100)
            volatility = float(np.std(daily_returns))
            best_day = float(np.max(daily_returns))
            worst_day = float(np.min(daily_returns))

            results.append({
                "name": name,
                "ticker": ticker,
                "period": period,
                "total_return": round(total_return, 2),
                "max_drawdown": round(max_dd, 2),
                "win_rate": round(win_rate, 1),
                "volatility_daily": round(volatility, 2),
                "best_day": round(best_day, 2),
                "worst_day": round(worst_day, 2),
                "start_price": round(float(prices[0]), 4),
                "end_price": round(float(prices[-1]), 4),
                "data_points": len(prices),
            })
        except Exception:
            continue

    return {"assets": results, "period": period}
