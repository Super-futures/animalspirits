# Animal Spirits API — v0.1

Minimal FastAPI backend serving live market data for the Animal Spirits prototype.

## Endpoints

- `GET /` — health check
- `GET /api/vix` — live VIX data, normalised to 0–1
- `GET /api/market/us` — US market field: VIX + S&P 500 blended signal

## Deploy to Render (free tier)

1. Push this folder to a GitHub repo
2. Go to render.com → New Web Service
3. Connect the repo
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy — you get a URL like `https://animal-spirits-api.onrender.com`

## Local dev

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open: http://localhost:8000/api/vix

## Response shape — /api/market/us

```json
{
  "vix": {
    "raw": 18.4,
    "change_pct": 2.1,
    "normalised": 0.12,
    "series": [17.2, 17.8, 18.1, 18.4],
    "source": "Yahoo Finance — ^VIX",
    "label": "CBOE Volatility Index"
  },
  "sp500": {
    "current": 5204.3,
    "change_pct": -0.4,
    "normalised": 0.43
  },
  "field_value": 0.21,
  "confidence": 0.85,
  "source": "Yahoo Finance",
  "lag_days": 0
}
```

`field_value` is the normalised 0–1 signal that feeds directly into
the Animal Spirits market bloom for the US region.
