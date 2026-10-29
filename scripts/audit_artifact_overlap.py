#!/usr/bin/env python3
"""Measure every local GEMS TIFF against the pinned lattice and each other.

Uses the shared ``gemsdoe30.novelty`` functions (no private evaluator). Dots are
positive in-footprint cells; the footprint is the finite cells of the organizer
template (``data/raw/sample_submission.tif``, restored by
``scripts/restore_public_mirrors.py --ids sample_submission``).

Outputs a JSON receipt. Exit 0 = audit completed (it does NOT approve anything);
exit 1 = a required input is missing or unreadable.

    .venv/bin/python scripts/audit_artifact_overlap.py \
        --candidate docs/downloads/GEMSDOE30-concealed-geothermal-unique-20261029.tif \
        --out docs/research/2026-10-29-repo-review/overlap-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.novelty import compare  # noqa: E402

TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LATTICE = ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif"
DOWNLOADS = ROOT / "docs/downloads"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_grid(path: Path):
    import rasterio

    with rasterio.open(path) as src:
        return src.read(1).astype(np.float64), src.crs.to_string(), src.shape, src.transform


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.candidate = args.candidate.resolve()
    args.out = args.out.resolve()

    for required in (TEMPLATE, LATTICE, args.candidate):
        if not required.exists():
            print(f"missing required input: {required}", file=sys.stderr)
            return 1

    tmpl, tcrs, tshape, ttf = read_grid(TEMPLATE)
    footprint = np.isfinite(tmpl)

    def on_grid(path: Path):
        arr, crs, shape, tf = read_grid(path)
        same = crs == tcrs and shape == tshape and tf == ttf
        values = np.where(footprint, np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0), 0.0)
        return values, same, {"crs": crs, "shape": list(shape), "grid_matches_template": same}

    lattice, _, lattice_meta = on_grid(LATTICE)
    cand, cand_same, cand_meta = on_grid(args.candidate)
    cand_dots = int(np.count_nonzero(footprint & (cand > 0)))
    cmp_lattice = compare(cand, lattice, footprint, stage="dots")

    rows = []
    candidate_sha = sha256(args.candidate)
    for path in sorted(DOWNLOADS.glob("*.tif")):
        if sha256(path) == candidate_sha:
            rows.append({"file": path.name, "skipped": True, "reason": "same bytes as candidate (self)"})
            continue
        other, same, meta = on_grid(path)
        if not same:
            rows.append({"file": path.name, "grid_matches_template": False, "skipped": True})
            continue
        if not np.any(footprint & (other > 0)):
            rows.append({"file": path.name, "skipped": True, "reason": "no in-footprint positive dots"})
            continue
        c = compare(cand, other, footprint, stage="dots")
        rows.append({
            "file": path.name,
            "sha256": sha256(path),
            "candidate_fraction_within_3px": c["candidate_fraction_within_3px_of_reference"],
            "spearman": c["spearman_full_footprint"],
            "reference_dots": c["reference_dots"],
            "dot_duplicate": c["dot_duplicate"],
            "correlation_duplicate": c["correlation_duplicate"],
        })

    scored = [r for r in rows if not r.get("skipped")]
    worst = max(scored, key=lambda r: r["candidate_fraction_within_3px"] or 0.0) if scored else None
    receipt = {
        "schema_version": 1,
        "candidate": {
            "path": str(args.candidate.relative_to(ROOT)),
            "sha256": sha256(args.candidate),
            "dots_positive_in_footprint": cand_dots,
            "values_unique_in_footprint": sorted(float(v) for v in np.unique(cand[footprint])[:10]),
            **cand_meta,
        },
        "template": {"path": str(TEMPLATE.relative_to(ROOT)), "sha256": sha256(TEMPLATE), "crs": tcrs, "shape": list(tshape)},
        "lattice": {"path": str(LATTICE.relative_to(ROOT)), "sha256": sha256(LATTICE), **lattice_meta},
        "vs_lattice": cmp_lattice,
        "vs_local_downloads": {
            "count_compared": len(scored),
            "max_fraction_within_3px": worst["candidate_fraction_within_3px"] if worst else None,
            "max_file": worst["file"] if worst else None,
            "rows": rows,
        },
        "decision_rule": "dot_duplicate if >0.70 of candidate dots lie within 3 px; correlation_duplicate if |Spearman|>0.90",
        "scope": "Audit receipt only. Not a holdout score, not a leaderboard estimate, not a submission approval.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"candidate dots={cand_dots} vs_lattice={cmp_lattice['candidate_fraction_within_3px_of_reference']:.6f} "
          f"max_local={receipt['vs_local_downloads']['max_fraction_within_3px']} "
          f"({receipt['vs_local_downloads']['max_file']}) compared={len(scored)} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
