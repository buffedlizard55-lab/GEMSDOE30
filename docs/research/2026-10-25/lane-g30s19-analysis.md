# Lane G30-S19 — why H33 won, and a unique candidate designed to beat it (2026-10-25)

Every number below is labelled **HOLDOUT-DTI** (local, evaluator
`component-holdout-v2-footprint-20261025`) or **OWNER-REPORTED** (unverified).
Nothing is ORGANIZER-CONFIRMED. No projection is written as a score.

## 1. Why did `h33-h33-2-b2-…-zeros` get 0.2778 (OWNER-REPORTED, GEMSDOE32)?

Verified by byte reconstruction (prior session, re-used here): H33's 37,654-dot
support is *exactly* the GEMSDOE28 solo-d2.8 support (40,199 dots) with every
dot at catalogue distance ≤2 px (≤200 m) deleted — zero mismatching pixels.
The lineage is one belief surface refined by emission only:

`H19-5 multiline belief 0.1922 → Poisson d1.5 0.2477 → d2.8 0.2600–0.2708 → >2 px flank prune 0.2778` (all OWNER-REPORTED)

Mechanism (official metric: DTI = T/(0.2T+0.2F+0.8G), R=300 m triangular,
α=0.2, β=0.8 — [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)):

1. Known USGS/INGENIOUS pixels are masked out of scoring, so dots hugging
   catalogue traces earn little/no TP credit.
2. TP credit per truth pixel is a **max** over nearby predictions: redundant
   neighbours add FP mass (F) without adding T.
3. Therefore thinning (removing redundancy) and flank pruning (removing
   mask-adjacent waste) raise T-per-F efficiency. H33 is an *emission*
   improvement, not new geology: Spearman 0.968 and 100% ≤3 px overlap vs its
   GEMSDOE28 parent (measured, `h33-historical-duplicate-audit.json`).

**Consequence:** pruning this family further has diminishing returns and
deletes genuine splays/extensions (which count as "new" faults). Beating
0.2778 requires a better *belief surface* — more true unmapped-fault coverage
per FP unit — emitted at least as efficiently. That is Lane G30-S19.

## 2. Can we beat 0.2778? Honest answer

It cannot be known locally: the hidden expert-labelled test set is not the
catalogue. What *can* be shown — and was, under a preregistered
hide-and-recover protocol — is that the new lane recovers withheld whole fault
components far better than every non-leaky comparator and better than the
registry family evaluated on the same frame. That is the strongest legitimate
local evidence available, and it is the project's promotion criterion. The
catalogue frame is known to be biased (IR-30-039 inversion: H33 scores
HOLDOUT-DTI 0.0054 here *by construction*, since its prune used the full
catalogue), so holdout superiority is necessary-but-not-sufficient evidence.
Anyone promising >0.2778 in advance is hallucinating; this candidate is the
best-validated unique entrant this repo has produced.

## 3. Results (HOLDOUT-DTI; 20,870 withheld positives, 1,085 components)

| Arm | Dots | HOLDOUT-DTI |
|---|---:|---:|
| **Habitat GBM + EDGE @60k (submitted recipe)** | 60,000 | **0.2230** [95% CI 0.2052–0.2396] |
| Habitat GBM + EDGE self-stop | 62,779 | 0.2227 |
| Habitat×proximity + EDGE self-stop | 64,602 | 0.2150 |
| Habitat×proximity + Poisson r2.8 | 41,832 | 0.1945 |
| Proximity-only + EDGE | 72,106 | 0.1672 |
| Registry D28 (leaky reference, not a gate) | 44,090 | 0.1176 |
| Registry H33 (leaky reference, not a gate) | 37,654 | 0.0054 |
| E2 failed design (distance-input GBM, best arm) | 56,809 | 0.0296 |

- Leakage canaries: 43/43 features AUC ≤0.90 (max 0.7636, visible-only
  proximity). Strongest physics singles: `edge_coinc_mag_topo` 0.576,
  `geod_2ndinv` 0.578 — weak alone, strong jointly (the habitat thesis).
- Novelty (final dots): max Spearman 0.029; max ≤3 px overlap 65.1%
  (edge-hybrid-80k); vs H33 winner Spearman 0.025, overlap 34.9% ⇒ unique lane.
- Winner anatomy learned and reused (permitted): sparse binary dots, 0 on
  catalogue, >2 px flank exclusion, zeros-outside encoding. Belief, features,
  model and emitter are all independent of every registry raster.

## 4. Irregularities flagged for owner review

- **IR-S19-01** Lane self-assigned: the prompt's "single method paragraph"
  is not identifiable in the text received; lane frozen in preregistration
  before experiments. Owner may reassign future sessions.
- **IR-S19-02** Requested shared files `evaluate_holdout.py` /
  `submission_writer.py` don't exist; shared equivalents in
  `src/gemsdoe30/{holdout,submission}.py` were reused (no private fork).
- **IR-S19-03** All historical scores (0.2778, 0.3195, 0.4413…) remain
  OWNER-REPORTED with no organizer receipts; the prompt's leader claims conflicted; a parallel session read the
  official leaderboard on 2026-10-25 as #1 = 0.4413 (IR-30-057/072), so 0.3195 is a stale snapshot. This session did not independently re-read it (login-walled here).
- **IR-S19-04** Data are hash-pinned owner mirrors, not organizer-authenticated
  downloads. Template contains label pixels (footprint only was used).
- **IR-S19-05** EDGE truth-mass prior = visible catalogue count (60,988);
  dot budget 60k transferred from the holdout curve. Bootstrap CI holds FP
  fixed (conditional CI).
- **IR-S19-06** Novelty registry = 9 pinned priority rasters + local
  downloads; other parallel lanes' *surfaces* were unavailable, so the
  surface-stage check used registry dots as reference. A complete-registry
  pass is not claimed.
- **IR-S19-07** Closest novelty neighbour is edge-hybrid-80k at 65.1%
  ≤3 px overlap (passes the 70% gate). Both lanes predict fault habitat, so
  partial overlap is expected; no dots were moved to game the gate.

## 5. How to submit (owner action — automation used no slot)

1. Download `gemsdoe30-g30s19-habitat-edge-60000dots-20261025T210221Z-b527922d7f-zeros.tif`
   (SHA-256 `8a0301d5…f43cc9`) from the site home page.
2. On DrivenData → New submission → choose that file.
3. Paste note (84 chars): `G30-S19 habitat GBM (19-band, no catalogue-distance inputs) + EDGE 60k, off-cat >2px`
4. Save the organizer receipt + returned score next to the run card; only then
   is any number ORGANIZER-CONFIRMED.

Reproduce: `python scripts/restore_public_mirrors.py && python scripts/prepare_data.py && python scripts/lane_g30s19.py canary|holdout2|final --keep 60000|novelty`
