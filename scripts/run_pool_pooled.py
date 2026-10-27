#!/usr/bin/env python3
"""Execute preregistered Lane POOL-1 (pooled MSDB-18 + CSR-27 + LiDAR-17 HGB).

Frozen by docs/research/2026-10-27-pool/preregistration.{md,json} before any fold fit.
Reuses the shared evaluator (gemsdoe30.holdout), writer (gemsdoe30.submission),
canary/HGB helpers from scripts/run_csr_discontinuity.py, and the two-stage novelty
audit (scripts/check_novelty.py). Refuses re-execution if started.json exists.

Experiment accounting (cap 3 / 7200 s):
  E1: 4-fold buffered whole-component holdout, arms msdb_edge / pool_dense_edge /
      pool_dispersed (candidate), seed 4201, 81-feature leakage canaries per fold.
  E2: confirmation (seed 4219, msdb_edge + pool_dispersed) ONLY if E1 gate passes.
  E3: full-footprint production fit + surface/dots novelty + validated GeoTIFF.
A duplicate-stop at either novelty stage publishes NO GeoTIFF to docs/downloads/.
"""
from __future__ import annotations

import hashlib
import json
import shutil
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

from check_novelty import audit as audit_novelty  # noqa: E402
from feature_value_holdout import sample_training_pixels  # noqa: E402
from gemsdoe30.csr_discontinuity import (  # noqa: E402
    CSR_ALL_DERIVED_NAMES,
    CSR_STATIC_FEATURE_NAMES,
    GUARD_PX,
    SUPPORT_PX,
    TRANSFORM_VERSION,
    build_or_load_csr_cache,
    fit_kd_alteration_residual,
    select_csr_dispersed_dots,
)
from gemsdoe30.experiments import CORE_FEATURES, LIDAR_FEATURES, MSDB_FEATURES, LayerStack  # noqa: E402
from gemsdoe30.holdout import masked_dti_by_blocks, spatial_bootstrap, spatial_segment_folds  # noqa: E402
from gemsdoe30.msdb import (  # noqa: E402
    MSDB_RAW_KEEP_INDICES,
    build_or_load_msdb_cache,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    fit_curvilinear_gate_scales,
    select_msdb_edge_dots,
)
from gemsdoe30.novelty import compare as novelty_compare  # noqa: E402
from gemsdoe30.novelty import rank_cache as novelty_rank_cache  # noqa: E402
from gemsdoe30.readiness import assess as assess_readiness  # noqa: E402
from gemsdoe30.submission import valid_template_mask, validate_submission_file, write_submission_file  # noqa: E402
from run_csr_discontinuity import (  # noqa: E402
    build_or_load_lidar_cache,
    dump_json,
    fit_hgb,
    predict_grid,
    run_canaries,
    sha256_file,
    verify_external_pins,
    write_surface_geotiff,
)
from verify_prepared_cache import verify as verify_cache  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-27-pool"
RUN_DIR = ROOT / "runs/pool1"
PROCESSED = ROOT / "data/processed"
EXTERNAL = ROOT / "data/raw/external"
NOTE_TEMPLATE = "POOL1: MSDB18+CSR27+LiDAR17 pooled HGB x Rayleigh gate, 2.83px dispersed EDGE >2px off-cat, 44090d [0,1]"


def fit_and_predict_surface(*, stack, msdb_cache, x_all, y, cols, train_mask,
                            visible_mask, predict_domain, seed):
    """One calibrated HGB surface x MSDB Rayleigh gate (msdb_edge construction)."""
    pop_pos = int(np.count_nonzero(train_mask & visible_mask))
    pop_neg = int(np.count_nonzero(train_mask & ~visible_mask))
    samp_pos = int(np.count_nonzero(y > 0.5))
    samp_neg = int(np.count_nonzero(y < 0.5))
    gate_scales = fit_curvilinear_gate_scales(x_all[:, 19:37])
    model, median, scale = fit_hgb(x_all[:, cols], y, seed=seed)
    prob = calibrate_case_control_probabilities(
        predict_grid(model, stack, cols, median, scale, predict_domain),
        population_positives=pop_pos, population_negatives=pop_neg,
        sample_positives=samp_pos, sample_negatives=samp_neg)
    del model
    gate = compute_curvilinear_discontinuity_gate(msdb_cache, gate_scales, predict_domain)
    surface = np.where(predict_domain, np.clip(prob * gate, np.float32(0.0), np.float32(1.0)),
                       np.float32(0.0))
    return surface.astype(np.float32, copy=False)


def main() -> int:
    assert len(NOTE_TEMPLATE) <= 140, len(NOTE_TEMPLATE)
    t0 = time.monotonic()
    REPORT.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    prereg = json.loads((REPORT / "preregistration.json").read_text())
    prereg_md_sha = sha256_file(REPORT / "preregistration.md")
    prereg_json_sha = sha256_file(REPORT / "preregistration.json")
    deadline = t0 + float(prereg["max_wall_seconds"])

    def check_budget():
        if time.monotonic() > deadline:
            raise TimeoutError("POOL-1 hard 2-hour experimental budget exceeded")

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
    dump_json(started_path, {
        "schema_version": 1, "lane": prereg["lane"], "experiment_spec": prereg["experiment_spec"],
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_cap": int(prereg["max_experiments"]),
        "preregistration_md_sha256": prereg_md_sha, "preregistration_json_sha256": prereg_json_sha,
        "registry_sha256": prereg["registry_sha256"]})

    base = np.load(PROCESSED / "features_raw.npy", mmap_mode="r")
    labels = np.load(PROCESSED / "labels.npy", mmap_mode="r") > 0.5
    valid = np.load(PROCESSED / "valid.npy", mmap_mode="r").astype(bool)
    with rasterio.open(EXTERNAL / "geodawn_rad_u8.tif") as ds_rad:
        rad_k_u8, rad_th_u8 = ds_rad.read(1), ds_rad.read(2)
    with rasterio.open(EXTERNAL / "geodawn_extensions_u8.tif") as ds_ext:
        tmi_up150_u8 = ds_ext.read(4)

    print("[POOL-1] Building/loading static caches (MSDB18, CSR26, LiDAR17)...", flush=True)
    msdb = build_or_load_msdb_cache(base, valid, PROCESSED / "msdb_v2", prereg["dataset_signature"])
    csr_static = build_or_load_csr_cache(base, valid, tmi_up150_u8, PROCESSED / "csr1_static",
                                         prereg["dataset_signature"],
                                         ext_pins["ext_geodawn_extensions_u8"]["sha256"])
    lidar = build_or_load_lidar_cache(valid, ext_pins["ext_lidar_scarp_features_u8"]["sha256"])
    del tmi_up150_u8
    print(f"[POOL-1] Caches ready at {time.monotonic() - t0:.0f}s", flush=True)

    feature_names = list(CORE_FEATURES) + list(MSDB_FEATURES) + list(CSR_ALL_DERIVED_NAMES) + list(LIDAR_FEATURES)
    assert len(feature_names) == 81
    dump_json(REPORT / "feature-receipt.json", {
        "schema_version": 1, "transform_version": TRANSFORM_VERSION, "support_px": SUPPORT_PX,
        "guard_px": GUARD_PX, "dataset_signature": prereg["dataset_signature"], "external_pins": ext_pins,
        "csr_static_finite_pixels_in_footprint": {
            CSR_STATIC_FEATURE_NAMES[i]: int(np.count_nonzero(np.isfinite(csr_static[i]) & valid))
            for i in range(len(CSR_STATIC_FEATURE_NAMES))}})

    msdb_cols = list(MSDB_RAW_KEEP_INDICES) + [19 + j for j in range(18)]
    pool_cols = (list(MSDB_RAW_KEEP_INDICES) + [19 + j for j in range(18)]
                 + [37 + j for j in range(27)] + [64 + j for j in range(17)])
    assert len(msdb_cols) == 31 and len(pool_cols) == 75
    dot_budget = int(prereg["dot_budget"])
    seed1, seed2 = int(prereg["primary_seed"]), int(prereg["confirmation_seed"])
    arms = tuple(prereg["arms"])

    def layers_for(kd_resid):
        return ([base[i] for i in range(19)] + [msdb[i] for i in range(18)]
                + [csr_static[i] for i in range(26)] + [kd_resid] + [lidar[i] for i in range(17)])

    def run_experiment(seed, run_arms, with_canaries):
        block_rows = {a: [] for a in run_arms}
        folds, canaries = [], []
        for fold in spatial_segment_folds(labels, valid, buffer_px=GUARD_PX):
            check_budget()
            f = int(fold["fold"])
            kd_resid, kd_meta = fit_kd_alteration_residual(rad_k_u8, rad_th_u8, fold["train_mask"], valid)
            stack = LayerStack(layers_for(kd_resid))
            x_all, y = sample_training_pixels(stack, fold["visible"], fold["train_mask"],
                                              negatives_per_positive=6, seed=seed + f)
            if with_canaries:
                print(f"  [seed {seed} fold {f}] 81-feature leakage canaries...", flush=True)
                fc = run_canaries(stack, feature_names, x_all, y, fold, seed + f)
                canaries.append({"fold": f, "kd_fit": kd_meta, "features": fc})
                print(f"  [seed {seed} fold {f}] canaries max_sym_auc="
                      f"{max(r['max_symmetric_auc'] for r in fc):.4f} alarms="
                      f"{sum(r['alarm_above_0_90'] for r in fc)}", flush=True)
            active = fold["score_valid"] & ~fold["visible"]
            count = int(round(dot_budget * int(active.sum()) / int(valid.sum())))
            fold_rec = {**fold["metadata"], "dot_budget_each_arm": count, "arms": {}}

            def score(arm, dots):
                sc = masked_dti_by_blocks(dots, fold["hidden"], fold["visible"],
                                          fold["score_valid"], block_size_px=128)
                block_rows[arm].extend(sc["spatial_blocks"])
                fold_rec["arms"][arm] = {k: v for k, v in sc["pooled"].items() if k != "dti"}
                print(f"    {arm} fold {f} HOLDOUT-DTI = {sc['pooled']['dti']:.6f}", flush=True)
                return sc

            if "msdb_edge" in run_arms:
                print(f"  [seed {seed} fold {f}] msdb_edge (budget={count})...", flush=True)
                surf = fit_and_predict_surface(stack=stack, msdb_cache=msdb, x_all=x_all, y=y,
                                               cols=msdb_cols, train_mask=fold["train_mask"],
                                               visible_mask=fold["visible"], predict_domain=active,
                                               seed=seed + f)
                dots = select_msdb_edge_dots(surf, active, count)
                del surf
                score("msdb_edge", dots)
                del dots
            if "pool_dense_edge" in run_arms or "pool_dispersed" in run_arms:
                print(f"  [seed {seed} fold {f}] pooled surface (budget={count})...", flush=True)
                surf = fit_and_predict_surface(stack=stack, msdb_cache=msdb, x_all=x_all, y=y,
                                               cols=pool_cols, train_mask=fold["train_mask"],
                                               visible_mask=fold["visible"], predict_domain=active,
                                               seed=seed + f)
                if "pool_dense_edge" in run_arms:
                    dots = select_msdb_edge_dots(surf, active, count)
                    score("pool_dense_edge", dots)
                    del dots
                if "pool_dispersed" in run_arms:
                    dots = select_csr_dispersed_dots(
                        surf, active, count, gamma=float(prereg["ridge_concentration_gamma"]),
                        min_sq_dist_excl=int(prereg["min_interdot_sq_dist_exclusive"]))
                    score("pool_dispersed", dots)
                    del dots
                del surf
            folds.append(fold_rec)
            del x_all, y, kd_resid, stack
        summary = spatial_bootstrap(block_rows, candidate="pool_dispersed",
                                    replicates=int(prereg["bootstrap_replicates"]),
                                    seed=int(prereg["bootstrap_seed"]))
        return summary, folds, canaries

    print(f"[POOL-1] Experiment 1 (seed={seed1})...", flush=True)
    experiments_run = 1
    summary_e1, folds_e1, canaries_e1 = run_experiment(seed1, arms, with_canaries=True)
    alarms = [{"fold": c["fold"], **r} for c in canaries_e1 for r in c["features"] if r["alarm_above_0_90"]]
    max_sym_auc = max(r["max_symmetric_auc"] for c in canaries_e1 for r in c["features"])
    delta_msdb = summary_e1["candidate_minus"]["msdb_edge"]
    delta_dense = summary_e1["candidate_minus"]["pool_dense_edge"]
    e1_pass = (not alarms and float(delta_msdb["value"]) > 0.0 and float(delta_msdb["ci95"][0]) > 0.0)
    print(f"[POOL-1] E1 pooled: msdb_edge={summary_e1['arms']['msdb_edge']['value']:.6f} "
          f"pool_dense={summary_e1['arms']['pool_dense_edge']['value']:.6f} "
          f"pool_dispersed={summary_e1['arms']['pool_dispersed']['value']:.6f} "
          f"(vs msdb {delta_msdb['value']:+.6f} CI [{delta_msdb['ci95'][0]:+.6f},{delta_msdb['ci95'][1]:+.6f}]); "
          f"canary alarms={len(alarms)} max_auc={max_sym_auc:.4f}; gate={e1_pass}", flush=True)

    confirmation_summary, e2_pass = None, False
    if e1_pass:
        experiments_run += 1
        print(f"[POOL-1] Experiment 2 confirmation (seed={seed2})...", flush=True)
        confirmation_summary, _, _ = run_experiment(seed2, ("msdb_edge", "pool_dispersed"),
                                                    with_canaries=False)
        d2 = confirmation_summary["candidate_minus"]["msdb_edge"]
        e2_pass = float(d2["value"]) > 0.0 and float(d2["ci95"][0]) > 0.0
        print(f"[POOL-1] E2: pool_dispersed={confirmation_summary['arms']['pool_dispersed']['value']:.6f} "
              f"vs msdb_edge={confirmation_summary['arms']['msdb_edge']['value']:.6f} "
              f"(diff {d2['value']:+.6f} CI [{d2['ci95'][0]:+.6f},{d2['ci95'][1]:+.6f}]); gate={e2_pass}", flush=True)

    experiments_run += 1
    check_budget()
    prod_seeds = [seed1, seed2] if (e1_pass and e2_pass) else [seed1]
    print(f"[POOL-1] Experiment {experiments_run} production fit (seeds={prod_seeds})...", flush=True)
    kd_full, kd_full_meta = fit_kd_alteration_residual(rad_k_u8, rad_th_u8, valid, valid)
    prod_stack = LayerStack(layers_for(kd_full))
    surface_acc = np.zeros(valid.shape, dtype=np.float32)
    for s in prod_seeds:
        check_budget()
        x_full, y_full = sample_training_pixels(prod_stack, labels, valid,
                                                negatives_per_positive=6, seed=s + 90)
        surf_s = fit_and_predict_surface(stack=prod_stack, msdb_cache=msdb, x_all=x_full, y=y_full,
                                         cols=pool_cols, train_mask=valid, visible_mask=labels,
                                         predict_domain=valid, seed=s + 90)
        surface_acc += surf_s / np.float32(len(prod_seeds))
        del x_full, y_full, surf_s
    del kd_full, prod_stack

    tpl_path = ROOT / "data/raw/sample_submission.tif"
    surf_tif = RUN_DIR / "pool1_continuous_surface.tif"
    write_surface_geotiff(surface_acc, tpl_path, surf_tif)
    print("[POOL-1] Stage-1 surface novelty audit (394 rasters)...", flush=True)
    surface_novelty = audit_novelty(surf_tif, tpl_path, reg_path, "surface")
    dump_json(REPORT / "novelty-surface.json", surface_novelty)
    max_surf_rho = max((float(r["spearman_full_footprint"]) for r in surface_novelty["comparisons"]
                        if r["spearman_full_footprint"] is not None), default=0.0)
    surface_dup = (any(r.get("identical_inside_footprint") or
                       (r["spearman_full_footprint"] is not None and float(r["spearman_full_footprint"]) > 0.90)
                       for r in surface_novelty["comparisons"]) or bool(surface_novelty.get("errors")))
    print(f"[POOL-1] Stage-1 max Spearman={max_surf_rho:.6f} duplicate_or_err={surface_dup}", flush=True)

    dist_cat = distance_transform_edt(~labels)
    off_cat = valid & (dist_cat > float(prereg["off_catalogue_min_distance_px"]))
    prod_dots = select_csr_dispersed_dots(surface_acc, off_cat, dot_budget,
                                          gamma=float(prereg["ridge_concentration_gamma"]),
                                          min_sq_dist_excl=int(prereg["min_interdot_sq_dist_exclusive"]))
    del surface_acc
    with rasterio.open(tpl_path) as tpl_ds:
        fp_mask = valid_template_mask(tpl_ds, np)
    values_sha = hashlib.sha256(np.ascontiguousarray(prod_dots[fp_mask], dtype=np.float32).tobytes()).hexdigest()
    run_id = f"gems30-POOL1-{dot_budget}-20261027-{values_sha[:12]}"
    runs_tif = RUN_DIR / f"{run_id}-zeros.tif"
    write_submission_file(prod_dots, tpl_path, runs_tif, note=NOTE_TEMPLATE, run_name=run_id,
                          metadata_path=runs_tif.with_suffix(".json"), outside_value=0.0)
    val_report = validate_submission_file(runs_tif, tpl_path, require_finite_all_cells=True, portal_safe=True)
    with rasterio.open(runs_tif) as out_ds:
        whole = out_ds.read(1)
    pts = np.argwhere(whole > 0.5).astype(np.float64)
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    d_at_dots = dist_cat[whole > 0.5]
    dots_le2 = int(np.count_nonzero(d_at_dots <= 2.0))
    whole_ok = bool(np.isfinite(whole).all() and float(whole.min()) >= 0.0 and float(whole.max()) <= 1.0)
    if not val_report.passed or not whole_ok or dots_le2 != 0:
        raise RuntimeError(f"submission validation failed: {val_report.to_dict()} whole_ok={whole_ok} dots_le2={dots_le2}")

    print("[POOL-1] Stage-2 dots novelty audit (394 rasters)...", flush=True)
    dots_novelty = audit_novelty(runs_tif, tpl_path, reg_path, "dots")
    dump_json(REPORT / "novelty-dots.json", dots_novelty)
    max_dot_rho = max((float(r["spearman_full_footprint"]) for r in dots_novelty["comparisons"]
                       if r["spearman_full_footprint"] is not None), default=0.0)
    top_row = max(dots_novelty["comparisons"],
                  key=lambda r: float(r["candidate_fraction_within_3px_of_reference"] or 0.0))
    max_overlap = float(top_row["candidate_fraction_within_3px_of_reference"] or 0.0)
    dots_dup = (any(r.get("identical_inside_footprint") or
                    (r["spearman_full_footprint"] is not None and float(r["spearman_full_footprint"]) > 0.90) or
                    float(r["candidate_fraction_within_3px_of_reference"] or 0.0) > 0.70
                    for r in dots_novelty["comparisons"]) or bool(dots_novelty.get("errors")))
    print(f"[POOL-1] Stage-2 max Spearman={max_dot_rho:.6f} max 3px overlap={max_overlap:.6f} "
          f"(vs {top_row['reference']}) duplicate_or_err={dots_dup}", flush=True)

    # Separate transparent audit vs the 6 dense-parent calibration exclusions.
    registry = json.loads(reg_path.read_text())
    calib_rows = []
    cached = novelty_rank_cache(whole, fp_mask)
    for row in registry.get("calibration_exclusions", []):
        with rasterio.open(ROOT / row["path"]) as ds:
            ref = ds.read(1)
        stats = novelty_compare(whole, ref, fp_mask, stage="dots", cached_ranks=cached)
        calib_rows.append({"reference": row["path"], "site": row.get("site"),
                           "reference_sha256": row["sha256"], **stats})
    dump_json(REPORT / "novelty-calibration-parents.json", {
        "schema_version": 1, "candidate": str(runs_tif.relative_to(ROOT)),
        "note": "Dense pre-thinning parents/unions (>100k positive px) excluded from the dotted-submission duplicate gate; reported here in full, never hidden.",
        "comparisons": calib_rows})

    duplicate_stop = bool(surface_dup or dots_dup)
    tif_rel = None
    if not duplicate_stop:
        tif_rel = Path(f"docs/downloads/{run_id}-zeros.tif")
        shutil.copyfile(runs_tif, ROOT / tif_rel)
        meta = json.loads(runs_tif.with_suffix(".json").read_text())
        dump_json((ROOT / tif_rel).with_suffix(".json"), meta)
        # Novelty audits were run on byte-identical values; verify the public copy.
        with rasterio.open(ROOT / tif_rel) as pub:
            pub_whole = pub.read(1)
        assert np.array_equal(pub_whole, whole)
    raster_sha = sha256_file(ROOT / tif_rel) if tif_rel else sha256_file(runs_tif)

    elapsed = round(time.monotonic() - t0, 2)
    results_payload = {
        "schema_version": 1, "experiment_spec": "pool1", "lane": "POOL-1",
        "transform_version": TRANSFORM_VERSION, "dataset_signature": prereg["dataset_signature"],
        "preregistration_md_sha256": prereg_md_sha, "preregistration_json_sha256": prereg_json_sha,
        "kd_full_fit": kd_full_meta, "summary": summary_e1, "confirmation_seed4219": confirmation_summary,
        "folds": folds_e1, "feature_canaries": canaries_e1, "canary_alarms": alarms,
        "max_feature_symmetric_auc": max_sym_auc, "ablation_dispersed_minus_dense": delta_dense,
        "experiments_run": experiments_run, "experimental_elapsed_seconds": elapsed}
    dump_json(REPORT / "results.json", results_payload)

    validator_output = {
        "status": "passed", "no_nan_inside_footprint": True, "no_nan_anywhere": whole_ok,
        "values_in_0_1_inside_footprint": True, "values_in_0_1_whole_array": whole_ok,
        "min_whole_array": float(whole.min()), "max_whole_array": float(whole.max()),
        "crs_match": True, "shape_match": True, "transform_match": True,
        "single_float32_band": True, "outside_footprint_value": 0.0,
        "positive_catalogue_pixels": int(np.count_nonzero((whole > 0.5) & labels)),
        "dots_within_2px_of_catalogue": dots_le2,
        "emitted_dots": int(np.count_nonzero(whole > 0.5)),
        "min_interdot_nn_px": float(nn.min()), "p10_interdot_nn_px": float(np.quantile(nn, 0.10)),
        "median_interdot_nn_px": float(np.median(nn)),
        "catalogue_distance_quantiles_px": {
            "p10": float(np.quantile(d_at_dots, 0.10)), "p25": float(np.quantile(d_at_dots, 0.25)),
            "p50": float(np.quantile(d_at_dots, 0.50)), "p75": float(np.quantile(d_at_dots, 0.75)),
            "p90": float(np.quantile(d_at_dots, 0.90)),
            "frac_gt_5px": float(np.mean(d_at_dots > 5.0)), "frac_gt_15px": float(np.mean(d_at_dots > 15.0)),
            "frac_gt_50px": float(np.mean(d_at_dots > 50.0))},
        "organizer_acceptance_confirmed": False, "submission_report": val_report.to_dict()}
    dump_json(REPORT / "validation.json", validator_output)

    lane_pass = bool(e1_pass and e2_pass and not duplicate_stop and whole_ok and dots_le2 == 0)
    cand = summary_e1["arms"]["pool_dispersed"]
    card = {
        "schema_version": 1, "experiment_spec": "pool1", "run_id": run_id,
        "submission_name": run_id, "note": NOTE_TEMPLATE,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lane": "POOL-1 (preregistered 2026-10-27 before any fold fit)",
        "lane_preregistration_sha256": prereg_md_sha, "externally_assigned_lane_verified": False,
        "hypothesis": ("Pooling MSDB-1v2's 18 piedmont/curvilinear features with CSR-1's 27 "
                       "cover-compensated Laplace/Poisson + 1.8 km Radon features and 17 LiDAR "
                       "morphology bands in ONE HGB lets the trees learn the Walker Lane regime "
                       "interaction that made CSR-1 win Fold 3 (+0.02300) while MSDB won Folds 0-2, "
                       "beating msdb_edge pooled under the identical buffered holdout."),
        "mechanism": ("75-feature HGB (13 stationary raw + MSDB-18 + CSR-27 + LiDAR-17), Prentice-Pyke "
                      "case-control calibration x MSDB Rayleigh curvilinear gate, 1D Hessian ridge "
                      "concentration (gamma=1.25) and dispersed submodular 300 m EDGE emission "
                      "(dr^2+dc^2>6, >2 px off-catalogue, 44,090 dots)."),
        "non_fault_mimic": ("Buried pluton/caldera margins, incised bedrock paleochannels, unreactivated "
                            "Mesozoic contacts, saline playa clay pans, Lake Lahontan recessional "
                            "shorelines, volcanic flow fronts."),
        "experiments_run": experiments_run, "experiment_cap": int(prereg["max_experiments"]),
        "experimental_elapsed_seconds": elapsed, "dataset_signature": prereg["dataset_signature"],
        "published_tiff": str(tif_rel) if tif_rel else None,
        "tif_path": str(tif_rel) if tif_rel else str(runs_tif.relative_to(ROOT)),
        "sha256": raster_sha, "raster_sha256": raster_sha, "values_sha256": values_sha,
        "holdout_dti": float(cand["value"]), "ci95": list(cand["ci95"]),
        "baseline_dti": {"msdb_edge": float(summary_e1["arms"]["msdb_edge"]["value"]),
                         "pool_dense_edge": float(summary_e1["arms"]["pool_dense_edge"]["value"])},
        "max_feature_auc": max_sym_auc, "max_registry_corr": max(max_surf_rho, max_dot_rho),
        "dot_overlap_pct": round(100.0 * max_overlap, 4),
        "holdout": {"label": "HOLDOUT-DTI", **cand,
                    "evaluator_version": summary_e1["evaluator_version"],
                    "protocol_version": summary_e1["protocol_version"],
                    "bootstrap": summary_e1["bootstrap"],
                    "comparators": {k: summary_e1["arms"][k] for k in ("msdb_edge", "pool_dense_edge")},
                    "candidate_minus": summary_e1["candidate_minus"],
                    "confirmation_seed4219": confirmation_summary},
        "feature_canaries": {"features_per_fold": len(feature_names), "folds": 4,
                             "alarms": alarms, "max_auc_either_direction": max_sym_auc},
        "registry": {"registry_path": prereg["registry_path"], "registry_sha256": prereg["registry_sha256"],
                     "aligned_rasters_compared": len(dots_novelty["comparisons"]),
                     "malformed_exclusions_audited": len(dots_novelty.get("malformed_exclusions_audited", [])),
                     "calibration_parents_reported_separately": len(calib_rows),
                     "surface_max_spearman": max_surf_rho, "dots_max_spearman": max_dot_rho,
                     "dots_max_fraction_within_3px": max_overlap,
                     "dots_closest_reference": top_row["reference"],
                     "dots_closest_reference_site": top_row.get("site"),
                     "duplicate_stop": duplicate_stop},
        "validator_output": validator_output,
        "historical_best_rerun": {"verified": True, "benchmark_arm": "msdb_edge",
                                  "evaluator_version": summary_e1["evaluator_version"],
                                  "protocol_version": summary_e1["protocol_version"],
                                  "candidate_beats_best_with_paired_ci": bool(e1_pass and e2_pass)},
        "lane_scientific_gates_all_passed": lane_pass,
        "lane_scientific_verdict": "promote" if lane_pass else "negative",
        "verdict": "promote" if lane_pass else "negative",
        "submission_approved": False, "slot_selected": False,
        "download_ok": bool(tif_rel and not duplicate_stop), "ok_to_submit": False,
        "organizer_score": None}
    readiness = assess_readiness(
        card, results_payload,
        format_passed=bool(val_report.passed and whole_ok and dots_le2 == 0),
        hash_matches=True, surface_audit=surface_novelty, dots_audit=dots_novelty,
        registry=registry, artifact_public=bool(tif_rel))
    dump_json(REPORT / "readiness.json", readiness)
    card["global_readiness_verdict"] = readiness["research_verdict"]
    card["download_ok"] = bool(readiness["download_ok"])
    card["display_status"] = (
        "LANE PROMOTED — OWNER SLOT SELECTION REQUIRED BEFORE PORTAL UPLOAD" if lane_pass
        else "NEGATIVE — DO NOT SUBMIT TO PORTAL" + (" (research download OK)" if tif_rel else " (no TIFF published)"))
    dump_json(REPORT / "run-card.json", card)
    print(f"[POOL-1] Done in {elapsed:.0f}s -> {tif_rel} ({card['display_status']})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
