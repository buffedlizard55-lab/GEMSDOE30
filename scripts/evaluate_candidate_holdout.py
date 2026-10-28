#!/usr/bin/env python3
"""Holdout-DTI evaluation of an already-built candidate GeoTIFF.

Reuses the shared template stack (gemsdoe30.holdout, gemsdoe30.submission)
and the restored organizer mirrors. Protocol:

  * truth / catalogue   = data/raw/labels.tif (known-fault binary mask, value 1)
  * valid footprint     = finite cells of data/raw/sample_submission.tif
  * holdout             = spatial_segment_folds: whole 8-connected catalogue
                          components are split into hidden/known by centroid
                          quadrant, known pixels are masked exactly as the
                          organizer masks known faults, hidden components are
                          stand-in "new faults".
  * scorer              = masked_dti_by_blocks with the published
                          distance-weighted Tversky (alpha 0.2, beta 0.8,
                          300 m triangular kernel), pooled across the 4 folds.
  * uncertainty         = spatial_bootstrap over geographic blocks (paired
                          95% CI) vs a no-signal zero prediction control.

This is a catalogue-proxy HOLDOUT-DTI, NOT an organizer score. A pass is
necessary evidence, never a competition score.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from gemsdoe30.holdout import (  # noqa: E402
    EVALUATOR_VERSION,
    masked_dti_by_blocks,
    spatial_segment_folds,
    spatial_bootstrap,
)
from gemsdoe30.submission import valid_template_mask  # noqa: E402

PREDICTION = Path("docs/downloads/GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif")
LABELS = Path("data/raw/labels.tif")
TEMPLATE = Path("data/raw/sample_submission.tif")
OUT = Path("docs/research/candidate-holdout-evaluation.json")


def read_single_band(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1, masked=False)


def _archived_main() -> int:
    for p in (PREDICTION, LABELS, TEMPLATE):
        if not p.is_file():
            print(f"BLOCKED: required input missing: {p}", file=sys.stderr)
            return 2

    with rasterio.open(TEMPLATE) as tmpl:
        valid = valid_template_mask(tmpl, np)

    prediction = read_single_band(PREDICTION)
    catalogue = (read_single_band(LABELS) == 1.0)

    if prediction.shape != valid.shape or catalogue.shape != valid.shape:
        print("BLOCKED: prediction, catalogue and footprint must share a grid", file=sys.stderr)
        return 2

    # Score only inside the scored footprint; NaN outside contributes nothing.
    scored_prediction = np.where(
        valid, np.nan_to_num(prediction, nan=0.0), 0.0
    ).astype(np.float64)
    zero_prediction = np.zeros_like(scored_prediction)

    folds = list(
        spatial_segment_folds(catalogue, valid, buffer_px=16, kernel_radius_px=3)
    )
    print(f"folds: {len(folds)}  "
          f"withheld components={[f['metadata']['withheld_components'] for f in folds]}  "
          f"withheld positives={[f['metadata']['withheld_positives'] for f in folds]}")

    arms = {"candidate": [], "zero_control": []}
    for fold in folds:
        md = masked_dti_by_blocks(
            scored_prediction,
            truth=catalogue,
            known=fold["visible"],
            valid=fold["score_valid"],
            block_size_px=32,
        )
        arms["candidate"].extend(md.get("spatial_blocks", []))
        md0 = masked_dti_by_blocks(
            zero_prediction,
            truth=catalogue,
            known=fold["visible"],
            valid=fold["score_valid"],
            block_size_px=32,
        )
        arms["zero_control"].extend(md0.get("spatial_blocks", []))

    result = spatial_bootstrap(arms, candidate="candidate", replicates=2000, seed=3071)
    report = {
        "schema_version": 1,
        "evaluator_version": EVALUATOR_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prediction_file": str(PREDICTION),
        "prediction_sha256": hashlib.sha256(PREDICTION.read_bytes()).hexdigest(),
        "catalogue_file": str(LABELS),
        "template_file": str(TEMPLATE),
        "note": "catalogue-proxy HOLDOUT-DTI; not an organizer score; not a promotion authorization",
        "folds": [f["metadata"] for f in folds],
        "candidate": result["arms"]["candidate"],
        "candidate_minus_zero_control": result["candidate_minus"].get("zero_control"),
        "bootstrap": result["bootstrap"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    c = report["candidate"]
    print(f"HOLDOUT-DTI = {c['value']:.6f}")
    print(f"95% CI      = [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}]")
    print(f"withheld positives = {c['withheld_positives']}")
    print(f"tp_weight={c['tp_weight']:.3f} fp_weight={c['fp_weight']:.3f}")
    d = report["candidate_minus_zero_control"]
    print(f"delta vs zero control = {d['value']:+.6f}  CI [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    print(f"report written to {OUT}")
    return 0


def main() -> int:
    print(
        "BLOCKED: this archived script scored a pre-built full-grid raster against a zero control "
        "using truth=catalogue (including guard segments) instead of truth=fold['hidden'] and a "
        "count-matched baseline. Do not rerun or use it for selection.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
