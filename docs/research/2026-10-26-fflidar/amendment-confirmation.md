# Amendment A1 — one fresh-seed confirmation (written after Experiment 1, before any confirmation run)

**Status of the original preregistration:** unchanged and preserved. This amendment
is *not* part of the frozen preregistration; it is recorded here, before the
confirmation is run, so the weaker evidentiary status is explicit.

## What Experiment 1 measured (HOLDOUT-DTI, evaluator `component-holdout-v3-blockstats-20261025`, 60,988 withheld positives)

- `fusion_edge` = 0.182417 [0.168230, 0.196433]
- `msdb_edge` (same seed/folds) = 0.175639 [0.161471, 0.189566]
- Paired Δ = **+0.006779, 95% CI [−0.000067, +0.012888]** — the frozen gate
  (lower bound > 0) **failed by 0.000067**. Fusion won weighted TP in 3/4 folds.
- Canaries: 54 features × 4 folds, 0 alarms (max either-direction AUC 0.6667).

## Amendment

Exactly **one** confirmation experiment (Experiment 2 of the ≤3 budget) is added:

- Identical frozen recipe, folds, arms, budgets, emitter and bootstrap as
  Experiment 1. **Nothing is retuned** — no feature, threshold, hyperparameter,
  quota or budget changes.
- The only change is the seed: sampler/model seed **3063** (Experiment 1: 3051).
  This follows this repo's standing promotion practice (`docs/hypotheses.md`:
  screens require "fresh-seed replication" before a slot may be proposed).
- Gate (single, pre-committed): on the fresh seed alone,
  `fusion_edge − msdb_edge > 0` with paired 95% CI lower bound > 0
  (2,000 geographic-block bootstrap draws, seed 3071).
- If the confirmation fails, the lane ends `negative`; Experiment 3 stays
  unspent and no further seed is tried (that would be seed-hunting).
- If it passes, the candidate is `fusion_edge` (the Experiment-2 stratified
  arm `fusion_ffstrat` is **not** run: its preregistered condition — a clean
  Experiment-1 pass — was not met, and inventing a new condition after seeing
  data would be tuning). The production TIFF (full-catalogue fusion model,
  seed 3051, already built) is then re-issued with a corrected submission note
  (see IR-FFL-02 in `review.md`: the original note wrongly says "stratified
  quotas" for an EDGE emission) and the dot-novelty audit is re-run to bind
  the new file bytes. Pixel values do not change.
- Evidentiary caveat, stated plainly: because this amendment was written after
  Experiment 1 was seen, a confirmation pass is weaker than a preregistered
  pass. Both experiments' numbers are reported whatever happens.
