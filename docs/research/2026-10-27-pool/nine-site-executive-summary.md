# Archived nine-site executive summary — superseded 27 Oct 2026

> **Use the [current session review](../2026-10-27-current-session-review.md), not this archival page, for today’s file, estimate, or uniqueness decision.** The earlier draft mixed a dotted-submission-only novelty result with a later literal any-raster stop, included a speculative public-score range, and overstated the causal meaning of H33-B2 pruning. Those interpretations are withdrawn below; source run cards and frozen negative receipts remain unchanged.

## Current answer

- **File to download for a new submission:** none. Historical TIFFs are for source inspection only; do not upload them.
- **Defensible public-score estimate:** none. No organizer receipt is available for the owner-reported historical values, and HOLDOUT-DTI does not calibrate to the public leaderboard.
- **Uniqueness / slot:** no current candidate is cleared. The 44,090-dot preflight has a 37,441/44,090 (84.9195%) minimum overlap within 3 px of the pinned lattice, above the strict 70% stop. No new holdout or slot decision was made.
- **Leaderboard freshness:** no live organizer-page check was made. The repository’s 27 Oct snapshot value and the user-supplied current value conflict; neither is asserted current.

The exact historical files, owner-reported values, and lattice bounds for all nine sites are in the [current session review](../2026-10-27-current-session-review.md#nine-site-executive-record); directional pairwise dot overlaps are summarized [here](../2026-10-27-current-session-review.md#pairwise-nine-site-evidence) and preserved in frozen [`fleet-audit.json`](../2026-10-26-csr/fleet-audit.json).

## Historical scores and holdout evidence

The nine owner-ledger values are **OWNER-REPORTED, unverified, and not ORGANIZER-CONFIRMED**: GEMSDOE24 0.2477; GEMSDOE25 0.2600; GEMSDOE27 0.2449; GEMSDOE28 0.2710; GEMSDOE30 0.2600; GEMSDOE31 0.2708; GEMSDOE32 0.2778; GEMSDOE33 0.2632; GEMSDOE36 0.2750. These are preserved as reported claims, not measurements or forecasts. Their exact files and historical format/novelty findings are in the linked audit.

The only two GEMSDOE30 holdout results highlighted in this historical summary are:

- **HOLDOUT-DTI 0.186699 [0.173113, 0.200171] (seed 4201)** and **HOLDOUT-DTI 0.187694 [0.173631, 0.201989] (seed 4219)** for POOL-1; evaluator `component-holdout-v3-blockstats-20261025`; 60,988 withheld positives. POOL-1 beat the same-protocol `msdb_edge` comparator on both seeds, but the final dots breached the frozen 70% duplicate stop. **No TIFF was published.** See [`POOL-1 run card`](run-card.json) and [`post-merge addendum`](postmerge-addendum.json).
- **HOLDOUT-DTI 0.158162 [0.144986, 0.171474]** for CSR-1; evaluator `component-holdout-v3-blockstats-20261025`; 60,988 withheld positives. It did not beat same-run `msdb_edge` (**HOLDOUT-DTI 0.169986 [0.156534, 0.183948]**, same evaluator and withheld count). The exact CSR-1 raster subsequently failed the literal lattice novelty gate and the published outside-footprint convention. It is a historical research artifact, not an approved submission.

These holdouts are catalogue-recovery proxies, not organizer scores. Do not use either result to forecast a public score. Other sites’ site-frame results use different evaluators/protocols and are intentionally not compared here.

## H33-B2: verified file lineage, unverified score cause

The frozen pixel audit records D2.8 → r1 after 3,891 dots are removed, then r1 → H33-B2 after a further 2,545 dots are removed; H33-B2 has 37,654 dots, and the GEMSDOE36 PINN artifact contains those H33-B2 dots plus 1,200 more. The selected 37,660-dot GEMSDOE28 historical file is not the G28 r1 intermediate identical to the GEMSDOE31 selection.

The reported 0.2778 for H33-B2 is an owner claim with no organizer receipt. Pruning near-catalogue halo dots is a plausible way to reduce false-positive cost, but without hidden truth the removed cells’ true/false-positive status is unknown. The audit does **not** prove constant true-positive credit, that pruning caused a score rise, or that the owner value is correct. File genealogy is not a new geological discovery.

## Research continuation

The prior POOL-1 continuation plan is not a slot authorization. The current repository shortlist contains four proposed-but-unrun mechanisms, ranked qualitatively with source-access limits in the [current session review](../2026-10-27-current-session-review.md#candidate-hypotheses--proposals-only-no-lane-authorized). No candidate is being fitted now: the lane was not assigned, the active novelty stop remains, and the training-feature raster/processed arrays are not present in this checkout (raw owner-mirror labels are present). Preserve the experiment cap and shared holdout/writer implementation; only a positive leakage-safe spatial holdout, complete two-stage novelty pass, exact saved-byte validation, and a separate selector can authorize a later file.
