# Boundary-weight sweep (fold-0 screen) — the recorded retry criterion, executed

**Date:** 2026-10-03 · **Design:** `scripts/loss_weight_sweep.py` ·
**Record:** [loss-weight-sweep.json](loss-weight-sweep.json) ·
**Status:** **no weight selected; boundary line stays not promoted.**

This is the exact retry the ablation follow-up required: *"use a larger training
budget and a boundary-weight sweep before any fresh-seed test, and score
emitted masks rather than dense probability surfaces"* (see
[seed-31 confirmation JSON](loss-ablation-holdout-seed31.json)). All four
arms trained with identical recipes and seed 30 on fold 0 (the same 300 m-buffered
180 ° quadrant design as the ablation) at 2 epochs × 50 steps = 100 steps per
arm (2.5× the ablation screen's 2 × 20 steps), then predicted their held-out
quadrant and were scored two ways:

* **dense** — exact distance-weighted Tversky on the fold-0 evaluated quadrant
  (truth 29,319 px; scored 2,449,030 px);
* **emitted** — uniform Poisson-disk emission from the top-480k scored pixels
  (radius 3 px, the family's pool cap), then the same metric on the dot mask.

| arm | boundary weight | dense DTI | emitted DTI | dots |
|---|---|---|---|---|
| **regional** | 0 | **0.07300** | 0.17879 | 52,498 |
| combined-025 | 0.25 | 0.07040 | 0.17045 | 52,516 |
| combined-050 | 0.50 | 0.06823 | 0.17402 | 53,163 |
| combined-100 | 1.00 | 0.06883 | **0.17976** | 54,068 |

**Screen rule (frozen in the script): a weight is selected for confirmation only
if it is best under *both* scorings.** The scorings disagree — dense prefers
plain `regional`, emitted prefers `combined-100` (by +0.0010, one fold, one
seed) — so **`selected_for_confirmation = null`**. No fresh-seed test is
warranted.

## What this means

1. On the dense surface — the setting the earlier ablation screened on — the
   boundary term hurts at every weight at this budget, consistent with the
   seed-31 non-replication (Δ +0.0001).
2. The emitted-mask reading (the brief's preferred scoring) shows at most a
   +0.0010 fold-0 edge for the strongest weight — two to five times below the
   +0.002/+0.005 promotion margins and not corroborated by the dense reading.
3. The retry criterion is now **executed, not open**: larger budget ✓, weight
   sweep ✓, emitted-mask scoring ✓. The boundary-loss line stays **not
   promoted**, and further λ tuning on this design is a dead end unless a new
   mechanism is proposed. Effort should follow the registered next candidates
   (H-32-05 pinch-out edges; H-31-02 scarp arm) and the emission-calibration
   item in [verification-protocol.md](verification-protocol.md).

## Irregularity found and fixed during the run (IR-grade note)

The first scoring pass used an un-pooled Poisson thinning of the *entire*
all-positive surface: at radius 3 px that degenerates to a score-blind geometric
lattice — two different models produced **identical** 269,600-dot masks. Found
by cross-arm comparison, fixed by pooling candidates to the top-480k scored
pixels and by scoring only the evaluated fold-quadrant (the prediction arrays
are NaN outside it). All four arms were (re-)scored with the corrected scorer
before comparison; the JSON records the correction in `scoring_note`. Lesson
recorded in `docs/irregularities.md` as IR-30-023.

## Deviations from the script's printed plan

* None in training: all four arms ran the promised recipe (fold 0, seed 30,
  2 × 50 steps, batch 4, 256² patches, fold-local robust normalization).
* The scorer correction above applies to the *scoring* half of the design; it
  was applied uniformly and does not bias arm-vs-arm comparison.
* Fold-0-only by design: this is a **screen**, not a promotion test. Fold-isolated
  values are diagnostics (per the script's own note).
