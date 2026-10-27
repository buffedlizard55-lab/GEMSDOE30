# POOL-1 review — pooled MSDB∪CSR∪LiDAR lane: mechanism **confirmed**, artifact **duplicate-stopped** (2026-10-27)

> **Post-merge addendum (2026-10-27):** PR #55's registry-preflight proved the pinned 13GEMSDOE lattice stops every ≥22,164-dot candidate under a literal any-raster 70% rule (CSR-1 measured 99.9864% vs the lattice). POOL-1's frozen registry reported lattices/dense parents separately, and CTD-1/FC-1 (merged in parallel) postdate it — POOL-1 vs CTD-1/FC-1 = 0.55%/2.81% (no collision). Frozen receipts unchanged; see `postmerge-addendum.json`. POOL-2 (§7) additionally requires the owner's lattice-policy resolution.


## 1. Decision (no ambiguity, no human inspection anywhere)

| Question | Answer |
|---|---|
| New TIFF to download from this run? | **NO — none was published.** The production raster breached the frozen duplicate-stop rule and was quarantined in ignored `runs/pool1/` (sha256 `1d9cab5d…`). It must not be renamed, re-encoded or perturbed into a "unique" file (AGENTS.md rule 2). |
| OK TO SUBMIT anything new this week? | **NO.** `verdict=negative`, `download_ok=false`, `ok_to_submit=false`, `slot_selected=false`. Verify: `.venv/bin/python scripts/verify_pool_run.py` → exit 0; `--require-promote` → exit 2. |
| Did the science work? | **YES — first lane in this repo to beat the standing best (`msdb_edge`) on the shared evaluator, confirmed on a second seed.** The mechanism is the deliverable; the raster is not. |
| What is the single best next action? | Next session, under a fresh budget and a **new preregistration (POOL-2, §7)**: pooled features + a novelty-constrained emitter frozen *before* fitting. Do not rescue this raster. |
| If a slot were spent today anyway (owner override, against advice)? | The only already-published, format-valid, still-unique file in this repo is CSR-1 (§6). It is **not** approved — it trails `msdb_edge` on holdout. |

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

## 5. PhD answer: why GEMSDOE32's H33-B2 (0.2778, owner-reported) tops the nine sites, and what beating it requires

Re-verified pixel-exactly today on 2026-10-27 HEAD clones (`fleet-audit.json`):

`h19-5` (121,131 px, 0.1922) → D2.8 (44,090, 0.2600; GEMSDOE25 = GEMSDOE30 identical)
→ r1 (40,199, 0.2708; GEMSDOE28 = GEMSDOE31 identical) → H33-B2 (37,654, 0.2778) →
PINN (38,854, 0.2750). Each step **adds zero dots**: r1 deletes exactly the 3,891 dots
at 1.0 px from the catalogue; H33-B2 deletes exactly the 2,545 dots at 1.41–2.0 px.
Because the organizer masks known-fault pixels pixel-exactly with **no buffer**, 1–2 px
halo dots are unmasked false positives paying 0.2 each, while a dot at 3 px still earns
kernel credit at 1–2 px (triangular kernel, R=300 m). The entire 0.2600→0.2778 gain is
denominator hygiene (0.2·FP ↓), not new geology; PINN's +1,200 dots reversed a little
of it (0.2750). All four numbers are **owner-reported** — no organizer receipt binds any
of them to a file in any repo we can inspect.

Consequences: (i) the pruning ceiling is exhausted — further gains require **recall of
hidden faults**, which carry 4× the FP weight (β=0.8 vs α=0.2); (ii) catalogue-recovery
HOLDOUT-DTI and the public leaderboard measure different truths (withheld catalogue
segments vs expert-mapped *new* faults, which forum clarifications suggest include new
geometry of existing systems) — the h19-5 habitat is dense exactly where such new
geometry lives, which a >2 px off-catalogue, dispersed emitter deliberately avoids.
Our holdout therefore *cannot* certify ">0.2778"; anyone claiming a calibrated
leaderboard estimate from it is overfitting a proxy (GEMSDOE31's cross-family audit:
best LOO RMSE 0.090). Live leaderboard today (2026-10-27, read via the public page):
**#1 = 0.4544** (xiaofanhu); the prompt's 0.4413 was the 2026-10-25 value and 0.3195 a
2026-10-03 snapshot.

What POOL-1 *does* establish: the strongest catalogue-recovery mechanism in this
programme, by a confirmed +0.013…+0.017 HOLDOUT-DTI over the previous best, with the
largest gains in the Walker Lane transtensional fold — i.e. genuinely better recovery
of concealed, non-range-front fault segments, the population the Final Round's
expanded labels will reward. Converting that into a submittable file is an emission
problem, not a modelling problem (§7).

## 6. The nine sites in one table (full detail: `nine-site-executive-summary.md`)

| Site | Historical leader (owner-reported) | Unique? (measured) | Latest lane status (2026-10-27 HEAD) | File to download | OK to submit? |
|---|---|---|---|---|---|
| GEMSDOE24 | D1.5 0.2477 | No — h19-5 family; ⊂ GEMSDOE27 | No new submission authorized; lattice-feasibility stop | — | **NO** |
| GEMSDOE25 | D2.8 0.2600 | No — **identical to GEMSDOE30 d28** | H73-BW blocked pre-fit; H73-PM negative | — | **NO** |
| GEMSDOE27 | gap-closure 0.2449 | No — = D1.5 + 1,259 dots | H31-1 evidence-qualified, selector decision pending; H31-3/H32 negative | H31-1 (research) | **NO** (site's own selector step) |
| GEMSDOE28 | r1 0.2708 | No — = GEMSDOE31, ⊂ D2.8 | S22C ctxHGB passes site gates (own frame HOLDOUT 0.12018); selector checklist required | S22C (research) | **NO** (checklist pending) |
| GEMSDOE30 | d28 0.2600 (MSDB1-edge 0.1462) | Family file; CSR-1 unique (67.70% max today) | **POOL-1: confirmed mechanism, duplicate-stopped** | CSR-1 (research) | **NO** |
| GEMSDOE31 | solo-d28 0.2708 | No — identical to GEMSDOE28 r1 | No file approved; projections audited unreliable | — | **NO** |
| GEMSDOE32 | **H33-B2 0.2778** | No — exact pruned subset of r1 | H47-1 LDGI repo-high holdout 0.12196 (own frame), verdict negative | — | **NO** |
| GEMSDOE33 | H33D 0.2632 | Overlaps family, not a subset | FSML2-CC unique but negative | — | **NO** |
| GEMSDOE36 | PINN 0.2750 | No — = H33-B2 + 1,200 dots | KPL-36 verdict promote on its site (own frame 0.1701) — **already submitted: 0.1647 owner-reported** | — (already spent) | **NO** (duplicate of a spent slot) |

Cross-site HOLDOUT numbers are **not comparable** (different evaluators/withheld sets:
e.g. GEMSDOE28's frame scores dotted-b2 at 0.10519; GEMSDOE36 uses `gems-segment-pooled-v1`;
ours is `component-holdout-v3-blockstats-20261025`). Only same-protocol paired deltas rank methods.

**Estimated leaderboard scores:** none are defensible as point estimates. The two
observed same-family anchors are MSDB1-edge (our HOLDOUT 0.1705 → 0.1462 owner-reported)
and KPL-36 (its HOLDOUT 0.1701 → 0.1647 owner-reported, different evaluator). A POOL-2
successor at HOLDOUT ≈ 0.187 would, under those two anchors alone, scenario-project to
roughly **0.16–0.19** — a projection with ≥ ±0.09 cross-family error, **not** a score,
and still below the h19-5 family's habitat-driven 0.2778 (owner-reported) on the
*public* split. Its value proposition is the Final Round's expanded-label rescoring,
where verified newly-discovered concealed faults count.

## 7. Next lane (POOL-2) — to be preregistered fresh next session (not executed here; budget 3/3 spent)

Frozen design sketch for the next session's preregistration (must be re-frozen before
any fit): same 75-feature pooled model; emission = dispersed EDGE with two
*pre-declared* novelty constraints — (a) spacing `dr²+dc²>12` (≥3.46 px) and
(b) exclusion of pixels within 3 px of the three breaching GEMSDOE30 dot sets —
with the holdout cost of (a)+(b) measured against `msdb_edge` *and* against an
unconstrained pooled arm in the same folds. If the constrained emitter still beats
`msdb_edge` with paired CI > 0 on two seeds and passes both novelty stages vs a
refreshed registry, it becomes the first file in this repo that is simultaneously
best-on-holdout and unique. If it fails, that negative is the deliverable. Alternative
genuinely-distinct lanes if POOL-2 fails: KRA-1 Riedel alignment, MCD-1 clay-cap
saddle (both frozen in the POOL-1 preregistration ranking).

## 8. Irregularities flagged

- IR-POOL-01: no externally assigned single-method lane paragraph in the prompt; lane self-assigned and frozen here (same standing gap as all prior lanes).
- IR-POOL-02: prompt leaderboard figures stale (0.3195 = Oct 3; 0.4413 = Oct 25; live Oct 27 #1 = 0.4544).
- IR-POOL-03: all nine historical "site bests" are one emission family; three pairs are byte/value-identical across sites (25=30, 28=31; 24⊂27).
- IR-POOL-04: GEMSDOE31 clone contains an aligned raster with 2,610,312 in-footprint NaNs (`gemsdoe31-csdu-stepover-8cf9dc27-nan.tif`) — would fail portal range checks; finite-subset audited.
- IR-POOL-05: GEMSDOE36's site banner says "OK TO SUBMIT / verdict: promote" for KPL-36 while the owner's ledger already records a 0.1647 score for that file — treat as already submitted; do not respend.
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
