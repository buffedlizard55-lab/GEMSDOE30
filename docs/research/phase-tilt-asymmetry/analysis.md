# PTA-1 Scientific Analysis — Unit-Consistent 3D Phase-Tilt Curvature & Signed Dip-Contact Asymmetry

**Run ID:** `gems30-PTA1-44090-20261025-9a3f7f9535a4`  
**Artifact:** [`docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif`](../../downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif) (`SHA-256: 958f733cbd3501bd0ea92451a848cc28f62c913691ab3f4bc9b61aeebaaeb827`)  
**Verdict:** `negative` (`download_ok = true`, `submission_approved = false`, `slot_selected = false`)  
**Evaluator / Protocol:** `component-holdout-v3-blockstats-20261025` / `buffered-quadrant-whole-components-v1-20261025` (`60,988` withheld positive pixels across 4 buffered whole-component quadrant folds, `buffer_px = 17`, `371` geographic bootstrap blocks, `2,000` paired replicates)

---

## 1. Executive Summary of Findings

`PTA-1` tested a zero-topography, zero-catalogue-geometry subsurface detector designed specifically for **concealed intrabasin and alluvial-covered Great Basin faults** — the exact regime where surface LiDAR scarps (`det_elev_slope`) and USGS/INGENIOUS Quaternary trace maps (`labels.tif`) are systematically blind.

1. **Significant physical subsurface gain (`pta1_cand` vs `sub8_raw`):**  
   `pta1_cand` achieved `HOLDOUT-DTI = 0.096683` (`95% CI [0.085289, 0.108433]`), outperforming the raw 8-band subsurface baseline `sub8_raw` (`0.087814 [0.076810, 0.099620]`) by **`+0.008870`** with a **strictly positive paired 95% spatial-bootstrap CI `[+0.001561, +0.015976]`** (winning 3 of 4 geographic folds) and improving the repository's prior zero-topography subsurface benchmark `TDX-1` (`0.072844 [0.063480, 0.083059]`) by **`+32.7%` (`+0.023839`)** under the identical evaluator and `core19` comparator (`0.13982063017811727` reproduced to 16 decimal places).
2. **Physical mechanism corroborated in single-feature canaries (`pta_dip_cover_step`):**  
   Across all `148` univariate canary checks (`37` features × `4` folds, `0` alarms `> 0.90`), **`pta_dip_cover_step`** — the signed Grauch–Hudson hanging-wall thickening of MT conductive cover (`depth_to_base_surf`) along $-\nabla_h \tilde{g} / \|\nabla_h \tilde{g}\|$ across $300\text{–}600\text{ m}$ — achieved bidirectional raw AUC **`0.5988`** (Fold 3) and **`0.5933`** (Fold 1), outperforming **every** raw subsurface GeoDAWN, gravity, and MT input channel (`depth_to_base_surf` max `0.5181`).
3. **Unit-consistency + polarity control (`pta1_cand` vs `pta_naive_sym`):**  
   Correcting the `1,000×` `tmi_vg` unit mismatch (`nT/m` vs `nT/km` in `tmi_hg`, `IR-PTA-01`) and preserving hanging-wall vs footwall dip sign improved point-estimate `HOLDOUT-DTI` over the matched `pta_naive_sym` control (`0.093374 [0.082536, 0.104402]`) by **`+0.003310`** (winning 3 of 4 folds, including `+0.01240` in Fold 1), though the paired 95% CI `[-0.002587, +0.009260]` straddles zero (`-0.00259`). Thus `+0.00556` of the gain over `sub8_raw` arises from multi-scale spatial derivative context shared with `pta_naive_sym`, and `+0.00331` is the point-estimate increment from unit + dip-polarity specificity.
4. **Honest negative promotion decision (`pta1_cand` vs `core19`):**  
   On the public scarp-mapped Quaternary fault catalogue (`labels.tif`), omitting `det_elev_slope` and regional habitat channels yields `pta1_cand - core19 = -0.043137` (`95% CI [-0.059768, -0.025808]`). Per Rule 5, **negative results are first-class deliverables**: `gems30-PTA1-44090-20261025-9a3f7f9535a4.tif` is published as a verified, genuinely unique downloadable GeoTIFF (`download_ok = true`), and **zero weekly competition slots are spent** (`submission_approved = false`, `slot_selected = false`).
5. **100% clean two-stage novelty across all 194 unique aligned rasters in 9 priority repos:**  
   - **Pre-placement continuous surface (`194` rasters):** `max Spearman = 0.10548 <= 0.90` (**PASSED**).  
   - **Final `44,090` Poisson-thinned dots (`194` rasters):** `max Spearman = 0.03191 <= 0.90`, `max fraction within 3 px = 0.54597 (54.60%) <= 0.70` (**PASSED**).  
   - Against the 9 priority historical submissions (`GEMSDOE24..36`), `<=3 px` dot overlap is only **`19.74%` (`GEMSDOE32` H33) to `30.93%` (`GEMSDOE27`)**, with **`54.15%`** of `PTA-1` dots placed in `<5°` basin/piedmont terrain (vs `19.1%` for `H33` and `39.9%` for `G30-S19`).

---

## 2. Complete Quantitative Holdout Ledger (`HOLDOUT-DTI`)

All values below are **`HOLDOUT-DTI`** under `component-holdout-v3-blockstats-20261025` / `buffered-quadrant-whole-components-v1-20261025` (`60,988` withheld positive pixels, `371` geographic bootstrap blocks, `2,000` paired replicates, `seed = 3071`). None is an organizer score or leaderboard projection.

| Fixed Arm / Paired Contrast | Features | Fold 0 (`29,340` pos) | Fold 1 (`12,566` pos) | Fold 2 (`9,403` pos) | Fold 3 (`9,679` pos) | Pooled `HOLDOUT-DTI` | Paired 95% Spatial-Block CI |
|---|---:|---:|---:|---:|---:|---:|---|
| `core19` (full 19-band comparator) | 19 | 0.10343 | 0.15526 | 0.13613 | 0.14065 | **0.139821** | `[0.124178, 0.155905]` |
| `sub8_raw` (raw subsurface GeoDAWN/gravity/MT) | 8 | 0.07734 | 0.09602 | 0.07800 | 0.08080 | **0.087814** | `[0.076810, 0.099620]` |
| `pta_naive_sym` (1× `tmi_vg` + dip-symmetric control) | 18 | 0.08365 | 0.09321 | 0.08652 | 0.08835 | **0.093374** | `[0.082536, 0.104402]` |
| **`pta1_cand` (1000× `tmi_vg` 3D tilt + signed dip-asymmetry)** | **18** | **0.08507** | **0.10561** | **0.07796** | **0.09278** | **0.096683** | **`[0.085289, 0.108433]`** |
| *(Reference)* `TDX-1` (`tdx6`, prior subsurface session) | 6 | — | — | — | — | 0.072844 | `[0.063480, 0.083059]` |
| **`pta1_cand − sub8_raw` (subsurface value-add)** | — | +0.00773 | +0.00959 | −0.00004 | +0.01198 | **`+0.008870`** | **`[+0.001561, +0.015976]`** *(CI > 0)* |
| **`pta1_cand − pta_naive_sym` (unit + polarity specificity)** | — | +0.00142 | +0.01240 | −0.00856 | +0.00443 | **`+0.003310`** | `[-0.002587, +0.009260]` |
| **`pta1_cand − core19` (vs scarp-inclusive full stack)** | — | −0.01836 | −0.04965 | −0.05817 | −0.04787 | **`-0.043137`** | `[-0.059768, -0.025808]` |

---

## 3. Novelty Profile Against the 9 Priority Reference Sites & Full 194-Raster Registry

| Reference Site | Pinned Reference Raster | Ref Dots | Surface Spearman | Dots Spearman | `PTA-1` Fraction `<=3 px` | Status (`<=0.90` / `<=0.70`) |
|---|---|---:|---:|---:|---:|---|
| `GEMSDOE32` | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 37,654 | `0.0252` | `0.0027` | **`19.74%`** | Passed |
| `GEMSDOE36` | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 38,854 | `0.0258` | `0.0027` | **`20.25%`** | Passed |
| `GEMSDOE28` | `h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif` | 40,199 | `0.0298` | `0.0045` | **`23.34%`** | Passed |
| `GEMSDOE31` | `h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 40,199 | `0.0298` | `0.0045` | **`23.34%`** | Passed |
| `GEMSDOE33` | `h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 41,865 | `0.0324` | `0.0061` | **`25.32%`** | Passed |
| `GEMSDOE25` | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 44,090 | `0.0373` | `0.0088` | **`28.53%`** | Passed |
| `GEMSDOE30` | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 44,090 | `0.0373` | `0.0088` | **`28.53%`** | Passed |
| `GEMSDOE24` | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 60,069 | `0.0443` | `0.0095` | **`29.84%`** | Passed |
| `GEMSDOE27` | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 61,328 | `0.0452` | `0.0096` | **`30.93%`** | Passed |
| **Max across all `194` registry rasters** | `GEMSDOE30` 80k-dot EDGE research raster (`b3773335…`) | 80,000 | **`0.1055`** | **`0.0319`** | **`54.60%`** | **Passed (`<70%`)** |

---

## 4. Why `PTA-1` Matters for Beating `0.2778` / `0.3195` / `0.4413` Next

1. **Catalogue proxy bias vs hidden-test physics (`IR-30-039`, `IR-30-046`):** Public `labels.tif` traces are overwhelmingly range-front LiDAR/photogeologic scarps (`det_elev_slope` median `~12°` on catalogue vs `3.75°` across the study footprint), whereas INGENIOUS concealed geothermal structures in Dixie Valley, Carson Sink, Granite Springs Valley, and Humboldt House step basinward under low-slope (`<5°`) alluvial cover.
2. **Orthogonal subsurface base learner:** Because `PTA-1` shares only **`19.74%`** 3 px support with `H33` (`0.2778` owner-reported) and places **`54.15%`** of its dots in `<5°` basin/piedmont terrain while achieving statistically significant gain over raw subsurface bands (`+0.00887`, CI `[+0.00156, +0.01598]`), it provides the exact orthogonal **concealed-basin specialist** needed for a regime-partitioned multi-scale spatial CNN/UNet ensemble (feeding scarp channels only in bedrock/piedmont regimes and `PTA-1` unit-consistent 3D tilt + `pta_dip_cover_step` in low-slope `<3°` alluvial basins, followed by `d_cat > 2 px` flank pruning + metric-exact `EDGE` emission).
