## Current session update — 2026-10-25

Data placement and preparation completed locally using `scripts/restore_public_mirrors.py`
and `scripts/prepare_data.py`. See `docs/research/2026-10-25/prepared-manifest.json`.
The large files remain ignored and may need restoration in a fresh checkout.
Mirror integrity is verified; organizer origin/authentication is not independently
verified. The older access notes below are historical, not a current placement blocker.

# Local data placement

Competition rasters are not committed. The official competition data page currently requires an authorized DrivenData login; this repository will not handle credentials or bypass that access control.

Place the files downloaded through an authorized session in `data/raw/`:

- `training_features.tif` — official 100 m multiband feature raster.
- `labels.tif` — binary known-fault training labels, aligned to the feature grid.
- `sample_submission.tif` — organizer-provided output template/footprint.

Those default names follow the project brief and must be checked against the actual downloaded files. Do not rename files based on names alone; compare metadata and inspect their contents. Optional public sources are catalogued in [`../docs/sources.md`](../docs/sources.md).

Run `bash scripts/download_competition_data.sh` to check placement, then `python scripts/prepare_data.py`. The first script is intentionally a preflight, not a downloader: the DrivenData data page redirects unauthenticated visitors to its login page. Prepared `features_raw.npy` retains finite source values and NaNs for missing/outside-footprint cells; each model checkpoint fits and records fold-local median/IQR scaling from training pixels only. Raw and prepared data directories are Git-ignored.
