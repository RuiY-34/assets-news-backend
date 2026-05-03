import json
from services.ai_client import ask_ai

SYSTEM_PROMPT = """You are a financial analyst assistant. Given market movers and news headlines,
produce a concise strategic signal. Always respond with valid JSON only — no markdown, no extra text."""

USER_PROMPT = """Asset class: {asset_type}

Top movers:
{movers}

Latest news headlines:
{headlines}

Respond with this JSON structure:
{{
  "signal": "bullish" | "bearish" | "neutral",
  "summary": "2-3 sentence strategic overview",
  "key_points": ["point 1", "point 2", "point 3"],
  "risk_level": "low" | "medium" | "high"
}}"""

WEEKLY_PROMPT = """Asset class: {asset_type}

Weekly movers (this week's performance):
{movers}

News headlines this week:
{headlines}

Give a weekly strategic overview. Respond with this JSON structure:
{{
  "signal": "bullish" | "bearish" | "neutral",
  "summary": "2-3 sentence weekly review and outlook for next week",
  "key_points": ["point 1 about this week", "point 2 about this week", "point 3 heading into next week"],
  "risk_level": "low" | "medium" | "high"
}}"""


def analyze(asset_type: str, movers: list[dict], news: list[dict], weekly: bool = False) -> dict:
    movers_text = "\n".join(
        f"- {m['name']} ({m['symbol']}): {m['change_pct']:+.2f}% @ {m['price']}"
        for m in movers
    )
    headlines_text = "\n".join(
        f"- {n['title']} ({n['source']})" for n in news
    ) or "No headlines available."

    prompt_template = WEEKLY_PROMPT if weekly else USER_PROMPT
    user_content = prompt_template.format(
        asset_type=asset_type,
        movers=movers_text,
        headlines=headlines_text,
    )

    try:
        return json.loads(ask_ai(SYSTEM_PROMPT, user_content))
    except Exception:
        return {
            "signal": "neutral",
            "summary": "AI analysis unavailable.",
            "key_points": [],
            "risk_level": "medium",
        }
