# Cumulative repository review — 2026-10-03

**Branch:** `arena/01a1035b-gemsdoe30`. This is the three-pass review against the canonical owner brief preserved in `README.md`. It records repository evidence only: no competition upload, score claim, or merge is implied unless separately recorded below.

## Pass 1 — implement and verify

- Re-read the complete owner brief and current-state section. The 300 m metric-geometry term remains paired with regional soft-Tversky; spatial holdout changed near-miss allocation, but the seed-31 DTI gain did not replicate (Δ +0.000115, 2/4 folds). No improvement or promotion claim.
- Rechecked H-31-02b's recorded spatial, strike-permutation, and SGMC results. The candidate is not promoted, the global budget is not an active-count match, and the inspected SGMC labels were not rerun or retuned.
- Inspected the exact H-33-01 B40 JSON per-arm `mean_dots`: 40,000 for `f_nat`, `f_nat_legacy`, `P0/P25/P50/P75/P100`, `P_rank`, `blind_random_B`, and `rand_P0/P25/P50/P75/P100`; 35,824 for `historical_d28`. The report now records that scope. Code review confirms the 40k model/random selections are inside the scoring domain; the 80k gate remains void at 68,573 vs 80,000 active dots.
- Corrected the landing and submission pages to separate the archived +25.1% `cand_t04s4` comparison from the 85,526-dot SGMC-hedge TIFF and to state unequal active counts for both archived comparisons and the GBM/random diagnostic.
- Corrected the range-error explanation and all user-facing zero-outside language: local checks pass, NaN as the cause is plausible rather than confirmed, and organizer acceptance of zero outside is unverified. No upload was made.
- Marked the frozen pre-experiment shortlist as historical/superseded; linked it to the current five-item untried shortlist. Reviewed and corrected source/access statements for the locally inspected D2.8 TIFF and the GDR 1391 runner-bridge archives.
- Updated download sidecar notes and outside-convention labels, corrected the D2.8 browser download filename to match its manifest, and regenerated `docs/status.json` using `scripts/build_status.py`.
- Revalidated each of the three published `-zeros.tif` research copies against the exact local template: **12/12 local checks each**. This does not establish portal acceptance.

## Pass 2 — defect review and fixes

- Searched site HTML, research notes, source register, IR register, download manifests, and README for stale `+25.1%`, matched-count, H-31-02b, D2.8 attribution, NaN-cause, and zero-outside claims. Corrected the active copy and sidecars; older session logs remain only where explicitly historical and now qualified.
- Reclassified IR-30-019 as **open** for portal-validator cause/outside-convention uncertainty; IR-30-012 now describes only the repository's local in-footprint validator. No text claims that local `--portal-safe` validation proves organizer acceptance.
- Checked that H-31-02b and H-33-01 result/preregistration artifacts were not rerun or rewritten. The H-33 B40 count explanation cites the result JSON and audited selector/scorer code; the B80 void is preserved.
- Reviewed source/access wording against `data/external/external_receipt.json`: selected GDR 1391 archives were transferred/hashed by the public runner; the Qfaults v2 raster still has zero ROI features; remaining source/schema/coverage gates are called out. DrivenData access is still login-gated; no credentials, bypass, upload, or monitoring were used.
- Ran local link checks: all relative Markdown links in 34 Markdown files resolve; all local `href`/`src` targets and HTML fragments in 7 site pages resolve; every `download` basename matches its linked file. Fixed the D2.8 filename mismatch and one stale research Markdown link found in this pass. Added direct buttons for all three research TIFFs plus the manual submission guide to the first home-page callout.
- Full suite in the project venv: `.venv/bin/python -m pytest -q` → **85 passed, 11 subtests passed**. The system Python lacks the optional dependencies; the successful run used the checked-in project venv and the repository's `src` import configuration.

## Pass 3 — full-brief re-check

| Acceptance area | Outcome |
| --- | --- |
| Metric-shaped loss paired with regional loss; near-miss behavior on spatially blocked holdout | Implemented and tested in prior experiments. Near-miss behavior changed; fresh-seed DTI gain did not replicate. No improvement claim and no retuning of the same loss screen. |
| D2.8 vs public leaderboard high 0.3195 | D2.8 bytes are locally downloaded, hash-checked, inspected, and format-validated. Official snapshot separately showed DARD 0.3195 and `wbg1` 0.2600; neither row identifies a TIFF hash. D2.8 attribution remains unresolved. |
| Three-to-five genuinely untried geological hypotheses | Current shortlist contains five, with layers/signatures, physical rationale, difference from prior work, planning priors/costs, official source/access gates, and falsifiable spatial-holdout criteria. H-31-04 source/schema audit is the lowest-cost next action; no new experiment is authorized until frozen. |
| No weekly slot without comparable blocked-holdout improvement and confirmation | Complied. No candidate is promoted; no file was submitted and no weekly slot used. H-31-02b failed its primary/perturbation gates; H-33-01's 80k gate was void and its 40k sensitivity is not a promotion result. |
| Easy TIFF download and exact manual submission steps | Direct links remain prominent on site entry and the executive summary. Three local zero-outside files pass strict checks. The page explains manual DrivenData steps and requires the entrant to review current official instructions; portal acceptance is unverified. |
| Official sources, access checks, score attribution, irregularities | `docs/sources.md`, `docs/irregularities.md`, and styled pages distinguish official facts, owner mirrors, user claims, and proxy results. Official rules PDF review covers all seven chunks; deadline-time conflict, eligibility, AI disclosure, and organizer-authenticated data remain open. |
| Automatic DrivenData monitoring or submission | None added. No account credentials handled, no monitoring, and no submission performed. |
| Status feed and local verification | `docs/status.json` regenerated from machine-readable evidence. `pytest`: 85 passed + 11 subtests; 3 TIFFs pass 12 local checks each; local link/fragment/download-name audits pass. |
| PR and merge | Pending final GitHub push/PR/merge attempt on the fixed branch; outcome must be recorded here only after the operation completes. |

## Remaining blockers

Organizer-authenticated training files and hidden expert labels are unavailable in this session; D2.8 receipt/hash attribution is unresolved; zero-outside portal acceptance and the historical range-error cause are unverified; the official deadline clocks conflict; entrant eligibility and the final AI-use narrative need authorized human sign-off. Current local candidates are not promoted. Do not rerun or retune against inspected SGMC labels. The next science action is a provenance/schema audit for H-31-04, followed—only if viable—by a preregistered, blocked holdout and fresh confirmation. No weekly slot is justified without an improvement over the current comparable holdout best and an exact-file audit.
