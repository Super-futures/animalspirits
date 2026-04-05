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
AV_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
AV_BASE = "https://www.alphavantage.co/query"

def cached(key, fn):
    now = time.time()
    if key in _cache and _cache[key]["data"] is not None and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fn()
    if data is not None:
        _cache[key] = {"data": data, "ts": now}
    return data

def fetch_quote(symbol):
    """Fetch latest quote from Alpha Vantage — GLOBAL_QUOTE endpoint."""
    try:
        r = httpx.get(AV_BASE, params={
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": AV_KEY,
        }, timeout=10)
        data = r.json()
        q = data.get("Global Quote", {})
        if not q or not q.get("05. price"):
            return None
        price = float(q["05. price"])
        change_pct = float(q["10. change percent"].replace("%", ""))
        prev = float(q["08. previous close"])
        return {
            "symbol": symbol,
            "current": round(price, 2),
            "prev": round(prev, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception as e:
        print(f"fetch_quote error {symbol}: {e}")
        return None

def build_field(index_symbol, vol_symbol=None, vol_range=(10, 80)):
    """Build a market field value from index + optional volatility."""
    idx = fetch_quote(index_symbol)
    if not idx:
        return None

    change_pct = idx["change_pct"]
    idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)

    vol_data = None
    vol_norm = 0.5
    if vol_symbol:
        vol = fetch_quote(vol_symbol)
        if vol:
            vraw = vol["current"]
            vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
            vol_data = {
                "raw": vraw,
                "normalised": vol_norm,
                "symbol": vol_symbol,
                "source": f"Alpha Vantage — {vol_symbol}",
            }

    return {
        "index": {
            "symbol": index_symbol,
            "current": idx["current"],
            "change_pct": change_pct,
            "normalised": idx_norm,
        },
        "volatility": vol_data,
        "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
        "confidence": 0.85 if vol_data else 0.65,
        "source": "Alpha Vantage",
        "lag_days": 0,
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.3", "status": "live"}

@app.get("/api/market/us")
def get_us_market():
    return cached("us_market", lambda: build_field("SPY", vol_symbol="VIXY", vol_range=(10, 80)))

@app.get("/api/market/uk")
def get_uk_market():
    return cached("uk_market", lambda: build_field("ISF.L", vol_range=(10, 60)))

@app.get("/api/market/india")
def get_india_market():
    return cached("india_market", lambda: build_field("NIFTYBEES.BSE", vol_range=(10, 60)))

@app.get("/api/market/all")
def get_all_markets():
    return {
        "us":    cached("us_market",    lambda: build_field("SPY",           vol_symbol="VIXY", vol_range=(10, 80))),
        "uk":    cached("uk_market",    lambda: build_field("ISF.L",                            vol_range=(10, 60))),
        "india": cached("india_market", lambda: build_field("NIFTYBEES.BSE",                    vol_range=(10, 60))),
    }

@app.get("/api/debug")
def debug():
    """Test Alpha Vantage connectivity."""
    result = fetch_quote("SPY")
    return {"spy": result, "key_set": bool(AV_KEY)}
