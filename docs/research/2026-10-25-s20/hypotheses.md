# Lane G30-S20 — candidate geological hypotheses (generated BEFORE implementation)

**Written:** 2026-10-25T22:02Z, before any S20 feature stack, canary, or holdout
was run (data restoration/preflight only was in progress). **Scope of “untried”:**
not implemented as specified in this repository (`src/`, `scripts/`, `docs/`
searched this session). That is not a claim about every private or external
project. **Every score-like number below is either OWNER-REPORTED (from the
owner's prompt, unverified, no organizer receipt) or a labelled HOLDOUT-DTI
from a repository receipt. Planning priors are qualitative rank aids, never
score forecasts.**

## Why the reported winner won, in one paragraph (the bar)

`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` — **0.2778 OWNER-REPORTED**
(GEMSDOE32) — was byte-reconstructed in this repo as exactly the GEMSDOE28
solo-d2.8 dot support with every dot at catalogue distance ≤2 px deleted
(37,654 of 40,199 dots, zero mismatching pixels;
`docs/research/2026-10-25/recipe-reconstruction.json`). Under the official
metric (distance-weighted Tversky, α=0.2, β=0.8, R=300 m triangular kernel —
[problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)),
TP credit per truth pixel is a **max** over nearby predictions while FP mass
accumulates per prediction, and known-catalogue pixels are masked from
scoring. Thinning + flank pruning therefore raise TP-per-FP efficiency without
any new geology. The lineage 0.1922 → 0.2477 → 0.2600–0.2708 → 0.2778
(all OWNER-REPORTED) is one belief surface refined by emission only
(Spearman 0.968, 100% of dots within 3 px of its parent). **Implication:**
more pruning of that family is exhausted and is a duplicate under this
session's novelty rules. Beating it requires a better *belief surface* —
more coverage of genuinely unmapped faults per unit FP mass — emitted at
least as efficiently. The live public leader read this session
(2026-10-25) is **0.4413** ([official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/));
0.3195 was the leader in a verified 2026-10-03 snapshot and is stale.

## The five candidates

| Rank | Hypothesis (layers · physical signature) | Why it should catch faults *missing* from USGS/INGENIOUS | Named non-fault mimic | Difference from everything implemented in this repo | Expected utility / cost |
|---|---|---|---|---|---|
| **1 — LANE G30-S20** | **Discovery-channel morphology + alteration habitat, with oriented line coherence.** Layers: owner-derived 1 m-DEM scarp stack `lidar_scarp_features_u8.tif` (USGS 3DEP; `ex_max, ex_mean, step_max, lapneg_max, lappos_max, downface_max, upface_max, cross_max, relief, coh100` + circular `sin/cos(2·strike)`), explicit scarp transforms `dipole=√(lapneg·lappos)` (crest-convexity × base-concavity pair = a step, not a generic slope) and `step_max×coh100`; GeoDAWN radiometrics `geodawn_rad_u8.tif` (K, Th, U, TC) + `geodawn_extensions_u8.tif` (Th/K, U/K, U/Th, TMI↑150 m) + gradient magnitudes of TC and Th/K; added to the G30-S19 19-band derivative habitat stack. Second stage: belief reweighting `B' = √(B · Lmax)` where `Lmax` is the max over 16 orientations of the 9-px (900 m) line-mean of `B`. | The hidden test faults were *manually identified by experts* (official problem page). A young fault scarp a few metres high in Quaternary alluvium is conspicuous in 1–2 m topography but is diluted to nothing in the 100 m `det_elev` bands and has no geologic-map trace (same alluvium both sides) — exactly the population a catalogue misses. Within-cell **max** aggregation in the scarp stack preserves that sub-pixel step. Radiometric ratios can be *offset* across a fault even where nobody drew one. Line coherence then requires along-strike persistence, which isolated noise speckles lack. | **Fluvial terrace risers and Lake Lahontan paleo-shoreline scarps** produce identical crest/base dipoles, and **lithologic contacts** produce identical radiometric ratio steps. | G30-S19 (current holdout best, HOLDOUT-DTI 0.2230) is a *pointwise* GBM on the 19 competition bands only. H-31-02/H-31-02b used scarp-orientation transforms *alone* (no radiometrics, no habitat GBM, no EDGE) and failed their gates. `emission_holdout.py` used only 4 scarp channels + radiometrics as ordinary inputs to a 22-feature quadrant model (no dipole, no circular strike, no line coherence, different frame; in that frame “all-22” 0.1499 vs “bands-10” 0.1238 pooled — measured, `emission-holdout-results.json`, *not* transferable as a quantity). `feature_value_holdout.py` exists but has **no result artifact** in this repo. Nothing in `src/` computes an oriented line-mean belief. | Highest expected lift / low cost. Both rasters are SHA-pinned (`mirror-pins-extra.json`) and restore via GitHub in this sandbox; no new external download is needed, so it is validatable today. |
| 2 | **Cross-contact magnetic texture displacement.** Layers `rtp`, `mag_anom`, `iso_grav_anom`. Signature: windowed phase/texture offset estimated on opposite flanks of an independently extracted gravity edge, retained only if the displacement direction/magnitude is consistent at two scales. | A buried strike-slip or oblique fault can laterally offset magnetic texture with no surface scarp and no mapped trace; edge *amplitude* methods cannot see a matched-but-shifted texture. | Intrusive lithologic contact (texture changes because rock type changes, not because it was displaced). | Repo basement-edge/coherence work ranks gradient ridges; nothing estimates a cross-edge displacement field. | Moderate expected lift / medium–high cost (windowed phase correlation over 12.3 M cells on 2 CPU cores; orientation bookkeeping). Deferred: exceeds what can be validated carefully in this session's budget. |
| 3 | **Residual demagnetization corridor.** Layers `mag_anom`, `rtp`, `tmi_vg` conditioned on `iso_grav_anom` + broad spatial trend fitted on training blocks only. Signature: coherent *negative* residual ribbons after removing the gravity-predicted magnetic response. | Hydrothermal alteration along a buried fluid pathway can destroy magnetite, leaving a magnetic low with no lithologic reason to be mapped as a fault. | Non-magnetic sediment fill in a paleochannel or basin. | Existing work uses absolute magnetic amplitude/gradients or ridge coincidence; no conditional residual field exists in `src/` or `scripts/`. | Uncertain lift / medium cost; residual definition is easy to leak through trend fitting if not blocked carefully. |
| 4 | **Conductivity-curvature saddle × basement ramp.** Layers `cond_surf`, `depth_to_base_surf`, `iso_grav_anom_hg`. Signature: Hessian saddle topology (det H < 0, oriented) in conductivity intersecting a basement-depth ramp, rather than high conductivity or edge amplitude alone. | A fault breaching sedimentary cover can juxtapose conductive units at a cover transition where surface mapping is blind. | Saline basin groundwater / sediment-facies transition. | Goes beyond vent-corridor coincidence and basement-slope ranks by testing an explicit saddle *topology*; not implemented. | Low–moderate lift / low cost, but interpolation artefacts in `cond_surf`/`depth_to_base_surf` are a first-order risk. |
| 5 | **Pure radiometric 3-endmember unmixing along lineaments (H-31-04 standalone).** Layers K/Th/U + ratios only. Signature: compositional (log-ratio) endmember residual required to persist 300–700 m along a lineament, with a lithology-matched null. | Fault-fed alteration can enrich K / mobilise U along a trace with no mapped fault. | Lithologic unit boundary (ratios primarily track rock type). | Radiometrics have been used as ordinary GBM inputs; an explicit unmixing + persistence + lithology-null test has not. It is *subsumed as features* by Rank 1, so the standalone form is ranked last — Rank 1 tests whether radiometrics help at all in the strong model before anyone pays for the fragile standalone version. | Low lift / low cost. Official source: USGS GeoDAWN DOI [10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ) (public-domain USGS release, [ScienceBase 657e1d85…](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)); local rasters are owner-derived quantisations, hash-pinned, obtainable. |

## Lane decision

This session's single lane is **Rank 1 (G30-S20)**. The prompt's “single
method paragraph” was again not identifiable in the received text, so the
lane is **self-assigned and frozen here before any result** (irregularity
IR-S20-01). Staying in-lane means: the only new information channels are the
lidar-scarp and radiometric layers above; the only new transform is the
specified oriented line coherence; catalogue-distance fields are never model
inputs; fault-vector-derived rasters already in `data/external/`
(`derived_gdr_qfaults_v2`, `derived_sgmc_faults`) are **excluded** because
they overlap the labels/catalogue and would leak catalogue tracing (the repo
receipt records only 1 of 59,065 Qfaults-v2 pixels >300 m from the catalogue).

External sources needed for Rank 1 and their obtainability, checked this
session: **none beyond the two SHA-pinned owner-derived rasters**, whose
official origins are USGS 3DEP (no use restrictions; owner metadata receipt,
706/716 tiles) and USGS GeoDAWN DOI 10.5066/P93LGLVQ (public domain).
Owner-derived ≠ organizer-authenticated; hashes verify consistency only
(IR-S20-02). Direct USGS/ScienceBase hosts are outside this sandbox's
allowlist, so the validated path is `scripts/restore_public_mirrors.py`
against `docs/research/mirror-pins-extra.json` pins — the same mechanism
prior sessions verified.
