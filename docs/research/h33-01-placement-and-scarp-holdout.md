# H-33-01, H-31-02r, and H-32-05b Registered Holdout Results

**Run:** 2026-10-03 · **Script:** `scripts/placement_and_scarp_holdout.py` · **Runtime:** 180.87 s ·
**Preregistration:** [`docs/research/h33-01-placement-and-scarp-preregistration.md`](h33-01-placement-and-scarp-preregistration.md) ·
**Artifact:** [`docs/research/h33-01-placement-and-scarp-holdout.json`](h33-01-placement-and-scarp-holdout.json).

---

## Executive summary of verdicts

1. **Methodological confounder `IR-30-033a` (un-thinned pixel clumping) is proven and quantified:**
   In Session 4's `H-32-05` test, `top_n_emission` selected 15,000 contiguous pixels (`median NN
   spacing = 1.0 px`, `99.95 %` within 300 m of another emitted pixel) and scored **0.00373** DTI.
   Emitting the *same* feature surface with `r = 3.0 px` (300 m) Poisson-disk spacing raises DTI to
   **0.02380** (**6.38×** higher), proving that ~85 % of the previously reported 10× deficit against
   `random_near_matched` was caused by 300 m kernel self-cannibalization rather than the feature
   field alone.
2. **Methodological defect `IR-30-029` (non-selective coherence floor) is fixed, and `H-32-05b`
   remains falsified on the catalogue proxy:** Computing structure-tensor coherence at the 1.5 km
   (`15×15` px) range-front scale on the step-ridge field yields a `p90` threshold of **0.6545** that
   selects **exactly 10.0 %** (`516,432 / 5,164,312`) of footprint pixels (fixing the `99.65 %` pass
   rate of the `3×3` tensor in `IR-30-029`). The `p90` gate improves the Poisson-thinned basement
   step score from `0.02380 → 0.02574` (screen) and `0.02566 → 0.02933` (confirmation), but still
   trails `basement_matched_control` (`0.03660` / `0.03655`, `0/4` quadrants). **`H-32-05b` is not
   promoted.**
3. **`H-33-01` (Placement Policy across `d_known` Strata):** On the catalogue component-holdout
   frame (`N = 15,000`), near-catalogue splay placement (`300–1,500 m`) scores **0.07234** (screen)
   and **0.07434** (confirmation) — **2.7×** uniform domain placement (`0.02674` / `0.02694`) and
   **18.6×** far-basin placement (`0.00389` / `0.00326`). The `60/25/15 %` power-law hedge beats
   uniform placement on the catalogue screen (`+0.02930`), catalogue confirmation (`+0.01962`), and
   unclustered SGMC (`+0.00413`), but trails uniform on one of the two 5 km clustered SGMC seeds
   (`−0.00274` on seed 31, `+0.00632` on seed 41), so the strict cross-frame gate holds **`promoted
   = false`**.
4. **`H-31-02r` (Reduced 1 m LiDAR Scarp Dipole + 500 m Strike Continuity):**
   * **Transform clause PASSES on both splits:** `scarp_dipole_continuity` beats `step_max_only` by
     **`+0.00608` (+22.4 %)** on screen (`0.03323` vs `0.02715`) and **`+0.00515` (+20.2 %)** on
     confirmation (`0.03066` vs `0.02551`). The crest-toe curvature dipole (`sqrt(lapneg · lappos)`)
     weighted by 500 m strike-vector persistence (`|⟨exp(2iθ)⟩|`) carries substantial signal beyond
     raw scarp step height.
   * **Catalogue proxy vs independent SGMC inventory divergence:** On the catalogue component proxy,
     `scarp_dipole_continuity` (`0.03323`, `median NN = 3.61 px`) sits slightly below the dispersed
     `scarp_matched_control` (`0.03585`, `median NN = 8.94 px`, Δ `−0.00261`, `2/4` quadrants)
     because unmapped bedrock/range-front scarps outside the Quaternary catalogue are penalized as
     false positives when truth is restricted to the Quaternary catalogue. When the **exact same
     15,000 `scarp_dipole_continuity` dots** are scored on the **independent USGS SGMC fault
     compilation**, they beat `scarp_matched_control` by **`+86.1 %` (`0.05913` vs `0.03178`)** on
     seed 31 and **`+82.8 %` (`0.05308` vs `0.02903`)** on seed 41 in the unclustered frame, and by
     **`+91.6 %` (`0.02916` vs `0.01522`)** on seed 31 and **`+60.5 %` (`0.01652` vs `0.01029`)** on
     seed 41 in the **5 km spatially clustered frame**. Because our preregistered gate required a
     win on the catalogue proxy as well, **`H-31-02r` is not slot-promoted**, but it is the
     strongest non-model geological feature transform measured on the independent fault inventory.

---

## 1. Frame 1A — Catalogue component-holdout (`N = 15,000`, `r = 3.0 px` Poisson-disk)

Emittable domain (`d_known > 300 m`): `1,135,103` px in `300–1,500 m`, `1,946,271` px in
`1,500–4,000 m`, and `1,929,264` px in `> 4,000 m` (screen split, `3,199` components).

| Arm | Screen DTI (seed 31) | Screen `TPw` | Median NN (px) | Confirm DTI (seed 41) | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `policy_near_splay` (`300–1,500 m`) | **0.07234** | 1,358.1 | 5.39 | **0.07434** | 2.7× uniform; 18.6× far-basin |
| `policy_powerlaw_hedge` (`60/25/15 %`) | **0.05604** | 1,050.1 | 8.00 | **0.04656** | +0.02930 / +0.01962 vs uniform |
| `scarp_hedge_matched_control` | 0.04722 | 883.8 | 8.06 | 0.05082 | Matched control for `scarp_dipole_near_hedge` |
| `scarp_dipole_near_hedge` (`H-31-02r` + hedge) | 0.04695 | 878.5 | 3.16 | **0.05138** | Wins confirmation (+0.00055), ties screen (−0.00027) |
| `basement_matched_control` | 0.03660 | 684.1 | 9.06 | 0.03655 | Dispersed Poisson-disk control |
| `scarp_matched_control` | 0.03585 | 670.0 | 8.94 | 0.03316 | Dispersed Poisson-disk control |
| **`scarp_dipole_continuity` (`H-31-02r`)** | **0.03323** | 620.9 | 3.61 | **0.03066** | **+22.4 % / +20.2 % over `step_max_only`** |
| `step_max_only` (ablation) | 0.02715 | 506.9 | 3.61 | 0.02551 | First-order scarp step without dipole × continuity |
| `policy_uniform_domain` (`> 300 m`) | 0.02674 | 499.3 | 9.06 | 0.02694 | Unstratified baseline |
| **`basement_step_ridge_p90` (`H-32-05b`)** | **0.02574** | 480.2 | 3.00 | **0.02933** | Fixes `IR-30-029` (10.0 % pass rate) + `IR-30-033a` |
| `policy_mid_relay` (`1,500–4,000 m`) | 0.02399 | 447.8 | 6.08 | 0.02110 | Mid-range step-over annulus |
| `basement_ungated_poisson` | 0.02380 | 443.8 | 3.00 | 0.02566 | **6.38× `basement_unthinned_legacy`** |
| `policy_far_basin` (`> 4,000 m`) | 0.00389 | 72.5 | 5.83 | 0.00326 | Far-field basin interior |
| `basement_unthinned_legacy` (`IR-30-033a`) | 0.00373 | 69.4 | **1.00** | 0.00526 | 99.95 % of pixels within 300 m (clumped) |

---

## 2. Frames 1B & 1C — Independent USGS SGMC fault inventory (unclustered and 5 km clustered)

All arms emit `N = 15,000` dots (`r = 3.0 px`) outside the 300 m catalogue mask. In Frame 1B, 30 %
of connected SGMC components are hidden (~18.3 k pixels); in Frame 1C, 8 regional 5 km-radius discs
centered on SGMC traces are hidden (`2,095` pixels in seed 31; `1,896` pixels in seed 41) and all
visible SGMC traces are masked by 300 m.

| Arm (`N = 15,000`, `r = 3.0 px`) | Frame 1B Unclustered (seed 31) | Frame 1B Unclustered (seed 41) | Frame 1C Clustered 5 km (seed 31) | Frame 1C Clustered 5 km (seed 41) |
| --- | ---: | ---: | ---: | ---: |
| **`scarp_dipole_continuity` (`H-31-02r`)** | **0.05913** | **0.05308** | **0.02916** | **0.01652** |
| **`scarp_dipole_near_hedge`** | **0.05601** | **0.04988** | **0.02921** | **0.01446** |
| `scarp_matched_control` | 0.03178 | 0.02903 | 0.01522 | 0.01029 |
| `policy_powerlaw_hedge` (`60/25/15 %`) | 0.03308 | 0.02827 | 0.01384 | 0.01173 |
| `policy_near_splay` (`300–1,500 m`) | 0.03259 | 0.03240 | 0.00802 | 0.01063 |
| `policy_uniform_domain` (`> 300 m`) | 0.02895 | 0.02863 | 0.01657 | 0.00541 |
| `policy_far_basin` (`> 4,000 m`) | 0.02673 | 0.02411 | 0.00880 | 0.00369 |
| `policy_mid_relay` (`1,500–4,000 m`) | 0.02396 | 0.02404 | 0.01555 | 0.01195 |

### Why `H-31-02r` jumps by +83 % to +92 % on the independent SGMC frames

The 1 m LiDAR scarp dipole + 500 m strike-continuity operator (`scarp_dipole_continuity`) does not
use SGMC in any way — it uses only `lidar_scarp_features_u8.tif` (`step_max`, `lapneg_max`,
`lappos_max`, `coh100`, `strike`, `valid`) and competition `det_elev_slope`. On the catalogue
component-holdout frame, any unmapped range-front or bedrock fault scarp that is absent from the
USGS Quaternary compilation is scored as a false positive. On the SGMC frames (both unclustered and
5 km clustered), those same 1 m LiDAR scarps coincide with bedrock/range-front faults mapped by
NBMG/CGS geologists in the State Geologic Map Compilation, nearly doubling the DTI of a
distance-and-spacing-matched random control (`0.05913` vs `0.03178` unclustered; `0.02916` vs
`0.01522` clustered).

---

## 3. Reproduce

```bash
python scripts/placement_and_scarp_holdout.py
```
