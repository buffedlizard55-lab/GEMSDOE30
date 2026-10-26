"""Unit tests for translation-invariant tilt-alteration features and decensored collar emission."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt

from gemsdoe30.tilt_alteration import (
    BAND_IDX,
    STATIC_DERIVED_NAMES,
    SUBSURFACE_FEATURES,
    SUPPORT_PX,
    TAD_FEATURES,
    assemble_tad_layers,
    build_hydrothermal_impulse,
    calibrate_oof_by_training_quantiles,
    compute_static_derived_layers,
    decensored_collar_select,
    exact_operator_support_px,
    fit_apply_rad_kd,
    sobel_xy_safe,
)


def test_exact_operator_support_fits_within_v3_spatial_guard():
    measured = exact_operator_support_px(grid_size=49)
    assert measured == 15
    assert measured <= SUPPORT_PX


def test_footprint_isolation_blocks_outside_nan_and_extreme_values():
    rng = np.random.default_rng(7)
    h, w = 41, 43
    valid = np.zeros((h, w), dtype=bool)
    valid[5:36, 6:37] = True

    base_a = rng.normal(0.0, 1.0, size=(19, h, w)).astype(np.float32)
    base_a[BAND_IDX["cond_surf"]] = np.abs(base_a[BAND_IDX["cond_surf"]]) + 0.5
    rad_a = rng.integers(5, 220, size=(4, h, w), dtype=np.uint8)
    ext_a = rng.integers(5, 220, size=(4, h, w), dtype=np.uint8)
    lidar_a = rng.integers(5, 220, size=(12, h, w), dtype=np.uint8)
    lidar_a[-1] = 255
    hydro_a = np.zeros((h, w), dtype=np.float32)
    hydro_a[20, 20] = 2.0

    base_b = base_a.copy()
    base_b[:, ~valid] = np.nan
    rad_b = rad_a.copy()
    rad_b[:, ~valid] = 255
    ext_b = ext_a.copy()
    ext_b[:, ~valid] = 0
    lidar_b = lidar_a.copy()
    lidar_b[:, ~valid] = 255
    hydro_b = hydro_a.copy()
    hydro_b[~valid] = 1e6

    out_a = compute_static_derived_layers(
        base_a, valid, rad_u8=rad_a, ext_u8=ext_a, lidar_u8=lidar_a, hydro_impulse=hydro_a
    )
    out_b = compute_static_derived_layers(
        base_b, valid, rad_u8=rad_b, ext_u8=ext_b, lidar_u8=lidar_b, hydro_impulse=hydro_b
    )
    for name in STATIC_DERIVED_NAMES:
        assert np.all(np.isnan(out_a[name][~valid]))
        assert np.all(np.isnan(out_b[name][~valid]))
        np.testing.assert_allclose(out_a[name][valid], out_b[name][valid], rtol=0, atol=1e-6)


def test_constant_field_sobel_has_zero_gradient_on_irregular_footprint_boundary():
    valid = np.zeros((15, 15), dtype=bool)
    valid[3:12, 4:11] = True
    valid[6, 6] = False
    arr = np.where(valid, 42.5, np.nan).astype(np.float32)
    gx, gy = sobel_xy_safe(arr, valid)
    assert np.all(gx[valid] == 0.0)
    assert np.all(gy[valid] == 0.0)
    assert np.all(np.isnan(gx[~valid]))


def test_fold_safe_rad_kd_never_uses_heldout_pixels():
    rng = np.random.default_rng(11)
    valid = np.ones((20, 20), dtype=bool)
    train = np.zeros((20, 20), dtype=bool)
    train[:10, :] = True

    th = rng.integers(20, 100, size=(20, 20), dtype=np.uint8)
    k_a = np.clip(2 * th.astype(int) + 10, 1, 254).astype(np.uint8)
    k_b = k_a.copy()
    # Corrupt held-out region severely; training OLS parameters and training residuals must not change.
    k_b[~train] = 250

    kd_a, meta_a = fit_apply_rad_kd(k_a, th, valid, train)
    kd_b, meta_b = fit_apply_rad_kd(k_b, th, valid, train)
    assert meta_a == meta_b
    np.testing.assert_array_equal(kd_a[train], kd_b[train])


def test_hydrothermal_impulse_ignores_dist_known_fault_px(tmp_path: Path):
    csv_a = tmp_path / "ws_a.csv"
    csv_b = tmp_path / "ws_b.csv"
    header = "row,col,dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c\n"
    csv_a.write_text(header + "4,5,0.0,35.0,110.0,95.0,140.0\n8,9,0.1,20.0,80.0,75.0,82.0\n")
    csv_b.write_text(header + "4,5,999.9,35.0,110.0,95.0,140.0\n8,9,500.0,20.0,80.0,75.0,82.0\n")

    valid = np.ones((12, 12), dtype=bool)
    paleo = np.zeros((12, 12), dtype=np.uint8)
    paleo[2, 3] = 1
    probes = np.zeros((12, 12), dtype=np.uint8)
    imp_a, counts_a = build_hydrothermal_impulse(paleo, probes, csv_a, valid)
    imp_b, counts_b = build_hydrothermal_impulse(paleo, probes, csv_b, valid)
    assert counts_a == counts_b == {"paleo_sinter_pixels": 1, "probe_2m_pixels": 0, "geothermometer_upflow_pixels": 1}
    np.testing.assert_array_equal(imp_a, imp_b)
    assert imp_a[4, 5] == pytest.approx(1.5)
    assert imp_a[8, 9] == 0.0


def test_decensored_collar_select_respects_h33_exclusion_spacing_and_quotas():
    rng = np.random.default_rng(99)
    h, w = 120, 120
    valid = np.ones((h, w), dtype=bool)
    cat = np.zeros((h, w), dtype=bool)
    cat[60, 20:100] = True
    surface = rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32)

    dots, realized = decensored_collar_select(surface, valid, cat, total_dots=200, min_spacing_px=3.0)
    assert int((dots > 0).sum()) == 200
    assert realized == {"far_gt_30px": 60, "mid_10_to_30px": 80, "near_2_to_10px": 60, "fallback_rollover": 0}
    d_cat = distance_transform_edt(~cat)
    pts = np.argwhere(dots > 0)
    assert np.all(d_cat[pts[:, 0], pts[:, 1]] > 2.0)
    # Pairwise Euclidean distance >= 3.0 px for all emitted dots.
    diffs = pts[:, None, :] - pts[None, :, :]
    d2 = np.sum(diffs * diffs, axis=-1).astype(float)
    np.fill_diagonal(d2, np.inf)
    assert float(d2.min()) >= 9.0 - 1e-9


def test_assemble_tad_layers_length_and_calibration_bounds():
    assert len(SUBSURFACE_FEATURES) == 16
    assert len(TAD_FEATURES) == 24
    rng = np.random.default_rng(3)
    p = rng.uniform(0.0, 0.5, size=(10, 10)).astype(np.float32)
    tr = np.zeros((10, 10), dtype=bool)
    tr[:5, :] = True
    sc = ~tr
    cal = calibrate_oof_by_training_quantiles(p, tr, sc)
    assert np.all(cal[tr] == 0.0)
    assert np.all((cal[sc] >= 0.0) & (cal[sc] <= 1.0))
    dummy = np.zeros((4, 4), dtype=np.float32)
    layers = assemble_tad_layers(np.zeros((19, 4, 4), dtype=np.float32), {k: dummy for k in STATIC_DERIVED_NAMES}, dummy)
    assert len(layers) == 24
