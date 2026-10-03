#!/usr/bin/env python3
"""Stitch four held-out-quadrant prediction arrays into one OOF mosaic."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    for fold in range(4):
        parser.add_argument(f"--fold{fold}", type=Path, required=True, help=f"NaN-masked fold {fold} .npy from infer_model.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        import numpy as np

        from gemsdoe30.cv import spatial_quadrant_masks

        valid_path = args.data_dir / "valid.npy"
        prepared_manifest_path = args.data_dir / "manifest.json"
        if not valid_path.is_file() or not prepared_manifest_path.is_file():
            raise FileNotFoundError("processed valid.npy/manifest.json is missing; run scripts/prepare_data.py")
        valid = np.load(valid_path, mmap_mode="r").astype(bool, copy=False)
        prepared_manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
        if prepared_manifest.get("shape_hw") != list(valid.shape):
            raise ValueError("prepared manifest shape does not match valid.npy")
        mask_sha256 = hashlib.sha256(np.packbits(valid).tobytes()).hexdigest()
        if prepared_manifest.get("valid_mask_sha256") != mask_sha256:
            raise ValueError("valid.npy does not match the footprint checksum in manifest.json")
        transform_gdal = prepared_manifest.get("transform_gdal")
        if not isinstance(transform_gdal, list) or len(transform_gdal) != 6:
            raise ValueError("prepared manifest is missing the exact source-grid affine transform")
        grid_signature = {
            "shape_hw": list(valid.shape),
            "epsg": prepared_manifest.get("epsg"),
            "transform_gdal": transform_gdal,
            "valid_mask_sha256": mask_sha256,
        }
        mosaic = np.full(valid.shape, np.nan, dtype=np.float32)
        fold_receipts = []
        expected_recipe = None
        for fold in range(4):
            path = getattr(args, f"fold{fold}")
            if not path.is_file():
                raise FileNotFoundError(path)
            sidecar_path = path.with_suffix(".json")
            if not sidecar_path.is_file():
                raise FileNotFoundError(f"missing inference provenance sidecar: {sidecar_path}")
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            if sidecar.get("fold") != fold:
                raise ValueError(f"fold {fold} sidecar identifies fold {sidecar.get('fold')}")
            if sidecar.get("prediction_scope") != "held-out quadrant only; NaN elsewhere":
                raise ValueError(f"fold {fold} input is not marked as a held-out-only prediction array")
            if sidecar.get("grid_signature") != grid_signature:
                raise ValueError(f"fold {fold} prediction grid does not match prepared data")
            recipe = sidecar.get("training_recipe")
            if not isinstance(recipe, dict):
                raise TypeError(f"fold {fold} sidecar has no training recipe")
            if recipe.get("loss_mode") != sidecar.get("checkpoint_loss_mode"):
                raise ValueError(f"fold {fold} sidecar loss mode is inconsistent")
            if expected_recipe is None:
                expected_recipe = recipe
            elif recipe != expected_recipe:
                raise ValueError("fold checkpoint recipes differ; train paired, consistent folds")
            values = np.load(path, mmap_mode="r")
            if values.shape != valid.shape:
                raise ValueError(f"fold {fold} shape {values.shape} != valid grid {valid.shape}")
            _, fold_mask = spatial_quadrant_masks(valid, fold, buffer_m=300.0)
            if not fold_mask.any():
                raise ValueError(f"fold {fold} has no valid pixels")
            if not np.all(np.isfinite(values[fold_mask])):
                raise ValueError(f"fold {fold} has missing/non-finite held-out predictions")
            if np.any((values[fold_mask] < 0.0) | (values[fold_mask] > 1.0)):
                raise ValueError(f"fold {fold} predictions are outside [0, 1]")
            if np.any(np.isfinite(values[valid & ~fold_mask])):
                raise ValueError(f"fold {fold} array contains values outside its held-out quadrant")
            mosaic[fold_mask] = values[fold_mask]
            fold_receipts.append(
                {
                    "fold": fold,
                    "input": str(path),
                    "run_name": sidecar.get("run_name"),
                    "checkpoint_sha256": sidecar.get("checkpoint_sha256"),
                    "finite_heldout_pixels": int(np.isfinite(values[fold_mask]).sum()),
                }
            )

        if not np.all(np.isfinite(mosaic[valid])):
            raise ValueError("OOF mosaic does not cover every valid template pixel")
        if args.output.suffix.lower() != ".npy":
            raise ValueError("OOF mosaic output must end in .npy")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.output, mosaic)
        manifest = {
            "output_file": str(args.output),
            "shape": list(mosaic.shape),
            "valid_pixels": int(valid.sum()),
            "grid_signature": grid_signature,
            "training_recipe": expected_recipe,
            "folds": fold_receipts,
            "scope": "four-fold out-of-fold predictions for known-catalogue spatial proxy",
            "not_a_score": True,
        }
        args.output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
        print(f"OOF STITCH BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
