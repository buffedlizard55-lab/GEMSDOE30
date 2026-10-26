#!/usr/bin/env python3
"""FFL-1 Experiment 2 (Amendment A1): one fresh-seed confirmation, seed 3063.

Identical frozen recipe to Experiment 1 in scripts/lane_fflidar.py; only the
sampler/model seed changes. No production model is fitted here.
Writes docs/research/2026-10-26-fflidar/results-confirmation.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

import lane_fflidar as lane  # noqa: E402
from feature_value_holdout import sample_training_pixels  # noqa: E402
from gemsdoe30.holdout import masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds  # noqa: E402
from gemsdoe30.lidar_morphology import StackedFeatures  # noqa: E402
from gemsdoe30.msdb import (  # noqa: E402
    MSDB_FEATURE_NAMES,
    MSDB_RAW_KEEP_INDICES,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
)

SEED = 3063  # the single confirmation seed frozen in amendment-confirmation.md


def main() -> int:
    t0 = time.monotonic()
    report = lane.REPORT
    base, labels, valid = lane.load_base()
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    msdb = build_or_load_msdb_cache(base, valid, lane.MSDB_CACHE, manifest["dataset_signature"])
    lidar = lane.stage_build(valid)
    stack = StackedFeatures(base, msdb, lidar)
    keep = list(MSDB_RAW_KEEP_INDICES)
    msdb_cols = keep + [19 + j for j in range(18)]
    fusion_cols = msdb_cols + [37 + j for j in range(17)]
    block_rows = {"msdb_edge": [], "fusion_edge": []}
    folds_out = []

    for fold in spatial_segment_folds(labels, valid, buffer_px=lane.GUARD_PX):
        f = int(fold["fold"])
        x_all, y = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                          negatives_per_positive=6, seed=SEED + f)
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(lane.DOT_BUDGET * int(active.sum()) / int(valid.sum())))
        pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        samp_pos = int(np.count_nonzero(y > 0.5))
        samp_neg = int(np.count_nonzero(y < 0.5))
        gate_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])
        fold_result = {"fold": f, "dot_budget_each_arm": count, "arms": {}}
        for arm, cols in (("msdb_edge", msdb_cols), ("fusion_edge", fusion_cols)):
            model, median, scale = lane.fit_model(x_all[:, cols], y, seed=SEED + f)
            raw = lane.predict_ordered(model, stack, cols, median, scale, active)
            del model
            cal = calibrate_case_control_probabilities(
                raw, population_positives=pop_pos, population_negatives=pop_neg,
                sample_positives=samp_pos, sample_negatives=samp_neg)
            del raw
            psi = compute_curvilinear_discontinuity_gate(msdb, gate_scales, active)
            gated = (cal * psi).astype(np.float32)
            del cal, psi
            dots = lane.edge_dots(gated, active, count)
            del gated
            scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            del dots
            block_rows[arm].extend(scored["spatial_blocks"])
            fold_result["arms"][arm] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            print(f"fold {f}: {arm} scored ({count} dots)", flush=True)
        folds_out.append(fold_result)
        del x_all, y

    summary = spatial_bootstrap(block_rows, candidate="fusion_edge", replicates=2000, seed=3071)
    delta = summary["candidate_minus"]["msdb_edge"]
    passed = bool(delta["value"] > 0 and delta["ci95"][0] > 0)
    payload = {
        "schema_version": 1, "experiment": 2, "amendment": "amendment-confirmation.md",
        "seed": SEED, "summary": summary, "folds": folds_out,
        "gate": {"rule": "fresh-seed fusion_edge-msdb_edge > 0 with paired 95% CI lower bound > 0",
                 "passed": passed},
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "label": "HOLDOUT-DTI",
    }
    lane.dump(report / "results-confirmation.json", payload)
    print(f"confirmation delta={delta['value']:.6f} CI={delta['ci95']} passed={passed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
