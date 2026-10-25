# TDX-1 — three-pass verification journal

Date: **2026-10-25 UTC**. Session branch: `arena/54be04c9-gemsdoe30`.
Current selection: [docs/current-run.json](../../current-run.json).
**Research verdict: NEGATIVE. Download for research; DO NOT SUBMIT.**
No human-inspector override, competition authentication, uploader or weekly-slot selector exists here.

## Pass 1 — implementation and real-data execution

- Read the owner brief and prior nine-site scientific audit; retained the complete
  current task text in [README](../../../README.md#current-owner-prompt).
- Ranked four unimplemented physical mechanisms before the first fit; selected only
  gravity-normal magnetic profile displacement. Exact bands, signatures, non-fault
  mimics, utility/cost and distinctions from earlier code are in the original plan
  (frozen at the first-run commit) and [corrective plan](preregistration.md).
- Restored hash-pinned physical inputs and prepared the cached stack. Dataset signature
  `291d346794ba20730708eaf1ab0f5695396732d7f1b183382ec1f3aeede855ed`.
  Owner mirrors are not organizer authentication.
- Reused the shared evaluator/writer/sampler; added whole-component buffered folds
  and pooled geographic-block sufficient statistics centrally, not in private forks.
- Snapshotted 119 public TIFF sources across the nine priority sites. Compared 104
  unique aligned files; one toy off-grid exclusion. Global/parallel coverage remains incomplete.
- Executed one fixed hypothesis with three prespecified arms. Initial 16px execution
  took 196.32 seconds and was negative. Its sources, plan, outputs and statistics are
  frozen at `361b128f9951191378a3a07b06a5d76ce1933836`.
- Built a responsive landing page and executive submission guide with the download,
  automated blocked status, short note, exact hash and evidence links at the top.

## Pass 2 — defect discovery, fixes and one corrective execution

- **Support-bound defect:** square Gaussian corners plus profile sampling and bilinear
  interpolation can reach 16.6077 px; 16px was not conservative. Registered the analytic
  correction before rebuilding/refitting: use 17px support **and** training guard.
  No geological scale, lag, model, density, emitter or outcome-dependent threshold was tuned.
- The current transform is `tdx1-profiles-v2-euclidean-support-20261025`.
  A regression checks diagonal reach and exclusion around unavailable source cells.
  [Original-run retirement / immutable source link](correction-v1-retirement.json).
- Corrective execution: **204.86 seconds**, **401.18 cumulative seconds**, two executions
  in total—within three experiments/two hours. This is the same hypothesis on already
  inspected folds, **not fresh independent confirmation or a second independent method**.
- The shared cache verifier compared **every** prepared feature, label and mask cell
  with pinned raw-source windows before the corrective fit. It hashes all four arrays.
  Tests detect altered caches even when raw-source hashes remain unchanged.
- Corrected an invalid arbitrary-binarization theorem; a counterexample regression
  distinguishes common-amplitude monotonicity from independently raising weak false positives.
- Central writer rejects mismatched CRS, blank identity and notes over 140 characters.
- Strengthened verification to recompute the full pooled summary and paired CIs,
  check comparator/run-card agreement, reject truncated CIs, bind exact template/
  registry/preregistration identities, and reject repeated references with misleading counts.
- Added frozen-registry restore: no main-branch refresh, no JSON rewrite, no new experiment.
  Restored/verified all 105 frozen files including the exclusion. Bad remote/cached blobs fail.
- Current feed follows the explicit run pointer and reopens the exact TIFF. Historical
  range-immunity fields are quarantined as legacy claims; none advertise current immunity.
- Preview serves public assets only; hidden/ignored paths, directory listings and private
  symlink targets are blocked. Preview host is accepted; server binds `0.0.0.0`.

## Pass 3 — full requirements, consistency and reliability review

| Requirement | Verified outcome / limitation |
|---|---|
| Genuinely new TIFF, not historical re-encoding | New six-feature fit, new physical transform, 44,090 dots; no historical raster values enter features or placement. The earlier internal TDX fit is explicitly same-family, not claimed independent novelty. |
| Current artifact identity | `gems30-TDX1-44090-20261025-5fc508ea81ac.tif`; SHA-256 `9556e3ddd8ea7658ca510ab02d5b5304ac4c3332c54e7f86df5a24769bd03cdb`. |
| Public TIFF contract | Reopened: one float32 band, EPSG:32611, 3730×3292, exact affine grid, finite [0,1] inside, NaN nodata outside. Zero positive-catalogue pixels. Private portal acceptance remains unverified. |
| HOLDOUT-DTI | Evaluator `component-holdout-v3-blockstats-20261025`; protocol `buffered-quadrant-whole-components-v1-20261025`, **17px guard**, 60,988 withheld positives, 371 geographic blocks / 2,000 paired bootstrap draws. Candidate **0.072844**, 95% CI **[0.063483, 0.083061]**. |
| Same-protocol stronger comparator | Core19 HOLDOUT-DTI **0.139821**, 95% CI **[0.124178, 0.155905]**; same evaluator/guard/withheld positives. Candidate difference **−0.066977**, paired 95% CI **[−0.085747, −0.048300]**. Performance gate fails. |
| Feature canaries | 22 features × four folds; no AUC >0.90. Maximum bidirectional raw/univariate AUC ≈0.643433. Diagnostic only, not proof against upstream leakage. |
| Observed novelty | Across 108 observed comparisons: surface max Spearman 0.053133; dots max Spearman 0.013710; maximum directional Euclidean ≤3px overlap 40.4922%. No observed stop threshold crossed in the frozen external snapshot; global coverage incomplete. |
| Automated decision | Eight gates passed, one failed, three unknown. Ordinary verifier exits 0 only for a consistent research receipt; `--require-promote` returns expected **2**. Submission approved false; slot selected false. |
| H33 explanation | Exact support reconstruction and source-linked metric mechanism, not organizer-confirmed causation. Owner's 0.2778 remains unverified; G32’s historical 0.4413 was explicitly unreliable mirror drift, not an organizer file result; newer peer leaderboard claims are separate and not freshly fetched by this lane. No higher-score forecast. |
| Complete owner/source record | Full task text preserved; 119 distinct named submission claims retained in quarantined CSV, including an unknown/blank result. No fabricated organizer receipts or current leader. Official/free-source review links distinguish freshly read GitHub code from hosts inaccessible here. |
| User-facing download | Automated browser checks at 1440×1100 and 390×844: overview, guide, working TIFF download/hash, note copy warning, no page errors or horizontal overflow. No upload action. [Browser receipt](browser-check.json). |
| Static/site regression | Local links and HTML anchors resolve; current artifact identity/note matches both pages; generated HTML and actual-raster PNG reproduce exactly. |
| Tests | **180 passed, 5 skipped, 7 subtests passed**. Five skips are optional torch training/loss tests; no torch/GPU execution claimed. Two rasterio/Affine pending-deprecation warnings, not failures. |
| Experimental restraint | No further fitting, hyperparameter sweep or slot selection after the corrective negative result. Unknown historical-best checkpoint, external lane allocation, complete parallel registry and portal constraints remain blockers. |

### Commands actually verified

```bash
.venv/bin/python scripts/verify_prepared_cache.py
.venv/bin/python scripts/sync_priority_registry.py --restore-only
.venv/bin/python scripts/verify_current_run.py
.venv/bin/python scripts/build_research_site.py --check
.venv/bin/python -m pytest -q
# Expected return code: 2, not successful promotion.
.venv/bin/python scripts/verify_current_run.py --require-promote
node scripts/browser_smoke.cjs
git diff --check
```

The optional browser driver uses pinned `playwright-core@1.64.1` and
`@sparticuz/chromium@153.0.0` under ignored `outputs/browser/`; screenshots/download
copies are not committed. No external fonts or generated marketing images are used.
Direct scientific dependency versions are in [requirements-tdx1.txt](../../../requirements-tdx1.txt);
the [environment receipt](environment-and-sources.json) records execution versions.
Bitwise reproduction across different platforms/versions is not promised.

## Delivery state

Local three-pass checks above are complete. [PR #28](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/28)
was opened from the assigned session branch. The PR timeline is the authoritative
GitHub checks/merge receipt; CI, merge and deployment are not presumed successful
by this pre-merge journal. The final response records the separately observed result.
Concurrent main-branch history must be preserved, and unrelated open PRs are not closed.

## Remaining work (not performed experiments)

1. Share complete parallel/surface registry and identifiable lane allocation programmatically.
2. Preserve this negative result. Preregister same-feature-count zero-lag/phase-scrambled
   falsification on a genuinely fresh confirmation design, not a different seed on these folds.
3. Only after that, assess additive information alongside all core modalities.
4. Rerun a source/fold-bound historical-best checkpoint with the same exact evaluator,
   guard and emission protocol; do not equate the core19 recipe control with that best.
5. Keep the separate slot selector closed until its current portal/rules/entrant evidence
   exists. Neither a valid TIFF nor automated local inspection can invent organizer acceptance.


## Concurrent-main integration check

Integrated main through `7f3f4c7` without closing or merging unrelated PRs. Preserved
#24's worktree-only availability scope, all peer code/results/downloads, and both
score-ledger streams (136 rows total; current task claims remain unverified).
Namespaced TDX irregularities (`IR-TDX-*`) to avoid collisions with concurrently
assigned IDs. The shared max-kernel extraction merged cleanly; all pooled/tile
regressions and recomputed TDX confidence intervals still pass unchanged.

Four late TIFFs were checked against both saved TDX states, with no refit or dot
changes. The exact addendum and its source commit are immutable evidence. Readiness
now covers 108 observed references and blocks if a newly arrived or removed local
reference lacks matching evidence. Local post-integration suite: **180 passed,
5 optional torch skips, 7 subtests passed**, two rasterio deprecation warnings.
Peer `promote` reports remain separate from the selected TDX negative decision.


Publication preflight caught a generated landing-page change left unstaged while
resolving the concurrent merge. Included the generated root HTML in the follow-up
publication commit and repeated the exact-site check; no model or raster changed.
A clean-worktree assertion is required before the final push/merge verification.
