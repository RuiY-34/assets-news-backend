import yfinance as yf

RISK_TICKERS = {
    # Volatility
    "^VIX":    "VIX (US Vol)",
    "^VXN":    "VXN (NASDAQ Vol)",
    "^VVIX":   "VVIX (Vol of Vol)",
    # Credit (proxy via ETFs)
    "HYG":     "High Yield Bonds",
    "LQD":     "IG Corp Bonds",
    "JNK":     "HY Junk Bonds",
    # Safe havens
    "GC=F":    "Gold",
    "^TNX":    "10Y Treasury Yield",
    "^IRX":    "3M Treasury Yield",
    # Equity stress
    "^GSPC":   "S&P 500",
    "UVXY":    "VIX Short-Term Futures",
    # FX stress
    "DX-Y.NYB": "USD Index",
    "JPYUSD=X": "JPY/USD (safe haven)",
}


PERIOD_TO_YF = {
    "1d": "5d",
    "1w": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
}


def get_risk_indicators(period: str = "1d") -> dict:
    yf_period = PERIOD_TO_YF.get(period, "5d")
    symbols = list(RISK_TICKERS.keys())
    data = yf.download(symbols, period=yf_period, auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if "Close" in data else data

    results = {}
    for symbol, name in RISK_TICKERS.items():
        try:
            series = closes[symbol].dropna()
            if len(series) < 2:
                continue
            curr       = float(series.iloc[-1])
            prev_1d    = float(series.iloc[-2])
            period_start = float(series.iloc[0])
            change_1d  = (curr - prev_1d) / prev_1d * 100
            change_5d  = (curr - period_start) / period_start * 100
            results[symbol] = {
                "symbol": symbol,
                "name": name,
                "price": round(curr, 4),
                "change_1d": round(change_1d, 2),
                "change_5d": round(change_5d, 2),
            }
        except Exception:
            continue
    return results


def get_risk_news() -> list[dict]:
    queries = ["^VIX", "HYG", "^TNX"]
    seen = set()
    items = []
    for symbol in queries:
        try:
            news = yf.Ticker(symbol).news or []
            for n in news:
                content = n.get("content", {})
                title = content.get("title", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                items.append({
                    "title": title,
                    "source": content.get("provider", {}).get("displayName", "Yahoo Finance"),
                    "url": content.get("canonicalUrl", {}).get("url", ""),
                    "published": content.get("pubDate", ""),
                })
                if len(items) >= 8:
                    return items
        except Exception:
            continue
    return items
