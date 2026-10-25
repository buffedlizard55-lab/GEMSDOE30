# Lane G30-S20 preregistration — frozen before any S20 holdout result

Frozen 2026-10-25 (before feature construction). Companion:
[hypotheses.md](hypotheses.md) (Rank 1 is this lane). Budget: **3 experiments**
(E1 seed-31 paired ablation, E2 seed-47 replication, E3 final full-catalogue
production) and no tuning after E1 beyond the selection rule written here.

## Hypothesis and mechanism

Adding (a) sub-100 m fault-scarp morphology from 1 m DEMs and (b) GeoDAWN
radiometric composition to the 19-band habitat GBM, then requiring
oriented along-strike line coherence of the belief, recovers withheld whole
fault components with higher pooled HOLDOUT-DTI than the identical habitat
GBM without those channels, because expert-labelled new faults are plausibly
enriched for surface scarps / altered traces that the 100 m geophysical
bands dilute. **Named non-fault mimic:** fluvial terrace risers and Lake
Lahontan paleo-shoreline scarps (identical topographic dipoles) and
lithologic contacts (identical radiometric ratio steps).

## Shared tools (no private fork)

- Evaluator: `src/gemsdoe30/holdout.py::split_components` +
  `masked_dti_by_blocks` / `fp_weight_field`, `EVALUATOR_VERSION =
  component-holdout-v2-footprint-20261025` (this is the repo equivalent of
  the prompt's `evaluate_holdout.py`, which does not exist — IR-S20-03).
  Metric constants pinned by that module and the official page: α=0.2,
  β=0.8, 300 m triangular kernel, pooled sufficient statistics.
- Writer/validator: `src/gemsdoe30/submission.py::write_submission_file`,
  `scripts/validate_submission.py` (repo equivalent of `submission_writer.py`).
- Emitter: `src/gemsdoe30/emitter_opt.py::edge_select` (EDGE), driven exactly
  as in `scripts/lane_g30s19.py::emit_edge` (top-500 k belief pool,
  truth-mass = visible catalogue pixel count, max 120 k dots).
- Habitat feature construction: imported unchanged from
  `scripts/lane_g30s19.py` (band list, median/IQR normalisation fitted on
  eligible training pixels only, gradient/Laplacian/local-std/structure-
  tensor/edge-coincidence layers). Catalogue-distance layers it computes
  (`dist_visible_catalogue_px_capped`, `prox_exp_d10px`,
  `log1p_dist_visible_px`) are **excluded from every model**, as in S19-E3.
- Line coherence: new shared function
  `src/gemsdoe30/fields.py::line_coherent_belief` with unit tests, so the
  transform is fixed in the template, not in a private script copy.

## Holdout protocol (hide-and-recover, identical in E1/E2)

1. `split_components(catalogue, seed=31)` (E1) / `seed=47` (E2): whole
   8-connected fault components hidden, stratified within 3.2 km tiles.
2. Every catalogue-derived quantity (distance fields, support, eligibility,
   truth-mass prior, normalisation statistics) is computed from the
   **visible** (`known`) components only. Visible fault pixels are masked
   pixel-exactly out of scoring (`scored = valid & ~known`), mirroring the
   organizer's known-fault masking.
3. Training eligibility: all `known` positives; negatives sampled (same
   sampled pixel indices for every arm — paired) from
   `valid & dist(hidden)>3 px & dist(known)>3 px` (300 m buffer around both
   hidden truth and the unlabelled catalogue halo), ≤400 k negatives,
   `rng seed 7`.
4. Model: `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
   max_leaf_nodes=31, min_samples_leaf=200, l2_regularization=1.0,
   random_state=7)` — identical to S19. Prevalence correction and EDGE
   emission identical to S19. Support: `scored & dist(known)>2 px`
   (the winner-anatomy rule learned from H33, recomputed from visible only).
5. **Leakage canary first:** every candidate feature alone, AUC of hidden
   positives vs sampled scored negatives (negatives >3 px from hidden).
   Any feature with AUC >0.90 or <0.10 is flagged leakage-suspect and
   excluded from *all* arms before training; the canary table is a receipt.
6. Score: pooled HOLDOUT-DTI (`masked_dti_by_blocks`), reported with
   evaluator version, withheld-positive count, and 95 % CI from a
   hidden-component bootstrap (500 resamples, FP mass held fixed —
   conditional CI, stated as such). The paired arm difference gets the same
   bootstrap treatment.

## Arms (E1) and the predeclared selection rule

- **A — habitat control:** S19 habitat features only (≈ replication of the
  current best on the identical split).
- **B — combined:** A + external features listed below.
- **C — combined + line:** `line_coherent_belief` (16 orientations, length
  9 px, `B' = clip(√(B·Lmax), 0, 1)` on the prevalence-corrected belief)
  applied to B's belief.
- **D — habitat + line (diagnostic only):** line coherence applied to A.
  D can never become the candidate; it only attributes the line effect.

**Primary endpoint:** pooled HOLDOUT-DTI at matched **60,000 dots** (the
fixed budget transferred from the S19 holdout curve before E1 runs; EDGE
self-stop DTI is reported as a secondary endpoint).

**Candidate selection (frozen):** the candidate is **C** if C is the best of
{A, B, C} on the primary endpoint, else **B** if B beats A, else there is
*no candidate* and the lane is negative. No other arm, weighting, length,
orientation count, or dot budget may be tried after E1 is seen.

**Promotion gate (all must hold):**
1. E1: candidate@60 k − A@60 k ≥ **+0.005** pooled HOLDOUT-DTI.
2. E2 (fresh seed 47, candidate recipe vs A, trained identically):
   candidate@60 k − A@60 k **> 0**.
3. Canaries: no unexcluded candidate feature flagged (AUC>0.90 or <0.10).
4. Novelty: continuous belief surface *before* placement and final dots
   *after* placement vs every registry raster (9 pinned priority-site
   rasters + every distinct local download in `docs/downloads/`, including
   the promoted S19 Candidate C): Spearman ρ ≤0.90 and ≤70 % of final dots
   within 3 px of any single reference. Breach = duplicate: log and stop.
5. Validator: shared-writer output re-opened and verified (single band
   float32, EPSG:32611, 3730×3292, template transform, finite [0,1] inside
   footprint, no NaN inside; zeros-twin finite everywhere), 0 dots on the
   catalogue, 0 dots within 2 px of it, SHA-256 recorded.

A candidate that fails any gate is a **negative deliverable**: its TIFF may
still be published for education, labelled *do not submit*, and the
previously promoted S19 candidate remains the site's submit-this file.
Nothing in this lane allocates or spends a weekly submission slot; slot
selection is the owner's separate step.

## External feature list (frozen; band order verified at preflight or stop)

Lidar scarp stack (12-band uint8; `q=0` = no lidar ⇒ value 0 + explicit
`lidar_present`; decoded `t=(q−1)/254` clipped to [0,1] — monotone, so GBM
splits are unaffected by the owner's sqrt quantisation):
`t(ex_max), t(ex_mean), t(step_max), t(lapneg_max), t(lappos_max),
t(downface_max), t(upface_max), t(cross_max), t(relief), t(coh100),
lidar_present=(valid band>0), sin(2θ), cos(2θ)` with `θ=t(strike)·π`
(zero where absent), `scarp_dipole=√(t(lapneg)·t(lappos))`,
`step_x_coh=t(step_max)·t(coh100)`.

Radiometrics (uint8 `q/255`; all-zero column ⇒ `rad_present=0`, values 0):
`K, Th, U, TC, ThK, UK, UTh, TMI_up150, gradmag(TC), gradmag(ThK),
rad_present`. Gradient magnitudes are Sobel on the filled (absent→0) field,
zeroed where `rad_present=0`.

Excluded by design: every catalogue-distance feature; the GDR well/spring
`dist_known_fault_px` column (label-derived); `derived_gdr_qfaults_v2`,
`derived_sgmc_faults` and any other fault-vector raster (label-overlapping);
the sample template's values (footprint only).

## E3 production (only the selected recipe, unchanged hyperparameters)

If the E1 selection rule yields no candidate, E3 instead produces the lane's
designed arm **C** as an explicitly education-only artifact (the owner's
unique-TIFF requirement); its verdict remains negative regardless of E2.

Train on the full catalogue (positives = all catalogue pixels; negatives
`dist>3 px` halo-excluded, ≤600 k, seed 7), prevalence-correct, apply line
coherence iff the candidate is C, EDGE-emit, keep exactly **60,000 dots**,
support `footprint & ~catalogue & dist(catalogue)>2 px`. Write zeros-outside
(primary, whole array finite in [0,1]) and NaN-outside twins with the shared
writer; validate; novelty-check; publish run card. E3 runs **even if the
gate fails** (the owner requires a unique downloadable TIFF with an obvious
verdict), but a gate-failed E3 file is labelled *do not submit* everywhere.
