# POOL-1 preregistration — pooled MSDB∪CSR∪LiDAR feature lane (frozen 2026-10-27, before any fold fit)

**Lane (self-assigned, frozen here; no externally assigned method paragraph was supplied — IR-POOL-01).**
One pooled HistGradientBoosting model over the *union* of the two strongest previously
separate feature families in this repository — MSDB-1v2's 18 piedmont/curvilinear
features and CSR-1's 27 cover-compensated Laplace/Poisson + Radon features — plus the
17-band 1 m LiDAR morphology stack and the 13 stationary raw bands both parents share
(75 model features), calibrated (Prentice–Pyke case–control), multiplied by the MSDB
Rayleigh curvilinear-discontinuity gate, and emitted with CSR-1's 1D-ridge-concentrated
dispersed EDGE emitter (`γ=1.25`, `dr²+dc²>6`, >2 px off-catalogue, 44,090 dots).

## Why this lane, and why it is not a rerun of either parent

- MSDB-1v2 is the strongest comparable full-stack baseline on the shared evaluator
  (`component-holdout-v3-blockstats-20261025`): HOLDOUT-DTI 0.169986 (CSR-1 run) /
  0.170462 (original run), 60,988 withheld positives.
- CSR-1 (0.158162 pooled) *beat* `msdb_edge` by +0.02300 in Fold 3 (SE Walker Lane
  transtensional domain) but trailed in Folds 0–2. Its full expert excluded
  `det_elev` (band 11) and all 18 MSDB piedmont features; MSDB's model excluded all
  27 CSR subsurface/Radon features. **No prior lane in this repository has pooled
  MSDB-18 and CSR-27 in a single fitted model** (FFL-1 pooled MSDB+LiDAR only;
  CSR-1 used a dual-expert Noisy-OR that never saw MSDB features).
- A pooled tree ensemble can learn the regime interaction explicitly (e.g. split on
  `geod_shearrate` / `msdb_transtensional_index`, then weight CSR Radon/Laplace
  features in the high-shear branch and MSDB piedmont features elsewhere) — the
  CSR-2 regime-gating idea, learned rather than hand-gated.
- Named non-fault mimics: buried pluton/caldera margins, incised paleochannels,
  unreactivated Mesozoic contacts, saline playa clay pans, Lake Lahontan
  recessional shorelines, volcanic flow fronts.

## Ranked alternatives considered (frozen before fitting)

| Rank | Lane | Layers / signature | Why it could catch catalogue-missing faults | Status |
|---|---|---|---|---|
| 1 | **POOL-1 (this lane)** | 13 raw + MSDB-18 + CSR-27 + LiDAR-17 in one HGB | Combines the only two feature families that each beat core19 somewhere; trees learn regime gating | **Executed this session** |
| 2 | CSR-2 hand regime gate | CSR surface gated by geod_shearrate quantile onto MSDB surface | Directly encodes Fold-3 finding | Deferred — hand gate risks fold-label overfitting; POOL-1 subsumes it learnably |
| 3 | KRA-1 Riedel alignment | geodetic strain tensor × discontinuity strike | Low-relief Walker Lane accommodation faults | Deferred (named in CSR-1 prereg; new transform, higher cost) |
| 4 | MCD-1 MT clay-cap demagnetization saddle | cond_surf × RTP low × K/Th × paleo-springs | Blind hydrothermal conduits without scarps | Deferred — partially inside CSR features already |
| 5 | SLD-1 SGMC contact-projection discordance | USGS SGMC lithologic polygons | Sub-alluvial bedrock-contact offsets | Blocked — mrdata.usgs.gov unreachable from sandbox; needs owner-side rasterization |

## Frozen protocol (identical evaluator to MSDB-1v2 / CSR-1)

- Data: pinned owner mirrors restored 2026-10-27 (features sha256 `4371c82e…`,
  labels `7ba308cc…`, template `2176d08e…`); prepared cache verified cell-exact;
  `dataset_signature = 291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`.
  External pins: GeoDAWN rad/extensions + 3DEP LiDAR u8 stacks (mirror-pins-extra.json).
- Folds: `gemsdoe30.holdout.spatial_segment_folds`, 4 buffered whole-component
  quadrant folds, guard 17 px (> 16 px CSR support), 60,988 withheld positives total.
- Scoring: `masked_dti_by_blocks` (α=0.2, β=0.8, 300 m triangular kernel, known
  faults masked pixel-exactly) + `spatial_bootstrap` (371 geographic blocks,
  2,000 paired replicates, bootstrap seed 4231).
- Arms (count-matched every fold): `msdb_edge` (standing bar, exact CSR-1-run
  construction), `pool_dense_edge` (diagnostic: pooled surface + dense EDGE),
  `pool_dispersed` (**candidate**: pooled surface + dispersed EDGE).
- Leakage canaries: all 81 stack features, each fold, raw + univariate-HGB
  bidirectional AUC; any > 0.90 = leakage stop.
- Seeds: primary 4201; confirmation 4219 (Experiment 2 runs **only if** Experiment 1
  passes); production seeds {4201} or {4201, 4219} if both pass (CSR-1 precedent).
- Promotion gate (both experiments): candidate − `msdb_edge` > 0 **and** paired 95%
  CI lower bound > 0; zero canary alarms. `pool_dense_edge` is a diagnostic ablation,
  not a required delta.
- Novelty gate (two-stage, `scripts/check_novelty.py` against
  `docs/research/2026-10-27-pool/registry.json`, sha256
  `5b6f77da636cd964a6a498cebb1cbd283f956e71cdf413529402bac5c078e9a5`:
  394 aligned rasters from 2026-10-27 HEAD clones of the nine priority sites,
  2 classified exclusions finite-subset-audited, 6 dense-parent calibration
  exclusions reported separately): pre-placement surface Spearman ≤ 0.90 vs every
  registry raster; final dots Spearman ≤ 0.90 **and** ≤ 70% of dots within 3 px of
  any single registry raster. Breach = duplicate-stop, no TIFF in `docs/downloads/`.
- Format gate: shared writer `gemsdoe30.submission`, all-finite whole-array [0,1]
  float32 single band, EPSG:32611, 3730×3292, exact template transform, 0 dots
  within ≤2 px of catalogue (prevents the portal "[0,1]" rejection class).
- Budget: ≤ 3 experiments, ≤ 7,200 s experimental wall-clock. No post-hoc retuning:
  any change to features, gates, emitter or budget after seeing fold scores is a new
  lane requiring a new preregistration.
- Every number labelled HOLDOUT-DTI (evaluator, withheld positives, 95% CI) or
  ORGANIZER-CONFIRMED. No leaderboard projection will be written as a score.
