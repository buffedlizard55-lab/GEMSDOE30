# Untried hypothesis candidates — GEMSDOE30 session 2026-10-27

**Context.** The repository's active untried shortlist (docs/hypotheses.md, reviewed 2026-10-03) is:
1. H-31-04 radiometric K–Th–U alteration unmixing along lineaments (low cost, local GeoDAWN bands);
2. H-32-03 geothermometer discordance/blind-upflow zoning (needs GDR 1486 chemistry, source audit open);
3. H-32-02 Quaternary vent-feeder alignment (GDR 1391, CC BY 4.0, local; n=21, low power);
4. H-31-03 drainage-response fault traces (needs USGS NHD + 3DEP; sandbox cannot reach USGS hosts, IR-30-019);
5. H-32-04 kinematically constrained Qfaults gap completion (conditional, needs an independent inventory).

Tested and not promoted: H-31-01 relay connector (+1.2% per pixel, noise), H-31-02 scarp matched filter (failed), H-VENT (negative), H-NEARSPLAY (promoted on holdout but duplicate-stopped on expanded registry at 71.26%), H-31-05 curvature (negative), metric-emission sweep, quadrature phase, tilt alteration, CSR, LSM, POOL-1 (science confirmed, raster duplicate-stopped).

The candidates below are **not in any inspected register**. They are ranked by expected holdout-DTI improvement (planning prior only — not a forecast) and implementation cost. Per the parallel-run protocol, the top candidate must beat the same-protocol control on the spatially blocked holdout with paired 95% CI lower bound > 0 before any weekly slot is considered; the lattice witness (first_provably_stopped_budget = 22,164 dots) additionally makes every dense raster a duplicate-stop, so any promoted recipe must emit <= 22,163 dots with > 30% outside the lattice neighbourhood.

## H-NEW-1 — GeoDAWN radiometric alteration ratio coherence along lineaments (rank 1)

- **Layers:** USGS GeoDAWN airborne radiometrics (K, Th, U, total count; owner-derived 100m stack `geodawn_rad_u8.tif` is local) → ratio space Th/K, U/K, U/Th; GeoDAWN lineament/trace mask as the coherence axis.
- **Physical signature:** fault-controlled fluid ascent produces illite/clay (±K enrichment) and uranium mobility haloes; the diagnostic is *along-lineament coherence* of ratio anomalies, not raw band magnitude.
- **Why it catches catalogue-missing faults:** alteration can exist where no surface trace was mapped; the catalogue is independent of the radiometric grid. A lithology-stratified null (ratios within map units) removes the rock-type confounder.
- **Difference from repo work:** radiometric bands have been used as ordinary model inputs; no three-endmember ratio unmixing plus lineament-coherence test exists in this checkout.
- **Expected gain / cost:** +0.001…+0.012 planning prior; low compute; all inputs local (SHA-pinned).
- **Official source:** USGS GeoDAWN data release DOI 10.5066/P93LGLVQ (public domain per catalog record) — https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and. Local copies are owner-derived quantisations, not organizer-authenticated; verify band metadata and lineage before freezing.
- **Gate:** frozen unmixing + coherence arm vs raw-band and lithology-stratified spatial nulls on four buffered spatial blocks; require pooled ΔDTI >= +0.005 over same-run control, >= 3/4 positive folds, fresh-seed replication.

## H-NEW-2 — Aeromagnetic edge × radiometric thorium anomaly intersection, off-catalogue (rank 2)

- **Layers:** GeoDAWN total-field magnetics TMI (first vertical derivative / analytic-amplitude edge) × radiometric thorium anomaly; mask = pixels > 2 px outside the catalogue.
- **Physical signature:** concealed faults offset magnetic basement and focus radiogenic fluid alteration; the intersection targets the *joint* edge, which neither scalar alone isolates.
- **Why it catches catalogue-missing faults:** blind faults with no scarp expression still offset basement magnetic sources; catalogue-independent physics.
- **Difference from repo work:** potential-field work exists (CSR cover-blind expert), but not a TMI-edge × radiometric-Th conjunction masked off-catalogue.
- **Expected gain / cost:** +0.002…+0.010 planning prior; low cost; inputs local.
- **Official source:** same GeoDAWN release (DOI 10.5066/P93LGLVQ).
- **Gate:** conjunction arm vs TMI-only, Th-only, and count-matched spatial nulls on blocked holdout; same +0.005 / 3-of-4 / fresh-seed gate.

## H-NEW-3 — Quaternary vent density kernel weighted by magnetic-lineament proximity (rank 3)

- **Layers:** INGENIOUS Quaternary volcanic vents/flows (GDR 1391, CC BY 4.0; locally rasterized `derived_gdr_volcanics_100m_u8.tif`) → 2–8 km density kernel; mask off-catalogue; weight by proximity to magnetic lineament edges.
- **Physical signature:** vent fields mark crustal pathways; a fault that fed volcanism is a geothermal conduit even if never mapped as a Quaternary fault.
- **Why it catches catalogue-missing faults:** 0/21 GDR vents lie within 300 m of a catalogue trace (measured), so vent-driven structures are systematically catalogue-absent.
- **Difference from repo work:** H-32-02 tests *aligned vent pairs*; this tests vent *density* (areal propensity) — a different statistic, untested here.
- **Expected gain / cost:** +0.001…+0.010; low cost; low statistical power (21 vents).
- **Official source:** GDR 1391 https://gdr.openei.org/submissions/1391.
- **Gate:** kernel bandwidth and magnetic tolerance frozen pre-run; vs 1,000 spatially constrained random point sets and magnetic-only control on blocked holdout; positive paired effect in >= 3/4 folds else reject (no post-hoc widening).

## H-NEW-4 — Drainage-response traces: knickpoint chains and channel offsets (rank 4, conditional)

- **Layers:** USGS NHD flowlines + USGS 3DEP 1 m DEM (public domain).
- **Physical signature:** strike-aligned knickpoint chains and left/right-lateral channel offsets across candidate traces; rivers record deformation where scarps are eroded/buried.
- **Why it catches catalogue-missing faults:** a fault-trace compilation is not a drainage analysis; inventories disagree by construction.
- **Difference from repo work:** no hydrology layer exists in this checkout or any inspected owner summary.
- **Expected gain / cost:** +0.002…+0.020; medium-high data/processing cost (tile download, DEM conditioning, flowline extraction, registration).
- **Official source:** USGS TNM (https://tnmaccess.nationalmap.gov) — test bbox query returned products; full ROI coverage and transfer **not verified**, and the sandbox cannot reach USGS/TNM hosts (IR-30-019); transfer must run off-sandbox.
- **Gate:** hard gate — obtain and checksum full-ROI NHD + 3DEP, verify coverage, then freeze detector; slope-only and random controls on blocked holdout; +0.005 / 3-of-4 / fresh-seed. Incomplete coverage stops the test.

## H-NEW-5 — Kinematically constrained Qfaults gap completion (rank 5, conditional; from H-32-04)

- **Layers:** Qfaults v2 traces with recency/slip/length (GDR 1391, local) + independent inventory (OSTI 1148722 or GDR 616) for truth.
- **Physical signature:** physically consistent gap extensions > 300 m from known traces, same slip sense/rate.
- **Why it catches catalogue-missing faults:** unmapped geometry of existing systems counts as "new fault" per organizer clarification (forum t/11536).
- **Difference from repo work:** uses fault kinematics, not topography; H-32-04 is already registered but conditional on an independent truth set.
- **Expected gain / cost:** +0.005…+0.025 conditional; medium cost.
- **Official source:** https://www.osti.gov/dataexplorer/biblio/dataset/1148722 and https://gdr.openei.org/submissions/616 — pages verified; archive retrieval/schema/coverage **not verified**.
- **Gate:** obtain and checksum an independent inventory, verify independence from INGENIOUS/Qfaults and ROI coverage, then preregister buffered holdout; +0.005 over count-matched baseline, >= 3/4 folds, fresh-seed. No independent truth → do not score or promote.

## Validation plan (this session)

The top local candidate (H-NEW-1 or H-NEW-2) is validated on the same spatially buffered component holdout used here (`scripts/holdout_unique_submission.py` pattern: `split_components`, `masked_dti_by_blocks`, `spatial_bootstrap`), against a count-matched control, with the leakage canary (AUC <= 0.90). This session's unique raster was evaluated on that holdout: HOLDOUT-DTI 0.030752 [0.027582, 0.034455] vs random-dots control 0.030371 [0.028689, 0.031941], paired difference +0.000381 [-0.002989, +0.004218] — CI crosses zero, so **no promotion**. The holdout harness itself is verified and reusable for the next session's hypothesis tests.
