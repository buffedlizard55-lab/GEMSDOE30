# Preregistration — Lane `MSDB-1`: Multi-Scale Steerable Discontinuity & Piedmont Cover-Breach Habitat with Bayes-Calibrated 300 m Submodular Coverage

- **Date (UTC):** `2026-10-25`
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE30` (`arena/89455fb7-gemsdoe30`)
- **Dataset signature (`data/processed/manifest.json`):** `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`
- **Frozen 9-site registry (`docs/research/msdb-piedmont/registry.json`):** `c978bdd07c90f1cb1060e15c857d460bb9fe4050d63055072bdd467859235a89` (`180` source GeoTIFFs across `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, `GEMSDOE36` → `165` unique grid-aligned rasters, `1` grid-mismatched exclusion)
- **Evaluator / Holdout Protocol:** `component-holdout-v3-blockstats-20261025` / `buffered-quadrant-whole-components-v1-20261025` (`buffer_px = 17`, `60,988` withheld fault pixels across `4` disjoint whole-component quadrant folds, `371` `128 × 128` spatial blocks)

---

## 1. Root-Cause Forensic Explanation of `GEMSDOE32` `H33` (`0.2778` `OWNER-REPORTED`) and Why Beating It Requires Both a New Physical Surface and Submodular Allocation

### 1.1 Exact Byte Forensics (`MEASURED`, verified in `docs/research/2026-10-25/recipe-reconstruction.json`)
Line-by-line byte comparison across the restored scored rasters proves with **zero pixel discrepancies (`0` non-matching pixels out of `12,279,160`)**:
1. `GEMSDOE27` `H27-4` (`gems27-hybrid-oof-ensemble-v1-20261001-235933.tif`, `121,150` binary dots, `0.1922` `OWNER-REPORTED`) was an over-dense (`~2.34%` of footprint) rank-weighted blend of 5-fold spatial OOF probabilities (`0.55` UNet-34 + `0.45` LightGBM).
2. `GEMSDOE28` solo `d=2.8` (`gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif`, `40,199` binary dots, `0.2708` `OWNER-REPORTED` on `GEMSDOE28`) applied greedy non-maximum suppression at minimum Euclidean spacing $d = 2.8\text{ px}$ (`280 m`) to the continuous `H27-4` surface, cutting dot volume by `3.01×` (`121,150 → 40,199`) and raising `OWNER-REPORTED` score by **`+0.0786` (`+40.9%`)**.
3. `GEMSDOE32` `H33` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`, `37,654` binary dots, `0.2778` `OWNER-REPORTED`) equals `GEMSDOE28` solo `d=2.8` **minus the exact `2,545` dots lying within Euclidean distance $\le 2\text{ px}$ (`200 m`) of the known USGS/INGENIOUS catalogue `labels.tif`**, adding a further **`+0.0070`**.

### 1.2 Exact Metric & Forum-Verified Mechanism (`ORGANIZER-CONFIRMED` rules, DrivenData Problem Description & Forum Threads `11516`, `11536`, `11550`, `11556`)
The official pooled Distance-Weighted Tversky Index (`page/967/`, confirmed pooled over all evaluation subset pixels in `t/11550` with no extra per-fault weights in `t/11556`) is:
$$\mathrm{DTI} = \frac{T_w}{T_w + 0.2 F_w + 0.8(|G| - T_w)} = \frac{T_w}{0.8|G| + 0.2(T_w + F_w)}, \qquad k(d) = \max\!\left(1 - \frac{d}{300\text{ m}},\, 0\right)$$
where:
- $T_w = \sum_{g \in G} \max_{d(x, g) \le 300\text{ m}} p(x) k(d(x, g))$ uses a **pointwise `max` operator** over nearby predictions (`page/967/`).
- $F_w = \sum_{p(x) > 0} p(x)\bigl[1 - \max_{g \in G} k(d(x, g))\bigr]$ uses a **linear `sum` operator** over all emitted non-zero pixels (`page/967/`).
- Known USGS/INGENIOUS fault pixels ($C = \text{labels.tif}$) are **masked/excluded** from evaluation in both Phase 1 and Phase 2 (`chrisk-dd`, `t/11516`), while `"new faults"` explicitly include **unmapped continuations, splays, and parallel strands** (`chrisk-dd`, `t/11536`).

This `max`-vs-`sum` asymmetry explains the entire `0.1922 → 0.2708 → 0.2778` trajectory:
- Placing two unit dots within $< 3\text{ px}$ of a hidden fault pixel $g$ yields **almost zero extra $T_w$** (because $\max$ saturates near $1$), while away from hidden faults every extra dot adds $+1.0$ to $F_w$ (`+0.2` in the denominator). Thinning to $d \approx 2.8\text{–}3.0\text{ px}$ preserves $>90\%$ of $T_w$ while slashing $F_w$ by $>65\%$.
- Removing dots at $0 < d(x, C) \le 2\text{ px}$ (`200 m`) strips predictions triggered by the geophysical halo of *already-mapped* USGS/INGENIOUS traces (where parallel digitization jitter is unlikely to be labeled as a distinct fault strand), while preserving $> 200\text{ m}$ step-overs, splays, and tip continuations (`t/11536`).
- **Mathematical ceiling:** At fixed recall $r = T_w / |G|$, $\mathrm{DTI} = r / [0.8 + 0.2(r + F_w/|G|)] < r / 0.8$. Even with zero false positives ($F_w = 0$), reaching the live 2026-10-25 top-10 (`0.3379–0.4413`, `#1 xiaofanhu = 0.4413`) requires substantially higher true-positive coverage $T_w/|G|$ per unit $F_w$, which cannot be achieved by further post-processing `H27-4`.

---

## 2. Newly Discovered Competition Metadata Irregularities (`MEASURED`, 2026-10-25)

Line-by-line verification of `training_features.tif` against restored `geodawn_rad_u8.tif` and exact finite-difference derivatives revealed two high-impact band-semantics errors affecting prior feature engineering across the GEMSDOE fleet:

1. **`Band 6 (tc)` is GeoDAWN Radiometric Total Count, NOT Magnetic Tilt Angle:**
   - `training_features.tif` Band 6 carries GDAL metadata `category="magnetic_data"` and `description="Tilt angle or total curvature - magnetic field derivative"`, yet its in-footprint values span `[2.953, 88.573]` (strictly positive; magnetic tilt angle is bounded in $[-\pi/2, +\pi/2]$ rad or $[-90^\circ, +90^\circ]$).
   - Cross-checking against USGS GeoDAWN radiometrics (`geodawn_rad_u8.tif` Band 4 `TC`, Glen & Earney 2024, DOI `10.5066/P93LGLVQ`) yields **`Spearman = 0.999957`** (`Pearson = 0.999951`), whereas `Spearman(Band 6, arctan2(Band 9 tmi_vg, Band 3 tmi_hg)) = 0.01597`. The competition Problem Description (`page/967/`, figure `gems_tc_tmi.png`) confirms *"radiometrics total count (left) and total magnetic intensity (right)"*.
   - **Consequence:** No raw competition band provides true Miller & Singh (1994) potential-field magnetic tilt $\arctan2(\text{tmi\_vg}, \text{tmi\_hg})$, and `Band 6` was never exploited as a surficial gamma-ray exposure-rate boundary detector.

2. **`Bands 18 & 11 (iso_grav_anom_hg, iso_grav_anom_vg)` Are Signed Image-Axis Derivatives `(dg/dx, dg/dy)`:**
   - Unlike `Band 3 (tmi_hg)` (`>= 0`, `Spearman = 0.99989` with $\|\nabla \text{tmi}\|$) and `Band 9 (tmi_vg)` (true vertical potential-field derivative $\partial_z \text{tmi}$, `Spearman = 0.7803` with $-\nabla^2 \text{tmi}$), `Band 18` spans `[-15.44, +12.86]` and `Band 11` spans `[-18.16, +12.58]`.
   - Direct finite-difference audit against `Band 13 (iso_grav_anom)` proves `Spearman(Band 18, +dg/dx) = +0.9558`, `Spearman(Band 11, +dg/dy) = +0.9357`, and `Spearman(hypot(Band 18, Band 11), Band 5 iso_grav_anom_slope) = +0.9407`.
   - **Consequence:** Prior `H-32-05` treated `|Band 18|` as total horizontal gravity gradient, inadvertently erasing E–W fault scarps (`dg/dx ≈ 0`), whereas `(Band 18, Band 11)` directly encodes the signed 2-D gravity gradient vector $\nabla g$!

---

## 3. Ranked Untried Geological Hypotheses (4 Candidates, Ranked by Expected DTI Gain vs. Implementation Cost)

| Rank | ID & Name | Exact Competition / External Layers | Physical Signature & Transform | Why USGS/INGENIOUS Misses It & Named Non-Fault Mimic | How It Differs from All Existing Fleet Lanes | Cost & Expected Gain |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1 (Selected)** | **`MSDB-1` — Multi-Scale Steerable Discontinuity & Piedmont Cover-Breach Habitat + Bayes-Calibrated 300 m Submodular Coverage** | All 19 raw bands + 18 derived local physical layers (`det_elev`, `rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `(iso_grav_anom_hg, iso_grav_anom_vg)`, `depth_to_base_surf`, `cond_surf`, `tc`, `geod_*`; optional verification against USGS GeoDAWN `10.5066/P93LGLVQ` & GDR `1391`) | True potential-field magnetic tilt $\arctan2(\text{tmi\_vg}, \text{tmi\_hg})$, zero-crossing crest $\cos\theta_{\text{tilt}}$, and Salem tilt-depth $\|\nabla\theta_{\text{tilt}}\|$; scale-normalized Hessian tubularity $|\lambda_1|-|\lambda_2|$ & relay-ramp saddle index $\sqrt{\max(-\lambda_1\lambda_2,0)}$ at $100\text{ m}$ & $300\text{ m}$; 1-D structure-tensor coherence; strike-normal $\cos^2\Delta\theta$ concordance across reconstructed $\nabla g$, $\nabla\text{rtp}$, $\nabla\text{depth\_to\_base}$, and $\nabla\text{tc}$; thin-cover piedmont ramp index; plus **Prentice–Pyke Bayes prevalence odds recalibration** feeding exact 300 m submodular `edge_select` | Quaternary range-front mapping stops where alluvial fans bury low-relief piedmont step-overs, synthetic parallel strands, and breached relay ramps (`t/11536`). **Named non-fault mimics:** volcanic flow fronts, intrusive pluton margins, and paleoshoreline/playa benches | Fixes `Band 6` and `(Band 18, Band 11)` physics errors; strictly bounded `12.73 px <= 17 px` support (zero leakage); unlike `TDX-1` (6-feat flank lag), `H-32-05` (`|dg/dx|` bug), `G30-S19` (uncalibrated `edge_select` + `d<=2` heuristic), `MSCR-1` (`GEMSDOE25`), `H29-HPVC` (`GEMSDOE27`), and `SCGP-Submod` (`GEMSDOE31`), pairs multi-physics steerable tubularity/concordance with exact Bayes case-control calibration before 300 m submodular allocation | Low–Moderate (`~4 min` on 2 CPUs); **Highest expected `HOLDOUT-DTI` gain** |
| **2** | **`MT-HF-Saddle` — Subsurface Hydrothermal-Upflow Saddle & Magnetotelluric Alteration Decoupling** | `cond_surf` (B17), `cond_2km` (B1), `heat_flow` (B10), `quat_vent_prox` (B16), `mag_thick` (B19), `rtp` (B2); external INGENIOUS MT `10.5066/P9TWT2LU` & Heat Flow `10.5066/P9BZPVUC` | Vertical conductivity inversion $\log(\text{cond\_2km}/\text{cond\_surf})$ interacted with local magnetic demagnetization troughs (argillic/chloritic alteration destroying magnetite along hydrothermal fault conduits) and `cond_surf` hyperbolic saddle breaches | Blind geothermal fault zones (e.g., McGinness Hills, Bradys step-overs) lack Quaternary surface scarps because argillic alteration softens scarp preservation under basin fill. **Named non-fault mimic:** conductive saline playa brines and flat-lying smectite-rich lacustrine clays | Unlike `H29-HPVC` (`GEMSDOE27` piedmont-vent CELF) and `H-32-01` (vent-corridor proximity gate, falsified), targets deep-vs-shallow MT decoupling + magnetic destruction rather than vent proximity | Low (`~2 min`); Moderate gain (coarser regional resolution of MT/heat-flow grids limits `300 m` localization alone; key saddle term included as B10 in `MSDB-1`) |
| **3** | **`RadTC-Fan` — Radiometric–Topographic Alluvial-Fan Truncation & Regolith Age Offset** | `tc` (B6, verified Radiometric Total Count), `det_elev` (B12), plus external GeoDAWN `K_pct`, `eU_ppm`, `eTh_ppm` (`10.5066/P93LGLVQ`, CC0) | Cross-gradient concordance $\|\nabla \text{tc}_{300\text{m}}\| \cdot \cos^2\Delta\theta(\nabla\text{tc}, \nabla\text{det\_elev})$ and K/Th fractionation steps across subtle $100\text{–}300\text{ m}$ piedmont slope breaks | Active piedmont faults juxtapose older, desert-varnished/K-leached Pleistocene fan remnants against younger Holocene wash deposits with distinct U–Th–K gamma emission even when scarp height is $< 1\text{ m}$ (invisible at 100 m DEM scale). **Named non-fault mimic:** lithologically distinct adjacent drainage catchments feeding coalescing bajadas | Never previously tested correctly because `Band 6 (tc)` was misidentified in GDAL metadata as magnetic tilt across prior pipelines | Low (`~2 min`); Moderate gain (coverage strongest on subaerial piedmonts, attenuated over playas; core `tc`–`det_elev` concordance included in `MSDB-1`) |
| **4** | **`WL-Strain` — Active Walker Lane Transtensional Strain-Partitioning & Slip/Dilation Reactivation** | `geod_dilaterate` (B8), `geod_shearrate` (B7), `geod_2ndinv` (B4), local Hessian strike $\theta_{\text{strike}}$ from `rtp`/`iso_grav_anom`; external GPS strain `10.1785/0220220153` & Faulds structural catalog `10.15121/1881483` | Orientation-resolved slip/dilation tendency: projects regional geodetic strain tensor onto inferred 100–300 m potential-field fault strike to preferentially weight NNE-striking normal splays inside NW-shearing Walker Lane transtensional step-overs | Regional Quaternary fault compilations under-sample short ($1\text{–}5\text{ km}$) oblique transfer faults and horse-tail splays inside Walker Lane accommodation zones. **Named non-fault mimic:** Mesozoic thrust or caldera ring structures aligned by chance with modern extension | Unlike `GEMSDOE36` Anderson-PINN (`H19`, neural stress regularizer), uses analytical geodetic transtensional partitioning without neural physics loss instability | Moderate (`~5 min`); Lower standalone `300 m` precision because GPS strain varies at $>10\text{ km}$ wavelength (regional habitat term included in `MSDB-1`) |

---

## 4. Preregistered Experimental Design for Rank-1 Lane `MSDB-1`

1. **Spatial Guard & Zero-Leakage Guarantee:**
   - Every filter in `src/gemsdoe30/msdb.py` uses `scipy.ndimage.gaussian_filter` with `truncate = 3.0` and maximum axial half-width `9 px` ($\sigma = 3.0\text{ px}$ or $\sigma_1 = 1.0\text{ px}$ followed by $\sigma_w = 2.0\text{ px}$: `3 + 6 = 9 px`).
   - Exact Euclidean support radius is $\sqrt{9^2 + 9^2} = \sqrt{162} = 12.727922\dots\text{ px} \le 13\text{ px} < 17\text{ px}$ (`holdout_guard_px = 17`). Any pixel within `12.728 px` of any non-finite source pixel is masked to `NaN` in derived spatial layers and imputed strictly from `train_mask` fold-local medians.
   - Zero dataset-wide quantiles, zero catalogue distance/density features, zero external rasters, and zero registry predictions enter `msdb.py`.

2. **Three Count-Matched Fixed Arms (`buffered-quadrant-whole-components-v1-20261025`):**
   - Active placement domain in fold $f$: `active = fold["score_valid"] & ~fold["visible"]`; full footprint: `valid & ~labels`.
   - Exact per-fold dot budget for all 3 arms: `count = round(44090 * count(active) / count(valid))` (`20,902`, `11,661`, `4,821`, `6,728`).
   - **Arm 1 (`core19`):** Exact 19 raw competition bands + `HGB(max_iter=120, lr=0.1, max_leaf_nodes=31)` + greedy `r = 3.0 px` Poisson-disk (`select_dots`), reproducing the repo benchmark (`0.139821`).
   - **Arm 2 (`msdb_poisson`):** 37 features (`19` raw + `18` `MSDB-1`) + regularized `HGB(max_iter=200, lr=0.06, max_leaf_nodes=31, min_samples_leaf=100, l2_regularization=1.0)` + greedy `r = 3.0 px` Poisson-disk (`select_dots`).
   - **Arm 3 (`msdb_edge`, Primary Candidate):** Exact same 37-feature fold surface as `msdb_poisson` + exact Prentice–Pyke Bayes prevalence odds recalibration (computed strictly on `fold["train_mask"]`) + exact 300 m submodular marginal-coverage allocation (`edge_select`, `max_dots = count`, `truth_mass = 1e9`).

3. **Leakage, Novelty, and Promotion Gates:**
   - **Single-feature leakage canary:** All `37` features tested solo in all `4` folds (`148` checks); alarm if raw bidirectional ROC-AUC or univariate training-only HGB ROC-AUC exceeds `0.90`.
   - **Two-stage novelty audit against frozen 165-raster registry:** Stop before placement if continuous surface `Spearman > 0.90`; stop before publication if final dots `Spearman > 0.90` or `3-px` overlap `> 0.70`.
   - **Scientific promotion criterion:** `msdb_edge` must beat **both** `core19` and `msdb_poisson` on pooled `HOLDOUT-DTI` with 2,000-replicate paired `128 × 128` spatial block bootstrap (`seed = 3071`) lower 95% confidence bound strictly `> 0.0`, zero canary alarms, and clean novelty gates.
