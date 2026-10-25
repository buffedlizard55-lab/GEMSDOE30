# TDX-C2 — full-stack displacement falsification (2026-10-25)

**Registered before implementing or running this continuation.** This is an autonomous
continuation of the prior TDX-1 next step, not an externally assigned parallel lane.
The received prompt again contains no identifiable single-method paragraph. Missing
lane/complete parallel-registry evidence stays unknown and blocks approval. No slot
will be selected or used. Read the complete owner prompt embedded in README first.

## Prior evidence and scope

TDX-1 was negative against core19 but positive against physics3, on already inspected
buffered regional trials. Its recommendation was matched zero-lag/phase-scrambled
controls before adding displacement to the full stack. This continuation tests the
**incremental, displacement-specific information conditional on all 19 core bands**.
It does not claim that repeating those folds gives fresh independent confirmation.
Original TDX-1 receipts and its negative artifact remain immutable references.

## Four ranked prospective hypotheses (qualitative priors, NOT projected DTI)

All use existing cached magnetic anomaly (band 1), RTP (2) and isostatic gravity (13);
no unverified new external data is needed. Layer names are checked against the official
reference notebook and local band tags. These specific conditional/control hypotheses
have no implementation in the checked-out code at registration.

| Rank | Untested hypothesis; exact signature | Why an unmapped fault, not just a catalogue trace? | Difference from implemented TDX-1 | Named non-fault mimic | Expected utility / cost |
|---|---|---|---|---|---|
| 1 | **Habitat-conditioned displacement specificity:** add the two cross-scale nonzero-lag profile gains and their gravity-weighted consensus to the full 19-band stack; compare matched zero-lag and phase-scrambled controls | A buried offset can remain in magnetic fabric even where cover removes a mappable surface scarp; no catalogue geometry is an input | Tests added information beyond core19 and whether any gain is displacement-specific, rather than a six-feature model versus only three raw bands | Intrusive lithologic contact; survey/gridding seam | Highest information gain, uncertain performance gain / medium CPU cost; **only hypothesis executed** |
| 2 | **Signed-lag run continuity:** parallel-transport the magnetic lag sign along a gravity-edge tangent, then measure persistent rather than isolated sign runs | A concealed through-going offset should sustain a signed fabric break beyond mapped ends | TDX-1 discards lag signs after two-scale agreement and does not assess along-edge runs | Curved intrusive contact or flight-line artifact | Moderate, uncertain / medium; not executed |
| 3 | **Opposite-flank reciprocity:** require forward and reverse profile correspondence to yield opposite lags of equal magnitude at both scales | Reciprocal texture offsets are a stronger buried-structure test than one-way matching | TDX-1 uses only one-way matching | Repeated stratigraphic magnetic bands | Moderate-to-low / medium; not executed |
| 4 | **Offset localization relative to adjacent normals:** compare lag gain at the gravity edge to matched profiles displaced on either side, rejecting broad texture mismatch | A localized buried break may be sharper than regional lithologic/source-depth variation | TDX-1 has no matched off-edge localization control; would need a newly derived support/guard bound | Magnetic source-depth transition | Uncertain / medium-to-high; not executed |

These are falsifiable geological/signal-processing hypotheses, not established fault,
slip, permeability, temperature, geothermal-vent or economic-resource detections.
RTP and magnetic anomaly are related transforms, not independent surveys.

## One frozen experiment, four fixed arms

- `core19`: exactly the prior 19-band HGB comparator.
- **Fixed candidate `tdx22`**: core19 plus the original two TDX-1 gains and their
  gravity-normalized consensus. No new transform scale or emitter optimization.
- `zero22`: core19 plus positive zero-lag correlation (geometric mean across the
  same two scales) for each magnetic band and its gravity-weighted consensus.
- `phase22`: core19 plus TDX-1 lag-gain features after a fixed local Fourier
  phase scrambling of each right-hand 13-sample profile. Use phases
  `[0.73, -1.21, 2.33, -2.02, 1.07, -0.48]` radians on the six non-DC rFFT
  frequencies, unchanged at both scales and all pixels. Preserve profile DC,
  power spectrum and sample support; never shift source pixels between regions.
  This is one deterministic falsification control, not a null-distribution estimate.

Same HGB settings/sampler as TDX-1: 120 iterations, learning rate 0.1, 31 leaves,
no early stopping, seed 3070 + fold; all visible training positives and six sampled
negatives per positive. Identical training coordinates/targets for all arms.
Normalization is training-only. Full-data refit always uses `tdx22`, never the best
arm. Existing source-independent cached core/TDX features are reused and hash-checked.

Use the shared `gemsdoe30.holdout` evaluator, not a private fork: four buffered
whole-component quadrant trials, physical/training guard 17 px, visible-fault pixels
masked exactly, pooled 300 m triangular DTI with alpha .2/beta .8. No catalogue-
derived predictor is used. All 60,988 catalogue positives are hidden once. Counts
match the predeclared 44,090 full-footprint dot density in each active scored domain;
existing score-ordered 3 px Poisson emitter, no tuning. A capacity shortfall fails
the gate. Use 128 px geographic blocks aggregated across folds, 2,000 paired
bootstrap draws, seed 3071, 95% percentile intervals.

Before accepting results, test **all 28 distinct raw/derived features individually**
in all four folds using bidirectional raw AUC and training-only univariate HGB
(32 iterations, 7 leaves). AUC outside [.10,.90] in either direction is an alarm,
not a good feature. Failure stops promotion. Low AUC does not prove no leakage.

Scientific gate: `tdx22` must have a strictly positive paired 95% CI lower bound
against **each** of core19, zero22 and phase22; no canary alarm or count shortfall.
This alone cannot establish performance above a historical best whose checkpoint/
matching-protocol receipt is unavailable, nor predict the hidden organizer score.

## Novelty, release, budget and stopping

Freeze a fresh nine-priority-repository inventory and include every other local
published TIFF before construction. Use the shared exact full-footprint Spearman
and directional Euclidean <=3 px overlap checks. Check the continuous surface
**before placement** and the fixed final dots before publication. rho > .90 or
final-dot overlap > .70 with **any** observed reference means duplicate-stop: no
retuning, no perturbing dots to pass, no further experiment, no new public TIFF.
Original continuous surfaces and other private parallel lanes are missing, so a
successful observed check is not a global novelty certificate.

The final candidate may be built only after the fold experiment; a negative result
is still a deliverable. If it passes observed duplicate checks and the shared file
validator, publish it as a **new, quarantined research TIFF**, not an approved entry.
A positive scientific gate still needs complete registry/lane/historical-best and
separate current portal/slot evidence. No human-inspector override or upload path.

Budget: **one experiment with four fixed arms**, no search, at most three executions
including documented bug fixes, stop by two hours from this session's first work
(2026-10-25T22:46Z), even if incomplete. Record actual elapsed time and all failures.
Negative results are not suppressed. No competition portal is contacted by this run.

## Sources and evidence rules

- Official reference: https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b
- Notebook band definitions: https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb
- Official problem/metric (manual review; host unavailable in this sandbox): https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- Official rules PDF (manual review; not newly verified here): https://docs.nlr.gov/docs/fy26osti/96647.pdf

All measured performance numbers are labelled HOLDOUT-DTI with evaluator, withheld
positives and 95% CI. No ORGANIZER-CONFIRMED score is available. Owner-reported values
are quarantined as unverified claims, never substituted for organizer receipts.
Mirrored input hashes verify consistency, not organizer authentication or rights.
