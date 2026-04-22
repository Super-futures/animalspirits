# Animal Spirits

**A relational visualisation of collective behavioural states**

Animal Spirits is a computational observatory that models economic behaviour as an emergent field arising from the interaction of three signal domains. Rather than treating attention, market, and narrative as separate indicators, the system renders their interdependence as a continuous behavioural regime.

The project draws on Keynes's notion of *animal spirits*, reframed as a **collective system condition** rather than an individual psychological driver. Behaviour is not measured directly. It is inferred from the relationships between signals.

---

## Concept

The system separates two distinct properties of collective behaviour:

- **Direction** — expansionary vs contractionary momentum (Bull ↔ Bear)
- **Tension** — stability vs instability arising from misalignment (Stag)

These are not categories or labels. They are **probabilistic conditions** of the system at a given moment, derived from a low-dimensional dynamical field.

---

## The three axes

| Axis | Signal | Visual language | Source |
|---|---|---|---|
| Attention (A) | Wikipedia pageview volume for economic terms | Warm · circular · diffuse | Wikimedia Pageviews API |
| Market (M) | Index log-return momentum + volatility | Cool · rounded-rectangle · defined | Yahoo Finance (via proxy) |
| Narrative (N) | News volume + velocity | Violet · directional arrows | GDELT Project |

Each axis represents a distinct dimension:
- **A** → what draws collective cognitive focus
- **M** → what constrains or enables action
- **N** → what stories propagate and at what speed

No single axis is sufficient. Insight emerges from their **interaction**.

---

## Signal pipeline

All signals pass through a common processing layer before entering the dynamical model:

1. **Smoothing** — EMA (α ≈ 0.25) applied to raw attention, log-returns, and narrative volume
2. **Derivatives** — finite-difference velocity for market (`dM`) and narrative (`dN`), clamped to [-1.0, 1.0]
3. **Volatility** — rolling standard deviation of market returns (`V`)
4. **Normalisation** — per-region z-score over a rolling buffer: `X' = (X - μ) / σ`

This ensures scale invariance and cross-region comparability.

---

## Latent field

A single scalar field is constructed from the normalised signals:

```
Ψ(t) = 0.8·A'(t) + 1.0·M'(t) + 0.9·N'(t)
```

Ψ encodes the combined directional pressure of the system. It is not a sentiment score — it is a **field coordinate**.

---

## Behavioural states

### Bull / Bear (directional field)

```
z_bull = Ψ + a·dM'          (a ≈ 0.8)
z_bear = -Ψ + b·dN'         (b ≈ 0.6)

P_bull_raw = sigmoid(z_bull)
P_bear_raw = sigmoid(z_bear)
Z = P_bull_raw + P_bear_raw

P_bull = P_bull_raw / Z
P_bear = P_bear_raw / Z
```

### Stag (instability field)

Stag is not a third independent class. It is an **emergent property** of misalignment:

```
tension = |A' - M'| + k·|dN'| + v·max(0, V')    (k ≈ 0.5, v ≈ 0.4)
P_stag = sigmoid(tension - 1.0)
```

When attention and market diverge, narrative accelerates, or volatility rises, tension increases and the system enters a transitional state.

---

## System metrics

### Entropy

```
H = -(P_bull·log(P_bull) + P_bear·log(P_bear))
```

- Low H → confident regime (bull or bear dominant)
- High H → transition / uncertainty

### Instability

```
instability = P_stag + H
```

Used to modulate visual diffusion, fragmentation, and desaturation.

### Temporal lag

```
L(t) ≈ A'(t) - M'(t)
```

Encodes which axis leads. Visualised as spatial offset between attention and market blooms.

---

## Visual language

The map encodes relationships, not values:

| Mathematical quantity | Visual encoding |
|---|---|
| A ↔ M offset | Spatial displacement between blooms |
| dN | Narrative arrow direction and density |
| V | Diffusion radius |
| P_bull / P_bear | Continuous green ↔ red gradient |
| P_stag | Fragmentation, desaturation, blur |
| H | Entropy ring dash ratio around regime badge |
| instability | Ghost trail intensity, jitter, opacity modulation |

**Ghost trails** — canvas fade at 8% per frame makes drift and regime shifts visible as motion smear.

**Stag fragmentation** — when instability > 0.6, blooms split into 2–5 orbiting satellites (count scales with entropy). Reads as "coming apart."

**Narrative wake** — decaying arrow tails over 4 frames make velocity visible over time.

**RBF isolines** — Ψ = 0 contour drawn via radial-basis interpolation between region centres. Faint neutral membrane separating bullish and bearish territories.

**Curved entanglement arcs** — quadratic Bézier links between regions, thickness scaling with narrative delta, colour shifting toward source regime.

**Unified sparklines** — single 24 px canvas per panel with A, M, N in horizontal bands. Fill between A and M shows divergence directly.

---

## Regions

| Region | Attention | Market | Narrative | Rhythm |
|---|---|---|---|---|
| United States | Wikimedia (English) | S&P 500 + VIX | GDELT (English) | Baseline |
| United Kingdom | Wikimedia (English) | FTSE 100 | GDELT (English) | Slower · more persistent |
| India | Wikimedia (English) | Nifty 50 + India VIX | GDELT (English) | Faster · higher variance |

Regional rhythm differences are structural. Signals are normalised per region to preserve comparability.

**Methodological note:** English-language Wikipedia and GDELT coverage reflects anglophone media and search behaviour. This limitation is declared rather than suppressed.

---

## Data sources

| Source | Axis | Key |
|---|---|---|
| [Yahoo Finance](https://finance.yahoo.com) | Market — S&P 500, FTSE 100, Nifty 50, VIX | None |
| [Wikimedia Pageviews API](https://wikimedia.org/api/rest_v1/) | Attention — article views by term | None |
| [GDELT Project](https://www.gdeltproject.org) | Narrative — global news volume and velocity | None |

---

## Live data status

Per-axis status in the bottom right:

- `M●` green — market axis live · `M○` — simulated
- `A●` orange — attention axis live · `A○` — simulated
- `N●` violet — narrative axis live · `N○` — simulated

The system runs fully on simulated data if APIs are unavailable. The API wakes from sleep on first load (free tier — allow ~50 seconds on first visit).

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

Attention (Wikimedia) and some narrative (GDELT) calls are made browser-direct where CORS permits. Market data (Yahoo Finance) routes via the Render proxy due to cloud IP restrictions.

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

**API → Render**
Connect the repo to Render, set root directory to `api/`. Free tier supported.

---

## Intellectual context

The project engages Keynes's original formulation of animal spirits, Robert Shiller's narrative economics thesis, and the tradition of data-driven affective mapping in media art and critical design. A research paper formalising the conceptual framework is in preparation.

---

## Status

v0.9 prototype · continuous behavioural field model · 3 regions · 3 axes · 3 states

This is a research prototype and affective observatory. It is not a trading signal engine.

---

## Limitations

- Signals are partial and culturally situated (anglophone bias)
- Narrative data is noisy and uneven across regions
- The model is low-dimensional and intentionally reductive
- The system is not predictive and should not be used for trading
