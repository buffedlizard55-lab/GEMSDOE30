# Nine-site executive summary — GEMSDOE24/25/27/28/30/31/32/33/36 (verified 2026-10-27)

Method: depth-1 git clones at the HEADs below; every `docs/**.tif` inventoried
(`registry.json`: 394 aligned rasters); historical-leader subset algebra recomputed
pixel-exactly (`fleet-audit.json`); each site's own current decision read from its
HEAD README/run cards. All leaderboard numbers from the owner's prompt ledger are
**OWNER-REPORTED** (no organizer receipt in any repo). Live public leaderboard
2026-10-27: **#1 0.4544** — [source](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

## The answer first: what to download, estimated score, unique?

| # | File (site) | Owner-reported leaderboard | HOLDOUT-DTI (labelled) | Unique vs other 8 sites? (measured) | Download → submit? |
|---|---|---|---|---|---|
| — | **POOL-1 production raster (GEMSDOE30, this run)** | none (never submitted) | **0.186699** [0.173, 0.200] E1; 0.187694 E2 (`component-holdout-v3-blockstats-20261025`, 60,988 withheld) — beats `msdb_edge` +0.0172/+0.0134, paired CIs > 0 | **NO** — 88.74%/75.81%/71.08% dots within 3 px of FFL1/MSDB1/CSR1 (own repo) | ⛔ **Not published (duplicate-stop)** |
| 1 | `gems30-CSR1-44090-20261026-502fb5948335-zeros.tif` (GEMSDOE30) | none (not in owner ledger) | 0.158162 (same evaluator as above) — trails `msdb_edge` 0.169986 | **YES** — max 67.70% ≤ 70% vs 380 unique-SHA rasters rechecked 2026-10-27; surface ρ ≤ 0.138 | Download YES (research) · **Submit NO** (negative gate) |
| 2 | `h33-h33-2-b2-…-e5eb6e7e-zeros` (GEMSDOE32) | **0.2778** (highest of the 9) | — (family scored 0.10519 in GEMSDOE28's frame) | **NO** — exact subset of r1/D2.8 family | Already submitted · **do not resubmit** |
| 3 | `anderson-geothermal-pinn-38854` (GEMSDOE36) | 0.2750 | — | **NO** — = H33-B2 + 1,200 dots | Already submitted |
| 4 | `h27-4-r1-solo-d2-8` (GEMSDOE28) = GEMSDOE31 leader | 0.2708 | — | **NO** — identical across two sites | Already submitted |
| 5 | `h33d-analog-tip-stepover-r30` (GEMSDOE33) | 0.2632 | — | Family overlap, not a subset | Already submitted |
| 6 | `dotted-h19-5-d2-8` (GEMSDOE25) = `d28-poisson300m` (GEMSDOE30) | 0.2600 | — | **NO** — identical across two sites | Already submitted |
| 7 | `h25-1-dotted-h19-5-d1-5` (GEMSDOE24) | 0.2477 | — | **NO** — exact subset of GEMSDOE27 leader | Already submitted |
| 8 | `topo-gap-closure-t-v2-on-d1-5` (GEMSDOE27) | 0.2449 | — | **NO** — = D1.5 + 1,259 dots | Already submitted |
| 9 | `gemsdoe36-kpl36-exp3-…-fc869911e88c-zeros` (GEMSDOE36 latest) | 0.1647 | 0.170100 (`gems-segment-pooled-v1`, site frame) | Site claims ≤70% on its registry | Already submitted (banner stale, IR-POOL-05) |
| 10 | `gems30-MSDB1-edge44090` (GEMSDOE30) | 0.1462 | 0.170462 (our evaluator) | 64.78% max at its audit | Already submitted |

**Bottom line:** there is currently **no unsubmitted, unique, gate-passing file on any
of the nine sites**. The highest-scoring historical file (H33-B2, 0.2778 owner-reported)
is a pruned re-emit of the same h19-5 dots already submitted five times under different
names. The best *science* (POOL-1) exists but its dots collide with this repo's own
MSDB family. The next submittable file must come from a fresh preregistered lane
(POOL-2, novelty-constrained emission) — see `review.md` §7.

**Score estimates:** refused as point values (protocol: a projection is never a score;
GEMSDOE31's cross-family audit puts LOO RMSE at 0.090). Scenario anchors only:
HOLDOUT ≈ 0.170 (our evaluator) → 0.1462 owner-reported (MSDB1-edge);
HOLDOUT 0.1701 (GEMSDOE36 evaluator) → 0.1647 (KPL-36). A future POOL-2 at
HOLDOUT ≈ 0.187 scenarios to ~0.16–0.19 public — below 0.2778 — with its upside in
the Final Round expanded-label rescoring. Beating 0.2778/0.4544 on the *public* split
requires recall of expert-mapped new geometry near existing systems, which our
>2 px off-catalogue dispersed emission deliberately trades away; that trade must be
revisited explicitly (collar width is a preregistration decision, not a tweak).

## Per-site detail (HEAD, own current decision)

- **GEMSDOE24** `2521cb676e17` — "No new submission is authorized"; 2026-10-27 integrity
  review shows the retained r13 lattice forces ≥82.34% 3-px overlap for any 37,654-dot
  candidate under a literal any-raster gate. Local best point S3DEP1 HOLDOUT 0.166060
  (`gems-segment-pooled-v1`) remains DO NOT SUBMIT (71.32% vs stopped DKRN1).
- **GEMSDOE25** `5a60fb475b71` — H73-BW blocked before fit (8 cache-gate errors);
  H73-PM HOLDOUT 0.11343 vs same-run H35 0.15239 (22,290 withheld) — negative.
- **GEMSDOE27** `5ee301149eb5` — Session-13 audit; H31-1 strongest evidence-qualified
  download but explicitly "not authorized for a weekly upload" pending selector;
  H31-3 (+0.00037, CI spans 0) and H32 (−0.00349) negative.
- **GEMSDOE28** `67dbdf4da84f` — S22C ctxHGB: first fresh lane there to pass its site
  gates (HOLDOUT 0.12018 vs dotted-b2 0.10519, Δ+0.01498 [+0.01067, +0.01932], 36,596
  withheld, site frame) — still "SELECTOR CHECKLIST REQUIRED", no slot spent.
- **GEMSDOE30** `3c3d7255fdbb` → this run — CSR-1 negative-but-unique (0.158162);
  **POOL-1 confirmed +0.0172/+0.0134 over `msdb_edge`, duplicate-stopped at 88.74%**.
- **GEMSDOE31** `abd9a45cc7ad` — "NO file is approved to submit"; cross-family
  projection audit (LOO RMSE 0.090) retires in-family score projections; H31-YM negative.
  Clone also carries a malformed aligned raster (2,610,312 in-footprint NaNs).
- **GEMSDOE32** `1398109a23f0` — banner DO NOT SUBMIT; H47-1 LDGI repo-high
  HOLDOUT 0.121959 (site frame), verdict negative; lattice fail-closed at 99.6%.
- **GEMSDOE33** `122e2240a835` — "NO raster is OK TO SUBMIT"; FSML duplicate,
  FSML2-CC unique-but-negative; B2 forensics note agrees H33-B2 is one emission family.
- **GEMSDOE36** `61783525af4a` — KPL-36 "verdict: promote" (HOLDOUT 0.170100,
  `gems-segment-pooled-v1`, Δ+0.0096 vs GVSC replication) **but the owner ledger
  already records 0.1647 for that exact file** — slot spent; banner is stale.

## Why 0.2778 happened (one paragraph)

H33-B2 = D2.8 minus exactly the dots at ≤2 px from already-mapped faults. The
organizer masks only the catalogue pixels themselves, so 1–2 px halo dots were paid
false positives (0.2 each) earning almost no extra kernel credit beyond what 3 px
dots already provide. Deleting 6,436 such dots (0.2600 → 0.2708 → 0.2778) is pure
denominator hygiene at constant truth credit (T ≈ 6,602 across the ladder). No site
added a single new dot to reach its "best" score — the nine "leaders" are one
44,090-dot cloud viewed through three distance collars. Surpassing 0.2778 therefore
cannot come from more pruning; it needs higher hidden-fault recall (β=0.8 penalizes
misses 4×), which is precisely what POOL-1 improved on the catalogue proxy — the
open problem is emitting those dots somewhere the MSDB family hasn't already packed,
and/or revisiting the >2 px collar for the public split under a new preregistration.
