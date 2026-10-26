# Executive review — 26 October 2026

## Decision first

**OK to download existing format-valid research TIFFs. NOT cleared to submit. No new TIFF generated this session.** This is a negative, audit-only deliverable, not a claim of a better model. The prompt supplies no identifiable single-method lane paragraph; assigning ourselves a new lane would violate the parallel protocol. Complete parallel surfaces and an identical-protocol best-model comparison are also missing. Zero experiments and zero weekly slots were used.

Current bytes were reopened with the shared `gemsdoe30.submission` validator against the SHA-pinned owner-mirror template. Both H-NEARSPLAY and MSDB-1v2 pass format and SHA checks: [machine report](readiness.json). Neither is approved. These checks do not rerun training, holdout, canaries, or novelty. Template provenance remains an owner mirror, not organizer authentication.

## Nine-site executive summary

**All numerical performance claims in the table are owner-reported and unverified, NOT HOLDOUT-DTI or ORGANIZER-CONFIRMED.** They are retained only to prioritize receipt acquisition, not as scores we can certify. No submission-page receipts bind them to file hashes. “Leader” means highest claim in the supplied list for that site, not a selected competition entry. Each site needs a receipt, exact artifact hash, full novelty checks and comparable holdout evaluation before selection.

| Site | Highest supplied claim (unverified) | Artifact named by owner | Interpretation / action |
|---|---|---|---|
| [24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | 0.2477 | h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan | Dotted legacy family; do not confuse with newer negative geothermal-lineament run. |
| [25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | 0.2600 | dotted-h19-5-d2-8-20261002-e56ea318af89-nan | Spacing change is not a new geological mechanism; check aliases before selection. |
| [27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | 0.2449 | topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan | Gap closure claim exceeds its newer supplied hydrothermal-piedmont result; no authenticated receipt. |
| [28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | 0.2710 | h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan | Highest supplied site claim; small differences among related variants need paired evaluation. |
| [30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | 0.2600 | d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca | Legacy reference, not the later MSDB or annulus artifact. No verified high-score approval. |
| [31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/) | 0.2708 | h27-4-solo-d28-20261004-8acb75e1-nan | Related to site 28 solo lineage; site/name differences do not prove uniqueness. |
| [32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | 0.2778 | h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros | Highest supplied nine-site claim; prioritize receipt acquisition, not upload. |
| [33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | 0.2632 | h33d-analog-tip-stepover-r30-20261004-cb490425926e | Tip/stepover mechanism already represented; do not propose it as untried. |
| [36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/) | 0.2750 | anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros | Second-highest supplied nine-site claim; PINN name alone is not evidence of physical generalization. |

The [25 October byte-inspection snapshot](../2026-10-25/priority-site-public-snapshot.json) is archived evidence, not today's inventory. [Today's GitHub main pointers](public-heads.json) were fetched independently; they establish repository revisions only. They do not authenticate website statements or organizer scores. Direct official non-GitHub hosts are unavailable from this sandbox. No current leaderboard ranking, rules PDF, weekly quota or submission receipt was fetched here. Conflicting leader claims in the prompt must not become a current-score feed.

## Why H33 plausibly improved, and what is not established

The [stored recipe reconstruction](../2026-10-25/recipe-reconstruction.json) and [prior forensic review](../msdb-piedmont/review.md) report H33 as the solo d2.8 dot set minus dots within two pixels of catalogue faults. This is postprocessing lineage, not evidence for a new geothermal-vent detector. Under the repository's max-pooled triangular kernel, clustered predictions can add penalty mass without proportional recovery; thinning and near-catalogue exclusion can improve this trade-off. However, exclusion can also discard real unmapped parallel strands. Exact reconstruction establishes an operation, **not why hidden-label performance changed**. Prior prose asserting that all removed points were false positives or retained a specific hidden-label recall is unsupported without hidden labels and is not adopted here.

Can we beat the owner's H33 claim? Possibly, but neither a catalogue-proxy win nor mathematical motivation establishes that. A better ranker must recover additional hidden geometry at acceptable false-positive cost. No projection is a score. Mapping fault geometry is this competition's immediate target; identifying active geothermal vents is a separate inference requiring independent thermal/flow evidence.

## Four proposed hypothesis refinements — frozen before any execution

Ranking below is qualitative expected value / cost, not projected DTI. These exact conjunctions are proposals; novelty across private parallel lanes is UNKNOWN. None is authorized for execution without lane allocation. Search of existing local work reveals extensive use of magnetic tilt, curvature, radiometry, lineaments, texture displacement and piedmont ramps: merely renaming these is not novelty.

| Rank / cost | Specific layers and transform | Physical signature and missing-catalogue rationale | Difference and non-fault mimic |
|---|---|---|---|
| 1 / medium | Cached magnetic anomaly derivatives plus total-count radiometry and DEM; compare opposite-normal magnetic residual profiles after fitting smooth lithologic transitions, then require radiometric residual consistency | A narrow demagnetized core with bilateral intact flanks could reveal covered hydrothermal fault damage lacking a mapped scarp | Residual core-vs-flank **model comparison**, not existing tilt/Hessian strength or profile-displacement lag. Mimic: altered volcanic flow margin or intrusive contact. |
| 2 / medium | Cached gravity anomaly, basement depth and DEM; detrend each locally, estimate cross-slope asymmetry with a null matched for regional gradient | A one-sided buried basement step beneath a smooth fan surface could indicate a concealed normal fault | Conditional signed asymmetry after local trend removal, not existing magnitude/coherence ramp gating. Mimic: sedimentary basin margin with no fault. |
| 3 / high | Cached magnetic and gravity derivatives; ridge-normal curvature with multiscale phase-consistency residual after subtracting shared regional gradients | Consistent opposite-polarity derivative lobes across scales could identify a narrow buried structural boundary despite absent surface expression | Explicit polarity/scale null model rather than generic lineament agreement; differs from existing texture lag. Mimic: dike or lithologic boundary. |
| 4 / medium | Cached DEM and total-count radiometry; compare paired upstream/downstream residuals along relief-matched drainage normals | A localized repeated cross-drainage break may expose a subtle fault trace not included in mapped inventory | Hydrology-conditioned discontinuity test rather than global scarp amplitude. Mimic: paleoshoreline, road cut, stream terrace. |

All are conditional on restoring the existing pinned cached stack and confirming its band schema; none needs newly proposed external data. Current checkout lacks training stack/cache, and no performance claim is made. Existing free owner mirrors are integrity-pinned but not official provenance. Official source for underlying magnetic/radiometric acquisition: [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and). Official competition reference: [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution). GitHub HEAD was reachable at `aebe92f7c8a990f0e3443451b7a825d9afd6336b`; this does not verify inaccessible source hosts or new layer availability.

## Next scientific execution, after blockers resolve

1. Obtain an explicit lane and complete registry including continuous surfaces. Restore the pinned stack/cache; verify hashes and band semantics, never template prediction values as features.
2. Freeze candidate 1, matched nulls, folds and bounded transform support. Use `gemsdoe30.holdout`, not a private evaluator. Whole fault components must be hidden with a buffer larger than feature support; all catalogue features derive from visible faults only. Mask visible faults pixel-exactly.
3. Run every feature alone as a leakage canary. AUC above the protocol threshold stops investigation until explained. Evaluate candidate and **current best on identical withheld positives**, dot budget, mask and evaluator. Report pooled HOLDOUT-DTI, evaluator version, withheld-positive count, and paired spatial-block confidence interval.
4. Enforce both continuous-surface and final-dot duplicate stops. A failed novelty gate ends the attempt, not an invitation to jitter dots. At most three experiments or two hours. Only a positive paired interval against current best can advance to the separate slot selector.

## Three-pass verification and limitations

- Pass 1: inspected README, agent instructions, current pointers, run cards, shared readiness/writer code and public-registry review. Restored only pinned labels/template; reopened both primary TIFFs and checked SHA identities. No new raster built.
- Pass 2: found README claiming both artifacts passed all gates despite MSDB's recorded negative readiness; added an overriding dated decision and corrected its current description. Added regression tests ensuring format validity cannot approve a slot and missing evidence stays unapproved.
- Pass 3: reran the complete test suite and the dedicated review command. Machine receipt and test counts are recorded in `verification.json`. Linked the dated review from landing and submission-guide pages. Existing historical prose/receipts remain archival; no historical scientific result was silently rewritten.

Unmet requests are explicit: no newly generated unique TIFF, no new holdout execution, no organizer-confirmed best submission, and no full literature-source verification. These cannot honestly be reported complete under the missing-lane and registry constraints. No automated competition portal access or upload is implemented.
