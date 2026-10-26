# Geothermal-corridor lane — review (2026-10-26)

**Deliverable:** a unique, one-click-downloadable, machine-validated GeoTIFF and an
unambiguous machine verdict. **Verdict: download OK, NOT OK to submit**
(`ok_to_submit=false`, `verdict=negative`, no slot selected, organizer score: none).
Machine receipts: [run card](run-card.json) · [readiness](readiness.json) ·
[validation](validation.json) · [pinned-registry novelty](novelty-dots.json) ·
[downloads novelty audit](novelty-downloads-audit.json).

## What was built

`GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif`
(SHA-256 `0ed2670200159cab23436a5033a90d7582accc63811756d3393441c6bbdac564`,
375,154 bytes, 40,000 binary dots), written by
`scripts/build_geothermal_corridor_submission.py` through the shared
`gemsdoe30.submission.write_submission_file` (no private writer/evaluator):

- Belief = weighted linear pool of `exp(-distance/1000 m)` proximity surfaces:
  GDR Quaternary volcanics 0.4, GDR paleogeothermal springs 0.3, GDR 2 m
  temperature probes 0.3, multiplied by `(0.75 + 0.25 × SGMC-proximity)`.
- Domain = template footprint with distance-to-SGMC **> 2 px** and belief > 0.10.
- Emission = `poisson_disk_select_ordered`, radius 3.0 px (300 m kernel scale),
  capped at 40,000 most-confident dots; values {0,1}, NaN outside footprint.
- Portal note (110/140): `Geothermal corridor off-cat: Q-volcanics x
  paleo-springs x 2m probes, SGMC-gated, 3px Poisson disk, 40000 dots`.

Validation without any human inspector: 12/12 `validate_submission_file`
checks (single float32 band, EPSG:32611, 3730×3292, transform/shape identical to
template, finite [0,1] on all 5,167,373 footprint cells, NaN outside). This
directly prevents the portal failure *"Predicted values must be in range
[0, 1]"* inside the footprint.

Uniqueness (lane thresholds: Spearman ≤ 0.90, ≤70% of dots within 3 px):
vs all 23 submission rasters in `docs/downloads/`, max Spearman **0.018**,
max 3 px overlap **60.6%** (dense 80k edge-hybrid; next 39.2% vs G30-TAD,
17.2% vs the GEMSDOE25 0.2600 file, 17.2% vs d28, 19.8% vs PTA-1, 26.5% vs
MSDB-1). The pinned-registry decision stays `blocked-incomplete-evidence`
because that registry is explicitly incomplete (3 scored files absent).
Best-submission files for GEMSDOE27/28/31/32/33/36 are not present locally, so
no direct file comparison against those six is claimed.

## Focus sites: best owner-reported submission each (unverified claims)

| Site | Best owner-reported submission | Score |
|---|---|---:|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan | 0.2477 |
| GEMSDOE25 | dotted-h19-5-d2-8-20261002-e56ea318af89-nan | 0.2600 |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan | 0.2449 |
| GEMSDOE28 | h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan | 0.2710 |
| GEMSDOE30 | d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca | 0.2600 |
| GEMSDOE31 | h27-4-solo-d28-20261004-8acb75e1-nan | 0.2708 |
| GEMSDOE32 | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | **0.2778** |
| GEMSDOE33 | h33d-analog-tip-stepover-r30-20261004-cb490425926e | 0.2632 |
| GEMSDOE36 | anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros | 0.2750 |

All nine scores are owner/user-reported, with no organizer receipt in this
repository. They are a reference frontier, not verified facts.

## Why GEMSDOE32's H33-B2 (0.2778, owner-reported) topped the fleet

Full verified analysis: [`2026-10-25-lsm/why-h33-scored-0.2778.md`](../2026-10-25-lsm/why-h33-scored-0.2778.md).
In brief, with each claim's class labelled there:

1. **It is a pruning trajectory, not new signal (byte-verified lineage).**
   h19-5 support (121,131 px, 0.1922) → 280 m Poisson thinning D2.8 (44,090,
   0.2600) → drop dots at catalogue distance ≤1 px, r1 (40,199, 0.2708) →
   drop ≤2 px, H33-B2 (37,654, 0.2778).
2. **Metric mechanism (published formula).** With pooled
   `DTI = T / (0.2T + 0.2F + 0.8G)` and TP credit a *max* over the 300 m
   kernel, credit never stacks: redundant dots add FP mass only. Known faults
   are masked pixel-exactly (DrivenData staff, forum 11516), so dots in the
   1–2 px unmasked flank pay full FP while earning ~0 TP (implied hit rates
   0.000–0.004 for the removed sets). Deleting them is pure gain.
3. **Same coverage, fewer wasted dots (projection).** D2.8/r1/H33/PINN all imply
   ≈40.5% hidden-truth coverage; H33 wins by wasting fewest dots (≈0.134 hits
   per dot vs 0.023 for random). Adding 1,200 dots back (GEMSDOE36 PINN) scores
   *less* (0.2750), confirming the added dots were below random productivity.
4. **Beating it needs better-localised belief, not more pruning.** At H33's dot
   budget, 0.3195 needs ≈0.155 hits/dot and 0.4413 needs ≈0.218 hits/dot
   (projection table in the linked analysis). Pruning the same belief further
   cannot supply that; new, expert-confirmable evidence per dot must.

Design rules this lane keeps from that analysis: binary dots at ~300 m
separation, nothing within 2 px of mapped structure, ~40k operating point.
What it changes is the belief: geothermal-discharge proximity (an independent
channel to blind-system structure per Faulds OSTI 1110517/1148722/1724109,
summarised in [`geothermal-vents-knowledge.md`](../geothermal-vents-knowledge.md))
instead of topographic/scarp or tilt/alteration evidence.

## Hypotheses considered (ranked; this session implemented #1 only)

| # | Hypothesis (layers / signature) | Why it can catch catalogue-missing faults | Difference from implemented lanes | Cost / gate |
|---|---|---|---|---|
| 1 (**implemented as screen artifact; holdout pending**) | Off-catalogue geothermal corridor: GDR volcanics + paleo springs + 2 m probes distance-decay pool, SGMC-proximity boost, >2 px off SGMC, 3 px Poisson | Blind geothermal systems (~39%+ of Great Basin systems, OSTI 1148722) discharge along faults the surface-rupture catalogue omits; locally 21/21 vents sit >300 m from catalogue truth | No shipped lane uses discharge-proximity as primary belief; TAD/PTA-1 use tilt/alteration/MT, S19/S20 lidar scarp, d28/h33 dot thinning of h19-5 | Low (layers already local, receipt-pinned). Gate: buffered whole-component holdout vs core19 — **blocked on organizer labels** |
| 2 | H-32-03 geothermometer discordance (GDR 1391 quartz/chalcedony/cation chemistry + `cond_surf`) | Mixing/steam-loss chemistry can mark upflow where no trace is mapped | Prior work used spring temperature/distance, not chemistry discordance | Low–medium; hold out whole geothermal systems; needs chemistry geodatabase restored+hashed (GDR 1391, CC BY 4.0 — obtainable) |
| 3 | H-31-04 radiometric alteration endmember lineament (GeoDAWN K/Th/U log-ratio residual with 300–700 m linear persistence) | Fault-fed alteration changes K-U-Th relations beyond mapped traces | Radiometrics used as raw channels before; endmember+persistence not implemented | Low–medium; GeoDAWN DOI 10.5066/P93LGLVQ official; lithology/flight-block matched controls required |
| 4 | H-32-02 volcanic feeder alignment × magnetic edge (multi-vent axial alignment corroborated by `tmi_hg`/`rtp` edge) | Dike/feeder swarms guiding vent chains are unmapped structure | Vent *proximity* tested near-random; alignment×edge corroboration not tested | Low cost, very low power (~21 local vents); exploratory only |
| 5 | H-31-03 drainage-response discontinuity (NHD flowline offsets/knickpoint chains) | Drainage preserves displacement after scarps erode/bury | No hydrology layer exists in repo | High; official USGS TNM NHD discoverable but bytes/terms/full-ROI coverage **not yet verified** — not viable until a clipped official product is downloaded, checksummed and aligned |

## Limitations and next steps (suggestions for the next session)

1. **Organizer data access is the single blocker to promotion.** `labels.tif`,
   `training_features.tif`, `sample_submission.tif` require a DrivenData login
   (data page redirects unauthenticated visitors); no credentials are handled
   here. With those files in `data/raw/` (run
   `bash scripts/download_competition_data.sh` then
   `.venv/bin/python scripts/prepare_data.py` on an unrestricted machine), run
   the buffered whole-component holdout (`gemsdoe30.holdout`) for this belief
   vs `core19`, single-feature canaries, and dots-on-catalogue counts. Only a
   holdout pass can flip `ok_to_submit`.
2. **Template is a proxy.** The grid was taken from the PTA-1 artifact (itself
   written on the competition grid), not from an organizer-authenticated
   `sample_submission.tif`. Re-validate against the true template once obtained:
   `.venv/bin/python scripts/validate_submission.py <tif> --template data/raw/sample_submission.tif`.
3. **Registry completeness.** Fetch best-submission files for
   GEMSDOE27/28/31/32/33/36 (and the 3 missing `data/raw/scored/` files) so the
   pinned registry can be attested complete and novelty re-run at both stages
   (surface + dots).
4. **SGMC ≠ organizer catalogue.** The >2 px halo and off-core counts are
   against SGMC mapped structure. Recompute against `labels.tif` when available;
   near-catalogue productivity on the leaderboard is ~random (linked H33
   analysis §4), so consider re-emitting with the halo measured on the true
   catalogue.
5. **No score is claimed.** Any number for this file without a submission-page
   receipt would be a projection; none is reported. Organizer slots (3/week,
   1 final pick) stay protected until gates pass.
6. **GPU/model work remains future work.** The metric-shaped (Kervadec-style
   boundary + regional) UNet training path in `src/gemsdoe30/training.py` /
   `losses.py` still needs the organizer features and a GPU session; this lane
   deliberately used only public external layers available in-repo.
