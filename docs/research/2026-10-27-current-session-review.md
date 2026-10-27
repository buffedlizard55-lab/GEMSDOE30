# Current session review — 2026-10-27

## Executive decision

**No new TIFF was generated. No TIFF in this checkout is approved to download and submit.** The current registry preflight remains a verified, zero-experiment `DUPLICATE-STOP`. This is the correct outcome under the lane/novelty policy: do not reuse, rename, perturb, or lower the dot budget of an old raster to evade the stop. No weekly slot was selected or used. The machine-readable card for this review is [`current-session-run-card.json`](2026-10-27-current-session-run-card.json).

The currently linked nine-site table is in [`priority-executive-summary.html`](../../../priority-executive-summary.html). It now separates owner-reported historical values from a new-candidate score estimate; every new estimate is explicitly **not available**, because there is no validated new candidate and no defensible conversion from a catalogue holdout to the hidden leaderboard. Historical file links are for audit only, **not download recommendations**.

## H33-B2 (GEMSDOE32) and the reported 0.2778

The supplied `0.2778` is an **owner-reported historical score**, not an organizer receipt in this checkout. The byte-level fleet audit supports a lineage explanation: H33-B2 is a 37,654-dot pruned subset of an earlier 40,199-dot r1 raster, with 2,545 dots removed from the mapped-fault halo within 2 pixels. It is consistent with reducing false-positive cost while retaining nearby support under the 300 m triangular metric kernel. This is a physically plausible explanation for why a sparser derivative could rank above its parent, but the hidden test labels and score receipt are unavailable; therefore the amount of causal improvement attributable to pruning is **not identified**. A single scalar score cannot recover the hidden TP/FP components.

It is possible in principle for a genuinely better method to exceed 0.2778. This repository has no comparable organizer-confirmed estimate that establishes it will. POOL-1 is evidence of improved *catalogue hide-and-recover* performance, not evidence of a higher leaderboard score: its two-seed `HOLDOUT-DTI` result is not comparable to H33's owner-reported competition score, and its raster was duplicate-stopped.

**Leaderboard irregularity:** the request names 0.3195 as current; repository snapshots contain different dated public-leaderboard figures, including a 0.4544 snapshot. These are not a fresh portal receipt and are not reconciled here. DrivenData access is not scraped or monitored. Treat the present official leaderboard value as **unknown in this audit** and do not use either number as a score estimate.

## Nine-site executive record

The nine pinned source rasters and owner-reported values are preserved in the fleet audit. Values below remain claims, not `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`. “New estimate” is intentionally unavailable. The lattice percentages are mathematical lower bounds under the literal 3-pixel/70% rule, not individual pairwise measurements for each historical raster.

| Site | Pinned historical best (research reference only) | Owner-reported value | New-submission score estimate | Unique under literal rule? | Download and submit? |
|---|---|---:|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | Not available | **No clearance**; lattice lower bound ≥88.93% | No; historical reference only |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | Not available | **No clearance**; ≥84.92%; exact-value alias with GEMSDOE30 in the frozen fleet | No; historical reference only |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | Not available | **No clearance**; ≥89.16% | No; historical reference only |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | Not available | **No clearance**; ≥82.34% | No; historical reference only |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | Not available | **No clearance**; ≥84.92%; exact-value alias with GEMSDOE25 in the frozen fleet | No; historical reference only |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | Not available | **No clearance**; ≥83.46% | No; historical reference only |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | Not available | **No clearance**; ≥82.34%; known pruned lineage with G28 r1 and G36 PINN | No; historical reference only |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | Not available | **No clearance**; ≥84.12% | No; historical reference only |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | Not available | **No clearance**; ≥82.89%; frozen audit found H33-B2 plus 1,200 dots | No; historical reference only |

The strict bound derives from the pinned 13GEMSDOE witness: 5,160,724 of 5,167,373 footprint cells are within 3 pixels; 6,649 are not. For any candidate with `K` distinct in-footprint dots, at least `max(0, K − 6,649)` must be within 3 pixels. At `K = 44,090`, that is at least 37,441 dots (84.9195%), above the strict 70% limit. At `K ≥ 22,164` the bound alone proves a stop. **Below that budget is not an automatic pass** and must not be selected merely to avoid the bound.

## Candidate hypotheses — proposals only, no lane authorized

Repository search and the dated hypothesis register support the following as **unimplemented variants in this checkout**, not globally novel ideas. Related work exists: TAD tested radial distance-collar decensoring, vent proximity/feeder ideas were explored, and earlier work proposed drainage transforms. No candidate below is a claim that parallel teams have not tried it. The ranking is qualitative, balancing expected usefulness for the target and cost; no numerical DTI prior is defensible from current evidence.

| Rank | Candidate and layers | Target signature and reason it may find missing fault geometry | Difference from implemented work / main non-fault mimic | Data and viability | Relative holdout priority / cost |
|---:|---|---|---|---|---|
| 1 | **Polygon-conditioned concealment / observation propensity** — USGS SGMC map-unit age/lithology polygons plus relief and the existing label-free geophysical/scarp surface | Estimate where exposed-surface mapping is less likely under young alluvium or basin fill; reweight independent physical evidence rather than treating absence from the catalogue as absence of a fault. | The radial TAD collar is implemented and tested; the polygon-defined propensity model is not. It must beat distance-only and matched-random controls or it is merely a distance prior. Mimics: unfaulted basin fill, playas, paleoshorelines, and contacts. | Official source listed in the repo: [USGS State Geologic Map Compilation](https://mrdata.usgs.gov/geology/state/) (public-domain source record). Earlier `external_receipt.json` records NV/CA archive bytes, but those polygon archives are **not present in this worktree** and this URL was not fetched anew in this session. Restore/checksum the exact official packages and rasterize only map-unit polygons before considering it runnable. | Highest qualitative priority; low-to-medium compute, **data restoration first**. Potentially most relevant to the selection bias, but no numerical gain estimate. |
| 2 | **Buried-source-depth magnetic lineaments** — GeoDAWN/competition magnetic grids; upward continuation, tilt/analytic-signal transforms, Euler source-depth solutions | Track coherent magnetic lineaments whose inferred source is buried, then test if the overlying lineament predicts missing structure without an observable scarp. | Existing experiments use magnetic levels, derivatives, and edge/ridge features; this specific source-depth inversion/filter is not implemented. Mimics: dikes, pluton margins, volcanic/caldera architecture, flight-line artefacts. | Official source: [USGS GeoDAWN, DOI 10.5066/P93LGLVQ](https://doi.org/10.5066/P93LGLVQ). The pinned `training_features.tif` (418,912,844 bytes) and raw GeoDAWN inputs are absent in this worktree; the owner mirror is not organizer-authenticated. Restore and verify inputs before preregistration. | Second; medium processing and stronger independent geophysical rationale, conditional on restored inputs. No numeric score estimate. |
| 3 | **Drainage χ / normalized channel-steepness disequilibrium** — USGS NHD flowlines plus 3DEP DEM, fixed concavity index, basin-normalized χ and `ksn` profiles | Seek channel-profile disequilibria and aligned steepness changes across a corridor, which could preserve deformation after a scarp is buried or eroded. | Prior H-31-03 was a qualitative channel-offset/knickpoint proposal; the quantitative χ/`ksn` transform is not implemented. Mimics: lithologic transitions, capture, lava dams, roads, and DEM conditioning artefacts. | Official sources: [USGS TNM](https://www.usgs.gov/the-national-map-data-delivery) for NHD products and [USGS 3DEP](https://www.usgs.gov/3d-elevation-program). The older register records 35 products for one test bbox, but **full-footprint coverage, downloadable bytes, and current reuse terms remain unchecked**. This is not viable until clipped official files are obtained, checksummed, and aligned. | Third; potentially useful independent geomorphology but high data/conditioning cost. No numerical score estimate. |
| 4 | **Heat-flow anomaly and borehole-gradient corridors** — IHFC Global Heat Flow Database plus GDR well/spring measurements | Detect spatially coherent heat-flow anomalies or depth-gradient breaks that may indicate fluid circulation along concealed permeable structures. | Existing thermal work used spring temperatures, probes, geothermometry, and alteration; regional heat-flow anomaly and borehole-gradient discontinuity are different observables and are not implemented. Mimics: lithology, topographic groundwater flow, survey/sampling bias, and non-fault hydrothermal convection. | Official source recorded in the hypothesis register: [IHFC Global Heat Flow Database](https://ihfc-iugg.org/products/global-heat-flow-database), [DOI 10.5880/fidgeo.2024.014](https://doi.org/10.5880/fidgeo.2024.014). No dataset is staged or checksummed here and the number of in-footprint sites has not been counted. First verify the archive, license/attribution, and ROI count; if underpowered, reject before fitting. | Fourth; medium data cost and likely sparse coverage. No numerical score estimate. |

**Top candidate is not run.** The preflight run card states the assigned lane is unknown and a single valid registered raster already proves the duplicate stop under the literal policy. The training feature stack is absent. Starting any fit/holdout now would violate the stop and have no path to an acceptable downloadable raster. Reconsider only after explicit lane assignment and documented resolution of registry policy; then preregister the chosen candidate, run every feature-alone leakage canary, and compare pooled DTI/paired 95% CI against the same-protocol best before any selector step.

## Three-pass implementation and verification

### Pass 1 — inspect and implement

- Read `AGENTS.md`, the current README decision and owner prompt, `docs/current-run.json`, the registry-preflight card, its three-pass review, and POOL-1 evidence before editing.
- Reproduced the current registry proof after restoring only the pinned sample template, labels, and lattice witness. `training_features.tif` remains absent; no model or holdout was run.
- Found that `scripts/build_research_site.py` still entered a historical PTA/TAD build before dispatching on `latest_review`. This made current-site `--check` fail on the stale `index.html` and could only regenerate pages from obsolete status text. Added a fail-closed, early receipt-driven build route for the selected registry-preflight snapshot, with both preflight and POOL-1 verifiers required.
- Found that the status feed treated POOL-1's verifier as a pointer-based inspection; it reported a misleading `pointer` error and “inspection unavailable” although the standalone receipt verifier passed. Added a verifier-specific negative-result path and regenerated `docs/status.json`.
- Updated the nine-site table to distinguish owner-reported historical values from a new-submission estimate, clearly say “not available,” and state that historical rasters are not downloads for submission. Added the POOL-1 parallel result and link to current navigation from the same committed receipts.

### Pass 2 — review and fix

- Checked each nine-site row against `docs/research/2026-10-26-csr/fleet-audit.json`, and the lattice bound against the verified preflight run card. The page labels the bound correctly as a lower bound, not an individual overlap measurement or full-registry uniqueness pass.
- Checked POOL-1 displayed values against `run-card.json` and `novelty-dots.json`; the current generated pages state that its model mechanism improved HOLDOUT-DTI twice but its dots were duplicate-stopped and no TIFF was published.
- Reviewed hypothesis novelty against the current source/register and code search. Downgraded H-34-01 from “untried” to its exact distinction: radial collar decensoring was tried, polygon propensity is not. Marked all external-data checks that cannot be repeated from current local bytes as blocked, rather than declaring them ready.
- No downloaded artifact is named “OK to submit”; no new TIFF, filename, score projection, or slot selection is claimed.

### Pass 3 — tests and final cross-check

- `scripts/verify_registry_preflight.py`: **PASS as negative** — 37,441/44,090 minimum bound; historical CSR-1 44,084/44,090 within 3 px; no submission.
- `scripts/verify_pool_run.py`: **PASS as negative receipt** — two-seed HOLDOUT-DTI improvements reproduce from receipts; duplicate references remain blocking; quarantined raster is absent and was not restored or published.
- `scripts/build_status.py --skip-tests`: **PASS**; the refreshed feed now reports POOL-1 as a verified negative with both paired HOLDOUT-DTI contrasts and the duplicate references, not as an inspection error.
- `.venv/bin/python scripts/build_research_site.py --check`: **PASS** after rebuilding the receipt-driven current pages; this route is scoped to the selected current receipts rather than obsolete hidden caches.
- `.venv/bin/python -m pytest -q`: **418 passed, 5 skipped, 4 warnings, 7 subtests passed** after all implementation and regression-test changes. The five skips are optional PyTorch-dependent loss tests.
- `git diff --check`: **PASS** after all implementation and documentation changes. Final result is not a model experiment and does not meet a promotion or download gate.

## Limitations and next actions

1. No unique, policy-compliant downloadable candidate is authorized under the verified literal duplicate stop. Do not generate a TIFF now.
2. No current organizer receipt for the nine scores and no fresh leaderboard value are included. Never use owner claims or stale public snapshots as a forecast.
3. `training_features.tif` is missing, so the requested new holdout cannot run. The login-walled DrivenData page is not accessed; existing GitHub mirrors are owner supplied and not organizer-authenticated.
4. The historical repository-wide novelty inventory is not a live, complete parallel registry. A fresh complete registry and explicit policy decision are required for future work.
5. Several proposed candidates depend on externally staged data (SGMC polygons, NHD/3DEP coverage, IHFC archive); data presence, checksum, coverage, and reuse terms are preconditions—not assumptions.
6. Local format validation does not establish DrivenData acceptance. No upload automation, receipt, or weekly-slot selector exists.
7. The site builder is now current-receipt-aware for this `latest_review`; older branches of its historical builder remain for archived selectors. Future `latest_review` types must add a tested renderer branch rather than bypassing receipt verification.

**Reproduction commands** (from the repository root, `.venv` installed):

```bash
.venv/bin/python scripts/verify_registry_preflight.py
.venv/bin/python scripts/verify_pool_run.py
.venv/bin/python scripts/build_research_site.py --check
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_submission.py docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif --template data/raw/sample_submission.tif  # expected failure: zero outside footprint
```

The last command tests a historical negative only. It does not create an eligible file or explain the historical portal range rejection.
