# Amendment A2 — duplicate-stop of `fusion_edge` production; final experiment = frozen stratified emission

## Duplicate-stop (measured 2026-10-26, after the Amendment-A1 promotion)

The pinned nine-site registry snapshot predates this repo's own later downloads,
so the first novelty audits never compared the FFL-1 candidate against the
MSDB-1v2 raster published in `docs/downloads/`. Direct measurement:

- **78.28% of FFL-1 `fusion_edge` dots fall within 3 px of
  `gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif` dots** (> 70% limit;
  reverse direction 79.90%). Spearman of the continuous fusion surface vs that
  raster is only ~0.11–0.16, so this is a *dot-stage* collision: both emitters
  spend the budget on the same high-belief neighbourhoods.

Under owner protocol rule 1 this emission is a duplicate. **The `fusion_edge`
production TIFF is therefore `negative` / DO NOT SUBMIT permanently**, whatever
later experiments show. The earlier `promote` in the run card is superseded by
this amendment and the corrected final card; the error (an incomplete registry
scope) is logged as IR-FFL-01 in `review.md`. This is the same failure mode the
G30-LSM lane recorded (IR-30-087: "run the dot-stage novelty check *before*
experiments") — the registry used here was frozen before the MSDB download
existed in it, and the check was not re-run against `docs/downloads/`.

## Experiment 3 (last of the ≤3 budget) — frozen stratified emission

- Uses only the preregistered, already-frozen quotas
  (`preregistration.json`: (2,5] 14%, (5,10] 15%, (10,30] 34%, (30,50] 16%,
  >50 px 21%; Poisson r=3.0 within stratum; ≤2 px excluded) and the
  already-saved Experiment-1 fold fusion surfaces. No refitting, no quota,
  feature or threshold changes. This is the Rank-2 hypothesis from the
  preregistration, run last because its original gate condition (a clean
  Experiment-1 pass) was not met; the justification for running it now is the
  uniqueness gate, not score tuning, and that change of condition is recorded
  here before the run.
- Holdout gates (all required): pooled `fusion_ffstrat` HOLDOUT-DTI >
  same-run `msdb_edge` (Experiment 1, seed 3051) with paired 95% CI lower
  bound > 0 (2,000 geographic-block draws, seed 3071); per-arm emitted counts
  exactly matched.
- Production (only if the holdout gates pass): stratified dots from the
  already-built full-catalogue gated fusion surface; expanded-registry audit
  against the pinned registry **plus every TIFF in `docs/downloads/`**
  (candidate excluded by SHA-256): Spearman ≤ 0.90 and ≤70% of dots within
  3 px of *every* reference; strict all-finite [0,1] validator; 0 catalogue
  dots. Any failure ⇒ final verdict `negative`, Experiment budget exhausted.
