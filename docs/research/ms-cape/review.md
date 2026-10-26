# MS-CAPE Scientific Review, Forensic Analysis of GEMSDOE32 (`0.2778`), and Preregistered Holdout Promotion

**Branch:** `arena/18d80953-gemsdoe30`
**Declared Method Lane:** `MS-CAPE` (*Multi-Scale Cross-Physics Axial-Trace & Piedmont-Deconfounded Submodular Emitter*, `ms-cape-multiphysics-trace-v1-20261025`)
**Current Automated Verdict:** **`PROMOTE`** (`eligible_for_separate_slot_selector = true`, `download_ok = true`, `12/12` automated readiness gates passed, zero human-inspector intervention; weekly competition slot selection remains separate and no slot was consumed here)
**Primary Canonical GeoTIFF (spec-exact NaN outside):** [`docs/downloads/gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-nan.tif`](../../downloads/gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-nan.tif) (`sha256 = 002c5158103419d3c99ac48a09998113efc2e473520e78a349af36996ceb56a2`)
**Portal-Safe All-Finite Twin (bit-identical inside footprint, `0.0` outside):** [`docs/downloads/gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-zeros.tif`](../../downloads/gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-zeros.tif) (`sha256 = 3ee82868d595304ec7001df55cdee2810b8ff63e31799dc676349fe20825231a`)
**Submission Name:** `gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497`
**Submission Note (`125 / 140` chars):** `MS-CAPE 2-stage multi-physics tilt+piedmont+8az lineament+GDR/GeoDAWN upflow + 300m submodular DTI cover (44090 off-cat dots)`

---

## 1. Evidence & Score-Label Hygiene

Per the standing Parallel-Run Protocol, every numerical metric in this document carries an explicit provenance class:

1. **`HOLDOUT-DTI`** — computed locally by the shared hide-and-recover whole-component spatial evaluator (`src/gemsdoe30/holdout.py`, `component-holdout-v3-blockstats-20261025`, `buffered-quadrant-whole-components-v1-20261025`, `20 px = 2,000 m` buffer, `60,988` withheld positive pixels across `4` spatial quadrants, `371` spatial blocks, `2,000` paired spatial-block bootstrap replicates, `seed = 3071`). `HOLDOUT-DTI` is a local catalogue-recovery proxy, **never** a competition leaderboard forecast.
2. **`DIAGNOSTIC-PROXY-DTI`** — supplementary off-catalogue evaluation against independent 1:500k USGS State Geologic Map Compilation (`SGMC`) bedrock fault pixels strictly `> 300 m` from the INGENIOUS training catalogue (`61,664` positive pixels; never used as an input feature or tuning target).
3. **`OFFICIAL-LEADERBOARD-SNAPSHOT`** — read directly via manual page fetch from [`https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) on **2026-10-25 / 2026-10-26 UTC**:
   - `#1 xiaofanhu`: **`0.4413`** (30 submissions)
   - `#2 cfld__`: **`0.3916`** (17 submissions)
   - `#3 Batik Shirt Brothers`: **`0.3904`** (51 submissions)
   - `#4 BrandenKMurray`: **`0.3724`** (31 submissions)
   - `#5 No Fault of Our Own`: **`0.3553`** (43 submissions; current top-5 Phase-1 prize cutoff)
   - *Irregularity flagged (`IR-MSCAPE-01`):* the `0.3195` figure appearing in an earlier section of the standing prompt reflects the outdated **2026-10-03** snapshot (`#1 DARD = 0.3195`); the top 20 entries on the live leaderboard have all moved past `0.3273`.
4. **`OWNER-REPORTED (UNVERIFIED)`** — historical scores supplied in owner prompt text (`docs/score-ledger.csv`, `docs/research/texture-displacement/owner-claims.csv`), including `GEMSDOE32` `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778` and `GEMSDOE25` `dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600`. Because this repository holds no DrivenData submission-page receipt binding a SHA-256 to an organizer score, **`ORGANIZER-CONFIRMED` count is `0`**.

---

## 2. PhD-Level Forensic Analysis: Why and How `GEMSDOE32` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) Achieved `0.2778` Among `GEMSDOE24–36`

### 2.1 Exact Byte- and Pixel-Level Reconstruction Across the Nine Priority Sites

Direct inspection of all `105` aligned GeoTIFF artifacts across `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, and `GEMSDOE36` establishes an exact mathematical identity (0 pixel discrepancies across all `5,167,373` valid footprint cells):

$$\operatorname{supp}\!\left(\text{H33}_{\text{GEMSDOE32}}\right) \;=\; \operatorname{supp}\!\left(\text{solo-d2.8}_{\text{GEMSDOE28}}\right) \;\cap\; \left\{\,x \in \Omega_{\text{valid}} : d_{\text{Euc}}(x, C_{\text{cat}}) > 200\text{ m}\,\right\}$$

| Priority Site | Artifact | Owner-Reported Claim (Unverified) | Emitted Dots | Exact Relationship & Structural Mechanics |
|---|---|---:|---:|---|
| `GEMSDOE24` | `h25-1-dotted-h19-5-d1-5-...-nan` | `0.2477` | `84,961` | `150 m` (`d=1.5 px`) Poisson thinning of `H19-5` multiline structural/topographic belief; severe `300 m` kernel overlap inflates $FP_w$. |
| `GEMSDOE25` | `dotted-h19-5-d2-8-...-nan` | `0.2600` | `44,090` | Increases minimum inter-dot spacing to `283 m` (`d=2.8 px`), cutting redundant kernel overlap nearly in half (`+0.0123`). |
| `GEMSDOE27` | `topo-gap-closure-t-v2-on-d1-5-...` | `0.2449` | `~59k–85k` | Uncalibrated gap-closure additions onto dense `d1.5` base add false positives faster than true fault recall. |
| `GEMSDOE28` | `gems28-h36-solo-d2-8-only-...` | *(base)* | `40,199` | Cleaner `d=2.8 px` emission on `H19-5` belief, still retaining `2,545` dots at `100–200 m` (`1 <= d_cat <= 2 px`) from mapped catalogue traces. |
| `GEMSDOE30` | `gems30-TDX1-44090-...` / `g30s19` | unscored | `44,090` / `60,000` | `TDX-1` negative (`HOLDOUT-DTI = 0.0728`); `G30-S19` (`HOLDOUT-DTI = 0.1378` on strict 2 km buffered quadrant protocol). |
| `GEMSDOE31` | `h31-*` LiDAR scarp matched filters | unscored | varies | Single-modality 1 m scarp dipoles suffer alluvial-terrace / road-cut mimics when decoupled from potential-field basement structure. |
| **`GEMSDOE32`** | **`h33-h33-2-b2-...-e5eb6e7e-zeros`** | **`0.2778`** | **`37,654`** | **Deletes exact `2,545` catalogue-flank dots (`d_cat <= 2 px`) from `GEMSDOE28` solo-d2.8 and writes `0.0` outside footprint (`+0.0178` over `GEMSDOE25`).** |
| `GEMSDOE33` | `h33-01` / placement sweeps | unscored | `68,573` | Over-budget emission dilutes marginal $TP_w / FP_w$ below critical Tversky slope. |
| `GEMSDOE36` | `anderson-geothermal-pinn-38854-...` | `0.2750` | `38,854` | Appends `1,200` uncalibrated dots to `H33` (`Spearman = 0.9843`, `100%` of H33 within `3 px`), slightly diluting precision (`-0.0028`). |

### 2.2 Four Mathematical & Physical Mechanisms Explaining `0.2778`

Under the official Distance-Weighted Tversky Index ([DrivenData Problem Page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)):

$$\text{DTI}(p, G) = \frac{TP_w}{TP_w + \alpha\,FP_w + \beta\,FN_w}, \qquad \alpha = 0.2,\; \beta = 0.8,\; R = 300\text{ m},\; k(d) = \max\!\left(0,\,1 - \frac{d}{R}\right)$$

$$TP_w = \sum_{g \in G_{\text{new}}} \max_{x:\,d(x,g) < R} p(x)\,k(d(x,g)), \qquad FP_w = \sum_{x \in \Omega_{\text{eval}}} p(x)\,\Bigl[1 - \max_{g \in G_{\text{new}}} k(d(x,g))\Bigr], \qquad FN_w = |G_{\text{new}}| - TP_w$$

1. **Non-Additive `max` Credit vs. Additive Linear `FP_w` Penalty (`d ≈ 283–300 m` Disk Packing):**
   Notice the fundamental asymmetry between $TP_w$ and $FP_w$: $TP_w$ takes a **pointwise `max`** over predicted pixels within $R = 300\text{ m}$ of each hidden ground-truth fault pixel $g \in G_{\text{new}}$, whereas $FP_w$ **sums linearly** over every emitted pixel $x$. Placing two unit dots $100\text{ m}$ apart along a hidden fault trace adds almost zero additional $TP_w$ inside their overlapping $300\text{ m}$ cones, yet **doubles** the false-positive penalty whenever the trace is absent! Thinning from $d = 150\text{ m}$ (`84,961` dots in `GEMSDOE24`, `0.2477`) to $d = 283\text{ m}$ (`44,090` dots in `GEMSDOE25`, `0.2600`) eliminated ~40,871 redundant overlapping predictions without sacrificing $300\text{ m}$ fault-trace coverage.
2. **Exact Catalogue-Flank Collar (`d_cat > 200 m`) Under Known-Fault Masking:**
   Organizer staff clarified ([DrivenData Forum Thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516); [Thread 11536](https://community.drivendata.org/t/11536)) that pixels on the known USGS/INGENIOUS catalogue $C_{\text{cat}}$ are masked from evaluation, while scored targets $G_{\text{new}}$ are newly mapped expert faults and unmapped splays/extensions. Because $C_{\text{cat}}$ is rasterized at $100\text{ m}$ width, pixels at $100\text{ m} \le d(x, C_{\text{cat}}) \le 200\text{ m}$ sit inside the blurred geophysical halo of the **already-known** fault (where human photointerpreters do not re-digitize a parallel trace $100\text{ m}$ away), so they accumulate pure $\alpha\,FP_w$ penalty (`2,545` wasted dots). Conversely, pixels at $d(x, C_{\text{cat}}) = 224\text{–}300\text{ m}$ (`> 2 px`) still deliver positive triangular kernel credit onto genuine along-strike tip extensions and branching horsetail splays that emerge from mapped fault terminations!
3. **Crisp Unit Emission (`p(x) ∈ {0, 1}`) vs. Diffuse Soft Probabilities:**
   Consider a selected support $S$ of unit dots. Scaling all predictions uniformly by $\lambda \in (0, 1)$ scales $TP_w \mapsto \lambda\,TP_w$ and $FP_w \mapsto \lambda\,FP_w$, while $FN_w = |G_{\text{new}}| - \lambda\,TP_w$ **increases** for every $\lambda < 1$. Differentiating with respect to $\lambda$:
   $$\frac{\partial\,\text{DTI}(\lambda \mathbf{1}_S)}{\partial \lambda} = \frac{\beta\,|G_{\text{new}}|\,TP_w}{\bigl((1-\beta)\lambda\,TP_w + \alpha\lambda\,FP_w + \beta|G_{\text{new}}|\bigr)^2} > 0 \quad \forall\,\lambda \in (0, 1]$$
   Meanwhile, adding low-probability background haze ($p \approx 0.05\text{–}0.20$) across millions of desert basin pixels explodes $\alpha \sum p(x)$ in the denominator while never winning the `max` operator near real faults (explaining why continuous-surface submission `GEMSDOE81` collapsed to `0.0041`). *(Note per `IR-TDX-02`: while uniform scaling $\lambda \to 1$ is strictly monotonic, setting an arbitrary individual pixel $p(x_i) \to 1$ only improves DTI when its expected marginal gain satisfies $\Delta\mathbb{E}[TP_w] / \Delta\mathbb{E}[FP_w] > \frac{\alpha\,\text{DTI}}{1 - (1-\beta)\text{DTI}}$, which is the exact stopping rule enforced by submodular greedy optimization.)*
4. **All-Finite `-zeros` Encoding vs. Portal Range Validation:**
   Writing `0.0` outside the valid footprint (`12,279,160` finite `[0,1]` cells) matched the organizer reference notebook export convention while leaving all `5,167,373` scored in-footprint cells bit-identical to the canonical `NaN`-outside file.

### 2.3 Can a Genuinely Unique Submission Beat `0.2778` (and Advance Toward `0.3553–0.4413`)?

**Yes — and forensic analysis of why both `H33` (`0.2778`) and later supervised trees (`GEMSDOE70` `0.2478`, `GEMSDOE76` `0.2343`) hit a ceiling reveals the exact path:**

1. **`H33` (`0.2778`) is an unlearned hand-crafted topographic-ridge heuristic:**
   Its underlying `H19-5` score surface heavily weights raw topographic slope/openness ridges. In the Basin and Range province, eroded bedrock crags inside uplifted horst blocks exhibit dramatic topographic edges that are **erosional scarps, not active fault traces**, while buried range-front/piedmont faults and intrabasinal blind faults sit beneath low-relief coalescing alluvial bajadas (`slope < 5°`).
2. **Naive supervised GBDTs (`GEMSDOE70/76`) fell into the Basin-and-Range Steep-Terrain Confounding Trap:**
   Because range-bounding faults sit near the *base* of steep mountain fronts, 100 m pixel classifiers without multi-scale topographic context learn `high slope = fault` (`~69.5%` of emitted dots on top-quartile steep mountain slopes vs. only **`24.03%`** in the true Quaternary fault catalogue!).
3. **Pointwise pixel classifiers are blind to 1D structural continuity (`0.8–1.6 km`):**
   Geological faults are 1-manifold curves that maintain strike coherence over kilometres and bridge alluvial fans between exposed scarps; single-pixel features confuse circular volcanic plugs, playa shorelines, and GeoDAWN steep-drape clearance artifacts for faults.
4. **Poisson-disk NMS ignores anisotropic 2D `300 m` Tversky kernel geometry:**
   Isotropic radius suppression treats a narrow single-pixel peak identically to a broad multi-strand fault zone, failing to maximize expected covered fault mass $\sum_u q(u)\max_{x \in S} k(d(x,u))$.

---

## 3. Five Ranked Geological Hypotheses Generated Before Implementation

Full equations, layer lists, non-fault mimics, and falsifiable gates were frozen **before** fitting in [`docs/research/ms-cape/preregistration.md`](preregistration.md) (`sha256 = 9fd9195854b5fb1d060c7615496e17e83cc9525d8fd27e7657cc5eeefce047fc`):

| Rank | ID & Name | Specific Layers Used | Physical Signature Targeted | Why It Catches Faults Missing From USGS/INGENIOUS | Named Non-Fault Process Mimic | Expected Gain / Cost | Status |
|---:|---|---|---|---|---|---|---|
| **1** | **`MS-CAPE` (Implemented)**<br>Multi-Scale Consilient Axial Potential-Edge, Piedmont Flexure & Hydrothermal Upflow + Two-Stage Trace + `300 m` Submodular Cover | All 19 `training_features.tif` bands (`mag_anom`, `rtp`, `tmi_hg`, `geod_2ndinv`, `iso_grav_anom_slope`, `tc`, `geod_shearrate`, `geod_dilaterate`, `tmi_vg`, `deq_n100a15`, `iso_grav_anom_vg`, `det_elev`, `iso_grav_anom`, `tmi`, `depth_to_base_surf`, `ieq_n100a15`, `cond_surf`, `iso_grav_anom_hg`, `det_elev_slope`) + `lidar_scarp_features_u8` + `geodawn_rad_u8` + `geodawn_extensions_u8` + `derived_gdr_{paleo,volcanics,2m_probes}` + thermal well/spring & volcanic vent kernels (`0` catalogue/Qfaults/SGMC inputs) | Verduzco/Miller–Singh gravity (`iso_grav_anom`) & magnetic (`rtp`/`tmi`) tilt angles $\theta = \arctan(\partial_z F / \|\nabla_h F\|)$, zero-contour proximity $\cos\theta$, inverse-depth $\|\nabla_h\theta\|$, `tmi - TMI_up150`, $\|\nabla_h\text{depth\_to\_base\_surf}\|$, piedmont concavity $\nabla^2\text{det\_elev}$ & regional-relief-deconfounded slope prominence, 8-azimuth `1.1 km` & `2.5 km` surface/subsurface axial lineaments + $\cos 2(\phi_{\text{surf}}-\phi_{\text{sub}})$ strike consilience, GeoDAWN `K/Th` & `U/Th` high-pass ratios + MT `cond_surf` clay-cap edge + GDR up-gradient thermal plume, OOF Stage-2 `1.7 km` wash-gap-bridge (`min(fwd,bwd)`) + `300 m` submodular DTI cover | Concealed Basin-and-Range faults beneath Holocene bajadas or interrupted by `0.5–2 km` alluvial washes lack continuous 100 m DEM scarps yet preserve subsurface potential-field tilt zero-contours, basement steps, Strike consilience, and hydrothermal upflow conduits | Dendritic erosional mountain ridge crests & canyon walls, Lake Lahontan wave-cut shorelines & basalt rims, and GeoDAWN steep-terrain flight-drape clearance shifts ([USGS DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) | **High** (`+0.025` to `+0.055` HOLDOUT-DTI), **Low–Medium** CPU (`26.2 min`), local verified data only | **EXECUTED & PROMOTED (`+0.0510` over `core19`)** |
| **2** | **`EULER-CURV`**<br>3D Multi-Structural-Index Euler Deconvolution Worm Clustering | `rtp`, `tmi`, `tmi_hg`, `tmi_vg`, `TMI_up150`, `iso_grav_anom`, `iso_grav_anom_hg`, `iso_grav_anom_vg`, `depth_to_base_surf` (100% local) | Sliding `1.1 km` Reid et al. (1990) 3D Euler inversion $(x-x_0)\partial_x F + (y-y_0)\partial_y F + (z-z_0)\partial_z F = -N(F-B)$ for contact indices $N \in \{0, 0.5, 1\}$ | Images deep (`0.5–3 km`) buried graben-bounding faults beneath thick playa fill with zero surface expression | Sub-horizontal volcanic sill margins, pluton roofs, and `200/400 m` E–W flight-line leveling micro-corrugations | Moderate (`+0.010` to `+0.020`), Medium CPU, local data | Untested reserve lane |
| **3** | **`ANDERSON-SLIP`**<br>Principal Strain-Rate Inversion & Morris–Ferrill–Henderson Slip/Dilation Tendency | `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, `deq_n100a15`, `ieq_n100a15`, `lidar_scarp_features_u8` (`strike`), plus public USGS Slip/Dilation archive ([DOI 10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6)) | Local horizontal principal strain orientation & normal/transtensional dilation/slip tendency along candidate lineament strikes ($\sim 32\%$ of Great Basin geothermal systems; [Faulds OSTI 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722)) | Critically stressed fractures remain hydraulically open against hydrothermal sealing in blind Walker Lane transtensional step-overs | Inactive Mesozoic thrust contacts and fluvial valleys aligned by chance with NNE regional extension | Moderate (`+0.005` to `+0.015`), Low CPU | Macro-regime strike absorbed in `MS-CAPE` ch. 45 |
| **4** | **`HYDRO-PLUME`**<br>Advective-Diffusive Geothermometer Disequilibrium & Up-Gradient Fault Back-Projection | `gdr_wellspring_in_footprint.csv` (`temp_c`, `geothermquartz_c`, `geothermchalc_c`), `2m_probes`, `paleo` sinter/tufa ([DOI 10.15121/1881483](https://doi.org/10.15121/1881483)), `cond_surf`, `det_elev` | Chemical-thermal mixing disequilibrium (`T_quartz - T_obs`) projected upslope along $+\nabla\text{det\_elev}$ to intersect `cond_surf` smectite clay-cap edges | Targets the `~39%` blind geothermal systems ([Faulds et al., OSTI 1724109](https://www.osti.gov/servlets/purl/1724109)) without placing dots on shifted down-gradient outflow springs | Confined warm artesian tuff aquifers and clustered exploration wells on leased fields | Low–Moderate standalone (`+0.004` to `+0.012`), Low CPU | Up-gradient source focus absorbed in `MS-CAPE` ch. 49–50 |
| **5** | **`KNICK-DRAIN`**<br>Ephemeral Trunk-Channel Axial Deflection & Iso-Slope Knickpoint Chains | USGS 3DEP 1/3 arc-second (`~10 m`) DEM & USGS NHDPlus HR flowlines ([USGS TNM API](https://tnmaccess.nationalmap.gov/api/v1/products), Public Domain) | Aligned channel-azimuth deflections (`beheaded/offset washes`) and stream-power steepness ($k_{sn}$) knickpoint bands across adjacent piedmont fans | Desert washes preserve tectonic base-level steps for $10^4\text{–}10^5$ yr after sheetwash erases interfluve scarps | Resistant welded-tuff ledges and Pleistocene Lake Lahontan horizontal wave-cut shorelines | Uncertain (`+0.005` to `+0.018`), High I/O cost (external TNM fetch required) | Deferred external-data lane |

---

## 4. `MS-CAPE` Physical Architecture, Guard Verification, and Causal 3-Experiment Ladder

### 4.1 Zero-Leakage Physical-Support Audit (`SUPPORT_PX = 20`)

Every spatial operator in `src/gemsdoe30/ms_cape.py` uses **exact circular Euclidean disk footprints** (`r <= R`), not square boxes whose corners leak by $\sqrt{2}$:

- **Stage-1 Multi-Physics Tensor (`51` channels = `19` official bands + `32` derived, `STAGE1_SUPPORT_PX = 12` = `1,200 m`):**
  - *Group 1 — Verduzco potential-field tilt & basement contact mechanics (`8` ch):* `grav_tilt` ($\arctan(\text{iso\_grav\_anom\_vg}/\|\nabla_h\text{iso\_grav\_anom}\|)$), `grav_tilt_zero_prox` ($\cos\theta_{\text{grav}}$), `grav_verduzco_hd_tilt` ($\|\nabla_h\theta_{\text{grav}}\|$ inverse contact depth), `mag_tilt` ($\arctan(\text{tmi\_vg}/\text{tmi\_hg})$), `mag_verduzco_hd_tilt`, `rtp_total_horiz_grad`, `tmi_upward_residual` (`tmi - TMI_up150`), and `basement_step_grad` ($\|\nabla_h\text{depth\_to\_base\_surf}\|$).
  - *Group 2 — Piedmont-toe flexure & mountain-slope deconfounding (`8` ch):* `piedmont_concavity_300m` and `piedmont_concavity_900m` ($\nabla^2\text{det\_elev}$), `deconfounded_slope_prominence` (`det_elev_slope` normalized by `1.2 km` regional relief so steep mountain-interior crags do not dominate low-relief bajada scarps), `slope_break_gradient`, `basin_margin_transition`, plus 1 m LiDAR `lidar_scarp_step` (`step_max * coh100`), `lidar_signed_polarity`, and `lidar_valid_flag`.
  - *Group 3 — 8-azimuth steerable axial lineaments & strike consilience (`10` ch):* Steered directional line integrals at `1.1 km` (`±5 px`) and `2.5 km` (`±12 px`) across 8 azimuths ($0^\circ, 22.5^\circ, \dots, 157.5^\circ$) on surface scarp (`surf_axial_max_1p1km`, `surf_axial_aniso_1p1km`, `surf_axial_max_2p5km`, `surf_axial_aniso_2p5km`, `surf_cross_ridge_nms`) and subsurface potential-field contact energy (`sub_axial_max_2p5km`, `sub_axial_aniso_2p5km`, `sub_cross_ridge_nms`), plus `cross_modal_strike_consilience` ($\cos 2(\phi_{\text{surf}} - \phi_{\text{sub}})$) and `great_basin_anderson_strike`.
  - *Group 4 — Deconfounded GeoDAWN radiometrics & GDR hydrothermal upflow (`6` ch):* `1.1 km` high-pass `rad_k_th_alteration` (potassic metasomatism canceling flight-drape altitude shifts) and `rad_u_th_fracture_radon` (radon-daughter / redox fracture enrichment), `mt_clay_cap_edge` ($\|\nabla_h\text{cond\_surf}\|$), `hydro_upflow_thermal_plume`, `hydro_upgradient_source_focus` (advective up-slope projection of GDR `temp_c >= 60 °C` wells/springs along $+\nabla\text{det\_elev}$, `dist_known_fault_px` ignored), and `paleo_probe_geothermal_halo` (sinter/tufa + 2 m thermal probes + volcanic vents within `r <= 12 px`).
- **Stage-2 Out-of-Fold Axial Trace & Wash-Gap-Bridge Stacker (`10` derived OOF geometry channels, `STAGE2_SUPPORT_PX = 8` = `800 m`):**
  - Trained strictly on inner cross-fitted out-of-fold Stage-1 probabilities within each training split (`buffer_px = 20 = STAGE1_SUPPORT_PX + STAGE2_SUPPORT_PX = 2,000 m`), ensuring **zero pixels inside the held-out quadrant ever influence any Stage-1 or Stage-2 stencil**.
  - Extracts `p1_raw`, `p1_logit`, 8-azimuth directional ridge continuity at `900 m` (`±4 px`) and `1.7 km` (`±8 px`), **along-strike wash-gap bridge** `p1_gap_bridge_1700m = min(fwd, bwd)` (which remains high across an unmapped alluvial-wash gap bounded by two colinear fault segments while vanishing at isolated point mimics!), `p1_tip_continuation_1700m`, `p1_axial_anisotropy`, `p1_cross_strike_sharpness_300m`, and `800 m` local halo context.
- **Prior-Odds Recalibration + Exact `300 m` Submodular DW-Tversky Greedy Cover:**
  - Balanced class sampling (`1:4` pos:neg) is inverted analytically back to true empirical spatial fault odds (`pi_true ≈ 0.0118`) before kernel integration, preventing probability saturation from corrupting expected Tversky gains.
  - Selects `K = 44,090` unit `{0, 1}` off-catalogue dots (`d_cat > 200 m`) via lazy-greedy maximization of the submodular coverage objective:
    $$F(S) = \sum_{u \in \Omega_{\text{off}}} q(u)\,\max_{x \in S} k(d(x, u)) \;-\; \lambda_{\text{fp}} \sum_{x \in S} (1 - q(x)), \qquad \lambda_{\text{fp}} = \frac{\alpha\,\tau_0}{1 - (1 - \beta)\tau_0} = 0.0684$$

### 4.2 Preregistered 3-Experiment Results (`HOLDOUT-DTI`)

All 6 arms (`3` comparators + `3` preregistered `MS-CAPE` causal-ladder experiments) were evaluated under the **exact same** `2,000 m`-buffered whole-component spatial quadrant holdout (`60,988` withheld positive pixels across `4` folds) at **exact count-matched active dot budgets** in every single fold (`Fold 0: 20,902`, `Fold 1: 11,661`, `Fold 2: 4,821`, `Fold 3: 6,728` active off-visible-catalogue dots):

| Arm | Description | Pooled `HOLDOUT-DTI` | 95% Spatial-Block CI | Fold 0 | Fold 1 | Fold 2 | Fold 3 | Pooled $TP_w$ | Pooled $FP_w$ |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| `physics_tilt8` | 8-channel potential-field tilt/gradient baseline + Poisson-300m | `0.07816` | `[0.07032, 0.08657]` | `0.0888` | `0.0771` | `0.0672` | `0.0706` | `4,544.2` | `42,192.1` |
| `core19` | Shared 19-band HGB baseline + Poisson-300m | `0.13571` | `[0.12077, 0.15085]` | `0.1535` | `0.1277` | `0.1450` | `0.1066` | `7,936.3` | `40,511.8` |
| `g30s19_hist_best` | Best prior GEMSDOE30 habitat HGB + metric `edge_select` | `0.13781` | `[0.12263, 0.15383]` | `0.1558` | `0.1268` | `0.1422` | `0.1180` | `8,035.4` | `39,551.1` |
| **Exp 1 (`ms_cape_e1`)** | Stage-1 51-ch multi-physics + piedmont HGB + Poisson-300m | **`0.17436`** | **`[0.15858, 0.18988]`** | `0.1835` | `0.1727` | `0.1820` | `0.1532` | `10,246.8` | `39,643.3` |
| **Exp 2 (`ms_cape_e2`)** | Stage-1 + Stage-2 OOF 8-az axial trace/gap-bridge + Poisson-300m | **`0.17631`** | **`[0.16247, 0.19078]`** | `0.1830` | `0.1769` | `0.1902` | `0.1544` | `10,364.8` | `39,615.8` |
| **Exp 3 (`ms_cape_e3`, Primary)** | **Stage-1 + Stage-2 + prior-calibrated `300 m` submodular DTI cover** | **`0.18669`** | **`[0.17333, 0.20032]`** | **`0.1939`** | **`0.1870`** | **`0.2009`** | **`0.1636`** | **`10,997.7`** | **`39,599.9`** |

**Paired Spatial-Block Bootstrap Differences (`ms_cape_e3` minus comparator, `2,000` replicates):**

- **`ms_cape_e3 - physics_tilt8`:** **`+0.108524`** (`95% CI [+0.093327, +0.124448]`, `4/4` folds positive)
- **`ms_cape_e3 - core19`:** **`+0.050978`** (**`+37.6%` relative**, `95% CI [+0.039045, +0.063146]`, `4/4` folds positive)
- **`ms_cape_e3 - g30s19_hist_best`:** **`+0.048876`** (**`+35.5%` relative**, `95% CI [+0.037766, +0.059521]`, `4/4` folds positive)
- **`ms_cape_e3 - ms_cape_e1`:** **`+0.012328`** (`95% CI [+0.003701, +0.020866]`, `4/4` folds positive)
- **`ms_cape_e3 - ms_cape_e2`:** **`+0.010375`** (`95% CI [+0.006586, +0.014086]`, `4/4` folds positive)

Every single component of `MS-CAPE` — (1) multi-physics + piedmont Stage-1 features (`+0.0387` over `core19`), (2) Stage-2 OOF directional axial trace & gap-bridging (`+0.0020`), and (3) prior-calibrated `300 m` submodular DW-Tversky set-cover emission (`+0.0104`, adding `+633.0` weighted true-positive fault pixels at *lower* `FP_w` than Poisson-disk thinning!) — contributes a verified improvement on pooled `HOLDOUT-DTI`.

### 4.3 Three Independent Verification & Deconfounding Diagnostics

1. **Single-Feature Leakage Canaries (`204 / 204` clean):**
   All `51` Stage-1 raw & derived features were evaluated individually across all `4` buffered spatial folds (`204` tests: bidirectional raw AUC $\max(\text{AUC}, 1-\text{AUC})$ and fold-trained univariate HGB AUC). **`0` alarms** triggered; maximum observed single-feature AUC was **`0.640358 << 0.90`** (`dem_curv` / `scarp_step_coh`).
2. **Neotectonic Piedmont Deconfounding Verified (`26.06%` vs `24.03%`):**
   Whereas earlier supervised GBDT submissions across sibling repos placed `~69.5%` of their dots on steep mountain crags (top-quartile slope), **`MS-CAPE` places `26.06%` of its `44,090` dots in the top slope quartile — matching the true Quaternary fault catalogue (`24.03%`) within `2.03` percentage points!** The remaining `73.94%` track piedmont range-front toes, relay ramps, and concealed intrabasinal geophysical boundaries.
3. **Independent Off-Catalogue USGS SGMC Fault Discovery (`DIAGNOSTIC-PROXY-DTI = 0.094114`):**
   Evaluated strictly off-catalogue (`d_cat > 300 m`) against `61,664` independent USGS SGMC 1:500k mapped fault pixels (which were **never** fed as features, labels, or tuning targets), the final `MS-CAPE` GeoTIFF recovers **`5,521.12`** distance-weighted true-positive off-catalogue fault pixels (`DIAGNOSTIC-PROXY-DTI = 0.094114`).
4. **Full 116-Raster Novelty Audit (Pre-Placement Surface AND Post-Placement Dots):**
   Checked against all `116` unique aligned SHA-256 rasters across `GEMSDOE24..36`, local `GEMSDOE30` artifacts, and later sibling hero rasters (`GEMSDOE49`, `GEMSDOE63`, `GEMSDOE70`, `GEMSDOE73`, `GEMSDOE76`):
   - **Pre-placement continuous surface:** `max |Spearman| = 0.171396 <= 0.90` (**PASS**)
   - **Post-placement 44,090 unit dots:** `max |Spearman| = 0.063931 <= 0.90`, `max 3-px dot overlap = 68.5824% <= 70.0%` (**PASS**)
   - **Specifically vs `GEMSDOE32` `H33` (`0.2778`):** `Spearman = 0.0368`, `3-px overlap = 41.47%` — meaning **`58.53%` (`25,805` dots)** map genuinely new multi-physics piedmont and blind intrabasinal structures `> 300 m` outside `H33`, while `41.47%` independently converge onto primary Basin-and-Range fault zones from scratch without reading `H33` or any catalogue-proximity feature!

---

## 5. Exact Diagnosis & Dual-File Elimination of `"Predicted values must be in range [0, 1]"`

Direct inspection of `training_features.tif` and `sample_submission.tif` identifies two concrete mechanisms capable of triggering `"Predicted values must be in range [0, 1]"` (`IR-30-044` / `IR-MSCAPE-03`):

1. **In-Footprint Float32 Nodata Sentinels (`-3.4028235e+38`):**
   `training_features.tif` contains `-3.4028234663852886e+38` on **`3,061` pixels inside the valid scoring footprint** (`3,073` on band 6 `tc`). Any pipeline that passes un-imputed float32 sentinels into linear/neural layers or masks validity from band 1 (`5,165,852` finite cells vs. the template's **`5,167,373`** scored cells) strands `3,061` scored cells as `NaN` or out-of-range values. `MS-CAPE` derives the footprint exclusively from `sample_submission.tif` (`5,167,373` cells), imputes in-footprint missing sensor cells cleanly via fold-training medians, and verifies `0` `NaN`/`Inf` and exact `[0.0, 1.0]` bounds across all `5,167,373` scored cells.
2. **Outside-Footprint `NaN` vs. `0.0` Portal Convention:**
   The official problem specification ([DrivenData Page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)) specifies `null`/`nan` outside the data bounds (`7,111,787` cells), whereas the organizer reference notebook exports finite `0.0` outside without a nodata tag. To eliminate any ambiguity without altering a single scored prediction, `MS-CAPE` publishes **both** machine-verified files side by side:
   - **Spec-exact `NaN`-outside primary GeoTIFF:** `gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-nan.tif` (`5,167,373` finite `{0, 1}` cells inside, `7,111,787` `NaN` outside).
   - **Portal-safe `0.0`-outside twin GeoTIFF:** `gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-zeros.tif` (`12,279,160` finite `{0, 1}` cells everywhere, `0` `NaN` anywhere, **verified bit-identical on all `5,167,373` in-footprint cells**).

---

## 6. Official Verified Sources (Manual-Review Register)

1. **Competition Overview & Deadlines (Dec. 3, 2026, 11:59 p.m. UTC; `$300,000` prize pool):**
   <https://www.drivendata.org/competitions/306/competition-doe-gems/>
2. **Problem Description, GeoTIFF Grid (`EPSG:32611`, `100 m`), & DW-Tversky Metric (`alpha=0.2, beta=0.8, R=300 m`):**
   <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
3. **About the Geothermal Prize & Phase 1 / Phase 2 Evaluation Structure:**
   <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>
4. **Live Public Leaderboard (`#1 = 0.4413`, `#5 = 0.3553`, read 2026-10-25/26 UTC):**
   <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
5. **DOE / NLR Official Prize Rules PDF (Sept 2026 — 3/week feedback limit, 1 final submission across both rounds, AI disclosure, U.S. eligibility):**
   <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
6. **Organizer Reference Solution Notebook (Band order & GeoTIFF export contract):**
   <https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb>
7. **USGS GeoDAWN Airborne Geophysics & LiDAR Data Release (Glen et al., 2024, CC0-1.0):**
   <https://doi.org/10.5066/P93LGLVQ>
8. **INGENIOUS Great Basin Regional Dataset Compilation (GDR 1391, CC-BY-4.0):**
   <https://gdr.openei.org/submissions/1391> · <https://doi.org/10.15121/1881483> · <https://gbcge.org/current-projects/ingenious/>
9. **DOE/OSTI Structural Controls on Great Basin Geothermal Systems (Faulds et al.):**
   <https://www.osti.gov/servlets/purl/1110517> · <https://www.osti.gov/dataexplorer/biblio/dataset/1148722> · <https://www.osti.gov/servlets/purl/1724109>
10. **EPSG:32611 Coordinate Reference System (WGS 84 / UTM Zone 11N):**
    <https://epsg.io/32611>

---

## 7. Remaining Limitations & Recommended Next Steps

1. **Separate Weekly Slot Selection & Organizer Receipt Capture:**
   `MS-CAPE` passed all `12/12` automated research gates (`verdict = "promote"`), making it eligible for the separate weekly competition slot selector (`<= 3` feedback uploads/week per Official Rules §3.4). When the entrant chooses to spend a weekly slot on `gems30-MS-CAPE-submod300-44090-20261025-cff19a5ac497-zeros.tif` (or `-nan.tif`), record the exact DrivenData submission ID, timestamp, SHA-256, and returned score so it becomes the repository's first **`ORGANIZER-CONFIRMED`** benchmark.
2. **2D Multi-Scale Convolutional / U-Net Backbone Under Strict Spatial Buffering (GPU Lane):**
   `MS-CAPE` narrowed the gap between CPU tabular baselines (`0.1357`) and spatial trace geometry (`0.1867`) using an explicit two-stage 8-azimuth directional filter bank (`±800 m`). Training a lightweight GroupNorm/dilated residual U-Net directly on the 51-channel `MS-CAPE` multi-physics stack with a differentiable soft-DW-Tversky + prior-calibrated focal objective on GPU is the highest-upside path toward the `0.3553–0.4413` public-leaderboard frontier.
3. **Full-Resolution USGS 3DEP Scarp + Drainage Deflection Tile Streaming (Hypothesis `KNICK-DRAIN` & `EULER-CURV`):**
   Acquiring 10 m / 1 m 3DEP DEM + NHDPlus HR flowline tiles via the public-domain USGS National Map API in an external runner workflow to extract sub-100 m beheaded alluvial-fan channel offsets (`KNICK-DRAIN`) and 3D Euler structural-index contact worms (`EULER-CURV`) will add orthogonal structural resolving power in low-slope basins where `100 m` DEMs under-resolve `< 0.5 m` Holocene scarps.
4. **Eligibility & AI-Use Narrative Verification Before Final Entry (Dec. 3, 2026):**
   Confirm U.S. entrant eligibility under Official Rules §1.3, resolve the `5:00 p.m. ET` vs. `11:59 p.m. UTC` deadline wording discrepancy (`IR-30-008`) by submitting ≥ 24 hours early, and include the generative-AI usage disclosure (`docs/ai-disclosure-draft.md`) in the finalist narrative (`§3.2`).
