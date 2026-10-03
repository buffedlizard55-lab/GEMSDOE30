# H-32-05 registered result — buried range-front pinch-out edges: **falsified**

**Run:** 2026-10-03 · harness `scripts/basement_edge_holdout.py` · runtime 50.4 s ·
preregistration `docs/research/h32-05-preregistration.md` (frozen before the run) ·
machine-readable result `docs/research/h32-05-basement-edge-holdout.json`.

**Verdict: the registered gate failed on every scoring clause. Not promoted. No submission slot
spent.**

---

## 1. Gate outcome

| Registered clause | Requirement | Measured | Pass |
| --- | --- | --- | --- |
| Screen pooled Δ vs `random_near_matched` (N = 15,000, split seed 31) | ≥ **+0.002** | **−0.02614** | **fail** |
| Quadrant sign consistency (screen) | ≥ 3 of 4 | **0 / 4** | **fail** |
| Confirmation pooled Δ (fresh split seed 41) | > 0 | **−0.02591** | **fail** |
| Transform clause: primary > `dbs_magnitude` on both splits | > 0 on both | +0.00122 / +0.00345 | **pass** |

`promoted = false`.

## 2. The numbers

Screen split (seed 31): 3,199 catalogue components, 20,870 hidden truth pixels, 40,118 known
(masked) pixels.

| Arm | N = 15,000 DTI | N = 40,000 DTI | hidden credit fraction (N = 15,000) |
| --- | --- | --- | --- |
| `random_near_matched` (control) | **0.02897** | **0.06207** | 0.0719 |
| `far_random` (control) | 0.02802 | 0.05637 | 0.0699 |
| `grav_edge_only` | 0.00666 | 0.01171 | 0.0075 |
| `basement_edge_only` | 0.00292 | 0.00466 | 0.0046 |
| **`basement_edge_corroborated` (primary)** | **0.00283** | **0.01040** | **0.0036** |
| `dbs_magnitude` (novelty control) | 0.00161 | 0.00269 | 0.0019 |

Confirmation split (seed 41): 20,247 hidden truth pixels, 40,741 known pixels; ordering identical,
primary 0.00449 vs matched control 0.03040 at N = 15,000.

Quadrant diagnostics (screen, N = 15,000), primary vs matched control:
`q0 0.00000 / 0.02892`, `q1 0.00000 / 0.02451`, `q2 0.01095 / 0.02974`, `q3 0.00801 / 0.03577` —
the primary arm is at or near zero credit in every quadrant.

## 3. Interpretation — what is and is not established

**Established (measured, reproducible):**

1. On the catalogue-component proxy, **every geophysical arm tested here loses badly to random
   emission at matched budgets** — by roughly an order of magnitude in DTI. This replicates the
   pattern already recorded for H-31-01 (relay connector) and H-32-01 (vent corridors): hand-built
   geophysical evidence fields do not beat proximity to already-mapped structure on this proxy.
2. **The transform clause passed.** The basement-surface *edge* beat the basement-depth *magnitude*
   on both splits (+0.0012 screen, +0.0034 confirmation, and 0.01040 vs 0.00466 for `basement_edge_only`
   at N = 40,000). The directional claim in the preregistration — that the *step geometry* carries
   more than the field value — is supported, but the whole family sits far below the random controls,
   so it does not rescue the hypothesis.
3. Corroboration with the gravity-gradient field did **not** help: `basement_edge_only` ≥ primary at
   N = 15,000 on the screen split. `grav_edge_only` was the best of the four feature arms, which is
   consistent with USGS OFR 2005-1154 (concealed basin faults mapped from horizontal gravity
   gradients) but is still ~4× worse than the matched random control.

**Not established / limitations that must be stated:**

* **The coherence constraint was non-selective as configured.** 5,149,374 of 5,167,373 footprint
  pixels (99.65 %) satisfied `coherence ≥ 0.5`, so the "must be an oriented linear feature" clause
  barely constrained the primary arm — the arm was effectively the plain rank-sum of the two edge
  fields. The preregistered floor of 0.5 was too permissive. This is a design defect in the test, not
  a property of the geology, and it means the *oriented-edge* variant of H-32-05 has **not** been
  fairly tested.
* A catalogue-component holdout is a **necessary but biased** proxy: it can reward predictions on
  catalogue-like faults that the competition masks, and it makes generic proximity to mapped
  structure the dominant predictor. A negative result here is evidence against spending a slot, not
  proof that basement steps are useless for the hidden expert labels.

## 4. Decision and next step

* **Not promoted.** Per the standing promotion rule, no submission slot is proposed for H-32-05.
* The honest next experiment is **not** another hand-built field. Three consecutive component-holdout
  falsifications (H-31-01, H-32-01, H-32-05) against a `random_near_matched` control that sits at
  ~0.029 DTI say the binding constraint is **where** emission is placed relative to mapped structure,
  not which scalar field ranks the pixels. The highest-value next test is therefore a
  **placement-policy** experiment (how to allocate a fixed budget between near-catalogue and
  off-catalogue space) rather than a new detector.
* If an oriented-edge retry is wanted, it must re-preregister with a coherence floor chosen on the
  screen split only (e.g. the top decile of coherence) and must be reported against the same
  matched control.

## 5. Reproduce

```bash
python scripts/prepare_data.py            # requires data/raw/ in place (see docs/status.json)
python scripts/basement_edge_holdout.py   # writes docs/research/h32-05-basement-edge-holdout.json
```

Both splits are deterministic (split seeds 31 / 41, draw seeds 17 / 23); the feature arms emit
deterministic top-N sets, so only the two random controls vary by draw seed.
