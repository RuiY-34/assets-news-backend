from fastapi import APIRouter, Query
from datetime import date as date_type
import numpy as np
import yfinance as yf
import json
from services.ai_client import ask_ai


def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = np.diff(prices[-(period * 3):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100.0 - (100.0 / (1 + rs)))


def _get_technicals(symbol: str) -> dict:
    try:
        data = yf.download(symbol, period="1y", auto_adjust=True, progress=False)
        closes = data["Close"].dropna().values.flatten().astype(float)
        if len(closes) < 15:
            return {}

        current = closes[-1]
        rsi = round(_calculate_rsi(closes), 1)
        ma50 = round(float(np.mean(closes[-50:])), 4) if len(closes) >= 50 else None
        ma200 = round(float(np.mean(closes[-200:])), 4) if len(closes) >= 200 else None
        pct_vs_50 = round((current - ma50) / ma50 * 100, 2) if ma50 else None
        pct_vs_200 = round((current - ma200) / ma200 * 100, 2) if ma200 else None

        # Signal
        if rsi >= 70:
            signal = "overbought"
        elif rsi <= 30:
            signal = "oversold"
        elif ma50 and ma200:
            if current > ma50 and current > ma200:
                signal = "bullish"
            elif current < ma50 and current < ma200:
                signal = "bearish"
            else:
                signal = "mixed"
        else:
            signal = "neutral"

        # Golden / Death cross (50MA crosses 200MA)
        cross = None
        if ma50 and ma200 and len(closes) >= 201:
            prev_ma50 = float(np.mean(closes[-51:-1]))
            prev_ma200 = float(np.mean(closes[-201:-1]))
            if prev_ma50 < prev_ma200 and ma50 > ma200:
                cross = "golden_cross"
            elif prev_ma50 > prev_ma200 and ma50 < ma200:
                cross = "death_cross"

        return {
            "rsi": rsi,
            "ma50": ma50,
            "ma200": ma200,
            "pct_vs_50ma": pct_vs_50,
            "pct_vs_200ma": pct_vs_200,
            "signal": signal,
            "cross": cross,
        }
    except Exception:
        return {}

router = APIRouter()

_ANALYST_SYSTEM = "You are a financial analyst. Respond with valid JSON only — no markdown, no extra text."


def _ask_ai(prompt: str) -> str:
    return ask_ai(_ANALYST_SYSTEM, prompt)


@router.get("/prices")
def get_watchlist_prices(symbols: str = Query(..., description="Comma-separated ticker symbols")):
    tickers = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not tickers:
        return []

    try:
        if len(tickers) == 1:
            data = yf.download(tickers[0], period="2d", auto_adjust=True, progress=False)
            closes = data["Close"] if "Close" in data else data
        else:
            data = yf.download(tickers, period="2d", auto_adjust=True, progress=False, threads=True)
            closes = data["Close"] if "Close" in data else data
    except Exception:
        return []

    results = []
    for symbol in tickers:
        try:
            if len(tickers) == 1:
                series = closes.dropna()
            else:
                series = closes[symbol].dropna()

            if len(series) < 1:
                results.append({"symbol": symbol, "price": None, "change_1d": None})
                continue

            curr = float(series.iloc[-1])
            prev = float(series.iloc[-2]) if len(series) >= 2 else curr
            chg = (curr - prev) / prev * 100 if prev != 0 else 0.0

            results.append({
                "symbol": symbol,
                "price": round(curr, 4),
                "change_1d": round(chg, 2),
            })
        except Exception:
            results.append({"symbol": symbol, "price": None, "change_1d": None})

    return results


@router.get("/detail/{symbol}")
def get_watchlist_detail(symbol: str):
    symbol = symbol.upper()

    # Performance across timeframes
    periods = {"1w": "5d", "1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}
    performance = {}
    ticker = yf.Ticker(symbol)

    for label, period in periods.items():
        try:
            data = yf.download(symbol, period=period, auto_adjust=True, progress=False)
            closes = data["Close"].dropna()
            if len(closes) >= 2:
                start = float(closes.iloc[0])
                end = float(closes.iloc[-1])
                performance[label] = round((end - start) / start * 100, 2)
            else:
                performance[label] = None
        except Exception:
            performance[label] = None

    # News
    news = []
    try:
        raw_news = ticker.news or []
        for n in raw_news[:6]:
            content = n.get("content", {})
            title = content.get("title", "")
            if not title:
                continue
            news.append({
                "title": title,
                "source": content.get("provider", {}).get("displayName", "Yahoo Finance"),
                "published": content.get("pubDate", ""),
            })
    except Exception:
        pass

    # Build performance summary for AI
    perf_text = "\n".join(
        f"- {k}: {v:+.2f}%" if v is not None else f"- {k}: N/A"
        for k, v in performance.items()
    )
    headlines_text = "\n".join(f"- {n['title']}" for n in news) or "No recent news."

    # AI analysis
    ai_analysis = {}
    try:
        raw = json.loads(_ask_ai(
            f"You are analysing the fund/asset: {symbol}.\n\n"
            f"Recent performance:\n{perf_text}\n\n"
            f"Recent news headlines:\n{headlines_text}\n\n"
            f"Respond with a JSON object with these exact keys:\n"
            f"- 'news_impact': 2 sentences on how recent news has impacted or may impact this asset\n"
            f"- 'short_term': 1-2 sentences on short-term outlook (1-4 weeks)\n"
            f"- 'mid_term': 1-2 sentences on mid-term outlook (1-3 months)\n"
            f"- 'long_term': 1-2 sentences on long-term outlook (6-12 months)\n"
            f"- 'signal': 'bullish', 'bearish', or 'neutral' overall"
        ))
        if isinstance(raw, dict):
            ai_analysis = raw
    except Exception:
        pass

    technicals = _get_technicals(symbol)

    return {
        "symbol": symbol,
        "performance": performance,
        "news": news,
        "ai_analysis": ai_analysis,
        "technicals": technicals,
    }


@router.get("/backtest/{symbol}")
def backtest_symbol(
    symbol: str,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    action: str = Query("buy", description="buy or sell"),
    amount: float = Query(10000, description="Amount in GBP/USD"),
):
    symbol = symbol.upper()
    try:
        data = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True, progress=False)
        closes = data["Close"].dropna()

        if len(closes) < 2:
            return {"error": "Not enough data for this date range."}

        prices = closes.values.flatten().astype(float)
        dates = [str(d.date()) for d in closes.index.tolist()]

        entry_price = prices[0]
        exit_price = prices[-1]
        pct_return = (exit_price - entry_price) / entry_price * 100

        # If sell, returns are inverted
        if action == "sell":
            pct_return = -pct_return

        dollar_pnl = (pct_return / 100) * amount
        shares = amount / entry_price

        # Daily returns for stats
        daily_returns = np.diff(prices) / prices[:-1] * 100
        if action == "sell":
            daily_returns = -daily_returns

        # Max drawdown
        peak = prices[0]
        max_dd = 0.0
        for p in prices:
            if p > peak:
                peak = p
            dd = (p - peak) / peak * 100
            if dd < max_dd:
                max_dd = dd
        if action == "sell":
            max_dd = -max_dd

        # Chart data (sample up to 60 points)
        step = max(1, len(prices) // 60)
        chart = [
            {"date": dates[i], "price": round(float(prices[i]), 4)}
            for i in range(0, len(prices), step)
        ]

        return {
            "symbol": symbol,
            "action": action,
            "start_date": start_date,
            "end_date": end_date,
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "pct_return": round(pct_return, 2),
            "dollar_pnl": round(dollar_pnl, 2),
            "amount_invested": amount,
            "shares": round(shares, 4),
            "days": len(prices),
            "max_drawdown": round(max_dd, 2),
            "win_rate": round(float(np.sum(daily_returns > 0) / len(daily_returns) * 100), 1),
            "best_day": round(float(np.max(daily_returns)), 2),
            "worst_day": round(float(np.min(daily_returns)), 2),
            "chart": chart,
        }
    except Exception as e:
        return {"error": str(e)}
