# Source register and verification notes

**Reviewed:** 2026-10-03 (UTC date; pages read in this session). “Verified” below means that the named page's text was retrieved and checked for the stated claim. It does not mean that a private dataset, linked archive, hidden label, score receipt, or external raster binary was downloaded or authenticated.

## Primary competition sources

| Source | Status and claim checked | Link for review |
| --- | --- | --- |
| DrivenData problem description, competition 306 / page 967 | Read the metric, training-data overview, and submission-format sections. It specifies a distance-weighted Tversky index, triangular 300 m support, 100 m pixels, `alpha=0.2`, `beta=0.8`; it requires one 32-bit-float prediction layer, same projected CRS/resolution/bounds as the training raster, and null/NaN outside bounds. | [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| DrivenData leaderboard | Read the live public table on 2026-10-03. The displayed #1 was DARD at 0.3195. The table also displayed `wbg1` at #15 with 0.2600. A leaderboard row alone does not identify a TIFF file from an unrelated GitHub Pages archive. | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| DrivenData competition data page | Direct fetch resolved to the DrivenData login page; no competition files were returned. This confirms the present sandbox is unauthenticated, not that the files are globally unavailable. | [Data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) |
| DrivenData Terms of Use | Read the prohibited-uses clause: it disallows using a robot, spider, or other automatic process to access the website, including for monitoring or copying. This project therefore does not implement an automated DrivenData leaderboard crawler. | [Terms of Use](https://www.drivendata.org/termsofuse/) |
| Official GEMS Prize Rules, NLR PDF, September 2026 | Read the relevant sections. §3.2 allows generative AI but requires a narrative description of extent and use; §3.3 describes 100 m multiband features, labels, and the GeoTIFF example; §3.4 permits up to three platform submissions per week and requires one final submission; §3.5 requires one selected final submission for both prize rounds. Appendix A.1 states a 5:00 p.m. ET deadline time. | [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |
| DrivenData competition homepage | Read the overview; it currently states a competition end of 2026-12-03 11:59 p.m. UTC and describes the two prize rounds. This differs in clock time from the rules PDF's Appendix A.1 5:00 p.m. ET; obtain organizer clarification before relying on a deadline. | [Competition homepage](https://www.drivendata.org/competitions/306/competition-doe-gems/) |
| DrivenData reference solution | Public GitHub repository landing page/README reviewed. It is an organizer-provided starting point; its existence is verified, but this session did not run its notebook or independently reproduce its model results. | [Reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution) |

## Scientific and geospatial sources

| Source | Status and claim checked | Link for review |
| --- | --- | --- |
| USGS State Geologic Map Compilation (SGMC) | **Transferred and hash-verified 2026-10-03** by the repository's GitHub-runner bridge. `https://mrdata.usgs.gov/geology/state/shp/NV.zip` → 69,056,094 B, SHA-256 `3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b`; `CA.zip` → 24,977,406 B, SHA-256 `78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58`. Land management: US Government work / public domain (USGS Mineral Resources Program), nominal scales 1:24,000–1:250,000. The rasterised derivation (`data/external/derived_sgmc_faults_100m_u8.tif`, SHA-256 `26d142c4c93282cd94f6950ab96f22aeff59fbbea523d43d662e76fa1b161b5c`) contains 21,160 fault features and 82,151 pixels inside the competition footprint; 61,664 of those pixels (75.1 %) are more than 300 m from any public-catalogue fault. Every byte, hash and stage is recorded in `data/external/external_receipt.json`. Direct download from this sandbox is blocked (`SSL_ERROR_SYSCALL`); the transfer happens on a GitHub Actions runner and the result is committed back to the repository. | [SGMC state maps index](https://mrdata.usgs.gov/geology/state/) · [ScienceBase all-state bundle](https://www.sciencebase.gov/catalog/item/5888bf4fe4b05ccb964bab9d) · [OGC WFS](https://mrdata.usgs.gov/services/wfs/sgmc2) |
| USGS GeoDAWN data release | USGS ScienceBase catalog record read. It identifies the release as airborne magnetic and radiometric data for northwestern Great Basin Nevada/California, publication date 2024-03-01, with DOI 10.5066/P93LGLVQ. The data describe survey methods and include geophysical grids. No files were downloaded into this checkout. | [USGS ScienceBase record](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7) · [DOI](https://doi.org/10.5066/P93LGLVQ) |
| INGENIOUS GDR 1391 | DOE Geothermal Data Repository record read. It explicitly says publicly accessible and displays a CC BY 4.0 license. Its catalog lists 2 m temperature probes, paleogeothermal features, Quaternary faults/volcanics, geodetic shear/dilation, seismicity, wells/springs, and other layers. The catalog lists downloadable ZIPs for [2 m temperature probes (1.03 MB)](https://gdr.openei.org/files/1391/2m_temperature_probe_INGENIOUS_regional_data.zip), [paleogeothermal features (82.04 kB)](https://gdr.openei.org/files/1391/paleo_geothermal_regional.zip), and [Quaternary volcanics (9.44 MB)](https://gdr.openei.org/files/1391/great_basin_q_volcanics.zip). A direct shell `curl --head --location` check from the agent sandbox failed with `SSL_ERROR_SYSCALL`, so the transfer was moved to a GitHub Actions runner: **on 2026-10-03 the bridge downloaded and hash-verified** `qfaults_ingenious_nad83conus117_2023-06-27.zip` (6,131,182 B, SHA-256 `c7b091c9…`), `paleo_geothermal_regional.zip` (84,008 B, `faffcf69…`), `great_basin_q_volcanics.zip` (9,898,770 B, `c4a2d2df…`) and `2m_temperature_probe_INGENIOUS_regional_data.zip`; the paleo layer rasterised to 244 px and the volcanics to 6,776 px inside the footprint. The Ingenious Quaternary-fault v2 shapefile downloaded but rasterised to **zero** features because no feature intersected the grid — flagged as an open irregularity (CRS/projection mismatch suspected) and not used. Full record: `data/external/external_receipt.json`. | [GDR 1391 record](https://gdr.openei.org/submissions/1391) · [DOI](https://doi.org/10.15121/1881483) |
| USGS Great Basin 3-D temperature model v1.1 | USGS Data Catalog page read. It identifies a 3-D temperature model, describes its modeling assumptions, gives DOI 10.5066/P149FR54, states public access and a U.S. public-domain license. This is a regional thermal prior, not a fault map; model grids were not downloaded here. | [USGS Data Catalog record](https://data.usgs.gov/datacatalog/data/USGS:65b3fe07d34e36a390458ce9) · [DOI/data](https://doi.org/10.5066/P149FR54) |
| USGS 3D Elevation Program (3DEP) | Cited by the competition's About page as the source of coordinated airborne LiDAR/surface topography; not used as evidence for a measured model gain in this repo. | [3DEP overview](https://www.usgs.gov/3d-elevation-program) |
| Siler, 2022, slip and dilation tendency | USGS ScienceBase/search metadata and the INGENIOUS GDR record identify this as a dataset calculating slip/dilation tendency for Great Basin Quaternary faults. It is candidate context for structural hypotheses, not proof that a new fault exists. | [USGS ScienceBase record](https://www.sciencebase.gov/catalog/item/6296974dd34ec53d276bb33d) · [DOI 10.5066/P9YL58W6](https://doi.org/10.5066/P9YL58W6) |
| Kervadec et al., boundary loss | arXiv record gives first submission 2018-12-17; PMLR lists the conference paper in MIDL 2019, volume 102, pp. 285–296. The paper argues that a boundary term complements regional losses and reports results on two imbalanced medical-segmentation datasets. It does **not** establish a gain for geological line mapping or the GEMS metric. | [PMLR paper](https://proceedings.mlr.press/v102/kervadec19a.html) · [arXiv record](https://arxiv.org/abs/1812.07032) |

## Owner-maintained result pages — secondary evidence, not official score receipts

| Page | What was read | Limitation |
| --- | --- | --- |
| GEMSDOE25 | Its landing page and executive-summary page offer the `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` and label it format-validated but unscored/not slot-approved. It gives a 44,090-pixel count and a truncated SHA-256 prefix. | Owner-maintained page, not DrivenData; exact score/file association is not verified. Its current status conflicts with the 0.2600 attribution supplied in the prompt. The TIFF bytes were not downloaded or independently inspected in this sandbox. |
| GEMSDOE24 | Its landing page describes an H19-5 dotted candidate and an owner-reported 0.2477 score anchor; it also distinguishes model expectations from scores. | Owner-reported, no organizer receipt authenticated here. |
| GEMSDOE27 | Its public pages describe topology/gap-closure and catalogue-derived holdout work and explicitly call those proxy results, not hidden-test scores. | Owner-maintained and not independently rerun; useful as a novelty audit only. |

## Access and verification boundaries

- No DrivenData credentials were present, and no credential, cookie, account, or login bypass was attempted.
- Shell HTTPS transfer attempts to the public GEMSDOE25/GEMSDOE27 TIFF hosts, Dropbox, and three direct GDR 1391 ZIP URLs failed with TLS connection errors (`SSL_ERROR_SYSCALL` for the GDR host). The web-page tool could retrieve the GDR catalog text and resource links but did not provide the archive bytes. Therefore no owner-hosted TIFF's pixel values/geotransform/checksum/score receipt, and no GDR archive checksum/schema/alignment, are independently verified in this checkout.
- The public GDR and USGS catalog pages exposed license/access statements and archive/DOI links. Actual binary downloads, checksums, spatial alignment, and license compatibility with every proposed use remain explicit preconditions for those external-data experiments.
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

### Official rules PDF read line-by-line (fetch tool, chunks 0–3 of 7)

[`https://docs.nlr.gov/docs/fy26osti/96647.pdf`](https://docs.nlr.gov/docs/fy26osti/96647.pdf) —
"Geologic Enhanced Mapping System (GEMS) Prize Official Rules, September 2026". The host
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

* The row "The TIFF bytes were not downloaded or independently inspected in this sandbox" is
  **superseded**: the D2.8 NaN variant and the GEMSDOE25 zeros variant were downloaded via the
  GitHub API on 2026-10-03 and inspected pixel-by-pixel (see
  `docs/downloads/gems24-h25-1-…-zeros.json`; in-footprint bytes identical; 0/1 binary;
  44,090 dots; NaN/0 outside conventions characterized). Score attribution remains unresolved.
* The GEMSDOE25 landing page (fetched 2026-10-03) states its own range-error root-cause
  inference — "The earlier range error was caused by NaNs inside the footprint (inferred from
  the file; the portal validator is not public)" — and publishes a zeros-outside fallback. This
  corroborates this repository's `[0, 1]` portal-safe fix, independently arrived at.
