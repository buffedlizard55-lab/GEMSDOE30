# Paired regional-vs-boundary loss ablation on real data (2026-10-03)

**Status: ran twice (seed 30 screen, seed 31 fresh-seed confirmation). The screen did not
replicate: the fresh seed gives pooled ΔDTI ≈ +0.0001 with only 2/4 folds positive, against a
required +3/4. The geometry term's behavioural effect on near-misses *did* replicate; its
proxy-DTI benefit did not. Verdict: not promoted, no candidate file, no submission slot.**

Raw results are committed as [`loss-ablation-holdout.json`](loss-ablation-holdout.json)
(seed-30 screen, copy of `runs/loss-ablation/holdout.json`) and
[`loss-ablation-holdout-seed31.json`](loss-ablation-holdout-seed31.json) (fresh-seed
confirmation, copy of `runs/loss-ablation/seed31/holdout.json`); the prediction arrays stay out of
Git.

## What was run

The question this experiment answers is the one the project brief asks: does a loss shaped like the
competition metric's own geometry — a Euclidean distance-transform term built on the **actual 300 m
triangular kernel radius**, added to (not replacing) the regional soft-Tversky objective — change
which near-misses the model is willing to make, and does that help on a spatially held-out grid?

* Data: the prepared real grid — 3730×3292, EPSG:32611, 100 m, 5,167,373 valid pixels, 60,988
  catalogue-positive pixels (`data/processed/`, owner-mirror source, SHA-256 pinned; not
  organizer-authenticated).
* Folds: the four fixed spatial quadrants with a **300 m training-exclusion buffer** around each
  held-out block (`gemsdoe30.cv.spatial_quadrant_masks`).
* Arms: `--loss regional` (`boundary_weight = 0.0`, the control) versus `--loss combined`
  (`boundary_weight = 0.5`). Everything else — 2 epochs × 20 steps, batch 2, patch 192, AdamW
  lr 1e-3, base channels 24, same feature normalisation — is identical between arms and between
  seeds; only the seed changes between rounds (30 → 31). Both arms train fresh checkpoints, infer
  their own held-out quadrant, and are stitched into an OOF mosaic with provenance sidecars.
  `scripts/evaluate_loss_ablation.py` re-verifies every hash, recipe field, fold receipt and grid
  signature before scoring, and scores the **exact masked distance-weighted Tversky** on the
  stitched mosaic.
* **This is a screen budget.** 40 optimizer steps per fold is far below a converged training run
  (the default recipe is 5 × 100). The comparison is paired and internally valid, but the absolute
  numbers are not a model-quality claim.
* **The scored arrays are raw probability surfaces**, not thinned emission files. Both arms are
  treated identically, so the paired delta is the evidence; the absolute DTI (~0.06) is not a
  submission-representative number, because a real entry would be emitted/thresholded (the
  metric-emission line of work) rather than scored as a dense field.

## Round A — seed 30 screen, pooled exact full-grid OOF

| Arm | TPw | FPw | FNw | DTI |
| --- | ---: | ---: | ---: | ---: |
| regional control | 38,178.08 | 2,794,669.04 | 22,809.92 | **0.062042** |
| combined (boundary 0.5) | 39,800.42 | 2,826,124.69 | 21,187.58 | **0.063990** |

*Pooled ΔDTI = **+0.001948** (+3.14 % relative).* Per-fold quadrant-isolated diagnostics:
+0.000983 / +0.001983 / +0.003348 / −0.000898 → 3/4 folds positive.

Near-miss behaviour at seed 30 (truth pixels whose best credit comes from a partial-distance
prediction): partial-credit truth count **80 → 40**; exact-credit truth 60,908 → 60,948.

## Round B — fresh seed 31 confirmation (identical protocol, only the seed changed)

| Arm | TPw | FPw | FNw | DTI |
| --- | ---: | ---: | ---: | ---: |
| regional control | 37,480.91 | 2,808,022.84 | 23,507.09 | **0.060659** |
| combined (boundary 0.5) | 36,464.39 | 2,719,570.96 | 24,523.61 | **0.060774** |

*Pooled ΔDTI = **+0.000115** (+0.19 % relative) — eighteen times smaller than the screen, and the
sign flips within folds.* Per-fold quadrant-isolated diagnostics:

| Fold | Held-out truth px | Regional | Combined | Δ |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 29,319 | 0.063576 | 0.062992 | **−0.000584** |
| 1 | 12,596 | 0.048487 | 0.047032 | **−0.001455** |
| 2 | 9,473 | 0.072023 | 0.073179 | **+0.001156** |
| 3 | 9,600 | 0.065094 | 0.067056 | **+0.001962** |

2 of 4 folds positive, against the 3/4 required by the promotion rule. Note folds 0 and 3 change
sign relative to the seed-30 screen, which is what a noise-dominated effect looks like at this
budget.

Near-miss behaviour at seed 31 (complete OOF grid):

| Arm | exact (0 m) | 0–100 m | 100–200 m | 200–300 m | no credit |
| --- | ---: | ---: | ---: | ---: | ---: |
| regional | 59,099 | 0 | 1,175 | 714 | 0 |
| combined | 60,264 | 0 | 583 | 141 | 0 |

Partial-distance-only truth coverage falls **1,889 → 724 (−62 %)**, i.e. the near-miss conversion
the brief predicted *replicates* at the fresh seed: the combined objective keeps moving predictions
onto exact pixels and off partial credit. False-positive probability mass also drops in every
band (100–200 m: 108,125 → 105,622; 200–300 m: 103,983 → 101,624; ≥300 m: 2,687,973 → 2,602,228),
with the proportion of mass beyond 300 m essentially unchanged (~91.5 % → ~91.4 %).

## Verdict

* **The behavioural claim is supported:** adding the 300 m boundary term to the regional loss
  changes which near-misses the model is willing to make — consistently across both seeds it
  converts partial-distance truth coverage into exact-pixel coverage and reduces near-miss-only
  truth pixels (seed 30: 80 → 40; seed 31: 1,889 → 724).
* **The utility claim is not supported:** at the screen budget, the same term does *not* reliably
  raise the pooled catalogue-proxy DTI (seed 30: +0.0019 with 3/4 folds; seed 31: +0.0001 with
  2/4 folds, sign-flipping folds). The seed-30 screen was not a stable effect.
* **Not promoted. No candidate file, no submission slot.** A ~0.0001 pooled difference with
  inconsistent fold signs is inside the reproduction noise of this protocol, and the promotion rule
  requires ≥3/4 folds plus a fresh-seed confirmation.
* Honest reading for the brief: the loss geometry does what the paper says it does to *near-miss
  allocation*, but at this budget the catalogue proxy cannot see a benefit from it; the boundary
  weight 0.5 is an untuned initial setting, and the proxy masks out the very catalogue pixels the
  metric actually scores against.

## Where this leaves the boundary-loss question

Candidate follow-ups, in order of expected value per cost:

1. **Larger training budget before re-testing the loss.** 40 steps cannot distinguish a small
   effect; the honest prerequisite for any loss claim is a budget where the regional control's own
   fold-to-fold spread is small.
2. **Boundary-weight sweep (0.1 / 0.25 / 0.5 / 1.0)** under the same paired protocol, one seed,
   then confirm the selected weight on a second seed. The paper's guidance is a small additive
   weight; 0.5 was never tuned here.
3. **Emission-aware scoring.** Since the real metric is evaluated on emitted/thinned masks, a loss
   delta measured on dense probability surfaces may be the wrong target; the metric-emission line
   (see [`metric-emission-holdout-results.md`](metric-emission-holdout-results.md)) is the place
   where the boundary term's geometry could matter, if it is retried at all.
4. **Treat the boundary term as a diagnostic, not a lever** until 1–3 are answered; the repo does
   not claim a boundary-loss gain anywhere.

## Reproduce

```bash
# paired arms, one fresh checkpoint per fold and arm (screen budget); SEED=30 then 31
for F in 0 1 2 3; do for ARM in regional combined; do
  PYTHONPATH=src python scripts/train_model.py --fold $F --loss $ARM --seed $SEED \
    --epochs 2 --steps-per-epoch 20 --batch-size 2 --patch-size 192 \
    --output runs/loss-ablation/seed$SEED/fold$F-$ARM.pt
  PYTHONPATH=src python scripts/infer_model.py --predictions-only --fold $F \
    --checkpoint runs/loss-ablation/seed$SEED/fold$F-$ARM.pt \
    --output runs/loss-ablation/seed$SEED/fold$F-$ARM.oof.npy
done; done

# stitch each arm, then evaluate the pair
for ARM in regional combined; do
  PYTHONPATH=src python scripts/stitch_oof_predictions.py \
    --fold0 runs/loss-ablation/seed$SEED/fold0-$ARM.oof.npy \
    --fold1 runs/loss-ablation/seed$SEED/fold1-$ARM.oof.npy \
    --fold2 runs/loss-ablation/seed$SEED/fold2-$ARM.oof.npy \
    --fold3 runs/loss-ablation/seed$SEED/fold3-$ARM.oof.npy \
    --output runs/loss-ablation/seed$SEED/oof-$ARM.npy
done
PYTHONPATH=src python scripts/evaluate_loss_ablation.py \
  --regional runs/loss-ablation/seed$SEED/oof-regional.npy \
  --combined runs/loss-ablation/seed$SEED/oof-combined.npy \
  --output runs/loss-ablation/seed$SEED/holdout.json
```

Note: scripts that import `gemsdoe30` from a source checkout need `PYTHONPATH=src` (or
`python -m pip install -e .`).
