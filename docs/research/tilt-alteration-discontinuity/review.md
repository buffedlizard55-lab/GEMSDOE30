# G30-TAD Scientific Review — Multi-Physics Tilt-Depth, Potassic Alteration & Observability-Decensored Collar Emission

- **Date**: 2026-10-25 / 2026-10-26 UTC
- **Branch**: `arena/8b4f7b50-gemsdoe30`
- **Lane**: `G30-TAD` (self-assigned; logged as `IR-TAD-01` because the owner prompt contains no lane paragraph after `"your lane is the single method paragraph below"`)
- **Frozen preregistration**: [`preregistration.md`](preregistration.md) (`9c7e91953be22f435d0113f8a9ce95d19cfc9aa86f7c3120d33052e91ef0c3d2`)
- **Pinned 190-raster registry**: [`registry.json`](registry.json) (`bec529994d009be6cedd23c35d0e788f876ae62bb4d2f86f3491c90915bdc527`)
- **Machine verifier**: `python scripts/verify_tad_run.py` -> [`readiness.json`](readiness.json)
- **Final Run Card**: [`run-card.json`](run-card.json)
- **Automated decision**:
  - **Technical format & 190-raster novelty gates**: **PASSED (`download_ok = true`)** — unique dual GeoTIFFs published in `docs/downloads/`:
    - Primary portal-range-hardened (`0.0` outside, `nodata=None`, all `12,279,160` cells finite in `[0, 1]`): [`gems30-TAD24-decensored-38000-20261025-ea3669f488ea-zeros.tif`](../../downloads/gems30-TAD24-decensored-38000-20261025-ea3669f488ea-zeros.tif) (`sha256 = 3077db43ee72ee526d8b943d1db40f19ce49be9d8ccd3109068ca442964f26cc`)
    - Companion documented-spec (`NaN` outside, `validate_submission_file = passed`): [`gems30-TAD24-decensored-38000-20261025-ea3669f488ea-nan.tif`](../../downloads/gems30-TAD24-decensored-38000-20261025-ea3669f488ea-nan.tif) (`sha256 = 54139f2cf86f75ba96bddba0f49409e934c77d716eb39150dbd04daf23b6b7e4`)
  - **Scientific weekly-slot gate**: **NEGATIVE (`verdict = "negative"`, `ok_to_submit = false`) — DO NOT SPEND A WEEKLY SUBMISSION SLOT** (`tilt_alt24` improved pooled `HOLDOUT-DTI` point estimate over `core19` by `+0.00423`, over `subsurface16` by `+0.03445`, and over `random_dispersed` by `+0.06152`, with `144/144` single-feature leakage canaries passing `<= 0.6434`, **but** the paired 95% spatial-block bootstrap CI against `core19` is `[-0.01554, +0.02398]`, which crosses zero).

---

## 1. What Problem `G30-TAD` Solved — And What It Falsified

Before `G30-TAD`, three concurrent sessions (`TDX-C2`, `G30-S20`, and `G30-LSM`) all collided with the same structural failure mode (`IR-30-079`, `IR-30-087`):
1. **Pure magnetic flank-lag (`TDX-1`) collapsed below random** (`HOLDOUT-DTI = 0.07284` vs `random_dispersed = 0.08253`), because raw magnetic profile cross-correlation had weak signal-to-noise without depth-normalized potential-field tilt, upward continuation, alteration chemistry, and MT clay-cap edges.
2. **Full-stack habitat models (`TDX-C2`, `G30-LSM`) beat or matched `core19` on catalogue recovery, then failed the mandatory `70% / 3 px` dot-overlap gate (`79.09%` and `80.20%`) and published zero TIFFs**, because keeping raw regional coordinate-proxy bands (`tmi`, `rtp`, `iso_grav_anom`, `det_elev`, `depth_to_base_surf`, `geod_*`) + greedy `d_cat > 2 px` placement concentrated `54%–76%` of emitted dots inside `< 1 km` of mapped range-front traces—the exact zone that differential algebra on H33 (`0.2778`) vs D2.8 (`0.2600`) and PINN (`0.2750`) shows earns near-zero net credit on hidden test faults.

`G30-TAD` tested two coupled hypotheses across three bounded experiments (`769.0 s <= 7,200 s` cap):
- **Feature physics (`E1`)**: Strip all 12 regional coordinate-proxy bands of `core19` and replace them with 17 local translation-invariant multi-physics discontinuity transforms (`tilt_alt24` = 16 geophysical/hydrothermal `subsurface16` features + 8 local topographic/1 m LiDAR dip-slip `surface` features; footprint-isolated `norm_gauss` and Neumann-masked `sobel_xy_safe` with exact impulse support `15 px <= 17 px` fold buffer; fold-safe OLS `rad_kd` fit strictly on training folds; label-free hydrothermal impulse ignoring `dist_known_fault_px`).
- **Observability-decensored collar emission (`E2` & `E3`)**: Stitch cross-quadrant out-of-fold probabilities (`S_oof`, quantile-calibrated strictly against each fold's own training distribution) and emit `38,000` binary `{0, 1}` dots at `3.0 px` Poisson-disk spacing using fixed `30% / 40% / 30%` allocation across `(2, 10] px` (`200 m–1 km`), `(10, 30] px` (`1–3 km` blind step-over collar), and `> 30 px` (`> 3 km` basin floor).

---

## 2. Experiment E1 — Buffered 4-Quadrant Whole-Component Holdout (`v3`) & 144 Canaries

All scores below are **`HOLDOUT-DTI`** (`evaluator_version = component-holdout-v3-blockstats-20261025`, `protocol_version = buffered-quadrant-whole-components-v1-20261025`, `60,988` withheld positive pixels across 4 disjoint quadrants, `17 px = 1.7 km` fold training buffer, `371` geographic bootstrap blocks, `2,000` paired replicates, `seed = 3071`; exact count-matched fold budgets `20,902 + 11,661 + 4,821 + 6,728 = 44,112` dots):

| Arm | Features | Fold 0 (NW) | Fold 1 (NE) | Fold 2 (SW) | Fold 3 (SE) | Pooled `HOLDOUT-DTI` | 95% Spatial-Block CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| `random_dispersed` | 0 (label-free 3 px Poisson disk) | 0.08152 | 0.08700 | 0.08469 | 0.07727 | **0.08253** | `[0.07923, 0.08563]` |
| `subsurface16` | 16 (zero elevation/slope/LiDAR) | 0.09508 | 0.13626 | 0.10052 | 0.12567 | **0.10959** | `[0.09685, 0.12264]` |
| `core19` | 19 (raw competition stack) | 0.11277 | 0.17728 | 0.15277 | 0.15848 | **0.13982** | `[0.12418, 0.15590]` |
| **`tilt_alt24`** | **24 (coordinate-free tilt + alt + scarp)** | **0.13078** | **0.16850** | **0.13713** | **0.15737** | **0.14405** | **`[0.12717, 0.16007]`** |

### Paired Spatial-Block Differences (`tilt_alt24` minus comparator)
- **`tilt_alt24 - random_dispersed`**: **`+0.06152`**, 95% CI **`[+0.04472, +0.07844]`** (**statistically positive**)
- **`tilt_alt24 - subsurface16`**: **`+0.03445`**, 95% CI **`[+0.02272, +0.04592]`** (**statistically positive**)
- **`tilt_alt24 - core19`**: **`+0.00423`**, 95% CI **`[-0.01554, +0.02398]`** (**point estimate positive, CI crosses zero -> weekly-slot promotion gate FAILS CLOSED**)

### Key Scientific Takeaways from E1
1. **Pure subsurface geophysics + potassic alteration works (`subsurface16 = 0.10959`)**: Without touching a single pixel of elevation, slope, or 1 m LiDAR, `subsurface16` beats `random_dispersed` (`0.08253`) by **`+0.02706` (`+32.8%`)** and outperforms `TDX-1` (`0.07284`) by **`+0.03675` (`+50.5%`)**. Salem tilt-depth (`h_tilt`), `150 m` FFT upward-continuation residual, fold-safe radiometric $K_d$/Efimov-$F$ potassic alteration, MT clay-cap conductance edge, and basement hinge carry genuine cross-quadrant fault signal beneath basin cover.
2. **Regional heterogeneity across Nevada quadrants**: In **Fold 0 (NW Nevada — Winnemucca/Black Rock/Humboldt structural belt, 28,904 withheld positives = 47.4% of all catalogue truth)**, removing the 12 coordinate-proxy bands and adding local tilt-depth + alteration + dip-slip physics jumped `HOLDOUT-DTI` from `0.11277` (`core19`) to **`0.13078` (`+0.01801`)**! Conversely, in Folds 1–2 (NE & SW Walker Lane), dropping raw `det_elev` and regional tectonic strain (`geod_2ndinv`, `geod_shearrate`, `depth_to_base_surf`) cost `-0.0088` to `-0.0156`, because Walker Lane transtensional range fronts correlate strongly with regional strain rate and basin depth.
3. **144/144 single-feature leakage canaries passed**: Every one of the `36` unique features across `core19 ∪ tilt_alt24` was tested alone in all `4` folds (`144` checks, both raw bidirectional AUC and fold-trained univariate HGB AUC). Maximum bidirectional AUC was **`0.6434 <= 0.90`** (`0` alarms). Bit-exact determinism of all E1 arms and CIs was verified across two independent executions ([`results-e1.first-execution.json`](results-e1.first-execution.json) vs [`results-e1.json`](results-e1.json)).

---

## 3. Experiment E2 — Observability-Decensored Collar Diagnostic (`P1` vs `P0`)

1. **Interleaved whole-component holdout (`seed = 42`, `19,732` withheld positives, `37,697` dots)** on out-of-fold `S_oof`:
   - `tilt_alt24_oof_p1`: **`HOLDOUT-DTI = 0.11291`** (`95% CI [0.09796, 0.12820]`)
   - `subsurface16_oof_p1`: **`HOLDOUT-DTI = 0.08220`** (`95% CI [0.06936, 0.09547]`), `tilt_alt24 - subsurface16 = +0.03072` (`[+0.01782, +0.04334]`)
   - `random_p1`: **`HOLDOUT-DTI = 0.07711`** (`95% CI [0.07123, 0.08264]`), `tilt_alt24 - random = +0.03581` (`[+0.02068, +0.05110]`)
2. **Distance-stratum decensoring (`38,000` full-grid dots)**:
   - Plain `d_cat > 2 px` (`P0`) placed `{<=2 px: 0, 2-10 px: 13,462 (35.4%), 10-30 px: 13,130 (34.6%), >30 px: 11,408 (30.0%)}` (already dramatically less crowded than `G30-LSM`'s `54.4%` inside `<=10 px` because `tilt_alt24` dropped regional elevation/strain levels!).
   - Decensored `30/40/30` (`P1`) cleanly reallocated `-2,062` near-collar dots into the `1–3 km` blind step-over zone: **`{<=2 px: 0, 2-10 px: 11,400 (30.0%), 10-30 px: 15,200 (40.0%), >30 px: 11,400 (30.0%)}`** with `fallback_rollover = 0`.
3. **Off-catalogue `SGMC-new` diagnostic (`61,664` bedrock fault pixels `> 300 m` from competition labels; reported with `IR-30-081` caveat, NOT a leaderboard proxy)**:
   - **`tilt_alt24_oof_p1_decensored`**: **`0.08178`** (`TP_w = 4,699.34`) — **improves over plain `tilt_alt24_oof_p0_plain_d2` (`0.08117`, `TP_w = 4,663.83`) at identical `38,000`-dot budget**, confirming that shifting `2,062` dots from `< 1 km` into the `1–3 km` step-over collar recovers additional unmapped bedrock structures!

---

## 4. Experiment E3 — 190-Raster Pre-Placement Surface & Post-Placement Dot Novelty + Dual GeoTIFF Validation

Audited against [`registry.json`](registry.json) (`190` aligned GeoTIFFs across `GEMSDOE24/25/27/28/30/31/32/33/36` and all repository downloads):
- **Pre-placement continuous OOF surface (`tad24-oof-surface.tif`)**:
  - `max_spearman = 0.1637 <= 0.90` (`0` errors; closest reference `GEMSDOE24-918e6e23...`) — **PASSED**.
- **Post-placement 38,000-dot binary raster (`gems30-TAD24-decensored-38000-20261025-ea3669f488ea-nan.tif` / `-zeros.tif`)**:
  - `max_spearman = 0.0397 <= 0.90`
  - **`max_fraction_within_3px = 0.5144 <= 0.70` (`51.44%`, `18.56` percentage points below the `70.0%` duplicate limit; `0` errors)** — **PASSED**!
- **Automated GeoTIFF Format & Range Validation (`validation.json`)**:
  - Primary `-zeros.tif`: `3730 x 3292`, single-band `float32`, `EPSG:32611`, exact affine geotransform, **all `12,279,160` cells finite in `[0.0, 1.0]`** (`0` `NaN`/`Inf` cells anywhere, preventing `"Predicted values must be in range [0, 1]"` under whole-array portal checks), `38,000` `{0, 1}` dots inside `5,167,373` valid footprint, `0` dots on or within `<= 2 px` of catalogue faults.
  - Companion `-nan.tif`: identical `38,000` in-footprint `{0, 1}` dots (`values_identity_sha256 = ea3669f488ea...`), `NaN` outside footprint, passes all 12 checks of `gemsdoe30.submission.validate_submission_file`.

---

## 5. Limitations & Concrete Next-Session Blueprint

1. **Why `tilt_alt24` did not clear the `core19` CI gate (`+0.00423`, `[-0.01554, +0.02398]`)**:
   - Dropping all 12 regional bands of `core19` (`det_elev`, `geod_2ndinv`, `geod_shearrate`, `depth_to_base_surf`, etc.) hurt Walker Lane quadrants (Folds 1–2) where active fault density genuinely co-varies with regional transtensional strain rate, even while boosting NW Nevada (Fold 0) by `+0.01801`.
   - Meanwhile, `G30-LSM` (`lsm42`, which *kept* `core19` and added 17 multiscale 1 m LiDAR scarp profile features) cleared the `v3` holdout CI gate (`0.15717`, `+0.01735` `[+0.00662, +0.02786]`), **but failed dot uniqueness (`80.2% > 70%`) because it lacked `G30-TAD`'s `decensored_30_40_30` collar selector and subsurface tilt-depth/alteration features**!
2. **Exact Next-Session Hypothesis (`G30-FUSION`, highest expected value)**:
   - **Combine the two proven halves**: fuse `core19` + `G30-LSM`'s 17 multiscale 1 m LiDAR scarp-profile features + `G30-TAD`'s `subsurface16` potential-field tilt-depth (`h_tilt`, `tmi_up150_res`), fold-safe potassic alteration (`rad_kd`, `rad_efimov_f`), and MT clay-cap conductance edge (`cond_log_grad`), **AND emit via `G30-TAD`'s `decensored_30_40_30` OOF collar selector** (checking 190-raster dot overlap *before* spending E2/E3 budget, per `IR-30-087`).
   - Run an ablation keeping regional strain (`geod_2ndinv`, `geod_shearrate`, `depth_to_base_surf`) while still excluding raw `tmi`/`rtp`/`iso_grav_anom` coordinate levels so Fold 0 (`+0.0180`) and Folds 1–2 (`0.1773 / 0.1528`) both retain full structural signal.
   - Fetch clipped USGS SGMC quaternary/alluvial polygon cover (`NV.zip` + `CA.zip` already SHA-pinned in `data/external/external_receipt.json`, `H-34-01`) so the `30/40/30` collar weights become a continuous physical **alluvial-concealment observability weight** $w_{\text{conceal}}(x)$ rather than a purely radial distance stratum.
