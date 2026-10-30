# Repository review · 2026-10-30 · executive summary

**Verdict: no file is approved for download or submission. No new TIFF was generated.**

This is a negative result, and it is a deliverable. The reasons are measured and reproducible below, and the owner decisions that would unblock a submission are listed in §6.

Branch: `arena/2a368cf4-gemsdoe30` · base `main` @ `eaff218` · run card: [`run-card.json`](run-card.json)

---

## 1. Summary for the owner (read this first)

| Question | Answer | Basis |
|---|---|---|
| Which file should I download and submit? | **None.** Do not download any of the nine historical files for submission. | Every file fails the uniqueness test or has no receipt. See §2. |
| What is the estimated score for a new submission? | **No estimate can be written.** The only numbers are owner-reported values with no receipt. | Rule 3 of the owner protocol: a projection is never written as a score. No HOLDOUT-DTI was produced this session. |
| Is any submission unique? | **No.** Among the nine requested sites, the files form one family. Two are identical inside the footprint, and several are exact subsets of others. | Measured: [`nine-site-family.json`](nine-site-family.json). |
| Can a unique TIFF be generated now? | **Not validly.** The repo's only uniqueness gate flags random dots as duplicates, so no file can be shown unique under it. | Measured: [`lattice-random-control.json`](lattice-random-control.json). |
| What is the highest official score? | **#1 is 0.4544** (official board, 2026-10-30). The owner's 0.4413 does not appear on the board. 0.3195 is rank #50, the cutoff. | Official leaderboard, dated receipt [`leaderboard-snapshot.json`](leaderboard-snapshot.json). |
| Does anything beat 0.2778 (H33-B2)? | **Not demonstrated.** H33-B2 is itself below the rank-50 cutoff (0.3195), so it is not visible on the board. | As above. |

---

## 2. The nine requested sites: file, estimate, uniqueness

All nine files are the historical rasters from the owner-supplied, SHA-pinned mirrors (restored into `data/raw/priority-readiness/`, not in the repository and not organizer-authenticated). Owner-reported scores are labelled **UNVERIFIED OWNER CLAIM** and are not HOLDOUT-DTI or ORGANIZER-CONFIRMED.

| Site | Historical file (SHA-256 prefix) | Owner-reported score | Estimate for a new download | Unique vs the other 8 sites? (measured) | Outside-footprint encoding (published check) | Download? |
|---|---|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-…-nan.tif` (`68d0e2e4`) | 0.2477 | None | **No.** All 60,069 of its dots are also dots of GEMSDOE27 | NaN · passes | **No** |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-…-nan.tif` (`91eae1ca`) | 0.2600 | None | **No.** Identical inside the footprint to GEMSDOE30; all dots of 31 and 32 are contained in it | NaN · passes | **No** |
| GEMSDOE27 | `gems27-topo-gap-closure-…-nan.tif` (`33003374`) | 0.2449 | None | **No.** Contains all 60,069 GEMSDOE24 dots | NaN · passes | **No** |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-…-nan.tif` (`5556aa14`) | 0.2710 | None | **No.** Shares 67.5–74.0% of its dots with each other site | NaN · passes | **No** |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-…-91eae1ca.tif` (`8cf893ea`) | 0.2600 | None | **No.** Same in-footprint values as GEMSDOE25; zeros outside instead of NaN | **zeros · FAILS** | **No** |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-…-nan.tif` (`07b6db44`) | 0.2708 | None | **No.** All 40,199 of its dots are also dots of GEMSDOE25 and GEMSDOE30 | NaN · passes | **No** |
| GEMSDOE32 (H33-B2) | `gemsdoe32-h33-h33-2-b2-…-zeros.tif` (`c55bafc4`) | **0.2778** | None | **No.** All 37,654 of its dots are also dots of GEMSDOE25, 30, 31 and 36 | **zeros · FAILS** | **No** |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-…tif` (`87f857d5`) | 0.2632 | None | **No.** Shares 66–83% of its dots with each other site | **zeros · FAILS** | **No** |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-…-zeros.tif` (`e1589102`) | 0.2750 | None | **No.** Contains all 37,654 GEMSDOE32 dots; shares 96.9% with GEMSDOE25 | **zeros · FAILS** | **No** |

Notes on the table:
- "Dots" means positive cells inside the 5,167,373-cell template footprint. Values inside the footprint are binary (0 or 1) for all nine files.
- The published-format check is the repo's validator (`scripts/audit_priority_readiness.py --check`, exit 0 this session). "Passes" refers only to the null/NaN-outside clause. It is not a statement about portal acceptance.
- Every file lies at 99.9% overlap with the pinned lattice witness, but that is an artefact (§4), so it is not used as a uniqueness result here.

---

## 3. Why did H33-B2 (0.2778) score highest? (what is verified, and what is not)

**Verified in this session** ([`nine-site-family.json`](nine-site-family.json), `h33b2_vs_d28`):
1. H33-B2 (GEMSDOE32) is exactly the GEMSDOE25 D2.8 raster minus **6,436 dots**. No dot is added (`dots_in_32_not_in_25 = 0`).
2. Every removed dot lies **within 2 px (Euclidean) of a labelled fault cell** (`removed_dots_max_distance_to_labelled_fault_px = 2.0`; share within 2 px = 1.0).
3. H33-B2 stores zeros outside the footprint, not NaN (§2, the zeros-outside column).

**Not verified (owner-reported only):**
- The 0.2778 value itself. It is below the rank-50 cutoff (0.3195), so it cannot be found on the public board, and no organizer receipt is linked to this file.
- Whether removing those 6,436 dots causes the reported gain.

**Hypothesis (H-HALO, unmeasured).** The metric scores each predicted dot by its distance to the nearest *new* fault. It masks known faults pixel-exactly. A dot 1–2 px beside a catalogued trace is therefore not masked and not near a new fault, so it is scored as a false positive. Removing such dots can raise the score even though no fault is found. A catalogue digitisation offset would produce the same effect. This is a testable hypothesis on a spatially blocked holdout. It has not been tested.

**Answer to "can we beat 0.2778?":** not demonstrated, and not measurable in this session. A candidate would need (a) a working uniqueness gate, (b) a same-protocol holdout gain with a 95% CI lower bound above zero, and (c) a slot. None of these is in place (§6).

---

## 4. The uniqueness gate is broken (verified)

The owner protocol stops a candidate if more than 70% of its dots fall within 3 px of one registry raster's dots. The pinned witness is the 13GEMSDOE lattice (206,895 positive cells).

Measured with the shared `gemsdoe30.novelty.compare` ([`lattice-random-control.json`](lattice-random-control.json)):

| Random dots in footprint | Trials | Fraction within 3 px of lattice (min – max) | Flagged "duplicate" |
|---|---|---|---|
| 9,652 | 5 | 99.80% – 99.91% | 5 / 5 |
| 22,164 | 5 | 99.82% – 99.92% | 5 / 5 |
| 44,090 | 5 | 99.84% – 99.90% | 5 / 5 |

So random noise passes as a duplicate. The gate cannot separate a candidate from chance, whatever the candidate contains. This confirms IR-30-097 with an independent measurement. Its consequence is that no dense candidate can be cleared under the literal rule, and the repo must not change the rule silently to get a file through.

---

## 5. Official-source checks (links for manual review)

| Claim checked | Source | Result |
|---|---|---|
| Leaderboard top and ranks | [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) (fetched 2026-10-30) | #1 0.4544; 0.3195 is #50; 0.4413 absent. Receipt: [`leaderboard-snapshot.json`](leaderboard-snapshot.json). |
| Submission format | [Problem description, Submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) (fetched 2026-10-30) | Single-band GeoTIFF; EPSG 32611; 100 m; same bounds as training data; "data outside the bounds is null or nan"; `float32` with values between 0 and 1. |
| Rules: submissions per week; GenAI disclosure; deadline | [Official Rules PDF, Sept 2026](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2 (fetched 2026-10-30) | "three submissions per week"; a generative-AI use statement is required in the narrative; public-board scores "may not be the same as the final scores". §1.2 defers key dates to the competition website, so the deadline conflict (IR-TAD-02) is **not resolved** here. |
| Organizer's own output convention | [gems-prize-reference-solution @ aebe92f](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) (archive fetched 2026-10-30; notebook sha256 `1a762273…`) | Static reading only: no nodata set; predictions written to random test patches (other cells 0.0); `float64` on this reading, which conflicts with the rules' `float32`. Receipt: [`reference-writer-check.json`](reference-writer-check.json). |
| Metric definition | [Problem description, Performance metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Distance-weighted Tversky with α = 0.2, β = 0.8, triangular kernel, R = 3 px. Matches `src/gemsdoe30/metric.py` per the repo's 2026-10-29 check (not re-run here). |

**Portal error "Predicted values must be in range [0, 1]".** Still undiagnosed. The organizer's text permits NaN outside; the organizer's reference writes zeros-plus-predictions with no NaN. Both conventions are in the organizer's own materials. Only an authorised portal probe can settle which one the portal accepts (§6, decision 3). Nothing in this session establishes portal acceptance.

---

## 6. Decisions needed from the owner (none is a credential)

1. **Uniqueness rule (IR-30-111).** Replace the literal 70%/3 px test against dense witnesses with a chance-corrected statistic (for example, flag only if overlap exceeds a random-dot baseline at the same budget by a pre-registered margin), or drop the dense lattice from the registry. Until this is decided, no file can be shown unique.
2. **Lane.** Assign one method paragraph for a 3-experiment, 2-hour holdout. None was supplied in this session's message. S29-A in [`docs/research/2026-10-29-session-review.md`](../2026-10-29-session-review.md) is the cheapest, as recorded there.
3. **Portal probe (IR-30-115, IR-30-092/093).** Decide whether one weekly slot may test a float32 raster with NaN outside versus one with zeros outside. Consider the owner-reported scores of the four zero-outside files (0.2600, 0.2778, 0.2632, 0.2750). If those were portal uploads of these exact bytes, the portal accepted zeros. That is unverified and must be confirmed from your DrivenData submission history.
4. **Deadline (IR-TAD-02).** Confirm the controlling cutoff on the competition website or with the organizer. The overview page and the rules PDF Appendix A.1 give different times (carried forward; not re-verified this session).
5. **Your submission history and weekly cap.** The rules allow three submissions per week (§3.2). I cannot see your DrivenData account, so the remaining slots for this week are unknown.
6. **Generative-AI narrative.** The rules require a statement of GenAI use in the submission narrative (§3.2). A draft exists at `docs/ai-disclosure-draft.md`. It needs your review.

---

## 7. Irregularities for review

New entries IR-30-110 to IR-30-118 are in [`docs/irregularities.md`](../../../docs/irregularities.md). The most important:
- **IR-30-110** The board moved in one day. 0.3195 is now rank #50, not #47.
- **IR-30-111** The lattice gate is non-discriminating (measured, 15/15 random trials).
- **IR-30-114** The restored "sample_submission" mirror has exactly the labelled-fault cells (`sample==1` is identical to `labels==1`), although the organizer says the sample "predicts total fault absence". It is used only for its finite grid and footprint, never as a prediction.
- **IR-30-115** The four highest-scoring owner-reported files all use zeros outside the footprint.

---

## 8. What was verified, how, and what was not

Verified this session (exit codes observed):
- `git`: branch equals `main` at `eaff218` before this review (0 commits ahead, 0 behind).
- `scripts/restore_public_mirrors.py --ids sample_submission labels` and `--pins … --ids registry_lattice`: exit 0; SHA-256 pins matched.
- `scripts/audit_priority_readiness.py --restore-only` then `--check`: exit 0.
- `scripts/verify_current_run.py`, `verify_stopped_attempt.py`, `verify_geothermal_chemistry_run.py`, `verify_quadrature_phase_run.py`, `verify_csr_run.py`, `verify_registry_preflight.py`, `verify_lsm_run.py`, `verify_tad_run.py`: all exit 0.
- `scripts/verify_registry_preflight.py --require-promote`: exit 2 (expected; the stop stands).
- `scripts/build_research_site.py --check`: exit 0.
- `python -m pytest -q` with pinned inputs restored: **457 passed, 5 skipped** (the skips are optional Torch tests).
- New: `scripts/lattice_random_control.py`, `scripts/verify_nine_site_family.py`, and the test file `tests/test_repo_review_2026_10_30.py`.

Not verified (limits):
- No portal, organizer, or DrivenData account data was accessed. Leaderboard values are a public, JavaScript-rendered read with relative timestamps only.
- The reference notebook was read statically, not executed (it needs GPU and the competition data).
- Historical scores are owner-reported. No HOLDOUT-DTI was measured this session.
- Mirrors are integrity-pinned, not organizer-authenticated.

---

## 9. Next steps (ordered by value; none spends a slot)

1. Owner decides decision 1 (uniqueness rule). This unblocks everything else.
2. Owner assigns a lane (decision 2). Then pre-register a holdout for H-HALO against the S29-A plan, with buffers and frozen folds, before any experiment.
3. Owner decides on one portal probe (decision 3). A probe is the only way to resolve the range error.
4. Confirm the deadline and the weekly cap on the competition website (decisions 4 and 5).
5. Keep leaderboard references dated. Any future rank must cite its receipt date (IR-30-110).

---

## 10. Links

- Run card: [`run-card.json`](run-card.json)
- Leaderboard receipt: [`leaderboard-snapshot.json`](leaderboard-snapshot.json) (2026-10-29 receipt kept unchanged: [`../2026-10-29-leaderboard-snapshot.json`](../2026-10-29-leaderboard-snapshot.json))
- Lattice control: [`lattice-random-control.json`](lattice-random-control.json)
- Nine-site family audit: [`nine-site-family.json`](nine-site-family.json)
- Reference-writer check: [`reference-writer-check.json`](reference-writer-check.json)
- Earlier nine-site audit: [`../../2026-10-28-priority-audit.json`](../2026-10-28-priority-audit.json) · [`../../../priority-readiness-audit.html`](../../../priority-readiness-audit.html)
- Hypotheses register: [`../../hypotheses-2026-10-29.md`](../hypotheses-2026-10-29.md)
- Owner protocol: [`README.md`](../../../README.md#current-owner-prompt) · [`AGENTS.md`](../../../AGENTS.md)
