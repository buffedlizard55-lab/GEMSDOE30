# 30 October 2026 — repository review

**Verdict: NEGATIVE. No TIFF is approved to download or submit. No new TIFF was generated. No weekly slot was selected. No new holdout experiment was run.**

Branch: `arena/a759532a-gemsdoe30` (identical to `main` at `eaff218` before this review). Scope: check the live leaderboard, the public site, every local TIFF in `docs/downloads/` against the official format, the duplicate structure of those files, and the repo's own verifiers and tests.

## 1. Plain answers

| Question | Answer | Evidence |
| --- | --- | --- |
| What is the highest official score? | **0.4544** (rank #1, xiaofanhu). Public-test DW-Tversky. | [Live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), read 2026-10-30 |
| Is 0.4413 on the board? | **No** in the ranks checked (live ranks 1–23; the 29 Oct snapshot ranks 1–50). | [Snapshot](../2026-10-29-leaderboard-snapshot.json) |
| Is 0.3195 the highest? | **No.** It is rank #47 in the 29 Oct snapshot. | Same snapshot |
| Is 0.2778 (GEMSDOE32, H33-B2) the highest GEMSDOE score? | **Not verifiable.** It is below the rank-50 cutoff (0.3167), so it is not in the top 50. Owner-reported only. | Snapshot; [ledger](../../score-ledger.csv) |
| Can a file be downloaded and submitted now? | **No file is cleared.** See section 3. | Sections 2–4 |
| Can a unique TIFF be generated this session? | **No.** The repo's duplicate-stop rule, the uniqueness-rule decision (IR-30-097) and the lane/policy requirements are unresolved. Generating one anyway would bypass them. | [README](../../../README.md), [IR-30-097](../../irregularities.md) |

## 2. Format check of every TIFF in `docs/downloads/` (this session)

Method: `rasterio` read of each file; compared to the organizer template grid used by the repo (`docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif`: EPSG:32611, 3730 × 3292, 100 m, float32, 5,167,373 footprint cells). Checked grid match, NaN inside the footprint, finite cells outside the footprint, and the value range of the footprint cells. Reference for the format: [organizer PDF, NLR 96647](https://docs.nlr.gov/docs/fy26osti/96647.pdf) and [competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

- All 40 TIFFs: grid matches the template; no NaN inside the footprint; footprint values lie in [0, 1].
- **Two conventions exist.** Files named `-nan` / `-nanoutside` / `allfinite` carry NaN outside the footprint (0 finite cells outside). Files named `-zeros` carry 0 outside (7,111,787 finite cells outside). The organizer's text says outside-bound values are "null or NaN" (IR-30-092). Which convention the portal accepts is still unknown.
- **Reproduced mechanism for the portal error (IR-30-093, still a hypothesis).** On a NaN-outside file, a plain whole-array check `min >= 0 and max <= 1` evaluates to `False` (min = max = NaN). The same file with NaN replaced by 0 passes. Whether the portal uses such a check is **not verified**. A portal probe would consume a weekly slot (owner decision).

## 3. Executive table — which file, what estimate, is it unique?

| File (in `docs/downloads/`) | Dots | Format (section 2) | Uniqueness | Estimated score | Download and submit? |
| --- | --- | --- | --- | --- | --- |
| `GEMSDOE30-concealed-geothermal-unique-20261029.tif` (PR #76) | 29,707 | passes | **NOT unique.** 99.83% of dots within 3 px of the pinned 13GEMSDOE lattice (IR-30-088). | **None.** No holdout receipt; no organizer receipt. | **NO** |
| `GEMSDOE30-geothermal-unique-20261029T165045Z-3995629e.tif` (PR #78) | 9,652 | passes | **NOT unique.** Its own novelty receipt sets `duplicate_stop: true`. | **None.** | **NO** |
| `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca-nanoutside.tif` (owner label GEMSDOE30 "0.2600") | 44,090 | passes | **NOT unique.** Same dot set as 3 other local files (section 4). | Owner-reported 0.2600; **UNVERIFIED** (no receipt). | **NO** |
| `gems30-unique-offlattice-structural-20261028-s8.tif` / `-s7.tif` | 6,649 each | passes | **NOT unique:** s7 and s8 are the same dot set. | None. | **NO** |
| `GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif` | 40,000 | passes | **NOT unique:** byte-identical to the `20261026T160300Z` file. Lattice overlap 99.90% (per the 27 Oct site). | HOLDOUT-DTI 0.073314 (CI 0.063811–0.082800, 60,988 withheld positives; archived proxy, not an organizer score). | **NO** (duplicate-stopped) |

Estimate labels: **HOLDOUT-DTI** = repo evaluator, not organizer; **ORGANIZER-CONFIRMED** = none exists for any repo file; **OWNER-REPORTED UNVERIFIED** = numbers supplied in the task text. No projected score is written as a result.

## 4. Duplicate structure inside the repo (new finding, IR-30-099 proposed)

Exact dot-set comparison of all local TIFFs (positives > 0.5, finite):

- Byte-identical content under different names: `GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif` = `…-20261027T233111Z.tif`.
- Same dot set (100% overlap), different outside convention or name: the `gems24-h25-1-dotted-h19-5-d2-8-…-e56ea318af89` pair (`-nan`, `-zeros`), the `gemsdoe30-d28-poisson300m-offcat-44090-…-91eae1ca` triple, `gemsdoe30-edge-hybrid-80k-02845bd4` (`allfinite`, `nan`), the `g30s19` and `g30s20` pairs, `sgmc-hedge-d10-85k` (two), `TAD24-decensored-38000` (`nan`, `zeros`), `oof-gbm-adaptive-r5` (`nan`, `zeros`), `offlattice s7/s8`.
- **Irregularity:** the file `gems24-h25-1-dotted-h19-5-d2-8-…-nan.tif` has the same dot set as the file the GEMSDOE30 label calls `…91eae1ca`. The GEMSDOE24 owner label for that site is `h25-1-dotted-h19-5-d1-5 … 0.2477`, and the GEMSDOE25 label is `dotted-h19-5-d2-8 … 0.2600`. So at least one file's name, site and score attribution conflict. **Flag for review.** Do not treat any of these labels as independent submissions.

## 5. Verification run this session (all reproduced locally)

| Step | Result |
| --- | --- |
| `scripts/restore_public_mirrors.py --ids sample_submission` | restored; "Not organizer-authenticated" |
| `scripts/restore_public_mirrors.py --pins …/lattice-pin.json --ids registry_lattice` | restored |
| `scripts/build_research_site.py --check` | exit 0 |
| `scripts/verify_registry_preflight.py` | exit 0: `VERIFIED NEGATIVE: 37441/44090 minimum; historic CSR-1 44084/44090 within 3 px; no submission` |
| `pytest -q` | **411 passed, 38 skipped (pinned inputs not restored), 0 failed** |
| Live leaderboard fetch | #1 0.4544, #2 0.3925 (the 29 Oct snapshot shows #2 at 0.3916; the board moves) |

## 6. Irregularities for review

1. **IR-30-088 (carried).** PR #76's claim of "0.000 overlap with the pinned lattice" is false (99.83%).
2. **IR-30-097 (carried).** The literal 70%-within-3-px uniqueness rule is saturated by the lattice; no dense candidate can clear it. Owner decision required.
3. **IR-30-093 (carried; mechanism reproduced above).** NaN-outside files fail a naive whole-array range check. Portal behaviour unverified.
4. **IR-30-099 (proposed, this review).** Duplicate and mislabelled files in `docs/downloads/` (section 4).
5. **IR-30-100 (proposed).** The public Pages index (`https://buffedlizard55-lab.github.io/GEMSDOE30/`) still shows the **27 Oct** decision page, while the repo's latest review is 29 Oct. Checked live on 2026-10-30. The published site may not have been rebuilt after the last merges.
6. **Owner score claims.** 0.4413 and 0.3195 are not "current highest" on the official board; 0.2778 is outside the top 50 (section 1).
7. **Open PR #82** (`arena/5220da6d-gemsdoe30`, "Hash-bind duplicate stop and disable off-lattice generator") is open, with mergeability UNKNOWN. Not touched in this session.

## 7. Next steps (ranked; none executed here)

1. **Owner decision on the uniqueness rule (IR-30-097).** Without it no file can be cleared. Options: a rule that tests the lattice only at a stated tolerance, or a rule that compares against the organizer's own reference predictions rather than a pinned 13GEMSDOE raster.
2. **Owner decision on the outside-footprint convention (IR-30-092/093).** A single probe slot would settle NaN vs 0; this is the cheapest way to clear the "[0, 1]" portal error.
3. **De-duplicate `docs/downloads/`.** Move byte-duplicates to a stopped-artifacts folder, not deleted (AGENTS.md forbids altering stopped rasters; this needs an owner instruction).
4. **Rebuild and republish the Pages site** so the public page shows the current decision.
5. **Obtain an organizer receipt** (submission-page screenshot or the DrivenData submission history) for any score claimed in the leaderboard table. Without one, every score remains OWNER-REPORTED UNVERIFIED.
6. **Pick one lane, one hypothesis, three experiments and a two-hour budget** (S29-A is the cheapest per the 29 Oct review), using `gemsdoe30.holdout` and `gemsdoe30.submission` only.

## 8. Limitations and what is needed

- **DrivenData access.** No account credentials are available here; the training data and the submission history cannot be read. The leaderboard is read only as public page text.
- **No organizer receipt** links any repository raster to a leaderboard row.
- **Pinned inputs** (`sample_submission.tif`, the 13GEMSDOE lattice) come from owner mirrors, not organizer-authenticated downloads.
- **Requested but not done in this session:** the full "unique TIF" generation, the 3–5 hypothesis write-up with the full validation chain, and the README prompt rewrite. Each depends on decisions 1–2 above or on a multi-session lane.

## 9. Links for manual review

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Problem page and metric: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Leaderboard: https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- About page: https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- Format document: https://docs.nlr.gov/docs/fy26osti/96647.pdf
- CRS reference (EPSG:32611): https://epsg.io/32611
- Live Pages site (stale, IR-30-100): https://buffedlizard55-lab.github.io/GEMSDOE30/

## 10. Run card

```json
{
  "date_utc": "2026-10-30",
  "branch": "arena/a759532a-gemsdoe30",
  "experiments_run": 0,
  "budget": "3 experiments / 2 hours (none used)",
  "tif_generated": false,
  "tif_approved_for_download_or_submit": false,
  "slot_selected": false,
  "verdict": "negative",
  "official_top_score": {"value": 0.4544, "source": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/", "class": "ORGANIZER-CONFIRMED public board (public-test DW-Tversky)"},
  "owner_claims": {"0.4413": "not on board (ranks 1-23 live; 1-50 snapshot)", "0.3195": "rank 47 (snapshot)", "0.2778": "below rank 50 cutoff 0.3167; OWNER-REPORTED UNVERIFIED"},
  "format_check": "all 40 local TIFFs grid-match the template; [0,1] on footprint; NaN-outside vs zeros-outside conventions both present",
  "uniqueness": "no local TIFF cleared; PR #76 file 99.83% within 3 px of lattice",
  "duplicate_pairs_100pct_dotset": 14, "exact_array_duplicate_groups": 4,
  "verifiers": {"build_research_site --check": 0, "verify_registry_preflight": 0, "pytest": "411 passed / 38 skipped / 0 failed"},
  "irregularities_raised": ["IR-30-099 (proposed)", "IR-30-100 (proposed)"],
  "open_owner_decisions": [1, 2, 3, 4, 5, 6, 7]
}
```
