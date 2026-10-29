# Repository review — 2026-10-29

## Decision

**NEGATIVE: no new TIFF is approved for download or competition upload; no weekly slot was selected.** This review makes no geological experiment, score estimate, prediction, or change to the registry policy. The existing stop is a deliberate safety gate, not evidence that the project has found a winning model.

## Pass 1 — inspect the current project

Reviewed `AGENTS.md`, the README mission and preserved owner prompt, `docs/current-run.json`, the 2026-10-29 continuation card/review, the nine-site readiness audit, package/test configuration, source tree, and CI workflows. The repository already preserves the key requested operating principles: fail closed on novelty, label holdout results separately from organizer receipts, prevent slot selection from being inferred from format validity, and retain negative experiments. It also has an executive page and site-specific pages for the nine requested sites.

The current repository evidence says the nine historical leader files are audit references only. The 0.2778 H33-B2 value and the other site values in the owner-provided list are not backed here by organizer submission-page receipts. The source audit reports all nine historical rasters above 99.90% overlap within 3 pixels against a pinned lattice witness; their file/score names therefore do not supply nine independent candidate strategies. `docs/research/2026-10-29-continuation-card.json` records no new holdout, no raster hash, no validator result for a new candidate, `ok_to_submit: false`, and a negative verdict.

## Pass 2 — reproduce and challenge

Created an isolated `.venv` and installed `.[research,test]` using the repository's constraints. Restored the SHA-pinned public mirror inputs (template, labels, lattice witness) and the nine historical audit inputs using the documented commands. These are repository-maintained mirrors; restoration does **not** authenticate them as organizer-provided data.

| Check | Result |
|---|---|
| `scripts/verify_registry_preflight.py` | VERIFIED NEGATIVE: minimum bound 37,441/44,090; historical CSR raster 44,084/44,090 within 3 px; no submission approval |
| `scripts/audit_priority_readiness.py --check` | Verified the nine historical byte audit; no new raster, forecast, or slot approval |
| `scripts/build_research_site.py --check` | Passed; receipts/download link/generated pages are deterministic |
| `python -m pytest -q` | 438 passed, 5 skipped, 4 Rasterio pending-deprecation warnings, 7 subtests passed |
| `git diff --check` | Passed |

Environment prerequisites mattered: before restoration the site check and one test failed because `data/raw/sample_submission.tif` was absent. After the documented mirror restoration, both succeeded. This is a reproducibility precondition, not a code defect. Five optional-loss tests were skipped because PyTorch is not installed; the complete training stack and organizer-authenticated feature raster were not available, so this review does not validate model training or official-data holdout performance.

## Pass 3 — findings and next work

1. **No score estimate is justified.** Historical owner-reported scores, archive HOLDOUT-DTI, and public leaderboard snapshots are different evidence classes. The values 0.4413 and 0.3195 supplied as the current leaderboard maximum conflict; neither was refreshed from an authenticated leaderboard receipt in this review. Do not project either into a candidate score.
2. **No unique candidate may be promoted under the present stop.** The site's existing nine-file audit and the pinned-lattice stop supersede the request to publish a TIFF. Do not create a renamed, re-encoded, or perturbed copy to evade it. A future surface must pass registry novelty before placement and final-dot overlap after placement, against a complete, frozen registry.
3. **The portal range error remains undiagnosed.** The exact rejected upload bytes and submission receipt are not available. A local format validator cannot identify what the portal checked or prove organizer acceptance. Do not claim a fix without the exact file and authoritative response.
4. **Scientific validation is data-blocked.** The official competition feature stack requires authorized access. The available owner mirrors and external derived rasters are not substitutes for the complete organizer-authenticated data/cache. Without it, no new leakage canary or same-protocol buffered-segment holdout can be reported.
5. **Recommended sequence:** obtain the complete stack through authorized access; resolve the method-lane assignment and apply one consistent novelty rule; freeze spatial folds/controls; run individual feature canaries; evaluate at most three experiments within two hours using shared tools; require a positive paired 95% CI against the same-protocol best; then validate saved bytes and invoke the separate slot selector only if every gate passes.

### Manual source links

These are source references for human review, not sources freshly verified in this restricted environment:

- [Competition description and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391)

## Final run card

```json
{
  "hypothesis": "No new geological hypothesis was tested in this repository review.",
  "mechanism": "Reproduced the documented negative duplicate-stop and offline site/audit checks only.",
  "named_non_fault_process": "Not evaluated; no new surface or feature was produced.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "evaluator_version": null,
  "withheld_positives": null,
  "registry_surface_correlation": null,
  "registry_final_dot_overlap": "No new candidate; historical nine-site audit reports >99.90% within 3 px against its pinned lattice witness.",
  "raster_sha256": null,
  "validator_output": "No new candidate; not applicable.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "ok_to_download_and_submit": false
}
```
