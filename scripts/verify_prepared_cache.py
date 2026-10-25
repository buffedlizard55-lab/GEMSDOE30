#!/usr/bin/env python3
"""Compare every cached feature/label/mask cell with its pinned raw-source window.

This is integrity verification, not a model experiment or organizer authentication.
No large arrays or source data are committed; only the compact receipt is published.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np
import rasterio
from rasterio.windows import Window
from gemsdoe30.submission import valid_template_mask


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(data_dir: Path):
    manifest = json.loads((data_dir / "manifest.json").read_text())
    sources = {name: Path(row["path"]) for name, row in manifest["source_files"].items()}
    for name, path in sources.items():
        if sha(path) != manifest["source_files"][name]["sha256"]:
            raise ValueError(f"raw source hash mismatch: {name}")
    arrays = {name: np.load(data_dir / name, mmap_mode="r") for name in
              ("features_raw.npy", "labels.npy", "valid.npy", "label_valid.npy")}
    with rasterio.open(sources["sample_submission"]) as template, rasterio.open(sources["training_features"]) as features, rasterio.open(sources["labels"]) as labels:
        valid = valid_template_mask(template, np)
        shape = (template.height, template.width)
        if arrays["features_raw.npy"].shape != (features.count, *shape):
            raise ValueError("cached feature shape mismatch")
        if arrays["features_raw.npy"].dtype != np.float32 or arrays["labels.npy"].dtype != np.float32:
            raise ValueError("cached feature/label dtype mismatch")
        if any(arrays[name].shape != shape for name in ("labels.npy", "valid.npy", "label_valid.npy")):
            raise ValueError("cached label/mask shape mismatch")
        if arrays["valid.npy"].dtype != np.bool_ or arrays["label_valid.npy"].dtype != np.bool_:
            raise ValueError("cached masks must be boolean")
        for ds in (features, labels):
            if (ds.shape, ds.crs, ds.transform) != (template.shape, template.crs, template.transform):
                raise ValueError("raw grid mismatch")
        positive_value = 255.0 if 255.0 in manifest["label_values_observed"] else 1.0
        windows = 0
        for r0 in range(0, shape[0], 512):
            for c0 in range(0, shape[1], 512):
                h, w = min(512, shape[0] - r0), min(512, shape[1] - c0)
                sl = np.s_[r0:r0 + h, c0:c0 + w]
                window = Window(c0, r0, w, h)
                footprint = valid[sl]
                raw = features.read(window=window, masked=True, out_dtype="float32").filled(np.nan)
                raw[:, ~footprint] = np.nan
                if not np.array_equal(arrays["features_raw.npy"][:, sl[0], sl[1]], raw, equal_nan=True):
                    raise ValueError(f"cached feature value mismatch at window {r0},{c0}")
                target = labels.read(1, window=window, masked=True, out_dtype="float32").filled(np.nan)
                finite = np.isfinite(target) & footprint
                expected_labels = ((target == positive_value) & finite).astype(np.float32)
                expected = {"labels.npy": expected_labels, "valid.npy": footprint, "label_valid.npy": finite}
                for name, values in expected.items():
                    if not np.array_equal(arrays[name][sl], values):
                        raise ValueError(f"cached {name} value mismatch at window {r0},{c0}")
                windows += 1
    return {"schema_version": 1, "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "dataset_signature": manifest["dataset_signature"], "all_cells_match_raw_sources": True,
            "windows_checked": windows, "comparison": "exact float32/bool equality, NaNs matched only where expected",
            "array_sha256": {name: sha(data_dir / name) for name in arrays},
            "raw_source_sha256": {name: row["sha256"] for name, row in manifest["source_files"].items()},
            "organizer_authenticated": False, "is_performance_measurement": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/texture-displacement/cache-verification.json"))
    args = parser.parse_args()
    result = verify(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Every prepared feature, label and mask cell matches the pinned raw-source derivation")


if __name__ == "__main__":
    main()
