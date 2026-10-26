# Three-Pass Verification Journal — `PTA-1` (`2026-10-25`)

## Pass 1 — Full End-to-End Implementation & Execution

1. **Primary source & 9-site audit completed:** Verified official DrivenData competition specification (`/page/967/`), live leaderboard (`#1 xiaofanhu = 0.4413` on `2026-10-25`; `0.3195` on `2026-10-03`), NLR Prize Rules (`96647.pdf`), USGS GeoDAWN (`10.5066/P93LGLVQ`), OpenEI GDR 1391 (`10.15121/1881483`), DrivenData Staff forum clarifications (`11516, 11527, 11529, 11536, 11543, 11550, 11553, 11556, 11557, 11563`), and all 9 priority repositories (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`).
2. **Dataset unit/sign & metadata audit (`IR-PTA-01..03`):** Discovered and regression-tested the `1,000×` unit mismatch between `tmi_hg` (`nT/km`) and `tmi_vg` (`nT/m`), signed `iso_grav_anom_hg`, and embedded GDAL description discrepancies on `tc`, `deq_n100a15`, `ieq_n100a15`, and `depth_to_base_surf`.
3. **Preregistration & single-experiment execution (`PTA-1`):** Froze 4 ranked geological hypotheses and the 4-arm `PTA-1` experiment (`core19`, `sub8_raw`, `pta_naive_sym`, `pta1_cand`) in `preregistration.md` (`sha256: 10a6d800c4372bffd3741859e3bbb2ec3caa33b1e49333476fd3b3cdad70e824`) before running `scripts/run_phase_tilt_asymmetry.py` (`304.9 s`, `1` of `3` experiments used).
4. **Unique GeoTIFF & receipts:** Published `docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif` (`sha256: 958f733cbd3501bd0ea92451a848cc28f62c913691ab3f4bc9b61aeebaaeb827`), verified across all `194` registry rasters (`max surface Spearman = 0.1055`, `max 3 px dot overlap = 54.60%`), and generated deterministic GitHub Pages + `docs/status.json`.

## Pass 2 — Bug, Requirement, Assumption & Edge-Case Audit

1. **Bug caught & fixed in `src/gemsdoe30/readiness.py`:** `paired_improvement` gate detail string previously branched only on `spec["id"] == "tdx1"` vs `"tdxc2"`, causing `pta1` to display `tdxc2`'s `"zero-lag and phase-null controls"` text. Fixed to emit exact `spec["label"]` comparator names while preserving byte-identical strings for `tdx1` and `tdxc2`.
2. **Bug caught & fixed in `scripts/download_competition_data.sh`:** Unquoted `<<EOF` heredoc in missing-file message expanded backticks around `` `gh` `` and executed `gh` help output onto stderr during `--check-only`. Fixed to `(gh)` and verified clean stderr + exit code `2` on empty temp directory and exit code `0` with SHA-256 verification on `data/raw/`.
3. **Late-registry invariant across archived runs (`IR-PTA-09`):** Publishing a new `.tif` under `docs/downloads/` requires read-only late-registry rows in archived `texture-displacement` (`110 → 111`) and `texture-controls` (`166 → 167`) without touching frozen `registry.json` files. Measured exact `TDX-1` vs `PTA-1` dot comparison and recorded fail-closed `undefined: true` where git-ignored `outputs/` rasters are absent; verified both with `verify_current_run.py` and `verify_stopped_attempt.py`.
4. **Memory & support-radius check:** Confirmed `TIGHT_SUPPORT_PX = 12` (`sqrt(8^2 + 6^2 + 4.5^2) = 11.02 px <= 12 px`) and `SUPPORT_PX = 17` matching `spatial_segment_folds(..., buffer_px=17)`, keeping peak RSS comfortably inside the `3.8 GiB` RAM sandbox via `float32` scalars, eager intermediates deletion, and `LayerStack` memmaps.

## Pass 3 — Final Accuracy, Reliability, Completeness & CI Parity Check

1. Re-ran `verify_current_run.py` (on both `docs/current-run.json` = `PTA-1` and archived `TDX-1`), `verify_stopped_attempt.py` (`TDX-C2`), `validate_submission.py`, `build_research_site.py --check`, `build_status.py`, `download_competition_data.sh`, `pytest -q`, and `git diff --check`.
2. Verified every link and anchor across `index.html`, `executive-summary.html`, `experiment-review.html`, and `docs/index.html`, and confirmed both `--require-promote` verifiers exit `2` as designed.
