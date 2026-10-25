# G30-LSM E3 amendment — crest-line (ridge) emission of the frozen lsm42 belief

**Frozen:** 2026-10-25 (UTC), after E1/E2 and the frame-validity diagnostic, before any E3 computation.
This is the third and final experiment allowed by the budget. E1/E2 results are unchanged. **No feature, model,
seed, fold or budget of `lsm42` is altered.** Only the dot-placement rule is tested.

## Motivation (from observed E2 diagnostics, not from E3 outcomes)

* At equal budget (about 38 k dots) on the independent SGMC-new frame, H33 earns TP 5,400 and lsm42 earns 4,158 at similar FP.
  The h-family places dots on topographic and geophysical *ridges*: lines.
* Poisson-disk maxima of a smooth pixelwise probability surface fill high-probability *zones*.
* Faults are lines, so dots on zone flanks pay FP and earn little TP.
* The SGMC frame itself is not a valid leaderboard proxy:
  * its overall Spearman with owner scores is −0.18 (n = 19);
  * the label-blind lattice tops it.
  * It is therefore reported, not gated.

## Hypothesis H-LSM-1r

Restricting dot candidates to crest lines of the frozen lsm42 surface raises HOLDOUT-DTI at a fixed budget.

**Crest-line definition.** The surface is Gaussian-smoothed with σ = 1 px, and the Hessian is computed with σ = 1 px Gaussian derivatives. A crest pixel must satisfy both:
* the most negative Hessian eigenvalue is < 0;
* P(x) ≥ P at both neighbours along that eigenvector, using quantised 8-neighbour directions.

**Placement.** Same as before: values P, Poisson-disk r = 3.0, identical budgets and masks, with candidates limited to the crest pixels.
**Mimic.** The flanks of broad high-probability zones (range-front aprons, basin margins) where no single trace exists.

## Frozen protocol

**E3a — v3 spatially blocked holdout**
* Identical to E1: the same folds, the seed 3070 + fold models, and the lsm42 features.
* Both arms use the **same lsm42 predictions** in each fold. Arms:
  * `lsm42` — plain emission; the E1 values must reproduce exactly;
  * `lsm42_ridge` — crest-line emission.
* Emissions: primary (44,090 TDX-1-exact) and production (38,000, more than 2 px from the visible catalogue).
* Statistics: paired spatial-block bootstrap, 128 px blocks, 2,000 replicates, seed 3071.
* **Gate (promotion of the ridge emission):**
  1. `lsm42_ridge − lsm42` > 0 with paired 95 % CI lower bound > 0 under the primary emission;
  2. production-emission point estimate ≥ `lsm42`;
  3. capacity — every fold supplies its exact count.

**E3b — SGMC-new frame (reported, not gated)**
* Production surface `surface_lsm42.npy`, 38,000 crest dots, compared with lsm42-plain, H33 and D2.8 via a paired bootstrap.

**Decision rule**
* If the E3a gate passes, the production artifact becomes the crest-line emission. Its novelty and format gates are re-run.
* Otherwise the E1-promoted plain lsm42 artifact stands.
* Either outcome is reported, and no further variants are run.
