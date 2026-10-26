# Official data-source availability check — 2026-10-26

This is a source/access check, not an experiment and not a validation result. Official-source pages were searched on 2026-10-26. The sandbox's shell transfer allowlist does not include USGS, TNM, or IHFC hosts, so no fresh official archive was downloaded in this turn. Existing owner mirrors are identified as mirrors, not official proof of provenance.

## GeoDAWN radiometrics — verified source; derived mirror restored

- **Official source:** [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), also indexed in the [USGS Data Catalog](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7). The USGS record identifies the public-domain release and describes magnetic/radiometric grids for the northwestern Great Basin.
- **Local access check:** restored `ext_geodawn_rad_u8` and `ext_geodawn_extensions_u8` from the exact owner-mirror pins in `docs/research/mirror-pins-extra.json` via `scripts/restore_public_mirrors.py`. Both SHA-256 pins passed. Each is a 4-band `uint8` GeoTIFF on the 3,730 × 3,292, EPSG:32611, 100 m grid.
- **Important limitation:** these are owner-derived 1st–99th-percentile quantisations, not the original USGS float grids. The source DOI is official; the quantisation, byte provenance, and preprocessing are owner-mirror claims. Do not treat the local restoration as USGS or organizer authentication. The exact local receipt is `geodawn-layer-restoration.json`.
- **Shortlist impact:** the byte-pinned layers are obtainable without a new transfer; a lithology-conditioned ratio test still needs the raw USGS grids or documented quantisation parameters before a quantitative log-ratio interpretation is defensible.

## USGS State Geologic Map Compilation (SGMC) — official packages obtainable; polygon inputs absent

- **Official source:** [USGS state geologic maps](https://mrdata.usgs.gov/geology/state/), including public Nevada and California archives; the USGS page lists map-unit lithology/age and the national SGMC data release, DOI 10.5066/F7WH2N65. The official downloads page lists Nevada and California packages and describes their GIS attributes.
- **Repository evidence:** `docs/sources.md` and the dated preflight records preserve prior public-runner transfers and SHA-256 checks for `NV.zip` (69,056,094 bytes) and `CA.zip` (24,977,406 bytes), checked 2026-10-03. This is historical access evidence, not a fresh transfer today.
- **Local availability:** this worktree contains a derived SGMC fault raster but not the original unit polygons/archives. The proposed concealment mechanism requires map-unit polygons and age/lithology attributes; the fault-line raster is not a substitute. An approved bridge/fresh official download is required before implementation.

## USGS National Map NHD / 3DEP — discoverable, full-ROI acquisition not verified

- **Official source:** [USGS The National Map products API](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=National%20Hydrography%20Dataset%20(NHD)%20Best%20Resolution&bbox=-119,38.5,-118.5,39). Existing repository source notes record 35 NHD products in a test bounding box and public download URLs, plus 3DEP products. The 3DEP source is public-domain USGS elevation data.
- **Unresolved availability:** the test query does not prove complete coverage of the competition footprint, viable clipped download sizes, or aligned NHD/DEM products. No full-footprint NHD/3DEP files are present here. Treat the drainage candidate as blocked—not runnable—until product IDs, complete coverage, byte hashes, license/attribution, conditioning, and alignment are checked.

## IHFC Global Heat Flow Database — download advertised; ROI power unknown

- **Official/community data source:** [IHFC release-2024 download page](https://www.ihfc-iugg.org/products/global-heat-flow-database/data) lists the 2024 xlsx/txt release at DOI [10.5880/fidgeo.2024.014](https://doi.org/10.5880/fidgeo.2024.014) and an IHFC-server backup. The current listing reports approximately 91,182 global points, including 54,553 continental points.
- **Unresolved availability:** no data file or ROI count was fetched in this turn. Fewer than roughly 50 in-footprint sites would make a site-level alignment test underpowered. In addition, the related `MT-HF-Saddle` family overlaps existing conductance/clay-cap/strain and heat-flow feature work, so it is not promoted as a genuinely untried candidate here.

## Submission-process sources

- [DrivenData problem specification, page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) is the organizer source for the metric and required prediction format.
- [NLR Official Rules PDF, OSTI 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) is the organizer's competition-rules source. The repository's 2026-10-25 live verification records the single final entry across prize phases and the weekly submission limit. The live submission page and any file-specific receipt were not checked in this review.
- A local validator only demonstrates checks encoded in this repository. It is **not** a DrivenData acceptance receipt. For this project, only a score copied from the official submission-page receipt may be called `ORGANIZER-CONFIRMED`.
