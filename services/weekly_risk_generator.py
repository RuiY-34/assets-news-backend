import json
from datetime import date, timedelta
from services.risk_data import get_risk_indicators, get_risk_news
from services.ai_client import ask_ai

SYSTEM_PROMPT = """You are a senior risk manager at a hedge fund. Respond with valid JSON only — no markdown, no extra text."""


def _ask(question: str) -> str:
    return ask_ai(SYSTEM_PROMPT, question)


def _normalize_points(points: list) -> list[str]:
    result = []
    for p in points:
        if isinstance(p, str):
            result.append(p)
        elif isinstance(p, dict):
            result.append(next(iter(p.values()), ""))
    return result


def _ask_section(prompt: str) -> dict:
    try:
        result = json.loads(_ask(prompt))
        if isinstance(result, dict):
            return {
                "summary": result.get("summary", ""),
                "points": _normalize_points(result.get("points", [])),
            }
    except Exception as e:
        print(f"[weekly_risk_generator] section error: {e}")
    return {"summary": "", "points": []}


def _format_indicators(indicators: dict) -> str:
    lines = []
    for v in indicators.values():
        lines.append(
            f"- {v['name']} ({v['symbol']}): {v['price']} | 1d: {v['change_1d']:+.2f}% | 5d: {v['change_5d']:+.2f}%"
        )
    return "\n".join(lines) or "No data."


def generate_weekly_risk_report() -> dict:
    indicators = get_risk_indicators()
    news = get_risk_news()

    week_end = date.today()
    week_start = week_end - timedelta(days=6)
    week_str = f"{week_start.strftime('%B %d')} – {week_end.strftime('%B %d, %Y')}"

    ind_text = _format_indicators(indicators)
    headlines = "\n".join(f"- {n['title']}" for n in news[:8]) or "No headlines."

    vix = indicators.get("^VIX", {})
    vix_level = vix.get("price", "N/A")
    vix_5d = vix.get("change_5d", 0)

    try:
        score_raw = json.loads(_ask(
            f"Week of {week_str}. Based on these weekly risk indicator moves, give an overall market risk score from 1-10 "
            f"(1=very low risk, 10=extreme risk) and a one-sentence justification summarising this week's risk environment. "
            f"Respond as JSON: {{\"score\": <number>, \"justification\": \"<string>\"}}\n\n"
            f"Indicators (5d moves shown):\n{ind_text}"
        ))
        risk_score = int(score_raw.get("score", 5))
        risk_justification = score_raw.get("justification", "")
    except Exception:
        risk_score = 5
        risk_justification = ""

    market_risk_section = _ask_section(
        f"Week of {week_str}. Analyse equity market risk based on this week's S&P 500 performance and VIX moves "
        f"and give a JSON with 'summary' (2 sentences on equity market risk and drawdown potential heading into next week) "
        f"and 'points' (3 bullet strings on: weekly market momentum, downside risk, and correlation risks).\n\n"
        f"Indicators:\n{ind_text}"
    )

    vol_section = _ask_section(
        f"Week of {week_str}. Analyse this week's volatility (VIX={vix_level}, 5d change={vix_5d:+.2f}%) "
        f"and give a JSON with 'summary' (2 sentences on this week's vol regime and what it means heading into next week) "
        f"and 'points' (3 bullet strings on weekly vol trends, term structure, and positioning implications).\n\n"
        f"Indicators:\n{ind_text}"
    )

    credit_section = _ask_section(
        f"Week of {week_str}. Analyse this week's credit risk based on HY/IG bond ETF weekly movements and give a JSON with "
        f"'summary' (2 sentences on this week's credit spread dynamics and default risk sentiment) "
        f"and 'points' (3 bullet strings on weekly IG spreads, HY spreads, and credit positioning into next week).\n\n"
        f"Indicators:\n{ind_text}"
    )

    liquidity_section = _ask_section(
        f"Week of {week_str}. Based on this week's Treasury yields, USD index, and safe haven flows (Gold, JPY), "
        f"give a JSON with 'summary' (2 sentences on this week's liquidity conditions and funding stress) "
        f"and 'points' (3 bullet strings on weekly Treasury market, USD liquidity, and safe haven demand).\n\n"
        f"Indicators:\n{ind_text}"
    )

    try:
        tail_raw = json.loads(_ask(
            f"Week of {week_str}. Based on this week's news headlines and market data, identify the top tail risks heading into next week. "
            f"Respond as JSON: {{\"tail_risks\": [\"risk1\", \"risk2\", \"risk3\"], "
            f"\"geopolitical\": \"1-2 sentences on geopolitical risks this week\", "
            f"\"macro_tail\": \"1-2 sentences on macro tail risks for next week\"}}\n\n"
            f"Headlines:\n{headlines}\n\nIndicators:\n{ind_text}"
        ))
        if not isinstance(tail_raw, dict):
            tail_raw = {}
        tail_risks = _normalize_points(tail_raw.get("tail_risks", []))
        geopolitical = tail_raw.get("geopolitical", "")
        macro_tail = tail_raw.get("macro_tail", "")
    except Exception as e:
        print(f"[weekly_risk_generator] tail error: {e}")
        tail_risks, geopolitical, macro_tail = [], "", ""

    try:
        action_raw = json.loads(_ask(
            f"Week of {week_str}. Given weekly risk score {risk_score}/10 and this week's market data, "
            f"give a JSON with 'hedging' (1-2 sentences on hedging strategies for next week), "
            f"'positioning' (1-2 sentences on recommended risk positioning into next week), "
            f"and 'watch_levels' (array of 3 strings: key levels to watch next week).\n\n"
            f"Indicators:\n{ind_text}"
        ))
        if not isinstance(action_raw, dict):
            action_raw = {}
        hedging = action_raw.get("hedging", "")
        positioning = action_raw.get("positioning", "")
        watch_levels = _normalize_points(action_raw.get("watch_levels", []))
    except Exception as e:
        print(f"[weekly_risk_generator] action error: {e}")
        hedging, positioning, watch_levels = "", "", []

    return {
        "risk_score": risk_score,
        "risk_justification": risk_justification,
        "market_risk": market_risk_section,
        "volatility": vol_section,
        "credit_risk": credit_section,
        "liquidity": liquidity_section,
        "tail_risks": tail_risks,
        "geopolitical": geopolitical,
        "macro_tail": macro_tail,
        "hedging": hedging,
        "positioning": positioning,
        "watch_levels": watch_levels,
        "indicators": list(indicators.values()),
        "news": news[:6],
        "is_weekly": True,
        "week_label": week_str,
    }
