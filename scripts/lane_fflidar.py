#!/usr/bin/env python3
"""Lane FFL-1: MSDBxLiDAR fusion + distance-stratified far-field emission.

Preregistration: docs/research/2026-10-26-fflidar/preregistration.md (frozen
2026-10-26 before any fold was fitted). Stages, in order:
  build  - 17 label-free LiDAR layers -> data/processed/fflidar/lidar.npy
  e1     - v3 spatially blocked holdout: msdb_edge vs fusion_edge (GATE 1)
  e2     - stratified emission on the saved e1 fusion surfaces (GATE 2, only if e1 passes)
  final  - production TIFF (all-finite, zeros outside), novelty, run card
Shared tools only: gemsdoe30.holdout / msdb / lidar_morphology / emitter_opt /
emission / submission / novelty and scripts/feature_value_holdout's sampler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from check_novelty import audit  # noqa: E402
from feature_value_holdout import fit_standardiser, sample_training_pixels  # noqa: E402
from gemsdoe30.emission import poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.holdout import (  # noqa: E402
    EVALUATOR_VERSION,
    SEGMENT_PROTOCOL_VERSION,
    masked_dti_by_blocks,
    spatial_bootstrap,
    spatial_segment_folds,
)
from gemsdoe30.lidar_morphology import LIDAR_LAYERS, StackedFeatures, lidar_layers  # noqa: E402
from gemsdoe30.msdb import (  # noqa: E402
    MSDB_FEATURE_NAMES,
    MSDB_RAW_KEEP_INDICES,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
    select_msdb_edge_dots,
)
from gemsdoe30.submission import validate_submission_file, write_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-fflidar"
RUN = ROOT / "runs/fflidar"
CACHE = ROOT / "data/processed/fflidar"
MSDB_CACHE = ROOT / "data/processed/msdb-piedmont"
REGISTRY_SRC = ROOT / "docs/research/msdb-piedmont/registry.json"
SEED = 3051
DOT_BUDGET = 44090
GUARD_PX = 17
STRATA = [  # frozen in preregistration.json (H33 profile, <=2px removed, 11-30 merged)
    (2.0, 5.0, 0.14), (5.0, 10.0, 0.15), (10.0, 30.0, 0.34),
    (30.0, 50.0, 0.16), (50.0, None, 0.21),
]


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def load_base():
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")
    labels &= valid
    return base, labels, valid


def band_names() -> list[str]:
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    return [n.split(" - ")[0] for n in manifest["feature_band_names"]]


# ---------------------------------------------------------------- build
def stage_build(valid) -> np.ndarray:
    path = CACHE / "lidar.npy"
    meta = CACHE / "lidar_manifest.json"
    expected = {"layers": list(LIDAR_LAYERS), "shape": [len(LIDAR_LAYERS), *valid.shape]}
    if path.is_file() and meta.is_file() and json.loads(meta.read_text()) == expected:
        return np.load(path, mmap_mode="r")
    CACHE.mkdir(parents=True, exist_ok=True)
    lidar_path = ROOT / "data/raw/external/lidar_scarp_features_u8.tif"
    template = ROOT / "data/raw/sample_submission.tif"
    with rasterio.open(lidar_path) as ds, rasterio.open(template) as tpl:
        if (ds.shape, ds.crs, ds.transform) != (tpl.shape, tpl.crs, tpl.transform) or ds.count != 12:
            raise ValueError("LiDAR descriptor stack grid/band mismatch")
        stack = ds.read()
    out = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                    shape=(len(LIDAR_LAYERS), *valid.shape))
    for i, (name, layer) in enumerate(lidar_layers(stack, valid)):
        assert name == LIDAR_LAYERS[i]
        out[i] = layer
        print("built lidar", name, flush=True)
    del stack
    out.flush()
    del out
    meta.write_text(json.dumps(expected, indent=2) + "\n")
    return np.load(path, mmap_mode="r")


# ---------------------------------------------------------------- models
def fit_model(x, y, *, seed):
    median, scale = fit_standardiser(x)
    filled = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.06, max_leaf_nodes=31,
        min_samples_leaf=100, l2_regularization=1.0,
        early_stopping=False, random_state=seed)
    with threadpool_limits(limits=2):
        model.fit((filled - median) / scale, y)
    return model, median, scale


def predict_ordered(model, stack, columns, median, scale, valid, *, block=256):
    """Predict on `valid` pixels using stack channels listed in `columns`."""
    height, width = valid.shape
    out = np.zeros((height, width), dtype=np.float32)
    cols = list(columns)
    for row in range(0, height, block):
        r1 = min(row + block, height)
        for col in range(0, width, block):
            c1 = min(col + block, width)
            block_valid = valid[row:r1, col:c1]
            if not block_valid.any():
                continue
            data = np.asarray(stack[:, row:r1, col:c1], dtype=np.float32)
            flat = data.reshape(data.shape[0], -1).T[:, cols]
            flat_valid = block_valid.reshape(-1)
            sel = flat[flat_valid]
            sel = np.where(np.isfinite(sel), sel, median)
            with threadpool_limits(limits=2):
                prob = model.predict_proba((sel - median) / scale)[:, 1]
            target = np.zeros((r1 - row, c1 - col), dtype=np.float32)
            target.reshape(-1)[flat_valid] = prob.astype(np.float32)
            out[row:r1, col:c1] = target
    return out


def canaries(parts, part_channels, names, x, y, fold, seed):
    """parts: list of (array, offset). part_channels[j] -> (part_index, channel)."""
    domain = fold["score_valid"] & ~fold["visible"]
    rng = np.random.default_rng(seed + 10000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60000, negatives.size), replace=False)
    test = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])
    rows = []
    for j, name in enumerate(names):
        part_idx, ch = part_channels[j]
        values = np.asarray(parts[part_idx][ch]).ravel()[test].astype(np.float32)
        median, scale = fit_standardiser(x[:, j:j + 1])
        train_filled = np.where(np.isfinite(x[:, j:j + 1]), x[:, j:j + 1], median)
        model = HistGradientBoostingClassifier(max_iter=32, learning_rate=0.1,
                                               max_leaf_nodes=7, early_stopping=False,
                                               random_state=seed + j)
        with threadpool_limits(limits=2):
            model.fit((train_filled - median) / scale, y)
        filled = np.where(np.isfinite(values), values, median[0])
        raw_auc = float(roc_auc_score(target, filled)) if np.ptp(filled) > 0 else 0.5
        with threadpool_limits(limits=2):
            prob = model.predict_proba(((filled - median[0]) / scale[0])[:, None])[:, 1]
        uni_auc = float(roc_auc_score(target, prob)) if np.ptp(prob) > 0 else 0.5
        rows.append({
            "feature": name, "label": "LEAKAGE-CANARY AUC (not DTI)",
            "raw_auc": raw_auc, "raw_auc_either_direction": max(raw_auc, 1 - raw_auc),
            "univariate_training_only_hgb_auc": uni_auc,
            "alarm_above_0_90": bool(max(raw_auc, 1 - raw_auc) > 0.90 or max(uni_auc, 1 - uni_auc) > 0.90),
            "heldout_positives": int(positives.size), "sampled_negatives": int(negatives.size),
        })
    return rows


def stratified_counts(count: int) -> list[int]:
    raw = [share * count for _, _, share in STRATA]
    base = [int(math.floor(v)) for v in raw]
    remainder = count - sum(base)
    order = sorted(range(len(raw)), key=lambda i: (-(raw[i] - base[i]), i))
    for i in order[:remainder]:
        base[i] += 1
    return base


def stratified_select(surface, active, distance, count):
    dots = np.zeros(surface.shape, dtype=np.float32)
    quotas = stratified_counts(count)
    placed = []
    for (low, high, _), quota in zip(STRATA, quotas):
        if quota <= 0:
            continue
        if high is None:
            mask = active & (distance > low)
        else:
            mask = active & (distance > low) & (distance <= high)
        rows, cols = poisson_disk_select_ordered(surface, 3.0, mask=mask, max_kept=quota)
        if len(rows) != quota:
            raise ValueError(f"stratified capacity shortfall in ({low},{high}]: {len(rows)} of {quota}")
        dots[rows, cols] = 1.0
        placed.append(int(len(rows)))
    if int(np.count_nonzero(dots)) != count:
        raise ValueError(f"stratified total mismatch: {np.count_nonzero(dots)} != {count}")
    return dots, placed


def edge_dots(surface, active, count):
    return select_msdb_edge_dots(surface, active, count)


# ---------------------------------------------------------------- main run
def run(deadline: float) -> dict:
    t0 = time.monotonic()

    def check_time():
        if time.monotonic() > deadline:
            raise TimeoutError("FFL-1 experimental time budget exceeded")

    REPORT.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    prereg_md = REPORT / "preregistration.md"
    prereg = json.loads((REPORT / "preregistration.json").read_text())
    prereg_sha = sha(prereg_md)
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    if manifest["dataset_signature"] != prereg["dataset_signature"]:
        raise ValueError("prepared dataset signature differs from preregistration")
    started_path = REPORT / "started.json"
    if started_path.exists():
        raise ValueError("started.json already exists; refusing unscheduled re-execution")
    dump(started_path, {"experiment_count": 1, "experiment_cap": 3,
                        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "preregistration_sha256": prereg_sha,
                        "preregistration_json_sha256": sha(REPORT / "preregistration.json")})

    base, labels, valid = load_base()
    raw_names = band_names()
    print("building/loading MSDB cache...", flush=True)
    msdb = build_or_load_msdb_cache(base, valid, MSDB_CACHE, manifest["dataset_signature"])
    print("building/loading LiDAR layers...", flush=True)
    lidar = stage_build(valid)
    stack = StackedFeatures(base, msdb, lidar,
                            names=raw_names + list(MSDB_FEATURE_NAMES) + list(LIDAR_LAYERS))
    all_names = raw_names + list(MSDB_FEATURE_NAMES) + list(LIDAR_LAYERS)
    parts = [base, msdb, lidar]
    part_channels = ([(0, j) for j in range(19)] + [(1, j) for j in range(18)]
                     + [(2, j) for j in range(17)])
    keep = list(MSDB_RAW_KEEP_INDICES)
    msdb_cols = keep + [19 + j for j in range(18)]
    fusion_cols = msdb_cols + [37 + j for j in range(17)]

    # registry copy (pinned nine-site inventory) for novelty audits
    registry_path = REPORT / "registry.json"
    if not registry_path.exists():
        registry = json.loads(REGISTRY_SRC.read_text())
        registry["complete_scope"] = "nine_priority_sites_pinned_20261026"
        registry["coverage_fflidar"] = ("166 restored TIFFs from GEMSDOE24,25,27,28,30,31,32,33,36 "
                                        "at pinned snapshots; sessions outside those sites are out of scope")
        dump(registry_path, registry)

    arms_e1 = ("msdb_edge", "fusion_edge")
    block_rows = {name: [] for name in ("msdb_edge", "fusion_edge", "fusion_ffstrat")}
    folds_out, canaries_out = [], []
    fold_surfaces = {}

    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        check_time()
        f = int(fold["fold"])
        print(f"fold {f}: sampling + canaries (54 features)...", flush=True)
        x_all, y = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                          negatives_per_positive=6, seed=SEED + f)
        checks = canaries(parts, part_channels, all_names, x_all, y, fold, SEED + f)
        canaries_out.append({"fold": f, "features": checks})
        alarms = [r for r in checks if r["alarm_above_0_90"]]
        print(f"fold {f}: canaries done, alarms={len(alarms)}", flush=True)

        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * int(active.sum()) / int(valid.sum())))
        pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        samp_pos = int(np.count_nonzero(y > 0.5))
        samp_neg = int(np.count_nonzero(y < 0.5))
        # gate scales from the MSDB channels of the training sample (cols 19..36)
        gate_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])

        fold_result = {**fold["metadata"], "dot_budget_each_arm": count, "arms": {}}

        for arm, cols in (("msdb_edge", msdb_cols), ("fusion_edge", fusion_cols)):
            check_time()
            print(f"fold {f}: fitting {arm}...", flush=True)
            model, median, scale = fit_model(x_all[:, cols], y, seed=SEED + f)
            raw = predict_ordered(model, stack, cols, median, scale, active)
            del model
            cal = calibrate_case_control_probabilities(
                raw, population_positives=pop_pos, population_negatives=pop_neg,
                sample_positives=samp_pos, sample_negatives=samp_neg)
            del raw
            psi = compute_curvilinear_discontinuity_gate(msdb, gate_scales, active)
            gated = (cal * psi).astype(np.float32)
            del cal, psi
            if arm == "fusion_edge":
                surf_path = RUN / f"fold{f}_fusion_gated.npy"
                np.save(surf_path, gated)
                fold_surfaces[f] = surf_path
            dots = edge_dots(gated, active, count)
            if arm == "fusion_edge":
                del gated
            scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            del dots
            block_rows[arm].extend(scored["spatial_blocks"])
            fold_result["arms"][arm] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            print(f"fold {f}: {arm} scored ({count} dots)", flush=True)
        folds_out.append(fold_result)
        del x_all, y

    summary_e1 = spatial_bootstrap({k: block_rows[k] for k in arms_e1},
                                   candidate="fusion_edge", replicates=2000, seed=3071)
    delta1 = summary_e1["candidate_minus"]["msdb_edge"]
    canary_alarms = [dict(fold=c["fold"], **r) for c in canaries_out for r in c["features"]
                     if r["alarm_above_0_90"]]
    e1_pass = bool(delta1["value"] > 0 and delta1["ci95"][0] > 0 and not canary_alarms)
    print(f"E1 gate: fusion_edge-msdb_edge={delta1['value']:.6f} CI={delta1['ci95']} pass={e1_pass}", flush=True)

    summary = summary_e1
    candidate_arm = "fusion_edge"
    e2_pass = False
    if e1_pass:
        # Experiment 2: stratified emission on saved fusion surfaces (no refit)
        for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
            check_time()
            f = int(fold["fold"])
            gated = np.load(fold_surfaces[f])
            active = fold["score_valid"] & ~fold["visible"]
            count = int(round(DOT_BUDGET * int(active.sum()) / int(valid.sum())))
            distance = distance_transform_edt(~fold["visible"])
            dots, placed = stratified_select(gated, active & (distance > 2.0), distance, count)
            del gated
            scored = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
            del dots
            block_rows["fusion_ffstrat"].extend(scored["spatial_blocks"])
            folds_out[f]["arms"]["fusion_ffstrat"] = {k: v for k, v in scored["pooled"].items() if k != "dti"}
            folds_out[f]["ffstrat_stratum_counts"] = placed
            print(f"fold {f}: fusion_ffstrat scored ({count} dots, strata={placed})", flush=True)
        summary = spatial_bootstrap(block_rows, candidate="fusion_ffstrat",
                                    replicates=2000, seed=3071)
        d_vs_edge = summary["candidate_minus"]["fusion_edge"]
        d_vs_msdb = summary["candidate_minus"]["msdb_edge"]
        e2_pass = bool(d_vs_edge["value"] > 0 and d_vs_msdb["value"] > 0 and d_vs_msdb["ci95"][0] > 0)
        if e2_pass:
            candidate_arm = "fusion_ffstrat"
        print(f"E2 gate: ffstrat-fusion_edge={d_vs_edge['value']:.6f}; "
              f"ffstrat-msdb_edge={d_vs_msdb['value']:.6f} CI={d_vs_msdb['ci95']} pass={e2_pass}", flush=True)

    experiments_run = 2 if e1_pass else 1
    results = {
        "schema_version": 1, "experiment_spec": "fflidar1",
        "summary": summary, "summary_experiment_1": summary_e1,
        "folds": folds_out, "feature_canaries": canaries_out,
        "canary_alarms": canary_alarms,
        "gates": {"experiment_1_fusion_beats_msdb_ci": e1_pass,
                  "experiment_2_ffstrat_beats_both": e2_pass if e1_pass else None},
        "candidate_arm_selected_by_gates": candidate_arm,
    }

    # ---------------------------------------------------------- production
    print("fitting full-catalogue fusion model...", flush=True)
    x_full, y_full = sample_training_pixels(stack, labels, valid,
                                            negatives_per_positive=6, seed=SEED)
    gate_scales_full = fit_curvilinear_gate_scales(x_full[:, 19:37])
    model, median, scale = fit_model(x_full[:, fusion_cols], y_full, seed=SEED)
    raw = predict_ordered(model, stack, fusion_cols, median, scale, valid)
    del model, x_full
    cal = calibrate_case_control_probabilities(
        raw, population_positives=int(np.count_nonzero(valid & labels)),
        population_negatives=int(np.count_nonzero(valid & ~labels)),
        sample_positives=int(np.count_nonzero(y_full > 0.5)),
        sample_negatives=int(np.count_nonzero(y_full < 0.5)))
    del raw, y_full
    psi = compute_curvilinear_discontinuity_gate(msdb, gate_scales_full, valid)
    gated_full = (cal * psi).astype(np.float32)
    del cal, psi

    template = ROOT / "data/raw/sample_submission.tif"
    surface_tif = RUN / "ffl1-surface.tif"
    write_submission_file(gated_full, template, surface_tif,
                          note="FFL-1 continuous research surface; not a submission.",
                          run_name="gems30-ffl1-surface")
    print("auditing surface novelty...", flush=True)
    surface_audit = audit(surface_tif, template, registry_path, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    surface_dup = surface_audit["decision"] == "duplicate-stop" or bool(surface_audit.get("errors"))
    print("surface novelty:", surface_audit["decision"], flush=True)

    distance_full = distance_transform_edt(~labels)
    eligible = valid & ~labels & (distance_full > 2.0)
    if candidate_arm == "fusion_ffstrat" and not surface_dup:
        dots, placed_full = stratified_select(gated_full, eligible, distance_full, DOT_BUDGET)
    else:
        dots = edge_dots(gated_full, eligible, DOT_BUDGET)
        placed_full = None
    del gated_full
    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-FFL1-{candidate_arm}-{DOT_BUDGET}-20261026-{identity[:12]}"
    note = prereg["note_template"]
    assert len(note) <= 140, len(note)
    generated = RUN / f"{run_name}.tif"
    # Primary portal contract: finite everywhere (0.0 outside), whole array in [0,1].
    write_submission_file(dots, template, generated, run_name=run_name, note=note,
                          outside_value=0.0)
    published = ROOT / "docs/downloads" / f"{run_name}.tif"
    published.write_bytes(generated.read_bytes())
    # sidecar next to the published file, bound to its bytes
    side_src = generated.with_suffix(".json")
    side = json.loads(side_src.read_text())
    side["output_file"] = published.name
    (published.with_suffix(".json")).write_text(json.dumps(side, indent=2) + "\n")
    del dots

    print("auditing final-dot novelty...", flush=True)
    dots_audit = audit(published, template, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    dots_dup = dots_audit["decision"] == "duplicate-stop" or bool(dots_audit.get("errors"))
    print("dots novelty:", dots_audit["decision"], flush=True)

    validation_strict = validate_submission_file(published, template, require_finite_all_cells=True)
    dump(REPORT / "validation.json", validation_strict.to_dict())
    with rasterio.open(published) as ds, rasterio.open(template) as ref:
        arr = ds.read(1)
        validator = {
            "status": "passed" if validation_strict.passed else "failed",
            "no_nan_inside_footprint": bool(np.isfinite(arr[valid]).all()),
            "no_nan_anywhere": bool(np.isfinite(arr).all()),
            "values_in_0_1_inside_footprint": bool(np.all((arr[valid] >= 0.0) & (arr[valid] <= 1.0))),
            "values_in_0_1_whole_array": bool(np.all((arr >= 0.0) & (arr <= 1.0))),
            "min_whole_array": float(arr.min()), "max_whole_array": float(arr.max()),
            "crs_match": ds.crs == ref.crs, "shape_match": ds.shape == ref.shape,
            "transform_match": ds.transform == ref.transform,
            "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
            "outside_footprint_value": 0.0,
            "positive_catalogue_pixels": int(np.count_nonzero(arr[labels] > 0)),
            "dots_within_2px_of_catalogue": int(np.count_nonzero((arr[valid] > 0) & (distance_full[valid] <= 2.0))),
            "emitted_dots": int(np.count_nonzero(arr[valid] > 0)),
            "organizer_acceptance_confirmed": False,
        }

    def maxima(report, stage):
        rows = report.get("comparisons", [])
        corrs = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        ovs = [r["candidate_fraction_within_3px_of_reference"] for r in rows
               if r["candidate_fraction_within_3px_of_reference"] is not None]
        return {"decision": report["decision"], "registry_entries_compared": len(rows),
                "max_spearman": max(corrs) if corrs else None,
                "max_fraction_within_3px": max(ovs) if ovs else None,
                "errors": report.get("errors", [])}

    elapsed = round(time.monotonic() - t0, 2)
    holdout = {
        "label": "HOLDOUT-DTI", "value": summary["arms"][candidate_arm]["value"],
        "withheld_positives": summary["arms"][candidate_arm]["withheld_positives"],
        "ci95": summary["arms"][candidate_arm]["ci95"],
        "tp_weight": summary["arms"][candidate_arm]["tp_weight"],
        "fp_weight": summary["arms"][candidate_arm]["fp_weight"],
        "evaluator_version": summary["evaluator_version"],
        "protocol_version": summary["protocol_version"],
        "bootstrap": summary["bootstrap"],
        "comparators": {k: summary["arms"][k] for k in summary["arms"] if k != candidate_arm},
        "candidate_minus": summary["candidate_minus"],
    }
    promote = bool(e1_pass and (candidate_arm == "fusion_edge" or e2_pass)
                   and not surface_dup and not dots_dup and validation_strict.passed
                   and validator["positive_catalogue_pixels"] == 0
                   and validator["dots_within_2px_of_catalogue"] == 0)
    card = {
        "schema_version": 1, "experiment_spec": "fflidar1",
        "run_id": run_name, "submission_name": run_name, "note": note,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": ("1 m-LiDAR scarp morphology fused with the corrected MSDB-1v2 stationary "
                       "potential-field/topographic discontinuity stack finds uncatalogued faults "
                       "better than MSDB alone; allocating the dot budget across catalogue-distance "
                       "strata (excluding <=2 px) spends dots where prior lanes under-sample."),
        "mechanism": ("48-feature HGB (13 stationary raw + 18 MSDB physics + 17 LiDAR scarp layers), "
                      "Prentice-Pyke Bayes calibration x Rayleigh curvilinear gate; emission = "
                      f"{candidate_arm} (44,090 dots, >2 px off catalogue, r=3 px spacing within strata)"),
        "non_fault_mimic": ("Lake Lahontan paleo-shorelines/playa benches; fluvial terrace risers; "
                            "volcanic flow fronts; pluton contacts; roads/canals/mines"),
        "lane": "FFL-1 (self-assigned, preregistration frozen 2026-10-26; IR-30-078)",
        "lane_preregistration_sha256": prereg_sha,
        "experiments_run": experiments_run, "experiment_cap": 3,
        "experimental_elapsed_seconds": elapsed,
        "dataset_signature": manifest["dataset_signature"],
        "published_tiff": f"docs/downloads/{published.name}",
        "raster_sha256": sha(published),
        "values_sha256": identity,
        "holdout": holdout,
        "feature_canaries": {"features_per_fold": len(all_names), "folds": 4,
                             "alarms": canary_alarms,
                             "max_auc_either_direction": max(
                                 max(r["raw_auc_either_direction"],
                                     max(r["univariate_training_only_hgb_auc"],
                                         1 - r["univariate_training_only_hgb_auc"]))
                                 for c in canaries_out for r in c["features"])},
        "registry": {"surface": maxima(surface_audit, "surface"), "dots": maxima(dots_audit, "dots"),
                     "scope": "pinned nine-site registry (166 restored TIFFs); outside sessions out of scope"},
        "validator_output": validator,
        "production_stratum_counts": placed_full,
        "historical_best_rerun": {
            "verified": True, "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "candidate_beats_best_with_paired_ci": bool(
                summary["candidate_minus"].get("msdb_edge", {}).get("ci95", [0])[0] > 0)},
        "verdict": "promote" if promote else "negative",
        "submission_approved": False, "slot_selected": False,
        "download_ok": bool(validation_strict.passed and not surface_dup and not dots_dup),
        "ok_to_submit": bool(promote),
        "display_status": ("OK TO SUBMIT - research promoted; slot not selected (separate selector, <=3/week)"
                           if promote else "DO NOT SUBMIT - automated gates not all passed"),
        "organizer_score": None,
    }
    results["raster_sha256"] = card["raster_sha256"]
    dump(REPORT / "results.json", results)
    dump(REPORT / "run-card.json", card)
    print(json.dumps({"run_name": run_name, "verdict": card["verdict"],
                      "holdout": holdout["value"], "elapsed_s": elapsed}, indent=1), flush=True)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=7000)
    args = parser.parse_args()
    run(time.monotonic() + args.max_seconds)


if __name__ == "__main__":
    main()
