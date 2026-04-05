from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
import time
import random
from datetime import datetime, timedelta

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

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

# ── Yahoo Finance ─────────────────────────────────────────────

YF_HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]

def fetch_yf(ticker):
    for host in random.sample(YF_HOSTS, len(YF_HOSTS)):
        try:
            r = httpx.get(f"{host}/v8/finance/chart/{ticker}",
                params={"range": "10d", "interval": "1d"},
                headers={"User-Agent": random.choice(USER_AGENTS), "Accept": "application/json",
                         "Referer": "https://finance.yahoo.com/", "Origin": "https://finance.yahoo.com"},
                timeout=12, follow_redirects=True)
            if r.status_code != 200: continue
            d = r.json()
            result = d.get("chart", {}).get("result")
            if not result: continue
            meta = result[0].get("meta", {})
            closes = [v for v in result[0].get("indicators", {}).get("quote", [{}])[0].get("close", []) if v is not None]
            if len(closes) < 2: continue
            current, prev = round(closes[-1], 2), round(closes[-2], 2)
            return {"current": current, "prev": prev, "change_pct": round((current-prev)/prev*100, 2),
                    "series": [round(v, 2) for v in closes],
                    "name": meta.get("longName") or meta.get("shortName") or ticker}
        except Exception as e:
            print(f"YF error {ticker}: {e}")
    return None

def fetch_yf_retry(ticker, retries=2):
    for _ in range(retries):
        r = fetch_yf(ticker)
        if r: return r
        time.sleep(0.5)
    return None

def build_market_field(idx, vol=None, vol_range=(10, 80)):
    if not idx: return None
    cp = idx["change_pct"]
    idx_norm = round(min(max((cp + 3) / 6, 0), 1), 3)
    vol_norm, vol_info = 0.5, None
    if vol:
        vraw = vol["current"]
        vol_norm = round(min(max((vraw - vol_range[0]) / (vol_range[1] - vol_range[0]), 0), 1), 3)
        vol_info = {"raw": vraw, "normalised": vol_norm}
    return {"index": {"current": idx["current"], "change_pct": cp, "normalised": idx_norm,
                      "series": idx["series"], "name": idx["name"]},
            "volatility": vol_info,
            "field_value": round(vol_norm * 0.7 + (1 - idx_norm) * 0.3, 3),
            "confidence": 0.88 if vol else 0.70, "source": "Yahoo Finance", "lag_days": 0}

# ── Wikimedia Pageviews — sentiment axis ─────────────────────

WIKI_TERMS = {
    "anxiety":    {"us": ["Recession","Unemployment","Stock_market_crash","Inflation","Cost_of_living"],
                   "uk": ["Recession","Unemployment","Cost_of_living_crisis","Inflation","Mortgage"],
                   "india": ["Recession","Unemployment_in_India","Inflation","Rupee","Sensex"]},
    "confidence": {"us": ["Bull_market","Economic_growth","Consumer_confidence","Investment","Hiring"],
                   "uk": ["Economic_growth","Consumer_confidence","Investment","Employment","Trade"],
                   "india": ["Economic_growth","Bull_market","Investment","Make_in_India","GDP"]},
    "aspiration": {"us": ["Luxury_goods","Travel","Real_estate","Lifestyle","Wealth"],
                   "uk": ["Luxury_goods","Travel","Property","Lifestyle","Premium"],
                   "india": ["Luxury_goods","Tourism","Real_estate","Middle_class","Consumer"]},
    "constraint": {"us": ["Budget","Debt","Frugality","Discount","Bankruptcy"],
                   "uk": ["Austerity","Budget","Debt","Food_bank","Discount"],
                   "india": ["Budget","Debt","Frugality","Savings","Austerity"]},
}

WIKI_PROJECTS = {"us": "en.wikipedia", "uk": "en.wikipedia", "india": "en.wikipedia"}

def fetch_wiki_views(article, project="en.wikipedia"):
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=7)
        url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
               f"{project}/all-access/all-agents/{article}/daily/"
               f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}")
        r = httpx.get(url, headers={"User-Agent": "AnimalSpirits/1.0 (research prototype)"}, timeout=8)
        if r.status_code != 200: return 0
        items = r.json().get("items", [])
        if not items: return 0
        views = [item.get("views", 0) for item in items]
        return sum(views) / len(views) if views else 0
    except Exception as e:
        print(f"Wiki error {article}: {e}")
        return 0

def fetch_sentiment(region, cluster):
    terms = WIKI_TERMS.get(cluster, {}).get(region, [])
    project = WIKI_PROJECTS.get(region, "en.wikipedia")
    if not terms: return None
    views = []
    for term in terms[:3]:
        v = fetch_wiki_views(term, project)
        views.append(v)
        time.sleep(0.2)
    if not any(v > 0 for v in views): return None
    total = sum(views)
    max_expected = 50000
    normalised = round(min(total / max_expected, 1.0), 3)
    return {"value": normalised, "confidence": 0.72, "source": "Wikimedia Pageviews",
            "terms": terms[:3], "views": [round(v) for v in views]}

# ── GDELT — narrative axis ────────────────────────────────────

GDELT_QUERIES = {
    "anxiety":    {"us": "economy recession unemployment inflation", "uk": "economy recession cost living",
                   "india": "economy recession inflation rupee"},
    "confidence": {"us": "economic growth jobs investment bull market", "uk": "economic growth investment jobs",
                   "india": "economic growth investment gdp"},
    "aspiration": {"us": "luxury travel real estate consumer spending", "uk": "luxury travel property spending",
                   "india": "luxury travel consumer middle class"},
    "constraint": {"us": "budget cuts debt bankruptcy frugal", "uk": "austerity budget food bank debt",
                   "india": "budget savings debt frugal austerity"},
}

GDELT_COUNTRIES = {"us": "US", "uk": "UK", "india": "India"}

def fetch_gdelt(region, cluster):
    try:
        query = GDELT_QUERIES.get(cluster, {}).get(region, "economy")
        # use sourcelang instead of sourcecountry — more reliable
        lang_filter = {"us": "sourcelang:english", "uk": "sourcelang:english", "india": "sourcelang:english"}
        lang = lang_filter.get(region, "sourcelang:english")
        full_query = f"{query} {lang}"
        r = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": full_query, "mode": "artlist", "maxrecords": "25",
                    "timespan": "24h", "format": "json"},
            timeout=15, headers={"User-Agent": "Mozilla/5.0 AnimalSpirits/1.0"})
        if r.status_code != 200:
            print(f"GDELT status {r.status_code} for {region}/{cluster}")
            return None
        text = r.text.strip()
        if not text or text == "{}":
            print(f"GDELT empty response for {region}/{cluster}")
            return None
        data = r.json()
        articles = data.get("articles", [])
        if not articles:
            print(f"GDELT no articles for {region}/{cluster}: {list(data.keys())}")
            return None
        tones = [float(a.get("tone", 0)) for a in articles if a.get("tone")]
        if not tones: return None
        avg_tone = sum(tones) / len(tones)
        tone_norm = round(min(max((avg_tone + 10) / 20, 0), 1), 3)
        tone_velocity = round((tones[-1] - tones[0]) / max(len(tones), 1) / 2, 3) if len(tones) > 1 else 0
        titles = [a.get("title", "") for a in articles[:3] if a.get("title")]
        return {"volume": len(articles), "avg_tone": round(avg_tone, 2),
                "tone_normalised": tone_norm, "velocity": tone_velocity,
                "confidence": 0.75, "source": "GDELT",
                "dominant_headline": titles[0] if titles else "",
                "top_headlines": titles}
    except Exception as e:
        print(f"GDELT error {region} {cluster}: {e}")
        return None

# ── Endpoints ─────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "1.5", "status": "live"}

@app.get("/api/market/all")
def get_market_all():
    def fetch_us():
        spx = fetch_yf_retry("%5EGSPC"); time.sleep(0.6)
        vix = fetch_yf_retry("%5EVIX")
        return build_market_field(spx, vix, (10, 80))
    def fetch_uk():
        time.sleep(0.3); return build_market_field(fetch_yf_retry("%5EFTSE"), None, (10, 60))
    def fetch_india():
        time.sleep(0.3)
        nsei = fetch_yf_retry("%5ENSEI"); time.sleep(0.4)
        ivix = fetch_yf_retry("%5EINDIAVIX")
        return build_market_field(nsei, ivix, (10, 60))
    us = cached("mkt_us", fetch_us); time.sleep(0.4)
    uk = cached("mkt_uk", fetch_uk); time.sleep(0.4)
    india = cached("mkt_india", fetch_india)
    return {"us": us, "uk": uk, "india": india}

@app.get("/api/sentiment/{region}/{cluster}")
def get_sentiment(region: str, cluster: str):
    key = f"sent_{region}_{cluster}"
    return cached(key, lambda: fetch_sentiment(region, cluster))

@app.get("/api/sentiment/all")
def get_sentiment_all():
    result = {}
    for region in ["us", "uk", "india"]:
        result[region] = {}
        for cluster in ["anxiety", "confidence", "aspiration", "constraint"]:
            key = f"sent_{region}_{cluster}"
            result[region][cluster] = cached(key, lambda r=region, c=cluster: fetch_sentiment(r, c))
            time.sleep(0.15)
    return result

@app.get("/api/narrative/{region}/{cluster}")
def get_narrative(region: str, cluster: str):
    key = f"narr_{region}_{cluster}"
    return cached(key, lambda: fetch_gdelt(region, cluster))

@app.get("/api/narrative/all")
def get_narrative_all():
    result = {}
    for region in ["us", "uk", "india"]:
        result[region] = {}
        for cluster in ["anxiety", "confidence", "aspiration", "constraint"]:
            key = f"narr_{region}_{cluster}"
            result[region][cluster] = cached(key, lambda r=region, c=cluster: fetch_gdelt(r, c))
            time.sleep(0.2)
    return result

@app.get("/api/all")
def get_all():
    return {
        "market":    get_market_all(),
        "sentiment": get_sentiment_all(),
        "narrative": get_narrative_all(),
    }

@app.get("/api/debug")
def debug():
    return {
        "version": "1.5",
        "market": {"spx": fetch_yf("%5EGSPC"), "ftse": fetch_yf("%5EFTSE")},
        "sentiment": fetch_sentiment("us", "anxiety"),
        "narrative": fetch_gdelt("us", "anxiety"),
    }
