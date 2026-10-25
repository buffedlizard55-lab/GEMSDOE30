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
