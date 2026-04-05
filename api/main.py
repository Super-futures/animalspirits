from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache = {}
CACHE_TTL = 900

def cached(key, fn):
    now = time.time()
    if key in _cache and _cache[key]["data"] is not None and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fn()
    if data is not None:
        _cache[key] = {"data": data, "ts": now}
    return data

YF_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_yf(ticker):
    try:
        r = httpx.get(
            f"{YF_BASE}{ticker}",
            params={"range": "5d", "interval": "1d"},
            headers=HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        d = r.json()
        meta = d.get("chart", {}).get("result", [{}])[0].get("meta", {})
        closes = d.get("chart", {}).get("result", [{}])[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [v for v in closes if v is not None]
        if not closes or len(closes) < 2:
            print(f"YF empty for {ticker}: {str(d)[:200]}")
            return None
        current = round(closes[-1], 2)
        prev = round(closes[-2], 2)
        change_pct = round((current - prev) / prev * 100, 2)
        return {
            "current": current,
            "prev": prev,
            "change_pct": change_pct,
            "series": [round(v, 2) for v in closes],
            "name": meta.get("longName") or meta.get("shortName") or ticker,
        }
    except Exception as e:
        print(f"fetch_yf error {ticker}: {e}")
        return None

def build_field(index_data, vol_data=None, vol_range=(10, 80)):
    if not index_data:
        return None
    change_pct = index_data["change_pct"]
    idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)
    vol_norm = 0.5
    vol_info = None
    if vol_data:
        vraw = vol_data["current"]
        vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
        vol_info = {"raw": vraw, "normalised": vol_norm}
    return {
        "index": {
            "current": index_data["current"],
            "change_pct": change_pct,
            "normalised": idx_norm,
            "series": index_data["series"],
            "name": index_data["name"],
        },
        "volatility": vol_info,
        "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
        "confidence": 0.88 if vol_data else 0.70,
        "source": "Yahoo Finance via proxy",
        "lag_days": 0,
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.9", "status": "live"}

@app.get("/api/market/us")
def get_us():
    def fetch():
        return build_field(fetch_yf("%5EGSPC"), fetch_yf("%5EVIX"), (10, 80))
    return cached("us", fetch)

@app.get("/api/market/uk")
def get_uk():
    def fetch():
        return build_field(fetch_yf("%5EFTSE"), None, (10, 60))
    return cached("uk", fetch)

@app.get("/api/market/india")
def get_india():
    def fetch():
        return build_field(fetch_yf("%5ENSEI"), None, (10, 60))
    return cached("india", fetch)

@app.get("/api/market/all")
def get_all():
    def fetch_us():   return build_field(fetch_yf("%5EGSPC"), fetch_yf("%5EVIX"), (10, 80))
    def fetch_uk():   return build_field(fetch_yf("%5EFTSE"), None, (10, 60))
    def fetch_india():return build_field(fetch_yf("%5ENSEI"), None, (10, 60))
    return {
        "us":    cached("us",    fetch_us),
        "uk":    cached("uk",    fetch_uk),
        "india": cached("india", fetch_india),
    }

@app.get("/api/debug")
def debug():
    return {
        "spx": fetch_yf("%5EGSPC"),
        "ftse": fetch_yf("%5EFTSE"),
        "nsei": fetch_yf("%5ENSEI"),
    }
