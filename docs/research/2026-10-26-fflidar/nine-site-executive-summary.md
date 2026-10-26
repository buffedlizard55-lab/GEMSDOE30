# Executive summary — the nine priority sites, and which single file is best on each

**Scope:** GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31,
GEMSDOE32, GEMSDOE33, GEMSDOE36. **Evidence label for every score below:
`OWNER-REPORTED UNVERIFIED`** — each value comes from `docs/score-ledger.csv`
(owner task text / owner pages, 2026-10-25) and **no organizer submission-page
receipt exists in this repository for any of them**, so none is
`ORGANIZER-CONFIRMED`. The live public leaderboard snapshot read 2026-10-25
(organizer-published) had #1 = 0.4413; the owner's later brief states 0.3195 was
the then-current #1 at an earlier read. Leaderboard values cannot be attributed
to any specific file below (ledger class IR: numeric coincidence is not
attribution).

> ## FINAL FFL-1 OUTCOME — DO NOT SUBMIT (updated 2026-10-26)
>
> This session generated one newly generated, byte-distinct research TIFF,
> `gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif`
> (44,090 dots; TIFF SHA-256
> `7950607036e51faaf0258b4efeff29d75b8f12eb712aa592cd661822d3c85c07`; note:
> “FFL1: MSDB31+LiDAR17 fusion x Rayleigh gate + 300m EDGE, >2px off-cat, 44090 dots, all-finite zeros-outside”).
> Its strict whole-array validator passes (single float32 band, EPSG:32611,
> template shape/transform, every cell finite in `[0, 1]`, zero dots on or
> within 2 px of the catalogue). **It is nevertheless `negative` and must not
> be submitted:** the corrected expanded audit (pinned registry + every TIFF
> in `docs/downloads/`, candidate excluded) found **78.280789% of its dots
> within 3 px of MSDB-1v2**, above the 70% duplicate-stop threshold. The
> frozen stratified rescue was geometrically infeasible on the v3 quadrant
> holdout (zero eligible pixels in the `(2,5]` and `(5,10]` strata in every
> fold), so no production replacement was generated. **Submit nothing from
> FFL-1 and spend no weekly slot.** Full reasoning:
> [`review.md`](review.md); machine decision: [`readiness.json`](readiness.json).

## The one table that matters

| Rank | Site | Best submission on that site (do not re-submit: it is a prior file, not a new one) | Owner-reported | Dots | What it actually is (byte-verified lineage) |
|---|---|---|---|---|---|
| 1 | GEMSDOE32 | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | **0.2778** | 37,654 | H33-B2 = GEMSDOE28 r1-solo with the 2,545 dots ≤2 px from the catalogue removed (0 pixel diffs) |
| 2 | GEMSDOE36 | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 | 38,854 | H33-B2 **plus** 1,200 added dots (verified superset) — the additions *lowered* the score |
| 3 | GEMSDOE28 | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 | 37,660 | Re-thinning of the same h19-5/D2.8 family (r1 lineage) |
| 4= | GEMSDOE28 / GEMSDOE31 | `h27-4-r1-solo-d2-8-…-nan` / `h27-4-solo-d28-…-nan` (identical support) | 0.2708 | 40,199 | D2.8 with distance-1 px dots removed |
| 6 | GEMSDOE33 | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 | 41,865 | Same family + tip/step-over additions at r=3.0 |
| 7= | GEMSDOE25 / GEMSDOE30 | `dotted-h19-5-d2-8-…-nan` / `d28-poisson300m-offcat-44090-…` | 0.2600 | 44,090 | Raw D2.8 (Poisson 2.8 px thinning of h19-5, no near-catalogue pruning) |
| 9 | GEMSDOE24 | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 | 60,069 | Denser d=1.5 thinning of h19-5 (more dots, more FP mass) |
| 10 | GEMSDOE27 | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 | — | d1.5 + gap-closure additions (the additions earned ≈0 in the differential analysis) |

## Answer, per site, to "which is the best submission to submit?"

- **None of the files above is the file to submit in this session.** They are
  prior submissions; re-submitting any of them would be an exact duplicate and
  would violate the uniqueness protocol. Their role is calibration only.
- **The best *prior* file overall is GEMSDOE32's H33-B2 (0.2778, owner-reported).**
  It is best not because of new signal but because it wastes the fewest dots on
  the shared h19-5 signal: 300 m spacing, then removal of the ≤200 m
  digitisation-halo band, whose implied hit rate is ≈0.002/dot versus 0.134/dot
  for the retained set (projection in `2026-10-25-lsm/why-h33-scored-0.2778.md`).
- **There is no file to submit from this session.** The newest lane's run card
  (`docs/research/2026-10-26-fflidar/run-card.json`) is `negative`, its
  readiness says “DO NOT SUBMIT - automated gates not all passed”, and
  `scripts/verify_fflidar_run.py --require-promote` exits 2 by design. Submit
  nothing and keep the weekly slot (≤3 per 7 days, NLR rules §3.4). The FFL-1
  TIFF is retained only as a downloadable research artifact for audit.

## Why a new file can plausibly beat 0.2778 (and why most cannot)

1. All nine sites' best files are one family. Their implied hidden-truth
   coverage is the same ≈40.5%; they differ only in wasted dots. Pruning alone
   caps at ≈0.46 even with an oracle filter — practical gains must come from a
   better-localised belief, i.e. new physical features (this lane: corrected
   MSDB physics + 1 m LiDAR scarps) and better allocation (distance strata).
2. Near-catalogue placement is empirically barren (≤2 px band, gap closure,
   and the GEMSDOE36 PINN additions all earned ≤ random). Yet the previous
   in-repo best raster (MSDB-1v2) still placed 18.2% of dots ≤2 px from the
   catalogue and only 9.6% beyond 30 px. Reallocation is untested headroom.
3. Reaching 0.30 / 0.3195 / 0.4413 at 37–44k dots requires ≈0.145 / 0.155 /
   0.218 hits per dot versus H33's 0.134 (projection) — a +8% / +16% / +63%
   localisation improvement, not a new pruning trick.

## What FFL-1 actually found

All FFL numbers below are **HOLDOUT-DTI** (evaluator
`component-holdout-v3-blockstats-20261025`; 60,988 withheld positives; 371
geographic blocks; 2,000 paired bootstrap draws), never organizer scores:

| Seed | `fusion_edge` | Same-run `msdb_edge` | Paired Δ [95% CI] | Interpretation |
|---:|---:|---:|---:|---|
| 3051 (Exp. 1) | 0.182417 [0.168230, 0.196433] | 0.175639 [0.161471, 0.189566] | +0.006779 [−0.000067, +0.012888] | Point gain; frozen CI gate missed by 0.000067 |
| 3063 (Amendment-A1 confirmation) | 0.183949 [0.169419, 0.197874] | 0.173427 [0.159043, 0.187952] | +0.010522 [+0.004182, +0.016362] | Fresh-seed paired gate passed |

The LiDAR/MSDB feature fusion is therefore supported on the catalogue proxy,
and 54 features × 4 folds produced zero leakage-canary alarms (max
either-direction AUC 0.6667). But the production `fusion_edge` dots failed the
expanded uniqueness audit (78.280789% within 3 px of MSDB-1v2), and the frozen
distance-stratified alternative could not be scored on quadrant folds. **The
feature result is positive; the submission result is negative.** See
[`review.md`](review.md) for the full PhD-level analysis and
[`readiness.json`](readiness.json) for the machine gates.

## Irregularities flagged from this audit (full ledger: `docs/irregularities.md`)

- Every fleet score is owner-reported; two ledger rows conflict with owner
  pages that say "unscored/not slot-approved" (GEMSDOE25). Treat all as
  unverified until an organizer receipt is supplied.
- GEMSDOE31's best file is byte-identical in support to GEMSDOE28's r1-solo:
  it is not an independent result.
- GEMSDOE36's file is a superset of GEMSDOE32's H33: likewise not independent.
- The README's documented command `restore_public_mirrors.py --include-extra`
  is rejected by the script (no such flag); extra mirrors restore via
  `--pins docs/research/mirror-pins-extra.json` (logged as IR-FFL-04;
  IR-30-087 was already assigned to the G30-LSM dot-stage-timing lesson).
