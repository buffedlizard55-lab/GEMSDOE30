# Score and file attribution analysis

**Snapshot reviewed:** 2026-10-03. The leaderboard changes as competitors submit, so values below are time-stamped observations, not a promise of current rank.

## What is established

1. **The public metric is spatial, not exact-pixel overlap.** The official problem description defines a distance-weighted Tversky index with a triangular kernel `k(d)=max(1-d/300 m, 0)`, `alpha=0.2` for false positives, and `beta=0.8` for false negatives. At the 100 m grid, the kernel support is three pixel-centre steps. A false positive at distance `d` from the nearest truth has mass `p(x)·[1-k(d)]`; each truth pixel's true-positive credit is the maximum nearby `p(x)·k(d)` and therefore saturates at its best prediction.
2. **A one-pixel near miss has fractional credit.** For one unit-probability prediction shifted from one isolated truth pixel on a 100 m grid:

   | Offset | TPw | FPw | FNw | DTI (approximately) |
   | ---: | ---: | ---: | ---: | ---: |
   | 0 m | 1 | 0 | 0 | 1.000 |
   | 100 m | 2/3 | 1/3 | 1/3 | 0.667 |
   | 200 m | 1/3 | 2/3 | 2/3 | 0.333 |
   | 300 m | 0 | 1 | 1 | 0 |
   | 400 m | 0 | 1 | 1 | 0 |

   This calculation is reproduced by `python scripts/loss_geometry_probe.py` and the unit tests. It is a toy derivation, not a held-out model result.
3. **The leaderboard's displayed top score was 0.3195.** On the 2026-10-03 read, rank 1 was DARD with 0.3195. Rank 15 was `wbg1` with 0.2600. That official table associates those values with leaderboard participants, not with a GitHub Pages TIFF by filename or SHA-256.
4. **The GEMSDOE25 page has a conflicting artifact status.** Its currently readable landing page and executive-summary page describe the D2.8 TIFF as format-validated but **unscored / not slot-approved**, give a 44,090-pixel count and a truncated SHA-256 prefix, and label a 0.2510 conditional model output as an expectation rather than a score. The user's prompt separately reports that the same named artifact scored 0.2600. No DrivenData receipt, submission ID, full-file hash matched to an official result, or current official artifact-to-score crosswalk was available here. The attribution is unresolved.
5. **The supplied 0.2600 is not the current public leader.** Even if its artifact attribution is later confirmed, it would be below the observed 0.3195 public score. Exceeding 0.26 and exceeding the current public leader are different targets: the latter requires at least a 0.0595 absolute increase over 0.26 (about 22.9% relative), under that snapshot. Public leaderboard performance is not private-test or final-round performance.

## Local D2.8 file audit — measured properties, not score attribution

The exact local artifact is `docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`, SHA-256 `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`. It is a one-band float32, 3730×3292, EPSG:32611, 100 m raster matching the locally pinned template. It contains **44,090** binary positive pixels; none overlaps a known catalogue label. **8,266** fall inside the 3-pixel catalogue buffer and **35,824** are outside it. A separate direct Euclidean distance-to-catalogue calculation reports **19.5214%** (about 8,607 of 44,090) within 300 m; this differs because the proximity constructions differ, not because the file changed. Median dot-to-catalogue distance is about **1.5 km**. These are properties of the file, not evidence that the dots trace uncatalogued faults.

Local proxy metrics are protocol-specific and not competition scores: full-catalogue DTI **0.1617719829** (`emitter-comparison.json`); catalogue checkerboard hide-and-recover DTI **0.1509524764** (`emission-anatomy.json`); five-repeat SGMC component-holdout DTI **0.07260906, 0.07182390, 0.06866501, 0.06639569, 0.07355228** (mean **0.07060919**). The catalogue checkerboard, full-catalogue, and SGMC frames use different truths and masks, so their scores are not interchangeable. None verifies or predicts the hidden competition score.

The archived zero-outside copy preserves the in-footprint predictions and passes a strict all-finite diagnostic, but it fails the published-format outside check because the public specification requires null/NaN outside. It is not linked as a submission-format file. The NaN-outside research TIFF follows the published convention and passes local checks against the available template. The exact file behind the earlier `[0,1]` error is unknown, so its cause remains undiagnosed; local validation does not establish organizer acceptance.

## Why dotting/thinning could increase DTI — mechanism, not attribution

The official definition allows several nearby predictions to compete for the same truth pixel, but only the *best* nearby probability contributes that pixel's TPw. Additional emitted probability still contributes to FPw, with a smaller cost close to truth and a larger cost far away. Therefore, a dense line or band can be redundant under the metric. A thinned/dotted set can sometimes retain much of the local maximum credit while reducing the total false-positive mass. Conversely, too much thinning can leave truth pixels with no strong prediction within 300 m and increase FNw. The optimum depends on the unknown new-fault distribution and on the candidate's spatial relationship to those faults.

This is a plausible mechanism for a higher score from a dotted raster; it **does not prove** that it explains the user-reported 0.2600, that the TIFF found new geology, or that thinning will generalize to the private labels. The GEMSDOE25 owner page itself does not call D2.8 a scored, slot-approved winner. Its conditional calibration/model estimates are not competition scores.

## Boundary-loss decision

Exact-pixel regional losses assign nearly identical penalties to different non-overlapping shifts. The GEMS geometry term in `src/gemsdoe30/losses.py` adds a distance-transform false-positive weight and a local max over the exact 300 m triangular kernel, so a prediction 100 m away is treated more favorably than one 200 m or 400 m away. This term is combined with regional soft-Tversky rather than replacing it. It is Kervadec-inspired, not a verbatim reproduction of the medical-image surface loss.

The synthetic probe establishes only that the implemented objective has the intended toy geometry. The paired real-data ablation has now run at two seeds on buffered spatial folds (owner-mirror data restored 2026-10-03): the seed-30 screen was positive (pooled DTI 0.062042 → 0.063990) but the fresh-seed-31 confirmation did not replicate (Δ +0.000115, 2/4 folds), so the boundary term is **not promoted** even though its near-miss behaviour reproduced (partial-distance truth coverage 1,889 → 724). Evidence: `research/loss-ablation-holdout.md`, `research/loss-ablation-holdout-seed31.json`.

## Prize phases change what "winning" means (rules §1.1, verified 2026-10-03)

The official rules split the $300,000 pool into **Phase 1** ($50,000, split *equally* among the top five on a private withheld subset of expert-new faults) and **Phase 2** ($250,000: $100k/$70k/$40k/$25k/$15k) judged on the **updated label set that experts create by reviewing Phase-1 submissions** (community thread 11527). Three strategic consequences, all consistent with the observed leaderboard:

1. Phase 1 rewards *generalization* (one final submission is chosen without private-score knowledge, §3.6.2) — public-LB spikes are noise; the frozen holdout discipline is the right proxy.
2. Phase 2 rewards **expert-confirmable geometry**: traces a geology panel can review when they revise the region. Sparse, strike-consistent predictions may be easier to inspect than dense probability fields, but the local D2.8 bytes do not verify fault identity, strike consistency, or the user-reported score sequence. Do not infer that D2.8's reported 0.1922 → 0.2600 rise came from confirmable geology without an exact-file receipt and independent geological validation.
3. Equal Phase-1 splits reduce the value of rank-1 gaming; top-5 private performance is the Phase-1 target, and the Phase-2 pool is 5× larger — invest in *real* fault geometry for the final selected entry.

## Bottom line

- We **cannot verify** the score-to-file link for the D2.8 artifact from the available evidence.
- We **cannot claim** that this repository currently produces a TIFF that scores above 0.26 or above 0.3195.
- The metric supports two falsifiable levers: (i) better spatial ranking of new-fault evidence, and (ii) calibration/emission that avoids redundant probability while preserving 300 m coverage. The boundary-loss experiment tested the first model-training lever (screen positive, confirmation negative); the emission sweep tested the second (thin, do not flood); the H-32 register adds independent geothermal-observation levers.
- Do not spend a weekly slot until an exact candidate beats the current comparable holdout best, survives confirmation, and passes the exact template/file audit.

## Source trail

Official facts and source-access notes are listed in [`sources.md`](sources.md). User-provided historical scores are retained separately in [`score-ledger.csv`](score-ledger.csv) and are explicitly marked unverified. The two conflicting owner/score claims are registered in [`irregularities.md`](irregularities.md).
