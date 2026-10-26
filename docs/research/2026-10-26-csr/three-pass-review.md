# Three-Pass Cumulative Review & Verification Journal — `CSR-1` (`2026-10-26`)

## Pass 1 — Initial Implementation, Execution & End-to-End Verification

1. **Completed Open Items From Prior Sessions (`GDX-1` & `FFL-1`):**
   - Repaired `scripts/sync_priority_registry.py` and `scripts/check_novelty.py` in place to formally classify malformed in-footprint rasters (`classify_footprint_validity`), support `--include-docs-tiffs`, and emit diagnostic `malformed_exclusions_audited` metrics (`GEMSDOE31` `774c7c5aa...` `2,610,312` in-footprint `NaN`s -> `CSR-1` finite-subset overlap `1.45%`).
   - Built frozen `docs/research/2026-10-26-csr/registry.json` (`374` `.tif` entries -> `357` unique aligned 1-band rasters, `2` exclusions, `5` continuous surfaces; `SHA-256: cf8ccc608e01ed233b350b0b48fc6904c3ec1fd8f7517863dbf2ecc0a9f9d62b`).
2. **Preregistered Hypotheses & Physics Implementation:**
   - Froze 4 ranked untried geological hypotheses in `preregistration.md` (`SHA-256: 28383a27...`) and `preregistration.json` (`SHA-256: 329f4e13...`) before fitting any model.
   - Implemented `src/gemsdoe30/csr_discontinuity.py` (`26` features: 3D FFT Laplace/Poisson vertical gravity derivative $\partial g/\partial z$, `1,000× tmi_vg` unit-consistent 3D magnetic tilt sharpness, fold-safe MT conductive-cover stripped gravity gradient, signed cross-strike polarity, `1.8 km` 18-azimuth Radon stepover, Noisy-OR basin fusion, and 1D Hessian ridge concentration), plus `min_sq_dist_excl` spacing in `src/gemsdoe30/emitter_opt.py`, `"csr1"` contract in `src/gemsdoe30/experiments.py`, and `"csr1"` readiness logic in `src/gemsdoe30/readiness.py`.
3. **Executed Preregistered `CSR-1` Run (`1,495.2 s`, `2/3` experiments) & Standalone Verifier:**
   - Produced `docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` (`SHA-256: 0fbf3b4a47c2...`, `44,090` dots, all `12,279,160` cells finite in `[0.0, 1.0]`, `0` dots `<= 2 px` of catalogue, `min NN = 2.8284 px`), passing `12/12` strict format checks, `324/324` leakage canaries (`<= 0.6629`), and both stages of `357`-raster novelty (`surface ρ = 0.1378 <= 0.90`; `dots 3-px = 67.70% <= 70.0%`, `59.86%` vs `MSDB1-edge`).
   - Verified `HOLDOUT-DTI = 0.158162` (`+0.01325` vs `core19_edge`, `+0.02300` vs `msdb_edge` in Fold 3 Walker Lane, `-0.01182` pooled vs `msdb_edge` -> honest `verdict = "negative"`, `download_ok = true`, `ok_to_submit = false`).
   - Built and ran `scripts/verify_csr_run.py` (`exit 0`, `12` gates verified in `2.67 s`).

---

## Pass 2 — Bug, Edge-Case, Assumption & Regression Review

1. **Bug Caught & Fixed Before Full Run (Shared Submission Writer Signature):**
   - During pre-run inspection of `scripts/run_csr_discontinuity.py`, caught two call-site mismatches against `src/gemsdoe30/submission.py`: `write_submission_file` expects keyword `outside_footprint="zero"` and `extra_metadata={...}` (not `outside_convention` / `metadata`), and `validate_submission_file` takes `(candidate_path, template_path, ...)` positionally and checks `report["passed"]` (`not report["ok"]`). Fixed cleanly and smoke-tested on a `16 × 16` synthetic GeoTIFF (`12/12` checks passed) before launching the 25-minute `CSR-1` run.
2. **Archived Receipt & Live-Inventory Compatibility Invariant (`test_live_registry_coverage.py` & `test_gdx_release.py`):**
   - Verified that `test_live_registry_coverage.py` requires `docs/current-run.json` top-level `run_card` and `readiness` to remain pointed at archived `phase-tilt-asymmetry` without mutating archived bytes when new `.tif` files arrive in `docs/downloads/`, and that `test_gdx_release.py` hashes `README.md` from `<a id="current-owner-prompt">` to EOF against `docs/research/2026-10-26-gdx/prompt-preservation.json`.
   - Preserved `docs/research/2026-10-26-gdx/*` receipts untouched, preserved `README.md` from `<a id="current-owner-prompt">` to EOF byte-for-byte, kept `geothermal-chemistry-review.html` verified via `verify_geothermal_chemistry_run.py`, and wired `CSR-1` via `latest_review` + `verify_csr_run.py` in both `.github/workflows/review-tests.yml` and `.github/workflows/status-feed.yml`.
3. **Tamper-Proof Regression Suite (`tests/test_csr_release.py`):**
   - Added parametrized mutation tests verifying that tampering with `ok_to_submit`, `verdict`, `raster_sha256`, `experiments_run`, `note` length, canary AUCs, novelty overlap, or holdout sufficient statistics causes `verify_csr_run.py` to fail closed, that `run_csr_discontinuity.py` refuses re-entry once `run-card.json` exists, and that every generated HTML page has valid internal links, unique element IDs, zero broken fragments, and explicit `OK TO DOWNLOAD: YES` / `NOT APPROVED FOR SUBMISSION` scope.

---

## Pass 3 — Line-by-Line Re-Check Against Original Prompt & Scientific Accuracy Polish

1. **Prompt Compliance Audit (Every Requirement Checked Line-by-Line):**
   - *Work on next steps first:* Completed malformed `GEMSDOE31` classification, live `357`-raster 9-site sync, same-fold `msdb_edge` comparator, unit-consistent 3D potential-field operators, and `2.83 px` dispersed 1D-Hessian `EDGE` emitter solving `FFL-1`'s `78.28%` duplicate-stop (`59.86%`).
   - *9 priority sites (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`):* Dedicated Markdown (`nine-site-executive-summary.md`) + HTML (`priority-executive-summary.html` + 9 `priority-GEMSDOE*.html` subpages) with master table of file to download, historical claim vs 2026-10-26 status, value-hash aliases, and `CSR-1` 3-px uniqueness (`36.06%–40.59%`).
   - *PhD explanation of `GEMSDOE32` (`0.2778`) & surpassing `0.2778` / `0.3195` / `0.4413`:* Exact subset & Tversky differential algebra (`44,090 -> 40,199 -> 37,654 -> 38,854`) under pixel-exact `labels == 1` masking (`t/11516`), plus mathematical recall threshold (`34% -> 52–60%`) and concrete `CSR-2` spatial regime-gating + 2D UNet roadmap.
   - *3–5 untried hypotheses before coding:* 4 ranked hypotheses frozen in `preregistration.{md,json}` before `started.json`, with exact layers, transforms, unmapped-fault targets, non-fault mimics, and official CC0/CC-BY source DOIs.
   - *Parallel-Run Protocol:* Pre-placement surface (`ρ = 0.1378 <= 0.90`) AND final dots (`ρ = 0.0856 <= 0.90`, `3-px = 67.70% <= 70.0%`) checked; shared `gemsdoe30.holdout` & `gemsdoe30.submission` reused; every metric labelled `HOLDOUT-DTI` with evaluator version, `60,988` positives, and 95% CI; `324/324` single-feature canaries `<= 0.6629`; `2/3` experiments (`1,495.2 s <= 7,200 s`); canonical JSON run card emitted (`verdict = "negative"`).
   - *Unique, zero-human-validated `[0, 1]` GeoTIFF & unmistakable GitHub Pages UX:* `docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` (`12,279,160 / 12,279,160` finite cells in `[0.0, 1.0]`), top-of-site & `executive-summary.html` banner (`OK TO DOWNLOAD: YES` · `OK TO SUBMIT: NO`), copyable unique name & `104/140`-char note, and 5-step DrivenData upload guide.
   - *Full prompt embedded in `README.md`, irregularities flagged (`IR-CSR-01..05`), zero untracked large caches committed.*
