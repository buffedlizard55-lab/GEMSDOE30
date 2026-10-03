# Emitter comparison: where the mass goes matters more than how it is learned

Two holdout frames ask how to place prediction mass under `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`. Artifacts: [`emitter-comparison.json`](emitter-comparison.json) (catalogue frames), [`novelty-holdout.json`](novelty-holdout.json) (SGMC independent-inventory frame), and [`discovery-shift.json`](discovery-shift.json) (truth-density and clustering sweeps).

**Count convention:** Frame 1’s `global dots` is the footprint-wide emitter count. Frame 2 reports both the global emission budget and the pixels active in the masked scoring domain. Equal global budgets in Frame 2 are **not** equal active-domain counts; the full audit is in [`novelty-holdout.md`](novelty-holdout.md). None of these proxy DTI values is a competition score.

## Frame 1 — the catalogue (proxy only, structurally limited)

`scripts/emitter_comparison.py`. Truth is the public catalogue; regimes are the full catalogue, a random 25% of catalogue components hidden with the removed pixels excluded from scoring, and truth confined to 3 km discs. The table’s `global dots` column is measured before each scoring regime’s mask.

| emitter | global dots | full catalogue | thin 25% | 3 km clusters |
|---|---:|---:|---:|---:|
| `lattice_4px` (blind) | 323,245 | 0.24634 | 0.08008 | 0.03688 |
| `lattice_5px` | 206,895 | 0.24525 | **0.09138** | 0.04234 |
| `model_poisson_4px` (combined OOF, 4 px) | 309,492 | **0.25461** | 0.08356 | 0.03792 |
| `model_t0.4_s4px` (threshold 0.4, then 4 px) | ~80k | 0.22007 | 0.10451 | 0.05825 |
| `model_t0.4_s4px` off-catalogue (`cand_t04s4`) | 80,392 | 0.00165 | 0.00096 | 0.00047 |
| historical D2.8 artefact (0.2600 attribution unresolved) | 44,090 | 0.16177 | **0.11305** | **0.05800** |
| `inventory_*` (SGMC off-catalogue dots) | ≤17,077 | 0.00037 | 0.00026 | 0.00011 |

Three conclusions, with scope:

1. Converting this model surface to sparse dots has a large effect on these *catalogue proxy frames*: the raw OOF probability mosaic scores 0.09712, while the 4 px Poisson emitter scores 0.25461 on the same full-catalogue frame. This is a measured emitter comparison, not evidence of private-test improvement.
2. At roughly comparable global counts, the 4 px model emitter (309,492 dots) is above a 4 px blind lattice (323,245) by 0.00827 DTI on this frame. The effect is modest and proxy-specific.
3. Catalogue frames cannot rank off-catalogue strategies: `cand_t04s4` intentionally avoids catalogue pixels and therefore scores about 0.002 against catalogue truth. Frame 2 uses a separate inventory, but it still is not the expert-labelled competition test set.

## Frame 2 — SGMC independent-inventory proxy

`scripts/novelty_holdout.py` hides 30% of connected SGMC components (1,679 total) and excludes a 3-pixel dilation of visible catalogue faults from the scoring domain. The five-repeat score means and both count scopes are:

| emitter | global N | active N in scored domain | mean DTI | range |
|---|---:|---:|---:|---:|
| `cand_t04s4` | 80,392 | **80,388** | **0.09526** | 0.08380–0.10483 |
| `blind_random_80392` | 80,392 | **73,843** | 0.07617 | 0.07268–0.07967 |
| `cand_gbm` | 90,358 | **75,001** | 0.07279 | 0.06848–0.07885 |
| `blind_random_75001` | 75,001 | **68,848** | 0.07460 | 0.07237–0.07612 |
| `cand_hedge` | 85,526 | **85,526** | 0.18343 | 0.17391–0.19114 |
| `blind_random_85526` | 85,526 | **78,512** | 0.08110 | 0.07851–0.08630 |
| `lattice` | 574,329 | **527,504** | 0.09395 | 0.08901–0.09966 |
| `model_probability_dots` | 568,942 | **506,746** | 0.09498 | 0.08966–0.10078 |
| historical D2.8 artefact | 44,090 | **35,824** | 0.07061 | 0.06640–0.07355 |
| `visible_inventory_dots` | varies by repeat | **3,507 mean** | 0.00121 | 0.00101–0.00168 |

The positive `cand_t04s4`/random result is **matched on global N only**: the global budget is 80,392, but active scored-domain counts are 80,388 and 73,843. The +25.1% relative DTI difference is a frozen global-budget screen, not an active-count-matched estimate of score-ordering benefit. The `cand_gbm`/random comparison is unmatched globally and in-domain (90,358/75,001 versus 75,001/68,848). The 85,526-dot SGMC hedge directly uses SGMC, so its score against held-out SGMC traces is tautological and cannot validate the hedge.

The historical comparison does not recreate the archived `cand_t04s4` mask and has no fresh-seed paired confirmation. These count-scope limitations do not authorize a rerun on already-inspected SGMC labels. Future placement claims must report both counts and use a fresh, independent holdout; if the question is placement at equal active mass, match the active scored-domain count.

## Frame 3 — truth-set shift

`scripts/discovery_shift_analysis.py` re-scores OOF mosaics under density thinning, clustered truth, and a blind 4 px lattice. Under the organizer-style mask:

| truth realisation | regional model field | combined model field | blind lattice 4 px |
|---|---:|---:|---:|
| full catalogue | 0.10503 | 0.09712 | 0.24634 |
| 50% density | 0.05738 | 0.05270 | 0.14670 |
| 25% | 0.02970 | 0.02735 | 0.08188 |
| 10% | 0.01217 | 0.01118 | 0.03505 |
| 4% | 0.00491 | 0.00452 | 0.01451 |
| 3 km clusters | 0.00980 | 0.00878 | 0.03492 |

The lattice-to-raw-field gap widens as this synthetic truth gets sparser. This is a density-shift diagnostic, not an estimate of hidden-fault clustering. A plausible operating rule is to prefer sparse, well-placed predictions over a dense probability field, but every candidate still needs a fresh spatial holdout.

## Limitations

- The catalogue is masked out of real scoring; Frame 1 is a biased proxy. Frame 2 substitutes a state geologic-map inventory for the organizers’ expert labels. Neither is the private test set.
- Historical “same-count” comparisons refer to a fixed **global** budget unless explicitly stated otherwise. Active counts after a scoring mask can differ and must be reported separately.
- The 3 km cluster radius and density ladder are modelling choices, not measured properties of the private truth.
- D2.8’s reported 0.2600 remains unlinked to its exact TIFF. See [`leaderboard-analysis.md`](../leaderboard-analysis.md).
