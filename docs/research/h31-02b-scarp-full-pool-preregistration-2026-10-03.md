# H-31-02b full-pool scarp-emitter screen — preregistration

**Frozen:** 2026-10-03, before any DTI from this variant. **Status:** preregistered; no holdout score included here. Parent geology hypothesis and feature transform: `H-31-02` in `docs/hypotheses.md` and `docs/research/h31-02-scarp-preregistration-2026-10-03.md`.

## 1. Why this separate registration exists

The first H-31-02 preregistration froze a 120,000-cell candidate-pool cap. Its capacity-only run, `docs/research/h31-02-scarp-orientation-preflight.json`, found accepted capacities of 25,664 / 18,481 / 16,318 / 18,857 against exact requirements 29,114 / 22,102 / 18,009 / 24,165; the SGMC global capacity was 33,737 against 80,392. **No DTI was calculated and no holdout label was used in that preflight.** The frozen H-31-02 test is therefore capacity-limited and void; its 120,000 cap will not be changed under that registration.

This separate variant removes only the arbitrary candidate-pool truncation. The feature formula, source bytes, 3-pixel minimum separation, exact dot budgets, folds, random seeds, and DTI gates remain unchanged. It still tests the same geological hypothesis, but has a distinct registration so the capacity failure cannot be hidden or presented as a scored negative result. Candidate ordering is fixed over all eligible positive-score cells; no labels, catalogue geometry, or SGMC values enter the ranking.

## 2. Data and provenance gates

Use the exact input, grid, encodings, and provenance checks in §2–3 of the parent preregistration: pinned owner mirror `data/raw/external/lidar_scarp_features_u8.tif` (SHA-256 `d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568`), owner metadata SHA recorded at run time, template/processed-data manifest, and the USGS SGMC raster/receipt. The owner-derived LiDAR stack is not organizer-authenticated. Never use template values as features or targets.

Before any DTI, run `python scripts/scarp_orientation_holdout.py --preflight-only`. Verify exact candidate and uniform capacity for all four spatial folds and for the 80,392-dot SGMC screen. If **any** budget is unavailable, write the preflight record and stop; no DTI is calculated. Record hashes, grid, candidate capacity, and the fact that DTI scoring has not occurred.

## 3. Frozen emitter for this variant

Use the exact frozen score `S` from parent preregistration §§3 and the existing tested implementation in `src/gemsdoe30/scarp.py`. The ranking domain is each fold's valid footprint (or the full valid footprint for the SGMC screen), restricted to `S > 0`.

Unlike the voided parent screen, there is **no candidate-pool cap**: rank every eligible cell by descending `S`, breaking ties by raster row then column. Apply the same greedy Poisson-disk acceptance rule with Euclidean exclusion radius **3.0 pixels**. Emit the first exact frozen budget from the accepted order. The implementation may stop the greedy sweep immediately when the required count is accepted; if it reaches the end first, record the available capacity and void the comparison. This early stop is exactly the prefix of the full deterministic greedy result, not a different selection rule.

## 4. Primary spatial holdout

Use the same four fixed spatial quadrants and fold-local exact 300 m DTI proxy as parent preregistration §4. The pooled result omits cross-quadrant kernel interactions and is not a competition score. Per-fold exact budgets are **29,114 / 22,102 / 18,009 / 24,165** (total **93,390**), matching the archived `adaptive` comparator's per-fold emitted counts in `docs/research/metric-emission-holdout-results.json`. Same-run uniform controls use those exact per-fold counts, sampled without replacement from each fold's valid footprint with seeds `20261003 + fold`.

**Primary pass (all required):** (1) pooled candidate DTI ≥ **0.19427** (archived fold-local best 0.1892699400542499 +0.005); (2) candidate exceeds same-run fold-count-matched uniform DTI by ≥ **0.005**; (3) candidate-minus-uniform is positive in at least **3/4** folds; (4) both arms have exact per-fold counts and distinct masks. Any failed capacity/count invariant voids the comparison. No post-hoc transform, fold, budget, or gate changes.

## 5. Independent SGMC screen

Use the exact parent preregistration §5 component holdout draws (five repeats, `seed=30*31 + repeat`, hide 30% of 8-connected SGMC components, score outside the 300 m dilation of visible catalogue). Emit **80,392** global dots using the same full-pool, 3-pixel selector. The exact-count blind-random control is drawn from the full valid footprint with seed `1000 + 80,392`, matching the recipe recorded in `docs/research/novelty-holdout.md`.

Compare with the saved per-repeat `cand_t04s4` benchmark in `docs/research/novelty-holdout.json` (mean **0.09525705977964063**), which is an archived numeric baseline only: its OOF mask is absent and cannot be recomputed here. Independent-screen pass requires (1) mean candidate DTI ≥ **0.10025705977964063**; (2) candidate beats the archived best in at least **4/5** repeats; and (3) mean DTI beats same-run exact-count blind random by ≥ **0.005**. Report whether the deterministic random scores/counts exactly reproduce their saved values. Even an apparent screen pass is not promotion; regenerate the historical best mask and run fresh seed-31 paired confirmation before any promotion decision.

## 6. Additional fixed checks

* The rank score is not a probability; probability calibration is not applicable. If a later learned model consumes it, apply the repository's existing calibration gates.
* Within each held-out quadrant, permute the valid strike codes while preserving step, face, coherence, and coverage. If original candidate gain over uniform is positive, the permutation must remove at least **50%** of that gain. Report the check regardless of screen result; failure blocks promotion.
* Report per-fold lift, top direct-hit/missed catalogue components with coordinates and local feature values, and a map-based confounder review. Qualitative inspection cannot override numeric gates.

## 7. Interpretation and stop conditions

A successful run would establish only that this fixed, full-pool emitter beats frozen proxy baselines on two imperfect holdouts. It cannot establish private-test gain, leaderboard gain, calibration, or a valid competition score. **No weekly slot may be used from either screen alone.** If any capacity or provenance check fails, record the failure and stop without DTI.
