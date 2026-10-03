# Preregistration: H-33-01 Placement-Policy Holdout, H-31-02r LiDAR Scarp Continuity, and H-32-05b Spacing-Matched Retry

**Frozen:** 2026-10-03 (before executing `scripts/placement_and_scarp_holdout.py`) ·
**Status:** preregistered protocol · **Output:** `docs/research/h33-01-placement-and-scarp-holdout.json`
and `docs/research/h33-01-placement-and-scarp-holdout.md`.

---

## 1. Motivation and methodological corrections (IR-30-029, IR-30-033)

Three consecutive component-holdout tests in earlier sessions (`H-31-01` relay connector,
`H-32-01` vent corridors, `H-32-05` buried basement edges) failed against their
`random_near_matched` controls (~0.029 DTI at `N = 15,000`), leading `README.md` and
`docs/hypotheses.md` to designate a **placement-policy** test (how a fixed dot budget is
allocated across distance-to-known-fault strata) and the **H-31-02 reduced matched-filter
scarp arm** as the next experiments.

Before running those tests, a line-by-line audit of `scripts/basement_edge_holdout.py` and
`scripts/vent_corridor_holdout.py` identified three methodological confounders that this
preregistration fixes:

1. **IR-30-033a (Un-thinned pixel clumping vs dispersed random control):** In
   `scripts/basement_edge_holdout.py`, `top_n_emission` selected the top 15,000 pixels of a
   smooth gradient surface without Poisson-disk thinning (`median nearest-neighbour distance =
   1.0 px`, with `99.987 %` of emitted pixels within 300 m of another emitted pixel), whereas
   `random_near_matched` drew 15,000 dispersed random pixels (`median NN distance = 8.94 px`,
   only `7.47 %` within 300 m). Under the official 300 m max-kernel DTI, contiguous pixels
   cannibalize ~90 % of their own 300 m kernel support while paying full false-positive weight.
   **Correction:** Every arm and every control in this protocol uses **300 m (`r = 3.0 px`)
   Poisson-disk spacing** at identical dot count `N = 15,000`.
2. **IR-30-029 (Structure-tensor scale mismatch on smooth regional surfaces):** In `H-32-05`,
   a `3×3` (300 m) structure tensor on `depth_to_base_surf` passed `99.65 %` of footprint
   pixels at `coherence >= 0.5` because any smooth regional surface is locally planar over
   300 m (`∇z` nearly constant). **Correction:** In `H-32-05b`, we compute the **cross-gradient
   step ridge** (positive Laplacian perpendicular to the gradient) and evaluate structure-tensor
   coherence over a **1.5 km (`15×15` px) range-front window**, gating at the **90th percentile
   (`p90`)** inside the valid footprint.
3. **IR-30-033b (Target-mask leakage in emittable support):** `vent_corridor_holdout.py`
   defined `emittable = valid & ~known & ~hidden`, excluding held-out truth pixels from the
   emittable pool. **Correction:** The emittable support is strictly `valid & ~dilate(known, 3 px)`
   (matching the organizer's 300 m known-fault masking rule and never consulting `hidden`).

---

## 2. Experiment 1 (`H-33-01`) — Spatial placement policy across distance-to-catalogue strata

* **Question:** How does a fixed budget of `N = 15,000` Poisson-disk dots (`r = 3.0 px`) score
  when allocated across distance-to-known-fault strata (`d_known`) on (a) the catalogue
  component-holdout frame, (b) the independent USGS SGMC off-catalogue component-holdout frame,
  and (c) a **spatially clustered (5 km regional disc)** SGMC holdout frame?
* **Strata (all restricted to the unmasked domain `d_known > 300 m`):**
  1. `policy_near_splay`: 100 % of dots in `300 m < d_known <= 1,500 m` (splays, parallel
     strands, tip extensions of mapped fault zones).
  2. `policy_mid_relay`: 100 % of dots in `1,500 m < d_known <= 4,000 m` (step-overs, relay
     ramps, piedmont faults).
  3. `policy_far_basin`: 100 % of dots in `d_known > 4,000 m` (blind intra-basin faults).
  4. `policy_powerlaw_hedge`: 60 % in `300–1,500 m` (9,000 dots), 25 % in `1,500–4,000 m`
     (3,750 dots), 15 % in `> 4,000 m` (2,250 dots).
  5. `policy_uniform_domain`: unstratified Poisson-disk draw across all `d_known > 300 m`
     (control).
* **Pre-stated promotion gate (`H-33-01`):** A placement policy is promoted only if it beats
  `policy_uniform_domain` by `>= +0.002` pooled DTI on **both** the catalogue component-holdout
  frame AND the independent SGMC novelty frame (unclustered and clustered) on both screen
  (`seed = 31`) and confirmation (`seed = 41`). (If a policy wins on the catalogue frame but
  loses on the independent SGMC frame, that divergence is recorded as a structural proxy
  diagnostic and no slot is spent.)

---

## 3. Experiment 2 (`H-31-02r`) — Reduced matched-filter LiDAR scarp dipole + strike-continuity arm

* **Layers:** `data/raw/external/lidar_scarp_features_u8.tif` (USGS 3DEP 1 m DEM derived bands:
  `step_max` band 3, `lapneg_max` band 4, `lappos_max` band 5, `coh100` band 10, `strike`
  band 11, `valid` band 12) + competition `det_elev_slope` (band 19).
* **Physical signature:** Normal-fault scarps in unconsolidated Basin-and-Range alluvium exhibit
  paired convex-crest (`lapneg_max`) and concave-toe (`lappos_max`) curvature across a finite
  step (`step_max`) that persists along a consistent strike azimuth (`strike`, `coh100`) over
  500 m (`5×5` px window weighted by `cos(2·Δθ)`), corroborated by `det_elev_slope` where 1 m
  LiDAR coverage is absent (`24.6 %` of footprint).
* **Arms (all emitted at `N = 15,000` dots with `r = 3.0 px` Poisson-disk spacing on
  `d_known > 300 m`):**
  1. `scarp_dipole_continuity` (primary): rank-sum of the strike-coherent scarp dipole index
     `sqrt(lapneg_max · lappos_max) · step_max · coh100 · strike_persistence_500m` and
     `det_elev_slope`.
  2. `scarp_dipole_near_hedge`: same score restricted to the `policy_powerlaw_hedge` stratum
     weights (`60 / 25 / 15 %` across near/mid/far).
  3. `step_max_only` (transform ablation): first-order `step_max` (+ `det_elev_slope` fallback)
     without the crest-toe dipole or 500 m strike-continuity operator.
  4. `scarp_matched_control`: Poisson-disk (`r = 3.0 px`) random dots matched to
     `scarp_dipole_continuity`'s `distance_to_known` decile profile (`N = 15,000`).
* **Pre-stated promotion gate (`H-31-02r`):**
  1. Screen (`split_seed = 31`, `N = 15,000`): pooled ΔDTI vs `scarp_matched_control`
     `>= +0.002`;
  2. Quadrant sign consistency: `>= 3 of 4` quadrants positive vs `scarp_matched_control`;
  3. Confirmation (`split_seed = 41`, `N = 15,000`): pooled ΔDTI `> 0` vs
     `scarp_matched_control`;
  4. Transform clause: `scarp_dipole_continuity` > `step_max_only` on both splits.

---

## 4. Experiment 3 (`H-32-05b`) — Spacing-matched buried basement step ridge with p90 1.5 km coherence

* **Layers:** Competition bands `depth_to_base_surf`, `iso_grav_anom_hg`, `tmi_hg`.
* **Physical signature:** Cross-gradient step ridge of `depth_to_base_surf` (where gradient
  magnitude `|∇z|` is both large and locally ridge-peaked across strike), gated by the **90th
  percentile (`p90`, selecting ~10 % of footprint pixels)** of 1.5 km (`15×15` px)
  structure-tensor coherence on the ridge field, corroborated by `|iso_grav_anom_hg|` and
  `|tmi_hg|`, emitted with `r = 3.0 px` Poisson-disk spacing (`N = 15,000`).
* **Arms (`N = 15,000`, `r = 3.0 px` Poisson-disk):**
  1. `basement_step_ridge_p90` (primary): p90-gated 1.5 km coherent basement step ridge +
     gravity/magnetic horizontal gradients, Poisson-thinned at `r = 3.0 px`.
  2. `basement_unthinned_legacy` (diagnostic reproduction): un-thinned `top_n_emission` from
     `H-32-05` to measure the exact DTI recovery from fixing pixel clumping (`IR-30-033a`).
  3. `basement_matched_control`: Poisson-disk (`r = 3.0 px`) random dots matched to
     `basement_step_ridge_p90`'s `distance_to_known` decile profile (`N = 15,000`).
* **Pre-stated promotion gate (`H-32-05b`):**
  1. Screen (`split_seed = 31`): pooled ΔDTI vs `basement_matched_control` `>= +0.002`;
  2. Quadrant sign consistency: `>= 3 of 4` quadrants positive;
  3. Confirmation (`split_seed = 41`): pooled ΔDTI `> 0` vs `basement_matched_control`.
