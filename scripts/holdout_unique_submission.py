#!/usr/bin/env python3
"""Holdout evaluation of the unique submission raster (catalogue proxy, not a score).

Uses the shared component-holdout stack:
  * Catalogue (known faults): derived_gdr_qfaults_v2_100m_u8.tif
    (INGENIOUS Qfaults v2 rasterized on the competition grid).
  * Truth stand-in: data/raw/labels.tif (60,988 labelled fault pixels).
  * Scored domain: template footprint minus catalogue pixels, exactly as the
    organizer masks known faults.
  * Split: whole 8-connected catalogue components, interleaved by 3.2 km tile
    (seed 31), half hidden as stand-in "new" faults.
  * Statistic: pooled distance-weighted Tversky, alpha 0.2 / beta 0.8,
    300 m triangular kernel; 95% CI from paired spatial-block bootstrap
    (component-holdout-v3-blockstats-20261025).
  * Control: 20,000 count-matched uniform random dots (seeded), same folds.
  * Leakage canary: ROC AUC of the candidate alone vs the hidden truth.

This is a labelled-fault proxy, biased toward catalogue-like faults; it is
NOT an organizer score and cannot forecast the leaderboard.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gemsdoe30.holdout import (
    EVALUATOR_VERSION,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    split_components,
    spatial_bootstrap,
    spatial_segment_folds,
)
from gemsdoe30.submission import valid_template_mask

REPO = Path(__file__).resolve().parents[1]
CANDIDATE = REPO / "docs" / "downloads" / "gems30-unique-uncovered-cells-20k-20261027T233516Z.tif"
TEMPLATE = REPO / "data" / "raw" / "sample_submission.tif"
LABELS = REPO / "data" / "raw" / "labels.tif"
CATALOGUE = REPO / "data" / "external" / "derived_gdr_qfaults_v2_100m_u8.tif"
OUT = REPO / "docs" / "research" / "2026-10-27-unique-submission" / "holdout-report.json"
BLOCK_PX = 256
BOOTSTRAP_REPS = 2000


def read_bool(path, label, shape):
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    if arr.shape != shape:
        raise ValueError(f"{label}: shape {arr.shape} != {shape}")
    return arr


def main() -> int:
    with rasterio.open(TEMPLATE) as ds:
        profile = ds.profile
        valid = valid_template_mask(ds, np)
        transform = ds.transform
    print(f"template {profile['height']}x{profile['width']} {ds.crs if False else transform} valid={int(valid.sum()):,}")

    labels_raw = read_bool(LABELS, "labels", valid.shape)
    catalogue = read_bool(CATALOGUE, "catalogue", valid.shape)
    truth = (labels_raw == 1.0) & valid
    print(f"label pixels: {int(truth.sum()):,}  catalogue pixels: {int(catalogue.sum()):,}")

    with rasterio.open(CANDIDATE) as ds:
        cand = ds.read(1).astype(np.float64)
    if cand.shape != valid.shape:
        raise ValueError("candidate grid mismatch")
    # Score only the published footprint; NaN outside becomes 0 and is masked out.
    pred = np.where(valid, cand, 0.0)
    if not np.all(np.isfinite(pred[valid])) or np.any((pred[valid] < 0) | (pred[valid] > 1)):
        raise ValueError("candidate in-footprint values must be finite in [0, 1]")

    known_full = catalogue | ~valid
    truth_full = truth  # already restricted to valid footprint

    # Whole-grid single split (50% of whole catalogue components hidden as
    # stand-in "new" faults; visible components masked as known).
    hidden_comp, known_comp, n_comp = split_components(catalogue, seed=31, stratify=32)
    known_full_split = known_comp | ~valid
    fp_w = fp_weight_field(hidden_comp, known_full_split)
    res = masked_dti(pred, hidden_comp, known_full_split, fp_weight=fp_w)
    print("single split:", {k: round(v, 6) if isinstance(v, float) else v for k, v in res.items()})

    # Leakage canary: candidate alone vs hidden stand-in truth on scored domain.
    scored = valid & ~known_full_split
    try:
        auc = float(roc_auc_score(hidden_comp[scored].astype(int), pred[scored]))
    except ValueError:
        auc = None
    print(f"leakage canary AUC (candidate vs hidden catalogue truth): {auc}  (>0.90 would be leakage)")

    # Four buffered regional folds + paired block bootstrap vs count-matched control.
    rng = np.random.default_rng(777)
    pool = np.flatnonzero(valid & ~catalogue)
    control_dots = rng.choice(pool, size=int(pred[pred > 0].sum()), replace=False)
    control = np.zeros(valid.shape, dtype=np.float64)
    control.flat[control_dots] = 1.0

    folds = list(spatial_segment_folds(catalogue, valid, buffer_px=16, kernel_radius_px=3))

    def block_rows(fold_list, prediction):
        rows = []
        for fold in fold_list:
            hidden_f = fold["hidden"] & valid
            known_f = (catalogue & ~fold["hidden"]) | fold["guard"] | ~valid
            out = masked_dti_by_blocks(
                prediction, hidden_f, known_f, fold["score_valid"], block_size_px=BLOCK_PX
            )
            rows.extend(out["spatial_blocks"])
        return rows

    cand_rows = block_rows(folds, pred)
    ctrl_rows = block_rows(folds, control)
    keys = {(r["block_row"], r["block_col"]) for r in cand_rows}
    assert keys == {(r["block_row"], r["block_col"]) for r in ctrl_rows}, "block mismatch"
    print(f"folds: {len(folds)}  geographic blocks: {len(keys)}  withheld positives per fold: "
          f"{[int(f['metadata']['withheld_positives']) for f in folds]}")

    bootstrap = spatial_bootstrap(
        {"candidate": cand_rows, "control": ctrl_rows},
        candidate="candidate",
        replicates=BOOTSTRAP_REPS,
        seed=3071,
    )
    print(json.dumps(bootstrap["arms"], indent=2))
    print(json.dumps(bootstrap["candidate_minus"], indent=2))

    auc_safe = None if auc is None else (float(auc) if np.isfinite(auc) else None)
    report = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evaluator_version": EVALUATOR_VERSION,
        "candidate": str(CANDIDATE.relative_to(REPO)),
        "candidate_sha256": __import__("hashlib").sha256(CANDIDATE.read_bytes()).hexdigest(),
        "catalogue": str(CATALOGUE.relative_to(REPO)),
        "labels": str(LABELS.relative_to(REPO)),
        "withheld_positives": int(res["hidden_truth_pixels"]),
        "single_split": res,
        "leakage_canary_auc": auc_safe,
        "bootstrap": bootstrap,
        "scope": "catalogue-proxy holdout; NOT an organizer score; not a leaderboard forecast",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
