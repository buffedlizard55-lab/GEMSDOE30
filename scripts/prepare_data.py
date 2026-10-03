#!/usr/bin/env python3
"""Validate supplied grids and prepare raw, windowed arrays for fold-local training.

Expected default inputs under data/raw/: training_features.tif, labels.tif, and
sample_submission.tif. This script does not authenticate to DrivenData or fetch
competition files. It is intentionally fail-closed on grid and label mismatches.
Feature normalization is fitted later from each training-fold mask, not globally.
"""

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


def _dependencies():
    try:
        import numpy as np
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:
        raise SystemExit("Missing geospatial dependencies. Install with `pip install -e '.[train]'`.") from exc
    return np, rasterio, Window


def _check_aligned(reference, dataset, label: str) -> None:
    if (dataset.height, dataset.width) != (reference.height, reference.width):
        raise ValueError(f"{label} shape {(dataset.height, dataset.width)} != template {(reference.height, reference.width)}")
    if dataset.transform != reference.transform:
        raise ValueError(f"{label} geotransform does not match sample submission")
    if dataset.crs != reference.crs:
        raise ValueError(f"{label} CRS does not match sample submission: {dataset.crs} != {reference.crs}")


def _valid_from_template(template, np):
    data = template.read(1, masked=False)
    valid = np.isfinite(data)
    if template.nodata is not None:
        if np.isnan(template.nodata):
            valid &= ~np.isnan(data)
        else:
            valid &= data != template.nodata
    valid &= template.dataset_mask() != 0
    return valid


def prepare(features_path: Path, labels_path: Path, template_path: Path, output_dir: Path) -> dict:
    np, rasterio, Window = _dependencies()
    for path in (features_path, labels_path, template_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    tile_size = 512

    with rasterio.open(template_path) as template, rasterio.open(features_path) as features, rasterio.open(labels_path) as labels:
        if template.count != 1:
            raise ValueError(f"sample template must have one band; found {template.count}")
        if features.count < 1:
            raise ValueError("training_features must contain at least one band")
        if labels.count != 1:
            raise ValueError(f"labels must contain exactly one band; found {labels.count}")
        _check_aligned(template, features, "training_features")
        _check_aligned(template, labels, "labels")
        epsg = template.crs.to_epsg() if template.crs else None
        if epsg != 32611:
            raise ValueError(f"expected EPSG:32611 template; found {template.crs}")
        transform = template.transform
        if (
            abs(transform.a - 100.0) > 1e-6
            or abs(transform.e + 100.0) > 1e-6
            or abs(transform.b) > 1e-9
            or abs(transform.d) > 1e-9
        ):
            raise ValueError(f"expected a north-up 100 m grid; found transform {transform}")
        height, width, channels = template.height, template.width, features.count
        footprint = _valid_from_template(template, np)
        if not footprint.any():
            raise ValueError("template has no finite valid footprint pixels")

        label_encodings: set[float] = set()
        for row in range(0, height, tile_size):
            h = min(tile_size, height - row)
            for col in range(0, width, tile_size):
                w = min(tile_size, width - col)
                window = Window(col, row, w, h)
                inside = footprint[row : row + h, col : col + w]
                label_block = labels.read(1, window=window, masked=True, out_dtype="float32")
                lb = np.asarray(label_block.filled(np.nan), dtype=np.float32)
                good_label = inside & np.isfinite(lb)
                if good_label.any():
                    label_encodings.update(float(v) for v in np.unique(lb[good_label]))

        if not label_encodings:
            raise ValueError("labels contain no finite values inside the template footprint")
        if not (label_encodings <= {0.0, 1.0} or label_encodings <= {0.0, 255.0}):
            raise ValueError(f"labels are not recognized binary 0/1 or 0/255 values: {sorted(label_encodings)[:20]}")

        features_out = np.lib.format.open_memmap(
            output_dir / "features_raw.npy", mode="w+", dtype=np.float32, shape=(channels, height, width)
        )
        labels_out = np.lib.format.open_memmap(
            output_dir / "labels.npy", mode="w+", dtype=np.float32, shape=(height, width)
        )
        valid_out = np.lib.format.open_memmap(
            output_dir / "valid.npy", mode="w+", dtype=np.bool_, shape=(height, width)
        )
        label_valid_out = np.lib.format.open_memmap(
            output_dir / "label_valid.npy", mode="w+", dtype=np.bool_, shape=(height, width)
        )
        finite_feature_counts = np.zeros(channels, dtype=np.int64)

        for row in range(0, height, tile_size):
            h = min(tile_size, height - row)
            for col in range(0, width, tile_size):
                w = min(tile_size, width - col)
                window = Window(col, row, w, h)
                inside = footprint[row : row + h, col : col + w]
                block = features.read(window=window, masked=True, out_dtype="float32")
                for channel in range(channels):
                    band = np.asarray(block[channel].filled(np.nan), dtype=np.float32)
                    band[~inside] = np.nan
                    finite_feature_counts[channel] += np.count_nonzero(np.isfinite(band))
                    features_out[channel, row : row + h, col : col + w] = band

                label_block = labels.read(1, window=window, masked=True, out_dtype="float32")
                lb = np.asarray(label_block.filled(np.nan), dtype=np.float32)
                finite_label = np.isfinite(lb) & inside
                positive_value = 255.0 if 255.0 in label_encodings else 1.0
                positives = (lb == positive_value) & finite_label
                labels_out[row : row + h, col : col + w] = positives.astype(np.float32)
                valid_out[row : row + h, col : col + w] = inside
                label_valid_out[row : row + h, col : col + w] = finite_label

        for array in (features_out, labels_out, valid_out, label_valid_out):
            array.flush()
        empty_channels = [index + 1 for index, count in enumerate(finite_feature_counts) if count == 0]
        if empty_channels:
            raise ValueError(f"feature channels have no finite values inside the template footprint: {empty_channels}")

        transform_gdal = [float(value) for value in transform.to_gdal()]
        valid_mask_sha256 = hashlib.sha256(np.packbits(footprint).tobytes()).hexdigest()
        feature_band_names = [
            description or f"band_{index + 1}"
            for index, description in enumerate(features.descriptions)
        ]
        source_files = {
            "training_features": {"path": str(features_path), "sha256": _sha256_file(features_path)},
            "labels": {"path": str(labels_path), "sha256": _sha256_file(labels_path)},
            "sample_submission": {"path": str(template_path), "sha256": _sha256_file(template_path)},
        }
        signature_payload = {
            "source_file_sha256": {name: row["sha256"] for name, row in source_files.items()},
            "shape_hw": [height, width],
            "feature_channels": channels,
            "feature_band_names": feature_band_names,
            "epsg": epsg,
            "transform_gdal": transform_gdal,
            "valid_mask_sha256": valid_mask_sha256,
            "label_values_observed": sorted(label_encodings),
        }
        dataset_signature = hashlib.sha256(
            json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        manifest = {
            "schema_version": 3,
            "prepared_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "features_path": str(features_path),
            "labels_path": str(labels_path),
            "template_path": str(template_path),
            "source_files": source_files,
            "dataset_signature": dataset_signature,
            "feature_array": "features_raw.npy",
            "shape_hw": [height, width],
            "feature_channels": channels,
            "feature_band_names": feature_band_names,
            "feature_dtypes": list(features.dtypes),
            "finite_feature_pixels_by_channel": [int(count) for count in finite_feature_counts],
            "epsg": epsg,
            "transform_gdal": transform_gdal,
            "pixel_size_m": [abs(transform.a), abs(transform.e)],
            "template_valid_pixels": int(footprint.sum()),
            "valid_mask_sha256": valid_mask_sha256,
            "label_valid_pixels": int(label_valid_out.sum()),
            "positive_label_pixels": int(labels_out.sum()),
            "label_values_observed": sorted(label_encodings),
            "normalization": {
                "fit_scope": "training-fold pixels only; fitted separately for each checkpoint",
                "method": "deterministic spatially balanced robust median/IQR samples; clip scaled values to [-8, 8]",
                "missing_value_after_scaling": 0.0,
                "heldout_pixels_used_for_fit": False,
            },
        }
        (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=Path("data/raw/training_features.tif"))
    parser.add_argument("--labels", type=Path, default=Path("data/raw/labels.tif"))
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    try:
        manifest = prepare(args.features, args.labels, args.template, args.output_dir)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"DATA PREPARATION BLOCKED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
