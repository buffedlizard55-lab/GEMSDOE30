# Three-Check Verification Protocol Results (`H-31-02r` LiDAR Scarp Dipole + Strike Continuity)

**Run:** 2026-10-03 · **Script:** `scripts/run_verification_checks.py` · **Runtime:** 63.1 s ·
**Protocol:** [`docs/research/verification-protocol.md`](verification-protocol.md) ·
**Artifact:** [`docs/research/verification-checks-results.json`](verification-checks-results.json).

---

## 1. Summary of the three checks

| Check | Criterion (`verification-protocol.md`) | Catalogue Component Frame | Independent SGMC Novelty Frame | Verdict |
| --- | --- | --- | --- | --- |
| **Check 1 — Spatial block-validation** | Pooled ΔDTI `>= +0.002` vs spacing+distance-matched control; `>= 3/4` quadrants positive; confirmation `> 0` | Δ `−0.00073` (`−0.00261` in `h33-01`), `2/4` quadrants (**fail**) | Δ **`+0.03670`** (`0.06650` vs `0.02979`), **`4/4`** quadrants (`+0.0167`, `+0.0237`, `+0.0376`, `+0.0966`) (**pass**) | **Split by frame** (withheld from slot promotion) |
| **Check 2 — Probability calibration** | 4-fold OOF isotonic reliability slope in `[0.8, 1.2]` and top-decile `val/train` precision ratio `>= 0.70` | Slope = **`0.9009`** (`[0.8, 1.2]` ✅); mean top-decile ratio = **`1.0495`**, **`4/4`** folds `>= 0.70` (**pass**) | Slope = **`0.9101`** (`[0.8, 1.2]` ✅); mean top-decile ratio = `1.0940`, `2/4` folds `>= 0.70` (NV vs CA density step) | **Pass on catalogue; slope passes on both (`0.901`, `0.910`)** |
| **Check 3 — Feature-perturbation stability** | Held-out permutation of own family removes `>= 50 %` of gain; unrelated family retains `> 0`; `>= 3/4` folds positive | — (no positive gain on catalogue proxy to decompose) | LiDAR permutation removes **`57.0 %`** of gain; full topography (`LiDAR + det_elev_slope`) removes **`97.2 %`**; unrelated `iso_grav_anom_hg` retains **`100.0 %`** (`+0.03670`); **`4/4`** folds positive (**pass**) | **Pass** |

---

## 2. Check 2 detail — 4-fold out-of-fold probability calibration

Before calibration, the raw `[0, 1]` rank surface has a reliability slope of `0.0575` because rank
scores span `[0, 1]` while the 300 m fault-proximity base rate is `~2–4 %`. Fitting `fit_bin_calibrator`
(monotone Pool-Adjacent-Violators quantile calibration) strictly on each fold's 3 buffered training
quadrants (`spatial_quadrant_masks(..., buffer_m=300.0)`) and predicting on the held-out quadrant
restores calibration across fold-local deciles:

* **Catalogue component frame (`check2_pass = true`):**
  * Pooled OOF reliability slope: **`0.9009`** (intercept `+0.0020`, target `[0.80, 1.20]`).
  * Per-fold top-decile `val / train` precision ratios: `4 / 4` folds `>= 0.70`, mean **`1.0495`**.
* **SGMC novelty frame:**
  * Pooled OOF reliability slope: **`0.9101`** (intercept `+0.0022`, target `[0.80, 1.20]`).
  * Per-fold top-decile `val / train` precision ratios: `fold_0 = 0.6275`, `fold_1 = 1.8320`,
    `fold_2 = 0.2453`, `fold_3 = 1.6713` (`mean = 1.0940`, `2 / 4` folds `>= 0.70`). The east-west
    split in fold ratios reflects the structural density difference between the Nevada (`NV_structure.shp`,
    eastern quadrants 1 and 3) and California/Modoc (`CA_structure.shp`, western quadrants 0 and 2)
    state compilations.

---

## 3. Check 3 detail — Held-out feature-perturbation stability

On the held-out SGMC novelty frame (`N = 15,000` dots, `r = 3.0 px` Poisson-disk spacing):

* **Unperturbed candidate (`scarp_dipole_continuity`):** `0.06650` DTI vs `0.02979` matched control
  (`raw_gain = +0.03670`).
* **Permuting 1 m LiDAR scarp channels (`step_max`, `lapneg_max`, `lappos_max`, `coh100`, `strike`):**
  DTI drops to `0.04556`, removing **`57.04 %`** of the gain (passes the `>= 50 %` requirement; the
  residual `0.04556` comes from the unperturbed 100 m `det_elev_slope` fallback).
* **Permuting the full topographic scarp family (`LiDAR + det_elev_slope`):** DTI drops to `0.03080`,
  removing **`97.25 %`** of the gain (collapsing to the random control `0.02979`).
* **Permuting an unrelated geophysical channel (`iso_grav_anom_hg`):** DTI remains `0.06650`,
  retaining **`100.0 %`** (`+0.03670 > 0`) of the gain.
* **Per-quadrant deltas:** `q0 = +0.01666`, `q1 = +0.02374`, `q2 = +0.03756`, `q3 = +0.09663`
  (**`4 / 4` positive**).

---

## 4. Qualitative block atlas — where `H-31-02r` helps and where it fails

Blocks are `64 × 64` pixels (`6.4 km × 6.4 km`) in UTM Zone 11N (`EPSG:32611`), ranked by
`ΔTPw = TPw(candidate) − TPw(matched_control)`.

### A. Independent SGMC novelty frame

* **Where it helps #1 — Quadrant 3 (SE), rows `[3136, 3200]`, cols `[1792, 1856]`, centroid
  `[425,750 m E, 4,191,750 m N]` (`306` hidden truth px):**
  `TPw` rises from `7.05 → 76.78` (**`ΔTPw = +69.73`**). High 1 m LiDAR `step_max`, paired
  crest-toe curvature (`lapneg_max`, `lappos_max`), and coherent 500 m strike alignment (`coh100`)
  trace out range-front and horst-bounding bedrock fault scarps mapped in the Nevada state geologic
  compilation (`NV_structure.shp`) that were omitted from the Quaternary fault compilation.
* **Where it helps #2 — Quadrant 2 (SW), rows `[2560, 2624]`, cols `[1600, 1664]`, centroid
  `[406,550 m E, 4,249,350 m N]` (`125` hidden truth px):**
  `TPw` rises from `3.31 → 50.48` (**`ΔTPw = +47.17`**). Linear range-margin scarps with strong
  500 m directional persistence localize multiple parallel strands of un-catalogued state-map
  faults within the 300 m scoring kernel.
* **Where it fails #1 — Quadrant 0 (NW), rows `[320, 384]`, cols `[320, 384]`, centroid
  `[278,550 m E, 4,473,350 m N]` (`201` hidden truth px):**
  `TPw` falls from `10.11 → 0.00` (**`ΔTPw = −10.11`**). This northwestern block lies outside the
  1 m LiDAR tile footprint (`lidar_valid == 0`) on subdued volcanic tablelands where `det_elev_slope`
  is below the global top-15,000 cutoff, so the detector emits zero dots while the dispersed random
  control places scattered dots by chance.
* **Where it fails #2 — Quadrant 1 (NE), rows `[512, 576]`, cols `[2752, 2816]`, centroid
  `[521,750 m E, 4,454,150 m N]` (`293` hidden truth px):**
  `TPw` falls from `9.48 → 0.00` (**`ΔTPw = −9.48`**). Intra-basin concealed faults in low-relief
  alluvial playa terrain have neither a 1 m topographic step nor a 100 m DEM slope anomaly, so a
  purely topographic scarp detector misses them completely.

### B. Catalogue component-holdout frame

* **Where it helps #1 — Quadrant 0 (NW), rows `[1664, 1728]`, cols `[1344, 1408]`, centroid
  `[380,950 m E, 4,338,950 m N]` (`52` hidden truth px):**
  `TPw` rises from `0.57 → 21.60` (**`ΔTPw = +21.03`**). Held-out Quaternary fault strands with
  sharp holistic 1 m LiDAR scarps along the range front are captured at `< 200 m` offset.
* **Where it helps #2 — Quadrant 2 (SW), rows `[3328, 3392]`, cols `[1536, 1600]`, centroid
  `[400,150 m E, 4,172,550 m N]` (`86` hidden truth px):**
  `TPw` rises from `0.00 → 15.67` (**`ΔTPw = +15.67`**). Strike-persistent 1 m scarp segments
  recover held-out splay traces along a steep range front where random placement places zero dots.
* **Where it fails #1 — Quadrant 0 (NW), rows `[1024, 1088]`, cols `[1600, 1664]`, centroid
  `[406,550 m E, 4,402,950 m N]` (`93` hidden truth px):**
  `TPw` falls from `9.75 → 0.06` (**`ΔTPw = −9.70`**). Buried basin-floor Quaternary faults mapped
  from subsurface/aerial-photo lineaments have subdued surface relief, so the top-15,000 scarp
  budget is spent on steeper nearby bedrock ridges instead.
* **Where it fails #2 — Quadrant 3 (SE), rows `[2496, 2560]`, cols `[1792, 1856]`, centroid
  `[425,750 m E, 4,255,750 m N]` (`69` hidden truth px):**
  `TPw` falls from `8.46 → 0.00` (**`ΔTPw = −8.46`**). Low-relief piedmont strands adjacent to
  already-masked range-front faults fall below the global scarp-dipole threshold.

---

## 5. Reproduce

```bash
python scripts/run_verification_checks.py
```
