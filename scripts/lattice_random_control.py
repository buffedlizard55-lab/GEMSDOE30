"""Random-dot control for the 13GEMSDOE lattice duplicate witness (IR-30-097).

Question answered: can the literal 70 %-within-3-px duplicate rule tell a
candidate apart from chance against the pinned 13GEMSDOE lattice? Random dots
are placed uniformly inside the official template footprint (the finite cells
of the restored sample_submission grid), then scored with the shared
``gemsdoe30.novelty.compare`` (no private evaluator). If random dots already
exceed 70 %, the witness is non-discriminating at that budget and any dense
candidate is stopped regardless of content.

Requires the pinned template and lattice to be restored first:
    python scripts/restore_public_mirrors.py --ids sample_submission labels
    python scripts/restore_public_mirrors.py --pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice
Writes a receipt only; never writes a raster or a submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.novelty import compare  # noqa: E402  shared evaluator, not a private fork

TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LATTICE = ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif"
OUT = ROOT / "docs/research/2026-10-30-repo-review/lattice-random-control.json"
# 9,652 = dot count of the PR #78 raster (IR-30-098); 22,164 = the bound budget (README 2026-10-27); 44,090 = dot count of the GEMSDOE25/30 D2.8 family.
BUDGETS = (9652, 22164, 44090)
SEEDS = (0, 1, 2, 3, 4)
EXPECTED_LATTICE_SHA = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
EXPECTED_TEMPLATE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    for path, expected in ((TEMPLATE, EXPECTED_TEMPLATE_SHA), (LATTICE, EXPECTED_LATTICE_SHA)):
        if not path.exists():
            raise SystemExit(f"missing {path}; restore the pinned input first (see docstring)")
        if sha256(path) != expected:
            raise SystemExit(f"hash mismatch for {path}; refusing to score")
    with rasterio.open(TEMPLATE) as src:
        template = src.read(1)
        grid = (src.crs.to_string(), src.shape, tuple(src.transform)[:6])
    with rasterio.open(LATTICE) as src:
        lattice = src.read(1)
        lattice_grid = (src.crs.to_string(), src.shape, tuple(src.transform)[:6])
    if grid != lattice_grid:
        raise SystemExit("template and lattice grids differ; refusing to score")
    footprint = np.isfinite(template)
    flat_idx = np.flatnonzero(footprint)
    lattice_clean = np.where(footprint, lattice, np.nan).astype(np.float32)

    rows = []
    for budget in BUDGETS:
        for seed in SEEDS:
            rng = np.random.default_rng(seed)
            pick = rng.choice(flat_idx, size=budget, replace=False)
            cand = np.full(template.shape, np.nan, dtype=np.float32)
            cand.flat[flat_idx] = 0.0
            cand.flat[pick] = 1.0
            res = compare(cand, lattice_clean, footprint, stage="dots")
            rows.append({
                "budget": budget,
                "seed": seed,
                "fraction_within_3px": res["candidate_fraction_within_3px_of_reference"],
                "dot_duplicate_by_literal_rule": res["dot_duplicate"],
            })
    frac = {b: [r["fraction_within_3px"] for r in rows if r["budget"] == b] for b in BUDGETS}
    summary = {
        str(b): {
            "min": min(v),
            "max": max(v),
            "mean": sum(v) / len(v),
            "random_dots_flagged_duplicate": sum(r["dot_duplicate_by_literal_rule"] for r in rows if r["budget"] == b),
            "trials": len(v),
        }
        for b, v in frac.items()
    }
    return {
        "schema_version": 1,
        "purpose": "Random-dot control for the pinned 13GEMSDOE lattice witness (IR-30-097). Measures chance-level overlap under the literal 70%/3 px rule.",
        "evaluator": "gemsdoe30.novelty.compare (stage=dots, Euclidean <=3 px, shared repo code)",
        "template": {"path": "data/raw/sample_submission.tif", "sha256": EXPECTED_TEMPLATE_SHA, "footprint_cells": int(footprint.sum()), "provenance": "owner-supplied mirror, integrity-pinned, NOT organizer-authenticated"},
        "witness": {"path": "data/raw/registry-extra/13gems-lattice-s5.tif", "sha256": EXPECTED_LATTICE_SHA, "positive_cells": int(np.count_nonzero(lattice_clean > 0))},
        "trials": rows,
        "summary_by_budget": summary,
        "interpretation": "If random dots already exceed 70% at a budget, the literal rule cannot separate a candidate from chance at that budget; the duplicate verdict is then non-discriminating, not evidence of copying.",
        "ok_to_submit": False,
        "slot_selected": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the receipt JSON (default prints only)")
    args = parser.parse_args(argv)
    receipt = run()
    text = json.dumps(receipt, indent=2, sort_keys=False) + "\n"
    if args.write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}")
    print(json.dumps(receipt["summary_by_budget"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
