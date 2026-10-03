# H-34-01 preregistration — SGMC substrate-concealment prior (frozen 2026-10-03)

Status: **registered, not yet run.** This file is written *before* the concealment
raster exists on the grid and before any mask is emitted. Every parameter below is
frozen; any deviation has to be reported as exploratory and cannot gate a submission
slot.

## 1. Hypothesis

A geological map is a mapping-effort product: a trace is drawn where rock is exposed
well enough to follow. Faults beneath playa, lake beds, young basin fill and
Quaternary cover are therefore systematically under-represented in *any* surface
catalogue — and the organizer scores only faults that the USGS/INGENIOUS catalogue
*does not* contain. The prior under test says that a limited budget of evidence is
better spent inside concealing substrate than spread uniformly over exposed bedrock,
because that is where a missing fault can hide without leaving a mappable trace.

This is not an evidence layer. It is an *observability weight* applied to the existing
evidence field, so it can only re-allocate evidence, never create it. That property is
what makes the mandatory controls below decisive rather than decorative.

## 2. Data (free, official, already hash-verified in this repository)

| Item | Source | Status |
| --- | --- | --- |
| SGMC Nevada package `NV.zip` (69,056,094 B, sha256 `3b333ac025e59aae…`) | <https://mrdata.usgs.gov/geology/state/> (public domain) | downloaded and SHA-verified by `scripts/fetch_external_layers.py`; receipt in `data/external/external_receipt.json` |
| SGMC California package `CA.zip` (24,977,406 B, sha256 `78765ba4428df9f2…`) | same | same |
| Competition grid (labels + template) | hash-pinned owner mirror, SHA-verified each run | `data/raw/{labels,sample_submission}.tif` |

Derived layers produced by the extended fetch script (committed, auditable):

* `data/external/derived_sgmc_cover_100m_u8.tif` — cover classes 0–4, `255` = not
  mapped by SGMC or outside the footprint.
* `data/external/derived_sgmc_concealed_100m_u8.tif` — the `concealed / inferred /
  queried` subset of the same structure linework (mapping-effort signal inside the
  fault layer itself; secondary arm only).

## 3. Frozen class mapping (`src/gemsdoe30/concealment.py`, unit-tested)

| Class | Meaning | Weight at γ = 1 |
| --- | --- | --- |
| 0 | pre-Cenozoic bedrock, undivided, or unmapped | 1.00 |
| 1 | Mesozoic–Paleogene indurated units | 1.25 |
| 2 | Neogene/Tertiary basin fill and volcanics | 1.50 |
| 3 | Quaternary surficial cover | 1.75 |
| 4 | playa / lake bed / evaporite / salt flat | 2.00 |

Age class comes from the SGMC map-unit `AGE` string; any unit text naming a playa,
lake bed, evaporite or salt flat escalates the unit to class 4 regardless of age. The
weight is `1 + γ·class/4` with **γ = 1.0 primary** (γ = 0.5 reported as a labelled
sensitivity, never gating). A layer whose class mapping is degenerate (numeric age
code, or > 98 % class 0) is refused by the fetch script rather than published.

## 4. Frame

Identical to the registered emitter holdout so the arms are directly comparable:
`holdout.split_components(labels == 1, seed=31, stratify=32)` splits whole 8-connected
catalogue components into a stand-in *hidden* half and a *known* half; `known` is
masked out of every metric term exactly as the organizer masks the catalogue;
`fp_weight_field(hidden, known)` is computed once and used by every arm and fold; four
spatial quadrant blocks are scored separately and pooled.

Emitter: **EDGE** (`gemsdoe30.emitter_opt.edge_select`) with the same normalisation as
the registered emitter runs (`truth_mass = 80,000`) and **count-matched** emission of
exactly `N = 80,000` dots per arm (`mask_from_order(order, keep=min(N, accepted))`;
any arm with `accepted < N` is reported as short and cannot pass the gate).

## 5. Arms (each arm = one field × one weight, same emitter, same N)

| Arm | Belief field | Weight |
| --- | --- | --- |
| `hybrid` | `geometric_mean(proximity, external)` | none (baseline evidence) |
| `proximity` | `proximity_belief(known)` | none |
| `proximity_cover` | proximity | `cover_weight(cover, γ)` |
| `hybrid_cover` | hybrid | `cover_weight(cover, γ)` |
| `hybrid_matched_control` | hybrid | `cover_weight(matched_control, γ)` |
| `external_concealed` (secondary) | external belief with the concealed-linework layer added | none |

`matched_control` is the decisive control: for each cover class *c* = 1…4 it draws the
same number of cells as the true class-*c* mask from the *bedrock* pool (class 0) with
a **matched distance-to-known profile** (`holdout.distance_matched_draw`, 10 quantile
bins, seeded RNG), then assigns class *c* to the drawn cells. The control therefore
carries the same class histogram *and* the same distance-to-mapped-fault distribution
as the true prior, but no map-unit information. If `hybrid_cover` only wins because
concealed substrate happens to lie far from the catalogue, this arm reproduces the
win and the hypothesis fails.

Realised distance distributions (true vs control, per class) are recorded in the run
JSON as the control's integrity check.

## 6. Gate (frozen)

Primary comparison: `hybrid_cover` (γ = 1) pooled cross-validated DTI must satisfy

1. **≥ +0.005** over the best of `hybrid`, `proximity`, `proximity_cover`,
   `hybrid_matched_control` in the same run, **and**
2. **positive in ≥ 3 of 4** spatial folds against that same best comparator, **and**
3. `accepted ≥ N` for both `hybrid_cover` and the comparator (count-matched).

If the gate fails, H-34-01 is recorded as **falsified on this frame**, no submission
slot is spent, and the result is reported with the same prominence as a pass. If the
gate passes, a fresh-draw confirmation is required before any promotion: the same two
arms re-run with `split_components` seed 41 (fresh hidden/known split) and a fresh
control RNG, and the gate must hold again.

## 7. Standing rules restated

* No candidate may consume a weekly submission slot unless it beats the current
  holdout best; H-34-01 starting from ΔDTI ≈ +0.002…+0.015 is a *planning prior*, not
  a result.
* The catalogue split is a proxy frame, not the organizer's hidden truth; absolute
  values are not competition scores.
* Absolute DTI values from this script are comparable only within the run (same frame,
  same folds, same emitter, same N).
* Result files: `docs/research/h34-01-concealment-holdout.json` (+ `.md` verdict) and,
  for any confirmation run, `…-confirmation.json`. No artifact from this experiment is
  site-linked or promoted without a separate promotion record.
