from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from cache import cache
from services.risk_generator import generate_risk_report
from services.weekly_risk_generator import generate_weekly_risk_report
from services.cross_asset import get_cross_asset_moves, get_regime_signal, get_positioning
from services.fear_greed import calculate_fear_greed
from services.funding_stress import calculate_funding_stress

router = APIRouter()

VALID_PERIODS = {"1d", "1w", "1m", "3m", "6m", "1y"}


@router.get("")
def get_risk(period: str = Query("1d", description="Period: 1d, 1w, 1m, 3m, 6m, 1y")):
    if period not in VALID_PERIODS:
        period = "1d"
    if period == "1w":
        cache_key = "weekly_risk_report"
        cached = cache.get(cache_key)
        if cached:
            return cached
        try:
            report = generate_weekly_risk_report()
            report["generated_at"] = datetime.now(timezone.utc).isoformat()
            cache.set(cache_key, report)
            return report
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    cache_key = f"risk_{period}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        report = generate_risk_report(period=period)
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set(cache_key, report)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weekly")
def get_weekly_risk():
    cached = cache.get("weekly_risk_report")
    if cached:
        return cached
    try:
        report = generate_weekly_risk_report()
        report["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set("weekly_risk_report", report)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fear-greed")
def get_fear_greed(period: str = Query("1d")):
    if period not in VALID_PERIODS:
        period = "1d"
    cache_key = f"fear_greed_{period}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        result = calculate_fear_greed(period=period)
        cache.set(cache_key, result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funding-stress")
def get_funding_stress():
    cached = cache.get("funding_stress")
    if cached:
        return cached
    try:
        result = calculate_funding_stress()
        cache.set("funding_stress", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cross-asset")
def get_cross_asset():
    cached = cache.get("cross_asset")
    if cached:
        return cached
    try:
        moves = get_cross_asset_moves()
        regime = get_regime_signal(moves)
        positioning = get_positioning()
        result = {
            "moves": moves,
            "regime": regime,
            "positioning": positioning,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        cache.set("cross_asset", result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
