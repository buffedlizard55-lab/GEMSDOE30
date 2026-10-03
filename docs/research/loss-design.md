# Metric-aligned, 300 m boundary-aware loss

## Why change the objective

The competition scores continuous probabilities, not hard masks. Its official definition uses a 300 m triangular kernel: a nearby prediction can earn fractional true-positive credit, while the same off-trace probability still incurs a distance-weighted false-positive cost. A conventional regional overlap loss gives an exact-overlap view of error and generally cannot distinguish two equally non-overlapping predictions solely by their distance to a line label. A GEMS-specific geometry term can resolve that mismatch.

The official distance-weighted terms are:

\[
 k(d)=\max(1-d/R,0),\quad R=300\text{ m},
\]

\[
 TP_w=\sum_{g\in G}\max_{x:d(x,g)\le R} p(x)k(d(x,g)),
\]

\[
 FP_w=\sum_x p(x)\left(1-\max_{g\in G} k(d(x,g))\right),
 \qquad FN_w=\sum_{g\in G}\left[1-\max_{x:d(x,g)\le R}p(x)k(d(x,g))\right],
\]

\[
 DTI=\frac{TP_w}{TP_w+0.2FP_w+0.8FN_w+\epsilon}.
\]

On the challenge's 100 m square grid, a unit-probability prediction one cell (100 m) away from one isolated truth pixel obtains `TPw=2/3`, `FNw=1/3`, `FPw=1/3`, and DTI approximately 0.667. At 200 m it obtains `TPw=1/3`, and at 300 m the triangular-kernel credit is zero. The executable synthetic check is `python scripts/loss_geometry_probe.py`.

## Implemented objective

The training scaffold's regional control is soft-Tversky. This implementation keeps that regional term and adds a GEMS-specific geometry term for the paired ablation:

\[
 L_{regional}=1-\frac{TP_{pixel}+\epsilon}{TP_{pixel}+0.2FP_{pixel}+0.8FN_{pixel}+\epsilon},
\]

\[
 L_{geometry}=1-DTI_{300m},\qquad
 L_{combined}=1.0L_{regional}+0.5L_{geometry}.
\]

`src/gemsdoe30/losses.py::GEMSBoundaryAwareLoss` implements both parts. Its geometry term uses a label-side Euclidean distance transform for the false-positive weight, and the exact discrete neighborhood maximum for per-truth-pixel probability credit. Predictions are sigmoid probabilities; gradients flow through the probability values and neighborhood maximum (subgradient at ties), while the fixed target distance transform is not differentiated. The metric utilities in `metric.py` provide an independent reference implementation for evaluation.

The geometry coefficient 0.5 is a declared starting comparison setting, **not a validated optimum**. Run a frozen sweep only after the primary paired comparison, and do not select a value from the public leaderboard. Empty-label patches are excluded from the geometry ratio because the official DTI is degenerate when `G` is empty; the regional component remains active and can penalize false positives.

## Relation to Kervadec et al.

Kervadec, Bouchtiba, Desrosiers, Granger, Dolz, and Ben Ayed submitted an arXiv preprint in 2018 and published *Boundary loss for highly unbalanced segmentation* at MIDL 2019 (PMLR 102, pp. 285–296). Their paper motivates a contour/distance-oriented term that **complements** regional losses, and reports results on highly unbalanced medical-image segmentation datasets. That is relevant motivation for this experiment, not evidence that it will improve geological-fault scores.

This repository does **not** claim to reproduce their signed-distance surface loss verbatim. It uses a GEMS-specific distance-weighted Tversky surrogate to match the competition's triangular kernel and loss arithmetic. The class/docstrings call this Kervadec-inspired and state the distinction. A pure regional objective remains the paired ablation control.

## What is tested today

- Unit tests check the 300 m kernel, the official weighted-count arithmetic example (`TPw=3`, `FPw=1.89`, `FNw=2` gives 0.60), exact alignment, fractional 100/200 m near misses, the 300 m cutoff, footprint masking, and invalid probability rejection.
- The optional gradient suite compares the differentiable EDT/kernel loss directly against the independent full-grid metric implementation on a masked raster; it also tests finite gradients and non-finite parameter rejection.
- `tests/test_cv.py` places an OOF prediction 100 m across a quadrant seam: the exact whole-grid score retains its 2/3 credit, while the quadrant-isolated diagnostics correctly show why they must not be pooled. The OOF evaluator also rejects a changed array whose hash no longer matches its sidecar.
- `scripts/loss_geometry_probe.py` compares regional and metric geometry losses for a single-pixel synthetic translation. The regional loss ties non-overlapping shifts; the combined objective orders the 100 m miss ahead of the 200 m and farther misses.
- A disposable 64×64 synthetic pipeline smoke passed data preparation, both loss arms across four folds, OOF inference/stitching/evaluation, full-data fit, GeoTIFF writing, and exact-template format validation. This checks software plumbing only.

**Not tested:** training on GEMS rasters, change in real held-out near misses, improvement over a real spatial-holdout baseline, competition score, or private-test/generalization performance. No competition data or template were in this checkout.

## Real-data experiment protocol

1. Use identical model, initial weights, train/validation spatial folds, patch draws, optimizer steps, and seeds for the regional and combined arms.
2. Split in buffered spatial blocks and hold entire spatial areas/components out. Training labels must not enter the held-out fold's distance transform. The code accepts a `valid_mask` for labels and a separate `loss_mask` so an input halo can support the 300 m transform while only core pixels contribute to loss.
3. Score the complete stitched OOF mosaic once with the exact metric implementation and the full label-valid footprint. This preserves 300 m true-positive and false-positive interactions across quadrant boundaries. Fold-isolated DTI values are heterogeneity diagnostics only; do not sum their components or treat them as the exact pooled score.
4. Report each fold and seed, pooled score, metric components, exact-pixel overlap diagnostics, and the distance profile of held-out truth credit and false-positive mass. The explicit behavioral test is whether the combined model reduces missed/low-credit truth at 100–200 m relative to the exact-overlap control without creating excessive far-field FP mass.
5. Pre-register the confirmation gate and minimum gain. A single positive screen is not promotion. No candidate is eligible for a weekly slot until confirmation and exact-file audit pass.

## Known optimization risks

- A ratio loss computed per training patch is only an approximation to a region-wide pooled score; use the exact full-block metric for selection.
- The metric's maximum can yield sparse gradients when predictions are far from positives. Positive-centered patch sampling and the regional loss are intended to maintain useful gradients, but must be checked empirically.
- Label and target incompleteness mean catalogue holdout tests are proxies. A change that improves known-fault recovery may not improve expert-mapped unmapped faults.
- Patch edges truncate the 300 m neighborhood. The sampler supplies a three-cell halo and excludes its edge from the loss; real training/inference should keep this invariant.
- Kernel geometry is planar pixel-centre distance in the projected grid. Confirm pixel size, CRS, and affine transform against the organizer's actual template before using it.
