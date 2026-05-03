import yfinance as yf
from datetime import date as date_type


def calculate_funding_stress() -> dict:
    indicators = []

    try:
        symbols = ["^IRX", "^FVX", "^TNX", "HYG", "LQD", "DX-Y.NYB"]
        data = yf.download(symbols, period="3mo", auto_adjust=True, progress=False, threads=True)
        cl = data["Close"]

        # 1. 3M T-bill yield level and weekly change
        try:
            irx = cl["^IRX"].dropna().values.astype(float)
            if len(irx) >= 5:
                current = irx[-1]
                change = current - irx[-5]
                signal = "stress" if change > 0.3 else "elevated" if change > 0.1 else "normal"
                indicators.append({
                    "name": "3M T-Bill Yield",
                    "value": round(current, 2),
                    "change": round(change, 3),
                    "unit": "%",
                    "signal": signal,
                    "note": "Rising = short-term funding pressure",
                })
        except Exception:
            pass

        # 2. Yield curve: 3M vs 10Y (inverted = stress)
        try:
            irx = cl["^IRX"].dropna().values.astype(float)
            tnx = cl["^TNX"].dropna().values.astype(float)
            if len(irx) >= 1 and len(tnx) >= 1:
                spread = round(float(tnx[-1]) - float(irx[-1]), 2)
                signal = "stress" if spread < -0.5 else "elevated" if spread < 0 else "normal"
                indicators.append({
                    "name": "Yield Curve (3M–10Y)",
                    "value": spread,
                    "change": None,
                    "unit": "%",
                    "signal": signal,
                    "note": "Negative = inverted (recession signal)",
                })
        except Exception:
            pass

        # 3. HY credit spread proxy — LQD vs HYG 1-month relative (LQD outperform = HY stress)
        try:
            hyg = cl["HYG"].dropna().values.astype(float)
            lqd = cl["LQD"].dropna().values.astype(float)
            if len(hyg) >= 22 and len(lqd) >= 22:
                hyg_ret = (hyg[-1] - hyg[-22]) / hyg[-22] * 100
                lqd_ret = (lqd[-1] - lqd[-22]) / lqd[-22] * 100
                spread = round(lqd_ret - hyg_ret, 2)  # positive = HY underperforming = stress
                signal = "stress" if spread > 2 else "elevated" if spread > 0.5 else "normal"
                indicators.append({
                    "name": "HY Credit Spread Proxy",
                    "value": spread,
                    "change": None,
                    "unit": "%",
                    "signal": signal,
                    "note": "IG outperforms HY when credit stress rises",
                })
        except Exception:
            pass

        # 4. USD strength — rapid USD rise = EM/global funding squeeze
        try:
            dxy = cl["DX-Y.NYB"].dropna().values.astype(float)
            if len(dxy) >= 22:
                current = round(float(dxy[-1]), 2)
                change_1m = round((dxy[-1] - dxy[-22]) / dxy[-22] * 100, 2)
                signal = "stress" if change_1m > 3 else "elevated" if change_1m > 1 else "normal"
                indicators.append({
                    "name": "USD Index (DXY)",
                    "value": current,
                    "change": change_1m,
                    "unit": "",
                    "signal": signal,
                    "note": "Sharp USD rise = global liquidity squeeze",
                })
        except Exception:
            pass

    except Exception:
        pass

    n_stress = sum(1 for i in indicators if i["signal"] == "stress")
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
        "generated_at": date_type.today().isoformat(),
    }
