from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time
import random

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

YF_HOSTS = [
    "https://query1.finance.yahoo.com",
    "https://query2.finance.yahoo.com",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

def fetch_yf(ticker):
    for host in random.sample(YF_HOSTS, len(YF_HOSTS)):
        try:
            r = httpx.get(
                f"{host}/v8/finance/chart/{ticker}",
                params={"range": "10d", "interval": "1d"},
                headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "application/json,text/plain,*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://finance.yahoo.com/",
                    "Origin": "https://finance.yahoo.com",
                },
                timeout=12,
                follow_redirects=True,
            )
            if r.status_code != 200:
                print(f"YF {host} returned {r.status_code} for {ticker}")
                continue
            d = r.json()
            result = d.get("chart", {}).get("result")
            if not result:
                print(f"YF no result for {ticker}: {str(d)[:200]}")
                continue
            meta = result[0].get("meta", {})
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [v for v in closes if v is not None]
            if len(closes) < 2:
                continue
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
            print(f"YF fetch error {host} {ticker}: {e}")
            continue
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
        "source": "Yahoo Finance",
        "lag_days": 0,
    }

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "1.3", "status": "live"}

def fetch_yf_retry(ticker, retries=2):
    for _ in range(retries):
        result = fetch_yf(ticker)
        if result is not None:
            return result
        time.sleep(0.5)
    return None

@app.get("/api/market/us")
def get_us():
    return cached("us", lambda: build_field(fetch_yf_retry("%5EGSPC"), fetch_yf_retry("%5EVIX"), (10, 80)))

@app.get("/api/market/uk")
def get_uk():
    return cached("uk", lambda: build_field(fetch_yf_retry("%5EFTSE"), None, (10, 60)))

@app.get("/api/market/india")
def get_india():
    return cached("india", lambda: build_field(fetch_yf_retry("%5ENSEI"), fetch_yf_retry("%5EINDIAVIX"), (10, 60)))

@app.get("/api/market/all")
def get_all():
    # fetch sequentially with delays to avoid rate limiting
    def fetch_us():
        spx = fetch_yf_retry("%5EGSPC")
        time.sleep(0.8)
        vix = fetch_yf_retry("%5EVIX")
        return build_field(spx, vix, (10, 80))
    def fetch_uk():
        time.sleep(0.4)
        return build_field(fetch_yf_retry("%5EFTSE"), None, (10, 60))
    def fetch_india():
        time.sleep(0.4)
        nsei = fetch_yf_retry("%5ENSEI")
        time.sleep(0.4)
        ivix = fetch_yf_retry("%5EINDIAVIX")
        return build_field(nsei, ivix, (10, 60))

    us    = cached("us",    fetch_us)
    time.sleep(0.5)
    uk    = cached("uk",    fetch_uk)
    time.sleep(0.5)
    india = cached("india", fetch_india)
    return {"us": us, "uk": uk, "india": india}

@app.get("/api/debug")
def debug():
    results = {}
    for sym, label in [
        ("%5EGSPC","spx"), ("%5EFTSE","ftse"),
        ("%5ENSEI","nsei"), ("%5EVIX","vix"),
        ("%5EINDIAVIX","indiavix"),
    ]:
        results[label] = fetch_yf_retry(sym)
    return {"version": "1.3", "results": results}
