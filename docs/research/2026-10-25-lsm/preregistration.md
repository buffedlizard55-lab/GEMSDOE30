# G30-LSM — ranked hypotheses and frozen preregistration

**Frozen:** 2026-10-25 (UTC), before any LSM model was fitted or scored. The lane script records this file's
SHA-256 in `started.json`. The only results available when this was written were the label-free
leaderboard calibration (`leaderboard-calibration.json`) and the distance profiles of existing rasters.
**Lane:** self-assigned (the owner prompt says "the single method paragraph below" but has no paragraph;
recorded as IR-30-078). **Budget:** ≤3 experiments and ≤2 h of experiment time; no slot selection.

## 0. Evidence that shaped the lane (label-free; owner scores are UNVERIFIED)

| Evidence | What it implies | Source |
|---|---|---|
| Exact 5-px uniform lattice `r13-lattice-s5` scored 0.0904 (owner-reported) | Hidden new-fault density is ρ ≈ 0.244 % of scored pixels (±12 % for ±10 % in the line-coverage constant): about 21 % of the catalogue density | `leaderboard-calibration.json` |
| d2.8, r1-solo, H33, prethin, PINN all have implied coverage 0.402–0.406 | The D-family variants find the same truth and differ only in wasted dots | same |
| 6,436 dots within ≤2 px of the catalogue: implied hit rate 0.002 | The ≤200 m band is effectively barren, even though staff say corrections can exist there | same; [forum t/11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) |
| Gap-closure (+1,259 dots, 3–10 px) hit rate ≈ 0; PINN additions (+1,200 dots, 3–30 px) 0.013; uniform random 0.023 | Near-catalogue *geometric* additions earn no more than random dots on the leaderboard | same |
| G30-S19's "promoted" raster puts 76 % of its dots within 1 km of the catalogue (only 2.4 % beyond 3 km); its 0.2230 came from the interleaved catalogue proxy | The interleaved proxy over-rewards proximity, so it is not a valid promotion frame for the leaderboard (IR-30-079) | `analysis-distance-profiles` in `results.json` |

**Design consequence:** this lane uses **no catalogue-proximity input**. It is validated on the repository's
spatially blocked v3 protocol, where proximity cannot help. Its only leaderboard-informed choices are
(a) dropping the barren ≤2 px band and (b) a fixed 38,000-dot operating point (H33 has 37,654). Both are
emission rules, not inputs to the belief model.

## 1. Ranked hypotheses (untried in this repository as specified)

Ranked by expected DTI gain ÷ implementation cost.

### H-LSM-1 (rank 1) — LiDAR scarp morphology fused with geophysical context
* **Layers:** all 19 GeoDAWN bands, plus 6 label-free geophysical derivatives, plus the 12-channel 100 m descriptor
  stack derived from USGS 3DEP 1 m DEMs (706/716 tiles; owner mirror pinned in `mirror-pins-extra.json`).
  The official source is the public-domain USGS 3DEP 1 m DEM, obtainable through the
  [TNM Access API](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119,38.5,-118.5,39).
* **Signatures:**
  * the 10 m-minus-50 m slope step;
  * the crest–toe curvature dipole √(LoG⁻·LoG⁺);
  * the facing step √(step·max(up, down));
  * a scarp-versus-channel ratio max(up, down)/(cross + 0.01);
  * 5×5 axial strike persistence |Σw·e^{2iθ}|/Σw;
  * 3×3 neighbourhood support.
* **Why it catches faults missing from the catalogue:** compilations at 1:24k–1:250k miss short, low scarps (≲2–3 m, ≲1 km). 1 m LiDAR resolves them. Expert re-mappers routinely use LiDAR hillshade, although the organizer does not disclose the sources ([forum t/11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527)). The geophysical context should down-weight the non-fault mimics listed below.
* **Named non-fault mimics:**
  * Lake Lahontan paleo-shorelines (contour-parallel wave-cut steps);
  * fluvial terrace risers and channel banks;
  * roads, canals and mines.
* **How it differs from earlier work:**
  * H-31-02r used one fixed LiDAR transform as a standalone ranker.
  * TDX-1, core19 and G30-S19 used no LiDAR.
  * G30-S19 multiplied a habitat score by exp(−d/1.5 km).
  * No repository model has fused 2 m-resolved scarp morphology with geophysics while having **no** catalogue-distance input.

### H-LSM-2 (rank 2) — geophysical edge derivatives alone (`geo25`, ablation arm)
* Six transforms: gradient magnitudes of RTP, isostatic gravity, detrended elevation and depth-to-conductive-base; RTP structure-tensor coherence; and |∇²| of detrended elevation.
* These test whether any H-LSM-1 gain comes from LiDAR or from edge transforms that the raw bands lack.

### H-LSM-3 (rank 3, not run) — radiometric K/eTh alteration halos
* **Layer:** GeoDAWN radiometrics (`geodawn_rad_u8.tif`).
* **Mechanism:** hydrothermal fluid flow along permeable faults depletes K relative to eTh.
* **Prior evidence:** GEMSDOE46's scarp+radiometric fusion was reported at 0.1589.
* **Why not run:** lower expected gain.

### H-LSM-4 (rank 4, not run; data obtainable) — paleo-shoreline rejection
* **Method:** reject LiDAR steps that follow a constant absolute elevation near the Sehoo highstand (~1,330 m). This needs absolute elevation.
* **Data:** USGS 3DEP 1/3″ DEM via TNM Access, public domain. It would have to be fetched through GitHub Actions, because this sandbox can reach only GitHub and PyPI.

### H-LSM-5 (rank 5, not run) — side-of-fault (hanging-wall) asymmetry
* **Method:** relative detrended elevation with respect to the nearest mapped fault.
* **Why not run:** this is a catalogue-relative feature, and the leaderboard evidence in §0 argues against proximity-driven placement.

## 2. Frozen protocol

**E1 — spatially blocked catalogue holdout (gate)**
* **Evaluator and protocol:** shared `gemsdoe30.holdout`, evaluator `component-holdout-v3-blockstats-20261025`, protocol `buffered-quadrant-whole-components-v1-20261025`, with `spatial_segment_folds(labels, valid, buffer_px=17)`. These are TDX-1's folds: 60,988 withheld positives in total.
* **Arms:** `core19` (19 raw bands; current v3 holdout best, 0.139821 [0.124178, 0.155905]), `geo25` and `lsm42`.
* **Model and sampling:** HistGradientBoosting (120 iterations, learning rate 0.1, 31 leaves, no early stopping, seed 3070+fold). Training samples come from the shared sampler (6 negatives per positive, seed 3070+fold) on `train_mask` with the fold's visible labels.
* **Primary emission:** TDX-1-exact — Poisson-disk r = 3.0 px on `active`, count = round(44,090·|active|/|valid|).
* **Secondary emission:** production rule — mask = `active` ∩ (distance to visible catalogue > 2 px), count = round(38,000·|active|/|valid|), r = 3.0.
* **Statistics:** pooled DTI per arm; paired geographic-block bootstrap with 128 px blocks, 2,000 replicates, seed 3071.
* **Gate (all required for "promote"):**
  1. `lsm42 − core19` > 0, with paired 95 % CI lower bound > 0, under the primary emission.
  2. `lsm42 ≥ core19` (point estimate) under the secondary emission.
  3. No leakage canary above 0.90, for every input in every fold. Two AUCs are checked: the raw AUC in either direction, and the AUC of a training-only univariate HGB.
* **Attribution (reported, not gated):** `lsm42 − geo25`.

**E2 — independent-inventory frame (confirmation and frame validity)**
* **Truth:** USGS SGMC fault pixels more than 3 px from the catalogue (61,664 px; `data/external/derived_sgmc_faults_100m_u8.tif`). Catalogue pixels are masked exactly; FP accrues everywhere else.
* **Models:** full-catalogue `core19` and `lsm42` (seed 3070), with production emission (38,000 dots, catalogue distance > 2 px, r = 3.0).
* **Frame validity:** the same frame scores all 11 owner-scored isolated-dot rasters. Spearman(owner score, frame DTI) is reported as a diagnostic.
* **Confirmation requirement:** `lsm42 ≥ core19` (point estimate) in this frame.

**Production (only if E1 passes)**
* **Model:** the full-catalogue `lsm42` model.
* **Novelty checks:**
  * surface stage: Spearman > 0.90 against any registry raster ⇒ duplicate-stop;
  * dot stage: Spearman > 0.90, or > 70 % of dots within 3 px of any raster ⇒ duplicate-stop.
  * The comparison set is the 105 hash-pinned priority-site rasters, the parallel addendum, the 11 owner-scored rasters and every `docs/downloads` TIFF.
* **Emission:** 38,000 dots, Poisson r = 3.0, catalogue distance > 2 px, values {0, 1}.
* **Output files:**
  * the primary file is finite everywhere, with zeros outside the footprint;
  * an alternate file has NaN outside.
  * Both pass the shared validator.
* **Format check:** the zeros file is additionally checked for "every value in [0, 1] across the whole array". This directly addresses the portal error "Predicted values must be in range [0, 1]".

**Stop rules**
* A failed E1 gate ⇒ verdict negative. The TIFF is still built as a research artifact, labelled DO NOT SUBMIT.
* No retuning of features, thresholds, budgets or seeds after E1 has been seen.
* A duplicate at either stage ⇒ stop.

**Labels**
* HOLDOUT-DTI applies only to E1/E2 outputs.
* Leaderboard numbers are OWNER-REPORTED UNVERIFIED unless an organizer receipt exists.
* Calibration outputs are PROJECTIONS.
