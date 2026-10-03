# Geothermal vents and fault discovery — verified knowledge base

**Compiled:** 2026-10-03 (autonomous research session). **Purpose:** the owner brief names
"the scientific discovery of geothermal vents" as the part of the project that matters most and
asks that everything gathered from official, verified sources be stored as a starting point for
other projects. This document is that store. Evidence classes used throughout:

* **[OFFICIAL]** — quoted or paraphrased from a document fetched and read this session
  (rules PDF, DrivenData community staff posts, DOE OSTI publications, USGS/GDR records).
* **[MEASURED]** — computed in this checkout from local bytes; reproducible with the listed
  script/command; local files are SHA-256-pinned owner mirrors, **not organizer-authenticated**.
* **[CLAIM]** — user/owner-reported, not authenticated here.
* **[INFERENCE]** — reasoning that combines the above; not itself evidence.

---

## 1. What the competition actually is [OFFICIAL]

Source: [GEMS Prize Official Rules, September 2026](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
(fetched and read 2026-10-03; the URL is `docs.nlr.gov` — National Laboratory of the Rockies,
the prize administrator — not NREL).

| Fact | Rules text (section) | Consequence for strategy |
| --- | --- | --- |
| Goal | "accurate information about the presence of structures indicative of geothermal resources" (§1) | The scientific target is fault structure that indicates geothermal resources — vent/structure science is on-mission, not decorative. |
| Feature data | GeoDAWN lidar/magnetics/radiometrics (Glen & Earney 2024, DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ)) + USGS 1 m DEM (§2, §3.3) | The organizers explicitly provide 1 m DEM links — fine-scale topography is expected to carry signal. |
| Training labels | "existing fault data … obtained from the INGENIOUS project's Great Basin Regional Dataset Compilation" (§3.3, DOI [10.15121/1881483](https://doi.org/10.15121/1881483)) | `labels.tif` = the mapped catalogue. The metric masks it (community thread 11516). |
| Test labels | "labels for this prize come from the USGS Quaternary Fault and Fold Database and from a set of newly identified faults labeled by geology experts at [NLR] and USGS" (§2) | The scored target is **expert-new faults**: geometry experts could confirm but the catalogue does not contain. |
| Metric | distance-weighted Tversky; "penalizes false negatives … more than false positives" (§3.6.1) | α = 0.2 / β = 0.8 as published on the problem page; coverage > precision (see `why-d28-scored-026.md`). |
| Feedback | "up to three [submissions] per week" (§3.4) | Weekly slots are scarce; validate on holdout first (project rule). |
| Final entry | "choose only one submission for evaluation across both prize rounds … without knowledge of your scores on the private test set" (§3.4, §3.6.2) | The final pick must be scientifically defensible, not the luckiest public-LB spike. |
| Finalists | "complete code assets and documentation … able to sufficiently reproduce the winning results" (§3.5) | This repository's audit trail is a competitive asset. |
| AI use | Generative AI allowed; must "indicate in the narrative … the extent to which … you used generative AI" (§3.2) | `docs/ai-disclosure-draft.md` must be completed truthfully before entry. |
| Phase 1 | $50,000 split **equally** among top 5 on the private withheld subset (§1.1) | Top-5 on the private set is the Phase-1 goal; equal split reduces the value of rank-1 gaming. |
| Phase 2 | $250,000 (1st $100k … 5th $15k) on the **updated** label set created by expert review of Phase-1 submissions (§1.1, §3.6.1) | The bigger pool rewards traces experts will *confirm* when they revise the map — scientifically real, mappable faults, not leaderboard-exploitation artefacts. |
| Deadline | "5:00 p.m. ET on the prize submission deadline date" (Appendix A.1) vs the homepage's 11:59 p.m. UTC | **Open irregularity IR-26** — confirm the controlling cutoff with the organizer. |
| Eligibility | U.S. citizens/permanent residents (individuals), U.S.-incorporated entities, U.S. academics; FFRDC/DOE/FCOC/MFTRP exclusions (§1.3) | Verify entrant eligibility before any entry; the operator is responsible for certification under penalty of perjury. |

DrivenData staff clarifications (community forum, fetched 2026-10-03):
* [Thread 11516](https://community.drivendata.org/t/11516): "Pixels corresponding to known
  USGS/INGENIOUS faults are masked / excluded from evaluation, so they do not count towards
  penalty terms." (staff, 2026-09-16)
* [Thread 11536](https://community.drivendata.org/t/11536): "'new fault' means 'any fault pixel
  not already captured by USGS/INGENIOUS' and can include newly mapped geometry of an existing
  fault system." (staff, 2026-09-23)
* [Thread 11527](https://community.drivendata.org/t/11527): organizers will not disclose the
  test faults' sources, types, or coverage; the Final Round test set is "updated by expert review
  of all Phase 1 submissions." (staff, 2026-09-23)

---

## 2. The science: how geothermal systems relate to faults here [OFFICIAL]

Primary literature (U.S. Department of Energy / OSTI; fetched 2026-10-03):

1. **[Faulds et al., "Structural investigations of Great Basin geothermal fields" (OSTI 1110517)](https://www.osti.gov/servlets/purl/1110517)**
   — "most systems occupy discrete steps in normal fault zones or lie in belts of intersecting,
   overlapping, and/or terminating faults"; "Most fields are associated with steeply dipping
   faults and, in many cases, with Quaternary faults"; step-overs control Desert Peak and
   Brady's; "Exploration strategies should focus on intersecting, terminating, and overlapping
   features of fault systems."
2. **[Faulds, "Structural Inventory of Great Basin Geothermal Systems…" (OSTI 1148722)](https://www.osti.gov/dataexplorer/biblio/dataset/1148722)**
   — inventory of **426 geothermal systems**; "step-overs or relay ramps in normal fault zones
   are the most favorable setting, hosting ~32% of the systems"; accommodation zones 9%,
   displacement-transfer zones 5%, pull-aparts 3%, bends 2%, range-front faults 1%; "~39% are
   blind (no surface hot springs or fumaroles), but estimates suggest that as much as 75% of the
   geothermal resources in the region are blind"; "Quaternary faults typically lie within or near
   most of the geothermal systems."
3. **[Faulds et al., "Discovering new geothermal systems in the Great Basin" (OSTI 1724109)](https://www.osti.gov/servlets/purl/1724109)**
   — "nearly all geothermal systems located proximal to Quaternary faults"; "upwelling fluids
   along the faults commonly flow into permeable sediments … Outflow … may therefore surface
   many kilometers away from the deeper source or remain entirely blind"; **linear tufa towers
   follow dextral-normal faults and mark the blind Pyramid Lake system**.
4. **[GDR 616 — Nevada Great Basin Play Fairway Analysis regional data (Faulds)](https://gdr.openei.org/submissions/616)**
   — free official play-fairway layers: structural settings, Quaternary faults, strain,
   earthquakes, gravity, 3 km temperature, springs/wells, favorability models.
5. **[GDR 1486 — GBCGE Subsurface Database Explorer and APIs (NBMG/UNR)](https://gdr.openei.org/submissions/1486)**
   — the well/spring/structural-setting compilation behind the local wellspring mirror.
6. **[GDR 458 — USGS "Geologic Framework of Thermal Springs, Black Canyon…"](https://gdr.openei.org/submissions/458)** — official example of spring-to-fault geologic framing.

**Synthesis [INFERENCE]:** the scored hidden faults are exactly the population that (a) experts
can map from lidar/geophysics but (b) the INGENIOUS catalogue lacks — thin, discontinuous
Quaternary scarps, splay/step-over strands, and blind-system structures. The literature says
discharge sites and their kilometre-scale outflow haloes sit on these structures; vents, springs,
tufa and alteration are *independent* channels to the same geometry the metric rewards.

---

## 3. Local data inventory [MEASURED] (owner mirrors, SHA-256-pinned in `docs/research/mirror-pins*.json`)

| File | Content | Key measurements (this checkout) |
| --- | --- | --- |
| `data/external/gdr_wellspring_in_footprint.csv` | 27,092 rows; wells + springs with `temp_c`, quartz/chalcedony/cation geothermometers, thermal class | 12,570 unique grid cells; **512 cells ≥ 60 °C**, **256 ≥ 100 °C**, max 296.5 °C; median site 24 px (2.4 km) from catalogue truth; 11.6 % of rows within 300 m of catalogue vs 8.6 % base rate; hot cells ≥ 60 °C: **2.3× enriched** within 300 m (102/512), median 14 px (1.4 km) from catalogue |
| `data/external/gdr_volcanic_vents_in_footprint.csv` | 21 vents (20 basalt, 1 rhyolite) with grid positions | **0 of 21 within 300 m of catalogue truth**; median distance 22 px (2.2 km) — feeder structures of these eruptions are unmapped in the catalogue |
| `data/external/gdr_qfaults_traces.csv` | 1,126 Quaternary fault traces (Qfaults attributes: slip rate, recency, slip sense, length); 376 centroids in footprint | 55 % of in-footprint centroids within 3 px of catalogue truth (6.4× base rate) — Qfaults substantially overlaps the catalogue (expected: training labels derive from INGENIOUS/Qfaults); **45 % sit > 300 m from catalogue** |
| `data/external/lidar_scarp_features_u8.tif` | 12-band uint8 scarp stack: `ex_max, ex_mean, step_max, lapneg_max, lappos_max, downface_max, upface_max, cross_max, relief, coh100, strike, valid` | owner-derived; registered input for the reduced H-31-02 matched-filter arm |
| `data/external/geodawn_rad_u8.tif` / `geodawn_extensions_u8.tif` | K, Th, U, TC / Th:K, U:K, U:Th, TMI_up150 | owner-derived quantisations of the GeoDAWN radiometrics (DOI 10.5066/P93LGLVQ) |
| `data/raw/training_features.tif` | 19 float32 bands (magnetics, gravity, geodesy, seismicity-distance, DEM, conductivity, basement depth — full list in `prepared-manifest.json`) | 3,730 × 3,292 @ 100 m, EPSG:32611 |
| `data/raw/labels.tif` | INGENIOUS catalogue positives | 60,988 positive pixels; 3,199 8-connected components |
| `data/raw/sample_submission.tif` | official template | NaN outside footprint (7,111,787 px), 0/1 inside; **contains the catalogue as 1s — irregularity IR-27** |

---

## 4. What others are overlooking (contrarian angles grounded in §2)

1. **Discharge-geometry priors.** Owner sites use thermal/alteration as scalar features; none
   tests spring-cluster *alignment corridors* or geothermometer-estimated reservoir temperature
   as a conduit proxy (H-32-01/03/05). The literature's core discovery pattern (terminations,
   intersections, step-overs of Quaternary faults) is relational, and discharge data is the only
   fully independent channel to it.
2. **Volcanic vent alignments.** 21 vents, none near the catalogue: their feeder dike swarms are
   unmapped structure (H-32-02). No inspected owner page uses vents at all.
3. **Phase-2 realism.** The Phase-2 label set is built by experts reviewing submissions
   (thread 11527). Sparse, geometrically clean, literature-consistent traces (dotted masks with
   correct strike) should be more confirmable than dense probability fields — consistent with
   the observed leaderboard success of the thin "dotted" family ([CLAIM] 0.2477/0.2600 attributions
   unverified, but the family is at the group's frontier).
4. **Blind-system surface proxies** (tufa alignments, dead ground, thermal-infrared anomalies)
   from free USGS/NASA archives — registered but conditional on data acquisition (H-32-04).

---

## 5. Knowledge gaps and next official data to obtain

| Gap | Free official source | Status |
| --- | --- | --- |
| 1 m DEM tiles for matched-filter scarps (H-31-02 raw arm) | USGS 3DEP via [TNM API](https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter) — "All 3DEP products are public domain"; 32 tiles verified for a test bbox; ~275–287 MB each | obtainability verified 2026-10-03; bulk transfer must run off-sandbox |
| Play-fairway structural/favorability layers for cross-validation | [GDR 616](https://gdr.openei.org/submissions/616) | page verified; ZIP retrieval not yet executed |
| 426-system structural inventory (incl. blind-system flags) | [OSTI 1148722](https://www.osti.gov/dataexplorer/biblio/dataset/1148722) | page verified; spreadsheet retrieval not yet executed |
| NHD flowlines for drainage-response faults (H-31-03) | USGS TNM NHD products (same API) | query not yet executed |
| Tufa/sinter mapped localities (blind-system proxies) | NBMG geothermal field maps / GDR 458-style USGS products | not yet catalogued |

---

## 6. Citation register (manual-review links)

| # | Source | URL | Class | Read |
| --- | --- | --- | --- | --- |
| 1 | GEMS Prize Official Rules, Sept 2026 | https://docs.nlr.gov/docs/fy26osti/96647.pdf | official | 2026-10-03, chunks 0–3 |
| 2 | DrivenData problem description | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | official | 2026-10-03 (prior sessions) |
| 3 | DrivenData community staff — catalogue masking | https://community.drivendata.org/t/11516 | official | 2026-10-03 |
| 4 | DrivenData community staff — "new fault" definition | https://community.drivendata.org/t/11536 | official | 2026-10-03 |
| 5 | DrivenData community staff — test-set secrecy/update | https://community.drivendata.org/t/11527 | official | 2026-10-03 |
| 6 | DrivenData leaderboard snapshot | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | official | 2026-10-03 (DARD 0.3195; wbg1 0.2600 rank 15) |
| 7 | GeoDAWN data release (Glen & Earney 2024) | https://doi.org/10.5066/P93LGLVQ | official | cited in rules §2 |
| 8 | INGENIOUS Great Basin compilation (Ayling et al. 2022) | https://doi.org/10.15121/1881483 | official | cited in rules §3.3 |
| 9 | Faulds et al. — structural investigations | https://www.osti.gov/servlets/purl/1110517 | official (DOE) | 2026-10-03 |
| 10 | Faulds — 426-system structural inventory | https://www.osti.gov/dataexplorer/biblio/dataset/1148722 | official (DOE) | 2026-10-03 |
| 11 | Faulds et al. — discovering blind systems | https://www.osti.gov/servlets/purl/1724109 | official (DOE) | 2026-10-03 |
| 12 | GDR 616 Nevada Play Fairway data | https://gdr.openei.org/submissions/616 | official (DOE) | 2026-10-03 |
| 13 | GDR 1486 GBCGE subsurface database | https://gdr.openei.org/submissions/1486 | official (DOE) | 2026-10-03 |
| 14 | GDR 1391 INGENIOUS | https://gdr.openei.org/submissions/1391 | official (DOE) | prior session |
| 15 | Kervadec et al. boundary loss (PMLR 2019) | https://proceedings.mlr.press/v102/kervadec19a.html | official (PMLR) | prior session |
| 16 | USGS Quaternary Fault and Fold Database | https://www.usgs.gov/programs/earthquake-hazards/faults | official | cited in rules §2 |

**No-hallucination statement:** every number in §1–§3 is either quoted from a source in this
register, measured in this checkout with the command listed, or explicitly tagged [CLAIM]/
[INFERENCE]. Scores attributed to owner files remain unauthenticated ([CLAIM]).
