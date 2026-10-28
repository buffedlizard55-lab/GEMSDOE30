# Start every GEMSDOE30 session here

1. Read README's current decision and complete `current-owner-prompt` section,
   `docs/current-run.json`, and the latest run card/plan before changing code.
2. Preserve the mandatory duplicate stop and negative results. Never rename,
   re-encode or perturb a stopped raster to claim a unique submission.
3. Reuse `gemsdoe30.holdout` and `gemsdoe30.submission`; no private evaluators/writers.
4. Freeze hypotheses, controls and buffered folds before scientific execution.
   Respect the owner's three-experiment/two-hour budget and lane allocation.
5. Distinguish stored receipts, current byte inspection, research promotion and
   organizer slot selection. Unknown is never approved. No uploader/override.
6. Keep large data/caches and quarantined predictions ignored; no credentials.

Current continuation: the 2026-10-27 registry preflight is **DUPLICATE-STOP**.
Read `docs/research/2026-10-27-registry-preflight/run-card.json` and run
`scripts/verify_registry_preflight.py` after restoring the pinned 13GEMSDOE
witness. No new lane, fit, placement, raster or slot was authorized. Under the
literal 70%-within-3-pixels rule, the pinned lattice proves a stop for any
budget of 22,164 or more distinct valid-footprint dots; a lower budget is NOT
an automatic pass and must not be chosen solely to evade the rule. The CTD-1
and FC-1 files merged in PR #54 both measurably exceed 99.9% overlap and are
stopped; their saved-prediction holdout used the full catalogue before hiding
faults and is not leakage-safe. Do not regenerate or submit either. A scientific
continuation requires an explicit assigned lane and a policy resolution, plus
fresh complete two-stage novelty checks and separate selector approval. The
2026-10-27 follow-up review is `docs/research/2026-10-27-followup-review.md`;
its ranked hypotheses are proposals only and its negative card is
`docs/research/2026-10-27-followup-run-card.json`. The README includes the
latest owner-prompt addendum and must be reread before each change.

GDX-1 is negative; 3/3 experiments exhausted. Never remove its `started.json` or
`resumed.json`, or the CSR/QPC/FFL stop/start evidence. A verifier exit 0 means
a negative receipt was reproduced, not that a slot is approved; use
`--require-promote` to require a promotion (the current preflight exits 2).
Archived novelty receipts remain unchanged; live additions are blocking UNKNOWN.

POOL-1 (parallel 2026-10-27 lane, merged after the preflight): pooled
MSDB+CSR+LiDAR mechanism beat `msdb_edge` on HOLDOUT-DTI on two seeds, but its
raster is duplicate-stopped (88.74% vs FFL1 on its frozen 394-raster registry,
which predates CTD-1/FC-1 and excludes the lattice witness); 3/3 experiments
exhausted, no TIFF published. Never remove
`docs/research/2026-10-27-pool/started.json` or rescue its quarantined raster.
Use `scripts/verify_pool_run.py` (exit 0 verifies the negative; `--require-promote`
exits 2). POOL-2 requires the same policy resolution as every other lane.
