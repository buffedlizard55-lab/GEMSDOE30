# Preregistration — metric-algebra emission on hidden spatial quadrants

**Registered:** 2026-10-03, before the experiment was executed. **Script:**
`scripts/metric_emission_holdout.py`. **Data:** prepared owner-mirror competition grid
(5,167,373 valid pixels, 60,988 catalogue positives; SHA-256 pins in `docs/research/mirror-pins.json`).
Owner mirrors are integrity-checked but **not organizer-authenticated**.

## Why a new design is needed

The registered 2026-10-03 emission pilot (`scripts/emission_holdout.py`) compared
thinning rules **at matched emitted-pixel counts** (11,025 per fold). The published
index is

```
DTI = A / (0.2*(A + F) + 0.8*G)        A = TP_w, F = FP_w, G = truth pixels
```

so the emitted count is a free decision variable, not a constraint. Matching counts
across arms removes exactly the dimension along which a marginal-rule emitter can win,
and can therefore produce a null result about the mechanism the pilot was testing.
This is recorded as a design defect of the earlier experiment, discovered in Pass 2
review of this session.

## Hypothesis (falsifiable)

**H1.** On hidden spatial quadrants of the real grid, a rule that keeps a pixel only
when its expected marginal credit exceeds `lambda * cost` with
`lambda = alpha*s/(1 - alpha*s)` — evaluated on a *soft* belief surface with the
metric's maximum-credit rule — reaches a higher proxy DTI than (a) a dense threshold
of the same surface and (b) uniform Poisson-disk thinning of the same surface, when
each rule is allowed to choose its own operating point.

**H2 (mechanism, secondary).** The optimum dot spacing is *not* a constant. It is
predicted to shrink where the belief surface is confident and widen where it is not,
so a fixed-radius thinning sweep should be beaten by the adaptive rule at a matched
surface. H2 is a mechanism statement; the gate below is applied to H1.

## Design

* Four fixed spatial quadrants; the model is fit on the other three quadrants with a
  300 m buffer removed from training around the held-out block.
* Inside the held-out block, catalogue fault pixels are the **stand-in truth**
  (the organizer's hidden truth is an expert-labelled set *absent* from the catalogue —
  this proxy can reward catalogue-like predictions and is a known limitation).
* Known-fault pixels outside the block are masked, mirroring the official rule that
  USGS/INGENIOUS pixels are excluded from evaluation.
* Rules: `dense`, `uniform` (Poisson disk), `adaptive` (confidence-scaled disk), and
  `metric` (greedy marginal rule). Parameters: 6 belief quantiles × 7 radii for the
  disk rules; the metric rule is swept over the same 6 belief cuts.
* **Parameter selection is leave-one-fold-out**: for fold *f* the parameter is chosen
  on the pooled other three folds and reported on fold *f*. No fold is scored at a
  parameter tuned on itself. Oracle maxima are reported separately and are not
  selectable results.
* Pooling sums the sufficient statistics of the buffered blocks; this omits 300 m
  interactions across block seams and is **not** an official score.

## Gate (registered before running)

A family is **promoted** only if, at its leave-one-fold-out selected parameter:

1. its pooled cross-validated proxy DTI exceeds **both** the `dense` and `uniform`
   families by **≥ 0.005 absolute**; **and**
2. the fold-level difference against `uniform` has the same sign in **≥ 3 of 4 folds**.

Otherwise the family is **not promoted**, no competition slot is proposed, and the
result is recorded as a negative finding. No post-hoc gate changes.

## Known limitations (registered in advance)

* Stand-in truth is the catalogue, not the organizer's new-fault set.
* Only one model family and one seed per fold; fold-level noise is not estimated.
* FP mass is counted **inside the held-out block only**; the official metric sums FP
  over the whole unmasked footprint. Emission outside the block is therefore not
  penalised here. The report records emitted mass so the difference is visible.
* CPU only; this is a pointwise/GBM surface, not a full-capacity spatial model.
