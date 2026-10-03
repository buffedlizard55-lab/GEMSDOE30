# H-33-01 preregistration — placement policy: how a fixed emission budget should be split between near-catalogue and off-catalogue space

**Frozen:** 2026-10-03 (this session), before any scoring run. Harness: `scripts/placement_policy_holdout.py`.
**Registered result:** `docs/research/h33-01-placement-policy-holdout.json` (+ this document stays as written;
post-hoc changes require a new preregistration, not an edit).
**Type:** this is a *policy* test, not a detector test — the standing recommendation from three consecutive
detector falsifications (H-31-01, H-32-01, H-32-05) against the same proximity-matched control
(`README.md` "Session 4" §5; `docs/research/h32-05-basement-edge-holdout.md` closing note).

---

## 1. Question

Every submission in this family emits a *fixed budget* of binary dots (the metric's max-rule makes thinning
profitable — `docs/research/why-d28-scored-026.md` §4). All previous work asks *which field ranks pixels*.
Three falsifications say the field is second-order; this experiment asks the first-order question directly:

> Given one ranking field and one budget, how should the dots be **stratified by distance to the public
> fault catalogue** — near the catalogue (but outside the masked pixels themselves), intermediate, or far?

The incumbent historical best (owner-reported 0.2600, `dotted-h19-5-d2-8`) places 19.5 % of its dots within
300 m of the catalogue against an 8.6 % base rate (**2.3× enrichment**, [MEASURED],
`docs/research/emission-anatomy.json`). The official rule says catalogue pixels are masked from scoring and
that "new fault" includes newly mapped geometry of existing systems ([OFFICIAL], staff posts
<https://community.drivendata.org/t/11516> and <https://community.drivendata.org/t/11536>). If hidden
expert-labelled faults cluster along mapped structures (extensions, splays, en-echelon steps), a
near-catalogue *band* is an enriched target region at no FP cost from the catalogue itself — while far-field
dots are cheaper to obtain (more area) but hit sparse truth less often. Nobody has measured the optimum
split on this repository's frames; the current emitters use whatever split their score field happens to
produce.

## 2. Frame (the only one that can answer this — see §6 for why)

Identical to the registered novelty frame (`docs/research/novelty-holdout.md`, `scripts/novelty_holdout.py`):

* **Truth** = USGS SGMC fault linework (NV + CA, public domain, rasterised to the competition grid by the
  verified external-layers workflow, `data/external/external_receipt.json`), split into 3×3-connectivity
  connected components; per repeat, a random **30 % of components** is hidden; the hidden set **and** the
  scored domain are intersected with the domain below.
* **Domain** = template footprint minus the public catalogue dilated by 3 px (300 m) — the organizer's
  masking rule. Catalogue pixels and their kernel neighbourhoods can earn nothing and cost nothing.
* **Metric** = exact masked DTI, `α = 0.2`, `β = 0.8`, triangular kernel `k(d) = max(1 − d/300 m, 0)`,
  100 m pixels (`gemsdoe30.emission.dti_components_masked`).
* **Strata** (by Euclidean distance to the nearest catalogue pixel, computed on the full grid, then
  intersected with the domain):
  * `near` = (3 px, 6 px] — first band outside the mask, i.e. (300 m, 600 m];
  * `mid` = (6 px, 12 px];
  * `far` = > 12 px.
  These three bands partition the domain; a dot's band is its *placement*, not its truth relationship.
* **Repeats** = 5, draw seeds `30*31 + r` (`r = 0..4`) — the exact repeat schedule of the 5-repeat
  budget-matched run that produced the standing +25.1 % figure.

## 3. Ranking field

One field for all arms: the stitched 4-fold out-of-fold UNet probability mosaic, **regional** arm,
seed 30, recipe `6 epochs × 100 steps × batch 4 × 96 px patches` (`scripts/run_loss_ablation_batch.sh`
recipe; the exact recipe whose dot-set earned the standing +25.1 % result). Regenerated in this session
from the SHA-256-pinned data (`dataset_signature 291d3467…dee855ed`) so the field, frames and controls
share one run. **No arm uses the SGMC inventory** (that would be tautological, `novelty-holdout.md`).

Preprocessing, identical for every arm: clip to [0, 1]; zero outside the domain; within a stratum, order
candidates by descending score (ties by raster order) after 4 px Poisson-disk thinning of that stratum
(spacing applies *within* strata; between-stratum duplicates are not removed — registered as a known
cost of stratification, it can only help the f = 0 arm slightly by allowing mid/far overlap).

## 4. Arms (all emissions are count-B by construction; deterministic given the field and draws)

Budget **B ∈ {80,000, 40,000}** — the matched count of the standing `cand_t04s4` result, and D2.8's scale.

| Arm | Policy | Allocation (near / mid / far) | Purpose |
| --- | --- | --- | --- |
| `P0` | model-rank, no near band | 0 / B/2 / B/2 | anti-nearness extreme |
| `P25` | model-rank | ¼B / ⅜B / ⅜B | modest near-band, like the incumbent |
| `P50` | model-rank | ½B / ¼B / ¼B | balanced |
| `P75` | model-rank | ¾B / ⅛B / ⅛B | near-heavy |
| `P100` | model-rank | B / 0 / 0 | pure nearness extreme |
| `P_rank` | no model: greedy fill by ascending distance-to-catalogue over the whole domain, first B | data-driven | "generic proximity prior as a policy" — the strongest possible no-learning near-band strategy |
| `blind_random_B` | uniform random dots over the **whole** domain, exactly B | ~area-proportional | **the standing primary control** (budget-matched blind random, `README.md` "Current next steps" item 7) |
| `random_strata_B` | uniform random dots **within each stratum** at the tested split, exactly B | ¼B / ⅜B / ⅜B | isolates policy (where) from ranking (which pixel): `P25` vs this = value of the model *inside* the policy |
| `f_nat` | incumbent recipe: 0.4-threshold + 4 px Poisson over the whole domain, take top B by score | whatever it produces | reference: today's actual emitter, at matched count |
| `historical_d28` | the owner-reported 0.2600 artefact, as published | its own (measured split recorded) | calibration reference only — never a gate target |

Pool shortfall rule (frozen): if a stratum cannot supply its quota (after thinning), the remainder is passed
mid → far → near in that order; shortfalls are recorded per repeat and arm. If `P100` is shortfall-limited
below ¼ of B, it is reported but excluded from `f*` selection.

## 5. Selection and gates (frozen before the run)

`f*` = the fraction (from {0, .25, .5, .75, 1}) with the highest **mean DTI at B = 80,000** over the 5
screen repeats. Gates:

* **G1 (policy beats blind placement).** `mean_{repeats}( P_{f*} − blind_random_B ) ≥ +0.005` and the arm
  wins in **≥ 4/5** repeats. Threshold = the registered emission-family margin (`verification-protocol.md`).
* **G2 (near band has signal).** `mean( P_{f*} − P0 ) > 0` on screen **and** on confirmation, with
  **≥ 4/5** repeat wins on screen. If the best split is f = 0 this is satisfied trivially and the correct
  conclusion is "no enrichment near the catalogue"; if f* > 0 but loses to `P0`, the near band is
  *harmful* on this frame.
* **G3 (ranking inside the policy earns its keep).** `mean( P_{f*} − random_strata_B ) ≥ 0` at the same
  split. Below 0 ⇒ the policy's apparent gain is pure strata geometry, not learned ranking — reported as
  such and treated as a *prior policy*, not a model result.
* **G4 (confirmation).** Fresh component-draw seed 31 (same protocol, 5 repeats):
  `mean( P_{f*} − blind_random_B ) > 0` with **≥ 3/5** wins, and `f*`-selection agreement within one step
  (else recorded as unstable).
* Sensitivity (never a gate): all arms at B = 40,000; `P_rank` vs `P_{f*}` (is model ranking worth more
  than raw proximity *within* the winning policy?); per-band dot counts of every arm (the descriptive
  anatomy that answers "how did D2.8 place"; its `f_nat` counterpart included).

**Promotion semantics.** Pass = the placement split `f*` is promoted *as a placement rule for candidate
construction on this frame*, i.e. the next built candidate applies it; it is **not** a submission
approval and not a score claim. Fail closes the placement-policy line, and the incumbent
model-score-selection over the whole domain stands, with the measured numbers recorded either way.

## 6. Known limitations declared in advance

1. **Frame substitution.** The competition truth is the organizers' private expert set; the hidden-SGMC
   frame is the only locally available independent expert compilation. Near-catalogue enrichment of SGMC
   (24.9 % within 300 m vs 8.61 % base, [MEASURED]) bounds, but does not equal, the enrichment of expert
   "new faults". A frame-negative result is weak evidence of global falsity and a frame-positive result is
   weak evidence of a leaderboard gain — recorded per IR-30-021-style circularity warnings; the gates
   above therefore control *slot spending*, not truth.
2. **Catalogue-frame blindness.** On any frame whose truth *is* the catalogue, every off-mask placement
   question is unanswerable (`emitter-holdout.md` Frame 1: `cand_t04s4` scores ≈ 0.002 by construction).
   No arm here is scored on the catalogue frame; running them there would be meaningless, and we say so
   instead of reporting it.
3. **Single field.** One UNet OOF surface; the sibling GBM surface is not re-run here (2-core sandbox). If
   G1–G4 pass, a second-field check is required before promotion is *used* in a candidate.
4. **Between-stratum duplicates** (§3) slightly favour the f = 0 arm; magnitude is measured and reported.
5. Owner-mirror data are SHA-256 consistent with all prior sessions but remain **not organizer-authenticated**
   (IR-30-001).

## 7. Reproduce

```bash
python3 scripts/train_model.py --fold F --loss regional --output runs/fF-regional.pt \
    --epochs 6 --steps-per-epoch 100 --batch-size 4 --patch-size 96 --seed 30   # F = 0..3
python3 scripts/infer_model.py --checkpoint runs/fF-regional.pt --fold F --predictions-only \
    --output runs/oof/regional-fF.npy                                            # each F
python3 scripts/stitch_oof_predictions.py --fold0 … --fold3 … --output runs/oof/regional-oof.npy
python3 scripts/placement_policy_holdout.py            # screen seed 30 + confirmation seed 31 in one run
```
