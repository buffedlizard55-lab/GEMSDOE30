# QPC-1 review — negative; duplicate-stop; do not submit

**Decision:** no competition slot selected or upload performed. The QPC-1 final
candidate is **not published or downloadable**. Its dot audit crossed the user's
70% duplicate threshold, and its preregistered matched-control improvement gate
failed. No retuning, perturbation, re-encoding or resume is authorized. A prior,
independently validated [GDX-1 research TIFF](../2026-10-26-gdx/gems30-GDX1-44090-20261026-2992ee3619f5.tif)
remains available, but it is negative and **not approved for submission**.

## Hypothesis and execution

The preregistered hypothesis was that co-located, two-scale magnetic and gravity
high-pass/gradient vector concordance could reveal concealed structural boundaries
missed in the fault catalogue. It is a *quadrature-like proxy*, not a calibrated
Hilbert phase, dip, geothermal vent, or proof of faulting. An intrusive/volcanic
contact, dike swarm or survey-leveling seam is a named non-fault mimic. The
[preregistration](preregistration.md) documents four ranked proposals, exact
layers and support, physical rationale, costs, and trusted source links. The
[source and knowledge audit](source-audit.md) distinguishes primary-source claims
from unverified mirror lineage.

A single candidate experiment and the fixed FFL comparator replay used **2/3**
experiments and **550.904 seconds**, starting 2026-10-26 22:03:35 UTC. The
exclusive [start marker](started.json) hashes the plan, registry, runner,
transform and package versions. The fixed replay was counted as experiment two;
the duplicate-stop ends this lane despite the unused nominal budget. No fourth
GDX experiment was attempted.

Every one of the 23 candidate input channels and all 54 FFL comparator channels
was tested alone in each of four folds: **308** individual-feature canaries. Both
raw and train-only univariate AUC directions were checked; maximum bidirectional
AUC was **0.663826**, below the 0.90 alarm. This does not prove absence of every
form of leakage. Detailed records are in [results.json](results.json) and
[canaries-partial.json](canaries-partial.json). All four FFL confirmation fold
TP/FP/counts reproduced the frozen seed-3063 confirmation within 1e-6. Archived
MSDB fold identities and block masks/truth also matched before pairing.

## Matched holdout — not a leaderboard estimate

All rows are **HOLDOUT-DTI**, evaluator `component-holdout-v3-blockstats-20261025`,
protocol `buffered-quadrant-whole-components-v1-20261025`, **60,988 withheld
positive pixels**, and 95% paired geographic-block bootstrap CIs (2,000 draws).
The four folds hide entire connected fault components with a 17-pixel guard;
visible faults are masked pixel-exactly. The shared evaluator uses α=0.2, β=0.8
and a 300 m triangular kernel. These are conditional mapped-fault recovery
measurements, not organizer scores or forecasts for unmapped hidden faults.

| System | HOLDOUT-DTI [95% CI] | QPC minus system [paired 95% CI] |
|---|---:|---:|
| QPC-1, 23 features | **0.13866497 [0.12368501, 0.15499953]** | — |
| 21-feature within-field persistence control | 0.13885883 [0.12322521, 0.15497552] | −0.00019385 [−0.00619281, 0.00601667] |
| MSDB edge comparator | 0.17046161 [0.15622653, 0.18416757] | −0.03179664 [−0.04595774, −0.01789022] |
| Fixed FFL confirmation replay | 0.18394914 [0.16941880, 0.19787439] | −0.04528417 [−0.05937678, −0.03115278] |
| Core19 descriptive control | 0.13362779 [0.11828522, 0.14887498] | +0.00503718 [−0.00118370, +0.01118681] |

The lower CI bounds against persistence, MSDB and FFL were not all positive, so
the preregistered gate **failed**. The stronger FFL confirmation was discovered
in a pre-run re-audit of `main` and added to the frozen plan before any QPC fit.
It was an amended fresh-seed confirmation after an earlier FFL gate failed and is
not independent external field validation. FFL uses a different model/edge-emitter
system; the system-level comparison is not an isolated causal estimate of the
four QPC features. FFL itself was previously duplicate-stopped and is never an
acceptable fallback submission.

**Post-stop parallel-work correction:** unmerged [PR #41](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/41)
was outside the main-based frozen snapshot. Its pinned MS-CAPE card reports
HOLDOUT-DTI **0.18668700 [0.17332555, 0.20031682]**, 60,988 withheld positives,
evaluator `component-holdout-v3-blockstats-20261025`. It used a **20 px** guard
rather than QPC's **17 px**, with different visible and training counts. Hidden
component IDs, budgets and aggregate block truth/scored counts happen to match,
but pixel-exact active-mask identity and a paired comparison have not been
established. This is a potentially stronger *unverified parallel record*, not a
matched FFL replay or a slot recommendation. Its branch TIFFs were not in the
QPC registry; no post-stop comparison or new experiment was attempted. See the
[hash-pinned parallel inventory](parallel-inventory.json). A separate post-stop
[nine-repository head inventory](parallel-heads-inventory.json) found 25 public
open PR heads; their trees and rasters were not systematically scanned or compared.
The shared future-snapshot script now enumerates such head identities and marks
their unscanned trees/rasters UNKNOWN; it does not rewrite the frozen QPC registry. Claims about the
"strongest" comparator in the frozen preregistration apply only to the audited
main/17-pixel comparable record, not all open branches or private work.

## Two-stage novelty and file decision

The actual fitted continuous QPC surface was audited before final dot placement:
353 successful comparisons, maximum Spearman **0.15910948**, with one malformed
reference remaining unknown. The subsequent final-dot audit found maximum
candidate-within-3-pixel overlap **78.915854%** against the existing GEMSDOE30
`gemsdoe30-g30s19-habitat-edge-60000dots-20261025T210221Z-b527922d7f-nan.tif`
(and the value-equivalent zero-outside encoding). Six registry entries exceeded
70%, including a GEMSDOE36 file. This is a **duplicate-stop**, regardless of the
candidate's different byte hash or apparently distinct mechanism.

The stopped candidate's internal raster SHA-256 is recorded in the
[canonical run card](run-card.json), but it was **withheld**, not validated after
the stop, and is not a public download. Accordingly `validator_output` is null:
a no-result is not a passed format check. The pre-placement and dot receipts
are [novelty-surface.json](novelty-surface.json) and
[novelty-dots.json](novelty-dots.json). The frozen registry contains 370 source
TIFF paths, 354 deduplicated aligned identities, and nine pinned public commits.
A GEMSDOE31 reference has **2,610,312 non-finite in-footprint cells**, so no
correlation is claimed for it. Private/parallel work, outside-`docs/` outputs,
and unavailable original continuous surfaces remain unknown. Neither the
partial audit nor a different filename establishes global uniqueness.

## How to verify without rerunning a model

1. Restore the owner-mirrored template and labels with
   `python scripts/restore_public_mirrors.py --ids sample_submission labels`.
   Their hashes provide byte integrity, not organizer authentication.
2. Install the pinned scientific environment (`python -m pip install -e '.[research,test]' -c requirements-tdx1.txt`).
3. Run `python scripts/verify_quadrature_phase_run.py`: it verifies the frozen
   identities, full novelty inventory and duplicate flags, matched fold statistics,
   feature-alone canaries and recomputed block-bootstrap intervals. It exits 0
   for a valid negative finding. With `--require-promote` it exits 2.
4. CI verifies the hash-bound surface receipt; it can reopen the saved surface
   only where the ignored local bytes still exist. Never infer that CI downloaded
   private surfaces or reran scientific fits. `started.json` prevents resumption.

## Nine-site result and remaining work

The [nine-site executive summary](nine-site-executive-summary.md) names each
historical file, owner-reported claim, directional relatedness and unknown
estimated score. The best user-reported H33 claim (0.2778) is unverified. The
verified d28 → r1 → H33 pruning lineage is consistent with fewer low-yield false
positives, but does not reveal hidden TP/FP or establish why the owner-observed
score changed. A genuinely better score is plausible, not quantified or proven.

Before any future independent lane, obtain the assigned method paragraph, an
attested complete registry (including private work and original surfaces),
authenticated input provenance, and actual organizer receipts as applicable.
Preregister a genuinely new hypothesis, use a fresh budget, repeat feature canaries,
matched best-comparator block tests and both novelty stages, and independently
confirm. Only a separate selector can consider a slot after all gates pass. The
old range-error file and portal receipt are absent, so the exact cause and portal
acceptance of any local file remain unproven. The repository status feed is not a
DrivenData scraper.
