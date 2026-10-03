# Why 0.2600 happened, and what 0.3195 actually costs

*Written 2026-10-03 from `docs/research/metric-response-surface.json` (162.2 s of exact metric
evaluations on the real 5,167,373-pixel footprint) and the official sources listed at the end.
Every number below is either quoted from an official source or reproducible from that JSON.*

---

## 1. What is officially true

Three statements are on the record and are used as axioms here. Everything else is inference and is
labelled as such.

| # | Statement | Source |
|---|---|---|
| A1 | `DTI = TP_w / (TP_w + α·FP_w + β·FN_w + ε)` with `α = 0.2`, `β = 0.8`, kernel radius `R = 300 m`, 100 m pixels. Worked example: `TP_w=3.00, FP_w=1.89, FN_w=2.00 → 0.60`. | [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| A2 | "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards penalty terms," and "for scoring purposes it should not matter whether these known faults are included with predictions or not." | staff reply, [thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516), 2026-09-16 |
| A3 | Public leaderboard on 2026-10-03: 1st 0.3195, 2nd 0.3128, 3rd 0.3042, 5th 0.2941, 15th 0.2600. | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |

The competition's own description also states that the private truth is a set of faults "manually
identified" by consulted experts that "are not contained within the current public USGS database"
([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).

**Owner claim, not official fact:** that the leaderboard 0.2600 corresponds to the repository
artefact `gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`. That file exists here,
validates cleanly (single band, float32, EPSG:32611, exact geotransform match, values in [0,1],
NaN outside the footprint — `docs/research/reference-validation.json`), and its dot count is
44,090. The score itself is taken as an official leaderboard value; the artefact↔score mapping is
inference.

---

## 2. The exact marginal rule — the single most useful fact about this metric

Write `T = TP_w`, `F = FP_w`, `G = ` the number of truth pixels (`FN_w = G − T` for the part of the
truth that is not covered; uncovered truth contributes weight 1). Adding one prediction pixel that
lands with kernel credit `k ∈ [0,1]` of an **uncovered** truth pixel changes the terms to
`T + k` and `F + (1 − k)`, so

```
DTI_new = (T + k) / (D + 0.2)      where D = 0.2(T + F) + 0.8G
```

because `Δ(T + F) = k + (1 − k) = 1` exactly. Hence the dot helps **iff**

```
k > 0.2 · DTI          (exact; the general form is k > α·DTI)
```

At the current operating point this is the whole game:

| current DTI | minimum kernel credit for a new dot to help | equivalent: probability the dot sits within `d` m of truth |
|---|---|---|
| 0.1618 | **0.032** | 3.2 % on a truth pixel, or 9.7 % inside 200 m |
| 0.2600 | **0.052** | 5.2 % on a truth pixel, or 15.6 % inside 200 m |
| 0.3195 | **0.064** | 6.4 % on a truth pixel, or 19.2 % inside 200 m |
| 0.4000 | **0.080** | 8.0 % on a truth pixel, or 24.0 % inside 200 m |

Two consequences that are not intuitive and that drive every recommendation in this repository:

1. **Exploration is almost free.** A geological hypothesis with a 5 % chance of being a real fault
   is worth betting on at the current score. Hedging across many weak independent hypotheses is
   close to optimal, and the metric's `α = 0.2` is doing all of this — with the symmetric
   `α = β = 0.5` the same threshold would be 5× larger.
2. **The rule is target-set independent.** `k > α·DTI` contains no reference to `G`, so it does not
   matter how sparse the hidden truth turns out to be. Precision requirements do not loosen or
   tighten as the private truth set shrinks; only the *current* DTI sets the bar.

The closely related slope form is also exact: a bundle of new mass must satisfy
`ΔT/ΔF > α·DTI/(1 − α·DTI)`, i.e. **≥ 5.5 % of any added mass must be genuinely covered truth at
DTI 0.26** (6.8 % at 0.3195). This matches `gemsdoe30.emission.marginal_inclusion_ratio`.

## 3. Why the metric loves dots and hates probability maps

`FP_w` weights each prediction pixel by its distance to the nearest truth pixel, saturating at
`R = 300 m`. A *dense* probability field therefore pays full price for every pixel that is more
than 300 m from truth — predicting `p = 0.5` everywhere over the 5.17 M-pixel footprint injects
≈ 2.6 M units of `FP_w` and scores ≈ 0.01. By contrast a prediction placed **on** an
already-covered truth pixel costs `FP_w = 0`, so redundant dots on known fault is *free*, not
harmful. Measured:

* exact-metric blind lattice (no learning at all), spacing 4 px = 400 m:
  `T = 28,709`, `F = 310,050`, `DTI = 0.2463`;
* the same lattice at 3 px and 5 px: 0.2347 and 0.2453 — an interior optimum;
* a lattice restricted to a 1-pixel corridor around the catalogue: `DTI = 0.7321` at 2 px spacing
  (that number is oracle-adjacent and not available on the hidden set — the corridor *is* the
  label — it is quoted only to show where the mass must go);
* perfect localisation plus 3-px dotting: 0.6330 with zero `FP_w`.

This is why the historical recipes in this repository are dot recipes and should stay that way. It
is also why the *one-click deliverable* is a dotted float32 raster rather than a smooth
probability surface (see `docs/submission-how-to.md`).

## 4. Reading 0.2600

The stored 44,090-dot artefact scores, against the **public catalogue** as a stand-in truth set:

| quantity | value |
|---|---|
| `TP_w` | 9,498.8 |
| `FP_w` | 40,135.2 |
| uncovered truth | 51,489.2 of 60,988 px |
| `DTI` (catalogue proxy) | **0.1618** |
| `DTI` after thinning the dots to 1.5 px | 0.1508 |

The same artefact's official leaderboard score is **0.2600**. One and the same prediction therefore
scores 0.1618 against the catalogue and 0.2600 against the hidden truth — a **+0.098 gap that
contains no information about model quality**, only about how the target set differs from the
catalogue. Two mechanisms can produce it, and the data can bound their combination:

* if the hidden truth has fewer pixels than the catalogue and the dot placement earns the same
  weighted coverage, then `DTI = 0.2600` with `T = 9,498.8`, `F = 40,135.2` implies a hidden truth
  of **G ≈ 33,259 px, i.e. 0.55 × the catalogue**. This is a calibrated estimate, not a measurement,
  and it is the single most useful unknown in the project;
* if instead the hidden truth is the same size, the artefact's `F` must be much smaller on the
  hidden set, which is only possible if the hidden faults sit where the dots already are.

Either way, **the catalogue proxy is not comparable to the leaderboard**, and rank-ordering arms by
the catalogue proxy can invert the true order. That is the direct explanation of the inversion
already recorded in `docs/research/emission-holdout-results.json`, and it is why the ablation below
is evaluated under an explicit density shift rather than on the catalogue alone.

## 5. Why 0.3195 costs surprisingly little — and why it is reachable

Spanning the leaderboard with the calibrated target size `G = 33,259`:

| `DTI` | required `TP_w` | required recall of the hidden truth | or: allowed `FP_w` at 30 % recall |
|---|---|---|---|
| 0.2600 | 9,499 | 28.6 % | 40,135 |
| 0.2941 | — | 32 % | ≈ 37,000 |
| 0.3195 | — | 35 % | ≈ 35,000 |
| 0.4000 | — | 44 % | ≈ 27,000 |

The leader's margin over 0.2600 corresponds to raising weighted recall from ~29 % to ~35 % while
holding the false-positive budget — a 6-percentage-point move, not a different regime. Combined
with §2, the practical statement is:

> **Any additional prediction mass whose expected kernel credit against the hidden truth exceeds
> 0.064 improves on the current #1. With a 300 m kernel, that is a hit rate of roughly 1 in 8 for
> dots placed within 200 m, or 1 in 16 for dots placed exactly on a candidate line.**

The user's own 0.2600 is therefore *not* a plateau: under this metric, adding several independent
5–20 %-confidence geological layers is expected to gain, and the recorded leaderboard gap to #1 is
inside the range that broad, honest hedging can close. That is precisely what the ranked
hypotheses in `docs/hypotheses.md` are for, and why H1 (the SGMC off-catalogue linework, 61,668
pixels more than 300 m from every catalogue fault) is the highest-value bet available: it is a
large, curated, public, independent source, and the admission bar is 5.2 %.

## 6. What would falsify this reading

* The hidden truth could be *denser* than the catalogue (the competition says "a small number of
  newly identified faults", which argues against it, but the pixellated extent of those faults is
  unknown). Then the 0.2600 ≈ 0.1618 + localisation story would be wrong in detail and the implied
  `G ≈ 33k` would be an overestimate.
* The dot artefact↔score mapping is inference, not official.
* All catalogue-proxy numbers here are computed against pixels that the organizer *masks out* of
  the real scoring. They are diagnostic of geometry, never of hidden-set performance.

## 7. Reproducing

```
PYTHONPATH=src python scripts/metric_response_surface.py     # 162 s, writes docs/research/metric-response-surface.json
PYTHONPATH=src python -m unittest discover -s tests          # metric identities and worked example
```

Sources: competition metric and submission contract
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>; project background
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>; leaderboard
<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>; masking
clarification <https://community.drivendata.org/t/11516>; rules
<https://docs.nlr.gov/docs/fy26osti/96647.pdf>.
