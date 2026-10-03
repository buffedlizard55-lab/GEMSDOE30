# EDGE emitter holdout — registered result

**Registered before running:** [`emitter-opt-preregistration.md`](emitter-opt-preregistration.md)
**Machine-readable results:** [`emitter-opt-holdout.json`](emitter-opt-holdout.json) (run A),
[`emitter-opt-holdout-convergence.json`](emitter-opt-holdout-convergence.json) (run B)
**Code:** `src/gemsdoe30/emitter_opt.py`, `src/gemsdoe30/fields.py`,
`scripts/emitter_opt_holdout.py` · **Tests:** `tests/test_emitter_opt.py`, `tests/test_fields.py`

## Question

The published index is `DTI = T/(0.2(T+F)+0.8G)` with a 300 m triangular kernel. A dot of credit
`k` pays for itself iff `k > 0.2s/(1−0.2s)`. Given one belief field, does a **metric-exact**
emitter — greedy on expected marginal credit `dT(x) = Σ_δ π(x+δ)·max(0, k(δ) − C(x+δ))`, stopped at
that exact threshold — beat the belief-ordered emission families this project has been shipping
(uniform Poisson-disk thinning, confidence-adaptive thinning, dense quantile selection, and
`emission.metric_optimal_emission`)?

## Frame (frozen)

* Whole 8-connected catalogue components split deterministically (seed 31, 32-px interleaving tiles)
  into a stand-in **hidden** half (20,870 px, the local stand-in for "new faults") and a **known**
  half (40,118 px). Catalogues: 60,988 px total; scored domain 5,127,255 px.
* Every metric term is computed with the known half masked out, exactly as the organizer masks
  USGS/INGENIOUS pixels; four spatial quadrant folds are scored separately and pooled.
* Parameter choice is **leave-one-fold-out** per family: fold *f*'s operating point is chosen on the
  other three folds and reported on *f*. Oracle (method-selected-per-fold) numbers are reported
  separately in the JSON and are not selectable results.
* Belief fields contain **only** information a competitor legitimately has — known traces and free
  official external layers — never the hidden half:
  * `proximity` — `exp(−d/1 km)` around known traces, cut at 3 km.
  * `external` — `exp(−d/0.7 km)` around USGS SGMC fault linework + GDR paleo-geothermal + 2 m
    temperature probes + Quaternary volcanics, cut at 2.1 km. (Qfaults excluded: 59,037 of its
    59,065 px sit on the training catalogue, so it is a copy of the answer key.)
  * `hybrid` — geometric mean of the two.
  * `gbm` — the published OOF GBM emission diffused with a 1.5-px Gaussian. **Leak-contaminated**
    (the shipped model trained on the whole catalogue, hidden half included) and included only to
    compare emitters on one identical field.

## Run A — 80,000-dot cap

Pooled cross-validated DTI at each family's leave-one-fold-out choice (best per family in bold):

| family | proximity | external | hybrid |
| --- | ---: | ---: | ---: |
| **edge** | **0.18754** | **0.15784** | **0.18368** |
| adaptive | 0.13848 | 0.14015 | 0.14014 |
| uniform | 0.12466 | 0.12994 | 0.12535 |
| dense | 0.05951 | 0.10321 | 0.07429 |
| metric (existing) | 0.03107 | 0.09171 | 0.06047 |
| **edge margin** | **+0.04906** | **+0.01768** | **+0.04354** |
| folds won (edge vs best other) | 4/4 | 3/4 | 3/4 |

The registered gate — edge ≥ +0.005 over the best other family **and** wins ≥ 3/4 folds — is met on
all three fields. The EDGE sweeps hit the 80,000-dot cap on all three, so the *reported operating
points were cap-limited* (`IR-30-041`); run B re-ran the same frame with a 160,000-dot cap.

## Run B — 160,000-dot cap (convergence) and the leak-contaminated field

| field | edge | cap reached? | pooled CV peak | best other | margin |
| --- | ---: | --- | --- | ---: | ---: |
| proximity | **0.19125** | accepted 160,000 (cap) — but the **choice is interior** | peak at keep = **100,000**; 0.19092 at 110k, 0.18433 at 160k | 0.13848 | **+0.05277** |
| hybrid | **0.18368** | accepted 152,004 — the marginal rule stopped on its own | plateau 70k–80k (0.18493 / 0.18496), declines to 0.16641 at 152,004 | 0.14014 | **+0.04354** |
| gbm (leaked) | 0.11834 | accepted 114,570 — stopped on its own | — | **adaptive 0.13326** | **−0.01491** |

Two findings matter as much as the win:

1. **The proximity optimum is interior and the emitter's own stop is not where the score peaks.**
   Measured pooled CV rises monotonically to 0.19125 at 100,000 dots and falls thereafter, while
   the marginal rule kept accepting to the 160,000 cap. The *prefix* selection (leave-one-fold-out)
   is what finds the peak; a submission should use the measured plateau, not `accepted`.
2. **EDGE loses on the leak-contaminated model field** (0.11834 vs adaptive 0.13326, −0.01491).
   The GBM field is a diffusion of an already distance-thinned emission: its support already encodes
   a spacing, and re-optimising credit over it concentrates dots rather than re-spacing them. EDGE is
   therefore validated for **geometry/evidence-derived belief fields**, not as a universal
   replacement for thinning a model emission. This negative is reported here deliberately; it caps
   what the result can be used to claim.

## Candidate artifact built from the frozen recipe

`docs/downloads/gemsdoe30-edge-hybrid-80k-02845bd4-nan.tif` — SHA-256
`f87d3fc008230ec12a2b2ad260de643d15b8e474135d28020dafd2c784d2cbd5`, 592,782 B, sidecar
`…-nan.json`:

* 80,000 dots (inside the hybrid field's leave-one-fold-out plateau), **0 dots on the training
  catalogue** — masked pixels would be deleted from every metric term;
* binary 0/1 support (the metric-optimal shape: a graded map is strictly dominated by its own
  thresholded support);
* full-catalogue proxy DTI `0.1779398` — reported for provenance only, **not a score** (IR-30-039);
* published-format validation passed: single float32 band, EPSG:32611, exact 100 m template grid,
  finite [0, 1] inside the footprint, NaN outside.

## Limits — what this result does and does not license

* The stand-in hidden truth is *half the same catalogue*. It measures whether a rule places dots
  where a withheld piece of the same fault **system** lies. It cannot measure coverage of faults the
  catalogue lacks, which is what the competition scores. The margins are proxy margins.
* Absolute values here are **not comparable** with the earlier registered `uniform 0.18675` /
  `adaptive 0.18927` numbers from `scripts/metric_emission_holdout.py`: different frame (per-fold GBM
  surfaces, quadrant scoring) whose inputs (`data/processed/*.npy`) are absent in this environment.
  Only same-frame comparisons are made above.
* The proximity field encodes a geological statement the organizers endorse in part
  (clarification 11536: a "new fault" may be newly mapped geometry of an existing system); it is not
  evidence that most hidden faults lie near the catalogue.
* `expected_dti_at_sweep` in the JSONs (0.39–0.64) is the emitter's *model-consistent* expectation,
  not a measured index, and it is systematically optimistic — compare it with the measured 0.19.
* No weekly submission slot is requested or justified by this report. The candidate is offered as a
  published-format, unpromoted research artifact for the owner's decision.

## Reproduce

```bash
PYTHONPATH=src python scripts/emitter_opt_holdout.py                                  # run A
PYTHONPATH=src python scripts/emitter_opt_holdout.py --fields proximity,hybrid,gbm \
    --max-dots 160000 --prefix-step 10000 \
    --output docs/research/emitter-opt-holdout-convergence.json                        # run B
PYTHONPATH=src python scripts/build_edge_candidate.py --field hybrid --keep 80000 --max-dots 200000
PYTHONPATH=src python -m pytest tests/test_emitter_opt.py tests/test_fields.py -q
```
