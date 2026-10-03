#!/usr/bin/env python3
"""Compose a metric-aware dot candidate from a model field plus external fault inventories.

Two mass sources, both justified in ``docs/metric-response-surface.md`` and
``docs/hypotheses.md``:

1. **Model peaks.**  The learned probability field is reduced to dots with a Poisson-disk
   spacing derived from the metric's 300 m kernel (spacing ~3 px = 300 m so that adjacent
   kernels overlap and cover every 100 m of a hypothesised trace).
2. **External inventory.**  The USGS SGMC fault linework, restricted to pixels farther than
   ``--catalogue-buffer-px`` from the public catalogue: those are the pixels the organizer
   masks today, so they are the only part of the inventory that can earn credit on a
   *new-fault* truth set.  Optional filters select the subset with independent evidence of
   surface expression (the 1 m lidar scarp bands).

Every emitted dot carries value 1.0.  Under ``DTI = T / (0.2(T+F) + 0.8G)`` scaling a dot
down scales `T` and `F` together and only shrinks the numerator, so a binary emission is
always at least as good as a diluted one for a fixed set of dot locations.

Output is a probability-style ``.npy`` array ready for ``scripts/build_submission.py``.
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

from gemsdoe30.emission import poisson_disk_select  # noqa: E402

SCARP_BANDS = {"step_max": 3, "cross_max": 8, "relief": 9, "coh100": 10, "lapneg_max": 4,
               "downface_max": 6}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--external-dir", type=Path, default=ROOT / "data/external")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--model", type=Path, default=ROOT / "runs/oof/combined-oof.npy",
                        help="2D model probability grid (NaN outside the footprint)")
    parser.add_argument("--base", type=Path, default=None,
                        help="optional binary base raster (.tif/.npy) kept verbatim, e.g. a "
                             "previously validated dot artefact")
    parser.add_argument("--model-spacing-px-keep", action="store_true",
                        help="keep the model field verbatim instead of Poisson-thinning it")
    parser.add_argument("--inventory-min-separation-from-base-px", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--catalogue-buffer-px", type=int, default=3,
                        help="pixels erased around the catalogue before emitting")
    parser.add_argument("--model-spacing-px", type=float, default=3.0)
    parser.add_argument("--inventory-spacing-px", type=float, default=3.0)
    parser.add_argument("--model-threshold", type=float, default=0.35,
                        help="minimum model probability for a dot to be considered")
    parser.add_argument("--inventory", choices=("none", "sgmc"), default="sgmc")
    parser.add_argument("--inventory-scarp-filter", default=None,
                        help=f"scarp band name; keep inventory pixels at or above "
                             f"--inventory-scarp-percentile. One of {sorted(SCARP_BANDS)}")
    parser.add_argument("--inventory-scarp-percentile", type=float, default=50.0)
    parser.add_argument("--erode-catalogue-in-inventory", type=int, default=3)
    parser.add_argument("--max-runtime-seconds", type=float, default=None)
    args = parser.parse_args()

    import rasterio
    from scipy.ndimage import binary_dilation

    started = time.time()
    with rasterio.open(args.template) as template:
        footprint = np.isfinite(template.read(1))
        grid = {
            "shape_hw": [template.height, template.width],
            "epsg": template.crs.to_epsg() if template.crs else None,
            "transform_gdal": [float(v) for v in template.transform.to_gdal()],
        }
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & footprint
    blocked = binary_dilation(catalogue, iterations=args.catalogue_buffer_px)
    domain = footprint & ~blocked

    if args.model.is_file():
        raw = np.load(args.model)
    else:
        raise FileNotFoundError(f"model grid missing: {args.model}")
    model = np.where(footprint, np.nan_to_num(raw, nan=0.0), 0.0).astype(np.float32)
    model = np.where(domain & (model >= args.model_threshold), model, 0.0)

    report: dict[str, object] = {
        "script": "scripts/build_candidate_dots.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": grid,
        "domain_pixels": int(domain.sum()),
        "model_threshold": args.model_threshold,
        "model_spacing_px": args.model_spacing_px,
        "inventory": args.inventory,
        "inventory_spacing_px": args.inventory_spacing_px,
    }

    model_dots = np.zeros(footprint.shape, dtype=np.float32)
    if args.model_spacing_px > 0:
        selected = poisson_disk_select(model, args.model_spacing_px, threshold=None)
        model_dots = np.where(selected > 0, 1.0, 0.0).astype(np.float32)
    report["model_dots"] = int(model_dots.sum())

    base_dots = np.zeros(footprint.shape, dtype=np.float32)
    if args.base is not None:
        if not args.base.is_file():
            raise FileNotFoundError(f"base raster missing: {args.base}")
        if args.base.suffix.lower() in {".tif", ".tiff"}:
            with rasterio.open(args.base) as dataset:
                base_plane = dataset.read(1)
        else:
            base_plane = np.load(args.base)
        base_dots = np.where(footprint & (np.nan_to_num(base_plane, nan=0.0) > 0), 1.0, 0.0)
        base_dots = base_dots.astype(np.float32)
    report["base_dots"] = int(base_dots.sum())
    if args.model_spacing_px_keep:
        model_dots = np.where(domain & (model > 0), 1.0, 0.0).astype(np.float32)

    inventory_dots = np.zeros(footprint.shape, dtype=np.float32)
    if args.inventory == "sgmc":
        with rasterio.open(args.external_dir / "derived_sgmc_faults_100m_u8.tif") as dataset:
            inventory = (dataset.read(1) > 0) & footprint
        inventory = inventory & ~binary_dilation(catalogue, iterations=args.erode_catalogue_in_inventory)
        report["inventory_pixels_off_catalogue"] = int(inventory.sum())
        if args.inventory_scarp_filter:
            if args.inventory_scarp_filter not in SCARP_BANDS:
                raise ValueError(f"unknown scarp band {args.inventory_scarp_filter!r}")
            scarp_path = args.external_dir / "lidar_scarp_features_u8.tif"
            if not scarp_path.is_file():
                raise FileNotFoundError(f"scarp layer missing: {scarp_path}")
            with rasterio.open(scarp_path) as dataset:
                band = dataset.read(SCARP_BANDS[args.inventory_scarp_filter]).astype(np.float64)
            valid_band = band[(band > 0) & (band < 255) & footprint]
            if valid_band.size < 1000:
                raise ValueError("scarp band has too few valid pixels to threshold")
            cutoff = float(np.percentile(valid_band, args.inventory_scarp_percentile))
            filtered = inventory & (band >= cutoff)
            report["inventory_scarp_filter"] = {
                "band": args.inventory_scarp_filter,
                "percentile": args.inventory_scarp_percentile,
                "cutoff": cutoff,
                "pixels_kept": int(filtered.sum()),
                "pixels_before": int(inventory.sum()),
            }
            inventory = filtered
        if args.inventory_min_separation_from_base_px > 0 and base_dots.any():
            near_base = binary_dilation(base_dots > 0,
                                        iterations=args.inventory_min_separation_from_base_px)
            inventory = inventory & ~near_base
            report["inventory_after_base_separation"] = int(inventory.sum())
        inventory_float = inventory.astype(np.float32)
        selected = poisson_disk_select(inventory_float, args.inventory_spacing_px, threshold=None)
        inventory_dots = np.where(selected > 0, 1.0, 0.0).astype(np.float32)
        report["inventory_dots"] = int(inventory_dots.sum())

    combined = np.maximum(np.maximum(base_dots, model_dots), inventory_dots)
    combined = np.where(domain, combined, 0.0).astype(np.float32)
    probabilities = np.where(footprint, combined, np.nan).astype(np.float32)
    report["emitted_pixels"] = int(np.nansum(probabilities > 0))
    report["overlap_pixels"] = int(((model_dots > 0) & (inventory_dots > 0)).sum())
    report["disk_filter_note"] = ("inventory dots are also kept by poisson_disk_select; where a base "
                                  "dot already sits within the separation distance the inventory "
                                  "contribution merges into it")
    report["valid_pixels"] = int(footprint.sum())
    report["min_in_footprint"] = float(np.nanmin(probabilities[footprint]))
    report["max_in_footprint"] = float(np.nanmax(probabilities[footprint]))
    report["runtime_seconds"] = round(time.time() - started, 1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, probabilities)
    sidecar = args.output.with_suffix(".run.json")
    sidecar.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
