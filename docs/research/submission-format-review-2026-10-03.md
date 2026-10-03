# Submission-format correction review — 2026-10-03

**Branch:** `arena/01a103c1-gemsdoe30`

**Scope:** align the GeoTIFF writer, validator, CLIs, site, and download sidecars with the published GEMS outside-footprint convention. This pass did not change geological features, models, holdout scores, or submission-slot status.

## Verified rule and unresolved report

The [official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) specifies a one-band float32 prediction raster on the competition grid, finite values in `[0,1]` inside the data bounds, and null/NaN outside. The local template has 7,111,787 NaN outside cells and 5,167,373 valid in-footprint cells. The repository default now follows the published null/NaN-outside format.

The earlier “Predicted values must be in range [0, 1]” report is **not diagnosed**: the exact submitted file was not identified, and the organizer-side validator is private. A strict whole-raster finite check flags NaN outside by design; that does not establish that the private portal uses such a check, nor justify substituting zero outside. Local validation is not portal-acceptance evidence.

## Artifact audit

All six tracked TIFFs in `docs/downloads/` were checked against the available local template after the correction. The exact file hash and validation results are in each adjacent JSON sidecar.

| File | SHA-256 | Outside convention | Published-format check | Whole-array finite diagnostic | Site link / scientific status |
| --- | --- | --- | --- | --- | --- |
| `GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-nan.tif` | `f5d137b9c010873f0b4fc11e841d923f359d33c7272ded0da9ac9b7c1efc7cc2` | NaN | Pass | Fail (expected: outside NaNs) | Linked research download; proxy gate failed; unpromoted/unscored |
| `gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif` | `fed5232e8efeefef00728ce9d5884f08e007c542f317cb11419452d14ff866da` | NaN | Pass | Fail (expected: outside NaNs) | Linked research download; SGMC check is tautological; unpromoted/unscored |
| `gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8` | NaN | Pass | Fail (expected: outside NaNs) | Linked external reference; 0.2600 file attribution unresolved; owner page says unscored/not slot-approved |
| `GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-zeros.tif` | `dd5cd18a721196602eaccd8946b047eb8c929cbfdcac033512628f6dd0030f50` | 0.0 | **Fail** (outside is not null/NaN) | Pass | Archived diagnostic only; not linked or upload-recommended |
| `gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e-zeros.tif` | `d7977d7b93287f17fbf3cb85f10fdbee4acc5c8453a7faa451e760363433a286` | 0.0 | **Fail** (outside is not null/NaN) | Pass | Archived diagnostic only; not linked or upload-recommended |
| `gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif` | `b00a6fb6cab70d0f957308e297695c4032ab97997a41a15ff1295add3df31a26` | 0.0 | **Fail** (outside is not null/NaN) | Pass | Archived diagnostic only; not linked or upload-recommended |

All six retain the expected one-band float32, EPSG:32611, 3730×3292, 100 m grid and locally match the template transform. Every file has 5,167,373 finite in-footprint values in `[0,1]`. The three NaN-outside files have 7,111,787 outside NaNs. The three zero-outside copies preserve their source files' in-footprint values but fail the published outside-value check. Their sidecars now record both validation outcomes; the status feed also distinguishes published-format compliance from the strict diagnostic.

## Implementation and verification passes

### Pass 1 — implement and verify

- `validate_submission_file` now defaults to the published format: finite in-footprint probabilities, exact template geometry, and null/NaN outside. Whole-raster finite validation is an explicit diagnostic (`require_finite_all_cells`); `portal_safe` remains only as a compatibility alias.
- `write_submission_file` defaults to NaN outside. Its sidecar records `published_format_compliant` and a separate whole-raster diagnostic result. Zero-outside writes are labeled nonstandard.
- `scripts/build_submission.py` defaults to NaN outside and rejects zero outside unless `--allow-nonstandard-zero-outside` is supplied. `scripts/validate_submission.py` exposes `--finite-all-cells` and labels `--portal-safe` as a legacy diagnostic alias. `scripts/make_portal_safe.py` requires `--confirm-nonstandard-outside` and warns that the output is not a submission recommendation.
- All three published-format TIFF links at the start of `index.html` and in `executive-summary.html` now point to NaN-outside research files. The manual guide describes the published convention and the exact, undiagnosed range-error status. Archived zero copies remain only for auditability and are unlinked.
- Updated the six download sidecars, `docs/status.json`, the source/score analysis notes, AI-disclosure draft, and irregularity register (IR-30-038). The D2.8 score/file attribution remains unresolved.
- Full test suite: `./.venv/bin/python -m pytest tests -q` → **97 passed, 11 subtests passed, 0 skipped**. Tests verify NaN-default writing, explicit acknowledgement for zero-outside diagnostics, independent diagnostic/report fields, and the legacy converter's behavior.

### Pass 2 — defect and edge-case review

- Confirmed that a zero-outside TIFF cannot pass the default published-format validator even when it passes the strict all-finite diagnostic; its sidecar clearly reports `published_format_compliant: false`.
- Confirmed that a NaN-outside TIFF passes the default published-format check and fails only the optional whole-array finite diagnostic. No diagnostic name or help text claims actual portal behavior.
- Confirmed that the builder refuses zero outside without an explicit nonstandard acknowledgement and that the legacy conversion script also fails closed without acknowledgement.
- Rechecked source/output identity for the three archived zero copies: all preserve in-footprint values; no claim is made about organizer acceptance.
- Static-site link audit: 8 HTML pages, 162 local `href`/`src` references, 9 download attributes, 40 Markdown pages, and 275 inline Markdown links. Local targets and HTML fragments resolve; every HTML download attribute matches its linked basename; no zero-outside TIFF is linked.
- The exact historical error file is still unavailable; the earlier hypothesis that outside NaNs caused the error remains unverified and is not stated as a diagnosis.

### Pass 3 — full-brief re-check

- Metric-aware boundary loss remains paired with regional loss; prior spatial-holdout evidence shows changed near-miss allocation but no replicated DTI improvement. This format-only pass did not modify or re-score it.
- Five active, ranked geology hypotheses remain in `docs/hypotheses.md`; H-31-04 remains unvalidated. No new geological implementation was made, no candidate was promoted, no competition file was uploaded, and no weekly slot was used.
- The site keeps the three downloadable TIFFs prominent, marks them as research/unpromoted, and links the exact submission guide. No automated DrivenData access, credential handling, or submission workflow was added.
- A local format check is not an organizer acceptance test. Score 0.2600 remains unauthenticated to the D2.8 TIFF; the dated public 0.3195 leaderboard snapshot has no connection to any TIFF in this checkout.

## PR / merge verification

To be updated only after the assigned branch's actual GitHub operations are checked. This review does not claim a new PR or merge.
