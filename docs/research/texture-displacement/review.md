# TDX-1 scientific review and autonomous submission decision

**Date:** 2026-10-25. **Verdict: NEGATIVE — DO NOT SUBMIT.**

A **newly generated** single-band GeoTIFF is now available:
[`gems30-TDX1-44090-20261025-5fc508ea81ac.tif`](../../downloads/gems30-TDX1-44090-20261025-5fc508ea81ac.tif).
Download is appropriate for reproducibility and research. Competition upload is **not approved**.
It is not a renamed, pruned, re-encoded or unioned historical submission. The candidate
uses a new six-feature model fit to physical data and visible training labels; historical
raster values enter only the duplicate audit. A changed hash alone would not prove novelty.

- [Executive submission guide](../../../executive-summary.html)
- [Machine-adjudicated readiness gates](readiness.json)
- [Final JSON run card](run-card.json)
- [Frozen hypotheses / plan](preregistration.md)
- [Full experiment, canaries and bootstrap sufficient statistics](results.json)
- [Exact TIFF validation](validation.json)
- [Three-pass verification / reliability journal](verification.md)
- [119 unverified owner-reported submission claims](owner-claims.csv)

## 1. What the historical H33 result establishes — and what it does not

**Quarantined historical claim, OWNER-REPORTED / UNVERIFIED:** the prompt associates
`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` with **0.2778**. This is neither a
new HOLDOUT-DTI measurement nor ORGANIZER-CONFIRMED: no submission-page receipt
binding the name, bytes and result was available. Likewise, the prompt's competing
current-leader claims are not used as a verified live leaderboard.

The earlier [byte-derived reconstruction](../2026-10-25/recipe-reconstruction.json),
rerunnable with `scripts/audit_priority_recipes.py`, establishes that H33's positive
support is reproduced **exactly** by retaining GEMSDOE28 base dots whose Euclidean
catalogue distance exceeds two pixels. The base has **40,199** dots, H33 **37,654**,
and support mismatch is **zero** (raster diagnostics, not performance scores).
GEMSDOE25/GEMSDOE30 and GEMSDOE28/GEMSDOE31 also share identical in-footprint
values in those named historical references. See the [nine-site review](../2026-10-25/review.md)
and [pinned educational duplicate audit](../h33-historical-duplicate-audit.json).

The [GEMSDOE32 source discussion](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/README.md#L292-L320)
was retrieved again through GitHub in this session. It describes small catalogue-flank
pruning and explicitly identifies its much larger live-mirror number as an unreliable
extrapolation outside calibration. A calibrated mirror, drift correction or projection
is **not** an organizer score and is not admitted as one here.

For weighted truth credit `T`, false-positive mass `F`, truth count `G`, and the
specified weights, the shared evaluator uses:

```text
DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon)
```

Credit at a truth pixel is the **maximum** nearby predicted value times the triangular
300 m kernel. Multiple nearby predictions do not add unrestricted credit to one truth
pixel. Pruning can therefore improve DTI if its FP savings outweigh lost coverage.
This is a plausible mathematical explanation, **not causal identification** of what
happened on hidden expert faults. Buffer pruning can also erase genuine short splays.

**Can a unique method exceed the historical claim?** In principle yes; no verified
experiment here establishes that it will. Extrapolating a leaderboard response from
those closely related files is especially weak evidence. TDX-1 tests new information
instead of treating another thinning setting as scientific independence.

A shared-documentation defect was also corrected: increasing a **common amplitude**
on a fixed probability shape improves the metric until a value reaches one. It does
**not** prove that setting every nonzero value independently to one is optimal.
A low-confidence false positive can gain penalty without adding coverage. A new
regression test supplies that counterexample. Binary dots remain a preregistered
empirical emitter, not a theorem about all competitive predictions.

## 2. Research lane, sources and physical signature

The prior session's first unimplemented proposal was magnetic texture displacement.
This session continues **only that mechanism**: profiles on opposite sides of a
smoothed gravity-gradient normal, matched at nonzero tangential lags at two scales.
The four ranked prospective hypotheses, exact bands, non-fault processes, differences
from local methods, implementation costs and off-catalogue rationale were written in
[the plan](preregistration.md) before construction/fitting/evaluation.

The prompt refers to an assigned single-method paragraph but does not identify one.
This is an autonomous **research continuation**, not a fabricated external allocation;
readiness records lane verification as unknown. No additional geological hypothesis
or hyperparameter sweep was run. There were **two executions of the same fixed
hypothesis/three arms**, including one preregistered bug correction: approximately
**401 seconds total**, **205 seconds for the corrective execution** (runtime, not scores).
The first negative run is frozen at commit `361b128f9951191378a3a07b06a5d76ce1933836`;
[the retirement receipt](correction-v1-retirement.json) links its exact full commit.
The current plan records the post-result amendment before the corrective construction.
This is not a new independent geological method or fresh independent confirmation.

| Input | Verified local band | Interpretation source | Evidence boundary |
|---|---:|---|---|
| `mag_anom` | 1 | [Official reference notebook, cell 5](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) | Described as magnetic anomaly; original archive construction not independently authenticated here |
| `rtp` | 2 | Same official notebook and local band tags | Reduced-to-pole magnetic field; related to band 1, **not an independent second survey** |
| `iso_grav_anom` | 13 | Same official notebook and local band tags | Isostatic gravity anomaly; an edge is not uniquely a fault |

All inputs came from the existing hash-pinned cached feature stack. No new external
source is required for these screens or represented as freshly available. The raw
source and preparation signatures match the existing pins. [Environment, source hash
and band tags](environment-and-sources.json); [derived-cache receipt](feature-receipt.json).
The [full-cell cache verification](cache-verification.json) freshly confirms every
prepared feature/label/mask cell equals the pinned raw-source derivation, not merely
a claimed preparation signature.
Mirror hashes establish consistency, not organizer origin, licensing certification or
absence of all possible upstream geological-model priors.

**Primary non-fault mimic:** an intrusive lithologic contact. Other serious mimics are
magnetic source-depth changes, survey/gridding seams and unrelated sources at different
depths. At this grid spacing the registered lags are signal-processing hypotheses, not
validated measurements of fault slip. A correlated magnetic low/offset is not evidence
by itself of fluid temperature, permeability, a vent, or an economic geothermal resource.

### Guard-bound defect found and corrected before the final file

The initial code called 16 px conservative, overlooking diagonal corners of the
separable Gaussian's **square** support. The analytic upper bound is
`sqrt(2)*6 + sqrt(3^2+6^2) + sqrt(2) = 16.6077 px`, including bilinear interpolation.
The corrected transform and training guard therefore both use **17 px**. This is
an analytic implementation correction, not a parameter selected to improve a score.
The original negative result, plan, exact sources and hash are retained at the linked
commit; the old unpublished same-family download has been retired, not represented
as another novel method. Current metrics and download all refer to the corrected run.
A regression now checks the diagonal reach and finite-support exclusion.

## 3. Hide-and-recover protocol actually executed

- **Evaluator:** `component-holdout-v3-blockstats-20261025`.
- **Protocol:** `buffered-quadrant-whole-components-v1-20261025`.
- Four coarse geographic quadrants. Whole 8-connected catalogue components are assigned
  by centroid and are hidden exactly once. These are raster-connected segments, not
  a claim to have reconstructed the original vector database's named fault records.
- A fold scores its quadrant plus a 300 m halo around complete withheld components;
  segments crossing a quadrant edge are never cut. Whole other components touching
  a 17 px training guard are removed from the visible catalogue. Those guard components'
  **exact pixels**, not a blanket neighborhood, are unscored. Remaining visible faults
  are masked pixel-exactly by the shared evaluator.
- Training pixels lie outside the 17 px regional guard. The physical transform has
  conservatively bounded support within that guard. No catalogue-distance/direction
  input is used; held-out labels never enter a fold's training targets or statistics.
- A geographic negative/halo pixel may participate in multiple regional trials. This
  is **not advertised as a disjoint OOF mosaic**. All **60,988 withheld positive pixels**
  are counted once across the four trials. Exact active dot budgets are matched among
  all three arms in every fold; there are no pool-capacity shortfalls.
- The shared exact triangular-kernel evaluator retains interactions across bootstrap
  tile edges within each fold. It pools TP/FP/truth sufficient statistics, **not** mean
  fold DTI. Truth-empty blocks retain all FP mass.
- Paired uncertainty uses **371 geographic blocks**, each **12.8 km** on a side,
  aggregated across folds, with **2,000** bootstrap draws. Intervals are conditional
  catalogue-proxy diagnostics; they do not quantify uncertainty on hidden expert faults.

| Regional trial | Whole withheld components | Withheld positives | Active dots, each arm |
|---|---:|---:|---:|
| NW / fold 0 | 1,822 | 29,340 | 20,902 |
| NE / fold 1 | 684 | 12,566 | 11,661 |
| SW / fold 2 | 375 | 9,403 | 4,821 |
| SE / fold 3 | 318 | 9,679 | 6,728 |

These are counts, not scores. Tiny regional area overlaps mean the sum of regional
budgets need not equal the final full-footprint budget of **44,090** dots.

## 4. Results — all performance values below are HOLDOUT-DTI

**Common evaluator/protocol above; 60,988 withheld positives; paired spatial-block 95% CIs.**
No row is a competition result, projection or ORGANIZER-CONFIRMED score.

| Fixed arm | HOLDOUT-DTI | 95% CI | Interpretation |
|---|---:|---:|---|
| `physics3` — raw magnetic anomaly, RTP, gravity | 0.064591 | [0.055373, 0.074301] | Physics-input ablation |
| `tdx6` — those inputs plus registered displacement features | **0.072844** | **[0.063483, 0.083061]** | Fixed candidate; no selection among arms |
| `core19` — rerun existing 19-band HGB recipe | **0.139821** | **[0.124178, 0.155905]** | Stronger same-protocol recipe comparator; not a claimed historical-best reproduction |

| Paired difference, still HOLDOUT-DTI | Value | Paired 95% CI |
|---|---:|---:|
| `tdx6 − physics3` | +0.008253 | [+0.004208, +0.012197] |
| `tdx6 − core19` | **−0.066977** | **[−0.085747, −0.048300]** |

**Scientific conclusion:** the derived features add local catalogue-recovery information
beyond the three raw fields, but this restricted model is decisively inferior to the
stronger core-stack comparator. The result does not justify discarding other modalities
or spending a weekly slot. Nor does the positive ablation uniquely verify physical fault
displacement: an edge/texture-complexity interaction can improve prediction without
matching the hypothesized causal mechanism. A matched zero-lag / phase-scrambled control
is a necessary future falsification, not an experiment silently added after this result.

The historical best UNet checkpoints are not in this checkout. Its older holdout numbers
cannot be used as a comparable corrected-evaluator best. This missing rerun is an
additional unknown gate, **not concealed by calling `core19` the historical best**.

### Leakage canaries — AUC diagnostics, not DTI

Every one of the **22 raw/derived inputs** was tested alone in each fold, using both
bidirectional raw-value AUC and a training-only univariate HGB. There are **no AUC
alarms above 0.90**; the largest recorded canary is approximately **0.643433**.
A low AUC is not proof of no leakage or complete source independence. All per-feature,
per-fold values and test sample sizes are retained in [results.json](results.json).

## 5. Novelty — exact diagnostics, not performance scores

The inventory expanded from one reference per site to **119 published TIFF source
files** at nine immutable main-branch snapshots. After byte-identity deduplication,
**104 unique aligned files** were compared. One toy format-test raster was excluded
because it is not on the competition grid. All aliases, Git blob identities, SHA-256
hashes, commit/tree identities and exclusion reasons are in [registry.json](registry.json).

Both the full continuous candidate surface **before placement** and the final dots
were tested. No registry values were used to alter or avoid predictions.

| Diagnostic | Maximum over observed registry | Stop threshold |
|---|---:|---:|
| Surface full-footprint Spearman | 0.042623 | >0.90 |
| Final-dot full-footprint Spearman | 0.013575 | >0.90 |
| Candidate dots within Euclidean 3 px of any one reference | 40.4922% | >70% |

[Surface audit](novelty-surface.json) · [Final-dot audit](novelty-dots.json).

**Concurrent-main addendum:** main advanced to `7f3f4c7` with four TIFFs from
H-CC1, residual-ridge and G30-S19 lanes. Both saved TDX states were checked against
all four **after they arrived**, with no refit or placement changes. This is additive
late evidence, not a claim that these references existed before original placement.
[Exact late registry](registry-parallel-addendum.json), [surface](novelty-parallel-surface.json),
[dots](novelty-parallel-dots.json). **108 total observed comparisons:** maximum surface
Spearman **0.053133**, final-dot Spearman **0.013710**, maximum 3px overlap still
**40.4922%**. No observed duplicate stop fired; complete parallel/original-surface
coverage is still unknown. The run card preserves the frozen-snapshot summaries
and separately records the combined evidence; automated readiness uses all 108.
New or removed local references without a matching addendum fail verification.

Positive support of a dense surface is not treated as placed dots; the meaningful
pre-placement statistic is rank correlation. Final support receives both tests.
The file is distinct **against this observed inventory**, not certified globally unique.
The registry explicitly remains **incomplete for all parallel sessions and original
continuous surfaces**. Passing the observed comparisons does not turn this into approval.

## 6. File contract and the historical range rejection

The shared writer rejected no in-footprint values and performed no clipping or repair.
The output was reopened with the shared validator: one float32 band; EPSG:32611;
shape **3,730 × 3,292**; exact template affine transform; **no NaN/Inf inside**;
all in-footprint values are **0 or 1**; **zero positive catalogue pixels**; NaN nodata
outside the scoring footprint. [Validator output](validation.json).

```text
SHA-256 9556e3ddd8ea7658ca510ab02d5b5304ac4c3332c54e7f86df5a24769bd03cdb
Name    gems30-TDX1-44090-20261025-5fc508ea81ac
Note    TDX1 gravity-normal magnetic texture lag; 6-feature HGB; negative research result, NOT approved for competition upload.
```

The portal's earlier `Predicted values must be in range [0, 1]` rejection cannot be
causally diagnosed without the exact uploaded bytes. The new artifact satisfies the
repository's documented **in-footprint** probability contract. Its published-format
NaN nodata outside is intentionally not the nonstandard whole-array-finite diagnostic.
Neither the reference notebook's omission of a nodata argument nor an owner's reported
successful zero-outside submission proves current private-validator behavior. No
"range-error immune" or organizer-acceptance guarantee is made.

A legacy conversion bug found in review was fixed once in the shared writer: diagnostic
conversion previously checked shape/transform but not source CRS. It now rejects a
CRS mismatch. The shared writer also enforces a nonblank run name and note length.

## 7. Claim-by-claim evidence and access limits

| Claim | Evidence / review link | Class and limitation |
|---|---|---|
| Layer meanings and source grid | [Official reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb), cells 5–6 | OFFICIAL implementation, freshly read via GitHub; not a private metric implementation |
| Reference uses Tversky training and writes georeferenced TIFF | Same notebook, cells 16, 19 | OFFICIAL code; training loss is not the distance-weighted evaluator |
| H33 pruning recipe | [Pinned owner source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/README.md#L292-L320) + [byte reconstruction](../2026-10-25/recipe-reconstruction.json) | OWNER source + local raster measurement; no organizer score attribution |
| New method and no copying | [Frozen plan](preregistration.md), [new transform](../../../src/gemsdoe30/texture.py), [runner](../../../scripts/run_texture_displacement.py) | Inspectable code and new fit; not global patent/scientific novelty |
| Performance / CIs / canaries | [Results](results.json), [shared holdout](../../../src/gemsdoe30/holdout.py) | HOLDOUT-DTI / AUC diagnostics only, catalogue proxy |
| Novelty against observed files | [Registry](registry.json), two comparison receipts | Local exact diagnostics; complete parallel coverage unknown |
| Format/range/grid | [Validation](validation.json), [shared writer](../../../src/gemsdoe30/submission.py) | Local public-contract check, not organizer approval |
| Current leaderboard, slot cap and acceptance | [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), [submission/data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Not freshly accessible; do not invent receipts, slots or current scores |
| Written rules | [Official PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [historical review](../official-rules-review-2026-10-03.md) | Manual-review links; PDF not freshly fetched this session |
| GeoDAWN / geothermal context | [USGS release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [GDR 1391](https://gdr.openei.org/submissions/1391), [INGENIOUS](https://gbcge.org/current-projects/ingenious/) | Official-source review links, not newly retrieved literature or newly obtainable data claims |

This environment permits GitHub and package-registry network access, not DrivenData,
USGS/GDR/NLR web hosts. No credential request, login bypass, leaderboard scraping,
competition upload or submission-slot selection was performed.

## 8. Reproduction, automated inspection and next-session priorities

Python **3.11+**, CPU; no GPU is required for this fixed HGB experiment. GPU availability
is a separate limitation for larger legacy UNet training. Large inputs/caches stay ignored.

```bash
python -m venv .venv
.venv/bin/pip install -e '.[research,test]' -c requirements-tdx1.txt
.venv/bin/python scripts/restore_public_mirrors.py
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/verify_prepared_cache.py
.venv/bin/python scripts/sync_priority_registry.py --restore-only
.venv/bin/python scripts/run_texture_displacement.py --max-seconds 5400
.venv/bin/python scripts/verify_current_run.py --write
.venv/bin/python scripts/build_research_site.py
.venv/bin/python -m pytest -q
# Exit 2 is EXPECTED here: a negative result is not promotable.
.venv/bin/python scripts/verify_current_run.py --require-promote
```

For exact historical reproduction, preserve the committed registry snapshots rather
than treating a future live inventory refresh as the same inventory. A refresh can
correctly detect a new duplicate, including a self-reference after this artifact is
published; stop rather than hiding it. The frozen experiment result is not silently
rewritten by the status feed or CI.

**Next priorities, not implemented experiments:**

1. Obtain a programmatically shared, complete parallel-run registry and an identifiable
   lane allocation; missing original surfaces remain an explicit blocker.
2. Preserve this negative result. Before another trial, preregister a same-feature-count
   zero-lag / phase-scrambled control to distinguish displacement correspondence from
   generic edge/complexity features. The already inspected folds are not a fresh
   confirmation set just because the seed changes.
3. If this mechanism survives that falsification, test whether its information adds
   to the full core stack, rather than replacing other modalities with a weaker model.
   This would be a **new** preregistered experiment, not a post-hoc promoted arm here.
4. Restore or retrain the historical best with source/fold-bound checkpoints using the
   same corrected evaluator and protocol. Do not compare incompatible archived metrics.
5. Keep the separate slot selector closed until its required current portal evidence
   and entrant eligibility/rules obligations are available. Automated project inspection
   is implemented; it cannot fabricate organizer receipts or legal eligibility.

**Maximize P(Win):** reject an inferior candidate and conserve the weekly cap.
**Own the Outcome:** deliver the new TIFF, reproducible negative evidence, corrected
shared tooling and machine-readable decision instead of outsourcing inspection.


## 9. Three progressively deeper review passes

[The complete journal](verification.md) separates implementation/execution,
bug discovery/correction, and the full requirements/reliability check. Latest local
suite: **180 passed, 5 optional torch tests skipped, 7 subtests passed**; two
rasterio/Affine deprecation warnings. Ordinary exact-artifact verification and
site staleness checks passed; promotion-required verification correctly exited 2.
Desktop/mobile automated downloads both matched the corrected raster SHA-256.
PR, CI and deployment results are reported only once independently observed.


### Concurrent lanes and source claims are preserved, not selected

The merge retains all three peer lanes' code, rasters and reports, the earlier
worktree-readiness follow-up, and all score-ledger rows. G30-S19's `promote` is
that lane's reported research verdict under a different, spatially interleaved
v2 protocol and FP-conditioned uncertainty—not a head-to-head win against this
v3 geographic trial, an organizer score or a slot selected here. H-CC1 and the
residual-ridge negative findings remain visible too. The landing page and status
feed link these records without re-adjudicating or hiding them.

Peer sessions also record a newer official-leaderboard read at 0.4413. This lane
has not independently fetched that host. A newer leaderboard-row claim would not
authenticate the unrelated historical G32 mirror estimate of the same number or
bind any owner TIFF to an organizer submission result. No current leader or higher
hidden-test forecast is asserted by TDX-1.
