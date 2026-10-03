# GEMSDOE30 — DOE GEMS fault-discovery research

> **Complete persistent project brief — read this section before every project session.** These are the standing scope, scientific, operational, and integrity requirements from the project request—not a session-status summary. Preserve every acceptance criterion when changing this brief. Keep `docs/score-ledger.csv`, `docs/irregularities.md`, and the linked official sources in sync when updating claims.

## Mission and non-negotiable requirements

1. **Objective and historical review:** build an auditable, scientifically grounded workflow to identify previously unmapped geological faults in the DOE GEMS / GeoDAWN region and pursue a result above the user-reported 0.3195 public-leader score. Study the reported GEMSDOE25 D2.8 result and historical submissions; authenticate score-to-file attribution using a submission receipt, ID, hash, or equivalent evidence rather than assuming a score belongs to a named TIFF. Treat public leaderboard snapshots as dynamic feedback, not the private test set or the final award decision. Develop a defensible path to improvement, but never promise a score or prize.
2. **Metric-aware learning:** the official public metric is a distance-weighted Tversky index with a triangular 300 m support kernel on 100 m pixels, `alpha=0.2`, `beta=0.8`. Prefer training objectives that represent this geometry. Pair any distance/boundary term with a regional loss; compare them under a spatially blocked holdout and report how their near-miss behavior changes. A synthetic unit probe is not a real holdout result.
3. **Submission first:** when a scientifically promoted candidate exists, make a single-band float32 GeoTIFF with probabilities in `[0,1]`, on the exact sample-template CRS, shape, bounds, and transform; put null/NaN only outside the valid footprint. Check for NaN/Inf *inside* the footprint, which can trigger the portal's “Predicted values must be in range [0, 1]” error. Make the download and the submission instructions obvious at the top of the site. Give every run a unique filename and a short paste-ready submission note.
4. **No slot without evidence:** pre-register 3–5 genuinely distinct geological hypotheses. Each must state the exact layers, physical signature, why it could indicate a fault absent from USGS/INGENIOUS, what makes it different from prior work, likely DTI change and cost, official data source/license/access status, and a falsifiable holdout gate. Validate the leading candidate against the current spatial-holdout best, with confirmation, before spending a weekly submission slot. No holdout pass means no slot.
5. **Research and provenance:** use free, publicly accessible, official or otherwise authoritative data where allowed. Verify claims against the relevant official/primary source line by line where possible; store exact citations/URLs, access and licensing checks, source hashes, experiment protocols, results, and irregularities. Distinguish official facts from user-supplied claims, owner-mirror evidence, hypotheses, and model estimates. Record unavailable files, failed downloads, and other blockers. Never invent a score, source, file hash, access result, or holdout result.
6. **Competition integrity:** respect the rules and source terms. Do not bypass the DrivenData login, collect or store account credentials, submit files, or consume competition slots on the user's behalf. Public leaderboard values are time-stamped snapshots; do not build a robot/spider that monitors DrivenData.
7. **Autonomous execution and accountability:** complete what can be done without asking for manual input; identify hard blockers rather than disguising them. Review work in three cumulative passes: implement and verify; inspect bugs/edge cases; re-check against this brief and fix. Flag every unresolved irregularity.
8. **Core values:** **Maximize P(Win)** by choosing evidence-driven work with a plausible path to generalization, not by chasing attractive but unverified claims. **Own the Outcome** end-to-end: record failures, fix defects, keep the user-facing path usable, and state what remains blocked.
9. **Project governance:** use this repository as the research and submission-tooling home. Keep private/large competition data and generated rasters out of Git. The final competition entry must satisfy all eligibility, documentation, AI-disclosure, and submission rules; confirm current requirements with the organizer when ambiguous.
10. **Delivery:** complete the requested code, documentation, and user-facing site work autonomously where possible. When asked, open a pull request from the assigned project branch and merge it to `main` if GitHub permissions and repository policy allow; report any failure and never claim a PR or merge that did not occur.

## Latest session outcome — supersedes older blocked-status paragraphs below

### Session 2026-10-03 (continued) — three real holdouts, one falsified hypothesis, one shipped candidate

Everything below was produced, measured and committed in this repository. Nothing here is a
leaderboard claim.

**1. The paired 300 m boundary-loss hypothesis is falsified.** Eight checkpoints (four spatial
folds × {regional, combined}), identical seed/architecture/steps, out-of-fold inference over the
whole grid. Pooled DTI: regional **0.105026**, combined **0.097119**, delta **−0.00791**;
positive in **1 of 4** folds. The geometry term adds **+107,821 units of far-field `FP_w`** and
the near-miss exchange rate is about **1 unit of new near-miss credit per 85 units of new distant
false-positive mass** — against a metric that prices them at 1 : 0.2. Verdict recorded as
`not promoted; no submission slot`. Evidence: `runs/loss-ablation/holdout.json`,
[docs/research/loss-ablation-verdict.md](docs/research/loss-ablation-verdict.md).

**2. Turning the model into dots matters more than any modelling change tried here.** The same
out-of-fold probability field scores **0.10503** submitted as a field and **0.25461** after
400 m Poisson-disk sparsification — a **2.4×** difference from the emission operator alone.
The learned field beats a blind lattice by only **+3.4 %** on the catalogue frame and **+4.4 %**
on the independent-inventory frame, which is the honest size of the localisation signal.
Evidence: [docs/research/emitter-holdout.md](docs/research/emitter-holdout.md).

**3. The external-data bridge works.** A GitHub Actions runner downloads official layers,
SHA-256-verifies them, rasterises them onto the competition grid and commits the result back
(`data/external/external_receipt.json`). Verified transfers: USGS SGMC `NV.zip` 69,056,094 B and
`CA.zip` 24,977,406 B; GDR 1391 paleo-geothermal, Quaternary volcanics and 2 m temperature
probes. Flagged irregularity: the Ingenious Quaternary-fault v2 shapefile downloaded but
rasterised to **zero** features inside the grid (CRS mismatch suspected).

**4. Rank-1 hypothesis (SGMC fault inventory) is delivered but not validated.**
`derived_sgmc_faults_100m_u8.tif`: 21,160 features, 82,151 px in the footprint, **61,664 px
(75.1 %) more than 300 m from every catalogue fault**. Two falsification tests disagree:
**+2.9× enrichment** over chance against the catalogue (positive) versus a **low-power lidar
corroboration test** (AUC 0.520, positive control also only 0.522). Full record:
[docs/hypotheses.md](docs/hypotheses.md), `docs/research/sgmc-falsification.json`.

**5. Metric theory that drives every decision here.** Adding one prediction pixel with kernel
credit `k` against an uncovered truth pixel changes the DTI denominator by exactly `0.2` and the
numerator by `k`, so **a dot helps iff `k > 0.2 × DTI`** — about **5.2 %** at the incumbent's
operating point. The rule does not depend on the size of the hidden truth set, which is why
broad, honest hedging across weak hypotheses is near-optimal under this metric.
Derivation and the measured response surface: [docs/metric-response-surface.md](docs/metric-response-surface.md).

**6. Shipped candidate (no leaderboard score, no slot used).**
`docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif` — single band, float32,
values in [0,1], EPSG:32611, 3730×3292, template-identical geotransform, NaN on all 7,111,787
cells outside the footprint, SHA-256 `fed5232e…66da`. It is the model's off-catalogue dots plus a
bounded SGMC hedge whose worst-case cost is ≤ 3 % of the DTI denominator. The historic
`…-nan.tif` artefact with the owner-reported 0.2600 stays as the incumbent reference.

### Session 2026-10-03 (earlier) — data restored, two pilots run

Read the standing brief above every session. On 2026-10-03 we autonomously restored SHA-256-pinned **owner mirrors** via GitHub API and prepared the real 3730×3292 grid (5,167,373 valid pixels, 60,988 catalogue positives). This resolves local data placement, **not organizer authenticity**. `python scripts/restore_public_mirrors.py` reproduces restoration; immutable pins are in `docs/research/mirror-pins.json`. The mirrored template contains labels: footprint only, never use its values as model features/predictions.

A preregistered four-arm CPU pilot ran all four 800 m-buffered spatial folds. See [protocol](docs/research/pilot-preregistration.md), [complete results](docs/research/pilot-results.json), [data audit](docs/research/data-audit.json). The top runnable strain/conductance interaction **failed its screen** against the same-run context control. No model candidate promoted; no competition slot used. This limited pointwise pilot is not a full-capacity U-Net or a comparison against the archived best.

The D2.8 historical research TIFF is now a **local one-click download** on the site, independently format-checked against the mirrored template. It remains score-attribution-unverified and not slot-approved. 25 tests pass in this session. Previous status text below describes the baseline, not today's restored state.

Later on 2026-10-03 the metric-aware emission line was exercised end to end: `src/gemsdoe30/emission.py` gained a masked-domain scorer fix and a count-matched candidate pool, `tests/test_emission.py` (19 tests) passes, and `scripts/emission_holdout.py` ran three count-matched arms on the four 300 m-buffered quadrants. **All three arms failed their registered gate** (adaptive minus uniform pooled ΔDTI +0.0008 to +0.0016, positive in only 1–2 of 4 folds): uniform Poisson-disk thinning stays the default, no candidate promoted, no slot used. Suite now collects 44 tests; 39 pass on this image and 5 torch-gated tests skip. Numbers: [emission-holdout-results.json](docs/research/emission-holdout-results.json). The owner-artifact audit in [artifact-structure.json](docs/research/artifact-structure.json) also records that catalogue-proxy DTI ordering is *inverted* relative to the owner-reported leaderboard ordering, consistent with the official rule that the Initial Prize Round scores only the private set of new expert-labelled faults.

## Current verified state — 2026-10-03

- The recorded baseline commit for this checkout already contains the model/loss, tests, training/inference/validation scripts, and site scaffold. The Git history available here is shallow/grafted to that commit, so earlier claims about a prior README-only state cannot be independently verified from this repository. At the start of this review there were **no competition rasters, sample template, checkpoints, real holdout predictions, or generated GEMSDOE30 TIFFs**; real-data training remains blocked.
- The DrivenData data page redirects an unauthenticated visitor to its login page. No DrivenData credentials/session or competition rasters are available here, and the shell cannot retrieve the public owner-mirror TIFFs in this environment. The safe data preflight is `bash scripts/download_competition_data.sh`; it reports missing inputs and does **not** attempt a login bypass.
- The official leaderboard was read on **2026-10-03**: the displayed leader was **DARD, 0.3195**. It is a live, changeable public score; it is not private-test performance. The supplied claim that the linked GEMSDOE25 D2.8 TIFF scored 0.2600 is **not authenticated to that exact file**: the GEMSDOE25 landing page currently describes that TIFF as unscored/not slot-approved, while the public leaderboard contains a 0.2600 row for participant `wbg1` at rank 15. See [analysis](docs/leaderboard-analysis.md) and [irregularities](docs/irregularities.md).
- The 300 m loss geometry and spatial-holdout pipeline are implemented. **23 tests pass** with NumPy, SciPy, rasterio, PyTorch, and pytest installed; the geometry term matches the independent metric on a masked grid, and a seam regression test confirms the pooled OOF score keeps 100 m near-miss credit across quadrants. Review fixed quadrant-component pooling, prevents fold-specific checkpoints from being relabeled across OOF folds, and checks prediction/checkpoint hashes and experiment recipes. A disposable synthetic 64×64 smoke passed paired four-fold training/inference, OOF stitching/evaluation, full-fit inference, and exact-template TIFF validation. **All are software/synthetic checks only. No real spatial holdout has run, no score gain is claimed, and no new GEMSDOE30 TIFF has been produced.**
- The site exposes a one-click link to the pre-existing GEMSDOE25 research TIFF, clearly labeled external, unscored, and not slot-approved. It is not represented as this repository's model output or as an approved competition submission. A genuine GEMSDOE30 download will be generated only after data placement, training, holdout promotion, and exact-template validation.

## Start here

1. Read the [executive summary and submission guide](executive-summary.html).
2. Read the styled [leaderboard/file attribution analysis](docs/leaderboard-analysis.html), [ranked hypotheses](docs/hypotheses.html), [loss design](docs/loss-design.html), and [irregularity register](docs/irregularities.html).
3. Review the styled [official/primary source register](docs/sources.html); full claim-by-claim notes remain in `docs/sources.md`. Before any eventual entry, review the [working AI-use disclosure draft](docs/ai-disclosure-draft.md) against every team member's actual use.
4. Install the optional geospatial/training stack and run the test suite (optional geospatial and loss-gradient tests run when their dependencies are installed):

   ```bash
   python -m pip install -e '.[train,test]'
   python -m unittest discover -s tests -v
   python scripts/loss_geometry_probe.py
   ```

5. Place the competition files, downloaded through an authorized competition session, in `data/raw/` as `training_features.tif`, `labels.tif`, and `sample_submission.tif`. Then run:

   ```bash
   bash scripts/download_competition_data.sh
   python scripts/prepare_data.py
   ```

   The preparation script fails closed on CRS, transform, shape, label encoding, or footprint mismatch. It records SHA-256 values for the three source rasters and a dataset signature in the prepared manifest, then writes raw features and masks under the Git-ignored `data/processed/`. Each training run fits and stores its own robust normalization statistics using training-fold pixels only, never held-out pixels; the checkpoint is bound to that prepared dataset signature.

6. Run the *paired* loss experiment on all four buffered spatial folds with the same seed and optimization settings in both arms. For each fold `F` in `0 1 2 3`, run:

   ```bash
   python scripts/train_model.py --fold F --loss regional --output runs/fF-regional.pt
   python scripts/train_model.py --fold F --loss combined --output runs/fF-combined.pt
   python scripts/infer_model.py --checkpoint runs/fF-regional.pt --fold F --predictions-only --output runs/fF-regional.npy
   python scripts/infer_model.py --checkpoint runs/fF-combined.pt --fold F --predictions-only --output runs/fF-combined.npy
   ```

   Keep each inference `.json` sidecar beside its `.npy`. The stitcher checks prediction-array and checkpoint SHA-256 values, explicit checkpoint/fold identity, the source-bound prepared-grid/dataset signature, identical training recipes, and held-out-only masks before it creates a hashed OOF mosaic. The evaluator verifies both OOF manifests and paired recipes. It computes the exact pooled DTI once over the complete stitched OOF grid (retaining cross-quadrant 300 m interactions); fold-isolated values are diagnostics only. Then compare both arms with the exact metric and near-miss diagnostics:

   ```bash
   python scripts/stitch_oof_predictions.py --fold0 runs/f0-regional.npy --fold1 runs/f1-regional.npy --fold2 runs/f2-regional.npy --fold3 runs/f3-regional.npy --output runs/regional-oof.npy
   python scripts/stitch_oof_predictions.py --fold0 runs/f0-combined.npy --fold1 runs/f1-combined.npy --fold2 runs/f2-combined.npy --fold3 runs/f3-combined.npy --output runs/combined-oof.npy
   python scripts/evaluate_loss_ablation.py --regional runs/regional-oof.npy --combined runs/combined-oof.npy
   ```

   Repeat the complete paired design with preregistered fresh seeds for confirmation. Do not treat one fold or the synthetic probe as confirmation.

7. Only after a candidate clears the frozen holdout and confirmation gates should it be fit on all permitted training labels. `scripts/infer_model.py` or `scripts/build_submission.py` writes a uniquely named, template-matched TIFF and a JSON sidecar. `scripts/validate_submission.py FILE.tif --template data/raw/sample_submission.tif` must pass before any human upload.

## Useful links

- [DrivenData competition homepage](https://www.drivendata.org/competitions/306/competition-doe-gems/) — navigate to Problem Description, About, Data, and Leaderboard. The requested direct pages are documented in `docs/sources.md`.
- [Official GEMS rules PDF (NLR, September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
- [DOE Geothermal Data Repository: INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391)
- [Kervadec et al., Boundary loss (2018 preprint; PMLR proceedings 2019)](https://proceedings.mlr.press/v102/kervadec19a.html)

## Repository map

- `index.html`, `executive-summary.html`, `docs/assets/site.css` — GitHub Pages landing page and submission instructions; the landing page links the external reference TIFF, not an approved GEMSDOE30 result.
- `docs/ai-disclosure-draft.md` — truthful current-session starting point for the rules-required entrant narrative; must be updated and reviewed before any entry.
- `src/gemsdoe30/metric.py` — reference DTI implementation; vectorized with NumPy/SciPy when installed, dependency-free for small tests.
- `src/gemsdoe30/losses.py` — regional soft-Tversky plus the 300 m metric-geometry term, inspired by (not a verbatim copy of) Kervadec et al.
- `src/gemsdoe30/cv.py`, `analysis.py` — buffered spatial blocks, exact full-grid OOF scoring, fold-isolated diagnostics, and near-miss profiles.
- `src/gemsdoe30/normalization.py` — deterministic robust scaling fit separately on each training-fold mask and saved in each checkpoint to prevent held-out feature leakage.
- `src/gemsdoe30/submission.py` — strict GeoTIFF writer/validator and sidecar.
- `scripts/` — data preflight, preparation, paired training arms, inference, validation, and probes.
- `docs/` — source ledger, reported-score ledger, hypothesis register, results interpretation, and irregularities.
- `data/raw/`, `data/processed/`, `outputs/`, `runs/` — local-only data and outputs; ignored by Git.

## Current next steps and limits

1. **No candidate here has a leaderboard score.** The only verified number in the repository is
   the historic artefact's owner-reported 0.2600. The shipped candidate beat a blind lattice by
   +4.4 % on the only independent off-catalogue frame that exists, which is necessary but not
   sufficient evidence. Spending a slot is a judgement call the user owns; the file and its
   paste-ready comment are ready if that call is made.
2. **The catalogue cannot validate off-catalogue strategies.** Any holdout whose truth is the
   public catalogue can only reward predictions placed on that catalogue — and those pixels are
   exactly the ones the organizer masks out. Every remaining hypothesis must therefore be scored
   on an independent inventory frame (`scripts/novelty_holdout.py`) or on the private test set.
3. **Hypotheses 2–5 are registered but unrun** (`docs/hypotheses.md`). Next in line: the 1 m
   lidar paired-curvature scarp transform (H2), then the tilt-angle/upward-continuation field for
   buried structures (H3). Each needs its own pre-registered screen, the four buffered spatial
   folds, and a same-run control.
4. **H1's SGMC hedge cannot be validated locally.** It is shipped as an explicitly bounded,
   unvalidated bet. If the user prefers maximum conservatism, ship
   `runs/candidates/model_t04_s4.npy` (the same model dots without the hedge) instead — the two
   differ only by the 5,281 inventory pixels.
5. **Open irregularities to resolve with the organizer or by re-reading sources:** the Ingenious
   Quaternary-fault v2 CRS failure; the competition-homepage end time (2026-12-03 23:59 UTC)
   versus the rules PDF's Appendix A.1 (17:00 ET); and the fact that SGMC linework carries **no
   age attribute**, which prevents restricting the hedge to late-Cenozoic faults.
6. **Deadline and submission mechanics remain manual.** DrivenData's Terms of Use prohibit
   robots/spiders/automatic access, so there is no automated leaderboard feed and no automated
   upload. The site's status feed (`docs/status.json`) is the machine-readable summary this
   project can offer.
7. **Reproduce everything from a clean checkout** with the commands in *Start here*; the two new
   holdout scripts are `scripts/emitter_comparison.py` and `scripts/novelty_holdout.py`, and the
   candidate builder is `scripts/build_candidate_dots.py`.
