# 3–5 Candidate Geological Hypotheses — 2026-10-29 Session

**Context:** This session targets the DOE GEMS concealed-fault competition. The current
AGENTS.md records a mandatory DUPLICATE-STOP (2026-10-27 registry preflight); no new
lane, fit, placement, raster, or slot was authorized by that governance file. These
hypotheses are therefore **preregistration candidates only** — none may consume a weekly
submission slot until an explicit lane is assigned, the duplicate-stop is resolved, and
a holdout gate passes. This document follows the owner brief's required brief format:
each entry names the exact layer(s), the physical signature, why it can catch a fault
missing from the USGS/INGENIOUS catalogue, and how it differs from anything already
implemented in this repo. Ranking is by expected DTI improvement and implementation
cost. All priors are planning priors, not forecasts or measured gains.

## Data basis (all locally available, SHA-256 pinned owner mirrors; not organizer-authenticated)

| Layer | Source | Pixels in footprint | Official source |
|---|---|---|---|
| `derived_sgmc_faults_100m_u8.tif` | USGS SGMC state geologic map (NV + CA structure) | 82,151 | USGS MRDS, public domain |
| `derived_gdr_paleo_100m_u8.tif` | GDR 1391 paleo-geothermal (sinter/tufa deposits) | 244 | GDR 1391, CC BY 4.0 |
| `derived_gdr_volcanics_100m_u8.tif` | GDR 1391 Quaternary volcanics (vents + flows) | 6,776 | GDR 1391, CC BY 4.0 |
| `derived_gdr_2m_probes_100m_u8.tif` | GDR 1391 2 m temperature probes | 2,700 | GDR 1391, CC BY 4.0 |

All external rasters are aligned to the competition grid (3730×3292, EPSG:32611,
100 m, transform [243350, 100, 0, 4508550, 0, -100]). The template grid reference is
`docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif`.

---

## Hypothesis 1 — Paleo-geothermal spring alignment corridors (rank 1)

**Layers:** `derived_gdr_paleo_100m_u8.tif` (paleo-geothermal sinter/tufa/travertine
deposits) + `derived_gdr_volcanics_100m_u8.tif` (Quaternary vents/flows) + distance
transform to the SGMC fault catalogue (for masking only, not as a proximity feature).

**Physical signature:** Sinter, tufa and travertine mounds precipitate from CO₂-rich
thermal waters discharging along fault-controlled conduits. A *cluster alignment*
transform — pairing deposits 2–8 km apart with along-strike overlap and scoring the
connector corridor between them — targets the fault zone that connects the discharge
points. The deposits themselves may lie >1 km from the source structure (outflow
surfaces can surface km from the conduit), so the corridor lies *between* mapped
features rather than on them.

**Why it catches catalogue-missing faults:** The USGS/INGENIOUS catalogue is a
surface-mapping product; blind or concealed conduits that feed paleo-spring deposits
may have no mapped surface trace. Measured: 100% of the 244 paleo pixels are >300 m
from any SGMC fault pixel, and 0 of 21 GDR volcanic vents lie within 300 m of the
catalogue (median 2.2 km). The structures that fed these discharges are unmapped in
the catalogue but are exactly the "new fault" population the organizer scores
(thread 11536: "new fault" = any fault pixel not already captured by USGS/INGENIOUS).

**Difference from implemented work:** No existing repo hypothesis pairs paleo-geothermal
deposits into alignment corridors. Owner thermal work (h19-4 "thermal-pop",
15GEMSDOE "conj_alteration_mag") uses temperature/alteration as scalar emission
fields; H-32-01 tested hot-spring clusters as a corridor and failed (−0.01494) — but
that used *active* spring temperature cells, not paleo-geothermal deposits, which are
a different, older, more structurally-rooted observable. No inspected code constructs
pairwise alignment corridors from independent point deposits.

**Named non-fault mimic:** Fossil sinter mounds preserved on non-fractured lithology,
relict spring deposits from now-inactive hydrologic systems, or lake-shore tufa
unrelated to faulting. Falsification: require ≥2 deposits per corridor, corridor
azimuth within ±20° of regional structural grain, and a count-matched random-deposit
null on buffered spatial blocks.

**Expected ΔDTI / cost:** +0.002…+0.012 planning prior; **low** cost — all data local,
CPU-feasible, no new external transfer.

**Validation path:** Component holdout with whole-SGMC-components hidden; paleo-corridor
arm vs count-matched random-deposit control and vs deposit-only (no corridor) control;
require pooled Δ ≥ +0.005, ≥3/4 folds positive, fresh-seed confirmation.

---

## Hypothesis 2 — Quaternary volcanic vent feeder fissure alignment (rank 2)

**Layers:** `derived_gdr_volcanics_100m_u8.tif` (21 vents: 20 basalt, 1 rhyolite) +
magnetic-edge texture from competition bands (`tmi_hg`, `rtp`) as corroboration only.

**Physical signature:** Cinder-cone vent chains mark surface expressions of feeder
fissures — linear swarms of vents aligned along strike over 2–8 km. A 2+ vent
alignment test extended along co-located magnetic lineaments targets the blind feeder
fissure system beneath the vents.

**Why it catches catalogue-missing faults:** Measured: 0 of 21 vents lie within 300 m
of any SGMC fault pixel (median 2.2 km). The feeder structures that supplied these
eruptions are structurally unmapped in the catalogue. Linear vent chains and associated
tufa mark blind fault systems (e.g., Pyramid Lake — Faulds et al. OSTI 1724109).
~39% of Great Basin geothermal systems are blind; up to ~75% of regional geothermal
resources may be blind (OSTI 1148722).

**Difference from implemented work:** No inspected repo or owner page uses volcanic
vents in any form. H-32-02 (vent feeder alignment) was registered but not executed due
to low power (n=21). This hypothesis is contrarian, nearly free, and targets a
structural setting (volcanic feeder fissures) that a surface fault catalogue cannot
contain.

**Named non-fault mimic:** Volcanic fields aligned along pre-existing lithologic
contacts or non-tectonic stress fields; monogenetic vent clustering from magma
supply rather than fault control. Falsification: compare aligned-vent score against
1,000 spatially constrained random point sets and magnetic-edge-only controls.

**Expected ΔDTI / cost:** +0.001…+0.010 planning prior (low power: n=21); **low** cost
— local CSV-derived raster only.

**Validation path:** Component holdout; vent-alignment arm vs spatial-random and
magnetic-edge controls; report as pilot due to small n; require positive paired effect
in ≥3/4 folds or reject rather than widen post hoc.

---

## Hypothesis 3 — 2 m shallow temperature probe anomaly corridors (rank 3)

**Layers:** `derived_gdr_2m_probes_100m_u8.tif` (2 m temperature probe survey) +
`derived_gdr_paleo_100m_u8.tif` as independent corroboration.

**Physical signature:** Shallow (2 m) temperature anomalies indicate near-surface
convective fluid flow along permeable fault zones. Clusters of warm probes (>60 °C)
aligned along strike mark blind conduits; the corridor transform scores the linear
structure connecting anomalous probe sites, not the point values themselves.

**Why it catches catalogue-missing faults:** 2 m probe surveys sample near-surface
thermal anomalies that can occur above blind faults with no surface rupture. The probe
network is an independent measurement programme from the fault-mapping programme, so
its spatial pattern is not circular with the catalogue. Measured: 2,700 probe pixels
in footprint; distribution relative to catalogue is untested in this checkout.

**Difference from implemented work:** Owner thermal work used spring *temperature
populations* (h19-4) and geothermometer chemistry (H-32-03), but no inspected work
uses 2 m shallow probe data as a corridor transform. This is a different measurement
depth and a different spatial sampling from spring temperature.

**Named non-fault mimic:** Shallow solar-heating effects, near-surface sediment
properties, or local topography-driven cold-air drainage producing spurious warm
anomalies. Falsification: depth-gradient check (2 m vs surface temperature where
available), aspect-matched controls, and whole-site-cluster holdout.

**Expected ΔDTI / cost:** +0.001…+0.008 planning prior; **low** cost — local raster.

**Validation path:** Component holdout; probe-anomaly corridor arm vs temperature-only
point arm and count-matched distance-matched random control; require ≥ +0.005, ≥3/4
folds; stop if ROI site count < 50 (underpowered).

---

## Hypothesis 4 — Basin-cover observability prior (rank 4)

**Layers:** `derived_sgmc_faults_100m_u8.tif` (for masking only) + SGMC geologic map
unit polygons (young cover, basin fill, lake beds) → observability weight × competition
relief bands (`det_elev`, `det_elev_slope`).

**Physical signature:** Not an edge filter but an *observability weight*: cells where
young cover, basin fill, or Quaternary lake beds hide surface expression, restricted
to the structural grain implied by known traces. This models *where missing faults are
likely to exist* rather than *what a fault looks like*.

**Why it catches catalogue-missing faults:** The catalogue is a mapping-effort product:
faults beneath basin fill, lake beds, and Quaternary cover are systematically missing
from any surface catalogue. The organizer's "new faults" are by construction the ones
the catalogue lacks. A concealment prior re-weights where to spend existing evidence
rather than adding a new detector — orthogonal to all evidence-based hypotheses.

**Difference from implemented work:** H-34-01 (substrate-concealment prior) was
registered but not executed; the current fetch script rasterises only SGMC linework,
not polygon units. No inspected code models the selection process that produced the
labels. This is the only candidate that targets *why* labels are missing rather than
*what a fault looks like*.

**Named non-fault mimic:** Alluvial fans, playa deposits, and non-tectonic
topographic lows that look like "cover" but contain no structure. Falsification:
distance-matched control (a concealment prior must not reduce to "far from the
catalogue"); lithology-stratified null; compare against proximity field and
distance-matched random field.

**Expected ΔDTI / cost:** +0.002…+0.015 planning prior; **low** cost — archives already
downloaded and hash-verified; needs polygon-unit rasterization extension.

**Validation path:** Component holdout; concealment-weighted emitter vs proximity-only
emitter and count-/distance-matched random emitter; require ≥ +0.005, ≥3/4 folds,
fresh-draw confirmation.

---

## Hypothesis 5 — Depth-filtered potential-field lineaments (rank 5)

**Layers:** Competition magnetic bands (`tmi_hg`, `rtp`, `mag_anom`) → upward
continuation → tilt-angle derivative → 3-D analytic signal → Euler deconvolution for
source depth; retain lineaments with inverted source depth >0.5–1 km.

**Physical signature:** A buried magnetic source with no surface rupture produces no
scarp, no mapped trace, and almost no topographic lineament — invisible to a surface
catalogue by construction — while still concentrating permeability and heat in the
overlying damage zone. Depth filtering isolates blind sources from shallow mapped
lithologic contacts.

**Why it catches catalogue-missing faults:** Buried structures have no surface
expression for a field mapper to record. Depth-localized magnetic lineaments target
exactly these concealed permeability conduits. Faults that displace magnetic basement
but are covered by alluvium are absent from Qfaults (which requires surface evidence).

**Difference from implemented work:** Prior work used magnetic *values* or their
horizontal gradient (H-32-02 magnetic-edge corroboration, GBM feature stack). No
inspected code inverts for source *depth* or filters lineaments by it. The depth filter
is the key distinction: it separates "mapped already" (shallow, surface-expressed) from
"cannot be mapped" (deep, buried).

**Named non-fault mimic:** Flight-line levelling artefacts, variable magnetization,
remanence, non-fault lithologic contacts with depth extent. Falsification: rotated-kernel
null for flight-line artefacts; depth-cutoff preregistration; depth-filtered arm must
beat (a) same transform without depth filter and (b) spacing/distance-matched control.

**Expected ΔDTI / cost:** +0.002…+0.012 planning prior; **medium** cost — transforms
are cheap but band-lineage verification against official GeoDAWN grids is required;
sandbox cannot reach sciencebase.gov directly.

**Validation path:** Component holdout; depth-filtered arm vs non-depth-filtered arm
and spacing-matched control; require ≥ +0.005, ≥3/4 positive folds; reject if flight-line
artefacts carry the effect.

---

## Ranking summary

| Rank | Hypothesis | Expected ΔDTI | Cost | Data status | Key differentiator |
|---|---|---|---|---|---|
| 1 | Paleo-geothermal spring alignment corridors | +0.002…+0.012 | Low | All local | Corridors between independent deposits |
| 2 | Volcanic vent feeder fissure alignment | +0.001…+0.010 | Low | All local | Contrarian; n=21 vents, 0 near catalogue |
| 3 | 2 m temperature probe anomaly corridors | +0.001…+0.008 | Low | All local | Different measurement depth than springs |
| 4 | Basin-cover observability prior | +0.002…+0.015 | Low | All local | Models *why* labels are missing |
| 5 | Depth-filtered potential-field lineaments | +0.002…+0.012 | Medium | Local + official grids | Depth inversion; targets buried sources |

**Next action:** H-1 (paleo-geothermal corridors) is the cheapest next action with all
data on disk. None of these hypotheses is promoted, none is validated, and none may
consume a weekly submission slot under the current duplicate-stop.