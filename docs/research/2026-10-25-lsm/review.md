# G30-LSM — scientific review and final decision (2026-10-25)

**Decision: DO NOT SUBMIT — duplicate-stop at the dot stage. No TIFF was published.**

- **Machine receipt:** [`readiness.json`](readiness.json). Recompute it with `python scripts/verify_current_run.py`; exit 0 means verified, and `--require-promote` exits 2.
- **Run card:** [`run-card.json`](run-card.json).
- **Logged identity:** `gems30-LSM42-38000-20261025-eb81d4c94efc`.

**Labels used here:**
- **HOLDOUT-DTI:** values from the repository's catalogue-recovery proxies. They are not organizer scores.
- **Owner-reported:** unverified leaderboard claims.
- **Projection:** derived quantities.

## 1. What was asked and what was delivered

| Requirement | Outcome |
|---|---|
| Review the top submissions of GEMSDOE24/25/27/28/30/31/32/33/36 | Done. The byte lineage was re-verified: D2.8 ⊂ h19-5 → r1 = D2.8 ∧ d>1 px (= GEMSDOE31) → **H33 = r1 ∧ d>2 px** → GEMSDOE36 PINN = H33 + 1,200 dots |
| PhD-level explanation of H33's 0.2778 | [`why-h33-scored-0.2778.md`](why-h33-scored-0.2778.md). Lattice-calibrated hidden-truth density, implied coverage, and marginal hit rates of every nested change |
| 3–5 ranked, untried hypotheses before implementing | [`preregistration.md`](preregistration.md) §1. Five hypotheses ranked, three tested (E1–E3) |
| Validate the top hypothesis on the spatially blocked holdout | E1 **passed** (§3) |
| Unique TIFF, obviously OK or not OK, no human inspector | Automated decision: **NOT OK**. The candidate is a dot-stage duplicate under the owner's 70 %/3 px rule (§4). No file was published, per protocol |
| ≤3 experiments / ≤2 h | 3 experiments, 457 s of experiment compute |

## 2. Evidence that shaped the lane

These are projections from owner-reported scores; see [`leaderboard-calibration.json`](leaderboard-calibration.json).
* **Hidden-truth density.** The exact 5-px uniform lattice (0.0904) implies ρ ≈ 0.244 % of scored pixels.
* **The D-family shares one signal.** D2.8, r1, H33 and PINN all imply ≈ 40.5 % coverage. H33 earns 0.134 hits per dot, which is 5.8× uniform-random (0.023).
* **Near-catalogue dots are unproductive.** The ≤2 px band has an implied hit rate of 0.002, gap closure ≈ 0, and PINN additions 0.013.
* **Frame validity.** The SGMC-new frame is **not** a leaderboard proxy: Spearman −0.18 across 19 owner-scored rasters, and the lattice tops it ([`frame-validity.json`](frame-validity.json)).

## 3. Experiments (frozen before running)

| # | Question | Result (HOLDOUT-DTI, 95 % paired spatial-block CI) | Verdict |
|---|---|---|---|
| E1 | Does LiDAR-morphology + geophysics fusion (`lsm42`) beat the v3 spatially blocked best (`core19`)? Evaluator `component-holdout-v3-blockstats-20261025`, 60,988 withheld positives, TDX-1-identical folds, budget and emission | core19 **0.1398** [0.1242, 0.1559] (reproduces the recorded TDX-1 value exactly); geo25 0.1487 [0.1341, 0.1642]; **lsm42 0.1572** [0.1415, 0.1736]; **lsm42 − core19 = +0.0174 [+0.0066, +0.0279]**; production emission +0.0192 [+0.0085, +0.0299]; lsm42 − geo25 = +0.0085 [−0.0016, +0.0188] (LiDAR share not significant); lsm42 > core19 in 4/4 folds | **Gate passed** |
| E2 | Independent SGMC-new frame (61,664 truth px), production models | lsm42 0.0725 vs core19 0.0679 (Δ +0.0046 [−0.0011, +0.0103]); vs H33 0.0940: **Δ −0.0215 [−0.0354, −0.0057]**; vs D2.8: Δ −0.0203 [−0.0340, −0.0048] | Confirmation passed (point estimate). The frame is not a leaderboard proxy |
| E3 | Does crest-line placement beat plain placement on the same lsm42 belief? | ridge − plain = +0.0016 [−0.0029, +0.0055] (primary), −0.0003 (production); on the SGMC frame +0.0087 [+0.0054, +0.0122] (reported, not gated) | **Gate failed**; plain kept |

**Leakage canaries:** 168 checks (42 inputs × 4 folds). The maximum single-feature AUC is 0.665, and no alarm fired. The six most predictive single inputs are LiDAR morphology layers.

**Determinism:** a second E1 execution, run to persist block statistics, reproduced every value exactly. The verifier recomputes the bootstrap from those statistics.

## 4. Why the candidate stopped (the important negative result)

**Surface stage:** max rank correlation 0.218 against 131 references (pass).

**Dot stage:** more than 70 % of the 38,000 final dots fall within 3 px of 5 distinct sparse registry rasters (9 files):

| Reference | Dots | Within 3 px | Chance for random eligible dots |
|---|---:|---:|---:|
| G30-S19 habitat + EDGE | 60,000 | 80.2 % | 13.8 % |
| GEMSDOE28 (EDGE-family) | 38,545 | 80.1 % | 17.6 % |
| GEMSDOE27 (two rasters) | 59,243 / 59,075 | 79.8 % / 79.6 % | 16.4 % |
| GEMSDOE10 h28 dotted-ridge | 69,281 | 74.9 % | — |
| *(dense, non-discriminating)* GEMSDOE13 5-px lattice | 206,895 | 99.1 % | ≈ 100 % |

**Mechanism.** The model has **no** distance-to-fault input, yet 70 % of its dots lie 200 m–1 km from mapped faults and 6 % lie beyond 3 km. A habitat model trained on catalogue pixels learns that catalogue-like pixels sit beside catalogue faults, because geophysical and topographic fields are spatially smooth. Proximity-based lanes placed their dots in the same zone.

The leaderboard differentials (§2) indicate this zone is unproductive, so the stop very likely also saved a weekly slot.

**Dense references.** The lattice reference flags *every* possible candidate. A 70 %/3 px rule against a raster whose 3 px dilation covers ≥ 70 % of the footprint cannot discriminate (IR-30-086). The stop does **not** depend on it.

## 5. What a future session should do (ordered)

1. **Uniqueness first.** Before any experiment, place full-catalogue production dots and run the dot-stage novelty check. It takes about 5 minutes.
2. **Far-field allocation.** Allocate the dot budget across catalogue-distance strata to match the h-family's profile (≈ 30 % within 1 km, ≈ 30 % beyond 3 km) or a lattice-calibrated hit-rate profile. Rank *within* strata by the holdout-validated lsm42 belief. This targets where the leaderboard says hidden truth is, and should also clear the 70 % rule.
3. **Validate the stratified emission on v3 against core19.** Then run the SGMC equal-budget comparison against H33 as a diagnostic.
4. **Pluvial shoreline rejection (H-LSM-4).** Fetch the 3DEP 1/3″ DEM via a GitHub Actions workflow, because this sandbox can reach only GitHub and PyPI.

## 6. Limitations

* **Owner scores.** Every leaderboard number is owner-reported and unverified. A misattributed lattice score would rescale ρ, but not the sign of the differentials.
* **What HOLDOUT-DTI measures.** It is a catalogue-recovery proxy and cannot measure the expert-new-fault hit rate. No offline frame here is a validated leaderboard proxy.
* **Novelty inventory.** The inventory is observed, not global: 105 hash-pinned priority-site rasters, the addendum, 11 owner-scored rasters and repository downloads. Rasters from GEMSDOE37–92 were not downloaded.
* **Site and score access.** The portal, rules PDF and live scores were read through a fetch tool, not authenticated. No slot was selected or used.

## 7. Sources verified this session (fetched 2026-10-25)

* **Problem page, metric and format:** <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
* **Live leaderboard:** #1 0.4413 (xiaofanhu), #50 0.2818. <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>.
* **Staff, masking:** the mask is pixel-exact and identical to the training labels; near-known predictions are fully penalised; new-fault truth can lie within 300 m of known traces. [forum t/11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516).
* **Staff, aggregation:** scores are pooled over all public pixels as one Tversky index. Chunking is undisclosed. Final re-evaluation covers the entire GeoDAWN area. [forum t/11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550).
* **Staff, test faults:** sources, types and coverage are undisclosed. Phase 2 truth is updated by expert review of all Phase 1 submissions. [forum t/11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527).
* **Official external source, verified obtainable:** USGS TNM Access returned **32** 3DEP 1 m DEM GeoTIFF products for bbox −119, 38.5, −118.5, 39 (project `NV_WestCentral_EarthMRI_2020_D20`). Each has a direct `prd-tnm.s3.amazonaws.com` download URL, and the record states "All 3DEP products are public domain". [query](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119,38.5,-118.5,39&max=2).

**Reproducibility note.** `scripts/lane_lsm.py` gained stages during the session (E3, final-stage guards). The stage that produced each committed result is unchanged in the committed file, so each `script_sha256` field records the file state at execution time:
* E1 was re-executed with the committed `stage_e1` and reproduced the first execution exactly;
* `stage_e2` and `stage_e3` are byte-identical to the code that ran.

**Not exercised:** the promote-path file checks in `verify_lsm_run.py` ran on no real artifact this session, because nothing was promoted.
