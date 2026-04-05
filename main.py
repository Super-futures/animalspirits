from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yfinance as yf
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

def fetch_index(ticker_symbol, vol_symbol=None, vol_range=(10, 80)):
    """Robust index fetcher with fallback strategies."""
    try:
        end = datetime.today()
        start = end - timedelta(days=30)
        
        ticker = yf.Ticker(ticker_symbol)
        # try download first — more reliable than history()
        df = yf.download(ticker_symbol, start=start.strftime("%Y-%m-%d"), 
                        end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
        
        if df.empty:
            # fallback to history()
            df = ticker.history(period="1mo")
        
        if df.empty:
            return None

        closes = df["Close"].dropna().tolist()
        if len(closes) < 2:
            return None

        # flatten if nested (yf.download returns MultiIndex sometimes)
        if hasattr(closes[0], '__len__'):
            closes = [float(c[0]) if hasattr(c, '__len__') else float(c) for c in closes]

        current = round(float(closes[-1]), 2)
        change_pct = round((float(closes[-1]) - float(closes[-2])) / float(closes[-2]) * 100, 2)
        idx_norm = round(min(max((change_pct + 3) / 6, 0), 1), 3)

        vol_data = None
        vol_norm = 0.5
        if vol_symbol:
            try:
                vdf = yf.download(vol_symbol, start=start.strftime("%Y-%m-%d"),
                                 end=end.strftime("%Y-%m-%d"), progress=False, auto_adjust=True)
                if vdf.empty:
                    vdf = yf.Ticker(vol_symbol).history(period="1mo")
                if not vdf.empty:
                    vc = vdf["Close"].dropna().tolist()
                    if vc:
                        vraw = round(float(vc[-1]), 2)
                        vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
                        vol_data = {
                            "raw": vraw,
                            "normalised": vol_norm,
                            "series": [round(float(v), 2) for v in vc[-10:]],
                            "source": f"Yahoo Finance — {vol_symbol}",
                        }
            except Exception as e:
                print(f"Vol fetch error {vol_symbol}: {e}")

        return {
            "index": {
                "ticker": ticker_symbol,
                "current": current,
                "change_pct": change_pct,
                "normalised": idx_norm,
                "series": [round(float(v), 2) for v in closes[-10:]],
            },
            "volatility": vol_data,
            "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
            "confidence": 0.85 if vol_data else 0.65,
            "source": "Yahoo Finance",
            "lag_days": 0,
        }
    except Exception as e:
        print(f"fetch_index error {ticker_symbol}: {e}")
        return None

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "0.2", "status": "live"}

@app.get("/api/market/us")
def get_us_market():
    return cached("us_market", lambda: fetch_index("^GSPC", vol_symbol="^VIX", vol_range=(10, 80)))

@app.get("/api/market/uk")
def get_uk_market():
    return cached("uk_market", lambda: fetch_index("^FTSE", vol_symbol="^VFTSE", vol_range=(10, 60)))

@app.get("/api/market/india")
def get_india_market():
    return cached("india_market", lambda: fetch_index("^NSEI", vol_symbol="^INDIAVIX", vol_range=(10, 60)))

@app.get("/api/market/all")
def get_all_markets():
    return {
        "us":    cached("us_market",    lambda: fetch_index("^GSPC", vol_symbol="^VIX",      vol_range=(10, 80))),
        "uk":    cached("uk_market",    lambda: fetch_index("^FTSE", vol_symbol="^VFTSE",    vol_range=(10, 60))),
        "india": cached("india_market", lambda: fetch_index("^NSEI", vol_symbol="^INDIAVIX", vol_range=(10, 60))),
    }

@app.get("/api/debug")
def debug():
    """Test endpoint — returns raw yfinance data for diagnostics."""
    try:
        df = yf.download("^GSPC", period="5d", progress=False)
        return {
            "empty": df.empty,
            "shape": list(df.shape),
            "columns": list(df.columns.astype(str)),
            "tail": df.tail(2).to_dict() if not df.empty else {}
        }
    except Exception as e:
        return {"error": str(e)}
