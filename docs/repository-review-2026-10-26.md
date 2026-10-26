# GEMSDOE30 repository review — 2026-10-26

## Executive decision

**Do not upload any file from this checkout.** The current lane (FFL-1) used all 3/3 experiments within its 2-hour budget. Its generated TIFF is format-valid, but the required expanded-registry dot check records a duplicate-stop: 78.280789% of its dots lie within 3 px of the MSDB-1v2 raster (limit: 70%). The stratified rescue was infeasible under the frozen holdout folds. This is a negative research result, not an organizer score.

- FFL-1 file: [`gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif`](research/2026-10-26-fflidar/gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif)
- SHA-256: `7950607036e51faaf0258b4efeff29d75b8f12eb712aa592cd661822d3c85c07`
- Machine decision: [`readiness.json`](research/2026-10-26-fflidar/readiness.json) (`negative`, `ok_to_submit=false`, `submission_approved=false`, `slot_selected=false`)
- Full science and nine-site summaries: [FFL-1 review](research/2026-10-26-fflidar/review.md) · [nine-site summary](research/2026-10-26-fflidar/nine-site-executive-summary.md)
- The best supplied prior result remains GEMSDOE32 H33-B2, reported as 0.2778. It is an earlier artifact and must not be copied or re-submitted. That number is owner-reported and has no submission-page receipt in this repository; it is **not** `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED` here.

The archived FFL holdout numbers are `HOLDOUT-DTI` from evaluator `component-holdout-v3-blockstats-20261025`, with 60,988 withheld positives and spatial-block 95% CIs. Experiment 1: fusion 0.182417 [0.168230, 0.196433] vs same-run MSDB 0.175639 [0.161471, 0.189566], paired difference +0.006779 [−0.000067, +0.012888]. Fresh-seed amendment confirmation: fusion 0.183949 [0.169419, 0.197874] vs MSDB 0.173427 [0.159043, 0.187952], paired difference +0.010522 [+0.004182, +0.016362]. The first frozen CI gate missed; the amendment is disclosed separately. Neither result estimates or guarantees a leaderboard score.

## Repository findings and repair

1. **Fixed: verifier did not independently verify the expanded negative duplicate evidence.** `scripts/verify_fflidar_run.py` checked the expanded 172-raster receipt only in a branch used when a candidate could be promoted. Since FFL-1 is negative, that bypassed the decisive receipt that justified its duplicate-stop. The verifier now checks that receipt on every run, binds it to the candidate TIFF SHA-256, validates all overlap/correlation values, recomputes the thresholds, and requires the negative duplicate finding to appear in readiness. Regression tests cover altered hashes and inconsistent decisions. A duplicate result is accepted as a verified negative; it is not treated as a verifier error.
2. **Historical review is time-scoped.** [`review-2026-10-26.html`](../review-2026-10-26.html) and [`research/review-2026-10-26/review.md`](research/review-2026-10-26/review.md) record a 00:34 UTC pre-FFL audit and must not be read as describing later work. FFL-1 was subsequently recorded at 00:50 UTC. The older machine report remains an audit snapshot, not the live lane pointer.
3. **No organizer receipt or portal upload automation exists.** Local TIFF validation establishes the documented file contract only. It does not establish organizer acceptance, score, eligibility, or slot selection. The nine supplied site results and current leaderboard claims are not bound to local bytes by official receipts.
4. **Training stack absent from this worktree.** The SHA-pinned owner-mirror `sample_submission.tif` was restored to ignored `data/raw/` for local byte checks. `training_features.tif` and `labels.tif` are absent; the mirrors are explicitly not organizer-authenticated. No new training, holdout, novelty experiment, or TIFF was run/generated in this review. The FFL lane's 3-experiment cap is already consumed.
5. **Shared test coverage is healthy with five optional skips.** After restoring the hash-pinned template, the full test run completed: 262 passed, 5 skipped, 2 Rasterio pending-deprecation warnings, plus 7 subtests passed. The five skips are optional Torch-dependent tests. The strict FFL verifier and current-run verifiers, stopped-attempt checks, and generated-site consistency check were also run.

## Future hypotheses — proposals only, not authorized experiments

The following are refinements already recorded in the dated review. Their novelty against every parallel team's private registry is unknown; they are not certified as untried. FFL-1's budget is exhausted, so none should be executed in this lane. First obtain a distinct lane assignment, restore and verify the training/cache stack, and preregister the evaluator, controls and registry.

| Priority | Cached layers / transform | Why it could find unmapped fault geometry | Main mimic | Relative cost |
|---|---|---|---|---|
| 1 | Magnetic anomaly normal profiles plus total-count radiometry and DEM; compare bilateral residual-core models after removing smooth lithologic trends | A narrow demagnetized damage core with bilateral intact flanks may indicate a covered structure without a mapped scarp | Altered volcanic-flow margin or intrusive contact | Medium |
| 2 | Gravity anomaly, basement depth and DEM; locally detrend, then test signed cross-slope asymmetry against a regional-gradient-matched null | One-sided buried basement step below a smooth fan could indicate a concealed normal fault | Non-fault basin margin | Medium |
| 3 | Magnetic and gravity derivatives; ridge-normal curvature and multiscale polarity/phase residual after removing shared regional gradients | Persistent opposite-polarity lobes may isolate a narrow buried boundary | Dike or lithologic boundary | High |
| 4 | DEM and total-count radiometry; drainage-normal paired residuals under relief-matched controls | Repeated localized cross-drainage breaks may expose subtle structure where broad scarp amplitude is weak | Paleoshoreline, terrace or road cut | Medium |

No DTI improvement is projected. These concepts depend on the cached stack and should be rejected or revised if their feature definitions duplicate an existing method. If an idea requires an external layer, verify the official source, license, coverage and downloadable bytes before considering it viable. Useful official references: [USGS GeoDAWN airborne magnetic/radiometric data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [EPSG:32611](https://epsg.io/32611), and the [official competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/). The dynamic leaderboard and login-protected competition files were not fetched or revalidated in this review.

## Reproducible checks

From repository root, with test/research extras installed and the pinned public-mirror template restored:

```bash
python -m pytest -q
python scripts/verify_fflidar_run.py
python scripts/verify_current_run.py
python scripts/verify_stopped_attempt.py
python scripts/verify_lsm_run.py
python scripts/verify_tad_run.py
python scripts/build_research_site.py --check
```

`verify_fflidar_run.py --require-promote` is expected to exit 2 because the recorded verdict is negative. No command in this review submits to DrivenData or consumes a weekly slot.
