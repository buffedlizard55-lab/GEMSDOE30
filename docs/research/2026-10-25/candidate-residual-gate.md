# Candidate: residual-ridge gate (review hypothesis 3) — design, pre-registration, result

Status: **NEGATIVE on the holdout**. A downloadable, format-valid, repository-unique TIFF was generated
(`docs/downloads/gemsdoe30-h3a-residual-ridge-gate-p400-7a88865b-nan.tif`), but it did **not** beat
the count-matched proximity comparator on any holdout protocol, so it is **not recommended for a weekly slot**.
No organizer score exists for it. Every number below is a **HOLDOUT-DTI** measured by the shared evaluator
(`component-holdout-v2-footprint-20261025`), not a competition score.

## 1. Hypothesis (ranked 3 of 4 in [review.md](review.md))

| Field | Content |
|---|---|
| Layers | `rtp` (target), regressors `iso_grav_anom`, `det_elev`, `depth_to_base_surf` (19-band cube, `data/processed/manifest.json`) |
| Physical signature | Magnetically quiet residual ribbons that are gravity-consistent, scored as bright ridges of −residual (Hessian, σ = 200 m) |
| Off-catalogue rationale | Ridge score is computed from geophysics, not from catalogue geometry; the only catalogue input is a 3 km corridor gate |
| Named non-fault mimic | Nonmagnetic sediment fill (basin infill produces gravity-consistent magnetic lows) |
| Difference from repo methods | Repo had proximity fields (`fields.proximity_belief`), edge emitter on proximity/external beliefs, and basement-edge/scarp work; none residualised magnetics against gravity/elevation/basement and ranked negative ridges |

**Expected utility / cost (review's qualitative ranking):** low-to-uncertain utility, medium cost. Implemented because it was
the highest-ranked hypothesis implementable in this session without new data. **Hypothesis 1 (cross-contact texture displacement)
was not implemented**: it needs an untested displacement estimator whose validation alone would exceed the session budget.

## 2. Pre-registration (frozen before the first holdout run)

Recorded in the headers of `scripts/residual_gate_holdout.py` and `scripts/build_residual_gate_candidate.py`:

* Hidden split: `holdout.split_components(catalogue, seed=31)` (3,199 stand-in hidden components; 20,870 withheld positive pixels in the scored domain).
* Scored domain: footprint minus all visible catalogue pixels (organizer-style masking, as documented in this repo).
* Feature visibility: `--buffer-m 3500` (primary strict arm: 3.5 km = 3 km gate + 300 m metric reach + 200 m margin) and `0` (the existing stand-in protocol, sensitivity arm).
* Candidate A: gated residual ridge, gate 3 km from visible traces. Emitter: greedy Poisson-disk, radius 4 px (400 m), binary 0/1.
* Comparator B: proximity belief exp(−d/1 km), cut at 3 km, same emitter, **count-matched** to A.
* Ablation D: ridge + gate on raw `rtp` (no residualisation), count-matched to A.
* Control R: uniform random scores, same emitter, count-matched to A. Any arm must beat R to show signal beyond dot density.
* Arm E (catalogue-free): residual ridge with no distance gate. This is the only arm that is structurally testable under the strict buffer.
* Statistics: pooled masked DTI (α = 0.2, β = 0.8, 300 m triangular kernel); whole-tile (32 px = 3.2 km) block bootstrap, 2,000 draws, seed 31, 95% percentile CI.
* Canary: each feature alone, AUC of hidden-vs-scored pixels; |AUC − 0.5| beyond 0.40 (AUC outside [0.10, 0.90]) flagged for leakage review.

## 3. Experiments (budget: 3 experiments / 2 hours)

| # | Design | What it showed |
|---|---|---|
| 1 | Strict 3.5 km buffer, arms A, B, D | A, B, D scored exactly 0.0. **Structural, not a finding about the field:** gated dots are ≤ 3 km from visible faults and hidden pixels are ≥ 3.5 km from visible features, so no dot falls within the 300 m reach of a hidden pixel. |
| 2 | Strict buffer, adds catalogue-free arm E | E = 0.04471 [0.03768, 0.05200] (tp 974, fp 24,464, 20,870 withheld positives). Canary: all features 0.36–0.58 AUC. |
| 3 | Final: strict buffer and 0 m, adds random control R | Results in §4. Run artifacts: `residual-gate-holdout-buffer3500.json`, `residual-gate-holdout-buffer0.json`. |

No further experiments were run. The budget is spent; the verdict is negative.

## 4. Results (HOLDOUT-DTI · evaluator `component-holdout-v2-footprint-20261025` · withheld positives shown)

**Protocol 0 m (existing stand-in; 20,870 withheld positives; 70,488 dots per arm):**

| Arm | Pooled DTI | 95% tile-bootstrap CI |
|---|---:|---|
| B proximity comparator (count-matched) | **0.17703** | [0.16814, 0.18570] |
| D raw-rtp ridge + gate | 0.13070 | [0.12194, 0.13973] |
| **A residual ridge + gate (candidate)** | **0.12222** | [0.11395, 0.13060] |
| E catalogue-free residual ridge | 0.07940 | [0.07216, 0.08705] |
| R random control | 0.08320 | [0.07894, 0.08770] |

Paired tile-bootstrap differences (A − X): vs B **−0.05481 [−0.06596, −0.04406]**; vs D **−0.00848 [−0.01276, −0.00414]**; vs E +0.04282 [0.03716, 0.04875]; vs R +0.03903 [0.03073, 0.04734]. A never exceeds B or D in any of 2,000 resamples.

**Protocol strict 3.5 km buffer (20,870 withheld positives; 24,876 dots per arm):**

| Arm | Pooled DTI | 95% CI |
|---|---:|---|
| A, B, D (gated) | 0.00000 | structurally zero (see §3, experiment 1) |
| E catalogue-free residual ridge | 0.04471 | [0.03768, 0.05200] |
| R random control | 0.04368 | [0.04004, 0.04720] |

E and R have overlapping CIs. **The catalogue-free residual ridge is not distinguishable from random dot density in this protocol.**
This is a negative result for the hypothesis under strict buffering. It is not proof the physics is absent: the residual model
explains only **R² = 0.055** of `rtp` (5,164,312 fit pixels), so the "residual" is mostly the raw magnetic signal.

**Feature canaries (both protocols):** all 19 raw bands, `residual_rtp`, `distance_to_visible_m`, and each belief field were
tested alone against hidden-vs-scored pixels. Strict buffer: every AUC lies between 0.41 and 0.58. At 0 m, the most extreme are
`distance_to_visible_m` (AUC 0.2442: nearer visible traces mean more hidden pixels) and `belief_B_proximity` (0.7482). These are
expected for proximity features on a stand-in split that interleaves hidden and visible components in the same tiles. Neither crosses
the 0.10 / 0.90 alarm lines, and no feature reaches the 0.90 leakage threshold. Full values: `residual-gate-holdout-buffer0.json` → `feature_canaries`.

**Interpretation limits.** (a) The 0 m protocol is a catalogue stand-in, not organizer labels, and it favours proximity, so B's lead
over A there is a property of the protocol as much as of the field. (b) The strict protocol is buffered but its hidden set is still
a catalogue split. (c) Neither protocol uses expert-labelled new faults, which is where the competition is scored.

## 5. Duplicate / novelty checks

* Final-dot check against the nine pinned registry rasters (`check_novelty.py --stage dots`): Spearman ≈ 0.002–0.003 against every
  reference; at most **22%** of candidate dots within 3 px of any reference (threshold: Spearman > 0.90 or > 70%). No duplicate.
  Decision `blocked-incomplete-evidence` because the registry is explicitly partial (`complete: false`). **Not a novelty certificate.**
* Repo-wide check against all 12 other TIFFs in `docs/downloads` (including the other session's H-CC1 candidate, Spearman −0.0010, 10.2 % within 3 px, no duplicate) (`check_downloads_novelty.py`): max Spearman 0.0103; max
  within-3px fraction **45.0%** (GEMSDOE30 edge-hybrid). No duplicate under the thresholds.
* **Surface-stage check not run.** The registry contains final dot rasters only; the continuous surfaces that produced them were not
  reconstructed, so the required pre-placement surface comparison is **blocked**.

## 6. Output file and validation (independently re-read with rasterio)

* File: `docs/downloads/gemsdoe30-h3a-residual-ridge-gate-p400-7a88865b-nan.tif`; the final SHA-256 is recorded in the sidecar `…-nan.json` and the run card (the note tag was edited after the first build, which changed the bytes).
* One band, float32, NaN outside the template footprint; 5,167,373 footprint cells, all finite; values exactly {0, 1}; 78,256 dots; 0 dots on known catalogue pixels.
* CRS EPSG:32611, shape 3730 × 3292, transform identical to `sample_submission.tif`.
* Submission name: `gemsdoe30-h3a-residual-ridge-gate-p400-7a88865b`
* Submission note: `GEMSDOE30 review-hyp3 residual-ridge gate, 3km catalogue corridor, 400m Poisson` (79 characters)

## 7. Verdict

**Negative.** Candidate A is below the count-matched proximity comparator (−0.0548 paired, 0 m) and below the raw-rtp ablation
(−0.0085 paired, 0 m), and the catalogue-free variant is not distinguishable from random dots (strict buffer). The file is valid and
unique, so it can be downloaded for format testing, but **the holdout does not support spending a weekly slot on it**. Promotion
to a real slot is a separate selector step and is not recommended on this evidence.

Reproduce:

```bash
/home/user/gems-venv/bin/python scripts/restore_public_mirrors.py
/home/user/gems-venv/bin/python scripts/prepare_data.py
PYTHONPATH=src /home/user/gems-venv/bin/python scripts/residual_gate_holdout.py --buffer-m 3500 --out docs/research/2026-10-25/residual-gate-holdout-buffer3500.json
PYTHONPATH=src /home/user/gems-venv/bin/python scripts/residual_gate_holdout.py --buffer-m 0 --out docs/research/2026-10-25/residual-gate-holdout-buffer0.json
PYTHONPATH=src /home/user/gems-venv/bin/python scripts/build_residual_gate_candidate.py
```
