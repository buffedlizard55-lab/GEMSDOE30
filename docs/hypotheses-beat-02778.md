# Candidate geological hypotheses to beat 0.2778 (untried, ranked)

**Context.** The h19-5 family dominates GEMSDOE24/25/27/28/30/31/32/33/36
(owner-reported 0.1922 → 0.2600 → 0.2708 → 0.2778 → 0.2750). Every step adds
**zero new dots** — each step only removes dots within 1–2 px of catalogue
faults. The gain is "denominator hygiene" (alpha=0.2 FP-mass reduction), not
recovery of any concealed fault. The pruning ceiling is exhausted.

**The requirement to beat 0.2778:** recall concealed faults. In the
distance-weighted Tversky metric (alpha=0.2, beta=0.8, R=300 m triangular
kernel), false negatives carry 4× the weight of false positives. A submission
that only prunes catalogue-proximal dots can never exceed the pruning ceiling;
it must place dots where new, unmapped fault geometry actually exists.

Below are **five hypotheses** never tried in this repo or on any priority site.
Each names: specific layer(s), physical signature, why it catches faults absent
from the USGS/INGENIOUS catalogue, how it differs from prior work, expected
DTI gain (planning prior, not a score), and implementation cost. **None has
been holdout-validated in this checkout; none may consume a weekly submission
slot until it passes the holdout gate (paired 95% CI lower bound > 0 vs
control on two seeds) and both novelty stages.**

---

## H-1 · Step-over / relay-ramp connector completion (rank 1)

**Layers:** competition `det_elev`, `tmi_hg`; LiDAR scarp channels
`step_max`, `cross_max`, `strike` (all local, SHA-256 pinned). Catalogue
geometry used only as geometry (to define mapped strands), not as emission
target.

**Physical signature:** pairs of sub-parallel lineament terminations (azimuth
within ~20°, separation 0.3–3 km, along-strike overlap) plus the connector
segment between them. Dots are placed on the unmasked pixels *between* mapped
strands, not adjacent to them.

**Why it catches catalogue-absent faults:** Extensional step-overs and relay
ramps host short, oblique breaching strands. Field mapping campaigns record the
two long boundary strands and routinely omit the short connector. The
USGS/INGENIOUS catalogue is therefore systematically incomplete precisely in
this domain. Staff on the competition have explicitly ruled that such connectors
count as new faults.

**How it differs from prior work:** Prior registers test scalar fields (thermal
points, strain×conductance, seismicity density, 3-D temperature) or multiline
density corroboration / ridge-top gap closure. None pairs lineament
terminations or tests along-strike overlap geometry. Closest disclosed prior:
GEMSDOE27 "topo-gap-closure" (owner-reported 0.2449), which bridges gaps in a
scalar ridge surface without pairing constraints. This repo's own
`relay_connector_holdout.py` tested a proximity-dilation variant on the real
catalogue and found only +1.2% credit per pixel over a proximity-matched
control — too small to separate from draw noise; this hypothesis uses a
*relational* pairing constraint (two terminations + overlap), which is a
different feature family.

**Expected ΔDTI / cost:** +0.005…+0.030 planning prior, moderate confidence;
**medium cost** — all inputs already local, CPU-feasible.

**Official source / access:** Competition raster via authorized DrivenData
session or pinned owner mirror (not organizer-authenticated). LiDAR scarp
features derive from USGS 3DEP 1 m DEM (public domain per USGS). No new
external transfer needed.

**Falsifiable gate:** Hide whole catalogue components; build the connector map
from known traces only; score on hidden components with the exact masked
distance-weighted Tversky. Require pooled ΔDTI ≥ +0.005 over the same-run
no-connector control, ≥3/4 positive folds, fresh-seed replication.

**Status:** A proximity-dilation variant was tested 2026-10-03 and not
promoted. The relational pairing variant is **untried**.

---

## H-2 · Matched-filter scarp bank on USGS 3DEP 1 m DEM (rank 2)

**Layers:** USGS 3DEP 1 m DEM tiles (public domain).

**Physical signature:** oriented, scale-selected step matched filters for
0.5–5 m fault scarps, followed by a continuity tracker that links scarp
segments across gaps at a fixed strike tolerance. Output: scarp-likelihood
raster at 100 m, aggregated to the competition grid.

**Why it catches catalogue-absent faults:** Short, discontinuous scarps of
minor faults are systematically absent from Quaternary fault compilations and
are invisible at the competition's 100 m resolution. The competition itself
supplies 1 m DEM links — evidence the organizers expect fine-scale topography
to carry signal. These minor scarps are the surface expression of concealed or
poorly mapped fault strands.

**How it differs from prior work:** The local owner-derived `lidar_scarp_features_u8.tif`
stack (12 channels) contains first-order scarp statistics only. The owner's
public LiDAR attempt scored 0.1461. No orientation × step-height matched filter
and no segment-continuity linker exists in either codebase.

**Expected ΔDTI / cost:** +0.005…+0.040 planning prior (highest ceiling,
lowest confidence); **high cost** — ~700–1,200 tiles at ~275–287 MB each
(tens to ~200 GB) if raw DEMs are used. A reduced version applies the new
transform to the already-local 12-channel scarp stack at low cost.

**Official source / access:** [Obtainability verified]
`https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-119,38.5,-118.5,39`
returned 32 products for a test bbox inside the GeoDAWN region with direct
GeoTIFF URLs on `prd-tnm.s3.amazonaws.com`; "All 3DEP products are public
domain." Caveat: this sandbox cannot open `prd-tnm` / `tnmaccess` / USGS hosts
directly (TLS EOF); transfer must run off-sandbox.

**Status:** Reduced-stack variant (H-31-02b) was tested and failed
spatial/perturbation gates — do not retune against inspected SGMC labels. The
full raw-DEM matched-filter/continuity arm is **distinct and untested**, but
blocked on verified broad-area coverage and off-sandbox transfer.

---

## H-3 · Quaternary vent-feeder alignment along magnetic edges (rank 3)

**Layers:** GDR 1391 Quaternary vents (21 sites: 20 basalt, 1 rhyolite; CC BY
4.0); `tmi_hg` magnetic-anomaly edges from the competition feature stack.

**Physical signature:** ≥2 vents aligned over 2–8 km, with the alignment
continuing along a dike-like linear magnetic anomaly edge. Dots placed along
the inferred feeder corridor between and beyond aligned vents.

**Why it catches catalogue-absent faults:** Volcanic vent chains expose feeder
structures (dikes, blind faults) that are absent from the fault catalogue.
Measured: 0/21 vents are within 300 m of a catalogue trace. No inspected local
or owner summary uses vent geometry at all.

**How it differs from prior work:** Radically distinct — no prior lane uses
volcanic vent geometry. All prior work is fault-/topography-/strain-centered.
Small n=21 limits statistical power; volcanic/non-tectonic confounding must be
controlled with spatially constrained random point sets and magnetic-only
controls.

**Expected ΔDTI / cost:** +0.001…+0.010 planning prior; **low compute cost**,
**low statistical power**.

**Official source / access:** [GDR 1391](https://gdr.openei.org/submissions/1391)
states CC BY 4.0; the Quaternary-volcanics ZIP was downloaded/hash-verified
via the recorded bridge receipt and rasterized locally. Feature source is
official, but the competition raster remains an owner mirror.

**Falsifiable gate:** Freeze vent-pair distance/strike and magnetic-edge
tolerance *before* fitting; compare aligned-vent corridors to 1,000 spatially
constrained random point sets and magnetic-only controls on blocked holdout.
Require positive paired effect in ≥3/4 folds and fresh-seed confirmation;
otherwise reject rather than widen the search post hoc.

**Status:** Registered, not run.

---

## H-4 · K–Th–U radiometric alteration unmixing along lineaments (rank 4)

**Layers:** GeoDAWN K, Th, U, total count (`geodawn_rad_u8.tif`, 4 bands) plus
ratio stack (Th/K, U/K, U/Th; `geodawn_extensions_u8.tif`).

**Physical signature:** ratio-space alteration anomaly — K-enrichment with U
mobilisation — tested for *along-lineament coherence*, not raw band magnitude.
Dots placed where a radiometric alteration halo coincides with a linear
structural trend but no mapped fault trace.

**Why it catches catalogue-absent faults:** Fault-controlled fluid pathways
produce clay/illite (± K) and uranium alteration haloes detectable radiometrically
even where the surface fault trace is unmapped. The catalogue is independent of
the radiometric grid, so alteration-defined lineaments can reveal faults the
catalogue misses.

**How it differs from prior work:** Both this repo and the owner use
radiometric bands as ordinary model features. An explicit three-endmember
K–Th–U unmixing combined with a lineament-coherence test is not implemented in
either. Beware: K/Th ratios are dominated by lithology, so a lithology-stratified
null is mandatory.

**Expected ΔDTI / cost:** +0.001…+0.012 planning prior; **low cost** — the
rasters are already local.

**Official source / access:** USGS GeoDAWN data release, DOI
[10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) (public-domain USGS data
per the catalog record). Local copies are owner-derived quantisations, not
organizer-authenticated; verify band metadata and exact source lineage before
freezing.

**Status:** Registered, not run; cheapest arm to add.

---

## H-5 · Drainage-response fault traces (rank 5)

**Layers:** USGS National Hydrography Dataset (NHD) flowlines + USGS 3DEP DEM
(1 m or 10 m).

**Physical signature:** strike-aligned knickpoint chains, left/right-lateral
channel offsets, and beheaded channels across a candidate fault trace.

**Why it catches catalogue-absent faults:** Fluvial geomorphology records
deformation where the scarp itself is eroded, buried, or too subdued to map. A
fault-trace compilation is not a drainage analysis, so the two inventories
disagree by construction — drainage captures faults the catalogue omits.

**How it differs from prior work:** The repository uses no hydrology layer at
all; no inspected owner page reports a flowline-based transform.

**Expected ΔDTI / cost:** +0.002…+0.020 planning prior; **medium-high cost**
(tile download, hydrological conditioning, flowline extraction, DEM–flowline
registration).

**Official source / access:** `tnmaccess.nationalmap.gov` exposes NHD products
through the same public TNM API used for 3DEP. The specific NHD query and local
transfer have **not** been executed; treat as conditional. 3DEP/NHD are USGS
public-domain data.

**Status:** Registered, not run; source check incomplete — must be completed
before promotion.

---

## Promotion rule (unchanged)

No weekly submission slot may be proposed for a hypothesis whose feature data
are not obtained and checksummed, whose recipe and thresholds are not frozen
before the run, whose holdout gate does not pass on a buffered spatial holdout,
and whose exact candidate GeoTIFF does not pass the template audit. A
catalogue-derived holdout is a necessary but biased proxy: the official metric
masks catalogue pixels, so a catalogue holdout can reward exactly the
predictions the competition ignores.

**Cross-site algebra illustration only — not an inference about the public
leader:** if weighted false-positive mass were exactly zero, a DTI of 0.3195
would correspond to roughly 27% of hidden positive mass covered under the
metric's Tversky algebra. The actual false-positive mass, hidden-label size,
candidate attribution, and public-to-private relationship are unknown, so the
leader's score does not reveal coverage or the value of any listed hypothesis.
Planning priors are experiment ranges, not measured gains, calibrated forecasts,
or competition-score predictions.
