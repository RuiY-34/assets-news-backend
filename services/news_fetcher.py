import yfinance as yf

# Representative tickers per category for news fetching
NEWS_TICKERS: dict[str, list[str]] = {
    "stocks":         ["^GSPC", "^IXIC", "SPY"],
    "crypto":         ["BTC-USD", "ETH-USD"],
    "forex":          ["EURUSD=X", "DX-Y.NYB"],
    "commodities":    ["GC=F", "CL=F"],
    "fixed_income":   ["^TNX", "LQD"],
    "central_banks":  ["^IRX", "^TNX"],
    "equities_news":  ["^GSPC", "SPY", "QQQ"],
    "boe":            ["GBPUSD=X"],
    "regions":        ["^FTSE", "^N225", "^HSI"],
}


def fetch_news(category: str, limit: int = 6) -> list[dict]:
    tickers = NEWS_TICKERS.get(category, ["^GSPC"])
    seen = set()
    items = []

    for symbol in tickers:
        if len(items) >= limit:
            break
        try:
            news = yf.Ticker(symbol).news or []
            for n in news:
                content = n.get("content", {})
                title = content.get("title", "")
                url   = content.get("canonicalUrl", {}).get("url", "") or content.get("clickThroughUrl", {}).get("url", "")
                pub   = content.get("pubDate", "")
                source = content.get("provider", {}).get("displayName", "Yahoo Finance")

                if not title or title in seen:
                    continue
                seen.add(title)
                items.append({
                    "title":     title,
                    "source":    source,
                    "url":       url,
                    "published": pub,
                })
                if len(items) >= limit:
                    break
        except Exception as e:
            print(f"[news_fetcher] {symbol}: {e}")

    return items
