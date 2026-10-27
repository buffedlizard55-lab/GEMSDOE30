#!/usr/bin/env python3
"""Build a check_novelty-compatible registry from local depth-1 clones of the nine
priority sites (GEMSDOE24/25/27/28/30/31/32/33/36).

Discovery snapshot only: it inventories every ``.tif`` under each clone's ``docs/``
tree plus this repository's own ``docs/`` tree, classifies each file against the
pinned ``sample_submission.tif`` grid, and records SHA-256 identities. It never
attests complete parallel coverage (private lanes and original continuous surfaces
remain unknown) and it never mutates any frozen historical registry: the output
path must not already exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from gemsdoe30.submission import valid_template_mask  # noqa: E402

SITES = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")
LATTICE_DOT_THRESHOLD = 100_000


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git_head(path: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clones", type=Path, default=ROOT / "data/raw/registry-clones")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exclude-prefix", action="append", default=[],
                        help="repo-relative path prefixes to skip (e.g. the new run folder)")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing registry snapshot: {output}")

    with rasterio.open(args.template) as tpl:
        grid = (tpl.shape, tpl.crs, tpl.transform)
        mask = valid_template_mask(tpl, np)

    sources: list[tuple[str, Path]] = []  # (site, docs_dir)
    clone_heads: dict[str, str | None] = {}
    for site in SITES:
        if site == "GEMSDOE30":
            sources.append((site, ROOT / "docs"))
            clone_heads[site] = git_head(ROOT)
        else:
            clone = args.clones / site
            if not (clone / "docs").is_dir():
                raise SystemExit(f"missing clone docs dir for {site}: {clone}")
            sources.append((site, clone / "docs"))
            clone_heads[site] = git_head(clone)

    rasters, exclusions, calibration = [], [], []
    for site, docs_dir in sources:
        for path in sorted(docs_dir.rglob("*")):
            if path.suffix.lower() not in (".tif", ".tiff") or not path.is_file():
                continue
            rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
            if any(rel.startswith(prefix) for prefix in args.exclude_prefix):
                continue
            row = {"site": site, "path": rel, "sha256": sha256_file(path),
                   "bytes": path.stat().st_size}
            try:
                with rasterio.open(path) as ds:
                    aligned = ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid
                    if not aligned:
                        exclusions.append({**row, "aligned": False,
                                           "excluded_reason": f"count={ds.count} shape={ds.shape} crs={ds.crs} != template grid"})
                        continue
                    values = ds.read(1)
            except Exception as exc:  # unreadable raster: record, never hide
                exclusions.append({**row, "aligned": False,
                                   "excluded_reason": f"rasterio open/read failed: {exc}"})
                continue
            inside = values[mask]
            finite = np.isfinite(inside)
            footprint_complete = bool(finite.all() and (inside[finite] >= 0.0).all() and (inside[finite] <= 1.0).all())
            dots = int(np.count_nonzero(inside[finite] > 0.5)) if finite.any() else 0
            if not footprint_complete:
                exclusions.append({**row, "aligned": True, "footprint_complete": False,
                                   "invalid_in_footprint_cells": int((~finite).sum()),
                                   "excluded_reason": "aligned but non-finite or out-of-[0,1] cells inside footprint; finite-subset audited by check_novelty"})
            elif dots > LATTICE_DOT_THRESHOLD:
                calibration.append({**row, "aligned": True, "footprint_complete": True,
                                    "dots_gt_0p5": dots,
                                    "excluded_reason": f"dense calibration lattice ({dots} dots > {LATTICE_DOT_THRESHOLD}); 3-px overlap statistic is degenerate by construction"})
            else:
                rasters.append({**row, "dots_gt_0p5": dots})

    payload = {
        "schema_version": 1,
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "builder": "scripts/build_registry_from_clones.py",
        "complete": False,
        "coverage": ("Every .tif under docs/ at the pinned clone HEADs below (nine priority sites, "
                     "2026-10-27). Private/unpublished lanes, open-PR heads and original continuous "
                     "surfaces are NOT covered; novelty decisions are therefore observed-subset only."),
        "clone_heads": clone_heads,
        "template": str(args.template.relative_to(ROOT)) if args.template.is_relative_to(ROOT) else str(args.template),
        "template_sha256": sha256_file(args.template),
        "rasters": rasters,
        "exclusions": exclusions,
        "calibration_exclusions": calibration,
        "counts": {"aligned_rasters": len(rasters), "exclusions": len(exclusions),
                   "calibration_exclusions": len(calibration)},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"registry: {len(rasters)} aligned, {len(exclusions)} exclusions, "
          f"{len(calibration)} calibration exclusions -> {output}")
    print(f"registry sha256: {sha256_file(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
