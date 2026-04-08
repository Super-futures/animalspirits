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
    _cache[key] = {"data": data, "ts": now}  # cache None too — prevents retry storm on upstream failure
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
        # fetch articles with tone via artlist + outputfields
        r = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": full_query, "mode": "artlist", "maxrecords": "25",
                    "timespan": "24h", "format": "json",
                    "sort": "toneasc"},
            timeout=15, headers={"User-Agent": "Mozilla/5.0 AnimalSpirits/1.0"})
        if r.status_code != 200:
            print(f"GDELT status {r.status_code} for {region}/{cluster}")
            return None
        text = r.text.strip()
        if not text or text == "{}" or "Please limit" in text:
            print(f"GDELT rate limited or empty for {region}/{cluster}")
            return None
        data = r.json()
        articles = data.get("articles", [])
        if not articles:
            print(f"GDELT no articles for {region}/{cluster}")
            return None

        # tone field may be absent in artlist — use article count + seendate as proxy
        # also try fetching tone via timelinetone in parallel
        tones_raw = [a.get("tone") for a in articles if a.get("tone") is not None]

        if tones_raw:
            tones = [float(t) for t in tones_raw]
        else:
            # fetch tone timeline as fallback
            r2 = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",
                params={"query": full_query, "mode": "timelinetone",
                        "timespan": "24h", "format": "json"},
                timeout=12, headers={"User-Agent": "Mozilla/5.0 AnimalSpirits/1.0"})
            if r2.status_code == 200:
                td = r2.json()
                timeline = td.get("timeline", [{}])[0].get("data", [])
                tones = [float(p.get("value", 0)) for p in timeline if p.get("value") is not None]
            else:
                tones = [0.0]

        if not tones: tones = [0.0]
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

# ── Endpoints — Animal Spirits ────────────────────────────────

@app.get("/")
def root():
    return {"name": "Animal Spirits API", "version": "1.9", "status": "live"}

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

@app.get("/api/gdelt/{region}/{cluster}")
def gdelt_proxy(region: str, cluster: str):
    key = f"gdelt_{region}_{cluster}"
    return cached(key, lambda: fetch_gdelt(region, cluster))

@app.get("/api/gdelt/all")
def gdelt_all():
    # fetch all 12 combinations sequentially with 6s gap to respect rate limit
    # cached for 15min so only runs once per window
    result = {}
    for r in ["us","uk","india"]:
        result[r] = {}
        for c in ["anxiety","confidence","aspiration","constraint"]:
            key = f"gdelt_{r}_{c}"
            if key in _cache and _cache[key]["data"] is not None:
                result[r][c] = _cache[key]["data"]
            else:
                data = fetch_gdelt(r, c)
                if data is not None:
                    _cache[key] = {"data": data, "ts": time.time()}
                result[r][c] = data
                time.sleep(6)  # respect GDELT 5s rate limit
    return result

@app.get("/api/gdelt/cluster/{cluster}")
def gdelt_by_cluster(cluster: str):
    # fetch one cluster across all regions — 3 calls, 18s total
    # used by frontend to fetch active cluster only
    result = {}
    for r in ["us","uk","india"]:
        key = f"gdelt_{r}_{cluster}"
        if key in _cache and _cache[key]["data"] is not None:
            result[r] = _cache[key]["data"]
        else:
            data = fetch_gdelt(r, cluster)
            if data is not None:
                _cache[key] = {"data": data, "ts": time.time()}
            result[r] = data
            time.sleep(6)
    return result

@app.get("/api/debug")
def debug():
    # raw GDELT test
    gdelt_raw = None
    try:
        r = httpx.get("https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": "economy recession sourcelang:english",
                    "mode": "artlist", "maxrecords": "5",
                    "timespan": "24h", "format": "json"},
            timeout=15, headers={"User-Agent": "Mozilla/5.0 AnimalSpirits/1.0"})
        gdelt_raw = {"status": r.status_code, "length": len(r.text), "preview": r.text[:300]}
    except Exception as e:
        gdelt_raw = {"error": str(e)}
    return {
        "version": "1.9",
        "market": {"spx": fetch_yf("%5EGSPC"), "ftse": fetch_yf("%5EFTSE")},
        "sentiment": fetch_sentiment("us", "anxiety"),
        "narrative": "see /api/gdelt/us/anxiety",
        "gdelt_raw": gdelt_raw,
    }

# ── Undertow: PortWatch constants ────────────────────────────
# Dataset UUIDs confirmed from World Bank Red Sea Monitoring notebook:
#   chokepoint6 (Hormuz): cb5856222a5b4105adc6ee7e880a1730
#   chokepoint1 (Suez):   c57c79bf612b4372b08a9c6ea9c97ef0
PW_DATASETS = {
    "hormuz": "cb5856222a5b4105adc6ee7e880a1730",
    "suez":   "c57c79bf612b4372b08a9c6ea9c97ef0",
}
PW_NORMAL = {"hormuz": 130, "suez": 60}  # pre-crisis 7-day average baselines (EIA/IEA 2025)
PW_TTL    = 21600  # 6 hours — PortWatch updates weekly, no value in fetching more often

# ── Endpoints — Undertow ──────────────────────────────────────

@app.get("/api/undertow/market")
def get_undertow_market():
    """
    Brent Crude (BZ=F) and Baltic Dry Index (^BDI) for Undertow.
    Proxied server-side — Yahoo Finance blocks browser CORS requests.
    Normalisation: Brent $70=0.0 / $140=1.0 · BDI 400=0.0 / 4000=1.0
    Cached 15 minutes (shared CACHE_TTL).
    """
    def fetch_brent():
        data = fetch_yf_retry("BZ%3DF")  # BZ=F — %3D encodes = (matches existing %5E^ convention)
        if not data:
            return None
        closes = data["series"]
        if len(closes) < 2:
            return None
        latest = closes[-1]
        # mean absolute return over last 11 intervals — volatility proxy
        n = min(len(closes), 12)
        vol = 0.0
        for i in range(1, n):
            vol += abs(closes[i] - closes[i - 1]) / closes[i - 1]
        vol = round(min(vol / (n - 1) / 0.014, 1.0), 3)
        return {
            "latest": latest,
            "norm":   round(min(max((latest - 70) / 70, 0), 1), 3),
            "vol":    vol,
            "series": closes,
        }

    def fetch_bdi():
        data = fetch_yf_retry("%5EBDI")  # ^BDI — %5E encodes ^ (matches existing convention)
        if not data:
            return None
        closes = data["series"]
        if len(closes) < 2:
            return None
        latest = closes[-1]
        # week-on-week trend direction
        prev  = closes[max(0, len(closes) - 7)]
        trend = round((latest - prev) / prev, 4) if prev else 0.0
        return {
            "latest": latest,
            "norm":   round(min(max((latest - 400) / 3600, 0), 1), 3),
            "trend":  trend,
            "series": closes,
        }

    brent = cached("undertow_brent", fetch_brent)
    bdi   = cached("undertow_bdi",   fetch_bdi)

    return {"brent": brent, "bdi": bdi}


@app.get("/api/undertow/portwatch")
def get_undertow_portwatch():
    """
    IMF PortWatch AIS transit calls for Hormuz and Suez.
    Queries the public ArcGIS FeatureServer — no API key required.
    Updated weekly by PortWatch (Tuesdays 09:00 ET) — cached 6 hours.
    Returns 7-day average daily transit count, normalised against
    pre-crisis baselines: Hormuz 130/day, Suez 60/day (EIA/IEA 2025).

    Dataset UUIDs confirmed from World Bank Red Sea Monitoring notebook:
      chokepoint6 (Hormuz): cb5856222a5b4105adc6ee7e880a1730
      chokepoint1 (Suez):   c57c79bf612b4372b08a9c6ea9c97ef0
    """
    def fetch_portwatch_node(node, uuid):
        try:
            url = (
                f"https://portwatch.imf.org/datasets/{uuid}_0/query"
                f"?where=1%3D1"
                f"&outFields=date%2Cn_total%2Cn_tanker%2Ccapacity"
                f"&orderByFields=date+DESC"
                f"&resultRecordCount=7"
                f"&returnGeometry=false&f=json"
            )
            r = httpx.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Undertow/1.0; research)"},
                timeout=15,
                follow_redirects=True,
            )
            if r.status_code != 200:
                print(f"PortWatch {node}: HTTP {r.status_code}")
                return None
            features = r.json().get("features", [])
            if not features:
                print(f"PortWatch {node}: no features returned")
                return None
            total = sum(f.get("attributes", {}).get("n_total") or 0 for f in features)
            avg   = round(total / len(features), 1)
            norm  = round(min(avg / PW_NORMAL[node], 1.0), 3)
            latest_ts = features[0].get("attributes", {}).get("date")
            return {
                "avg_daily":       avg,
                "norm":            norm,
                "n_features":      len(features),
                "latest_ts":       latest_ts,
                "normal_baseline": PW_NORMAL[node],
            }
        except Exception as e:
            print(f"PortWatch {node} error: {e}")
            return None

    results = {}
    now = time.time()
    for node, uuid in PW_DATASETS.items():
        cache_key = f"undertow_pw_{node}"
        if (cache_key in _cache
                and _cache[cache_key]["data"] is not None
                and now - _cache[cache_key]["ts"] < PW_TTL):
            results[node] = _cache[cache_key]["data"]
        else:
            data = fetch_portwatch_node(node, uuid)
            if data is not None:
                _cache[cache_key] = {"data": data, "ts": now}
            results[node] = data

    return results
