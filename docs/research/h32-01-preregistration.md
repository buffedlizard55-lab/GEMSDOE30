# H-32-01 preregistration — geothermal-discharge corridor holdout (frozen before the run)

**Frozen:** 2026-10-03, before `scripts/vent_corridor_holdout.py` was executed on real data.
**Hypothesis:** hot-spring discharge clusters mark fault-zone permeability conduits that the
USGS/INGENIOUS catalogue does not contain; emission near spring clusters therefore recovers
hidden ("new") fault components at higher credit per pixel than proximity-matched random
emission.

## Evidence base (all local measurements and official sources already recorded)

* 27,092 GDR wellspring rows → 12,570 unique grid cells; 512 cells with `temp_c ≥ 60`;
  256 with `temp_c ≥ 100` (max 296.5 °C).
* Hot cells (≥ 60 °C) are **2.3× enriched** within 300 m of catalogue truth versus the
  8.6 % footprint base rate (102/512 within 3 px), median distance 14 px (1.4 km).
* Faulds et al. (DOE OSTI 1110517, 1148722, 1724109): most Great Basin geothermal systems
  occupy steps, terminations and intersections of Quaternary fault zones; upflow commonly
  surfaces up to kilometres from the source structure; ~39 % of systems are blind.
* Catalogue-proxy caveat: the official metric masks catalogue pixels and scores hidden expert
  faults only (`docs/research/emission-anatomy.json` shows catalogue-proxy DTI inverts the
  owner-reported leaderboard ordering). This holdout is a necessary but biased proxy.

## Frozen design

1. **Split:** whole 8-connected catalogue components, interleaved hidden/known within 3.2 km
   centroid tiles (`gemsdoe30.holdout.split_components`). Screen split seed **31**;
   confirmation split seed **41**.
2. **Zones (spring data only — never catalogue geometry):**
   * `spring_buf_r3 / r10 / r20`: hot cells (≥ 60 °C) dilated by 3 / 10 / 20 px
     (300 m / 1 km / 2 km). Primary: **r10** (1 km — matches the Faulds observation that
     upflow surfaces km-scale from the structure; also matches the measured 1.4 km median).
   * `spring_corr_2_8km`: straight corridors between hot-cell pairs 2–8 km apart, buffered
     by 3 px (alignment signature).
   * Emission pools exclude hidden truth and masked known pixels.
3. **Controls:** `random_near_matched` (distance-to-known-fault-profile matched draws from the
   full emittable footprint; removes the ~2.3× generic proximity prior) and `far_random`.
   Confirmation also reruns the ≥ 100 °C subset as a sensitivity arm.
4. **Budgets:** 5,000 / 15,000 / 45,000 matched pixels per arm; **primary budget 15,000**;
   6 draws per arm (screen draw seed 131, confirmation 231).
5. **Scoring:** exact published index (`R = 300 m`, `α = 0.2`) on the masked domain
   (truth = hidden components). Quadrant diagnostics keep cross-quadrant 300 m credit and are
   informational except for the gate clause below.

## Frozen gate (all clauses required)

| Clause | Requirement |
| --- | --- |
| Screen pooled | `spring_buf_r10` − `random_near_matched` ≥ **+0.002** DTI at budget 15,000 (split seed 31) |
| Quadrant consistency | spring arm above matched control in **≥ 3 of 4** quadrants (screen) |
| Confirmation | pooled delta **> 0** on split seed 41 with fresh draws |

**Failure of any clause ⇒ not promoted. No submission slot may be spent on this hypothesis
unless the gate passes and a fresh-seed confirmation of the *emitted candidate* also passes
the project's standard promotion rules.** Any deviation from this document must be recorded in
the results file before the run is interpreted.

## Post-run recording requirements

Report: all arms × all budgets (mean ± std over draws), quadrant diagnostics, pool sizes,
gate result with each clause, and the catalogue-proxy caveat. Negative results are reported
in full.
