from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from cache import cache
from services.report_generator import generate_report
from services.weekly_report_generator import generate_weekly_report
from services.macro_calendar import get_upcoming_events, get_central_banks
from services.sector_rotation import get_sector_rotation

router = APIRouter()

VALID_PERIODS = {"1d", "1w", "1m", "3m", "6m", "1y"}


@router.get("")
def get_report(period: str = Query("1d", description="Period: 1d, 1w, 1m, 3m, 6m, 1y")):
    if period not in VALID_PERIODS:
        period = "1d"
    # Keep 1w routed through the weekly generator for existing compatibility
    if period == "1w":
        cache_key = "weekly_report"
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            report = generate_weekly_report()
            report["generated_at"] = datetime.now(timezone.utc).isoformat()
            cache.set(cache_key, report)
            return report
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    cache_key = f"report_{period}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        report = generate_report(period=period)
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set(cache_key, report)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly")
def get_weekly_report():
    cached = cache.get("weekly_report")
    if cached:
        return cached
    try:
        report = generate_weekly_report()
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set("weekly_report", report)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sector-rotation")
def get_sector_rotation_data():
    cached = cache.get("sector_rotation")
    if cached:
        return cached
    try:
        result = get_sector_rotation()
        cache.set("sector_rotation", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar")
def get_calendar():
    return {
        "events": get_upcoming_events(days=21),
        "central_banks": get_central_banks(),
    }
