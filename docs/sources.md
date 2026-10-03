# Source register and verification notes

**Reviewed:** 2026-10-03 (UTC date; pages read in this session). “Verified” below means that the named page's text was retrieved and checked for the stated claim. It does not mean that a private dataset, linked archive, hidden label, score receipt, or external raster binary was downloaded or authenticated.

## Primary competition sources

| Source | Status and claim checked | Link for review |
| --- | --- | --- |
| DrivenData problem description, competition 306 / page 967 | Read the metric, training-data overview, and submission-format sections. It specifies a distance-weighted Tversky index, triangular 300 m support, 100 m pixels, `alpha=0.2`, `beta=0.8`; it requires one 32-bit-float prediction layer, same projected CRS/resolution/bounds as the training raster, and null/NaN outside bounds. | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DrivenData leaderboard | Read the live public table on 2026-10-03. The displayed #1 was DARD at 0.3195. The table also displayed `wbg1` at #15 with 0.2600. A leaderboard row alone does not identify a TIFF file from an unrelated GitHub Pages archive. | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| DrivenData competition data page | Direct fetch resolved to the DrivenData login page; no competition files were returned. This confirms the present sandbox is unauthenticated, not that the files are globally unavailable. | [Data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) |
| DrivenData Terms of Use | Read the prohibited-uses clause: it disallows using a robot, spider, or other automatic process to access the website, including for monitoring or copying. This project therefore does not implement an automated DrivenData leaderboard crawler. | [Terms of Use](https://www.drivendata.org/termsofuse/) |
| Official GEMS Prize Rules, NLR PDF, September 2026 | **Complete review:** all seven parsed chunks (0–6) were retrieved and reviewed on 2026-10-03; the full section-by-section checklist is [`research/official-rules-review-2026-10-03.md`](research/official-rules-review-2026-10-03.md). Verified eligibility/certification (§1.3/A.1–A.3), prize structure (§1.1), AI disclosure (§3.2), one-layer 100 m GeoTIFF and portal-format reference (§3.2–3.3), up to three weekly platform submissions and one final selection across both prize rounds (§3.4–3.6), finalist reproducibility (§3.5), DOE/public-use rights and third-party rights (Appendix A.4–A.5/A.10), and deadline time (Appendix A.1). The deadline clock conflicts with the homepage and requires organizer clarification. | [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| DrivenData competition homepage | Read the overview; it currently states a competition end of 2026-12-03 11:59 p.m. UTC and describes the two prize rounds. This differs in clock time from the rules PDF's Appendix A.1 5:00 p.m. ET; obtain organizer clarification before relying on a deadline. | [Competition homepage](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| DrivenData reference solution | Public GitHub repository landing page/README reviewed. It is an organizer-provided starting point; its existence is verified, but this session did not run its notebook or independently reproduce its model results. | [Reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) |

## Scientific and geospatial sources

| Source | Status and claim checked | Link for review |
| --- | --- | --- |
| USGS State Geologic Map Compilation (SGMC) | **Transferred and hash-verified 2026-10-03** by the repository's GitHub-runner bridge. `https://mrdata.usgs.gov/geology/state/shp/NV.zip` → 69,056,094 B, SHA-256 `3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b`; `CA.zip` → 24,977,406 B, SHA-256 `78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58`. Land management: US Government work / public domain (USGS Mineral Resources Program), nominal scales 1:24,000–1:250,000. The rasterised derivation (`data/external/derived_sgmc_faults_100m_u8.tif`, SHA-256 `26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c`) contains 21,160 fault features and 82,151 pixels inside the competition footprint; 61,664 of those pixels (75.1 %) are more than 300 m from any public-catalogue fault. Every byte, hash and stage is recorded in `data/external/external_receipt.json`. Direct download from this sandbox is blocked (`SSL_ERROR_SYSCALL`); the transfer happens on a GitHub Actions runner and the result is committed back to the repository. | [SGMC state maps index](https://mrdata.usgs.gov/geology/state/) · [ScienceBase all-state bundle](https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d) · [OGC WFS](https://mrdata.usgs.gov/services/wfs/sgmc2) |
| USGS GeoDAWN data release | USGS ScienceBase catalog record read. It identifies the release as airborne magnetic and radiometric data for northwestern Great Basin Nevada/California, publication date 2024-03-01, with DOI 10.5066/P93LGLVQ. The data describe survey methods and include geophysical grids. The catalog page was read. Owner-derived, quantised GeoDAWN bands are present locally via a pinned owner mirror, but the original survey tiles and a fully authenticated source-to-band lineage were not independently obtained; the local feature rasters are not organizer-authenticated. | [USGS ScienceBase record](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) · [DOI](https://doi.org/10.5066/P93LGLVQ) |
| INGENIOUS GDR 1391 | DOE Geothermal Data Repository record read. It explicitly says publicly accessible and displays a CC BY 4.0 license. Its catalog lists 2 m temperature probes, paleogeothermal features, Quaternary faults/volcanics, geodetic shear/dilation, seismicity, wells/springs, and other layers. The catalog lists downloadable ZIPs for [2 m temperature probes (1.03 MB)](https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip), [paleogeothermal features (82.04 kB)](https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip), and [Quaternary volcanics (9.44 MB)](https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip). A direct shell `curl --head --location` check from the agent sandbox failed with `SSL_ERROR_SYSCALL`, so the transfer was moved to a GitHub Actions runner: **on 2026-10-03 the bridge downloaded and hash-verified** `qfaults_ingenious_nad83conus117_2023-06-27.zip` (6,131,182 B, SHA-256 `c7b091c9…`), `paleo_geothermal_regional.zip` (84,008 B, `faffcf69…`), `great_basin_q_volcanics.zip` (9,898,770 B, `c4a2d2df…`) and `2m_temperature_probe_INGENIOUS_regional_data.zip` (1,080,530 B, SHA-256 `1301f70d…652eca3`); the paleo, volcanics, and 2 m probe layers rasterised to 244, 6,776, and 2,700 footprint pixels, respectively. The first derivation of the Ingenious Quaternary-fault v2 shapefile failed because its EPSG:32611 coordinates were incorrectly transformed as longitude/latitude; the CRS-ingestion defect is fixed (IR-30-034). The follow-up `data/external/external_receipt.partial.json` records a derived `data/external/derived_gdr_qfaults_v2_100m_u8.tif` (191,289 B, SHA-256 `82bdf4e6…ef701eb9`) with 1,117 in-grid features and 59,065 footprint pixels. Only 1 raster pixel lies >300 m from the catalogue, so this INGENIOUS/Qfaults layer is not independent truth. The canonical receipt retains the original failed derivation; the partial receipt is the follow-up derivation record. Full raw-download record: `data/external/external_receipt.json`. | [GDR 1391 record](https://gdr.openei.org/submissions/1391) · [DOI](https://doi.org/10.15121/1881483) |
| USGS Great Basin 3-D temperature model v1.1 | USGS Data Catalog page read. It identifies a 3-D temperature model, describes its modeling assumptions, gives DOI 10.5066/P149FR54, states public access and a U.S. public-domain license. This is a regional thermal prior, not a fault map; model grids were not downloaded here. | [USGS Data Catalog record](https://data.usgs.gov/datacatalog/data/USGS:65b3fe07d34e36a390458ce9) · [DOI/data](https://doi.org/10.5066/P149FR54) |
| USGS 3D Elevation Program (3DEP) | Cited by the competition's About page as the source of coordinated airborne LiDAR/surface topography; not used as evidence for a measured model gain in this repo. | [3DEP overview](https://www.usgs.gov/3d-elevation-program) |
| Siler, 2022, slip and dilation tendency | USGS ScienceBase/search metadata and the INGENIOUS GDR record identify this as a dataset calculating slip/dilation tendency for Great Basin Quaternary faults. It is candidate context for structural hypotheses, not proof that a new fault exists. | [USGS ScienceBase record](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) · [DOI 10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6) |
| Kervadec et al., boundary loss | arXiv record gives first submission 2018-12-17; PMLR lists the conference paper in MIDL 2019, volume 102, pp. 285–296. The paper argues that a boundary term complements regional losses and reports results on two imbalanced medical-segmentation datasets. It does **not** establish a gain for geological line mapping or the GEMS metric. | [PMLR paper](https://proceedings.mlr.press/v102/kervadec19a.html) · [arXiv record](https://arxiv.org/abs/1812.07032) |

## Owner-maintained result pages — secondary evidence, not official score receipts

| Page | What was read | Limitation |
| --- | --- | --- |
| GEMSDOE25 | Its landing page and executive-summary page offer the `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` and label it format-validated but unscored/not slot-approved. It gives a 44,090-pixel count and a truncated SHA-256 prefix. | Owner-maintained page, not DrivenData; exact score/file association is not verified. Its current status conflicts with the 0.2600 attribution supplied in the prompt. The exact local D2.8 NaN TIFF was downloaded through the public GitHub API and SHA-256 checked (`91eae1ca…bbe639b8`); the finite-zero diagnostic was generated locally (`b00a6fb6…df31a26`), preserves in-footprint values, passes only the strict all-finite diagnostic, and fails the published null/NaN-outside check. This verifies the local artifact, not its score attribution or organizer provenance. |
| GEMSDOE24 | Its landing page describes an H19-5 dotted candidate and an owner-reported 0.2477 score anchor; it also distinguishes model expectations from scores. | Owner-reported, no organizer receipt authenticated here. |
| GEMSDOE27 | Its public pages describe topology/gap-closure and catalogue-derived holdout work and explicitly call those proxy results, not hidden-test scores. | Owner-maintained and not independently rerun; useful as a novelty audit only. |

## Access and verification boundaries

- No DrivenData credentials were present, and no credential, cookie, account, or login bypass was attempted.
- Direct sandbox shell requests to the public GEMSDOE25/GEMSDOE27 TIFF hosts, Dropbox, and several direct GDR 1391 ZIP URLs failed with TLS connection errors (`SSL_ERROR_SYSCALL` for the GDR host). That records a limitation of this transfer path only: the D2.8 TIFF was obtained through the public GitHub API, and selected GDR 1391 archives were separately obtained and SHA-256 verified through a public GitHub Actions runner. No DrivenData competition archive was obtained; per-artifact access and remaining gaps are listed below.
- Access is verified per artifact, not by catalog page alone. A public GitHub Actions runner downloaded and SHA-256-verified the GDR 1391 Qfaults v2, paleogeothermal, Quaternary-volcanics, and 2 m-probe archives; the first Qfaults derivation was invalid because of a CRS-ingestion bug, now fixed (IR-30-034). The corrected Qfaults raster and its follow-up metadata are in `data/external/derived_gdr_qfaults_v2_100m_u8.tif` and `data/external/external_receipt.partial.json`; it has 59,065 in-footprint pixels, of which only 1 is >300 m from the catalogue. This source is therefore not independent truth even though it is now correctly rasterized. The canonical receipt preserves the initial failed derivation; do not conflate the two records. Paleo, volcanics, and probe layers rasterized to 244, 6,776, and 2,700 footprint pixels. Chemistry CSV lineage, GeoDAWN original tiles, full 3DEP/NHD coverage, and all use-specific licensing/attribution conditions remain gates before the corresponding experiments.
- Current leaderboard values are snapshots only. DrivenData's Terms of Use prohibit automated monitoring/copying, so no scheduled scraper is included. The live leaderboard page is the source of record when reviewed through an authorized, permitted route.

## Owner-side knowledge documents (fetched 2026-10-03, owner-reported only)

The following documents were fetched from the public GitHub mirror
`github.com/buffedlizard55-lab/GEMSDOE25` → `knowledge/` via the GitHub API on 2026-10-03 and are
treated as **owner-reported prior work, not independently verified and not competition receipts**:

* `12_h30_relay_factorial_outcomes_2026-10-03.md` — H30-1 paired relay × terrain factorial: screen
  +0.004078 (4/4 folds) PASS → fresh-draw confirmation −0.001275 (1/4 folds) FAIL → "Stop this
  candidate"; no full-data TIFF or slot.
* `07_findings_2026-10-02.md` — fractional factorial 2^(5−1) (E catalogue +0.0610 4/4; B DEM
  curvature/scarp +0.0253 4/4; D thermal/geochemical +0.0044 4/4; A potential field −0.0027 1/4;
  C strain/seismicity −0.0109 0/4); add-on conjunction X1+X2+X3 passing both replicates (+0.0050,
  +0.0038); emission sweeps selecting score-ordered ≈2.4 px dots at ≈2.45–3.5 % share; the root-cause
  inference that the reported "[0,1]" portal error came from a file that was NaN over roughly 2.34 M
  of the 5.17 M footprint pixels.
* Related docs listed but not yet read in full: `09_preregistered_hypotheses_2026-10-02.md`,
  `10_preregistered_h28_live_anchored_emission_design_2026-10-02.md`,
  `current_project_brief_2026-10-03.md`, `03_hypotheses_ranked_2026-10-02.md`,
  `06_geothermal_research_digest_2026-10-02.md`, `owner_brief_verbatim.txt`.

These inform (but never replace) this repository's own holdout evidence; where the two disagree, the
local measured result and the official sources win. Cross-check recorded in
[`hypotheses.md`](hypotheses.md).

## Addendum — 2026-10-03 second session verification (all read this session)

### Official rules PDF — complete review (fetch tool, all seven chunks 0–6 of 7)

[`https://docs.nlr.gov/docs/fy26osti/96647.pdf`](https://docs.nlr.gov/docs/fy26osti/96647.pdf) —
"Geologic Enhanced Mapping System (GEMS) Prize Official Rules, September 2026". All seven
parsed chunks were retrieved and reviewed on 2026-10-03; see the full section-by-section
[`official-rules-review-2026-10-03.md`](research/official-rules-review-2026-10-03.md). The host
`docs.nlr.gov` is the prize administrator's domain (National Laboratory of the Rockies), not a
typo for NREL (a `docs.nrel.gov` fetch failed). Verified facts:

| Rules claim | Section | Use in this project |
| --- | --- | --- |
| Training labels "obtained from the INGENIOUS project's Great Basin Regional Dataset Compilation" (DOI [10.15121/1881483](https://doi.org/10.15121/1881483)) | §3.3 + footnote 4 | catalogue provenance; what the metric masks |
| Label universe also includes "newly identified faults labeled by geology experts at [NLR] and USGS" and the USGS Quaternary Fault and Fold Database | §2 | hidden-test population definition |
| Feature data = GeoDAWN (DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) + USGS 1 m DEM; "instructions … for downloading USGS DEM elevation data at 1-m resolution" | §2, §3.3 | 3DEP external-data plan |
| Metric "penalizes false negatives … more than false positives" | §3.6.1 | α=0.2/β=0.8 reading |
| "up to three [submissions] per week"; exactly one final submission chosen without private-score knowledge; evaluated in both prize rounds | §3.4, §3.6.2 | slot discipline |
| Finalists submit "complete code assets and documentation" that reproduce results | §3.5 | repository auditability |
| Generative-AI use must be disclosed in the narrative | §3.2 | `ai-disclosure-draft.md` |
| Phase 1 = $50,000 split equally among top 5 (private withheld subset); Phase 2 = $250,000 (1st $100k … 5th $15k) on the expert-updated label set | §1.1 | Phase-2 realism strategy |
| Deadline "5:00 p.m. ET on the … deadline date" (Appendix A.1) | A.1 | deadline-discrepancy irregularity |
| Eligibility: U.S. citizens/permanent residents; U.S. entities/academics; FFRDC/DOE/FCOC/MFTRP exclusions; under-18 ineligible; certification under penalty of perjury | §1.3 | entrant must verify eligibility before any entry |

### Leaderboard snapshot read 2026-10-03 (one-time research read; no monitoring)

[`Leaderboard`](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/):
rank 1 **DARD 0.3195** (12 submissions), rank 2 nchuzhoy 0.3128, rank 3 alexoktaba 0.3042,
rank 4 Batik Shirt Brothers 0.2998, rank 5 xiaofanhu 0.2941, …, rank 15 **wbg1 0.2600**
(9 submissions). Rows are participants' best public DW-Tversky scores — no filenames or hashes.
Recorded in `score-ledger.csv` with `evidence_class=official-snapshot`.

### DOE/OSTI geothermal structural literature (fetched 2026-10-03)

| Source | Verified content used |
| --- | --- |
| [Faulds et al., Structural investigations of Great Basin geothermal fields (OSTI 1110517)](https://www.osti.gov/servlets/purl/1110517) | step-overs/terminations/intersections host most systems; Quaternary faults dominate; exploration should target those geometries |
| [Faulds, Structural inventory of 426 systems (OSTI 1148722)](https://www.osti.gov/dataexplorer/biblio/dataset/1148722) | step-overs/relay ramps ~32 %; ~39 % blind (up to 75 % of resources); Quaternary faults near most systems |
| [Faulds et al., Discovering new geothermal systems (OSTI 1724109)](https://www.osti.gov/servlets/purl/1724109) | outflow can surface km from source; linear tufa towers mark the blind Pyramid Lake system along dextral-normal faults |
| [GDR 616 Nevada Play Fairway data](https://gdr.openei.org/submissions/616) | free structural/strain/seismicity/spring/favorability layers |
| [GDR 1486 GBCGE subsurface database](https://gdr.openei.org/submissions/1486) | NBMG/UNR well+spring+structural-setting database (provenance of the local wellspring mirror) |

### Corrections to earlier rows in this file

* An earlier draft said the D2.8 TIFF bytes were unavailable in this sandbox. That draft claim
  was superseded by the 2026-10-03 GitHub-API retrieval and is corrected in the current GEMSDOE25
  table above: the NaN artifact hash was checked; its local zero-outside diagnostic preserves the
  same in-footprint values (44,090 binary dots) and passes the separate all-finite diagnostic, but
  fails the published null/NaN-outside format check. This does not verify who uploaded that exact
  file or which official score, if any, belongs to it.
* The GEMSDOE25 landing page reports its own range-error inference: NaNs inside that project's file may have triggered the message; it explicitly says the portal validator is not public. This owner-side statement is not confirmation of this repository's prior error cause. The public GEMS problem description requires null/NaN outside; the local zero-outside copies are now recorded as nonstandard diagnostics, fail the published-format outside check, and are not linked as submission-format downloads. The exact prior-error file remains unidentified, and no local check establishes portal acceptance.

## Addendum — 2026-10-03, session 30 (new sources checked for the H-34 hypothesis register)

| Source | Status and claim checked | Link for review |
| --- | --- | --- |
| USGS Mineral Resources On-Line Spatial Data — geologic maps of US states (SGMC) | Read the index page this session. It states the compilation provides "digital geologic maps of the US states with consistent lithology, age, GIS database structure, and format", published by the USGS Mineral Resources Program, with per-state shapefile+CSV packages and an OGC WFS endpoint, and a national all-states bundle on ScienceBase. Licence: US Government work (public domain). This matters for **H-34-01**: the *polygon* attributes (age + lithology per map unit) are what a concealment prior needs, and the repository currently rasterises only the fault *linework* from these same archives. The per-state archives `NV.zip` (69,056,094 B) and `CA.zip` (24,977,406 B) are already downloaded and SHA-256-verified inside this repository via the Actions bridge. | [SGMC index](https://mrdata.usgs.gov/geology/state/) · [National bundle](https://www.sciencebase.gov/catalog/file/get/5888bf4fe4b05ccb964bab9d?name=USGS_SGMC_Geodatabase.zip) · [WFS capabilities](https://mrdata.usgs.gov/services/wfs/sgmc2?service=WFS&request=GetCapabilities&version=1.1.0) |
| USGS GeoDAWN airborne magnetic and radiometric release (DOI 10.5066/P93LGLVQ) | ScienceBase record read this session. Verified verbatim claims used by **H-34-02**: the survey supports "geologic and geophysical mapping and modeling that will assist geothermal and critical mineral studies", spans 149,030 line-km over 51,857 km² of the Walker Lane / western Great Basin (Nevada and eastern California), was acquired 2021-11-01 to 2022-11-20 under EarthMRI with DOE/GTO support, and the release "included … geoTIFF images of geophysical grids", contractor reports, magnetic and radiometric grids, and flight-path shapefiles. Publication date 2024-03-01. Licence: US Government work (public domain). Access from this sandbox is blocked (TLS `SSL_ERROR_SYSCALL`); the repository's proven transfer path is the GitHub Actions bridge. Owner-derived quantised GeoDAWN bands are present locally but their source-to-band lineage is not independently authenticated. | [ScienceBase record](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) · [DOI](https://doi.org/10.5066/P93LGLVQ) |
| USGS The National Map (TNM) Products API — 3DEP and NHD | Query executed this session against the public product API for a test bbox inside the competition footprint (`-119,38.5,-118.5,39`, dataset `National Hydrography Dataset (NHD) Best Resolution`). The API returned 35 product records with direct public download URLs on `prd-tnm.s3.amazonaws.com`, including the national NHD FileGDB (31,436,969,083 B) and the California state FileGDB (982,386,104 B), published 2025-09-18 and 2023-12-27 respectively. This is what **H-34-03** needs (flowlines) alongside 3DEP elevation products; both are US public-domain. Verified obtainability, but the ROI-clipped product has not been transferred, checksummed or aligned in this repository, so H-34-03 is registered as *not runnable yet*. | [TNM Products API query](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=National%20Hydrography%20Dataset%20(NHD)%20Best%20Resolution&bbox=-119,38.5,-118.5,39) · [TNM API docs](https://tnmaccess.nationalmap.gov/api/v1/docs) · [3DEP](https://www.usgs.gov/3d-elevation-program) |
| IHFC Global Heat Flow Database (release 2024) | Read this session. Verified: the database "contains about 91,182 data points from 1,586 publications (54,553 from the continental domain and 36,629 from the oceanic domain; status: release 2024)", is maintained by the International Heat Flow Commission of IASPEI, documents its quality assessment in doi:10.1016/j.tecto.2023.229976 (49 % of data re-assessed in 2024), and is downloadable as xlsx/csv from GFZ Data Services (DOI 10.5880/fidgeo.2024.014) with an IHFC-server backup. Reuse terms are set by the GFZ data-services record (not re-read here). Relevance: **H-34-04** heat-flow anomaly/alignment evidence, and the required power check (Nevada site density) — this session did **not** count the ROI sites, so H-34-04 remains conditional. | [IHFC database](https://ihfc-iugg.org/products/global-heat-flow-database) · [Data download page](https://ihfc-iugg.org/products/global-heat-flow-database/data) · [Release 2024 DOI](https://doi.org/10.5880/fidgeo.2024.014) |

**What was not verified this session.** No organizer data file was downloaded (the competition data tab
still resolves to a login page); no leaderboard change was read; no new external archive was
transferred (the SGMC, GDR and GeoDAWN archives above were already on disk from earlier sessions);
the H-34-03 and H-34-04 gridded products have not been clipped, transferred, checksummed or aligned,
and neither hypothesis may be run before that happens.

