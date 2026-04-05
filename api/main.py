from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache = {}
CACHE_TTL = 900  # 15 minutes
FMP_KEY = os.environ.get("FMP_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

def cached(key, fn):
    now = time.time()
    if key in _cache and _cache[key]["data"] is not None and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fn()
    if data is not None:
        _cache[key] = {"data": data, "ts": now}
    return data

def fetch_quote(symbol):
    """Fetch latest quote from FMP."""
    try:
        r = httpx.get(
            f"{FMP_BASE}/quote/{symbol}",
            params={"apikey": FMP_KEY},
            timeout=10
        )
        data = r.json()
        if not data or not isinstance(data, list) or not data[0].get("price"):
            print(f"FMP empty for {symbol}: {str(data)[:200]}")
            return None
        q = data[0]
        return {
            "symbol": symbol,
            "current": round(float(q["price"]), 2),
            "prev": round(float(q["previousClose"]), 2),
            "change_pct": round(float(q["changesPercentage"]), 2),
            "name": q.get("name", symbol),
        }
    except Exception as e:
        print(f"fetch_quote error {symbol}: {e}")
        return None

def fetch_history(symbol, days=10):
    """Fetch recent daily closes from FMP."""
    try:
        r = httpx.get(
            f"{FMP_BASE}/historical-price-full/{symbol}",
            params={"apikey": FMP_KEY, "timeseries": days},
            timeout=10
        )
        data = r.json()
        hist = data.get("historical", [])
        if not hist:
            return []
        return [round(float(h["close"]), 2) for h in reversed(hist)]
    except Exception as e:
        print(f"fetch_history error {symbol}: {e}")
        return []

def build_field(index_symbol, vol_symbol=None, vol_range=(10, 80)):
    idx = fetch_quote(index_symbol)
    if not idx:
        return None
    change_pct = idx["change_pct"]
    idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)
    series = fetch_history(index_symbol)

    vol_data = None
    vol_norm = 0.5
    if vol_symbol:
        vol = fetch_quote(vol_symbol)
        if vol:
            vraw = vol["current"]
            vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
            vol_series = fetch_history(vol_symbol)
            vol_data = {
                "raw": vraw,
                "normalised": vol_norm,
                "symbol": vol_symbol,
                "series": vol_series,
                "source": f"FMP — {vol_symbol}",
            }

    return {
        "index": {
            "symbol": index_symbol,
            "name": idx["name"],
            "current": idx["current"],
            "change_pct": change_pct,
            "normalised": idx_norm,
            "series": series,
        },
        "volatility": vol_data,
        "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
        "confidence": 0.85 if vol_data else 0.65,
        "source": "Financial Modelling Prep",
        "lag_days": 0,
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.6", "status": "live"}

@app.get("/api/market/us")
def get_us_market():
    return cached("us_market", lambda: build_field("%5EGSPC", vol_symbol="%5EVIX", vol_range=(10, 80)))

@app.get("/api/market/uk")
def get_uk_market():
    return cached("uk_market", lambda: build_field("%5EFTSE", vol_range=(10, 60)))

@app.get("/api/market/india")
def get_india_market():
    return cached("india_market", lambda: build_field("%5ENSEI", vol_range=(10, 60)))

@app.get("/api/market/all")
def get_all_markets():
    return {
        "us":    cached("us_market",    lambda: build_field("%5EGSPC", vol_symbol="%5EVIX", vol_range=(10, 80))),
        "uk":    cached("uk_market",    lambda: build_field("%5EFTSE",                       vol_range=(10, 60))),
        "india": cached("india_market", lambda: build_field("%5ENSEI",                       vol_range=(10, 60))),
    }

@app.get("/api/debug")
def debug():
    results = {}
    for sym in ["%5EGSPC", "%5EVIX", "%5EFTSE", "%5ENSEI"]:
        results[sym] = fetch_quote(sym)
    return {"key_set": bool(FMP_KEY), "results": results}
