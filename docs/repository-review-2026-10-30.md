# GEMSDOE30 repository review — 2026-10-30

## Executive decision

**NEGATIVE: no TIFF is approved to download and submit. No new TIFF, score forecast, or competition submission was produced.** I did not start a geological experiment or select a weekly slot. The repository's active continuation instructions keep the duplicate stop in force, while this session has no assigned method lane and no organizer-authenticated training feature/label stack for a fresh holdout.

This review is a repository audit, not a fresh review of the live competition page or of all parallel GEMSDOE websites. The nine historical rasters were reopened from SHA-pinned public GitHub mirrors and audited against the repository's pinned witness. The historical score numbers are **owner-reported, not ORGANIZER-CONFIRMED**. No new submission score estimate is defensible. Machine-readable run card: [`docs/repository-review-2026-10-30-card.json`](repository-review-2026-10-30-card.json).

## Answer about GEMSDOE32 H33-B2 (reported 0.2778)

The repository's byte-level lineage audit is consistent with progressive thinning: an earlier D2.8 raster (44,090 dots) was reduced to an r1 raster (40,199 dots), then H33-B2 (37,654 dots) by removing mapped-catalogue-adjacent dots. The plausible mechanism is a precision/false-positive trade-off: removing redundant or low-value cells can reduce the metric's false-positive cost while preserving enough distance-kernel support around withheld faults. This is a **mechanistic hypothesis, not a demonstrated causal explanation** for the reported score: the hidden labels, an organizer submission receipt tying the raster to a score, and an identical controlled ablation are not present here. We cannot establish that H33-B2 beat its parent by the stated amount or predict a score above 0.2778.

The inspected H33-B2 raster contains 37,654 positive cells. It fails this repository's shared published-format validator because 7,111,787 cells outside the template footprint are finite zeros rather than null/NaN/nodata. That validator result is local format evidence; it does not establish why a portal might report a range error. The precise cause of the historical portal error remains unconfirmed without the exact rejected bytes and organizer receipt.

## Nine-site executive inventory

Numbers in the “historical claim” column are owner-supplied values captured in a frozen manifest. They are not a score estimate for a new file, not HOLDOUT-DTI, and not organizer-confirmed. A new score estimate is deliberately **unavailable**.

| Site | Audited historical raster | Historical claim (unverified) | New score estimate | Unique / acceptable to submit? |
|---|---|---:|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | 0.2477 | Not available | **No clearance.** 60,022/60,069 dots (99.922%) fall within 3 px of the pinned witness; format passes. |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | 0.2600 | Not available | **No clearance.** 44,053/44,090 (99.916%) within 3 px; exact in-footprint value alias with GEMSDOE30's audited raster; format passes. |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | 0.2449 | Not available | **No clearance.** 61,281/61,328 (99.923%) within 3 px; format passes. |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | 0.2710 | Not available | **No clearance.** 37,626/37,660 (99.910%) within 3 px; format passes. |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | 0.2600 | Not available | **No clearance.** 44,053/44,090 (99.916%) within 3 px; exact in-footprint value alias with GEMSDOE25; fails outside-footprint nodata check. |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | 0.2708 | Not available | **No clearance.** 40,166/40,199 (99.918%) within 3 px; format passes. |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | 0.2778 | Not available | **No clearance.** 37,622/37,654 (99.915%) within 3 px; fails outside-footprint nodata check. |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | 0.2632 | Not available | **No clearance.** 41,829/41,865 (99.914%) within 3 px; fails outside-footprint nodata check. |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | 0.2750 | Not available | **No clearance.** 38,822/38,854 (99.918%) within 3 px; fails outside-footprint nodata check. |

The overlap figures above are final-dot comparisons against one pinned 13GEMSDOE lattice raster, using the repository's strict `>70% within 3 px` stop. They do **not** prove the nine rasters are all exact copies of that lattice. The lattice itself covers almost the entire valid footprint, making this witness poorly discriminating (IR-30-097); nevertheless, the current repository policy requires the stop to be honored. The audit also records an exact in-footprint value alias between the GEMSDOE25 and GEMSDOE30 selected rasters. No row is approved as pairwise unique across the full, changing parallel registry. The pre-placement continuous-surface checks are not available for these historical outputs.

Auditable source of every row and measurement: [`docs/research/2026-10-28-priority-audit.json`](research/2026-10-28-priority-audit.json), generated by [`scripts/audit_priority_readiness.py`](../scripts/audit_priority_readiness.py). That audit is explicitly limited to nine frozen references, not the full parallel registry or a live leaderboard.

## Additional high-risk artifact checks

I re-ran the shared `audit_artifact_overlap.py` implementation on the two 2026-10-29 files whose names imply uniqueness:

- `GEMSDOE30-concealed-geothermal-unique-20261029.tif` (SHA-256 `b319577b30e9d1d238abc00ee8fad5a389794962c6bc60db11c24a363fdcff73`): **99.8317%** of 29,707 dots are within 3 px of the pinned lattice; duplicate stop triggers. It is not cleared.
- `GEMSDOE30-geothermal-unique-20261029T165045Z-3995629e.tif` (SHA-256 `ac941748f450b94f2783cc612c5e26046104d22e07fb72049967c94bfb166a84`): **99.9068%** of 9,652 dots are within 3 px of the pinned lattice, and **100%** overlap within 3 px with each of two earlier geothermal-corridor rasters; duplicate stop triggers. It is not cleared.

These current measurements confirm the negative decision. Audit output was written only to `/tmp`; tracked research evidence was not rewritten. Names and format validity do not prove uniqueness or eligibility.

## Unexecuted hypothesis shortlist (proposals only)

I did not start any candidate: no lane is assigned, the training stack is missing, and the experiment cap/stop receipts apply. The prior dated repository review lists four proposals after searching the local code/register. “Unexecuted” here means not found as the exact tested transform in this repository; it is **not** a claim that no other GEMSDOE site or team has tried it. Expected DTI is unknown for all four; no projection is a score.

| Priority (qualitative) | Layers and targeted signature | Why it may find an unmapped fault | Main non-fault mimic | Access / cost / status |
|---|---|---|---|---|
| 1 — cheapest first test | Cached detrended elevation + TMI; 0.5–2 km difference-of-Gaussians band-pass energy | Fault-scale, low-relief structures can persist at wavelengths missed by existing broad curvature/edge features | Volcanic-flow boundary or lithologic contact | Owner mirror contains bands but is not organizer-authenticated; low implementation cost; not tested locally. |
| 2 — larger potential, high cost | USGS Great Basin 3-D temperature model v1.1; depth-gradient and isotherm-bending discontinuities | Fault-controlled fluid circulation can perturb conductive gradients without a surface trace | Conductive lithologic contrast or model smoothing/artifact | Official ScienceBase/DOI listing is recorded in the prior review; actual retrieval/alignment was not verified here and outbound host access is restricted; high cost. Leakage/circularity review needed. |
| 3 — blocked pending independent validation | Qfaults linework attributes; slip-sense/rate-consistent gap completion | Kinematically coherent segments may extend structures absent from the current catalogue | Non-fault mapped linework / correlated source catalogue | Pinned owner mirror exists, but Qfaults overlaps INGENIOUS/USGS labels, making catalogue holdout circular; medium cost; do not score without independent truth. |
| 4 — presently not viable | Strain-rate tensor components; compare principal-axis orientation with lineament strike | Faults may localize along the regional extension direction | Interpolated broad geodetic strain or hydrologic deformation | No verified tensor-component source identified in the repository; unavailable/blocked until data source and coverage are verified; medium cost. |

The ordering is a *work-priority heuristic* (data availability and implementation cost), not a quantitative expected-DTI ranking. Candidate details and prior source checks are in [`docs/research/2026-10-29-session-review.md`](research/2026-10-29-session-review.md). The correct first gate for any future lane is still feature-alone leakage canaries followed by the shared buffered holdout and paired CI; hypotheses cannot be promoted from plausibility alone.

## Three review passes

### Pass 1 — repository and evidence inventory

- Read `AGENTS.md`, the current README mission/owner-prompt section, `docs/current-run.json`, `docs/status.json`, the latest dated repository review, and the nine-site frozen audit.
- Confirmed branch `arena/537d0f2b-gemsdoe30`, clean tracked worktree at start, and no feature/label training stack in the checkout. Restored only SHA-pinned owner-mirror `sample_submission.tif`, the pinned lattice witness, and the nine small historical rasters to ignored `data/raw/` for offline validation. These owner mirrors are not organizer-authenticated.
- No DrivenData login, leaderboard scrape, score claim, experiment, candidate generation, or slot-selection action was made.

### Pass 2 — reproduce high-risk gates and test failure modes

- `scripts/audit_priority_readiness.py --restore-only` followed by `--check`: **passed**; independently reopened the nine frozen rasters and reproduced the stored audit. It found no new raster, score estimate, or approval.
- `scripts/verify_registry_preflight.py`: **exit 0, VERIFIED NEGATIVE**; reproduced the strict lattice duplicate stop (minimum 37,441/44,090 dots for the historic CSR reference) and no-submission decision.
- `scripts/audit_artifact_overlap.py` on the two 2026-10-29 candidate-named TIFFs: **both duplicate-stopped** as detailed above.
- `scripts/build_research_site.py --check`: **passed**; generated pages and receipts are deterministic and consistent with current source evidence.
- Full test suite after restoring the nine historical rasters: **412 passed, 37 skipped, 4 warnings, 7 subtests passed**. Skips are data-gated cases requiring absent labels/catalogues/references or optional Torch; four warnings are Rasterio pending deprecations. No failures.

### Pass 3 — requirements and release-readiness review

- Rechecked the request's hard requirements against the repository: no approved download, no score forecast presented as a score, no weekly slot selected, and clear separation of local format validation from scientific promotion/organizer acceptance.
- Confirmed the nine-site table uses exact SHA-pinned historical bytes and labels claimed scores as unverified; confirmed a new score cannot be measured without valid shared holdout inputs.
- Confirmed all generated `data/raw/`, Python environment and caches are ignored; no temporary audit files were added to Git. Final decision remains **negative**. No generated TIFF is safe to offer as “OK to submit” on current evidence.

## Findings, limitations and next actions

1. **Submission blocker:** no candidate passes both the shared leakage-safe holdout promotion gate and complete two-stage uniqueness registry checks. Do not submit a listed historical raster or either candidate-named 2026-10-29 artifact.
2. **Data blocker:** `training_features.tif` and `labels.tif` are absent. The locally restored sample template and owner mirrors are not organizer-authenticated; a fresh HOLDOUT-DTI cannot be defensibly computed from them.
3. **Protocol blocker:** no single current method lane is assigned, and prior experiment caps/stop receipts in `AGENTS.md` remain in force. Do not quietly start a new experiment, change the lane, or re-encode a stopped output.
4. **Novelty-policy blocker:** the pinned lattice covers nearly all valid pixels within 3 px, so its overlap stop is not discriminating. Do not bypass the literal current rule; resolve the witness/policy consistently in a selector/governance step before trying another dense submission. A smaller dot budget is not an automatic pass.
5. **Score provenance:** H33-B2's 0.2778 and other historical figures remain owner-reported. The previously checked public leaderboard snapshot is dated 2026-10-29, not current to this review date; live rank and the owner's conflicting 0.3195/0.4413 claims remain unverified here.
6. **Format nuance:** the four all-finite-zero-outside historical rasters fail the repository's null-outside-template check. This is not proof of the portal's exact range error. The sample-submission contract and the portal's precise nodata behavior should be resolved using an authorized organizer receipt and exact rejected file.
7. **Registry scope:** the nine-site byte audit and local `docs/downloads/` comparisons do not constitute a complete, current parallel-run registry. Pre-placement surfaces for the nine historical sites were not preserved in the audit, so surface-stage uniqueness is unverified.
8. **Next safe sequence:** restore organizer-authorized data with provenance; assign a single lane and freeze controls/folds; run each feature's leakage canary; spend no more than the specified experiment/time budget; require paired pooled HOLDOUT-DTI CI lower bound above zero against the frozen best; then screen the continuous surface and final dots against a complete registry; validate the exact written TIFF; finally let the separate weekly-slot selector decide. Only an organizer receipt may be called ORGANIZER-CONFIRMED.

## Source links for manual review

- [Official competition overview and problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Official competition data page (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN airborne magnetic/radiometric data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [Competition report / submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [EPSG:32611](https://epsg.io/32611)

Links are pointers for verification; the non-GitHub sources and live leaderboard were not freshly fetched in this session because outbound access is restricted. Exact local artifacts and the reproduced audit are cited above.

## Run card

```json
{
  "hypothesis": "No new hypothesis was tested: no lane was assigned and no leakage-safe training/holdout stack was available. For H33-B2, the unverified proposed mechanism is that removing low-value/catalogue-adjacent dots reduces false-positive cost while retaining enough 300 m-kernel support; causality is not established.",
  "mechanism": "Zero-experiment repository review; reopened nine SHA-pinned historical rasters, reproduced the registry preflight, site-build check, and tests; no prediction surface or raster was created.",
  "named_non_fault_process": "Not evaluated for a new candidate. Known potential mimics in the pre-existing research include Lahontan shorelines/terraces, volcanic flow fronts, and lithologic contacts; none was tested here.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "evaluator_version": null,
  "withheld_positives": null,
  "correlation_overlap_vs_registry": {
    "new_candidate": "not applicable; none generated",
    "nine_historical_rasters_vs_pinned_lattice": "each exceeds the literal >70% within-3-px dot stop; range 99.910% to 99.923%",
    "pr76_named_unique_artifact_vs_lattice": 0.9983168950079105,
    "pr78_named_unique_artifact_vs_lattice": 0.9990675507666805,
    "pr78_vs_prior_geothermal_corridor_dots": 1.0,
    "surface_stage": "not checked for historical artifacts"
  },
  "raster_sha256": null,
  "validator_output": "No new raster. Historical format audit: GEMSDOE30, 32, 33, 36 fail null-outside-footprint; other five pass local format validator. No organizer acceptance is implied.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "ok_to_download_and_submit": false,
  "experiments_run": 0,
  "slot_selected": false,
  "tests": "412 passed, 37 skipped, 4 warnings, 7 subtests passed",
  "irregularities": ["IR-30-088", "IR-30-089", "IR-30-097", "IR-30-098"]
}
```
