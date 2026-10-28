# Repository review — 2026-10-28

## Decision

**No new submission GeoTIFF was generated, and none is approved for upload.** The repository's current decision (DUPLICATE-STOP, DO NOT SUBMIT) is unchanged. This review independently re-ran the verifiers and tests instead of relying on the 2026-10-27 write-up.

## What was independently reproduced today

All commands were run from the repository root with `PYTHONPATH=src` and a fresh `.venv` (Python 3.11.2, numpy 2.4.6, rasterio 1.4.4, scipy, `-e .[research,test]`).

| Check | Command | Result |
|---|---|---|
| Duplicate-stop proof | `.venv/bin/python scripts/verify_registry_preflight.py` | **VERIFIED NEGATIVE**: 37,441/44,090 minimum overlap bound; historical CSR-1 44,084/44,090 within 3 px; no submission |
| Pinned witness hash | `sha256sum data/raw/registry-extra/13gems-lattice-s5.tif` | `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`, matches `docs/research/2026-10-27-registry-preflight/lattice-pin.json` |
| POOL-1 receipt | `.venv/bin/python scripts/verify_pool_run.py` | Receipt-only verification passes; `breaching_references` lists CSR1, MSDB1 and FFL1; raster absent |
| Format validator on historical CSR-1 | `.venv/bin/python scripts/validate_submission.py docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif --template data/raw/sample_submission.tif` | Exit 1. Passes CRS (EPSG:32611), shape (3730×3292), transform, float32, single band, and finite values in [0,1] inside the footprint. **Fails `null_outside_template_footprint`** (7,111,787 zeros outside the footprint). |
| Test suite | `.venv/bin/python -m pytest -q` | 424 passed, 5 skipped (optional PyTorch loss tests), 7 subtests passed |

Inputs restored only for verification (`scripts/restore_public_mirrors.py --ids sample_submission labels`, plus the lattice via codeload at the pinned commit). They are owner mirrors, **not organizer-authenticated**, and sit under the git-ignored `data/raw/`. The training feature raster was not restored, so no model was run.

## Irregularities flagged for review

1. **Leaderboard figures in the brief are not traceable to any receipt in the repo.** The brief states 0.3195 is the current highest score and 0.4413 is the current GEMSDOE high. The repo's own records (`OWNER_BRIEF.md`, `docs/score-ledger.csv`) list 0.3195 only as a user-reported leader on a 2026-10-03 snapshot. Neither figure is `ORGANIZER-CONFIRMED`.
2. **The 0.2778 H33-B2 figure is owner-reported.** Its raster is in GEMSDOE32. The repo gives no causal explanation of why it scored higher; the "why" in the repo is only a lineage observation (2,545 dots near visible catalogue faults removed).
3. **Validator vs. portal wording.** The published spec permits null/NaN outside the footprint, while the earlier portal error reads "Predicted values must be in range [0, 1]". The repo's validator treats zeros outside the footprint as a failure, which matches the likely cause of the portal error, but this is **not confirmed** by a portal receipt.
4. **Twenty-one named-prefix repositories cited in the brief** (`KANLERGEMSDOE1..3`, `EUGGEMSDOE1..3`, `WBGGEMSDOE1..3`, `GINNYGEMSDOE1..3`, `GEMSDOEkarage1..3`, `ApartGEMSDOE1..3`, `GEMSDOESASS1..3`) returned HTTP 404 in the 2026-10-27 audit. They are treated as unverified owner text.
5. **Training inputs are absent.** `training_features.tif` (418,912,844 bytes, owner mirror) is not in the checkout, so no new holdout or model run is possible here.
6. **No lane assignment.** The brief's parallel-run protocol refers to a single method paragraph that does not appear in this session's message. Under the repo's `AGENTS.md` rule 4, no new fit, placement, raster, or slot is authorized without an explicit lane and a policy resolution.

## Why a new TIFF was not generated

- A 44,090-dot candidate must overlap the pinned lattice by at least 84.9% regardless of placement. The literal policy stops anything above 70%.
- For budgets below 22,164 dots the bound does not prove a stop, and the repo rules forbid lowering the budget to evade the rule.
- Producing a file now would violate the duplicate stop and would not be a unique, policy-compliant submission.

## Next actions (in priority order)

1. **Decide the lane and policy.** The owner needs to assign a method paragraph and state how the 70%-within-3-px rule applies to dot budgets below 22,164. Without this, no new raster can be generated legitimately.
2. **Obtain an organizer receipt** for at least one current submission. This would turn the 0.2778 and 0.3195 figures into verified values, and would confirm or rule out the [0,1] / null-outside-footprint cause of the portal error.
3. **Restore `training_features.tif`** from the pinned owner mirror (hash-checked) so a holdout can run once a lane is assigned.
4. **Keep the verifiers in CI.** The commands above should stay in the review checklist so that any future file is checked against the registry lattice before upload.

## Reproduction

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[research,test]'
.venv/bin/python scripts/restore_public_mirrors.py --ids sample_submission labels
PYTHONPATH=src .venv/bin/python scripts/verify_registry_preflight.py
PYTHONPATH=src .venv/bin/python scripts/verify_pool_run.py
PYTHONPATH=src .venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python scripts/validate_submission.py docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif --template data/raw/sample_submission.tif   # expected: fails null_outside_template_footprint
```

The lattice is restored from `https://codeload.github.com/buffedlizard55-lab/13GEMSDOE/tar.gz/92ee6f074323f161eed837b80ec3ee5b662e26f5` (pinned commit; source file `docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif`).
