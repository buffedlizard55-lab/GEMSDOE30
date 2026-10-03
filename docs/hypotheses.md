# Ranked geological hypotheses (2026-10-03 session)

Every hypothesis below is written against four verified constraints. Read them first —
they change which ideas are viable.

**C1. Known faults are masked.** DrivenData staff, 2026-09-16, community thread 11516, verbatim:
> "1. Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from evaluation,
> so they do not count towards penalty terms. 2. Re-evaluation will also mask/exclude the existing
> USGS/INGENIOUS faults."
Source: <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>
Consequence: predicting the catalogue is *free but worthless*. The task is detection of faults the
catalogue does not contain. Any holdout that rewards re-predicting the catalogue is mis-shaped.

**C2. The test faults are expert-labelled faults absent from the public catalogue.** Competition
problem description: "we have consulted with fault experts who have manually identified faults that
are not contained within the current public USGS database".
Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>

**C3. Many faults in this region have no surface expression.** Sponsor's own About page: "Most faults
in the GeoDAWN region of Nevada are more subtle, and many are hidden below the surface, requiring
geophysical data to detect."
Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/>

**C4. The metric geometry (verbatim equations, page 967).** With a triangular kernel of 300 m support,
`TP_w` credits each truth pixel from the *best* nearby prediction while `FP_w` accumulates linearly
with predicted mass, and `alpha=0.2`, `beta=0.8`. Redundant coverage is a pure loss; recall is worth
4x precision. Local measurements of this response surface are in
`docs/research/metric-response-surface.json`.

Ranking is by (expected DTI gain on the *hidden-fault* target) / (implementation cost), and each row
names the exact free official source plus its verified access status in this checkout.

---

## H1 — SGMC state-geologic-map faults as a discovery layer (rank 1)

* **Layers.** `data/external/derived_sgmc_faults_100m_u8.tif` — the fault linework of the USGS
  *State Geologic Map Compilation* (SGMC) state packages for Nevada and California, rasterised to the
  competition 100 m grid. Used both as a direct emission prior and as a `distance-to-SGMC-fault`
  feature surface.
* **Physical signature.** Mapped traces from state geological surveys (nominal scales 1:24,000 to
  1:250,000). The transform that matters is a *set difference in interpretation space*: distance to
  the nearest SGMC fault, re-weighted by the local map scale, with the catalogue subtracted.
* **Why it can catch a fault the catalogue is missing.** The competition labels come from "the USGS
  quaternary fault maps and from INGENIOUS" (page 967). The SGMC is an independent compilation of
  *state* maps: different agencies, different mapping campaigns, different epochs. A fault digitised
  by the Nevada Bureau of Mines and Geology at 1:24,000 but absent from the Quaternary Fault and Fold
  Database is exactly the class of feature the sponsor's experts would have had to hand when they
  labelled "new" faults.
* **Difference from work already in this repository.** Every prior experiment here used the catalogue
  as ground truth or as a validation proxy. The SGMC layer has only ever been used upstream as a
  *proxy class* (sibling repo GEMSDOE29, `scripts/build_sgmc_candidate.py`); it has never been used
  as a model input or as an emission prior inside this pipeline.
* **Cost.** Low. The fetch-and-rasterise step is implemented (`scripts/fetch_external_layers.py`) and
  runs on a GitHub runner; rasterisation, hashing and the receipt are automatic.
* **Source and obtainability (checked).** USGS Mineral Resources Program, public domain:
  <https://mrdata.usgs.gov/geology/state/> → `NV.zip`, `CA.zip`. Verified obtainable: the CI bridge
  downloaded NV.zip (69,056,094 bytes, SHA-256 `3b333ac0…b76b`) and CA.zip (24,977,406 bytes, SHA-256
  `78765ba4…fd58`) on 2026-10-03; both hashes are recorded in
  `data/external/external_receipt.json`.
* **Falsifiable gate.** On the buffered spatial holdout, the SGMC-augmented arms must beat the
  identical-architecture official-features-only arm on the *masked discovery* metric, and must not
  lose on the catalogue-retention metric. Failing either is a rejection.
* **Risk.** Positional quality of the 1:250,000 sheets is ~250 m, which is at the metric's 300 m
  tolerance; a naive emission would smear error into false-positive mass. The gate is therefore
  evaluated after the emission operator, not on the raw probability map.

### H1 measured status (2026-10-03) — the layer exists, and it is partly corroborated

The bridge ran on a GitHub runner and committed the layer. Verified from
`data/external/external_receipt.json` (run 37140924182, 2026-10-03T17:33Z):

| quantity | value |
|---|---|
| source archives | `NV.zip` 69,056,094 B SHA-256 `3b333ac0…7606`, `CA.zip` 24,977,406 B SHA-256 `78765ba4…4431` |
| SGMC line features inside the grid | 21,160 |
| rasterised pixels inside the footprint | 82,151 |
| connected components | 1,679 (median 21 px, max 1,794 px) |
| pixels more than 300 m from any catalogue fault | **61,664 (75.1 %)** |
| layer SHA-256 | `26d142c4…61b5c` |
| attribute schema | `STATE, DESCRIPT, MISC, REF_ID, SRC_URL, GEOM, WEB_GEOM, SYMBOL` — **no age field**; `DESCRIPT` carries certainty and sense of displacement (`certain` 37,797 + 3,610 thrust-certain in NV; `approximate` 9,893; `concealed` 2,180; `inferred or queried` 302) |

Two falsification tests were run, and they disagree in strength:

* **Corroboration test (positive).** 24.94 % of SGMC pixels lie within 300 m of a public-catalogue
  fault, against a footprint base rate of 8.61 % — a **2.9× enrichment** over chance. The layer is
  therefore not random linework; it preferentially marks real faults.
* **Independent-evidence test (weak).** Against a *local* control (partner pixels 1–2 km away,
  matched on distance-to-catalogue and terrain-slope decile, n = 58,494) the SGMC off-catalogue class
  is only marginally enriched in 1 m lidar scarp morphology: best band `step_max` AUC = 0.520,
  `downface_max` 0.522, everything else 0.49–0.52 (`docs/research/sgmc-falsification.json`). The
  positive control behaves the same way — catalogue faults themselves score only AUC ≈ 0.52 on this
  measure — so the test is low-power rather than negative: it cannot separate real from unreal
  linework with these bands.
* **Self-prediction test (negative, informative).** Hiding 30 % of SGMC connected components and
  emitting dots along the visible 70 % predicts the hidden 30 % *worse than a blind lattice*
  (0.00128 vs 0.09187 mean DTI at 5,700 vs 208,000 dots; the budget difference explains most of it,
  but the layer clearly is not self-similar at component scale). Do not assume local SGMC density
  extrapolates.

**Verdict.** H1 stays rank 1 but as an explicitly *unvalidated bet*, because 75.1 % of the layer is
information the catalogue does not contain and the admission bar under the metric is only
`0.2 × DTI ≈ 5.2 %`. Its inclusion in the shipped candidate is a bounded hedge (cost ≤ 3 % of the
DTI denominator for 5,281 dots), not a promoted result. There is no local frame that can validate it:
the catalogue frames cannot score off-catalogue strategies at all, and any frame built from the SGMC
itself is tautological for an emitter that uses the SGMC (see `docs/research/emitter-holdout.md`).

## H2 — 1 m LiDAR scarp curvature pair (rank 2)

* **Layers.** `data/external/lidar_scarp_features_u8.tif` (12 bands: `ex_max`, `ex_mean`, `step_max`,
  `lapneg_max`, `lappos_max`, `downface_max`, `upface_max`, `cross_max`, `relief`, `coh100`, `strike`,
  `valid`), derived from the USGS 3DEP 1 m DEM that the sponsor collected "coordinated with this
  effort" (About page).
* **Physical signature.** A fault scarp is a *monoclinal step*: it produces a spatially paired
  positive and negative second derivative across the scarp face (convex crest, concave base). The
  transform is an oriented Laplacian response pair, tracked along the local `strike` band, with a
  coherence requirement (`coh100`) so that single-cell noise does not fire.
* **Why it can catch a missing fault.** Published fault maps are compiled from field mapping and
  aerial-photograph interpretation. Scarps smaller than a metre — degraded, vegetated, or on
  un-mapped ground — are systematically absent from those compilations and are precisely what 1 m
  lidar reveals. The competition supplies `1m_DEM_links.csv` for exactly this purpose.
* **Difference from prior work.** Existing experiments used the 100 m `det_elev_slope` band and ridge
  transforms. Neither the 1 m-derived curvature pair nor an along-strike coherence filter has been
  used here.
* **Cost.** Low: the derived 100 m layer is already mirrored and hash-pinned; re-deriving from raw
  DEM tiles is a CI job, not a local one.
* **Source and obtainability.** USGS 3D Elevation Program, public domain:
  <https://www.usgs.gov/3d-elevation-program>; tile access via <https://apps.nationalmap.gov/>. The
  competition's own `1m_DEM_links.csv` (DrivenData, login-gated) enumerates the tiles. The derived
  layer used here is owner-mirrored from 706/716 tiles (recorded in
  `docs/research/mirror-pins-extra.json`); the primary source is verified reachable in principle but
  the raw DEM tiles are *not* in this checkout.

## H3 — Buried-structure magnetic/gravity lineaments: tilt-angle ridges with upward-continuation persistence (rank 3)

* **Layers.** `tmi`, `rtp`, `tmi_hg`, `tmi_vg`, `iso_grav_anom`, `iso_grav_anom_hg`,
  `iso_grav_anom_vg`, plus mirrored `TMI_up150` and ratio products.
* **Physical signature.** The tilt angle `atan2(dF/dz, sqrt((dF/dx)^2 + (dF/dy)^2))` is insensitive to
  source depth and produces ridge maxima directly over buried contacts and fault planes; ridge
  *persistence* across upward continuations of 150/300/600 m isolates structures that exist at depth
  rather than shallow noise.
* **Why it can catch a missing fault.** The catalogue is dominated by surface-expressed Quaternary
  faults. Structures buried under basin fill are absent from it by construction (C3), and the sponsor
  states geophysical data are required to detect them.
* **Difference from prior work.** The sibling repositories' "worming" test failed because the feature
  was emitted as sparse binary peak sets, nonzero on 0.001–0.084 % of the footprint. This hypothesis
  is a *field* formulation: a continuous, normalized persistence score per pixel, so the feature can
  actually influence a learned decision surface.
* **Cost.** Medium. Vertical derivatives and continuations are cheap; doing them at multiple scales
  on 12.3 M pixels on two CPU cores is not, so this would run in CI or on a downsampled grid.
* **Source and obtainability.** USGS GeoDAWN release, DOI 10.5066/P93LGLVQ,
  <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7> (public). Most bands are already
  inside the official 19-band stack.

## H4 — Thermal plumbing: spring geothermometry residuals and paleo-spring deposits (rank 4)

* **Layers.** GDR 1391 "Well and Spring Temperature and Chemistry" (`temp_c`, `geothermquartz_c`,
  `geothermchalc_c`, `geothermcat_c`), paleogeothermal features (sinter/tufa), and 2 m temperature
  probe surveys.
* **Physical signature.** Two transforms: (i) the *geothermometry residual* — measured spring
  temperature minus the temperature implied by its chemistry — is large where fluids rise quickly
  along a permeable structure; (ii) anisotropic kernel density of thermal points elongated along the
  local structure orientation, i.e. a fluid-pathway lineament field.
* **Why it can catch a missing fault.** A spring line with no mapped fault is direct surface evidence
  of an unmapped permeable structure. Sinter/tufa deposits record *paleo* upflow and survive after the
  spring dies, so they extend the record beyond currently active systems.
* **Difference from prior work.** Earlier attempts used a coarse "thermal pop" count and raw
  openness. The geothermometry residual and the paleo-spring deposit layer have not been used.
* **Cost.** Medium: the signal is sparse (a few thousand points in a 12 M-pixel grid), so it must be
  turned into a smooth field or it degenerates into isolated points.
* **Source and obtainability.** GDR 1391, CC BY 4.0, DOI 10.15121/1881483,
  <https://gdr.openei.org/submissions/1391>. Confirmed obtainable: `paleo_geothermal_regional.zip`
  (82.04 kB) and `2m_temperature_probe_INGENIOUS_regional_data.zip` (1.03 MB) are named download
  targets in `scripts/fetch_external_layers.py`; a subset of the well/spring table is already
  mirrored and hash-pinned (`data/external/gdr_wellspring_in_footprint.csv`).

## H5 — Geodetic strain localisation index (rank 5)

* **Layers.** `geod_shearrate`, `geod_dilaterate`, `geod_2ndinv` (official 19-band stack), optionally
  the full GDR geodetic shear/dilation grids.
* **Physical signature.** Strain-rate *localisation*: the ratio of the local second invariant to a
  long-wavelength background, which highlights narrow deforming corridors rather than broad
  regional trends.
* **Why it can catch a missing fault.** Geodetic strain is depth-integrated and independent of
  surface expression, so it can flag active structures that have no mapped scarp.
* **Difference from prior work.** The bands were previously used raw, and an earlier strain x
  conductance interaction pilot failed its registered screen. The localisation transform is the new
  element, and the prior negative result is a reason to rank this last, not to hide it.
* **Cost.** Low (layers are in hand) — but expected gain is the lowest of the five and it carries a
  documented prior failure.
* **Source and obtainability.** Nevada Geodetic Laboratory products distributed through GDR 1391
  (CC BY 4.0, `geodetics_INGENIOUS_regional_data.zip`, 51.99 MB) and the official feature stack.

---

## What is deliberately *not* proposed, and why

* **Predicting the catalogue.** Free under the mask (C1) and worthless — it cannot earn credit.
* **A denser version of the existing dotting.** The metric response surface shows spacing is already
  near the geometric optimum; extra density adds `FP_w` linearly for no extra `TP_w`.
* **Blind region-wide dispersion.** Measured: a spacing-4 lattice over the whole footprint scores
  0.246 against the *catalogue* proxy but collapses to 0.020 when the truth set is made sparse (4 % of
  catalogue density) — which is the regime the private test set lives in. Localisation, not
  dispersion, is the binding constraint.
* **Any use of `dist_known_fault_px` columns** in the GDR exports: those are derived from the labels
  and would be label leakage.
