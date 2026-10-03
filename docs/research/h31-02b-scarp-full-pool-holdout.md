# H-31-02b full-pool scarp-orientation screen — measured interpretation

**Decision: not promoted; no weekly slot.** The frozen preregistration and machine-readable result remain unchanged. This note records the post-run interpretation and makes the two pixel-count scopes explicit; it does not amend either artifact.

Evidence: [`h31-02b-scarp-full-pool-preregistration-2026-10-03.md`](h31-02b-scarp-full-pool-preregistration-2026-10-03.md), [`h31-02b-scarp-full-pool-holdout.json`](h31-02b-scarp-full-pool-holdout.json), and [`h31-02b-scarp-full-pool-preflight.json`](h31-02b-scarp-full-pool-preflight.json). The feature stack is an owner-derived mirror, not organizer-authenticated.

## Registered primary spatial gate — failed

The candidate emitted the exact frozen per-fold budgets **29,114 / 22,102 / 18,009 / 24,165** (total **93,390**) at 3-pixel spacing. The four fold budgets and distinct candidate/control masks passed their construction checks.

| Measure | DTI |
| --- | ---: |
| Candidate, pooled fold-local catalogue proxy | **0.1655413755** |
| Same-run uniform control, same per-fold emitted counts | **0.1348326480** |
| Candidate − uniform | **+0.0307087275** |
| Archived adaptive spatial-holdout best | **0.1892699401** |
| Candidate − archived best | **−0.0237285646** |

The candidate beat uniform in 4/4 folds and passed the candidate-vs-uniform clause, but it missed the registered primary threshold of archived best +0.005. The primary gate therefore **failed**; the positive uniform comparison does not override that clause.

## Registered strike perturbation — failed

The strike-permuted candidate scored **0.1637027764**. It removed **5.99%** of the candidate's positive gain over uniform, below the preregistered **50%** requirement. The feature-perturbation gate failed.

## SGMC screen — preregistered global budget passed, not active-count matched

The SGMC screen used the frozen **global emission budget** of **80,392 pixels** for both candidate and blind-random control. “Global” here means all emitted pixels in the valid footprint before applying the SGMC holdout scoring mask. The DTI is evaluated only on the scored domain, so the active count in that domain is a separate quantity:

| Arm | Global budget | Pixels active in scored domain | Mean DTI |
| --- | ---: | ---: | ---: |
| H-31-02b candidate | 80,392 | **72,310** | **0.1294372572** |
| Blind random control | 80,392 | **73,843** | **0.0761671325** |
| Archived `cand_t04s4` numeric baseline | 80,392 | **80,388** | **0.0952570598** |

The candidate cleared the registered numerical SGMC screen (5/5 wins over the archived per-repeat baseline; +0.0532701247 over the same-run random mean; `screen_pass: true`). But it was **not active-scored-domain-count matched** to either control. The archived baseline mask is absent, and no fresh-seed paired confirmation was run. The frozen global-budget screen result is valid as recorded; it is not evidence of an active-count-matched placement advantage and cannot promote the candidate.

Do not rerun, retune, or create a new active-count-matched comparison against these already-inspected SGMC labels. Any future confirmation needs a new, uninspected independent holdout frame or another defensible source of labels.

## Final status

`promotion_eligible: false`; the primary spatial and strike-perturbation gates failed, the SGMC result is screen-only, and no submission slot was used. This result tests the fixed reduced-stack orientation transform, not every scarp detector and not the full raw 1 m DEM matched-filter/continuity hypothesis. The latter remains untested and would require complete, source-verified DEM coverage. No holdout value here is a competition score.
