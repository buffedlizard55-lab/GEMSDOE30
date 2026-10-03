# H-32-05 preregistration — buried range-front pinch-out edges (basement-surface step detector)

**Frozen:** 2026-10-03, before any scoring run. Harness: `scripts/basement_edge_holdout.py`.
**Registered result:** `docs/research/h32-05-basement-edge-holdout.json`.
**Status of this document:** design and gate are frozen. Post-hoc changes require a new
preregistration, not an edit to this file.

---

## 1. Hypothesis

Faults that are **buried beneath basin fill** have no topographic scarp, so they are systematically
absent from expression-based inventories (Quaternary-fault compilations require surface evidence).
Their displacement nevertheless persists in the **depth-to-basement surface**: a normal fault
offsetting basin fill against crystalline basement produces an abrupt step in basement depth even
where the ground surface is flat and unmappable. The detector therefore targets the **edge of the
basement-depth surface**, corroborated by an independent density-contrast edge field — not the
basement depth value itself.

### Verified external support (read 2026-10-03; primary USGS publications)

| Claim used in the design | Source | Link |
| --- | --- | --- |
| "Concealed basin faults … were mapped using horizontal gradients in the gravity field"; "Gradient maxima occur approximately over steeply-dipping contacts that separate rocks of contrasting densities" | USGS Open-File Report 2005-1154 | <https://pubs.usgs.gov/of/2005/1154/of2005-1154.pdf> |
| "these data are effective in mapping structure concealed beneath sedimentary cover" (gravity + magnetics) | USGS Open-File Report 2005-1154 | <https://pubs.usgs.gov/of/2005/1154/of2005-1154.pdf> |
| Gravity inverted to estimate depth to pre-Cenozoic basement; a lineation "that separates deep, undulating basement … from a shallow basement surface … may reflect a buried fault zone" | USGS Open-File Report 2000-189 | <https://pubs.usgs.gov/of/2000/0189/pdf/of00-189.pdf> |
| "undulations of the basement surface, interpreted to be caused by north-striking faults" | USGS Open-File Report 2000-189 | <https://pubs.usgs.gov/of/2000/0189/pdf/of00-189.pdf> |
| "at Devils Hole, Nevada, … springs are aligned directly above an abrupt step in the basement surface" (links basement steps to geothermal discharge) | USGS Open-File Report 2000-189 | <https://pubs.usgs.gov/of/2000/0189/pdf/of00-189.pdf> |
| "Various derivative and filtering methods were employed to delineate buried faults and contacts from gravity and magnetic data. A depth to basement gravity inversion …" — Northern Granite Springs Valley, **northwestern Nevada** (inside the competition footprint) | USGS publication 70259621 | <https://pubs.usgs.gov/publication/70259621> |
| GeoDAWN airborne magnetic/radiometric data release (public-domain USGS/DOE EarthMRI + GTO acquisition), DOI 10.5066/P93LGLVQ | USGS Science Data Release | <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> |

The Devils Hole statement is the strongest single link: it is a USGS-observed case in which **an
abrupt step in the basement surface controls the alignment of springs** — i.e. exactly the coupling
this competition is scored on (permeable structure hosting geothermal discharge) at a structure with
no mapped surface trace.

## 2. Layers used

Competition bands only (verified present locally; SHA-256-pinned, see `docs/research/mirror-pins.json`):

| Band (manifest name) | Index (0-based) | Verified stats inside footprint (2026-10-03) |
| --- | --- | --- |
| `depth_to_base_surf` | 14 | finite 5,167,373; min −14.84; median 316.36; max 7,135.31; σ 695.28 |
| `iso_grav_anom_hg` | 17 | finite 5,167,373; min −15.44; median 0.038; max 12.86; σ 2.038 |
| `tmi_hg` | 2 | finite 5,167,373; min 0.005; median 13.16; max 2,200.44; σ 40.85 |

**No catalogue geometry is used to build any arm.** The catalogue is used only (a) to define the
hidden/known component split and (b) to mask known pixels exactly as the organizer masks
USGS/INGENIOUS pixels.

## 3. Feature construction (frozen)

All fields are computed on the full 3,730 × 3,292 grid, restricted to the template footprint
(`valid & label_valid`); non-finite band cells are treated as missing and excluded from emission.

1. `dbs` = `depth_to_base_surf`, then **3 × 3 median filter** (gravity-inversion surfaces are smooth
   but carry interpolation artifacts; a median filter preserves genuine steps while suppressing
   single-cell noise).
2. `dbs_edge` = Sobel gradient magnitude of the median-filtered `dbs` (units: metres of basement
   relief per pixel, 100 m).
3. `dbs_coherence` = structure-tensor coherence of the same field,
   `(λ1 − λ2) / (λ1 + λ2 + ε)` from the 3 × 3 smoothed tensor, ε = 1e-9. Coherence ∈ [0, 1]
   separates **oriented** (linear, fault-like) edges from isotropic blobs. This is the physical
   discriminator: a range-front pinch-out is a line, not a spot.
4. `grav_edge` = `|iso_grav_anom_hg|` (already a horizontal-gradient product; independent physics —
   density contrast rather than geometry).
5. Rank fields by descending value inside the footprint (`rank_*`, 0 = highest).

### Arms (all emissions are deterministic top-N by rank; no within-arm sampling)

| Arm | Emission rule | Purpose |
| --- | --- | --- |
| **`basement_edge_corroborated`** (PRIMARY) | top-N by `rank(dbs_edge) + rank(grav_edge)` restricted to `dbs_coherence ≥ 0.5` | The hypothesis: corroborated, oriented basement steps |
| `basement_edge_only` | top-N by `dbs_edge` | Ablation: does corroboration add anything? |
| `dbs_magnitude` | top-N by `depth_to_base_surf` value (**not** its edge) | **Key novelty control** — this is how every prior use of the band worked (plain model feature). If the primary arm does not beat this, the transform is not doing the work. |
| `grav_edge_only` | top-N by `|iso_grav_anom_hg|` | Ablation: is the basement surface needed at all? |
| `random_near_matched` | count-matched draws from the whole emittable support with the primary arm's distance-to-known-fault profile | Removes generic "near mapped faults" proximity (measured at ~2.3× in the relay experiment) |
| `far_random` | count-matched uniform draws from the emittable support | Unmatched baseline |

Budgets: **N = 15,000** (primary, matching H-32-01 for comparability) and **N = 40,000**.
Ties in rank are broken by flat index (deterministic).

## 4. Holdout design

Identical in structure to the registered H-31-01 / H-32-01 harnesses (`gemsdoe30.holdout`):

1. 8-connected components of the catalogue; whole components assigned to a **hidden** half and a
   **known** half by the deterministic 3.2 km-tile centroid interleave (`split_components`, seed 31
   screen / seed 41 confirmation). Interleaving at fault-zone scale is required so the test measures
   within-zone geometry rather than regional proximity.
2. Hidden components are stand-in "new faults" (the only truth). Known components are masked out of
   every metric term, exactly as the organizer masks USGS/INGENIOUS pixels.
3. Emissions are additionally restricted to `valid & ~known` (never emitted on truth or masked pixels).
4. Score = the exact published distance-weighted Tversky index (`dti_from_components`, R = 300 m
   triangular kernel, α = 0.2), computed on the masked domain by `masked_dti`; per-quadrant
   diagnostics by `masked_dti_by_blocks` (diagnostic only; the pooled value is the decision statistic).

## 5. Registered gate (all clauses must hold)

1. **Screen** (split seed 31, N = 15,000): `basement_edge_corroborated` pooled DTI −
   `random_near_matched` pooled DTI **≥ +0.002**.
2. **Quadrant consistency** (screen, N = 15,000): the primary arm beats its matched control in
   **≥ 3 of 4** quadrants.
3. **Confirmation** (fresh split seed 41): pooled delta **> 0**.
4. **Transform clause (new, stronger than H-32-01):** on **both** splits the primary arm must beat
   `dbs_magnitude` at N = 15,000. Without this, the result is explained by "basement depth is a
   useful feature", which is already implemented everywhere in this repository and in the owner's
   sites, and the hypothesis as stated (the *edge* of the buried surface) is not supported.

**Failure of any clause ⇒ not promoted, no submission slot is spent.** A catalogue-component
holdout is a necessary but biased proxy: it can reward catalogue-like faults that the competition
masks. No number produced here is a competition score.

## 6. What would falsify the physical story (pre-declared)

* Primary ≈ `dbs_magnitude` → the step geometry carries nothing beyond the field itself.
* Primary ≈ `random_near_matched` → basement edges are just a proxy for "near mapped faults".
* Primary > `random_near_matched` but fails the transform clause → the win is a plain-feature effect,
  and the correct action is to add the band to the model, not to claim a discovery hypothesis.
