# Scientific Review & Experimental Record — Lane `MSDB-1v2` (`2026-10-25`)

- **Observed-Registry-Distinct Research Artifact (not an approved submission):** [`docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif`](../../downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif). Download for audit/reproducibility only; **do not upload**.
- **SHA-256:** `22850984a68c393f60c6cc9aeafd8d74fd8a3479654bdfcfd3626a4b99ff0381`
- **Submission Name:** `gems30-MSDB1-edge44090-20261025-e7856ec3f14a`
- **Submission Note (`119 / 140` chars):** `MSDB-1v2: 31-feat stationary discontinuity+piedmont ramp HGB x Rayleigh curv gate + Bayes 300m EDGE, 44090 off-cat dots`
- **Machine-Adjudicated Receipts:** [`run-card.json`](run-card.json) · [`readiness.json`](readiness.json) · [`results.json`](results.json) · [`validation.json`](validation.json) · [`browser-check.json`](browser-check.json) · [`preregistration.md`](preregistration.md)

> **2026-10-26 readiness correction (`IR-MSDB-06`):** the shared gate contract now
> enforces the frozen `msdb_edge > msdb_poisson` positive-CI requirement in addition
> to `core19`. Its CI is `[-0.002173, +0.004628]`, so `paired_improvement` is
> **failed**. No raster, model, holdout number, or experiment was changed; the file
> remains download-only and **NOT APPROVED FOR SUBMISSION**.

---

## 1. Automated Gate Summary (Zero Human Inspection Required)

| Gate | Automated State | Measured Value / Evidence |
| :--- | :--- | :--- |
| **GeoTIFF Format, Grid & `EPSG:32611` CRS** | **`PASSED`** | `1` band `float32`, `3730 × 3292` at `100 m`, exact `sample_submission.tif` geotransform |
| **Portal Range `[0, 1]` & In-Footprint Finite** | **`PASSED`** | `5,167,373 / 5,167,373` valid pixels finite in `[0.0, 1.0]`; `NaN` nodata outside footprint |
| **Exact Known-Catalogue Exclusion (`t/11516`)** | **`PASSED`** | `0` positive predictions on all `60,988` known USGS/INGENIOUS fault pixels; `44,090` off-catalogue dots |
| **Observed 9-Site / 165-Raster Surface Novelty** | **`PASSED`** | Max full-footprint `Spearman = 0.154504 <= 0.90` across `165` unique aligned GeoTIFFs (`180` files across `GEMSDOE24,25,27,28,30,31,32,33,36`) |
| **Observed 9-Site / 165-Raster Final-Dot Novelty** | **`PASSED`** | Max `Spearman = 0.063378 <= 0.90`; Max `3-px` overlap `= 64.7789% <= 70.00%` (`0` duplicates) |
| **Single-Feature Leakage Canaries (`37 × 4`)** | **`PASSED`** | `0 / 148` alarms (`max univariate AUC = 0.6419 <= 0.90` across all `37` raw + derived features in `4` folds) |
| **Paired Buffered `HOLDOUT-DTI` vs `core19` Baseline** | **`PASSED (+27.6%)`** | `msdb_edge = 0.170462 [0.156227, 0.184168]` vs `core19 = 0.133628 [0.118285, 0.148875]`; paired $\Delta = \mathbf{+0.036834}$ (`95% CI: [+0.022322, +0.050315]`), winning **`4 / 4` disjoint spatial quadrants** |
| **Internal Emitter Ablation (`msdb_edge` vs `msdb_poisson`)** | **`TIE (+0.00114)`** | `msdb_edge - msdb_poisson = +0.001135` (`95% CI: [-0.002173, +0.004628]`); `96.9%` (`+0.035698 [+0.021622, +0.048841]`) of total gain comes from the `MSDB-1v2` geological representation |
| **Conservative Weekly-Slot Governance (`readiness.py`)** | **`negative` (unapproved)** | Because internal `msdb_edge - msdb_poisson` 95% CI includes `0` (`-0.00217`) and external session/UNet-checkpoint inventories are `unknown`, `readiness.py` records `research_verdict = "negative"` and `submission_approved = false` rather than auto-approving a `3/week` competition slot |

---

## 2. Verified Competition Rules, Official Clarifications & Audited Data Sources

Every external reference below was directly fetched and verified on `2026-10-25`:

1. **DrivenData Competition Overview & Problem Specification:**
   - Overview: <https://www.drivendata.org/competitions/306/competition-doe-gems/> — Administered by National Laboratory of the Rockies (NLR) for the U.S. DOE Geothermal Technologies Office (`$300,000` prize pool: `$50,000` Initial Round across top 5 × `$10,000`; `$250,000` Final Round `$100k / $70k / $40k / $25k / $15k`). Note deadline discrepancy (`IR-MSDB-03`): DrivenData lists `Dec. 3, 2026, 11:59 p.m. UTC`, whereas NLR Official Rules Appendix A.1 specifies `5:00 p.m. ET` (`22:00 UTC`).
   - Problem Description & Metric: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> — Official Distance-Weighted Tversky Index (`alpha = 0.2`, `beta = 0.8`, linear buffer `R = 300 m` = `3 px` at `100 m` resolution on `EPSG:32611` <https://epsg.io/32611>; background on Tversky 1977 set similarity: <https://en.wikipedia.org/wiki/Tversky_index>). Single-band `float32` GeoTIFF in `[0, 1]` inside data bounds, `null`/`NaN` outside.
   - Official Rules PDF (Sept. 2026): <https://docs.nlr.gov/docs/fy26osti/96647.pdf> — Strict **3 submissions per 7-day rolling week** (§3.4); **1 final submission** selected for prize evaluation (§3.4–3.6.2); generative AI permitted with disclosure outside narrative word count (§3.2); external data permitted if publicly accessible, non-proprietary, and shareable under license (§3.2).
   - Live Public Leaderboard Snapshot (`2026-10-25`, `ORGANIZER-PUBLISHED` public leaderboard): <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> — `#1 xiaofanhu = 0.4413`, `#2 cfld__ = 0.3916`, `#3 Batik Shirt Brothers = 0.3904`, `#4 BrandenKMurray = 0.3724`, `#5 No Fault of Our Own = 0.3539`, `#9 DARD = 0.3398`, `#10 Azazel = 0.3379`.

2. **DrivenData Staff (`chrisk-dd`) Forum Rulings (`ORGANIZER-CONFIRMED` scoring mechanics):**
   - Known-fault masking (<https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>): *"Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards penalty terms."* Same mask applies in Final Round.
   - Definition of `"new faults"` (<https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536>): *"A 'new fault' refers to any fault pixel that is not already captured by the existing USGS or INGENIOUS fault datasets. This includes newly mapped continuations, splays, or parallel strands of an existing fault system."*
   - Pooled pixel aggregation (<https://community.drivendata.org/t/pooling-of-tversky-index-calculations/11550>): $T_w, F_w, \text{FN}_w$ are pooled globally over all evaluation pixels into one Tversky ratio (not averaged per tile).
   - Phase 2 label revisions (<https://community.drivendata.org/t/clarifying-test-revisions-and-fault-weighting/11556>): Final Round expert review may add, remove, or revise evaluation fault traces; no extra per-fault weighting exists beyond the published DW-Tversky equation.

3. **Official Public Geoscience Compilations & Licenses:**
   - **GBCGE / OpenEI GDR `1391` INGENIOUS Dataset** (Ayling, Faulds et al., 2022, DOE GTO `DE-EE0009254`, **CC BY 4.0**): <https://gdr.openei.org/submissions/1391> & <https://gbcge.org/current-projects/ingenious/> (DOI `10.15121/1881483`; sub-datasets: Heat Flow `10.5066/P9BZPVUC`, Gravity & Magnetics `10.5066/P9Z6SA1Z`, Magnetotelluric Conductance `10.5066/P9TWT2LU`, Slip & Dilation Tendency `10.5066/P9YL58W6`, Geodetic Strain `10.1785/0220220153`).
   - **USGS GeoDAWN Airborne Magnetic & Radiometric Survey** (Glen & Earney, 2024, **CC0 1.0 Public Domain**): <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> (DOI `10.5066/P93LGLVQ`, `149,030` line-km across `51,857 km²` of NW Nevada / SE Oregon).
   - **Organizer Reference Solution Notebook:** <https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb>.

---

## 3. PhD Root-Cause Analysis: Why `GEMSDOE32` `H33` (`0.2778` `OWNER-REPORTED`) Topped the Fleet and How to Beat It

### 3.1 Exact Byte-Level Reconstruction (`0` Pixel Differences)
Direct array comparison (`docs/research/2026-10-25/recipe-reconstruction.json`) establishes exact deterministic lineage across three generations:
1. **`GEMSDOE27` `H27-4` (`0.1922` `OWNER-REPORTED`, `121,150` binary dots):** 5-fold spatial OOF rank-blend (`0.55` UNet-34 + `0.45` LightGBM) thresholded densely (`2.34%` of footprint).
2. **`GEMSDOE28` solo `d=2.8` (`0.2708` `OWNER-REPORTED`, `40,199` binary dots):** Greedy minimum-spacing suppression at Euclidean radius $d = 2.8\text{ px}$ (`280 m`) on the `H27-4` continuous surface (`+0.0786` jump).
3. **`GEMSDOE32` `H33` (`0.2778` `OWNER-REPORTED`, `37,654` binary dots):** Exact set difference removing the `2,545` dots of `GEMSDOE28` solo `d=2.8` within Euclidean distance $\le 2\text{ px}$ (`200 m`) of `labels.tif` (`0` pixel diffs across all `12,279,160` cells; `+0.0070` jump).

### 3.2 Why This Worked Under DW-Tversky (`alpha = 0.2, beta = 0.8, R = 300 m`)
Writing $\mathrm{DTI} = \frac{T_w}{0.8|G| + 0.2(T_w + F_w)}$ exposes a fundamental operator asymmetry:
- **Submodular saturation of $T_w$:** Because $T_w(S) = \sum_{g \in G} \max_{x \in S} p(x) k(d(x, g))$ takes a **`max`** over `3 px` (`300 m`) balls, placing 3–4 adjacent dots inside one `300 m` fault neighborhood yields almost zero marginal $T_w$ beyond a single centered dot.
- **Additive accumulation of $F_w$:** Because $F_w(S) = \sum_{x \in S} p(x)[1 - \max_{g \in G} k(d(x, g))]$ **`sums`** over every emitted pixel, redundant cluster dots outside `300 m` of hidden truth inflate $0.2 F_w$ linearly. Spacing dots by $d \approx 2.8\text{–}3.0\text{ px}$ cut $F_w$ by roughly two-thirds while retaining $>90\%$ of $T_w$.
- **Off-mask digitization-halo pruning (`<= 2 px`):** Known catalogue pixels ($d=0$) are masked (`t/11516`), but raw geophysical gradients peak across those mapped scarps, spilling high model probabilities `100–200 m` (`1–2 px`) perpendicular to mapped traces where digitization jitter rarely represents a separate unmapped strand. Removing $d \le 2\text{ px}$ eliminated `2,545` near-catalogue false positives while preserving $> 200\text{ m}$ splays, step-overs, and along-strike continuations (`t/11536`).

### 3.3 Why Post-Processing Alone Plateaus Near `~0.28` and How to Reach `0.34–0.44`
Even if $F_w$ were driven toward zero, $\mathrm{DTI} \le \frac{T_w/|G|}{0.8 + 0.2(T_w/|G|)}$: reaching `0.35–0.44` requires substantially higher **true-positive recall $T_w/|G|$ per unit $F_w$** on concealed and subtle faults. Across the 9 priority sites, prior feature pipelines were handicapped by three structural bottlenecks:
1. **Two unflagged `training_features.tif` metadata bugs (`IR-MSDB-01`, `IR-MSDB-02`):** `Band 6 (tc)` is **GeoDAWN Radiometric Total Count** (`Spearman = 0.999957`), *not* magnetic tilt angle (`Spearman = 0.01597`), meaning no tree model ever had true Miller–Singh potential-field tilt $\arctan2(\text{tmi\_vg}, \text{tmi\_hg})$; and `(Band 18, Band 11)` are signed grid derivatives `(+dg/dx, +dg/dy)`, *not* unsigned horizontal gradient / vertical potential-field derivative.
2. **Cross-region covariate shift from non-stationary DC levels:** Including raw potential-field DC levels (`mag_anom`, `rtp`, `iso_grav_anom`, `tmi`) and 100-km smooth regional proxies (`deq_n100a15`, `ieq_n100a15`) caused boosted trees to memorize training-quadrant regional blobs rather than learning stationary 100–300 m fault-discontinuity physics.
3. **2-D blob bias in uncalibrated `EDGE`:** Case-control subsampling (`1:6`) concavely compresses posterior odds, inflating diffuse 2-D background blobs (`29`-pixel kernel weight sum `10.68`) relative to 1-D fault traces (`line weight sum 3.00`) unless Prentice–Pyke Bayes recalibration and 1-D curvilinear gating are applied.

---

## 4. `MSDB-1v2` Experimental Results (`component-holdout-v3-blockstats-20261025`)

All three arms were evaluated on the exact same `4` buffered whole-component spatial quadrant folds (`buffer_px = 17 >= physical_support_px = 13`, `60,988` withheld fault pixels, `371` `128 × 128` geographic blocks, `2,000` paired spatial-block bootstrap draws, identical active dot budgets `20,902 + 11,661 + 4,821 + 6,728 = 44,112` across folds):

| Fixed Arm | Pooled `HOLDOUT-DTI` | 95% Spatial Bootstrap CI | Pooled $T_w$ | Pooled $F_w$ | Fold 0 (`29,340` px) | Fold 1 (`12,566` px) | Fold 2 (`9,403` px) | Fold 3 (`9,679` px) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `core19` (19 raw bands + HGB + `r=3.0` Poisson) | `0.133628` | `[0.118285, 0.148875]` | `7,813.0` | `40,577.6` | `0.114868` | `0.162571` | `0.141962` | `0.143208` |
| `msdb_poisson` (31 stationary MSDB × Rayleigh gate + `r=3.0` Poisson) | `0.169326` | `[0.154797, 0.183273]` | `9,940.9` | `39,650.4` | `0.142496` | `0.228334` | `0.156235` | `0.182014` |
| **`msdb_edge` (`MSDB-1v2` + Bayes 300 m `EDGE`)** | **`0.170462`** | **`[0.156227, 0.184168]`** | **`10,006.7`** | **`39,558.7`** | **`0.144724`** | **`0.229667`** | **`0.158919`** | `0.178326` |

### Key Findings
- **Massive, uniform spatial generalization gain (`+27.6%`, `4 / 4` folds):** `msdb_edge` improves pooled `HOLDOUT-DTI` over `core19` by **`+0.036834`** (`95% CI: [+0.022322, +0.050315]`), increasing true-positive weighted fault recovery $T_w$ by **`+2,193.7` (`+28.1%`)** while simultaneously *lowering* false-positive weight $F_w$ by **`-1,018.9`**. Compare this with preserved `TDX-1` (`tdx6 = 0.072844`), which lost to `core19` by `-0.0670` on the same evaluator.
- **Clean decomposition of feature vs. placement gain:** `msdb_poisson - core19 = +0.035698` (`95% CI: [+0.021622, +0.048841]`), whereas `msdb_edge - msdb_poisson = +0.001135` (`95% CI: [-0.002173, +0.004628]`, winning `3 / 4` folds). Once the Rayleigh curvilinear gate collapses diffuse 2-D blobs onto 1-pixel-wide 1-D structural ridges, greedy `r=3.0 px` Poisson-disk and 300 m submodular `EDGE` allocate nearly equivalent trace coverage, with `EDGE` adding modest extra credit (`+65.8` $T_w$, `-91.7` $F_w$) at fault junctions and splays.

---

## 5. Limitations & Prioritized Next Steps

1. **Catalogue-recovery holdout is a proxy, not organizer test truth:** Withheld USGS/INGENIOUS segments over-represent geomorphically expressed range-front faults relative to subtle expert-mapped hidden test splays (`page/967/`). No `HOLDOUT-DTI` number may be projected onto the `0.4413` public leaderboard.
2. **Multi-scale convolutional / U-Net spatial context on the `MSDB` tensor:** Boosted trees (`HGB`) only access `100–300 m` (`<= 12.73 px`) Gaussian derivatives at a point, whereas multi-kilometer fault continuity (connecting discontinuous piedmont scarps across `1–3 km` alluvial washes) requires receptive fields of `32–128 px` (`3.2–12.8 km`) trained directly with a differentiable soft-Tversky (`alpha = 0.2, beta = 0.8`, `300 m` kernel) loss on the stationary 31-channel `MSDB` stack (with holdout `buffer_px` expanded to match the CNN receptive field).
3. **High-resolution external public-domain layers:** Incorporating unquantized USGS 3DEP `1/3`-arcsec (`~10 m`) scarp curvature and unquantized USGS GeoDAWN `K / eU / eTh` float32 grids (`10.5066/P93LGLVQ`, CC0) with strictly fold-local scaling is the highest-leverage external data upgrade for the next session.

---

## 6. Three-Pass Implementation & Verification Record

- **Pass 1 (Implementation & End-to-End Execution):** Restored and SHA-256-verified raw/external rasters and cell-verified `data/processed/`; discovered `Band 6 (tc)` and `(Band 18, Band 11)` metadata bugs; snapshotted 180 TIFFs (`165` unique aligned) across all 9 priority repos; implemented `src/gemsdoe30/msdb.py` + perturbation/physics unit tests (`tests/test_msdb.py`); generalized `readiness.py` and `verify_current_run.py`; caught and halted Experiment 1's `71.44%` `G30-S19` blob overlap prior to fold evaluation; executed Experiment 2 (`MSDB-1v2`, `+0.036834` over `core19`, `0/148` canary alarms, `64.78% <= 70%` novelty pass).
- **Pass 2 (Bug, Assumption & Edge-Case Audit):** Verified `verify_current_run.py` single-canonical-download invariant; fixed hardcoded `RESEARCH` paths in `build_research_site.py` and `tests/test_research_release.py` while keeping `isolated_evidence` pinned to `TDX-1`'s 108-file fixture; verified `build_status.py` dynamic pointer resolution and zero-approval-phrase safety rules.
- **Pass 3 (Prompt & Release Completeness Re-Check):** Verified verbatim `owner-prompt.txt` preservation in `README.md`, 119-row quarantined `owner-claims.csv`, deterministic site build (`build_research_site.py --check`), full test suite (`pytest`), clean `git status`, and PR CI verification prior to merge.
