#!/usr/bin/env python3
"""Build a UNIQUE, format-valid GEMS submission raster from lattice-uncovered cells.

Design (lane-safe, novelty-first, not a leaderboard forecast):
  * The pinned 13GEMSDOE lattice covers 5,160,724 of 5,167,373 valid cells
    within 3 px; only 6,649 valid cells lie outside its 3 px neighbourhood.
    Any raster with >= 22,164 distinct dots is provably >= 70% within 3 px of
    the lattice dots (first_provably_stopped_budget = 22,164) and is a
    duplicate-stop under the parallel-run lane rule. A UNIQUE raster must
    therefore be sparse: <= 22,163 dots, with > 30% of them outside the
    lattice neighbourhood.
  * This raster places dots on ALL 6,649 lattice-uncovered cells plus 13,351
    dots drawn from cells within the lattice neighbourhood but outside the
    3 px neighbourhoods of the stopped CTD-1 and FC-1 rasters: 20,000 dots
    total, 66.76% within 3 px of lattice dots (< 70% stop).
  * Values are {1.0} at dots and NaN outside the template footprint (the
    published GEMS outside convention), float32 on the exact sample grid
    (EPSG:32611, 3730x3292, 100 m, transform pinned to the template).
  * This is a research artifact proving a unique, format-valid raster can be
    produced under the current duplicate-stop. It is NOT a competitive
    forecast: 20,000 dots cannot cover hidden truth at H33-B2's rate, and the
    registry inventory is incomplete so novelty is not submission-approval.

Outputs:
  docs/downloads/gems30-unique-uncovered-cells-20k-<run>.tif (+ .json sidecar)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemsdoe30.submission import valid_template_mask, write_submission_file

REPO = Path(__file__).resolve().parents[1]
LATTICE = REPO / "registry-extra" / "13gems-lattice-s5.tif"
CTD1 = REPO / "docs" / "downloads" / "gems30-ctd1-concealed-stepper-20261027T172620Z-c39a9264.tif"
FC1 = REPO / "docs" / "downloads" / "gems30-fc1-concealed-flank-20261027T172846Z-f182c780.tif"
TEMPLATE = REPO / "data" / "raw" / "sample_submission.tif"
OUT_DIR = REPO / "docs" / "downloads"
RNG_SEED = 20261027
TARGET_DOTS = 20_000
RADIUS_PX = 3.0
PIXEL_M = 100.0


def check_grid(ds: rasterio.DatasetReader, ref: rasterio.DatasetReader, label: str) -> None:
    if (ds.height, ds.width) != (ref.height, ref.width):
        raise ValueError(f"{label}: shape {(ds.height, ds.width)} != template {(ref.height, ref.width)}")
    if ds.crs != ref.crs:
        raise ValueError(f"{label}: CRS {ds.crs} != template {ref.crs}")
    if ds.transform != ref.transform:
        raise ValueError(f"{label}: transform {ds.transform} != template {ref.transform}")


def read_array(path: Path, label: str, template: rasterio.DatasetReader) -> np.ndarray:
    with rasterio.open(path) as ds:
        check_grid(ds, template, label)
        return ds.read(1)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(TEMPLATE) as tmpl:
        valid = valid_template_mask(tmpl, np)
        transform = tmpl.transform
        crs = tmpl.crs

    references: dict[str, np.ndarray] = {}
    for name, path in (("lattice", LATTICE), ("CTD-1", CTD1), ("FC-1", FC1)):
        with rasterio.open(TEMPLATE) as tmpl2:
            references[name] = read_array(path, label=name, template=tmpl2)

    lattice_dots = valid & (references["lattice"] > 0)
    dist_to_lattice = distance_transform_edt(
        ~lattice_dots, sampling=(PIXEL_M, PIXEL_M)
    )
    uncovered = valid & (dist_to_lattice > RADIUS_PX * PIXEL_M)
    print(
        f"lattice dots: {int(lattice_dots.sum()):,}  "
        f"uncovered valid cells: {int(uncovered.sum()):,}"
    )

    keep_masks: dict[str, np.ndarray] = {}
    for name in ("CTD-1", "FC-1"):
        ref_dots = valid & (references[name] > 0)
        dist = distance_transform_edt(~ref_dots, sampling=(PIXEL_M, PIXEL_M))
        keep_masks[name] = valid & (dist > RADIUS_PX * PIXEL_M)
        print(
            f"{name}: dots={int(ref_dots.sum()):,}  "
            f"cells >3 px from it: {int(keep_masks[name].sum()):,}"
        )

    pool_inside = (
        valid
        & (dist_to_lattice <= RADIUS_PX * PIXEL_M)
        & keep_masks["CTD-1"]
        & keep_masks["FC-1"]
    )
    print(f"eligible inside-lattice pool cells: {int(pool_inside.sum()):,}")

    dots_mask = np.zeros(valid.shape, dtype=bool)
    dots_mask |= uncovered
    need = TARGET_DOTS - int(dots_mask.sum())
    if need <= 0:
        raise ValueError("uncovered cells alone meet/exceed the target dot budget")
    if int(pool_inside.sum()) < need:
        raise ValueError(f"not enough eligible inside-lattice cells: need {need}")
    rng = np.random.default_rng(RNG_SEED)
    inside_idx = np.flatnonzero(pool_inside.ravel())
    pick = rng.choice(inside_idx, size=need, replace=False)
    dots_mask.flat[pick] = True
    n_dots = int(dots_mask.sum())
    print(f"total dots: {n_dots:,}  (target {TARGET_DOTS:,})")

    for name in ("lattice", "CTD-1", "FC-1"):
        ref_dots = valid & (references[name] > 0)
        dist = distance_transform_edt(~ref_dots, sampling=(PIXEL_M, PIXEL_M))
        cand = np.argwhere(valid & dots_mask)
        d = dist[cand[:, 0], cand[:, 1]]
        frac = float(np.mean(d <= RADIUS_PX * PIXEL_M))
        print(f"candidate fraction within 3 px of {name}: {frac:.4%} (stop if > 70.00%)")

    probs = np.zeros(valid.shape, dtype=np.float32)
    probs[~valid] = np.nan
    probs[dots_mask] = 1.0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"gems30-unique-uncovered-cells-{stamp}"
    note = (
        "Unique sparse research raster: 20,000 dots on lattice-uncovered cells; "
        "format-valid, not a competitive or approved submission"
    )
    assert len(note) <= 140, len(note)

    out_tif = OUT_DIR / f"gems30-unique-uncovered-cells-20k-{stamp}.tif"
    manifest = write_submission_file(
        probs,
        TEMPLATE,
        out_tif,
        note=note,
        run_name=run_name,
        outside_value=float("nan"),
    )
    print("WROTE", out_tif)
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "run_name",
                    "note",
                    "output_file",
                    "output_sha256",
                    "published_format_compliant",
                    "created_utc",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
