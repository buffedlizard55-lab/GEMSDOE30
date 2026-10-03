# Why the D2.8 "dotted" raster scored what it did — and what it takes to beat 0.3195

**Session:** 2026-10-03 · **Author:** autonomous research session · **Status:** analysis + one real
holdout experiment; **no score is claimed for any file in this repository**, and no competition
slot was used.

Everything below separates three evidence classes explicitly:

* **[OFFICIAL]** — quoted from a DrivenData/NLR/USGS page that was fetched and read in this session.
* **[MEASURED]** — computed in this checkout from local bytes; reproducible with the listed script.
* **[CLAIM]** — user- or owner-reported values that no organizer receipt authenticates in this checkout.

---

## 1. What is officially true about the score

**[OFFICIAL]** The problem description defines the metric exactly
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>, fetched 2026-10-03):

```
TPw = Σ_{g∈G} max_{x: d(x,g) ≤ R} p(x)·k(d(x,g))
FPw = Σ_{x: p(x)>0} p(x)·[1 − max_{g∈G} k(d(x,g))]
FNw = Σ_{g∈G} [1 − max_{x: d(x,g) ≤ R} p(x)·k(d(x,g))]
DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw + ε),    k(d) = max(1 − d/R, 0),  R = 300 m,  α = 0.2, β = 0.8
```

The same page states the test set is a **private set of new faults that experts labelled before the
competition** and that the Final Round re-scores the same submissions against an expanded label set.

**[OFFICIAL]** DrivenData staff answered a direct question about what happens to the catalogue
(<https://community.drivendata.org/t/11516>, staff post 2026-09-16, fetched 2026-10-03):

> "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation, so they
> do not count towards penalty terms." … "Re-evaluation will also mask/exclude the existing
> USGS/INGENIOUS faults."

**[OFFICIAL]** And what a "new fault" is (<https://community.drivendata.org/t/11536>, staff post 2026-09-23):

> "'new fault' means 'any fault pixel not already captured by USGS/INGENIOUS' and can include newly
> mapped geometry of an existing fault system."

**[OFFICIAL]** The organizers declined to characterise the test faults
(<https://community.drivendata.org/t/11527>, staff post 2026-09-23): "We're not sharing details about
the data sources, fault types, or coverage behind the test faults beyond what's in the problem
description." They added that the Final Round test set is "updated by expert review of all Phase 1
submissions".

Three consequences follow immediately, and they are the core of this analysis:

1. **Predicting the catalogue is free but worthless.** Catalogue pixels are masked, so they can
   neither earn credit nor cost false-positive mass. (This corrects a natural misreading of the
   Hedge-v2 result: including the catalogue did not *hurt*; the surrounding emission did.)
2. **The training target and the reward target are different pixel sets.** A model trained to
   reproduce the catalogue is trained on exactly the pixels the metric ignores.
3. **Extensions, splays and parallel strands of mapped fault zones are legitimate, rewardable
   targets** — which makes the neighbourhood of the catalogue an *enriched* prior region, not a
   forbidden one.

## 2. What the 0.26 file actually is — [MEASURED]

Script: `python scripts/analyze_emission_anatomy.py --proxy` → `docs/research/emission-anatomy.json`.
All three owner rasters below were restored through the SHA-256-pinned owner mirrors and re-hashed
locally; the committed `docs/downloads/` copy of D2.8 is byte-identical to its pin
`91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`.

| Property | base `gems19-h19-5-…` | `dotted-…-d1-5` | `dotted-…-d2-8` |
| --- | ---: | ---: | ---: |
| **[CLAIM]** reported score (unverified) | 0.1922 | 0.2477 | 0.2600 |
| positive pixels inside footprint | 121,131 | 60,069 | 44,090 |
| distinct values | {0, 1} | {0, 1} | {0, 1} |
| connected components / mean size **[MEASURED]** | 26,645 / 4.55 px | 60,069 / 1.0 px | 44,090 / 1.0 px |
| nearest-neighbour spacing (median) | 1 px | 2.24 px | **3.0 px** |
| subset of the base raster? | — | **yes (all 60,069)** | **yes (all 44,090)** |
| pixels within 300 m of the catalogue | 19.95 % | 19.87 % | 19.52 % |
| catalogue-proxy DTI **[MEASURED]** | 0.1339 | **0.1539** | 0.1510 |

Four measured facts matter:

* The emission is a **binary mask**, not a probability field: two distinct values, `0` and `1`,
  everything else NaN outside the footprint. Binarity is theoretically optimal on a fixed support
  (scaling every value by λ<1 scales TPw and FPw together and strictly lowers the ratio), so this is
  not a defect.
* The "dotted" rasters are **strict subsets of the same base raster**, i.e. the reported score
  sequence is a controlled *thinning sweep* of one underlying map.
* The 300 m dilation of the catalogue covers **8.6 %** of the footprint, while ~19.5 % of these
  emissions sit inside it — a **2.3× enrichment**. That is the measurable footprint of the
  "extensions and splays count" rule.
* On the catalogue-proxy metric, the ordering of the two thinned variants is **inverted** relative to
  the reported ordering (0.1539 vs 0.1510). The proxy therefore cannot rank candidates — which is
  itself the explanation of why the owner's thinning direction is not one a catalogue-tuned pipeline
  would ever choose.

## 3. The algebra that explains the whole leaderboard

Substituting `FNw = G − TPw` (with `G` the hidden truth pixel count) gives an exact simplification
that the official page does not spell out:

```
DTI = A / (0.2·(A + F) + 0.8·G)          A = TPw,  F = FPw,  G = |truth|
```

Two exact consequences:

**(i) The marginal rule.** Adding emission mass `dA` at expected false-positive cost `dF` improves
the score iff

```
dA / dF  >  λ(s)  =  0.2·s / (1 − 0.2·s).
```

At the reported operating points: λ = 0.040 (s = 0.1922), 0.052 (0.2477), **0.055 (0.2600)**,
0.068 (0.3195). *A pixel is worth emitting whenever its expected credit exceeds ~5 % of its expected
false-positive weight.* False-positive mass is not precious; missed credit is.

**(ii) The coverage requirement.** Writing `c = A/G` (weighted coverage of the hidden truth) and
`ρ = F/G` (false-positive mass relative to the truth set), the score is

```
DTI = c / (0.2·c + 0.2·ρ + 0.8)
```

which inverts to a *target table* — the single most useful number in this project:

| target DTI | required coverage c at ρ = 0 | ρ = 0.5 | ρ = 1 | ρ = 2 | ρ = 5 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.2600 (reported D2.8) | 21.9 % | 24.7 % | 27.4 % | 32.9 % | 49.4 % |
| **0.3195 (current public leader)** | **27.3 %** | 30.7 % | 34.1 % | 41.0 % | 61.4 % |
| 0.40 | 34.8 % | 39.1 % | 43.5 % | 52.2 % | 78.3 % |
| 0.50 | 44.4 % | 50.0 % | 55.6 % | 66.7 % | 100 % |

(`c = 0.2·s·(ρ + 4) / (1 − 0.2·s)`, i.e. `c = f(ρ+4)` with `f = λ(s)/2`; verify with
`python -c "print(0.2*0.26*5/0.948)"`.)

**This is the answer to "can we beat 0.3195?"** The public leaderboard's entire spread (0.19 → 0.32)
spans roughly **16 % to 27 % weighted coverage** of a hidden label set, at low false-positive mass.
The competition is not a precision contest; it is a **recall contest under a 300 m tolerance**, and
everybody — including the leader — is sitting far below half coverage. A submission that reached
50 % weighted coverage with negligible FP mass would score ≈ 0.56 (0.50 at ρ = 1) — roughly 75 % above
today's public leader.

## 4. Why "dotting" was the winning move so far

Under the metric, credit for a truth pixel is a **maximum**, never a sum. A dense line therefore pays
false-positive weight for pixels that add no credit: the second, third and fourth pixel across a
fault trace only compete with the first. Removing them (thinning to dots) *cannot* reduce `A` below
the best remaining credit, while it *does* reduce `F` — so `dA/dF` is exactly the quantity the
marginal rule compares against λ ≈ 0.055.

The measured sweep says precisely this: cutting 121,131 → 60,069 → 44,090 pixels is a sequence of
removals that the *reported* scores reward (+0.0555, then +0.0123). In the same family, the base
raster's 121,131 pixels earn 6,573 units of catalogue-proxy credit while paying 115,392 units of proxy
FP mass — a credit-to-mass ratio of **0.057**, the same order as λ at the reported operating points
(0.040–0.055). That is exactly the regime in which deleting redundant pixels is profitable. **The dots
were not magic; they were the first-order fix for a map whose precision per pixel was mediocre but
whose kernel-scale coverage was already decent.** (Note this is a mechanism explanation of the *reported* ordering, not evidence that
these exact bytes earned 0.2600 — see §6.)

## 5. The four levers that actually move the score

Ranked by expected effect on `c` (coverage) and `ρ` (FP mass):

| # | Lever | Mechanism | Status in this repo |
| --- | --- | --- | --- |
| 1 | **Cover the hidden trace, not the mapped one** — emit on extensions, splays, parallel strands and transfer zones of mapped fault zones, and wherever independent evidence (magnetics, radiometrics, 1 m LiDAR scarps, hydrology) shows a lineament the catalogue lacks. | Raises `c` at essentially zero penalty, because FP close to a truth pixel is nearly free (weight `1 − k(d)`). | New hypotheses registered in `docs/hypotheses.md`; the 2.3× catalogue enrichment is measured. |
| 2 | **Emission geometry tuned to `λ`, not to a fixed spacing** | A fixed 300 m dot spacing is arbitrary. The rule that follows from the algebra is "keep a pixel when its *extra* credit exceeds λ × its expected FP weight" — dense where belief is high, sparse where it is low, and automatically *thicker* where positional uncertainty is real. | Implemented as `gemsdoe30.emission.metric_optimal_emission` and measured on hidden spatial quadrants (`scripts/metric_emission_holdout.py`). |
| 3 | **Stop spending the model's capacity on masked pixels** | Catalogue pixels are free but worthless; the optimum trains for the *unmapped* population — this is a positive-unlabeled problem, not a binary segmentation problem. | Partially addressed: the emission experiment masks the known-fault domain; training-side PU remains the top open engineering item. |
| 4 | **False-positive mass discipline** | `ρ` enters the denominator with weight 0.2, and far-field pixels cost the full 1.0. Long low-confidence tails are pure loss. | Already exploited by the owner's thinning; the metric-optimal emitter handles it inside the greedy rule. |

## 6. Irregularities attached to this analysis (do not skip)

* **[CLAIM]/[OFFICIAL] conflict.** The user brief attributes 0.2600 to the D2.8 file; the owner's own
  GEMSDOE25 page calls that TIFF *unscored/not slot-approved*; the official leaderboard's 0.2600 row
  belongs to participant `wbg1` with no filename. No receipt, submission ID or hash-to-score
  crosswalk has been produced in this checkout. **The attribution remains unverified.**
* **[MEASURED] proxy inversion.** The catalogue-proxy ordering of the two thinned variants is the
  reverse of the reported ordering, so no catalogue-based holdout number in this repository may be
  used to rank candidates against the hidden test set.
* **The base map is not the bottleneck at the margin; coverage is.** Because λ is small, the dominant
  error is *under-emission where faults plausibly exist*, and the leaderboard's tight 0.19–0.32 band
  is consistent with the whole field operating in a low-coverage regime rather than a
  false-positive-limited one.

## 7. Reproducing every number here

```bash
# local raster forensics, metric algebra, feasible regions, proxy inversion
python scripts/analyze_emission_anatomy.py --proxy

# the emitted-pixel/hidden-truth consistency grid per raster
python -c "import json;print(json.dumps(json.load(open('docs/research/emission-anatomy.json'))['rasters'],indent=1)[:2000])"

# the experiment that tests the marginal-rule emitter against thinning controls
python scripts/metric_emission_holdout.py --raw-dir data
```

Known limitation of §3's target table: `c` and `ρ` are defined against the **hidden** truth set, which
no participant can measure. The table is therefore a *design target and a diagnostic*, not a
measurable score predictor, and the only instrument available locally for ranking methods remains the
masked, spatially-blocked catalogue proxy — which §2 shows is biased.
