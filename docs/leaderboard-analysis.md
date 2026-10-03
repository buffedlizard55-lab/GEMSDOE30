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

## Why dotting/thinning could increase DTI — mechanism, not attribution

The official definition allows several nearby predictions to compete for the same truth pixel, but only the *best* nearby probability contributes that pixel's TPw. Additional emitted probability still contributes to FPw, with a smaller cost close to truth and a larger cost far away. Therefore, a dense line or band can be redundant under the metric. A thinned/dotted set can sometimes retain much of the local maximum credit while reducing the total false-positive mass. Conversely, too much thinning can leave truth pixels with no strong prediction within 300 m and increase FNw. The optimum depends on the unknown new-fault distribution and on the candidate's spatial relationship to those faults.

This is a plausible mechanism for a higher score from a dotted raster; it **does not prove** that it explains the user-reported 0.2600, that the TIFF found new geology, or that thinning will generalize to the private labels. The GEMSDOE25 owner page itself does not call D2.8 a scored, slot-approved winner. Its conditional calibration/model estimates are not competition scores.

## Boundary-loss decision

Exact-pixel regional losses assign nearly identical penalties to different non-overlapping shifts. The GEMS geometry term in `src/gemsdoe30/losses.py` adds a distance-transform false-positive weight and a local max over the exact 300 m triangular kernel, so a prediction 100 m away is treated more favorably than one 200 m or 400 m away. This term is combined with regional soft-Tversky rather than replacing it. It is Kervadec-inspired, not a verbatim reproduction of the medical-image surface loss.

The synthetic probe establishes only that the implemented objective has the intended toy geometry. Whether this improves actual fault discovery must be tested with paired, spatially blocked models using the same labels, seeds, folds, training budget, and exact metric. The current holdout baseline and comparison are unknown because the required competition data are absent.

## Bottom line

- We **cannot verify** the score-to-file link for the D2.8 artifact from the available evidence.
- We **cannot claim** that this repository currently produces a TIFF that scores above 0.26 or above 0.3195.
- The metric supports two falsifiable levers: (i) better spatial ranking of new-fault evidence, and (ii) calibration/emission that avoids redundant probability while preserving 300 m coverage. The boundary-loss experiment tests the first model-training lever; a separate, preregistered emission sweep is needed for the second.
- Do not spend a weekly slot until an exact candidate beats the current comparable holdout best, survives confirmation, and passes the exact template/file audit.

## Source trail

Official facts and source-access notes are listed in [`sources.md`](sources.md). User-provided historical scores are retained separately in [`score-ledger.csv`](score-ledger.csv) and are explicitly marked unverified. The two conflicting owner/score claims are registered in [`irregularities.md`](irregularities.md).
