# Independent-inventory emitter holdout — and why the control has to be budget-matched

**Status: completed, 5 repeats. This document supersedes the "+4.4 % over a blind lattice" figure that
appeared in an earlier draft of the README. The corrected, budget-matched result is +25.1 % over
uniform random dots at the same count — and −2.4 % for the other branch's published candidate.**
Raw numbers: [`novelty-holdout.json`](novelty-holdout.json) (this file, 5 repeats). No competition
score is claimed; no submission slot has been used.

## Why this frame exists

The competition truth is private and, per DrivenData staff, consists of *new* faults that are **not**
in the USGS/INGENIOUS catalogue, with catalogue pixels masked out of scoring. A local frame built from
the catalogue therefore cannot test novelty: it rewards exactly the repetition the official metric
discards. The only local substitute with an independent, expert-compiled origin is the **USGS State
Geologic Map Compilation (SGMC)** fault linework (NV + CA, public domain), which is *not* the source
of the competition catalogue and does overlap it only partially (24.94 % of its footprint pixels lie
within 300 m of a catalogue fault against an 8.61 % base rate).

## Protocol

1. Rasterise the SGMC fault linework onto the competition grid (100 m, EPSG:32611) → 21,160 features,
   82,151 pixels in the footprint. Provenance: [`external_receipt.json`](../../data/external/external_receipt.json).
2. Split it into connected components; at each repeat, hide a random 30 % of components (drawn so the
   hidden set keeps ~17.6 k pixels), dilate the *visible* components by 3 px and **exclude** that
   dilation from the scored domain — this is the organizer's own rule, applied to an inventory.
3. Score every emitter with the exact masked competition metric (`α = 0.2`, `β = 0.8`, `R = 300 m`,
   triangular kernel) on the same domain. Repeat with independent component draws.
4. **Control rule adopted after this experiment: compare emitters only at the same emitted count, in
   the same run.** Uniform *random* dots at exactly the candidate's count are the primary control,
   because a lattice's score is not monotone in its own spacing.

## Result (5 repeats, mean over repeats; dots = pixels emitted inside the scored domain)

| emitter | what it is | dots | mean DTI | range |
| --- | --- | ---: | ---: | --- |
| `cand_t04s4` | UNet out-of-fold field, threshold 0.4, 4 px Poisson spacing | 80,392 | **0.09526** | 0.08380–0.10483 |
| `blind_random_80392` | **matched control**: uniform random dots | 80,392 | **0.07617** | 0.07268–0.07967 |
| `blind_random_85526` | uniform random dots (hedge candidate's count) | 85,526 | 0.08110 | 0.07851–0.08630 |
| `cand_gbm` | HistGradientBoosting OOF field, adaptive 5 px thinning (sibling branch) | 75,001 | **0.07279** | 0.06848–0.07885 |
| `blind_random_75001` | **matched control** for the same | 75,001 | **0.07460** | 0.07237–0.07612 |
| `cand_hedge` | `cand_t04s4` + SGMC off-catalogue hedge | 85,526 | 0.18343 | 0.17391–0.19114 |
| `lattice` | blind 3 px lattice | 527,504 | 0.09395 | 0.08901–0.09966 |
| `model_probability_dots` | 3 px Poisson over the OOF field | 506,746 | 0.09498 | 0.08966–0.10078 |
| `historical_artefact` | the owner-reported 0.2600 dotted file | 35,824 | 0.07061 | 0.06640–0.07355 |
| `visible_inventory_dots` | dots on the visible inventory (sanity) | 3,495 | 0.00121 | 0.00101–0.00168 |

`lattice_7px` (97,028 dots) scored 0.09873 and `lattice_8px` (74,288 dots) 0.08442 in the same runs —
a 17 % swing from a 30 % change in count, with the *denser* lattice lower. This is why the lattice is
an unusable control at unmatched count.

## What is and is not evidence here

* **Evidence.** The matched-count comparison. The UNet dot set is worth **+25.1 %** over random dots
  at the same budget, and matches what the 3 px probability lattice achieves with **6.6× more dots**
  (0.09526 vs 0.09395) — the "thin, don't flood" result again, cross-checked on a frame the
  catalogue does not define.
* **Not evidence.** Every `*sgmc*` arm. The hidden set is a subset of the same SGMC inventory, so
  those arms score 0.18343 by construction. This number must never be quoted as validation; it only
  bounds the hedge's cost (≤ 3 % of the DTI denominator).
* **Not evidence against the other branch's model.** `cand_gbm` is a *different* model
  (HistGradientBoosting surfaces, adaptive thinning) and this frame is the first place it was scored
  at all. Its −2.4 % against its matched control is a statement about that emitter on *this* frame,
  not a general verdict on the model.
* **A live risk on both sides.** All of these are *unclustered* dot sets. The official hidden faults
  are expected to be spatially clustered (they are individual mapped fault traces, not a scattered
  field), and the repository's own 3 km cluster ladder
  ([`discovery-shift.json`](discovery-shift.json)) shows cluster-regime DTI is 20–30× lower than
  full-grid DTI. No emitter in this repository has been tested under a clustered target geometry.

## Reproduce

```bash
PYTHONPATH=src python3 scripts/novelty_holdout.py --repeats 5 \
  --extra-emitter "cand_gbm=docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13.tif" \
  --extra-emitter "cand_hedge=docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif" \
  --extra-emitter "cand_t04s4=runs/candidates/model_t04_s4.npy" \
  --extra-emitter "blind_random_75001=runs/candidates/blind_random_75001.npy" \
  --extra-emitter "blind_random_80392=runs/candidates/blind_random_80392.npy" \
  --extra-emitter "blind_random_85526=runs/candidates/blind_random_85526.npy"
```

(~126 s on 2 cores. The `blind_random_*` rasters are regenerated deterministically by drawing
`rng = np.random.default_rng(1000 + n)` without replacement from the in-footprint pixel index list.)
