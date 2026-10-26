#!/usr/bin/env python3
"""FFL-1 Experiment 3 (Amendment A2): frozen stratified emission, paired.

The candidate arm (`fusion_ffstrat`) is placed on the Experiment-1 saved fold
fusion surfaces (no candidate refitting). For an honest paired bootstrap the
two comparator arms are re-scored in the same folds: `fusion_edge` by
re-emitting EDGE on the same saved surfaces (must reproduce Experiment 1's
pooled value), and `msdb_edge` by refitting the frozen MSDB recipe at seed
3051 (must reproduce Experiment 1's pooled value within numerical tolerance).
Production stratified dots are placed only if the holdout gates pass.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402

import lane_fflidar as lane  # noqa: E402
from check_novelty import audit  # noqa: E402
from feature_value_holdout import sample_training_pixels  # noqa: E402
from gemsdoe30.holdout import masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds  # noqa: E402
from gemsdoe30.lidar_morphology import StackedFeatures  # noqa: E402
from gemsdoe30.msdb import (  # noqa: E402
    MSDB_RAW_KEEP_INDICES,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
)
from gemsdoe30.submission import write_submission_file  # noqa: E402

REPORT = lane.REPORT
RUN = lane.RUN
SEED = lane.SEED  # 3051, Experiment-1 seed (comparator reproduction)
NOTE = "FFL1 strat: MSDB31+LiDAR17 fusion, distance-stratified quotas >2px off-cat, 44090 dots, all-finite zeros-outside"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def expanded_registry(candidate_sha: str) -> Path:
    base = json.loads((REPORT / "registry.json").read_text())
    rows = list(base["rasters"])
    seen = {r["sha256"] for r in rows}
    for tif in sorted((ROOT / "docs/downloads").glob("*.tif")):
        digest = sha(tif)
        if digest == candidate_sha or digest in seen:
            continue
        seen.add(digest)
        rows.append({"site": "GEMSDOE30-downloads", "path": str(tif.relative_to(ROOT)),
                     "sha256": digest})
    out = {"complete": False,
           "coverage": "pinned nine-site registry + every TIFF in docs/downloads (candidate SHA excluded)",
           "rasters": rows, "exclusions": []}
    path = REPORT / "registry-expanded.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    return path


def main() -> int:
    assert len(NOTE) <= 140
    t0 = time.monotonic()
    base, labels, valid = lane.load_base()
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    msdb = build_or_load_msdb_cache(base, valid, lane.MSDB_CACHE, manifest["dataset_signature"])
    stack = StackedFeatures(base, msdb, lane.stage_build(valid))
    keep = list(MSDB_RAW_KEEP_INDICES)
    msdb_cols = keep + [19 + j for j in range(18)]

    block_rows = {"msdb_edge": [], "fusion_edge": [], "fusion_ffstrat": []}
    folds_out = []
    for fold in spatial_segment_folds(labels, valid, buffer_px=lane.GUARD_PX):
        f = int(fold["fold"])
        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(lane.DOT_BUDGET * int(active.sum()) / int(valid.sum())))
        gated_fusion = np.load(RUN / f"fold{f}_fusion_gated.npy")
        distance = distance_transform_edt(~fold["visible"])
        fold_result = {"fold": f, "dot_budget_each_arm": count, "arms": {}}

        dots = lane.edge_dots(gated_fusion, active, count)
        scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                      fold["score_valid"], block_size_px=128)
        del dots
        block_rows["fusion_edge"].extend(scored["spatial_blocks"])
        fold_result["arms"]["fusion_edge"] = {k: v for k, v in scored["pooled"].items() if k != "dti"}

        dots, placed = lane.stratified_select(gated_fusion, active & (distance > 2.0), distance, count)
        del gated_fusion
        scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                      fold["score_valid"], block_size_px=128)
        del dots
        block_rows["fusion_ffstrat"].extend(scored["spatial_blocks"])
        fold_result["arms"]["fusion_ffstrat"] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
        fold_result["ffstrat_stratum_counts"] = placed

        # comparator reproduction (frozen recipe, seed 3051)
        x_all, y = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                          negatives_per_positive=6, seed=SEED + f)
        gate_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])
        pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        model, median, scale = lane.fit_model(x_all[:, msdb_cols], y, seed=SEED + f)
        raw = lane.predict_ordered(model, stack, msdb_cols, median, scale, active)
        del model, x_all
        cal = calibrate_case_control_probabilities(
            raw, population_positives=pop_pos, population_negatives=pop_neg,
            sample_positives=int(np.count_nonzero(y > 0.5)),
            sample_negatives=int(np.count_nonzero(y < 0.5)))
        del raw, y
        psi = compute_curvilinear_discontinuity_gate(msdb, gate_scales, active)
        gated = (cal * psi).astype(np.float32)
        del cal, psi
        dots = lane.edge_dots(gated, active, count)
        del gated
        scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                      fold["score_valid"], block_size_px=128)
        del dots
        block_rows["msdb_edge"].extend(scored["spatial_blocks"])
        fold_result["arms"]["msdb_edge"] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
        folds_out.append(fold_result)
        print(f"fold {f}: three arms scored ({count} dots)", flush=True)

    summary = spatial_bootstrap(block_rows, candidate="fusion_ffstrat", replicates=2000, seed=3071)
    d_msdb = summary["candidate_minus"]["msdb_edge"]
    d_edge = summary["candidate_minus"]["fusion_edge"]
    holdout_pass = bool(d_msdb["value"] > 0 and d_msdb["ci95"][0] > 0)
    payload = {"schema_version": 1, "experiment": 3, "amendment": "amendment-stratified.md",
               "summary": summary, "folds": folds_out, "label": "HOLDOUT-DTI",
               "gate": {"rule": "fusion_ffstrat-msdb_edge > 0 with paired 95% CI lower bound > 0",
                        "passed": holdout_pass},
               "elapsed_seconds": round(time.monotonic() - t0, 2)}
    print(f"ffstrat-msdb={d_msdb['value']:.6f} CI={d_msdb['ci95']} "
          f"ffstrat-fusion_edge={d_edge['value']:.6f} pass={holdout_pass}", flush=True)

    production = None
    if holdout_pass:
        template = ROOT / "data/raw/sample_submission.tif"
        with rasterio.open(RUN / "ffl1-surface.tif") as ds:
            surface = ds.read(1)
        surface = np.where(valid & np.isfinite(surface), surface, 0.0).astype(np.float32)
        distance_full = distance_transform_edt(~labels)
        eligible = valid & ~labels & (distance_full > 2.0)
        dots, placed_full = lane.stratified_select(surface, eligible, distance_full, lane.DOT_BUDGET)
        identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
        run_name = f"gems30-FFL1-fusion_ffstrat-{lane.DOT_BUDGET}-20261026-{identity[:12]}"
        generated = RUN / f"{run_name}.tif"
        write_submission_file(dots, template, generated, run_name=run_name, note=NOTE, outside_value=0.0)
        published = ROOT / "docs/downloads" / f"{run_name}.tif"
        published.write_bytes(generated.read_bytes())
        side = json.loads(generated.with_suffix(".json").read_text())
        side["output_file"] = published.name
        published.with_suffix(".json").write_text(json.dumps(side, indent=2) + "\n")
        registry = expanded_registry(sha(published))
        dots_audit = audit(published, template, registry, "dots")
        lane.dump(REPORT / "novelty-dots-expanded.json", dots_audit)
        surf_audit = audit(RUN / "ffl1-surface.tif", template, registry, "surface")
        lane.dump(REPORT / "novelty-surface-expanded.json", surf_audit)
        production = {"run_name": run_name, "note": NOTE, "published_tiff": str(published.relative_to(ROOT)),
                      "raster_sha256": sha(published), "values_sha256": identity,
                      "stratum_counts": placed_full,
                      "dots_audit_max_spearman": max(r["spearman_full_footprint"] for r in dots_audit["comparisons"]),
                      "dots_audit_max_fraction_within_3px": max(r["candidate_fraction_within_3px_of_reference"] for r in dots_audit["comparisons"]),
                      "surface_audit_max_spearman": max(r["spearman_full_footprint"] for r in surf_audit["comparisons"]),
                      "dots_audit_errors": dots_audit.get("errors", []),
                      "surface_audit_errors": surf_audit.get("errors", [])}
        print(json.dumps(production, indent=1), flush=True)
    payload["production"] = production
    payload["elapsed_seconds"] = round(time.monotonic() - t0, 2)
    lane.dump(REPORT / "results-stratified.json", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
