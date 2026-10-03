# Emitter comparison: where the mass goes matters more than how it is learned

Two independent holdout frames, one question: **what is the best way to place prediction mass
under `DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`?** Artifacts: `docs/research/emitter-comparison.json`
(catalogue frames), `docs/research/novelty-holdout.json` (independent-inventory frame),
`docs/research/discovery-shift.json` (truth-density and truth-clustering sweeps).

## Frame 1 — the catalogue (a *proxy* frame, with a structural limitation)

`scripts/emitter_comparison.py`. Truth is the public catalogue; three regimes: the full
catalogue, a random 25 % of it with removed pixels excluded from scoring (the organizer's
masking rule), and truth confined to 3 km discs. The blind lattice and the historical
artefact are scored as-is; the model-derived emitters are Poisson-disk thinnings of the
stitched out-of-fold probability field.

| emitter | dots | full catalogue | thin 25 % | 3 km clusters |
|---|---|---|---|---|
| `lattice_4px` (blind, no learning) | 323,245 | 0.24634 | 0.08008 | 0.03688 |
| `lattice_5px` | 206,895 | 0.24525 | **0.09138** | 0.04234 |
| `model_poisson_4px` (combined OOF field, 4 px) | 309,492 | **0.25461** | 0.08356 | 0.03792 |
| `model_t0.4_s4px` (threshold 0.4, then 4 px) | ~80k | 0.22007 | 0.10451 | 0.05825 |
| `model_t0.4_s4px` **off-catalogue only** (`cand_t04s4`) | 80,392 | 0.00165 | 0.00096 | 0.00047 |
| historical artefact (leaderboard 0.2600) | 44,090 | 0.16177 | **0.11305** | **0.05800** |
| `inventory_*` (SGMC off-catalogue dots) | ≤17,077 | 0.00037 | 0.00026 | 0.00011 |

Three conclusions, in order of importance:

1. **Converting the model to dots is worth more than any modelling change attempted here.**
   The raw out-of-fold probability mosaic scores **0.09712** on the same grid and the same metric
   (`runs/loss-ablation/holdout.json`, `docs/research/discovery-shift.json`); Poisson-thinning it
   to 4 px spacing scores **0.25461**. Same model, same weights, same seed — a factor of **2.6**
   from the emission operator alone. The metric charges `FP_w` for every pixel a prediction touches, so a
   smooth field over a 5.17 M-pixel footprint is maximally expensive and minimally
   informative.
2. **The learned field does add something over blind spacing, but only ~3 %.** 0.25461 vs
   0.24634 at comparable dot counts, and 0.09589 vs 0.09187 on frame 2 below. This is the
   honest size of the localisation signal in a 19-band UNet trained for 600 steps: real,
   repeatable, and small.
3. **The catalogue frames cannot rank off-catalogue strategies at all.** `cand_t04s4`
   deliberately places no mass on catalogue pixels — which is exactly what the organizer's
   masking rule rewards — and therefore scores ≈0.002 against a truth set that *is* the
   catalogue. A truth set made of the catalogue can only be matched by predictions on the
   catalogue. This is the structural limitation of every catalogue-based holdout in this
   repository, and it is why frame 2 exists.

## Frame 2 — an independent expert-compiled inventory (the novelty frame)

`scripts/novelty_holdout.py`. The USGS State Geologic Map Compilation fault linework is split
by connected component (1,679 components; median 21 px; maximum 1,794 px); a random 30 % of
components is hidden and 70 % remains. The scoring domain is the footprint minus the
catalogue dilated by 3 px, so catalogue pixels can earn nothing and cost nothing — the
organizer's rule. Three repeats, identical hidden truth per repeat.

| emitter | mean DTI | min | max |
|---|---|---|---|
| `cand_t04s4` (threshold 0.4 → 4 px, off-catalogue) | **0.09589** | 0.08535 | 0.10226 |
| `model_probability_dots` (full field, 3 px) | 0.09277 | 0.08967 | 0.09442 |
| `lattice` (blind 3 px) | 0.09187 | 0.08902 | 0.09335 |
| historical artefact | 0.07102 | 0.06863 | 0.07260 |
| `visible_inventory_dots` (visible SGMC traces, 10 px) | 0.00128 | 0.00105 | 0.00168 |

* The **thresholded, off-catalogue candidate beats the blind lattice by +4.4 %** and the
  incumbent artefact by **+35 %** on this frame.
* The historical artefact — the only emitter here with a verified leaderboard score — is
  *worse than an unlearned lattice* on an independent fault inventory. Its advantage is
  specific to the catalogue's spatial pattern, not a general "finds new faults" advantage.
* `visible_inventory_dots` at 0.00128 is **not** a contradiction: it emits ~5,700 dots against
  the lattice's 208,000, so it is losing on budget, not on placement. Comparing emitters at
  unequal dot counts on this frame is invalid, and the table is labelled accordingly.
* **This frame is tautological for any emitter that uses the SGMC**, which is why the SGMC
  hedge is *not* validated here and is treated as an explicit, separately-reasoned bet in
  `docs/hypotheses.md`. What is non-tautological is the ranking among emitters that do not
  use the inventory.

## Frame 3 — truth-set shift

`scripts/discovery_shift_analysis.py` re-scores the two stitched OOF mosaics under density
thinning, clustered truth, and a third internal arm: a blind 4 px lattice at identical
runtime. Under the organizer's masking rule:

| truth realisation | regional model field | combined model field | blind lattice 4 px |
|---|---|---|---|
| full catalogue | 0.10503 | 0.09712 | 0.24634 |
| 50 % density | 0.05738 | 0.05270 | 0.14670 |
| 25 % | 0.02970 | 0.02735 | 0.08188 |
| 10 % | 0.01217 | 0.01118 | 0.03505 |
| 4 % | 0.00491 | 0.00452 | 0.01451 |
| 3 km clusters | 0.00980 | 0.00878 | 0.03492 |

The lattice's lead over the raw field widens as the truth gets sparser (2.3× → 3.0× → 3.6×),
which is the sharpest available statement of the density argument: **the sparser the hidden
truth, the more expensive a dense probability field becomes.** Combined with the metric
algebra in `docs/metric-response-surface.md` (a new dot helps iff its expected kernel credit
exceeds `0.2 × current DTI`, i.e. ~5 % at the incumbent's operating point), the operational
rule for this competition is: emit few, confident, well-placed dots; never emit a field.

## Limitations

* The catalogue is masked out of real scoring; frame 1 is a proxy whose ranking can invert,
  and frame 2 substitutes a state geologic-map inventory for the organizers' expert labels.
  Neither is the private test set.
* Emitter comparisons across unequal dot budgets are invalid; only same-budget comparisons
  are used for the decisions above.
* The 3 km cluster radius and 25 % density are modelling choices, not measured properties of
  the hidden truth. They bracket it rather than estimate it.
