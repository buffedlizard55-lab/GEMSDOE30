# TDX-1 — frozen research plan (2026-10-25)

This plan is written **before candidate feature construction, fitting or evaluation**.
It continues the first untested hypothesis in the previous [review](../2026-10-25/review.md).
It is a narrow, autonomously selected **research lane**, not an asserted assignment by
an external parallel-run coordinator. The prompt names no identifiable lane paragraph;
that ambiguity and the missing complete parallel registry prohibit submission approval.
No candidate is selected for an actual competition slot.

## Ranked hypotheses, before implementation

Ranks are qualitative expected information gain / implementation cost, **not projected scores**.
These were proposed but not implemented in the previous review; a search of the current
`src/`, `scripts/`, and prior experiment reports found no implementation of the named
matched-profile displacement transform. No claim of novelty outside reviewed code is made.

| Rank | Hypothesis and exact cached layers | Physical transform / missing-fault rationale | Non-fault mimic | Difference from current code | Utility / cost |
|---|---|---|---|---|---|
| 1 | Cross-contact magnetic texture displacement: `mag_anom` (band 1), `rtp` (band 2), `iso_grav_anom` (band 13) | Estimate a nonzero along-edge lag between magnetic profiles on opposite flanks of a gravity gradient; require lag agreement at two smoothing scales. Buried offsets need not have a mapped surface scarp. | Intrusive lithologic contacts; gridding seams | Profile correspondence, not the existing scalar gradient, basement-edge, scarp dipole, catalogue-tip or dot-pruning methods | Moderate, uncertain / medium CPU cost; **only hypothesis implemented here** |
| 2 | Conductivity-curvature saddles: `cond_surf` (17), `depth_to_base_surf` (15), `iso_grav_anom_hg` (18) | Saddle topology at a cover/basement transition could indicate a breach hidden from surface mapping. | Saline groundwater; sedimentary facies | Saddle topology, not generic high conductivity or edge-amplitude conjunction | Moderate-to-low / low; not tested in this lane |
| 3 | Conditional demagnetization ribbons: `mag_anom` (1), `rtp` (2), `tmi_vg` (9), gravity (13) | Spatially coherent negative magnetic residuals after conditioning on gravity and broad trend could reflect alteration along buried pathways. | Nonmagnetic basin fill | Conditional residual, not absolute magnetic amplitude | Uncertain / medium; not tested in this lane |
| 4 | Persistent signed profile offsets: `det_elev` (12), `det_elev_slope` (19), basement depth (15) | Opposing detrended topographic profiles with cross-scale persistent steps could extend low-relief unmapped structures. | Paleoshorelines; fluvial terraces | Matched profile displacement rather than LiDAR dipole maximum | Low-to-moderate / medium; not tested in this lane |

**Source / availability:** all named layers are already present in the hash-pinned
19-band cached competition stack. Their meanings, raster dimensions, CRS and resolution
are independently described in the organizer's [reference notebook, cell 5](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb).
Mirror consistency is not organizer authentication. No new external data is needed or
represented as obtainable. The proposed mechanisms are hypotheses, not established
identifications of fault displacement, geothermal alteration, permeability or vents.
Official-source links for later literature/data review are retained in the report with
explicitly unverified access; no inaccessible publication is represented as newly read.

## Fixed TDX-1 transform

Use only bands 1, 2 and 13 to construct the candidate. Smooth gravity with a Gaussian
sigma of 2 px (truncate 3), take its gradient normal, and sample magnetic profiles
on flanks at +/-3 px. Profiles have nine samples along the local tangent, at
integer offsets -4 through +4 px. Test lags -2, -1, 0, +1, +2 px using normalized
cross-correlation after removing each profile's mean. Magnetic smoothing sigmas
are 1 and 2 px (truncate 3). At each scale retain improvement over zero lag only
when the winning nonzero-lag correlation is positive; require the winning lag's
sign to agree across scales. Form one displacement feature per magnetic band;
the third derived feature is their geometric mean times gravity-edge strength
normalized by a **training-only** 95th percentile. Maximum physical filter/sample
support is conservatively bounded by 16 px. No registry raster, template value,
fault-distance feature or catalogue direction enters this transform.

## One experiment, three fixed arms; no tuning or candidate selection

- **Candidate `tdx6`:** the three raw physics bands plus the three derived features.
- **Ablation control `physics3`:** the same raw three bands without displacement.
- **Stronger recipe comparator `core19`:** the existing core 19-band HGB recipe,
  rerun with the corrected shared evaluator and identical folds/emission budget.
- Fit identical `HistGradientBoostingClassifier` settings: 120 iterations,
  learning rate 0.1, 31 leaves, no early stopping, seed 3070 + fold.
  Sample all visible positive training pixels and six negatives per positive.
  Use the repository's existing training sampler/standardizer and cached arrays.
- Before trusting results, evaluate **every raw/derived input alone** on held-out
  pixels: raw rank AUC (both directions) and a univariate HGB fitted on training
  pixels only (32 iterations, 7 leaves, no early stopping). AUC >0.90 is a leakage
  alarm and blocks promotion. A low AUC does not establish absence of leakage.
- The final download is always the `tdx6` method refit on the full visible catalogue,
  not whichever arm wins. A failed scientific gate still produces a clearly
  quarantined, format-validated negative-result TIFF, unless duplicate-stop fires.

## Shared buffered whole-segment spatial holdout

Extend the existing public `gemsdoe30.holdout` module, not a private evaluator.
Whole 8-connected catalogue components are assigned to one of four coarse spatial
quadrants by centroid; every component is hidden in exactly one fold. Score the
quadrant plus a 300 m halo around complete assigned components, so components
crossing a quadrant edge are not cut. Remove whole non-test components touching
a 16 px guard around that scored region from visible training faults; exclude
those guard components' pixels from scoring/training, not their neighborhoods.
Training pixels must lie more than 16 px outside the scoring region. Recompute
any catalogue features from `visible` only (none are used by TDX). Mask visible
fault pixels exactly, never a blanket fault buffer in the evaluator.

The scoring regions can overlap slightly near quadrant boundaries; these are
four specified regional trials, **not** a claimed disjoint OOF mosaic. Every
withheld positive is counted once. Pool TP/FP/truth sufficient statistics, not
fold DTI averages. Use the shared exact 300 m triangular kernel, alpha 0.2 and
beta 0.8. For uncertainty, retain full-fold cross-block kernel credit, aggregate
sufficient statistics by the same geographic 128 px (12.8 km) blocks across folds,
and draw 2,000 paired spatial-block bootstrap replicates (seed 3071). Report
HOLDOUT-DTI, evaluator/protocol version, withheld positives, and 95% percentile CI.
These are catalogue-recovery diagnostics, never hidden-test forecasts.

Allocate a density equivalent to 44,090 dots over the full footprint to each fold,
using scored-area proportional integer budgets, identical for all three arms.
Use the existing score-first greedy Poisson selector at 3 px. Check realized pool
capacity before scoring. A count shortfall invalidates the paired gate; do not
change budgets or thresholds after seeing outcomes.

## Novelty, release and stop rules

Snapshot the nine priority repositories' published TIFF inventories and compare
the continuous candidate surface **before placement**, then the final dots,
against every aligned, hash-pinned downloaded registry raster. Correlation is
full-footprint Spearman; dot overlap is candidate-directional, Euclidean <=3 px.
Stop and log a duplicate on rho >0.90 or final dot overlap >0.70. Dense surfaces'
positive-support overlap is reported as a diagnostic, not called a set of dots.
Record incomplete registry/surface coverage; never infer global completeness from
successful downloads. No registry is used to choose, remove, or move predictions.

Research promotion requires: no leakage alarm; exact-count construction; candidate
pooled HOLDOUT-DTI above both fixed controls, with paired 95% CI lower bound >0;
no duplicate; complete parallel registry and assigned-lane evidence; a comparable
rerun of the historical current best. Archived best UNet checkpoints are absent,
so that last gate cannot be silently substituted by the core19 comparator. Any
unknown/failed gate means `negative`, `submission_approved=false`.

Use the existing shared `submission.write_submission_file` / validator, with
NaN nodata outside the footprint (published format), no silent repairs, and a
unique method/hash name and <=140-character note. Reopen every output to check
finite [0,1] in-footprint values, CRS, shape, transform, one float32 band, nodata
and no positive visible-catalogue pixels. Zero-outside diagnostics are not passed
off as published-format submissions. No private portal acceptance is claimed.

**Budget:** one fixed paired experiment, three arms plus diagnostic canaries;
no hyperparameter sweep. Stop experimental computation after three experiments
or two hours from session start (2026-10-25T20:44Z), whichever occurs first.
No competition upload or slot selection, regardless of results.
