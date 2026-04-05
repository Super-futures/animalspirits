from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yfinance as yf
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# simple in-memory cache — avoids hammering yfinance
_cache = {}
CACHE_TTL = 900  # 15 minutes

def cached(key, fn):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fn()
    _cache[key] = {"data": data, "ts": now}
    return data

def fetch_vix():
    ticker = yf.Ticker("^VIX")
    hist = ticker.history(period="5d")
    if hist.empty:
        return None
    closes = hist["Close"].tolist()
    current = round(closes[-1], 2)
    prev = round(closes[-2], 2)
    change_pct = round((current - prev) / prev * 100, 2)
    # normalise VIX to 0-1 scale
    # VIX typically ranges 10-80; we clamp and normalise
    normalised = round(min(max((current - 10) / 70, 0), 1), 3)
    return {
        "raw": current,
        "prev": prev,
        "change_pct": change_pct,
        "normalised": normalised,
        "series": [round(v, 2) for v in closes],
        "source": "Yahoo Finance — ^VIX",
        "label": "CBOE Volatility Index",
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.1", "status": "live"}

@app.get("/api/vix")
def get_vix():
    data = cached("vix", fetch_vix)
    if not data:
        return JSONResponse({"error": "VIX data unavailable"}, status_code=503)
    return data

def fetch_index(ticker_symbol, vol_symbol=None, vol_range=(10, 80)):
    """Generic index fetcher — returns normalised field_value and metadata."""
    idx = yf.Ticker(ticker_symbol).history(period="5d")
    if idx.empty:
        return None
    closes = idx["Close"].tolist()
    current = round(closes[-1], 2)
    change_pct = round((closes[-1] - closes[-2]) / closes[-2] * 100, 2) if len(closes) >= 2 else 0
    idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)

    vol_data = None
    vol_norm = 0.5
    if vol_symbol:
        vol = yf.Ticker(vol_symbol).history(period="5d")
        if not vol.empty:
            vc = vol["Close"].tolist()
            vraw = round(vc[-1], 2)
            vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
            vol_data = {
                "raw": vraw,
                "normalised": vol_norm,
                "series": [round(v, 2) for v in vc],
                "source": f"Yahoo Finance — {vol_symbol}",
            }

    return {
        "index": {
            "ticker": ticker_symbol,
            "current": current,
            "change_pct": change_pct,
            "normalised": idx_norm,
            "series": [round(v, 2) for v in closes],
        },
        "volatility": vol_data,
        "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
        "confidence": 0.85,
        "source": "Yahoo Finance",
        "lag_days": 0,
    }

@app.get("/api/market/us")
def get_us_market():
    def fetch():
        return fetch_index("^GSPC", vol_symbol="^VIX", vol_range=(10, 80))
    return cached("us_market", fetch)

@app.get("/api/market/uk")
def get_uk_market():
    def fetch():
        return fetch_index("^FTSE", vol_symbol="^VFTSE", vol_range=(10, 60))
    return cached("uk_market", fetch)

@app.get("/api/market/india")
def get_india_market():
    def fetch():
        return fetch_index("^NSEI", vol_symbol="^INDIAVIX", vol_range=(10, 60))
    return cached("india_market", fetch)

@app.get("/api/market/all")
def get_all_markets():
    return {
        "us":    cached("us_market",    lambda: fetch_index("^GSPC", vol_symbol="^VIX",      vol_range=(10, 80))),
        "uk":    cached("uk_market",    lambda: fetch_index("^FTSE", vol_symbol="^VFTSE",    vol_range=(10, 60))),
        "india": cached("india_market", lambda: fetch_index("^NSEI", vol_symbol="^INDIAVIX", vol_range=(10, 60))),
    }
