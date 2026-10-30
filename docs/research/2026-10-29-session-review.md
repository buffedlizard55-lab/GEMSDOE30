# 2026-10-29 session review — executive decision, verified leaderboard, and blockers

**Verdict: NO FILE IS APPROVED FOR DOWNLOAD OR SUBMISSION. No new TIFF was generated in this session. No experiment was run (0 of 3). No weekly slot was selected.**

Scope: review of the repository (including the other 2026-10-29 sessions now merged on `main`), the official competition pages, the official rules PDF, the DrivenData forum staff answers, and the USGS and IHFC catalogue pages. Every claim is labelled by evidence level.

> **Dated addendum — 2026-10-30:** the newer public-board snapshot now places 0.3195 at rank 50 (rather than rank 47 in this 2026-10-29 snapshot); the historical snapshot below is retained unchanged. A fresh read of staff reply [11516/4](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) also confirms the pixel-exact mask and says new truth may fall within 300 m of known traces and may include corrections. The general penalty statement is staff-confirmed for an unmasked prediction far from new truth, but the claimed H33-B2 causal contribution remains unknown. See the [2026-10-30 session review](2026-10-30-session-review.md).

**Three findings change the picture and need your decision first:**

1. **The uniqueness witness cannot discriminate (IR-30-097).** The pinned 13GEMSDOE lattice covers 99.87% of the footprint within 3 px, so random dots average about 99.86% against it. The literal 70%/3 px rule therefore stops every candidate above 22,164 dots, whatever its content. The "99.9%" figures in the nine-site table measure coverage, not duplication, and the table's "unique? NO" column rests on that test alone.
2. **A TIFF on `main` from PR #78 is not cleared, and the guide that offered it has been regenerated (IR-30-098).** Its own novelty receipt sets `duplicate_stop: true` against two geothermal-corridor rasters.
3. **The official leaderboard contradicts the owner's two "leader" values (IR-30-091).** The top is 0.4544, not 0.4413, and 0.3195 is rank #47.

---

## 1. Executive summary — what to download, what it scores, and whether it is unique

**Download? No file.** None of the nine historical TIFFs is approved. The table below is generated from the byte audit (`docs/research/2026-10-28-priority-audit.json`). The owner-reported scores are **unverified owner claims, not organizer receipts or HOLDOUT-DTI values**.

| Site | Best owner-reported file (**do not download**) | Owner-reported score (UNVERIFIED) | Dots within 3 px of the pinned lattice (non-discriminating, IR-30-097) | Uniqueness | Published format check | Estimated score for a new file | OK to download and submit? |
|---|---|---|---:|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | 60,022 / 60,069 = 99.92% | **Not established** | pass | none (no holdout run) | **NO** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | 44,053 / 44,090 = 99.92% | **Not established** | pass | none (no holdout run) | **NO** |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | 61,281 / 61,328 = 99.92% | **Not established** | pass | none (no holdout run) | **NO** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | 37,626 / 37,660 = 99.91% | **Not established** | pass | none (no holdout run) | **NO** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` (zero outside) | 0.2600 | 44,053 / 44,090 = 99.92% | **Not established** | **FAIL** (outside not NaN) | none (no holdout run) | **NO** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | 40,166 / 40,199 = 99.92% | **Not established** | pass | none (no holdout run) | **NO** |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (zero outside) | 0.2778 | 37,622 / 37,654 = 99.92% | **Not established** | **FAIL** (outside not NaN) | none (no holdout run) | **NO** |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | 41,829 / 41,865 = 99.91% | **Not established** | **FAIL** | none (no holdout run) | **NO** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` (zero outside) | 0.2750 | 38,822 / 38,854 = 99.92% | **Not established** | **FAIL** | none (no holdout run) | **NO** |

Reading the table:
- **"Uniqueness: not established"** means no discriminating test has cleared these files. The lattice test is saturated (§6, IR-30-097). Sparse per-raster checks, where they exist, are the informative ones.
- A format-only change (for example zero-outside to NaN-outside) keeps the same dots, so it cannot create uniqueness. AGENTS.md also forbids renaming or re-encoding a stopped raster to change its status.
- **"Estimated score" is deliberately empty.** A projection is not a score (owner brief, requirement 3). No holdout was run.
- Even if the owner-reported values are accurate, none reaches the visible public top 50 (cutoff 0.3167, §2).

### The three answers

| Question | Answer | Evidence level |
|---|---|---|
| Is there a unique, approved TIFF to download and submit? | **No.** | Verified (CI verifiers, byte audit, §6) |
| What score should we expect from a new file? | **Unknown.** No holdout can run in this session (§6). | Verified limitation |
| What is the current leaderboard high? | **0.4544** on the official public board fetched 2026-10-29. Neither 0.4413 nor 0.3195 is the high. | Official snapshot (§2) |

## 1b. The PR #78 TIFF on `main` (not cleared)

File: [`docs/downloads/GEMSDOE30-geothermal-unique-20261029T165045Z-3995629e.tif`](../downloads/GEMSDOE30-geothermal-unique-20261029T165045Z-3995629e.tif), SHA-256 `ac941748f450b94f2783cc612c5e26046104d22e07fb72049967c94bfb166a84`, 9,652 dots, EPSG:32611, 3730×3292, NaN outside, values 0 and 1. It was generated by another session (PR #78). I did not create it and did not change it.

| Check | Result | Source |
|---|---|---|
| Format | PASS | its `validation.json` (and my reading of the raster) |
| Holdout | **not measured**: "NOT holdout-promoted; labels.tif unavailable in sandbox; HOLDOUT-DTI uncomputable" | its `meta.json` |
| Uniqueness vs organizer registry | "UNCHECKED" | its `meta.json` |
| Own novelty receipt | `duplicate_stop: true` vs `GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif` (9,652 of 9,652 dots within 3 px of its 40,000 dots) and vs `…-20261027T233111Z.tif` (same numbers) | its `novelty.json` |
| Pinned lattice (re-measured here) | 9,643 / 9,652 = 99.91% within 3 px. Not discriminating (random dots score 99.86%, IR-30-097). The receipt does not include the lattice at all. | this review |
| Name | "unique" in the file name | — |

**Verdict: not cleared; do not download or submit.** Its own receipt contradicts its name. The geothermal-corridor family it resembles was already stopped (README: "Geothermal-corridor TIFF … stopped"). The guide on `main` offered this file for download and said "Uniqueness: PARTIAL". The guide was regenerated from the receipt-driven generator in this PR (§5, IR-30-098).

---

## 2. Verified leaderboard and owner claims

Source: [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), read 2026-10-29. Receipt: `docs/research/2026-10-29-leaderboard-snapshot.json`, guarded by `tests/test_leaderboard_snapshot.py`.

| Owner claim | Official snapshot | Result |
|---|---|---|
| "0.4413 is the current GEMSDOE high" | #1 is **0.4544**. 0.4413 does not appear in ranks 1–50. The repo's IR-30-082 recorded 0.4413 for #1 on 2026-10-25; I did not re-verify that, and the board has since moved. | **Not supported** |
| "0.3195 is the highest score right now" | 0.3195 is **rank #47**. | **Not supported** |
| "0.2778 (GEMSDOE32 H33-B2) is the highest GEMSDOE score" | 0.2778 lies **below the rank-50 cutoff of 0.3167**, so it is not in the visible top 50. No receipt links any repo file to a team row. | **Cannot be placed; unverified** |

Limits: public-test scores only. The rules (PDF §3.6.1–3.6.2, [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)) say the private set and the final-round re-scoring decide the prize. The page text ends at rank 50, so lower ranks were not observed.

---

## 3. Why did H33-B2 score 0.2778, and can a new file beat it? (labelled)

### 3a. The metric, verified line by line

Official definition ([problem page, "Performance metric"](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)):
- kernel k(d) = max(1 − d/300 m, 0);
- TP_w = Σ_g max_{x: d≤R} p(x)·k(d(x,g)): **credit per hidden fault pixel is the maximum, not a sum**;
- FP_w = Σ_{x: p(x)>0} p(x)·[1 − max_g k(d(x,g))]: **every predicted cell with p>0 is charged**, weighted by distance to the nearest truth;
- FN_w = Σ_g [1 − max_{x: d≤R} p(x)·k(d(x,g))];
- DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε).

Checked against `src/gemsdoe30/metric.py`: TP, FP and FN follow the same definitions, with the valid-footprint mask applied. The official worked example (TP 3.00, FP 1.89, FN 2.00) gives 3.00/(3.00+0.378+1.60) = **0.6027**, which the code reproduces. **Verified** (`tests/test_metric.py::test_official_worked_example_arithmetic`).

Consequences, derived from the verified formula (analysis, not a score):
1. A binary dot earns at most one hit's credit per hidden fault, so redundant dots add penalty without adding credit.
2. A dot costs 0.2·(1 − k(d)) for its distance d to the nearest hidden fault. A dot exactly on a hidden fault costs nothing; a dot 300 m or more away costs 0.2 in full.
3. Because FN is weighted 0.8 and FP 0.2, a dot is worth adding when its expected kernel-weighted hit rate is high enough; the break-even is set by the repo's calibration (why-doc §2).

### 3b. The mask, verified against the official forum

- The public board is pooled over all public-test pixels (staff answer, [forum t/11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2)). **Verified.**
- Known USGS/INGENIOUS fault pixels are masked from evaluation (staff answer, [forum t/11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2)). The staff wording is "pixels corresponding to known faults"; it does **not** say that predictions near known faults are fully penalised. The repo's sentence "staff confirmed near-known predictions are fully penalised" is an inference from pixel-exact masking (IR-30-090).

### 3c. Lineage of the H33-B2 file (repo analysis, owner-reported inputs)

The repository's byte-level lineage (`docs/research/2026-10-25-lsm/why-h33-scored-0.2778.md`, §1) is consistent with the audit: D2.8 (44,090 dots) → r1 (40,199; removes dots at distance 1 px) → H33-B2 (37,654; removes dots at distance ≤2 px from the catalogue). The three steps only delete dots; none adds evidence. The score differences between steps are owner-reported.

### 3d. Answer

- **Likely reason it scored highest among the nine:** it keeps the same hidden-fault signal as its parents (the h19-5 lineament support) and deletes dots that earned little credit and carried FP penalty, so the score rises with fewer wasted dots. This is a *mechanism*, not an identification: the hidden truth and the organizer receipt are unavailable, so 0.2778 is not confirmed.
- **Can we beat 0.2778?** **Not demonstrated.** The repo's projection says a 0.30 score needs about 0.145 hits per dot (versus 0.134 for H33-B2). That is a projection, not a score. Beating it needs either a validated hit-rate gain on a leakage-safe holdout or a new information source. Neither exists in this session.

---

## 4. Ranked hypotheses (3–5), checked against the repository

Each row was checked by keyword search across `src/`, `scripts/`, `docs/` and `tests/`, plus the register in `docs/hypotheses.md`. "Already registered" means it is named in the register but never executed.

| Rank | Hypothesis | Layers and source | Physical signature | Why it could catch a missing fault | Status in repo | Obtainable? | Cost | Expected DTI gain |
|---|---|---|---|---|---|---|---|---|
| **1** | **S29-A — Scale-selective band-pass (difference-of-Gaussians, ~0.5–2 km) of detrended elevation and TMI** | `det_elev`, `tmi` (training_features bands, owner mirror) | Energy at fault-scale wavelengths after removing the regional trend and 100 m noise | Subdued, short, low-relief segments sit at a different scale from the high-relief scarps already encoded by the existing curvature and edge families | **NOT in repo** (0 hits for wavelet/spectral/fractal; curvature/Hessian families exist in 24 files, so it must beat them in an ablation) | Yes, once the pinned owner mirror is restored (not organizer-authenticated) | Low | Unknown; expected small |
| 2 | **S29-B — Heat-flow / temperature-gradient discontinuities** (= register hypothesis #4 and H-34-04) | USGS 3-D temperature model v1.1 ([ScienceBase item](https://www.sciencebase.gov/catalog/item/671f9d3ed34ed0f827eaa16d), DOI [10.5066/P149FR54](https://doi.org/10.5066/P149FR54), zip 200.02 MB); IHFC Global Heat Flow Database ([landing page](https://ihfc-iugg.org/products/global-heat-flow-database)) | Isotherm bending or gradient breaks that a conductive model does not explain | Fluid circulation along permeable faults can perturb conductive profiles even without a surface trace | **Already registered, never executed** (`docs/hypotheses.md` lines 187 and 356) | Listing verified; download not possible from this sandbox (outbound is GitHub/npm/PyPI only). A GitHub Actions fetch would be needed, as the repo's external-layers workflow does | High | Unknown |
| 3 | **S29-C — Qfaults trace completion** (= H-32-04, conditional) | Qfaults attribute CSV `gdr_qfaults_traces.csv` (pinned in `docs/research/mirror-pins-extra.json`, 126,177 bytes; not restored locally). A derived raster `derived_gdr_qfaults_v2_100m_u8.tif` is in `data/external/` | Kinematically consistent gap-extension between Qfaults traces | Traces may carry geometry the catalogue lacks | **Already registered, conditional, blocked** by the open circularity in IR-30-021 | Yes (pinned; the CSV needs a restore) | Medium | Unknown; cannot be tested without a circularity-safe holdout |
| 4 | **S29-D — Strain-tensor principal-axis orientation vs. lineament strike** | Strain-rate components | Faults align with principal strain axes | Faults nucleate along the active extension direction | **Not in repo**, but **blocked**: only the invariants `geod_2ndinv`, `geod_dilaterate`, `geod_shearrate` are in the feature list (`src/gemsdoe30/experiments.py`); no source for the tensor components was verified | No (source not identified) | Medium | Unknown |

Ranking logic (prior plausibility × cost, not a DTI estimate): S29-A is first because its data are already present and its cost is lowest, though its gain is probably modest. S29-B has the largest physical headroom but the highest cost and a leakage risk: the USGS model is compared against measured temperatures (ScienceBase summary), so any well data used as features would overlap its calibration. S29-C is blocked by IR-30-021. S29-D is blocked by data.

**None of these is validated.** Per the owner brief, none may consume a weekly slot before a same-protocol, spatially blocked holdout beats the current holdout best.

---

## 5. Irregularities flagged and corrections made

Recorded in `docs/irregularities.md` as **IR-30-090 to IR-30-098**. (IR-30-088 and IR-30-089 belong to other sessions on `main`; my earlier numbering collided with them and was renumbered.)

- **IR-30-090 (Medium):** "near-known predictions are fully penalised" overstates the forum wording (§3b).
- **IR-30-091 (High):** the owner's "0.4413 current high" and "0.3195 highest right now" are contradicted by the 2026-10-29 official snapshot (§2).
- **IR-30-092 (Medium):** the reference solution writes sigmoid outputs over the **whole** label grid with no footprint mask (cells 16 and 19 of the [reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution), commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`). The rules say data outside the bounds must be null or NaN. The conventions conflict; the portal's behaviour is unknown.
- **IR-30-093 (High):** the historical "Predicted values must be in range [0, 1]" error is still undiagnosed. One hypothesis, unverified: a whole-array min/max check fails whenever NaN is present (NumPy propagates NaN, so `min >= 0` is False). Testing it requires a controlled probe, which spends a weekly slot: a user decision.
- **IR-30-094 (Low):** the GEMSDOE25 and GEMSDOE30 owner files share the owner score 0.2600 and the token `91eae1ca`, but their SHA-256 values differ (`91eae1ca…` vs `8cf893ea…`). Attribution stays unresolved.
- **IR-30-095 (Low):** a test failed in a checkout without the restored template. It now skips with a restore instruction.
- **IR-30-096 (Low):** `OWNER_BRIEF.md` names two other session branches. This session is `arena/8357086d-gemsdoe30`.
- **IR-30-097 (High): the uniqueness witness cannot discriminate.** See the top of this review and §6.
- **IR-30-098 (High): the guide on `main` offered a download for the PR #78 file.** It said "Download submission TIF" and "Uniqueness: PARTIAL", against the file's own duplicate-stop receipt. The hand-edited guide also failed `build_research_site.py --check`. **Correction made:** the guide was regenerated from the receipt-driven generator. Only `executive-summary.html` changed, and the check now passes. The generator's guide says "NOT APPROVED FOR SUBMISSION" and has no download link for that file. The file itself was not changed.
- **Deadline discrepancy (existing IR-TAD-02, re-checked):** the competition homepage says **Dec. 3, 2026, 11:59 p.m. UTC**; the rules PDF Appendix A.1 says **5:00 p.m. ET** on the deadline date. Both are sourced; the discrepancy persists.

---

## 6. Decision and blockers

**Why no TIFF was generated in this session.** The owner brief requires three things before a file is offered: a holdout that beats the current best with a paired 95% CI lower bound above zero; a novelty check that passes; and a separate slot selection. This session has none of the three:

1. **No assigned lane.** The parallel-run protocol refers to "the single method paragraph below", and no such paragraph exists (IR-30-078). Without a lane, a new experiment would be self-assigned.
2. **No organizer-authenticated feature stack.** The `training_features` raster is pinned only as an owner mirror (`docs/research/mirror-pins.json`, 5 multipart parts, 418,912,844 bytes). It could be restored through the GitHub API, but a holdout built on it still carries that caveat, and no lane was assigned to justify the run.
3. **No holdout means no estimate.** Without a holdout, any "estimated score" would be a guess dressed as a number, which the owner brief forbids.
4. **The uniqueness witness is saturated (IR-30-097).** Measured here: the pinned lattice covers 5,160,724 of 5,167,373 footprint cells (99.87%) within 3 px. Random footprint dot sets average 99.86–99.87% over five trials each (9,652, 22,164 and 44,090 dots; seed 7; per-trial minimum 99.82%). The literal rule therefore stops any candidate above 22,164 dots. The nine-site "unique? NO" column and the PR #76 and PR #78 "duplicate" labels rest on this test alone. The generator-rendered guide shows the same stops.

**Decision needed from you (the rule is yours to change, not mine):** IR-30-086 recommended skipping the lattice overlap test where the reference's 3 px dilation covers at least 70% of the eligible domain, and it was not applied so that no gate would change after a failure. I agree with that recommendation in principle, but I did not change the gate: changing a stop rule is an owner decision. Until you decide, dense candidates cannot be cleared under the literal rule, whatever their content.

**What is needed from you (each one is a decision, not a credential):**
- Decide the uniqueness witness rule (item 4 above).
- Name one lane or hypothesis (S29-A is the cheapest), so a 3-experiment, 2-hour holdout can run under the protocol.
- Authorise restoring the owner-mirror feature stack for that lane, labelled as not organizer-authenticated.
- Check your DrivenData submission history and weekly cap yourself. The public board does not show which team is yours, and no DrivenData login was used or stored.
- Decide whether a probe slot may test the NaN-outside versus reference-convention question (IR-30-092, IR-30-093).
- Decide whether PR #78's file should move to a stopped-artifacts folder. I did not move it: AGENTS.md forbids altering stopped rasters.
- Resolve the deadline discrepancy from the official rules page's key-dates section.

**Limitations.** Outbound access here is restricted to GitHub, npm and PyPI, so DrivenData data, the USGS and IHFC downloads, and the GDR archive cannot be fetched from the sandbox. I read the official pages through the page fetcher, which is not a logged-in session.

---

## 7. Verification ledger

| Check | Result | How |
|---|---|---|
| Restored pinned inputs match their pins | `labels.tif` `7ba308cc…`, `sample_submission.tif` `2176d08e…`, lattice `b4570b40…` (matches `lattice-pin.json`) | `sha256sum` against the pins |
| Priority audit (nine sites) offline re-measurement | exit 0 | `scripts/audit_priority_readiness.py --check` |
| Current-run, stopped-attempt, geothermal, quadrature, CSR, registry-preflight, LSM and TAD verifiers | all exit 0 | the review-tests sequence in `.github/workflows/review-tests.yml` |
| `--restore-only` | exit 0 | `scripts/audit_priority_readiness.py --restore-only` |
| Research site determinism | exit 0 after the one-page regeneration | `scripts/build_research_site.py --check` |
| Full test suite (merged tree) | 444 passed, 5 skipped (optional torch/scipy) | `pytest -q` |
| Official format text | "float32", "values between 0 and 1", "data outside the bounds is null or nan" | [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Official metric and worked example | formula and 0.60 example match | problem page; `tests/test_metric.py` |
| Official rules | single GeoTIFF, 100 m, three submissions per week, one final submission, AI-use narrative | [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §§3.2, 3.4, 3.5 |
| Leaderboard | top 0.4544; 0.3195 at #47; 0.3167 at #50; 0.4413 absent | §2 and the snapshot test |
| Lattice witness | 5,160,724 / 5,167,373 cells (99.87%) within 3 px; random dots average 99.86–99.87% | `numpy`/`scipy` measurement in this session |
| Overlap calibration | the 3 px definition reproduces the audit: GEMSDOE30 d28 = 44,053 / 44,090 | same measurement, against the audit JSON |
| PR #78 TIFF | format PASS; 9,643 / 9,652 within 3 px of the lattice; own receipt `duplicate_stop: true` vs two geothermal-corridor rasters | §1b |
| USGS 3-D temperature model | ScienceBase record, file size and DOI verified | [ScienceBase](https://www.sciencebase.gov/catalog/item/671f9d3ed34ed0f827eaa16d) |
| IHFC | landing page verified; Great Basin subset **not** verified | [IHFC](https://ihfc-iugg.org/products/global-heat-flow-database) |
| Reference solution | notebook read; no footprint mask on output | [GitHub](https://github.com/drivendataorg/gems-prize-reference-solution) |

## 8. Process

- **Pass 1 — implement and verify:** restored inputs, ran every CI verifier and the full suite, read the official pages, wrote the leaderboard receipt and its test, fixed the environment-dependent test.
- **Pass 2 — adversarial review:** the H33 "fully penalised" wording, the 0.4413 claim, the reference-solution mask, and the lattice witness were each re-checked against sources or measurements. The lattice finding overturned my first draft, which had treated 99.9% as evidence of duplication. The PR #78 file was found on `main` after my first push and checked against its own receipt.
- **Pass 3 — full brief re-check:** every number in §1 is generated from the audit JSON; every official quote was checked against fetched text; no score was written as a result; the stale guide was regenerated rather than hand-edited.

Before any entry, the AI disclosure required by rules §3.2 must be updated to describe this session's use: see `docs/ai-disclosure-draft.md`.
