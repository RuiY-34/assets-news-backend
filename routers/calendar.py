from fastapi import APIRouter, Query
from services.macro_calendar import get_upcoming_events, get_central_banks
from services.opinions import get_opinions

router = APIRouter()


@router.get("")
def get_calendar():
    return {
        "events": get_upcoming_events(days=30),
        "central_banks": get_central_banks(),
    }


@router.get("/opinions")
def opinions(
    asset_class: str | None = Query(default=None),
    institution: str | None = Query(default=None),
):
    return get_opinions(asset_class=asset_class, institution=institution)
