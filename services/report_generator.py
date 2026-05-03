import json
from datetime import date
from services.market_data import get_top_movers, get_period_movers
from services.news_fetcher import fetch_news
from services.ai_client import ask_ai

SYSTEM_PROMPT = """You are a financial analyst. Respond with valid JSON only — no markdown, no extra text."""


def _ask(question: str) -> str:
    return ask_ai(SYSTEM_PROMPT, question)


def _normalize_points(points: list) -> list[str]:
    """Ensure points is always a list of plain strings."""
    result = []
    for p in points:
        if isinstance(p, str):
            result.append(p)
        elif isinstance(p, dict):
            result.append(next(iter(p.values()), ""))
    return result


def _ask_list(prompt: str) -> list:
    result = json.loads(_ask(prompt))
    raw = result if isinstance(result, list) else []
    return _normalize_points(raw)


def _ask_section(prompt: str) -> dict:
    result = json.loads(_ask(prompt))
    if isinstance(result, dict):
        return {
            "summary": result.get("summary", ""),
            "points": _normalize_points(result.get("points", [])),
        }
    return {"summary": "", "points": []}


def _format_movers(movers: list[dict]) -> str:
    return "\n".join(
        f"- {m['name']} ({m['symbol']}): {m['change_pct']:+.2f}% @ {m['price']}"
        for m in movers
    ) or "No data available."


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


def generate_report(period: str = "1d") -> dict:
    period_label   = PERIOD_LABELS.get(period, "today")
    horizon_label  = PERIOD_HORIZONS.get(period, "next 1-2 days")

    sectors      = get_period_movers("sectors", period)
    regions      = get_period_movers("regions", period)
    fixed_income = get_period_movers("fixed_income", period)
    forex        = get_period_movers("forex", period)
    commodities  = get_period_movers("commodities", period)

    all_news = fetch_news("stocks") + fetch_news("forex") + fetch_news("commodities")
    eq_news  = fetch_news("equities_news")
    headlines = "\n".join(f"- {n['title']}" for n in (all_news + eq_news)[:10]) or "No headlines."

    cb_news = fetch_news("central_banks") + fetch_news("boe")
    cb_headlines = "\n".join(f"- {n['title']}" for n in cb_news[:6]) or "No central bank news."
    today = date.today().strftime("%B %d, %Y")

    sec_text = _format_movers(sectors)
    reg_text = _format_movers(regions)
    fi_text  = _format_movers(fixed_income)
    fx_text  = _format_movers(forex)
    com_text = _format_movers(commodities)

    macro = _ask_list(
        f"Given these headlines and market moves for {period_label}, give 3 macro overview bullet points as a JSON array of strings.\n"
        f"Headlines: {headlines}\nRegions: {reg_text}\nFX: {fx_text}"
    )

    try:
        eq_section = json.loads(_ask(
            f"You are an equity strategist. Today is {today}. "
            f"Analyse these sector and regional market moves for {period_label} and respond with a JSON object with these exact keys:\n"
            f"- 'summary': 2 sentence overview of global equity markets for {period_label}\n"
            f"- 'sectors': 1-2 sentences on best and worst performing sectors and why\n"
            f"- 'regions': 1-2 sentences comparing US, Europe, and Asia performance\n"
            f"- 'reasons': 1-2 sentences explaining the key drivers behind the moves\n"
            f"- 'strategy_insight': 1-2 sentences of actionable insight for equity traders looking at the {horizon_label}\n"
            f"- 'points': array of 3 key bullet points\n\n"
            f"Sector data:\n{sec_text}\n\nRegional indices:\n{reg_text}\n\nNews:\n{headlines}"
        ))
    except Exception as e:
        print(f"[eq_section] error: {e}")
        eq_section = {}
    if not isinstance(eq_section, dict):
        eq_section = {}
    eq_section.setdefault("summary", "")
    eq_section.setdefault("sectors", "")
    eq_section.setdefault("regions", "")
    eq_section.setdefault("reasons", "")
    eq_section.setdefault("strategy_insight", "")
    eq_section["points"] = _normalize_points(eq_section.get("points", []))

    try:
        fi_section = json.loads(_ask(
            f"You are a fixed income strategist. Today is {today}. "
            f"Analyse this bond market data for {period_label} and central bank news and respond with a JSON object with these exact keys:\n"
            f"- 'summary': 2 sentence overview\n"
            f"- 'yield_curve': 1-2 sentences on yield curve shape (normal/flat/inverted), steepening or flattening trend, and what it signals\n"
            f"- 'credit_spreads': 1-2 sentences on IG vs HY credit spread movements and risk sentiment implications\n"
            f"- 'strategy_insight': 1-2 sentences of actionable insight for bond traders for the {horizon_label}\n"
            f"- 'rate_expectations': 1-2 sentences on Fed/BoE policy rate outlook based on the latest news — use specific dates and figures, do not guess\n"
            f"- 'points': array of 3 key bullet points\n\n"
            f"Bond market data:\n{fi_text}\n\n"
            f"Latest central bank news:\n{cb_headlines}"
        ))
    except Exception as e:
        print(f"[fi_section] error: {e}")
        fi_section = {}
    if not isinstance(fi_section, dict):
        fi_section = {}
    fi_section.setdefault("summary", "")
    fi_section.setdefault("yield_curve", "")
    fi_section.setdefault("credit_spreads", "")
    fi_section.setdefault("strategy_insight", "")
    fi_section.setdefault("rate_expectations", "")
    fi_section["points"] = _normalize_points(fi_section.get("points", []))

    fx_section = _ask_section(
        f"Analyse these FX and commodity movers for {period_label} and give a JSON object with 'summary' (2 sentences) and 'points' (3 bullet strings).\nFX: {fx_text}\nCommodities: {com_text}"
    )

    risks = _ask_list(
        f"Based on this market data for {period_label}, list 3 key risks for the {horizon_label} as a JSON array of strings.\n"
        f"Equities: {sec_text}\nFX: {fx_text}\nHeadlines: {headlines}"
    )

    insight = json.loads(_ask(
        f"Give one actionable financial insight paragraph for the {horizon_label} as a JSON string.\n"
        f"Equities: {sec_text}\nFixed Income: {fi_text}"
    ))
    if isinstance(insight, dict):
        insight = insight.get("insight", "")

    summary = json.loads(_ask(
        f"Summarise {period_label}'s markets in one sentence as a JSON string.\n"
        f"Equities: {sec_text}\nFX: {fx_text}\nCommodities: {com_text}"
    ))
    if isinstance(summary, dict):
        summary = summary.get("summary", "")

    return {
        "macro_overview":        macro,
        "equities":              eq_section,
        "fixed_income":          fi_section,
        "fx_commodities":        fx_section,
        "key_risks":             risks,
        "quick_insight":         insight if isinstance(insight, str) else str(insight),
        "one_sentence_summary":  summary if isinstance(summary, str) else str(summary),
        "sectors_data":          sectors,
        "regions_data":          regions,
        "fixed_income_data":     fixed_income,
        "fx_commodities_movers": forex + commodities,
        "period":                period,
    }
