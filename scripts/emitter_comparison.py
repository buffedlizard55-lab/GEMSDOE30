#!/usr/bin/env python3
"""Head-to-head emitter comparison on the official metric, under several truth regimes.

The question this answers is *not* "which model is better" but **"which way of placing
mass earns the most under the organizer's rule"**, because `FP_w` is distance weighted and
therefore punishes a smooth probability field for every pixel it touches.

Emitters compared (all binary, value 1.0, identical grid):

* ``lattice_<n>px``      blind even spacing, no learning at all — the control that any
                         learned result has to beat;
* ``model_poisson_<n>``  Poisson-disk thinning of the stitched out-of-fold probability
                         field at the same spacing;
* ``model_threshold_<t>`` model field binarised at a probability threshold;
* ``inventory_<n>``      the USGS SGMC linework off-catalogue, dotted;
* ``artefact``           the historical 44,090-dot submission raster, for calibration.

Truth regimes:

* ``full_catalogue``    the dense catalogue; diagnostic only;
* ``thin25``            a random 25 % of catalogue pixels, with the removed pixels excluded
                        from scoring exactly as the organizer masks known faults;
* ``clusters``          truth confined to a few 3 km discs, with everything else masked.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import dti_components_masked, poisson_disk_select  # noqa: E402


def _lattice(shape, spacing, footprint):
    grid = np.zeros(shape, dtype=np.float32)
    grid[np.arange(0, shape[0], spacing)[:, None], np.arange(0, shape[1], spacing)[None, :]] = 1.0
    return np.where(footprint, grid, 0.0)


def _score(prediction, truth, scored, radius_m, alpha):
    components = dti_components_masked(
        prediction, truth.astype(np.uint8), scored,
        pixel_size_m=100.0, radius_m=radius_m, alpha=alpha,
    )
    return {
        "dti": float(components["dti"]),
        "tp_weight": float(components["tp_weight"]),
        "fp_weight": float(components["fp_weight"]),
        "truth_pixels": float(components["truth_pixels"]),
        "emitted_pixels": int(((prediction > 0) & scored).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--external-dir", type=Path, default=ROOT / "data/external")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--model-oof", type=Path, default=ROOT / "runs/oof/combined-oof.npy")
    parser.add_argument("--artefact", type=Path,
                        default=ROOT / "docs/downloads/"
                                "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/research/emitter-comparison.json")
    parser.add_argument("--spacings", type=int, nargs="+", default=(2, 3, 4, 5))
    parser.add_argument("--thresholds", type=float, nargs="+", default=(0.2, 0.4, 0.6))
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--cluster-radius-km", type=float, default=3.0)
    parser.add_argument("--extra-emitter", action="append", default=[], metavar="NAME=PATH",
                        help="score an additional saved .npy/.tif emitter (repeatable)")
    args = parser.parse_args()

    import rasterio
    from scipy.ndimage import binary_dilation

    with rasterio.open(args.template) as template:
        footprint = np.isfinite(template.read(1))
        grid = {
            "shape_hw": [template.height, template.width],
            "epsg": template.crs.to_epsg() if template.crs else None,
            "transform_gdal": [float(v) for v in template.transform.to_gdal()],
        }
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & footprint
    blocked = binary_dilation(catalogue, iterations=3)

    model = np.where(footprint, np.nan_to_num(np.load(args.model_oof), nan=0.0), 0.0).astype(np.float32)
    model = np.clip(model, 0.0, 1.0)

    emitters: dict[str, np.ndarray] = {}
    for spacing in args.spacings:
        emitters[f"lattice_{spacing}px"] = _lattice(footprint.shape, spacing, footprint)
    for spacing in args.spacings:
        selected = poisson_disk_select(model, float(spacing), threshold=None)
        emitters[f"model_poisson_{spacing}px"] = np.where(
            footprint & (selected > 0), 1.0, 0.0).astype(np.float32)
    for threshold in args.thresholds:
        for spacing in args.spacings:
            selected = poisson_disk_select(model, float(spacing), threshold=float(threshold))
            emitters[f"model_t{threshold:g}_s{spacing}px"] = np.where(
                footprint & (selected > 0), 1.0, 0.0).astype(np.float32)
    for threshold in args.thresholds:
        emitters[f"model_threshold_{threshold:g}"] = np.where(
            footprint & (model >= threshold), 1.0, 0.0).astype(np.float32)
    inventory_path = args.external_dir / "derived_sgmc_faults_100m_u8.tif"
    inventory = None
    if inventory_path.is_file():
        with rasterio.open(inventory_path) as dataset:
            inventory = (dataset.read(1) > 0) & footprint & ~blocked
        for spacing in args.spacings:
            selected = poisson_disk_select(inventory.astype(np.float32), float(spacing),
                                           threshold=None)
            emitters[f"inventory_{spacing}px"] = np.where(
                footprint & (selected > 0), 1.0, 0.0).astype(np.float32)
    if args.artefact.is_file():
        with rasterio.open(args.artefact) as dataset:
            plane = np.nan_to_num(dataset.read(1), nan=0.0)
        emitters["artefact"] = np.where(footprint & (plane > 0), 1.0, 0.0).astype(np.float32)

    for spec in args.extra_emitter:
        if "=" not in spec:
            raise ValueError(f"--extra-emitter expects NAME=PATH, got {spec!r}")
        name, raw_path = spec.split("=", 1)
        extra_path = Path(raw_path)
        if not extra_path.is_file():
            raise FileNotFoundError(f"extra emitter missing: {extra_path}")
        if extra_path.suffix.lower() in {".tif", ".tiff"}:
            with rasterio.open(extra_path) as dataset:
                extra_plane = dataset.read(1)
        else:
            extra_plane = np.load(extra_path)
        emitters[name] = np.where(
            footprint & (np.nan_to_num(extra_plane, nan=0.0) > 0), 1.0, 0.0).astype(np.float32)

    # ---- truth regimes ------------------------------------------------------------
    rng = np.random.default_rng(args.seed)
    truth_rows, truth_cols = np.nonzero(catalogue)
    keep = rng.random(truth_rows.size) < 0.25
    thin = np.zeros(footprint.shape, dtype=bool)
    thin[truth_rows[keep], truth_cols[keep]] = True
    removed = catalogue & ~thin

    cluster = np.zeros(footprint.shape, dtype=bool)
    radius_px = args.cluster_radius_km * 10.0
    height, width = footprint.shape
    attempts = 0
    while cluster.sum() < 0.25 * catalogue.sum() and attempts < 400:
        attempts += 1
        centre_row = int(rng.integers(0, height))
        centre_col = int(rng.integers(0, width))
        row0, row1 = max(0, int(centre_row - radius_px)), min(height, int(centre_row + radius_px) + 1)
        col0, col1 = max(0, int(centre_col - radius_px)), min(width, int(centre_col + radius_px) + 1)
        rows = np.arange(row0, row1)[:, None]
        cols = np.arange(col0, col1)[None, :]
        disc = (rows - centre_row) ** 2 + (cols - centre_col) ** 2 <= radius_px**2
        cluster[row0:row1, col0:col1] |= disc & catalogue[row0:row1, col0:col1]

    regimes = {
        "full_catalogue": (catalogue, footprint),
        "thin25": (thin, footprint & ~removed),
        "clusters": (cluster, footprint & ~(catalogue & ~cluster)),
    }

    report: dict[str, object] = {
        "script": "scripts/emitter_comparison.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": grid,
        "metric": {"radius_m": 300.0, "alpha": 0.2, "pixel_size_m": 100.0},
        "regimes": {name: {"truth_pixels": int(t.sum()), "scored_pixels": int(s.sum())}
                    for name, (t, s) in regimes.items()},
        "emitters": {},
        "table": {},
    }
    started = time.time()
    for name, emitter in emitters.items():
        entry: dict[str, object] = {"total_pixels": int((emitter > 0).sum())}
        for regime, (truth, scored) in regimes.items():
            entry[regime] = _score(emitter, truth, scored, 300.0, 0.2)
        report["emitters"][name] = entry
        report["table"][name] = {regime: entry[regime]["dti"] for regime in regimes}
        print(f"{name:24s} " + "  ".join(
            f"{regime}={entry[regime]['dti']:.5f}" for regime in regimes), flush=True)
    report["elapsed_seconds"] = round(time.time() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
