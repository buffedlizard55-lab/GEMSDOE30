# Three implementation / review passes — 2026-10-27

This was a registry-and-evidence audit, **not a model experiment**. The current
[run card](run-card.json) is negative; no TIFF, submission name, note, holdout
score, slot, or external upload was created.

## Pass 1 — input, provenance, and scientific decision

- Reread the full owner prompt and prior stop/start markers. Restored the
  SHA-pinned sample, labels, training features, and three external owner mirrors
  locally; the [cache receipt](cache-verification.json) compares every cached
  cell to the raw-source derivation. These owner mirrors are not
  organizer-authenticated. Large data remains ignored.
- Reopened the exact CSR-1 bytes. Its in-footprint finite/range checks pass;
  the normal published-format validator fails because its out-of-footprint
  cells are zero. The separate whole-array finite diagnostic passes. Portal
  acceptance and the cause of the historical range error remain unknown.
- Restored the commit/SHA-pinned 13GEMSDOE lattice, verified band, shape, CRS,
  affine and in-footprint values, and established 44,084/44,090 measured
  three-pixel matches against CSR-1. The earlier 357-reference scan did not
  include this witness. **Stop**, rather than fit or produce a replacement.

## Pass 2 — shared tools, claims, and current UI

- Added a reusable distinct-dot budget lower bound to shared `novelty.py`, with
  strict integer threshold arithmetic and explicit `not-proven` semantics.
  Fixed the partially malformed-reference check: a subset correlation is not a
  whole-footprint correlation, and a directional dot proof must divide known
  matches by **all** candidate dots. Exclusions block complete clearance.
- Made the shared readiness adjudicator honor a proven malformed-reference
  duplicate even if ordinary comparisons are clear, and prevent a new
  incomplete audit from being overridden by a completeness claim. Treat
  strongly inverted correlations conservatively. Historical receipts are not
  rewritten.
- Replaced current Pages/README/status claims with a visible stop, correct
  format distinction, pinned nine-site historical sources and unverified score
  labels. Preserved the former README narrative and historical Pages behind
  explicit archive warnings. Corrected H33 lineage versus hidden-score
  causation; removed unsupported forecasts. Preserved the owner-prompt tail
  byte-for-byte (SHA-256
  `a042845fc4f85dd7d1f005d9256e1c9b7a9169b1fe2e3f00aa83712bdf05d36b`).
- Flagged the competition-page 23:59 UTC vs rules-PDF 5 p.m. ET deadline
  discrepancy; plan for the earlier time pending organizer clarification.
  The GitHub-only status workflow does not monitor DrivenData.

## Pass 3 — independent review and regression checks

- Independently recomputed three-pixel coverage using clipped integer-disk
  shifts (29 offsets, no edge wrap) and checked it equals the Euclidean distance
  transform: 5,160,724 covered / 6,649 uncovered footprint cells. The K=44,090
  bound is 37,441/44,090 = 84.9195%; 22,163 is not proven over 70%, 22,164 is.
  Rechecked actual CSR-1 overlap with an independent nearest-neighbour query.
- Added synthetic equality-boundary, negative-rank, malformed-subset,
  duplicate-propagation, invalid-input, edge-wrapping and tampered-witness/card
  tests. A partial 100% subset overlap cannot pass as a whole-candidate proof;
  a known-match lower bound strictly greater than 70% cannot be ignored.
- Ran the full test suite with restored data: **410 passed, 5 skipped** (optional
  PyTorch tests), 7 subtests passed. Deterministic Pages `--check`,
  `git diff --check`, pinned restoration and current negative verifier are
  required locally and in GitHub CI. The verifier's `--require-promote` exits 2.
- During this pass PR #54 merged two more research TIFFs. Preserved their bytes,
  rechecked them without model fitting or placement, and found CTD-1 overlap
  39,984/40,000 (99.9600%) and FC-1 overlap 10,844/10,848 (99.9631%): both
  duplicate-stopped, even though FC-1's 10,848-dot budget alone does not prove
  a stop. Their saved predictions used the full catalogue before components
  were hidden; the recorded single random split is not the requested buffered
  regional protocol. The FC controls also have different budgets. Archived
  scores are not accepted as leakage-safe selection evidence. Disabled the
  unsafe old generation and scoring entry points, and replaced the separate
  local scan with a fail-closed wrapper around the shared registry auditor.
- Remaining blockers: no externally assigned method lane, incomplete live
  parallel registry and the literal lattice duplicate rule. Even after those
  are resolved, a fresh same-protocol holdout, feature leakage checks, exact
  saved-byte validation and independent selector approval are mandatory.
