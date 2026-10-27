# Registry preflight and research review — 2026-10-27

## Decision: DUPLICATE-STOP · DO NOT SUBMIT

This is a **zero-experiment negative**, not a fresh prediction. The saved
[run card](run-card.json) is the single current card. No new surface, holdout,
GeoTIFF, filename, note, forecast or weekly-slot selection was created. The
previous CSR-1 file remains accessible **for historical research only**; its
newly reproduced literal-rule duplicate and independent format failure block
submission regardless of its archived all-finite diagnostic. No other old file
is made new by copying, renaming, masking or converting it.

### A deterministic stop before model fitting

The user included [13GEMSDOE](https://buffedlizard55-lab.github.io/13GEMSDOE/)
within the comparison universe. We restored its [immutable stride-5 prediction](https://github.com/buffedlizard55-lab/13GEMSDOE/blob/92ee6f074323f161eed837b80ec3ee5b662e26f5/docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif)
(SHA-256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`),
validated its in-footprint range and exact grid against the pinned template,
and measured Euclidean pixel distance to its positive support. The valid
footprint has 5,167,373 cells, of which only **6,649 are farther than 3 pixels**
from the 206,895 reference dots. A candidate of K distinct footprint dots must
therefore match at least `max(0, K − 6,649)` reference-neighbourhood cells.
For the CSR-1 budget K=44,090 the minimum is **37,441/44,090 = 84.9195%**,
which exceeds the literal strict `>70%` gate regardless of placement. The
first budget provably over the gate is **22,164**; at 22,163 the lower bound is
not over 70%. Lack of a proof below that threshold **does not mean unique**.
Reducing budget solely to get around this check is not a geological discovery.

We also measured the exact already-published CSR-1 file: **44,084/44,090 =
99.9864%** overlap; full-footprint Spearman is −0.0001321. A failure against
one reference suffices for a stop, while a pass against one never establishes
complete-registry uniqueness. The historical 357-raster CSR comparison omitted
this witness; its pass was therefore scoped, not evidence of global uniqueness.
The lattice is a coverage baseline, not proof that two models have the same
geologic meaning. It is used only as a registry witness, never as a feature.

### Parallel work merged during this audit

PR [#54](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/54) merged while
this review was underway. We preserved its exact files and checked their saved
bytes against the same witness, without building new candidates:

| Already-published file | Measured matches within 3 px | Budget proof | Local published format | Decision |
| --- | ---: | --- | --- | --- |
| [CTD-1](../../downloads/gems30-ctd1-concealed-stepper-20261027T172620Z-c39a9264.tif), SHA-256 `13074a02b38e7edea5faaccbaa18f382dffd395fd211139becb7d66278f02297` | **39,984/40,000 = 99.9600%** | proven >70% before placement | passes; NaN outside | **DUPLICATE-STOP; DO NOT SUBMIT** |
| [FC-1](../../downloads/gems30-fc1-concealed-flank-20261027T172846Z-f182c780.tif), SHA-256 `d6dadb9c6119767f0b4af2f2122e73529829b3c1b36cf1131165cb68b8da2612` | **10,844/10,848 = 99.9631%** | not proven by budget alone | passes; NaN outside | **DUPLICATE-STOP; DO NOT SUBMIT** |

FC-1 demonstrates why a sub-22,164 budget is not automatically unique. The
old CTD 27-raster scan was limited to local downloads and omitted 13GEMSDOE.
Its note says “all-finite”, but its saved bytes have NaN outside: normal
published format passes and the *whole-array finite* diagnostic fails. Neither
result proves portal acceptance. The preserved PR page is explicitly marked
[historical](../../../ctd1-history.html).

**Holdout integrity:** both original builders used the complete `labels.tif`
catalogue when deciding where to emit dots. The archived evaluator then hid
components and re-emitted the already-built file, rather than rebuilding each
catalogue-derived feature and prediction from visible faults. It calls a single
random component split, not the claimed buffered four regional folds; FC-1's
candidate and controls also have unequal dot counts. Consequently the stored
CTD/FC scores are not valid evidence under the requested leakage-safe
same-protocol holdout, regardless of their reported direction. See the immutable
[CTD builder](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/99b9cc9693bd19c474f298a99618599ade6f3c60/scripts/build_concealed_stepper_submission.py),
[FC builder](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/99b9cc9693bd19c474f298a99618599ade6f3c60/scripts/build_flank_concealed_submission.py)
and [evaluator](https://github.com/buffedlizard55-lab/GEMSDOE30/blob/99b9cc9693bd19c474f298a99618599ade6f3c60/scripts/evaluate_ctd1_holdout.py).
Their historical command-line generation/scoring paths are disabled; the local
novelty wrapper now delegates to the shared, explicit-registry auditor.

### The saved TIFF and score are separate questions

The exact CSR-1 TIFF has SHA-256
`0fbf3b4a47c2229b68de59e174617f3b47973613ff57950712d25b9166c1d900`.
It has finite [0,1] values inside the template footprint and its **whole-array
finite [0,1] diagnostic** passes. However, the published-format validator
requires null outside the footprint and independently fails its
`null_outside_template_footprint` check because this file uses zeros outside.
The organizer's actual rejection cause, portal acceptance and any artifact-linked
organizer score are **unknown**. Do not infer a successful upload from a local
diagnostic. The old card is retained verbatim as a historical record; the
[current run card](run-card.json) supersedes its old download/readiness wording.

The historical four-region catalogue hide-and-recover result was
**HOLDOUT-DTI**, evaluator `component-holdout-v3-blockstats-20261025`, 60,988
withheld positives: CSR-1 **0.158162 [0.144986, 0.171474]** versus same-run
`msdb_edge` **0.169986 [0.156534, 0.183948]**; paired difference
−0.011825 [−0.023453, +0.000297]. The positive fold-3 observation was noticed
post hoc, not independent confirmation. This is a mapped-catalogue proxy, not the
organizer's hidden score. CSR-2 is a previous proposal, not an assigned lane or
a new result. [Historical results](../2026-10-26-csr/results.json).

## Nine-site snapshot, not a live registry

The [2026-10-26 fleet audit](../2026-10-26-csr/fleet-audit.json) pins one
owner-identified historical best per priority site. Values 0.2477, 0.2600,
0.2449, 0.2710, 0.2600, 0.2708, 0.2778, 0.2632 and 0.2750 for GEMSDOE24,
25, 27, 28, 30, 31, 32, 33 and 36 respectively are **unverified owner claims**,
not `HOLDOUT-DTI` and not `ORGANIZER-CONFIRMED`: no submission-page receipts
were available. They are not forecasts. The dates and pinned historical files
must not be mistaken for present site leadership or selector approvals. Each
of the nine inspected files contains at least 22,164 dots, so the lattice bound
alone proves each would trip the literal directional dot rule on this footprint;
this is not a numerical overlap measurement for those nine files. Current
candidate status on the remote sites may have changed; refer to their live
pages and require a fresh registry and separate selector approval.

Inside-footprint equality was verified for G25/G30, and the separately inspected
40,199-dot G28 r1 intermediate equals the inspected G31 raster. It is not the
37,660-dot G28 historical selection in the nine-row table. H33-B2 is `r1` with
dots within 2 pixels of the visible catalogue removed (2,545 dots removed); G36's inspected PINN
contains H33-B2 plus 1,200 dots. These are raster-lineage facts, not proof of
physical fault discovery. The owner-reported 0.2778 is greater than some
owner-reported earlier values, but without hidden truth and organizer receipts
we cannot infer actual TP/FP changes, attribute improvement to pruning, or
establish an organizer-confirmed gain.

For reference, organizer DTI uses `TP = Σ_truth max_prediction kernel(distance)`;
`FN = |truth| − TP` and FP is the organizer's distance-weighted prediction
penalty, then `TP / (TP + 0.2 FP + 0.8 FN)`. See the
[official problem statement](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
for exact definitions. The formula and numerical causal inferences in the
historical CSR review §3.1 must not be relied on; history is not rewritten.

## Ranked geological hypotheses — proposals, not runs

Ranks are qualitative research priorities, **not score predictions**. These
are distinct mechanisms, not a claim that no parallel repo has contemplated
them. Do not run without an explicit single assigned lane, a feasible and
allowed novelty regime, and fresh pre-registration.

1. **Regime-gated terrain + cover-blind edge expert (CSR-2 proposal).** Use
   the pinned 3DEP-derived piedmont scarp features plus competition RTP,
   magnetic/gravimetric derivatives and MT conductance. Fit a buffered-fold
   local expert and combine it with the piedmont expert using a frozen regional
   cover/strain regime gate. Unmapped piedmont ruptures may have surface scarps,
   while alluvial cover can obscure deep continuation. It differs from CSR-1's
   single global combined model, but regional expert gating has been discussed
   in parallel work; it is **not** assumed fleet-unique. Mimics: eroded fan
   scarps, lava fronts, lithologic boundaries and flight-line seams. The input
   layers are already pinned owner-derived mirrors; local transforms are modest
   CPU, while re-training and blocked evaluation are additional cost. Rank is
   provisional because archived CSR-1 did not beat its matched control.
2. **Mapped-unit projection vs buried contact discordance.** Rasterize only
   geology polygons from the updated USGS GeMS/SGMC map, project bedrock-unit
   trends beneath alluvium and compare their predicted contact continuation to
   independent magnetic, gravity and MT discontinuities. A displaced projected
   contact could reveal a concealed fault. This tests continuity of mapped rock
   units rather than training directly on their fault traces. Mimics include
   unconformities and unfaulted stratigraphic terminations. Requires new data,
   source/coverage and license checks, reprojection and moderate GIS effort;
   fault/structure tables must be excluded to avoid leakage. USGS now
   recommends its [2026 updated GeMS release](https://doi.org/10.5066/P1A3DQZK)
   over the [2017 SGMC](https://www.usgs.gov/data/state-geologic-map-compilation-sgmc-geodatabase-conterminous-united-states).
   This projection proposal was already discussed in the historical review,
   not demonstrated implemented or fleet-unique.
3. **Drainage-deflection coincidence rather than scarp amplitude.** Derive
   flow direction and catchments from official 3DEP DEM, measure repeatable
   channel deflections or knickpoint alignments at a candidate cross-drainage
   strike, then test coincidence with an independent potential-field edge.
   Repeated drainage offsets might mark a previously untraced deformation zone.
   This differs from lidar-only crest/base morphology but was previously
   proposed locally. Mimics: lithologic contacts, lava dams, terraces, roads,
   DEM artefacts. Full DEM processing and boundary conditioning cost more than
   reading the cached scarp summary; coverage and metadata must be checked.
4. **Alteration-ratio persistence conditioned on survey geometry.** From
   GeoDAWN K, Th and U, compute a preregistered log-ratio residual with a
   within-survey-block null and require cross-line persistence plus independent
   gravity/magnetic support. Hydrothermal alteration can affect near-surface
   radiometry along structures even where a map omits a trace. This is a
   line-persistence and explicit flight-block control, not just the ordinary
   channel values already used; related concepts were proposed elsewhere.
   Mimics: soil/lithology, moisture, agricultural areas and acquisition seams.
   GeoDAWN has two different flight specifications and 200/400 m line spacing;
   not all anomalies resolve 100 m structures. The owner-derived caches exist;
   source metadata must be rechecked and the survey-block masks built. Low to
   medium processing cost, uncertain discriminating power.

Official input sources: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program)
(free, unrestricted products; tile coverage/quality varies), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
(CC0, DOI `10.5066/P93LGLVQ`), and [DOE INGENIOUS](https://gdr.openei.org/submissions/1391)
(CC BY 4.0, DOI `10.15121/1881483`; distinguish regional non-fault layers
from fault-derived leakage). The data locally restored from owner mirrors are
hash-pinned but **not organizer-authenticated**.

## Protocol, sources, next steps

Official rules specify one aligned float32 GeoTIFF, same bounds/grid and CRS,
values [0,1] and null outside; mapped USGS/INGENIOUS fault pixels are excluded
from scoring ([staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
Staff also says new geometry of an existing system can be a new target
([clarification](https://community.drivendata.org/t/where-do-you-draw-the-line/11536)).
Check the [official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/),
[rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), and
[organizer leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
for current terms and deadlines. **Deadline discrepancy:** the competition
homepage listed 3 December 2026 at 23:59 UTC; Appendix A.1 of the September 2026
rules PDF requires final content by 5:00 p.m. ET on the deadline date (22:00 UTC
on 3 December). Confirm with the organizer and plan for the earlier time; do
not assume the discrepancy is resolved. The PDF §3.4 permits up to three
feedback submissions per week and requires one final submission. The public
leaderboard displayed 0.4544 at a point in time on 2026-10-27; this is not
linked to any candidate here and is not a prediction.
DrivenData's [terms](https://www.drivendata.org/termsofuse/) prohibit automated
website access and unauthorized monitoring; this repository does not scrape
or schedule organizer-page monitoring. The GitHub-only build/status feed is a
versioned snapshot and does not certify the state of parallel runs.

To resume safely: allocate one scientific lane; resolve any registry policy
change explicitly (do not invent density exemptions); preregister and assess
budget feasibility; hold out entire fault segments with guard buffers and
recompute catalogue-derived features from visible faults only; check each
feature for leakage (AUC >0.90 is suspect); compare identical folds/metric and
95% CI against the current same-protocol best; check the full registry at both
surface and dots; validate the exact saved bytes; then obtain separate slot
selector approval. Three experiments/two hours remain upper limits, not an
obligation to run after a stop.

## Reproduce

```bash
python -m pip install -e '.[research,test]' -c requirements-tdx1.txt
python scripts/restore_public_mirrors.py --ids sample_submission
python scripts/restore_public_mirrors.py --pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice
python scripts/verify_registry_preflight.py
python scripts/validate_submission.py docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif --template data/raw/sample_submission.tif  # expected nonzero
python scripts/build_research_site.py --check
python -m pytest -q
```

The verifier requires no candidate generation or private data. A verified
negative exits 0; `--require-promote` exits 2. The separate
[cache-integrity receipt](cache-verification.json) checks restored raw-to-cache
derivation, not organizer provenance or performance.
