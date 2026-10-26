# Preregistration — Lane `CSR-1`: Cover-Compensated 3D Laplace/Poisson & 1.8 km Radon Curvilinear Discontinuity with 1D Ridge-Skeletonized Dispersed Emission

- **Frozen UTC:** `2026-10-26T22:18:00Z` (written and SHA-256 hashed before any `CSR-1` transform execution, model fitting, or holdout evaluation)
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE30` / `arena/75c44635-gemsdoe30`
- **Lane ID:** `CSR-1` (`experiment_spec = "csr1"`)
- **Dataset signature:** `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`
- **Fresh 9-site live registry pin (`docs/research/2026-10-26-csr/registry.json`):** `cf8ccc608e01ed233b350b0b48fc6904c3ec1fd8f7517863dbf2ecc0a9f9d62b` (`374` snapshotted `docs/**/*.tif[f]` files across all 9 priority sites; `357` unique aligned footprint-complete rasters + `2` formally classified exclusions)

---

## 1. Four Ranked Untried Geological Hypotheses (Frozen Before Implementation)

### Rank 1 (Implemented in `CSR-1`) — Cover-Compensated 3D Laplace/Poisson Potential-Field & 1.8 km Radon Curvilinear Discontinuity + 1D Ridge-Skeletonized Dispersed Emission
1. **Exact layers used:**
   - Competition 19-band cube (`training_features.tif`, SHA-256 `4371c82e...`): `rtp` (band 1, derivatives only), `tmi_hg` (band 2, `nT/km`), `geod_2ndinv` (band 3), `iso_grav_anom_slope` (band 4), `tc` (band 5, verified GeoDAWN Radiometric Total Count), `geod_shearrate` (band 6), `geod_dilaterate` (band 7), `tmi_vg` (band 8, `nT/m` scaled `×1000` to `nT/km`), `iso_grav_anom_vg` (band 10 = `+dg/dy`), `det_elev` (band 11, local curvature/coherence only — never raw elevation DC level), `iso_grav_anom` (band 12, Poisson vertical derivative only — never raw DC level), `depth_to_base_surf` (band 14, cover thickness `z` in `m`), `cond_surf` (band 16), `iso_grav_anom_hg` (band 17 = `+dg/dx`), `det_elev_slope` (band 18).
   - SHA-pinned official public-domain USGS GeoDAWN (`DOI: 10.5066/P92R3KTC`) & USGS 3DEP 1 m LiDAR rasters (`docs/research/mirror-pins-extra.json`): `lidar_scarp_features_u8.tif` (`f5540e27...`), `geodawn_rad_u8.tif` (`2997223e...`, `K, Th`), `geodawn_extensions_u8.tif` (`ad08a384...`, `TMI_up150`).
2. **Physical signature / transform (`SUPPORT_PX = 16 <= 17 px` guard; exact analytic Euclidean reach `13.73 px`):**
   - *True 3D Laplace & Planar Poisson Gravity Vertical Derivatives:* Reconstruct horizontal vector `(g_x, g_y) = (band 17, band 10)`, compute Laplace second vertical derivative `d^2g/dz^2 = -(d_x g_x + d_y g_y)` zero-crossing crest, and compute first vertical gravity derivative `dg/dz = (g - K_{h=300m, R=800m} * g)/h` via the planar Poisson upward-continuation kernel to obtain true Miller & Singh (1994) gravity tilt `arctan2(dg/dz, |nabla_H g|)` and contact crest `cos(theta_g)`.
   - *Unit-Consistent (`1000× tmi_vg`) 3D Magnetic Tilt, Analytic Signal & Upward-Continuation Persistence:* Convert `tmi_vg` to `nT/km`, compute true magnetic tilt, zero-contour crest, Salem local inverse contact depth `|nabla_H theta_m|`, 3D analytic signal `log1p(sqrt(tmi_hg^2 + (1000 tmi_vg)^2))`, and deep-source persistence `|nabla_H TMI_up150| / (tmi_hg + 10 nT/km)`.
   - *Cover-Attenuation Compensation & Hydrothermal Demagnetization–Clay-Cap Coupling:* Multiply horizontal gravity and 3D magnetic discontinuity amplitudes by bounded upward-continuation inverse gain `G_cover(z) = clip(1 + z / 300 m, 1, 6)`, compute fractional basement step `|nabla_H log(z + 100 m)|`, and couple local high-pass magnetic lows (`max(0, -rtp_hp)`) with `|nabla_H cond_surf|`.
   - *Pre-Model 12-Azimuth 1.8 km Flank-Subtracted Radon Line-Integrals:* Integrate cover-compensated gravity edge, unit-corrected magnetic crest-analytic signal, and fractional basement step along `L = 1.8 km` (`s in {-9,-6,-3,0,3,6,9} px`) minus `±300 m` parallel flanks across 12 azimuths (`0..165°`), extracting peak linear continuity, single-strike selectivity, orthogonal conjugate/stepover energy, and gravity–magnetic Radon strike concordance `cos^2(Delta theta^*)`.
   - *Cover-Decoupled Dual-Expert Noisy-OR + 1D Ridge-Skeletonized Dispersed EDGE (`r_min = 2.83 px`, `d_cat > 2 px`):* Combine a **topography-and-cover-level-blind subsurface expert** (`p_sub`, fit with inverse cover-censoring positive weights `w_pos(z) = clip(1 + z/400 m, 1, 3)`) with a **full structural-geomorphic expert** (`p_full`, excluding all 7 regional DC coordinate proxies) via Noisy-OR `1 - (1 - p_full)(1 - 0.35 p_sub)` × Rayleigh curvilinear gate; concentrate cross-strike blurred ribbons onto 1D ridge axes (`gamma = 1.25`) and emit via submodular `edge_select` with hard `dr^2 + dc^2 > 6` (`>= 282.8 m`) inter-dot dispersion.
3. **Why it catches concealed faults missing from USGS/INGENIOUS:** Buried intra-basin graben/horst faults, sub-alluvial relay ramps, and concealed stepovers sit beneath `200–2,000 m` of Quaternary fill where surface slope is zero (`det_elev_slope ≈ 0`) and potential-field horizontal gradients are upward-continuation attenuated by `2–6×`. Cover-compensated 3D potential-field derivatives + `1.8 km` Radon continuity + a cover-blind subsurface Noisy-OR expert prevent flat playas from vetoing buried structures, while `>= 282.8 m` 1D ridge dispersion stops wasting 35–45% of the dot budget double-tiling already-mapped range fronts.
4. **Non-fault mimics:** Buried pluton/caldera margins, incised paleochannels, unreactivated Mesozoic contacts, saline playa margins, and Lake Lahontan shorelines. Mitigated by `1.8 km` single-strike Radon selectivity, `TMI_up150` deep-source persistence, and active transtensional strain context.
5. **Difference from all prior `GEMSDOE30` code:** Fixes `PTA-1`/`G30-TAD`'s `dg/dy`-as-`dg/dz` gravity-tilt bug (`IR-PTA-03`) with true Laplace SVD + Poisson `dg/dz`; fixes `MSDB-1v2`/`FFL-1`'s `1000×` `tmi_vg` unit collapse (`IR-PTA-01`); reverses `MSDB-1v2`'s `exp(-z/500 m)` shallow-only filter with inverse cover compensation; introduces pre-model `1.8 km` flank-subtracted Radon line integrals and cover-decoupled Noisy-OR dual experts; and replaces `1-px` ribbon-packing `edge_select` with cross-strike ridge concentration + `>= 2.83 px` dispersion.

### Rank 2 — Kinematic Conjugate Riedel & Walker Lane Sinistral-Dextral Accommodation Tensor Alignment (`KRA-1`)
- **Layers:** `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `(iso_grav_anom_hg, iso_grav_anom_vg)`, `rtp`, `lidar_scarp_features_u8` (`strike`, `coh100`).
- **Signature:** Angular Mohr-Coulomb / Andersonian slip compatibility between observed local discontinuity strike `theta(x)` and predicted NW dextral Riedel (`R`), ENE clockwise-rotating sinistral conjugate (`R'`), and NNE extensional (`T`) planes partitioned by `dilate / (2ndinv + eps)`.
- **Why uncatalogued:** ENE sinistral-oblique accommodation faults (Carson, Olinghouse, Excelsior/Candelaria domains) have low vertical scarp relief despite high active shear/geothermal dilation.
- **Non-fault mimic:** Pre-Cenozoic metamorphic foliation or fold axes; mitigated by high geodetic strain invariant + sharp density gradient.
- **Difference from repo:** `MSDB-1v2` computed only scalar `dilate * shear / inv2` without testing strike-azimuth kinematic compatibility.
- **Rank rationale:** Lower standalone gain (`+0.003–0.008`) because the 19-band export provides scalar invariants rather than principal strain azimuths.

### Rank 3 — Magnetotelluric Smectite Clay-Cap Demagnetization + Epithermal K/Th & Paleogeothermal Sinter Saddle (`MCD-1`)
- **Layers:** `cond_surf`, `rtp`, `tmi_hg`, `TMI_up150`, `K, Th` (`geodawn_rad_u8`), and DOE GDR 1391 `derived_gdr_paleo_100m_u8.tif` (sinter/tufa deposits, CC BY 4.0, DOI `10.15121/1881483`, verified in `data/external/`).
- **Signature:** Coincident hydrothermal magnetite destruction (`-rtp` high-pass trough + depressed `tmi_hg`), conductive smectite clay-cap boundary (`|nabla_H cond_surf|`), potassic `K/Th` enrichment, and paleogeothermal sinter/tufa proximity.
- **Why uncatalogued:** >75% of Great Basin geothermal systems (e.g., McGinness Hills, Desert Peak, Salt Wells) are structurally controlled by blind stepovers lacking Quaternary surface scarps.
- **Non-fault mimic:** Saline evaporite playas (low magnetic anomaly + high electrical conductivity); mitigated by requiring linear gravity/basement steps.
- **Difference from repo:** `residual_gate.py` restricted `-rtp` to `<= 400 m` of known traces; `GDX-1` used well chemistry rather than demagnetization × MT clay-cap × sinter coupling (`core demagnetization × conductivity` term is incorporated as feature `csr_demag_claycap_index` inside Rank 1).

### Rank 4 — USGS SGMC Lithologic Unit-Contact (`Qa / Tv / Mz`) Sub-Alluvial Projection Discordance (`SLD-1`)
- **Layers:** Official free USGS SGMC (`NV.zip`, `CA.zip`, public domain, `https://mrdata.usgs.gov/geology/state/`) `SGMC_Geology` lithologic polygons (strictly excluding `SGMC_Structure` fault polylines) + `(iso_grav_anom_hg, iso_grav_anom_vg)`, `rtp`, `depth_to_base_surf`.
- **Obtainability verification:** `data/external/external_receipt.json` confirms `NV.zip` and `CA.zip` are free public-domain archives, but `mrdata.usgs.gov` is blocked from the session sandbox and only `derived_sgmc_faults_100m_u8.tif` (fault lines, unusable as features due to catalogue leakage) was committed by the prior runner workflow. Requires a future GitHub Actions run to rasterize `SGMC_Geology` lithologic polygons (`Qa/Tv/Mz`).

---

## 2. Frozen Experimental Protocol, Comparators, Budgets & Hard Gates

1. **Evaluator & Holdout Split (`gemsdoe30.holdout`):**
   - `spatial_segment_folds(labels, valid, buffer_px=17)` (`protocol_version = "buffered-quadrant-whole-components-v1-20261025"`, `evaluator_version = "component-holdout-v3-blockstats-20261025"`).
   - Whole 8-connected fault components assigned to 4 geographic quadrants; `17 px` (`1,700 m`) guard buffer around visible training quadrants exceeds `CSR-1` analytic support (`13.73 px <= 16 px`) + metric kernel (`3 px`).
   - Exact count-matched per-fold dot budget `round(44090 * active_pixels / total_valid_pixels)` across all arms (`DOT_BUDGET = 44,090`).
   - Paired spatial-block bootstrap (`2,000` replicates, `seed = 3137`, across `371` 6.4 km blocks) for 95% CIs on every arm and every pairwise difference.

2. **Arms Evaluated in Experiment 1 (`seed = 3101`):**
   - `core19_edge`: Baseline 19 competition bands (`HistGradientBoostingClassifier` + Prentice-Pyke calibration + standard `edge_select`).
   - `msdb_edge`: Standing promoted holdout benchmark (`MSDB-1v2` 31-feature stack + Rayleigh gate + standard `msdb` `edge_select`), refit in the identical folds & seed for exact paired bootstrap comparison.
   - `csr_dense_edge`: Ablation control (`CSR-1` dual-expert Noisy-OR × structural gate surface emitted via standard un-dispersed `edge_select`), isolating feature/model gain from emitter dispersion.
   - `csr_dispersed` (**Primary Candidate**): `CSR-1` dual-expert Noisy-OR × structural gate surface + cross-strike directional ridge concentration (`gamma = 1.25`) + dispersed submodular `edge_select` (`dr^2 + dc^2 > 6`, minimum inter-dot spacing `sqrt(8) = 2.828 px = 282.8 m`).

3. **Experiment Cap (`<= 3` experiments, `<= 2` hours):**
   - **Experiment 1:** 4-fold `gemsdoe30.holdout` evaluation + 4-fold bidirectional single-feature leakage canaries (`seed = 3101`).
   - **Experiment 2 (Confirmation, conditional on Experiment 1 passing primary gates):** Independent multi-seed confirmation (`seed = 3119`) comparing `csr_dispersed` vs `msdb_edge` on the same 4 spatial folds.
   - **Experiment 3 (Full-Footprint Production + Two-Stage Novelty + Validation):** Full-footprint fit (`seed = 3101` and `3119` averaged if Exp 2 passed; else single-seed `3101` research artifact), Stage-1 continuous-surface novelty audit (`Spearman <= 0.90`), `d_catalogue > 2.0 px` dispersed `44,090`-dot placement, strict whole-array `[0, 1]` GeoTIFF validation, and Stage-2 final-dot novelty audit (`Spearman <= 0.90` AND `3-px overlap <= 0.70` across all `357` aligned rasters + `2` audited exclusions).

4. **Frozen Pass / Stop Criteria (Zero Post-Hoc Adjustment):**
   - **Leakage Canary Gate:** Every candidate/comparator feature must satisfy `max(raw_auc, 1 - raw_auc, uni_hgb_auc, 1 - uni_hgb_auc) <= 0.90` in all 4 folds. Any violation halts immediately (`verdict = "negative"`).
   - **Holdout Improvement Gate:** `csr_dispersed` must beat **both** `core19_edge` and `msdb_edge` in Experiment 1 (`seed = 3101`) with paired spatial-block 95% CI lower bound `> 0.0`, **and** reproduce `csr_dispersed - msdb_edge > 0` with paired 95% CI lower bound `> 0.0` in Experiment 2 (`seed = 3119`).
   - **Two-Stage Novelty Gate:** Pre-placement continuous surface `max |Spearman| <= 0.90` and post-placement dots `max |Spearman| <= 0.90` and `max candidate_fraction_within_3px_of_reference <= 0.70` across all `357` aligned rasters in `docs/research/2026-10-26-csr/registry.json` (plus finite-subset check on malformed exclusions). Exceeding either threshold triggers immediate duplicate-stop (`verdict = "negative"`, `ok_to_submit = False`).
   - **Selector Discipline (Protocol Rule 7):** No portal upload or slot selection is ever performed automatically (`submission_approved = False`, `slot_selected = False`).
