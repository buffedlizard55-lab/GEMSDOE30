from __future__ import annotations

import time
import numpy as np
import pytest

from gemsdoe30.ms_cape import (
    STAGE1_SUPPORT_PX,
    STAGE2_SUPPORT_PX,
    SUPPORT_PX,
    axial_line_bank,
    compute_stage2_trace_features,
    cross_strike_sharpness,
    masked_box_mean,
    masked_grad,
    recalibrate_prior_odds,
    submod_dti_select,
)


def test_support_radius_strictly_bounded():
    assert STAGE1_SUPPORT_PX + STAGE2_SUPPORT_PX == SUPPORT_PX == 20
    h, w = 65, 65
    valid = np.ones((h, w), dtype=bool)
    impulse = np.zeros((h, w), dtype=np.float32)
    impulse[32, 32] = 10.0

    # Stage 1 max filter radius = 12 px
    b12 = axial_line_bank(impulse, valid, half_len=STAGE1_SUPPORT_PX, n_azimuths=8)
    ys, xs = np.nonzero(b12["axial_max"] > 0)
    dists = np.hypot(ys - 32, xs - 32)
    assert float(dists.max()) <= STAGE1_SUPPORT_PX + 1e-6

    # Stage 2 max filter radius = 8 px across ALL 10 channels (exact perturbation test)
    p_base = np.full((h, w), 0.05, dtype=np.float32)
    p_pert = p_base.copy()
    p_pert[32, 32] = 0.95
    s2_a = compute_stage2_trace_features(p_base, valid)
    s2_b = compute_stage2_trace_features(p_pert, valid)
    for ch in range(s2_a.shape[0]):
        ys2, xs2 = np.nonzero(np.abs(s2_a[ch] - s2_b[ch]) > 0.0)
        if ch == 4:
            # gap_bridge = min(fwd, bwd) is mathematically immune to isolated 1-px noise!
            assert ys2.size == 0
        else:
            assert ys2.size > 0
            assert float(np.hypot(ys2 - 32, xs2 - 32).max()) <= STAGE2_SUPPORT_PX + 1e-6


def test_masked_operators_never_bleed_outside_footprint():
    rng = np.random.default_rng(42)
    valid = np.zeros((40, 40), dtype=bool)
    valid[8:32, 8:32] = True
    f = rng.normal(size=(40, 40)).astype(np.float32)
    f[~valid] = -3.4e38  # Simulate sentinel outside footprint!

    m = masked_box_mean(f, valid, radius=5)
    assert np.isfinite(m).all()
    assert np.all(m[~valid] == 0.0)
    assert np.all(np.abs(m[valid]) < 10.0)

    gy, gx, gmag = masked_grad(f, valid)
    assert np.isfinite(gmag).all()
    assert np.all(gmag[~valid] == 0.0)
    assert np.all(gmag[valid] < 10.0)


def test_axial_anisotropy_and_wash_gap_bridge():
    valid = np.ones((45, 45), dtype=bool)
    # N-S linear fault trace at col=22 with a 3-pixel alluvial wash gap at rows 21..23!
    field = np.zeros((45, 45), dtype=np.float32)
    field[8:21, 22] = 0.9
    field[24:37, 22] = 0.9

    b8 = axial_line_bank(field, valid, half_len=8, n_azimuths=8)
    # Inside the wash gap (22, 22), BOTH forward and backward N-S rays see strong trace -> high gap_bridge!
    assert b8["gap_bridge"][22, 22] > 0.55
    assert b8["axial_aniso"][22, 22] > 0.80
    assert int(b8["best_idx"][22, 22]) == 0  # m=0 is N-S strike

    sharp = cross_strike_sharpness(field, valid, b8["best_idx"], offset_px=3)
    assert sharp[15, 22] > 0.80


def test_prior_odds_recalibration_recovers_base_rate():
    valid = np.ones((10, 10), dtype=bool)
    # If sample has pi_sample = 1/7 and model predicts sample prior 1/7 everywhere, calibrated prob == pi_true
    p_sub = np.full((10, 10), 1.0 / 7.0, dtype=np.float32)
    p_cal = recalibrate_prior_odds(p_sub, pi_true=0.012, pi_sample=1.0 / 7.0, valid=valid)
    assert np.allclose(p_cal, 0.012, atol=1e-6)


def test_submod_dti_select_matches_exact_greedy_and_respects_flank():
    rng = np.random.default_rng(7)
    prob = rng.uniform(0.001, 0.25, size=(32, 32)).astype(np.float32)
    # Plant two sharp fault traces
    prob[6:26, 10] = 0.75
    prob[8:24, 22] = 0.65
    active = np.ones((32, 32), dtype=bool)
    visible = np.zeros((32, 32), dtype=bool)
    visible[6:26, 9] = True  # Visible fault 1 px from trace at col=10 -> flank exclusion (>2 px) must skip col=10!

    dots = submod_dti_select(prob, active, visible, budget=12, flank_exclusion_px=2.0, min_sep_px=2.2)
    assert int(dots.sum()) == 12
    assert set(np.unique(dots)).issubset({0.0, 1.0})
    # Verify zero dots within <= 2.0 px of visible fault
    vis_coords = np.argwhere(visible)
    dot_coords = np.argwhere(dots > 0)
    for r, c in dot_coords:
        d_vis = np.min(np.hypot(vis_coords[:, 0] - r, vis_coords[:, 1] - c))
        assert d_vis > 2.0 + 1e-6
    # Verify pairwise dot spacing >= 2.2 px
    for i in range(len(dot_coords)):
        for j in range(i + 1, len(dot_coords)):
            d_ij = float(np.hypot(*(dot_coords[i] - dot_coords[j])))
            assert d_ij >= 2.2 - 1e-6


def test_submod_dti_full_grid_runtime():
    rng = np.random.default_rng(99)
    # 1/4 quadrant scale smoke timing check
    prob = rng.exponential(scale=0.01, size=(900, 800)).astype(np.float32)
    active = np.ones((900, 800), dtype=bool)
    vis = np.zeros((900, 800), dtype=bool)
    t0 = time.monotonic()
    dots = submod_dti_select(prob, active, vis, budget=2500)
    dt = time.monotonic() - t0
    assert int(dots.sum()) == 2500
    assert dt < 5.0
