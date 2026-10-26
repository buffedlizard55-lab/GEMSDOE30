# Preregistration — Lane `FFL-1` (2026-10-26): MSDB×LiDAR fusion surface with catalogue-distance-stratified far-field emission

- **Date (UTC):** 2026-10-26. Frozen before any FFL-1 fold was fitted or scored.
- **Lane assignment:** The owner prompt's parallel-run protocol says "Your lane is the
  single method paragraph below" but supplies no method paragraph (already logged as
  IR-30-078). This lane is therefore **self-assigned and frozen here**, following the
  explicit next-step recommendation in `docs/research/2026-10-25-lsm/review.md` §5
  (items 2–3: far-field distance-stratified allocation, validated on the v3 holdout).
  No other lane in this repository combines (a) the MSDB-1v2 stationary physics stack,
  (b) 1 m-DEM LiDAR scarp morphology, and (c) distance-stratified emission quotas.
- **Budget:** ≤3 experiments, ≤2 h experiment compute (owner parallel-run protocol §6).
  Experiment 1 = feature fusion (2 arms). Experiment 2 = stratified emission on the
  Experiment-1 fusion surface (no refitting). Experiment 3 is reserved and will not be
  used for tuning; if Experiments 1–2 fail their gates, Experiment 3 stays unspent.
- **Shared tools only:** `gemsdoe30.holdout` (`spatial_segment_folds`,
  `masked_dti_by_blocks`, `spatial_bootstrap`; evaluator
  `component-holdout-v3-blockstats-20261025`), `gemsdoe30.msdb`,
  `gemsdoe30.lidar_morphology`, `gemsdoe30.emitter_opt`/`emission`,
  `gemsdoe30.submission` (shared writer/validator), `scripts/check_novelty.py`,
  and the shared sampler/predictor in `scripts/feature_value_holdout.py`.
  There is no `evaluate_holdout.py`/`submission_writer.py` in this repo; the two
  modules above are their equivalents and are used unchanged except for the new
  experiment contract added to `gemsdoe30.experiments` (reported in `review.md`).
- **Labels:** Every number is `HOLDOUT-DTI` (evaluator, withheld positives, 95% CI) or
  `ORGANIZER-CONFIRMED` (organizer receipt). All fleet scores in the nine-site summary
  are `OWNER-REPORTED UNVERIFIED` (no organizer receipt exists in this repo).

## 1. Why H33 (0.2778, OWNER-REPORTED) topped the fleet — the design input

Byte-exact lineage verified in `docs/research/2026-10-25-lsm/why-h33-scored-0.2778.md`:
`h19-5` support (0.1922) → Poisson `d=2.8` thinning (D2.8, 0.2600) → drop dots at
distance 1 px (r1, 0.2708) → drop dots at distance ≤2 px (**H33-B2, 0.2778**).
All variants cover the same ≈40.5% of hidden truth (projection from owner-reported
scores); H33 wins by wasting the fewest dots. Leaderboard differentials (projections)
show the ≤2 px band earns ≈0.002 hits/dot and near-catalogue geometric additions earn
≈random (0.023) or less, while H33's overall rate is 0.134 hits/dot. Two consequences
are frozen into this lane: (i) **no dots within 2 px of the catalogue**, and
(ii) dot budget must be **reallocated toward catalogue-distant strata**, where the
MSDB-1v2 production raster is severely under-allocated (measured on
`gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif`: 18.2% of dots at ≤2 px,
only 5.4% at 30–50 px and 4.2% at >50 px, despite 959,149 and 1,066,471 eligible
pixels in those strata).

## 2. Ranked hypotheses (untried as specified in this repository)

| Rank | Hypothesis | Layers / physical signature | Why it can catch a fault missing from USGS/INGENIOUS | Difference from prior repo work | Expected ΔDTI (planning prior) / cost |
|---|---|---|---|---|---|
| 1 (Exp 1) | **MSDB×LiDAR fusion** | MSDB-1v2 31 stationary features (true Miller–Singh magnetic tilt `arctan2(tmi_vg,tmi_hg)`, Salem tilt-depth, reconstructed `(dg/dx,dg/dy)` strike concordance, Hessian tubularity/saddle at 100–300 m, piedmont ramp, GeoDAWN TC gradient) + 17 LiDAR layers decoded from the 12-band 100 m descriptor stack of USGS 3DEP 1 m DEMs (`step_max`, crest–toe dipole `√(LoG⁻·LoG⁺)`, facing step, scarp-vs-channel ratio, 5×5 axial strike persistence) | 1:24k–1:250k compilations miss short (≲1 km), low (≲2–3 m) scarps; 1 m LiDAR resolves them, and the MSDB potential-field context down-weights non-tectonic steps | LSM fused LiDAR with raw19+6 geo edges (HOLDOUT-DTI 0.1572) but never with the corrected MSDB physics; MSDB never saw LiDAR. No catalogue-distance input in either | +0.005…+0.020 / low (cached stacks exist) |
| 2 (Exp 2) | **Distance-stratified far-field emission (FF-STRAT)** | Same gated fusion surface; emission quotas across Euclidean distance-to-catalogue strata (frozen below), Poisson r=3.0 px within stratum | Expert "new faults" include splays/continuations (forum t/11536) but the leaderboard differentials show near-catalogue dots earn ≈0; hidden truth must be sampled where prior lanes barely place dots (>3 km: MSDB 4.2% of dots) | All prior emitters (EDGE, Poisson, lattice) allocate globally by belief; LSM review §5 proposed stratification but no lane ran it | +0.000…+0.015 on leaderboard (projection); catalogue-proxy effect unknown a priori / very low |
| 3 (not run) | **Radiometric endmember unmixing × lineament coherence** | GeoDAWN K/eU/eTh float grids (USGS, DOI 10.5066/P93LGLVQ, CC0 — catalog verified reachable in prior sessions); log-ratio endmember residual required to persist along a 300–700 m lineament | Hydrothermal alteration halos can mark concealed faults with no scarp | S20 used quantised ThK/UK/UTh ratios as ordinary HGB inputs; an endmember-residual × coherence transform was never implemented | +0.001…+0.012 / low–medium |
| 4 (not run) | **Pluvial-shoreline rejection** | USGS 3DEP 1/3″ DEM absolute elevation (TNM Access API returned 32 public-domain 1 m products for a test bbox, LSM review §7); reject LiDAR steps following a constant-elevation contour near the Lahontan highstand (~1,330 m) | Removes the dominant LiDAR non-fault mimic, raising precision of scarp dots in piedmont basins | Never implemented; needs an Actions-bridge fetch (sandbox cannot reach USGS) | +0.000…+0.008 / medium |
| 5 (not run) | **MT/heat-flow upflow saddle** | INGENIOUS MT conductance (DOI 10.5066/P9TWT2LU) + heat flow (10.5066/P9BZPVUC), CC BY 4.0 via GDR 1391; conductive saddle + magnetic magnetite-destruction trough coincidence | Blind upflow (Faulds: ~39% of Great Basin systems are blind) can sit over unmapped faults | Prior work used `cond_surf/cond_2km` as raw inputs only; no saddle/trough coincidence transform | +0.001…+0.010 / medium |

**Named non-fault mimics (primary lane):** Lake Lahontan paleo-shorelines and playa
benches; fluvial terrace risers/channel banks; volcanic lava-flow fronts; intrusive
pluton contacts; roads, canals and mines; lithologically contrasting bajada catchments.

## 3. Frozen Experiment 1 — feature fusion

- Folds: `spatial_segment_folds(labels, valid, buffer_px=17)`; 60,988 withheld
  positives; catalogue-based features derive only from each fold's `visible` faults;
  visible faults masked pixel-exactly in scoring (`masked_dti_by_blocks`,
  α=0.2, β=0.8, 300 m triangular kernel, pooled).
- Arms (count-matched per fold, `count = round(44090 × |active| / |valid|)`,
  `active = score_valid & ~visible`):
  1. `msdb_edge` — 31-feature MSDB model (13 retained raw + 18 MSDB), HGB
     (200 iter, lr 0.06, 31 leaves, min_samples_leaf 100, l2 1.0, seed 3051+fold),
     Prentice–Pyke Bayes calibration × fold-local Rayleigh gate, `edge_select`.
  2. `fusion_edge` — identical recipe plus the 17 LiDAR layers (48 model features).
- Leakage canaries: every input channel (19 raw + 18 MSDB + 17 LiDAR = 54) alone per
  fold (raw bidirectional AUC and training-only univariate HGB AUC); alarm if >0.90.
- Statistics: pooled HOLDOUT-DTI per arm; paired 128-px geographic-block bootstrap,
  2,000 replicates, seed 3071.
- **Gate (all required):** `fusion_edge − msdb_edge > 0` with paired 95% CI lower
  bound > 0; zero canary alarms; per-fold emitted counts exactly matched.

## 4. Frozen Experiment 2 — stratified far-field emission (only if Exp 1 passes)

- Same fold gated fusion surfaces as Experiment 1 (saved before Exp 1 scoring;
  no refitting, no new parameters except the frozen quotas below).
- Strata by Euclidean distance to the fold's **visible** catalogue (production: full
  catalogue), eligible domain `active & (distance > 2 px)`:
  `(2,5] px: 14%`, `(5,10] px: 15%`, `(10,30] px: 34%`, `(30,50] px: 16%`,
  `>50 px: 21%` of the fold count (largest-remainder rounding to the exact count;
  shares are the H33 distance profile from `leaderboard-calibration.json`,
  renormalised after removing its ≤2 px band, with 11–30 px merged).
  Within each stratum: `poisson_disk_select_ordered(surface, 3.0, mask=stratum)`
  in descending surface order. Spacing is enforced within strata (preregistered;
  cross-boundary pairs closer than 3 px are possible and conservative).
- **Gate:** `fusion_ffstrat − fusion_edge > 0` (point estimate) **and**
  `fusion_ffstrat − msdb_edge > 0` with paired 95% CI lower bound > 0.
  If the stratified arm fails, the production emission falls back to `fusion_edge`
  only if Experiment 1 passed; the stratified result is still reported.

## 5. Production (only from passing arms)

- Full-catalogue fusion fit (seed 3051), Bayes calibration, Rayleigh gate.
- Surface novelty first: Spearman vs every raster in the pinned 9-site registry
  (166 restored files, `docs/research/msdb-piedmont/registry.json` copy); >0.90 ⇒ stop.
- Emission: Experiment-2 emission if it passed, else Experiment-1 EDGE emission;
  44,090 dots, 0 dots on catalogue pixels, 0 dots within 2 px of the catalogue
  (for the stratified arm this is by construction; for the EDGE fallback the
  eligible domain is `valid & ~labels & (distance > 2 px)` — a deviation from the
  MSDB-1v2 production domain, frozen here because of §1).
- Final-dot novelty: Spearman >0.90 or >70% of dots within 3 px of any registry
  raster ⇒ duplicate-stop (log and do not promote).
- **Portal contract (fixes the reported "[0, 1]" rejection):** the primary TIFF is
  written **finite everywhere: 0.0 outside the footprint, no NaN/Inf anywhere**,
  single-band float32, EPSG:32611, 3730×3292, template transform. Validator must
  confirm: no NaN inside footprint, all values in [0,1] over the **whole array**,
  CRS/shape/transform match. (Owner-reported scores exist for `-zeros` files,
  including H33 0.2778; no organizer receipt is claimed.)
- Verdict `promote` requires: both applicable holdout gates, canaries, novelty,
  and validator all pass. `promote` means eligible for the separate weekly-slot
  selector (≤3/week, rules §3.4); it does **not** spend a slot. Anything else is
  `negative` and the site must say DO NOT SUBMIT in the first screen.
