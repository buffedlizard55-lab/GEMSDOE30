# GDX-1 — sampling-effort-normalized geothermal chemistry (frozen plan)

Registered 2026-10-26, before new scientific fitting or metric inspection.
Read README's complete owner prompt and AGENTS.md first. This is an autonomous
continuation of the geothermal-corridor research, **not an externally allocated
parallel-run lane**: the owner prompt refers to a method paragraph but supplies
none. Assignment and full parallel-registry gates remain unknown. No portal
upload, selector, or weekly slot is authorized by this experiment.

## Audit before implementation

- The shared implementations are `gemsdoe30.holdout` (not a separate
  `evaluate_holdout.py`) and `gemsdoe30.submission` (not a private writer).
- Restored the existing SHA-pinned owner mirrors with
  `scripts/restore_public_mirrors.py`, prepared once with `prepare_data.py`, and
  verified every feature/label/mask cell. Dataset signature is
  `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`.
  Data placement is no longer a blocker here; organizer authentication remains
  unverified. Do not confuse an owner mirror with official data authentication.
- Fresh nine-repository inventory: `registry.json` (328 unique aligned byte
  sequences, 344 source TIFFs, one excluded grid, retrieved before this run).
  This inventory is public-snapshot-complete, **not** a complete parallel-run
  surface registry. New own artifacts will not compare against themselves.
- `tilt_alteration.build_hydrothermal_impulse` already tests cation-minus-quartz
  >=15 C or quartz >=130 C; simple chemistry thresholds are NOT untried.
  `vent_corridor_holdout.py` already tested proximity; do NOT relabel it novel.
- The 27,092-row GDR well/spring export has repeated samples per grid cell and
  a label-derived `dist_known_fault_px` column. It is prohibited as an input.
  CSV field presence and repeated-site counts are data observations, not scores.

## Four unimplemented constructions, ranked before testing

Expected improvement is an ordinal scientific priority, NOT a DTI estimate.
No credible numeric leaderboard projection is available. All named data are
already obtainable via the repo's hash-pinned public GitHub mirrors; no new
external data are required. The official provenance URLs below remain available
for review, but the network policy prevents a fresh request to non-GitHub hosts.

| Rank | Construction / exact layers and signature | Why missing catalogue faults? | Difference from inspected code; non-fault mimic | Expected utility / cost |
|---|---|---|---|---|
| 1 (only executed method) | **GDX-1**: GDR 1391 `temp_c`, `geothermquartz_c`, `geothermcat_c`; site-median, density-normalized 1 km Gaussian maps of reservoir-minus-measured temperature, signed cation/quartz discordance, and shared-reservoir excess. Joint model with local GeoDAWN magnetic/gravity gradients, raw elevation slope, and local gradients of `depth_to_base_surf` / `cond_surf`. | Cooling/mixing of an ascending fluid may retain a reservoir-temperature signal where burial erased a surface fault trace. Joint geophysical discontinuities test a structural explanation rather than a circular catalogue-distance prior. | Existing TAD uses a thresholded OR impulse; corridor uses unnormalized proximity. This construction divides chemistry-weighted smoothing by the count of chemistry-observed sites, deduplicates repeated samples, and includes a density-only matched control. Mimic: non-fault aquifer mixing / steam loss around lithologic contacts; sampling clustered around developed fields. | Highest of these untested constructions, uncertain and sparse / low CPU |
| 2 | **Two-population thermal contrast**: separately normalize GDR `well_*` and `spring_*` temperatures; use signed well-minus-spring local contrast conditioned on MT-surface gradients. | A buried upflow path can have a warm well population but cold diluted outlets away from mapped scarps. | No implemented model contrasts the two sample populations at equal spatial support. A well is NOT assumed deep; depth is absent from this export. Mimic: pumping, variable well depths, seasonal spring cooling. | Moderate-to-low / low CPU; not executed |
| 3 | **Scale-phase concordance**: real/imaginary local wavelet quadrature of `rtp` and `iso_grav_anom` at fixed 200/500 m wavelengths, normalized phase agreement rather than amplitude or ridge strength. | Buried offset contacts can align in phase across independent fields despite weak surface relief. | Existing texture uses profile lags, PTA tilt derivatives, MSDB Hessian/tensor amplitudes; none computes this quadrature-phase agreement. Mimic: an intrusive or caldera lithologic boundary; survey seams. | Moderate-to-low / medium CPU; not executed |
| 4 | **Scalar dilatation-efficiency interaction**: `geod_dilaterate / max(abs(geod_2ndinv), fixed unit floor)` with a label-free local magnetic/MT discontinuity indicator, no raw regional magnitude. | Distinguishes potentially dilatant structural corridors from broad high-strain but shear-dominated regions. | Raw invariants and MSDB transtension exist; this dimensionless signed ratio conditioned on a thermal/MT edge is unimplemented. Scalar invariants do NOT determine principal-strain azimuth: do not claim stress resolved on fault strike without tensor components. Mimic: regional postseismic/viscoelastic deformation. | Lowest / low CPU, strong regional confounding risk; not executed |

## Sources and evidence boundary

- Official organizer reference re-fetched from GitHub commit
  `aebe92f7c8a990f0e3443451b7a825d9afd6336b`:
  <https://github.com/drivendataorg/gems-prize-reference-solution>.
  Notebook cell 5 provides the feature order; cell 16 states loss alpha/beta.
  Its generic metadata are not proof of physical unit/derivative semantics.
- GDR 1391 INGENIOUS compilation: <https://gdr.openei.org/submissions/1391>,
  DOI 10.15121/1881483; archived provenance/CC BY 4.0 in `mirror-pins-extra.json`.
  CSV SHA-256 `122718e65bdf55aab0ee12ad20d80062f0deb1de957225a61ad880dd5dc196ea`.
- GeoDAWN official release: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>.
- Geothermal structure background (archived primary-source review, not newly
  fetched literature): `../geothermal-vents-knowledge.md`, Faulds OSTI 1110517,
  1148722, 1724109. The chemical cooling/discordance interpretation here is a
  **hypothesis**, not proof that a vent or unmapped fault exists.
- Competition target is fault structure, not a labelled vent-finding task:
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
  The live leaderboard, account weekly cap, deadlines and rules cannot be
  freshly checked under this sandbox's host allowlist. Owner values 0.2778,
  0.3195 and 0.4413 are retained separately as UNVERIFIED OWNER CLAIMS, not
  ORGANIZER-CONFIRMED or HOLDOUT-DTI.

## Exact frozen construction and experiment

1. Accept finite temperatures in [-50,400] C; missing/zero values are handled
   explicitly. Collapse each *paired measurement's* contrast to its site-pixel
   median, not a difference between unrelated medians. For each of three
   chemical marks, use only rows where the required measurements coexist:
   `clip((quartz-temp)/100,-3,3)`, `clip((cation-quartz)/100,-3,3)`, and
   `clip((min(quartz,cation)-temp)/100,-3,3)`.
2. For each mark, a 1 km Gaussian (sigma=10 pixels, truncate=3) normalized by
   the smoothed count of sites with that mark. At effective count <0.05 sites
   (Gaussian weights rescaled by 2*pi*sigma^2), use zero; include the separate
   effort channel `log1p(smoothed site count)` and a coverage indicator for
   each mark. This avoids treating absent chemistry as measured equilibrium.
   Equal site weight, no names, thermal class, catalogue distance, or IDs.
3. Local physical channels: absolute `tmi_hg`, absolute gravity-slope channel,
   raw `det_elev_slope`, normalized-finite sigma=1 (truncate=2) gradient
   magnitudes of bands 15 and 17. These are derivative *proxies*; no claim that
   `depth_to_base_surf` is definitely basement or `cond_surf` a temperature.
   Total channels: 5 local physics + 1 effort + 3 values + 3 coverage = 12.
4. Fixed arms in **one** paired experiment: `gdx12` candidate;
   `effort6` (same local physics plus sampling effort, no chemical values);
   `core19` exact cached raw-feature reference. HGB 120 iterations, 31 leaves,
   learning_rate=0.1, early_stopping=False; identical train coordinates,
   6 negatives per visible positive, seed=3070+fold; training-only median/IQR.
   The current same-protocol core19 reference must reproduce
   HOLDOUT-DTI 0.13982063017811727 with the original 44,090 dot operating point
   and 17 px buffer. If it does not, mark comparator parity unknown, never
   substitute a historic score. Prior strongest differently-protocol models
   have no reserved, independent current-best confirmation; that gate remains
   unknown even if core19 is beaten.
5. Shared whole-component quadrant folds, **buffer=46 px** for the new
   chemical marks (Euclidean support <=sqrt(30^2+30^2)=42.43 px +3 px metric
   reach <46). The raw core19 parity reference is rerun separately on the
   original 17 px folds; results must not be mixed with the new protocol.
   Nothing depends on catalogue values except labels and pixel-exact masking
   from `fold.visible`; withheld/guard faults are never distance inputs.
6. All 28 unique raw/extra features tested **alone**, bidirectional raw AUC
   and train-only univariate HGB AUC, every fold, before interpreting DTI.
   AUC>0.90 in either direction blocks trust; constant channel AUC=0.5.
7. Count-matched score-ordered 3 px Poisson disks, 44,090 * active domain / full
   footprint dots per fold; final full-fit domain excludes exact catalogue
   pixels plus a declared 2 px emission halo (not the official scoring mask).
   Final count=44,090. The halo uses only visible catalogue for holdout.
8. Fit the frozen full candidate, audit saved continuous surface against the
   328-entry registry **before any placement**. Stop permanently on rho>0.90;
   otherwise write final dots via shared writer and audit rho>0.90 or >70%
   within 3 px. Any duplicate: log and stop, no parameter retries or jitter.
   Partial registry never certifies global uniqueness. Save the surface for
   reproducible later comparisons; large arrays stay ignored.
9. Shared evaluator `component-holdout-v3-blockstats-20261025`, pooled DTI
   (alpha=.2, beta=.8, 300m triangular support), 128 px geographic blocks,
   2,000 paired bootstrap draws, seed=3071, 95% percentile CI.
   GDX must beat **both** same-run comparators with positive paired CI lower
   bounds, no canary alarms, no dot shortfall. Otherwise negative. Even a pass
   is not slot approval: full registry, assigned lane, current-best confirmation,
   calibration/stability checks and separate selector are unresolved.
10. Budget <=3 experiments / <=2 hours. One frozen paired experiment planned;
    one raw core19 parity verification is reported separately as a second
    experiment conservatively. No tuning or rescue experiments. No slot used.

## Delivery and validation

Publish a new TIFF only if neither observed novelty stage triggers a duplicate.
Negative holdout artifacts may be downloaded as **research only**, with all
approval flags false. A duplicate-stopped TIFF stays quarantined in ignored
outputs, not advertised as unique or downloadable for upload. Every metric
must have HOLDOUT-DTI, evaluator, positives and CI; leaderboard estimates are
null without organizer receipt/calibration support. The submission name binds
to prediction values and date; note <=140 characters. End with a JSON run card.
Three review passes: implementation/tests; bugs and edge cases; original-task
reconciliation, CI, Pages and PR merge. Never claim all original ambitions were
met if no promotable high-scoring artifact exists.
