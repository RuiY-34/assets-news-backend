import httpx
from datetime import date, timedelta

# Central bank current rates and next meeting dates (updated manually or via news)
CENTRAL_BANKS = [
    {
        "bank": "Federal Reserve (Fed)",
        "currency": "USD",
        "current_rate": 4.25,
        "next_meeting": "2026-05-07",
        "last_decision": "Hold",
        "implied_next": "Hold / -25bp",
        "notes": "Fed in wait-and-see mode amid tariff uncertainty",
    },
    {
        "bank": "Bank of England (BoE)",
        "currency": "GBP",
        "current_rate": 4.50,
        "next_meeting": "2026-05-08",
        "last_decision": "-25bp",
        "implied_next": "Hold / -25bp",
        "notes": "BoE cautious on inflation persistence vs weak growth",
    },
    {
        "bank": "European Central Bank (ECB)",
        "currency": "EUR",
        "current_rate": 2.50,
        "next_meeting": "2026-04-17",
        "last_decision": "-25bp",
        "implied_next": "-25bp",
        "notes": "ECB cutting cycle continuing, inflation near target",
    },
    {
        "bank": "Bank of Japan (BoJ)",
        "currency": "JPY",
        "current_rate": 0.50,
        "next_meeting": "2026-04-30",
        "last_decision": "+25bp",
        "implied_next": "Hold",
        "notes": "BoJ hiking cautiously, watching yen and wage data",
    },
    {
        "bank": "People's Bank of China (PBoC)",
        "currency": "CNY",
        "current_rate": 3.10,
        "next_meeting": "2026-04-20",
        "last_decision": "Hold",
        "implied_next": "-10bp",
        "notes": "PBoC under pressure to ease amid trade war impact",
    },
]

# Key macro events — updated with upcoming scheduled releases
MACRO_EVENTS = [
    {"date": "2026-04-08", "event": "US NFIB Small Business Optimism", "importance": "medium", "region": "US"},
    {"date": "2026-04-09", "event": "US CPI (Mar)", "importance": "high", "region": "US"},
    {"date": "2026-04-09", "event": "FOMC Minutes", "importance": "high", "region": "US"},
    {"date": "2026-04-10", "event": "US PPI (Mar)", "importance": "high", "region": "US"},
    {"date": "2026-04-10", "event": "UK GDP (Feb)", "importance": "high", "region": "UK"},
    {"date": "2026-04-11", "event": "US Michigan Consumer Sentiment", "importance": "medium", "region": "US"},
    {"date": "2026-04-14", "event": "US Retail Sales (Mar)", "importance": "high", "region": "US"},
    {"date": "2026-04-15", "event": "China GDP Q1 2026", "importance": "high", "region": "CN"},
    {"date": "2026-04-16", "event": "US Industrial Production", "importance": "medium", "region": "US"},
    {"date": "2026-04-17", "event": "ECB Rate Decision", "importance": "high", "region": "EU"},
    {"date": "2026-04-23", "event": "US PMI Flash (Apr)", "importance": "medium", "region": "US"},
    {"date": "2026-04-23", "event": "UK PMI Flash (Apr)", "importance": "medium", "region": "UK"},
    {"date": "2026-04-24", "event": "US Durable Goods Orders", "importance": "medium", "region": "US"},
    {"date": "2026-04-30", "event": "US GDP Q1 Advance", "importance": "high", "region": "US"},
    {"date": "2026-04-30", "event": "BoJ Rate Decision", "importance": "high", "region": "JP"},
    {"date": "2026-05-02", "event": "US Non-Farm Payrolls (Apr)", "importance": "high", "region": "US"},
    {"date": "2026-05-07", "event": "Fed Rate Decision", "importance": "high", "region": "US"},
    {"date": "2026-05-08", "event": "BoE Rate Decision", "importance": "high", "region": "UK"},
]


def get_upcoming_events(days: int = 14) -> list[dict]:
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
