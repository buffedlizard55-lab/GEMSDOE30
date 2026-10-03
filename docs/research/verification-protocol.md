# Promotion verification protocol — three checks beyond a single holdout win

**Date:** 2026-10-03 · **Status:** standing protocol for every future promotion
candidate (loss, emission, feature, or rule change). Owner brief, distilled
requirement 7: *"Produce and describe THREE types of verification beyond a
private holdout and a qualitative note showing where a learned change helps and
where it fails."*

A spatially-blocked holdout result (even a confirmed one) is necessary but not
sufficient. Before any candidate earns a submission slot it must clear **all
three** checks below, each with a pre-stated promotion criterion. The criteria
are frozen before running the check; post-hoc tightening is a protocol
deviation and must be recorded.

---

## Check 1 — Spatial block-validation (the existing frozen gates)

**What it is.** The candidate is evaluated only on held-out spatial blocks that
training never saw: the four 300 m-buffered spatial quadrants (fold = 180 °
sector), pooled exactly as the official metric (distance-weighted Tversky,
R = 300 m triangular kernel, α = 0.2, β = 0.8, pixel-resolution support), plus
the guardrails each line already carries (fresh-seed confirmation for loss
changes; leave-one-fold-out emission selection; distance-matched controls where
a spatial prior is claimed).

**Promotion criterion (as enforced today).**

| Line | Screen | Confirmation |
|---|---|---|
| Loss change | pooled ΔDTI ≥ **+0.002** on seed 30 | seed-31 ΔDTI **> 0** with **≥ 3/4** folds positive |
| Emission family | beats uniform by **≥ +0.005** pooled DTI | selected in **all four** leave-one-fold-out splits |
| Spatial-prior signal (e.g. H-32 series) | ≥ **+0.002** vs **distance-matched** control | Δ **> 0** on a fresh split seed **and ≥ 3/4** quadrants positive |

**Recorded outcomes:** loss line failed confirmation (Δ +0.0001, 2/4) → not
promoted; emission family failed (+0.0025 < +0.005) → not promoted; H-32-01
failed all three clauses (−0.015) → falsified. See
`loss-ablation-holdout{,-seed31}.json`, `metric-emission-holdout-results.md`,
`h32-01-vent-corridor-holdout.md`.

## Check 2 — Probability calibration of the scored surface

**What it is.** Any learned change that alters the *score surface* (not just a
binary mask) must be calibrated on held-out folds before its emission behaviour
is trusted: within each score-decile bin of predicted probability (computed
fold-locally), the empirical fault frequency must track the predicted level.
The metric-emission post-mortem names miscalibration as the leading suspect for
the greedy rule's over-emission (46 % dots inside kernel support), and a
calibration layer was the named follow-up — this check exists to catch that
failure mode *before* a family is promoted.

**Promotion criterion.** On the held-out folds:

1. **Reliability slope** of empirical-vs-predicted bin frequencies within
   **[0.8, 1.2]** (least squares on bins with ≥ 500 px), **and**
2. **Top-bin precision stability:** the realized fault rate in the top
   predicted-decile bin on the held-out folds is **≥ 70 %** of the same bin's
   training-fold rate (a gross drop means the surface is ranking by
   fold-specific artefact).

Failing either criterion invalidates any emission-family comparison built on
that surface; re-calibrate (isotonic/binning on the training folds only) and
re-run Check 1 before interpreting emission results.

## Check 3 — Feature-perturbation stability

**What it is.** A promoted signal must be attributable to the geology it claims,
not to a fold artefact riding one channel. For every feature family the
candidate leans on, permute that family's channels **on the held-out folds
only** (training untouched) and re-score the candidate.

**Promotion criterion.**

1. Permuting the candidate's *own* feature family must remove **≥ 50 %** of its
   gain over baseline (if the gain survives its own features being destroyed,
   the "signal" is something else), **and**
2. Permuting any *unrelated* channel family must not flip the sign of the gain
   (retains **> 0**), **and**
3. Across the four quadrant folds the per-fold gain keeps its sign in
   **≥ 3/4** folds under the candidate's own configuration (already required by
   Check 1; repeated here as the stability reading).

## The qualitative note (required alongside the three checks)

Every promotion request must include a short atlas-style note naming **where the
change helps and where it fails**: at least two example blocks (approximate
centroids) per fold-sign outcome, the local layers visible there, and one
sentence on the mechanism each example supports or contradicts. Example:
`h32-01-vent-corridor-holdout.md` §"What the failure looks like" (spring haloes
capture scattered intermediates, never their corridor cores; every quadrant
negative). A promotion without this note is incomplete regardless of numbers.

---

## How to run

- Check 1: the existing gate scripts
  (`scripts/evaluate_loss_ablation.py`, `scripts/metric_emission_holdout.py`,
  `scripts/vent_corridor_holdout.py`) — each writes its JSON to
  `docs/research/`.
- Check 2–3: extend `scripts/score_sweep_arm.py` (calibration bins) and a
  small permutation harness around `train_model.py`/`infer_model.py`
  checkpoints; both to be added to `tests/` as smoke tests when first used.

**Scope note.** These checks govern *promotion into a submission slot* and
holdout-selected ranking claims. They do not gate exploratory screens, which
may run without them and are labelled as screens in their artifacts. All three
checks operate on the known-catalogue proxy; the private expert label set is
unavailable, and no proxy result implies a private score.
