# TDX-C2 — full-stack displacement falsification and mandatory duplicate stop

**2026-10-25 · NEGATIVE · NO NEW UNIQUE/APPROVED SUBMISSION TIFF.**

The fixed candidate was generated internally, but **79.0905%** of its dots were
within three pixels of a frozen G30-S19 reference. That exceeds the owner's 70%
lane limit. The final-dot audit stopped the run. No further experiment, parameter
change, replacement arm, or publication of the candidate followed. Its different
SHA-256 is **not** evidence of an independent strategy. The retained TDX-1 download
is explicitly an archive from the previous session, not a newly generated submission.

- [Latest JSON run card](run-card.json) · [mandatory stop](duplicate-stop.json)
- [Automated readiness](readiness.json) · [recorded local validator](validation.json)
- [Frozen hypotheses/plan](preregistration.md) · [full results and canaries](results.json)
- [Three-pass journal](verification.md)
- [Website](../../../index.html) · [executive submission guide](../../../executive-summary.html)

## 1. Answering the historical H33 question without inventing a score

The owner's H33 attribution **0.2778** is a quarantined **OWNER-REPORTED,
UNVERIFIED historical claim**, not HOLDOUT-DTI and not ORGANIZER-CONFIRMED. No
submission-page receipt binds that result to the supplied file. The conflicting
leaderboard values in the prompt also do not establish today's leaderboard.
This session cannot reach DrivenData/NLR/USGS/GDR hosts and does not pretend to
have freshly verified those pages. [All supplied historical claims](../texture-displacement/owner-claims.csv)
remain explicitly unverified; no projection becomes a score.

What was actually verified again, from exact raster bytes:

- GEMSDOE28 base support: **40,199 dots**; H33: **37,654 dots**.
- H33 support equals the GEMSDOE28 support after deleting every dot at Euclidean
  catalogue distance ≤2 pixels: **zero mismatching pixels**.
- GEMSDOE25/GEMSDOE30 selected references have identical in-footprint values.
- GEMSDOE28/GEMSDOE31 selected references have identical in-footprint values.

These are **raster diagnostics, not performance scores**. The educational
[reconstruction receipt](../2026-10-25/recipe-reconstruction.json) was rerun with
`scripts/audit_priority_recipes.py`; no historical TIFF was copied into new predictions.

For weighted truth credit T, false-positive mass F, truth count G, and epsilon:

```text
DTI = T / (T + .2 F + .8 (G - T) + epsilon)
    = T / (.2 T + .2 F + .8 G + epsilon).
```

Truth credit is a **maximum** of nearby probabilities times the 300 m triangular
kernel. Redundant nearby dots do not contribute unlimited additional credit.
Ignoring epsilon, deleting support that loses ΔT truth credit and saves ΔF penalty
improves DTI precisely when `.2 T ΔF > (.2 F + .8 G) ΔT`. This explains why
well-chosen thinning/pruning *can* help; it does not prove the hidden-test cause.
Mask-adjacent pruning can also erase genuine new splays and extensions. It is not
an independent geological hypothesis, and repeatedly trying related emitters is
not strong evidence of generalization.

**Can we exceed the claimed historical result?** In principle, a genuinely better
belief surface could. Neither the historical correlation nor this continuation
establishes it. This candidate did not even satisfy its matched proxy improvement
or novelty gates; it must not use a weekly slot.

## 2. What was preregistered and what was not

Before implementation, [four ranked prospective hypotheses](preregistration.md)
named exact layers, physical transforms, off-catalogue rationale, differences from
local code, non-fault mimics and qualitative utility/cost. Only hypothesis 1 ran:
**conditional displacement specificity beyond the full core feature stack**.
The other three—signed-lag continuity, reciprocal matching, and off-edge
localization—remain proposals, not results or alternative candidates selected here.
All use cached bands, so no unverified external download was represented as viable.

This continues the prior recorded recommendation to add matched zero-lag and
phase controls. The prompt again supplies no identifiable assigned-lane paragraph;
this is an **autonomous TDX research continuation**, not a claimed external lane
assignment. Once it collided with the habitat lane, it stopped.

The three added candidate inputs are the original two-scale magnetic-profile lag
gains and their gravity-weighted consensus. They are appended to all 19 cached
core bands. No historical predictions or catalogue geometry enter the transform.
No geological scales, lags, model settings, density or emitter were tuned.

Four fixed arms, with identical training coordinates and targets:

1. `core19`: existing 19-band HGB recipe.
2. `tdx22`: fixed candidate, core19 plus three displacement features.
3. `zero22`: core19 plus matched positive zero-lag coherence features.
4. `phase22`: core19 plus lag-gain features after deterministic local Fourier
   phase scrambling of right-flank profiles. DC and power spectrum are retained;
   no physical sample crosses a region boundary. This is **one matched control**,
   not a simulated null distribution.

HGB: 120 iterations, learning rate .1, 31 leaves, no early stopping; seed 3070+fold;
all visible training positives and six sampled negatives per positive. The final
refit always used `tdx22`; the phase control's point estimate did not select it.
A lazy channel view reuses cached arrays with the existing sampler/block predictor,
without materializing an additional gigabyte-scale feature raster.

## 3. Sources actually re-read and provenance boundaries

The official reference repository was freshly retrieved at commit
[`aebe92f7…`](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b).
Its notebook's saved cell-5 band metadata agrees with the local cached grid:
EPSG:32611, 3,730×3,292, 100 m pixels, 19 float32 bands. Bands 1, 2 and 13 are
magnetic anomaly, RTP and isostatic gravity anomaly. The same notebook's training
configuration specifies alpha .2/beta .8. The exact [source hashes/excerpts](official-source-audit.json)
are retained; the notebook's Tversky training loss is not falsely called an official
implementation of the distance-weighted evaluator.

Prepared arrays were checked **cell-for-cell** against hash-pinned raw mirrors,
not accepted on manifest claims alone: [cache verification](cache-verification.json).
Original TDX-1 feature arrays were reconstructed under their existing pinned
transform and verified hashes; new controls have a separate [cache receipt](feature-receipt.json).
Input consistency is not organizer authentication, permission to redistribute
competition training data, or proof of absence of upstream geophysical-model priors.
Large inputs, arrays and output TIFFs stay ignored and are not served by Pages.

Primary named mimic: **intrusive lithologic contact**. Survey/gridding seams,
source-depth changes and repeated lithologic fabric are additional mimics. RTP
and magnetic anomaly are related, not independent surveys. The inferred lags are
signal-processing signatures, not calibrated fault-slip estimates.

The official [problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf),
[USGS GeoDAWN release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
and [GDR INGENIOUS record](https://gdr.openei.org/submissions/1391) are review links,
**not freshly accessible/verified sources in this session**. No new external data
were needed for the four proposed tests. Prior repository access/leaderboard claims
retain their original dates and do not become this session's current verification.

## 4. Buffered hide-and-recover results

**Every measured performance number in this section is HOLDOUT-DTI**, evaluator
`component-holdout-v3-blockstats-20261025`, protocol
`buffered-quadrant-whole-components-v1-20261025`, **60,988 withheld positive pixels**,
95% paired spatial-bootstrap intervals. These are catalogue-recovery proxies,
not competition scores, forecasts, or fresh independent confirmation.

| Fixed arm | HOLDOUT-DTI | 95% CI |
|---|---:|---|
| core19 | 0.139821 | [0.124178, 0.155905] |
| **tdx22 candidate** | **0.136061** | **[0.120028, 0.152034]** |
| zero22 | 0.136713 | [0.122039, 0.151906] |
| phase22 | 0.140185 | [0.124203, 0.155878] |

| Paired HOLDOUT-DTI difference, same evaluator/positives | Difference | 95% CI |
|---|---:|---|
| candidate − core19 | −0.003760 | [−0.008176, 0.000704] |
| candidate − zero22 | −0.000652 | [−0.006727, 0.005426] |
| candidate − phase22 | −0.004124 | [−0.009306, 0.001013] |

All paired intervals cross zero. This fails the required positive lower-bound
improvement gate; it does **not** demonstrate statistically significant inferiority
or prove that real buried faults never displace magnetic fabric. It specifically
undercuts attributing the earlier restricted-model gain to incremental physical
information beyond core19. Additional nonlinear feature capacity can improve a
three-band ablation without improving the stronger full-stack model.

The core19 sufficient statistics and CI **exactly reproduce** the previous TDX-1
comparator, a useful engineering check, not independent replication. The same
geographic folds have already been inspected; a new seed is not an untouched test.

Construction/evaluation diagnostics (not scores):

- Four whole 8-connected component regional trials; every catalogue positive hidden
  exactly once. Entire neighboring components touching a **17 px** guard removed
  from visible labels/training. Remaining visible faults masked **pixel-exactly**.
- No catalogue-derived feature is used. Every normalizer/imputer is training-only.
- 300 m triangular max-credit kernel, alpha .2/beta .8. Pooled TP/FP/truth sufficient
  statistics, not mean fold DTI; cross-block kernel credit retained.
- **371** geographic 128 px blocks aggregated across folds; **2,000** paired bootstrap
  draws, seed 3071. Intervals are conditional on this biased catalogue proxy/model fit.
- Equal realized dot counts in every arm: **20,902 / 11,661 / 4,821 / 6,728** by fold,
  proportional to a frozen full-footprint budget of **44,090**, 3 px Poisson spacing.
  No capacity shortfall; no post-result emitter optimization.
- **28 inputs × 4 folds = 112 individual canary checks**. Bidirectional raw and
  training-only univariate HGB AUCs were tested; maximum alarm-direction AUC
  **0.643433**, below .90. Low AUC does not establish absence of all leakage.

## 5. Nine-site review, novelty failure and exact stopped identity

The fresh registry inventories **179 published source TIFFs**, deduplicated to
**164 aligned byte sequences**, with **one unaligned exclusion**, at immutable
main-branch snapshots of all nine priority repositories. All local published
TIFFs were already covered by those identities. No global parallel-registry or
original-continuous-surface completeness is inferred from that inventory.

- [Full pinned inventory](registry.json) · [fresh README source review](priority-site-review.json)
- [Nine educational reference raster/format checks](historical-reference-audit.json)
- [Continuous surface comparisons before placement](novelty-surface.json)
- [Final dot comparisons](novelty-dots.json)

Novelty diagnostics, **not performance scores**:

| Stage | Max full-footprint Spearman | Candidate dots ≤3 px from a reference | Decision |
|---|---:|---:|---|
| Continuous surface, before placement | 0.156573 | Not a dot set | Observed correlation threshold not crossed; overall coverage incomplete |
| Final dots | 0.063833 | **79.090497%** | **DUPLICATE-STOP** |

The overlap is against the existing 60,000-dot G30-S19 habitat output, including
its two encoding aliases. Low exact-pixel rank correlation is compatible with
high nearby-dot overlap; both protocol checks are necessary. No dots were removed,
shifted or randomized after this discovery.

Stopped name: `gems30-TDXC2-44090-20261025-d87627b24504`.

Note (≤140 characters):

> TDX-C2 core19 plus magnetic profile lag; matched zero-lag/phase controls; research only, NOT approved for competition upload.

Stopped raster SHA-256:
`af499375cec73f42f98f398370b390e96c3d3b23943477eb1f613570baa98e0d`.

It passed the shared writer's contract and an independent post-stop local file
reopen: no NaN inside, values [0,1], one float32 band, exact CRS/shape/transform,
NaN nodata outside, zero positive catalogue pixels. **Format validity did not
rescue the novelty/performance failures.** The TIFF is deliberately not copied
to `docs/downloads/`; the preview server blocks `outputs/`. CI verifies immutable
receipts and recomputes statistics; it does not claim to reopen absent private bytes.
Local `--inspect-quarantine` additionally reopens ignored bytes if present.

One experiment/four fixed arms; **373 seconds** UTC start-to-stop (one-second
precision). A post-stop audit-only finalizer recorded the run card/validator; it
neither refit nor changed any predictions. Original executed code is frozen at
commit `79d1be92e578f4e555fe5a5ae8d273728221c8af`; later changes fix negative-result
logging/no-overwrite safety, not scientific results. No second experiment ran.

## 6. Automation, limitations and next-session priorities

The latest attempt and retained archive use separate pointers/identities. Both
`--require-promote` checks exit **2**. Format, experiment, duplicate and uncertainty
verification is automated; there is no human-inspector override or uploader.
Current organizer allowance, eligibility, deadline and acceptance remain unverified,
so no competition slot can be selected by this system.

The previous range-error file is unidentified. Our shared writer rejects out-of-range
inside values instead of clipping them. NaN outside follows the documented local
contract. Several historical zero-outside references fail that contract, despite
valid inside values; that does not prove what the private portal accepts. No
range-error-immunity claim is made.

**Next session, in order:**

1. Preserve this negative result and its duplicate stop. Do not re-encode it or use
   the higher point-estimate control as an unvalidated replacement submission.
2. Programmatically synchronize external lane assignments and the complete parallel
   raster/**continuous-surface** registry; public dot rasters cannot substitute for
   unavailable original surfaces. Unknown must remain unknown.
3. Recover a current-best model checkpoint and rerun it under exactly matched folds,
   mask, counts and shared evaluator. Heterogeneous archived holdout results cannot
   establish a comparable current best.
4. Reserve genuinely untouched geographic faults/regions or nested spatial evaluation
   before further hypothesis tuning; do not present repeated inspected folds as
   independent validation.
5. Preregister a distinct physical mechanism with matched controls. No viable new
   external-data proposal should be claimed until its free official source is
   obtainable and its provenance/use terms are verified.
6. Fault discovery is not vent discovery. Thermal, permeability and flow evidence
   would be needed before any geothermal-vent claim. Cached fault labels alone do
   not supply those observations.

**Own the Outcome:** a negative experiment and mandatory stop are deliverables.
**Maximize P(Win):** preserve limited organizer feedback for unique, reproducible,
validated improvements instead of manufacturing a submission-ready label.
