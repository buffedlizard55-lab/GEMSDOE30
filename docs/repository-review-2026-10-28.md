# Repository review — 2026-10-28

## Decision

**Negative / stop: no new submission TIFF was generated, no TIFF is approved for download or portal submission, and no weekly slot was selected or used.** This is a verification-only continuation, not a geological experiment. `AGENTS.md`, the README's current-owner prompt and decision, `docs/current-run.json`, and the latest registry-preflight and POOL-1 receipts all require a duplicate stop; the assigned single-method lane is unspecified in the prompt. Do not lower the dot budget, re-encode, rename, perturb, or otherwise try to bypass the novelty stop.

The current public-site table remains the [nine-site executive summary](priority-executive-summary.html). Its historic entries and scores are owner-reported research references, not a verified current leaderboard or an estimate for a new candidate. In particular, the claimed GEMSDOE32 `0.2778` cannot identify the hidden TP/FP contributions or prove that H33-B2's pruning caused the score. The repo's byte-lineage review supports a plausible precision/false-positive explanation only. No comparable organizer receipt is available to say a new method will exceed that value or the reported `0.3195`.

## Protocol and candidate slate

The repo already documents four ranked, differentiated hypothesis proposals in [the prior current-session review](research/2026-10-27-current-session-review.md#candidate-hypotheses--proposals-only-no-lane-authorized): polygon-conditioned map-unit concealment, buried-source-depth magnetic lineaments, drainage χ/normalized channel-steepness disequilibrium, and heat-flow/borehole-gradient corridors. Their layers, target signatures, distinctions from implemented work, non-fault mimics, source requirements, and qualitative cost ranking are recorded there. These are proposals—not globally novel claims, validated experiments, or score projections. No additional slate was invented or experiment started because the lane and novelty policy are unresolved and the experiment cap is already exhausted in parallel attempts.

Sources named in that slate include the official [USGS SGMC](https://www.usgs.gov/data/state-geologic-map-compilation-sgmc-geodatabase-conterminous-united-states), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS National Map](https://www.usgs.gov/the-national-map-data-delivery), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), and [IHFC Global Heat Flow Database](https://ihfc-iugg.org/products/global-heat-flow-database). The source availability/coverage caveats in the linked review remain in force: the necessary feature stack is not staged; some external layers are absent; and no official source archive, full-footprint coverage, licensing, or checksums were newly revalidated during this verification-only pass. A URL in a document is not evidence that its data are locally available or validated.

## Reproduced checks

The following checks were executed in this checkout on 2026-10-28. The owner-provided sample grid, labels, and 13GEMSDOE lattice witness were restored from hash-pinned public GitHub mirrors. They are explicitly **not organizer-authenticated**. The 418,912,844-byte training feature stack remains absent; no holdout was run.

| Check | Result | Interpretation |
|---|---|---|
| `scripts/verify_registry_preflight.py` | PASS as a negative | Reproduced the pinned-lattice stop: the lower-bound overlap for a 44,090-dot candidate exceeds the strict 70% threshold. This is a geometry/novelty bound, not a score or full-registry clearance. |
| `scripts/verify_pool_run.py` | PASS as a negative receipt | POOL-1's paired `HOLDOUT-DTI` improvements reproduce in the stored receipt, but its final dots breach the duplicate stop. The verifier also confirms no public POOL-1 TIFF is published. This does not make POOL-1 a selectable submission. |
| `scripts/build_research_site.py --check` | PASS | Current receipt-driven pages and the download/readiness disclosures match their source artifacts. |
| `scripts/build_status.py` | PASS | Regenerated the machine-derived status feed from repository evidence; the feed does not claim a score gain. |
| `.venv/bin/python -m pytest -q` | **424 passed, 5 skipped, 4 warnings, 7 subtests passed** | The five skips are optional PyTorch-dependent loss tests; PyTorch was not installed. The four warnings are Rasterio affine-transform pending deprecations. |
| `git diff --check` | PASS | No whitespace errors. |

For transparent context, the POOL-1 receipt records **HOLDOUT-DTI** (evaluator `component-holdout-v3-blockstats-20261025`, 60,988 withheld positives; paired spatial-block 95% CI): screen candidate 0.186699 [0.173113, 0.200171] versus same-run `msdb_edge` control 0.169468 [0.155445, 0.183465], with paired difference **HOLDOUT-DTI** +0.017231 [+0.010515, +0.023980]. Its seed-confirmation receipt records **HOLDOUT-DTI** 0.187694 [0.173631, 0.201989] versus control 0.174247 [0.160153, 0.188516], with paired difference **HOLDOUT-DTI** +0.013446 [+0.006993, +0.019757], under the same evaluator and withheld-positive count. These are catalogue-proxy results, not `ORGANIZER-CONFIRMED` scores, leaderboard estimates, or a comparison to the owner's historical H33-B2 score. Although the paired holdout gains are positive, the submission artifact is duplicate-stopped and therefore not promotable. See the [POOL-1 run card](research/2026-10-27-pool/run-card.json) for the source receipts and duplicate references.

## Nine requested sites and download status

The site-by-site table in the [executive summary](priority-executive-summary.html) records the pinned historical reference, owner-reported value, a new-score estimate marked unavailable, novelty clearance status, and whether a file is safe to submit. The answer for all nine is unchanged: **none is a cleared new candidate; do not download a historical artifact for submission.** A mathematical lower bound from one pinned lattice witness is enough to stop those listed dot budgets under the literal rule, but it is not an exact pairwise measurement for every raster or a complete global registry audit.

The latest reconciled current run is still `DUPLICATE-STOP`. No run card for a new candidate can honestly provide a raster SHA, prediction validator result, HOLDOUT-DTI, or submission name because no candidate raster was created. Machine-readable statement: [`repository-review-2026-10-28-run-card.json`](repository-review-2026-10-28-run-card.json).

## Limitations and next actions

1. **Do not generate a TIFF until there is an explicit lane assignment and a documented resolution of the novelty policy.** The prompt says “the single method paragraph below” but contains no unambiguous assigned paragraph; all new fitting/placement is blocked by that ambiguity and the existing stop.
2. Restore `training_features.tif` from the competition's authorized account/session or another explicitly authorized source; it is absent here and cannot be recovered from the login-walled competition page without credentials. No credentials were requested or used.
3. Obtain a fresh, complete, policy-approved registry and repeat surface novelty before placement and final-dot novelty after placement. The lattice witness is sufficient to stop a candidate, but never sufficient to clear one.
4. After authorization and data restoration only, preregister one candidate, re-use the shared holdout and submission modules, run feature-alone leakage canaries, use buffered whole-segment hide-and-recover with all catalogue-derived features recomputed from visible faults, and require a paired spatial-block 95% CI improvement over the same-protocol best.
5. Only after scientific and novelty gates pass should the separate selector evaluate the weekly slot cap. Portal acceptance remains unknown until an organizer receipt exists; local TIFF validation is not portal confirmation.
6. The feed is generated from local receipts and dated repository artifacts. DrivenData authentication is unavailable in this run, so the current live leaderboard and submission-page receipts are not automatically verified. The supplied changing values `0.3195`, `0.4413`, and other historical claims must not be represented as fresh confirmed standings.

## Sources for manual review

- [DrivenData competition overview and rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — login/current page not checked in this audit.
- [Official GEMS technical report / submission rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data record](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [Official IHFC heat-flow database](https://ihfc-iugg.org/products/global-heat-flow-database)

The existing [sources index](sources.html) and [hypothesis register](hypotheses.html) include additional citations and their evidence-status caveats.
