from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models import AssetResponse
from cache import cache
from services.market_data import get_top_movers, get_weekly_movers
from services.news_fetcher import fetch_news
from services.ai_analyzer import analyze

router = APIRouter()

VALID_ASSET_TYPES = {"stocks", "crypto", "forex", "commodities"}


def build_response(asset_type: str) -> dict:
    movers = get_top_movers(asset_type)
    news = fetch_news(asset_type)
    signal = analyze(asset_type, movers, news)

    return {
        "asset_type": asset_type,
        "top_movers": movers,
        "news": news,
        "strategic_signal": signal,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{asset_type}/weekly")
def get_weekly_asset(asset_type: str):
    if asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown asset type. Valid types: {sorted(VALID_ASSET_TYPES)}",
        )

    cache_key = f"{asset_type}_weekly"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        movers = get_weekly_movers(asset_type)
        news = fetch_news(asset_type)
        signal = analyze(asset_type, movers, news, weekly=True)
        data = {
            "asset_type": asset_type,
            "top_movers": movers,
            "news": news,
            "strategic_signal": signal,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        cache.set(cache_key, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_type}", response_model=AssetResponse)
def get_asset(asset_type: str):
    if asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown asset type. Valid types: {sorted(VALID_ASSET_TYPES)}",
        )

    cached = cache.get(asset_type)
    if cached:
        return cached

    try:
        data = build_response(asset_type)
        cache.set(asset_type, data)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_asset_types():
    return {"asset_types": sorted(VALID_ASSET_TYPES)}
