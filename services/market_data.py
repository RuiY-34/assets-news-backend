import yfinance as yf

ASSET_TICKERS: dict[str, list[str]] = {
    "stocks": [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
        "META", "TSLA", "JPM", "V", "BRK-B",
    ],
    "sectors": [
        "XLK",   # Technology
        "XLF",   # Financials
        "XLE",   # Energy
        "XLV",   # Healthcare
        "XLI",   # Industrials
        "XLY",   # Consumer Discretionary
        "XLP",   # Consumer Staples
        "XLC",   # Communication Services
        "XLRE",  # Real Estate
        "XLB",   # Materials
        "XLU",   # Utilities
    ],
    "regions": [
        "^GSPC",   # S&P 500 (US)
        "^IXIC",   # NASDAQ (US)
        "^FTSE",   # FTSE 100 (UK)
        "^GDAXI",  # DAX (Germany)
        "^N225",   # Nikkei 225 (Japan)
        "^HSI",    # Hang Seng (Hong Kong)
        "^AXJO",   # ASX 200 (Australia)
        "^BSESN",  # Sensex (India)
    ],
    "crypto": [
        "BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD",
        "XRP-USD", "ADA-USD", "DOGE-USD", "AVAX-USD",
    ],
    "forex": [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X",
        "AUDUSD=X", "USDCAD=X", "USDCHF=X",
    ],
    "commodities": [
        "GC=F",   # Gold
        "SI=F",   # Silver
        "CL=F",   # Crude Oil
        "NG=F",   # Natural Gas
        "ZW=F",   # Wheat
        "ZC=F",   # Corn
    ],
    "fixed_income": [
        "^TNX",   # 10Y US Treasury Yield
        "^TYX",   # 30Y US Treasury Yield
        "^FVX",   # 5Y US Treasury Yield
        "^IRX",   # 3M US Treasury Yield
        "LQD",    # Investment Grade Corp Bonds ETF
        "HYG",    # High Yield Corp Bonds ETF
    ],
}

TICKER_NAMES: dict[str, str] = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA",
    "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta",
    "TSLA": "Tesla", "JPM": "JPMorgan", "V": "Visa", "BRK-B": "Berkshire",
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "BNB-USD": "BNB",
    "SOL-USD": "Solana", "XRP-USD": "XRP", "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin", "AVAX-USD": "Avalanche",
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF",
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "Crude Oil",
    "NG=F": "Natural Gas", "ZW=F": "Wheat", "ZC=F": "Corn",
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLI": "Industrials", "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples", "XLC": "Comms", "XLRE": "Real Estate",
    "XLB": "Materials", "XLU": "Utilities",
    "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^FTSE": "FTSE 100",
    "^GDAXI": "DAX", "^N225": "Nikkei 225", "^HSI": "Hang Seng",
    "^AXJO": "ASX 200", "^BSESN": "Sensex",
    "^TNX": "10Y Treasury", "^TYX": "30Y Treasury",
    "^FVX": "5Y Treasury", "^IRX": "3M Treasury",
    "LQD": "IG Corp Bonds", "HYG": "High Yield Bonds",
}


PERIOD_TO_YF = {
    "1d": "2d",
    "1w": "5d",
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y",
}


def get_period_movers(asset_type: str, period: str = "1d", limit: int = 5) -> list[dict]:
    tickers = ASSET_TICKERS.get(asset_type, [])
    if not tickers:
        return []

    yf_period = PERIOD_TO_YF.get(period, "2d")
    is_1d = period == "1d"

    data = yf.download(tickers, period=yf_period, auto_adjust=True, progress=False, threads=True)
    closes = data["Close"] if "Close" in data else data

    results = []
    for symbol in tickers:
        try:
            series = closes.dropna() if len(tickers) == 1 else closes[symbol].dropna()
            if len(series) < 2:
                continue

            start = float(series.iloc[-2]) if is_1d else float(series.iloc[0])
            end = float(series.iloc[-1])
            change_pct = (end - start) / start * 100

            results.append({
                "symbol": symbol,
                "name": TICKER_NAMES.get(symbol, symbol),
                "price": round(end, 4),
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return results[:limit]


def get_weekly_movers(asset_type: str, limit: int = 5) -> list[dict]:
    tickers = ASSET_TICKERS.get(asset_type, [])
    if not tickers:
        return []

    results = []

    data = yf.download(
        tickers,
        period="5d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    closes = data["Close"] if "Close" in data else data

    for symbol in tickers:
        try:
            if len(tickers) == 1:
                series = closes.dropna()
            else:
                series = closes[symbol].dropna()

            if len(series) < 2:
                continue

            week_start = float(series.iloc[0])
            week_end = float(series.iloc[-1])
            change_pct = (week_end - week_start) / week_start * 100

            results.append({
                "symbol": symbol,
                "name": TICKER_NAMES.get(symbol, symbol),
                "price": round(week_end, 4),
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return results[:limit]


def get_top_movers(asset_type: str, limit: int = 5) -> list[dict]:
    tickers = ASSET_TICKERS.get(asset_type, [])
    if not tickers:
        return []

    results = []

    # Download 2 days of data for all tickers at once
    data = yf.download(
        tickers,
        period="2d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    closes = data["Close"] if "Close" in data else data

    for symbol in tickers:
        try:
            if len(tickers) == 1:
                series = closes.dropna()
            else:
                series = closes[symbol].dropna()

            if len(series) < 2:
                continue

            prev = float(series.iloc[-2])
            curr = float(series.iloc[-1])
            change_pct = (curr - prev) / prev * 100

            results.append({
                "symbol": symbol,
                "name": TICKER_NAMES.get(symbol, symbol),
                "price": round(curr, 4),
                "change_pct": round(change_pct, 2),
            })
        except Exception:
            continue

    results.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return results[:limit]
