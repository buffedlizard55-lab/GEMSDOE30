# Priority-site review and submission decision — 2026-10-25

## Decision: NOT APPROVED FOR SUBMISSION

No new TIFF was generated in this session. No weekly slot was selected or used.
This is a negative **readiness** result, not a negative geological experiment.
The current prompt refers to a single method paragraph but does not provide an
identifiable lane assignment. The older README's metric-shaped-loss lane is not
assumed to authorize a new parallel run. The shared parallel-run registry and
shared-template location are also absent. Inventing those inputs or recycling a
historical raster would violate the owner's protocol.

The data-placement blocker **was resolved autonomously**: existing pinned owner
mirrors were restored through GitHub, then `scripts/prepare_data.py` completed.
[Prepared manifest](prepared-manifest.json). Hash identity establishes consistency,
not organizer authentication. Raw data and prepared arrays remain Git-ignored.

## What the historical winner actually does

**Owner-reported, UNVERIFIED score claim:** `0.2778` for
`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`. This is NOT
ORGANIZER-CONFIRMED. No submission-page receipt was obtained. The prompt's
leaderboard claims `0.4413` and `0.3195` conflict as descriptions of the current
lead; neither is asserted as current here. These numbers are preserved as claims,
not admitted to a validated score table. No new HOLDOUT-DTI is reported.

The [pinned GEMSDOE32 audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
describes deleting all base dots at catalogue distance <=2 pixels. The downloaded
reference has 37,654 positive pixels (local measurement). The GEMSDOE28 base has
40,199. This is emission pruning, not evidence of a newly learned independent
geological signal.

**Byte-derived reconstruction:** applying `distance_to_catalogue > 2 pixels` to
GEMSDOE28's positive support reproduces GEMSDOE32's support with **zero mismatching
pixels**. GEMSDOE25/GEMSDOE30 and GEMSDOE28/GEMSDOE31 also have identical
in-footprint values in the selected references. [Reconstruction receipt](recipe-reconstruction.json).
This establishes the actual spatial transformation, but still does not explain
the organizer's hidden labels or independently authenticate the reported result.

Under the repository metric, write weighted true-positive credit as T,
false-positive mass as F, and held-out truth mass as G. With the specified weights,
DTI = T / (0.2 T + 0.2 F + 0.8 G + epsilon).
Removing redundant predictions can reduce F faster than it reduces T. In
particular, nearby predictions compete through maximum kernel credit rather than
adding unlimited credit to one truth pixel. This gives a plausible explanation
for improvement from thinning and flank pruning. It is **not causal proof** of
why the private evaluation returned a particular result. Off-catalogue fault
labels, the actual uploaded bytes, and organizer receipts are unavailable.
A blanket catalogue buffer can also delete genuine short splays and extensions.

**Can a unique candidate beat the reported result?** It is possible, but there is
no defensible quantitative forecast here. A promising test must improve withheld
fault recovery per unit of false-positive mass using independent physical
information, not just extrapolate a fitted leaderboard response. More sparse is
not universally better, and the metric does not mathematically require binary
predictions. Earlier repository prose claiming otherwise is superseded by this
review.

### Measured duplicate audit (not performance scores)

Exact full-footprint Spearman correlation and directional overlap were computed
from the pinned historical bytes. Here the candidate is **the historical H33
reference**, not a new submission. Dots mean positive in-footprint cells; distance
is Euclidean in pixel coordinates, inclusive of 3 pixels. NaN/zero outside the
footprint does not affect either statistic.

| Compared with H33 reference | Spearman | H33 dots within 3 px of reference |
|---|---:|---:|
| GEMSDOE24 | 0.532368 | 100% |
| GEMSDOE25 | 0.923555 | 100% |
| GEMSDOE27 | 0.526747 | 100% |
| GEMSDOE28 | 0.967587 | 100% |
| GEMSDOE30 | 0.923555 | 100% |
| GEMSDOE31 | 0.967587 | 100% |
| GEMSDOE32 self-check | 1.000000 | 100% |
| GEMSDOE33 | 0.794679 | 99.9841% |
| GEMSDOE36 | 0.984321 | 100% |

[Machine-readable measurement](../h33-historical-duplicate-audit.json).
The self-check is a positive control, **not** the basis of the cross-site finding.
Even excluding it, these historical variants violate the present dot-overlap
threshold. Re-encoding, renaming, or lightly pruning them cannot establish
novelty. Dense reference rasters can make the directional overlap gate very
restrictive; the requested rule is retained, not silently relaxed.

The inventory covers one requested historical reference per priority site, not
all artifacts or every parallel lane. Passing this partial registry would **not**
certify novelty. Underlying continuous surfaces were not reconstructed, so this
is a final-dots educational comparison only.

## Priority-site evidence coverage

All nine source trees, available root/docs landing pages and READMEs were read
through GitHub at pinned commits. GitHub Pages hosts are outside this sandbox's
network allowlist, so the rendered deployments were not independently fetched.
[Source URLs and content hashes](source-audit.json) identify inspected documents;
[artifact pins](../priority-site-pins.json) identify exact downloaded rasters.

| Site | Requested family / starting point | Evidence limit |
|---|---|---|
| GEMSDOE24 | d1.5 thinning of H19-5 | Owner source + measured TIFF, no organizer receipt |
| GEMSDOE25 | d2.8 thinning | Same limit; historical score attribution conflict persists |
| GEMSDOE27 | topological gap closure on d1.5 | Same limit |
| GEMSDOE28 | solo d2.8 base; other variants inventoried but not compared | Same limit; no exhaustive site-wide novelty claim |
| GEMSDOE30 | d28 range-hardened copy | Identical in-footprint support to GEMSDOE25, not a new method |
| GEMSDOE31 | solo d28 | Historical support closely shared with GEMSDOE28 |
| GEMSDOE32 | two-pixel catalogue-flank pruning | Confirmed description and byte measurements, not hidden-test causality |
| GEMSDOE33 | analog/tip/stepover-labelled variant | Does not establish independence merely by having a different filename |
| GEMSDOE36 | Anderson/geothermal-labelled variant | Name is not proof of physically independent support |

GEMSDOE32's README itself describes **0.4413 as a problematic live-mirror
estimate for a pruned arm**, not a confirmed leaderboard result
([lines 315–320](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/012e17b2a115c3c0d5e7885bea625bf9657c99fc/README.md#L315-L320)).
This does not establish where the owner's current leaderboard claim came from,
but is a material reason not to promote that number to organizer evidence.
The H33 sidecar mixes a `catalogue_hidden_mean` with quadrant values that do not
average to that field, plus drift corrections and a projected leaderboard value.
Those fields are not accepted as a reproducible pooled HOLDOUT-DTI with a CI.

## Hypotheses proposed BEFORE candidate implementation

These are prospective hypotheses, **not established geology or measured gains**.
Rank expresses qualitative expected utility versus cost, not a numerical DTI
projection. Novelty is relative to reviewed local modules/scripts; global novelty
has not been demonstrated. None is assigned to this parallel session's lane.
No new external data is required for these first screens; exact band semantics
must still be checked against the pinned metadata before physical interpretation.

| Rank | Hypothesis, layers and transform | Why it might find unmapped faults | Named non-fault mimic | Difference from reviewed local methods | Expected utility / cost |
|---|---|---|---|---|---|
| 1 | **Cross-contact magnetic texture displacement**: `rtp`, `mag_anom`, `iso_grav_anom`. Estimate lateral phase/texture displacement across an independently extracted gravity edge, retaining displacement consistent across scales. | Buried lateral offsets may have no mapped surface scarp; seek disrupted texture rather than known-catalogue proximity. | Intrusive lithologic contact | Local basement-edge/coherence methods rank gradient ridges, not matched texture displacement on opposite flanks. | Moderate potential, medium cost; uncertain texture resolution |
| 2 | **Conductivity-curvature saddle at cover transitions**: `cond_surf`, `depth_to_base_surf`, `iso_grav_anom_hg`. Detect conductive curvature saddles intersecting a basement ramp, rather than generic high conductivity or edge amplitude. | Could identify a breach through cover where surface mapping is weak. | Saline basin groundwater / sediment facies transition | Goes beyond local vent-corridor coincidence and basement slope by testing a saddle topology interaction. | Moderate-to-low potential, low cost; interpolation artifacts a major risk |
| 3 | **Residual magnetic demagnetization corridor**: `mag_anom`, `rtp`, `tmi_vg`, `iso_grav_anom`. Fit magnetic response conditioned on gravity and broad spatial trend on training blocks only; detect coherent negative residual ribbons. | Hypothesized alteration along buried fluid pathways could differ from ordinary lithologic magnetic contrast. | Nonmagnetic sediment fill | Residual, conditional anomaly test rather than absolute magnetic amplitude or ridge conjunction. | Uncertain potential, medium cost; geothermal alteration not uniquely identified |
| 4 | **Topographic profile-offset persistence**: `det_elev`, `det_elev_slope`, `depth_to_base_surf`. Compare opposing detrended profiles across prospective edges and require signed offset persistence across scales without using catalogue directions. | Low-relief buried/eroded continuations may be missed by ridge-only surface mapping. | Lake shoreline terrace / fluvial incision | Matched profile displacement rather than existing local LiDAR dipole maximum and strike-continuity gate. | Low-to-moderate potential, medium cost; 100 m grid may be inadequate |

Hypothesis 1 is the first proposed test **after lane allocation**, not a chosen
submission. Its preregistration should compare against the current-best model
re-run on the same corrected folds, dot budget and evaluator version. Each
individual input/derived feature needs a held-out AUC canary; AUC >0.90 blocks
interpretation pending leakage investigation. Physical features independent of
the catalogue still require proof that interpolation/training never used hidden
labels. Any catalogue-derived feature must be rebuilt from visible faults only.
Hide whole segments and buffer at least the complete feature/filter support plus
the metric reach; spatial grouping and buffer distances must be preregistered.
Pool sufficient statistics, not fold DTI averages; bootstrap whole spatial groups
for paired 95% confidence intervals. Pixelwise bootstrap is not acceptable.

## Shared-tool review and defects fixed

- Existing shared modules are `src/gemsdoe30/holdout.py` and `submission.py`;
  requested `evaluate_holdout.py` / `submission_writer.py` are not present. No
  private replacement evaluator or writer was created.
- **IR-30-050:** `masked_dti_by_blocks` accepted `valid` but ignored it in pooled
  credit/FP calculations. Outside predictions could reach inside truth; outside
  truth could be counted; truth-empty quadrants omitted their FP contributions.
  Fixed in the shared module. The new version is
  `component-holdout-v2-footprint-20261025`. Prior results are not relabelled as
  this version, and their exact impact must be established by rerunning.
- Current component splitting is centroid-tile interleaving, not automatically
  a buffered spatially blocked segment protocol. It cannot be advertised as
  compliant with the new protocol merely because components are disjoint.
- **IR-30-051:** status generation could say all hashes were verified when some
  required files were absent (`all` over only present entries). Fixed to require
  every required entry and a positive hash match.
- **IR-30-052:** old landing/summary pages simultaneously advertised copied
  reference files as submission-ready and called them unpromoted research.
  Replaced those contradictory entry pages with explicit blocked status.
- The writer's local range/grid tests do not prove eligibility or hidden-test
  performance. Historical clipping/sanitization is not proof that a scientific
  model is sound. Use the strict shared writer for new model outputs; investigate
  invalid in-footprint predictions rather than hiding them with clipping.

## Official source register and access limits

| Source | What was verified here | Limit / follow-up |
|---|---|---|
| [DrivenData reference notebook](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb) | Actual code uses U-Net, Tversky training weights 0.2/0.8, sigmoid predictions, and writes a single-band TIFF with CRS/transform from labels and no explicit nodata argument. | Training Tversky loss is NOT the competition distance-weighted evaluator. Code alone does not prove portal behavior. |
| [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Link supplied by owner; historical specification retained in repo. | Outside network allowlist; not freshly verified here. |
| [Competition data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Existing mirror hashes verified locally. | No organizer download/authentication this session. |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Review link retained. | Not fetched; current eligibility, limits and deadline unverified. |
| [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official-source review link retained. | No new archive or literature verified from this host. |
| [GDR INGENIOUS 1391](https://gdr.openei.org/submissions/1391) | Existing local derived layers and historical download receipt retained. | Receipt is historical; not a fresh availability check or proof of independent ground truth. |

The target is fault prediction relevant to geothermal exploration, **not a
validated geothermal-vent detector**. A magnetic/gravity boundary is not evidence
of permeability, fluid temperature, or a commercially usable resource. Future
literature review should test these causal links, not infer them from DTI.

## Reproduce

```bash
python -m venv .venv
.venv/bin/pip install numpy scipy rasterio pytest shapely pyproj
python scripts/restore_public_mirrors.py
.venv/bin/python scripts/prepare_data.py
python scripts/review_priority_sites.py
.venv/bin/python scripts/audit_priority_recipes.py
.venv/bin/python scripts/check_novelty.py data/raw/registry/32.tif \
  --registry docs/research/priority-site-pins.json --stage dots \
  --output docs/research/h33-historical-duplicate-audit.json
# Expected exit 2: historical reference is a duplicate, not a new submission.
.venv/bin/python -m pytest -q
```

Negative evidence is a deliverable. Do not spend a slot until a lane is explicit,
a complete registry passes surface AND final-dot checks, feature canaries are
clean, and a reproducible same-protocol baseline is beaten with uncertainty
reported. Even then, promotion is research eligibility; actual slot allocation
is a separate selector step using the current submission-page cap.
