# Ranked untried geological hypotheses — 2026-10-26

## Decision and scope

No new experiment was run. No holdout result is assigned to any hypothesis below, no candidate is validated, and no competition lane or weekly slot was selected. The current externally assigned lane is still missing; the parallel registry remains incomplete. The 2026-10-25 MSDB-1v2 result is an existing run, not validation of this shortlist: its `HOLDOUT-DTI` versus `core19` is 0.170462 (evaluator `component-holdout-v3-blockstats-20261025`, 60,988 withheld positives, 95% CI [0.156227, 0.184168]), while the matched `msdb_edge − msdb_poisson` difference is +0.001135 with 95% CI [−0.002173, +0.004628] and is inconclusive. Do not treat the confidence interval crossing zero as equivalence.

The source/method screen covered the current checkout's `src/`, `scripts/`, research preregistrations, score ledger, and an immutable 2026-10-26 GitHub snapshot of the nine requested site repositories (220 published TIFF blobs; 205 unique aligned byte sequences). The exact candidate mechanisms below are not recorded as executed in this evidence set. This is **not** a claim of global uniqueness: private/unpublished branches, absent continuous surfaces, other lanes, and owner-side methods may still overlap. See the dated [public-source inventory](priority-site-public-snapshot.json) and [data-source check](data-source-check.md).

Ranks are qualitative expected lift relative to implementation and data cost. They are **planning priorities only**, not numeric DTI projections, test scores, or confidence claims.

## 1. SGMC cover-observability prior × independent structural evidence

**Expected improvement / cost:** highest expected gain per unit effort of these three; moderate implementation cost. No numeric gain is claimed.

**Mechanism.** Use USGS SGMC *map-unit polygons and age/lithology attributes* to estimate where basin fill, young surficial deposits, and low-relief cover systematically conceal surface fault evidence. Reweight a separately constructed, label-free geophysical/topographic structural score by a preregistered concealment likelihood. Do not use distance to catalogue faults as a feature. If a structural orientation prior is needed, derive it only from visible training faults in the training fold. Keep held-out whole fault segments buffered from training, mask visible catalogue pixels exactly, and build the concealment field without consulting held-out labels.

**Why this is distinct in the audited evidence.** H-34-01 is present as a proposal in `docs/hypotheses.md`, but no polygon-age/lithology observability transform is implemented in `src/` or `scripts/`. The locally available SGMC-derived raster encodes fault linework only; it is not the map-unit polygon product this mechanism requires. The current nine-site TIFF snapshot did not expose a documented matching output, but that is only artifact-level evidence, not a fleet-wide uniqueness result.

**Named non-fault mimics.** Young basin deposits, paleolake/playa sediments, alluvial-fan boundaries, and broad lithologic contacts can create the concealment classification without any fault. Required nulls: age/lithology-matched units, low-relief areas matched without structural evidence, and a concealment field permuted between comparable basins.

**Official-data availability.** The official [USGS SGMC state-map page](https://mrdata.usgs.gov/geology/state/) publishes the Nevada and California packages and map-unit attributes. Repository records show those packages were previously downloaded and SHA-256 checked through the public GitHub-runner bridge on 2026-10-03. The original polygons/archives are absent from this worktree now, so this is *source-obtainable but not locally ready*. Restore or re-fetch and hash the polygon archives before preregistration; the derived SGMC fault raster is not a substitute.

**Holdout/stop plan.** A fixed transform and map-unit grouping must be frozen before evaluation. Compare against the same structural score without concealment and against lithology-, relief-, distance-, and count-matched controls. Use whole fault segments with the standing buffer, exact visible-pixel mask, pooled DTI under the shared evaluator, 2,000 paired geographic-block bootstrap draws, and single-feature leakage canaries. Stop if any canary AUC exceeds 0.90 until explained, or if pre-/post-placement novelty crosses Spearman >0.90 or >70% of candidate dots lie within 3 px of a registered raster. No test has run.

## 2. GeoDAWN K–Th alteration residual conditioned on map unit and along-strike persistence

**Expected improvement / cost:** medium expected lift; low model-compute cost but moderate source/measurement-quality and lithology-control cost. No numeric gain is claimed.

**Mechanism.** Test a fold-local log-ratio anomaly (for example, robust `ln(K/eTh)` or the inverse `ln(eTh/K)`, frozen in advance) relative to the same SGMC map-unit population, then require the residual step to persist along a candidate geophysical lineament for a fixed 600–1,000 m scale. Use only visible training faults to define any fault-alignment summary; do not use catalogue distance, held-out labels, or a line derived from the target mask. The physical hypothesis is potassium mobility/depletion during fluid alteration along a permeable fault zone; thorium is treated as a comparatively immobile reference.

**Prior-work distinction and overlap.** Radiometric channels have appeared as ordinary inputs in broader G30-S20/GEMSDOE31/H-LSM work, and MSDB-1v2 uses the competition radiometric-total-count band. Therefore the *channels themselves are not novel*. The untried unit-conditioned log-ratio residual plus fixed along-strike persistence and lithology-matched null is not implemented in the reviewed code/tests. The prior `RadTC-Fan` proposal's `tc`/`det_elev` concordance is already included in MSDB-1v2; this candidate expressly does **not** retest that feature. A separate `H-LSM-3` K/eTh halo proposal is also recorded as not run. The distinction is method-level within audited evidence, not a global novelty certification.

**Named non-fault mimics.** Lithologic contacts, soil/weathering differences, flight-line seams, and survey/block boundaries can generate radiometric ratio steps. The null must compare within the same SGMC map unit and flight block, include a line-orientation rotation control, and report which fold-local features carry the effect.

**Official-data availability.** USGS's public-domain [GeoDAWN release (DOI 10.5066/P93LGLVQ)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) includes radiometric grids. Two exact-pinned owner-derived 4-band `uint8` mirrors (`K/Th/U/TC` and `Th/K`, `U/K`, `U/Th`, `TMI_up150`) were restored and hash-checked from GitHub during this review; see `geodawn-layer-restoration.json`. They are quantised 1st–99th percentile products, not the original USGS floating-point measurements. Obtain the raw official grids or the owner's quantisation metadata via the approved bridge before interpreting log ratios. Thus the source is obtainable, but a statistically defensible ratio test is **not yet data-ready**.

**Holdout/stop plan.** Freeze ratios, lithology grouping, persistence scale, and all controls before scoring. Use whole-segment buffered folds; all radiometric scaling and unit residuals must be fit on visible training blocks only. Compare against the same model without ratios and a within-lithology line-rotation null. Apply the shared pooled-DTI evaluator, paired 95% CI, AUC leakage canaries, and the standing pre-/post-placement novelty stop. No test has run.

## 3. USGS drainage χ disequilibrium and strike-aligned channel steepness (`ksn`)

**Expected improvement / cost:** low-to-medium expected lift and highest implementation cost; ranked third because new independent geomorphology is attractive but data processing and scale mismatch are substantial. No numeric gain is claimed.

**Mechanism.** Derive a fixed-concavity χ transform and normalized channel steepness from conditioned 3DEP elevation and official NHD flowlines. Measure basin-to-basin χ disequilibrium and strike-aligned `ksn` breaks across an independently extracted geophysical lineament. This is a basin-integrated fluvial-deformation hypothesis, not a channel-density raster or a catalogue-gap-closing rule.

**Prior-work distinction and overlap.** H-31-03 previously proposed qualitative channel offsets, beheaded tributaries, and knickpoint chains but was not run. The quantitative χ/`ksn` construction is not implemented in the reviewed code or feature stack. It is distinct from topographic gap-closure TIFFs, but not a claim that no other public or private site has considered drainage.

**Named non-fault mimics.** Lithologic resistance contrasts, climate/precipitation gradients, dams and channel edits, ordinary erosional knickpoints, and drainage-network extraction errors. Controls must match drainage area/density, lithology, and basin size; hold out entire basins so a basin cannot enter both sides.

**Official-data availability.** The official [USGS TNM products API](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=National%20Hydrography%20Dataset%20(NHD)%20Best%20Resolution&bbox=-119,38.5,-118.5,39) returned 35 NHD records for a test bounding box in an earlier source check, with public product links; USGS 3DEP elevation products are public domain. This confirms a source endpoint, **not full-footprint coverage or a viable complete download**. No complete NHD/3DEP set is present here. Do not call this candidate runnable until the full study area is covered, products are downloaded through an approved route, checksummed, aligned, and attributed.

**Holdout/stop plan.** Freeze the DEM conditioning, channel extraction, concavity index, and thresholds before looking at blocked labels. Compare χ/`ksn` against slope-only and drainage-density/lithology-matched nulls on whole-basin holdout blocks. Use whole-segment buffering, exact visible mask, pooled DTI, paired 95% CI, leakage canaries, and the standing novelty rules. No test has run.

## Explicit exclusions after the artifact/code audit

- **`RadTC-Fan` as originally described:** its core `tc`/`det_elev` concordance is already included in MSDB-1v2; a repeat would not be untried.
- **`MT-HF-Saddle`:** overlap exists with the GEMSDOE24 `con-claycap-strain-saddle` artifact and with prior conductivity/heat-flow work. Not called new.
- **`WL-Strain`:** overlaps the GEMSDOE27 H28-3 strain/conductivity negative artifact. Not called new.
- **Generic magnetic-depth/Euler or LiDAR-scarp fusion:** Euler/PINN artifacts and the G30-LSM experiment already cover those families; G30-LSM also reached a mandatory duplicate stop.
- **IHFC heat-flow anomaly alone:** the 2024 IHFC release advertises downloadable xlsx/txt data, but a footprint count was not checked and the heat-flow/MT family overlaps existing work. Not in the untried shortlist.

## Execution gate

Before any one of these is run: supply the externally assigned method lane; reconcile the complete parallel registry (including original surfaces); reserve a clean whole-segment buffered holdout; use the shared feature cache/evaluator/writer; freeze one method and its controls; and check novelty both before and after placement. The active experiment budget and slot status are not reset by this review. The candidate shortlist is not authorization to execute or upload.
