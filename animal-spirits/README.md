# Animal Spirits

**A platform for mapping collective affect and economic behaviour**

Animal Spirits maps three distinct axes per region — sentiment, market, and narrative velocity — tracking four affect clusters across geographies and time. Each axis is analytically independent: what populations feel, what capital is doing, and what stories are spreading fast enough to shape behaviour. The relationship between them is where the insight lives.

The name draws on Keynes's original formulation: the spontaneous urge to action that drives economic behaviour, neither fully rational nor fully legible, but observable.

---

## The four affect clusters

**Anxiety / fear** — anticipatory constraint. Searches for protection, liquidity, certainty. Tends to precede market drawdowns when narrative velocity is high.

**Confidence / optimism** — collective risk tolerance. Rising credit uptake, investment activity, expansive search behaviour. When the sentiment and market axes converge, the feedback loop between belief and action is at its tightest.

**Aspiration / desire** — future-oriented identity projection via consumption. Luxury travel, lifestyle upgrades, housing searches encode where people believe they are headed, not just where they are.

**Constraint behaviour** — active adjustment, distinct from anxiety. Searches for budgeting, discount retail, debt consolidation. A population in recalibration, not anticipation.

---

## The three axes

| Axis | Signal | Visual language | Source |
|---|---|---|---|
| Sentiment | Search behaviour | Warm · circular · diffuse | Google Trends |
| Market | Economic indicators | Cool · rounded-rectangle · defined | Yahoo Finance |
| Narrative | Story propagation speed and direction | Violet · directional arrows | GDELT |

The spatial offset between sentiment and market blooms encodes temporal lag — when one axis leads the other, the distance between their centres is the reading. Diffusion radius encodes uncertainty: high confidence produces tight, defined blooms; low confidence produces soft, wide fields.

No single axis is sufficient alone. Most sentiment tools collapse all three into a single fear/greed dial. Animal Spirits keeps them separate because the separateness is where the insight lives.

The most analytically significant state: divergent sentiment/market axes combined with accelerating narrative velocity — affect and markets opposing each other while a story spreads.

---

## Regions — v0.1

| Region | Sentiment source | Market indices |
|---|---|---|
| United States | Google Trends | VIX, S&P 500 |
| United Kingdom | Google Trends | FTSE 100 |
| Seoul | Google Trends (Phase 1) | KOSPI |

**Methodological note — Seoul:** Naver is the appropriate search pipeline for Korean sentiment data. Google Trends is used as a Phase 1 proxy with this limitation explicitly declared. Naver integration is staged for a subsequent phase.

---

## Structure

```
animal-spirits/
├── index.html          # frontend — D3 + Canvas, single file
├── README.md
└── api/
    ├── main.py         # FastAPI backend
    ├── requirements.txt
    ├── render.yaml     # Render deployment config
    └── README.md
```

---

## Running locally

**Frontend**
Open `index.html` directly in a browser. Runs fully on simulated data without the API.

**API**
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open `http://localhost:8000/api/market/us`

---

## Deploying

**Frontend → GitHub Pages or Netlify**
Push `index.html` to the repo root. Enable GitHub Pages or connect to Netlify. No build step required.

**API → Render**
Connect the repo to Render, set the root directory to `api/`. Render reads `render.yaml` automatically. Free tier is sufficient for prototype use.

On first load the frontend will prompt for your Render API URL. This is stored in the browser — you will not be asked again.

---

## Data sources

- [Google Trends](https://trends.google.com) via `pytrends`
- [Yahoo Finance](https://finance.yahoo.com) via `yfinance`
- [GDELT Project](https://www.gdeltproject.org) — real-time global news with emotional tone scoring

---

## Status

v0.7 prototype · simulated data with live market pipeline (VIX + S&P 500) · 3 regions · 3 axes · 4 affect clusters

This is a research prototype and affective observatory. It is not a trading signal engine.

---

## Intellectual context

The project engages Keynes's original formulation of animal spirits, Robert Shiller's narrative economics thesis, and the tradition of data-driven affective mapping in media art and critical design. A research paper formalising the conceptual framework is in preparation.
