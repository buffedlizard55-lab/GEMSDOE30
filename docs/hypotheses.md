# Ranked geological hypotheses — preregistration candidates

**Status of this file (2026-10-03):** the H-31/H-32 candidate tables below are retained as the
ranked research register; several candidates have since been tested and are no longer untried.
H-31-01, H-31-02b, H-32-01, H-32-05, and H-33-01 have measured outcomes; none was promoted.
The older four-candidate register is project history; obsolete availability statements there do
not describe the current workspace. Current source/access gates and next-candidate status are
summarized at the end of this file.

**Promotion rule (unchanged):** no weekly submission slot may be proposed for a hypothesis whose
feature data are not obtained and checksummed, whose recipe and thresholds are not frozen before the
run, whose holdout gate does not pass on a buffered spatial holdout, and whose exact candidate
GeoTIFF does not pass the template audit. A catalogue-derived holdout is a **necessary but biased**
proxy: the official metric masks catalogue pixels, so a catalogue holdout can reward exactly the
predictions the competition ignores (measured in `docs/research/emission-anatomy.json`).

---

## Active untried shortlist (reviewed 2026-10-03)

These five are the current **not-yet-tested-in-this-checkout** hypotheses selected from the older
registers. “Untried” is bounded by inspected repository experiments and public owner summaries; it
is not a claim about every private or historical run. H-31-01, H-31-02b, H-32-01, and H-32-05 are
excluded because their registered variants have been tested; H-32-04 is included only as a
conditional candidate because catalogue labels cannot validate it.

| Rank | Hypothesis · layers and physical signature | Why it could reveal uncatalogued faults · distinction | Planning gain / cost | Official source and access status | Falsifiable gate |
| --- | --- | --- | --- | --- | --- |
| **1** | **H-31-04 K–Th–U radiometric alteration unmixing along lineaments.** `geodawn_rad_u8.tif` K, Th, U, total count plus the derived Th/K, U/K, U/Th stack; test ratio-space alteration with along-lineament coherence, not raw magnitude. | Fluid-rock alteration can make a radiometric halo even where no scarp or mapped surface trace exists. Ratio/unmixing plus lineament coherence is distinct from using radiometric bands as ordinary model inputs; lithology-stratified null is mandatory because ratios track rock type. | **+0.001…+0.012** planning prior; **low** compute cost. | [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) is the official source and public-domain catalog record. The local bands are owner-derived/quantised mirrors, not organizer-authenticated; verify band metadata and exact source lineage before freezing. | On four buffered spatial blocks, compare frozen unmixing/coherence arm to identical regional baseline, raw-band arm, and count-matched spatial null; hold out whole catalogue components where possible. Require pooled ΔDTI ≥ +0.005 over the same-run best, ≥3/4 positive folds, and fresh-seed replication; report near-miss bins and lithology-stratified null. |
| **2** | **H-32-03 Geothermometer discordance / blind-upflow zoning.** Local wellspring chemistry fields `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c` plus `cond_surf`; flag non-equilibrium quartz/cation/chalcedony temperatures and test corridors along independent lineaments. | Chemistry can sample deep fluid pathways above faults with no surface expression. This is distinct from scalar spring-temperature/thermal-population work; the usable chemistry subset is small (~1,000 sites), so power is limited. | **+0.001…+0.012**; **low** compute cost after source/schema check. | [GDR 1486](https://gdr.openei.org/submissions/1486) is the recorded provenance for the owner-maintained well/spring mirror; [GDR 1391](https://gdr.openei.org/submissions/1391) documents the INGENIOUS compilation. The catalog pages were reviewed; the exact chemistry CSV lineage/license and schema must be reverified before use. Local owner mirrors are not organizer-authenticated. | Predeclare the discordance formula and lineament tolerance; compare chemistry-only and chemistry×conductance arms against temperature-only and proximity-matched controls on buffered spatial blocks. Require the common +0.005 / 3-of-4 / fresh-seed gate, with whole-site clusters held out and score-domain counts reported. Stop if the sample/source audit fails. |
| **3** | **H-32-02 Quaternary vent-feeder alignment.** 21 GDR 1391 vents (20 basalt, one rhyolite) plus `tmi_hg` / magnetic-anomaly edges; test 2+ vents aligned over 2–8 km and continuation along a magnetic dike-like edge. | Vent chains can expose feeder structures absent from the fault catalogue; measured 0/21 vents are within 300 m of a catalogue trace. No inspected local or owner summary uses vent geometry. Small `n=21` means low power and volcanic/non-tectonic confounding. | **+0.001…+0.010**; **low** compute cost; low statistical power. | [GDR 1391](https://gdr.openei.org/submissions/1391) states CC BY 4.0; the Quaternary-volcanics ZIP was downloaded/hash-verified via the recorded bridge receipt and rasterized locally. Feature source is official, but the competition raster remains an owner mirror. | Freeze vent-pair distance/strike and magnetic-edge tolerance; compare aligned vents to 1,000 spatially constrained random point sets and magnetic-only controls on blocked holdout. Require a positive paired effect in ≥3/4 folds and fresh-seed confirmation; otherwise reject rather than widen the search post hoc. |
| **4** | **H-31-03 Drainage-response fault traces.** USGS NHD flowlines plus 1–10 m USGS 3DEP DEM; seek strike-aligned knickpoint chains, channel offsets/beheaded channels, and channel geometry coherent across a candidate trace. | Rivers preserve deformation where a scarp is eroded or buried; no hydrology transform was found in inspected repo/owner summaries. Must separate tectonic signal from lithology, drainage capture, and DEM artefacts. | **+0.002…+0.020**; **medium-high** data/processing cost. | [USGS TNM NHD Best Resolution API query](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=National%20Hydrography%20Dataset%20(NHD)%20Best%20Resolution&bbox=-119,38.5,-118.5,39) returned product records for one test bbox. Full ROI coverage, actual downloads, reuse details, and DEM linkage remain unchecked; do not call it runnable yet. 3DEP is USGS public-domain data. | Obtain full-ROI data and checksum/schema first. Then freeze the geomorphic detector and compare it with slope-only and spatially matched random controls on buffered blocks; require +0.005 over best, ≥3/4 folds, and fresh-seed confirmation. Any incomplete NHD/DEM coverage stops the test. |
| **5** | **H-32-04 Kinematically constrained Qfaults gap completion.** Quaternary fault traces with recency, slip sense/rate, and length; seek physically consistent gap-extension/continuity >300 m from the known catalogue. | Such traces may contain unmapped geometry, but INGENIOUS/Qfaults labels overlap the training catalogue; a catalogue holdout would be circular. This differs from H-31 scarp morphology by using fault kinematics, not topography. | **+0.005…+0.025 conditional**; **medium** data/analysis cost. | [OSTI 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722) and [GDR 616](https://gdr.openei.org/submissions/616) are official independent-inventory candidates; pages verified, archive retrieval/schema/coverage not yet verified. The downloaded GDR 1391 Qfaults layer rasterizes to zero features in the ROI and is not usable as an independent truth set. | **Hard gate:** obtain and checksum an independent inventory, verify it is independent of INGENIOUS/Qfaults and covers the ROI, then preregister buffered spatial holdout and require +0.005 over a count-matched baseline, ≥3/4 folds, and fresh-seed confirmation. If no independent truth is available, do not score or promote; catalogue-only agreement cannot validate the hypothesis. |

For all matched-emitter gates, record both global emission budget and active scored-domain count; equal global counts alone are not active-count matched. A failed gate means no weekly slot. The current lowest-cost *next action* is the H-31-04 source/metadata audit, not immediate scoring.

---

## New register (2026-10-03 session)

Design context that makes these hypotheses different from the earlier four: the official clarifications
read this session establish that (i) known USGS/INGENIOUS pixels are masked out of scoring
([thread 11516](https://community.drivendata.org/t/11516)), (ii) "new fault" means *any fault pixel not
already captured by USGS/INGENIOUS* and **may include newly mapped geometry of an existing fault
system** ([thread 11536](https://community.drivendata.org/t/11536)), and (iii) the organizers will not
describe the test faults' sources, types or coverage
([thread 11527](https://community.drivendata.org/t/11527)). The exact metric algebra
(`docs/research/why-d28-scored-026.md`) gives the conditional marginal rule `k > 0.2 × current DTI`;
it does not make false positives universally "cheap" or reveal hidden-trace coverage. The hypotheses
below are judged on whether their physical signatures can add 300 m-weighted coverage of *unmapped*
geometry while controlling false-positive mass. The reported 0.2600 operating point is not
attributed to the local D2.8 TIFF.

| Rank | Candidate | Layers / physical signature | Why it can catch a fault absent from USGS/INGENIOUS | Difference from all inspected prior work | Expected ΔDTI prior and cost | Official source, access status (checked 2026-10-03) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **H-31-01 Relay-ramp / step-over connector completion** | Competition bands `det_elev`, `det_elev_slope`, `tmi_hg`, `tc`, `cond_surf`, `depth_to_base_surf` + LiDAR scarp channels (`step_max`, `cross_max`, `strike`) + **catalogue geometry used only as geometry**. Signature: *pairs* of sub-parallel lineament terminations (azimuth within ~20°, separation 0.3–3 km, along-strike overlap) and the connector between them. | Extensional step-overs and relay ramps are where short, oblique breaching strands live; mapping campaigns record the two long boundary strands and routinely omit the short connector. Staff explicitly ruled that this counts as a new fault. Credit here is at the *unmasked* pixels between mapped strands, i.e. exactly the unclaimed domain. | Prior registers test scalar fields (thermal points, strain×conductance, seismicity density, 3-D temperature) or, on the owner's public sites, multiline *density* corroboration and ridge-top gap closure. None of them pair lineament **terminations** or test along-strike overlap geometry; this is a relational, second-order feature. Closest neighbour to disclose: GEMSDOE27 "topo-gap-closure" (owner-reported 0.2449), which bridges gaps in a scalar ridge surface without pairing constraints. | **+0.005 … +0.030** planning prior, moderate confidence; **medium cost** — all inputs are already local (SHA-256 pinned), CPU-feasible. | Competition raster via authorized session or the pinned owner mirror (not organizer-authenticated); LiDAR-derived scarp features derive from USGS 3DEP 1 m DEM, described by USGS as **public domain**. No new external transfer needed. | **Tested 2026-10-03; not promoted.** Component holdout did not separate connector geometry from the proximity control, and owner-reported fresh-draw relay work also failed confirmation. Do not pursue the same feature with inspected labels; a materially new observable requires a new preregistration and holdout. |
| **2** | **H-31-02 Matched-filter scarp bank + along-strike continuity tracking on official USGS 3DEP 1 m DEM** | USGS 3DEP 1 m DEM tiles (public domain). Signature: oriented, scale-selected step matched filters for 0.5–5 m scarps, followed by a continuity tracker that links scarp segments across gaps at a fixed strike tolerance. | Short, discontinuous scarps of minor faults are systematically absent from field-mapped Quaternary compilations and are invisible at 100 m. The competition itself supplies 1 m DEM links, which is evidence the organizers expect fine-scale topography to carry signal. | The local owner-derived `lidar_scarp_features_u8.tif` stack (12 channels) already contains first-order scarp statistics, and the owner's public LiDAR attempt scored 0.1461. No full raw-DEM matched-filter/continuity implementation has been tested in either codebase. | **+0.005 … +0.040** planning prior for the full raw-DEM concept (highest ceiling, lowest confidence); **high cost**: broad-area tile acquisition is required. The low-cost reduced-stack orientation transform was tested separately as H-31-02b and is not a proxy for the full 1 m hypothesis. | **[Obtainability partially verified]** `https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119,38.5,-118.5,39` returned **32 products** for one test bbox with direct GeoTIFF URLs and a public-domain statement. This does not establish full study-area coverage or complete local access; the sandbox transfer is blocked by TLS, and broad-area volume/coverage remain unresolved (IR-30-006). | **H-31-02b reduced-stack screen tested and not promoted:** spatial and strike-perturbation gates failed; its SGMC screen was global-budget matched only and cannot promote it. Full 1 m DEM matched-filter/continuity hypothesis remains untested and access/coverage blocked. See [measured interpretation](research/h31-02b-scarp-full-pool-holdout.md). |
| **3** | **H-31-03 Drainage-response faults: channel offsets, beheaded channels and knickpoint alignment** | USGS National Hydrography Dataset flowlines + USGS 3DEP DEM (1 m or 10 m). Signature: strike-aligned knickpoint chains and left/right-lateral channel offsets across a candidate trace. | Fluvial geomorphology records deformation where the scarp itself is eroded, buried or too subdued to map; a fault-trace compilation is not a drainage analysis, so the two inventories disagree by construction. | The repository uses no hydrology layer at all, and no inspected owner page reports a flowline-based transform. | **+0.002 … +0.020**; **medium-high cost** (tile download, hydrological conditioning, flowline extraction, DEM–flowline registration). | **[Obtainability not yet verified]** `tnmaccess.nationalmap.gov` exposes NHD products through the same public TNM API used above; the specific NHD query and the local transfer have **not** been executed. Treat as conditional. | **Registered, not run; source check incomplete — must be completed before promotion.** |
| **4** | **H-31-04 Radiometric alteration unmixing along lineaments** | GeoDAWN K, Th, U and total count (`geodawn_rad_u8.tif`, 4 bands) and the ratio stack (`geodawn_extensions_u8.tif`: Th/K, U/K, U/Th, TMI upward-continued 150 m). Signature: ratio-space alteration anomaly (K-enrichment with U mobilisation) tested for *along-lineament coherence*, not raw band magnitude. | Fault-controlled fluid pathways produce clay/illite (± K) and uranium alteration haloes that can be detected radiometrically even where the surface trace is unmapped; the catalogue is independent of the radiometric grid. | Both this repository and the owner use radiometric bands as ordinary model features. An explicit three-endmember unmixing (K–Th–U) combined with a lineament-coherence test is not implemented in either. Beware: K/Th ratios are dominated by lithology, so a lithology-stratified null is required. | **+0.001 … +0.012**; **low cost** — the rasters are already local. | USGS GeoDAWN data release, DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) (public-domain USGS data per the catalog record). Local copies are owner-derived quantisations, not organizer-authenticated. | **Registered, not run; cheapest arm to add.** |
| **5** | **H-31-05 Curvature (second-derivative) strain-ridge detector** | `geod_dilaterate`, `geod_shearrate`, `geod_2ndinv` competition bands. Signature: Laplacian/structure-tensor ridge of the *strain* field rather than the strain value itself. | Interpolated strain grids are smooth; the edge structure that localises a fault zone may be sharper in the derivative than in the field. | The registered strain×conductance hypothesis and the owner's strain/scalar family both used the fields themselves; the owner's public pages report those families performing poorly. This is a cheap transform test, ranked last deliberately. | **−0.002 … +0.006** (the repository's own pilot already failed a strain-interaction screen; that prior is honoured here); **very low cost**. | Competition raster only; no external transfer. | **Registered, lowest priority; a negative result is the base-rate expectation.** |

**Metric context (not a score forecast):** the 300 m triangular kernel rewards nearby predictions;
under the verified algebra, an added unit prediction at kernel credit `k` improves a current score `s`
only if `k > 0.2 × s`. The hidden truth size and a candidate's true precision/coverage are unavailable,
and the 0.2600 leaderboard row is not authenticated to the named D2.8 TIFF. No listed planning prior
implies a likely leaderboard gain. The priors above are experimental ranges, not measurements or
predictions; see [`metric-response-surface.md`](metric-response-surface.md).

**Instantiated validation for rank 1 (this session):** hide-and-recover **component holdout** — a
deterministic subset of catalogue components is removed from training and used as stand-in truth, the
mapped remainder is masked exactly as the organizer masks known faults, and the connector feature must
raise the masked-domain DTI on the hidden components over the same-run no-connector control. This is
the design the previous session's review demanded ("catalogue geometry must hide held-out
components"); the quadrant proxy alone cannot test a feature whose target *is* between mapped strands.

**Measured outcome (2026-10-03, real data).** The harness `scripts/relay_connector_holdout.py` ran to
completion (`docs/research/relay-connector-holdout.json`) on the real catalogue. Design: the 3,199
8-connected catalogue components were split into hidden/known halves by centroid within 3.2 km tiles;
connector map = the 1,500 m dilation of *known* traces that contains ≥ 2 distinct known components,
minus everything within 300 m of a known trace; controls were (a) `zone_all`, the whole near-known
annulus minus the same 300 m band, and (b) `random_near`, count-matched draws from that same annulus;
every arm was scored with the exact masked distance-weighted Tversky on the hidden half only. At a
matched 15,000-pixel emission budget (means of 8 paired draws): connector zone **0.0485** DTI,
`random_near` **0.0480**, `zone_all` **0.0491**, far-field random **0.0214**. Credit per emitted pixel:
connector **0.0640**, `random_near` **0.0632**, `zone_all` **0.0626**, far random **0.0277**.

Reading: the connector geometry carried **+1.2 %** credit per pixel over a proximity-matched control —
far too small to separate from draw noise, and below the whole-annulus control. The dominant effect is
the generic proximity prior (~2.3× per-pixel credit for any pixel near mapped traces versus far field),
not the second-order terminal-pair geometry that H-31-01 claimed. A methodological caveat, recorded so
the test is not over-read either way: the connector pool (1,110,061 px) is 94 % of the entire near-known
annulus (1,178,995 px), so "connector" and "proximity-matched control" draw from nearly the same support
and the matched-budget comparison is intrinsically weak. A first version of the harness with a 102 km
checkerboard split produced the same non-result from the opposite direction (it separated whole fault
zones regionally), which is itself a reminder that the split must interleave at the fault-zone scale.

Verdict: **H-31-01 is not promoted as instantiated and is closed on this evidence.** The proposed
paired-termination variant is not an automatic next step: any materially different observable must be
specified before viewing new scores, justified against the owner-reported negative relay confirmation,
and evaluated on an uninspected holdout with a new preregistration. Do not reuse these inspected
catalogue component labels to retune the same connector feature.

### Measured outcome — metric-algebra emission holdout (2026-10-03, real data)

The preregistered emission experiment (`docs/research/metric-emission-preregistration.md`,
`scripts/metric_emission_holdout.py`) has now been run to completion on the real grid, all four
held-out quadrants, every rule choosing its own operating point, parameters selected
leave-one-fold-out. Raw output: `docs/research/metric-emission-holdout-results.json`; write-up:
`docs/research/metric-emission-holdout-results.md`.

**Registered gate: FAILED — no family promoted.** Pooled cross-validated proxy DTI: `uniform`
(Poisson-disk thinning) **0.18675**, `adaptive` **0.18927**, `dense` **0.13455**, `metric` (greedy
marginal rule) **0.13313**. The metric rule needed **≥ +0.005** versus both `dense` and `uniform`;
it came out **−0.0014** versus dense and **−0.0536** versus uniform, and was below uniform in every
fold. `adaptive` − `uniform` = +0.0025, positive but under the threshold — not promoted either.

Mechanism, recorded because it matters for the next attempt: the greedy rule was **truncated by the
candidate-pool cap**, not by its own stopping criterion — it emitted exactly 120,000 pixels per fold
(the pool limit) at only 0.033–0.043 credit per emitted pixel, while uniform thinning emitted 3–6×
fewer pixels at 2.4–4.7× the credit per pixel. On a pointwise-GBM belief surface, the estimated
marginal credit stays above λ ≈ 0.055·cost for far more pixels than the surface can actually
deliver against the sparse catalogue truth. This corroborates the earlier count-matched pilot's
null, and matches the owner's public evidence (their best artifacts are sparse dotted masks with
median spacing ≈ 2.2–3.0 px, i.e. near the 300 m kernel radius — coherent with "thin, do not
flood"). The natural follow-ups are (a) calibrating the belief surface before applying the marginal
rule, and (b) replacing the pool cap with an explicit FP-budget cap.

---



### Cross-check against the owner's own 2026-10-02/03 findings (owner-reported, unverified)

Before freezing the five new candidates, their families were checked against the owner's own
GEMSDOE25 knowledge documents (fetched 2026-10-03 via the GitHub API; **owner-reported, not
independently verified, not competition receipts**). These change the confidence ordering and stop
one line of work:

* **Relay/termination geometry is already twice-dead.** The owner's preregistered H30-1 paired relay ×
  terrain factorial *screened positive* (mean paired gain +0.004078, 4/4 folds, draws 6–7) and then
  **failed its fresh-draw confirmation** (−0.001275, 1/4 folds) → registered verdict "Stop this
  candidate." Our independent H-31-01 component holdout also failed to separate connector geometry
  from a proximity-matched control (+1.2 % credit/px). Do not build further on the relay-connector
  family unless a genuinely new observable is added; treat both results as one convergent negative.
* **DEM curvature / scarp descriptors (the owner's factor B) carry the effect**: +0.0253 on the
  catalogue-hide-and-recover proxy, 4/4 folds, and the owner's factor analysis attributes ~14 % of the
  effect energy to B (vs 80 % to catalogue geometry E, which is partly proxy-flattering). This is the
  strongest external corroboration for **H-31-02** (3DEP 1 m matched-filter scarps) being the right
  family — and the reason it is the top-ranked new candidate despite its transfer cost. Our own
  H-31-05 curvature detector is a weaker echo of the same family.
* **Thermal / geochemical evidence (factor D) is small but consistent** (+0.0044, 4/4) — supportive
  context for **H-31-04** (radiometric K–Th–U unmixing), which stays cheap and second-tier.
* **Potential-field gradients (A) were inert** (−0.0027, 1/4) and **strain/seismicity (C) was
  consistently negative** (−0.0109, 0/4) on the owner's proxy; this *deprioritizes* strain-derivative
  ideas (including parts of H-31-05) and is consistent with our own pilot's strain findings.
  H-31-02/03's DEM-based families are unaffected.
* **Emission geometry (owner's frozen sweeps, exploratory + confirmatory draws):** score-ordered dots
  at ~2.4 px spacing with total positive share ≈2.45–3.5 % beat score-blind `dot_thin` at equal pixel
  count (+0.0034–0.0037, 4/4) and the joint add-on surface (X1+X2+X3, each weak alone) passed both
  replicates (+0.0050, +0.0038) — but its predicted best corner B+E did **not** replicate, i.e. their
  own surface selection was partly screen-overfit. Our metric-emission gate failed in the same
  direction: thin, score-ranked dots beat both dense emission and the greedy marginal rule. Any
  future emission work here should therefore use **score-ordered thinning at a fixed small share,
  with the thinning radius and share chosen leave-one-fold-out**, not a marginal-rule greedy emitter.

**Historical status note:** this four-candidate table was drafted before owner-mirror rasters and experiments were available in this checkout; its old “none run/no data” statement is superseded. Owner mirrors have since been restored, and several later experiments are documented above. Novelty was checked against inspected GEMSDOE24–27 public summaries and owner-supplied notes—not every historical repository or private run—so treat “not found” as a bounded claim, not proof that no competitor has tried it.

**Promotion rule:** no weekly slot is available to a hypothesis until its feature data are obtained and checksummed, the recipe and thresholds are frozen, it beats the current same-run spatial-holdout best in a buffered spatial validation with a fresh-seed confirmation, and the exact candidate GeoTIFF passes the template audit. A positive catalogue-derived holdout is necessary but not sufficient evidence for hidden, expert-mapped faults.

## Rank table

| Rank | Candidate | Layers / physical signature | Why it may reveal an uncatalogued fault | Difference from inspected prior work | Planning prior for ΔDTI / cost | Official source and obtainability | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **Blind upflow / alteration evidence from independent geothermal observations** | GDR 1391 2 m temperature probes; paleogeothermal spring-deposit features (e.g. sinter/tufa/travertine); Quaternary volcanic vents/flows. Test each source separately, then a preregistered spatial-coincidence/corridor transform rather than an isotropic buffer alone. | Hydrothermal upflow and near-surface deposits can occur above fluid pathways whose surface fault trace is not in the USGS/INGENIOUS fault catalogue. These observations are independent of the catalogue geometry. They are indirect and can arise from non-fault heat sources, so a physical relationship must be tested rather than assumed. | The inspected 19GEMSDOE / 25GEMSDOE / 27GEMSDOE summaries mention thermal/geochemical or point-distance work, and 27 reports a prior thermal-distance arm near null. This candidate is deliberately limited to GDR sublayers described by the official GDR catalog as present in the compilation and tests new probe/deposit/volcanic evidence and joint geometry. **The distinction is provisional** until earlier code and exact source layers are audited. | **+0.000 to +0.006 DTI** planning prior, low confidence; medium-high cost (retrieve, checksum, inspect schemas, project, rasterize, run separate arms). The interval is an experiment-planning prior, not a forecast or measured gain. | GDR 1391 is cataloged as publicly accessible under CC BY 4.0; the page lists the [probe](https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip), [paleo-geothermal](https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip), and [volcanics](https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip) downloads. The catalog page is reachable, but direct shell HEAD requests to all three file URLs failed with `SSL_ERROR_SYSCALL`; actual archive bytes/hashes, schema, license conditions, and alignment are **not** verified here. Do not call the layer viable until those checks pass. | **Top candidate by expected upside; blocked.** No data placed and no holdout run. No slot. |
| **2** | **Dilatational-strain × conductive-corridor intersections** | Geodetic dilation/shear/strain-invariant grids plus surface conductance and depth-to-conductive-base layers in the competition/INGENIOUS stack. Signature: spatially coincident, locally persistent strain-gradient and conductive corridors, scored as joint features rather than independent scalar values. | Dilation can favor fracture opening; conductivity can respond to fluids/clay alteration. Their intersection may localize blind permeable structures beyond the mapped trace inventory. Basin clay caps, sediments, and smooth low-resolution fields are major confounders. | The linked GEMSDOE25/27 summaries describe raw/scalar geophysical layers and a strain/seismicity family that performed poorly as a standalone factor; they do not report this preregistered local interaction. This checkout has no previous implementation. Verify exact names and historical coverage against actual band metadata before fitting. | **+0.000 to +0.004 DTI** planning prior, low confidence; low-medium cost once the competition raster is available. | Requires the login-gated official training feature package/metadata plus GDR descriptions; the GDR catalog states CC BY 4.0 for its public compilation. Exact competition band names and any external archive contents are not verified here. The experiment is not presently runnable. | **Not run.** Good second option if the GDR download for rank 1 cannot be verified. |
| **3** | **Anisotropic seismicity-fabric / strain alignment** | Dependent and independent earthquake-density surfaces from INGENIOUS; geodetic shear/dilation. Compute orientation-coherent ridges or a structure-tensor fabric across scales, not a threshold on density. | A linear seismicity fabric aligned with regional shear may indicate a blind active strand omitted from a surface-fault catalogue. Seismicity swarms, catalog completeness, and aseismic faults can erase or mimic the signal. | The public GEMSDOE25 summary includes an inert scalar strain/seismicity family; no directional seismicity-fabric transform was found in the inspected summaries. It differs from DEM scarp persistence, magnetic/gravity edge coherence, and the topology/gap-closure experiments described on GEMSDOE27. This novelty claim is limited to inspected public summaries. | **+0.000 to +0.003 DTI** planning prior, low confidence; low-medium cost (existing/official grids plus directional filters). | The GDR 1391 catalog is publicly accessible under CC BY 4.0 and lists earthquake-density and geodetic models. Direct archive availability/schema are not verified here; the competition raster is login-gated. No archives or rasters are checked into this repo. | **Not run.** A negative result is plausible because earthquake density is an imperfect proxy for fault location. |
| **4** | **Vertical thermal-gradient anomalies from the USGS Great Basin 3-D temperature model** | USGS 3-D temperature model v1.1 (DOI 10.5066/P149FR54), with official Great Basin heat-flow layers as context. Derive depth-differenced gradients/isotherm bending at native resolution, then evaluate whether anomalies spatially coincide with structural corridors. | Subsurface fluid circulation can perturb conductive temperature profiles near faults, including faults without a mapped surface trace. The regional model is smoothed and explicitly relies on assumptions about conductive conditions; it may not resolve individual faults. | The inspected project summaries discuss surface temperature/radiometry and geothermal point features; no use of the exact v1.1 3-D temperature model was found in those summaries. This is a coarse thermal-system prior, not another DEM or magnetic edge filter. | **+0.000 to +0.002 DTI** planning prior, low confidence; medium-high cost (obtain, inspect depth levels/resolution, reproject carefully; prevent leakage). | USGS Data Catalog page states public access and U.S. public-domain license, and links DOI/data. Page access verified; actual grid retrieval and alignment not verified. | **Not run.** Keep lower-ranked because the spatial resolution and conductive-model assumptions may not support fault-scale localization. |

### Prior provenance

The DTI intervals above are deliberately broad, non-negative *planning priors*, not learned coefficients, confidence intervals, published findings, or model outputs. They are not calibrated to hidden labels. In the public archive for GEMSDOE27, some proposed H28 experiments also use approximate DTI ranges; those are owner hypotheses and were not used as independent evidence. The only promotion evidence accepted here will be a preregistered, reproducible holdout result.

## Frozen validation plan for rank 1

1. **Data/provenance gate:** retrieve the named GDR 1391 files from its catalog links; record bytes, URL, timestamp, SHA-256, license, feature schema, CRS, coordinate units, and bounding box. Confirm no unauthorized copying or data leakage. If archives cannot be fetched or aligned, stop rather than substitute guessed files.
2. **Novelty gate:** compare exact feature names/derivations against prior repository manifests and the inspected public experiment summaries. If the same layers or transform already exist, revise the hypothesis before seeing fold scores and record the change.
3. **Freeze a spatial protocol:** spatial quadrants/blocks with at least a 300 m exclusion buffer; hold out whole contiguous fault components where metadata permit. Do not randomly split pixels. Use the same folds, patch samples, model initialization, optimizer budget, and emission postprocessing for the baseline and candidate. Use fold-local transformations and no held-out labels in feature engineering.
4. **Paired comparison:** fit baseline, each individual data source, and the preregistered combined arm; score the complete stitched OOF grid with the exact distance-weighted Tversky implementation. Report TPw/FPw/FNw, exact full-grid DTI, quadrant-isolated diagnostics, every seed, and variation. Also report near-miss credit-distance bins and false-positive cost by distance. Do not average fold ratios or add components from masks that omit cross-quadrant kernel interactions.
5. **Confirmation:** after a screen pass, use fresh fixed seeds and the same frozen protocol. Require the candidate to beat the current same-run holdout best, with a prespecified minimum gain and no unacceptable fold-level regressions. Write the threshold/gate before running; do not tune against the public leaderboard.
6. **Submission gate:** only after confirmation may an all-permitted-training-data model be created. Hash the TIFF, record the one-line submission note, revalidate exact template CRS/shape/transform/footprint/range, and have the authorized entrant decide whether to use a weekly slot. A public leaderboard score is not a proxy holdout score.

## Current result

The rasters are present locally from SHA-256-pinned owner mirrors (not organizer-authenticated); the template-label irregularity is recorded in `docs/research/data-audit.json`. Multiple real-data holdouts have run, all on public-catalogue or SGMC proxy labels. **No candidate is promoted and no weekly submission slot is justified.**

1. **Four-arm spatial pilot** — failed its frozen promotion gate (interaction arm H lost to context control C by 0.000065 against required +0.002; `docs/research/pilot-results.json`).
2. **Paired regional-vs-boundary loss ablation** — seed-30 screen: pooled DTI 0.062042 → 0.063990, Δ +0.001948, 3/4 folds; partial-distance-only truth pixels 80 → 40. Fresh-seed 31 confirmation: Δ +0.000115, 2/4 folds, sign flips, although the near-miss conversion reproduced (1,889 → 724). The geometry term changes near-miss allocation as requested but does not reliably raise proxy DTI at this budget. `docs/research/loss-ablation-holdout.md` + `loss-ablation-holdout-seed31.json`.
3. **Preregistered metric-algebra emission holdout** — gate failed: pooled cross-validated DTI uniform 0.18675, adaptive 0.18927, dense 0.13455, metric-greedy 0.13313. The greedy rule missed its ≥+0.005 gates by −0.0014 versus dense and −0.0536 versus uniform; adaptive's +0.0025 is below threshold. The greedy rule was capped at 120,000 pixels/fold at 0.033–0.043 credit/pixel, versus uniform's 3–6× fewer pixels at 2.4–4.7× the credit. `docs/research/metric-emission-holdout-results.md`.
4. **H-31-01 relay-connector holdout** — +1.2% credit/pixel versus proximity-matched random, but below the full near-known annulus; not promoted. Do not retune the same connector feature on inspected labels. `docs/research/relay-connector-holdout.json`.
5. **H-31-02b reduced-stack scarp-orientation screen** — spatial proxy DTI 0.1655413755 versus uniform 0.1348326480, but below the archived spatial best 0.1892699401 by 0.0237285646 and below its registered +0.005 promotion threshold. Strike permutation removed only 5.99% of candidate gain (required ≥50%). Both primary/perturbation gates failed. The five-repeat SGMC screen mean 0.1294372572 passed its frozen numeric screen versus archived `cand_t04s4` (0.0952570598), but that comparison used the same 80,392 **global** budget with 72,310 / 80,388 active scored-domain pixels for candidate/archive (blind random: 73,843). It is not active-count matched; archived mask is absent and no fresh seed confirmation was run. **Not promoted. Do not rerun or tune against these inspected SGMC labels.** See [measured interpretation](research/h31-02b-scarp-full-pool-holdout.md).
6. **H-33-01 placement-policy holdout** — the 80k gate was void because quota arms emitted 68,573 in-domain dots against an 80,000-dot in-domain random control. The 40k sensitivity comparison is **active-scored-domain-count matched** for the model and random arms: the script builds every selection pool inside the scoring domain, draws blind random there, and `score_emitter` masks outside-domain pixels before recording `dots`. Means: whole-domain score-first 0.07608 versus 0.0721–0.0725 for band-stratified arms and 0.03660 for proximity-first. The JSON lacks separate global/active fields, but the code path establishes that all selected points in this sensitivity arm are active; see the post-run scope note in [result](research/h33-01-placement-policy-holdout.md). This verified 40k result does not resolve the separate global-vs-active mismatches in the H-31-02b/archived novelty screen (IR-30-033).
7. **Published research artifacts** — the GBM surface (90,358 dots) and SGMC-hedged variant (85,526 dots) pass local format validation and have paste-ready notes, but neither is holdout-promoted. Their local D2.8/SGMC comparisons are proxy evidence only.

The lowest-cost next data check is the still-untried H-31-04 radiometric K–Th–U unmixing arm, after source/schema and feature-manifest checks. The current five-candidate shortlist is below. The H-31-02b reduced-stack result does **not** test the full raw 1 m DEM matched-filter/continuity hypothesis; that broader concept remains blocked on verified study-area coverage and transfer. Any next experiment needs a preregistered spatial holdout and fresh confirmation, with both global emission budget and active scored-domain count reported; do not reuse already-inspected SGMC labels.

---

## H-32 register (2026-10-03 second session) — five prior candidates (some now tested)

Required brief format: each entry names the exact layers, the physical signature, why it can
catch a fault **missing from the USGS/INGENIOUS catalogue** rather than one already in it, and
how it differs from anything already implemented in this repo or on the inspected owner sites.
Ranking is by expected DTI improvement and implementation cost. The science base behind these
is [`docs/research/geothermal-vents-knowledge.md`](research/geothermal-vents-knowledge.md)
(official DOE/OSTI literature + measured local data). A rules-PDF fact discovered this session
shapes all five: the scored test labels are **expert-new faults** beyond the INGENIOUS catalogue
(rules §2, §3.3), and the Phase-2 label set will be revised by expert review of submissions
(thread 11527) — so candidates target structures experts can confirm.

| Rank | ID / candidate | Layers / physical signature | Why it can catch an un-catalogued fault | Difference from everything implemented/inspected | Expected ΔDTI (planning prior) | Implementation cost | Validation path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **H-32-01 Geothermal-discharge corridor** (hot-spring cluster alignment) | `gdr_wellspring_in_footprint.csv` (`temp_c`, thermal class; 512 cells ≥ 60 °C, 256 ≥ 100 °C) + `cond_surf`, `depth_to_base_surf`, `det_elev_slope` competition bands. Signature: alignment corridors through hot-spring clusters (pair segments 2–8 km) and 1 km discharge haloes — a relational corridor transform, not a scalar heat field. | Hot springs discharge along permeable fault zones; measured: only 11.6 % of spring rows sit within 300 m of the catalogue and the median hot cell is 1.4 km from any catalogue pixel (Faulds: outflow surfaces km from the source structure) — i.e. most discharge sites demand a conduit the catalogue does not contain. The scored population is exactly young permeable structure. | Owner thermal work (h19-4 "thermal-pop", 15GEMSDOE "conj_alteration_mag") uses temperature/alteration as scalar emission fields. No repo/owner work tests spring-cluster *alignment corridors* or geothermometer-ranked discharge as a conduit prior. The repo's H-31-01 paired geometry used catalogue terminations; this pairs independent discharge points. | **+0.005 … +0.030** | **Low** — data already local | **Tested; gate failed, not promoted.** See `h32-01-vent-corridor-holdout.md`; no slot used. |
| **2** | **H-32-04 Un-catalogued Qfaults trace completion** | `gdr_qfaults_traces.csv` (slip rate, recency <15 ka/<130 ka, slip sense, length) + catalogue geometry for masking. Signature: kinematically consistent gap-extension corridors between Qfaults traces (matching slip sense ± rate) that lie >300 m from catalogue pixels. | Rules §2: labels derive from Qfaults + expert new faults, but measured 45 % of in-footprint Qfaults centroids sit >300 m from any catalogue pixel — those traces are literally "fault pixels not already captured by USGS/INGENIOUS" (thread 11536), and Quaternary faults are the primary control on geothermal systems (Faulds). | h18-4 (owner, 0.036) predicted USGS *geologic-map* faults; nothing tested the Quaternary subset with kinematic weighting and gap extension. **Circularity warning:** catalogue holdout cannot validate this (hidden components ⊂ catalogue); needs an independent fault map. | **+0.005 … +0.025 conditional** | **Medium** | Independent validation sources named: [OSTI 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722) structural inventory and [GDR 616](https://gdr.openei.org/submissions/616) play-fairway structural layers — pages verified 2026-10-03; archive retrieval pending. Viable only with one of those. |
| **3** | **H-32-05 Buried range-front pinch-out edges** | `depth_to_base_surf`, `iso_grav_anom_hg`, `tmi_hg` competition bands. Signature: edge/ridge transforms (structure-tensor, Laplacian) of the *basement-depth surface* — a fault displacing basin fill shows as a sharp gradient in depth-to-basement even where the surface trace is buried and unmappable. | Faults buried under Quaternary alluvium have no scarp for lidar mapping and are systematically absent from expression-based catalogues (Qfaults requires surface evidence); their displacement persists in the basement surface and gravity/magnetic gradients. | The repo and all owner sites use `depth_to_base_surf` only as a plain model band; no edge/curvature transform of the basement surface exists anywhere in the inspected code/sites (H-31-05 curvatures the *strain* field, not the basement surface). | **+0.002 … +0.015** | **Low-medium** — local bands | **Run and falsified;** see `h32-05-basement-edge-holdout.md`. The oriented-edge subvariant remains untested because the preregistered coherence floor accepted 99.65% of the footprint. |
| **4** | **H-32-03 Geothermometer discordance upflow zoning** | wellspring `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c` + `cond_surf`. Signature: sites where cation ≫ quartz temperature (steam-loss upflow) or chalcedony ≪ quartz (mixing) — non-equilibrium chemistry marks the upflow conduit, then corridor geometry along local lineaments. | Deep upflow through a fault needs no surface expression (39–75 % of Great Basin systems are blind — Faulds); chemistry discordance is a direct sample of deep fluid pathways the catalogue cannot contain. | No repo/owner work uses spring chemistry at all (only temperature counts). | **+0.001 … +0.012** | **Low** — local CSV | Catalogue-component holdout (power limited: ~1k chemistry sites) |
| **5** | **H-32-02 Volcanic-vent feeder alignment** | `gdr_volcanic_vents_in_footprint.csv` (21 vents: 20 basalt, 1 rhyolite) + `tmi_hg`, `mag_anom`, `rtp` magnetic edges. Signature: strike-aligned vent chains (2+ vents, 2–8 km) extended along co-located magnetic lineaments (dike swarms). | Measured: **0 of 21 vents lie within 300 m of a catalogue fault** (median 2.2 km) — the structures that fed these eruptions are unmapped in the catalogue; cinder-vent alignments are classic surface expressions of feeder fissures (and linear tufa/vent chains mark the blind Pyramid Lake system — Faulds). | No inspected repo/owner page uses volcanic vents in any form. Contrarian and nearly free. | **+0.001 … +0.010** (low power: n = 21) | **Low** — local CSV | Catalogue-component holdout (power-limited; report as pilot) |

**Ranking rationale (Maximize P(Win)):** rank 1 has the strongest independent physics, measured
2.3× near-catalogue enrichment, the largest usable point set (12,570 spring cells), and is
runnable now; rank 2 has the highest conditional ceiling but cannot be validated against the
catalogue proxy at all, so it is gated on external inventory acquisition; ranks 3–5 are cheap
local transforms with modest priors, ordered by signal richness. **None of these priors is a
forecast; only a preregistered holdout pass can promote a candidate.**

**Status (measured 2026-10-03): H-32-01 ran its preregistered gate and FAILED — not promoted.**
Pooled ΔDTI (spring − proximity-matched control) was **−0.01494** (screen, split 31) and
**−0.01537** (confirmation, split 41) at the primary budget, with **0 of 4** quadrants positive;
spring zones earned ~3× less hidden credit per emitted pixel than matched random (0.0122 vs
0.0320). Every arm (300 m/1 km/2 km haloes, 2–8 km pair corridors), every budget (5k/15k/45k)
and both splits agree. Mechanism and limitations:
[`docs/research/h32-01-vent-corridor-holdout.md`](research/h32-01-vent-corridor-holdout.md) ·
raw [`h32-01-vent-corridor-holdout.json`](research/h32-01-vent-corridor-holdout.json). The
catalogue proxy cannot clear H-32-04 (circularity); H-32-01 failed its gate and H-32-05 was later
measured negative. The reduced-stack H-31-02b scarp screen has also run and failed its primary
spatial/strike gates. Current untried options are listed in the active shortlist above; H-31-04 is
the lowest-cost next data check, not a promoted or validated candidate. No slot is justified.

**Status (measured 2026-10-03, third session): H-32-05 ran its preregistered gate and FAILED —
not promoted.** Preregistration frozen in
[`h32-05-preregistration.md`](research/h32-05-preregistration.md) before the run; harness
`scripts/basement_edge_holdout.py`; result
[`h32-05-basement-edge-holdout.md`](research/h32-05-basement-edge-holdout.md).

| Clause | Required | Measured | Verdict |
| --- | --- | --- | --- |
| Screen pooled Δ vs `random_near_matched` (N = 15,000, seed 31) | ≥ +0.002 | **−0.02614** | fail |
| Quadrant sign consistency | ≥ 3 / 4 | **0 / 4** | fail |
| Confirmation pooled Δ (seed 41) | > 0 | **−0.02591** | fail |
| Transform clause (edge > basement-depth magnitude, both splits) | > 0 | +0.00122 / +0.00345 | **pass** |

Primary arm 0.00283 DTI vs matched-random 0.02897 at N = 15,000 — roughly a 10× deficit. The
transform clause passing is the one durable finding: the **step geometry** of the basement surface
does carry more than its raw value, and `grav_edge_only` (0.00666) was the best of the four feature
arms, consistent with [USGS OFR 2005-1154](https://pubs.usgs.gov/of/2005/1154/of2005-1154.pdf)
(concealed basin faults mapped from horizontal gravity gradients). But the whole family sits far
below the random controls. **Design defect declared:** the preregistered `coherence ≥ 0.5` floor
accepted 99.65 % of footprint pixels (5,149,374 / 5,167,373), so the "must be an oriented linear
feature" clause never actually constrained the primary arm — the oriented-edge variant of H-32-05
remains untested.

**Three component-holdout falsifications (H-31-01, H-32-01, H-32-05) against the same
`random_near_matched` control (~0.029 DTI) motivated the H-33-01 placement-policy test; they did
not prove that all placement policies fail.** H-33-01's 80k gate was void because quota arms
collapsed to 68,573 in-domain dots against an 80,000-dot in-domain control. For the 40k sensitivity
result, the script constructs all model and random arms inside the scoring domain; the recorded
`dots` field is after outside-domain masking. The model and random arms are therefore active-domain
count matched at 40,000. Whole-domain score-first thinning (0.07608) exceeded each band-stratified
arm (0.0721–0.0725) and blind random by about 35%, while pure proximity ranking scored 0.03660.
This code-verified H-33-01 scope is distinct from the mismatches in the H-31-02b/archived novelty
screen (IR-30-033). Full details: [H-33-01 result](research/h33-01-placement-policy-holdout.md).

**H-33-01 decision: not promoted; placement-policy line closed for the registered design.** The
next registered experiment should change the lever (for example, score-field quality or an
independently preregistered hybrid) rather than retuning the same band allocation. The lowest-cost
untried geological data check in the current shortlist is H-31-04, radiometric K–Th–U unmixing;
this is a research priority, not evidence of expected gain. No slot is justified.
