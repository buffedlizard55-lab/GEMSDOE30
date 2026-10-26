# QPC-1: proposed quadrature-phase concordance (preregistered)

Frozen 2026-10-26 UTC, before the QPC transform, fitting, candidate placement,
canary, or new holdout. Read the complete owner prompt in README and AGENTS.md
first. The prompt refers to an assigned method paragraph but supplies none.
This is an **autonomous, unassigned exploratory lane**, not an assertion of a
parallel allocation. Do not select a competition slot. All outputs remain
research-only while lane allocation and complete parallel coverage are unknown.

## Hypotheses ranked before execution

The rankings express relative scientific priority, **not numerical DTI
projections**. None is claimed globally novel. The first is the only method
selected for this lane. The alternatives are proposals, not extra experiments.
All required numerical layers already have SHA-pinned owner mirrors; a pinned
mirror proves reproducibility, not organizer authentication.

| Rank / relative expected utility and cost | Layers and proposed physical signature | Why could this reach a fault missed by the catalogue? | Difference from inspected implementations; named non-fault mimic |
|---|---|---|---|
| 1 / highest, medium CPU | **QPC-1**: reduced-to-pole magnetics (`rtp`) and isostatic gravity (`iso_grav_anom`); at two fixed Gaussian scales construct co-located local high-pass/gradient three-vectors and their normalized signed dot product, plus within-field scale persistence. A joint classifier learns where agreement is informative rather than assuming a fixed polarity. | A buried density/magnetization contrast can persist without a mapped surface scarp. Joint fields may distinguish an overlapping structural boundary from one-field noise; this is a testable hypothesis, not proof of a fault or geothermal upflow. | `msdb.py` uses Hessians, gradient-strike coherence and a scalar edge gate; `texture.py` uses cross-profile lags; `phase_tilt.py` uses tilt/depth and dip-asymmetry. None of those computes this co-located normalized high-pass/gradient quadrature vector at two scales. A volcanic flow edge, intrusive contact, dike swarm, or survey leveling artifact can mimic it. |
| 2 / medium, low CPU | GDR well/spring temperature records; separately site-deduplicate and effort-normalize the two populations, then test their signed temperature contrast and coverage masks. | Deep or mixed subsurface circulation might leave contrasting local observations where the structural scarp is concealed. The data do not establish well depth. | `geothermal_chemistry.py` pools site chemistry and models paired reservoir-temperature contrasts; it does not contrast the two record populations with separate sampling-effort denominators. Pumping, unequal well depths, seasonal temperatures, aquifer mixing, and clustered surveys can mimic the signal. A site-class availability check is required before fitting. |
| 3 / lower, medium CPU | `depth_to_base_surf`, `iso_grav_anom`, and `det_elev`; compare the *signed curvature zero-crossing displacement* of independently smoothed subsurface and surface fields, conditioned on local relief. | A buried step can shift a subsurface inflection relative to a smooth alluvial surface rather than coincide with a surface scarp. | Existing basement edge models use gradient magnitude / ridge coincidence, and PTA uses step asymmetry; this proposed signed multi-field inflection displacement is not the same transform. An erosional fan or non-fault basin margin can produce the same offset. |
| 4 / lower, medium CPU | `det_elev` and radiometric total-count proxy (`tc`); use local cross-profile **change in curvature sign**, conditioned on a stable orthogonal background, rather than a shared edge amplitude. | A subtle buried or degraded surface break could perturb both relief and surface-material distribution even if no fault trace is mapped. | Existing MSDB aligns gradient directions, while TDX models potential-field texture displacement, not this radiometry/topography curvature-sign transition. Shoreline terraces, roads, drainage incision, and depositional contacts are plausible mimics. Band-6 semantics remain a provenance issue; do not equate it blindly with tilt. |

No new external layer is needed for QPC-1. For rank 2, the GDR release explicitly
lists well/spring temperatures and chemistry; the public release is CC BY 4.0
and the owner mirror has been hash-restored. Its licence does not establish
that the particular derived mirror preserves the official data without error.

## Verified source boundary

- [Official GEMS problem, labels, metric and format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): the target is **fault structure**, not a labelled vent inventory. A potential feeder is not proof of a geothermal vent.
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): magnetic/radiometric surveys, lidar context, and variable terrain clearance; marked CC0.
- [USGS Granite Springs Valley study](https://www.usgs.gov/publications/a-geophysical-characterization-structure-and-geology-northern-granite-springs-valley): derivative magnetic/gravity methods delineate both faults **and contacts**; a dike swarm is an explicit ambiguity.
- [USGS Argenta Rise study](https://pubs.usgs.gov/publication/70271418): joint gravity, magnetic and MT interpretation of a prospective blind system; no claimed vent discovery from these predictors.
- [DOE GDR 1391](https://gdr.openei.org/submissions/1391): INGENIOUS compilation, explicitly including well/spring temperature and geochemistry; CC BY 4.0.
- [Organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b): feature ordering baseline. Its generic band descriptions do not resolve every physical-unit ambiguity.
- [DrivenData terms of use](https://www.drivendata.org/termsofuse/): the prohibited-use section restricts automated monitoring; no leaderboard scraper or uploader is introduced. Access to the data tab redirects to login; the public mirrors are not an authenticated substitute.

## Frozen single experiment

- Inputs: existing prepared 19-band stack, label and footprint arrays only.
  No template values, catalogue distances, coordinates, GDR fault distances,
  full-catalogue derivatives, or withheld-label-derived features may be inputs.
  Treat source masks as missing, not as extreme values.
- Transform: on each of `rtp` and `iso_grav_anom`, at sigma 1 and 3 pixels,
  form `[I - Gσ(I), σ ∂x Gσ(I), σ ∂y Gσ(I)]` with Gaussian truncate=3;
  normalize vector dot products only when both energies exceed a fixed numerical
  epsilon. Calculate signed magnetic/gravity concordance at both scales and
  same-field cross-scale persistence for magnetic and gravity. Invalid source
  neighborhoods yield NaN, never zero-padded numerical artifacts. These are
  *phase proxies*, not calibrated monogenic phases or estimates of dip/depth.
  The maximum axial support is 9 pixels, Euclidean support <13 pixels; the
  17-pixel fold guard covers support plus the 3-pixel metric reach.
- Models: identical training data and standardization for 19-band `core19`,
  `core19` plus the two within-field persistence features, and the candidate
  `core19` plus all four phase-proxy features. Existing HGB, 120 iterations,
  31 leaves, learning rate 0.1, early stopping off, 6 case-control negatives
  per visible positive, seed 3041 + fold. No randomization sweep or tuning.
- Four whole 8-connected fault-component geographic quadrant folds, 17-pixel
  guard. Catalogue-derived information comes exclusively from visible labels;
  visible faults are masked **pixel-exactly**. The fold active-domain dot count
  is the recorded 44,090 full-footprint budget scaled by active area; 3-pixel
  fixed Poisson emission. Score pooled DTI with the shared evaluator, alpha .2,
  beta .8 and 300 m triangular kernel. Perform geographic block bootstrap with
  2,000 paired draws and report 95% CIs and 60,988 withheld positives if verified.
- Before trusting any result, run both raw bidirectional and train-only univariate
  heldout AUC canaries on **each of the 23 exact input features** in every fold.
  Any AUC >.90 is a leakage alarm and blocks promotion until explained.
- Strongest recorded comparable proxy: the FFL-1 LiDAR/MSDB `fusion_edge`
  **confirmation**, seed 3063, not the lower MSDB-only value. It is a known
  duplicate-stopped research system, never a submission. Before QPC execution,
  the archive was re-audited and its stronger confirmation was found. Its block
  statistics were not retained, so replay its exact fixed comparator in these
  same folds (no final FFL TIFF, retuning, or slot), test its 54 input features
  individually, and require its four per-fold TP/FP/counts to reproduce the
  frozen confirmation to 1e-6. If they do not, best-comparator evidence is
  UNKNOWN and promotion is blocked. The replay is conservatively counted as a
  second experiment within this lane's cap. Restore its existing SHA-pinned
  LiDAR descriptor mirror; it is not organizer-authenticated.
- Additional comparator: frozen MSDB-1v2 `msdb_edge` block statistics from
  `docs/research/msdb-piedmont/results.json`; require the same labels, evaluator,
  whole-component 17 px folds, active masks, per-fold budgets, and geographic
  block identities. Do not compare distinct masks/budgets as if paired. FFL and
  MSDB use different architectures and EDGE emission, so such comparisons
  compare systems, not the isolated QPC transform. Scientific improvement
  requires paired 95% lower bounds >0 versus FFL, MSDB, and the within-field
  control, with no canary alarms. Global registry, assigned lane, independent
  confirmation, authenticated data, and a separate slot selector remain needed.
- Save an actual full-fit continuous surface and compare it before final dot
  placement. Then compare final dots against the same frozen public reference
  snapshot. A rho >.90 or directional 3 px overlap >70% against any reference
  is an immediate duplicate-stop; never perturb, rename, or rescue. Original
  unshared surfaces, private parallel artifacts, paths outside the inventory,
  and invalid references are UNKNOWN, not passes. An invalid reference may be
  retained as explicitly unresolved **only for a negative research artifact**;
  never claim full uniqueness or submission approval from partial comparisons.
- One candidate experiment plus one exact strongest-comparator replay are planned; ≤3 experiments and ≤2 hours.
  Failure, duplicate-stop, uncertainty, or a negative result is a deliverable.
  No portal upload, weekly-slot selection, or numeric leaderboard projection.

## Frozen input identities before execution

- Broadened nine-site public `docs/` raster snapshot SHA-256:
  `251430967cd4e85cd81775be747146caa9f131e2d8bd9fe4bebd74839546a72f`.
  It is incomplete for private parallel work and outside-docs predictions.
- Historical MSDB sufficient-statistics file SHA-256:
  `aa303c861dcaea1e3ccceb5f143f0df1b1e2564255e93795bee69fd3f5087842`.
  Historical MSDB run card SHA-256:
  `d279ed302c0888f72c89eb8b6e3aa0e74e9738ac02e72e47beac89cc2bbd0e0e`.
  Historical FFL confirmation SHA-256:
  `6d310609524ec5d4ff0e129db6354a7731dedc1fb9c902d4be619a324f1e4b99`;
  FFL run card SHA-256:
  `1c79260c01298fa838da4eb0c1234df07d70ca0e1faa896ec9d67117246c00e3`.
  Dataset signatures must match:
  `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`.
- Freeze and verify code/package versions in `started.json`; no overwriting the
  start marker, no resume or post-result parameter adjustment.
