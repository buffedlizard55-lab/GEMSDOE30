# Does the 300 m geometry term change near-miss behaviour? — measured verdict

**Answer: it changes where the mass goes, but not in the intended direction. The boundary
term is rejected. No submission slot is spent on it.**

Protocol: eight checkpoints, one per (fold, loss arm). Identical seed (30), architecture
(`SmallUNet`, 24 base channels), 6 epochs × 100 steps × batch 4 × 96 px patches, AdamW,
`lr 1e-3`; **only the loss differs**. Folds are the four raster quadrants with a 300 m
training-exclusion buffer. Inference is strictly out-of-fold: the checkpoint for fold *f*
never saw quadrant *f*, and its prediction of quadrant *f* is what is scored. Artifacts:
`runs/oof/{regional,combined}-f{0..3}.npy` stitched into `{regional,combined}-oof.npy`
(sha256 `aae74138…9a4a2d` and `864a7097…6de773`); full evaluator output in
`runs/loss-ablation/holdout.json`.

The two arms are the registered pair from `docs/loss-design.md`: `regional` is the soft
Tversky/regional overlap term alone (`boundary_weight = 0`), and `combined` keeps that term
and adds `1 − DTI_soft` computed with the official triangular kernel on a real Euclidean
distance transform at the true 300 m radius (`boundary_weight = 0.5`, 30 px offset
neighbourhood). The boundary term *augments*, never replaces, the regional term.

## Primary result

| quantity | regional | combined | delta |
|---|---|---|---|
| pooled `TP_w` | 29,373.12 | 29,224.19 | −148.93 |
| pooled `FP_w` | 1,125,054.81 | 1,231,376.87 | **+106,322.06** |
| pooled `FN_w` | 31,614.88 | 31,763.81 | +148.93 |
| **pooled DTI (exact, full stitched OOF grid)** | **0.105026** | **0.097119** | **−0.007906** |

Per fold (quadrant-isolated diagnostic): `0.096263 → 0.087276` (−0.008988),
`0.120099 → 0.103162` (−0.016938), `0.141343 → 0.135866` (−0.005477),
`0.091622 → 0.100754` (+0.009132). **One of four folds is positive.**

The boundary arm loses ~0.008 of pooled DTI, and essentially all of the damage is an
**11 %-larger far-field false-positive mass** with a small *reduction* in true-positive
weight. That is the opposite of the hypothesis: a proximity-aware objective was expected to
trade distant mass for near mass, not to add distant mass on top of everything else.

## Near-miss profile (the specific thing the hypothesis was about)

Per-truth-pixel best-credit distance, complete stitched OOF grid, 60,988 held-out truth
pixels:

| best kernel credit distance | regional | combined |
|---|---|---|
| exact (0 m) | **48,491** | 47,964 |
| 100–200 m | **7,427** | 7,195 |
| 200–300 m | 5,070 | **5,829** |
| no credit (≥300 m) | 0 | 0 |

Prediction mass by distance to the nearest held-out truth pixel:

| distance band | regional mass | combined mass | weighted `FP_w` change |
|---|---|---|---|
| 0–100 m | 27,625.8 | 26,940.5 | 0 (kernel is 1 there) |
| 100–200 m | 76,646.8 | 74,945.2 | −629.4 |
| 200–300 m | 68,599.1 | 67,421.8 | −869.7 |
| ≥300 m | 1,044,121.1 | **1,151,942.3** | **+107,821.2** |

So the boundary arm does redistribute: it moves truth pixels out of the *exact* and
*100–200 m* bins into the *200–300 m* bin, and it moves prediction mass out of both near
bins. Read as a near-miss experiment:

* **credit gained in the 200–300 m "near miss" band**: 759 more truth pixels, worth at most
  759 × 1/3 ≈ 253 units of `TP_w` — and the pooled `TP_w` actually *fell* by 149, so even
  that is more than offset elsewhere;
* **cost paid in the far field**: +107,821 units of `FP_w`, worth 0.2 × 107,821 ≈ 21,564
  units of the DTI denominator.

The exchange rate is roughly **1 unit of new near-miss credit per 85 units of new distant
false-positive mass**, against a metric that prices them at 1 : 0.2.

## Why this happens (mechanism, not excuse)

`FP_w` is `Σ_x p(x)·(1 − max_g k(d(x,g)))`. On a 5.17 M-pixel footprint with a 60,988-pixel
truth set, the overwhelming majority of pixels are more than 300 m from any truth pixel, so
that sum is dominated by the far field and is *linear in total emitted mass*. A boundary
term built from the same kernel therefore produces a gradient that is nearly uniform
inward — it raises probability in regions the distance transform cannot distinguish, which
is most of the map. The regional exact-pixel term, by contrast, is silent off the trace and
lets the optimizer concentrate. Adding the geometry term to the regional term therefore
buys localisation only where the two disagree, and pays for it everywhere else.

This is a property of the metric, not of the implementation. It also explains the empirical
fact recorded in `docs/metric-response-surface.md`: the winning strategy under this metric
is *sparse, confident, well-placed mass*, and a dense probability field is penalised in
proportion to its area. A loss that pushes the model toward a smooth probability field is
misaligned with the scorer even when its individual terms look like the scorer.

## Cross-check under truth-set shift

The same two mosaics were re-scored under controlled shifts of the target set
(`docs/research/discovery-shift.json`, `scripts/discovery_shift_analysis.py`). The combined
arm loses in **every** realisation — full catalogue (−0.0079), 50 % density (−0.0047),
25 % (−0.0025), 10 % (−0.0010), 4 % (−0.0004), and 3 km-clustered truth (−0.0010). The gap
*shrinks* as the truth set gets sparser, which is consistent with the mechanism above: the
damage is concentrated in the dense-coverage regime, and it never reverses sign.

## Verdict and what would change it

* **Decision: `not promoted; no submission slot`** (recorded in `runs/loss-ablation/holdout.json`).
* The hypothesis is *falsified as stated*. A future variant that could still be right would
  have to bound the geometry term's influence to a neighbourhood of the label (e.g. a
  focal/hard-negative mining form that is zero beyond a few hundred metres) or apply it to
  a *sparsified* output rather than to a dense sigmoid field. Both are new hypotheses and
  would need their own pre-registration.
* The 300 m geometry should be applied at **emission** time, where it is exact and free,
  rather than at training time, where it is expensive and mis-specified. That is what the
  emitter chain does instead.
