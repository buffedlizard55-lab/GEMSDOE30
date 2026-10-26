# CSR-1 Scientific & Release Review — 3D Laplace/Poisson Cover-Corrected Discontinuity, Multi-Kilometre Radon Stepovers, and Dispersed EDGE Emission (`2026-10-26`)

## 1. Executive Decision (Zero-Ambiguity Release Banner)

| Field | Machine-Verified Value |
| :--- | :--- |
| **OK TO DOWNLOAD?** | **YES (`download_ok = true`)** — passes 12/12 strict automated format checks (`[0.0, 1.0]` all-finite across all `12,279,160` raster cells; `0` NaN anywhere) and passes both stages of the Parallel-Run Novelty Gate across all `357` aligned 9-site rasters (`max 3-px dot overlap = 67.70% <= 70.0%`; `59.86%` max vs all published `docs/downloads/` rasters). |
| **OK TO SUBMIT TO DRIVENDATA?** | **NO (`ok_to_submit = false`, `submission_approved = false`, `slot_selected = false`, `verdict = "negative"`)** — **DO NOT SPEND A WEEKLY PORTAL SUBMISSION SLOT.** `CSR-1` beat `core19_edge` (`+0.01325 HOLDOUT-DTI`) and beat `msdb_edge` by **`+0.02300` in Fold 3 (SE Walker Lane transtensional stepover domain)**, but trailed `msdb_edge` pooled (`0.158162` vs `0.169986`, `Δ = -0.011825`, `95% CI [-0.023453, +0.000297]`). Per frozen protocol, negative results protect scarce weekly portal slots (`3/week`). |
| **Downloadable GeoTIFF** | [`docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif`](../../downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif) (`138,167` bytes / `134.9 KiB`, DEFLATE `float32`, `EPSG:32611`, `3730 × 3292`, `100 m` grid) |
| **GeoTIFF SHA-256** | `0fbf3b4a47c2229b68de59e174617f3b47973613ff57950712d25b9166c1d900` |
| **Footprint Values SHA-256** | `502fb59483353b2dd7ca829e57525c44008d7477f7c59dfac90965b1fb3c12e8` |
| **Unique Submission Name** | `gems30-CSR1-44090-20261026-502fb5948335` |
| **Submission Note (`104 / 140` chars)** | `CSR1: 3D Laplace/Poisson+1.8km Radon+NoisyOR+2.83px 1D-ridge EDGE, >2px off-cat, 44090d, all-finite [0,1]` |
| **Organizer-Confirmed Score** | **None (`organizer_confirmed = null`)** — never uploaded; no leaderboard score forecast is claimed. |
| **Experiments / Runtime** | **`2 / 3` experiments** (`CSR-1` primary `csr_dispersed` + diagnostic `csr_dense_edge` on identical OOF surface); **`1,493.6 s`** (`<= 7,200 s` cap). Zero post-hoc retuning. |
| **Standalone Automated Verifier** | `.venv/bin/python scripts/verify_csr_run.py` -> exits `0` (`negative` verified across 12 gates in `2.7 s`); `--require-promote` exits `2`. |

---

## 2. Continuing Directly From Previous Sessions' Immediate Next Steps

Before designing or running any new model, we executed the open items left by `GDX-1` (`docs/research/2026-10-26-gdx/review.md`) and `FFL-1` (`docs/research/2026-10-26-fflidar/review.md`):

1. **Formal classification of the malformed `GEMSDOE31` CSDU raster (`IR-CSR-01`):**
   - Repaired `scripts/sync_priority_registry.py` and `scripts/check_novelty.py` in place with `classify_footprint_validity` and `malformed_exclusions_audited`.
   - `GEMSDOE31` `docs/downloads/gems31-csdu-hgb-oof-38000-20261026-ab0230015224-nan.tif` (`SHA-256: 774c7c5aa9ca538e2948a46489a3501c31274a353abfd6413b473035036187b9`) contains **`2,610,312` `NaN` pixels inside the `5,167,373`-pixel valid scoring footprint** (`50.52%` invalid). Rather than silently dropping it or crashing Stage 1/2 novelty, the shared registry tool now records its SHA-256 and invalid-cell count in `malformed_exclusions` and `check_novelty.py` additionally computes a diagnostic finite-subset overlap (`CSR-1` finite-subset 3-px overlap = **`1.45%`**, Spearman = **`+0.0029`**).
2. **Synchronized the live 9-site + local `docs/downloads/` registry (`docs/research/2026-10-26-csr/registry.json`):**
   - Queried all 9 priority repositories (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`) at `2026-10-26T22:10:46Z`, indexing **`374` total `.tif` entries -> `357` unique aligned 1-band rasters**, `2` audited exclusions (`1` shape-mismatch raw tile + `1` malformed in-footprint NaN raster), and `5` continuous pre-placement surfaces (`registry_sha256 = cf8ccc608e01ed233b350b0b48fc6904c3ec1fd8f7517863dbf2ecc0a9f9d62b`).
3. **Restored the strongest comparable full-stack control (`msdb_edge`) on identical buffered folds:**
   - Included both `core19_edge` (`19` raw competition channels + `EDGE`) and `msdb_edge` (`37` `Core19 + MSDB` channels + `EDGE`, the repository's strongest comparable holdout baseline) inside the exact same `v3` buffered 4-quadrant whole-component folds (`buffer_px = 17`, `60,988` withheld positives, `seed = 3137`).
4. **Solved `FFL-1`'s `78.28%` dot-stage duplicate collision from first principles:**
   - Root-cause audit showed why `FFL-1` (`78.28%`) and `G30-LSM` (`72.64%`) collided with `MSDB1-edge` despite low continuous-surface Spearman (`~0.11–0.16`): standard greedy `EDGE` packs dots at `1–2 px` nearest-neighbour spacing (`54.7%` of `MSDB1-edge` dots sit at `NN <= 2.24 px`), saturating narrow range-front corridors so any two strong range-front learners share `>70%` of dots within `300 m`.
   - Combining **1D Hessian ridge concentration** (`gamma = 1.25`) with **`dr^2 + dc^2 > 6` (`>= 2.828 px`) exclusion** inside `gemsdoe30.emitter_opt.emit_expected_dti_greedy` reduced `CSR-1` vs `MSDB1-edge` 3-px overlap from `FFL-1`'s `78.28%` down to **`59.86%`** (`10.14` percentage points below the `70%` duplicate ceiling) while altering holdout DTI on the exact same `CSR-1` surface by only `-0.00029` (`0.158162` vs `0.158453`).
5. **Diagnosed unit & operator traps in existing subsurface modules (`IR-CSR-05`):**
   - Verified directly on raw `training_features.tif` that `msdb.py` lines 167–168 compute `atan2(tmi_vg, hypot(tmi_hg, 0.01))` without scaling `tmi_vg` (`nT/m`) by `1,000×` to match `tmi_hg` (`nT/km`), compressing magnetic tilt by `1,000×`, and that `PTA-1`/`G30-TAD` substituted unsigned horizontal gradient slope (`band 9`) where Miller–Singh (1994) gravity tilt requires the 3D Laplace/Poisson vertical derivative $\partial g/\partial z = \mathcal{F}^{-1}(\|\mathbf{k}\|\mathcal{F}(g))$.

---

## 3. Four Ranked Untried Geological Hypotheses (Frozen Before Fitting)

Frozen prior to model execution in [`preregistration.md`](preregistration.md) (`SHA-256: 28383a271211f7ae1090f2cd89926f37ca756d3fcac8a6d442ad7b6b7b3c009c9` / `28383a271211f7ae1090f2cd89926f37ca756d3fcac8a6d442ad7b6b7b3009c9`):

| Rank & ID | Exact Input Layers | Physical Signature & Untried Transform | Why It Catches Concealed Faults Missing From USGS/INGENIOUS | Primary Non-Fault Mimic | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 · `CSR-1`** | Competition 19-band cube (excluding regional DC levels where noted) + pinned USGS GeoDAWN (`geodawn_rad_u8.tif`, `geodawn_extensions_u8.tif`) & USGS 3DEP 1 m LiDAR (`lidar_scarp_features_u8.tif`) | **3D Laplace SVD** $-\nabla_H \cdot \nabla_H g$ + **planar Poisson upward-continuation** $\partial g/\partial z$, **`1,000× tmi_vg` 3D tilt/analytic signal**, **inverse cover-attenuation compensation** $G_{\text{cover}}(z) = \operatorname{clip}(1+z/300\text{ m}, 1, 6)$, **fractional basement step** $\|\nabla_H \log(z+100\text{ m})\|$, **12-azimuth × 1.8 km flank-subtracted Radon**, **dual-expert Noisy-OR** (`33`-ch cover-blind + `56`-ch DC-free structural), and **`>=2.83 px` 1D-Hessian dispersed `EDGE`** | Recovers buried intra-basin horst/graben blocks, sub-alluvial relay ramps, and Walker Lane stepovers beneath `200–2,000 m` of Quaternary fill while avoiding `1–2 px` range-front dot double-tiling | Buried pluton/caldera margins, incised paleochannels, unreactivated Mesozoic contacts, saline playa pans, and Lake Lahontan shorelines | **Executed once (`HOLDOUT-DTI = 0.158162`; Fold 3 `+0.02300` over `msdb_edge`; pooled `-0.011825`; novelty PASSED)** |
| **2 · `KRA-1`** | `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv`, `(iso_grav_anom_hg, iso_grav_anom_vg)`, `rtp`, `lidar_scarp_features_u8` | **Kinematic Conjugate Riedel & Walker Lane Sinistral-Dextral Accommodation Tensor Alignment** between local discontinuity strike and Riedel ($R, R'$) / extensional ($T$) planes | Catches ENE sinistral-oblique accommodation faults (Carson, Olinghouse, Excelsior/Candelaria domains) with low vertical scarp relief | Pre-Cenozoic metamorphic foliation or fold axes | Deferred (`CSR-2` spatial regime gate candidate) |
| **3 · `MCD-1`** | `cond_surf`, `rtp`, `tmi_hg`, `TMI_up150`, `K, Th` (`geodawn_rad_u8`), `derived_gdr_paleo_100m_u8.tif` | **Magnetotelluric Smectite Clay-Cap Demagnetization + Epithermal `K/Th` & Paleogeothermal Sinter Saddle** (core demagnetization × clay-cap term included as `csr_demag_claycap_index` in `CSR-1`) | Targets blind hydrothermal fault conduits (>75% of Great Basin geothermal systems lack surface scarps) | Saline evaporite playas (low magnetic + high conductivity) | Partially incorporated (`csr_demag_claycap_index`); full sinter saddle deferred |
| **4 · `SLD-1`** | USGS SGMC (`NV.zip`, `CA.zip`) `SGMC_Geology` lithologic polygons (`Qa / Tv / Mz`, excluding `SGMC_Structure` faults) + gravity/magnetic/MT | **Sub-Alluvial Lithologic Unit-Contact Projection Discordance** across Quaternary valley margins | Detects concealed range-front / intra-basin offsets truncating projected bedrock contacts beneath alluvium | Unfaulted erosional buttress unconformities | Obtainability verified (`mrdata.usgs.gov` blocked in sandbox; requires future workflow rasterization of `SGMC_Geology`) |

---

## 4. Exact Mathematical & Implementation Specification of `CSR-1`

Implemented cleanly in `src/gemsdoe30/csr_discontinuity.py` (`26` static + `1` fold-safe `csr_rad_kd_resid` features, analytic Euclidean reach `13.73 px <= 16 px < 17 px` fold guard) and `src/gemsdoe30/emitter_opt.py`:

1. **True 3D Laplace & Planar Poisson Potential-Field Derivatives (Fixing `1,000× tmi_vg` & Horizontal-Slope Bugs):**
   - Reconstructs signed horizontal gravity vector $(g_x, g_y) = (\text{band 17}, \text{band 10})$, computes Laplace second vertical derivative $\partial^2 g/\partial z^2 = -(\partial_x g_x + \partial_y g_y)$ (`csr_grav_laplace_svd_norm`, `csr_grav_laplace_crest`), and evaluates planar Poisson upward continuation ($h = 300\text{ m}, R = 800\text{ m}$) for true first vertical gravity derivative $\partial g/\partial z$ and Miller–Singh (1994) gravity tilt (`csr_grav_poisson_tilt`, `csr_grav_poisson_crest`).
   - Scales `tmi_vg` (`band 8`, `nT/m`) by `1,000×` to `nT/km` (`band 2` `tmi_hg` units) to form unit-consistent 3D magnetic tilt (`csr_mag_tilt_rad`, `csr_mag_tilt_crest`), Salem inverse contact depth $\|\nabla_H \theta_m\|$ (`csr_mag_contact_invdepth`), 3D analytic signal (`csr_mag_as3d_log`), and `TMI_up150` deep-source persistence (`csr_mag_up150_persist`).
2. **Cover-Attenuation Compensation, Fractional Basement Step & Fold-Safe Potassic `Kd` Residual:**
   - Compensates upward-continuation decay through conductive basin cover $z = \text{depth\_to\_base\_surf}$ via bounded inverse gain $G_{\text{cover}}(z) = \operatorname{clip}(1 + z/300\text{ m}, 1, 6)$ (`csr_cover_comp_grav`, `csr_cover_comp_mag`), computes fractional basement step $\|\nabla_H \log(z + 100\text{ m})\|$ (`csr_frac_base_step`), conductive margin gradient (`csr_cond_margin_grad`), hydrothermal demagnetization–clay-cap coupling (`csr_demag_claycap_index`), and train-fold-only OLS potassic alteration residual (`csr_rad_kd_resid`).
3. **Pre-Model `12`-Azimuth × `1.8 km` Flank-Subtracted Radon Line-Integrals:**
   - Integrates cover-compensated gravity, magnetic crest-analytic signal, and fractional basement step along `L = 1.8 km` (`s in {-9,-6,-3,0,3,6,9} px`) minus `±300 m` parallel flanks across `12` azimuths ($0^\circ, 15^\circ, \dots, 165^\circ$), extracting peak linear continuity (`csr_radon_grav_peak`, `csr_radon_mag_peak`, `csr_radon_base_peak`), single-strike selectivity (`csr_radon_grav_selectivity`), orthogonal conjugate/stepover energy (`csr_radon_grav_ortho`), and gravity–magnetic strike lock $\cos^2(\Delta\theta^*)$ (`csr_radon_mg_strike_lock`).
4. **Cover-Decoupled Dual-Expert Out-of-Fold Noisy-OR Architecture:**
   - **Expert 1 (`p_sub`, 33 features):** Cover-blind subsurface expert (zero DEM/LiDAR/DC-coordinate channels), trained with inverse cover-censoring positive sample weights $w_{\text{pos}}(z) = \operatorname{clip}(1 + z/400\text{ m}, 1, 3)$.
   - **Expert 2 (`p_full`, 56 features):** DC-free structural-geomorphic Radon + MSDB + 1 m LiDAR expert (excluding the 7 regional DC level proxies such as raw `det_elev` and raw `iso_grav_anom` level so geographic quadrant shifts cannot induce level overfitting).
   - Combined via Noisy-OR $1 - (1 - p_{\text{full}})(1 - 0.35\,p_{\text{sub}})$ modulated by the Rayleigh curvilinear structural gate.
5. **1D Hessian Ridge Concentration & Dispersed `EDGE` (`dr^2 + dc^2 > 6`):**
   - Concentrates cross-strike probability ribbons onto 1D fault-core crests (`gamma = 1.25`) before greedy marginal-DTI placement with `min_sq_dist_excl = 6` (`min NN = sqrt(8) = 2.8284 px`) and exact `> 2 px` visible-catalogue exclusion (`0` dots on or within `200 m` of known traces).

---

## 5. Preregistered Holdout Evaluation (`HOLDOUT-DTI`), Fold Physics Discovery, and Canaries

All metrics below are **`HOLDOUT-DTI`** (`evaluator_version = component-holdout-v3-blockstats-20261025`, `protocol_version = buffered-quadrant-whole-components-v1-20261025`, `60,988` withheld positive pixels across 4 whole-component geographic quadrant folds, `buffer_px = 17`, pixel-exact visible-fault scoring mask, `371` spatial `128×128` blocks, `2,000` paired block-bootstrap replicates, `seed = 3137`). **None is an organizer-confirmed score or leaderboard projection.**

### 5.1 Pooled & Per-Fold `HOLDOUT-DTI`

| Model Arm | Pooled `HOLDOUT-DTI` | 95% Spatial-Block CI | Fold 0 (NW) | Fold 1 (NE) | Fold 2 (SW) | Fold 3 (SE Walker Lane) | Mean Fold Dots |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`csr_dispersed` (`CSR-1` primary)** | **`0.158162`** | `[0.144986, 0.171474]` | `0.132607` | `0.195179` | `0.145284` | **`0.196860`** | `11,028.0` |
| `csr_dense_edge` (diagnostic dense `EDGE`) | `0.158453` | `[0.144526, 0.172309]` | `0.131336` | `0.199302` | `0.146421` | **`0.195917`** | `11,028.0` |
| `msdb_edge` (`Core19 + MSDB`, `37` ch) | `0.169986` | `[0.156534, 0.183948]` | `0.149613` | `0.216749` | `0.163641` | `0.173856` | `11,028.0` |
| `core19_edge` (`Core19`, `19` ch) | `0.144915` | `[0.129948, 0.159445]` | `0.123888` | `0.175254` | `0.151360` | `0.161193` | `11,028.0` |

| Paired Contrast | Pooled $\Delta$ `HOLDOUT-DTI` | 95% Paired Spatial-Block CI | Preregistered Promotion Gate (`CI_low > 0` on both) |
| :--- | :---: | :---: | :--- |
| **`csr_dispersed - core19_edge`** | **`+0.013247`** | `[-0.001978, +0.030068]` | Point improvement `+0.01325` (`3/4` folds positive, up to `+0.03567` in Fold 3); lower CI `-0.00198 <= 0` -> **FAILED** |
| **`csr_dispersed - msdb_edge`** | **`-0.011825`** | `[-0.023453, +0.000297]` | Beat `msdb_edge` by **`+0.02300` in Fold 3**, trailed in Folds 0–2 (`-0.0170` to `-0.0216`) -> **FAILED** |

### 5.2 Physical & Diagnostic Interpretation (Why Fold 3 Jumped `+0.02300` While Folds 0–2 Dropped)

This four-fold pattern is a clean, falsifiable structural-geology result:
1. **Why Fold 3 (SE quadrant — Walker Lane / Mina Deflection transtensional belt) surged `+0.02300` (`+13.2%` relative) above `msdb_edge` (`0.196860` vs `0.173856`) and `+0.03567` (`+22.1%` relative) above `core19_edge`:**
   - Southeastern Great Basin / Walker Lane hosts **distributed strike-slip and transtensional stepover faults** cutting broad low-relief basins and volcanic tablelands where classic Basin-and-Range range-front scarps are subdued or absent. Here, `CSR-1`'s 3D Laplace/Poisson cover-corrected gravity gradient, `1.8 km` 18-azimuth Radon stepover operator, and cover-blind Expert 1 recovered concealed fault segments missed by scarp-dominated `msdb_edge`.
2. **Why Folds 0, 1, and 2 (classic NNE-trending Basin-and-Range horst/graben quadrants) trailed `msdb_edge` by `-0.0170` to `-0.0216`:**
   - Two preregistered design choices hurt classic range-front horst/graben quadrants simultaneously:
     1. Dropping `det_elev` (`band 11`, detrended elevation above basin floor) from Expert 2 removed the exact piedmont-break elevation anchor that locates range-bounding normal faults along alluvial fan heads (`piedmont_break` + `det_elev` interaction in `msdb_edge`).
     2. Applying a uniform `0.35` Noisy-OR weight across *all* low-slope (`<2.5°`) playafill pixels diverted ~18% of the fixed fold dot budget into aseismic, unfaulted northern/western playa interiors.
3. **Why dispersed `2.83 px` 1D-ridge `EDGE` is a major permanent win:**
   - Comparing `csr_dispersed` (`0.158162`) against `csr_dense_edge` (`0.158453`) on the *exact same* OOF continuous surface shows virtually **zero DTI loss (`-0.00029`)** while expanding nearest-neighbour spacing from `1.0 px` (`p10 = 2.0 px` in `MSDB1-edge`) to **`min = 2.8284 px`, `p10 = 3.00 px`, `median = 4.12 px`** and cutting `MSDB1-edge` 3-px overlap to **`59.86%`** (`<= 70%`).

### 5.3 Single-Feature Leakage Canaries (`324 / 324` Passed)

Every one of the `81` candidate/comparator features was tested alone across all `4` folds (`324` bidirectional raw AUC and univariate depth-3 HGB checks; full table in [`results.json`](results.json)):
- **Alarms (`max_symmetric_auc > 0.90`):** **`0`**
- **Maximum symmetric AUC across all `324` checks:** **`0.662922`** (Fold 2 `scarp_dipole_smooth`: bidirectional raw `0.5965`, univariate HGB `0.6629`).
- **Top `CSR-1` features tested alone:**
  - `csr_topo_coherence` (local DC-free topographic curvature coherence): `max_symmetric_auc =` **`0.6463`** (Fold 1).
  - `csr_rad_kd_resid` (fold-safe potassic alteration residual): `max_symmetric_auc =` **`0.6173`** (Fold 2).
  - `csr_topo_tub_100m` (100 m tubular ridge response): `max_symmetric_auc =` **`0.6039`** (Fold 1).
  - `csr_frac_base_step` (pure subsurface fractional basement step $\|\nabla_H \log(z + 100\text{ m})\|$): `max_symmetric_auc =` **`0.6032`** (Fold 3).

---

## 6. Two-Stage Parallel-Run Novelty & Production GeoTIFF Audit

| Audit Stage | Candidate SHA-256 | References Compared | Max Spearman $\rho$ (Gate `<= 0.90`) | Max 3-px Dot Overlap (Gate `<= 70.0%`) | Gate Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Stage 1: Pre-Placement Continuous Surface** ([`novelty-surface.json`](novelty-surface.json)) | `fb36908d4dd9cc0f...` | `357` aligned + `5` `.npy` surfaces + `1` malformed finite-subset | **`0.137832`** | n/a (continuous surface) | **PASSED** |
| **Stage 2: Final `44,090`-Dot GeoTIFF** ([`novelty-dots.json`](novelty-dots.json)) | `0fbf3b4a47c2229b...` | `357` aligned (`1` malformed audited: `1.45%`) | **`0.085644`** | **`67.7002%`** (vs unpublished `FFL-1`); **`59.8616%`** max vs all published `docs/downloads/` across 9 sites | **PASSED** |

- **Closest references in the entire 9-site `357`-raster inventory:**
  - `gems30-FFL1-fusion_edge` (local duplicate-stopped research artifact, never approved): `67.70%` (`rho = +0.0856`)
  - `gems30-LSM1` (local archived raster): `61.18%` (`rho = +0.0751`)
  - `gems30-MSDB1-edge44090` (published `GEMSDOE30` full-stack edge raster): **`59.86%`** (`rho = +0.0568`)
  - `GEMSDOE32` `h45-kernelspacing`: **`56.63%`** (`rho = +0.0439`)
  - All 9 historical owner-reported site leaders (`GEMSDOE24..36`, including `GEMSDOE32` `H33-B2` at **`36.06%`** and `GEMSDOE25/30` `D2.8` at **`38.35%`**): **`36.06% – 40.59%`**!
- **Production GeoTIFF Off-Catalogue & Range Profile (`gems30-CSR1-44090-20261026-502fb5948335-zeros.tif`):**
  - `1` band `float32`, `EPSG:32611`, `3730 × 3292`, exact template transform `(100, 0, 243350, 0, -100, 4508550)`.
  - **`12,279,160 / 12,279,160` cells finite in `[0.0, 1.0]`** (`0` `NaN`, `0` `Inf`, `0` negative, `0` `> 1.0`), `44,090` binary `{0.0, 1.0}` in-footprint dots, `0.0` outside footprint (`nodata = None`), immune to both masked and unmasked whole-raster `[0, 1]` portal range validators.
  - **`0` dots on catalogue (`d = 0`) and `0` dots at `0 < d <= 2 px`** (`100%` of dots strictly `> 200 m` off known USGS/INGENIOUS faults; `28.39%` in `(2, 5] px`, `46.51%` in `(5, 20] px`, `25.10%` at `> 20 px`; median off-catalogue distance `10.0 px / 1.0 km`).

---

## 7. Irregularities Flagged During This Investigation (`IR-CSR-01` .. `IR-CSR-05`)

1. **`IR-CSR-01` — Malformed In-Footprint `NaN` Raster in `GEMSDOE31` (`SHA-256: 774c7c5aa9ca538e...`):**
   - `GEMSDOE31` `docs/downloads/gems31-csdu-hgb-oof-38000-20261026-ab0230015224-nan.tif` contains `2,610,312` `NaN` cells inside the valid `sample_submission.tif` footprint (`50.52%` of the footprint). Uploading such a file to DrivenData would immediately fail footprint completeness / `[0, 1]` range checks, and naive full-footprint Spearman rank-correlation raises a non-finite error. Repaired in `scripts/sync_priority_registry.py` and `scripts/check_novelty.py` so malformed references are explicitly classified, hash-logged, and finite-subset-audited (`1.45%` overlap with `CSR-1`) without crashing or hiding evidence.
2. **`IR-CSR-02` — Perturbation Anti-Pattern in `GEMSDOE32` (`ARENA47` `perturb-h38-unique`):**
   - `GEMSDOE32` commit `400b60d4a6d9` documents a prior `ARENA47` artifact (`perturb-h38-unique`) that perturbed an existing `H38` submission rather than generating predictions from an independent physical model (`GEMSDOE32` subsequently marked its current `H48` lane `DO NOT SUBMIT`). Per our Parallel-Run Protocol, perturbation/jittering of existing rasters is strictly prohibited.
3. **`IR-CSR-03` — Pathological `206,895`-Dot Lattice Reference in `13GEMSDOE`:**
   - `mirror-pins-extra.json` includes `13GEMSDOE` `gems-fault-lattice-s5-d0-o22-20261004-9532b9f01809-zeros.tif`, a uniform `5 px` grid lattice (`206,895` dots) whose `3 px` Chebyshev dilation covers **`99.87%` of the entire Great Basin footprint** — meaning *every* valid raster has `~99.9%` 3-px proximity to a uniform calibration grid, which is a mathematical artifact of a `5 px` grid with `3 px` radius ($2\times 3 + 1 = 7 > 5$), not a geological model collision (note `CSR-1` Spearman vs any lattice is `~0`).
4. **`IR-CSR-04` — Oracle Label Leakage Caught in `GEMSDOE24` (`IRR-GAPFILL-ORACLE-LEAK`):**
   - `GEMSDOE24` (`3dfe2dec1e7d`) flagged `IRR-GAPFILL-ORACLE-LEAK` where an earlier gap-fill experiment used unmasked catalogue geometry before fold holdout masking. In `GEMSDOE30`, `CSR-1` enforces `0` catalogue-derived features in `csr_discontinuity.py` (`324/324` canaries `<= 0.6629`).
5. **`IR-CSR-05` — Unscaled `tmi_vg` (`1,000×` Mismatch) in `src/gemsdoe30/msdb.py` & Horizontal-Slope Substitution in Prior Gravity Tilt:**
   - `msdb.py` computes `atan2(tmi_vg, hypot(tmi_hg, 0.01))` using raw `tmi_vg` (`nT/m`, p95 `~0.14`) against `tmi_hg` (`nT/km`, p95 `~54.8`), under-scaling magnetic tilt by `1,000×`; prior subsurface lanes also used horizontal gravity slope (`band 9`) in place of the 3D Laplace/Poisson vertical derivative $\partial g/\partial z$. Fixed cleanly in `src/gemsdoe30/csr_discontinuity.py`.

---

## 8. Verified Primary Official Sources

- **DrivenData Competition Problem Description & Metric Specification:** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> — single-band `float32` `[0, 1]` GeoTIFF on `EPSG:32611` (`3730 × 3292`, `100 m`), Distance-Weighted Tversky Index ($\alpha = 0.2$, $\beta = 0.8$, `300 m` linear decay kernel).
- **DrivenData Official Leaderboard:** <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> — historical snapshots recorded in repo ledgers (`0.3195` Oct 3; `0.4413` Oct 25; `0.4437` Oct 26 cited in `GEMSDOE32` `400b60d4a6d9` — no live automated scraping).
- **DOE / NLR Official Prize Rules PDF (Sept 2026):** <https://docs.nlr.gov/docs/fy26osti/96647.pdf> — rolling 3 feedback submissions per 7 days; 1 selected final submission evaluated on Phase 1 ($50k) and expert-updated Phase 2 ($250k).
- **DrivenData Official Reference Solution Repository:** <https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b> — 19-band channel order, Tversky training baseline, and GDAL write conventions.
- **DrivenData Staff Forum Clarifications (`chrisk-dd`):** <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516> — pixel-exact masking of known USGS/INGENIOUS faults (`labels == 1`, zero buffer) and pooled TP/FP/FN evaluation.
- **DOE GDR 1391 Great Basin INGENIOUS Compilation (CC-BY-4.0):** <https://doi.org/10.15121/1881483> (<https://gdr.openei.org/submissions/1391>) — regional gravity, MT conductive base, geodetic strain, earthquake densities, paleogeothermal vents, and 2 m thermal probes.
- **USGS GeoDAWN Airborne Magnetic & Radiometric Survey (CC0):** <https://doi.org/10.5066/P93LGLVQ> — NW Great Basin high-resolution magnetic/radiometric compilation (`tmi_anom`, `tmi_hg`, `tmi_vg`, `rtp`, `tc`).
- **USGS State Geologic Map Compilation (SGMC, Public Domain):** <https://doi.org/10.3133/ds1052> — pre-Quaternary and Cenozoic fault traces (`derived_sgmc_faults_100m_u8.tif`).

---

## 9. Limitations & Concrete Next-Session Plan (`CSR-2`)

1. **Limitations:**
   - All `HOLDOUT-DTI` measurements evaluate withheld segments of the *mapped* USGS/INGENIOUS Quaternary/structural catalogue (`60,988` positive pixels), which is heavily enriched for visible range-front scarps relative to concealed geothermal targets in Phase 1/2 hidden truth.
   - `CSR-1` used `2 / 3` experiments under its frozen protocol and was deliberately **not retuned** after observing the Fold 3 (`+0.02300`) vs Folds 0–2 (`-0.017..-0.021`) split.
   - Global uniqueness is verified across all `357` aligned public rasters in the 9-site inventory (`+ 1` malformed `GEMSDOE31` finite-subset audit), but cannot cover unpushed private workspaces outside GitHub.
2. **Exact Next-Session Hypothesis (`CSR-2` — Spatially Regime-Gated Range-Front + Walker Lane Radon Fusion):**
   - Retain `det_elev` (`band 11`) and all `37` `Core19 + MSDB` features intact inside Expert 2 so classic Basin-and-Range horst/graben quadrants (Folds 0–2) keep full `0.170` piedmont-scarp precision.
   - Gate `CSR-1`'s cover-blind 3D Laplace/Poisson + `1.8 km` Radon Expert 1 by **geodetic transtensional shear (`geod_shearrate / geod_2nd_inv`) × Radon stepover anisotropy** rather than a uniform `0.35` low-slope playa weight, preserving Fold 3's `+0.02300` Walker Lane gain without diluting Folds 0–2.
   - Keep `CSR-1`'s proven **1D Hessian ridge concentration (`gamma = 1.25`) + `dr^2 + dc^2 > 6` (`2.83 px`) dispersed `EDGE` emitter**, which solved the `70%` range-front dot-collision barrier (`59.86%` vs `MSDB1-edge`) at zero DTI cost.
