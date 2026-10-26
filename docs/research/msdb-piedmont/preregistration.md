# Preregistration — Lane `MSDB-1` (Experiment 2 of 3): Curvilinear Discontinuity-Gated Multi-Physics Piedmont Habitat with Bayes-Calibrated 300 m Submodular Coverage

- **Date (UTC):** `2026-10-25`
- **Repository / Branch:** `buffedlizard55-lab/GEMSDOE30` (`arena/89455fb7-gemsdoe30`)
- **Dataset signature (`data/processed/manifest.json`):** `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`
- **Frozen 9-site registry (`docs/research/msdb-piedmont/registry.json`):** `c978bdd07c90f1cb1060e15c857d460bb9fe4050d63055072bdd467859235a89` (`180` source GeoTIFFs across `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, `GEMSDOE36` → `165` unique grid-aligned rasters, `1` grid-mismatched exclusion)
- **Prior Experiment Accounting (`1 of 3` used, `194.62 s` elapsed, `0` holdout folds evaluated):** Experiment 1 (`docs/research/msdb-piedmont/experiment-1-duplicate-stop/receipt.json`) fed all 19 raw regional bands directly alongside the 18 `MSDB` discontinuity features into un-gated 2-D `EDGE`, causing diffuse basin-interior dots to overlap `G30-S19`'s `60,000`-dot raw-19-band habitat EDGE raster at `71.44%` (`> 70.00%` limit by `1.44` percentage points, despite low continuous surface `Spearman = 0.1489`). Per Parallel-Run Protocol Rule 1, Experiment 1 stopped immediately **prior to running or inspecting any holdout fold**. Experiment 2 (`2 of 3`) eliminates the regional coordinate-proxy/DC-level bands and enforces a parameter-free Rayleigh 1-D curvilinear-discontinuity gate before placement.
- **Evaluator / Holdout Protocol:** `component-holdout-v3-blockstats-20261025` / `buffered-quadrant-whole-components-v1-20261025` (`buffer_px = 17`, `60,988` withheld fault pixels across `4` disjoint whole-component quadrant folds, `371` `128 × 128` spatial blocks)

---

## 1. Root-Cause Forensic Analysis of `GEMSDOE32` `H33` (`0.2778` `OWNER-REPORTED`)

1. **Exact Byte Identity (`MEASURED`, `docs/research/2026-10-25/recipe-reconstruction.json`):**
   - `GEMSDOE27` `H27-4` (`121,150` binary dots, `0.1922` `OWNER-REPORTED`) → `GEMSDOE28` solo `d=2.8` (`40,199` binary dots, `0.2708` `OWNER-REPORTED`, greedy minimum spacing $d = 2.8\text{ px}$) → `GEMSDOE32` `H33` (`37,654` binary dots, `0.2778` `OWNER-REPORTED`, `0` pixel diffs vs removing the `2,545` dots at Euclidean distance $\le 2\text{ px}$ from `labels.tif`).
2. **Metric Algebra (`ORGANIZER-CONFIRMED` rules, DrivenData `page/967/` & Forum Threads `11516`, `11536`, `11550`, `11556`):**
   - Official pooled score: $\mathrm{DTI} = T_w / [0.8|G| + 0.2(T_w + F_w)]$ with $300\text{ m}$ (`3 px`) linear kernel $k(d) = \max(1 - d/300\text{ m}, 0)$.
   - Known USGS/INGENIOUS catalogue pixels are masked from both $T_w$ and $F_w$ (`t/11516`), while `"new faults"` explicitly include unmapped continuations, splays, and parallel strands (`t/11536`).
   - Because $T_w$ aggregates nearby predictions via **`max`** whereas $F_w$ aggregates via **`sum`**, spacing dots at $\sim 2.8\text{–}3.0\text{ px}$ and pruning immediate digitization-halo pixels cuts $F_w$ by $>65\%$ while preserving $>90\%$ of $T_w$. Reaching the live top-10 (`0.3379–0.4413`, `#1 = 0.4413`) requires raising true-positive recall $T_w/|G|$ per unit $F_w$ via new physical fault-discontinuity features and submodular 300 m kernel coverage.

---

## 2. Newly Discovered Competition Metadata Irregularities (`MEASURED`, 2026-10-25)

1. **`Band 6 (tc)` Is GeoDAWN Radiometric Total Count (`Spearman = 0.999957` with USGS GeoDAWN `TC`), NOT Magnetic Tilt Angle (`Spearman = 0.01597` with $\arctan2(\text{tmi\_vg}, \text{tmi\_hg})$).**
2. **`Bands 18 & 11 (iso_grav_anom_hg, iso_grav_anom_vg)` Are Signed Image-Axis Derivatives `(+dg/dx, +dg/dy)` (`Spearman = +0.9558, +0.9357`), NOT Unsigned $\|\nabla_h g\|$ / Potential-Field $\partial_z g$.**
3. **Bands `1, 10, 16, 19` (`mag_anom`/`cond_2km`, `deq_n100a15`/`heat_flow`, `ieq_n100a15`/`quat_vent_prox`, `det_elev_slope`/`mag_thick`) Disagreement Between GDAL Tags and Organizer Reference Notebook Cell 5 (`IR-30-059`).**

---

## 3. Ranked Untried Geological Hypotheses (4 Candidates)

1. **Rank 1 (Selected — `MSDB-1` v2):** *Curvilinear Discontinuity-Gated Multi-Physics Piedmont Habitat + Prentice–Pyke Bayes-Calibrated 300 m Submodular Coverage.* Combines 18 bounded-support (`<= 12.73 px < 17 px` guard) steerable Hessian tubularity/saddle, structure-tensor strike coherence, true Miller–Singh magnetic tilt & Salem tilt-depth, reconstructed `(dg/dx, dg/dy)` strike concordance, GeoDAWN `tc` radiometric fan-truncation gradient, and thin-cover piedmont basement ramp features with the 13 stationary local/tectonic raw bands (excluding the 6 regional DC-level / 100-km coordinate-proxy bands `0, 1, 9, 12, 13, 15`), gated by the fold-local Rayleigh curvilinear-discontinuity envelope $\Psi_{\text{curv}}(x) = 1 - \exp(-\frac{1}{2} S_{\text{curv}}(x)^2)$ and placed via Bayes-calibrated 300 m `edge_select`. **Named non-fault mimics:** volcanic lava-flow fronts, non-tectonic intrusive pluton contacts, paleoshoreline/playa benches, and contrasting bajada catchment boundaries.
2. **Rank 2 (`MT-HF-Saddle`):** *Subsurface Hydrothermal-Upflow Saddle & Magnetotelluric Alteration Decoupling* (`cond_2km/cond_surf` inversion + magnetic magnetite-destruction troughs; INGENIOUS MT `10.5066/P9TWT2LU` & Heat Flow `10.5066/P9BZPVUC`; mimic: conductive saline playa clays).
3. **Rank 3 (`RadTC-Fan`):** *Radiometric–Topographic Alluvial-Fan Truncation & Regolith Age Offset* (`tc` & USGS GeoDAWN `K, eU, eTh` `10.5066/P93LGLVQ` CC0 across low-relief piedmont slope breaks; mimic: multi-lithology coalescing bajadas).
4. **Rank 4 (`WL-Strain`):** *Active Walker Lane Transtensional Strain-Partitioning & Slip/Dilation Reactivation* (`geod_*` projected onto local potential-field strike; GPS strain `10.1785/0220220153`; mimic: older Mesozoic/caldera structures aligned with modern extension).

---

## 4. Exact Preregistered Protocol for Experiment 2 (`MSDB-1` v2)

- **Bounded Physical Support:** Every filter in `src/gemsdoe30/msdb.py` has axial half-width $\le 9\text{ px}$ and exact Euclidean support $\sqrt{9^2+9^2} = 12.728\text{ px} \le 13\text{ px} < 17\text{ px}$ (`holdout_guard_px = 17`).
- **Three Count-Matched Fixed Arms (`DOT_BUDGET = 44,090` full footprint; `round(44090 * count(active) / count(valid))` per fold):**
  1. `core19`: all 19 raw bands + `HGB(max_iter=120, lr=0.1, leaves=31)` + `r = 3.0 px` Poisson-disk (`select_dots`).
  2. `msdb_poisson`: 31 stationary local/tectonic + `MSDB` features + `HGB(max_iter=200, lr=0.06, leaves=31, min_samples_leaf=100, l2=1.0)` + Bayes recalibration $\times \Psi_{\text{curv}}(x)$ + `r = 3.0 px` Poisson-disk.
  3. `msdb_edge` (**Primary Candidate**): exact same gated surface $\pi_{\text{Bayes}}(x)\Psi_{\text{curv}}(x)$ + exact 300 m submodular marginal-coverage allocation (`edge_select`).
- **Gates:** All `37` raw + derived features tested solo across all `4` folds (`AUC <= 0.90`); continuous surface `Spearman <= 0.90` and final dots `3-px` overlap `<= 0.70` across all `165` unique aligned registry rasters; paired 2,000-draw `128 × 128` spatial block bootstrap (`seed = 3071`) requiring `msdb_edge > core19` and `msdb_edge > msdb_poisson` with lower 95% CI `> 0`.
