#!/usr/bin/env python3
"""Compare regional-only and combined-loss predictions on buffered spatial folds.

Inputs may be .npy probability grids or one-band GeoTIFFs. This evaluates known
catalogue faults as a proxy only; it is not hidden-test truth or a live score.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _read_grid(path: Path):
    import numpy as np
    if path.suffix.lower() in {".tif", ".tiff"}:
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError("rasterio is required for GeoTIFF inputs") from exc
        with rasterio.open(path) as src:
            if src.count != 1:
                raise ValueError(f"{path} must contain exactly one band")
            return src.read(1, masked=False)
    return np.load(path, mmap_mode="r")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--regional", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("runs/loss-ablation/holdout.json"))
    parser.add_argument("--buffer-m", type=float, default=300.0)
    args = parser.parse_args()

    try:
        import numpy as np

        from gemsdoe30.analysis import near_miss_profile
        from gemsdoe30.cv import compare_spatial_holdout, spatial_quadrant_masks

        labels_path = args.data_dir / "labels.npy"
        valid_path = args.data_dir / "valid.npy"
        label_valid_path = args.data_dir / "label_valid.npy"
        if not all(path.is_file() for path in (labels_path, valid_path, label_valid_path)):
            raise FileNotFoundError("processed labels/valid masks missing; run scripts/prepare_data.py")
        labels = np.load(labels_path, mmap_mode="r")
        footprint = np.load(valid_path, mmap_mode="r").astype(bool, copy=False)
        label_valid = np.load(label_valid_path, mmap_mode="r").astype(bool, copy=False)
        valid = footprint & label_valid
        regional = _read_grid(args.regional)
        combined = _read_grid(args.combined)

        comparison = compare_spatial_holdout(
            labels,
            regional,
            combined,
            valid,
            buffer_m=args.buffer_m,
        )
        profiles = []
        for fold in range(4):
            _, eval_mask = spatial_quadrant_masks(valid, fold, buffer_m=args.buffer_m)
            profiles.append(
                {
                    "fold": fold,
                    "regional": near_miss_profile(regional, labels, eval_mask),
                    "combined": near_miss_profile(combined, labels, eval_mask),
                }
            )
        positive_folds = sum(row["delta_dti"] > 0.0 for row in comparison["folds"])
        comparison["near_miss_profiles"] = profiles
        comparison["decision"] = (
            "screen-positive only; requires a preregistered fresh-seed confirmation and exact-file audit"
            if comparison["pooled_delta_dti"] > 0.0 and positive_folds >= 3
            else "not promoted; no submission slot"
        )
        comparison["positive_fold_count"] = positive_folds
        comparison["data_scope"] = "spatially held-out known-catalogue proxy; private expert labels are unavailable"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(comparison, indent=2))
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"HOLDOUT EVALUATION BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
