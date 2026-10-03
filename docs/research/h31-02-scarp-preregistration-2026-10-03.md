# H-31-02 reduced scarp-orientation holdout — preregistration

**Frozen:** 2026-10-03, before any new score calculation. **Status:** preregistered; no result included here. This tests a *reduced, owner-derived feature stack* and does not test the full raw 1 m DEM hypothesis. Parent hypothesis: `H-31-02` in `docs/hypotheses.md`. Exact transform is intentionally fixed to avoid post-hoc feature/threshold search.

## 1. Question and physical mechanism

Do short-wavelength topographic steps with a locally persistent axial strike identify fault-like traces beyond the current best spatial holdout, or are they mostly channels, terraces, landslides, roads, and other non-fault scarps?

The official About page lists fault scarps, offset layers, gravity/magnetic anomalies, elevation data, and edge-detection methods as mapping cues ([DrivenData page 968](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)). The official problem page says the existing fault set is incomplete and the test includes expert-identified faults ([page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)). These statements motivate the test; neither establishes signal in the local stack.

## 2. Data and provenance gate

Input: `data/raw/external/lidar_scarp_features_u8.tif`, the 12-channel 100 m descriptor stack pinned in `docs/research/mirror-pins-extra.json`, plus `data/processed/valid.npy`, `labels.npy`, and the template grid. The metadata is owner-supplied at the pinned GEMSDOE24 commit, not organizer-authenticated. It says the stack was derived from 706 of 716 3DEP tiles, gives the channel meanings/quantisation, and records known limitations (including that steps can be roads, channels, terrace risers, landslides, or mines). Before scoring, record the downloaded SHA-256, metadata SHA-256, dimensions, CRS/transform, valid-LiDAR coverage, and candidate capacity. First run `python scripts/scarp_orientation_holdout.py --preflight-only`, which must verify all four frozen fold counts (29,114 / 22,102 / 18,009 / 24,165) and the independent 80,392-dot global count without calculating DTI. Stop without scoring if any capacity or raster/grid check fails. Never treat sample-template values as features or prediction targets.

Official source/access check: the [USGS TNM 3DEP API test-bbox query](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119,38.5,-118.5,39) returned 32 products with direct GeoTIFF URLs and an all-3DEP-public-domain statement. This verifies that products can be found, not that all competition DEM tiles are downloaded or complete. Full-domain raw-DEM processing is outside this reduced screen.

## 3. Frozen transform

The source metadata's quantisation rule is `q = 1 + round(254*t(x/xmax))`, with `t = sqrt` or `linear`, and `q = 0` for no lidar. Decode only as follows:

* `step_max`, `upface_max`, and `downface_max`: `xmax = 1`, square-root encoding, so `v = ((clip(q-1, 0, 254) / 254) ** 2)`.
* `strike`: `xmax = 180°`, linear encoding, so `θ = π * clip(q-1, 0, 254) / 254`. Use doubled-angle sine/cosine because strike is axial (0° and 180° are equivalent); do not assume a north/east azimuth convention.
* `coh100` and `valid`: `xmax = 1`, linear encoding, so `v = clip(q-1, 0, 254) / 254`. `valid` is the local coverage weight; ignore `q=0` as missing data.

At the fixed 3×3-cell window, compute the coverage-weighted axial consensus

`O_raw = hypot(mean(w*cos(2θ)), mean(w*sin(2θ))) / max(mean(w), 1e-6)`,

where the means use zero-padded window filtering and `w` is decoded local coverage. To avoid treating one isolated valid pixel as a persistent lineament, multiply by `support = clip(9 * mean(w) / 3, 0, 1)` (three full-coverage cell equivalents are the frozen minimum support): `O = O_raw * support`. Clamp `O` to `[0,1]`. The single ranking field is

`S = sqrt(step_max * max(upface_max, downface_max)) * sqrt(coh100 * O) * valid`.

Set `S=0` where the centre-cell coverage is `<0.50` or `strike` is missing. No learned coefficients, labels, catalogue geometry, SGMC features, or additional scale/threshold search enter this transform. The implementation will include synthetic tests for 0°/180° equivalence, missing-data handling, and finite bounded output.

This is a 100 m, owner-derived proxy for a scarp signature—not a replacement for oriented filters on raw 1 m elevation.

## 4. Primary spatially blocked screen

* Four fixed spatial quadrants from `spatial_quadrant_masks`, matching the repository's archived catalogue-proxy protocol. In model-based CV the helper keeps training labels 300 m outside the held-out quadrant; this deterministic feature-only test has no training step. Each quadrant is scored in isolation with exact 300 m DTI, so pooled fold statistics omit kernel interactions across quadrant seams. This is the same fold-local proxy protocol as the comparator, not an exact stitched full-grid score or a competition score.
* In each held-out block, truth is `labels == 1` restricted to that block; the domain is the valid template footprint in that block. No training occurs on the held-out block because this is a deterministic feature-only detector.
* Ranking/emission is label-blind: eligible cells are `S > 0` within the held-out block; score-order them and apply greedy Poisson-disk spacing **3.0 pixels**, with a 120,000-cell candidate-pool cap. Count the accepted-pool capacity before the gate; emit the first exactly the current-best per-fold counts **29,114 / 22,102 / 18,009 / 24,165** (total **93,390**). If any fold cannot supply its frozen count, mark the experiment capacity-limited and **void the gate**, rather than silently comparing different budgets.
* Score with the exact 300 m, 100 m pixel, α=0.2, β=0.8 DTI implementation. Sum the sufficient statistics over folds and recompute one pooled DTI; report fold DTI only as a diagnostic. Compare with (a) the same-run, fold-count-matched uniform-random controls, and (b) the repository's current same-grid spatial-holdout best: `adaptive` = **0.18927** from `docs/research/metric-emission-holdout-results.json` (**93,390** dots total; per-fold counts above; catalogue-proxy score, not competition score).

**Screen gate (all required):** (1) pooled candidate DTI ≥ **0.19427** (current best +0.005); (2) candidate beats same-run, fold-count-matched uniform controls by ≥ **0.005** pooled; (3) candidate-minus-uniform is positive in ≥ **3/4** quadrants; (4) each arm emits the exact frozen counts per fold and the candidate/control masks are distinct. Any failed capacity/count invariant voids the metric comparison. A failed screen means **no weekly slot** and no post-hoc transform retuning under this registration.

## 5. Independent holdout and confirmation gate

The independent inventory is the USGS State Geologic Map Compilation (SGMC), rasterised in `data/external/derived_sgmc_faults_100m_u8.tif`. It is not the competition truth and is an imperfect proxy; the receipt identifies its public-domain source and overlap with the catalogue. For the screen, use the same 5 component draws as the existing `novelty-holdout` protocol (seed `30*31 + repeat`, `repeat=0..4`, hide 30% of 8-connected SGMC components, mask the 300 m dilation of the *visible catalogue*, exact DTI). Emit a fixed **80,392** global dots from `S` using the same 3-pixel greedy spacing; compare to exact-count uniform random dots and the archived non-leaking best `cand_t04s4` (mean **0.09526**, `docs/research/novelty-holdout.json`). The SGMC-derived hedge is excluded because it uses the same inventory as its target. Independent-screen pass requires (1) mean candidate DTI ≥ **0.10026** (archived best +0.005), (2) at least **4/5** paired draws beat the archived per-repeat best, and (3) pooled DTI beats exact-count blind random by ≥ **0.005**. The historical `cand_t04s4` probability/mask array is not present in this checkout, so an apparent pass against its saved per-repeat numbers is only a screen; the baseline must be regenerated before confirmation.

For any screen pass, a fresh-seed confirmation is mandatory before promotion: new component draws from seed 31, candidate mean DTI must exceed the current non-leaking best by ≥ **0.005** and beat matched random in ≥ **4/5** draws. If the OOF baseline cannot be reproduced on the fresh draws, this is a documented blocker, not permission to compare unpaired numbers as if they were equivalent. No file will be submitted or labelled holdout-promoted from this screen alone.

## 6. Additional promotion checks, frozen before the run

1. **Calibration:** the score `S` is an uncalibrated rank field, not a probability. Calibration is therefore **not applicable to this feature-only screen**. If a learned model consumes `S` and a probability surface is produced, require the standing reliability slope in `[0.8, 1.2]` and top-decile held-out fault-rate retention ≥70% of training-fold rate (`docs/research/verification-protocol.md`) before using its scores for emission.
2. **Feature perturbation:** within each held-out quadrant, randomly permute the valid `strike` values while leaving `step_max`, face response, `coh100`, and coverage fixed; recompute `O`, `S`, and the matched-budget mask. If the primary candidate has a positive gain over uniform, permuting its own strike feature must remove at least 50% of that gain. The candidate and same-run uniform masks must remain distinct. Report this regardless of screen outcome; failure blocks promotion even if the primary DTI gate passes.
3. **Qualitative note:** report which quadrant(s) provide positive/negative lift, top recovered/missed held-out fault components (centroids and local feature values), and whether candidate dots follow the claimed scarps or obvious stream/terrace/road confounders. A map screenshot is useful but cannot override the numerical gate.

## 7. Stop conditions and interpretation

* Stop before scoring if the owner mirror hash, grid alignment, encoding metadata, or valid-LiDAR mask fails.
* Do not substitute a guessed strike convention; doubled-angle local consensus is convention-free.
* A positive catalogue screen is necessary but biased because the competition masks known catalogue pixels. Independent SGMC agreement is required before any slot is considered; neither proxy result predicts a private score.
* The public leaderboard's **0.3195** is the current public target snapshot, not a private score. The owner-reported D2.8 **0.2600** remains unattributed to its exact TIFF; no comparison in this experiment uses that number as a measured baseline.
