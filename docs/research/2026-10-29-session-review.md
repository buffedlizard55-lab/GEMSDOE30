# 2026-10-29 session review — executive decision, verified leaderboard, and blockers

**Verdict: NO FILE IS APPROVED FOR DOWNLOAD OR SUBMISSION. No new TIFF was generated. No experiment was run (0 of 3). No weekly slot was selected.**

Scope: review of the repository, the official competition pages, the official rules PDF, the DrivenData forum staff answers, and the USGS/IHFC catalogue pages, with every claim labelled by evidence level. The repository's gates were executed rather than trusted: 438 tests pass with the pinned inputs restored, and every CI verifier exits 0 (details in §7).

---

## 1. Executive summary — what to download, what it scores, and whether it is unique

**Download? No file.** Every historical TIFF in the nine requested sites is unapproved. None is unique, and none has a validated score estimate. The table below is generated from the byte audit (`docs/research/2026-10-28-priority-audit.json`); the owner-reported scores are **unverified owner claims, not organizer receipts or HOLDOUT-DTI values**.

| Site | Best owner-reported file (**do not download**) | Owner-reported score (UNVERIFIED) | Dots within 3 px of the pinned 13GEMSDOE lattice | Unique vs registry? | Published format check | Estimated score for a new file | OK to download and submit? |
|---|---|---|---:|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | 60,022 / 60,069 = 99.92% | **NO** | pass | none (no holdout run) | **NO** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | 44,053 / 44,090 = 99.92% | **NO** | pass | none (no holdout run) | **NO** |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | 61,281 / 61,328 = 99.92% | **NO** | pass | none (no holdout run) | **NO** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | 37,626 / 37,660 = 99.91% | **NO** | pass | none (no holdout run) | **NO** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` (zero outside) | 0.2600 | 44,053 / 44,090 = 99.92% | **NO** | **FAIL** (outside not NaN) | none (no holdout run) | **NO** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | 40,166 / 40,199 = 99.92% | **NO** | pass | none (no holdout run) | **NO** |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (zero outside) | 0.2778 | 37,622 / 37,654 = 99.92% | **NO** | **FAIL** (outside not NaN) | none (no holdout run) | **NO** |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | 41,829 / 41,865 = 99.91% | **NO** | **FAIL** | none (no holdout run) | **NO** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (zero outside) | 0.2750 | 38,822 / 38,854 = 99.92% | **NO** | **FAIL** | none (no holdout run) | **NO** |

Reading the table:
- "Unique" means the literal rule in the owner brief: no more than 70% of dots within 3 px of any one registry raster. All nine files are at 99.9%. The duplicate rule uses the pinned 13GEMSDOE lattice witness; its restore and hash are checked by CI.
- A format-only change (for example, switching zero-outside to NaN-outside) keeps the same dots and therefore the same overlap. The repo's AGENTS.md forbids renaming or re-encoding a stopped raster to claim uniqueness, and this review does not do it.
- "Estimated score" is deliberately empty. A projection is not a score (owner brief, rule 3). No holdout was run this session.
- Even if the owner-reported values are accurate, none of them reaches the visible public top 50 (cutoff 0.3167, §2).

### The three answers you asked for

| Question | Answer | Evidence level |
|---|---|---|
| Is there a unique, approved TIFF to download and submit? | **No.** | Verified (CI verifiers, byte audit) |
| What score should we expect from a new file? | **Unknown.** The repo cannot produce a holdout score here because the organizer-authenticated feature stack is not present (§6). | Verified limitation |
| What is the current leaderboard high? | **0.4544** on the official public board fetched 2026-10-29. Neither 0.4413 nor 0.3195 is the high. | Official snapshot (§2) |

---

## 2. Verified leaderboard and owner claims

Source: [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), read 2026-10-29. Receipt: `docs/research/2026-10-29-leaderboard-snapshot.json`, guarded by `tests/test_leaderboard_snapshot.py`.

| Owner claim | Official snapshot | Result |
|---|---|---|
| "0.4413 is the current GEMSDOE high" | #1 is **0.4544**. 0.4413 does not appear in ranks 1–50. The repo's IR-30-082 recorded 0.4413 for #1 on 2026-10-25; that is a repo claim I did not re-verify, and the board has since moved. | **Not supported** |
| "0.3195 is the highest score right now" | 0.3195 is **rank #47**. | **Not supported** |
| "0.2778 (GEMSDOE32 H33-B2) is the highest GEMSDOE score" | 0.2778 lies **below the rank-50 cutoff of 0.3167**, so it is not in the visible top 50. No receipt links any repo file to a team row. | **Cannot be placed; unverified** |

Limits: public-test scores only. The rules (PDF §3.6.1–3.6.2, [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) say the private set and the final-round re-scoring decide the prize. The page text ends at rank 50, so lower ranks were not observed.

---

## 3. Why did H33-B2 score 0.2778, and can a new file beat it? (PhD-level answer, labelled)

### 3a. The metric, verified line by line

Official definition ([problem page, "Performance metric"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)):
- kernel k(d) = max(1 − d/300 m, 0);
- TP_w = Σ_g max_{x: d≤R} p(x)·k(d(x,g)): **credit per hidden fault pixel is the maximum, not a sum**;
- FP_w = Σ_{x: p(x)>0} p(x)·[1 − max_g k(d(x,g))]: **every predicted cell with p>0 is charged**, weighted by distance to the nearest truth;
- FN_w = Σ_g [1 − max_{x: d≤R} p(x)·k(d(x,g))];
- DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε).

Checked against `src/gemsdoe30/metric.py`: TP, FP and FN follow the same definitions, with the valid-footprint mask applied. The official worked example (TP 3.00, FP 1.89, FN 2.00) gives 3.00/(3.00+0.378+1.60) = **0.6027**, which the code reproduces and which `tests/test_metric.py::test_official_worked_example_arithmetic` asserts. **Verified.**

Consequences, derived from the verified formula (analysis, not a score):
1. A binary dot adds at most one hit's credit per hidden fault, so dense redundant dots add penalty without adding credit.
2. A dot costs 0.2·(1 − k(d)) for its distance d to the nearest hidden fault. A dot exactly on a hidden fault costs nothing; a dot ≥300 m away costs 0.2 in full.
3. Because FN is weighted 0.8 and FP 0.2, dots are worth adding when their expected kernel-weighted hit rate is high enough; the break-even is set by the repo's calibration (why-doc §2).

### 3b. The mask, verified against the official forum

- The public board is pooled over all public-test pixels (staff answer, [forum t/11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)). **Verified.**
- Known USGS/INGENIOUS fault pixels are masked from evaluation (staff answer, [forum t/11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)). The staff wording is "pixels corresponding to known faults"; it does **not** say that predictions near known faults are fully penalised. The repo's sentence "staff confirmed near-known predictions are fully penalised" is therefore an inference from pixel-exact masking; it is flagged as IR-30-088 below.

### 3c. Lineage of the H33-B2 file (repo analysis, owner-reported inputs)

The repository's byte-level lineage (`docs/research/2026-10-25-lsm/why-h33-scored-0.2778.md`, §1) is consistent with the audit: D2.8 (44,090 dots) → r1 (40,199; removes dots at distance 1 px) → H33-B2 (37,654; removes dots at distance ≤2 px from the catalogue). The three steps only delete dots; none adds evidence. The score differences between steps (+0.0108, +0.0070) are owner-reported.

### 3d. Answer

- **How it likely got the highest GEMSDOE score:** it keeps the same hidden-fault signal as its parents (the h19-5 lineament support) and deletes dots that earned little credit and carried FP penalty, so the score rises with fewer wasted dots. This is a *mechanism*, not an identification: the hidden truth and the organizer receipt are unavailable, so the 0.2778 value is not confirmed.
- **Can we beat 0.2778?** **Not demonstrated.** The repo's projection says a 0.30 score needs about 0.145 hits per dot (versus 0.134 for H33-B2). That is a projection, not a score. Beating it needs either a validated hit-rate gain on a leakage-safe holdout or a new information source. Neither exists in this session.

---

## 4. Ranked hypotheses (3–5), checked against the repository

Each row was checked by keyword search across `src/`, `scripts/`, `docs/` and `tests/`, plus the register in `docs/hypotheses.md`. "Already registered" means it is named in the register but never executed.

| Rank | Hypothesis | Layers and source | Physical signature | Why it could catch a missing fault | Status in repo | Obtainable? | Cost | Expected DTI gain |
|---|---|---|---|---|---|---|---|---|
| **1** | **S29-A — Scale-selective band-pass (difference-of-Gaussians, ~0.5–2 km) of detrended elevation and TMI** | `det_elev`, `tmi` (training_features bands, owner mirror) | Energy at fault-scale wavelengths after removing the regional trend and 100 m noise | Subdued, short, low-relief segments sit at a different scale from the high-relief scarps already encoded by the existing curvature and edge families | **NOT in repo** (0 hits for wavelet/spectral/fractal; curvature/Hessian families exist in 24 files, so it must beat them in an ablation) | Yes, once the pinned owner mirror is restored (not organizer-authenticated) | Low | Unknown; expected small |
| 2 | **S29-B — Heat-flow / temperature-gradient discontinuities** (= register hypothesis #4 and H-34-04) | USGS 3-D temperature model v1.1 ([ScienceBase item](https://www.sciencebase.gov/catalog/item/671f9d3ed34ed0f827eaa16d), DOI [10.5066/P149FR54](https://doi.org/10.5066/P149FR54), zip 200.02 MB); IHFC Global Heat Flow Database ([landing page](https://ihfc-iugg.org/products/global-heat-flow-database)) | Isotherm bending or gradient breaks that a conductive model does not explain | Fluid circulation along permeable faults can perturb conductive profiles even without a surface trace | **Already registered, never executed** (docs/hypotheses.md lines 187 and 356) | Listing verified; download not possible from this sandbox (outbound is GitHub/npm/PyPI only). Needs a GitHub Actions fetch, as the earlier external-layers workflow does | High | Unknown |
| 3 | **S29-C — Qfaults trace completion** (= H-32-04, conditional) | Qfaults attribute CSV `gdr_qfaults_traces.csv` (pinned in `docs/research/mirror-pins-extra.json`, 126,177 bytes; not restored locally). A derived raster `derived_gdr_qfaults_v2_100m_u8.tif` is in `data/external/` | Kinematically consistent gap-extension between Qfaults traces | Traces may carry geometry the catalogue lacks | **Already registered, conditional, blocked** by the open circularity in IR-30-021 | Yes (pinned; restore needed for the CSV) | Medium | Unknown; cannot be tested without a circularity-safe holdout |
| 4 | **S29-D — Strain-tensor principal-axis orientation vs. lineament strike** | Strain-rate components | Faults align with principal strain axes | Faults nucleate along the active extension direction | **Not in repo**, but **blocked**: only the invariants `geod_2ndinv`, `geod_dilaterate`, `geod_shearrate` are in the feature list (`src/gemsdoe30/experiments.py`); no source for the tensor components was verified | No (source not identified) | Medium | Unknown |

Ranking logic (prior plausibility × cost, not a DTI estimate): S29-A is first because its data are already present and its cost is lowest, though its gain is probably modest. S29-B has the largest physical headroom but the highest cost and a leakage risk: the USGS model is compared against measured temperatures (ScienceBase summary), so any well data used as features would overlap its calibration. S29-C is blocked by IR-30-021. S29-D is blocked by data.

**None of these is validated.** Per the owner brief, none may consume a weekly slot before a same-protocol, spatially blocked holdout beats the current holdout best.

---

## 5. Irregularities flagged for review

Recorded in `docs/irregularities.md` as IR-30-088 to IR-30-094 (IR-30-094: `OWNER_BRIEF.md` names other session branches; this session is `arena/8357086d-gemsdoe30`).

- **IR-30-088 (Medium):** "near-known predictions are fully penalised" overstates the forum wording (see §3b).
- **IR-30-089 (High):** the owner's "0.4413 current high" and "0.3195 highest right now" are contradicted by the 2026-10-29 official snapshot (§2).
- **IR-30-090 (Medium):** the reference solution writes sigmoid outputs over the **whole** label grid with no footprint mask ([notebook cell 16/19](https://github.com/drivendataorg/gems-prize-reference-solution), commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`). The rules say data outside the bounds must be null or NaN. The two conventions conflict, and the portal's behaviour is unknown.
- **IR-30-091 (High):** the historical "Predicted values must be in range [0, 1]" error is still undiagnosed. One hypothesis, unverified: a whole-array min/max check fails whenever NaN is present (NumPy propagates NaN, so `min >= 0` is False). Testing it requires a controlled probe, which spends a weekly slot, so it is the user's decision.
- **IR-30-092 (Low):** the GEMSDOE25 and GEMSDOE30 owner files share the owner score 0.2600 and the token `91eae1ca` (the GEMSDOE30 file name carries it; the GEMSDOE25 raster's SHA-256 begins with it), but their SHA-256 values differ (`91eae1ca…` vs `8cf893ea…`). Attribution stays unresolved, as the 2026-10-03 format review already recorded.
- **Deadline discrepancy (existing IR-TAD-02, re-checked):** the competition homepage says **Dec. 3, 2026, 11:59 p.m. UTC**; the rules PDF Appendix A.1 says **5:00 p.m. ET** on the deadline date. Both are sourced; the discrepancy persists.
- **Branch names (IR-30-094):** `OWNER_BRIEF.md` names two other session branches. The session assignment is `arena/8357086d-gemsdoe30`, and all work is on it.
- **Test robustness (IR-30-093, fixed):** `tests/test_current_registry_site.py` failed in a checkout without the restored template. It now skips with a clear message, matching the neighbouring tests.

---

## 6. Decision and blockers

**Why no TIFF was generated.** The owner brief requires three things before a file is offered: a holdout that beats the current best with a paired 95% CI lower bound above zero; a novelty check that passes; and a separate slot selection. This session has none of the three:

1. **No assigned lane.** The parallel-run protocol refers to "the single method paragraph below", and no such paragraph exists (repeated as IR-30-078). Without a lane, a new experiment would be self-assigned.
2. **No organizer-authenticated feature stack.** The `training_features` raster is pinned only as an owner mirror (`docs/research/mirror-pins.json`, 5 multipart parts, 418,912,844 bytes, not organizer-authenticated). It could be restored through the GitHub API, but a holdout built on it still carries that caveat, and no lane was assigned to justify the run.
3. **No holdout means no estimate.** Without a holdout, any "estimated score" would be a guess dressed as a number, which the owner brief forbids.

**What is needed from you (each one is a decision, not a credential):**
- Name one lane or hypothesis (S29-A is the cheapest), so a 3-experiment, 2-hour holdout can run under the protocol.
- Authorise restoring the owner-mirror feature stack for that lane, labelled as not organizer-authenticated.
- Check your DrivenData submission history and weekly cap yourself. The public board does not show which team is yours, and I could not log in (no credentials are used or stored).
- Decide whether to spend a probe slot on the NaN-outside versus reference-style convention question (IR-30-090/091).
- Resolve the deadline discrepancy from the official rules page's key-dates section.

**Limitations.** Outbound access here is restricted to GitHub, npm and PyPI, so DrivenData data, Dropbox, the USGS and IHFC downloads, and the GDR archive cannot be fetched from the sandbox. I read the official pages through the page fetcher, which is not the same as a logged-in session.

---

## 7. Verification ledger

| Check | Result | How |
|---|---|---|
| Restored pinned inputs match their pins | `labels.tif` `7ba308cc…`, `sample_submission.tif` `2176d08e…`, lattice `b4570b40…` | `scripts/restore_public_mirrors.py`, `sha256sum` |
| Priority audit (nine sites) offline re-measurement | exit 0 | `scripts/audit_priority_readiness.py --check` |
| Current-run, stopped-attempt, GDX, QPC, CSR, registry preflight, LSM, TAD verifiers | all exit 0 | the CI sequence in `.github/workflows/review-tests.yml` |
| Research site determinism | exit 0 | `scripts/build_research_site.py --check` |
| Full test suite (with restored inputs) | 438 passed, 5 skipped (optional torch) | `pytest -q` |
| Official format text | "float32", "values between 0 and 1", "data outside the bounds is null or nan" | [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Official metric and worked example | formula and 0.60 example match | problem page; `tests/test_metric.py` |
| Official rules | single GeoTIFF, 100 m, three submissions per week, one final submission, AI-use narrative required | [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §§3.2, 3.4, 3.5 |
| Leaderboard | top 0.4544; 0.3195 at #47; 0.3167 at #50; 0.4413 absent | §2 and the snapshot test |
| USGS 3-D temperature model | ScienceBase record and file size verified | [ScienceBase](https://www.sciencebase.gov/catalog/item/671f9d3ed34ed0f827eaa16d) |
| IHFC | landing page verified; Great Basin subset **not** verified | [IHFC](https://ihfc-iugg.org/products/global-heat-flow-database) |
| Reference solution | notebook read; no footprint mask on output | [GitHub](https://github.com/drivendataorg/gems-prize-reference-solution) |

## 8. Process

- **Pass 1 — implement and verify:** restored inputs, ran every CI verifier and the full suite, read the official pages, wrote the leaderboard receipt and its test, fixed the environment-dependent test.
- **Pass 2 — adversarial review:** the H33 "fully penalised" wording, the 0.4413 claim and the reference-solution mask were each re-checked against their sources; the register was grepped to avoid re-proposing registered ideas as new.
- **Pass 3 — full brief re-check:** every number in §1 is generated from `docs/research/2026-10-28-priority-audit.json`; every official quote was checked against the fetched text; no score was written as a result.

The AI disclosure required by rules §3.2 should be updated to describe this session's use before any entry is made: see `docs/ai-disclosure-draft.md`.
