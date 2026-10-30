"""Exact nine-site family audit (2026-10-30 repo review).

Measures, on the restored pinned historical bytes, how the nine requested
GEMSDOE leaders relate to each other: exact in-footprint equality, exact
dot-set containment, and the decomposition of GEMSDOE32 (H33-B2, 0.2778
owner-reported) against GEMSDOE25 (D2.8, 0.2600 owner-reported).

Inputs must be restored first (see README "Reproduce"):
    python scripts/restore_public_mirrors.py --ids sample_submission labels
    python scripts/audit_priority_readiness.py --restore-only
Writes a receipt only. Owner-reported scores are carried as labels, never as
HOLDOUT-DTI or ORGANIZER-CONFIRMED values.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "data/raw/priority-readiness"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LABELS = ROOT / "data/raw/labels.tif"
OUT = ROOT / "docs/research/2026-10-30-repo-review/nine-site-family.json"
SITES = ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1)


def run() -> dict:
    if not TEMPLATE.exists() or not LABELS.exists():
        raise SystemExit("restore data/raw/sample_submission.tif and labels.tif first")
    template = read(TEMPLATE)
    footprint = np.isfinite(template)
    labels = read(LABELS)
    known = labels == 1
    files = {}
    hashes = {}
    for site in SITES:
        matches = sorted(HIST.glob(f"{site}-*.tif"))
        if len(matches) != 1:
            raise SystemExit(f"expected exactly one restored raster for {site}; found {len(matches)}")
        path = matches[0]
        hashes[site] = {"file": path.name, "sha256": sha256(path)}
        raw = read(path)
        files[site] = np.where(footprint, raw, 0).astype(np.float32)
        hashes[site]["outside_footprint_finite_cells"] = int(np.isfinite(raw[~footprint]).sum())
        hashes[site]["outside_footprint_nonzero_cells"] = int(np.count_nonzero(np.nan_to_num(raw[~footprint])))
        hashes[site]["dots_in_footprint"] = int(np.count_nonzero(files[site] > 0))

    pairs = []
    for a, b in itertools.combinations(SITES, 2):
        same = bool(np.array_equal(files[a], files[b]))
        pa, pb = files[a] > 0, files[b] > 0
        inter = int(np.count_nonzero(pa & pb))
        na, nb = int(pa.sum()), int(pb.sum())
        if same or inter == min(na, nb):
            pairs.append({
                "a": a, "b": b, "identical_inside_footprint": same,
                "shared_dots": inter, "dots_a": na, "dots_b": nb,
                "smaller_set_contained_in_other": inter == min(na, nb),
            })

    shares = {}
    for site in SITES:
        own = files[site] > 0
        n_own = int(own.sum())
        vals = [(100.0 * int(np.count_nonzero(own & (files[other] > 0))) / n_own, other)
                for other in SITES if other != site]
        lo, hi = min(vals), max(vals)
        shares[site] = {
            "min_percent_of_own_dots_found_in_other_site": round(lo[0], 2),
            "min_site": lo[1],
            "max_percent_of_own_dots_found_in_other_site": round(hi[0], 2),
            "max_site": hi[1],
        }

    h32 = files["GEMSDOE32"] > 0
    h25 = files["GEMSDOE25"] > 0
    removed = h25 & ~h32 & footprint
    added = h32 & ~h25 & footprint
    dist = distance_transform_edt(~known)
    decomposition = {
        "comparison": "GEMSDOE25 (D2.8, owner-reported 0.2600) minus GEMSDOE32 (H33-B2, owner-reported 0.2778)",
        "dots_in_25_not_in_32": int(removed.sum()),
        "dots_in_32_not_in_25": int(added.sum()),
        "removed_dots_max_distance_to_labelled_fault_px": float(dist[removed].max()) if removed.any() else None,
        "removed_dots_share_within_2px_of_labelled_fault": float((dist[removed] <= 2.0).mean()) if removed.any() else None,
        "removed_dots_share_within_3px_of_labelled_fault": float((dist[removed] <= 3.0).mean()) if removed.any() else None,
        "note": "Euclidean pixel distance from the restored labels.tif label==1 cells (the mirror of the catalogue). Describes the raster pair; does not establish why the owner-reported scores differ.",
    }
    return {
        "schema_version": 1,
        "purpose": "Measured family relations among the nine requested historical GEMSDOE leaders (2026-10-30). Structural facts only; no score is estimated.",
        "inputs": {
            "template": {"path": "data/raw/sample_submission.tif", "sha256": sha256(TEMPLATE), "footprint_cells": int(footprint.sum())},
            "labels": {"path": "data/raw/labels.tif", "sha256": sha256(LABELS), "label_one_cells": int(known.sum())},
            "provenance": "owner-supplied SHA-pinned mirrors; NOT organizer-authenticated",
        },
        "rasters": hashes,
        "pairs_with_identity_or_containment": pairs,
        "own_dot_sharing_by_site": shares,
        "identical_pairs": [[p["a"], p["b"]] for p in pairs if p["identical_inside_footprint"]],
        "h33b2_vs_d28": decomposition,
        "scores": "owner-reported only; not HOLDOUT-DTI and not ORGANIZER-CONFIRMED",
        "ok_to_submit": False,
        "slot_selected": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    receipt = run()
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    print(json.dumps(receipt["h33b2_vs_d28"], indent=2))
    print("identical pairs:", receipt["identical_pairs"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
