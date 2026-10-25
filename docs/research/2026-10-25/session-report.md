# GEMSDOE30 session report — 2026-10-25 (branch `arena/6a157983-gemsdoe30`)

**Bottom line.** A unique, format-valid GeoTIFF was generated and is downloadable
(`docs/downloads/gemsdoe30-h-cc1-dispersed3px-32058dots-nan.tif`). It is **not** a
recommended competition entry: on the catalogue-proxy holdout it scores below a matched
random control, so the verdict is **negative**. Nothing here is a leaderboard score. No weekly
slot was used, and no organizer receipt exists for any number below.

Labels: **HOLDOUT-DTI** = catalogue stand-in holdout, shared evaluator
`component-holdout-v2-footprint-20261025`, withheld positives 19,714–20,870 per split, 95 % CI
(t-interval over 5 split seeds). **ORGANIZER-CONFIRMED** = none exists in this session.
**OWNER-REPORTED** = copied from the owner's prompt and unverified.

---

## 1. Why the GEMSDOE25 / GEMSDOE32 family scored well (analysis)

Source-verified facts:

- The official metric is `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)` with a 300 m triangular kernel.
  Rules, problem page: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>.
  Official FN term: `FN_w = Σ_g [1 − max_x p(x)k(d)]`, which equals `G − TP_w`.
- The repo's byte-level reconstruction shows that the historical H33 / GEMSDOE32 support equals GEMSDOE28's
  positive support with every dot at catalogue distance ≤ 2 px removed (0 mismatched pixels).
  Receipt: `docs/research/2026-10-25/recipe-reconstruction.json`. This is a reconstruction of files,
  not an explanation of the organizer's hidden labels.

Mechanism (PhD-level reading of the metric, checked by our measurements):

1. **α = 0.2 makes false positives cheap and false negatives expensive.** An unmatched truth pixel costs
   0.8 per unit, while a wasted dot costs 0.2 per unit. Score therefore rewards recall of the
   kernel-blurred truth, not precision.
2. **TP credit is a maximum over the kernel, not a sum.** Dots that cluster inside one 300 m neighbourhood
   add false-positive cost but almost no additional true-positive credit. Pruning dots that sit within 2 px of
   the catalogue removes redundant support and cuts FP mass faster than TP mass.
3. **Dispersion is the measured lever in this session** (section 3): the same top-1 % contact-coincidence
   score moved from 0.0234 to 0.0539 when thinned to 3-px spacing.
4. **Caveat — pruning and the holdout proxy both reward catalogue-like geometry.** The stand-in truth is the
   catalogue itself, and the competition labels are *new* faults. A gain on the proxy does not transfer
   automatically to the private set.

Score labels: the owner's GEMSDOE25 value of 0.2600 is **OWNER-REPORTED**. The ledger records the file
attribution as unresolved (`docs/score-ledger.csv`). The 0.2778 value for GEMSDOE32 is also **OWNER-REPORTED**.

**Can we beat 0.2778?** Not demonstrated. The only evidence this session is a negative holdout result. Under
the protocol, no candidate is promoted without beating the comparator on the fixed evaluator. The repo's
prior comparator was not reproduced here, so the gate cannot be applied honestly.

## 2. Leaderboard verification (official)

- Official leaderboard, read 2026-10-25: **#1 = 0.4413** (xiaofanhu), #2 = 0.3916, #10 = 0.3375,
  #23 = 0.3217, #24 = 0.3169. Source: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>.
- **Irregularity:** the prompt's "0.3195 is the highest score right now" does **not** match the official page.
  No 0.3195 entry appears on pages 1–2. The prompt's "0.4413" is the figure that matches.
- The page shows public-test scores only. Private-test and expanded-label scores decide the prizes.

## 3. What was built and measured (3 pre-registered experiments, cap reached)

Script: `scripts/contact_coincidence_holdout.py`. Receipt: `contact-coincidence-holdout.json`.
Run card: `h-cc1-run-card.json`.

Hypothesis **H-CC1**: where high-pass Sobel gradient magnitudes of RTP magnetics (`rtp`) and isostatic gravity
(`iso_grav_anom`) peak together, a discontinuity is more likely than either gradient alone. Uses **no**
catalogue-derived feature, so leakage is impossible by construction. The canary confirms this.

| Arm | Dots | HOLDOUT-DTI | 95 % CI | Result |
|---|---:|---:|---|---|
| Exp 1 — H-CC1 top 1 %, probability 0.5–1 | 51,207 | 0.0152 | [0.0141, 0.0163] | below control |
| Exp 2 — same selection, binary p = 1 (ablation) | 51,207 | 0.0234 | [0.0218, 0.0251] | below control |
| Exp 3 — same score, greedy 3-px dispersion, binary | **32,058** | **0.0539** | [0.0507, 0.0572] | below control; **not budget-matched** |
| Comparator — RTP gradient only, top 1 % | 51,207 | 0.0104 | [0.0093, 0.0114] | — |
| Control — matched random dots (5 seeds) | 51,207 | 0.0659 | [0.0631, 0.0687] | reference |

Canary AUC (seed 31, single feature alone, hidden vs scored domain): H-CC1 0.666, RTP gradient 0.589,
gravity gradient 0.618. None exceeds 0.90, so no leakage is flagged.

**Interpretation.**

- The contact-coincidence ranking is weak (AUC 0.67) and does not beat a random control at equal budget.
- Dispersion is a real effect. The same score's DTI rises ×2.3 when clustering is removed (exp 2 → exp 3).
- **Deviation (flagged):** experiment 3's 5 % pool was exhausted at 32,058 dots, short of the 51,207 budget,
  so it is not budget-matched. We therefore cannot claim it beats or loses to random at equal dots.
  Closing that gap needs a new, pre-registered experiment, which is outside this session's cap.
- Exp 1–3 used fixed thresholds chosen before running. Nothing was tuned on holdout labels.

## 4. The downloadable TIFF (what was generated, and what it is not)

- File: `docs/downloads/gemsdoe30-h-cc1-dispersed3px-32058dots-nan.tif` (+ `.json` sidecar).
- SHA-256: `837f555efe1c55f53258aa2fa8b5528684395cc1226a233cf8013690b6ac63ff`.
- Format: one float32 band, EPSG:32611, 3730 × 3292, 100 m north-up transform identical to the template.
  Values 0 or 1 inside the 5,167,373 valid cells, NaN outside (7,111,787 cells). The official page says
  "data outside the bounds is null or nan" (<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>).
- Validator: `scripts/validate_submission.py` passed every check (`h-cc1-validator.json`).
- Name: `gemsdoe30-h-cc1-dispersed3px-32058dots`. Note (117 chars):
  "H-CC1 dispersed 3px contact-coincidence, 32058 dots; catalogue-proxy holdout-DTI 0.0539 (unscored, not slot-approved)".
- **Uniqueness:** against 19 repo rasters (partial registry), max full-footprint Spearman = **0.0072** and max
  dot overlap within 3 px = **51.5 %**. Against the historical H33 top reference (GEMSDOE32, `…-zeros`, SHA pin
  `c55bafc4…` verified), Spearman = **0.0038** and 23 % of dots within 3 px. No duplicate threshold (0.90 / 70 %)
  is crossed. Decision remains `blocked-incomplete-evidence`, because the parallel registry is not supplied.
  Receipts: `h-cc1-novelty.json`, `h-cc1-vs-h33-novelty.json`, `novelty-registry-partial.json`.

**Is it OK to download and submit? Plainly:**

- **Download: yes.** It is a valid, unique file derived from the features and documented method above.
- **Submit as the final entry: no.** It is negative on the holdout and loses to a random control. The rules say
  one final submission is chosen (rules §3.4, §3.5). Do not use it for that.
- **Submit as a feedback upload: allowed by the rules, but only by you, from your own DrivenData account.**
  Up to three per week (rules §3.2). Before doing so, replace the training files with the official download
  (see irregularity I-1).
- The sandbox cannot upload to DrivenData. It is not authenticated and cannot sign the eligibility attestation,
  which the rules require the authorized individual to sign (rules §1.3, §A.1).

## 5. Hypotheses (ranked; validated only where data allowed)

Ranked by expected DTI gain × (1 / implementation cost). Planning priors are **not** measured scores.

| Rank | Hypothesis | Layers and signature | Why off-catalogue | Novelty vs repo | Status |
|---|---|---|---|---|---|
| 1 | **Coverage-first placement on a physical score** (dispersed dots, 3-px spacing, score from geology) | Any gradient score, thinned | Targets recall of unmapped segments without clustering FP cost | Mechanism newly measured here; "dotted/Poisson" names exist in other sites | **Tested** (exp 3): 0.0539, below random control, not budget-matched |
| 2 | **H-CC1 contact coincidence** (RTP × isostatic gravity gradient) | `rtp`, `iso_grav_anom` | Juxtaposition of two contrasts | Not implemented elsewhere in repo | **Tested** (exp 1–3): weak (AUC 0.67) |
| 3 | Geodetic strain-rate lineaments (`geod_shearrate`, `geod_dilaterate`) | Strain-rate ridges | Deformation localised on young fault zones | Dilatation appears in 8 repo docs; partly tried | Not tested. Confounder: groundwater subsidence |
| 4 | Basement-step gradient (`depth_to_base_surf`) | Sediment-thickness step | Faults juxtapose different basin depths | Basement appears in 6 repo docs | Not tested. Confounder: basin margins |
| 5 | Radiometric K/Th/U endmember along lineaments (GeoDAWN) | Radiometrics not in the 19-band training stack | Hydrothermal alteration along faults | Listed as H-31-04 in repo | **Blocked:** radiometric grids need the official USGS release (ScienceBase 657e1d85…), which this sandbox cannot reach. |

## 6. Irregularities (flagged for review)

- **I-1 Training data came from owner-hosted public GitHub mirrors.** The restore script pulled
  `training_features.tif` and `labels.tif` from the owner's public repos. Rules §3.1 and §3.3 say training data is
  provided to competitors on DrivenData after registration. Whether mirrored copies are permitted is a rights
  question I cannot settle here. Mitigation: replace them with your own official download, then verify the
  SHA-256 pins. The pins are consistency checks, not organizer authentication. The local copy is git-ignored and
  was not committed.
- **I-2 Method lane missing.** The prompt says "your lane is the single method paragraph below". No such paragraph
  exists in the request. The previous session also flagged this. This session self-assigned H-CC1 and recorded
  it as such.
- **I-3 Parallel registry missing.** Only 19 repo rasters plus 3 H33 references were checked. The decision stays
  `blocked-incomplete-evidence`.
- **I-4 Exp 3 not budget-matched** (32,058 vs 51,207 dots). See section 3.
- **I-5 Source gaps.** 3,061 in-footprint cells are NaN in both `rtp` and `iso_grav_anom`. They keep
  probability 0 and remain scored background.
- **I-6 Leaderboard figure conflict.** Official #1 is 0.4413. The prompt's 0.3195 "highest" is not on the page.
- **I-7 Branch mismatch.** `OWNER_BRIEF.md` names `arena/01a10289-gemsdoe30`, but this session is
  `arena/6a157983-gemsdoe30`. This session's work stays on the assigned branch.
- **I-8 Owner-reported scores** (0.2600, 0.2778, and others) remain unverified. None is used as evidence here.
- **I-9 Rules PDF is version "SEPTEMBER 2026"** (chunks 1–5 read). Appendix A.13 policy factors may weigh
  "technological diversity", which is relevant to the uniqueness goal. Not evaluated further here.
- **I-10 Holdout is a proxy.** Stand-in "new faults" are catalogue components. The competition scores **new**
  faults. Proxy scores are not competition estimates.

## 7. Limitations and what is needed next

1. **Data access:** the authorized DrivenData download must be done by the owner. Source: rules §3.1.
2. **Parallel registry and lane:** supply the method paragraph and the complete registry, or confirm H-CC1 as the
   assigned lane.
3. **Budget-matched exp 3b (not run, cap reached):** repeat the dispersion test with the pool widened until 51,207 dots
   are accepted, plus a random control at 32,058 dots. This is needed before any claim about dispersion versus random.
4. **Current-best comparator:** reproduce the repo's prior best on the fixed evaluator. Without it, the promotion gate
   cannot be applied.
5. **Radiometric source:** the official USGS GeoDAWN release (<https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7>,
   DOI <https://doi.org/10.5066/P93LGLVQ>) must be fetched from a network that can reach it.
6. **AI-use disclosure:** the rules (§3.2) require a narrative disclosure of generative-AI use. Draft:
   `docs/ai-disclosure-draft.md`.

## 8. Verification log (line by line)

| Claim | Check | Source / receipt |
|---|---|---|
| Metric formula and NaN-outside rule | Read official page 1 and 2 | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| Leaderboard #1 = 0.4413; no 0.3195 | Read pages 1–2 | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |
| Data-release, one final entry, 3/week | Read rules §1.1, §3.1–3.5, §A.1 | <https://docs.nlr.gov/docs/fy26osti/96647.pdf> (also <https://www.nlr.gov/docs/fy26osti/96647.pdf>) |
| Rules page points to official PDF | Read | <https://www.herox.com/GEMSPrize/resource/2274> |
| Historical H33 file integrity | SHA-256 of GEMSDOE32 `…-zeros.tif` = `c55bafc4…` (matches audit pin) | <https://github.com/buffedlizard55-lab/GEMSDOE32> |
| Candidate format | `validate_submission.py` | `h-cc1-validator.json` |
| Holdout numbers | `contact-coincidence-holdout.json` (shared `masked_dti`) | local receipt |
| Tests | `python -m pytest` | 129 passed, 5 skipped (torch absent) |

Every number in this file is copied from a receipt. None is a projection or a leaderboard score.
