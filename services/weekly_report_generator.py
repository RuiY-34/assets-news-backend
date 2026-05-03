import json
from datetime import date, timedelta
from services.market_data import get_weekly_movers
from services.news_fetcher import fetch_news
from services.ai_client import ask_ai

SYSTEM_PROMPT = """You are a financial analyst. Respond with valid JSON only — no markdown, no extra text."""


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


def generate_weekly_report() -> dict:
    sectors      = get_weekly_movers("sectors")
    regions      = get_weekly_movers("regions")
    fixed_income = get_weekly_movers("fixed_income")
    forex        = get_weekly_movers("forex")
    commodities  = get_weekly_movers("commodities")

    all_news = fetch_news("stocks") + fetch_news("forex") + fetch_news("commodities")
    eq_news  = fetch_news("equities_news")
    headlines = "\n".join(f"- {n['title']}" for n in (all_news + eq_news)[:10]) or "No headlines."

    cb_news = fetch_news("central_banks") + fetch_news("boe")
    cb_headlines = "\n".join(f"- {n['title']}" for n in cb_news[:6]) or "No central bank news."

    week_end = date.today()
    week_start = week_end - timedelta(days=6)
    week_str = f"{week_start.strftime('%B %d')} – {week_end.strftime('%B %d, %Y')}"

    sec_text = _format_movers(sectors)
    reg_text = _format_movers(regions)
    fi_text  = _format_movers(fixed_income)
    fx_text  = _format_movers(forex)
    com_text = _format_movers(commodities)

    macro = _ask_list(
        f"Given these weekly headlines and market moves, give 3 macro overview bullet points for the week as a JSON array of strings.\n"
        f"Headlines: {headlines}\nRegions: {reg_text}\nFX: {fx_text}"
    )

    try:
        eq_section = json.loads(_ask(
            f"You are an equity strategist. Week of {week_str}. "
            f"Analyse these weekly sector and regional market moves and respond with a JSON object with these exact keys:\n"
            f"- 'summary': 2 sentence overview of global equity markets this week\n"
            f"- 'sectors': 1-2 sentences on best and worst performing sectors this week and why\n"
            f"- 'regions': 1-2 sentences comparing US, Europe, and Asia weekly performance\n"
            f"- 'reasons': 1-2 sentences explaining the key drivers behind this week's moves\n"
            f"- 'strategy_insight': 1-2 sentences of actionable insight for equity traders heading into next week\n"
            f"- 'points': array of 3 key bullet points for the week\n\n"
            f"Sector data (weekly):\n{sec_text}\n\nRegional indices (weekly):\n{reg_text}\n\nNews:\n{headlines}"
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
            f"You are a fixed income strategist. Week of {week_str}. "
            f"Analyse this weekly bond market data and central bank news and respond with a JSON object with these exact keys:\n"
            f"- 'summary': 2 sentence overview of fixed income this week\n"
            f"- 'yield_curve': 1-2 sentences on yield curve changes this week and what they signal\n"
            f"- 'credit_spreads': 1-2 sentences on IG vs HY credit spread movements this week\n"
            f"- 'strategy_insight': 1-2 sentences of actionable insight for bond traders heading into next week\n"
            f"- 'rate_expectations': 1-2 sentences on Fed/BoE policy rate outlook based on this week's news\n"
            f"- 'points': array of 3 key bullet points\n\n"
            f"Bond market data (weekly):\n{fi_text}\n\n"
            f"Central bank news this week:\n{cb_headlines}"
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
        f"Analyse these weekly FX and commodity movers and give a JSON object with 'summary' (2 sentences on the week) and 'points' (3 bullet strings).\nFX: {fx_text}\nCommodities: {com_text}"
    )

    risks = _ask_list(
        f"Based on this week's market data, list 3 key risks heading into next week as a JSON array of strings.\n"
        f"Equities: {sec_text}\nFX: {fx_text}\nHeadlines: {headlines}"
    )

    insight = json.loads(_ask(
        f"Give one actionable financial insight paragraph about what to watch next week as a JSON string.\n"
        f"Equities: {sec_text}\nFixed Income: {fi_text}"
    ))
    if isinstance(insight, dict):
        insight = insight.get("insight", "")

    summary = json.loads(_ask(
        f"Summarise this week's markets in one sentence as a JSON string.\n"
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
        "is_weekly":             True,
        "week_label":            week_str,
    }
