#!/usr/bin/env python3
"""Hidden-quadrant holdout for lineament surfaces and metric-aware emission rules.

Protocol (spatially blocked, official masking semantics)
-------------------------------------------------------
* Four fixed quadrants; a 300 m buffer removes kernel interactions across seams.
* For fold ``f`` the model is fit on the other three quadrants only and predicts
  quadrant ``f`` (no label leakage from the scored block).
* Within the block, the catalogue faults play the role of the organizer's
  "new faults" (truth) and every pixel outside the block is masked exactly as the
  organizer masks known USGS/INGENIOUS pixels.  Fold-isolated sufficient
  statistics are summed, which is exact for a local kernel when the blocks are
  buffered, and the pooled DTI is recomputed from the pooled sums.
* Emission rules are compared at matched emitted-pixel counts, paired per fold.

This is a proxy: the real hidden truth is a small set of expert-labelled faults
absent from the catalogue, and a catalogue holdout can reward catalogue-like
faults.  A pass here is necessary evidence, never a competition score.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemsdoe30.cv import spatial_quadrant_masks  # noqa: E402
from gemsdoe30.emission import (  # noqa: E402
    adaptive_disk_select,
    candidate_pool,
    credit_retention,
    dti_from_components,
    poisson_disk_select,
)

BAND_INDEX = {
    "mag_anom": 0, "rtp": 1, "tmi_hg": 2, "geod_2ndinv": 3, "iso_grav_anom_slope": 4,
    "tc": 5, "geod_shearrate": 6, "geod_dilaterate": 7, "tmi_vg": 8, "deq_n100a15": 9,
    "iso_grav_anom_vg": 10, "det_elev": 11, "iso_grav_anom": 12, "tmi": 13,
    "depth_to_base_surf": 14, "ieq_n100a15": 15, "cond_surf": 16,
    "iso_grav_anom_hg": 17, "det_elev_slope": 18,
}
FEATURES_BANDS = [
    ("tmi_hg", "band", "tmi_hg"), ("iso_grav_anom_hg", "band", "iso_grav_anom_hg"),
    ("iso_grav_anom_slope", "band", "iso_grav_anom_slope"), ("det_elev_slope", "band", "det_elev_slope"),
    ("tmi_vg", "band", "tmi_vg"), ("depth_to_base_surf", "band", "depth_to_base_surf"),
    ("cond_surf", "band", "cond_surf"), ("deq_n100a15", "band", "deq_n100a15"),
    ("geod_2ndinv", "band", "geod_2ndinv"), ("det_elev", "band", "det_elev"),
]
FEATURES_EXTERNAL = [
    ("K", "rad", 0), ("Th", "rad", 1), ("U", "rad", 2), ("TC", "rad", 3),
    ("ThK", "ext", 0), ("UK", "ext", 1), ("UTh", "ext", 2), ("TMI_up150", "ext", 3),
    ("step_max", "scarp", 2), ("cross_max", "scarp", 7), ("relief", "scarp", 8),
    ("coh100", "scarp", 9),
]
FEATURES = [
    ("tmi_hg", "band", "tmi_hg"), ("iso_grav_anom_hg", "band", "iso_grav_anom_hg"),
    ("iso_grav_anom_slope", "band", "iso_grav_anom_slope"), ("det_elev_slope", "band", "det_elev_slope"),
    ("tmi_vg", "band", "tmi_vg"), ("depth_to_base_surf", "band", "depth_to_base_surf"),
    ("cond_surf", "band", "cond_surf"), ("deq_n100a15", "band", "deq_n100a15"),
    ("geod_2ndinv", "band", "geod_2ndinv"), ("det_elev", "band", "det_elev"),
    ("K", "rad", 0), ("Th", "rad", 1), ("U", "rad", 2), ("TC", "rad", 3),
    ("ThK", "ext", 0), ("UK", "ext", 1), ("UTh", "ext", 2), ("TMI_up150", "ext", 3),
    ("step_max", "scarp", 2), ("cross_max", "scarp", 7), ("relief", "scarp", 8),
    ("coh100", "scarp", 9),
]


def _open(path: Path):
    import rasterio
    return rasterio.open(path)


class FeatureStack:
    """Tiled reader that assembles the model matrix without holding the full grid."""

    def __init__(self, data_dir: Path, raw_dir: Path, feature_set: str = "all",
                 features: list | None = None):
        if features is None:
            features = FEATURES if feature_set == "all" else FEATURES_BANDS
        self._features = features
        self.bands = np.load(data_dir / "features_raw.npy", mmap_mode="r")
        self.rad = _open(raw_dir / "external" / "geodawn_rad_u8.tif")
        self.ext = _open(raw_dir / "external" / "geodawn_extensions_u8.tif")
        self.scarp = _open(raw_dir / "external" / "lidar_scarp_features_u8.tif")
        self.shape = self.bands.shape[1:]
        self.features = self._features
        self.names = [name for name, _, _ in self.features]

    def read(self, y0: int, y1: int, x0: int, x1: int) -> np.ndarray:
        out = []
        for name, source, key in self.features:
            if source == "band":
                out.append(np.asarray(self.bands[BAND_INDEX[key], y0:y1, x0:x1], dtype=np.float32))
            elif source == "rad":
                out.append(self.rad.read(key + 1, window=((y0, y1), (x0, x1))).astype(np.float32))
            elif source == "ext":
                out.append(self.ext.read(key + 1, window=((y0, y1), (x0, x1))).astype(np.float32))
            else:
                out.append(self.scarp.read(key + 1, window=((y0, y1), (x0, x1))).astype(np.float32))
        stack = np.stack(out, axis=0)
        stack[stack <= -1e37] = np.nan
        return stack


def sample_training_pixels(stack: FeatureStack, labels: np.ndarray, train_mask: np.ndarray,
                           per_class: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    rows = np.flatnonzero(train_mask.any(axis=1))
    cols = np.flatnonzero(train_mask.any(axis=0))
    ys, xs = np.nonzero(train_mask & (labels == 1))
    if ys.size == 0:
        raise ValueError("training fold has no positive pixels")
    take_pos = min(per_class, ys.size)
    sel = rng.choice(ys.size, take_pos, replace=False)
    pos_y, pos_x = ys[sel], xs[sel]
    # Rejection-sample negatives so the two classes share the training footprint.
    neg_y, neg_x = [], []
    attempts = 0
    while len(neg_y) < per_class and attempts < 200:
        attempts += 1
        cy = rng.integers(rows[0], rows[-1] + 1, size=per_class * 4)
        cx = rng.integers(cols[0], cols[-1] + 1, size=per_class * 4)
        keep = train_mask[cy, cx] & (labels[cy, cx] == 0)
        neg_y.extend(cy[keep].tolist())
        neg_x.extend(cx[keep].tolist())
    neg_y = np.asarray(neg_y[:per_class]); neg_x = np.asarray(neg_x[:per_class])
    return (np.concatenate([pos_y, neg_y]), np.concatenate([pos_x, neg_x]),
            np.concatenate([np.ones(pos_y.size, dtype=np.int8), np.zeros(neg_y.size, dtype=np.int8)]))


def gather_rows(stack: FeatureStack, ys: np.ndarray, xs: np.ndarray, block: int = 4096) -> np.ndarray:
    out = np.empty((ys.size, len(stack.features)), dtype=np.float32)
    for start in range(0, ys.size, block):
        stop = min(start + block, ys.size)
        y0, y1 = int(ys[start:stop].min()), int(ys[start:stop].max()) + 1
        x0, x1 = int(xs[start:stop].min()), int(xs[start:stop].max()) + 1
        tile = stack.read(y0, y1, x0, x1)
        out[start:stop] = tile[:, ys[start:stop] - y0, xs[start:stop] - x0].T
    return out


def fit_model(matrix: np.ndarray, target: np.ndarray, seed: int):
    from sklearn.ensemble import HistGradientBoostingClassifier
    median = np.nanmedian(matrix, axis=0)
    median = np.where(np.isfinite(median), median, 0.0)
    filled = np.where(np.isfinite(matrix), matrix, median)
    centre = filled.mean(axis=0)
    scale = filled.std(axis=0)
    scale[scale < 1e-6] = 1.0
    model = HistGradientBoostingClassifier(max_iter=120, learning_rate=0.08, max_depth=6,
                                           random_state=seed, early_stopping=False)
    model.fit((filled - centre) / scale, target)
    return model, centre, scale


def predict_surface(stack: FeatureStack, model, centre, scale, valid: np.ndarray,
                    band: Path, row_block: int = 96) -> None:
    rows = np.flatnonzero(valid.any(axis=1))
    cols = np.flatnonzero(valid.any(axis=0))
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    x0, x1 = int(cols[0]), int(cols[-1]) + 1
    surface = np.lib.format.open_memmap(band / "surface.npy", mode="w+", dtype=np.float32,
                                        shape=tuple(valid.shape))
    surface[:] = np.nan
    for start in range(y0, y1, row_block):
        stop = min(start + row_block, y1)
        tile = stack.read(start, stop, x0, x1)
        flat = tile.reshape(len(stack.features), -1).T
        filled = np.where(np.isfinite(flat), flat, centre)
        probability = model.predict_proba((filled - centre) / scale)[:, 1]
        block = probability.reshape(stop - start, x1 - x0)
        surface[start:stop, x0:x1] = np.where(valid[start:stop, x0:x1], block, np.nan)
    surface.flush()


def run_rule(score: np.ndarray, mask: np.ndarray, radius: float, gamma: float,
             rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    values = np.where(mask, score, -np.inf).astype(np.float32)
    if gamma == 0.0:
        return poisson_disk_select(values, radius, mask=mask, limit=rows.size)
    return adaptive_disk_select(values, radius, gamma=gamma, mask=mask, limit=rows.size)


def calibrate_and_select(score: np.ndarray, mask: np.ndarray, target: int, *, gamma: float,
                         limit: int) -> tuple[np.ndarray, float]:
    """Expand-then-bisect on the exclusion radius until the emitted count matches."""

    values = np.where(mask, np.asarray(score, dtype=np.float32), -np.inf).astype(np.float32)
    pool_rows, pool_cols = candidate_pool(values, mask, limit)
    low, high = 0.5, 64.0
    for _ in range(18):
        kept = run_rule(values, mask, high, gamma, pool_rows, pool_cols)
        if int(kept.sum()) <= target:
            break
        high *= 1.6
    else:
        kept = run_rule(values, mask, high, gamma, pool_rows, pool_cols)
    best = (high, int(kept.sum()))
    for _ in range(14):
        mid = 0.5 * (low + high)
        kept = run_rule(values, mask, mid, gamma, pool_rows, pool_cols)
        count = int(kept.sum())
        if abs(count - target) < abs(best[1] - target):
            best = (mid, count)
        if count > target:
            low = mid
        else:
            high = mid
    return run_rule(values, mask, best[0], gamma, pool_rows, pool_cols), best[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("runs/emission"))
    parser.add_argument("--buffer-m", type=float, default=300.0)
    parser.add_argument("--per-class", type=int, default=120000)
    parser.add_argument("--budget-per-fold", type=int, default=11025)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--pool-limit", type=int, default=180000)
    parser.add_argument("--reuse-surfaces", action="store_true")
    parser.add_argument("--feature-set", choices=("bands", "all"), default="all")
    parser.add_argument("--tag", default="all")
    args = parser.parse_args()
    args.output_dir = args.output_dir / args.tag
    args.output_dir.mkdir(parents=True, exist_ok=True)

    labels = np.load(args.data_dir / "labels.npy")
    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    stack = FeatureStack(args.data_dir, args.raw_dir, feature_set=args.feature_set)
    if stack.shape != valid.shape:
        raise SystemExit(f"shape mismatch: features {stack.shape} vs masks {valid.shape}")

    report: dict[str, object] = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "hidden quadrant, 300 m buffer, catalogue fault pixels as proxy truth, "
                    "pixels outside the scored block masked (official known-fault masking analogue)",
        "features": stack.names,
        "feature_set": args.feature_set,
        "budget_per_fold": args.budget_per_fold,
        "folds": [],
    }
    rules = {"uniform": 0.0, "adaptive": 1.0}
    per_rule_totals = {name: {"tp": 0.0, "fp": 0.0, "truth": 0.0, "emitted": 0} for name in rules}
    fold_reports = []
    for fold in range(4):
        train_mask, block_mask = spatial_quadrant_masks(valid, fold, buffer_m=args.buffer_m)
        truth = labels == 1
        scored = block_mask & valid & ~(truth & ~block_mask)  # block pixels only, nothing masked inside
        band = args.output_dir / f"fold{fold}"
        band.mkdir(exist_ok=True)
        if not (args.reuse_surfaces and (band / "surface.npy").exists()):
            ys, xs, target = sample_training_pixels(stack, labels, train_mask, args.per_class, args.seed + fold)
            matrix = gather_rows(stack, ys, xs)
            model, centre, scale = fit_model(matrix, target, args.seed + fold)
            predict_surface(stack, model, centre, scale, valid, band)
        surface = np.load(band / "surface.npy", mmap_mode="r")
        block_surface = np.where(scored, np.asarray(surface), -1.0).astype(np.float32)
        fold_result = {"fold": fold,
                       "block_pixels": int(scored.sum()),
                       "block_truth_pixels": int((truth & scored).sum()),
                       "rules": {}}
        for name, gamma in rules.items():
            kept, radius = calibrate_and_select(block_surface, scored, args.budget_per_fold,
                                                gamma=gamma, limit=args.pool_limit)
            prediction = np.where(kept, 1.0, 0.0).astype(np.float32)
            stats_truth = truth & scored
            stats = _masked_stats(prediction, stats_truth, scored)
            fold_result["rules"][name] = {
                "radius_px": radius,
                "emitted": int(kept.sum()),
                "dti": stats["dti"],
                "credit_retention_vs_block_truth": credit_retention(kept, stats_truth),
                "tp_weight": stats["tp"], "fp_weight": stats["fp"],
                "fp_per_emitted": stats["fp"] / max(int(kept.sum()), 1),
            }
            totals = per_rule_totals[name]
            totals["tp"] += stats["tp"]; totals["fp"] += stats["fp"]
            totals["truth"] += stats["truth"]; totals["emitted"] += int(kept.sum())
        fold_result["rules"]["uniform"]["emitted_delta_vs_adaptive"] = (
            fold_result["rules"]["uniform"]["emitted"] - fold_result["rules"]["adaptive"]["emitted"])
        fold_reports.append(fold_result)
        print(f"fold {fold}: " + " | ".join(
            f"{name} dti={fold_result['rules'][name]['dti']:.5f} "
            f"n={fold_result['rules'][name]['emitted']} r={fold_result['rules'][name]['radius_px']:.2f}"
            for name in rules), flush=True)

    pooled = {}
    for name, totals in per_rule_totals.items():
        pooled[name] = {
            "dti": dti_from_components(totals["tp"], totals["fp"], totals["truth"]),
            "tp_weight": totals["tp"], "fp_weight": totals["fp"],
            "truth_pixels": totals["truth"], "emitted": totals["emitted"],
        }
    report["folds"] = fold_reports
    report["pooled"] = pooled
    report["paired_delta_dti_adaptive_minus_uniform"] = pooled["adaptive"]["dti"] - pooled["uniform"]["dti"]
    report["folds_positive"] = sum(
        1 for fold in fold_reports
        if fold["rules"]["adaptive"]["dti"] > fold["rules"]["uniform"]["dti"])
    report["gate"] = {
        "criterion": "pooled delta > 0.0 with positive folds >= 3/4",
        "passed": bool(report["paired_delta_dti_adaptive_minus_uniform"] > 0.0 and report["folds_positive"] >= 3),
        "scope": "catalogue proxy; not an organizer score",
    }
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("pooled", "paired_delta_dti_adaptive_minus_uniform",
                                             "folds_positive", "gate")}, indent=1))
    return 0


def _masked_stats(prediction: np.ndarray, truth: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    from gemsdoe30.emission import dti_components_masked
    stats = dti_components_masked(prediction, truth, mask)
    return {"tp": stats["tp_weight"], "fp": stats["fp_weight"],
            "truth": stats["truth_pixels"], "dti": stats["dti"]}


if __name__ == "__main__":
    raise SystemExit(main())
