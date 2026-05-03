from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from routers import assets, report, risk, ai, watchlist, calendar
from cache import cache
from services.report_generator import generate_report
from services.risk_generator import generate_risk_report


def refresh_report():
    print(f"[scheduler] Refreshing morning report at {datetime.now().strftime('%H:%M')}...")
    try:
        data = generate_report()
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set("morning_report", data)
        print("[scheduler] Morning report refreshed.")
    except Exception as e:
        print(f"[scheduler] Morning report error: {e}")


def refresh_risk():
    print(f"[scheduler] Refreshing risk report at {datetime.now().strftime('%H:%M')}...")
    try:
        data = generate_risk_report()
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        cache.set("risk_report", data)
        print("[scheduler] Risk report refreshed.")
    except Exception as e:
        print(f"[scheduler] Risk report error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_report, "interval", hours=1)
    scheduler.add_job(refresh_risk, "interval", hours=1)
    scheduler.start()
    print("[scheduler] Auto-refresh every 1 hour.")
    yield
    scheduler.shutdown()


app = FastAPI(title="Assets News API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets.router, prefix="/assets", tags=["assets"])
app.include_router(report.router, prefix="/report", tags=["report"])
app.include_router(risk.router, prefix="/risk", tags=["risk"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])


@app.get("/health")
def health():
    return {"status": "ok"}
