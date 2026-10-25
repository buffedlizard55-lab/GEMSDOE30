# Lane G30-S19 — preregistration (written BEFORE any experiment in this session)

Date: 2026-10-25. Budget: max 3 experiments / 2 h. This file freezes the lane,
hypotheses, features, holdout, gates and emission before results are seen.

## Lane assignment (protocol gap, resolved explicitly)

The parallel-run protocol says "your lane is the single method paragraph below",
but the prompt as received contains no identifiable single method paragraph
(prior session correctly blocked on this). The same prompt also orders, at
highest urgency, autonomous generation of a unique submission with no manual
input. Resolution: this session self-assigns and freezes ONE lane here, stays
inside it, and flags the assignment as irregularity IR-S19-01 for owner review.
No other lane's surface or raster is used as a model input.

**LANE G30-S19:** an independent belief surface learned hide-and-recover from
the 19 competition feature bands only (plus label-free transforms of those
bands and distances to *visible* catalogue faults computed per fold), using a
histogram gradient-boosting classifier; emission by the shared EDGE
expected-marginal-DTI greedy (`src/gemsdoe30/emitter_opt.py`); final support
excludes catalogue pixels pixel-exactly and applies the >2 px catalogue-flank
exclusion whose mechanism was established by H33 forensics (learning from a
prior submission is explicitly permitted; copying its dots is not — no registry
raster, including H19-5/D28/H33, is an input feature at any stage).

Shared tools reused, not forked: `gemsdoe30.holdout` (evaluator
`component-holdout-v2-footprint-20261025`), `gemsdoe30.metric`,
`gemsdoe30.emission`, `gemsdoe30.emitter_opt`, `gemsdoe30.novelty`,
`gemsdoe30.submission` writer/validator. Requested template filenames
(`evaluate_holdout.py`, `submission_writer.py`) do not exist in this repo; the
equivalents above are used and the gap is flagged (IR-S19-02).

## Why H33 (0.2778, owner-reported, NOT organizer-confirmed) won — mechanism

Verified byte forensics (prior session, re-checked this session): H33 support =
GEMSDOE28 solo-d2.8 support with every dot at catalogue distance ≤2 px deleted
(zero mismatching pixels on reconstruction). The chain is
H19-5 multiline belief (0.1922) → Poisson thinning d1.5 (0.2477) → d2.8
(0.2600/0.2708 family) → flank prune (0.2778). Scores in this paragraph are
owner-reported claims, not receipts.
Metric algebra (official: α=0.2, β=0.8, R=300 m triangular;
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):
DTI = T/(0.2T+0.2F+0.8G). Known catalogue pixels are masked from scoring, and
credit per truth pixel is a MAX over nearby predictions, so (a) dots on/near
catalogue traces mostly duplicate credit the mask discards while still risking
FP mass just outside the mask, and (b) redundant near-duplicate dots add F
without adding T. Thinning + flank pruning therefore raises T/F efficiency.
Beating 0.2778 requires a *better belief* (more true unmapped-fault coverage
per FP unit), not more aggressive pruning of the same belief — pruning returns
diminish and eventually delete genuine splays/extensions (officially, "new
fault" includes new geometry of known systems).

## Candidate hypotheses (ranked before implementation)

| Rank | Hypothesis | Layers / signature | Why unmapped faults | Non-fault mimic | Differs from repo/registry | Cost |
|---|---|---|---|---|---|---|
| 1 | H-A Multi-physics edge-coherence habitat | `tmi_hg`, `tmi_vg`, `tc`, `rtp`/`mag_anom` gradients, `iso_grav_anom_hg/slope/vg`, `det_elev_slope`; gradient magnitude + structure-tensor coherence + multi-scale local σ | Buried faults offset magnetic/gravity texture and basement even with no scarp or mapped trace; coincident linear discontinuity in ≥2 physics is unlikely by chance | Lithologic contact / dike edge | Winners reuse the opaque H19-5 surface; repo edge work ranked single gradients. Here coherence is learned per-fold from visible faults only, no registry input | Low (bands in hand) |
| 2 | H-B Strain localization | `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate`, `ieq_n100a15`, `deq_n100a15` + interactions/gradients | Actively deforming unmapped faults localize geodetic strain and seismicity before surface rupture is mapped | Volcanic deformation / basin subsidence | Prior strain pilot was pointwise and failed its screen; here strain enters only as one group inside a regularized GBM with edge groups, judged by group ablation | Low |
| 3 | H-C Basement-ramp × conductivity breach | `depth_to_base_surf` gradient, `cond_surf` value/curvature, `iso_grav_anom` | Fault-controlled fluid pathways breach cover at basement ramps; conductive saddle at a ramp is a geothermal-pathway signature without a surface trace | Saline groundwater / sediment facies change | Repo tested basement slope and vent coincidence separately, not the learned ramp×conductivity interaction inside a full habitat model | Low |
| 4 | H-D Visible-fault geometry continuation | Distance to *visible* catalogue (per fold), distance-ring profile | Tips, stepovers and splays extend known systems into unmapped pixels (explicitly scored as "new") | Joint sets / mapping artefacts parallel to faults | Deliberately restricted to per-fold visible-only distance; final flank exclusion (>2 px) prevents it collapsing into catalogue tracing | Low; leakage-prone → canary-gated |

Top candidate implemented: H-A as the core of one GBM containing H-B/H-C/H-D
feature groups, with per-group ablation read from the same holdout run
(diagnostic only). No new external data is required; SGMC/Qfaults rasters are
excluded as inputs (they overlap the catalogue → leakage) and used, if at all,
only as a secondary descriptive frame. Volcanics/probe distances are excluded
from the primary model to keep the lane single and auditable.

## Frozen protocol

- **Holdout (hide-and-recover):** `split_components(seed=31)` hides whole
  8-connected catalogue components (spatially interleaved). Buffer: training
  sampling excludes all pixels within 3 px (300 m) of any hidden pixel;
  catalogue-distance features use known (visible) faults only; scoring masks
  known faults pixel-exactly (`valid & ~known`), pooled DTI α=0.2, β=0.8,
  R=300 m via `masked_dti_by_blocks`. Report withheld-positive count and a
  component-bootstrap 95% CI (resample hidden components, 500 draws, seed 7).
- **Leakage canaries (Experiment 1):** every candidate feature alone → AUC for
  hidden-positive vs scored-negative pixels (sampled, seed 7). Any feature with
  AUC >0.90 (or <0.10) is dropped and flagged before modelling.
- **Model (Experiment 2):** `HistGradientBoostingClassifier`
  (max_iter=300, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=200,
  l2=1.0, seed 7). Train on all visible positives + sampled visible negatives
  (≤400k, buffer-excluded, distance-stratified). Predict full grid.
  Comparators on the identical holdout/evaluator: (i) proximity-only belief,
  (ii) same GBM belief + Poisson-disk r=2.8, (iii) same GBM belief + EDGE,
  (iv) registry D28 and H33 rasters scored as-is — labelled LEAKY references
  (built with full-catalogue knowledge), never promotion gates.
- **Promotion gate:** EDGE-on-GBM pooled HOLDOUT-DTI must beat the best
  non-leaky comparator by ≥+0.005 and beat proximity-only; all canaries ≤0.90.
  Failure ⇒ verdict negative, no submission file promoted.
- **Final candidate (Experiment 3, only if gate passes):** retrain on full
  catalogue (same recipe), EDGE emission with truth-mass/dot budget transferred
  from the holdout operating point, support restricted to footprint pixels at
  catalogue distance >2 px. Novelty: surface Spearman and final-dot overlap
  (≤3 px) vs all 9 pinned registry rasters + all `docs/downloads/*.tif`;
  Spearman >0.90 or overlap >70% vs ANY one ⇒ duplicate-stop, verdict negative.
- **Writer/validator:** shared `write_submission_file`; primary file
  zeros-outside all-finite (matches the scored H33 "-zeros" convention and
  avoids the owner's "[0,1]" portal error), NaN-outside twin also written
  (published-spec literal). Both must pass `validate_submission.py`
  (zeros twin with `--finite-all-cells`). No slot is chosen by this session;
  promotion to a weekly slot remains the owner's separate selector step.
- **Number labelling:** every number is HOLDOUT-DTI (evaluator, n withheld, CI)
  or OWNER-REPORTED (unverified). Nothing is ORGANIZER-CONFIRMED; no
  projection is written as a score. Beating 0.2778 on the hidden test can
  neither be promised nor measured locally.
