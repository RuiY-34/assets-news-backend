from pydantic import BaseModel
from typing import Optional


class Mover(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published: str


class StrategicSignal(BaseModel):
    signal: str        # "bullish" | "bearish" | "neutral"
    summary: str
    key_points: list[str]
    risk_level: str    # "low" | "medium" | "high"


class AssetResponse(BaseModel):
    asset_type: str
    top_movers: list[Mover]
    news: list[NewsItem]
    strategic_signal: StrategicSignal
    cached_at: str
