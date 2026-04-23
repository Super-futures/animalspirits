# Animal Spirits

**A platform for mapping collective affect and economic behaviour.**

A single-file, real-time visualisation of three entangled signals — **Attention**, **Market**, and **Narrative** — projected into a latent field that resolves into continuous regime probabilities: **Bull**, **Bear**, and **Stag**.

---

## Quick Start

Open `animalspirits_v11.html` in any modern browser. No build step or server required.

```bash
open animalspirits_v11.html
```

The prototype fetches live data where available and falls back to a synthetic dynamics engine when offline.

---

## What It Shows

### Three Axes

| Axis | Visual | Meaning |
|------|--------|---------|
| **Attention** | Warm, diffuse circles | Collective focus and affect intensity |
| **Market** | Cool, defined squares | Price momentum and economic momentum |
| **Narrative** | Purple directional arrows | Story volume and velocity (tone × spread) |

### Three Regimes

The system does not use thresholds. Probabilities emerge from field dynamics:

- **Bull** (green) — Expansion. Signals aligned upward.
- **Bear** (red) — Contraction. Signals aligned downward.
- **Stag** (amber) — Instability. High tension when axes diverge or accelerate.

### Posture (v11)

Posture replaces dense technical readouts with an immediate, human-readable stance:

| Posture | Condition | Meaning |
|---------|-----------|---------|
| **Lean** | Signals aligned | Momentum is coherent. Safe to follow the drift. |
| **Caution** | Signals out of sync (\|A − M\| > 0.5) | Divergence between attention and market. Risk of reversal. |
| **Pause** | P(stag) > 0.6 | Instability elevated. Wait for clarity. |

Click any region panel to see its **Posture**, **Alignment**, and **Lag** (who is leading: attention or markets).

### Global Headline

A single sentence under the header aggregates all regions:

> **Global: Lean — signals moving together**  
> **Global: Caution — signals diverging**  
> **Global: Pause — instability elevated**

---

## Architecture

```
┌─────────────────────────────────────┐
│  SVG World Map (D3 + TopoJSON)      │
│  Canvas Overlay (blooms, trails,    │
│  arrows, isolines, fragmentation)   │
├─────────────────────────────────────┤
│  Signal Layer (EMA, Derivative,     │
│  Rolling Std, Per-region norm)      │
├─────────────────────────────────────┤
│  Dynamics Layer (Ψ field, tension,  │
│  entropy, regime probabilities)     │
├─────────────────────────────────────┤
│  Data Layer                         │
│  • Wikimedia pageviews (attention)  │
│  • GDELT (narrative tone)           │
│  • Custom market API                │
│  • Synthetic fallback engine        │
└─────────────────────────────────────┘
```

### Key Design Decisions

- **Single file** — HTML, CSS, and JS in one document for zero-friction prototyping.
- **Canvas over SVG** — Geographic features in SVG; high-frequency particle effects, trails, and narrative arrows in Canvas.
- **Synthetic fallback** — A stochastic latent-variable engine generates plausible dynamics when live APIs are unavailable or cold.
- **No thresholds** — Regimes are probabilistic outputs of a latent field, not hard rules.

---

## Data Sources

| Source | Axis | Endpoint / Method |
|--------|------|-------------------|
| Wikimedia REST API | Attention | `pageviews/per-article` for clustered terms (anxiety, confidence, aspiration, constraint) |
| GDELT | Narrative | `/api/gdelt/cluster/{cluster}` via Render proxy |
| Custom Market API | Market | `/api/market/all` via Render |
| Synthetic Engine | All | Internal Brownian-motion latent variable with regime-dependent drift |

---

## Mathematical Model

The system projects three smoothed, normalised signals into a latent field **Ψ**:

```
Ψ = 0.8·A_norm + 1.0·M_norm + 0.9·N_norm
```

From Ψ and the derivatives of market and narrative signals, it computes:

- **P(Bull)** — `sigmoid(Ψ + a·ΔM)`
- **P(Bear)** — `sigmoid(-Ψ + b·ΔN)`
- **Tension** — `|A − M| + k·|ΔN| + v_w·max(0, V)`
- **P(Stag)** — `sigmoid(tension − 1.0)`
- **Entropy H** — Shannon entropy of the bull/bear distribution
- **Instability** — `P(Stag) + H`

These values drive every visual parameter: bloom size, colour, fragmentation, jitter, dash patterns, and narrative arrow density.

---

## Controls

- **Regime slider** — Live aggregate bear/bull balance across all regions.
- **Time horizon** — `24h` / `7d` / `30d` rolling pulse (modulates synthetic drift speed).
- **Uncertainty toggle** — Visualises diffusion rings when instability is elevated.
- **Region click** — Focus a region to dim others and reveal its Posture box.

---

## Browser Support

Chrome, Safari, Firefox, Edge (latest). Requires ES6 and Canvas 2D.

---

## Notes

- The Render API may cold-start after periods of inactivity; the UI indicates live vs. simulated status per axis.
- Map data is loaded from `world-atlas@2` via jsDelivr CDN.
- D3.js v7 and TopoJSON v3 are loaded from cdnjs.

---

## License

Prototype v0.9 — for evaluation and demonstration.
