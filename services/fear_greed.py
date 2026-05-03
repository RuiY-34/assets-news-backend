import numpy as np
import yfinance as yf
from datetime import date as date_type


def _clamp(val: float) -> float:
    return max(0.0, min(100.0, float(val)))


def _label(score: float) -> tuple[str, str]:
    if score <= 25:
        return "Extreme Fear", "#F85149"
    if score <= 45:
        return "Fear", "#F0883E"
    if score <= 55:
        return "Neutral", "#D29922"
    if score <= 75:
        return "Greed", "#3FB950"
    return "Extreme Greed", "#58A6FF"


# How many trading days to look back for each period
PERIOD_LOOKBACK = {
    "1d": 2,
    "1w": 5,
    "1m": 21,
    "3m": 63,
    "6m": 126,
    "1y": 252,
}

PERIOD_YF = {
    "1d": "5d",
    "1w": "5d",
    "1m": "3mo",
    "3m": "6mo",
    "6m": "1y",
    "1y": "1y",
}

PERIOD_LABEL = {
    "1d": "1d", "1w": "5d", "1m": "1m", "3m": "3m", "6m": "6m", "1y": "1y",
}

# Scaling factors — larger lookback = smaller per-% effect
MOMENTUM_SCALE = {"1d": 10, "1w": 5,  "1m": 2,   "3m": 1,   "6m": 0.7, "1y": 0.5}
JUNK_SCALE     = {"1d": 25, "1w": 15, "1m": 8,   "3m": 4,   "6m": 2.5, "1y": 2}
HAVEN_SCALE    = {"1d": 5,  "1w": 3,  "1m": 1.5, "3m": 0.8, "6m": 0.5, "1y": 0.3}


def calculate_fear_greed(period: str = "1d") -> dict:
    lookback   = PERIOD_LOOKBACK.get(period, 2)
    yf_period  = PERIOD_YF.get(period, "5d")
    lb_label   = PERIOD_LABEL.get(period, "1d")
    m_scale    = MOMENTUM_SCALE.get(period, 5)
    j_scale    = JUNK_SCALE.get(period, 15)
    h_scale    = HAVEN_SCALE.get(period, 3)

    scores: dict[str, float] = {}
    components: dict[str, dict] = {}

    try:
        batch = yf.download(
            ["^GSPC", "^VIX", "SPY", "HYG", "LQD", "GC=F"],
            period=yf_period, auto_adjust=True, progress=False, threads=True,
        )
        cl = batch["Close"]

        # 1. Market Momentum — current vs lookback days ago
        try:
            gspc = cl["^GSPC"].dropna().values.astype(float)
            lb = min(lookback, len(gspc) - 1)
            if lb >= 1:
                pct = (gspc[-1] - gspc[-lb - 1]) / gspc[-lb - 1] * 100
                s = _clamp(50 + pct * m_scale)
                scores["momentum"] = s
                components["momentum"] = {
                    "score": round(s, 1), "label": "Market Momentum",
                    "note": f"S&P {pct:+.1f}% over {lb_label}",
                }
            else:
                raise ValueError("not enough data")
        except Exception:
            scores["momentum"] = 50
            components["momentum"] = {"score": 50, "label": "Market Momentum", "note": "N/A"}

        # 2. Volatility — current VIX vs avg VIX over the period
        try:
            vix = cl["^VIX"].dropna().values.astype(float)
            lb = min(lookback, len(vix))
            if lb >= 2:
                current_vix = vix[-1]
                avg_vix = float(np.mean(vix[-lb:]))
                pct = (current_vix - avg_vix) / avg_vix * 100
                s = _clamp(50 - pct * 1.5)
                scores["volatility"] = s
                components["volatility"] = {
                    "score": round(s, 1), "label": "Volatility (VIX)",
                    "note": f"VIX {current_vix:.1f} vs {avg_vix:.1f} avg ({lb_label})",
                }
            else:
                raise ValueError("not enough data")
        except Exception:
            scores["volatility"] = 50
            components["volatility"] = {"score": 50, "label": "Volatility (VIX)", "note": "N/A"}

        # 3. Junk Bond Demand — HYG vs LQD relative return over period
        try:
            hyg = cl["HYG"].dropna().values.astype(float)
            lqd = cl["LQD"].dropna().values.astype(float)
            lb = min(lookback, len(hyg) - 1, len(lqd) - 1)
            if lb >= 1:
                hyg_ret = (hyg[-1] - hyg[-lb - 1]) / hyg[-lb - 1] * 100
                lqd_ret = (lqd[-1] - lqd[-lb - 1]) / lqd[-lb - 1] * 100
                spread = hyg_ret - lqd_ret
                s = _clamp(50 + spread * j_scale)
                scores["junk_bonds"] = s
                components["junk_bonds"] = {
                    "score": round(s, 1), "label": "Junk Bond Demand",
                    "note": f"HY {hyg_ret:+.1f}% vs IG {lqd_ret:+.1f}% ({lb_label})",
                }
            else:
                raise ValueError("not enough data")
        except Exception:
            scores["junk_bonds"] = 50
            components["junk_bonds"] = {"score": 50, "label": "Junk Bond Demand", "note": "N/A"}

        # 4. Safe Haven Demand — Stocks vs Gold over period
        try:
            spy  = cl["SPY"].dropna().values.astype(float)
            gold = cl["GC=F"].dropna().values.astype(float)
            lb = min(lookback, len(spy) - 1, len(gold) - 1)
            if lb >= 1:
                spy_ret  = (spy[-1]  - spy[-lb - 1])  / spy[-lb - 1]  * 100
                gold_ret = (gold[-1] - gold[-lb - 1]) / gold[-lb - 1] * 100
                spread = spy_ret - gold_ret
                s = _clamp(50 + spread * h_scale)
                scores["safe_haven"] = s
                components["safe_haven"] = {
                    "score": round(s, 1), "label": "Safe Haven Demand",
                    "note": f"Stocks {spy_ret:+.1f}% vs Gold {gold_ret:+.1f}% ({lb_label})",
                }
            else:
                raise ValueError("not enough data")
        except Exception:
            scores["safe_haven"] = 50
            components["safe_haven"] = {"score": 50, "label": "Safe Haven Demand", "note": "N/A"}

    except Exception:
        for k, lbl in [("momentum", "Market Momentum"), ("volatility", "Volatility (VIX)"),
                        ("junk_bonds", "Junk Bond Demand"), ("safe_haven", "Safe Haven Demand")]:
            scores[k] = 50
            components[k] = {"score": 50, "label": lbl, "note": "N/A"}

    # 5. Market Breadth — % of sector ETFs positive over the period
    try:
        sectors = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLC", "XLRE", "XLB", "XLU"]
        sec_data = yf.download(sectors, period=yf_period, auto_adjust=True, progress=False, threads=True)["Close"]
        pos, total = 0, 0
        for sym in sectors:
            try:
                s = sec_data[sym].dropna().values.astype(float)
                lb = min(lookback, len(s) - 1)
                if lb >= 1:
                    total += 1
                    if s[-1] > s[-lb - 1]:
                        pos += 1
            except Exception:
                continue
        breadth_pct = (pos / total * 100) if total > 0 else 50
        s = _clamp(breadth_pct)
        scores["breadth"] = s
        components["breadth"] = {
            "score": round(s, 1), "label": "Market Breadth",
            "note": f"{pos}/{total} sectors positive over {lb_label}",
        }
    except Exception:
        scores["breadth"] = 50
        components["breadth"] = {"score": 50, "label": "Market Breadth", "note": "N/A"}

    composite = float(np.mean(list(scores.values())))
    label, color = _label(composite)

    return {
        "score": round(composite, 1),
        "label": label,
        "color": color,
        "components": components,
        "period": period,
        "generated_at": date_type.today().isoformat(),
    }
