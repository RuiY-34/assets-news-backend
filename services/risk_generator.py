import json
from datetime import date
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
        print(f"[risk_generator] section error: {e}")
    return {"summary": "", "points": []}


PERIOD_CHANGE_LABEL = {
    "1d": "1d", "1w": "5d", "1m": "1m", "3m": "3m", "6m": "6m", "1y": "1y",
}


def _format_indicators(indicators: dict, period: str = "1d") -> str:
    chg_label = PERIOD_CHANGE_LABEL.get(period, "period")
    lines = []
    for v in indicators.values():
        lines.append(
            f"- {v['name']} ({v['symbol']}): {v['price']} | 1d: {v['change_1d']:+.2f}% | {chg_label}: {v['change_5d']:+.2f}%"
        )
    return "\n".join(lines) or "No data."


PERIOD_LABELS = {
    "1d": "today",
    "1w": "this week",
    "1m": "the past month",
    "3m": "the past quarter",
    "6m": "the past 6 months",
    "1y": "the past year",
}

PERIOD_HORIZONS = {
    "1d": "next 1-2 days",
    "1w": "next 1-2 weeks",
    "1m": "next 4-6 weeks",
    "3m": "next 2-3 months",
    "6m": "next 3-6 months",
    "1y": "next 6-12 months",
}


def generate_risk_report(period: str = "1d") -> dict:
    period_label  = PERIOD_LABELS.get(period, "today")
    horizon_label = PERIOD_HORIZONS.get(period, "next 1-2 days")

    indicators = get_risk_indicators(period=period)
    news = get_risk_news()
    today = date.today().strftime("%B %d, %Y")

    ind_text = _format_indicators(indicators, period=period)
    headlines = "\n".join(f"- {n['title']}" for n in news[:8]) or "No headlines."

    vix = indicators.get("^VIX", {})
    vix_level = vix.get("price", "N/A")
    vix_1d = vix.get("change_1d", 0)

    # Overall risk score
    try:
        score_raw = json.loads(_ask(
            f"Today is {today}. Analysing {period_label}. Based on these risk indicators, give an overall market risk score from 1-10 "
            f"(1=very low risk, 10=extreme risk) and a one-sentence justification for the {horizon_label} outlook. "
            f"Respond as JSON: {{\"score\": <number>, \"justification\": \"<string>\"}}\n\n"
            f"Indicators:\n{ind_text}"
        ))
        risk_score = int(score_raw.get("score", 5))
        risk_justification = score_raw.get("justification", "")
    except Exception:
        risk_score = 5
        risk_justification = ""

    # Volatility section
    vol_section = _ask_section(
        f"Today is {today}. Period: {period_label}. Analyse this volatility data (VIX={vix_level}, 1d change={vix_1d:+.2f}%) "
        f"and give a JSON with 'summary' (2 sentences on vol regime for the {horizon_label}) "
        f"and 'points' (3 bullet strings on vol surface, term structure, and positioning implications).\n\n"
        f"Indicators:\n{ind_text}"
    )

    # Credit risk section
    credit_section = _ask_section(
        f"Today is {today}. Period: {period_label}. Analyse credit risk based on HY/IG bond ETF movements and give a JSON with "
        f"'summary' (2 sentences on credit spread dynamics for the {horizon_label}) "
        f"and 'points' (3 bullet strings on IG spreads, HY spreads, and credit positioning).\n\n"
        f"Indicators:\n{ind_text}"
    )

    # Liquidity & market stress
    liquidity_section = _ask_section(
        f"Today is {today}. Period: {period_label}. Based on Treasury yields, USD index, and safe haven flows (Gold, JPY), "
        f"give a JSON with 'summary' (2 sentences on liquidity conditions for the {horizon_label}) "
        f"and 'points' (3 bullet strings on Treasury market, USD liquidity, and safe haven demand).\n\n"
        f"Indicators:\n{ind_text}"
    )

    # Geopolitical & tail risks
    try:
        tail_raw = json.loads(_ask(
            f"Today is {today}. Period: {period_label}. Based on these news headlines and market data, identify the top tail risks for the {horizon_label}. "
            f"Respond as JSON: {{\"tail_risks\": [\"risk1\", \"risk2\", \"risk3\"], "
            f"\"geopolitical\": \"1-2 sentences on geopolitical risks\", "
            f"\"macro_tail\": \"1-2 sentences on macro tail risks\"}}\n\n"
            f"Headlines:\n{headlines}\n\nIndicators:\n{ind_text}"
        ))
        if not isinstance(tail_raw, dict):
            tail_raw = {}
        tail_risks = _normalize_points(tail_raw.get("tail_risks", []))
        geopolitical = tail_raw.get("geopolitical", "")
        macro_tail = tail_raw.get("macro_tail", "")
    except Exception as e:
        print(f"[risk_generator] tail error: {e}")
        tail_risks, geopolitical, macro_tail = [], "", ""

    # Risk action summary
    try:
        action_raw = json.loads(_ask(
            f"Today is {today}. Period: {period_label}. Given overall risk score {risk_score}/10 and this market data, "
            f"give a JSON with 'hedging' (1-2 sentences on hedging strategies for {horizon_label}), "
            f"'positioning' (1-2 sentences on recommended risk positioning), "
            f"and 'watch_levels' (array of 3 strings: key levels to watch).\n\n"
            f"Indicators:\n{ind_text}"
        ))
        if not isinstance(action_raw, dict):
            action_raw = {}
        hedging = action_raw.get("hedging", "")
        positioning = action_raw.get("positioning", "")
        watch_levels = _normalize_points(action_raw.get("watch_levels", []))
    except Exception as e:
        print(f"[risk_generator] action error: {e}")
        hedging, positioning, watch_levels = "", "", []

    return {
        "risk_score": risk_score,
        "risk_justification": risk_justification,
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
        "period": period,
    }
