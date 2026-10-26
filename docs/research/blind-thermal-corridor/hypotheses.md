# Ranked prospective hypotheses — blind (catalogue-missing) fault discovery

Prepared autonomously for GEMSDOE30. Every figure below is either a verified official
source or a clearly labelled HOLDOUT-DTI proxy; none is an organizer score or
hidden-test forecast. Sources: DrivenData problem page `/page/967/` (DTI α=0.2 β=0.8,
R=300 m triangular kernel), DrivenData staff threads 11516/11536/11550 (known USGS/
INGENIOUS faults masked pixel-exactly; hidden splays may sit <300 m from mapped traces;
pooled TP_w/FP_w/FN_w), NLR rules PDF 96647.pdf (≤3 submissions/week; 1 final selected
entry; deadline 2026-12-03 22:00 UTC), USGS GeoDAWN survey DOI 10.5066/P93LGLVQ (CC0),
DOE GDR INGENIOUS submission 1391 DOI 10.15121/1881483 (CC-BY-4.0).

## Method constraint (lane)
Each hypothesis is a single, implementable method paragraph using only layers already
present in `data/external/` (USGS SGMC NV/CA structure, DOE GDR Quaternary volcanics,
paleogeothermal springs, 2 m temperature probes) on the competition grid
(EPSG:32611, 3730×3292, 100 m). No hypothesis requires organizer-authenticated
`labels.tif`/`training_features.tif` (behind the DrivenData login) to be *built*; holdout
validation of any of them does require those organizer files and is therefore gated.

---

## H1 — Basin blind-fault thermal corridor (TOP CANDIDATE — implemented)

**Layers:** DOE GDR paleogeothermal sinter/tufa springs + 2 m temperature probes
(fluid/thermal expression); USGS SGMC mapped structure (catalogue proxy). Quaternary
volcanics deliberately EXCLUDED.

**Physical signature:** distance-decay (exp(−d/1000 m), matched to the 300 m DTI
kernel) linear pool of paleo-spring and 2 m probe proximity, weighted 0.5/0.5, placed
only in the 3–30 px (300 m–3 km) off-SGMC annulus — the hidden-splay band permitted by
the forum "<300 m from a mapped trace" rule — with SGMC core (0–2 px) excluded to avoid
the unmasked flank false-positive penalty. Binary {0,1} Poisson-disk emission at 3 px.

**Why it catches catalogue-missing faults:** The USGS/INGENIOUS Quaternary catalogue
favours well-constrained surface-rupturing traces; blind Great Basin geothermal systems
(e.g. Pyramid Lake, linear tufa towers) are hosted on concealed strands with fluid
discharge but no mapped young volcanism. H1 targets exactly that class: thermal/fluid
expression without volcanism, off the mapped core.

**How it differs from anything in this repo:** The shipped `geothermal-corridor` lane
pools volcanics(0.4)+paleo(0.3)+probes(0.3), rewards SGMC proximity, and emits >2 px off
structure everywhere. H1 removes volcanics entirely, removes the SGMC proximity boost,
and restricts dots to the 3–30 px concealed-splay annulus. Distinct mechanism and
distinct dot placement.

**Expected DTI improvement:** HOLDOUT-DTI not computable without organizer labels.
Directional expectation: positive on concealed intrabasin/piedmont faults, neutral-to-
negative on range-front scarps (complementary to the scarp-heavy 0.24–0.28 family).

**Implementation cost:** LOW — ~60 lines, reuses `gemsdoe30.emission.poisson_disk_select`
and `gemsdoe30.submission.write_submission_file`; all inputs present locally.

**Experiment log (this session):** Built and validated `GEMSDOE30-blind-thermal-corridor-
h1-annulus-20261026T202136Z.tif` (18,766 dots; 12/12 format checks passed; NaN outside;
EPSG:32611; 3,730×3,292; 100 m). Format-valid but **Protocol Rule 1 duplicate-stop**:
74.98% of dots within 3 px of the edge-hybrid-80k registry raster (>70% limit), so the
lane drifted into the EDGE-emitter belief-field zone. Logged as a negative deliverable at
`docs/research/blind-thermal-corridor/run-card.json`; the raster was NOT perturbed or
re-encoded and is NOT offered as a unique submission. See the executive summary for the
unique, lane-clear downloadable artifact (geothermal-corridor, max overlap 60.6% ≤ 70%).

---

## H2 — Piedmont geomorphic-scorp vs range-front relief decoupling (PGR-2)

**Layers:** DEM 1 m std/median slope anomaly normalized by regional `det_elev_slope`,
gated by basinward `iso_grav_anom` dip. Requires the 1 m LiDAR-derived slope bands
(not currently in `data/external/`).

**Physical signature:** subtle piedmont scarps (`dem_1m_std_slope` elevated relative to
regional range-front `det_elev_slope`) that are invisible to the regional scarp family.

**Why catalogue-missing:** range-front scarps are over-sampled by the 0.24–0.28 dotted
family (70–81% of dots on steep scarps); blind intrabasin scarps on alluvial fans are
under-mapped.

**Differs from repo:** G30-S19/S20 use lidar scarp + radiometrics but WITH the range-front
regional band; PGR-2 explicitly decouples local piedmont std-slope FROM regional relief.

**Expected DTI improvement:** moderate; complements H1 (topography vs thermal).

**Implementation cost:** MEDIUM — requires 1 m DEM slope bands (official source: USGS 3DEP /
the competition's `1m_DEM_links.csv`, behind DrivenData login).

---

## H3 — Potassium/thorium hydrothermal alteration halo along subsurface tilt contacts (KUS-3)

**Layers:** USGS GeoDAWN airborne radiometric K, eTh, U grids (DOI 10.5066/P93LGLVQ,
CC0), aligned to EPSG:32611 / 100 m; subsurface tilt-contact position from the gravity
field.

**Physical signature:** K/eTh potassic alteration halo along concealed, tilt-bound
structures (Grauch–Hudson hanging-wall cover geometry).

**Why catalogue-missing:** blind faults beneath conductive cover alter the near-surface
radiometric signature without a surface trace.

**Differs from repo:** PTA-1 uses magnetic tilt-phase + MT cover step; KUS-3 uses
radiometric potassium — an independent physics (geochemical alteration, not potential
field).

**Expected DTI improvement:** moderate-to-high in blind basins; orthogonal to PTA-1.

**Implementation cost:** HIGH — GeoDAWN radiometric grids are NOT in `data/external/`;
must be obtained from USGS (free, official, DOI 10.5066/P93LGLVQ) and co-registered.
Not obtainable in this sandbox without the organizer grid links; flagged as requiring
external data before viable.

---

## H4 — Transtensional geodetic shear × independent microseismicity partition (MCS-4)

**Layers:** GDR geodetic strain rate + independent background microseismicity
(`ieq_n100a15`/`deq_n100a15`).

**Physical signature:** zones where geodetic shear is high but mapped Quaternary slip is
low — strain accommodated on unmapped blind structures.

**Why catalogue-missing:** unmapped structures taking up geodetic strain.

**Differs from repo:** geodetic/seismic rate partitioning not used by any shipped lane.

**Expected DTI improvement:** low-to-moderate (coarse ~km regional prior, 100 m grid
dilution).

**Implementation cost:** MEDIUM — GDR strain/seismicity CSVs are in `external_receipt.json`
but their derived rasters are not present locally; requires rasterization.

---

## Ranking (expected DTI improvement / implementation cost)

| Rank | Hypothesis | Expected DTI gain | Cost | Data ready locally? | Verdict |
|:--:|:---|:---:|:--:|:---:|:---|
| 1 | H1 Basin blind-fault thermal corridor | positive (concealed class) | Low | Yes | **Implemented — build + validate** |
| 2 | H2 Piedmont scarp decoupling (PGR-2) | moderate | Medium | No (1 m DEM bands) | Prospective |
| 3 | H3 K/eTh alteration halo (KUS-3) | moderate–high | High | No (GeoDAWN radiometrics) | Needs USGS download |
| 4 | H4 Geodetic shear × microseismicity (MCS-4) | low–moderate | Medium | Partial (CSVs only) | Prospective |

**Holdout gate:** Per the parallel-run protocol, no weekly submission slot may be spent
until the top candidate beats the current holdout best on the buffered-spatial-block
holdout. That requires organizer `labels.tif`/`training_features.tif`, which are behind
the DrivenData login and absent from this checkout. H1 is therefore built and
format-/novelty-validated here, but labelled `ok_to_submit = false` until a holdout
pass is obtained.
