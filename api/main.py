from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache = {}
CACHE_TTL = 900  # 15 minutes

def cached(key, fn):
    now = time.time()
    if key in _cache and _cache[key]["data"] is not None and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fn()
    if data is not None:
        _cache[key] = {"data": data, "ts": now}
    return data

def fetch_stooq(symbol):
    """
    Fetch daily OHLCV from Stooq — no API key required.
    Returns last 30 days, parses closing prices.
    Stooq symbols:
      ^SPX  = S&P 500
      ^VIX  = CBOE VIX
      ^FTM  = FTSE 100
      ^NIF  = Nifty 50
    """
    try:
        end = datetime.today()
        start = end - timedelta(days=45)
        url = (
            f"https://stooq.com/q/d/l/"
            f"?s={symbol.lower()}"
            f"&d1={start.strftime('%Y%m%d')}"
            f"&d2={end.strftime('%Y%m%d')}"
            f"&i=d"
        )
        r = httpx.get(url, timeout=10, follow_redirects=True)
        lines = r.text.strip().split("\n")
        if len(lines) < 2:
            print(f"Stooq no data for {symbol}: {r.text[:200]}")
            return None
        # parse CSV — Date,Open,High,Low,Close,Volume
        header = lines[0].split(",")
        rows = [l.split(",") for l in lines[1:] if l.strip()]
        if not rows:
            return None
        close_idx = header.index("Close") if "Close" in header else 4
        closes = []
        for row in rows:
            try:
                closes.append(float(row[close_idx]))
            except:
                pass
        if len(closes) < 2:
            return None
        current = round(closes[-1], 2)
        prev = round(closes[-2], 2)
        change_pct = round((current - prev) / prev * 100, 2)
        return {
            "symbol": symbol,
            "current": current,
            "prev": prev,
            "change_pct": change_pct,
            "series": [round(c, 2) for c in closes[-10:]],
        }
    except Exception as e:
        print(f"fetch_stooq error {symbol}: {e}")
        return None

def build_field(index_symbol, vol_symbol=None, vol_range=(10, 80)):
    idx = fetch_stooq(index_symbol)
    if not idx:
        return None
    change_pct = idx["change_pct"]
    idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)
    vol_data = None
    vol_norm = 0.5
    if vol_symbol:
        vol = fetch_stooq(vol_symbol)
        if vol:
            vraw = vol["current"]
            vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
            vol_data = {
                "raw": vraw,
                "normalised": vol_norm,
                "symbol": vol_symbol,
                "series": vol["series"],
                "source": f"Stooq — {vol_symbol}",
            }
    return {
        "index": {
            "symbol": index_symbol,
            "current": idx["current"],
            "change_pct": change_pct,
            "normalised": idx_norm,
            "series": idx["series"],
        },
        "volatility": vol_data,
        "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
        "confidence": 0.85 if vol_data else 0.65,
        "source": "Stooq",
        "lag_days": 0,
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.5", "status": "live"}

@app.get("/api/market/us")
def get_us_market():
    return cached("us_market", lambda: build_field("^SPX", vol_symbol="^VIX", vol_range=(10, 80)))

@app.get("/api/market/uk")
def get_uk_market():
    return cached("uk_market", lambda: build_field("^FTM", vol_range=(10, 60)))

@app.get("/api/market/india")
def get_india_market():
    return cached("india_market", lambda: build_field("^NIF", vol_range=(10, 60)))

@app.get("/api/market/all")
def get_all_markets():
    return {
        "us":    cached("us_market",    lambda: build_field("^SPX", vol_symbol="^VIX", vol_range=(10, 80))),
        "uk":    cached("uk_market",    lambda: build_field("^FTM",                    vol_range=(10, 60))),
        "india": cached("india_market", lambda: build_field("^NIF",                    vol_range=(10, 60))),
    }

@app.get("/api/debug")
def debug():
    results = {}
    for sym in ["^SPX", "^VIX", "^FTM", "^NIF"]:
        results[sym] = fetch_stooq(sym)
    return results
