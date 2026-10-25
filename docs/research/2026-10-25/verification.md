# Three-pass verification — 2026-10-25

## Pass 1 — inspect, implement and measure

- Read the existing owner brief, prior review, hypothesis reports, shared metric,
  evaluator, writer, status builder and tests.
- Retrieved pinned source trees/landing pages for all nine priority sites, the
  official reference notebook, and one historical reference TIFF per site.
- Restored all existing core mirror pins and prepared the data successfully.
- Implemented reusable exact Spearman / directional dot-overlap diagnostics,
  hash/grid checks, partial-registry blocking and JSON receipts.
- Historical H33 comparison exited 2 (`duplicate-stop`), as required.
- First test run after novelty implementation: 120 passed, 5 optional torch tests
  skipped. These are test counts, not performance scores.

## Pass 2 — defects, uncertainty and edge cases

- Found/fixed pooled holdout footprint masking and missing FP statistics in
  truth-empty quadrants in the shared module; added regression tests.
- Found/fixed vacuous missing-file hash verification in status generation.
- Checked zero/NaN outside-encoding invariance, exact 3-pixel boundary,
  directional overlap, constant fields, empty masks/registries, hash/grid mismatch,
  non-finite input, and surface-versus-dot stage differences.
- Corrected assertions of legal portal acceptance and definitive historical
  range-error diagnosis. Replaced contradictory entry pages.
- Independently reconstructed H33 support from H28 and a catalogue-distance
  threshold: zero mismatching pixels. Also found identical in-footprint values
  for H25/H30 and H28/H31 selected references. No reconstructed TIFF was written.
- No historical DTI was silently relabelled with the corrected evaluator version.

## Pass 3 — acceptance recheck

- Final local suite: **124 passed, 5 skipped, 7 subtests passed**. Five skips are
  optional torch training/loss tests; PyTorch is not installed. Two rasterio
  pending-deprecation warnings; no test failures. Full GPU training is untested.
- Python compilation and `git diff --check` passed.
- Both current HTML entry pages' local href/src targets exist. This is a static
  link check, not a browser screenshot or full accessibility certification.
- New JSON receipts parse without nonstandard NaN/Infinity values.
- Run-card note is 118 characters, within the requested 140-character maximum.
- GitHub API confirms Pages is configured for `main` / root. Actual deployment
  after merge must be reported separately from local HTML checks.
- No experiment, submission slot, organizer score, or new unique candidate is
  claimed. The diagnostic historical reference passes the local all-finite
  validator; that result is NOT attached to a nonexistent new candidate.

## Requirements still unmet (explicit, not hidden)

1. A new unique submission TIFF has **not** been produced. Missing lane and full
   registry prevent a protocol-compliant experiment/novelty certification.
2. Top-hypothesis HOLDOUT-DTI, feature AUC canaries, withheld-positive count and
   CI are unmeasured. Buffered segment folds and the corrected comparator need
   to be established first. No claim of improving the leaderboard is justified.
3. Only one requested reference per site is in this educational registry. Full
   site-wide and parallel-lane surface coverage is not claimed.
4. Current rules PDF, live leaderboard, portal cap, official raw-data
   authentication and submission-page receipts were not freshly verified; their
   hosts are outside the sandbox allowlist. No new free external data source was
   advertised as obtainable without verification.
5. The current request was persisted as an explicit requirements amendment and
   prioritized in README, not as a complete literal transcription of the latest
   long message. Older literal brief is preserved and clearly historical.
6. Deep literature review and independent field validation remain future work;
   proposed geological mechanisms are hypotheses, not verified vent discoveries.

These failures prohibit submission approval. They do not negate the completed
restoration, exact historical forensics, shared-tool fixes, tests or site cleanup.

## CI follow-up (within pass 3)

The first remote run failed an existing test that assumed filesystem directory
iteration order: it found the two correct input TIFFs in reversed order. The
failed-output, partial-file and sidecar absence assertions all passed. Replaced
that order-dependent equality with `assertCountEqual`; this retains exact
membership/cardinality and does not relax the fail-closed writer requirement.
A clean tracked-file export also passed locally. CI failure output is now exposed
as check annotations because the Actions log-download host is outside the sandbox
allowlist. The first log lookup was additionally delayed by a GitHub API quota.

## Session 2 — 2026-10-25 (later, implementation session)

**Pass 1 — implement and measure.** Restored the nine owner mirrors (all SHA-256 pins matched) and prepared the data (`prepare_data.py`). Implemented review hypothesis 3 as `src/gemsdoe30/residual_gate.py`, with unit tests. Added a shared `max_kernel_credit` and `masked_tile_sums` to `holdout.py` for block bootstraps (exact pooled identity tested). Ran three experiments (budget spent):
1. Strict 3.5 km buffer, arms A/B/D → all 0 by construction (IR-30-056).
2. Strict buffer plus catalogue-free arm E → E 0.04471 [0.03768, 0.05200].
3. Final: strict and 0 m protocols, plus random control R → 0 m: B 0.17703, A 0.12222, D 0.13070, R 0.08320; strict: E 0.04471 vs R 0.04368 (overlapping CIs).

**Pass 2 — defects and edge cases fixed.**
* Derivative filters used `nearest` boundary mode and a 4σ truncation, which produced a spurious ridge on a flat plateau (≈3.5e-4). Fixed with `reflect` plus `truncate=8`; the plateau is now zero to numerical precision.
* First holdout run returned 0.0 for three arms. Investigated: structural (gate plus reach cannot reach a 3.5 km buffer), not a bug. Recorded as IR-30-056.
* Holdout run OOM-killed (exit 137) from eager float64 copies. Canaries now sample lazily. The killed output was discarded (IR-30-065).
* Build note and hypothesis strings were corrected after the first build; the TIFF bytes changed (note tag), so the final hash comes from the final build only.

**Pass 3 — acceptance recheck.**
* Independent rasterio re-read of the final TIFF: one band, float32, EPSG:32611, shape 3730×3292, transform equal to template, 5,167,373 footprint cells all finite, values exactly {0, 1}, 0 dots on known catalogue pixels.
* Duplicate checks: 9-site registry (dots stage) max Spearman 0.0034, max within-3px 22.2%; repo-wide (11 TIFFs) max Spearman 0.0103, max within-3px 45.0%. No duplicate. Surface stage blocked (IR-30-059).
* Run card generated by `scripts/make_run_card.py` from receipts (not by hand); its validator output was re-run on the final file.
* Live official facts re-read with the retrieval tool and recorded with dates (`live-verification.md`).
* Remaining open items are listed in `docs/irregularities.md` (IR-30-056 to IR-30-067). Notably: the known-fault mask rule is unconfirmed (IR-30-061), and the portal range error is undiagnosed (IR-30-064).
