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

@app.get("/api/market/us")
def get_us_market():
    def fetch():
        vix = fetch_vix()
        sp = yf.Ticker("^GSPC").history(period="5d")
        sp_close = sp["Close"].tolist() if not sp.empty else []
        sp_current = round(sp_close[-1], 2) if sp_close else None
        sp_change = round((sp_close[-1]-sp_close[-2])/sp_close[-2]*100, 2) if len(sp_close)>=2 else 0
        # market field value: blend of VIX (inverted for anxiety) and SP momentum
        # high VIX + falling SP = high anxiety market signal
        vix_norm = vix["normalised"] if vix else 0.5
        sp_norm = round(min(max((sp_change + 3) / 6, 0), 1), 3)  # -3% to +3% mapped 0-1
        return {
            "vix": vix,
            "sp500": {
                "current": sp_current,
                "change_pct": sp_change,
                "normalised": sp_norm,
                "series": [round(v, 2) for v in sp_close],
            },
            "field_value": round(vix_norm * 0.7 + (1 - sp_norm) * 0.3, 3),
            "confidence": 0.85,
            "source": "Yahoo Finance",
            "lag_days": 0,
        }
    return cached("us_market", fetch)
