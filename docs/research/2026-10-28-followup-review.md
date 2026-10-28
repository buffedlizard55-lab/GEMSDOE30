# Repository follow-up review — 2026-10-28

## Scope and decision

Read `AGENTS.md`, the current decision and owner prompt in `README.md`, `docs/current-run.json`, the 2026-10-28 audit review/run card, and the source pages and tests. This was a verification/documentation pass only: **zero new scientific experiments, no candidate raster generated, no score estimate, no upload, and no slot selected**. Existing mandatory duplicate-stop/lane protocol remains controlling. No new submission is cleared for download-and-submit.

## Work performed

The ignored `.venv` was recreated with the repository's research/test extras (excluding optional PyTorch); the pinned owner mirrors for `labels.tif`, `sample_submission.tif`, the 13GEMSDOE witness, and nine frozen historical TIFFs were restored using existing repo tooling. These files are SHA-pinned owner mirrors, not organizer-authenticated competition data. No credentials or organizer login were used.

Verified commands/results:

| Command/check | Result |
|---|---|
| `python scripts/audit_priority_readiness.py --restore` | Reopened all nine immutable historical raster references and reproduced the negative audit. No prediction was written. |
| `python scripts/verify_registry_preflight.py` | `VERIFIED NEGATIVE`: 37,441/44,090 minimum lattice overlap; historic CSR-1 44,084/44,090 within 3 px; no submission. |
| `python scripts/build_status.py --skip-tests` | Refreshed the machine-generated status feed from locally present mirror files and current verifier evidence. It explicitly preserves `organizer_authenticated: false`. |
| `python scripts/build_research_site.py` then `--check` | Rebuilt deterministic pages; check passed. The build correctly replaced stale `docs/executive-summary.html` content with a redirect to the canonical root submission guide. |
| `python -m pytest -q` | 432 passed, 5 skipped, 4 warnings, 7 subtests passed. Skips are optional PyTorch-dependent tests; warnings are Rasterio `Affine` multiplication deprecation warnings. |
| `git diff --check` | Passed. |

The before-state lacked local `data/raw` mirror files, so the initial audit could not run; after the documented restore, the checks above completed. The mirror restoration and `.venv` are ignored and not included in the patch.

## Findings and limits

1. **Submission decision remains negative.** Each of the nine target-site leaders is duplicate-stopped against the pinned witness. This is a literal threshold comparison, not a performance claim. Historical scores remain owner-reported absent organizer receipts. The 0.2778 H33-B2 claim is not an organizer-confirmed score, and no score estimate is defensible from the audit.
2. **No novel hypothesis was run.** The prompt does not provide an unambiguous single assigned method paragraph. Existing `AGENTS.md` explicitly blocks another lane/fit until policy and assignment are resolved. Do not bypass by changing the dot budget or renaming/re-encoding a stopped raster.
3. **Training/holdout limitations remain.** The restored label/template mirrors are not the complete authenticated organizer dataset; training features and a leakage-safe candidate holdout comparison are not made available by this work. Therefore no newly generated candidate could be scientifically promoted here.
4. **Publication state:** the repository builder previously reported `docs/executive-summary.html` stale; rebuilding restored the intended redirect to the canonical root guide, and deterministic check now passes. The site is generated statically; deployment is separate from local verification.
5. **No cross-repository edits** were made. Other GEMSDOE Pages and external participant repositories were not modified or treated as a complete live registry.

## Three-pass review

- **Pass 1 — inspect and verify:** followed session instructions, restored pinned inputs, reproduced the nine-site audit and registry stop.
- **Pass 2 — check defects and edge cases:** found a stale generated docs submission-guide page and stale generated status; rebuilt from the repo's source-of-truth generators. Re-ran focused registry tests and full test suite.
- **Pass 3 — compare against request:** confirmed the executive pages say which items are historical, distinguish owner claims from HOLDOUT-DTI and organizer-confirmed values, and do not imply that any file is approved to submit. The requested unique downloadable *approved submission* cannot be produced without violating the duplicate-stop and promotion gates, so the project clearly retains a negative verdict rather than fabricating one.

## Outstanding work / blockers

- Obtain the complete official competition dataset through permitted DrivenData access; authenticate its provenance and checksums. Do not infer official access from owner mirrors.
- Resolve the lane assignment and duplicate-registry policy with the project owner; establish a live-enough registry and run the mandated pre-placement surface and final-dot novelty checks.
- Only then preregister a distinct hypothesis and buffered whole-segment holdout with per-feature leakage canaries, use the shared evaluator/writer, and require a paired 95% CI lower bound above zero against the current same-protocol best.
- Obtain a hash-bound submission receipt for any organizer score, and clarify the exact portal nodata/range contract from the submission result. Keep a projection separate from a measured score.
- Use the separate slot selector only after all gates pass and after checking the current weekly cap; no slot was selected here.
