# GDX-1 outcome — new mechanism, negative evidence, no slot

**26 October 2026 UTC.** Canonical machine record: [run-card.json](run-card.json).
[Current executive summary](../../../executive-summary.html) ·
[Nine-site review](../../../priority-executive-summary.html) ·
[Preregistration](preregistration.md) · [A1 deviation](amendment-A1.md).

## Decision first

**Download OK for research; DO NOT SUBMIT.** GDX-1 failed both fixed paired
improvement criteria. No competition upload, slot selection, or organizer score.
No parameter/seed/placement rescue is allowed: conservative experiment accounting
is **3/3**, completed in **603.478 s** from the original start, including the
technical pause. This does **not** satisfy the ultimate objective of a globally
unique, high-scoring, submission-approved file. Negative results are deliverables;
pretending this one is competitive would undermine “Maximize P(Win).”

- File: [`gems30-GDX1-44090-20261026-2992ee3619f5.tif`](gems30-GDX1-44090-20261026-2992ee3619f5.tif)
- Name: `gems30-GDX1-44090-20261026-2992ee3619f5`
- SHA-256: `3d569d47f5e62e6e62586ddf940140b113d826ab85a5dc4a1642cb8f882c26ac`
- Note (118 / 140 characters): `GDX1 site-deduped, effort-normalized geothermal chemistry + local edges; 44090 dots; research only, NOT slot-approved.`
- Single float32 band, EPSG:32611, shape 3730 × 3292, affine
  `(100, 0, 243350, 0, -100, 4508550)`; finite binary probabilities on all
  5,167,373 template-footprint cells, NaN nodata outside. 44,090 dots; zero on
  or within 2 px of catalogue positives, ≥3 px dot spacing. Format checks do
  **not** prove private portal acceptance or explain the original range error.

## Hypothesis, mechanism, falsification

The frozen plan ranked four constructions before execution. Only rank 1 ran:
paired chemistry at co-measured sites, normalized by chemical observation effort,
combined with local geophysical edges. It is not a renamed vent-proximity raster
or the earlier TAD threshold on maximum chemistry. Other ranked constructions
(two-population thermal contrast, local wavelet phase agreement, scalar
strain-efficiency interaction) remain unexecuted and unscored.

Ascending fluids can cool/mix while reservoir geothermometers retain a different
signature from measured temperature. **That interpretation is a hypothesis**, not
a newly verified universal diagnostic of fault-controlled upflow. Aquifer mixing,
steam loss and contact-related non-fault circulation can mimic it; developed-field
sampling can explain apparent signal. The effort-only matched control is therefore
mandatory, not optional. The candidate did not beat it.

27,092 CSV records were deduplicated into 2,398 observed grid sites. Marks from
co-measured rows have 539 / 551 / 526 sites. Each chemical numerator is divided by
its **own** observed-site denominator; no unrelated-site normalization or
missing-as-zero measurement. Only `row`, `col`, `temp_c`, `geothermquartz_c`,
`geothermcat_c` are read. Row/column only locate site impulses, never become model
predictors. `dist_known_fault_px`, labels, IDs and thermal classes are forbidden
transformer inputs. Support is conservatively bounded at 43 px; guard=46 px
includes 3 px metric reach. Exact code/hash: [feature-receipt.json](feature-receipt.json).

## Performance: HOLDOUT-DTI, never a leaderboard score

Evaluator **component-holdout-v3-blockstats-20261025**; protocol
**buffered-quadrant-whole-components-v1-20261025**; 4 spatial folds, whole
8-connected fault components, 46 px buffer, **60,988 withheld positive pixels**.
Visible faults are masked pixel-exactly; catalogue-based construction uses only
visible faults. Pooled DTI, alpha .2 / beta .8, 300 m triangular kernel.

| Same-run arm | HOLDOUT-DTI | Spatial-block 95% CI |
|---|---:|---:|
| Core19 | 0.13690536 | [0.12095606, 0.15334760] |
| Local physics + sampling effort (effort6) | 0.12149272 | [0.10946138, 0.13475734] |
| GDX-1 (gdx12) | **0.11965057** | **[0.10769925, 0.13232384]** |
| GDX minus Core19 | −0.01725479 | [−0.03545321, +0.00176526] |
| GDX minus effort6 | −0.00184215 | [−0.00623542, +0.00265180] |

2,000 paired percentile replicates, seed 3071; 371 geographic blocks, 128 px each.
Both paired lower bounds had to exceed zero; neither did. The intervals overlap
zero, so this is **failure to demonstrate improvement**, not a claim of
statistically conclusive inferiority. These intervals are conditional catalogue
hide-and-recover uncertainty, not hidden-unmapped-fault / leaderboard uncertainty.

The 17 px archived Core19 HOLDOUT-DTI **0.13982063017811727** was reproduced within
1e−9 in a separate parity check. Do not substitute it for the 46 px control, rank
GDX against archived FFL/MSDB/TAD numbers from different protocols, or claim the
strongest comparable historical-best gate passed. That best-control reproduction
is absent. See [comparator-parity.json](comparator-parity.json).

All **28 exact inputs alone × 4 folds = 112 leakage canaries** are stored in
[results.json](results.json). Maximum bidirectional raw / train-only univariate
AUC = **0.6399607593**; 0 alarms above .90. Absence of an alarm is not proof of no
leakage. There is no probability-calibration or feature-perturbation confirmation;
the negative gate ended promotion work instead of wasting further experiments.

## Uniqueness: observed difference, global UNKNOWN

The original full-fit continuous surface was saved and audited **before any dot
placement**, independently from the final binary raster. The surface is a learned
label-based full fit, not an OOF/organizer performance measurement.

| Stage | Frozen-registry successful comparisons | Maximum rho | Maximum candidate dots within 3 px |
|---|---:|---:|---:|
| Pre-placement continuous surface | 327 | 0.1647020230 | Not applicable |
| Final 44,090 dots | 327 | 0.0917976630 | 54.24586074% |
| Additional local FFL surface | 1 | 0.0773506624 | Not applicable |
| Additional local FFL dots | 1 | 0.0202637870 | 44.53390792% |

No observed duplicate crosses rho >.90 or overlap >70%. **This is not a global
uniqueness pass.** The frozen 328-reference registry contains one pinned malformed
GEMSDOE31 source: SHA
`774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546`,
2,610,312 non-finite cells inside the template footprint. The original attempt
stopped before dots/canaries/DTI. Its code and stop were committed at `00b8509`.

A1 was documented before any placement or metric. It authorized only one exact
saved-array / saved-surface exploratory continuation; no new full fit or tuning.
The malformed reference stays unknown at both stages, never imputed and never
compared on a convenient finite subset. Private/parallel coverage and five
original-surface paths are also incomplete. The post-run local FFL audit is
explicitly an addendum, not claimed pre-placement chronological coverage. It
introduced no fit, placement, seed search, or new holdout experiment.

Original surface remains in ignored `outputs/geothermal-chemistry/gdx1-surface.tif`
(SHA `80c1c5096958fbacd5addfb5afd3563417d544663e5d7c71a052fcc67e2980be`).
The 442 MB feature array is also ignored, not added to Git. CI verifies saved
surface **receipts**, not unavailable original surface bytes; the verifier also
reopens that surface if present locally. Only the small negative research TIFF
is committed. Preserve the cache in external artifact storage before discarding
the worktree; no durable external upload is claimed here.

## Nine-site results and H33 explanation

[Machine raster audit](fleet-audit.json) binds all nine historical filenames,
source commits, byte/value hashes, format policy, pairwise diagnostics and claim
classes. [Nine-site executive summaries](nine-site-executive-summary.md) and nine
individual HTML pages expose exactly what exists. Those other repositories were
read-only sources; their sites were **not** edited.

Measured lineage: d28 **44,090** → r1 **40,199** (remove 3,891 within 1 px) → H33
**37,654** (remove another 2,545 within 2 px). Exact value aliases: G25=G30;
earlier G28 r1=G31. H33 equals the distance-pruned r1 subset. G36 adds exactly
1,200 dots. The supplied best G28 rung has 37,660 dots and is not that r1 base.

The owner reports H33 0.2778 and the G36 extension 0.2750. Precision-oriented
pruning is consistent with improved Tversky performance, because false positives
can be removed with relatively little true-positive loss. Hidden TP/FP cannot be
uniquely inverted from one scalar score. No organizer receipts authenticate those
values; no causal proof or leaderboard forecast is manufactured from related
files. The prompt's conflicting 0.3195 / 0.4413 leaders are not newly verified.
A newer G27 README's “approved” 27-reference result / ~0.235 projection is not
adopted as expanded-registry clearance.

## Shared tooling / UI repairs

TAD, current/retained artifact and stopped-attempt verifiers previously treated
additive public references as corruption of archived exact-set evidence. They now
verify every recorded addendum/identity first, preserve archived receipts, then
apply the shared `with_current_inventory` blocking UNKNOWN overlay. New research
TIFFs anywhere below `docs/`, not just `docs/downloads`, are included. Missing or
changed recorded references, forged CIs, duplicate rows and overridden decisions
still fail. No fabricated retrospective surface comparison, no silent green.

A clean receipt-driven front page replaces the stacked historical “LATEST”
banners. One obvious research download; a separate “do not submit” decision;
exact name/note copy; same-protocol CI table; source boundaries; nine pinned-site
executive reviews. Historical pages remain clearly archived. The status generator
and CI/workflow validation include GDX even though it is outside `docs/downloads`.
The original primary pointer remains PTA for compatibility; `latest_review`
selects the newest GDX report, **not** a submission.

## Reproduce and inspect automatically

```bash
python -m venv .venv
.venv/bin/pip install -e '.[research,test]' -c requirements-tdx1.txt
# Public owner mirrors, not authenticated organizer downloads:
.venv/bin/python scripts/restore_public_mirrors.py --ids sample_submission labels
.venv/bin/python scripts/verify_geothermal_chemistry_run.py
.venv/bin/python scripts/verify_geothermal_chemistry_run.py --require-promote  # expected exit 2
.venv/bin/python scripts/build_research_site.py --check
.venv/bin/python -m pytest -q
```

For full data/cache and original public references, use existing restore/prepare
commands and `sync_priority_registry.py --restore-only --output
 docs/research/2026-10-26-gdx/registry.json`. The costly experiment must **not** be
rerun: `started.json` and `resumed.json` are guards, not scratch. CI reproduces
statistics and gates, not model training. `scripts/audit_priority_fleet.py --check`
recomputes lineage only after restoring the historical nine and processed labels.

## Sources and unfinished acceptance criteria

[sources.json](sources.json) records pinned organizer-reference extracts and nine
fresh public README hashes/URLs. GDR 1391 / USGS GeoDAWN / official competition
links are maintained in the HTML and existing science ledger. Non-GitHub official
hosts were not freshly reachable under this sandbox's network policy. Older
literature facts, deadlines and physical-unit interpretations are not upgraded to
fresh verification. A point layer's sampling locations are not observed heat
anomalies; scalar strain invariants cannot recover principal-stress azimuth.

Remaining: a genuinely superior independent hypothesis; complete parallel raster
and original-surface registry; disposition of the malformed reference; externally
verified method assignment; strongest same-protocol control; calibration /
perturbation confirmation if a future candidate passes; official data / rules /
eligibility / current cap and cutoff authentication. No account credentials are
needed or requested. No statement here guarantees a leaderboard improvement.

**Next session:** read the full README prompt; freeze the assigned lane/inventory;
repair evidence provenance; restore the comparable control; only then test the
next ranked population-contrast hypothesis under a fresh budget. Do not rescue
GDX, FFL or H-NEARSPLAY by geometry perturbation or relabeling old predictions.

The three cumulative review passes, actual commands and final delivery status are
recorded in [three-pass-review.md](three-pass-review.md).
