#!/usr/bin/env python3
"""Execute the preregistered single-experiment MSDB-1 research lane end-to-end.

Implements Rank-1 hypothesis ``MSDB-1`` (Multi-Scale Steerable Discontinuity &
Piedmont Cover-Breach Habitat + Prentice-Pyke Bayes-Calibrated 300 m Submodular
Coverage) using shared repository infrastructure (`gemsdoe30.holdout`,
`gemsdoe30.emitter_opt`, `gemsdoe30.submission`, `gemsdoe30.novelty`,
`gemsdoe30.readiness`).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from check_novelty import audit
from feature_value_holdout import fit_standardiser, predict_grid, sample_training_pixels
from gemsdoe30.emission import poisson_disk_select_ordered
from gemsdoe30.holdout import (
    EVALUATOR_VERSION,
    SEGMENT_PROTOCOL_VERSION,
    masked_dti_by_blocks,
    spatial_bootstrap,
    spatial_segment_folds,
)
from gemsdoe30.msdb import (
    EUCLIDEAN_SUPPORT_EXACT_PX,
    MAX_AXIAL_HALFWIDTH_PX,
    MSDB_FEATURE_NAMES,
    MSDB_RAW_KEEP_INDICES,
    SUPPORT_PX,
    TRANSFORM_VERSION,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
    select_msdb_edge_dots,
)
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file, write_submission_file

REPORT = ROOT / "docs/research/msdb-piedmont"
CACHE = ROOT / "data/processed/msdb-piedmont"
RUN = ROOT / "runs/msdb-piedmont"
SEED = 3041
DOT_BUDGET = 44090
GUARD_PX = 17


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def check_time(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise TimeoutError("MSDB-1 experimental runtime budget exceeded")


def fit_core19_model(x: np.ndarray, y: np.ndarray, *, seed: int, iterations: int = 120, leaves: int = 31):
    median, scale = fit_standardiser(x)
    filled = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=iterations,
        learning_rate=0.1,
        max_leaf_nodes=leaves,
        early_stopping=False,
        random_state=seed,
    )
    with threadpool_limits(limits=2):
        model.fit((filled - median) / scale, y)
    return model, median, scale


def fit_msdb_model(x: np.ndarray, y: np.ndarray, *, seed: int):
    median, scale = fit_standardiser(x)
    filled = np.where(np.isfinite(x), x, median)
    model = HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.06,
        max_leaf_nodes=31,
        min_samples_leaf=100,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    )
    with threadpool_limits(limits=2):
        model.fit((filled - median) / scale, y)
    return model, median, scale


def predict_dual_grid(
    model,
    base: np.ndarray,
    msdb: np.ndarray,
    raw_keep_indices: list[int],
    median: np.ndarray,
    scale: np.ndarray,
    valid: np.ndarray,
    *,
    block: int = 256,
) -> np.ndarray:
    """Predict probabilities from retained raw channels + (18, H, W) MSDB memmap in tiles."""
    height, width = valid.shape
    out = np.zeros((height, width), dtype=np.float32)
    c_keep, c_msdb = len(raw_keep_indices), msdb.shape[0]
    for row in range(0, height, block):
        r1 = min(row + block, height)
        for col in range(0, width, block):
            c1 = min(col + block, width)
            block_valid = valid[row:r1, col:c1]
            if not block_valid.any():
                continue
            flat_valid = block_valid.reshape(-1)
            b_tile = base[raw_keep_indices, row:r1, col:c1].reshape(c_keep, -1)[:, flat_valid].T.astype(np.float32)
            m_tile = msdb[:, row:r1, col:c1].reshape(c_msdb, -1)[:, flat_valid].T.astype(np.float32)
            data = np.concatenate([b_tile, m_tile], axis=1)
            data = np.where(np.isfinite(data), data, median)
            prob = model.predict_proba((data - median) / scale)[:, 1]
            target = np.zeros((r1 - row, c1 - col), dtype=np.float32)
            target.reshape(-1)[flat_valid] = prob.astype(np.float32)
            out[row:r1, col:c1] = target
    return out


def select_poisson_dots(surface: np.ndarray, mask: np.ndarray, count: int) -> np.ndarray:
    if count < 1:
        raise ValueError("a positive predeclared dot budget is required")
    rows, cols = poisson_disk_select_ordered(surface, 3.0, mask=mask, max_kept=count)
    if len(rows) != count:
        raise ValueError(f"Poisson count shortfall: {len(rows)} of {count} requested dots")
    dots = np.zeros(surface.shape, dtype=np.float32)
    dots[rows, cols] = 1.0
    return dots


def summarize_novelty(surface: dict, dots: dict, rel_dir: str) -> dict:
    def maxima(report: dict) -> dict:
        rows = report.get("comparisons", [])
        correlations = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        overlaps = [
            r["candidate_fraction_within_3px_of_reference"]
            for r in rows
            if r["candidate_fraction_within_3px_of_reference"] is not None
        ]
        return {
            "decision": report["decision"],
            "registry_entries_compared": len(rows),
            "max_spearman": max(correlations) if correlations else None,
            "max_fraction_within_3px": max(overlaps) if overlaps else None,
            "errors": report.get("errors", []),
        }

    return {
        "complete": False,
        "surface": maxima(surface),
        "dots": maxima(dots),
        "coverage": "all published aligned TIFFs at nine recorded repository snapshots; missing other sessions and most original surfaces",
        "receipt_surface": f"{rel_dir}/novelty-surface.json",
        "receipt_dots": f"{rel_dir}/novelty-dots.json",
    }


def feature_canaries_dual(
    base: np.ndarray,
    msdb: np.ndarray,
    visible_labels: np.ndarray,
    fold: dict,
    raw_names: list[str],
    derived_names: list[str],
    seed: int,
    deadline: float,
):
    """Test all 37 raw + MSDB-1 features solo in fold `f` (canary alarm if AUC > 0.90)."""
    train = fold["train_mask"]
    domain = fold["score_valid"] & ~fold["visible"]
    xb, y = sample_training_pixels(base, visible_labels, train, negatives_per_positive=6, seed=seed)
    xm, ym = sample_training_pixels(msdb, visible_labels, train, negatives_per_positive=6, seed=seed)
    if not np.array_equal(y, ym):
        raise AssertionError("Paired sampler mismatch between raw and MSDB feature memmaps")
    xc_all = np.concatenate([xb, xm], axis=1)
    del ym

    rng = np.random.default_rng(seed + 10000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60000, negatives.size), replace=False)
    test = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])

    all_names = [*raw_names, *derived_names]
    rows = []
    for j, name in enumerate(all_names):
        check_time(deadline)
        training = xc_all[:, j : j + 1]
        values = base[j].ravel()[test] if j < 19 else msdb[j - 19].ravel()[test]
        model, median, scale = fit_core19_model(training, y, seed=seed + j, iterations=32, leaves=7)
        filled = np.where(np.isfinite(values), values, median[0])
        raw_auc = float(roc_auc_score(target, filled))
        with threadpool_limits(limits=2):
            probabilities = model.predict_proba(((filled - median[0]) / scale[0])[:, None])[:, 1]
        model_auc = float(roc_auc_score(target, probabilities))
        raw_either = max(raw_auc, 1.0 - raw_auc)
        model_either = max(model_auc, 1.0 - model_auc)
        rows.append(
            {
                "feature": name,
                "label": "LEAKAGE-CANARY AUC (not DTI)",
                "raw_auc": raw_auc,
                "raw_auc_either_direction": raw_either,
                "univariate_training_only_hgb_auc": model_auc,
                "alarm_above_0_90": raw_either > 0.90 or model_either > 0.90,
                "heldout_positives": int(positives.size),
                "sampled_negatives": int(negatives.size),
            }
        )
    del xc_all
    return rows, xb, xm, y


def run(max_seconds: int) -> dict:
    started_mono = time.monotonic()
    deadline = started_mono + max_seconds
    REPORT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)

    prereg_md = REPORT / "preregistration.md"
    prereg_json = REPORT / "preregistration.json"
    registry_path = REPORT / "registry.json"
    prereg_spec = json.loads(prereg_json.read_text())
    prereg_sha = sha(prereg_md)
    prereg_json_sha = sha(prereg_json)
    registry_sha = sha(registry_path)
    if registry_sha != prereg_spec["frozen_registry_sha256"]:
        raise ValueError("Frozen registry SHA-256 differs from preregistration.json")

    note = prereg_spec["note"]
    if len(note) > 140:
        raise ValueError("Submission note exceeds 140 characters")

    # 1. Fresh cell-by-cell prepared-cache verification receipt.
    cache_receipt_path = REPORT / "cache-verification.json"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_prepared_cache.py"), "--output", str(cache_receipt_path)],
        check=True,
        cwd=ROOT,
    )

    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    if manifest["dataset_signature"] != prereg_spec["dataset_signature"]:
        raise ValueError("Prepared dataset signature differs from preregistration.json")

    raw_names = [entry.split(" - ")[0] for entry in manifest["feature_band_names"]]
    if raw_names != prereg_spec["raw_feature_names"]:
        raise ValueError("Raw feature names differ from preregistration.json")
    if list(MSDB_FEATURE_NAMES) != prereg_spec["derived_feature_names"]:
        raise ValueError("Derived MSDB feature names differ from preregistration.json")

    raw_keep = list(MSDB_RAW_KEEP_INDICES)
    if raw_keep != prereg_spec["msdb_retained_raw_indices"]:
        raise ValueError("Retained MSDB raw indices differ from preregistration.json")
    experiment_ordinal = int(prereg_spec.get("experiment_ordinal", 1))
    previous_elapsed = float(prereg_spec.get("previous_experiment_elapsed_seconds", 0.0))

    started_path = REPORT / "started.json"
    if started_path.exists():
        raise ValueError("started.json already exists; refusing unscheduled re-execution")
    dump(
        started_path,
        {
            "experiment_count": experiment_ordinal,
            "experiment_cap": 3,
            "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "preregistration_sha256": prereg_sha,
            "preregistration_json_sha256": prereg_json_sha,
            "registry_sha256": registry_sha,
            "physical_support_px": SUPPORT_PX,
            "holdout_guard_px": GUARD_PX,
        },
    )

    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    labels = np.load(ROOT / "data/processed/labels.npy").astype(bool)
    valid = np.load(ROOT / "data/processed/valid.npy").astype(bool)
    template = ROOT / "data/raw/sample_submission.tif"

    print("Building/loading bounded-support MSDB-1 18-layer feature memmap...", flush=True)
    t_feat = time.monotonic()
    msdb = build_or_load_msdb_cache(base, valid, CACHE, manifest["dataset_signature"])
    print(f"MSDB-1 cache ready in {time.monotonic() - t_feat:.1f}s: shape={msdb.shape}", flush=True)

    transform_code_sha = sha(ROOT / "src/gemsdoe30/msdb.py")
    dump(
        REPORT / "feature-receipt.json",
        {
            "signature": {
                "transform_version": TRANSFORM_VERSION,
                "transform_code_sha256": transform_code_sha,
                "dataset_signature": manifest["dataset_signature"],
            },
            "support_px": SUPPORT_PX,
            "max_axial_halfwidth_px": MAX_AXIAL_HALFWIDTH_PX,
            "euclidean_support_px_exact": EUCLIDEAN_SUPPORT_EXACT_PX,
            "derived_feature_names": list(MSDB_FEATURE_NAMES),
            "msdb_retained_raw_indices": raw_keep,
        },
    )
    check_time(deadline)

    # 2. Full-footprint MSDB-1 v2 fit -> Rayleigh curvilinear gate -> surface novelty -> EDGE -> dot novelty.
    print("Fitting full-footprint MSDB-1 v2 (31 stationary features + Rayleigh curvilinear gate)...", flush=True)
    xb_full, y_full = sample_training_pixels(base, labels, valid, negatives_per_positive=6, seed=SEED)
    xm_full, ym_full = sample_training_pixels(msdb, labels, valid, negatives_per_positive=6, seed=SEED)
    if not np.array_equal(y_full, ym_full):
        raise AssertionError("Full-footprint paired sampler mismatch")
    full_gate_scales = fit_curvilinear_gate_scales(xm_full)
    xc_full = np.concatenate([xb_full[:, raw_keep], xm_full], axis=1)
    n_samp_pos = int(np.count_nonzero(y_full > 0.5))
    n_samp_neg = int(np.count_nonzero(y_full < 0.5))
    del xb_full, xm_full, ym_full

    full_model, full_median, full_scale = fit_msdb_model(xc_full, y_full, seed=SEED)
    del xc_full, y_full

    with threadpool_limits(limits=2):
        raw_surface = predict_dual_grid(full_model, base, msdb, raw_keep, full_median, full_scale, valid)
    del full_model

    n_pop_pos = int(np.count_nonzero(valid & labels))
    n_pop_neg = int(np.count_nonzero(valid & ~labels))
    cal_surface = calibrate_case_control_probabilities(
        raw_surface,
        population_positives=n_pop_pos,
        population_negatives=n_pop_neg,
        sample_positives=n_samp_pos,
        sample_negatives=n_samp_neg,
    )
    del raw_surface
    full_psi = compute_curvilinear_discontinuity_gate(msdb, full_gate_scales, valid)
    cal_surface = (cal_surface * full_psi).astype(np.float32)
    del full_psi

    surface_tif = RUN / "msdb1-surface.tif"
    write_submission_file(
        cal_surface,
        template,
        surface_tif,
        note="Continuous Bayes-calibrated MSDB-1 research surface; not a competition submission.",
        run_name="gems30-msdb1-surface",
    )
    print("Auditing continuous MSDB-1 surface against 165-raster 9-site registry...", flush=True)
    surface_audit = audit(surface_tif, template, registry_path, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    print("Surface novelty decision:", surface_audit["decision"], flush=True)
    if surface_audit["decision"] == "duplicate-stop" or surface_audit.get("errors"):
        dump(
            REPORT / "duplicate-stop.json",
            {"stage": "surface", "decision": surface_audit["decision"], "errors": surface_audit.get("errors", [])},
        )
        raise ValueError(f"Surface novelty gate blocked placement: {surface_audit['decision']}")
    check_time(deadline)

    print(f"Placing {DOT_BUDGET} submodular EDGE dots on full off-catalogue footprint...", flush=True)
    t_edge = time.monotonic()
    dots = select_msdb_edge_dots(cal_surface, valid & ~labels, DOT_BUDGET)
    print(f"Full-footprint EDGE selection finished in {time.monotonic() - t_edge:.1f}s", flush=True)
    del cal_surface

    identity = hashlib.sha256(np.ascontiguousarray(dots[valid]).tobytes()).hexdigest()
    run_name = f"gems30-MSDB1-edge44090-20261025-{identity[:12]}"
    generated = RUN / f"{run_name}.tif"
    manifest_output = write_submission_file(dots, template, generated, run_name=run_name, note=note)

    print("Auditing final MSDB-1 dots against 165-raster 9-site registry...", flush=True)
    dots_audit = audit(generated, template, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    print("Final-dot novelty decision:", dots_audit["decision"], flush=True)
    if dots_audit["decision"] == "duplicate-stop" or dots_audit.get("errors"):
        dump(
            REPORT / "duplicate-stop.json",
            {"stage": "dots", "decision": dots_audit["decision"], "errors": dots_audit.get("errors", [])},
        )
        raise ValueError(f"Dot novelty gate blocked publication: {dots_audit['decision']}")
    del dots

    # 3. 4-Fold Spatially-Blocked Buffered Whole-Component Hide-and-Recover Evaluation.
    arms = ("core19", "msdb_poisson", "msdb_edge")
    block_rows = {name: [] for name in arms}
    folds_out = []
    canaries_out = []
    hidden_total = np.zeros(valid.shape, dtype=np.uint8)

    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        check_time(deadline)
        f = int(fold["fold"])
        hidden_total += fold["hidden"]
        print(f"Fold {f}: running 37-feature single-feature leakage canaries...", flush=True)
        checks, xb, xm, y = feature_canaries_dual(
            base,
            msdb,
            fold["visible"],
            fold,
            raw_names,
            list(MSDB_FEATURE_NAMES),
            SEED + f,
            deadline,
        )
        canaries_out.append({"fold": f, "features": checks})
        fold_gate_scales = fit_curvilinear_gate_scales(xm)
        xc = np.concatenate([xb[:, raw_keep], xm], axis=1)
        del xm

        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(DOT_BUDGET * active.sum() / valid.sum()))
        fold_pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        fold_pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        fold_samp_pos = int(np.count_nonzero(y > 0.5))
        fold_samp_neg = int(np.count_nonzero(y < 0.5))

        fold_result = {
            **fold["metadata"],
            "calibration_counts": {
                "train_population_positives": fold_pop_pos,
                "train_population_negatives": fold_pop_neg,
                "train_sample_positives": fold_samp_pos,
                "train_sample_negatives": fold_samp_neg,
            },
            "curvilinear_gate_scales": [float(v) for v in fold_gate_scales],
            "dot_budget_each_arm": count,
            "arms": {},
        }

        # Arm 1: core19 (exact 19 raw bands + HGB + r=3.0 Poisson-disk)
        check_time(deadline)
        m_core, med_core, scl_core = fit_core19_model(xb, y, seed=SEED + f)
        with threadpool_limits(limits=2):
            pred_core = predict_grid(m_core, base, med_core, scl_core, active)
        del m_core, xb
        emit_core = select_poisson_dots(pred_core, active, count)
        del pred_core
        sc_core = masked_dti_by_blocks(emit_core, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        del emit_core
        block_rows["core19"].extend(sc_core["spatial_blocks"])
        fold_result["arms"]["core19"] = {k: v for k, v in sc_core["pooled"].items() if k != "dti"}
        print(f"Fold {f}: core19 -> {count} active dots scored", flush=True)

        # Fit MSDB-1 v2 31-feature regularized HGB once on fold training pixels; apply Rayleigh gate; evaluate both emitters.
        check_time(deadline)
        m_msdb, med_msdb, scl_msdb = fit_msdb_model(xc, y, seed=SEED + f)
        del xc, y
        with threadpool_limits(limits=2):
            pred_msdb_raw = predict_dual_grid(m_msdb, base, msdb, raw_keep, med_msdb, scl_msdb, active)
        del m_msdb

        pred_msdb_cal = calibrate_case_control_probabilities(
            pred_msdb_raw,
            population_positives=fold_pop_pos,
            population_negatives=fold_pop_neg,
            sample_positives=fold_samp_pos,
            sample_negatives=fold_samp_neg,
        )
        del pred_msdb_raw
        fold_psi = compute_curvilinear_discontinuity_gate(msdb, fold_gate_scales, active)
        pred_msdb_gated = (pred_msdb_cal * fold_psi).astype(np.float32)
        del pred_msdb_cal, fold_psi

        # Arm 2: msdb_poisson (isolates gated MSDB surface gain under identical r=3.0 Poisson-disk)
        emit_mpois = select_poisson_dots(pred_msdb_gated, active, count)
        sc_mpois = masked_dti_by_blocks(
            emit_mpois, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128
        )
        del emit_mpois
        block_rows["msdb_poisson"].extend(sc_mpois["spatial_blocks"])
        fold_result["arms"]["msdb_poisson"] = {k: v for k, v in sc_mpois["pooled"].items() if k != "dti"}
        print(f"Fold {f}: msdb_poisson -> {count} active dots scored", flush=True)

        # Arm 3: msdb_edge (Bayes prevalence-calibrated x Rayleigh-gated 300 m submodular coverage)
        emit_medge = select_msdb_edge_dots(pred_msdb_gated, active, count)
        del pred_msdb_gated
        sc_medge = masked_dti_by_blocks(
            emit_medge, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128
        )
        del emit_medge
        block_rows["msdb_edge"].extend(sc_medge["spatial_blocks"])
        fold_result["arms"]["msdb_edge"] = {k: v for k, v in sc_medge["pooled"].items() if k != "dti"}
        print(f"Fold {f}: msdb_edge -> {count} active dots scored", flush=True)

        folds_out.append(fold_result)

    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("Each withheld catalogue pixel must be evaluated in exactly one fold")

    summary = spatial_bootstrap(block_rows, candidate="msdb_edge", replicates=2000, seed=3071)
    feature_ablation = spatial_bootstrap(
        {"core19": block_rows["core19"], "msdb_poisson": block_rows["msdb_poisson"]},
        candidate="msdb_poisson",
        replicates=2000,
        seed=3071,
    )["candidate_minus"]["core19"]

    alarms = [dict(fold=f["fold"], **row) for f in canaries_out for row in f["features"] if row["alarm_above_0_90"]]
    beats = all(delta["value"] > 0 and delta["ci95"][0] > 0 for delta in summary["candidate_minus"].values())
    scientific_pass = bool(beats and not alarms)
    novelty = summarize_novelty(surface_audit, dots_audit, "docs/research/msdb-piedmont")

    validation = validate_submission_file(generated, template).to_dict()
    with rasterio.open(generated) as ds, rasterio.open(template) as reference:
        output = ds.read(1)
        validator = {
            "status": "passed" if validation["passed"] else "failed",
            "no_nan_inside_footprint": bool(np.isfinite(output[valid]).all()),
            "values_in_0_1": bool(np.all((output[valid] >= 0.0) & (output[valid] <= 1.0))),
            "crs_match": ds.crs == reference.crs,
            "shape_match": ds.shape == reference.shape,
            "transform_match": ds.transform == reference.transform,
            "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
            "nan_nodata_outside_footprint": bool(np.isnan(output[~valid]).all()),
            "positive_catalogue_pixels": int(np.count_nonzero(output[labels] > 0)),
            "emitted_dots": int(np.count_nonzero(output[valid] > 0)),
            "organizer_acceptance_confirmed": False,
        }
    if not validation["passed"] or validator["positive_catalogue_pixels"] != 0:
        raise AssertionError("Shared format validator or exact catalogue mask gate failed")
    dump(REPORT / "validation.json", validation)

    elapsed_this = round(time.monotonic() - started_mono, 2)
    total_elapsed = round(previous_elapsed + elapsed_this, 2)
    raster_digest = sha(generated)
    results_payload = {
        "schema_version": 2,
        "experiment_spec": "msdb1v2",
        "summary": summary,
        "feature_only_ablation_msdb_poisson_minus_core19": feature_ablation,
        "folds": folds_out,
        "feature_canaries": canaries_out,
        "bootstrap_sufficient_statistics": block_rows,
        "full_fit_calibration": {
            "population_positives": n_pop_pos,
            "population_negatives": n_pop_neg,
            "sample_positives": n_samp_pos,
            "sample_negatives": n_samp_neg,
            "curvilinear_gate_scales": [float(v) for v in full_gate_scales],
        },
        "raster_sha256": raster_digest,
        "preregistration_sha256": prereg_sha,
        "preregistration_json_sha256": prereg_json_sha,
        "evaluator_version": EVALUATOR_VERSION,
        "protocol_version": SEGMENT_PROTOCOL_VERSION,
        "experimental_elapsed_seconds": total_elapsed,
        "this_execution_seconds": elapsed_this,
        "scientific_gate_passed": scientific_pass,
    }
    dump(REPORT / "results.json", results_payload)

    blockers = []
    if not scientific_pass:
        blockers.append("Candidate failed paired HOLDOUT-DTI improvement gate or feature leakage canary")
    blockers += [
        "Complete parallel-run raster/surface registry unavailable beyond nine-site snapshot (165 unique aligned files)",
        "No externally assigned lane paragraph supplied; Rank-1 MSDB-1 lane selected autonomously from four-hypothesis ranking",
        "Historical UNet checkpoints absent in repository: same-protocol historical-best neural rerun unavailable",
        "Organizer portal upload receipt not confirmable offline inside sandbox",
    ]

    registry_manifest = json.loads(registry_path.read_text())
    provisional_card = {
        "schema_version": 2,
        "experiment_spec": "msdb1v2",
        "run_id": run_name,
        "hypothesis": (
            "Concealed Great Basin piedmont splays, breached relay ramps, and shallow-cover basement step-overs "
            "produce aligned 100-300 m curvilinear discontinuities across detrended elevation, true potential-field "
            "magnetic tilt, reconstructed 2-D vector gravity gradients, basement cover ramps, and GeoDAWN radiometric "
            "total count; gating a stationary 31-feature HGB posterior by a fold-local Rayleigh curvilinear-discontinuity "
            "envelope and allocating dots via Prentice-Pyke Bayes-calibrated 300 m submodular coverage improves buffered "
            "whole-segment fault recovery over both raw-band Poisson-disk (`core19`) and MSDB Poisson-disk (`msdb_poisson`)."
        ),
        "mechanism": (
            "18 bounded-support (`<= 12.73 px < 17 px` guard) steerable Hessian tubularity/saddle, structure-tensor "
            "coherence, true Miller-Singh magnetic tilt, reconstructed (dg/dx, dg/dy) strike concordance, and thin-cover "
            "piedmont ramp features + 13 stationary local/tectonic raw bands in a regularized HGB + Prentice-Pyke Bayes "
            "prevalence calibration x Rayleigh curvilinear discontinuity gate + exact 300 m `edge_select` submodular coverage."
        ),
        "non_fault_mimic": (
            "Volcanic lava-flow fronts, non-tectonic intrusive pluton contacts, paleoshoreline/playa benches, "
            "and lithologically contrasting adjacent bajada fan catchments"
        ),
        "lane": "MSDB-1v2 curvilinear discontinuity-gated piedmont habitat + Bayes-calibrated 300 m EDGE",
        "experiments_run": experiment_ordinal,
        "previous_execution_receipt": prereg_spec.get("previous_experiment_receipt"),
        "fixed_arms": list(arms),
        "candidate_arm": "msdb_edge",
        "comparator_arms": ["core19", "msdb_poisson"],
        "experiment_cap": 3,
        "experimental_elapsed_seconds": total_elapsed,
        "time_cap_hours": 2,
        "this_execution_seconds": elapsed_this,
        "corrective_execution": False,
        "physical_support_px": SUPPORT_PX,
        "holdout_guard_px": GUARD_PX,
        "confirmation_scope": "Single preregistered 4-fold spatially buffered whole-component holdout execution",
        "holdout": {
            **summary["arms"]["msdb_edge"],
            "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "scope": "buffered whole-segment catalogue-recovery proxy; NOT organizer performance",
            "comparators": {name: summary["arms"][name] for name in ("core19", "msdb_poisson")},
            "candidate_minus": summary["candidate_minus"],
            "feature_only_ablation_msdb_poisson_minus_core19": feature_ablation,
            "bootstrap": summary["bootstrap"],
        },
        "feature_canaries": {
            "features_per_fold": len(canaries_out[0]["features"]),
            "folds": 4,
            "alarm_count": len(alarms),
            "alarms": alarms,
            "receipt": "docs/research/msdb-piedmont/results.json",
        },
        "registry": novelty,
        "raster_sha256": raster_digest,
        "validator_output": validator,
        "submission_name": run_name,
        "note": note,
        "published_tiff": f"docs/downloads/{generated.name}",
        "download_ok": True,
        "submission_approved": False,
        "slot_selected": False,
        "verdict": "negative",
        "scientific_gate_passed": scientific_pass,
        "verdict_scope": "machine-adjudicated research readiness gates; no competition performance projection",
        "blockers": blockers,
        "preregistration_sha256": prereg_sha,
        "preregistration_json_sha256": prereg_json_sha,
        "dataset_signature": manifest["dataset_signature"],
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    readiness = assess(
        provisional_card,
        results_payload,
        format_passed=validation["passed"],
        hash_matches=True,
        surface_audit=surface_audit,
        dots_audit=dots_audit,
        registry=registry_manifest,
        preregistration=prereg_spec,
    )
    provisional_card["verdict"] = readiness["research_verdict"]
    provisional_card["download_ok"] = readiness["download_ok"]

    dest = ROOT / "docs/downloads" / generated.name
    shutil.copyfile(generated, dest)
    manifest_output.update(
        {
            "submission_approved": False,
            "download_ok": readiness["download_ok"],
            "submission_recommendation": False,
            "note": note,
            "scientific_gate_passed": scientific_pass,
            "run_card": "docs/research/msdb-piedmont/run-card.json",
            "lineage": "New fit of MSDB-1; zero previous submission values used as inputs or predictions",
            "method": TRANSFORM_VERSION,
            "preregistration_sha256": prereg_sha,
            "preregistration_json_sha256": prereg_json_sha,
            "dataset_signature": manifest["dataset_signature"],
        }
    )
    dump(dest.with_suffix(".json"), manifest_output)
    dump(REPORT / "run-card.json", provisional_card)
    dump(REPORT / "readiness.json", readiness)
    print(json.dumps(provisional_card, indent=2), flush=True)
    return provisional_card


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=int, default=5400)
    args = parser.parse_args()
    if not 1 <= args.max_seconds <= 7200:
        parser.error("max-seconds must be in [1, 7200]")
    run(args.max_seconds)


if __name__ == "__main__":
    main()
