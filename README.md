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
| Sentiment (S) | Wikipedia pageview volume for economic terms | Warm · circular · diffuse | Wikimedia Pageviews API |
| Market (M) | Index price momentum + volatility | Cool · rounded-rectangle · defined | Yahoo Finance |
| Narrative (N) | News tone, velocity, dominant headline | Violet · directional arrows | GDELT Project |

The spatial offset between sentiment and market blooms encodes temporal lag — when one axis leads the other, the distance between their centres is the reading. Diffusion radius encodes uncertainty. Narrative velocity amplifies or dampens the sentiment and market fields continuously — when stories spread fast, the system becomes more volatile.

No single axis is sufficient alone. The relationship between them is the analytical core.

---

## Signal types

The platform identifies qualitatively distinct system states derived from the relationship between axes:

| Signal | Condition | Meaning |
|---|---|---|
| **dislocation** | divergence + accelerating narrative | affect and markets opposing while a story spreads |
| **compression** | divergence + fading narrative | tension without momentum — story losing hold |
| **consensus forming** | alignment + acceleration | fields converging as narrative builds |
| **lag tension** | large temporal offset | sentiment and markets significantly out of step |
| **drift** | gradual divergence developing | slow separation beginning |

---

## System-level reading

A single continuously updating sentence near the header summarises the overall condition across regions — drawn from divergence, lag, and narrative velocity without numerical output. It updates slowly to avoid noise.

---

## Regions — v0.1

| Region | Sentiment | Market | Narrative |
|---|---|---|---|
| United States | Wikimedia (English) | S&P 500 + VIX | GDELT (English) |
| United Kingdom | Wikimedia (English) | FTSE 100 | GDELT (English) |
| India | Wikimedia (English) | Nifty 50 + India VIX | GDELT (English) |

**Methodological note:** Signals are platform-specific and culturally situated. English-language Wikipedia and GDELT coverage reflects anglophone media and search behaviour. This limitation is declared rather than suppressed — it is part of the instrument's epistemological position. Non-anglophone pipelines are staged for subsequent phases.

---

## Data sources

| Source | Axis | Key |
|---|---|---|
| [Yahoo Finance](https://finance.yahoo.com) | Market — S&P 500, FTSE 100, Nifty 50, VIX | None |
| [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/) | Sentiment — Wikipedia article views by term | None |
| [GDELT Project](https://www.gdeltproject.org) | Narrative — global news tone and velocity | None |
| Google Trends *(planned)* | Sentiment — search volume by keyword and region | Alpha access pending |

---

## Live data status

The frontend displays per-axis status in the bottom right:

- `M●` green — market axis live · `M○` — simulated
- `S●` orange — sentiment axis live · `S○` — simulated
- `N●` violet — narrative axis live · `N○` — simulated

The platform runs fully on simulated data if the API is unavailable — no functionality is lost, only the real-world signal. The API wakes from sleep on first load (free tier — allow ~50 seconds on first visit).

---

## Structure

```
animal-spirits/
├── index.html          # frontend — D3 + Canvas, single file
├── README.md
└── api/
    ├── main.py         # FastAPI backend — market, narrative proxy
    ├── requirements.txt
    ├── render.yaml
    └── README.md
```

Sentiment (Wikimedia) and some narrative (GDELT) calls are made browser-direct where CORS permits. Market data (Yahoo Finance) routes via the Render proxy due to cloud IP restrictions.

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

Live at:
- [super-futures.github.io/animalspirits](https://super-futures.github.io/animalspirits)

**API → Render**
Connect the repo to Render, set root directory to `api/`. Free tier supported.

---

## Intellectual context

The project engages Keynes's original formulation of animal spirits, Robert Shiller's narrative economics thesis, and the tradition of data-driven affective mapping in media art and critical design. A research paper formalising the conceptual framework is in preparation.

---

## Status

v0.8 prototype · three live data sources · 3 regions · 3 axes · 4 affect clusters · 5 signal types

This is a research prototype and affective observatory. It is not a trading signal engine.
