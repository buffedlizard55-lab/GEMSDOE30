# Preregistration — Lane `G30-TAD`: Translation-Invariant Tilt-Depth, Hydrothermal Alteration, and Dip-Slip Scarp Discontinuity Field with Observability-Decensored Emission

**Frozen UTC date:** `2026-10-25` (committed and SHA-256-locked in `registration.json` **before** any `G30-TAD` feature array, model fit, canary, holdout score, or novelty comparison is executed).  
**Lane status:** Self-assigned single method lane (`IR-TAD-01`: owner prompt specifies `"Your lane is the single method paragraph below. Stay inside it."` without an attached method paragraph).  
**Hard budget (Parallel-Run Protocol Rule 6):** At most **3 experiments** (`E1`, `E2`, `E3`) and **2 hours (`7,200 s`)** wall-clock experiment compute. Zero competition submission slots selected (`slot_selected = false`).

---

## 1. Scientific Hypothesis, Physical Mechanism, and Non-Fault Mimic

- **Hypothesis (`H-TAD-1`)**: Removing the 12 long-wavelength regional coordinate-proxy levels of `core19` and replacing them with 17 strictly translation-invariant local potential-field tilt-depth, 150 m upward-continuation vertical persistence, fold-safe lithology-normalized K–Th–U hydrothermal alteration, MT clay-cap lateral conductance boundary, 1 m LiDAR one-sided dip-slip polarity, basement-strike lock, and bounded hydrothermal sinter/probe/geothermometer conduit features (`tilt_alt24`, 24 total translation-invariant inputs = 7 competition derivatives + 17 derived local operators) improves cross-province whole-component fault recovery (`HOLDOUT-DTI`) over `core19`, `subsurface16`, and `random_dispersed` on buffered spatial quadrants (`evaluator_version = component-holdout-v3-blockstats-20261025`), while pairing its out-of-fold cross-quadrant belief with an observability-decensored `30% / 40% / 30%` distance-collar emission policy (`d_cat > 2 px`, `38,000` dots at `3.0 px` spacing) avoids the `< 1 km` range-front crowding collision (`> 70%` 3-px dot overlap) that stopped `G30-S20`, `TDX-C2`, and `G30-LSM`.
- **Physical mechanism**:
  1. **Buried contact localization without depth-attenuation bias**: Potential-field tilt angle $\theta = \arctan(\partial_z f / |\nabla_h f|)$ crosses zero ($\cos\theta = 1$) directly above steep fault contacts independent of $z_0^{-2}$ amplitude decay, while $|\nabla_h\theta| \approx 1/z_0$ encodes sediment burial thickness (`Salem et al., 2007`) and `TMI_up150` vs `tmi_hg` vertical persistence (`Jacobsen, 1987`) suppresses surficial volcanic float.
  2. **Hydrothermal fluid-pathway alteration**: Fold-safe OLS regression of GeoDAWN potassium `K` on immobile thorium `Th` (`Saunders et al., 1993`; `Dickson & Scott, 1997`), Efimov's alteration index $\ln((K+1)(U+1)/(\text{Th}+5)^2)$, MT smectite clay-cap lateral conductance gradients, and paleogeothermal sinter / 2 m thermal-probe / Na–K–Ca > quartz geothermometer disequilibrium (`Fournier, 1977`; `Giggenbach, 1988`) detect blind hydrothermal fault conduits beneath unconsolidated cover.
  3. **Crustally rooted dip-slip micro-scarp geometry**: One-sided 1 m LiDAR face-polarity asymmetry $|\text{downface} - \text{upface}|$, sub-cell sharpness `ex_max - ex_mean`, and strike co-alignment $\cos(2(\phi_{\text{lidar}} - \phi_{\text{grav/rtp}}))$ isolate degraded dip-slip tectonic scarps from symmetric gullies and contour-parallel Lake Lahontan pluvial shorelines.
  4. **Positive-Unlabeled observability de-censoring**: Because field mapping censors basin/stepover faults ($o(x) \ll 1$) relative to exposed range fronts ($o(x) \approx 1$), deleting the barren `≤ 200 m` digitization halo (`H33` mechanism) and capping `200 m – 1 km` allocation at `30%` directs `70%` of dots into `1–3 km` stepovers (`40%`) and `> 3 km` concealed structural corridors (`30%`).
- **Named non-fault geological mimic**: Sub-vertical tilted welded ash-flow tuff / caldera ring-fracture lithologic contacts exhibiting primary vapor-phase potassic crystallization and differential caprock cuesta erosion.

---

## 2. Frozen Feature Specification (`src/gemsdoe30/tilt_alteration.py`, `SUPPORT_PX = 17`)

Every spatial filter uses footprint-normalized Gaussian convolution $G_\sigma^{\text{valid}}(f) = G_\sigma(\mathbb{I}_{\text{valid}}\cdot f) / \max(G_\sigma(\mathbb{I}_{\text{valid}}), 10^{-6})$ with `truncate = 3.0` (`mode = "constant", cval = 0.0`) so outside-footprint cells (`~valid`) never bleed into `valid`. Exact maximum Chebyshev impulse support across all 24 features is `15 px <= SUPPORT_PX = 17 px` (`1,700 m`, verified by unit impulse test). No label, template value, `dist_known_fault_px`, `sgmc_faults`, or `qfaults` layer enters any feature.

| Index | Feature Name | Group | Exact Mathematical Definition | Chebyshev Support (px) |
|---:|---|---|---|---:|
| 0 | `tmi_hg` | `subsurface16` | Competition band 2 (`tmi_hg`) | 0 |
| 1 | `tmi_vg` | `subsurface16` | Competition band 8 (`tmi_vg`) | 0 |
| 2 | `tc` | `subsurface16` | Competition band 5 (`tc`) | 0 |
| 3 | `iso_grav_anom_hg` | `subsurface16` | Competition band 17 (`iso_grav_anom_hg`) | 0 |
| 4 | `iso_grav_anom_vg` | `subsurface16` | Competition band 10 (`iso_grav_anom_vg`) | 0 |
| 5 | `iso_grav_anom_slope` | `subsurface16` | Competition band 4 (`iso_grav_anom_slope`) | 0 |
| 6 | `mag_tilt_cos` | `subsurface16` | $|\text{tmi\_hg}| / \sqrt{\text{tmi\_hg}^2 + \text{tmi\_vg}^2 + 10^{-6}}$ | 0 |
| 7 | `mag_salem_tilt_hgrad` | `subsurface16` | $3\times 3$ Sobel $|\nabla_h \theta_{\text{mag}}|$, $\theta_{\text{mag}} = \arctan2(\text{tmi\_vg}, |\text{tmi\_hg}| + 10^{-3})$ | 1 |
| 8 | `mag_buried_contact_score` | `subsurface16` | $\cos^2\theta_{\text{mag}} \cdot \exp(-|\nabla_h\theta_{\text{mag}}| / 0.35)$ | 1 |
| 9 | `mag_up150_persistence` | `subsurface16` | $u - G_{\sigma=4}^{\text{valid}}(u)$, $u = \ln(|\nabla_h\text{TMI}_{\text{up150}}| + 0.5) - \ln(|\text{tmi\_hg}| + 0.5)$ | 13 |
| 10 | `grav_tilt_cos` | `subsurface16` | $|\text{iso\_grav\_anom\_hg}| / \sqrt{\text{iso\_grav\_anom\_hg}^2 + \text{iso\_grav\_anom\_vg}^2 + 10^{-6}}$ | 0 |
| 11 | `mag_grav_tilt_strike_lock` | `subsurface16` | $\cos\theta_{\text{mag}}\cos\theta_{\text{grav}}\cos(2(\phi_{\text{rtp}} - \phi_{\text{grav}}))$, axial strikes from $f - G_{\sigma=3}^{\text{valid}}(f)$ + Sobel | 10 |
| 12 | `rad_kd_potassic_resid` | `subsurface16` | $(K - (\hat{a}_{\text{train}}\text{Th} + \hat{b}_{\text{train}})) / \max(\hat{a}_{\text{train}}\text{Th} + \hat{b}_{\text{train}}, 5.0)$, OLS strictly on `train_mask` | 0 |
| 13 | `rad_efimov_f_local` | `subsurface16` | $e - G_{\sigma=4}^{\text{valid}}(e)$, $e = \ln((K + 1)(U + 1)/(\text{Th} + 5)^2)$ | 12 |
| 14 | `cond_claycap_boundary` | `subsurface16` | $c - G_{\sigma=4}^{\text{valid}}(c)$, $c = |\nabla_h\ln(\max(\text{cond\_surf}, 0) + 1)|$ | 13 |
| 15 | `bdepth_hinge_lap` | `subsurface16` | $G_{\sigma=1}^{\text{valid}}(\text{depth\_to\_base\_surf}) - G_{\sigma=4}^{\text{valid}}(\text{depth\_to\_base\_surf})$ | 12 |
| 16 | `det_elev_slope` | `surface8` | Competition band 18 (`det_elev_slope`) | 0 |
| 17 | `local_slope_highpass` | `surface8` | $\text{det\_elev\_slope} - G_{\sigma=4}^{\text{valid}}(\text{det\_elev\_slope})$ | 12 |
| 18 | `lidar_valid` | `surface8` | Decoded 3DEP coverage indicator `{0.0, 1.0}` | 0 |
| 19 | `lidar_dip_slip_polarity` | `surface8` | $\text{lidar\_valid}\cdot \frac{|\text{downface\_max} - \text{upface\_max}|}{\text{downface\_max} + \text{upface\_max} + 0.02}\cdot \text{step\_max}$ | 0 |
| 20 | `lidar_step_vs_cross_aniso` | `surface8` | $\text{lidar\_valid}\cdot \frac{\text{step\_max} - \text{cross\_max}}{\text{step\_max} + \text{cross\_max} + 0.02}\cdot \text{coh100}$ | 0 |
| 21 | `lidar_subcell_peakedness` | `surface8` | $\text{lidar\_valid}\cdot \frac{\text{ex\_max} - \text{ex\_mean}}{\text{ex\_max} + \text{ex\_mean} + 0.02}\cdot \sqrt{\text{lapneg\_max}\cdot\text{lappos\_max}}$ | 0 |
| 22 | `lidar_subsurface_strike_lock` | `surface8` | $\text{lidar\_valid}\cdot \text{coh100}\cdot \max\!\big(\cos(2(\phi_{\text{lidar}}-\phi_{\text{grav}})), \cos(2(\phi_{\text{lidar}}-\phi_{\text{rtp}}))\big)$ | 10 |
| 23 | `hydrothermal_upflow_halo` | `surface8` | $G_{\sigma=5}^{\text{valid}}(I_{\text{upflow}})$ (`truncate=3.0`), $I_{\text{upflow}} = 2\,\mathbb{I}_{\text{paleo}} + 1.5\,\mathbb{I}_{\Delta T_{\text{cat-qtz}}\ge 15 \lor T_{\text{qtz}}\ge 130} + 1\,\mathbb{I}_{\text{2m\_probe}}$ | 15 |

---

## 3. Frozen Three-Experiment Budget & Automated Decision Gates

### Experiment E1 — Buffered Cross-Quadrant Whole-Component Holdout (`v3`) & Single-Feature Leakage Canaries
- **Protocol**: `gemsdoe30.experiments.spatial_segment_folds(labels, valid, buffer_px=17)` (`withheld_positives = 60,988` across 4 folds, whole 8-connected components assigned by centroid, `17 px` spatial guard around training negatives/positives).
- **Learner & Sampling**: `sample_training_pixels(..., negatives_per_positive=6, seed=3070 + fold)` and `gemsdoe30.experiments.fit_model(..., seed=3070 + fold)` (`HistGradientBoostingClassifier`, identical across all learned arms).
- **Four Fixed Arms** (matched active-domain dot count `round(44090 * active.sum() / valid.sum())` per fold using `gemsdoe30.experiments.select_dots(..., min_spacing_px=3.0)`):
  1. `random_dispersed`: Dispersed 3-px Poisson-disk random null (`seed = 4070 + fold`).
  2. `subsurface16`: Columns `0..15` (`16` purely subsurface geophysical + radiometric alteration inputs; zero elevation/slope/LiDAR).
  3. `core19`: Standard 19-band competition stack (must reproduce recorded `TDX-1` / `G30-LSM` `HOLDOUT-DTI = 0.13982063` to `1e-9`).
  4. `tilt_alt24`: Full 24-input translation-invariant stack (`0..23`).
- **Scoring & Bootstrap**: `gemsdoe30.holdout.masked_dti_by_blocks(..., block_size_px=128)` (`evaluator_version = component-holdout-v3-blockstats-20261025`) + `spatial_bootstrap(..., candidate="tilt_alt24", replicates=2000, seed=3071)`.
- **Leakage Canaries**: Every unique input (`36` unique features across `core19` and `tilt_alt24` × 4 folds = `144` tests) evaluated individually for raw bidirectional AUC and training-only univariate HGB bidirectional AUC; any value `> 0.90` triggers a leakage alarm.

### Experiment E2 — Out-of-Fold Cross-Quadrant Surface Construction & Observability-Decensored Collar Diagnostic
- **Zero-Refit Out-of-Fold Surface (`S_oof`)**: Each held-out spatial quadrant $Q_f$ is scored exclusively by Fold $f$'s already-trained `tilt_alt24` model (never exposed to labels in $Q_f$), calibrated across quadrants strictly via each fold's **training-set** (`train_mask`) prediction quantiles (`1,001`-knot uniform quantile mapping onto `[0, 1]`).
- **Diagnostic Comparison (`38,000` full-grid dots, `d_vis > 2 px`, `3.0 px` Euclidean Poisson-disk spacing)**:
  - `plain_d2` (Policy P0): Unstratified top-score selection on `valid & (d_vis > 2.0)`.
  - `decensored_30_40_30` (Policy P1, **frozen production policy**): Sequential global-3px-spaced quota selection allocating `11,400` dots (`30%`) to `2 < d_vis <= 10 px` (`200 m – 1 km`), `15,200` dots (`40%`) to `10 < d_vis <= 30 px` (`1 – 3 km` stepovers/pediments), and `11,400` dots (`30%`) to `d_vis > 30 px` (`> 3 km` concealed basin/interior structures), with any unfilled stratum shortfall rolled deterministically into remaining `d_vis > 2 px` candidates by descending `S_oof`.
  - Evaluated as diagnostic evidence on (i) interleaved component holdout (`gemsdoe30.holdout.split_components`, seed 42, 50% visible / 50% hidden components, comparing `S_oof` P1 vs `subsurface16` OOF P1 and `random_dispersed`) and (ii) independent off-catalogue `SGMC-new` bedrock/concealed faults (`> 300 m` from `labels.tif`, `61,664` pixels, reported with `IR-30-081` caveat against `plain_d2` and `core19` OOF).
- **Pre-Committed Selection Rule**: Only `S_oof` + Policy P1 (`decensored_30_40_30`, `38,000` binary `{0, 1}` dots) proceeds to E3 regardless of diagnostic differences between P0 and P1, preventing post-hoc emitter selection.

### Experiment E3 — Pre-Placement Surface & Post-Placement Dot Novelty Gate + Dual-Encoded GeoTIFF Validation
- **Pinned Registry**: `docs/research/tilt-alteration-discontinuity/registry.json` (`190` unique aligned GeoTIFFs across all 9 priority repositories + all pre-existing `docs/downloads/*.tif` files).
- **Mandatory Duplicate Stop (Rule 1)**:
  - Stage 1 (`surface`): Compare continuous `S_oof` GeoTIFF against all `190` registry rasters via `gemsdoe30.novelty.compare`; if `max Spearman > 0.90` or any error occurs, log `duplicate-stop` and abort publication.
  - Stage 2 (`dots`): Compare final `38,000`-dot binary GeoTIFF against all `190` registry rasters; if `max Spearman > 0.90` OR `max candidate_fraction_within_3px_of_reference > 0.70` or any error occurs, quarantine in `outputs/`, do **not** publish to `docs/downloads/`, log `duplicate-stop`, and stop.
- **Automated Machine Promotion Gate (`scripts/verify_tad_run.py`)**:
  `verdict = "promote"` (`ok_to_submit = true`, `slot_selected = false`) **if and only if ALL six automated gates pass**:
  1. **Format & Range Contract**: Primary `-zeros.tif` (`0.0` outside footprint, `nodata = None`, finite `{0.0, 1.0}` across all `12,279,160` cells — immune to `[0, 1]` range errors) and companion `-nan.tif` (`NaN` outside, passing `gemsdoe30.submission.validate_submission_file`) match template CRS/shape/transform, match exact `38,000` inside-footprint dots (`0` on or within `≤ 2 px` of catalogue), and bind to `run-card.json` SHA-256 & `<= 140`-char note.
  2. **Preregistration & Support Guard**: `preregistration_sha256`, `registry_sha256`, `transform_code_sha256`, and `buffer_px == 17 >= exact_operator_support_px` match across all receipts.
  3. **Single-Feature Leakage Canaries**: All `144` canary checks (`36` unique features × 4 folds) have bidirectional raw and univariate HGB AUC `<= 0.90`.
  4. **Primary Paired Spatial Holdout Gate**: In E1 (`v3`, `60,988` withheld positives), `core19` reproduces recorded `0.13982063` (`±1e-9`) AND `tilt_alt24` achieves positive paired 95% spatial-block bootstrap CI lower bounds (`ci95[0] > 0`) simultaneously against **`random_dispersed`**, **`subsurface16`**, AND **`core19`**.
  5. **Surface & Dot Novelty Gate**: Both `surface` and `dots` pass against all `190` pinned registry rasters (`Spearman <= 0.90` and `dots within 3 px <= 0.70`, `0` errors).
  6. **Budget Gate**: `experiments_run <= 3` and `experimental_elapsed_seconds <= 7200`.
  If Gate 5 fails, no public TIFF is written (`duplicate-stop`). If Gate 5 and Gate 1 pass while Gate 3 or Gate 4 fails, the unique GeoTIFF is published as a verified negative artifact with `verdict = "negative"` and `ok_to_submit = false`.
