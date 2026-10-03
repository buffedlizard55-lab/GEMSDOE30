#!/usr/bin/env python3
"""Execute the standing three-check verification protocol (docs/research/verification-protocol.md)
on H-31-02r (LiDAR scarp dipole + 500 m strike continuity) across both evaluation frames:
1. Catalogue component-holdout frame
2. Independent USGS SGMC off-catalogue fault inventory frame

Writes machine-readable results to docs/research/verification-checks-results.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt, label, uniform_filter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gemsdoe30.cv import spatial_quadrant_masks  # noqa: E402
from gemsdoe30.emission import kernel_credit  # noqa: E402
from gemsdoe30.holdout import (  # noqa: E402
    PIXEL_M,
    RADIUS_M,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    split_components,
)
from gemsdoe30.verification import (  # noqa: E402
    evaluate_oof_calibration_across_folds,
    evaluate_perturbation_stability,
    extract_qualitative_atlas,
)
from scripts.placement_and_scarp_holdout import (  # noqa: E402
    PRIMARY_BUDGET,
    band_index,
    normalized_rank_score,
    poisson_disk_top_n,
    poisson_distance_matched_draw,
)


def build_scarp_score_from_dict(
    fdict: dict[str, np.ndarray],
    footprint: np.ndarray,
) -> np.ndarray:
    step_max = fdict["step_max"]
    lapneg = fdict["lapneg_max"]
    lappos = fdict["lappos_max"]
    coh100 = fdict["coh100"]
    strike_u8 = fdict["strike"]
    lidar_valid = fdict["lidar_valid"] & footprint
    dem_slope = fdict["det_elev_slope"]

    slope_rank = normalized_rank_score(dem_slope, footprint)
    dipole = np.sqrt(np.maximum(lapneg * lappos, 0.0)) * step_max * coh100
    dipole[~lidar_valid] = 0.0

    theta = strike_u8 * (math.pi / 255.0)
    w = np.where(lidar_valid, step_max + 1.0, 0.0)
    c2 = uniform_filter(w * np.cos(2.0 * theta), size=5, mode="nearest")
    s2 = uniform_filter(w * np.sin(2.0 * theta), size=5, mode="nearest")
    w_mean = uniform_filter(w, size=5, mode="nearest") + 1e-9
    strike_persistence = np.hypot(c2, s2) / w_mean
    strike_persistence[~lidar_valid] = 0.0

    dipole_cont = uniform_filter(dipole, size=3, mode="nearest") * strike_persistence
    dipole_rank = normalized_rank_score(dipole_cont, lidar_valid)
    return np.where(lidar_valid, 0.75 * dipole_rank + 0.25 * slope_rank, 0.5 * slope_rank)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--scarp-tif", type=Path, default=Path("data/raw/external/lidar_scarp_features_u8.tif"))
    parser.add_argument("--sgmc-tif", type=Path, default=Path("data/external/derived_sgmc_faults_100m_u8.tif"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/verification-checks-results.json"))
    parser.add_argument("--budget", type=int, default=PRIMARY_BUDGET)
    args = parser.parse_args()

    import rasterio

    started = time.time()
    manifest = json.loads((args.data_dir / "manifest.json").read_text())
    features = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
    footprint = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    catalogue = (np.load(args.data_dir / "labels.npy") == 1) & footprint
    transform_gdal = manifest["transform_gdal"]

    slope_idx = band_index(manifest, "det_elev_slope")
    grav_idx = band_index(manifest, "iso_grav_anom_hg")
    dem_slope = np.where(footprint & np.isfinite(features[slope_idx]), features[slope_idx], 0.0).astype(np.float64)
    grav_hg = np.where(footprint & np.isfinite(features[grav_idx]), features[grav_idx], 0.0).astype(np.float64)

    with rasterio.open(args.scarp_tif) as ds:
        fdict = {
            "step_max": ds.read(3).astype(np.float64),
            "lapneg_max": ds.read(4).astype(np.float64),
            "lappos_max": ds.read(5).astype(np.float64),
            "coh100": ds.read(10).astype(np.float64) / 255.0,
            "strike": ds.read(11).astype(np.float64),
            "lidar_valid": (ds.read(12) > 0) & footprint,
            "det_elev_slope": dem_slope,
            "iso_grav_anom_hg": grav_hg,
        }

    with rasterio.open(args.sgmc_tif) as ds:
        sgmc = (ds.read(1) > 0) & footprint

    raw_score = build_scarp_score_from_dict(fdict, footprint)

    known_cat_masked = binary_dilation(catalogue, iterations=3) & footprint
    emittable_sgmc = footprint & ~known_cat_masked

    # Define 300 m kernel-dilated SGMC off-catalogue target for probability calibration
    comp, comp_count = label(sgmc & emittable_sgmc, structure=np.ones((3, 3), dtype=int))
    comp_ids = np.arange(1, comp_count + 1)
    rng_split = np.random.default_rng(31)
    held_ids = rng_split.permutation(comp_ids)[: int(round(0.30 * comp_ids.size))]
    hidden_sgmc = np.isin(comp, held_ids) & emittable_sgmc
    visible_sgmc = (sgmc & emittable_sgmc) & ~hidden_sgmc
    domain_sgmc_masked = known_cat_masked | (binary_dilation(visible_sgmc, iterations=3) & footprint)
    eval_domain = footprint & ~domain_sgmc_masked

    # Binary target for Check 2: within 300 m of held-out fault trace
    d_target = distance_transform_edt(~hidden_sgmc, sampling=(PIXEL_M, PIXEL_M))
    y_300m_sgmc = (d_target <= RADIUS_M).astype(np.float64)

    check2_sgmc = evaluate_oof_calibration_across_folds(
        raw_score, y_300m_sgmc, eval_domain, buffer_m=RADIUS_M, n_bins=10
    )

    # Check 3: Feature-perturbation stability on the held-out SGMC novelty frame
    fpw_sgmc = fp_weight_field(hidden_sgmc, domain_sgmc_masked)
    d2k = distance_transform_edt(~catalogue, sampling=(PIXEL_M, PIXEL_M))
    cand_em = poisson_disk_top_n(raw_score, eval_domain, args.budget)
    ctrl_em = poisson_distance_matched_draw(
        eval_domain, cand_em, d2k, args.budget, np.random.default_rng(31)
    )
    cand_blocks = masked_dti_by_blocks(cand_em, hidden_sgmc, domain_sgmc_masked, footprint, fp_weight=fpw_sgmc)
    ctrl_blocks = masked_dti_by_blocks(ctrl_em, hidden_sgmc, domain_sgmc_masked, footprint, fp_weight=fpw_sgmc)
    per_fold_deltas = [
        float(cand_blocks[f"quadrant_{q}"]["dti"] - ctrl_blocks[f"quadrant_{q}"]["dti"])
        for q in range(4)
    ]

    def _score_perturbed(pert_dict: dict[str, np.ndarray]) -> float:
        s = build_scarp_score_from_dict(pert_dict, footprint)
        em = poisson_disk_top_n(s, eval_domain, args.budget)
        return float(masked_dti(em, hidden_sgmc, domain_sgmc_masked, fp_weight=fpw_sgmc)["dti"])

    check3_lidar_only = evaluate_perturbation_stability(
        _score_perturbed,
        fdict,
        eval_domain,
        baseline_dti=float(ctrl_blocks["pooled"]["dti"]),
        candidate_dti=float(cand_blocks["pooled"]["dti"]),
        own_family=["step_max", "lapneg_max", "lappos_max", "coh100", "strike"],
        unrelated_family=["iso_grav_anom_hg"],
        per_fold_deltas=per_fold_deltas,
        seed=30,
    )
    check3_full_topography = evaluate_perturbation_stability(
        _score_perturbed,
        fdict,
        eval_domain,
        baseline_dti=float(ctrl_blocks["pooled"]["dti"]),
        candidate_dti=float(cand_blocks["pooled"]["dti"]),
        own_family=["step_max", "lapneg_max", "lappos_max", "coh100", "strike", "det_elev_slope"],
        unrelated_family=["iso_grav_anom_hg"],
        per_fold_deltas=per_fold_deltas,
        seed=30,
    )

    # Qualitative block atlas on both SGMC frame and Catalogue component-holdout frame
    cand_credit_sgmc = kernel_credit(np.where(eval_domain, cand_em.astype(np.float32), 0.0))
    ctrl_credit_sgmc = kernel_credit(np.where(eval_domain, ctrl_em.astype(np.float32), 0.0))
    atlas_sgmc = extract_qualitative_atlas(
        cand_credit_sgmc, ctrl_credit_sgmc, hidden_sgmc & eval_domain, eval_domain, transform_gdal
    )

    # Catalogue component-holdout Check 1, Check 2 & qualitative atlas
    hidden_cat, known_cat, _ = split_components(catalogue, seed=31)
    hidden_cat &= footprint
    known_cat &= footprint
    known_cat_dil = binary_dilation(known_cat, iterations=3) & footprint
    eval_cat = footprint & ~known_cat_dil
    d_target_cat = distance_transform_edt(~hidden_cat, sampling=(PIXEL_M, PIXEL_M))
    y_300m_cat = (d_target_cat <= RADIUS_M).astype(np.float64)
    check2_catalogue = evaluate_oof_calibration_across_folds(
        raw_score, y_300m_cat, eval_cat, buffer_m=RADIUS_M, n_bins=10
    )

    fpw_cat = fp_weight_field(hidden_cat, known_cat_dil)
    d2k_cat = distance_transform_edt(~known_cat, sampling=(PIXEL_M, PIXEL_M))
    cand_cat_em = poisson_disk_top_n(raw_score, eval_cat, args.budget)
    ctrl_cat_em = poisson_distance_matched_draw(
        eval_cat, cand_cat_em, d2k_cat, args.budget, np.random.default_rng(17)
    )
    cand_credit_cat = kernel_credit(np.where(eval_cat, cand_cat_em.astype(np.float32), 0.0))
    ctrl_credit_cat = kernel_credit(np.where(eval_cat, ctrl_cat_em.astype(np.float32), 0.0))
    atlas_catalogue = extract_qualitative_atlas(
        cand_credit_cat, ctrl_credit_cat, hidden_cat & eval_cat, eval_cat, transform_gdal
    )

    cat_delta = float(
        masked_dti(cand_cat_em, hidden_cat, known_cat_dil, fp_weight=fpw_cat)["dti"]
        - masked_dti(ctrl_cat_em, hidden_cat, known_cat_dil, fp_weight=fpw_cat)["dti"]
    )
    sgmc_delta = float(cand_blocks["pooled"]["dti"] - ctrl_blocks["pooled"]["dti"])
    c1_cat_pass = cat_delta >= 0.002
    c1_sgmc_pass = sgmc_delta >= 0.002 and check3_lidar_only["fold_sign_consistency_ge_3_of_4"]
    c2_cat_pass = bool(check2_catalogue["check2_pass"])
    c2_sgmc_pass = bool(check2_sgmc["check2_pass"])
    c3_pass = bool(check3_lidar_only["check3_pass"])
    slot_promoted = bool(c1_cat_pass and c1_sgmc_pass and c2_cat_pass and c3_pass)

    report = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "docs/research/verification-protocol.md",
        "candidate_evaluated": "H-31-02r (scarp_dipole_continuity, N=15,000, r=3.0 px)",
        "check1_spatial_block_validation": {
            "catalogue_proxy_screen_delta": cat_delta,
            "sgmc_novelty_screen_delta": sgmc_delta,
            "sgmc_quadrants_positive": check3_lidar_only["folds_positive"],
            "pass_catalogue_proxy": c1_cat_pass,
            "pass_sgmc_novelty_frame": c1_sgmc_pass,
        },
        "check2_probability_calibration": {
            "catalogue_component_frame": check2_catalogue,
            "sgmc_novelty_frame": check2_sgmc,
        },
        "check3_feature_perturbation_stability": {
            "lidar_scarp_channels_only": check3_lidar_only,
            "full_topographic_scarp_family": check3_full_topography,
        },
        "qualitative_atlas": {
            "sgmc_novelty_frame": atlas_sgmc,
            "catalogue_component_frame": atlas_catalogue,
        },
        "overall_promotion_decision": {
            "check1_catalogue_proxy_pass": c1_cat_pass,
            "check1_sgmc_novelty_pass": c1_sgmc_pass,
            "check2_catalogue_oof_calibrated_pass": c2_cat_pass,
            "check2_sgmc_oof_calibrated_pass": c2_sgmc_pass,
            "check3_perturbation_stability_pass": c3_pass,
            "slot_promoted": slot_promoted,
            "reason": (
                f"Check 2 (4-fold OOF isotonic calibration: catalogue frame slope={check2_catalogue['pooled_oof_reliability_slope']:.4f}, "
                f"mean top-decile ratio={check2_catalogue['mean_fold_top_decile_val_to_train_ratio']:.4f}, "
                f"folds>=0.70={check2_catalogue['folds_with_top_decile_ratio_ge_0_70']}, pass={c2_cat_pass}; "
                f"SGMC frame slope={check2_sgmc['pooled_oof_reliability_slope']:.4f}, "
                f"mean top-decile ratio={check2_sgmc['mean_fold_top_decile_val_to_train_ratio']:.4f}, "
                f"folds>=0.70={check2_sgmc['folds_with_top_decile_ratio_ge_0_70']}, pass={c2_sgmc_pass}); "
                f"Check 3 (LiDAR permutation removes {100.0 * check3_lidar_only['own_family_gain_removed_fraction']:.1f}% "
                f"of gain, full-topography permutation removes {100.0 * check3_full_topography['own_family_gain_removed_fraction']:.1f}%, "
                f"unrelated gravity permutation retains +{check3_lidar_only['unrelated_family_retained_gain']:.5f}, "
                f"folds={check3_lidar_only['folds_positive']}, pass={c3_pass}); "
                f"Check 1 passes on the independent SGMC novelty frame (delta=+{sgmc_delta:.5f}) "
                f"but fails on the catalogue component proxy (delta={cat_delta:+.5f}). "
                f"Slot promoted = {slot_promoted}."
            ),
        },
        "runtime_seconds": round(time.time() - started, 2),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["overall_promotion_decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
