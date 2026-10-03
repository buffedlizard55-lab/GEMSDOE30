#!/usr/bin/env python3
"""Compare regional-only and combined-loss OOF predictions on buffered spatial folds.

Inputs must be the .npy mosaics produced by stitch_oof_predictions.py, with their
provenance sidecars intact. The score is a known-catalogue spatial proxy, not a
hidden-test score or proof of newly mapped faults.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


OOF_SCOPE = "four-fold out-of-fold predictions for known-catalogue spatial proxy"
EXPECTED_HOLDOUT_PROTOCOL = {
    "split": "four equal raster quadrants; row-major fold index",
    "training_exclusion_buffer_m": 300.0,
    "metric_radius_m": 300.0,
}
EXPECTED_METRIC_RECIPE = {
    "pixel_size_x_m": 100.0,
    "pixel_size_y_m": 100.0,
    "metric_radius_m": 300.0,
    "metric_alpha": 0.2,
    "metric_beta": 0.8,
    "patch_radius_halo_pixels": 3,
}
REQUIRED_RECIPE_FIELDS = {
    "loss_mode",
    "boundary_weight",
    "seed",
    "epochs",
    "steps_per_epoch",
    "batch_size",
    "patch_size",
    "learning_rate",
    "base_channels",
    "pixel_size_x_m",
    "pixel_size_y_m",
    "metric_radius_m",
    "metric_alpha",
    "metric_beta",
    "weight_decay",
    "optimizer",
    "patch_radius_halo_pixels",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_fold_pixel_counts(footprint: Any) -> list[int]:
    """Count valid template cells in each row-major quadrant."""

    height, width = footprint.shape
    row_mid, col_mid = height // 2, width // 2
    row_slices = (slice(0, row_mid), slice(row_mid, height))
    col_slices = (slice(0, col_mid), slice(col_mid, width))
    return [
        int(footprint[row_slices[fold // 2], col_slices[fold % 2]].sum())
        for fold in range(4)
    ]


def _read_oof(path: Path, footprint: Any, grid_signature: dict[str, Any], expected_loss: str):
    """Read and verify a stitched OOF array before scoring it."""

    import numpy as np

    if path.suffix.lower() != ".npy":
        raise ValueError(f"{path} is not an OOF .npy mosaic; full-fit TIFFs are not holdout predictions")
    if not path.is_file():
        raise FileNotFoundError(path)
    manifest_path = path.with_suffix(".json")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing OOF provenance sidecar: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("schema_version") != 1:
        raise ValueError(f"{manifest_path} has an unsupported or missing schema_version")
    if manifest.get("output_file") != path.name:
        raise ValueError(f"{manifest_path} names a different OOF array")
    if manifest.get("scope") != OOF_SCOPE or manifest.get("not_a_score") is not True:
        raise ValueError(f"{manifest_path} is not marked as a non-score OOF research artifact")
    if manifest.get("holdout_protocol") != EXPECTED_HOLDOUT_PROTOCOL:
        raise ValueError(f"{manifest_path} does not match the frozen four-fold/300 m protocol")
    if manifest.get("grid_signature") != grid_signature:
        raise ValueError(f"{manifest_path} grid signature differs from prepared data")
    if manifest.get("shape") != list(footprint.shape):
        raise ValueError(f"{manifest_path} shape differs from prepared data")
    if manifest.get("valid_pixels") != int(footprint.sum()):
        raise ValueError(f"{manifest_path} footprint pixel count differs from prepared data")

    folds = manifest.get("folds")
    if (
        not isinstance(folds, list)
        or any(not isinstance(row, dict) for row in folds)
        or sorted(row.get("fold") for row in folds) != [0, 1, 2, 3]
    ):
        raise ValueError(f"{manifest_path} must contain exactly one receipt for each held-out fold")
    expected_counts = _expected_fold_pixel_counts(footprint)
    for row in folds:
        fold = int(row["fold"])
        if row.get("checkpoint_fold") != fold:
            raise ValueError(f"{manifest_path} fold {fold} receipt is not bound to a checkpoint for that fold")
        if int(row.get("finite_heldout_pixels", 0)) != expected_counts[fold]:
            raise ValueError(f"{manifest_path} fold {fold} receipt has the wrong held-out pixel count")
        checkpoint_hash = row.get("checkpoint_sha256")
        if not isinstance(checkpoint_hash, str) or len(checkpoint_hash) != 64:
            raise ValueError(f"{manifest_path} fold {fold} is missing a full checkpoint SHA-256")
        try:
            int(checkpoint_hash, 16)
        except ValueError as exc:
            raise ValueError(f"{manifest_path} fold {fold} has a malformed checkpoint SHA-256") from exc

    digest = _sha256_file(path)
    if manifest.get("output_sha256") != digest:
        raise ValueError(f"{path} checksum does not match its OOF manifest")

    recipe = manifest.get("training_recipe")
    if not isinstance(recipe, dict) or not REQUIRED_RECIPE_FIELDS.issubset(recipe):
        raise ValueError(f"{manifest_path} is missing required training-recipe provenance")
    if recipe.get("loss_mode") != expected_loss:
        raise ValueError(f"{manifest_path} does not identify the expected {expected_loss!r} training arm")
    if any(recipe.get(key) != value for key, value in EXPECTED_METRIC_RECIPE.items()):
        raise ValueError(f"{manifest_path} was not trained with the official 100 m / 300 m metric geometry")
    boundary_weight = recipe.get("boundary_weight")
    if expected_loss == "regional" and boundary_weight != 0.0:
        raise ValueError("regional control must have boundary_weight=0")
    if expected_loss == "combined" and (
        not isinstance(boundary_weight, (int, float))
        or not math.isfinite(float(boundary_weight))
        or boundary_weight <= 0.0
    ):
        raise ValueError("combined arm must use a finite positive boundary_weight")

    values = np.load(path, mmap_mode="r", allow_pickle=False)
    if values.shape != footprint.shape:
        raise ValueError(f"{path} shape {values.shape} differs from valid grid {footprint.shape}")
    if not np.all(np.isfinite(values[footprint])):
        raise ValueError(f"{path} has missing/non-finite values inside the template footprint")
    if np.any((values[footprint] < 0.0) | (values[footprint] > 1.0)):
        raise ValueError(f"{path} has values outside [0, 1] inside the template footprint")
    if np.any(~np.isnan(values[~footprint])):
        raise ValueError(f"{path} must contain NaN outside the template footprint")
    return values, manifest


def _metric_recipe_without_loss_fields(recipe: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in recipe.items() if key not in {"loss_mode", "boundary_weight"}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--regional", type=Path, required=True, help="stitched regional-only OOF .npy")
    parser.add_argument("--combined", type=Path, required=True, help="stitched combined-loss OOF .npy")
    parser.add_argument("--output", type=Path, default=Path("runs/loss-ablation/holdout.json"))
    parser.add_argument("--buffer-m", type=float, default=300.0, help="fixed at 300 m to match OOF training")
    args = parser.parse_args()

    try:
        import numpy as np

        from gemsdoe30.analysis import near_miss_profile
        from gemsdoe30.cv import compare_spatial_holdout, spatial_quadrant_masks

        if not math.isclose(args.buffer_m, 300.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("--buffer-m must remain 300 m to match the stitched OOF training protocol")
        labels_path = args.data_dir / "labels.npy"
        valid_path = args.data_dir / "valid.npy"
        label_valid_path = args.data_dir / "label_valid.npy"
        prepared_manifest_path = args.data_dir / "manifest.json"
        if not all(path.is_file() for path in (labels_path, valid_path, label_valid_path, prepared_manifest_path)):
            raise FileNotFoundError("processed labels/valid masks/manifest missing; run scripts/prepare_data.py")
        labels = np.load(labels_path, mmap_mode="r", allow_pickle=False)
        footprint = np.load(valid_path, mmap_mode="r", allow_pickle=False).astype(bool, copy=False)
        label_valid = np.load(label_valid_path, mmap_mode="r", allow_pickle=False).astype(bool, copy=False)
        if labels.ndim != 2 or labels.shape != footprint.shape or label_valid.shape != footprint.shape:
            raise ValueError("processed labels and validity masks have inconsistent shapes")
        prepared_manifest = json.loads(prepared_manifest_path.read_text(encoding="utf-8"))
        if prepared_manifest.get("schema_version") != 3:
            raise ValueError("prepared manifest lacks source-file provenance; rerun scripts/prepare_data.py")
        dataset_signature = prepared_manifest.get("dataset_signature")
        if not isinstance(dataset_signature, str) or len(dataset_signature) != 64:
            raise ValueError("prepared manifest is missing the source-bound dataset signature")
        try:
            int(dataset_signature, 16)
        except ValueError as exc:
            raise ValueError("prepared dataset signature is not a hexadecimal SHA-256") from exc
        if prepared_manifest.get("shape_hw") != list(footprint.shape):
            raise ValueError("prepared manifest shape does not match valid.npy")
        mask_sha256 = hashlib.sha256(np.packbits(footprint).tobytes()).hexdigest()
        if prepared_manifest.get("valid_mask_sha256") != mask_sha256:
            raise ValueError("valid.npy does not match the prepared footprint checksum")
        transform_gdal = prepared_manifest.get("transform_gdal")
        if not isinstance(transform_gdal, list) or len(transform_gdal) != 6:
            raise ValueError("prepared manifest is missing the exact source-grid affine transform")
        grid_signature = {
            "shape_hw": list(footprint.shape),
            "epsg": prepared_manifest.get("epsg"),
            "transform_gdal": transform_gdal,
            "valid_mask_sha256": mask_sha256,
            "dataset_signature": dataset_signature,
        }

        regional, regional_manifest = _read_oof(args.regional, footprint, grid_signature, "regional")
        combined, combined_manifest = _read_oof(args.combined, footprint, grid_signature, "combined")
        if regional_manifest.get("holdout_protocol") != combined_manifest.get("holdout_protocol"):
            raise ValueError("regional and combined arms use different holdout protocols")
        if _metric_recipe_without_loss_fields(regional_manifest["training_recipe"]) != _metric_recipe_without_loss_fields(
            combined_manifest["training_recipe"]
        ):
            raise ValueError("regional and combined arms do not share the same seed and training recipe")

        valid = footprint & label_valid
        if not valid.any():
            raise ValueError("there are no finite labeled pixels inside the prepared footprint")
        comparison = compare_spatial_holdout(
            labels,
            regional,
            combined,
            valid,
            buffer_m=300.0,
        )
        fold_profiles = []
        for fold in range(4):
            _, eval_mask = spatial_quadrant_masks(valid, fold, buffer_m=300.0)
            fold_profiles.append(
                {
                    "fold": fold,
                    "regional": near_miss_profile(regional, labels, eval_mask),
                    "combined": near_miss_profile(combined, labels, eval_mask),
                    "scope": "quadrant-isolated diagnostic; excludes cross-quadrant 300 m interactions",
                }
            )
        comparison["near_miss_profiles"] = {
            "complete_oof_grid": {
                "regional": near_miss_profile(regional, labels, valid),
                "combined": near_miss_profile(combined, labels, valid),
                "scope": "complete stitched OOF grid; cross-quadrant kernel interactions retained",
            },
            "fold_isolated_diagnostics": fold_profiles,
        }
        positive_folds = sum(row["fold_isolated_delta_dti"] > 0.0 for row in comparison["folds"])
        comparison["decision"] = (
            "screen-positive only; exact full-grid OOF delta is positive and at least 3/4 isolated fold diagnostics improve; fresh-seed confirmation and exact-file audit still required"
            if comparison["pooled_delta_dti"] > 0.0 and positive_folds >= 3
            else "not promoted; no submission slot"
        )
        comparison["positive_fold_count"] = positive_folds
        comparison["fold_consistency_scope"] = "quadrant-isolated diagnostic scores; not used as the pooled DTI"
        comparison["data_scope"] = "out-of-fold, spatially held-out known-catalogue proxy; private expert labels are unavailable"
        comparison["training_recipes"] = {
            "regional": regional_manifest["training_recipe"],
            "combined": combined_manifest["training_recipe"],
        }
        comparison["oof_manifest_sha256"] = {
            "regional_array": regional_manifest["output_sha256"],
            "combined_array": combined_manifest["output_sha256"],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(comparison, indent=2))
        return 0
    except (ImportError, FileNotFoundError, RuntimeError, TypeError, ValueError) as exc:
        print(f"HOLDOUT EVALUATION BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
