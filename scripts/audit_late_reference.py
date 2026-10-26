#!/usr/bin/env python3
"""Audit a late local reference TIFF against a frozen candidate's saved states.

The stopped TDX-C2 experiment pinned its registry before any later artifact
existed. Whenever a new downloadable GeoTIFF appears in the repository, the
protocol requires it to be compared against that experiment's *saved* surface
and dot states -- without refitting the stopped model or changing any dots.

This script performs exactly that comparison and writes a
``novelty-parallel-<stage>.json`` receipt. It is read-only with respect to the
candidate: it never writes to, re-encodes, or re-emits the stopped raster.

Usage:
    python scripts/audit_late_reference.py \
        --directory docs/research/texture-controls \
        --candidate docs/downloads/<new>.tif \
        --output docs/research/texture-controls/novelty-parallel-dots.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_raster(path: Path):
    import rasterio

    with rasterio.open(path) as ds:
        data = ds.read(1, masked=False)
    return np.asarray(data, dtype=np.float64)


def compare(candidate: np.ndarray, reference: np.ndarray) -> dict:
    """Spearman rho over the shared finite footprint and 3-px dot overlap."""
    from scipy.stats import spearmanr

    finite = np.isfinite(candidate) & np.isfinite(reference)
    rho = None
    if finite.sum() > 1000:
        rho = float(spearmanr(candidate[finite].ravel(), reference[finite].ravel()).statistic)
    candidate_dots = np.isfinite(candidate) & (candidate > 0.5)
    reference_dots = np.isfinite(reference) & (reference > 0.5)
    overlap = None
    if candidate_dots.any() and reference_dots.any():
        distance = distance_transform_edt(~reference_dots, sampling=(100.0, 100.0))
        overlap = float(np.count_nonzero(candidate_dots & (distance <= 300.0))
                        / np.count_nonzero(candidate_dots))
    return {
        "spearman_full_footprint": rho,
        "candidate_fraction_within_3px_of_reference": overlap,
        "identical_inside_footprint": bool(np.array_equal(
            candidate[finite], reference[finite])) if finite.any() else False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="frozen experiment directory holding novelty-*.json")
    parser.add_argument("--candidate", type=Path, required=True,
                        help="late local reference TIFF to audit")
    parser.add_argument("--output", type=Path, required=True,
                        help="receipt path, e.g. novelty-parallel-dots.json")
    parser.add_argument("--stage", default="dots", choices=("surface", "dots"))
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    args = parser.parse_args()

    directory = args.directory
    original = json.loads((directory / f"novelty-{args.stage}.json").read_text())
    candidate_sha = original["candidate_sha256"]
    candidate_path = None
    for path in sorted((ROOT / "docs/downloads").glob("*.tif")):
        if sha256_file(path) == candidate_sha:
            candidate_path = path
            break
    if candidate_path is None:
        print("frozen candidate raster is not available locally; cannot audit bytes",
              file=sys.stderr)
        return 2

    candidate = read_raster(candidate_path)
    reference = read_raster(args.candidate)
    row = compare(candidate, reference)
    row.update({
        "stage": args.stage,
        "reference_path": str(args.candidate.relative_to(ROOT)),
        "reference_sha256": sha256_file(args.candidate),
    })

    receipt = {
        "schema_version": 1,
        "stage": args.stage,
        "candidate": original.get("candidate"),
        "candidate_sha256": candidate_sha,
        "template_sha256": original["template_sha256"],
        "registry_sha256": original["registry_sha256"],
        "registry_complete": False,
        "comparisons": [row],
        "errors": [],
        "decision": "late reference audited against the frozen saved states",
        "submission_approved": False,
        "note": ("Read-only audit of a late local reference against the stopped "
                 "experiment's saved candidate; no refit, no dot change, no new "
                 "public TIFF."),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(row, indent=2))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
