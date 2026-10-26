from __future__ import annotations

import math

import numpy as np
import pytest

from gemsdoe30.msdb import (
    EUCLIDEAN_SUPPORT_EXACT_PX,
    IDX_DET_ELEV,
    IDX_GRAV_DX,
    IDX_GRAV_DY,
    IDX_RTP,
    IDX_TC,
    IDX_TMI_HG,
    IDX_TMI_VG,
    MAX_AXIAL_HALFWIDTH_PX,
    MSDB_FEATURE_NAMES,
    SUPPORT_PX,
    calibrate_case_control_probabilities,
    compute_curvilinear_discontinuity_gate,
    compute_msdb_features,
    fit_curvilinear_gate_scales,
    select_msdb_edge_dots,
)


def _equal_or_both_nan(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (np.isnan(a) & np.isnan(b)) | np.isclose(a, b, rtol=0.0, atol=1.0e-6)


def test_msdb_support_bound_strictly_within_holdout_guard() -> None:
    assert MAX_AXIAL_HALFWIDTH_PX == 9
    assert math.isclose(EUCLIDEAN_SUPPORT_EXACT_PX, math.hypot(9, 9))
    assert SUPPORT_PX == 13
    assert SUPPORT_PX <= 17


def test_msdb_perturbation_and_sentinel_influence_bounded_by_9px_box() -> None:
    rng = np.random.default_rng(42)
    h, w = 61, 63
    raw = rng.normal(loc=5.0, scale=2.0, size=(19, h, w)).astype(np.float32)
    raw[IDX_TMI_HG] = np.abs(raw[IDX_TMI_HG]) + 0.5
    valid = np.ones((h, w), dtype=bool)
    base = compute_msdb_features(raw, valid)
    assert base.shape == (len(MSDB_FEATURE_NAMES), h, w)

    r0, c0 = 30, 31
    yy, xx = np.ogrid[:h, :w]
    outside_box = (np.abs(yy - r0) > MAX_AXIAL_HALFWIDTH_PX) | (np.abs(xx - c0) > MAX_AXIAL_HALFWIDTH_PX)
    outside_euclid = np.hypot(yy - r0, xx - c0) > EUCLIDEAN_SUPPORT_EXACT_PX + 1.0e-6

    # 1. Large finite perturbation at (r0, c0) across every band.
    perturbed_finite = raw.copy()
    perturbed_finite[:, r0, c0] += 1000.0
    out_finite = compute_msdb_features(perturbed_finite, valid)
    for k, name in enumerate(MSDB_FEATURE_NAMES):
        same_box = _equal_or_both_nan(base[k][outside_box], out_finite[k][outside_box])
        assert bool(same_box.all()), f"Finite perturbation leaked outside 9-px box in {name}"
        same_euc = _equal_or_both_nan(base[k][outside_euclid], out_finite[k][outside_euclid])
        assert bool(same_euc.all()), f"Finite perturbation leaked outside Euclidean bound in {name}"

    # 2. Float32 sentinel (-3.4e38) injection at (r0, c0).
    perturbed_sentinel = raw.copy()
    perturbed_sentinel[:, r0, c0] = np.float32(-3.4028235e38)
    out_sentinel = compute_msdb_features(perturbed_sentinel, valid)
    for k, name in enumerate(MSDB_FEATURE_NAMES):
        same_euc = _equal_or_both_nan(base[k][outside_euclid], out_sentinel[k][outside_euclid])
        assert bool(same_euc.all()), f"Sentinel mask leaked outside Euclidean bound in {name}"


def test_msdb_hessian_tubularity_and_saddle_physics() -> None:
    h, w = 65, 65
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    cy, cx = 32.0, 32.0
    valid = np.ones((h, w), dtype=bool)

    # Isotropic Gaussian dome: |lambda_1| == |lambda_2| at apex -> tubularity == 0, saddle == 0.
    raw_dome = np.ones((19, h, w), dtype=np.float32)
    raw_dome[IDX_DET_ELEV] = 100.0 * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2.0 * 6.0**2))
    feat_dome = compute_msdb_features(raw_dome, valid)
    assert abs(float(feat_dome[4, 32, 32])) < 1.0e-4  # msdb_topo_tubularity_300m
    assert abs(float(feat_dome[5, 32, 32])) < 1.0e-5  # msdb_topo_saddle_300m

    # 1-D fault ridge along y: strong tubularity along x=cx, high strike coherence.
    raw_ridge = np.ones((19, h, w), dtype=np.float32)
    raw_ridge[IDX_DET_ELEV] = 100.0 * np.exp(-((xx - cx) ** 2) / (2.0 * 3.0**2))
    feat_ridge = compute_msdb_features(raw_ridge, valid)
    assert float(feat_ridge[4, 32, 32]) > 5.0  # strong 1-D tubularity
    assert float(feat_ridge[10, 32, 29]) > 0.95  # 1-D structure tensor coherence

    # Hyperbolic saddle u = (x - cx)^2 - (y - cy)^2: opposite-sign principal curvatures.
    raw_saddle = np.ones((19, h, w), dtype=np.float32)
    raw_saddle[IDX_DET_ELEV] = (xx - cx) ** 2 - (yy - cy) ** 2
    feat_saddle = compute_msdb_features(raw_saddle, valid)
    assert float(feat_saddle[5, 32, 32]) > 10.0  # msdb_topo_saddle_300m


def test_msdb_magnetic_tilt_and_strike_concordance_physics() -> None:
    h, w = 45, 45
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    valid = np.ones((h, w), dtype=bool)
    raw = np.ones((19, h, w), dtype=np.float32)
    # Contact at x = 22: tmi_vg crosses zero, tmi_hg positive.
    raw[IDX_TMI_VG] = xx - 22.0
    raw[IDX_TMI_HG] = np.full((h, w), 5.0, dtype=np.float32)
    # Parallel x-gradients in RTP and reconstructed gravity vector, orthogonal y-gradient in TC.
    raw[IDX_RTP] = 3.0 * xx
    raw[IDX_GRAV_DX] = -2.0 * np.ones((h, w), dtype=np.float32)  # antiparallel still shares strike!
    raw[IDX_GRAV_DY] = np.zeros((h, w), dtype=np.float32)
    raw[IDX_DET_ELEV] = 4.0 * xx
    raw[IDX_TC] = 4.0 * yy  # orthogonal to det_elev

    feat = compute_msdb_features(raw, valid)
    assert abs(float(feat[0, 22, 22])) < 1.0e-6  # tilt == 0 on contact
    assert math.isclose(float(feat[1, 22, 22]), 1.0, rel_tol=1e-5)  # zero-crossing crest == 1
    assert float(feat[13, 22, 22]) > 0.999  # antiparallel gradients -> cos^2(pi) == 1
    assert float(feat[14, 22, 22]) < 1.0e-5  # orthogonal gradients -> cos^2(pi/2) == 0


def test_prentice_pyke_calibration_and_edge_selector_exact_budget() -> None:
    q = np.array([0.0, 0.14285714, 0.5, 0.9, 1.0], dtype=np.float32)
    cal = calibrate_case_control_probabilities(
        q,
        population_positives=40_000,
        population_negatives=4_000_000,
        sample_positives=40_000,
        sample_negatives=240_000,
    )
    assert cal.dtype == np.float32
    assert np.all(np.diff(cal) >= 0)
    # At sample prior q = 1/7 = 0.14285714, calibrated posterior equals population prior 40k / 4040k.
    expected_prior = 40_000 / 4_040_000
    assert math.isclose(float(cal[1]), expected_prior, rel_tol=1e-4)

    rng = np.random.default_rng(7)
    belief = rng.uniform(0.001, 0.2, size=(40, 40)).astype(np.float32)
    active = np.ones((40, 40), dtype=bool)
    active[:5, :] = False
    dots = select_msdb_edge_dots(belief, active, dot_budget=35)
    assert int(np.count_nonzero(dots)) == 35
    assert int(np.count_nonzero(dots[~active])) == 0
    with pytest.raises(ValueError):
        calibrate_case_control_probabilities(q, population_positives=0, population_negatives=10, sample_positives=1, sample_negatives=6)


def test_curvilinear_discontinuity_gate_suppresses_flat_blobs_and_transmits_ridges() -> None:
    h, w = 65, 65
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    valid = np.ones((h, w), dtype=bool)
    raw = np.ones((19, h, w), dtype=np.float32)
    # Sharp 1-D scarp ridge at x = 20; flat basin plain around x = 50.
    raw[IDX_DET_ELEV] = 80.0 * np.exp(-((xx - 20.0) ** 2) / (2.0 * 2.0**2))
    feat = compute_msdb_features(raw, valid)
    train_samples = feat[:, 12:52, 12:52].reshape(len(MSDB_FEATURE_NAMES), -1).T
    scales = fit_curvilinear_gate_scales(train_samples)
    gate = compute_curvilinear_discontinuity_gate(feat, scales, valid)
    assert gate.shape == (h, w)
    assert float(gate[32, 20]) > 0.90  # strong transmission on 1-D ridge
    assert float(gate[32, 50]) < 0.01  # >99% suppression on flat plain

