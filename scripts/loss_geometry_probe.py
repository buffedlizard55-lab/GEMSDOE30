#!/usr/bin/env python3
"""Dependency-free synthetic check of the 300 m near-miss loss geometry.

This is a mathematical unit probe only. It is not a spatial holdout experiment,
training result, or leaderboard score.
"""

from __future__ import annotations

import sys
import argparse
import json
from pathlib import Path


# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.metric import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_EPSILON,
    distance_weighted_tversky,
)


def regional_tversky_loss(prediction, truth) -> float:
    tp = fp = fn = 0.0
    for y in range(len(truth)):
        for x in range(len(truth[0])):
            p, g = prediction[y][x], truth[y][x]
            tp += p * g
            fp += p * (1.0 - g)
            fn += (1.0 - p) * g
    score = (tp + DEFAULT_EPSILON) / (
        tp + DEFAULT_ALPHA * fp + DEFAULT_BETA * fn + DEFAULT_EPSILON
    )
    return 1.0 - score


def run_probe() -> dict:
    size, center = 11, 5
    truth = [[0.0 for _ in range(size)] for _ in range(size)]
    truth[center][center] = 1.0
    rows = []
    boundary_weight = 0.5
    for offset_cells in (0, 1, 2, 3, 4):
        prediction = [[0.0 for _ in range(size)] for _ in range(size)]
        prediction[center][center + offset_cells] = 1.0
        components = distance_weighted_tversky(prediction, truth)
        regional_loss = regional_tversky_loss(prediction, truth)
        rows.append(
            {
                "offset_m": 100 * offset_cells,
                "regional_loss": regional_loss,
                "metric_geometry_loss": 1.0 - components.score,
                "combined_loss_regional_plus_0_5_geometry": regional_loss + boundary_weight * (1.0 - components.score),
                "tp_weight": components.tp_weight,
                "fp_weight": components.fp_weight,
                "fn_weight": components.fn_weight,
                "dti": components.score,
            }
        )
    return {
        "status": "synthetic_probe_only_not_holdout",
        "assumptions": {
            "grid": "100 m square pixels",
            "radius_m": 300,
            "kernel": "max(1 - distance / 300 m, 0)",
            "truth": "one positive pixel",
            "prediction": "one unit-probability pixel translated away from truth",
            "combined_loss": "regional soft-Tversky loss + 0.5 * (1 - exact GEMS DTI)",
        },
        "rows": rows,
        "interpretation": (
            "Exact-pixel regional loss ties every non-overlapping shift. The metric geometry "
            "orders near misses by distance (100 m receives 2/3 TP credit; 200 m receives 1/3; "
            "300 m and farther receive no TP credit). This demonstrates the intended loss "
            "shape on a toy grid only; real spatial holdout data are still required."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    result = run_probe()
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
