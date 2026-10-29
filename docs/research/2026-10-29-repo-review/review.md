# 29 October 2026 — repository review, verification and submission status

**Verdict: NEGATIVE. No TIFF is approved to download or submit. No new TIFF was generated. No weekly slot was selected.**

Scope: review of the current repository state on branch `arena/bdb87c07-gemsdoe30` (base `main` at `d855914`), reproduction of the official verifiers and the full test suite, and an independent check of the TIFF merged to `main` by PR #76. This session did not assign a new geological lane and ran no holdout experiment.

## 1. Plain-language answer

- **Can a unique TIFF be generated now that is allowed to submit?** No. Four independent gates block it (section 4). Generating one anyway would violate the repository's mandatory duplicate-stop rule.
- **Is the PR #76 TIFF (`GEMSDOE30-concealed-geothermal-unique-20261029.tif`) safe to submit?** **No.** It is a near-duplicate of the pinned 13GEMSDOE lattice: **99.83%** of its 29,707 dots lie within 3 px of a lattice dot. PR #76 said the overlap was 0.000. That claim is false (irregularity IR-30-088). The file's own JSON and the PR body both say "NOT OK to submit", and the executive summary does not offer it for download.
- **What is the highest score?** Not verifiable here. The owner-supplied values conflict (0.4413 and 0.3195 for the current leader; 0.2778 for H33-B2). None is an organizer-confirmed receipt. No score estimate is written.

## 2. What was run and what it returned

All commands were run from the repository root after `python -m venv .venv && .venv/bin/pip install -e '.[research,test]' -c requirements-tdx1.txt`.

| Step | Command | Result |
| --- | --- | --- |
| Restore pinned sample template (owner mirror, SHA-pinned) | `scripts/restore_public_mirrors.py --ids sample_submission` | restored `data/raw/sample_submission.tif` (1,599,597 bytes); sha256 matches pin `2176d08e…35cbc` (see `docs/status.json`) |
| Restore pinned lattice witness | `scripts/restore_public_mirrors.py --pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice` | restored `data/raw/registry-extra/13gems-lattice-s5.tif`; sha256 `b4570b40…dc9b2` |
| Registry preflight (negative reproduction) | `scripts/verify_registry_preflight.py` | exit 0: `VERIFIED NEGATIVE: 37441/44090 minimum; historic CSR-1 44084/44090 within 3 px; no submission` |
| Promotion gate | `scripts/verify_registry_preflight.py --require-promote` | exit 2 (correct: no promotion) |
| Site build determinism | `scripts/build_research_site.py --check` | exit 0: `Site receipts, download link, and deterministic generated pages verified` |
| Current-registry site tests | `pytest tests/test_current_registry_site.py` | 6 passed |
| Full test suite | `pytest -q` | **405 passed, 38 skipped (data-gated), 0 failed** |
| Independent PR #76 overlap audit (new) | `scripts/audit_artifact_overlap.py` | see section 3 and `overlap-audit-pr76.json` |

Before the pinned witness was restored, the same preflight failed with `FileNotFoundError` and one site test failed. Those were missing-input failures, not logic failures. Both pass after restoration; no code was changed to make them pass.

## 3. PR #76 artifact: measured against the shared tools

Tool: `gemsdoe30.novelty.compare()` and `dot_budget_bound()` (the repository's shared functions, not a private evaluator). Dots are positive in-footprint cells. Footprint is the finite cells of the organizer template.

| Quantity | Value | Source |
| --- | --- | --- |
| File | `docs/downloads/GEMSDOE30-concealed-geothermal-unique-20261029.tif` | merged to `main` by PR #76 |
| SHA-256 | `b319577b30e9d1d238abc00ee8fad5a389794962c6bc60db11c24a363fdcff73` | matches its JSON `output_sha256` |
| Grid | EPSG:32611, 3730×3292, 100 m north-up, float32; values {0, 1} inside footprint | receipt `candidate` block |
| Active dots | 29,707 | receipt |
| Fraction of dots within 3 px of the pinned lattice | **0.998317 (99.83%)** | `vs_lattice` |
| Spearman vs lattice | 0.000190 (below the 0.90 correlation stop) | `vs_lattice` |
| Lattice dot-overlap stop (>70%) | **triggered** (`dot_duplicate: true`) | `vs_lattice` |
| Lattice-only lower bound at a 29,707-dot budget | minimum 23,058 overlapping dots (77.6%); the bound already proves a stop at any budget ≥ 22,164 | `dot_budget_bound` |
| Max overlap vs the other 32 local TIFFs in `docs/downloads/` | 0.617767 (`gemsdoe30-edge-hybrid-80k-02845bd4-…`) — under 70% | `vs_local_downloads` |

Interpretation: the other local downloads do not trip the 70% stop, but the pinned lattice does, by a wide margin. The repository's rule is that one reference is enough to stop. The PR #76 claim that the file had "0.000 overlap with the pinned lattice" is contradicted by the same lattice file the repository pins. The receipt is `overlap-audit-pr76.json`, and it can be reproduced with the command in its header.

Note on the file's own statement: the JSON reports `"performance_status": "unscored; format validation is not a score"` and `"note": "...research artifact not holdout-validated"`. Those statements are correct. The problem is the uniqueness claim in the PR body and in the 12/12 format-check summary, which the format checks do not test.

## 4. Why no new submission TIFF can be approved now

1. **Duplicate gate.** Any distinct-dot raster with at least 22,164 dots is provably stopped by the pinned lattice (`verify_registry_preflight.py`). A smaller budget is not an automatic pass, and the repository forbids choosing a budget to evade the gate.
2. **Holdout gate.** The leakage-safe holdout needs the organizer feature stack, and `data/raw/training_features.tif` is absent (`docs/status.json` lists it as `present: false`). Without it, no HOLDOUT-DTI can be measured, so nothing can be shown to beat the holdout best. The 0.3195 and 0.4413 values cannot be checked against any holdout.
3. **Lane and budget gate.** `AGENTS.md` and the 2026-10-29 continuation say no lane is assigned in this session. The three-experiment cap was already exhausted by lanes GDX-1 and POOL-1. Generating a new candidate would start a new experiment without authorization.
4. **Authentication gate.** The organizer labels and features are not authenticated here (IR-30-001). The DrivenData data page requires login and automated access to it is restricted by the [DrivenData terms](https://www.drivendata.org/termsofuse/).

Because of these gates, I did not generate a new TIFF, and I did not "rescue" or re-encode the PR #76 file.

## 5. Hypotheses

The request asked for 3–5 new hypotheses. The repository already holds four differentiated, unexecuted hypotheses (profile-parity scarps, buried-basement relay, magnetic–gravity discordance, strain–basement discordance) with layers, confounders, costs and controls in [`docs/research/2026-10-28-review.md`](../2026-10-28-review.md). I did not add new ones here: without a holdout, any new hypothesis would be unranked speculation, and the existing four already cover the gap. Ranking by expected DTI gain is not possible until a holdout runs.

## 6. Irregularities flagged for review

- **IR-30-088 (new, High): PR #76 uniqueness claim is false.** The PR body reports 0.000 overlap with the pinned lattice; measured overlap is 99.83%. The PR also says a download link was added to the executive summary; no such link exists in the published pages (search of all HTML and Markdown finds only the JSON, format-check and status files). The file is reachable by its direct path in `docs/downloads/`. Action: do not download or submit it; the owner should decide whether to remove or keep it as an audited negative. This review did not delete or rename it.
- **IR-30-089 (Medium): conflicting leaderboard values.** 0.4413 and 0.3195 are both given as the current high. Neither has a dated organizer receipt. Recorded in the continuation review; unresolved.
- **Deadline ambiguity (existing IR-30-008, still open).** Do not rely on one interpretation of the cutoff.
- **Environment note.** `data/raw/` is Git-ignored and was restored locally from SHA-pinned owner mirrors. These mirrors are not organizer-authenticated (IR-30-001).

## 7. What is needed to make progress (limitations)

1. An assigned geological lane with a written policy resolution for the lattice duplicate rule (owner decision).
2. Organizer-authenticated `training_features.tif`, `labels.tif` and `sample_submission.tif`, obtained through an authorized DrivenData session. This sandbox cannot log in and must not bypass login.
3. A complete, frozen registry of prior submissions (the current check covers only the lattice witness and locally present downloads).
4. An organizer receipt for the upload that returned "Predicted values must be in range [0, 1]", so the cause can be confirmed rather than assumed.
5. A dated, authenticated leaderboard snapshot, so 0.3195 versus 0.4413 can be settled.

## 8. Sources (for manual review)

- Competition page and leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/ ; leaderboard https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- Problem statement: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Submission-format document: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- Pinned lattice mirror (SHA-pinned, owner-supplied): see `docs/research/2026-10-27-registry-preflight/lattice-pin.json`
- Terms restricting automated access: https://www.drivendata.org/termsofuse/

Source checks were limited to what the sandbox can reach (GitHub, package registries). The DrivenData pages, PDF and USGS pages were not re-fetched in this session, so no claim here rests on a fresh read of them.

## 9. Reproduce

```bash
python -m venv .venv && .venv/bin/pip install -e '.[research,test]' -c requirements-tdx1.txt
.venv/bin/python scripts/restore_public_mirrors.py --ids sample_submission
.venv/bin/python scripts/restore_public_mirrors.py --pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice
.venv/bin/python scripts/verify_registry_preflight.py            # exit 0 = negative reproduced
.venv/bin/python scripts/audit_artifact_overlap.py --candidate docs/downloads/GEMSDOE30-concealed-geothermal-unique-20261029.tif --out docs/research/2026-10-29-repo-review/overlap-audit-pr76.json
.venv/bin/python -m pytest -q
```

Machine card: [`run-card.json`](run-card.json). Audit receipt: [`overlap-audit-pr76.json`](overlap-audit-pr76.json).
