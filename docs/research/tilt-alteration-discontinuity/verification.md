# G30-TAD Three-Pass Verification Journal

- **Branch**: `arena/8b4f7b50-gemsdoe30`
- **Lane**: `G30-TAD` (`docs/research/tilt-alteration-discontinuity/`)
- **Date**: 2026-10-25 / 2026-10-26 UTC

---

## Pass 1 — Implementation, Bounded Execution & Machine Gate Wiring

1. **Autonomous Data & Registry Restoration**:
   - Restored SHA-pinned competition inputs (`training_features.tif`, `labels.tif`, `sample_submission.tif`), verified external USGS/GDR layers (`data/external/external_receipt.json`), verified full-cell `(19, 3730, 3292)` prepared cache (`dataset_signature = 291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`), and synced 191 priority-site files (`190` aligned rasters across `GEMSDOE24..36` + repository downloads).
   - Fetched and verified official DrivenData overview, page 967 metric/format specification, live leaderboard (`#1 xiaofanhu = 0.4413` on 2026-10-25), DOE/NLR Rules PDF (`96647.pdf`), USGS GeoDAWN (`10.5066/P93LGLVQ`), and GDR 1391 (`10.15121/1881483`).
2. **Pre-Implementation Hypotheses & Preregistration**:
   - Authored PhD-level H33 (`0.2778`) & PINN (`0.2750`) proof, geothermal literature synthesis, and 5 ranked untried hypotheses (`H-TAD-1..5`) in [`geothermal-and-h33-synthesis.md`](geothermal-and-h33-synthesis.md).
   - Froze [`preregistration.md`](preregistration.md) and [`registration.json`](registration.json) (`9c7e91953be22f435d0113f8a9ce95d19cfc9aa86f7c3120d33052e91ef0c3d2`) before any experiment or label contact.
3. **Module, Unit Tests & Bounded 3-Experiment Run**:
   - Implemented `src/gemsdoe30/tilt_alteration.py` (`7/7` synthetic unit tests passing in `tests/test_tilt_alteration.py`, exact impulse support `15 px <= 17 px` fold guard, zero `~valid` sentinel sensitivity, fold-safe `rad_kd`, label-free hydrothermal impulse).
   - Executed `scripts/run_tilt_alteration.py` (`769.0 s <= 7,200 s` cap): E1 `tilt_alt24 = 0.14405` vs `core19 = 0.13982` (`+0.00423`, paired 95% CI `[-0.01554, +0.02398]`), `subsurface16 = 0.10959`, `random_dispersed = 0.08253`, `144/144` canaries `<= 0.6434`; E2 `P1` `30/40/30` collar decensoring improved off-catalogue `SGMC-new` (`0.08178` vs `0.08117`); E3 passed 190-raster surface (`0.1637 <= 0.90`) and dot (`51.44% <= 70.0%`) novelty gates and published dual `-zeros.tif` / `-nan.tif` files.
   - Built `scripts/verify_tad_run.py`, wired `scripts/verify_current_run.py`, `scripts/build_status.py`, `scripts/build_research_site.py`, and `.github/workflows/review-tests.yml`.

---

## Pass 2 — Bug, Edge-Case, Assumption & Regression Audit (Issues Found & Fixed)

1. **Late-registry numeric completeness on `TDX-C2` (`tests/test_stopped_attempt.py`)**:
   - *Finding*: Initial late-registry update recorded `undefined: true` with an `errors` note for quarantined `TDX-C2`, which turned `dots` status to `unknown` when a regression test mutated overlap values.
   - *Fix*: Deterministically reconstructed `TDX-C2`'s exact surface and 44,090 dots (`identity[:12] == d87627b24504`, matching prior S20 overlap `0.7706282603765026` to 16 decimal places) without touching `TDX-1` receipts, recording exact numeric Spearman and 3-px overlap (`27.79%`) against both `G30-TAD` GeoTIFFs with `errors = []`.
2. **Copy-button DOM selector mismatch on `geothermal-tilt-alteration-review.html` (`docs/assets/research.js`)**:
   - *Finding*: `docs/assets/research.js` queries `document.getElementById('copy-status')` by exact ID, whereas `geothermal-tilt-alteration-review.html` initially rendered `id="tad-copy-status"`, causing `Copy name` / `Copy note` clicks on that subpage to return early.
   - *Fix*: Changed status paragraph ID on `geothermal-tilt-alteration-review.html` to `id="copy-status"` and asserted `"copy-status"` presence in `tests/test_tad_release.py`.
3. **Exact `TDX-1` overlap figure in `docs/irregularities.md` (`IR-TAD-05`) & hash typo in `review.md`**:
   - *Finding*: `IR-TAD-05` listed `16.06%` before reading the exact `novelty-parallel-dots.json` output (`0.15627126... = 15.63%`), and line 7 of `review.md` had a duplicated partial hash prefix.
   - *Fix*: Updated `IR-TAD-05` to exact measured `15.63%` (`TDX-1`) and `27.79%` (`TDX-C2`), and cleaned line 7 of `review.md`.
4. **Rerun no-overwrite exit code & regression test + `git diff --check` trailing blank lines**:
   - *Finding*: `git diff --check` flagged trailing blank lines at EOF in `docs/hypotheses.md` and `docs/irregularities.md`; `run_tilt_alteration.py` raised an uncaught `RuntimeError` traceback on rerun instead of clean exit code `2`.
   - *Fix*: Stripped trailing blank lines (`git diff --check` exits `0`), added clean `exit 2` handling in `run_tilt_alteration.py`, and added `test_tad_rerun_preflight_preserves_all_frozen_receipts` to `tests/test_tad_release.py`.

---

## Pass 3 — Line-by-Line Prompt & Release Re-Verification

1. **Original Prompt Compliance Matrix**:
   - Previous-session blockers & autonomous data preparation verified (`data/processed/` full-cell match `291d3467...`).
   - Priority sites `GEMSDOE24/25/27/28/30/31/32/33/36` audited at byte level; PhD-level explanation of `H33-B2` (`0.2778`) and `PINN` (`0.2750`) + ceiling/breakthrough mathematics delivered.
   - Five untried geological hypotheses (`H-TAD-1..5`) ranked prior to implementation with layers, transforms, blind-fault mechanism, repo differentiation, and non-fault mimics.
   - Parallel-Run Protocol enforced: single lane (`G30-TAD`), shared `holdout.py` & `submission.py`, every score labeled `HOLDOUT-DTI` (with evaluator version, withheld positive count, 95% CI) or explicitly quarantined historical claim, `144` single-feature leakage canaries (`<= 0.6434`), 190-raster pre-placement surface (`0.1637 <= 0.90`) & post-placement dot (`51.44% <= 70.0%`) novelty gates, `3/3` bounded experiments (`769.0 s <= 7,200 s`), complete JSON Run Card, and strict protection of weekly submission slots (`verdict = negative`, `ok_to_submit = false`).
   - Complete verbatim prompt preserved at `README.md#current-owner-prompt`; clean GitHub Pages site (`index.html`, `executive-summary.html`, `geothermal-tilt-alteration-review.html`, `experiment-review.html`, `priority-registry-review.html`) verified with live local HTTP smoke check, zero broken links/anchors, and all CI verifiers + `pytest -q` passing.
