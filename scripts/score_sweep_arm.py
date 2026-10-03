#!/usr/bin/env python3
"""Score one sweep arm's held-out predictions: dense surface AND emitted mask.

The brief's boundary-loss follow-up requires "score emitted masks rather than
dense probability surfaces". This scorer reads a fold-masked prediction ``.npy``
(as written by ``scripts/infer_model.py --predictions-only``) and reports the
exact distance-weighted Tversky components twice: once on the dense surface and
once after uniform Poisson-disk thinning (the emission family that the
preregistered holdout kept as default). Fold-isolated values are diagnostics.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import dti_components_masked, poisson_disk_select  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--dot-radius-px", type=float, default=3.0)
    parser.add_argument("--candidate-pool", type=int, default=480_000,
                        help="top-K scored pixels to thin (the real emission family's pool cap; "
                             "thinning an all-positive surface would degenerate to a score-blind lattice)")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    pred = np.load(args.predictions)
    labels = np.load(args.data_dir / "labels.npy")
    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    if pred.shape != valid.shape:
        raise ValueError("prediction grid does not match prepared footprint")
    # Infer writes NaN outside the evaluated fold; the scored domain is exactly
    # the pixels the model actually predicted (fold-isolated when --fold was used).
    evaluated = np.isfinite(pred)
    scored = valid & evaluated
    truth = (labels == 1) & scored
    pred = np.where(evaluated, pred, 0.0)
    if not scored.any():
        raise ValueError("predictions cover no scored pixels")

    dense = dti_components_masked(pred, truth, scored)
    dots = poisson_disk_select(pred, args.dot_radius_px, mask=scored,
                               limit=int(args.candidate_pool))
    dotted = np.zeros_like(pred)
    dotted[dots] = 1.0
    dotted_dti = dti_components_masked(dotted, truth, scored)

    report = {
        "predictions": str(args.predictions),
        "dense": dense,
        "emitted_uniform_dots": dotted_dti | {"dot_radius_px": args.dot_radius_px,
                                              "candidate_pool": int(args.candidate_pool),
                                              "dots": int(dotted.sum())},
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
