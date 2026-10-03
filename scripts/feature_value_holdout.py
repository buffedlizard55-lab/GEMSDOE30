#!/usr/bin/env python3
"""Spatially blocked *feature-value* holdout for additional geological layers.

Why this exists
---------------
The competition's private test set is a set of expert-labelled faults that are
NOT in the public USGS/INGENIOUS catalogue
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
Any candidate geological hypothesis must therefore be tested for whether it
carries *generalising* information about faults, not merely whether it can
memorise the catalogue.

This script runs a cheap, reproducible, paired ablation:

  * identical model class and identical hyper-parameters in every arm;
  * identical spatially blocked folds (four quadrants, 300 m exclusion buffer);
  * the *only* difference between arms is the set of input layers;
  * scoring is the exact official DTI pooled over the stitched OOF mosaic.

A cheap linear/boosted model is used deliberately: if an added layer does not
help even in a low-variance model class, the CNN is unlikely to rescue it, and
the ablation costs minutes instead of hours on CPU.

Limitations (recorded so nothing here is over-claimed):
  * the truth is still the public catalogue, i.e. a PROXY for the private new-fault
    set; a pass here is necessary, not sufficient;
  * the catalogue-derived distance fields (``dist_known_fault_px`` in the GDR
    exports) are label-derived and are never used as inputs.
"""

from __future__ import annotations

import sys
import argparse
import json
import time
from pathlib import Path

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier


# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.cv import spatial_quadrant_masks
from gemsdoe30.metric import distance_weighted_tversky

EXTERNAL = {
    "lidar_scarp": ("data/external/lidar_scarp_features_u8.tif", None),
    "geodawn_rad": ("data/external/geodawn_rad_u8.tif", None),
    "geodawn_ext": ("data/external/geodawn_extensions_u8.tif", None),
}


def load_external(path: Path) -> tuple[np.ndarray, list[str]]:
    with rasterio.open(path) as ds:
        array = ds.read().astype(np.float32)
        names = list(ds.descriptions)
        valid = array.sum(axis=0) != 0  # nodata==0 in these quantised layers
    array[:, ~valid] = np.nan
    return array, names


def assemble(features_dir: Path, arms: list[str]) -> tuple[np.ndarray, list[str]]:
    """Stack the requested channel groups into one float32 [C,H,W] array (memmap-backed)."""
    base = np.load(features_dir / "features_raw.npy", mmap_mode="r")
    blocks = [np.asarray(base, dtype=np.float32)]
    names = [f"official_{i}" for i in range(base.shape[0])]
    for arm in arms:
        path, _ = EXTERNAL[arm]
        array, channel_names = load_external(Path(path))
        blocks.append(array)
        names.extend(f"{arm}:{name}" for name in channel_names)
    return np.concatenate(blocks, axis=0), names


def sample_training_pixels(
    features: np.ndarray,
    labels: np.ndarray,
    train_mask: np.ndarray,
    *,
    negatives_per_positive: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    positives = np.argwhere(train_mask & (labels > 0.5))
    candidates = np.argwhere(train_mask & (labels < 0.5))
    if not len(positives) or not len(candidates):
        raise ValueError("training fold lacks positives or negatives")
    take = min(len(candidates), negatives_per_positive * len(positives))
    choice = rng.choice(len(candidates), size=take, replace=False)
    negatives = candidates[choice]
    coords = np.concatenate([positives, negatives], axis=0)
    target = np.concatenate([np.ones(len(positives)), np.zeros(len(negatives))])
    x = features[:, coords[:, 0], coords[:, 1]].T.astype(np.float32)
    return x, target


def fit_standardiser(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    median = np.nanmedian(x, axis=0)
    median = np.where(np.isfinite(median), median, 0.0)
    filled = np.where(np.isfinite(x), x, median)
    q1, q3 = np.percentile(filled, [25, 75], axis=0)
    scale = (q3 - q1) / 1.349
    scale = np.where(np.isfinite(scale) & (scale > 1e-8), scale, 1.0)
    return median, scale


def predict_grid(model, features: np.ndarray, median, scale, valid, *, block=256) -> np.ndarray:
    height, width = valid.shape
    out = np.zeros((height, width), dtype=np.float32)
    channels = features.shape[0]
    for row in range(0, height, block):
        r1 = min(row + block, height)
        for col in range(0, width, block):
            c1 = min(col + block, width)
            block_valid = valid[row:r1, col:c1]
            if not block_valid.any():
                continue
            data = features[:, row:r1, col:c1].reshape(channels, -1).T.astype(np.float32)
            flat_valid = block_valid.reshape(-1)
            data = data[flat_valid]
            data = np.where(np.isfinite(data), data, median)
            probability = model.predict_proba((data - median) / scale)[:, 1]
            target = np.zeros((r1 - row, c1 - col), dtype=np.float32)
            target.reshape(-1)[flat_valid] = probability.astype(np.float32)
            out[row:r1, col:c1] = target
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--labels", type=Path, default=Path("data/raw/labels.tif"))
    parser.add_argument("--arms", nargs="+", default=["base", "base+scarp", "base+scarp+rad"])
    parser.add_argument("--negatives-per-positive", type=int, default=6)
    parser.add_argument("--max-iter", type=int, default=120)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/feature-value-holdout.json"))
    parser.add_argument("--oof-dir", type=Path, default=Path("runs/feature-value"))
    args = parser.parse_args()

    with rasterio.open(args.labels) as ds:
        labels = ds.read(1).astype(np.float32)
    labels = (labels == 1).astype(np.float32)
    valid = np.load(args.data_dir / "valid.npy").astype(bool, copy=False)
    label_valid = np.load(args.data_dir / "label_valid.npy").astype(bool, copy=False)
    domain = valid & label_valid

    arm_specs = {
        "base": [],
        "base+scarp": ["lidar_scarp"],
        "base+rad": ["geodawn_rad", "geodawn_ext"],
        "base+scarp+rad": ["lidar_scarp", "geodawn_rad", "geodawn_ext"],
        "scarp_only": ["lidar_scarp"],
    }

    results: dict = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "purpose": "paired spatially-blocked feature-value ablation, catalogue proxy truth",
        "proxy_caveat": (
            "Truth is the public catalogue; the private test set is a different, sparser set of "
            "expert-labelled new faults. A win here is necessary but not sufficient."
        ),
        "folds": "four quadrants with a 300 m (3 px) training exclusion buffer",
        "model": {
            "class": "sklearn.ensemble.HistGradientBoostingClassifier",
            "max_iter": args.max_iter,
            "negatives_per_positive": args.negatives_per_positive,
            "seed": args.seed,
            "note": "identical hyper-parameters and sampling in every arm; only inputs differ",
        },
        "arms": {},
    }

    oof_paths: dict[str, Path] = {}
    for arm in args.arms:
        if arm not in arm_specs:
            raise SystemExit(f"unknown arm {arm!r}; choose from {sorted(arm_specs)}")
        extra = arm_specs[arm]
        base = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
        if extra:
            features, names = assemble(args.data_dir, extra)
        else:
            features = np.asarray(base, dtype=np.float32)
            names = [f"official_{i}" for i in range(base.shape[0])]
        mosaic = np.zeros(labels.shape, dtype=np.float32)
        fold_rows = []
        for fold in range(4):
            train_mask, validation = spatial_quadrant_masks(domain, fold, buffer_m=300.0)
            train_mask &= domain
            x, y = sample_training_pixels(
                features, labels, train_mask,
                negatives_per_positive=args.negatives_per_positive, seed=args.seed + fold,
            )
            median, scale = fit_standardiser(x)
            x = np.where(np.isfinite(x), x, median)
            model = HistGradientBoostingClassifier(
                max_iter=args.max_iter, learning_rate=0.1, max_leaf_nodes=31,
                early_stopping=False, random_state=args.seed + fold,
            )
            model.fit((x - median) / scale, y)
            del x
            prediction = predict_grid(model, features, median, scale, domain)
            mosaic[validation] = prediction[validation]
            fold_rows.append({
                "fold": fold,
                "train_pixels_sampled": int(len(y)),
                "train_positives": int(y.sum()),
            })
            print(f"  arm {arm} fold {fold} done", flush=True)

        scored = domain.copy()
        components = distance_weighted_tversky(
            np.where(scored, mosaic, np.nan), np.where(scored, labels, np.nan), scored,
            alpha=0.2, beta=0.8, radius_m=300.0,
        )
        # near-miss profile of the emitted confidence mass
        from scipy import ndimage
        distance_px = ndimage.distance_transform_edt(~(labels > 0.5))
        mass = mosaic[scored]
        within = mass[distance_px[scored] <= 3.0].sum() / max(mass.sum(), 1e-9)
        near_miss = {
            "confidence_mass_within_300m_fraction": float(within),
            "mean_distance_px_of_emitted_mass": float(
                (mass * distance_px[scored]).sum() / max(mass.sum(), 1e-9)
            ),
        }
        results["arms"][arm] = {
            "channels": len(names),
            "channel_names": names[:6] + (["..."] if len(names) > 6 else []),
            "pooled_oof_dti": components.score,
            "tp_weight": components.tp_weight,
            "fp_weight": components.fp_weight,
            "fn_weight": components.fn_weight,
            "near_miss": near_miss,
            "folds": fold_rows,
        }
        oof_path = args.oof_dir / f"{arm.replace('+', '_')}-oof.npy"
        oof_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(oof_path, mosaic)
        oof_paths[arm] = oof_path
        print(f"arm {arm}: pooled OOF DTI {components.score:.6f} "
              f"(mass within 300 m {within:.4f})", flush=True)

    if "base" in results["arms"]:
        baseline = results["arms"]["base"]["pooled_oof_dti"]
        for arm, row in results["arms"].items():
            row["delta_dti_vs_base"] = row["pooled_oof_dti"] - baseline
            row["relative_delta"] = (row["pooled_oof_dti"] - baseline) / max(baseline, 1e-9)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
