#!/usr/bin/env python3
"""Spatially blocked holdout on an *off-catalogue* fault inventory (the novelty frame).

The catalogue frame used everywhere else in this repository answers "can we re-predict
faults the organizers already handed us".  Under the organizer's masking rule those pixels
are not scored at all, so that frame cannot rank hypotheses about *new* faults.  This
script builds the second frame the project needs.

* Truth = USGS State Geologic Map Compilation (SGMC) fault linework inside the footprint,
  split into connected components; a random subset of components is hidden.
* Domain = the footprint minus the public catalogue dilated by ``--buffer-px``, i.e. the
  same way the organizers exclude known faults.  Catalogue pixels can earn nothing and
  cost nothing.
* Emitters are compared on the identical hidden truth, paired across repeats.

The question it answers is *not* "is the SGMC right" (that is tested separately in
``scripts/sgmc_falsification.py``) but **which emitter best anticipates unseen members of an
independent, expert-compiled fault inventory**: an even lattice, the learned model's
probability peaks, the visible part of the inventory itself, or an established dot
artefact.

A pass here is necessary evidence for a novelty hypothesis, never a competition score.
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


def _credit(prediction, truth, mask, radius_m, alpha):
    components = dti_components_masked(
        prediction, truth.astype(np.uint8), mask,
        pixel_size_m=100.0, radius_m=radius_m, alpha=alpha,
    )
    return {
        "dti": float(components["dti"]),
        "tp_weight": float(components["tp_weight"]),
        "fp_weight": float(components["fp_weight"]),
        "truth_pixels": float(components["truth_pixels"]),
        "emitted_pixels": int(((prediction > 0) & mask).sum()),
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
    parser.add_argument("--output", type=Path, default=ROOT / "docs/research/novelty-holdout.json")
    parser.add_argument("--holdout-fraction", type=float, default=0.3)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--buffer-px", type=int, default=3)
    parser.add_argument("--spacing-px", type=float, default=3.0)
    parser.add_argument("--inventory-spacing-px", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--extra-emitter", action="append", default=[], metavar="NAME=PATH",
                        help="score an additional saved .npy emitter (repeatable)")
    args = parser.parse_args()

    import rasterio
    from scipy.ndimage import binary_dilation, label

    with rasterio.open(args.template) as template:
        footprint = np.isfinite(template.read(1))
        grid = {
            "shape_hw": [template.height, template.width],
            "epsg": template.crs.to_epsg() if template.crs else None,
            "transform_gdal": [float(v) for v in template.transform.to_gdal()],
        }
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & footprint
    blocked = binary_dilation(catalogue, iterations=args.buffer_px)
    domain = footprint & ~blocked

    with rasterio.open(args.external_dir / "derived_sgmc_faults_100m_u8.tif") as dataset:
        inventory = (dataset.read(1) > 0) & footprint
    components, component_count = label(inventory, structure=np.ones((3, 3), dtype=np.uint8))
    component_ids = np.nonzero(np.bincount(components.ravel()))[0]
    component_ids = component_ids[component_ids != 0]

    model = None
    if args.model_oof.is_file():
        mosaic = np.load(args.model_oof)
        model = np.where(footprint, np.nan_to_num(np.asarray(mosaic, dtype=np.float32), nan=0.0), 0.0)
        model = np.clip(model, 0.0, 1.0)
    artefact = None
    if args.artefact.is_file():
        with rasterio.open(args.artefact) as dataset:
            plane = np.nan_to_num(dataset.read(1), nan=0.0)
        artefact = np.where(footprint & (plane > 0), 1.0, 0.0).astype(np.float32)

    lattice = np.zeros(footprint.shape, dtype=np.float32)
    spacing = max(1, int(round(args.spacing_px)))
    lattice[np.arange(0, footprint.shape[0], spacing)[:, None],
            np.arange(0, footprint.shape[1], spacing)[None, :]] = 1.0
    lattice = np.where(footprint, lattice, 0.0)

    report: dict[str, object] = {
        "script": "scripts/novelty_holdout.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": grid,
        "inventory": {
            "name": "USGS SGMC fault linework, 100 m rasterisation",
            "source": "https://mrdata.usgs.gov/geology/state/ (NV.zip, CA.zip); US public domain",
            "pixels_in_footprint": int(inventory.sum()),
            "connected_components": int(component_count),
            "pixels_off_catalogue": int((inventory & domain).sum()),
            "sha256": None,
        },
        "protocol": {
            "holdout_fraction": args.holdout_fraction,
            "buffer_px": args.buffer_px,
            "model_spacing_px": args.spacing_px,
            "inventory_spacing_px": args.inventory_spacing_px,
            "alpha": args.alpha,
            "radius_m": 300.0,
            "repeats": args.repeats,
            "seed": args.seed,
            "domain_pixels": int(domain.sum()),
        },
        "emitters_available": {"model_oof": model is not None, "artefact": artefact is not None,
                               "inventory": int(inventory.sum()) > 0},
        "repeats_detail": [],
        "summary": {},
    }
    started = time.time()
    pooled: dict[str, list[float]] = {}
    for repeat in range(args.repeats):
        rng = np.random.default_rng(args.seed * 31 + repeat)
        shuffled = rng.permutation(component_ids)
        held = shuffled[: int(round(args.holdout_fraction * shuffled.size))]
        holdout_mask = np.isin(components, held)
        visible_mask = inventory & ~holdout_mask
        truth = holdout_mask & domain
        if not truth.any():
            continue

        visible_dots = poisson_disk_select(visible_mask.astype(np.float32),
                                           float(args.inventory_spacing_px), threshold=None)
        emitters: dict[str, np.ndarray] = {
            "lattice": lattice,
            "visible_inventory_dots": np.where(footprint & (visible_dots > 0), 1.0, 0.0).astype(np.float32),
        }
        if model is not None:
            model_dots = poisson_disk_select(np.where(domain, model, 0.0),
                                             float(args.spacing_px), threshold=None)
            emitters["model_probability_dots"] = np.where(
                footprint & (model_dots > 0), 1.0, 0.0).astype(np.float32)
        if artefact is not None:
            emitters["historical_artefact"] = artefact
        for spec in args.extra_emitter:
            name, raw_path = spec.split("=", 1)
            extra_path = Path(raw_path)
            if not extra_path.is_file():
                raise FileNotFoundError(f"extra emitter missing: {extra_path}")
            if extra_path.suffix.lower() in {".tif", ".tiff"}:
                with rasterio.open(extra_path) as dataset:
                    extra_plane = dataset.read(1)
            else:
                extra_plane = np.load(extra_path, allow_pickle=False)
            emitters[name] = np.where(
                footprint & (np.nan_to_num(extra_plane, nan=0.0) > 0), 1.0, 0.0).astype(np.float32)

        entry: dict[str, object] = {
            "repeat": repeat,
            "hidden_components": int(held.size),
            "visible_components": int(component_ids.size - held.size),
            "holdout_truth_pixels_in_domain": int(truth.sum()),
            "emitters": {},
        }
        for name, emitter in emitters.items():
            entry["emitters"][name] = _credit(emitter, truth, domain, 300.0, args.alpha)
            pooled.setdefault(name, []).append(entry["emitters"][name]["dti"])
        report["repeats_detail"].append(entry)
        print(f"repeat {repeat}: " + "  ".join(
            f"{name}={entry['emitters'][name]['dti']:.5f}" for name in emitters), flush=True)

    for name, values in sorted(pooled.items()):
        report["summary"][name] = {
            "mean_dti": float(np.mean(values)),
            "min_dti": float(np.min(values)),
            "max_dti": float(np.max(values)),
            "repeats": len(values),
        }
    first = report["repeats_detail"][0]["emitters"] if report["repeats_detail"] else {}
    if "model_probability_dots" in first and "lattice" in first:
        report["decision"] = {
            "model_minus_lattice_mean_dti": float(
                np.mean(pooled["model_probability_dots"]) - np.mean(pooled["lattice"])),
            "criterion": "on this off-catalogue inventory, does the learned field beat an "
                         "unlearned lattice at comparable spacing?",
        }
    report["notes"] = [
        "The inventory is an independent expert compilation, so it is a legitimate held-out "
        "target for novelty hypotheses; it is not the competition truth.",
        "Emitters are not all matched on emitted count; compare DTI together with emitted_pixels.",
        "The historical artefact is included purely as a calibration reference.",
    ]
    report["elapsed_seconds"] = round(time.time() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} in {report['elapsed_seconds']}s")
    for name, entry in sorted(report["summary"].items()):
        print(f"  {name:26s} mean DTI {entry['mean_dti']:.5f} "
              f"({entry['min_dti']:.5f}..{entry['max_dti']:.5f}, n={entry['repeats']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
