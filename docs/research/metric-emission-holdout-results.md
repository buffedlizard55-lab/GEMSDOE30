# Metric-algebra emission holdout — registered result (2026-10-03)

**Gate outcome: no family promoted. The metric-greedy rule failed; uniform/adaptive Poissson-disk
thinning (the owner's "dotted" family) remains the best rule on this proxy.**

Full registered protocol: [`metric-emission-preregistration.md`](metric-emission-preregistration.md).
Raw output (all 312 rule evaluations, selection rows, oracle rows): committed as
[`metric-emission-holdout-results.json`](metric-emission-holdout-results.json) (copy of
`runs/metric-emission/report.json`; surfaces stay Git-ignored).

## Design in one paragraph

Four fixed spatial quadrants of the real prepared grid; for each fold a pointwise/GBM surface
(`emission_holdout.FeatureStack`, competition bands + local external layers) is fit on the other
three quadrants with a 300 m training-exclusion buffer, then evaluated inside the held-out block.
The block's catalogue pixels are the **stand-in truth**; the catalogue outside the block is masked,
mirroring the official rule that USGS/INGENIOUS pixels are excluded from evaluation. Every emission
rule chooses its **own** operating point (this is the difference from the earlier count-matched
pilot): `dense` = quantile threshold; `uniform` = Poisson-disk thinning at radius r after the
threshold; `adaptive` = confidence-scaled Poisson-disk thinning; `metric` = greedy marginal
emission using `config.credit` (expected credit) versus `1 - prod(1 - belief*k)` (weighted FP cost)
with λ ≈ 0.055. Parameter selection is **leave-one-fold-out**: fold *f* is scored at the parameter
chosen on the pooled other three folds. Pooling sums the four blocks' sufficient statistics and
therefore omits cross-seam 300 m interactions — it is a proxy, never an official score.

## Pooled cross-validated result (leave-one-fold-out)

| Family | Pooled TPw | Pooled FPw | Emitted px | **Pooled proxy DTI** |
| --- | ---: | ---: | ---: | ---: |
| dense | 19,821.70 | 472,794.23 | 516,739 | 0.13455 |
| metric (greedy) | 18,657.94 | 438,119.88 | 480,000 | 0.13313 |
| uniform (Poisson disk) | 13,397.11 | 101,338.92 | 110,721 | 0.18675 |
| adaptive (confidence-scaled disk) | 12,942.51 | 85,011.70 | 93,390 | **0.18927** |

Gate (registered before running): a family is promoted only if its pooled cross-validated DTI
exceeds **both** `dense` and `uniform` by **≥ 0.005 absolute**, and its fold-level difference
against `uniform` has the same sign in **≥ 3 of 4 folds**.

* `metric` − `uniform` = **−0.0536** → fails (and fails the same-sign condition: `metric` is below
  `uniform` in every fold).
* `metric` − `dense` = **−0.0014** → fails.
* `adaptive` − `uniform` = **+0.0025** → positive but below the +0.005 threshold → not promoted.

Selected parameters (leave-one-fold-out) and credit per emitted pixel:

| Fold | dense | metric | uniform | adaptive |
| ---: | --- | --- | --- | --- |
| 0 | q0.90, 0.11976, 0.0344/px | q0.90, 0.11161, 0.0433/px | q0.95 r3, 0.12270, 0.1631/px | q0.95 r5, 0.12761, 0.1295/px |
| 1 | q0.90, 0.12186, 0.0323/px | q0.90, 0.12163, 0.0335/px | q0.95 r3, 0.18647, 0.1416/px | q0.95 r5, 0.18689, 0.1242/px |
| 2 | q0.90, 0.17273, 0.0553/px | q0.90, 0.15475, 0.0388/px | q0.95 r2, 0.24713, 0.1046/px | q0.95 r5, 0.26635, 0.1684/px |
| 3 | q0.90, 0.17035, 0.0490/px | q0.90, 0.15703, 0.0399/px | q0.95 r2, 0.24760, 0.1019/px | q0.95 r5, 0.26601, 0.1404/px |

## Why the metric rule failed — mechanism, not just a number

The greedy rule was **truncated by the candidate-pool cap, not by its own stopping criterion**: it
emitted exactly the 120,000-pixel pool limit in every fold (480,000 total) while earning only
0.033–0.043 credit per emitted pixel. Uniform thinning emitted 3–6× fewer pixels at 2.4–4.7× the
credit per pixel. In other words, on this belief surface the estimated marginal credit exceeded
λ ≈ 0.055 × cost for far more than 120k pixels per fold — the surface is too optimistic about the
credit it will actually earn against the sparse catalogue truth. The metric's FP cost is paid by
*every* emitted pixel (`1 − max_g k(d)`), so over-emission is punished quadratically in the
denominator: pool-capped emission buys a large TP numerator at a larger FP cost.

This is consistent with the earlier count-matched pilot (adaptive ≈ uniform, all arms failing their
+0.005 gate) and with the owner's own evidence: their best-scoring artifacts are **sparse dotted
masks** (D2.8, 44,090 dots, median nearest-neighbour spacing 3.0 px ≈ the 300 m kernel radius;
D1.5, 60,069 dots at 2.24 px) while the dense masks score far lower. The proxy ordering
(`adaptive` > `uniform` > `dense` > `metric`) again matches "thin, don't flood".

## Deliverable built from the OOF surface (un-promoted)

The four fold surfaces were stitched block-wise into a complete out-of-fold grid (every pixel predicted by a model that never saw its quadrant; zero coverage gaps over the 5,167,373 valid pixels) and emitted with the adaptive rule (radius 5 px, gamma = 1.0, candidate pool 480,000) that the protocol selected in all four leave-one-fold-out folds. The result (90,358 dots; median nearest-neighbour spacing 2.83 px; 17.7 % of dots within 300 m of the catalogue versus an 8.6 % base rate) was written with `scripts/build_submission.py` to `GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13.tif` and passes all 11 local format checks. Because the adaptive family missed the frozen +0.005 gate against uniform (+0.0025), this file is **not promoted**; it ships with that statement in its manifest note and on the site. Array hash `be95b587…`, TIFF SHA-256 `f5d137b9…`.

## What this does and does not show

* **Shows:** with the real 300 m metric algebra evaluated on real out-of-fold data, a
  marginal-rule greedy emitter is *worse* than simple thinning; the earlier pilot's null result is
  not an artifact of its count-matched design, and the adaptive rule's small edge over uniform
  (+0.0025) is below the preregistered threshold.
* **Does not show:** anything about hidden expert labels or the leaderboard, and it does not test
  the metric rule on a *calibrated* surface. The belief surface here is a pointwise GBM, not a
  converged U-Net; miscalibration is the leading explanation for the greedy's over-emission, and a
  calibration layer (or a cap tied to a target FP budget instead of a pool cap) is the natural
  follow-up before declaring the marginal rule dead.
* Registered limitations stand: stand-in truth is the catalogue (which the official metric masks),
  one model family and seed per fold, FP mass counted inside the held-out block only, CPU-only
  pointwise surface rather than a spatial model.

## Consequence for the project

No emission family is promoted, so no candidate file is built from this line and no submission slot
is proposed. The dotted *uniform/adaptive* family keeps its status as the best-supported emission
strategy, and the remaining work is (a) re-running the greedy rule against a calibrated surface or
an explicit FP budget, and (b) the fresh-seed confirmation of the paired regional-vs-boundary loss
result in [`loss-ablation-holdout.md`](loss-ablation-holdout.md). **Update: (b) has since completed —
seed 31 gave pooled ΔDTI +0.0001 with only 2/4 folds positive, so the boundary loss is not promoted
either; the near-miss behavioural effect did reproduce (partial-credit truth 1,889 → 724).**
