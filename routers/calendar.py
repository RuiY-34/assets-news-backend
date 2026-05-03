from fastapi import APIRouter
from services.macro_calendar import get_upcoming_events, get_central_banks

router = APIRouter()


@router.get("")
def get_calendar():
    return {
        "events": get_upcoming_events(days=30),
        "central_banks": get_central_banks(),
    }
