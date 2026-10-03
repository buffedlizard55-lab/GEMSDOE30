#!/usr/bin/env python3
"""Metric-algebra emission experiment on hidden spatial quadrants (CPU, real data).

Why this experiment exists
--------------------------
The registered 2026-10-03 emission pilot compared thinning rules **at matched
emitted-pixel counts**.  Matching counts cannot detect the effect that matters:
the published index is

    DTI = A / (alpha*(A + F) + (1 - alpha)*G),

so the *number* of emitted dots is itself a free variable and the optimum sits
where the marginal credit/cost ratio ``dA/dF`` equals ``alpha*s/(1 - alpha*s)``.
A count-matched design therefore engineers a null result about the mechanism it
was meant to test.  This experiment instead lets every rule choose its own dot
count and reports the complete parameter curve.

Protocol (preregistered in docs/research/metric-emission-preregistration.md)
---------------------------------------------------------------------------
* Four fixed spatial quadrants of the real 3730x3292 prepared grid; each fold's
  model is fit on the other three quadrants only, with a 300 m buffer removed
  from training around the held-out block.
* Inside the held-out block the catalogue fault pixels play the role of the
  organizer's hidden "new faults" (stand-in truth).  The scored domain is the
  block; known-fault pixels outside the block are masked, mirroring the official
  rule that USGS/INGENIOUS pixels are excluded from evaluation.
* Rules compared on the *same* out-of-fold surface:
    dense   - binary threshold of the surface
    uniform - Poisson-disk thinning at a fixed radius (the owner's dotted family)
    adaptive- confidence-adaptive Poisson-disk thinning
    metric  - greedy selection by the published index's marginal rule
* Parameter selection is leave-one-fold-out: for fold f the parameter is chosen
  on the pooled other three folds and reported on fold f, so no fold is scored
  at a parameter tuned on itself.
* Pooling sums the sufficient statistics of the buffered blocks.  This omits
  300 m interactions across block seams; the script reports fold-isolated values
  and never presents the pooled number as an official score.

This is a proxy: the hidden truth is an expert-labelled set of faults *absent*
from the catalogue, so a pass here is necessary evidence, never a competition score.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.cv import spatial_quadrant_masks  # noqa: E402
from gemsdoe30.emission import (  # noqa: E402
    adaptive_disk_select,
    candidate_pool,
    dti_components_masked,
    metric_optimal_emission,
    poisson_disk_select,
)

_spec = importlib.util.spec_from_file_location("emission_holdout", ROOT / "scripts" / "emission_holdout.py")
assert _spec and _spec.loader
emission_holdout = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(emission_holdout)


def _quantile_thresholds(surface: np.ndarray, scored: np.ndarray, quantiles: list[float]) -> list[float]:
    values = surface[scored]
    values = values[np.isfinite(values)]
    if values.size == 0:
        return []
    return [float(np.quantile(values, q)) for q in quantiles]


def _emit(rule: str, surface: np.ndarray, scored: np.ndarray, threshold: float, radius: float,
          gamma: float, pool_limit: int) -> np.ndarray:
    values = np.where(scored, surface, -np.inf).astype(np.float32)
    if rule == "dense":
        return np.isfinite(values) & (values >= threshold)
    if rule == "metric":
        return metric_optimal_emission(values, scored, pool_limit=pool_limit)
    if rule == "uniform":
        return poisson_disk_select(values, radius, mask=scored, limit=pool_limit)
    if rule == "adaptive":
        return adaptive_disk_select(values, radius, gamma=gamma, mask=scored, limit=pool_limit)
    raise ValueError(rule)


def _score(prediction: np.ndarray, truth: np.ndarray, scored: np.ndarray) -> dict:
    components = dti_components_masked(prediction.astype(np.float32), truth.astype(np.float32), scored)
    components["emitted_pixels"] = int(np.count_nonzero(prediction & scored))
    return components


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/metric-emission"))
    parser.add_argument("--buffer-m", type=float, default=300.0)
    parser.add_argument("--per-class", type=int, default=120000)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--pool-limit", type=int, default=120000)
    parser.add_argument("--feature-set", choices=("bands", "all"), default="all")
    parser.add_argument("--reuse-surfaces", action="store_true")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels = np.load(args.data_dir / "labels.npy")
    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    stack = emission_holdout.FeatureStack(args.data_dir, args.raw_dir, feature_set=args.feature_set)

    quantiles = [0.90, 0.95, 0.98, 0.99, 0.995, 0.999]
    radii = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
    report: dict = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "hidden spatial quadrant (300 m buffer); block catalogue pixels are stand-in truth; "
                    "known-fault pixels outside the block masked; every rule chooses its own dot count",
        "features": stack.names,
        "grid": {"quantiles": quantiles, "radii_px": radii, "adaptive_gammas": [1.0]},
        "design_note": "previous count-matched emission pilot could not detect a marginal-rule effect; "
                       "this design sweeps each rule's own operating point",
        "folds": [],
    }

    curves: dict[int, dict[str, dict[str, dict]]] = {}
    surfaces: dict[int, Path] = {}
    for fold in range(4):
        train_mask, block_mask = spatial_quadrant_masks(valid, fold, buffer_m=args.buffer_m)
        truth = (labels == 1) & block_mask
        scored = block_mask & valid
        band = args.output_dir / f"fold{fold}"
        band.mkdir(parents=True, exist_ok=True)
        surfaces[fold] = band / "surface.npy"
        if not (args.reuse_surfaces and surfaces[fold].exists()):
            ys, xs, target = emission_holdout.sample_training_pixels(
                stack, labels, train_mask, args.per_class, args.seed + fold)
            matrix = emission_holdout.gather_rows(stack, ys, xs)
            model, centre, scale = emission_holdout.fit_model(matrix, target, args.seed + fold)
            emission_holdout.predict_surface(stack, model, centre, scale, valid, band)
        curves_path = band / "curves.json"
        if args.reuse_surfaces and curves_path.exists():
            cached = json.loads(curves_path.read_text(encoding="utf-8"))
            curves[fold] = cached["rules"]
            thresholds = cached["thresholds"]
            report["folds"].append(cached["fold_summary"])
            print(f"fold {fold}: reused cached curves ({len(curves[fold])} rules)", flush=True)
            continue
        surface = np.load(surfaces[fold], mmap_mode="r")
        values = np.asarray(surface)
        curves[fold] = {}
        thresholds = _quantile_thresholds(values, scored, quantiles)
        for index, threshold in enumerate(thresholds):
            tag = f"q{quantiles[index]:g}"
            curves[fold][f"dense@{tag}"] = _score(_emit("dense", values, scored, threshold, 0, 0, args.pool_limit),
                                                  truth, scored)
            curves[fold][f"metric@{tag}"] = _score(
                _emit("metric", values, scored, threshold, 0, 0, args.pool_limit), truth, scored)
            for radius in radii:
                curves[fold][f"uniform@{tag}@r{radius:g}"] = _score(
                    _emit("uniform", values, scored, threshold, radius, 0, args.pool_limit), truth, scored)
            for radius in (2.0, 3.0, 5.0, 8.0):
                curves[fold][f"adaptive@{tag}@r{radius:g}"] = _score(
                    _emit("adaptive", values, scored, threshold, radius, 1.0, args.pool_limit), truth, scored)
        fold_summary = {
            "fold": fold,
            "block_pixels": int(scored.sum()),
            "block_truth_pixels": int(truth.sum()),
            "thresholds": thresholds,
        }
        report["folds"].append(fold_summary)
        curves_path.write_text(json.dumps({"fold_summary": fold_summary, "thresholds": thresholds,
                                          "rules": curves[fold]}), encoding="utf-8")
        print(f"fold {fold}: block={int(scored.sum())} truth={int(truth.sum())} "
              f"rules={len(curves[fold])}", flush=True)

    # Leave-one-fold-out parameter selection per rule family.
    families = ("dense", "metric", "uniform", "adaptive")
    selection: dict[str, list] = {}
    for family in families:
        names = sorted({name for fold in curves for name in curves[fold] if name.split("@")[0] == family})
        per_fold_choice = []
        for fold in range(4):
            others = [f for f in range(4) if f != fold]
            best_name, best_value = None, -np.inf
            for name in names:
                components = [curves[f][name] for f in others if name in curves[f]]
                if len(components) != len(others):
                    continue
                tp = sum(c["tp_weight"] for c in components)
                fp = sum(c["fp_weight"] for c in components)
                g = sum(c["truth_pixels"] for c in components)
                pooled = tp / (0.2 * (tp + fp) + 0.8 * g) if g > 0 else 0.0
                if pooled > best_value:
                    best_name, best_value = name, pooled
            held = curves[fold].get(best_name)
            per_fold_choice.append({
                "fold": fold,
                "chosen_on_other_folds": best_name,
                "pooled_other_folds_dti": best_value,
                "held_out_dti": None if held is None else held["dti"],
                "held_out_emitted_pixels": None if held is None else held["emitted_pixels"],
                "held_out_fp_weight": None if held is None else held["fp_weight"],
            })
        selection[family] = per_fold_choice

    # Pooled cross-validated estimate: sum each fold's statistics at its own choice.
    pooled_cv: dict[str, dict] = {}
    for family in families:
        tp = fp = g = 0.0
        emitted = 0
        for row in selection[family]:
            name = row["chosen_on_other_folds"]
            fold = row["fold"]
            if name not in curves[fold]:
                continue
            c = curves[fold][name]
            tp += c["tp_weight"]
            fp += c["fp_weight"]
            g += c["truth_pixels"]
            emitted += c["emitted_pixels"]
        pooled_cv[family] = {
            "pooled_tp_weight": tp, "pooled_fp_weight": fp, "pooled_proxy_truth": g,
            "pooled_emitted_pixels": emitted,
            "pooled_dti": tp / (0.2 * (tp + fp) + 0.8 * g) if g > 0 else None,
        }

    # Oracle maxima (clearly labelled, not a selectable result).
    oracle = {}
    for family in families:
        best = {}
        for fold in range(4):
            names = [n for n in curves[fold] if n.split("@")[0] == family]
            if not names:
                continue
            name = max(names, key=lambda n: curves[fold][n]["dti"])
            best[fold] = {"rule": name, "dti": curves[fold][name]["dti"]}
        oracle[family] = best

    report["curves"] = {str(fold): curves[fold] for fold in curves}
    report["selection"] = selection
    report["pooled_cross_validated"] = pooled_cv
    report["oracle_on_holdout_not_selectable"] = oracle
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({"pooled_cross_validated": pooled_cv}, indent=1))
    print(f"wrote {args.output_dir / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
