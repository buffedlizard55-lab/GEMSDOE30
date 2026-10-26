# Receipt-integrity review — 26 October 2026

## Decision: DO NOT SUBMIT

**No new TIFF was generated. No experiment or competition slot was used.** The supplied prompt has no identifiable single-method lane paragraph. This session therefore continues verification of previous work, rather than self-assigning another scientific lane or restarting the exhausted FFL-1 budget. Existing downloads remain research-only. This does **not** fulfill the requested new, uniquely validated high-scoring submission; that outcome remains blocked.

### What was actually verified in this checkout

- Restored `sample_submission.tif` using the repository's pinned GitHub mirror and verified its stored SHA-256 through `scripts/restore_public_mirrors.py`. This proves mirror integrity, not organizer authentication.
- Reopened the archived FFL-1 TIFF using the shared `gemsdoe30.submission.validate_submission_file`, with `require_finite_all_cells=True`. All checks passed: [current byte report](validation.json). The [exact TIFF](../2026-10-26-fflidar/gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif) is a duplicate-stopped research artifact, **not a submission recommendation**.
- Found and fixed a verifier gap: `verify_fflidar_run.py` previously inspected the expanded final-dot novelty receipt only if the stratified production arm was promoted. A negative run could therefore verify successfully even if its decisive expanded duplicate receipt had a wrong hash or contradictory decision.
- The verifier now binds that receipt for **every** outcome, rejects empty/error/non-finite measurements, reconstructs its decision through the shared novelty decision function, and requires duplicate-stop artifacts to remain negative and not submittable. Promotion additionally requires the complete expanded registry. This does not recompute registry comparisons or training.
- Checked the archived expanded receipt: its maximum final-dot 3 px overlap remains 78.280789%, above the mandatory 70% duplicate-stop threshold. This is a novelty statistic, not a competition performance number. The registry is explicitly incomplete; it can establish a duplicate, but cannot certify global uniqueness.
- `verify_fflidar_run.py` exits 0 when the **negative** decision is consistent; `--require-promote` exits 2. Neither is an organizer acceptance receipt.

## Nine-site executive summary and H33 explanation

The [existing nine-site executive review](../review-2026-10-26/review.md) records the highest supplied artifact claim for each of GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36, the corresponding URLs, and four ranked geological hypothesis refinements with layer names, physical mechanisms, costs and non-fault mimics. These proposals have **not** been run in this session. Their novelty across parallel lanes is unknown; no numerical improvement forecast is made.

H33's reconstructed mechanism is pruning a previously thinned dot set near known faults, not independently discovering new geothermal vents. For the reconstruction and limits, use that review and the [stored recipe evidence](../2026-10-25/recipe-reconstruction.json). No hidden labels or submission-page receipt were obtained. Consequently the user-supplied H33 performance claim cannot be labeled ORGANIZER-CONFIRMED, and we do not infer a hidden-truth hit rate or guarantee a better score from it. The conflicting leaderboard claims in the prompt are not a current feed.

**Best file to upload today: none is selected or approved by this review.** Existing format validity, lower proxy loss, or a byte-distinct hash cannot override a duplicate-stop or missing comparable-best evidence.

## Sources and limitations

Official manual-review links (not newly fetched or authenticated in this session):

- [DrivenData problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Organizer reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution)
- [NLR rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [Official INGENIOUS dataset](https://gdr.openei.org/submissions/1391)

Network access here is restricted to GitHub and package registries. No official non-GitHub source, current weekly-cap state, private hidden labels, or organizer receipt was verified. The cached feature stack was absent from this checkout at session start; only the small pinned template was restored for byte validation. No new external dataset is represented as obtainable. Do not automate competition uploads or confuse fault mapping with verified geothermal vent discovery.

## Three-pass verification and next session

1. Implementation: read current owner brief, run pointers, negative run records and shared tooling; fix the negative receipt bypass; revalidate exact TIFF bytes.
2. Adversarial review: add tamper tests for digest/stage mismatch, empty/error receipts, contradictory decision, NaN/Inf/out-of-range/boolean metrics, threshold equality and incomplete-registry promotion. Add an integration test proving the full negative verifier consumes the expanded receipt.
3. Recheck: run the entire test suite, rerun both verifier modes and inspect the final diff. Record exact results in the PR and final response. Optional Torch training tests are not evidence of trained model performance when skipped.

Next work: obtain a named lane allocation without requiring a manual inspection gate; restore the pinned cache and frozen folds; collect all parallel registry surfaces/dots; compare a preregistered candidate to the **same-protocol full-stack best**, not merely core19 or a weaker subsurface arm; run each feature's leakage canary first. Stop at the existing duplicate thresholds and within three experiments/two hours. Seek organizer receipts binding submission name, file hash and result before treating any website claim as ORGANIZER-CONFIRMED. A selector, separate from scientific promotion, must decide any real slot.

Final local results: **282 passed, 5 skipped**, 7 subtests passed; the five skips are optional Torch loss tests. Two Rasterio pending-deprecation warnings remain. `git diff --check` passed. Both verifier modes were rerun after the code/test/site changes: ordinary verification exit 0, promotion-required exit 2 (expected negative).
