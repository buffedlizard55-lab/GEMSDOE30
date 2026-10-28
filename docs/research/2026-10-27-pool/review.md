# POOL-1 review — pooled MSDB∪CSR∪LiDAR lane: mechanism **confirmed**, artifact **duplicate-stopped** (2026-10-27)

> **Post-merge addendum (2026-10-27):** PR #55's registry-preflight proved the pinned 13GEMSDOE lattice stops every ≥22,164-dot candidate under a literal any-raster 70% rule (CSR-1 measured 99.9864% vs the lattice). POOL-1's frozen registry reported lattices/dense parents separately, and CTD-1/FC-1 (merged in parallel) postdate it — POOL-1 vs CTD-1/FC-1 = 0.55%/2.81% (no collision). Frozen receipts unchanged; see `postmerge-addendum.json`. POOL-2 (§7) additionally requires the owner's lattice-policy resolution.
>
> **Current-status correction / superseding review:** This document is an archived POOL-1 run report. Its prior §5 score-causation explanation, §6 “unique” scope, §7 POOL-2 continuation sketch, and §8 leaderboard freshness are superseded. H33-B2’s file lineage is verified but its claimed score cause is unknown; CSR-1 is stopped under the later literal lattice rule; there is no current public-score estimate, assigned lane, or slot approval. The current file/score/uniqueness answer and ranked unrun hypotheses are in [`2026-10-27-followup-review.md`](../2026-10-27-followup-review.md). The POOL-1 holdout receipt remains historical method evidence only.

## 1. Decision (no ambiguity, no human inspection anywhere)

| Question | Answer |
|---|---|
| New TIFF to download from this run? | **NO — none was published.** The production raster breached the frozen duplicate-stop rule and was quarantined in ignored `runs/pool1/` (sha256 `1d9cab5d…`). It must not be renamed, re-encoded or perturbed into a "unique" file (AGENTS.md rule 2). |
| OK TO SUBMIT anything new this week? | **NO.** `verdict=negative`, `download_ok=false`, `ok_to_submit=false`, `slot_selected=false`. Verify: `.venv/bin/python scripts/verify_pool_run.py` → exit 0; `--require-promote` → exit 2. |
| Did the science work? | **YES — first lane in this repo to beat the standing best (`msdb_edge`) on the shared evaluator, confirmed on a second seed.** The mechanism is the deliverable; the raster is not. |
| What is the current next action? | **No run.** The latest follow-up has no assigned lane and the literal lattice policy still stops the prescribed budget. Any future lane requires explicit assignment, policy resolution, fresh preregistration, and complete gates; do not rescue this raster. |
| Is any file safe under the current literal rule? | **No.** CSR-1 and POOL-1 are stopped; a local format pass or prior scoped novelty result is not an upload authorization. |

## 2. What was frozen before fitting

Preregistration `preregistration.md` (sha256 `ae3d7c89…`) + `preregistration.json`
(`083fb44b…`), registry `registry.json` (sha256 `5b6f77da…`, built from depth-1 clones of
the nine priority sites at 2026-10-27 HEADs: **394 aligned rasters**, 2 classified
exclusions, 6 dense-parent calibration exclusions reported separately). Five ranked
hypotheses were frozen; POOL-1 (rank 1) was executed. Data restored from pinned owner
mirrors and verified cell-exact (`dataset_signature 291d3467…`, features `4371c82e…`,
labels `7ba308cc…`, template `2176d08e…`). Data are owner mirrors, **not**
organizer-authenticated (DrivenData data page is login-walled; no credentials used).

**Lane:** one HGB over 13 stationary raw bands + MSDB-18 piedmont/curvilinear +
CSR-27 cover-compensated Laplace/Poisson/Radon + LiDAR-17 morphology (75 features),
Prentice–Pyke calibration × MSDB Rayleigh gate, CSR dispersed EDGE emitter
(γ=1.25, `dr²+dc²>6`, >2 px off-catalogue, 44,090 dots). No prior lane pooled
MSDB-18 with CSR-27 in a single fitted model (FFL-1: MSDB+LiDAR only, duplicate-stopped
at 78.28%; CSR-1: dual-expert Noisy-OR that never saw MSDB features and excluded
`det_elev`).

## 3. Holdout results (all values HOLDOUT-DTI, evaluator `component-holdout-v3-blockstats-20261025`, protocol `buffered-quadrant-whole-components-v1-20261025`, 60,988 withheld positives, 17 px whole-component guard, 371 blocks, 2,000 paired bootstrap replicates)

Experiment 1 (seed 4201):

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
| `msdb_edge` (standing bar) | 0.169468 | [0.155445, 0.183465] |
| `pool_dense_edge` (diagnostic) | 0.188702 | [0.174361, 0.203224] |
| **`pool_dispersed` (candidate)** | **0.186699** | **[0.173113, 0.200171]** |

Candidate − `msdb_edge` = **+0.017231 [+0.010515, +0.023980]** → E1 gate **passed**.
Dispersion cost vs dense: −0.002003 [−0.004005, −0.000065].
Per-fold candidate vs bar: F0 0.15384 vs 0.14816; F1 0.23994 vs 0.22054;
F2 0.18765 vs 0.16128; F3 0.21235 vs 0.17200 (**4/4 folds**, incl. +0.040 in the SE
Walker Lane fold where CSR-1 alone previously beat MSDB by +0.023).

Experiment 2 (confirmation, seed 4219): `pool_dispersed` **0.187694** [0.173631, 0.201989]
vs `msdb_edge` 0.174247 [0.160153, 0.188516]; Δ **+0.013446 [+0.006993, +0.019757]** →
gate **passed** (4/4 folds again).

Leakage canaries: 81 features × 4 folds, **0 alarms**, max symmetric AUC **0.6635 ≤ 0.90**.
For scale: previous best on this evaluator was MSDB-1v2 0.170462; CSR-1 0.158162.
POOL-1's 0.1867/0.1877 is a **+10% relative** improvement over the bar with paired CIs
excluding zero on two seeds. This is catalogue-recovery evidence, **not** a leaderboard
score or projection (see §5).

## 4. Why the artifact was stopped (novelty, two stages, 394 rasters)

- Stage 1 (pre-placement surface): max Spearman **0.1366 ≤ 0.90 — passed**.
- Stage 2 (final dots): max Spearman 0.2813, but **88.74%** of POOL-1 dots lie within
  3 px of `gems30-FFL1-fusion_edge` dots, **75.81%** vs published `MSDB1-edge`, and
  **71.08%** vs published `CSR1` — three breaches of the frozen **70%** duplicate-stop
  rule (next-highest reference: GEMSDOE32 at 66.50%). 0 audit errors; the malformed
  GEMSDOE31 raster (2,610,312 in-footprint NaNs) was finite-subset-audited (2.29%).
- Root cause (same physics CSR-1 diagnosed): the pooled model re-imports the MSDB/FFL
  range-front habitat, whose dense 1–2 px dot packing saturates the same corridors.
  CSR-1 escaped (59.86–67.70%) because its subsurface expert placed dots in genuinely
  different places; pooling traded that placement diversity for recall. Surface
  correlation stayed low (≤0.137) while *dot* overlap exploded — exactly why the
  protocol checks both stages.
- Dense calibration parents (reported separately, not hidden): 51.52% vs h19-5 parent,
  53.28% vs GEMSDOE31 union — POOL-1 is **not** an h19-5-family clone; it collides only
  with this repo's own MSDB-family dot packings.

Format of the quarantined raster itself was valid (12/12 strict checks: single float32
band, EPSG:32611, 3730×3292, exact transform, all 12,279,160 cells finite in [0,1],
44,090 dots, 0 within ≤2 px of catalogue, min NN 2.828 px) — it would not trigger the
portal "Predicted values must be in range [0, 1]" rejection. It is withheld solely for
duplication. Experiments used: **3/3**, 1,396 s.

## 5. H33-B2 file lineage and limits on explaining the owner-reported value

The frozen pixel audit (`fleet-audit.json`) establishes a file lineage: GEMSDOE25 D2.8 and GEMSDOE30 d28 are value-identical; an r1 intermediate is formed after 3,891 dots are removed; H33-B2 is formed after a further 2,545 are removed and contains 37,654 dots; GEMSDOE36 PINN contains H33-B2 plus 1,200 dots. The selected 37,660-dot GEMSDOE28 historical file is different from the G28 r1 intermediate identical to the GEMSDOE31 selection. The values 0.2600, 0.2708, 0.2778, and 0.2750 are owner-reported claims, not organizer-confirmed scores.

Removing near-catalogue dots could plausibly reduce false-positive cost, but the hidden labels are unavailable. The audit cannot determine whether removed cells were true or false positives, prove constant true-positive credit, or show that pruning caused the owner-reported score differences. It is verified raster genealogy, not a causal score explanation or new geological discovery.

POOL-1's two-seed, same-evaluator HOLDOUT-DTI improvement over `msdb_edge` is reported with its evaluator, withheld-positive count, and confidence intervals in §3. This supports only the preregistered catalogue-recovery proxy. It does not establish performance on expert-mapped new faults or predict a public leaderboard score. No defensible public-score estimate is available. The repository's 27 Oct leaderboard snapshot of 0.4544 conflicts with the user-supplied 0.3195 current value and an earlier repository snapshot; no live check was made here, so neither value is asserted current.

## 6. The nine sites in one table (full detail: `nine-site-executive-summary.md`)

| Site | Historical leader (owner-reported) | Within-nine novelty only (frozen snapshot; not global) | Archived site status (not current selector) | Historical research file | Current literal-rule decision |
|---|---|---|---|---|---|
| GEMSDOE24 | D1.5 0.2477 | No — h19-5 family; ⊂ GEMSDOE27 | No new submission authorized; lattice-feasibility stop | — | **NO** |
| GEMSDOE25 | D2.8 0.2600 (owner-reported) | No — **identical to GEMSDOE30 d28** | H73-BW blocked pre-fit; H73-PM archived negative in its own site frame | — | **NO** |
| GEMSDOE27 | gap-closure 0.2449 (owner-reported) | No — = D1.5 + 1,259 dots | H31-1 site-specific evidence-qualified result; selector decision pending; later site trials archived negative | H31-1 (research) | **NO** (site's own selector step) |
| GEMSDOE28 | r1 intermediate 0.2708 (owner-reported) | r1 intermediate = GEMSDOE31; the selected 37,660-dot G28 historical file is different | S22C site-specific gates reported passed; selector checklist was still required; not a current selector | Historical research sources only | **NO** — lattice stop for the selected budget |
| GEMSDOE30 | d28 0.2600 (owner-reported) | 67.70% applied only to 380 dotted rasters; later literal check stops CSR-1 at ≥84.9195% by bound and 99.9864% measured vs lattice | **POOL-1: confirmed same-protocol holdout improvement, duplicate-stopped raster** | Historical CSR-1 research file only | **NO** — literal duplicate stop; no slot |
| GEMSDOE31 | solo-d28 0.2708 | No — identical to GEMSDOE28 r1 | No file approved; projections audited unreliable | — | **NO** |
| GEMSDOE32 | **H33-B2 0.2778 (owner-reported)** | No — exact pruned subset of r1 | H47-1 LDGI archived site-frame result; verdict negative | — | **NO** |
| GEMSDOE33 | H33D 0.2632 | Overlaps family, not a subset | FSML2-CC unique but negative | — | **NO** |
| GEMSDOE36 | PINN 0.2750 (owner-reported) | No — = H33-B2 + 1,200 dots | KPL-36 site banner and owner-ledger status conflict; neither is current selector approval or an organizer receipt | — | **NO** — pinned-lattice stop |

Cross-site holdout results are **not comparable** because evaluators, withheld labels, and folds differ. They are omitted from current performance ranking unless the exact evaluator version, withheld-positive count, and 95% CI are available. Only same-protocol paired deltas rank methods.

**Public-score estimate: none.** The archived cross-family calibration does not justify a point estimate for an unsubmitted file; HOLDOUT-DTI and organizer scoring target different reference labels. No projection or scenario range is published here as a score. All owner-ledger values remain unverified claims, and no live leaderboard state is asserted.

## 7. Archived POOL-2 sketch — NOT a current lane or authorization

This historical design sketch is retained for provenance only. It is not the next
session's assignment and must not be run under the current duplicate stop. Any
future experiment requires an explicit assigned lane, a documented registry-policy
resolution, available/audited inputs, and fresh preregistration before a fit. The
old sketch proposed a pooled model with spacing and near-set exclusions, evaluated
against matched controls. Those constraints do not override the pinned-lattice bound,
which stops the prescribed 44,090-dot budget regardless. KRA-1 Riedel alignment and
MCD-1 clay-cap saddle were also prior proposals, not current authorizations.

## 8. Irregularities flagged

- IR-POOL-01: no externally assigned single-method lane paragraph in the prompt; lane self-assigned and frozen here (same standing gap as all prior lanes).
- IR-POOL-02: repository snapshot records 0.4544 on 27 Oct; user-supplied 0.3195 conflicts, and the repository records that value in an earlier snapshot. No live check was made in this follow-up; neither value is asserted current.
- IR-POOL-03: several historical files share an emission family. D2.8/GEMSDOE25 and d28/GEMSDOE30 are value-identical; the G28 r1 intermediate is identical to the G31 selection, while the selected 37,660-dot G28 file is different; D1.5 is a subset of the G27 gap-closure file.
- IR-POOL-04: GEMSDOE31 clone contains an aligned raster with 2,610,312 in-footprint NaNs (`gemsdoe31-csdu-stepover-8cf9dc27-nan.tif`) — would fail portal range checks; finite-subset audited.
- IR-POOL-05: GEMSDOE36's site banner says "OK TO SUBMIT / verdict: promote" for KPL-36, while the owner ledger reports 0.1647 for that file. No organizer receipt was found for the claim; do not treat the banner or ledger as current selector approval.
- IR-POOL-06: training data are owner mirrors, not organizer-authenticated; DrivenData/GitHub-Pages/Dropbox hosts are unreachable from this sandbox (only github.com/api.github.com/PyPI), so site review used git clones + the public leaderboard page.

## 9. Reproduce / verify (no human inspection)

```bash
.venv/bin/python scripts/verify_pool_run.py            # exit 0: negative verified
.venv/bin/python scripts/verify_pool_run.py --require-promote   # exit 2
.venv/bin/python scripts/validate_submission.py runs/pool1/gems30-POOL1-44090-20261027-fabc56fb91db-zeros.tif \
  --template data/raw/sample_submission.tif --finite-all-cells  # 12/12 format checks (quarantined file)
.venv/bin/python -m pytest tests/test_pool1_release.py -q
```

Official sources: [problem description & metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) ·
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ·
[reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) ·
[rules PDF (NLR 96647)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) ·
[GeoDAWN (USGS)](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) ·
[INGENIOUS](https://gbcge.org/current-projects/ingenious/) · [EPSG:32611](https://epsg.io/32611) ·
[Tversky index](https://en.wikipedia.org/wiki/Tversky_index)
