#!/usr/bin/env python3
"""Run a trained checkpoint over the template grid and write a checked GeoTIFF."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fold", type=int, choices=(0, 1, 2, 3), default=None, help="emit only this held-out quadrant")
    parser.add_argument("--predictions-only", action="store_true", help="save a masked .npy OOF array instead of a submission TIFF")
    parser.add_argument("--tile-size", type=int, default=256)
    parser.add_argument("--halo", type=int, default=32)
    parser.add_argument("--device", default=None)
    parser.add_argument("--note", default=None)
    args = parser.parse_args()

    try:
        import numpy as np
        import rasterio
        import torch

        from gemsdoe30.cv import spatial_quadrant_masks, validate_checkpoint_fold
        from gemsdoe30.model import SmallUNet
        from gemsdoe30.normalization import normalize_feature_block
        from gemsdoe30.submission import valid_template_mask, write_submission_file

        if args.predictions_only != (args.fold is not None):
            raise ValueError("--predictions-only and --fold must be provided together for out-of-fold arrays")
        if args.tile_size < 32 or args.halo < 0:
            raise ValueError("tile-size must be >= 32 and halo non-negative")
        feature_path = args.data_dir / "features_raw.npy"
        valid_path = args.data_dir / "valid.npy"
        prepared_manifest_path = args.data_dir / "manifest.json"
        if not feature_path.is_file() or not valid_path.is_file() or not prepared_manifest_path.is_file():
            raise FileNotFoundError("prepared feature arrays/manifest missing; run scripts/prepare_data.py")
        if not args.checkpoint.is_file() or not args.template.is_file():
            raise FileNotFoundError("checkpoint or template file is missing")
        prepared_manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))

        device_name = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
        device = torch.device(device_name)
        checkpoint = torch.load(args.checkpoint, map_location=device)
        if "fold" not in checkpoint:
            raise ValueError("checkpoint is missing explicit fold provenance; retrain it before inference")
        validate_checkpoint_fold(checkpoint.get("fold"), args.fold)
        dataset_signature = prepared_manifest.get("dataset_signature")
        if not isinstance(dataset_signature, str) or len(dataset_signature) != 64:
            raise ValueError("prepared manifest is missing source-file provenance; rerun scripts/prepare_data.py")
        try:
            int(dataset_signature, 16)
        except ValueError as exc:
            raise ValueError("prepared dataset signature is not a hexadecimal SHA-256") from exc
        if checkpoint.get("dataset_signature") != dataset_signature:
            raise ValueError("checkpoint was trained from a different prepared dataset signature")
        features = np.load(feature_path, mmap_mode="r")
        valid = np.load(valid_path, mmap_mode="r").astype(bool, copy=False)
        if features.ndim != 3 or features.shape[1:] != valid.shape:
            raise ValueError("processed feature grid and valid mask are inconsistent")
        if prepared_manifest.get("shape_hw") != list(valid.shape):
            raise ValueError("prepared manifest shape does not match its valid mask")
        if int(checkpoint["in_channels"]) != features.shape[0]:
            raise ValueError("checkpoint input channel count does not match prepared features")
        feature_stats = checkpoint.get("feature_stats")
        if not isinstance(feature_stats, list) or len(feature_stats) != features.shape[0]:
            raise ValueError("checkpoint is missing per-channel fold-local feature_stats")

        with rasterio.open(args.template) as template:
            if (template.height, template.width) != valid.shape:
                raise ValueError("processed footprint shape does not match the template")
            if template.crs is None or template.crs.to_epsg() != 32611:
                raise ValueError("template is not EPSG:32611")
            if prepared_manifest.get("epsg") != template.crs.to_epsg():
                raise ValueError("template CRS does not match the grid used during data preparation")
            expected_transform = prepared_manifest.get("transform_gdal")
            if not isinstance(expected_transform, list) or len(expected_transform) != 6:
                raise ValueError("prepared manifest is missing the exact source-grid affine transform")
            actual_transform = [float(value) for value in template.transform.to_gdal()]
            if not np.allclose(expected_transform, actual_transform, rtol=0.0, atol=1e-9):
                raise ValueError("template geotransform differs from the grid used during data preparation")
            template_valid = valid_template_mask(template, np)
            if not np.array_equal(template_valid, valid):
                raise ValueError("template footprint differs from the footprint used during data preparation")
            valid_mask_sha256 = hashlib.sha256(np.packbits(template_valid).tobytes()).hexdigest()
            if prepared_manifest.get("valid_mask_sha256") != valid_mask_sha256:
                raise ValueError("prepared manifest footprint checksum is inconsistent")
            grid_signature = {
                "shape_hw": list(valid.shape),
                "epsg": template.crs.to_epsg(),
                "transform_gdal": actual_transform,
                "valid_mask_sha256": valid_mask_sha256,
                "dataset_signature": dataset_signature,
            }

        fold_mask = None
        if args.fold is not None:
            _, fold_mask = spatial_quadrant_masks(valid, args.fold, buffer_m=300.0)

        model = SmallUNet(
            in_channels=int(checkpoint["in_channels"]),
            base_channels=int(checkpoint.get("base_channels", 24)),
        ).to(device)
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        predictions = np.full(valid.shape, np.nan, dtype=np.float32)
        height, width = valid.shape
        tile = int(args.tile_size)
        halo = int(args.halo)

        with torch.no_grad():
            for row in range(0, height, tile):
                core_h = min(tile, height - row)
                for col in range(0, width, tile):
                    core_w = min(tile, width - col)
                    if fold_mask is not None and not fold_mask[row : row + core_h, col : col + core_w].any():
                        continue
                    r0, r1 = max(0, row - halo), min(height, row + core_h + halo)
                    c0, c1 = max(0, col - halo), min(width, col + core_w + halo)
                    x = normalize_feature_block(
                        np.asarray(features[:, r0:r1, c0:c1], dtype=np.float32),
                        feature_stats,
                    )
                    logits = model(torch.from_numpy(x[None, ...]).to(device))
                    prob = torch.sigmoid(logits[0, 0]).cpu().numpy()
                    local_r0, local_c0 = row - r0, col - c0
                    core = prob[local_r0 : local_r0 + core_h, local_c0 : local_c0 + core_w]
                    inside = valid[row : row + core_h, col : col + core_w]
                    if fold_mask is not None:
                        inside = inside & fold_mask[row : row + core_h, col : col + core_w]
                    block = predictions[row : row + core_h, col : col + core_w]
                    block[inside] = core[inside]

        expected_mask = fold_mask if fold_mask is not None else valid
        if not np.all(np.isfinite(predictions[expected_mask])):
            raise ValueError("inference left NaN/Inf predictions inside the requested valid area")
        model_sha = _sha256_file(args.checkpoint)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_name = f"GEMSDOE30_{checkpoint['loss_mode']}_R300m_{timestamp}_{model_sha[:8]}"
        training_recipe = {
            "loss_mode": checkpoint["loss_mode"],
            "boundary_weight": float(checkpoint["boundary_weight"]),
            "seed": int(checkpoint["seed"]),
            "epochs": int(checkpoint["epochs"]),
            "steps_per_epoch": int(checkpoint["steps_per_epoch"]),
            "batch_size": int(checkpoint["batch_size"]),
            "patch_size": int(checkpoint["patch_size"]),
            "learning_rate": float(checkpoint["learning_rate"]),
            "base_channels": int(checkpoint.get("base_channels", 24)),
            "pixel_size_x_m": 100.0,
            "pixel_size_y_m": 100.0,
            "metric_radius_m": float(checkpoint["radius_m"]),
            "metric_alpha": float(checkpoint["alpha"]),
            "metric_beta": float(checkpoint["beta"]),
            "weight_decay": float(checkpoint.get("weight_decay", 1e-4)),
            "optimizer": checkpoint.get("optimizer", "AdamW"),
            "patch_radius_halo_pixels": 3,
        }

        if args.predictions_only:
            output = args.output or Path("runs") / f"{run_name}_fold{args.fold}_oof.npy"
            if output.suffix.lower() != ".npy":
                raise ValueError("--predictions-only output must end in .npy")
            output.parent.mkdir(parents=True, exist_ok=True)
            np.save(output, predictions)
            prediction_sha = _sha256_file(output)
            manifest = {
                "run_name": run_name,
                "checkpoint": str(args.checkpoint),
                "checkpoint_sha256": model_sha,
                "checkpoint_loss_mode": checkpoint["loss_mode"],
                "training_recipe": training_recipe,
                "fold": args.fold,
                "checkpoint_fold": checkpoint["fold"],
                "dataset_signature": dataset_signature,
                "fold_buffer_m": 300.0,
                "output_file": str(output),
                "prediction_sha256": prediction_sha,
                "grid_signature": grid_signature,
                "prediction_scope": "held-out quadrant only; NaN elsewhere",
                "status": "OOF research array; not a submission TIFF",
            }
        else:
            note = args.note or f"{run_name} | spatial holdout status must be checked before submission"
            if len(note) > 200:
                raise ValueError("submission note must be no more than 200 characters")
            output = args.output or Path("outputs") / f"{run_name}.tif"
            manifest = write_submission_file(
                predictions,
                args.template,
                output,
                note=note,
                run_name=run_name,
            )
            manifest["model_sha256"] = model_sha
            manifest["checkpoint_loss_mode"] = checkpoint["loss_mode"]
            manifest["checkpoint_fold"] = checkpoint["fold"]
            manifest["dataset_signature"] = dataset_signature
            manifest["training_recipe"] = training_recipe
            manifest["grid_signature"] = grid_signature
            manifest["submission_gate"] = "format-valid only; spatial holdout promotion is separate"
        sidecar = output.with_suffix(".json")
        sidecar.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, indent=2))
        return 0
    except (ImportError, FileNotFoundError, KeyError, ValueError, RuntimeError) as exc:
        print(f"INFERENCE BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
