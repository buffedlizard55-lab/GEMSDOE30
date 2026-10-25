#!/usr/bin/env python3
"""Dot-stage duplicate check of one candidate against every TIF in docs/downloads.

Complements check_novelty.py (pinned 9-site registry). Uses the same shared comparison
(gemsdoe30.novelty.compare). Writes a JSON receipt. Exit 0 only if no comparison is a
duplicate under the published thresholds (Spearman > 0.90 or > 70% dots within 3 px).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe30.novelty import compare  # noqa: E402
from gemsdoe30.submission import valid_template_mask  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    p.add_argument("--downloads", type=Path, default=ROOT / "docs/downloads")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.candidate = args.candidate.resolve()
    args.output = args.output.resolve()
    with rasterio.open(args.template) as ds:
        footprint = valid_template_mask(ds, np)
    with rasterio.open(args.candidate) as ds:
        cand = ds.read(1)
    rows, errors = [], []
    for ref in sorted(args.downloads.glob("*.tif")):
        if ref.resolve() == args.candidate.resolve():
            continue
        try:
            with rasterio.open(ref) as ds:
                if ds.shape != cand.shape or ds.count != 1:
                    errors.append({"reference": str(ref), "error": "grid/band mismatch"})
                    continue
                arr = ds.read(1)
            ref_vals = np.where(np.isfinite(arr), arr, 0.0)
            cand_vals = np.where(np.isfinite(cand), cand, 0.0)
            rows.append({"reference": str(ref.relative_to(ROOT)), **compare(cand_vals, ref_vals, footprint)})
        except Exception as exc:  # noqa: BLE001 - recorded, never silently dropped
            errors.append({"reference": str(ref), "error": str(exc)})
    duplicates = [r["reference"] for r in rows if r["dot_duplicate"] or r["correlation_duplicate"]
                  or r["identical_inside_footprint"]]
    result = {
        "schema_version": 1,
        "candidate": str(args.candidate.relative_to(ROOT)),
        "references_compared": len(rows),
        "errors": errors,
        "duplicates": duplicates,
        "max_spearman": max((r["spearman_full_footprint"] or 0.0) for r in rows) if rows else None,
        "max_fraction_within_3px": max((r["candidate_fraction_within_3px_of_reference"] or 0.0) for r in rows) if rows else None,
        "comparisons": rows,
        "decision": "duplicate-stop" if duplicates else ("blocked-errors" if errors else "no-duplicate-in-repo-downloads"),
        "note": "Repository downloads only; not the organizer's full registry, so not a novelty certificate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(result["decision"], "compared", len(rows), "max_spearman", result["max_spearman"],
          "max_within3px", result["max_fraction_within_3px"], "errors", len(errors))
    return 0 if result["decision"] == "no-duplicate-in-repo-downloads" else 2


if __name__ == "__main__":
    raise SystemExit(main())
