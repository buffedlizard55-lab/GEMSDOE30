#!/usr/bin/env python3
"""Novelty / duplicate scan of a candidate submission rasters against the local
registry (every TIFF in docs/downloads).  Reports Stage-1 surface correlation and
Stage-2 dot overlap per the LANE rule (rho <= 0.90; <=70% dots within 3 px).

This is a duplicate diagnostic, not a performance certificate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.novelty import compare, decision


def read_tif(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1, masked=False)


def main() -> int:
    candidate = Path(sys.argv[1])
    stage = sys.argv[2] if len(sys.argv) > 2 else "dots"
    assert stage in ("surface", "dots")

    reg = list(Path("docs/downloads").glob("*.tif"))
    cand = read_tif(candidate)
    with rasterio.open(candidate) as ds:
        template = ds.read(1, masked=False)
    valid = np.isfinite(template)

    rows = []
    for ref in sorted(reg):
        if ref.resolve() == candidate.resolve():
            continue
        try:
            rows.append(compare(cand, read_tif(ref), valid, stage=stage))
        except Exception as exc:  # noqa: BLE001 - keep scanning on grid mismatch
            rows.append({"reference": ref.name, "error": str(exc),
                         "spearman_full_footprint": None,
                         "candidate_fraction_within_3px_of_reference": None,
                         "identical_inside_footprint": False,
                         "correlation_duplicate": False,
                         "dot_duplicate": False,
                         "undefined": True})

    worst_rho = max((r["spearman_full_footprint"] for r in rows
                     if r.get("spearman_full_footprint") is not None),
                    default=None)
    worst_overlap = max((r["candidate_fraction_within_3px_of_reference"] for r in rows
                         if r.get("candidate_fraction_within_3px_of_reference") is not None),
                        default=None)
    n_dup_rho = sum(1 for r in rows if r.get("correlation_duplicate"))
    n_dup_overlap = sum(1 for r in rows if r.get("dot_duplicate"))
    n_identical = sum(1 for r in rows if r.get("identical_inside_footprint"))

    print(f"Candidate: {candidate.name}  stage={stage}  registry={len(rows)} rasters")
    print(f"  max Spearman rho: {worst_rho}")
    print(f"  max dot overlap (<=3 px): {worst_overlap}")
    print(f"  correlation duplicates (rho>0.90): {n_dup_rho}")
    print(f"  dot duplicates (>70% within 3 px): {n_dup_overlap}")
    print(f"  identical inside footprint: {n_identical}")
    print(f"  LANE decision: {decision(rows, stage=stage, registry_complete=False)}")
    print("\nWorst overlaps:")
    ranked = sorted([r for r in rows if r.get("candidate_fraction_within_3px_of_reference") is not None],
                    key=lambda r: r["candidate_fraction_within_3px_of_reference"], reverse=True)
    for r in ranked[:8]:
        print(f"  {r['reference']:70s} rho={r.get('spearman_full_footprint')} "
              f"overlap={r.get('candidate_fraction_within_3px_of_reference')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
