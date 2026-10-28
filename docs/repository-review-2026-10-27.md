# Repository review — 2026-10-27

## Executive decision

**No new submission GeoTIFF is available or approved. Do not upload or spend a weekly slot.** The registry preflight reproduces a mathematical duplicate stop against one pinned public 13GEMSDOE raster. A 44,090-dot candidate must have at least 37,441 dots within 3 pixels of that reference (84.9195%), exceeding the project’s strict >70% stop threshold regardless of placement. The previous CSR-1 file measured 44,084/44,090 (99.9864%) within 3 pixels and independently fails the published-format validator because it uses zero, rather than null/NaN, outside the footprint. The report of the earlier portal range error is still undiagnosed.

The requested historical leader H33-B2 (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`) is the highest owner-reported value in the supplied nine-site comparison: **0.2778, owner-reported and unverified**. It is not an `ORGANIZER-CONFIRMED` receipt and cannot be attributed to a specific causal improvement from the available hidden-test evidence. The pixel-lineage audit found H33-B2 is a prior raster with 2,545 dots near the visible catalogue removed; this is consistent with the competition’s mapped-fault exclusion strategy, but does not prove why its reported leaderboard value was higher. We cannot responsibly estimate a new candidate’s score or claim it exceeds 0.2778 or 0.3195.

| Site | Highest supplied historical selection | Reported value | Evidence status | Current download/submission decision |
|---|---|---:|---|---|
| GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE25 | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE30 | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE31 | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | Owner-reported; no receipt | Historical reference only; duplicate stop |
| **GEMSDOE30 current run** | **No new file generated** | **No estimate** | No new holdout or organizer receipt | **Do not download a historical raster as a new entry; not approved** |

The complete frozen comparison, filenames and lineage caveats are in the [nine-site executive summary](../priority-executive-summary.html) and [registry review](research/2026-10-27-registry-preflight/review.md). “Duplicate stop” here follows the owner’s literal 70%-within-3-pixels rule and the pinned witness; it is not a full proof of equivalence or a live inventory of all remote sites.

## Repository checks performed

1. Read the project README, full current-owner prompt, `AGENTS.md`, `OWNER_BRIEF.md`, current run pointer, status snapshot, current registry-preflight card/report, and existing three-pass review before changing files.
2. Restored SHA-pinned `sample_submission.tif`, `labels.tif`, and the pinned lattice witness from the project’s GitHub mirrors. These are owner/public mirrors, **not organizer-authenticated**. The training feature raster and complete training/cache inputs were not restored for a new model run.
3. Ran `.venv/bin/python scripts/verify_registry_preflight.py`: **verified negative**; 37,441/44,090 lower bound and 44,084/44,090 measured overlap reproduced. No experiment, new raster, submission name, note, forecast, or slot selection was made.
4. Ran current readiness and POOL-1 verification. Readiness remains negative: paired improvement and leakage-canary gates failed in the archived PTA-1 receipt; complete live-registry coverage is unknown. POOL-1’s archived mechanism result is positive on HOLDOUT-DTI but its artifact was duplicate-stopped; no TIFF was published. These historical holdout results are not leaderboard scores.
5. Ran the repository test suite: **415 passed, 5 skipped**, 7 subtests passed. The five skips are optional PyTorch-dependent tests; four Rasterio pending-deprecation warnings were reported.
6. Audited concurrent merges from PRs #56 (`POOL-1`), #58 (`GC-1` duplicate timestamp), and #59 (`VS-1`):
   - Verified `POOL-1` (`scripts/verify_pool_run.py`) and fixed `scripts/build_status.py` so `POOL-1` in `additional_stopped_attempts` verifies cleanly (`verified_now: true`).
   - Removed the byte-identical renamed duplicate `docs/downloads/GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif` (same SHA-256 `0ed26702...` as `20261026T160300Z.tif`) per `AGENTS.md` Rule 2, disabled CLI generation/scoring in `build_geothermal_corridor_submission.py`, `build_unique_submission.py`, and `evaluate_candidate_holdout.py`, and recorded exact `13GEMSDOE` lattice overlaps for `GC-1` (`39,960/40,000 = 99.9000%`) and `VS-1` (`37,654/37,654 = 100.0000%`, plus `13,098/37,654` dots directly on `labels.tif`) in `docs/research/2026-10-27-registry-preflight/postmerge-addendum.json`.
   - Checked the 21 named-prefix external repositories in the 2026-10-27 prompt (`KANLERGEMSDOE1..3`, `EUGGEMSDOE1..3`, `WBGGEMSDOE1..3`, `GINNYGEMSDOE1..3`, `GEMSDOEkarage1..3`, `ApartGEMSDOE1..3`, `GEMSDOESASS1..3`) via `api.github.com`: all 21 returned `HTTP 404 Not Found` and are logged as unverified owner text in `docs/score-ledger.csv`.
   - Regenerated all tracked Pages via `scripts/build_research_site.py` and verified `scripts/build_research_site.py --check`.

## Three-pass completion record

- **Pass 1 — implement and verify:** reviewed the active run pointer and registry evidence, reproduced the duplicate-stop, and regenerated the stale overview/submission-guide pages from the receipt-driven builder.
- **Pass 2 — bug and assumption review:** confirmed historical site scores are unverified claims, no competition-score estimate is supported, the current parallel registry is incomplete, and neither an archived TIFF nor a format-only pass authorizes submission. Identified missing training-feature data and the portal error’s unresolved cause.
- **Pass 3 — final cross-check:** reran all CI verifiers, the deterministic generated-site check, and whitespace validation; all passed. The full suite reported 414 passed, 5 optional skips, and 7 subtests passed. No new raster or submission slot was created.

## Experiments and submission gates

No geological hypotheses were run in this review. This was required: the current run card records no single assigned method paragraph/lane, and a valid registry witness already proves a duplicate stop for the requested 44,090-dot scale. The three-experiment cap is an upper bound, not a reason to proceed through a known stop. Do not evade the rule by lowering dot count. The current review describes four potential research directions as **proposals, not results**: regime-gated terrain/geophysics, buried contact discordance, drainage deflection, and alteration-ratio persistence. Each needs an explicit lane, a feasible complete novelty policy, preregistration, buffered leakage-safe holdout, feature-alone leakage canaries, and separate slot-selector approval before any upload decision.

The repository’s current site correctly says there is no file to submit. The old CSR-1 TIFF remains downloadable only as a historical research artifact and must not be submitted. A local format check, historical site score, or holdout metric is not portal acceptance or an organizer-confirmed score.

## Unresolved limitations / next work

- Obtain an explicit scientific lane and resolve the literal registry threshold/policy before further candidate generation. Keep the pinned lattice as a blocking witness until policy changes; don’t select a small budget to dodge it.
- The complete current registry is not known. Archived comparisons do not cover every newly published raster at both continuous-surface and final-dot stages.
- Restore and verify the full feature stack from a source whose provenance and authorization are understood. The DrivenData data page is login-protected; never bypass it or request/store credentials. Existing GitHub mirrors do not establish organizer authentication.
- Reproduce any proposed model using shared hide-and-recover tools: hold out whole fault components with spatial buffers; derive catalogue-based features from visible faults only; mask visible faults pixel-exactly; use the pooled 300 m triangular-kernel DTI; test each feature alone for leakage (AUC >0.90 is a warning); compare paired 95% CIs against the same-protocol best.
- Keep predictions and holdout DTI distinctly labelled. No estimate of competition score is supported by available evidence. Organizer-confirmed values require a copied submission-page receipt.
- Preserve the competition deadline discrepancy documented in the current review; plan for the earlier stated deadline and seek organizer clarification.

## Review source links

- [Official competition problem and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN magnetic and radiometric data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391)
- [Current machine-readable run card](research/2026-10-27-registry-preflight/run-card.json)
- [Current proof/reproduction review](research/2026-10-27-registry-preflight/review.md)
- [Project status JSON](status.json)
