# Pre-registration — EDGE expected-marginal-DTI emitter holdout (2026-10-03)

**Status of this document:** written and committed *before* the experiment was run. It freezes the
frame, the belief fields, the emitter families, the parameter grids and the decision rule. Any later
change must be recorded as a deviation with a timestamp.

## 1. Question

Does a greedy that ranks candidate dots by their **expected marginal kernel credit** (the metric's own
geometry) beat the belief-ordered emission families this project has already tested — dense
thresholding, uniform Poisson-disk thinning, confidence-adaptive thinning, and the existing
belief-ordered marginal rule — when every family chooses its own operating point?

## 2. Frame (why it is a necessary-but-biased proxy)

* Real grid: `data/raw/labels.tif` + `data/raw/sample_submission.tif`, 3730 × 3292, EPSG:32611, 100 m.
* Whole 8-connected catalogue components are split deterministically into a stand-in **hidden** half
  and a **known** half (`gemsdoe30.holdout.split_components`, seed 31, 32-pixel interleaving tiles).
* Known pixels are masked out of every metric term, exactly as the organizer masks
  USGS/INGENIOUS pixels (DrivenData community thread 11516).
* Hidden components are the stand-in "new faults". Four spatial quadrant blocks are scored
  separately; each block is cropped with a 3-pixel halo for exactness and speed.
* **Limitation, stated up front:** the catalogue is the inventory the official metric masks out, so
  an absolute number here is not a competition score and a win here does not guarantee transfer to
  the organizer's expert-labelled new faults.

## 3. Belief fields (never contain hidden components)

| Field | Definition |
| --- | --- |
| `proximity` | `exp(-d / 1 km)` around **known** catalogue traces, cut at 3 km |
| `external` | sum of `exp(-d / 0.7 km)` around USGS SGMC fault lines, GDR paleo-geothermal, GDR 2 m temperature probes, GDR Quaternary volcanics — all free official layers already derived onto the competition grid; cut at 2.1 km |
| `hybrid` | geometric mean of `proximity` and `external` |

`derived_gdr_qfaults_v2_100m_u8` is excluded because 59,037 of its 59,065 pixels lie on the training
catalogue — it is a copy of the answer key, not independent evidence.

## 4. Emitter families and parameter grids

| Family | Parameter grid | Operating point |
| --- | --- | --- |
| `dense` | belief quantiles 0.90, 0.95, 0.98, 0.99, 0.995 | threshold |
| `uniform` | Poisson radius 1–10 px | radius |
| `adaptive` | radius {3, 5} px × gamma {0.5, 1.0} | radius/gamma |
| `metric` | existing belief-ordered rule, pool cap 120,000 | fixed |
| `edge` | prefixes of the greedy acceptance order, step 5,000 dots | number of dots kept |

`edge` runs one greedy sweep per field with expected truth mass 80,000 (the loosest stop in the
reporting sweep) and a hard cap of 120,000 accepted dots; the acceptance order is independent of the
truth-mass assumption, so every prefix is a valid operating point.

## 5. Decision rule (frozen)

* Parameter selection is **leave-one-fold-out**: for fold *f*, each family's parameter is the argmax
  of pooled index over the other three folds; the held-out fold is then scored at that parameter.
* The headline number is the **pooled cross-validated** index (sum of sufficient statistics over the
  four folds at their own held-out choices).
* `edge` is **promoted as an emission operator** only if its pooled cross-validated index beats the
  best of `dense`/`uniform`/`adaptive`/`metric` on the same field by **≥ 0.005** and is higher in
  **≥ 3 of 4** folds. A promotion licenses *building a candidate file from the winning construction*;
  it does not license a weekly submission slot by itself (that still requires the full promotion
  protocol and the exact-file audit).
* Oracle values (parameter chosen on the scored fold) are reported separately, are not selectable,
  and may not be quoted as results.

## 6. Falsification

If `edge` does not clear the ≥ 0.005 / ≥ 3-of-4 gate on every field where its predecessor families
were run, the emitter is recorded as **not promoted** and the belief field — not the operator — is
reported as the binding constraint.

## 7. Reproduce

```bash
PYTHONPATH=src python scripts/emitter_opt_holdout.py \
  --output docs/research/emitter-opt-holdout.json
```
