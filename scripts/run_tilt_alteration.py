#!/usr/bin/env python3
"""Execute frozen lane G30-TAD (E1 holdout + canaries, E2 OOF collar diagnostic, E3 190-file novelty & TIFF validation).

Strictly bounded to 3 experiments and <= 7,200 s. Reuses shared holdout, novelty,
and submission modules without modifying frozen TDX-1 / TDX-C2 / G30-LSM artifacts.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from gemsdoe30.experiments import CORE_FEATURES, LayerStack
from gemsdoe30.holdout import (
    EVALUATOR_VERSION,
    SEGMENT_PROTOCOL_VERSION,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    spatial_bootstrap,
    spatial_segment_folds,
    split_components,
)
from gemsdoe30.submission import validate_submission_file, write_submission_file
from gemsdoe30.tilt_alteration import (
    BAND_IDX,
    STATIC_DERIVED_NAMES,
    SUBSURFACE_FEATURES,
    SUPPORT_PX,
    TAD_FEATURES,
    TRANSFORM_VERSION,
    assemble_tad_layers,
    build_hydrothermal_impulse,
    calibrate_oof_by_training_quantiles,
    compute_static_derived_layers,
    decensored_collar_select,
    exact_operator_support_px,
    fit_apply_rad_kd,
)
from scripts.check_novelty import audit as novelty_audit
from scripts.feature_value_holdout import predict_grid, sample_training_pixels
from scripts.run_texture_displacement import check_time, dump, fit_model, select_dots, sha
from scripts.verify_prepared_cache import verify as verify_prepared_cache

REPORT = ROOT / "docs/research/tilt-alteration-discontinuity"
CACHE = ROOT / "data/processed/tilt-alteration-discontinuity"
RUN = ROOT / "outputs/tilt-alteration-discontinuity"

SEED = 3070
PRIMARY_BUDGET = 44090
PRODUCTION_DOTS = 38000
RECORDED_TDX1_CORE19 = 0.13982063017811727

ARMS = ("random_dispersed", "subsurface16", "core19", "tilt_alt24")

# 36 unique features across core19 (0..18) + 16 static derived (19..34) + 1 fold-safe rad_kd (35).
UNIQUE_FEATURE_NAMES = CORE_FEATURES + STATIC_DERIVED_NAMES + ("rad_kd_potassic_resid",)

EXTERNAL_SOURCES = {
    "lidar_scarp": ROOT / "data/raw/external/lidar_scarp_features_u8.tif",
    "geodawn_rad": ROOT / "data/raw/external/geodawn_rad_u8.tif",
    "geodawn_ext": ROOT / "data/raw/external/geodawn_extensions_u8.tif",
    "wellspring_csv": ROOT / "data/raw/external/gdr_wellspring_in_footprint.csv",
    "gdr_paleo": ROOT / "data/external/derived_gdr_paleo_100m_u8.tif",
    "gdr_2m_probes": ROOT / "data/external/derived_gdr_2m_probes_100m_u8.tif",
}


def load_static_cache(base: np.ndarray, valid: np.ndarray, manifest: dict) -> tuple[dict[str, np.ndarray], np.ndarray, np.ndarray]:
    """Build or verify memmapped float32 static derived layers + return uint8 K and Th bands."""
    CACHE.mkdir(parents=True, exist_ok=True)
    ext_hashes = {key: sha(path) for key, path in EXTERNAL_SOURCES.items()}
    measured_support = exact_operator_support_px(grid_size=49)
    if measured_support > SUPPORT_PX:
        raise ValueError(f"operator support {measured_support} exceeds guard {SUPPORT_PX}")

    signature = {
        "transform_version": TRANSFORM_VERSION,
        "transform_code_sha256": sha(ROOT / "src/gemsdoe30/tilt_alteration.py"),
        "dataset_signature": manifest["dataset_signature"],
        "external_sha256": ext_hashes,
    }
    receipt_path = CACHE / "receipt.json"

    with rasterio.open(EXTERNAL_SOURCES["geodawn_rad"]) as ds_rad:
        rad_u8 = ds_rad.read()
    rad_k_u8 = np.ascontiguousarray(rad_u8[0])
    rad_th_u8 = np.ascontiguousarray(rad_u8[1])

    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("signature") != signature:
            raise ValueError("stale G30-TAD feature cache; remove cache directory before rebuilding")
        for name in STATIC_DERIVED_NAMES:
            if sha(CACHE / f"{name}.npy") != receipt["sha256"][name]:
                raise ValueError(f"derived cache hash mismatch: {name}")
    else:
        print("Constructing 16 static translation-invariant G30-TAD layers...", flush=True)
        with rasterio.open(EXTERNAL_SOURCES["geodawn_ext"]) as ds_ext:
            ext_u8 = ds_ext.read()
        with rasterio.open(EXTERNAL_SOURCES["lidar_scarp"]) as ds_lid:
            lidar_u8 = ds_lid.read()
        with rasterio.open(EXTERNAL_SOURCES["gdr_paleo"]) as ds_pal:
            paleo_u8 = ds_pal.read(1)
        with rasterio.open(EXTERNAL_SOURCES["gdr_2m_probes"]) as ds_prb:
            probes_u8 = ds_prb.read(1)

        hydro_impulse, hydro_counts = build_hydrothermal_impulse(
            paleo_u8, probes_u8, EXTERNAL_SOURCES["wellspring_csv"], valid
        )
        del paleo_u8, probes_u8
        derived = compute_static_derived_layers(
            base,
            valid,
            rad_u8=rad_u8,
            ext_u8=ext_u8,
            lidar_u8=lidar_u8,
            hydro_impulse=hydro_impulse,
        )
        del ext_u8, lidar_u8, hydro_impulse
        for name, arr in derived.items():
            np.save(CACHE / f"{name}.npy", np.asarray(arr, dtype=np.float32))
        del derived
        gc.collect()

        receipt = {
            "signature": signature,
            "support_px": SUPPORT_PX,
            "measured_impulse_support_px": measured_support,
            "hydrothermal_source_counts": hydro_counts,
            "sha256": {name: sha(CACHE / f"{name}.npy") for name in STATIC_DERIVED_NAMES},
            "uses_catalogue_geometry": False,
            "uses_dist_known_fault_px": False,
            "uses_sgmc_or_qfaults_as_features": False,
            "uses_registry_values": False,
            "uses_template_values_as_features": False,
        }
        dump(receipt_path, receipt)

    del rad_u8
    gc.collect()
    dump(REPORT / "feature-receipt.json", receipt)
    memmaps = {name: np.load(CACHE / f"{name}.npy", mmap_mode="r") for name in STATIC_DERIVED_NAMES}
    return memmaps, rad_k_u8, rad_th_u8


def build_unified_layers(
    base: np.ndarray,
    static_derived: dict[str, np.ndarray],
    rad_kd_fold: np.ndarray,
) -> tuple[list[np.ndarray], dict[str, list[int]]]:
    """Return 36 unique layers and exact column index lists for core19, subsurface16, and tilt_alt24."""
    layers: list[np.ndarray] = [base[j] for j in range(19)]
    idx_map: dict[str, int] = {name: j for j, name in enumerate(CORE_FEATURES)}
    for name in STATIC_DERIVED_NAMES:
        idx_map[name] = len(layers)
        layers.append(static_derived[name])
    idx_map["rad_kd_potassic_resid"] = len(layers)
    layers.append(rad_kd_fold)

    if len(layers) != len(UNIQUE_FEATURE_NAMES):
        raise AssertionError("unified unique layer count mismatch")

    # Sanity-check exact identity against assemble_tad_layers ordering.
    expected_tad = assemble_tad_layers(base, static_derived, rad_kd_fold)
    tad_cols = [idx_map[name] for name in TAD_FEATURES]
    for col, exp_arr in zip(tad_cols, expected_tad):
        if layers[col].shape != exp_arr.shape or not np.shares_memory(layers[col], exp_arr):
            raise AssertionError("TAD column mapping mismatch")

    cols = {
        "core19": list(range(19)),
        "subsurface16": [idx_map[name] for name in SUBSURFACE_FEATURES],
        "tilt_alt24": tad_cols,
    }
    return layers, cols


def run_canaries(
    layers: list[np.ndarray],
    x_train: np.ndarray,
    y_train: np.ndarray,
    fold: dict,
    seed: int,
    deadline: float,
) -> list[dict]:
    """Evaluate all 36 unique features individually on held-out fold positives vs negatives."""
    active = fold["score_valid"] & ~fold["visible"]
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(active & ~fold["hidden"])
    negatives = np.random.default_rng(seed + 10000).choice(negatives, min(60000, negatives.size), replace=False)
    test_idx = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])

    rows = []
    for j, name in enumerate(UNIQUE_FEATURE_NAMES):
        check_time(deadline)
        vals = np.asarray(layers[j]).ravel()[test_idx]
        model, median, scale = fit_model(x_train[:, j : j + 1], y_train, seed=seed + j, iterations=32, leaves=7)
        vals_clean = np.where(np.isfinite(vals), vals, median[0])
        raw_auc = float(roc_auc_score(target, vals_clean))
        with threadpool_limits(limits=2):
            prob = model.predict_proba(((vals_clean - median[0]) / scale[0])[:, None])[:, 1]
        uni_auc = float(roc_auc_score(target, prob))
        bidir_max = float(max(raw_auc, 1.0 - raw_auc, uni_auc, 1.0 - uni_auc))
        rows.append(
            {
                "feature": name,
                "label": "LEAKAGE-CANARY AUC (not DTI)",
                "raw_auc": raw_auc,
                "raw_auc_either_direction": float(max(raw_auc, 1.0 - raw_auc)),
                "univariate_training_only_hgb_auc": uni_auc,
                "univariate_auc_either_direction": float(max(uni_auc, 1.0 - uni_auc)),
                "max_bidirectional_auc": bidir_max,
                "alarm_above_0_90": bool(bidir_max > 0.90),
                "heldout_positives": int(positives.size),
                "sampled_negatives": int(negatives.size),
            }
        )
    return rows


def write_zeros_outside_geotiff(
    binary_dots: np.ndarray,
    valid: np.ndarray,
    template_path: Path,
    output_path: Path,
    *,
    run_name: str,
    note: str,
) -> dict:
    """Write portal-range-hardened float32 GeoTIFF with 0.0 outside footprint and nodata=None."""
    if len(note) > 140:
        raise ValueError("note exceeds 140 chars")
    arr = np.where(valid, np.asarray(binary_dots, dtype=np.float32), np.float32(0.0)).astype(np.float32)
    if not np.isfinite(arr).all() or float(arr.min()) < 0.0 or float(arr.max()) > 1.0:
        raise ValueError("zeros-outside array violates whole-array [0, 1] finite contract")

    with rasterio.open(template_path) as tpl:
        profile = tpl.profile.copy()
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        nodata=None,
        compress="deflate",
        predictor=2,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_tif = output_path.with_suffix(".partial.tif")
    with rasterio.open(tmp_tif, "w", **profile) as dst:
        dst.write(arr, 1)
        dst.update_tags(RUN_NAME=run_name, SUBMISSION_NOTE=note, OUTSIDE_ENCODING="zeros_finite_0_1")
    tmp_tif.replace(output_path)

    digest = sha(output_path)
    sidecar = {
        "schema_version": 3,
        "run_name": run_name,
        "note": note,
        "note_length": len(note),
        "output_file": output_path.name,
        "output_path": str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path),
        "output_sha256": digest,
        "template_sha256": sha(template_path),
        "outside_encoding": "zeros",
        "outside_convention": "0.0 outside; all-finite [0, 1] across full 3730x3292 frame",
        "published_format_compliant": False,
        "whole_raster_range_diagnostic_passed": True,
        "all_cells_in_0_1": True,
        "nan_cells_anywhere": 0,
        "whole_array_in_0_1": True,
        "emitted_dots": int((arr[valid] > 0).sum()),
        "submission_approved": False,
        "slot_selected": False,
        "performance_status": "unscored; format validation is not a score",
    }
    dump(output_path.with_suffix(".json"), sidecar)
    return sidecar


def distance_profile(dots_bool: np.ndarray, d_cat: np.ndarray) -> dict[str, int]:
    pts = d_cat[dots_bool]
    return {
        "le_2px": int(np.sum(pts <= 2.0)),
        "gt_2_le_10px": int(np.sum((pts > 2.0) & (pts <= 10.0))),
        "gt_10_le_30px": int(np.sum((pts > 10.0) & (pts <= 30.0))),
        "gt_30px": int(np.sum(pts > 30.0)),
    }


def novelty_summary(report: dict) -> dict:
    rows = report["comparisons"]
    return {
        "decision": report["decision"],
        "registry_entries_compared": len(rows),
        "max_spearman": max((r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None), default=None),
        "max_fraction_within_3px": max(
            (r["candidate_fraction_within_3px_of_reference"] for r in rows if r["candidate_fraction_within_3px_of_reference"] is not None),
            default=None,
        ),
        "errors": report["errors"],
    }


def run(max_seconds: float) -> int:
    if (REPORT / "started.json").exists():
        raise ValueError("G30-TAD execution already started; refusing to overwrite frozen experiment receipts")

    started_mono = time.monotonic()
    deadline = started_mono + max_seconds
    RUN.mkdir(parents=True, exist_ok=True)

    prereg_sha = sha(REPORT / "preregistration.md")
    reg_sha = sha(REPORT / "registry.json")
    registration = json.loads((REPORT / "registration.json").read_text())
    if registration["registered_plan_sha256"] != prereg_sha or registration["registry_sha256"] != reg_sha:
        raise ValueError("preregistration or registry hash changed after registration.json lock")

    dump(
        REPORT / "started.json",
        {
            "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "lane": "G30-TAD",
            "experiment_cap": 3,
            "fixed_arms_e1": list(ARMS),
            "preregistration_sha256": prereg_sha,
            "registry_sha256": reg_sha,
            "script_sha256": sha(__file__),
            "transform_code_sha256": sha(ROOT / "src/gemsdoe30/tilt_alteration.py"),
            "max_experimental_seconds": max_seconds,
        },
    )

    cache_check = verify_prepared_cache(ROOT / "data/processed")
    dump(REPORT / "cache-verification.json", cache_check)
    base = np.load(ROOT / "data/processed/features_raw.npy", mmap_mode="r")
    valid = np.load(ROOT / "data/processed/valid.npy").astype(bool)
    labels = (np.load(ROOT / "data/processed/labels.npy", mmap_mode="r") > 0.5) & valid
    label_valid = np.load(ROOT / "data/processed/label_valid.npy", mmap_mode="r")
    if np.any(valid & ~label_valid):
        raise ValueError("unknown training labels inside footprint")
    manifest = json.loads((ROOT / "data/processed/manifest.json").read_text())
    for row in manifest["source_files"].values():
        if sha(ROOT / row["path"]) != row["sha256"]:
            raise ValueError("raw source identity mismatch")

    static_derived, rad_k_u8, rad_th_u8 = load_static_cache(base, valid, manifest)
    height, width = valid.shape

    # =========================================================================
    # EXPERIMENT E1: Buffered 4-quadrant whole-component holdout + 144 canaries
    # =========================================================================
    print("=== Experiment E1: Buffered spatial-segment holdout (v3) + 144 feature canaries ===", flush=True)
    blocks: dict[str, list[dict]] = {arm: [] for arm in ARMS}
    folds_meta: list[dict] = []
    all_canaries: list[dict] = []
    hidden_total = np.zeros((height, width), dtype=np.uint8)

    oof_tad24 = np.zeros((height, width), dtype=np.float32)
    oof_sub16 = np.zeros((height, width), dtype=np.float32)
    oof_core19 = np.zeros((height, width), dtype=np.float32)
    quad_covered = np.zeros((height, width), dtype=np.uint8)

    for fold in spatial_segment_folds(labels, valid, buffer_px=SUPPORT_PX):
        check_time(deadline)
        f = int(fold["fold"])
        hidden_total += fold["hidden"].astype(np.uint8)

        y0, y1 = (0, height // 2) if f < 2 else (height // 2, height)
        x0, x1 = (0, width // 2) if f % 2 == 0 else (width // 2, width)
        quad_mask = np.zeros((height, width), dtype=bool)
        quad_mask[y0:y1, x0:x1] = True
        quad_valid = valid & quad_mask
        quad_covered += quad_valid.astype(np.uint8)

        rad_kd_fold, kd_ols = fit_apply_rad_kd(rad_k_u8, rad_th_u8, valid, fold["train_mask"])
        layers, arm_cols = build_unified_layers(base, static_derived, rad_kd_fold)

        x_tr, y_tr = sample_training_pixels(
            LayerStack(layers), fold["visible"], fold["train_mask"], negatives_per_positive=6, seed=SEED + f
        )
        print(f"Fold {f}: running 36 single-feature leakage canaries...", flush=True)
        fold_canaries = run_canaries(layers, x_tr, y_tr, fold, SEED + f, deadline)
        all_canaries.append({"fold": f, "features": fold_canaries})

        active = fold["score_valid"] & ~fold["visible"]
        eval_mask = active | quad_valid | fold["train_mask"]
        dot_count = int(round(PRIMARY_BUDGET * active.sum() / valid.sum()))
        fold_row = {**fold["metadata"], "rad_kd_ols": kd_ols, "dot_budget_each_arm": dot_count, "arms": {}}

        # Arm 1: random_dispersed
        rng_rand = np.random.default_rng(4070 + f)
        rand_surf = rng_rand.random((height, width), dtype=np.float32)
        rand_dots = select_dots(rand_surf, active, dot_count)
        scored_rand = masked_dti_by_blocks(rand_dots, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        blocks["random_dispersed"].extend(scored_rand["spatial_blocks"])
        fold_row["arms"]["random_dispersed"] = scored_rand["pooled"]
        del rand_surf, rand_dots

        # Learned arms: subsurface16, core19, tilt_alt24
        for arm_name, oof_buf in (("subsurface16", oof_sub16), ("core19", oof_core19), ("tilt_alt24", oof_tad24)):
            check_time(deadline)
            cols = arm_cols[arm_name]
            model, median, scale = fit_model(x_tr[:, cols], y_tr, seed=SEED + f)
            with threadpool_limits(limits=2):
                pred = predict_grid(model, LayerStack([layers[c] for c in cols]), median, scale, eval_mask)
            cal_quad = calibrate_oof_by_training_quantiles(pred, fold["train_mask"], quad_valid, knots=1001)
            oof_buf[quad_valid] = cal_quad[quad_valid]
            emitted = select_dots(pred, active, dot_count)
            scored = masked_dti_by_blocks(emitted, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
            blocks[arm_name].extend(scored["spatial_blocks"])
            fold_row["arms"][arm_name] = scored["pooled"]
            print(f"Fold {f}: {arm_name:14s} fold-DTI={scored['pooled']['dti']:.5f} ({dot_count} dots)", flush=True)
            del pred, cal_quad, emitted, model

        folds_meta.append(fold_row)
        del rad_kd_fold, layers, x_tr, y_tr
        gc.collect()

    if not np.array_equal(hidden_total, labels.astype(np.uint8)):
        raise AssertionError("each withheld positive must occur in exactly one fold")
    if not np.array_equal(quad_covered, valid.astype(np.uint8)):
        raise AssertionError("stitched OOF quadrants must partition valid footprint exactly once")

    summary_e1 = spatial_bootstrap(blocks, candidate="tilt_alt24", replicates=2000, seed=3071)
    core19_val = float(summary_e1["arms"]["core19"]["value"])
    if not math.isclose(core19_val, RECORDED_TDX1_CORE19, abs_tol=1e-9, rel_tol=0.0):
        raise ValueError(f"core19 comparator {core19_val:.12f} failed to reproduce recorded TDX-1 {RECORDED_TDX1_CORE19:.12f}")

    canary_alarms = [
        {"fold": fc["fold"], **r}
        for fc in all_canaries
        for r in fc["features"]
        if r["alarm_above_0_90"]
    ]
    max_canary_auc = max(r["max_bidirectional_auc"] for fc in all_canaries for r in fc["features"])
    primary_wins = all(summary_e1["candidate_minus"][comp]["ci95"][0] > 0.0 for comp in ("random_dispersed", "subsurface16", "core19"))
    e1_gate_passed = (len(canary_alarms) == 0) and bool(primary_wins)

    print("E1 Summary:", json.dumps(summary_e1["arms"], indent=2), flush=True)
    print("E1 Paired Deltas:", json.dumps(summary_e1["candidate_minus"], indent=2), flush=True)
    print(f"E1 Primary Gate Passed: {e1_gate_passed} (max canary AUC={max_canary_auc:.4f})", flush=True)

    dump(REPORT / "bootstrap-blocks-e1.json", {"schema_version": 1, "blocks": blocks})
    results_e1 = {
        "schema_version": 1,
        "experiment_id": "E1",
        "preregistration_sha256": prereg_sha,
        "evaluator_version": EVALUATOR_VERSION,
        "protocol_version": SEGMENT_PROTOCOL_VERSION,
        "recorded_tdx1_core19_value": RECORDED_TDX1_CORE19,
        "core19_exact_match": True,
        "summary": summary_e1,
        "folds": folds_meta,
        "feature_canaries": all_canaries,
        "max_canary_bidirectional_auc": max_canary_auc,
        "canary_alarms": canary_alarms,
        "primary_holdout_gate_passed": e1_gate_passed,
    }
    dump(REPORT / "results-e1.json", results_e1)

    # Round-trip save and bit-exact check for OOF surfaces (IR-30-084 guard).
    oof_path = RUN / "oof_tad24.npy"
    np.save(oof_path, oof_tad24)
    reloaded_oof = np.load(oof_path)
    if not np.array_equal(oof_tad24, reloaded_oof):
        raise ValueError("disk page round-trip mismatch on oof_tad24.npy")
    del reloaded_oof

    # =========================================================================
    # EXPERIMENT E2: OOF Collar-Decensored Emission Diagnostic
    # =========================================================================
    print("=== Experiment E2: OOF observability-decensored collar diagnostic ===", flush=True)
    check_time(deadline)
    hid_inter, vis_inter, _ = split_components(labels, seed=42)
    hid_inter = np.asarray(hid_inter, dtype=bool) & valid
    vis_inter = np.asarray(vis_inter, dtype=bool) & valid
    inter_budget = int(round(PRODUCTION_DOTS * (~vis_inter & valid).sum() / valid.sum()))

    dots_inter_tad, strata_inter_tad = decensored_collar_select(oof_tad24, valid, vis_inter, total_dots=inter_budget)
    dots_inter_sub, _ = decensored_collar_select(oof_sub16, valid, vis_inter, total_dots=inter_budget)
    dots_inter_rand, _ = decensored_collar_select(
        np.random.default_rng(5070).random((height, width), dtype=np.float32), valid, vis_inter, total_dots=inter_budget
    )
    inter_blocks = {
        "tilt_alt24_oof_p1": masked_dti_by_blocks(dots_inter_tad, hid_inter, vis_inter, valid, block_size_px=128)["spatial_blocks"],
        "subsurface16_oof_p1": masked_dti_by_blocks(dots_inter_sub, hid_inter, vis_inter, valid, block_size_px=128)["spatial_blocks"],
        "random_p1": masked_dti_by_blocks(dots_inter_rand, hid_inter, vis_inter, valid, block_size_px=128)["spatial_blocks"],
    }
    inter_summary = spatial_bootstrap(inter_blocks, candidate="tilt_alt24_oof_p1", replicates=2000, seed=3071)
    del dots_inter_tad, dots_inter_sub, dots_inter_rand

    # Full-catalogue diagnostic comparison on off-catalogue SGMC-new (>300 m from labels; IR-30-081 caveat).
    d_cat = distance_transform_edt(~labels)
    elig_d2 = valid & (d_cat > 2.0)
    dots_p0 = select_dots(oof_tad24, elig_d2, PRODUCTION_DOTS)
    dots_p1, strata_p1 = decensored_collar_select(oof_tad24, valid, labels, total_dots=PRODUCTION_DOTS)
    dots_core_p0 = select_dots(oof_core19, elig_d2, PRODUCTION_DOTS)

    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds_sgmc:
        sgmc_raw = (ds_sgmc.read(1) > 0) & valid
    sgmc_new = sgmc_raw & (d_cat > 3.0)
    sgmc_fpw = fp_weight_field(sgmc_new, labels)

    sgmc_scores = {}
    for key, arr in (
        ("tilt_alt24_oof_p1_decensored", dots_p1),
        ("tilt_alt24_oof_p0_plain_d2", dots_p0),
        ("core19_oof_p0_plain_d2", dots_core_p0),
    ):
        sc = masked_dti(np.where(valid, arr, 0.0), sgmc_new, labels, fp_weight=sgmc_fpw)
        sgmc_scores[key] = {
            "label": "SGMC-NEW-OFFCAT-DIAGNOSTIC-DTI (not leaderboard proxy; IR-30-081)",
            "dti": float(sc["dti"]),
            "tp_weight": float(sc["tp_weight"]),
            "fp_weight": float(sc["fp_weight"]),
            "truth_pixels": int(sgmc_new.sum()),
            "emitted_dots": int((arr[valid] > 0).sum()),
        }
    del sgmc_fpw

    prof_p0 = distance_profile(dots_p0 > 0, d_cat)
    prof_p1 = distance_profile(dots_p1 > 0, d_cat)
    del dots_p0, dots_core_p0, sgmc_raw, sgmc_new

    results_e2 = {
        "schema_version": 1,
        "experiment_id": "E2",
        "preregistration_sha256": prereg_sha,
        "precommitted_production_policy": "decensored_30_40_30 (S_oof + P1, 38,000 dots, d_cat > 2 px, 3.0 px spacing)",
        "interleaved_component_oof_holdout": {
            "seed": 42,
            "dot_budget": inter_budget,
            "realized_strata_tilt_alt24": strata_inter_tad,
            "summary": inter_summary,
        },
        "sgmc_new_offcatalogue_diagnostic": sgmc_scores,
        "full_grid_distance_profiles_38000": {
            "p0_plain_d2": prof_p0,
            "p1_decensored_30_40_30": prof_p1,
            "p1_realized_strata": strata_p1,
        },
    }
    dump(REPORT / "results-e2.json", results_e2)
    print("E2 Distance profile P0 vs P1:", prof_p0, prof_p1, flush=True)
    print("E2 SGMC-new diagnostic:", json.dumps(sgmc_scores, indent=2), flush=True)

    # =========================================================================
    # EXPERIMENT E3: 190-file Surface & Dot Novelty Gate + GeoTIFF Validation
    # =========================================================================
    print("=== Experiment E3: 190-raster pre-placement surface & post-placement dot novelty audit ===", flush=True)
    check_time(deadline)
    template_path = ROOT / "data/raw/sample_submission.tif"
    registry_path = REPORT / "registry.json"

    surface_tif = RUN / "tad24-oof-surface.tif"
    write_submission_file(
        oof_tad24,
        template_path,
        surface_tif,
        run_name="gems30-TAD24-oof-surface",
        note="Continuous G30-TAD cross-quadrant OOF surface; research check before dot placement.",
    )
    surface_audit = novelty_audit(surface_tif, template_path, registry_path, "surface")
    dump(REPORT / "novelty-surface.json", surface_audit)
    surf_sum = novelty_summary(surface_audit)
    print("E3 Surface novelty summary:", surf_sum, flush=True)

    inner_bytes = np.ascontiguousarray(dots_p1[valid].astype(np.float32)).tobytes()
    values_id = hashlib.sha256(inner_bytes).hexdigest()
    run_id = f"gems30-TAD24-decensored-38000-20261025-{values_id[:12]}"

    cand_nan_run = RUN / f"{run_id}-nan.tif"
    cand_zeros_run = RUN / f"{run_id}-zeros.tif"

    # Provisional research-safe note; upgraded only if every gate passes.
    provisional_note = "G30-TAD tilt-depth+Kd-alt+dip-slip OOF 38k decensored; automated gates evaluated."
    write_submission_file(dots_p1, template_path, cand_nan_run, run_name=run_id, note=provisional_note)
    dots_audit = novelty_audit(cand_nan_run, template_path, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    dots_sum = novelty_summary(dots_audit)
    print("E3 Dots novelty summary:", dots_sum, flush=True)

    check_time(deadline)
    prior_e1_seconds = 301.90 if (REPORT / "results-e1.first-execution.json").exists() else 0.0
    this_exec_s = float(time.monotonic() - started_mono)
    elapsed_s = float(prior_e1_seconds + this_exec_s)

    surf_novelty_ok = (
        not surf_sum["errors"]
        and surf_sum["max_spearman"] is not None
        and surf_sum["max_spearman"] <= 0.90
        and surface_audit["decision"] != "duplicate-stop"
    )
    dots_novelty_ok = (
        not dots_sum["errors"]
        and dots_sum["max_spearman"] is not None
        and dots_sum["max_spearman"] <= 0.90
        and dots_sum["max_fraction_within_3px"] is not None
        and dots_sum["max_fraction_within_3px"] <= 0.70
        and dots_audit["decision"] != "duplicate-stop"
    )

    if not (surf_novelty_ok and dots_novelty_ok):
        dump(
            REPORT / "duplicate-stop.json",
            {
                "run_id": run_id,
                "surface_novelty": surf_sum,
                "dots_novelty": dots_sum,
                "decision": "duplicate-stop",
                "published_tiff": None,
                "submission_approved": False,
            },
        )
        card = {
            "schema_version": 2,
            "lane": "G30-TAD",
            "run_id": run_id,
            "hypothesis": "Translation-invariant tilt-depth, Th-normalized K-Th-U alteration, and dip-slip scarp polarity with 30/40/30 decensored collar emission improves cross-quadrant fault recovery without range-front collision.",
            "mechanism": "24-input translation-invariant HGB cross-quadrant OOF surface + 30/40/30 collar-decensored 38,000 binary dots (d_cat > 2 px, 3 px spacing).",
            "non_fault_mimic": "Sub-vertical tilted welded ash-flow tuff / caldera ring-fracture lithologic contacts with vapor-phase potassic enrichment and differential caprock cuesta erosion.",
            "experiments_run": 3,
            "experiment_cap": 3,
            "experimental_elapsed_seconds": elapsed_s,
            "time_cap_hours": 2,
            "physical_support_px": SUPPORT_PX,
            "preregistration_sha256": prereg_sha,
            "registry_sha256": reg_sha,
            "dataset_signature": cache_check["dataset_signature"],
            "holdout": summary_e1,
            "feature_canaries": {
                "unique_features_per_fold": len(UNIQUE_FEATURE_NAMES),
                "folds": 4,
                "total_checks": 4 * len(UNIQUE_FEATURE_NAMES),
                "max_bidirectional_auc": max_canary_auc,
                "alarm_count": len(canary_alarms),
                "alarms": canary_alarms,
            },
            "registry": {"surface": surf_sum, "dots": dots_sum},
            "raster_sha256": sha(cand_nan_run),
            "published_tiff": None,
            "validator_output": validate_submission_file(cand_nan_run, template_path).to_dict(),
            "submission_name": run_id,
            "note": "G30-TAD duplicate-stop; quarantined in outputs/, DO NOT SUBMIT.",
            "verdict": "duplicate-stop",
            "ok_to_submit": False,
            "download_ok": False,
            "slot_selected": False,
        }
        dump(REPORT / "run-card.json", card)
        print("STOPPED: novelty duplicate-stop triggered.", flush=True)
        return 0

    budget_ok = elapsed_s <= 7200.0
    promote_all = bool(e1_gate_passed and surf_novelty_ok and dots_novelty_ok and budget_ok)
    verdict = "promote" if promote_all else "negative"
    final_note = (
        f"G30-TAD OOF tilt-depth+Kd-alt+dip-slip 38k decensored; HOLDOUT-DTI {summary_e1['arms']['tilt_alt24']['value']:.4f} vs core19 {core19_val:.4f}."
        if promote_all
        else f"G30-TAD OOF tilt-depth+Kd-alt+dip-slip 38k; negative gate ({summary_e1['arms']['tilt_alt24']['value']:.4f}); DO NOT SUBMIT."
    )
    if len(final_note) > 140:
        raise ValueError(f"final_note length {len(final_note)} > 140")

    pub_zeros = ROOT / "docs/downloads" / f"{run_id}-zeros.tif"
    pub_nan = ROOT / "docs/downloads" / f"{run_id}-nan.tif"

    sidecar_zeros = write_zeros_outside_geotiff(
        dots_p1, valid, template_path, pub_zeros, run_name=f"{run_id}-zeros", note=final_note
    )
    sidecar_nan = write_submission_file(
        dots_p1, template_path, pub_nan, run_name=f"{run_id}-nan", note=final_note
    )
    nan_sidecar_doc = json.loads(pub_nan.with_suffix(".json").read_text())
    nan_sidecar_doc["submission_approved"] = False
    nan_sidecar_doc["slot_selected"] = False
    dump(pub_nan.with_suffix(".json"), nan_sidecar_doc)
    # Keep identical copies in RUN for local inspection symmetry.
    shutil.copy2(pub_zeros, cand_zeros_run)
    shutil.copy2(pub_nan, cand_nan_run)

    val_nan = validate_submission_file(pub_nan, template_path).to_dict()
    with rasterio.open(template_path) as ds_tpl:
        tpl_crs = ds_tpl.crs
        tpl_transform = ds_tpl.transform
    with rasterio.open(pub_zeros) as ds_z:
        arr_z = ds_z.read(1)
        same_tf = bool(ds_z.transform == tpl_transform)
        same_crs = bool(ds_z.crs == tpl_crs)
        zeros_valid = {
            "passed": bool(
                np.isfinite(arr_z).all()
                and float(arr_z.min()) >= 0.0
                and float(arr_z.max()) <= 1.0
                and np.isin(arr_z[valid], (0.0, 1.0)).all()
                and np.all(arr_z[~valid] == 0.0)
                and int((arr_z[valid] > 0).sum()) == PRODUCTION_DOTS
                and int((arr_z[labels] > 0).sum()) == 0
                and int(prof_p1["le_2px"]) == 0
                and same_crs
                and same_tf
                and ds_z.shape == (height, width)
                and ds_z.count == 1
                and ds_z.dtypes == ("float32",)
            ),
            "whole_array_finite_in_0_1": True,
            "no_nan_inside_footprint": bool(np.isfinite(arr_z[valid]).all()),
            "values_in_0_1": bool(float(arr_z.min()) >= 0.0 and float(arr_z.max()) <= 1.0),
            "crs_match": same_crs,
            "shape_match": bool(ds_z.shape == (height, width)),
            "transform_match": same_tf,
            "single_float32_band": bool(ds_z.count == 1 and ds_z.dtypes == ("float32",)),
            "outside_encoding": "zeros_finite_0_1",
            "emitted_dots": int((arr_z[valid] > 0).sum()),
            "positive_catalogue_pixels": int((arr_z[labels] > 0).sum()),
            "dots_within_2px_of_catalogue": int(prof_p1["le_2px"]),
        }
    if not val_nan["passed"] or not zeros_valid["passed"]:
        raise ValueError("published GeoTIFF failed automated post-write format validation")

    # Verify post-write dot novelty identity matches published -nan.tif bytes inside footprint.
    dots_pub_audit = novelty_audit(pub_nan, template_path, registry_path, "dots")
    dump(REPORT / "novelty-dots.json", dots_pub_audit)
    dots_sum = novelty_summary(dots_pub_audit)

    top_overlap_row = max(
        (r for r in dots_pub_audit["comparisons"] if r["candidate_fraction_within_3px_of_reference"] is not None),
        key=lambda r: r["candidate_fraction_within_3px_of_reference"],
    )
    top_surf_row = max(
        (r for r in surface_audit["comparisons"] if r["spearman_full_footprint"] is not None),
        key=lambda r: r["spearman_full_footprint"],
    )

    validation_receipt = {
        "primary_zeros_outside": {"path": str(pub_zeros.relative_to(ROOT)), "sha256": sidecar_zeros["output_sha256"], **zeros_valid},
        "companion_nan_outside": {"path": str(pub_nan.relative_to(ROOT)), "sha256": sidecar_nan["output_sha256"], **val_nan},
        "values_identity_sha256": values_id,
    }
    dump(REPORT / "validation.json", validation_receipt)

    card = {
        "schema_version": 2,
        "lane": "G30-TAD",
        "experiment_spec": "tad24",
        "run_id": run_id,
        "hypothesis": "Removing the 12 regional coordinate-proxy bands of core19 and replacing them with 17 local potential-field tilt-depth, 150 m upward-continuation, fold-safe Th-normalized K-Th-U alteration, clay-cap conductance edge, 1 m LiDAR dip-slip polarity, basement strike-lock, and hydrothermal sinter/probe/geothermometer features (tilt_alt24) improves cross-quadrant fault recovery (HOLDOUT-DTI) over core19, subsurface16, and random_dispersed, while 30/40/30 collar-decensored OOF emission avoids <1 km range-front crowding.",
        "mechanism": "4-fold buffered spatial-quadrant HGB out-of-fold probability surface (quantile-calibrated strictly on training folds) over 24 translation-invariant multi-physics discontinuity features, emitted as 38,000 binary {0,1} dots (3.0 px Euclidean Poisson-disk spacing, 0% at d_cat <= 2 px, 30% in 2-10 px, 40% in 10-30 px, 30% in >30 px).",
        "non_fault_mimic": "Sub-vertical tilted welded ash-flow tuff / caldera ring-fracture lithologic contacts with primary vapor-phase potassic crystallization and differential caprock cuesta erosion.",
        "experiments_run": 3,
        "experiment_cap": 3,
        "experimental_elapsed_seconds": elapsed_s,
        "time_cap_hours": 2,
        "physical_support_px": SUPPORT_PX,
        "measured_impulse_support_px": exact_operator_support_px(grid_size=49),
        "preregistration_sha256": prereg_sha,
        "registry_sha256": reg_sha,
        "dataset_signature": cache_check["dataset_signature"],
        "holdout": {
            "label": "HOLDOUT-DTI",
            **summary_e1["arms"]["tilt_alt24"],
            "evaluator_version": EVALUATOR_VERSION,
            "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "scope": "buffered 4-quadrant whole-component catalogue-recovery proxy; NOT organizer performance",
            "comparators": {k: summary_e1["arms"][k] for k in ("core19", "subsurface16", "random_dispersed")},
            "candidate_minus": summary_e1["candidate_minus"],
            "bootstrap": summary_e1["bootstrap"],
        },
        "e2_diagnostics": results_e2,
        "feature_canaries": {
            "unique_features_per_fold": len(UNIQUE_FEATURE_NAMES),
            "folds": 4,
            "total_checks": 4 * len(UNIQUE_FEATURE_NAMES),
            "max_bidirectional_auc": max_canary_auc,
            "alarm_count": len(canary_alarms),
            "alarms": canary_alarms,
            "receipt": "docs/research/tilt-alteration-discontinuity/results-e1.json",
        },
        "registry": {
            "pinned_snapshot": "docs/research/tilt-alteration-discontinuity/registry.json",
            "surface": {
                **surf_sum,
                "closest_reference": top_surf_row["reference"],
                "receipt": "docs/research/tilt-alteration-discontinuity/novelty-surface.json",
            },
            "dots": {
                **dots_sum,
                "closest_reference": top_overlap_row["reference"],
                "receipt": "docs/research/tilt-alteration-discontinuity/novelty-dots.json",
            },
        },
        "files": {
            "primary_zeros_outside": {
                "path": str(pub_zeros.relative_to(ROOT)),
                "sha256": sidecar_zeros["output_sha256"],
                "outside_encoding": "zeros",
            },
            "companion_nan_outside": {
                "path": str(pub_nan.relative_to(ROOT)),
                "sha256": sidecar_nan["output_sha256"],
                "outside_encoding": "nan",
            },
            "values_identity_sha256": values_id,
        },
        "published_tiff": str(pub_zeros.relative_to(ROOT)),
        "companion_nan_tiff": str(pub_nan.relative_to(ROOT)),
        "raster_sha256": sidecar_zeros["output_sha256"],
        "companion_nan_sha256": sidecar_nan["output_sha256"],
        "validator_output": {
            "status": "passed",
            "primary_zeros_outside_passed": zeros_valid["passed"],
            "companion_nan_outside_passed": val_nan["passed"],
            "whole_array_finite_in_0_1": True,
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_match": True,
            "shape_match": True,
            "transform_match": True,
            "single_float32_band": True,
            "emitted_dots": PRODUCTION_DOTS,
            "positive_catalogue_pixels": 0,
            "dots_within_2px_of_catalogue": 0,
        },
        "dots_by_catalogue_distance_px": prof_p1,
        "submission_name": f"{run_id}-zeros",
        "note": final_note,
        "download_ok": True,
        "ok_to_submit": promote_all,
        "submission_approved": False,
        "slot_selected": False,
        "verdict": verdict,
        "scientific_gate_passed": e1_gate_passed,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    dump(REPORT / "run-card.json", card)
    print(f"=== G30-TAD finished in {elapsed_s:.1f}s | verdict={verdict} | ok_to_submit={promote_all} ===", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-seconds", type=float, default=6600.0)
    args = parser.parse_args()
    try:
        return run(args.max_seconds)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
