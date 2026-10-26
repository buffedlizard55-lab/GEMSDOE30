# FFL-1 review — MSDB × 1 m LiDAR fusion, far-field allocation, and a dot-stage duplicate-stop

**Final machine verdict: `negative` — DO NOT SUBMIT.**
**No competition slot was selected or spent. No organizer score exists for this lane.**

The retained TIFF is a newly generated, byte-distinct research artifact, not a
promotable submission:

- File: [`gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif`](gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif)
- Submission name: `gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3`
- Note (107/140 characters): “FFL1: MSDB31+LiDAR17 fusion x Rayleigh gate + 300m EDGE, >2px off-cat, 44090 dots, all-finite zeros-outside”
- TIFF SHA-256: `7950607036e51faaf0258b4efeff29d75b8f12eb712aa592cd661822d3c85c07`
- Prediction-values SHA-256: `eacd73e854a31ad7c64f2e3fa2171ba7442068cafb26d08efdd22b8d239f2908`
- Machine receipts: [run card](run-card.json) · [readiness](readiness.json) ·
  [strict validation](validation.json) · [expanded dot audit](novelty-dots-expanded.json)

The file passes the strict all-cell finite `[0, 1]` check. It nevertheless must
not be uploaded: **78.280789% of its dots lie within 3 px of the MSDB-1v2
raster**, above the owner's 70% duplicate-stop threshold. Its continuous
surface is not a near-copy (maximum Spearman `0.112546` against that raster in
the expanded audit); the failure occurs at dot placement. This is precisely
why surface correlation alone is not a sufficient uniqueness test.

---

## 1. Executive answer

### 1.1 What was tested?

FFL-1 asked whether augmenting the corrected 31-feature MSDB stationary
discontinuity representation with 17 one-metre LiDAR scarp-morphology layers
improves recovery of withheld catalogue fault components, and whether
allocating a fixed 44,090-dot budget across catalogue-distance strata can
convert that surface into a more unique far-field submission.

The leakage-canary universe contained 54 channels: 19 raw bands, 18 MSDB
physics features, and 17 LiDAR morphology features. The fitted fusion model
used 48 of them—13 stationary raw inputs, all 18 MSDB features, and all 17
LiDAR layers—while the MSDB comparator used the corresponding 31 (13 + 18).
The non-fault processes that can mimic the
target signature include Lake Lahontan paleo-shorelines and playa benches,
fluvial terrace risers, volcanic flow fronts, pluton contacts, roads, canals,
and mines.

### 1.2 What improved?

On the catalogue-component proxy, the fusion surface improved weighted
true-positive recovery over the same-run MSDB comparator in both experimental
seeds:

| Experiment | Candidate | HOLDOUT-DTI | Comparator | HOLDOUT-DTI | Paired Δ [95% CI] | Gate |
|---|---|---:|---|---:|---:|---|
| Exp. 1, seed 3051 | `fusion_edge` | 0.182417 [0.168230, 0.196433] | `msdb_edge` | 0.175639 [0.161471, 0.189566] | +0.006779 [−0.000067, +0.012888] | Frozen CI gate failed by 0.000067 |
| Confirmation, seed 3063 | `fusion_edge` | 0.183949 [0.169419, 0.197874] | `msdb_edge` | 0.173427 [0.159043, 0.187952] | +0.010522 [+0.004182, +0.016362] | Amendment-A1 gate passed |

All values above are **HOLDOUT-DTI**, evaluator
`component-holdout-v3-blockstats-20261025`, protocol
`buffered-quadrant-whole-components-v1-20261025`, 60,988 withheld positives,
371 geographic blocks, 2,000 paired spatial-bootstrap replicates. They are not
organizer scores and must not be projected onto the leaderboard as if they were.

The confirmation was not part of the original frozen gate. Amendment A1 was
written after Experiment 1 and before the confirmation run; it allowed exactly
one fresh seed and no retuning. Its evidential status is therefore disclosed
as an amendment-confirmed point improvement, not a clean preregistered pass.

### 1.3 Why is the final verdict nevertheless negative?

Three separate gates must not be conflated:

1. **Feature value:** supported on the catalogue proxy by the two paired
   experiments above.
2. **Unique submission:** failed. Expanded-registry dot overlap with MSDB-1v2
   is 78.280789%, so `fusion_edge` is duplicate-stopped permanently.
3. **Far-field remedy:** not validated. The frozen distance-stratified arm is
   geometrically infeasible on the v3 quadrant evaluator, as detailed in §6.

Because promotion requires all applicable gates, the correct outcome is
`negative`. Retaining the TIFF makes the failure auditable; it does not make
it submittable.

---

## 2. Nine-site conclusion and the H33 question

The lane's site-by-site audit is in
[`nine-site-executive-summary.md`](nine-site-executive-summary.md). Every fleet
score there remains **OWNER-REPORTED UNVERIFIED**; no organizer submission-page
receipt for those files is present in this repository.

The best prior file is GEMSDOE32's
`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, owner-reported at **0.2778**.
Byte/support lineage shows why it beat its relatives:

1. The dense H27/H19-family belief surface had broad, useful fault signal.
2. Thinning to approximately one dot per 2.8 px reduced redundant
   false-positive mass under the distance-weighted Tversky denominator.
3. Removing dots within 2 px of the catalogue removed a nearly barren
   digitisation-halo band while retaining most 300 m true-positive credit.

Thus H33's advantage is primarily an **allocation and waste-reduction**
advantage on a shared belief surface, not evidence of a wholly new geological
detector. GEMSDOE36's superset scored lower after adding dots, reinforcing
that additional placements can dilute rather than improve the pooled metric.

### Is >0.2778 achievable?

**In principle, yes; from this lane, not demonstrated.** The historical
calibration in the nine-site summary implies that a 37–44k-dot file needs
roughly 0.145 hits/dot to reach 0.30 and 0.155 hits/dot to reach 0.3195,
versus H33's implied 0.134 (all projections, not scores). The FFL fusion
features produced a real paired gain on the catalogue proxy, but:

- the gain is only +3.9% (Exp. 1) to +6.1% (confirmation) relative to the
  same-run MSDB proxy arm;
- catalogue-component recovery is not the hidden expert-new-fault target;
- the emission that expressed the fusion surface duplicated MSDB placements;
- the proposed far-field emission could not be validated on the frozen
  evaluator.

Accordingly, >0.2778 remains a plausible research direction, not a claim.
A future claim requires a placement rule that preserves the fusion surface's
true-positive advantage while demonstrably moving enough dots away from prior
rasters, validated before production on an evaluator whose geometry can
actually express that placement rule.

---

## 3. Method and leakage controls

### 3.1 Spatial holdout

The evaluator withholds whole catalogue components in buffered quadrants,
derives catalogue-dependent quantities only from visible faults, masks visible
fault pixels exactly, and pools the 300 m triangular distance-weighted
Tversky index (alpha 0.2, beta 0.8) across folds. Fold dot budgets are
count-matched by active footprint area.

This design tests spatial transfer to unseen catalogue components. It does
not recreate the hidden expert-labelled new-fault population: splays,
continuations, and parallel strands close to mapped faults may be more
important in the hidden target than in a quadrant-withheld catalogue proxy.

### 3.2 Leakage canaries

All 54 features were screened in each of four folds: 216 feature-fold canary
records, zero alarms. The largest either-direction AUC was **0.666660**
(`scarp_dipole_smooth`, fold 2), below the owner's 0.90 leakage threshold.
This rules out a gross single-feature label leak under the implemented test;
it does not rule out multivariate leakage, evaluator mismatch, or subtle
spatial dependence. No canary result is a DTI score.

### 3.3 Frozen budget

Three experiments were consumed:

1. Experiment 1: `fusion_edge` versus `msdb_edge`, seed 3051.
2. Amendment-A1 confirmation: same arms, fresh seed 3063.
3. Experiment 3: frozen stratified design attempted after Amendment A2; zero
   folds could be scored because the fold strata lacked eligible pixels.

No seed hunting, quota retuning, or post-failure emitter search followed.

---

## 4. Novelty: the decisive failure

### 4.1 Why the first audit passed

The pinned nine-site audit compared the candidate against 165 aligned
registry rasters. It found:

- continuous/gated surface maximum Spearman: **0.162624**;
- final-dot maximum Spearman: **0.065443**;
- maximum fraction of FFL dots within 3 px of a pinned reference:
  **0.661851** (66.1851%), nominally below 70%.

That registry snapshot predated this repository's own MSDB-1v2 publication in
`docs/downloads/`. Applying the owner's rule only to that stale snapshot was
the central procedural error (IR-FFL-01).

### 4.2 Expanded audit

The corrected audit uses the pinned registry plus every TIFF in
`docs/downloads/`, excluding only the candidate's own SHA-256: **168
comparisons**. Results:

| Stage | Max Spearman | Reference at maximum | Max FFL dots within 3 px | Decision |
|---|---:|---|---:|---|
| Surface | 0.112546 | MSDB-1v2 | — | blocked-incomplete-evidence (global registry cannot be attested) |
| Dots | 0.112546 against the dot raster | MSDB-1v2 | **0.782808** | **duplicate-stop** |

The directional reverse measurement is 0.799047 of MSDB dots within 3 px of
FFL dots. Both directions exceed 70%; no orientation ambiguity rescues the
candidate.

This outcome is scientifically plausible. Two independently trained models can
produce modestly correlated continuous scores while an EDGE/top-ranked emitter
selects the same compact maxima. Protocol compliance therefore requires the
dual check mandated by the owner: continuous surface before placement and
final dots after placement, against the broadest available local inventory —
including this repo's latest downloads, not only a frozen external snapshot.

---

## 5. File contract and the outside-footprint ambiguity

The strict FFL validator reopens the moved TIFF and confirms:

- one `float32` band;
- EPSG:32611;
- shape and transform exactly equal to `sample_submission.tif`;
- the whole 12,279,160-cell array is finite and in `[0, 1]`;
- outside-footprint value is exactly `0.0`;
- 44,090 emitted dots;
- zero dots on catalogue pixels and zero within 2 px of the catalogue;
- TIFF SHA-256 matches the run card and sidecar.

This addresses the owner's previously reported portal error, “Predicted values
must be in range [0, 1]”, at the level of the whole array. It does **not**
prove organizer acceptance. The original sidecar also records
`published_format_compliant=false` because the repository's published-format
validator expects null/NaN outside the footprint, whereas this artifact uses
the owner-requested all-finite zeros-outside convention. Those are distinct
contracts. The negative duplicate verdict makes the distinction moot for this
file: it must not be submitted under either rationale.

The artifact was moved from `docs/downloads/` to this research directory to
avoid breaking the shared current-run verifier: a new TIFF in `docs/downloads/`
requires an exact late-registry surface audit for MSDB-1v2, but the MSDB
continuous surface file is no longer present locally to regenerate that
receipt exactly. Card and sidecar hashes are unchanged. Their embedded
historical absolute output path still names the former downloads location
(IR-FFL-05); `run-card.json.published_tiff` is authoritative for the current
path, and `validation.json` was regenerated against the moved file.

---

## 6. Why the stratified remedy was not run to production

Amendment A2 froze production conditional on first validating the already
preregistered quotas:

- (2,5] px: 14%
- (5,10] px: 15%
- (10,30] px: 34%
- (30,50] px: 16%
- >50 px: 21%

with Poisson `r=3.0` placement within strata and ≤2 px excluded.

In v3 folds, however, active pixels lie in a withheld quadrant while the
visible catalogue lies principally in the other quadrants. The measured
eligible counts were:

| Fold | (2,5] | (5,10] | (10,30] | (30,50] | >50 |
|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 3,209 | 20,659 | 2,425,825 |
| 1 | 0 | 0 | 3,166 | 14,919 | 1,348,566 |
| 2 | 0 | 0 | 2,566 | 20,080 | 542,411 |
| 3 | 0 | 0 | 2,665 | 15,789 | 770,120 |

The first two strata cannot receive any dots, and the third cannot support its
34% quota under the spacing rule at the fold budgets. Redefining bins or
redistributing quotas after observing this geometry would create a new,
unfrozen hypothesis. Experiment 3 therefore scored zero folds, production was
not generated, and the gate is failed/infeasible rather than silently bypassed.

A future far-field study needs a preregistered segment-interleaved whole-
component holdout in which visible and withheld fault segments coexist over
the same terrain at controlled distances, while retaining spatial buffers and
count matching. It should also report chance-expected 3 px overlap for dense
references. That evaluator must be frozen before looking at candidate scores.

---

## 7. FFL irregularities

The global register entries are in
[`docs/irregularities.md`](../../irregularities.md), section
“2026-10-26 FFL-1”.

| ID | Severity | Short description |
|---|---|---|
| IR-FFL-01 | Critical | Initial promotion used a registry that omitted the repo's own MSDB download; expanded audit duplicate-stopped the candidate and reversed the verdict. |
| IR-FFL-02 | Medium | Initial production wording implied stratified quotas for an EDGE emission; corrected without changing pixel values. |
| IR-FFL-03 | High | Frozen production-distance strata are geometrically infeasible in v3 quadrant folds. |
| IR-FFL-04 | Low | README documented a nonexistent `restore_public_mirrors.py --include-extra` flag; corrected. |
| IR-FFL-05 | Medium | Artifact relocation left a historical absolute path in the sidecar; zeros-outside strict contract differs from the published NaN-outside validator. |
| IR-FFL-06 | Medium | Fresh-seed confirmation was an amendment after a 0.000067 frozen-gate miss; it is not equivalent to a preregistered pass. |
| IR-FFL-07 | Low | The first lane process exited nonzero after printing its final card; all downstream receipts were independently regenerated or verified. |

---

## 8. Reproduction and automated verification

From the repository root:

```bash
.venv/bin/python scripts/verify_fflidar_run.py
.venv/bin/python scripts/verify_fflidar_run.py --require-promote  # expected exit 2
.venv/bin/python scripts/verify_current_run.py                     # MSDB pointer unchanged
.venv/bin/python -m pytest -q tests/test_fflidar.py
.venv/bin/python scripts/build_research_site.py --check
```

`verify_fflidar_run.py` rehashes the TIFF, checks the sidecar and strict
all-finite `[0, 1]` contract, screens the recorded novelty/canary receipts,
and derives the expected non-promotion from the stratified/infeasibility
receipt. Exit 0 means the negative decision is internally verified; it never
means submission approval.

Key receipts:

- [Preregistration](preregistration.md) and [machine preregistration](preregistration.json)
- [Amendment A1 — confirmation](amendment-confirmation.md)
- [Amendment A2 — duplicate-stop/stratified experiment](amendment-stratified.md)
- [Experiment 1 results](results.json)
- [Confirmation results](results-confirmation.json)
- [Stratified infeasibility receipt](results-stratified.json)
- [Pinned novelty surface](novelty-surface.json) and [dots](novelty-dots.json)
- [Expanded registry](registry-expanded.json), [surface](novelty-surface-expanded.json), and [dots](novelty-dots-expanded.json)
- [Nine-site executive summary](nine-site-executive-summary.md)

---

## 9. Limitations and next work

1. **Organizer authenticity:** competition arrays were restored from
   hash-pinned owner mirrors, not authenticated through a DrivenData session.
   Mirror consistency is not organizer provenance.
2. **Hidden-target mismatch:** whole-component catalogue recovery rewards
   rediscovery of mapped-fault styles. Hidden splays/continuations and
   expert-labelled new faults may have a different distance distribution.
3. **No score inference:** HOLDOUT-DTI gains cannot be converted into a
   leaderboard forecast. There is no ORGANIZER-CONFIRMED FFL score.
4. **Incomplete global registry:** 168 observed comparisons are broad local
   evidence, not proof about unexported private or parallel-session rasters.
5. **Placement remains the bottleneck:** the next experiment should audit a
   proposed dot set against all current downloads *before* spending holdout
   experiments, then use a distance-expressive holdout frozen in advance.
6. **No geothermal-vent claim:** fault likelihood is not temperature,
   permeability, flow, or vent evidence. No vent/resource conclusion follows
   from this lane.

**Bottom line:** FFL-1 found a reproducible feature-level signal but failed
the uniqueness requirement at emission. Preserving that negative result —
rather than spending a weekly slot on a duplicate — is the outcome.
