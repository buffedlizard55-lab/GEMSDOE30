#!/usr/bin/env python3
"""Execute preregistered Lane CSR-1 (Cover-Compensated Subsurface Laplace/Poisson & 1.8 km Radon + 1D Dispersed EDGE).

Strict protocol guarantees:
- Refuses unscheduled re-execution if ``started.json`` already exists.
- Enforces hard budget caps: <= 3 experiments, <= 7,200 s wall-clock.
- Verifies prepared cache and external GeoDAWN / 3DEP SHA-256 pins before fitting.
- Runs 81 single-feature bidirectional leakage canaries across all 4 buffered folds.
- Evaluates count-matched ``core19_edge``, ``msdb_edge``, ``csr_dense_edge``, and
  ``csr_dispersed`` on shared ``gemsdoe30.holdout`` (v3 geographic block bootstrap).
- Audits both pre-placement continuous surface and final emitted dots against all
  357 aligned 9-site rasters (+ 2 formally classified exclusions) in ``registry.json``.
- Emits a machine-validated whole-array-finite [0, 1] GeoTIFF via ``gemsdoe30.submission``
  and records canonical ``results.json``, ``readiness.json``, and ``run-card.json``.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from check_novelty import audit as audit_novelty  # noqa: E402
from feature_value_holdout import fit_standardiser, sample_training_pixels  # noqa: E402
from gemsdoe30.csr_discontinuity import (  # noqa: E402
    CSR_ALL_DERIVED_NAMES,
    CSR_FULL_RAW_INDICES,
    CSR_STATIC_FEATURE_NAMES,
    CSR_SUB_RAW_INDICES,
    GUARD_PX,
    SUPPORT_PX,
    TRANSFORM_VERSION,
    build_or_load_csr_cache,
    calibrate_weighted_case_control_probabilities,
    compute_csr_structural_gate,
    fit_csr_gate_scales,
    fit_kd_alteration_residual,
    select_csr_dispersed_dots,
)
from gemsdoe30.experiments import CORE_FEATURES, LIDAR_FEATURES, MSDB_FEATURES, LayerStack  # noqa: E402
from gemsdoe30.holdout import masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds  # noqa: E402
from gemsdoe30.lidar_morphology import LIDAR_LAYERS, lidar_layers  # noqa: E402
from gemsdoe30.msdb import (  # noqa: E402
    MSDB_RAW_KEEP_INDICES,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
    select_msdb_edge_dots,
)
from gemsdoe30.readiness import assess as assess_readiness  # noqa: E402
from gemsdoe30.submission import valid_template_mask, validate_submission_file, write_submission_file  # noqa: E402
from verify_prepared_cache import verify as verify_cache  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-csr"
RUN_DIR = ROOT / "runs/csr1"
PROCESSED = ROOT / "data/processed"
EXTERNAL = ROOT / "data/raw/external"
NOTE_TEMPLATE = "CSR1: 3D Laplace/Poisson+1.8km Radon+NoisyOR+2.83px 1D-ridge EDGE, >2px off-cat, 44090d, all-finite [0,1]"


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def verify_external_pins() -> dict[str, dict]:
    pins = {row["id"]: row for row in json.loads((ROOT / "docs/research/mirror-pins-extra.json").read_text())["files"]}
    verified = {}
    for pin_id, rel in (
        ("ext_lidar_scarp_features_u8", "data/raw/external/lidar_scarp_features_u8.tif"),
        ("ext_geodawn_rad_u8", "data/raw/external/geodawn_rad_u8.tif"),
        ("ext_geodawn_extensions_u8", "data/raw/external/geodawn_extensions_u8.tif"),
    ):
        p = ROOT / rel
        digest = sha256_file(p)
        size = p.stat().st_size
        if digest != pins[pin_id]["sha256"] or size != pins[pin_id]["bytes"]:
            raise ValueError(f"external pin mismatch for {rel}: got {digest} ({size} B)")
        verified[pin_id] = {"path": rel, "sha256": digest, "bytes": size}
    return verified


def build_or_load_lidar_cache(valid: np.ndarray, lidar_sha256: str) -> np.ndarray:
    cache_dir = PROCESSED / "csr1_lidar"
    cache_dir.mkdir(parents=True, exist_ok=True)
    arr_path = cache_dir / "lidar_features.npy"
    meta_path = cache_dir / "lidar_manifest.json"
    expected = {
        "lidar_sha256": lidar_sha256,
        "layers": list(LIDAR_LAYERS),
        "shape": [len(LIDAR_LAYERS), int(valid.shape[0]), int(valid.shape[1])],
    }
    if arr_path.is_file() and meta_path.is_file():
        try:
            if json.loads(meta_path.read_text()) == expected:
                arr = np.load(arr_path, mmap_mode="r")
                if arr.shape == tuple(expected["shape"]) and arr.dtype == np.float32:
                    return arr
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    lidar_tif = EXTERNAL / "lidar_scarp_features_u8.tif"
    tpl_tif = ROOT / "data/raw/sample_submission.tif"
    with rasterio.open(lidar_tif) as ds, rasterio.open(tpl_tif) as tpl:
        if (ds.shape, ds.crs, ds.transform) != (tpl.shape, tpl.crs, tpl.transform) or ds.count != 12:
            raise ValueError("LiDAR descriptor grid/band mismatch")
        raw_u8 = ds.read()
    mm = np.lib.format.open_memmap(arr_path, mode="w+", dtype=np.float32, shape=tuple(expected["shape"]))
    for idx, (name, layer) in enumerate(lidar_layers(raw_u8, valid)):
        assert name == LIDAR_LAYERS[idx]
        mm[idx] = layer
    del raw_u8
    mm.flush()
    del mm
    dump_json(meta_path, expected)
    return np.load(arr_path, mmap_mode="r")


def fit_hgb(
    x: np.ndarray,
    y: np.ndarray,
    *,
    seed: int,
    sample_weight: np.ndarray | None = None,
) -> tuple[HistGradientBoostingClassifier, np.ndarray, np.ndarray]:
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
        model.fit((filled - median) / scale, y, sample_weight=sample_weight)
    return model, median, scale


def predict_grid(
    model: HistGradientBoostingClassifier,
    stack: LayerStack,
    columns: list[int],
    median: np.ndarray,
    scale: np.ndarray,
    domain: np.ndarray,
    *,
    block: int = 256,
) -> np.ndarray:
    h, w = domain.shape
    out = np.zeros((h, w), dtype=np.float32)
    cols = list(columns)
    for r0 in range(0, h, block):
        r1 = min(r0 + block, h)
        for c0 in range(0, w, block):
            c1 = min(c0 + block, w)
            sub_dom = domain[r0:r1, c0:c1]
            if not sub_dom.any():
                continue
            cube = np.asarray(stack[cols, r0:r1, c0:c1], dtype=np.float32)
            flat = cube.reshape(len(cols), -1).T
            flat_dom = sub_dom.reshape(-1)
            sel = flat[flat_dom]
            sel = np.where(np.isfinite(sel), sel, median)
            with threadpool_limits(limits=2):
                prob = model.predict_proba((sel - median) / scale)[:, 1]
            tile = np.zeros((r1 - r0, c1 - c0), dtype=np.float32)
            tile.reshape(-1)[flat_dom] = prob.astype(np.float32)
            out[r0:r1, c0:c1] = tile
    return out


def run_canaries(
    stack: LayerStack,
    feature_names: list[str],
    x_train: np.ndarray,
    y_train: np.ndarray,
    fold: dict,
    seed: int,
) -> list[dict]:
    domain = fold["score_valid"] & ~fold["visible"]
    rng = np.random.default_rng(seed + 20_000)
    positives = np.flatnonzero(fold["hidden"])
    negatives = np.flatnonzero(domain & ~fold["hidden"])
    negatives = rng.choice(negatives, min(60_000, negatives.size), replace=False)
    test_idx = np.concatenate([positives, negatives])
    target = np.concatenate([np.ones(positives.size), np.zeros(negatives.size)])
    rows = []
    for j, fname in enumerate(feature_names):
        layer_2d = stack.layers[j]
        values = np.asarray(layer_2d).ravel()[test_idx].astype(np.float32)
        med, scl = fit_standardiser(x_train[:, j : j + 1])
        tr_fill = np.where(np.isfinite(x_train[:, j : j + 1]), x_train[:, j : j + 1], med)
        clf = HistGradientBoostingClassifier(
            max_iter=32,
            learning_rate=0.1,
            max_leaf_nodes=7,
            early_stopping=False,
            random_state=seed + j,
        )
        with threadpool_limits(limits=2):
            clf.fit((tr_fill - med) / scl, y_train)
        te_fill = np.where(np.isfinite(values), values, med[0])
        raw_auc = float(roc_auc_score(target, te_fill)) if np.ptp(te_fill) > 0 else 0.5
        with threadpool_limits(limits=2):
            prob = clf.predict_proba(((te_fill - med[0]) / scl[0])[:, None])[:, 1]
        uni_auc = float(roc_auc_score(target, prob)) if np.ptp(prob) > 0 else 0.5
        sym_max = max(raw_auc, 1.0 - raw_auc, uni_auc, 1.0 - uni_auc)
        rows.append(
            {
                "feature": fname,
                "label": "LEAKAGE-CANARY AUC (not DTI)",
                "raw_auc": raw_auc,
                "raw_auc_either_direction": max(raw_auc, 1.0 - raw_auc),
                "univariate_training_only_hgb_auc": uni_auc,
                "max_symmetric_auc": sym_max,
                "alarm_above_0_90": bool(sym_max > 0.90),
                "heldout_positives": int(positives.size),
                "sampled_negatives": int(negatives.size),
            }
        )
    return rows


def fit_and_predict_csr_surface(
    *,
    stack: LayerStack,
    csr_static: np.ndarray,
    x_all: np.ndarray,
    y: np.ndarray,
    sub_cols: list[int],
    full_cols: list[int],
    train_mask: np.ndarray,
    visible_mask: np.ndarray,
    predict_domain: np.ndarray,
    seed: int,
    noisy_or_sub_weight: float,
    gate_floor: float,
) -> np.ndarray:
    pop_pos = float(np.count_nonzero(train_mask & visible_mask))
    pop_neg = float(np.count_nonzero(train_mask & ~visible_mask))

    # Expert 1: Cover-Decoupled Subsurface Expert (blind to det_elev, det_elev_slope, raw z level, LiDAR)
    z_samp = np.where(np.isfinite(x_all[:, 14]), np.maximum(x_all[:, 14], np.float32(0.0)), np.float32(0.0))
    pos_sel = y > 0.5
    weights = np.ones(y.shape[0], dtype=np.float32)
    weights[pos_sel] = np.clip(np.float32(1.0) + z_samp[pos_sel] / np.float32(400.0), np.float32(1.0), np.float32(3.0))

    mod_sub, med_sub, scl_sub = fit_hgb(x_all[:, sub_cols], y, seed=seed + 500, sample_weight=weights)
    raw_sub = predict_grid(mod_sub, stack, sub_cols, med_sub, scl_sub, predict_domain)
    del mod_sub
    cal_sub = calibrate_weighted_case_control_probabilities(
        raw_sub,
        population_positives=pop_pos,
        population_negatives=pop_neg,
        effective_sample_positives=float(weights[pos_sel].sum()),
        effective_sample_negatives=float(weights[~pos_sel].sum()),
    )
    del raw_sub

    # Expert 2: Full Structural-Geomorphic + Subsurface Radon Expert (no regional DC coordinates)
    mod_full, med_full, scl_full = fit_hgb(x_all[:, full_cols], y, seed=seed)
    raw_full = predict_grid(mod_full, stack, full_cols, med_full, scl_full, predict_domain)
    del mod_full
    cal_full = calibrate_case_control_probabilities(
        raw_full,
        population_positives=int(pop_pos),
        population_negatives=int(pop_neg),
        sample_positives=int(pos_sel.sum()),
        sample_negatives=int((~pos_sel).sum()),
    )
    del raw_full

    w_sub = np.float32(noisy_or_sub_weight)
    p_union = np.float32(1.0) - (np.float32(1.0) - cal_full) * (np.float32(1.0) - w_sub * cal_sub)
    del cal_sub, cal_full

    g_scales = fit_csr_gate_scales(csr_static, train_mask)
    gate = compute_csr_structural_gate(csr_static, predict_domain, g_scales, floor=gate_floor)
    surface = np.where(predict_domain, np.clip(p_union * gate, np.float32(0.0), np.float32(1.0)), np.float32(0.0))
    return surface.astype(np.float32, copy=False)


def write_surface_geotiff(surface: np.ndarray, template_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as tpl:
        profile = tpl.profile.copy()
    profile.update(driver="GTiff", count=1, dtype="float32", nodata=None, compress="deflate", predictor=3)
    clean = np.where(np.isfinite(surface), np.clip(surface, np.float32(0.0), np.float32(1.0)), np.float32(0.0)).astype(
        np.float32
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(clean[None, :, :])


def main() -> int:
    assert len(NOTE_TEMPLATE) <= 140
    t0 = time.monotonic()
    REPORT.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    prereg_md_path = REPORT / "preregistration.md"
    prereg_json_path = REPORT / "preregistration.json"
    prereg = json.loads(prereg_json_path.read_text())
    prereg_md_sha = sha256_file(prereg_md_path)
    prereg_json_sha = sha256_file(prereg_json_path)
    deadline = t0 + float(prereg["max_wall_seconds"])

    def check_budget() -> None:
        if time.monotonic() > deadline:
            raise TimeoutError("CSR-1 hard 2-hour experimental time budget exceeded")

    started_path = REPORT / "started.json"
    if started_path.exists():
        raise RuntimeError(f"{started_path} already exists; refusing unscheduled re-execution")

    cache_receipt = verify_cache(PROCESSED)
    dump_json(REPORT / "cache-verification.json", cache_receipt)
    if cache_receipt["dataset_signature"] != prereg["dataset_signature"]:
        raise ValueError("dataset_signature mismatch against frozen preregistration")

    ext_pins = verify_external_pins()
    reg_path = ROOT / prereg["registry_path"]
    if sha256_file(reg_path) != prereg["registry_sha256"]:
        raise ValueError("registry.json SHA-256 differs from frozen preregistration")

    dump_json(
        started_path,
        {
            "schema_version": 1,
            "lane": prereg["lane"],
            "experiment_spec": prereg["experiment_spec"],
            "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "experiment_cap": int(prereg["max_experiments"]),
            "preregistration_md_sha256": prereg_md_sha,
            "preregistration_json_sha256": prereg_json_sha,
            "registry_sha256": prereg["registry_sha256"],
        },
    )

    base = np.load(PROCESSED / "features_raw.npy", mmap_mode="r")
    labels = np.load(PROCESSED / "labels.npy", mmap_mode="r") > 0.5
    valid = np.load(PROCESSED / "valid.npy", mmap_mode="r").astype(bool)

    with rasterio.open(EXTERNAL / "geodawn_rad_u8.tif") as ds_rad:
        rad_k_u8 = ds_rad.read(1)
        rad_th_u8 = ds_rad.read(2)
    with rasterio.open(EXTERNAL / "geodawn_extensions_u8.tif") as ds_ext:
        tmi_up150_u8 = ds_ext.read(4)

    print("[CSR-1] Building/loading static caches (MSDB18, CSR26, LiDAR17)...", flush=True)
    msdb = build_or_load_msdb_cache(base, valid, PROCESSED / "msdb_v2", prereg["dataset_signature"])
    csr_static = build_or_load_csr_cache(
        base,
        valid,
        tmi_up150_u8,
        PROCESSED / "csr1_static",
        prereg["dataset_signature"],
        ext_pins["ext_geodawn_extensions_u8"]["sha256"],
    )
    lidar = build_or_load_lidar_cache(valid, ext_pins["ext_lidar_scarp_features_u8"]["sha256"])
    del tmi_up150_u8

    feature_names = list(CORE_FEATURES) + list(MSDB_FEATURES) + list(CSR_ALL_DERIVED_NAMES) + list(LIDAR_FEATURES)
    assert len(feature_names) == 81

    csr_finite_counts = {
        CSR_STATIC_FEATURE_NAMES[i]: int(np.count_nonzero(np.isfinite(csr_static[i]) & valid))
        for i in range(len(CSR_STATIC_FEATURE_NAMES))
    }
    dump_json(
        REPORT / "feature-receipt.json",
        {
            "schema_version": 1,
            "transform_version": TRANSFORM_VERSION,
            "support_px": SUPPORT_PX,
            "guard_px": GUARD_PX,
            "dataset_signature": prereg["dataset_signature"],
            "external_pins": ext_pins,
            "csr_static_finite_pixels_in_footprint": csr_finite_counts,
        },
    )

    core19_cols = list(range(19))
    msdb_cols = list(MSDB_RAW_KEEP_INDICES) + [19 + j for j in range(18)]
    sub_cols = list(CSR_SUB_RAW_INDICES) + [37 + j for j in range(22)] + [63]
    full_cols = list(CSR_FULL_RAW_INDICES) + [37 + j for j in range(27)] + [64 + j for j in range(17)]

    dot_budget = int(prereg["dot_budget"])
    seed1 = int(prereg["primary_seed"])
    arms_e1 = tuple(prereg["arms"])
    block_rows_e1: dict[str, list[dict]] = {a: [] for a in arms_e1}
    folds_e1: list[dict] = []
    canaries_e1: list[dict] = []
    experiments_run = 1

    print(f"[CSR-1] Experiment 1 (seed={seed1}) across 4 buffered spatial-segment folds...", flush=True)
    for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
        check_budget()
        f = int(fold["fold"])
        kd_resid, kd_meta = fit_kd_alteration_residual(rad_k_u8, rad_th_u8, fold["train_mask"], valid)
        layers_list = (
            [base[i] for i in range(19)]
            + [msdb[i] for i in range(18)]
            + [csr_static[i] for i in range(26)]
            + [kd_resid]
            + [lidar[i] for i in range(17)]
        )
        stack = LayerStack(layers_list)
        x_all, y = sample_training_pixels(
            stack, fold["visible"], fold["train_mask"], negatives_per_positive=6, seed=seed1 + f
        )

        print(f"  [Fold {f}] Running 81-feature bidirectional leakage canaries...", flush=True)
        fold_canaries = run_canaries(stack, feature_names, x_all, y, fold, seed1 + f)
        canaries_e1.append({"fold": f, "kd_fit": kd_meta, "features": fold_canaries})
        alarms = [r for r in fold_canaries if r["alarm_above_0_90"]]
        print(f"  [Fold {f}] Canaries complete: max_sym_auc={max(r['max_symmetric_auc'] for r in fold_canaries):.4f}, alarms={len(alarms)}", flush=True)

        active = fold["score_valid"] & ~fold["visible"]
        count = int(round(dot_budget * int(active.sum()) / int(valid.sum())))
        pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
        pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
        samp_pos = int(np.count_nonzero(y > 0.5))
        samp_neg = int(np.count_nonzero(y < 0.5))

        fold_rec = {**fold["metadata"], "dot_budget_each_arm": count, "arms": {}}

        # Arm 1: core19_edge
        print(f"  [Fold {f}] Fitting & scoring core19_edge (budget={count})...", flush=True)
        m_c19, med_c19, scl_c19 = fit_hgb(x_all[:, core19_cols], y, seed=seed1 + f)
        p_c19 = calibrate_case_control_probabilities(
            predict_grid(m_c19, stack, core19_cols, med_c19, scl_c19, active),
            population_positives=pop_pos,
            population_negatives=pop_neg,
            sample_positives=samp_pos,
            sample_negatives=samp_neg,
        )
        del m_c19
        d_c19 = select_msdb_edge_dots(p_c19, active, count)
        del p_c19
        sc_c19 = masked_dti_by_blocks(d_c19, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        del d_c19
        block_rows_e1["core19_edge"].extend(sc_c19["spatial_blocks"])
        fold_rec["arms"]["core19_edge"] = {k: v for k, v in sc_c19["pooled"].items() if k != "dti"}
        print(f"    core19_edge fold {f} HOLDOUT-DTI = {sc_c19['pooled']['dti']:.6f}", flush=True)

        # Arm 2: msdb_edge (standing promoted benchmark)
        print(f"  [Fold {f}] Fitting & scoring msdb_edge (budget={count})...", flush=True)
        msdb_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])
        m_msdb, med_msdb, scl_msdb = fit_hgb(x_all[:, msdb_cols], y, seed=seed1 + f)
        p_msdb = calibrate_case_control_probabilities(
            predict_grid(m_msdb, stack, msdb_cols, med_msdb, scl_msdb, active),
            population_positives=pop_pos,
            population_negatives=pop_neg,
            sample_positives=samp_pos,
            sample_negatives=samp_neg,
        )
        del m_msdb
        psi_msdb = compute_curvilinear_discontinuity_gate(msdb, msdb_scales, active)
        g_msdb = (p_msdb * psi_msdb).astype(np.float32)
        del p_msdb, psi_msdb
        d_msdb = select_msdb_edge_dots(g_msdb, active, count)
        del g_msdb
        sc_msdb = masked_dti_by_blocks(d_msdb, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        del d_msdb
        block_rows_e1["msdb_edge"].extend(sc_msdb["spatial_blocks"])
        fold_rec["arms"]["msdb_edge"] = {k: v for k, v in sc_msdb["pooled"].items() if k != "dti"}
        print(f"    msdb_edge fold {f} HOLDOUT-DTI = {sc_msdb['pooled']['dti']:.6f}", flush=True)

        # CSR Dual-Expert Surface -> Arm 3 (csr_dense_edge) & Arm 4 (csr_dispersed)
        print(f"  [Fold {f}] Fitting & scoring CSR dual-expert arms (budget={count})...", flush=True)
        csr_surf = fit_and_predict_csr_surface(
            stack=stack,
            csr_static=csr_static,
            x_all=x_all,
            y=y,
            sub_cols=sub_cols,
            full_cols=full_cols,
            train_mask=fold["train_mask"],
            visible_mask=fold["visible"],
            predict_domain=active,
            seed=seed1 + f,
            noisy_or_sub_weight=float(prereg["noisy_or_subsurface_weight"]),
            gate_floor=float(prereg["gate_floor"]),
        )
        d_dense = select_msdb_edge_dots(csr_surf, active, count)
        sc_dense = masked_dti_by_blocks(d_dense, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        del d_dense
        block_rows_e1["csr_dense_edge"].extend(sc_dense["spatial_blocks"])
        fold_rec["arms"]["csr_dense_edge"] = {k: v for k, v in sc_dense["pooled"].items() if k != "dti"}
        print(f"    csr_dense_edge fold {f} HOLDOUT-DTI = {sc_dense['pooled']['dti']:.6f}", flush=True)

        d_disp = select_csr_dispersed_dots(
            csr_surf,
            active,
            count,
            gamma=float(prereg["ridge_concentration_gamma"]),
            min_sq_dist_excl=int(prereg["min_interdot_sq_dist_exclusive"]),
        )
        del csr_surf
        sc_disp = masked_dti_by_blocks(d_disp, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
        del d_disp
        block_rows_e1["csr_dispersed"].extend(sc_disp["spatial_blocks"])
        fold_rec["arms"]["csr_dispersed"] = {k: v for k, v in sc_disp["pooled"].items() if k != "dti"}
        print(f"    csr_dispersed fold {f} HOLDOUT-DTI = {sc_disp['pooled']['dti']:.6f}", flush=True)

        folds_e1.append(fold_rec)
        del x_all, y, kd_resid, stack

    summary_e1 = spatial_bootstrap(
        block_rows_e1,
        candidate="csr_dispersed",
        replicates=int(prereg["bootstrap_replicates"]),
        seed=int(prereg["bootstrap_seed"]),
    )
    all_canary_alarms = [
        {"fold": c["fold"], **r}
        for c in canaries_e1
        for r in c["features"]
        if r["alarm_above_0_90"]
    ]
    max_sym_auc = max(r["max_symmetric_auc"] for c in canaries_e1 for r in c["features"])
    delta_c19 = summary_e1["candidate_minus"]["core19_edge"]
    delta_msdb = summary_e1["candidate_minus"]["msdb_edge"]
    delta_dense = summary_e1["candidate_minus"]["csr_dense_edge"]

    print(
        f"[CSR-1] Exp 1 Pooled HOLDOUT-DTI: "
        f"core19_edge={summary_e1['arms']['core19_edge']['value']:.6f}, "
        f"msdb_edge={summary_e1['arms']['msdb_edge']['value']:.6f}, "
        f"csr_dense_edge={summary_e1['arms']['csr_dense_edge']['value']:.6f}, "
        f"csr_dispersed={summary_e1['arms']['csr_dispersed']['value']:.6f} "
        f"(vs msdb: {delta_msdb['value']:+.6f} CI [{delta_msdb['ci95'][0]:+.6f}, {delta_msdb['ci95'][1]:+.6f}])",
        flush=True,
    )

    e1_gate_passed = (
        len(all_canary_alarms) == 0
        and float(delta_c19["value"]) > 0.0
        and float(delta_c19["ci95"][0]) > 0.0
        and float(delta_msdb["value"]) > 0.0
        and float(delta_msdb["ci95"][0]) > 0.0
    )

    confirmation_summary = None
    e2_gate_passed = False
    seed2 = int(prereg["confirmation_seed"])
    if e1_gate_passed:
        experiments_run += 1
        print(f"[CSR-1] Experiment 2 (confirmation seed={seed2})...", flush=True)
        block_rows_e2: dict[str, list[dict]] = {"msdb_edge": [], "csr_dispersed": []}
        for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
            check_budget()
            f = int(fold["fold"])
            kd_resid, _ = fit_kd_alteration_residual(rad_k_u8, rad_th_u8, fold["train_mask"], valid)
            layers_list = (
                [base[i] for i in range(19)]
                + [msdb[i] for i in range(18)]
                + [csr_static[i] for i in range(26)]
                + [kd_resid]
                + [lidar[i] for i in range(17)]
            )
            stack = LayerStack(layers_list)
            x_all, y = sample_training_pixels(
                stack, fold["visible"], fold["train_mask"], negatives_per_positive=6, seed=seed2 + f
            )
            active = fold["score_valid"] & ~fold["visible"]
            count = int(round(dot_budget * int(active.sum()) / int(valid.sum())))
            pop_pos = int(np.count_nonzero(fold["train_mask"] & fold["visible"]))
            pop_neg = int(np.count_nonzero(fold["train_mask"] & ~fold["visible"]))
            samp_pos = int(np.count_nonzero(y > 0.5))
            samp_neg = int(np.count_nonzero(y < 0.5))

            msdb_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])
            m_msdb, med_msdb, scl_msdb = fit_hgb(x_all[:, msdb_cols], y, seed=seed2 + f)
            p_msdb = calibrate_case_control_probabilities(
                predict_grid(m_msdb, stack, msdb_cols, med_msdb, scl_msdb, active),
                population_positives=pop_pos,
                population_negatives=pop_neg,
                sample_positives=samp_pos,
                sample_negatives=samp_neg,
            )
            del m_msdb
            g_msdb = (p_msdb * compute_curvilinear_discontinuity_gate(msdb, msdb_scales, active)).astype(np.float32)
            del p_msdb
            d_msdb = select_msdb_edge_dots(g_msdb, active, count)
            del g_msdb
            sc_msdb = masked_dti_by_blocks(d_msdb, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
            del d_msdb
            block_rows_e2["msdb_edge"].extend(sc_msdb["spatial_blocks"])

            csr_surf = fit_and_predict_csr_surface(
                stack=stack,
                csr_static=csr_static,
                x_all=x_all,
                y=y,
                sub_cols=sub_cols,
                full_cols=full_cols,
                train_mask=fold["train_mask"],
                visible_mask=fold["visible"],
                predict_domain=active,
                seed=seed2 + f,
                noisy_or_sub_weight=float(prereg["noisy_or_subsurface_weight"]),
                gate_floor=float(prereg["gate_floor"]),
            )
            d_disp = select_csr_dispersed_dots(
                csr_surf,
                active,
                count,
                gamma=float(prereg["ridge_concentration_gamma"]),
                min_sq_dist_excl=int(prereg["min_interdot_sq_dist_exclusive"]),
            )
            del csr_surf
            sc_disp = masked_dti_by_blocks(d_disp, fold["hidden"], fold["visible"], fold["score_valid"], block_size_px=128)
            del d_disp
            block_rows_e2["csr_dispersed"].extend(sc_disp["spatial_blocks"])
            del x_all, y, kd_resid, stack

        confirmation_summary = spatial_bootstrap(
            block_rows_e2,
            candidate="csr_dispersed",
            replicates=int(prereg["bootstrap_replicates"]),
            seed=int(prereg["bootstrap_seed"]),
        )
        d2 = confirmation_summary["candidate_minus"]["msdb_edge"]
        e2_gate_passed = float(d2["value"]) > 0.0 and float(d2["ci95"][0]) > 0.0
        print(
            f"[CSR-1] Exp 2 Confirmation: csr_dispersed={confirmation_summary['arms']['csr_dispersed']['value']:.6f} "
            f"vs msdb_edge={confirmation_summary['arms']['msdb_edge']['value']:.6f} "
            f"(diff={d2['value']:+.6f} CI [{d2['ci95'][0]:+.6f}, {d2['ci95'][1]:+.6f}], passed={e2_gate_passed})",
            flush=True,
        )

    # Experiment 3: Full-footprint production surface + two-stage novelty + validated GeoTIFF
    experiments_run += 1
    check_budget()
    prod_seeds = [seed1, seed2] if (e1_gate_passed and e2_gate_passed) else [seed1]
    print(f"[CSR-1] Experiment {experiments_run} (full-footprint production fit, seeds={prod_seeds})...", flush=True)
    kd_full, kd_full_meta = fit_kd_alteration_residual(rad_k_u8, rad_th_u8, valid, valid)
    prod_layers = (
        [base[i] for i in range(19)]
        + [msdb[i] for i in range(18)]
        + [csr_static[i] for i in range(26)]
        + [kd_full]
        + [lidar[i] for i in range(17)]
    )
    prod_stack = LayerStack(prod_layers)
    surface_acc = np.zeros(valid.shape, dtype=np.float32)
    for s in prod_seeds:
        check_budget()
        x_full, y_full = sample_training_pixels(prod_stack, labels, valid, negatives_per_positive=6, seed=s + 90)
        surf_s = fit_and_predict_csr_surface(
            stack=prod_stack,
            csr_static=csr_static,
            x_all=x_full,
            y=y_full,
            sub_cols=sub_cols,
            full_cols=full_cols,
            train_mask=valid,
            visible_mask=labels,
            predict_domain=valid,
            seed=s + 90,
            noisy_or_sub_weight=float(prereg["noisy_or_subsurface_weight"]),
            gate_floor=float(prereg["gate_floor"]),
        )
        surface_acc += surf_s / np.float32(len(prod_seeds))
        del x_full, y_full, surf_s
    del kd_full, prod_stack

    tpl_path = ROOT / "data/raw/sample_submission.tif"
    surf_tif = RUN_DIR / "csr1_continuous_surface.tif"
    write_surface_geotiff(surface_acc, tpl_path, surf_tif)

    print("[CSR-1] Running Stage-1 pre-placement continuous-surface novelty audit...", flush=True)
    surface_novelty = audit_novelty(surf_tif, tpl_path, reg_path, "surface")
    dump_json(REPORT / "novelty-surface.json", surface_novelty)
    max_surf_spearman = max(
        (float(r["spearman_full_footprint"]) for r in surface_novelty["comparisons"]),
        default=0.0,
    )
    surface_duplicate = any(
        r.get("identical_inside_footprint") or float(r["spearman_full_footprint"]) > 0.90
        for r in surface_novelty["comparisons"]
    ) or bool(surface_novelty.get("errors"))
    print(f"[CSR-1] Stage-1 surface max Spearman = {max_surf_spearman:.6f}, duplicate_or_err={surface_duplicate}", flush=True)
    if surface_duplicate:
        raise RuntimeError("Stage-1 continuous-surface novelty duplicate/error STOP triggered")

    dist_cat = distance_transform_edt(~labels)
    off_cat_active = valid & (dist_cat > float(prereg["off_catalogue_min_distance_px"]))
    prod_dots = select_csr_dispersed_dots(
        surface_acc,
        off_cat_active,
        dot_budget,
        gamma=float(prereg["ridge_concentration_gamma"]),
        min_sq_dist_excl=int(prereg["min_interdot_sq_dist_exclusive"]),
    )
    del surface_acc

    with rasterio.open(tpl_path) as tpl_ds:
        fp_mask = valid_template_mask(tpl_ds, np)
    values_sha = hashlib.sha256(np.ascontiguousarray(prod_dots[fp_mask], dtype=np.float32).tobytes()).hexdigest()
    short_sha = values_sha[:12]
    run_id = f"gems30-CSR1-{dot_budget}-20261026-{short_sha}"
    tif_rel = Path(f"docs/downloads/{run_id}-zeros.tif")
    tif_path = ROOT / tif_rel

    write_info = write_submission_file(
        prod_dots,
        tpl_path,
        tif_path,
        note=NOTE_TEMPLATE,
        run_name=run_id,
        metadata_path=tif_path.with_suffix(".json"),
        outside_value=0.0,
    )
    val_report = validate_submission_file(
        tif_path,
        tpl_path,
        require_finite_all_cells=True,
        portal_safe=True,
    )
    with rasterio.open(tif_path) as out_ds:
        whole = out_ds.read(1)
    pts = np.argwhere(whole > 0.5).astype(np.float64)
    nn_dists, _ = cKDTree(pts).query(pts, k=2)
    min_nn_px = float(nn_dists[:, 1].min())
    p10_nn_px = float(np.quantile(nn_dists[:, 1], 0.10))
    median_nn_px = float(np.median(nn_dists[:, 1]))
    d_at_dots = dist_cat[whole > 0.5]
    dots_le2 = int(np.count_nonzero(d_at_dots <= 2.0))
    whole_finite_01 = bool(np.isfinite(whole).all() and float(whole.min()) >= 0.0 and float(whole.max()) <= 1.0)
    if not val_report.passed or not whole_finite_01 or dots_le2 != 0:
        raise RuntimeError(f"Submission validation failed: {val_report.to_dict()}")

    print("[CSR-1] Running Stage-2 final-dot novelty audit across 357 aligned rasters...", flush=True)
    dots_novelty = audit_novelty(tif_path, tpl_path, reg_path, "dots")
    dump_json(REPORT / "novelty-dots.json", dots_novelty)
    max_dot_spearman = max((float(r["spearman_full_footprint"]) for r in dots_novelty["comparisons"]), default=0.0)
    top_overlap_row = max(
        dots_novelty["comparisons"],
        key=lambda r: float(r["candidate_fraction_within_3px_of_reference"]),
    )
    max_dot_overlap = float(top_overlap_row["candidate_fraction_within_3px_of_reference"])
    dots_duplicate = any(
        r.get("identical_inside_footprint")
        or float(r["spearman_full_footprint"]) > 0.90
        or float(r["candidate_fraction_within_3px_of_reference"]) > 0.70
        for r in dots_novelty["comparisons"]
    ) or bool(dots_novelty.get("errors"))
    print(
        f"[CSR-1] Stage-2 dots max Spearman = {max_dot_spearman:.6f}, "
        f"max 3-px overlap = {max_dot_overlap:.6f} (vs {top_overlap_row['reference']}), "
        f"duplicate_or_err = {dots_duplicate}",
        flush=True,
    )

    elapsed = round(time.monotonic() - t0, 2)
    results_payload = {
        "schema_version": 1,
        "experiment_spec": "csr1",
        "lane": "CSR-1",
        "transform_version": TRANSFORM_VERSION,
        "dataset_signature": prereg["dataset_signature"],
        "preregistration_md_sha256": prereg_md_sha,
        "preregistration_json_sha256": prereg_json_sha,
        "kd_full_fit": kd_full_meta,
        "summary": summary_e1,
        "confirmation_seed3119": confirmation_summary,
        "folds": folds_e1,
        "feature_canaries": canaries_e1,
        "canary_alarms": all_canary_alarms,
        "max_feature_symmetric_auc": max_sym_auc,
        "ablation_dispersed_minus_dense": delta_dense,
        "experiments_run": experiments_run,
        "experimental_elapsed_seconds": elapsed,
    }
    dump_json(REPORT / "results.json", results_payload)

    raster_sha = sha256_file(tif_path)
    validator_output = {
        "status": "passed",
        "no_nan_inside_footprint": True,
        "no_nan_anywhere": whole_finite_01,
        "values_in_0_1_inside_footprint": True,
        "values_in_0_1_whole_array": whole_finite_01,
        "min_whole_array": float(whole.min()),
        "max_whole_array": float(whole.max()),
        "crs_match": True,
        "shape_match": True,
        "transform_match": True,
        "single_float32_band": True,
        "outside_footprint_value": 0.0,
        "positive_catalogue_pixels": int(np.count_nonzero((whole > 0.5) & labels)),
        "dots_within_2px_of_catalogue": dots_le2,
        "emitted_dots": int(np.count_nonzero(whole > 0.5)),
        "min_interdot_nn_px": min_nn_px,
        "p10_interdot_nn_px": p10_nn_px,
        "median_interdot_nn_px": median_nn_px,
        "catalogue_distance_quantiles_px": {
            "p10": float(np.quantile(d_at_dots, 0.10)),
            "p25": float(np.quantile(d_at_dots, 0.25)),
            "p50": float(np.quantile(d_at_dots, 0.50)),
            "p75": float(np.quantile(d_at_dots, 0.75)),
            "p90": float(np.quantile(d_at_dots, 0.90)),
            "frac_gt_5px": float(np.mean(d_at_dots > 5.0)),
            "frac_gt_15px": float(np.mean(d_at_dots > 15.0)),
            "frac_gt_50px": float(np.mean(d_at_dots > 50.0)),
        },
        "organizer_acceptance_confirmed": False,
        "submission_report": val_report.to_dict(),
        "write_info": write_info,
    }

    lane_scientific_pass = bool(
        e1_gate_passed
        and e2_gate_passed
        and not surface_duplicate
        and not dots_duplicate
        and whole_finite_01
        and dots_le2 == 0
    )

    prelim_card = {
        "schema_version": 1,
        "experiment_spec": "csr1",
        "run_id": run_id,
        "submission_name": run_id,
        "note": NOTE_TEMPLATE,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lane": "CSR-1 (preregistered 2026-10-26 before any fold fit)",
        "lane_preregistration_sha256": prereg_md_sha,
        "externally_assigned_lane_verified": False,
        "hypothesis": (
            "Cover-compensated 3D Laplace/Poisson gravity vertical derivatives, unit-consistent 1000x tmi_vg "
            "magnetic tilt/analytic signal, and 12-azimuth 1.8 km flank-subtracted Radon line-integrals inside "
            "a cover-decoupled Noisy-OR dual-expert ensemble with 1D ridge concentration and >=2.83 px dispersed "
            "submodular EDGE emission improve concealed-fault recovery over core19 and MSDB-1v2 while avoiding "
            "1-2 px range-front dot collisions."
        ),
        "mechanism": (
            "Dual-expert HGB (33-feature cover-blind subsurface expert with inverse cover-censoring weights "
            "+ 56-feature DC-free structural-geomorphic Radon expert) combined via Noisy-OR x Rayleigh "
            "curvilinear gate, concentrated onto 1D Hessian ridge crests (gamma=1.25) and emitted via "
            "submodular 300 m EDGE with dr^2+dc^2>6 (>=282.8 m) spacing and >2 px off-catalogue collar."
        ),
        "non_fault_mimic": (
            "Buried pluton/caldera margins, incised bedrock paleochannels, unreactivated Mesozoic contacts, "
            "saline playa clay pans, and Lake Lahontan recessional shorelines."
        ),
        "experiments_run": experiments_run,
        "experiment_cap": int(prereg["max_experiments"]),
        "experimental_elapsed_seconds": elapsed,
        "dataset_signature": prereg["dataset_signature"],
        "published_tiff": str(tif_rel),
        "tif_path": str(tif_rel),
        "sha256": raster_sha,
        "raster_sha256": raster_sha,
        "values_sha256": values_sha,
        "holdout_dti": float(summary_e1["arms"]["csr_dispersed"]["value"]),
        "ci95": list(summary_e1["arms"]["csr_dispersed"]["ci95"]),
        "baseline_dti": {
            "core19_edge": float(summary_e1["arms"]["core19_edge"]["value"]),
            "msdb_edge": float(summary_e1["arms"]["msdb_edge"]["value"]),
            "csr_dense_edge": float(summary_e1["arms"]["csr_dense_edge"]["value"]),
        },
        "max_feature_auc": max_sym_auc,
        "max_registry_corr": max(max_surf_spearman, max_dot_spearman),
        "dot_overlap_pct": round(100.0 * max_dot_overlap, 4),
        "holdout": {
            "label": "HOLDOUT-DTI",
            **summary_e1["arms"]["csr_dispersed"],
            "evaluator_version": summary_e1["evaluator_version"],
            "protocol_version": summary_e1["protocol_version"],
            "bootstrap": summary_e1["bootstrap"],
            "comparators": {
                k: summary_e1["arms"][k] for k in ("core19_edge", "msdb_edge", "csr_dense_edge")
            },
            "candidate_minus": summary_e1["candidate_minus"],
            "confirmation_seed3119": confirmation_summary,
        },
        "feature_canaries": {
            "features_per_fold": len(feature_names),
            "folds": 4,
            "alarms": all_canary_alarms,
            "max_auc_either_direction": max_sym_auc,
        },
        "registry": {
            "registry_path": prereg["registry_path"],
            "registry_sha256": prereg["registry_sha256"],
            "aligned_rasters_compared": len(dots_novelty["comparisons"]),
            "malformed_exclusions_audited": len(dots_novelty.get("malformed_exclusions_audited", [])),
            "surface_max_spearman": max_surf_spearman,
            "dots_max_spearman": max_dot_spearman,
            "dots_max_fraction_within_3px": max_dot_overlap,
            "dots_closest_reference": top_overlap_row["reference"],
            "dots_closest_reference_site": top_overlap_row.get("site"),
        },
        "validator_output": validator_output,
        "historical_best_rerun": {
            "verified": True,
            "benchmark_arm": "msdb_edge",
            "evaluator_version": summary_e1["evaluator_version"],
            "protocol_version": summary_e1["protocol_version"],
            "candidate_beats_best_with_paired_ci": bool(e1_gate_passed and e2_gate_passed),
        },
        "lane_scientific_gates_all_passed": lane_scientific_pass,
        "lane_scientific_verdict": "promote" if lane_scientific_pass else "negative",
        "verdict": "negative",
        "submission_approved": False,
        "slot_selected": False,
        "download_ok": True,
        "ok_to_submit": False,
        "organizer_score": None,
    }

    readiness = assess_readiness(
        prelim_card,
        results_payload,
        format_passed=bool(val_report.passed and whole_finite_01 and dots_le2 == 0),
        hash_matches=bool(tif_path.is_file() and sha256_file(tif_path) == raster_sha),
        surface_audit=surface_novelty,
        dots_audit=dots_novelty,
        registry=json.loads(reg_path.read_text()),
        artifact_public=tif_path.is_file(),
    )
    dump_json(REPORT / "readiness.json", readiness)

    # Strict Parallel-Run Protocol Rule 7 & fail-closed global registry readiness:
    # `verdict` reflects lane promotion vs negative; `ok_to_submit` / `submission_approved`
    # remain fail-closed False until the owner's cross-session selector checks any private lanes.
    prelim_card["verdict"] = "promote" if lane_scientific_pass else "negative"
    prelim_card["global_readiness_verdict"] = readiness["research_verdict"]
    prelim_card["download_ok"] = bool(readiness["download_ok"])
    prelim_card["display_status"] = (
        "LANE PROMOTED (NEW HOLDOUT-DTI RECORD & 357-RASTER UNIQUE) — CROSS-SESSION SELECTOR REQUIRED BEFORE PORTAL UPLOAD"
        if lane_scientific_pass
        else "NEGATIVE — RESEARCH DOWNLOAD OK; DO NOT SUBMIT TO PORTAL"
    )
    dump_json(REPORT / "run-card.json", prelim_card)
    print(f"[CSR-1] Run complete in {elapsed:.1f}s -> {tif_rel} ({prelim_card['display_status']})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
