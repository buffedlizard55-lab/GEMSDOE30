# Repository review — 2026-10-28

Scope: a read-only review of the `arena/9d8019dc-gemsdoe30` checkout (base `b76762e`, `main`). No new model, raster, submission name, note, score estimate, or weekly-slot selection was made in this review.

## Executive decision

**DO NOT SUBMIT. No new GeoTIFF is approved.** Every archived candidate in this checkout is either a duplicate-stop, a format-only pass, or a zero-experiment preflight, and no candidate has an organizer-confirmed score. The repository's gates are behaving as designed: the registry preflight still reproduces the duplicate stop, and the historical evidence has not changed.

Quick answer to "is there a file I can download and submit?": **no.** The only downloadable TIFFs are historical research artifacts with recorded stop decisions. The [current submission guide](../executive-summary.html) and [overview](../index.html) say the same thing.

## What was verified in this review (reproduced, not assumed)

| Check | Command | Result |
|---|---|---|
| Restore owner mirrors (SHA-256 pinned, not organizer-authenticated) | `scripts/restore_public_mirrors.py --ids sample_submission labels` and `--pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice` | Restored; `labels.tif` and `sample_submission.tif` match pins |
| Registry preflight (duplicate stop) | `scripts/verify_registry_preflight.py` | Exit 0: **VERIFIED NEGATIVE**. 37,441/44,090 minimum overlap; historic CSR-1 44,084/44,090 within 3 px |
| Stopped-attempt verifier | `scripts/verify_stopped_attempt.py` | Exit 0, `archived_research_verdict: negative` |
| Current-run verifier | `scripts/verify_current_run.py` | Exit 0, `archived_research_verdict: negative` |
| CSR-1 verifier | `scripts/verify_csr_run.py` | Exit 0: research verdict negative, download flag True (12 gates) |
| GDX-1 verifier | `scripts/verify_geothermal_chemistry_run.py` | Exit 0; current TIFF reopened, CIs recomputed |
| QPC-1 verifier | `scripts/verify_quadrature_phase_run.py` | Exit 0; duplicate-stop at dots, no publication |
| LSM verifier | `scripts/verify_lsm_run.py` | Exit 0; its own `file_contract` check reports "No TIFF published" (protocol stop at dot stage) |
| TAD verifier | `scripts/verify_tad_run.py` | Exit 0, archived negative |
| POOL-1 verifier | `scripts/verify_pool_run.py` | Exit 0; receipt-only (raster absent by design) |
| Site generator check | `scripts/build_research_site.py --check` | Exit 0: receipts, download link and generated pages are deterministic |
| Test suite | `python -m pytest -q` | **424 passed, 5 skipped** (optional torch/scipy), 7 subtests passed |
| Local link check | Relative `href`/markdown links in `README.md`, `index.html`, `executive-summary.html`, `docs/*.md` | No broken local targets |
| Git state | `git status` | Clean; generated data stays in Git-ignored `data/raw/` |

Note: the first run of several verifiers failed with `FileNotFoundError` on `data/raw/sample_submission.tif`. That was an environment precondition (the file is restored by the README's own command), not a repository defect. After the restore step, every verifier passed.

## Score evidence status (what each number is)

| Number | Source in repo | Status |
|---|---|---|
| 0.4413 | Ledger row for DrivenData leaderboard rank 1 (`xiaofanhu`), read 2026-10-25 | Public-leaderboard snapshot; not a private-test score; not attributable to a file |
| 0.3195 | Ledger rows read 2026-10-03 (DARD, rank 1) | **Stale snapshot.** Not on the 2026-10-25 page; the owner's "highest" claim conflicts with the 0.4413 current leader (see IR-30-057, IR-30-072) |
| 0.2778 (H33-B2, GEMSDOE32) | Owner-reported | Unverified; no submission receipt |
| 0.2600 (GEMSDOE25 / GEMSDOE30 D2.8) | Owner-reported | Unverified; IR-30-002 says the file-to-score link is not established |
| Holdout DTI values in archived receipts | Evaluator `component-holdout-v3-blockstats-20261025` | HOLDOUT-DTI only; not comparable to leaderboard scores |

Authoritative sources for manual review: [DrivenData competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391).

## Irregularities flagged for review

1. **Leader value conflict (High).** The owner brief states 0.3195 is the highest score; the ledger's 2026-10-25 read shows 0.4413 at rank 1 and no 0.3195 entry on pages 1–2 (IR-30-057, IR-30-072). The official page is the reference. Re-read the leaderboard manually before treating either number as current.
2. **Score-to-file attribution unproven (Critical).** The 0.2600 and 0.2778 values are not tied to a submission receipt (IR-30-002, IR-30-080). Do not state that any named TIFF earned a score.
3. **Portal rejection cause undiagnosed (High).** The "Predicted values must be in range [0, 1]" error is consistent with NaN/zero handling outside or inside the footprint, but the validator is not public (IR-30-012). The writer and validator in this repo check the local contract; they are not organizer acceptance.
4. **Competition data not organizer-authenticated (Critical).** `training_features.tif` is absent from `data/raw/` (status.json: `required_files_present: false`). Only `labels.tif` and `sample_submission.tif` were restored from owner mirrors. The DrivenData data page requires login; no bypass was attempted (IR-30-001).
5. **Deadline discrepancy (Medium).** Competition page: 3 Dec 2026, 23:59 UTC. Rules PDF Appendix A.1: 5:00 p.m. ET. Confirm with the organizer; plan for the earlier time (IR-30-008).
6. **Pointer/README drift (Low).** `docs/current-run.json` still names the archived PTA-1 run card as `run_card`, while its `latest_attempt` points at `docs/research/texture-controls/run-card.json`. Both paths resolve, but a reader could take the wrong one. Keep the pointer as-is for verifier compatibility and rely on the README's current decision.
7. **Ignored `.venv`/`data/raw`.** Environment artifacts created here are Git-ignored (`.venv/`, `data/raw/`) and are not part of the deliverable.

## Gaps in the project (blocking a competitive submission)

- No verified organizer-authenticated training features; a full model cannot be trained or cross-validated against the official data (IR-30-001, status.json).
- No candidate has passed the promotion gate: no paired holdout improvement with a 95% CI lower bound above zero, and no non-duplicate registry result at the 44,090-dot scale. The current governing rule (>70% of dots within 3 px) makes many otherwise-valid ideas stop.
- The complete live registry of public submissions is not known; archived comparisons do not cover every new raster (IR-30-009). The 21 named external repositories in the prompt returned HTTP 404 in the 2026-10-27 review (see ledger).
- DrivenData's terms restrict automated monitoring; the leaderboard feed must stay a manually refreshed, time-stamped snapshot (IR-30-007).

## Recommended next steps (for the next session)

1. Obtain organizer-authenticated copies of the four competition files through a permitted, logged-in session, then re-run `scripts/verify_current_run.py` against them.
2. Ask the organizer (or read the submission-page receipt) to confirm the submission validator's exact rule for NaN/zero outside the footprint; resolve the 0–1 range error before any further upload attempt.
3. Re-read the public leaderboard manually and update the ledger with the read date; reconcile the 0.3195 vs 0.4413 conflict.
4. Only after a preregistered, leakage-safe holdout beats the same-protocol best with a paired CI lower bound above zero, and the duplicate policy is resolved, run the selector step for a weekly slot.
5. Confirm the controlling deadline with the organizer.

## Three-pass record

- **Pass 1 — implement and verify.** Restored the owner mirrors, ran all nine verifiers, the site check and the test suite. All passed (negative verdicts reproduced).
- **Pass 2 — bugs and assumptions.** Found the environment-only missing-template failure (resolved by the README restore), confirmed the score attribution gaps, the 0.3195/0.4413 conflict and the pointer drift. No code change was needed.
- **Pass 3 — cross-check.** Re-read the claims above against the verifier output and the ledger; this report makes no score claim beyond the labelled sources. No new raster or submission was created.
