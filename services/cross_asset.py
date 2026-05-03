import yfinance as yf
import pandas as pd

CROSS_ASSET_TICKERS = {
    "^GSPC":    "S&P 500",
    "^TNX":     "10Y Treasury",
    "GC=F":     "Gold",
    "CL=F":     "Oil",
    "DX-Y.NYB": "USD Index",
    "^VIX":     "VIX",
    "BTC-USD":  "Bitcoin",
    "EURUSD=X": "EUR/USD",
}

# COT-style positioning proxies via ETF flows (long/short ratio proxy)
POSITIONING_PROXIES = {
    "Equities":       {"long": "SPY",  "short": "SH"},
    "Bonds":          {"long": "TLT",  "short": "TBF"},
    "Gold":           {"long": "GLD",  "short": "DGZ"},
    "USD":            {"long": "UUP",  "short": "UDN"},
    "Volatility":     {"long": "UVXY", "short": "SVXY"},
}


def get_cross_asset_moves() -> list[dict]:
    symbols = list(CROSS_ASSET_TICKERS.keys())
    data = yf.download(symbols, period="5d", auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if "Close" in data else data

    results = []
    for symbol, name in CROSS_ASSET_TICKERS.items():
        try:
            series = closes[symbol].dropna()
            if len(series) < 2:
                continue
            curr    = float(series.iloc[-1])
            prev    = float(series.iloc[-2])
            week    = float(series.iloc[0])
            chg_1d  = (curr - prev) / prev * 100
            chg_5d  = (curr - week) / week * 100
            results.append({
                "symbol":    symbol,
                "name":      name,
                "price":     round(curr, 4),
                "change_1d": round(chg_1d, 2),
                "change_5d": round(chg_5d, 2),
            })
        except Exception:
            continue
    return results


def get_regime_signal(moves: list[dict]) -> dict:
    lookup = {m["symbol"]: m for m in moves}

    vix      = lookup.get("^VIX", {}).get("price", 20)
    spx_1d   = lookup.get("^GSPC", {}).get("change_1d", 0)
    gold_1d  = lookup.get("GC=F", {}).get("change_1d", 0)
    usd_1d   = lookup.get("DX-Y.NYB", {}).get("change_1d", 0)
    tsy_1d   = lookup.get("^TNX", {}).get("change_1d", 0)

    # Classify regime
    if vix > 30:
        regime = "Risk-Off / Stress"
        color  = "#F85149"
    elif vix > 20 and spx_1d < -1:
        regime = "Risk-Off / Caution"
        color  = "#D29922"
    elif vix < 15 and spx_1d > 0:
        regime = "Risk-On / Bullish"
        color  = "#3FB950"
    else:
        regime = "Neutral / Mixed"
        color  = "#58A6FF"

    # Unusual signals
    signals = []
    if gold_1d > 0.5 and usd_1d > 0.3:
        signals.append("Gold + USD both rising → flight to safety / stress signal")
    if spx_1d < -1 and tsy_1d < 0:
        signals.append("Equities and bonds selling off together → liquidity squeeze")
    if spx_1d > 1 and vix > 20:
        signals.append("Equities rallying but VIX still elevated → uncertain rally")
    if gold_1d > 1 and spx_1d > 1:
        signals.append("Gold + Equities both up → reflation / inflation hedge demand")

    return {
        "regime": regime,
        "color": color,
        "vix": vix,
        "signals": signals,
    }


def get_positioning() -> list[dict]:
    all_tickers = []
    for v in POSITIONING_PROXIES.values():
        all_tickers += [v["long"], v["short"]]

    data = yf.download(all_tickers, period="5d", auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if "Close" in data else data

    results = []
    for asset, proxies in POSITIONING_PROXIES.items():
        try:
            long_s  = closes[proxies["long"]].dropna()
            short_s = closes[proxies["short"]].dropna()

            long_chg  = (float(long_s.iloc[-1]) - float(long_s.iloc[0])) / float(long_s.iloc[0]) * 100
            short_chg = (float(short_s.iloc[-1]) - float(short_s.iloc[0])) / float(short_s.iloc[0]) * 100

            # Net bias: positive = market leaning long
            net_bias = long_chg - short_chg
            if net_bias > 1:
                bias = "Long"
                bias_color = "#3FB950"
            elif net_bias < -1:
                bias = "Short"
                bias_color = "#F85149"
            else:
                bias = "Neutral"
                bias_color = "#D29922"

            results.append({
                "asset":      asset,
                "bias":       bias,
                "bias_color": bias_color,
                "net_5d":     round(net_bias, 2),
                "long_etf":   proxies["long"],
                "short_etf":  proxies["short"],
            })
        except Exception:
            continue

    return results
