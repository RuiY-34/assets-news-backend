import yfinance as yf
import numpy as np
from datetime import date as date_type

SECTORS = [
    ("XLK", "Technology"),
    ("XLF", "Financials"),
    ("XLE", "Energy"),
    ("XLV", "Healthcare"),
    ("XLI", "Industrials"),
    ("XLY", "Consumer Disc."),
    ("XLP", "Consumer Staples"),
    ("XLC", "Comms"),
    ("XLRE", "Real Estate"),
    ("XLB", "Materials"),
    ("XLU", "Utilities"),
]


def get_sector_rotation() -> dict:
    symbols = [s for s, _ in SECTORS]
    name_map = {s: n for s, n in SECTORS}

    try:
        data = yf.download(symbols, period="1y", auto_adjust=True, progress=False, threads=True)
        cl = data["Close"]
    except Exception:
        return {"sectors": [], "generated_at": date_type.today().isoformat()}

    results = []
    for sym in symbols:
        try:
            series = cl[sym].dropna().values.astype(float)
            if len(series) < 10:
                continue

            def pct(a, b):
                return round((b - a) / a * 100, 2) if a != 0 else 0.0

            ret_1d = pct(series[-2], series[-1]) if len(series) >= 2 else 0
            ret_1w = pct(series[-5], series[-1]) if len(series) >= 5 else 0
            ret_1m = pct(series[-22], series[-1]) if len(series) >= 22 else 0
            ret_3m = pct(series[-63], series[-1]) if len(series) >= 63 else 0

            # Momentum: this week vs prior week — positive = accelerating
            prev_week = pct(series[-10], series[-5]) if len(series) >= 10 else 0
            momentum = round(ret_1w - prev_week, 2)

            results.append({
                "symbol": sym,
                "name": name_map[sym],
                "price": round(float(series[-1]), 2),
                "ret_1d": ret_1d,
                "ret_1w": ret_1w,
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "momentum": momentum,
                "trend": "↑" if momentum > 0.3 else "↓" if momentum < -0.3 else "→",
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["ret_1w"], reverse=True)

    return {
        "sectors": results,
        "top_performing": [r["name"] for r in results[:3]],
        "bottom_performing": [r["name"] for r in results[-3:]],
        "generated_at": date_type.today().isoformat(),
    }
