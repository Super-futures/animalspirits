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
| Sentiment | Wikipedia pageview volume for economic terms | Warm · circular · diffuse | Wikimedia Pageviews API |
| Market | Index price momentum + volatility | Cool · rounded-rectangle · defined | Yahoo Finance |
| Narrative | News tone, velocity, dominant headline | Violet · directional arrows | GDELT Project |

The spatial offset between sentiment and market blooms encodes temporal lag — when one axis leads the other, the distance between their centres is the reading. Diffusion radius encodes uncertainty: high confidence produces tight, defined blooms; low confidence produces soft, wide fields.

No single axis is sufficient alone. Most sentiment tools collapse all three into a single fear/greed dial. Animal Spirits keeps them separate because the separateness is where the insight lives.

The most analytically significant state: divergent sentiment/market axes combined with accelerating narrative velocity — affect and markets opposing each other while a story spreads.

---

## Regions — v0.1

| Region | Sentiment | Market indices | Narrative |
|---|---|---|---|
| United States | Wikimedia (English) | S&P 500 + VIX | GDELT (English) |
| United Kingdom | Wikimedia (English) | FTSE 100 | GDELT (English) |
| India | Wikimedia (English) | Nifty 50 + India VIX | GDELT (English) |

**Methodological note:** Signals are platform-specific and culturally situated. English-language Wikipedia and GDELT coverage skews toward anglophone media and search behaviour. This limitation is declared rather than suppressed — it is part of the instrument's epistemological position. Non-anglophone pipelines (Naver for Korea, vernacular Indian sources) are staged for subsequent phases.

---

## Data sources

| Source | Axis | Coverage | Key |
|---|---|---|---|
| [Yahoo Finance](https://finance.yahoo.com) | Market | S&P 500, FTSE 100, Nifty 50, VIX, India VIX | None |
| [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/) | Sentiment | Wikipedia article views by term and language | None |
| [GDELT Project](https://www.gdeltproject.org) | Narrative | Global news tone, volume, velocity | None |
| [Google Trends](https://trends.google.com) *(planned)* | Sentiment | Search volume by keyword and region | Alpha access pending |

---

## Live data status

The frontend displays per-axis status in the bottom right:

- `M●` — market axis live · `M○` — simulated
- `S●` — sentiment axis live · `S○` — simulated
- `N●` — narrative axis live · `N○` — simulated

The platform runs fully on simulated data if the API is unavailable — no functionality is lost, only the real-world signal.

---

## Structure

```
animal-spirits/
├── index.html          # frontend — D3 + Canvas, single file
├── README.md
└── api/
    ├── main.py         # FastAPI backend — market, sentiment, narrative
    ├── requirements.txt
    ├── render.yaml     # Render deployment config
    └── README.md
```

---

## Running locally

**Frontend**
Open `index.html` directly in a browser. Runs on simulated data without the API.

**API**
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open `http://localhost:8000/api/debug`

---

## Deploying

**Frontend → GitHub Pages or Netlify**
Push `index.html` to the repo root. No build step required.

Live at:
- [animal-spirits.netlify.app](https://animal-spirits.netlify.app)
- [super-futures.github.io/animalspirits](https://super-futures.github.io/animalspirits)

**API → Render**
Connect the repo to Render, set root directory to `api/`. Free tier supported — note that free instances sleep after inactivity and take ~50 seconds to wake. The frontend handles this gracefully, showing `connecting...` while the API wakes.

---

## Intellectual context

The project engages Keynes's original formulation of animal spirits, Robert Shiller's narrative economics thesis, and the tradition of data-driven affective mapping in media art and critical design. A research paper formalising the conceptual framework is in preparation.

---

## Status

v0.7 prototype · three live data sources · 3 regions · 3 axes · 4 affect clusters

This is a research prototype and affective observatory. It is not a trading signal engine.
