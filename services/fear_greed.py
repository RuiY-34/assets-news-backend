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


def calculate_fear_greed() -> dict:
    scores: dict[str, float] = {}
    components: dict[str, dict] = {}

    # Batch 1: main indices
    try:
        batch = yf.download(
            ["^GSPC", "^VIX", "SPY", "HYG", "LQD", "GC=F"],
            period="1y", auto_adjust=True, progress=False, threads=True,
        )
        cl = batch["Close"]

        # 1. Market Momentum — S&P 500 vs 125-day MA
        try:
            gspc = cl["^GSPC"].dropna().values.astype(float)
            if len(gspc) >= 126:
                pct = (gspc[-1] - np.mean(gspc[-125:])) / np.mean(gspc[-125:]) * 100
                s = _clamp(50 + pct * 10)
                scores["momentum"] = s
                components["momentum"] = {"score": round(s, 1), "label": "Market Momentum",
                                           "note": f"S&P {pct:+.1f}% vs 125d MA"}
            else:
                scores["momentum"] = 50
                components["momentum"] = {"score": 50, "label": "Market Momentum", "note": "N/A"}
        except Exception:
            scores["momentum"] = 50
            components["momentum"] = {"score": 50, "label": "Market Momentum", "note": "N/A"}

        # 2. Volatility — VIX vs 50-day MA (high VIX = fear)
        try:
            vix = cl["^VIX"].dropna().values.astype(float)
            if len(vix) >= 50:
                current_vix = vix[-1]
                ma50 = np.mean(vix[-50:])
                pct = (current_vix - ma50) / ma50 * 100
                s = _clamp(50 - pct * 1.5)
                scores["volatility"] = s
                components["volatility"] = {"score": round(s, 1), "label": "Volatility (VIX)",
                                             "note": f"VIX {current_vix:.1f} vs {ma50:.1f} avg"}
            else:
                scores["volatility"] = 50
                components["volatility"] = {"score": 50, "label": "Volatility (VIX)", "note": "N/A"}
        except Exception:
            scores["volatility"] = 50
            components["volatility"] = {"score": 50, "label": "Volatility (VIX)", "note": "N/A"}

        # 3. Junk Bond Demand — HYG vs LQD 5-day relative return
        try:
            hyg = cl["HYG"].dropna().values.astype(float)
            lqd = cl["LQD"].dropna().values.astype(float)
            if len(hyg) >= 5 and len(lqd) >= 5:
                spread = ((hyg[-1] - hyg[-5]) / hyg[-5] - (lqd[-1] - lqd[-5]) / lqd[-5]) * 100
                s = _clamp(50 + spread * 25)
                scores["junk_bonds"] = s
                components["junk_bonds"] = {"score": round(s, 1), "label": "Junk Bond Demand",
                                             "note": f"HY vs IG 5d spread: {spread:+.2f}%"}
            else:
                scores["junk_bonds"] = 50
                components["junk_bonds"] = {"score": 50, "label": "Junk Bond Demand", "note": "N/A"}
        except Exception:
            scores["junk_bonds"] = 50
            components["junk_bonds"] = {"score": 50, "label": "Junk Bond Demand", "note": "N/A"}

        # 4. Safe Haven Demand — Stocks vs Gold 5-day (stocks up = greed)
        try:
            spy = cl["SPY"].dropna().values.astype(float)
            gold = cl["GC=F"].dropna().values.astype(float)
            if len(spy) >= 5 and len(gold) >= 5:
                spread = ((spy[-1] - spy[-5]) / spy[-5] - (gold[-1] - gold[-5]) / gold[-5]) * 100
                s = _clamp(50 + spread * 5)
                scores["safe_haven"] = s
                spy_ret = (spy[-1] - spy[-5]) / spy[-5] * 100
                gold_ret = (gold[-1] - gold[-5]) / gold[-5] * 100
                components["safe_haven"] = {"score": round(s, 1), "label": "Safe Haven Demand",
                                             "note": f"Stocks {spy_ret:+.1f}% vs Gold {gold_ret:+.1f}%"}
            else:
                scores["safe_haven"] = 50
                components["safe_haven"] = {"score": 50, "label": "Safe Haven Demand", "note": "N/A"}
        except Exception:
            scores["safe_haven"] = 50
            components["safe_haven"] = {"score": 50, "label": "Safe Haven Demand", "note": "N/A"}

    except Exception:
        for k, lbl in [("momentum", "Market Momentum"), ("volatility", "Volatility (VIX)"),
                        ("junk_bonds", "Junk Bond Demand"), ("safe_haven", "Safe Haven Demand")]:
            scores[k] = 50
            components[k] = {"score": 50, "label": lbl, "note": "N/A"}

    # 5. Market Breadth — % of sector ETFs positive this week
    try:
        sectors = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLC", "XLRE", "XLB", "XLU"]
        sec_data = yf.download(sectors, period="5d", auto_adjust=True, progress=False, threads=True)["Close"]
        pos, total = 0, 0
        for sym in sectors:
            try:
                s = sec_data[sym].dropna().values.astype(float)
                if len(s) >= 2:
                    total += 1
                    if s[-1] > s[0]:
                        pos += 1
            except Exception:
                continue
        breadth_pct = (pos / total * 100) if total > 0 else 50
        s = _clamp(breadth_pct)
        scores["breadth"] = s
        components["breadth"] = {"score": round(s, 1), "label": "Market Breadth",
                                  "note": f"{pos}/{total} sectors positive this week"}
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
        "generated_at": date_type.today().isoformat(),
    }
