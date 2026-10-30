# Repository review — 30 October 2026

## Decision

**NEGATIVE — no TIFF is approved to download or submit.** This checkout has an active duplicate-stop/lane restriction. No submission TIFF or new experiment was created, no holdout score was estimated, and no weekly slot was selected. This review is repository inspection only; it does not weaken any earlier stop or claim an improvement over a leaderboard result.

## Review scope and findings

Reviewed the project instructions (`AGENTS.md`), mission and operating brief in `README.md`, current-run/status records, 29 October repository review and run card, priority-site audit pages, the registry preflight verifier, and the project/test configuration.

1. **Safety controls are clear and fail-closed.** The project explicitly separates research promotion from slot selection, requires the shared evaluator/writer, preserves negative receipts, and disallows renaming/perturbing a stopped raster. The repository's current lane is not assigned; continuing into a new geological experiment would violate that rule. The historical 13GEMSDOE lattice witness has the recorded non-discriminating coverage issue and is still a duplicate stop, not a novelty clearance.
2. **No trusted score estimate is available for the nine historical sites.** The prior nine-site audit labels the supplied values as owner-reported and unverified; those are neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED. Its historical TIFFs are audit references, not upload recommendations. The 0.2778 H33-B2 explanation is a plausible pruning/coverage mechanism recorded in the 29 October review, but its causal contribution is unproven. The conflicting 0.3195 and 0.4413 claims are not a basis for a score forecast.
3. **Data/evaluation access remains the main scientific blocker.** The checkout contains derived external rasters, but no `data/raw/training_features.tif`, organizer-authenticated template/labels, or local environment dependencies were available to run the requested pipeline. An owner-controlled mirror can support reproducibility but is not organizer authentication.
4. **No new hypotheses were ranked or run here.** The repository already contains four frozen, unexecuted hypothesis proposals in [`docs/research/2026-10-28-review.md`](research/2026-10-28-review.md). A fresh ranking or experiment in this review would conflict with the single-lane instruction and existing cap/stop state. The next scientific step is gated on explicit lane/policy resolution and authenticated inputs; do not interpret this review as a lane assignment.
5. **No live site, leaderboard, submission portal, or slot cap was verified today.** Previously stored dated snapshots are historical evidence only. External-source links remain available in the prior review for manual audit.

## Verification attempted

- `git status --short`: clean before review.
- `python scripts/verify_registry_preflight.py`: **not run successfully**; failed at import because system Python lacks NumPy (`ModuleNotFoundError`).
- `python scripts/build_research_site.py --check`: **not run successfully**; failed because NumPy is missing.
- `python -m pytest -q`: **not run successfully**; pytest is not installed for system Python.
- No virtualenv is present in this checkout. These are environment-precondition failures, not passing tests and not evidence that the code is defective. The previous repository review records its distinct successful test run; this review does not claim to reproduce it.

No package was installed, no dataset fetched, no artifact regenerated, and no tracked scientific result changed. Re-run the documented test setup in an environment with the project's test extras and restore the pinned template inputs before treating verifiers as reproduced.

## Required next actions (gated)

1. Resolve the lane assignment and the duplicate-witness policy consistently; do not work around the 70%/3 px stop by reducing dot count or altering old rasters.
2. Restore organizer-authenticated competition features, labels and sample grid with provenance and hashes. Keep mirrors clearly labelled as mirrors.
3. Once authorized, freeze folds/controls, run the shared feature-alone leakage canaries and the shared spatially buffered holdout, recording evaluator version, withheld positives and 95% CI. Respect the three-experiment/two-hour cap.
4. Run surface-level and final-dot novelty checks against a complete current registry. A pass against the pinned witness alone is insufficient.
5. Only after holdout promotion and exact-byte validator checks may a separate selector consider a slot. Confirm the portal's [0,1] and nodata behavior from an actual receipt; the prior range error remains unexplained.

## Source pointers

- [Official competition overview / task](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [Competition report PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

Links are provided for traceability; no claim is made that these pages were fetched or their current contents checked during this review.

## Run card

```json
{
  "hypothesis": "No geological hypothesis tested; prior frozen proposals remain in docs/research/2026-10-28-review.md.",
  "mechanism": "Repository and prior evidence review only; no surface or raster generated.",
  "named_non_fault_process": "Not tested; no new signal was evaluated.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "evaluator_version": null,
  "withheld_positives": null,
  "registry_surface_correlation": null,
  "registry_final_dot_overlap": "No candidate generated. Existing duplicate-stop remains in force.",
  "raster_sha256": null,
  "validator_output": "No candidate; validator not applicable. System test attempts blocked by missing NumPy/pytest.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "ok_to_download_and_submit": false,
  "experiments_used": 0,
  "slot_selected": false
}
```
