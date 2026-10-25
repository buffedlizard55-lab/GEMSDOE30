# 2026-10-25 review: GEMSDOE32 H33-2-B2, the nine-site record, and the next defensible experiment

**Status:** one negative, component holdout screen completed; no submission TIFF generated, no competition slot used, no candidate promoted. This is intentional: the pre-registration screen did not beat its count- and distance-matched control, the old benchmark is not comparable on this protocol, and the full registry-raster duplicate gate could not be run.

## Executive decision

The user-reported `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is **not organizer-confirmed in the inspected evidence**. The linked GEMSDOE32 build record labels its output `UNSCORED`, reports a model-projected `0.2747`, and explicitly says no organizer score exists for the artifact. The score may have arrived later, but the supplied number does not include a DrivenData submission receipt or an authenticated score-to-file crosswalk. The project's older D2.8 `0.2600` pairing has the same problem: owner records conflict with the claimed attribution. Do not state either number as a verified file score.

The published H33-2-B2 mechanism is a **deletion-only prediction operation**, not a new geothermal/fault detector: remove dots within 200 m of the catalogue from a prior emission, leaving 37,654 dots. The physical/metric rationale is plausible: catalogue pixels are excluded from scoring, so deleting predictions that only spend false-positive mass can improve an emission. It can also delete valid uncatalogued geometry close to mapped faults. The owner-described holdout improvement and projected live score are not proof of organizer performance or causation.

A fresh unique GeoTIFF is **not approved for download/submission**. The tested candidate below performed worse than a matched random control on the component holdout; it did not beat a comparable best, the full cross-repository raster duplicate test is incomplete, and the exact current public leader is not refreshed here. Fabricating a TIFF by changing or relabelling an older raster would violate the stated uniqueness rule.

## Cumulative review passes

1. **Evidence and attribution pass:** reviewed the nine requested sibling repositories and their accessible public records; separated user/owner claims, local projections, and official receipts; recorded supplied per-site values as user-reported in `docs/score-ledger.csv`. H33-2-B2 remains unverified because its inspected build says `UNSCORED`; binary sibling TIFF retrieval is blocked by API rate limits.
2. **Scientific/protocol pass:** implemented one reduced H-34-01 proxy screen with the cached stack, whole-component split, buffer, exact visible-label mask, and shared `masked_dti`; parity-tested the optimized bootstrap path. The result is negative versus the matched control. The requested compound concealment × class-specific cross-anomaly × strike-continuity detector was not implemented; the screen must not be represented as that detector.
3. **Release/reproducibility pass:** removed the stale site download links and submit-ready prose; refreshed `README.md`, `executive-summary.html`, the hypothesis page, generated `docs/status.json`, and added current source/run-card records. The current Python suite passes (121 tests plus 11 subtests), JSON/score-ledger checks pass, local navigation links resolve, and `git diff --check` is clean. The registry duplicate audit remains explicitly **not passed**, so no file or slot is released.

## Evidence and sources

| Statement | Evidence class | Review link / local reproducible record |
|---|---|---|
| H33-2-B2 source name, 37,654-dot construction, 4-quadrant owner model result, projected 0.2747, `UNSCORED` status, and explicit absence of organizer score | Owner-published, secondary | [GEMSDOE32 build record](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/registry/submission_build.json); [GEMSDOE32 README](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/README.md); [GEMSDOE32 H33 audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/main/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json). These records do not authenticate a DrivenData score. |
| Historical D2.8 bytes and score-attribution conflict | Local byte measurements + owner/user claim | [`why-d28-scored-026.md`](why-d28-scored-026.md); [GEMSDOE25 artifact page](https://github.com/buffedlizard55-lab/GEMSDOE25/blob/main/README.md). The exact `0.2600` claim is not a receipt. |
| Current top of the official leaderboard | **Not rechecked** | The user supplied both `0.3195` and `0.4413`; the local official snapshot is dated 2026-10-03. No current score is asserted. [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The repo avoids automated leaderboard monitoring under the recorded Terms-of-Use review. |
| Metric format and science context | Official source as documented in prior source review | [Problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/); [official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf); [`docs/sources.md`](../sources.md). |
| Inputs used by this screen | SHA-pinned owner mirror, **not** organizer-authenticated | `data/processed/manifest.json`; fingerprints recorded in [`candidate-screens/concealment-screen.json`](candidate-screens/concealment-screen.json). |

### Nine-project prior-art review (bounded, not a claim about every private experiment)

The score/name list in the user prompt is owner/user-reported, not a set of organizer receipts. The reviewed public repositories show a progression from H19-5/D1.5/D2.8 sparse emissions, to topological gap closure, catalogue-flank deletion, Bayesian/ridge/topological variants, H33-2-B2 deletion, analog step-over/relay features, and the GEMSDOE36 geothermometry/physics-constrained family. The H33-2-B2 registry itself says the 0.2747 value is a model projection and its built file was unscored at that recorded time. The local source and score ledgers retain the known conflicts rather than assigning one score to one TIFF by name.

The session inspected the relevant repository records at [GEMSDOE24](https://github.com/buffedlizard55-lab/GEMSDOE24), [GEMSDOE25](https://github.com/buffedlizard55-lab/GEMSDOE25), [GEMSDOE27](https://github.com/buffedlizard55-lab/GEMSDOE27), [GEMSDOE28](https://github.com/buffedlizard55-lab/GEMSDOE28), [GEMSDOE30](https://github.com/buffedlizard55-lab/GEMSDOE30), [GEMSDOE31](https://github.com/buffedlizard55-lab/GEMSDOE31), [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32), [GEMSDOE33](https://github.com/buffedlizard55-lab/GEMSDOE33), and [GEMSDOE36](https://github.com/buffedlizard55-lab/GEMSDOE36). The first-pass metadata/path inspection succeeded; binary TIFF retrieval for the cross-site similarity audit then hit the GitHub API rate limit. Consequently, the lane/raster similarity check against every site was **not passed**, not assumed.

| Site | User-listed submission and score | Evidence status in this review |
|---|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5` — **USER-REPORTED 0.2477** | User-supplied value; not an organizer receipt. |
| GEMSDOE25 | `dotted-h19-5-d2-8` — **USER-REPORTED 0.2600** | Owner page/build materials call the mirrored file unscored/not slot-approved; no score-to-file receipt. |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5` — **USER-REPORTED 0.2449** | User-supplied value; exact submission receipt/hash association not inspected. |
| GEMSDOE28 | `h36-1-rung30-blind-r1` — **USER-REPORTED 0.2710** | User-supplied value; public materials describe local/unscored experiments; no organizer receipt inspected. |
| GEMSDOE30 | `d28-poisson300m-offcat` — **USER-REPORTED 0.2600** | Historical local bytes are audited in this checkout, but the score attribution is unresolved; not a new method. |
| GEMSDOE31 | `h27-4-solo-d28` — **USER-REPORTED 0.2708** | The user's number is unsupported by the inspected public record; the site materials say no score for that artifact. |
| GEMSDOE32 | `h33-h33-2-b2` — **USER-REPORTED 0.2778** | Its inspected build record labels the file `UNSCORED`; reports 0.2747 as a model projection, not a score. |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30` — **USER-REPORTED 0.2632** | User-supplied value; exact organizer receipt/hash association not inspected. |
| GEMSDOE36 | `anderson-geothermal-pinn` — **USER-REPORTED 0.2750** | Public build record contains local holdout/projection diagnostics; user-listed number is not authenticated here as an organizer score. |

The table intentionally labels every number as user-reported. It is a prior-art index, not a verified leaderboard or file attribution ledger. The official leaderboard is not automatically queried; the conflicting user claims `0.3195` and `0.4413` are both unresolved as current values.

## Why H33-2-B2 could improve a submission (conditional mechanism, not a causal score explanation)

The public metric rewards triangular-kernel proximity to target faults within 300 m and penalizes weighted false-positive mass; it masks pixels already represented by the USGS/INGENIOUS catalogue. Under those conditions, a catalogue-flank pruning rule can be useful if the removed predictions have low marginal target-truth credit and nonzero false-positive cost. The same edit is harmful where an unmapped extension, parallel splay, or fault tip lies near a known trace. A single owner-reported leaderboard value cannot distinguish these mechanisms from model selection, score noise, upload identity, or hidden-label composition.

**Conclusion:** H33-2-B2 is best understood as an emission-domain calibration/ablation whose reported score is unverified, not as evidence that its geological hypothesis discovered new geothermal vents. The available build receipt does not explain a `0.2778` result; its listed projected value is a different number and is explicitly labelled a model estimate.

## Ranked untried hypotheses

“Untried” below means no matching implemented feature/experiment was found in the inspected GEMSDOE30 source and the reviewed nine-project public records. This is a bounded repository audit, not a claim of global scientific novelty. Expected benefit is deliberately ordinal: no numeric DTI forecast is supported.

| Rank | Hypothesis / specific layers | Physical signature | Why it could find faults missing from USGS/INGENIOUS | Difference from implemented/reviewed methods | Expected DTI upside / implementation cost | Free official source and availability check |
|---|---|---|---|---|---|---|
| **1 (external-data gated)** | **Groundwater hydrothermal chemistry residuals:** USGS NWIS groundwater/spring water temperature, specific conductance, and available dissolved-solute observations; fit site/date/depth-aware local background residuals, then test spatially coherent anomalies near independent geophysical boundaries. | Persistent warm/high-conductance or solute-anomalous groundwater after seasonal and basin-background correction; align support with local fault-permeability geometry rather than using well density. | Upflow and fluid-rock interaction can occur above blind/permeable structures with no mapped surface trace; water-quality sampling is an observation process distinct from fault cataloguing. | Distinct from GDR vent/well temperature point priors and the GEMSDOE36 geothermal-temperature PINN: the proposed test is a **quality- and season-controlled groundwater chemistry residual**, not a temperature-only point cloud or catalogue-flank edit. | **Potentially moderate/high but wholly unmeasured**; **high** linkage/QC cost and likely sparse, biased sampling. | [USGS Water Services](https://waterservices.usgs.gov/) documents machine-readable REST water data; its own notice says the legacy service is scheduled to retire in 2027. Official documentation lists temperature and specific conductance among water-quality observations ([service overview](https://waterservices.usgs.gov/about/)). Service existence is checked; Great Basin coverage, groundwater-site count, parameter completeness, download success, and access terms for the exact query were **not checked**. Therefore this is not yet viable; first retrieve and count sites inside the footprint. |
| **2 (data-transfer gated)** | **3-D thermal-model residual vs basement architecture:** USGS Great Basin 3-D temperature model v1.1, competition `depth_to_base_surf`, `cond_surf`, and gravity/magnetic gradients; target a spatially coherent residual/gradient departure rather than absolute temperature. | A thermal gradient or modeled-temperature residual localized over a basement step/conductive corridor, with scale-aware spatial coherence. | Deep advective heat flow can reveal blind structures under cover; a model residual paired with structural geometry can be more discriminating than spring locations alone. | Existing work reviewed here uses shallow wells, vents, point geothermometry, heat-flow/Euler corroboration, and generic geophysical features; this candidate uses the separate USGS regional 3-D thermal model and tests its **residual**, not the absolute thermal field. | **Moderate, uncertain**; **medium** processing and model-grid registration cost. | USGS catalog record and DOI are in [`docs/sources.md`](../sources.md): [USGS data record](https://data.usgs.gov/datacatalog/data/USGS:65b3fe07d34e36a390458ce9), [DOI 10.5066/P149FR54](https://doi.org/10.5066/P149FR54). Catalog metadata was reviewed previously; the grid bytes have not been downloaded or verified in this checkout. It is not viable until the exact grids are obtained, checksummed, and aligned. |
| **3 (access/coverage gated)** | **Transient-vs-secular GNSS strain residuals:** station daily east/north/up time series, after seasonal/common-mode and earthquake-step removal; compare residual transient strain orientation with the static competition geodetic strain bands and basement edges. | Spatially coherent transient displacement gradients or strain-rate changes along a structure, not static geodetic magnitude alone. | Blind faults may creep or accommodate transient deformation without a mapped scarp; the time-series programme is independent of the surface-fault inventory. | The competition stack and GEMSDOE36 methods use static strain fields / orientation constraints; this hypothesis specifically isolates **time-varying residuals**, with seasonal, hydrologic, and earthquake transients treated as confounders. | **Potentially moderate, high uncertainty**; **high** cost (station QC, reference frame, interpolation, time-series model, spatial coverage). | [EarthScope GNSS data](https://www.earthscope.org/data/) and [daily GNSS position time-series documentation](https://www.unavco.org/data/web-services/documentation/gps-position-documentation.html). EarthScope indicates access is transitioning to authenticated identity management; this agent did not obtain station data or test Great Basin coverage. Not viable until access and station completeness are confirmed. |


**Excluded as prior art, not a new candidate:** USGS NHD/3DEP channel-profile χ/ksn was not ranked because H-31-03 already appears in this repository’s historical register and its source coverage is not verified for the full region.

### Executable candidate screen (H-34-01 basin concealment proxy)

The current local shortlist already ranked H-34-01 first as a low-cost runnable direction. To avoid replacing it with an unmeasured new external-data idea, this session tested a reduced, explicit proxy made only from `depth_to_base_surf` and `det_elev_slope`: the equal-weight mean of empirical basement-depth percentile and inverse absolute-slope percentile. The score is a basin-cover/low-relief **observability prior**, not a fault detector.

- **Leakage canary:** each of the 19 cached numerical bands was scored alone on the same held-out component split; the maximum AUC was **0.576** (geodetic second invariant), below the prescribed **0.90** investigate threshold. The candidate composite AUC was **0.476**. These AUCs are screening diagnostics, not DTI or competition scores. Full per-band values are in the JSON artifact.
- **Holdout protocol:** evaluator `src/gemsdoe30/holdout.py::masked_dti` (the experiment calls it directly; a distance-transform implementation is cross-checked to < `2e-7`); hide complete 8-connected fault components, use a 300 m exclusion buffer around hidden positives for any hypothetical visible-label training set, mask the 40,118 visible-positive pixels exactly in scoring, and use the pooled triangular DTI (`R=300 m`, 100 m pixels, α=0.2, β=0.8). No supervised model was trained in this candidate screen, and no catalogue-derived predictor was built. The official-source rasters are owner mirrors, not organizer-authenticated.
- **HOLDOUT-DTI (evaluator `scripts/concealment_holdout.py` v1 / shared `masked_dti`; 20,870 withheld positive pixels; component-bootstrap 95% CI):** concealment prior **0.006789** (95% CI **0.002977–0.011871**); distance-profile-matched random control **0.036913** (95% CI **0.033334–0.040439**). The candidate is below its matched control and is a clear negative screen. The CI resamples 1,085 hidden components from additive TP/FP/truth sufficient statistics; it is a descriptive cluster-bootstrap interval for this proxy, not a private-test interval.
- **Comparator discipline:** the H19-5/D2.8 TIFF was **not** treated as a valid holdout baseline because its training/selection provenance cannot be proven independent of the withheld components. The older spatial-quadrant best of 0.18927 is not compared numerically to this component split. Therefore this result does not claim a win/loss against the current best on a matched protocol.
- **Decision:** stop this exact H-34-01 reduced transform; no fresh-seed confirmation is warranted after the large screen failure. No slot, submission, or output TIFF. Full data, band AUCs, CI, SHA pins, and caveats: [`candidate-screens/concealment-screen.json`](candidate-screens/concealment-screen.json); reproducible command: `.venv/bin/python scripts/concealment_holdout.py` (or `python scripts/concealment_holdout.py` with the documented train dependencies installed).

## Unique TIFF / registry gate

No candidate TIFF was created. This is the correct result under the required gates, not an omission hidden from the site:

1. H-34-01 failed its matched-control screen and did not beat a comparable current best.
2. The nine target public repos' raster files were not all retrievable in this run: GitHub API returned rate-limit HTTP 403 during binary acquisition. Paths/owner metadata are not the raster bytes. The candidate's pre-placement surface correlation and final-dot overlap therefore cannot be measured against every registry raster.
3. A prior artifact cannot be relabelled, resized, re-encoded, or slightly perturbed and called a unique discovery.
4. The portal validator is private; a local format check cannot establish organizer acceptance. No file can responsibly be labelled “OK to download and submit” until scientific, duplicate, format, and provenance gates pass.

Once a future candidate passes those gates, build with `src/gemsdoe30/submission.py` / `scripts/build_submission.py`, validate against the locally pinned sample template, compute SHA-256, and publish a one-click download with a unique run name and a note of at most 140 characters. No weekly slot has been used.

## Current limits and next actions

- Owner-mirror data placement is now reproducible in this checkout: `python scripts/restore_public_mirrors.py`; then `python scripts/prepare_data.py`. SHA-256 values are recorded above. These files are still not organizer-authenticated.
- The reducer's `data/external/` has derived small rasters but not the raw USGS SGMC polygon packages claimed by earlier notes as “on disk.” H-34-01's full SGMC map-unit-age/lithology version remains data-blocked; this screen only tested the competition-band proxy.
- Fetch a hash-pinned set of the nine registered submission rasters using an allowed route after the API rate limit resets; build a read-only duplicate audit before constructing any final dots.
- Resolve data access and ROI coverage for NWIS, the 3-D thermal-model grid, and EarthScope GNSS before calling any external candidate viable.
- Run a frozen candidate with a held-out segment buffer, feature-alone canaries, pooled DTI and component-cluster CI; compare only within a matched evaluator/frame; stop after three experiments or two hours.
- Update the live-feed workflow without automating DrivenData access; retain official leaderboard snapshots only when obtained through an allowed, dated process.
- Keep entrant authorization, eligibility, AI disclosure and the official deadline conflict under review; no automated competition login or upload is available or attempted.

## Run card

```json
{
  "hypothesis": "H-34-01 reduced basin-concealment prior: thick basement cover plus low absolute detrended-elevation slope",
  "mechanism": "Concealed basin-fill settings may under-represent blind/subdued faults in a surface catalogue; the tested transform is only an observability prior",
  "named_non_fault_mimic": "Alluvial basin fill, lithologic contacts, and low-relief depositional surfaces",
  "holdout_dti_and_95pct_ci": "HOLDOUT-DTI; scripts/concealment_holdout.py v1 with shared src/gemsdoe30/holdout.py::masked_dti; 20,870 withheld positive pixels; component-bootstrap 95% CI: 0.006789 [0.002977, 0.011871]. Matched random: HOLDOUT-DTI 0.036913 [0.033334, 0.040439]. Neither is ORGANIZER-CONFIRMED.",
  "correlation_overlap_vs_registry": "NOT PASSED; candidate surface/final dots not published; the nine-site binary registry raster set could not be fully fetched after GitHub API rate-limit HTTP 403",
  "raster_sha256": "NONE — no TIFF generated",
  "validator_output": "NOT RUN; no candidate raster. Required future checks: no NaN inside footprint, values in [0,1], single band and exact template CRS/shape/transform",
  "submission_name": "NONE — no slot-ready artifact",
  "submission_note": "No submission: screen failed; no unique registry audit or format validation",
  "verdict": "negative"
}
```
