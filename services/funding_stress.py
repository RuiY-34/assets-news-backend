import yfinance as yf
from datetime import date as date_type

PERIOD_TO_YF = {
    "1d": "5d",
    "1w": "5d",
    "1m": "3mo",
    "3m": "6mo",
    "6m": "1y",
    "1y": "1y",
}

PERIOD_LOOKBACK = {
    "1d": 2,
    "1w": 5,
    "1m": 22,
    "3m": 63,
    "6m": 126,
    "1y": 252,
}

PERIOD_LABEL = {
    "1d": "1d", "1w": "5d", "1m": "1m", "3m": "3m", "6m": "6m", "1y": "1y",
}


def calculate_funding_stress(period: str = "1d") -> dict:
    yf_period = PERIOD_TO_YF.get(period, "5d")
    lookback  = PERIOD_LOOKBACK.get(period, 2)
    lb_label  = PERIOD_LABEL.get(period, "1d")
    indicators = []

    try:
        symbols = ["^IRX", "^FVX", "^TNX", "HYG", "LQD", "DX-Y.NYB"]
        data = yf.download(symbols, period=yf_period, auto_adjust=True, progress=False, threads=True)
        cl = data["Close"]

        # 1. 3M T-bill yield — change over period
        try:
            irx = cl["^IRX"].dropna().values.astype(float)
            lb = min(lookback, len(irx) - 1)
            if lb >= 1:
                current = irx[-1]
                change = round(current - irx[-lb - 1], 3)
                # Thresholds scale with period length
                t1 = 0.3 * (lb / 5)
                t2 = 0.1 * (lb / 5)
                signal = "stress" if change > t1 else "elevated" if change > t2 else "normal"
                indicators.append({
                    "name": "3M T-Bill Yield",
                    "value": round(current, 2),
                    "change": change,
                    "unit": "%",
                    "signal": signal,
                    "note": f"Change over {lb_label}: rising = funding pressure",
                })
        except Exception:
            pass

        # 2. Yield curve: 3M vs 10Y (inverted = stress) — current snapshot
        try:
            irx = cl["^IRX"].dropna().values.astype(float)
            tnx = cl["^TNX"].dropna().values.astype(float)
            if len(irx) >= 1 and len(tnx) >= 1:
                spread_now = round(float(tnx[-1]) - float(irx[-1]), 2)
                lb = min(lookback, len(irx) - 1, len(tnx) - 1)
                spread_then = round(float(tnx[-lb - 1]) - float(irx[-lb - 1]), 2) if lb >= 1 else spread_now
                change = round(spread_now - spread_then, 2)
                signal = "stress" if spread_now < -0.5 else "elevated" if spread_now < 0 else "normal"
                indicators.append({
                    "name": "Yield Curve (3M–10Y)",
                    "value": spread_now,
                    "change": change,
                    "unit": "%",
                    "signal": signal,
                    "note": f"Negative = inverted | {lb_label} change: {change:+.2f}%",
                })
        except Exception:
            pass

        # 3. HY credit spread proxy — LQD vs HYG relative return over period
        try:
            hyg = cl["HYG"].dropna().values.astype(float)
            lqd = cl["LQD"].dropna().values.astype(float)
            lb = min(lookback, len(hyg) - 1, len(lqd) - 1)
            if lb >= 1:
                hyg_ret = (hyg[-1] - hyg[-lb - 1]) / hyg[-lb - 1] * 100
                lqd_ret = (lqd[-1] - lqd[-lb - 1]) / lqd[-lb - 1] * 100
                spread = round(lqd_ret - hyg_ret, 2)
                t1 = 2 * (lb / 22)
                t2 = 0.5 * (lb / 22)
                signal = "stress" if spread > t1 else "elevated" if spread > t2 else "normal"
                indicators.append({
                    "name": "HY Credit Spread Proxy",
                    "value": spread,
                    "change": None,
                    "unit": "%",
                    "signal": signal,
                    "note": f"IG vs HY over {lb_label}: positive = HY underperforming",
                })
        except Exception:
            pass

        # 4. USD strength — over period
        try:
            dxy = cl["DX-Y.NYB"].dropna().values.astype(float)
            lb = min(lookback, len(dxy) - 1)
            if lb >= 1:
                current = round(float(dxy[-1]), 2)
                change_pct = round((dxy[-1] - dxy[-lb - 1]) / dxy[-lb - 1] * 100, 2)
                t1 = 3 * (lb / 22)
                t2 = 1 * (lb / 22)
                signal = "stress" if change_pct > t1 else "elevated" if change_pct > t2 else "normal"
                indicators.append({
                    "name": "USD Index (DXY)",
                    "value": current,
                    "change": change_pct,
                    "unit": "",
                    "signal": signal,
                    "note": f"USD {change_pct:+.1f}% over {lb_label}: sharp rise = liquidity squeeze",
                })
        except Exception:
            pass

    except Exception:
        pass

    n_stress   = sum(1 for i in indicators if i["signal"] == "stress")
    n_elevated = sum(1 for i in indicators if i["signal"] == "elevated")

    if n_stress >= 2:
        overall, color = "High Stress", "#F85149"
    elif n_stress == 1 or n_elevated >= 2:
        overall, color = "Elevated", "#F0883E"
    else:
        overall, color = "Normal", "#3FB950"

    return {
        "overall": overall,
        "color": color,
        "indicators": indicators,
        "period": period,
        "generated_at": date_type.today().isoformat(),
    }
