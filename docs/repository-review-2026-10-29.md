# Repository review — 29 October 2026

## Executive decision

**NO — do not download or submit any of the nine historical TIFFs as a new entry. No new TIFF is approved; no slot was selected.** The requested goal of generating a unique, higher-scoring GeoTIFF is not met. This review deliberately makes no leaderboard-score estimate: no candidate passed a leakage-safe, same-protocol blocked holdout and the reported historical values lack organizer submission receipts.

This review obeys the repository's current stop conditions. The prompt does not unambiguously assign the single method lane referenced by its parallel-run protocol; the frozen 13GEMSDOE registry witness independently stops every historical selection under the literal `>70% within 3 px` rule. No new fit, feature evaluation, placement, raster, or submission-slot selection was performed. This is a negative result, not evidence that the project has achieved its competition objective.

## Nine-site executive table

The files and quoted values below are taken from the frozen priority audit. Values are **UNVERIFIED OWNER-REPORTED historical claims**, not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED` scores. The measured overlap and format result are byte/grid diagnostics against the pinned 13GEMSDOE witness and the local shared validator; neither establishes portal acceptance or score performance.

| Site | Historical file (audit reference only) | Reported historical value | Dots within 3 px of pinned witness | Local format validator | Defensible new-score estimate | Unique / OK to download and submit? |
|---|---|---:|---:|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 (unverified) | 99.9218% | PASS | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 (unverified) | 99.9161% | PASS | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 (unverified) | 99.9234% | PASS | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 (unverified) | 99.9097% | PASS | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 (unverified) | 99.9161% | FAIL (outside-footprint null convention) | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 (unverified) | 99.9179% | PASS | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 (unverified) | 99.9150% | FAIL (outside-footprint null convention) | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 (unverified) | 99.9140% | FAIL (outside-footprint null convention) | **Unavailable** | **NO — duplicate stop** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 (unverified) | 99.9176% | FAIL (outside-footprint null convention) | **Unavailable** | **NO — duplicate stop** |

The file names above identify historical artifacts for audit and are **not download recommendations**. The repository's [current submission guide](../executive-summary.html) and [byte-audit page](../priority-readiness-audit.html) say this explicitly. The machine receipt contains source links, immutable hashes, full validator checks, correlation diagnostics and counts: [`docs/research/2026-10-28-priority-audit.json`](research/2026-10-28-priority-audit.json). The frozen source files were restored from owner-controlled GitHub mirrors and pinned by SHA-256; that verifies byte consistency, not organizer authentication. The prior pairwise value audit also reports that GEMSDOE25 and GEMSDOE30 have identical in-footprint values despite distinct encoded TIFF hashes; treat them as an in-footprint array alias, not proof of identical files or an independent method.

## What the 0.2778 claim does and does not tell us

Among the nine values supplied in the request, **0.2778 is numerically the largest reported historical claim**. It is not tied in this checkout to an organizer receipt, and this is not a current leaderboard value. The archived raster-lineage audit identifies H33-B2 as a 37,654-dot selection derived from a 40,199-dot earlier raster after removing 2,545 dots near the mapped-catalogue halo. That supplies a plausible *mechanistic hypothesis*: selective pruning could reduce false-positive cost while retaining distance-kernel support near concealed faults. It does not establish that this caused the reported value, that the file was the scored submission, or that the same procedure would improve a new score. Hidden labels, exact score receipt and the organizer's full evaluation state are absent.

The supplied prompt also calls both **0.3195** and **0.4413** the current high at different points. The repository contains a historical leaderboard snapshot recording 0.4413 on 25 October 2026 and earlier, dated evidence for 0.3195; neither was refreshed from the live page in this review. Treat the discrepancy as unresolved. A future score prediction from these dependent, unverified examples would be false precision.

## Highest-scoring hypothesis proposals and status

The existing [28 October review](research/2026-10-28-review.md#four-candidate-hypotheses--proposals-frozen-before-any-implementation) already proposes and ranks four different hypotheses with layers, signal, confounder and falsification plan: (1) cross-profile parity discrimination, (2) basement-normalized conductivity-contact asymmetry, (3) gravity–magnetic edge disagreement localization, and (4) local strain–basement discordance. They are research proposals, not externally assigned lanes, and none is a measured score. Their qualitative ranks are not quantitative leaderboard forecasts.

No candidate was executed in this review. The mandatory protocol says a new experiment must stay in the single assigned lane; none is unambiguous here. Additionally, under the current fixed witness and literal uniqueness threshold, the audit proves that any raster with 22,164 or more distinct in-footprint dots must exceed 70% overlap with that witness. A smaller dot budget is **not** automatically unique and must not be chosen simply to evade the stop. It would be unsafe and scientifically unsound to fabricate a TIFF to satisfy the download request.

## Reproduction and verification (three passes)

### Pass 1 — establish the repository state

- Read `AGENTS.md`, the full README mission and owner prompt, `docs/current-run.json`, the continuation card, current nine-site audit and prior scientific reviews.
- Restored only small, SHA-pinned `sample_submission.tif`, `labels.tif` and the 13GEMSDOE witness through the documented GitHub mirror tool. No DrivenData login or credential bypass was attempted; owner mirrors are not organizer-authenticated.
- Restored the nine small historical references to the ignored local cache using `scripts/audit_priority_readiness.py --restore-only`; it wrote no evidence or prediction.

### Pass 2 — reproduce measurements and inspect failure modes

- `python scripts/verify_registry_preflight.py`: exit 0, **VERIFIED NEGATIVE**; reproduces the 37,441/44,090 minimum-overlap proof and historical witness diagnostics.
- `python scripts/audit_priority_readiness.py --check`: exit 0; remeasures all nine historical rasters offline and matches the frozen JSON/HTML audit.
- `python scripts/build_research_site.py --check`: exit 0; deterministic site receipts and rendered pages match.
- First test attempt before restoring the pinned template had one expected environment-precondition failure in a builder test; after restoring the documented inputs, the full suite passed. This is not reported as a passing first attempt.

### Pass 3 — full suite and final cross-check

- `.venv/bin/python -m pytest -q`: **438 passed, 5 skipped, 4 warnings, 7 subtests passed**. All five skips were optional Torch-based loss tests; PyTorch is not installed in this research/test environment. The four Rasterio warnings are pending deprecations.
- Confirmed `data/raw/`, `.venv/` and generated model/data products are Git-ignored. No tracked raster was newly generated or changed.
- Confirmed the nine-site audit reports no score estimate, no submission approval and no selected slot. The live leaderboard and live submission cap were not queried.

## Findings and open limitations

1. **Release blocker — no eligible submission.** Every named historical raster fails the literal novelty stop; four additionally fail local outside-footprint null validation. Do not upload any of them.
2. **Scientific blocker — method lane unresolved.** The stated protocol references a single method paragraph but does not clearly identify it in the provided prompt. Choosing one of several prior proposals would break the lane rule.
3. **Evaluation blocker — no comparative holdout result for a new candidate.** No new `HOLDOUT-DTI`, evaluator version, withheld-positive count or confidence interval exists for this session. No forecast is defensible.
4. **Evidence blocker — score provenance.** The nine values and current-leader claims have no organizer receipts in this checkout; the reported 0.3195 and 0.4413 snapshots conflict.
5. **Portal blocker — prior [0,1] rejection unresolved.** The exact rejected file and portal receipt are unavailable. A local validator cannot prove the portal's treatment of outside-footprint nodata or upload acceptance.
6. **Data provenance blocker.** The feature raster/cache is not included in this checkout. Existing SHA-pinned owner mirrors and prepared manifests do not establish that the local copies are organizer-authenticated. Full organizer data access remains required for valid training/evaluation.
7. **Test scope.** Optional torch losses were skipped; this run verifies the base test suite and existing negative receipts, not model training/inference. The current public-submission registry and weekly slot cap may have changed.
8. **External-site scope.** This review audits this repository and its frozen snapshots only. It does not edit any other GEMSDOE repository, query DrivenData, or claim to have re-read the listed Pages sites live.

## Required next actions

1. Keep the current fail-closed decision; do not publish a historical artifact as a unique submission.
2. Resolve the lane and duplicate-policy rules uniformly, then freeze a hypothesis, controls and buffered folds before any experiment.
3. Obtain permitted, organizer-authenticated features, labels and template with provenance/hash receipts. Test every feature alone on the shared spatially-blocked holdout; AUC above 0.90 is a leakage alarm until resolved.
4. Under the experiment/time cap, require the shared pooled 300 m triangular DTI (alpha 0.2, beta 0.8) to beat the same-protocol current best with paired 95% CI lower bound above zero. Screen the surface before placement and final dots after placement against a complete current registry; stop if Spearman >0.90 or >70% of dots lie within 3 px of a registry raster.
5. Run the shared writer/validator on exact saved bytes and establish the portal's actual range/nodata rule. Only then may the separate selector consider a weekly slot. Label any displayed value as HOLDOUT-DTI with evaluator, withheld positives and CI, or ORGANIZER-CONFIRMED from a receipt.
6. Refresh the dated official leaderboard snapshot and resolve the 0.3195/0.4413 conflict without automated scraping or using owner mirrors as official receipts.

## Source links for manual review

- [Official competition overview and task](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [Competition report / rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

These are source pointers, not claims that non-GitHub pages were successfully fetched in this environment. Current access here is restricted; the official pages, portal receipt, live leaderboard and weekly cap remain unverified in this review.

## Final run card

```json
{
  "hypothesis": "No new geological hypothesis was tested in this repository review.",
  "mechanism": "Reproduced the existing negative duplicate-stop, nine-site audit, and deterministic site checks only.",
  "named_non_fault_process": "Not evaluated; no new surface or feature was produced.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "evaluator_version": null,
  "withheld_positives": null,
  "registry_surface_correlation": null,
  "registry_final_dot_overlap": "No new candidate; historical audit rows all exceed 99.90% within 3 px of the pinned witness.",
  "raster_sha256": null,
  "validator_output": "No new candidate; not applicable.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "ok_to_download_and_submit": false
}
```
