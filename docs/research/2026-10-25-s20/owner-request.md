# Owner request for this session (S20, 2026-10-25) — distilled, read first

The full standing brief lives verbatim in
[`OWNER_BRIEF.md`](../../../OWNER_BRIEF.md); this file records only what the
2026-10-25 S20 prompt added or re-emphasised, so the session is auditable.

1. **Focus sites (highest owner-reported submissions):** GEMSDOE24
   `h25-1-dotted-h19-5-d1-5…: 0.2477`; GEMSDOE25 `dotted-h19-5-d2-8…: 0.2600`;
   GEMSDOE27 `topo-gap-closure-t-v2-on-d1-5…: 0.2449`; GEMSDOE28
   `h27-4-r1-solo-d2-8…: 0.2708`, `h32-1-prethin-tip-euler-d2-8…: 0.2649`,
   `h36-1-rung30-blind-r1…: 0.2710`, `h38-1-hf-euler-r30-r1…: 0.2707`;
   GEMSDOE30 `d28-poisson300m-offcat-44090…: 0.2600`; GEMSDOE31
   `h27-4-solo-d28…: 0.2708`; GEMSDOE32 **`h33-h33-2-b2…-zeros: 0.2778`
   (the family maximum — explain it, then try to beat it with a unique
   submission)**; GEMSDOE33 `h33d-analog-tip-stepover-r30…: 0.2632`;
   GEMSDOE36 `anderson-geothermal-pinn-38854…-zeros: 0.2750`.
   All are **owner-reported, none organizer-confirmed** (no receipts).
2. **Highest urgency:** generate a *unique* submission TIF (never a copy;
   prior submissions may be studied for learning only), downloadable in one
   click, with an unambiguous machine-checked verdict on whether it is OK
   to submit — automated gates, no human inspector.
3. **Parallel-run protocol:** one lane; rank-correlation >0.90 or >70 % of
   dots within 3 px of any registry raster (checked on the surface *and*
   on final dots) = duplicate, log and stop; reuse shared feature stack /
   holdout evaluator / submission writer; label every number HOLDOUT-DTI
   (evaluator, withheld positives, 95 % CI) or ORGANIZER-CONFIRMED;
   per-feature leakage canary (AUC >0.90 = leakage until proven otherwise);
   end with a JSON run card (hypothesis, mechanism, non-fault mimic,
   HOLDOUT-DTI + CI, registry correlation/overlap, raster SHA-256,
   validator output, submission name + ≤140-char note, promote/negative);
   ≤3 experiments / ≤2 h; never allocate a weekly slot — selection is a
   separate owner step.
4. **Before implementing:** 3–5 untried geological hypotheses (layers,
   physical signature, why off-catalogue, difference from this repo),
   ranked by expected DTI improvement vs cost; validate the top one on the
   spatially blocked holdout before any slot is considered; any hypothesis
   needing new external data must name a specific free official source and
   verify it is obtainable first.
5. Leaderboard figures in the prompt conflict (0.4413 vs “0.3195 highest”);
   the official page fetched this session reads **#1 = 0.4413**
   (0.3195 was the verified 2026-10-03 leader). Recorded in
   `docs/score-ledger.csv`.
6. Standing requirements carried over: prompt in the repo README and read
   each session; Core Values (*Maximize P(Win)*, *Own the Outcome*);
   executive-summary page explains exactly how to submit; unique filename +
   short distinguishing note; the historical portal error
   “Predicted values must be in range [0, 1]” must be impossible by
   construction on the primary download; three cumulative passes; open a
   PR from the assigned branch and merge to `main`; state remaining work
   and limitations. No manual input; verify line by line; no hallucinations.
