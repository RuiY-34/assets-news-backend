from datetime import date, timedelta

CENTRAL_BANKS = [
    {
        "bank": "Federal Reserve",
        "currency": "USD",
        "current_rate": 4.25,
        "next_meeting": "2026-05-07",
        "last_decision": "Hold",
        "implied_next": "Hold / -25bp",
        "notes": "Wait-and-see amid tariff uncertainty",
    },
    {
        "bank": "Bank of England",
        "currency": "GBP",
        "current_rate": 4.50,
        "next_meeting": "2026-05-08",
        "last_decision": "-25bp",
        "implied_next": "-25bp",
        "notes": "Cutting cycle continues, weak growth",
    },
    {
        "bank": "European Central Bank",
        "currency": "EUR",
        "current_rate": 2.25,
        "next_meeting": "2026-06-05",
        "last_decision": "-25bp",
        "implied_next": "-25bp",
        "notes": "Inflation near target, cutting continues",
    },
    {
        "bank": "Bank of Japan",
        "currency": "JPY",
        "current_rate": 0.50,
        "next_meeting": "2026-06-17",
        "last_decision": "Hold",
        "implied_next": "Hold",
        "notes": "Watching yen and wage data",
    },
    {
        "bank": "PBoC",
        "currency": "CNY",
        "current_rate": 3.10,
        "next_meeting": "2026-05-20",
        "last_decision": "Hold",
        "implied_next": "-10bp",
        "notes": "Easing pressure from trade war",
    },
]

# prev = prior release value, consensus = market estimate
MACRO_EVENTS = [
    # ── May 2026 ──
    {"date": "2026-05-05", "event": "ISM Services PMI (Apr)",        "importance": "high",   "region": "US", "prev": "50.8", "consensus": "51.0", "unit": ""},
    {"date": "2026-05-07", "event": "Fed Rate Decision",              "importance": "high",   "region": "US", "prev": "4.25%", "consensus": "Hold", "unit": ""},
    {"date": "2026-05-07", "event": "Fed Press Conference",           "importance": "high",   "region": "US", "prev": "", "consensus": "", "unit": ""},
    {"date": "2026-05-08", "event": "BoE Rate Decision",              "importance": "high",   "region": "UK", "prev": "4.50%", "consensus": "-25bp", "unit": ""},
    {"date": "2026-05-09", "event": "CPI (Apr)",                      "importance": "high",   "region": "US", "prev": "2.4%", "consensus": "2.3%", "unit": "YoY"},
    {"date": "2026-05-12", "event": "PPI (Apr)",                      "importance": "high",   "region": "US", "prev": "2.7%", "consensus": "2.5%", "unit": "YoY"},
    {"date": "2026-05-13", "event": "UK GDP (Mar)",                   "importance": "high",   "region": "UK", "prev": "0.5%", "consensus": "0.1%", "unit": "MoM"},
    {"date": "2026-05-14", "event": "Retail Sales (Apr)",             "importance": "high",   "region": "US", "prev": "-0.1%", "consensus": "0.2%", "unit": "MoM"},
    {"date": "2026-05-15", "event": "Michigan Consumer Sentiment",    "importance": "medium", "region": "US", "prev": "52.2", "consensus": "53.0", "unit": ""},
    {"date": "2026-05-15", "event": "Industrial Production (Apr)",    "importance": "medium", "region": "US", "prev": "-0.3%", "consensus": "0.1%", "unit": "MoM"},
    {"date": "2026-05-21", "event": "PMI Flash (May)",                "importance": "medium", "region": "US", "prev": "50.8", "consensus": "51.0", "unit": ""},
    {"date": "2026-05-21", "event": "PMI Flash (May)",                "importance": "medium", "region": "EU", "prev": "50.4", "consensus": "50.5", "unit": ""},
    {"date": "2026-05-22", "event": "FOMC Minutes",                   "importance": "high",   "region": "US", "prev": "", "consensus": "", "unit": ""},
    {"date": "2026-05-27", "event": "GDP Q1 Second Estimate",         "importance": "high",   "region": "US", "prev": "-0.3%", "consensus": "-0.2%", "unit": "QoQ"},
    {"date": "2026-05-29", "event": "PCE Inflation (Apr)",            "importance": "high",   "region": "US", "prev": "2.6%", "consensus": "2.5%", "unit": "YoY"},
    {"date": "2026-05-30", "event": "Core PCE (Apr)",                 "importance": "high",   "region": "US", "prev": "2.8%", "consensus": "2.6%", "unit": "YoY"},
    # ── June 2026 ──
    {"date": "2026-06-03", "event": "ISM Manufacturing PMI (May)",   "importance": "medium", "region": "US", "prev": "48.7", "consensus": "49.5", "unit": ""},
    {"date": "2026-06-05", "event": "Non-Farm Payrolls (May)",        "importance": "high",   "region": "US", "prev": "177K", "consensus": "150K", "unit": ""},
    {"date": "2026-06-05", "event": "Unemployment Rate (May)",        "importance": "high",   "region": "US", "prev": "4.2%", "consensus": "4.3%", "unit": ""},
    {"date": "2026-06-05", "event": "ECB Rate Decision",              "importance": "high",   "region": "EU", "prev": "2.25%", "consensus": "-25bp", "unit": ""},
    {"date": "2026-06-11", "event": "CPI (May)",                      "importance": "high",   "region": "US", "prev": "2.3%", "consensus": "2.2%", "unit": "YoY"},
    {"date": "2026-06-18", "event": "Fed Rate Decision",              "importance": "high",   "region": "US", "prev": "4.25%", "consensus": "Hold", "unit": ""},
    {"date": "2026-06-26", "event": "PCE Inflation (May)",            "importance": "high",   "region": "US", "prev": "2.5%", "consensus": "2.4%", "unit": "YoY"},
]


def get_upcoming_events(days: int = 30) -> list[dict]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    upcoming = []
    for e in MACRO_EVENTS:
        event_date = date.fromisoformat(e["date"])
        if today <= event_date <= cutoff:
            days_away = (event_date - today).days
            upcoming.append({**e, "days_away": days_away})
    return sorted(upcoming, key=lambda x: x["date"])


def get_central_banks() -> list[dict]:
    today = date.today()
    result = []
    for cb in CENTRAL_BANKS:
        meeting_date = date.fromisoformat(cb["next_meeting"])
        days_to_meeting = (meeting_date - today).days
        result.append({**cb, "days_to_meeting": days_to_meeting})
    return sorted(result, key=lambda x: x["days_to_meeting"])
