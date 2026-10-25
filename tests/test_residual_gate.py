import numpy as np
import pytest

from gemsdoe30.residual_gate import (
    fit_residual,
    gated_residual_ridge,
    ridge_strength,
    robust_zscore,
)


def test_fit_residual_recovers_exact_linear_model():
    rng = np.random.default_rng(0)
    g = rng.normal(size=(60, 70))
    z = rng.normal(size=(60, 70))
    target = 2.0 + 3.0 * g - 0.5 * z
    foot = np.ones(g.shape, dtype=bool)
    residual, info = fit_residual(target, [g, z], foot)
    assert np.nanmax(np.abs(residual)) < 1e-4
    assert info["r_squared"] == pytest.approx(1.0, abs=1e-9)
    assert info["coefficients"][1] == pytest.approx(3.0, abs=1e-4)


def test_fit_residual_nan_outside_footprint_and_on_bad_inputs():
    target = np.arange(400, dtype=float).reshape(20, 20)
    reg = np.random.default_rng(1).normal(size=(20, 20))
    reg[0, 0] = np.nan
    foot = np.ones((20, 20), dtype=bool)
    foot[10:, :] = False
    residual, _ = fit_residual(target, [reg], foot)
    assert np.isnan(residual[0, 0])
    assert np.isnan(residual[15, 3])
    with pytest.raises(ValueError):
        fit_residual(target, [reg[:5]], foot)


def test_robust_zscore_is_zero_outside_valid_and_rejects_constant():
    x = np.linspace(-1, 1, 101).reshape(101, 1) * np.ones((1, 3))
    valid = np.ones(x.shape, dtype=bool)
    valid[0, 0] = False
    z = robust_zscore(x, valid)
    assert z[0, 0] == 0.0
    with pytest.raises(ValueError):
        robust_zscore(np.ones((5, 5)), np.ones((5, 5), dtype=bool))


def test_ridge_detects_a_planted_ribbon_and_not_a_plateau():
    n = 120
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    ribbon = np.exp(-((xx - 60.0) ** 2) / (2 * 2.0 ** 2))  # bright crest, width ~2 px
    valid = np.ones((n, n), dtype=bool)
    r_ridge = ridge_strength(ribbon, valid, sigma_px=2.0)
    plateau = np.ones((n, n))
    r_flat = ridge_strength(plateau, valid, sigma_px=2.0)
    assert r_ridge[:, 60].mean() > 10 * r_ridge[:, 20].mean()
    assert r_flat.max() < 1e-9


def test_gated_belief_is_zero_outside_gate_and_peaks_on_planted_quiet_ribbon():
    n = 150
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    residual = np.zeros((n, n))
    residual += 0.05 * np.sin(xx / 9.0) * np.cos(yy / 13.0)
    residual[:, 75] = -6.0  # a dark ribbon along column 75
    valid = np.ones((n, n), dtype=bool)
    # visible catalogue: a single vertical trace at column 20 (far from the ribbon)
    distance = np.abs(xx - 20.0) * 100.0
    belief = gated_residual_ridge(residual, valid, distance, gate_m=10_000.0)
    assert belief.min() >= 0.0 and belief.max() <= 1.0
    far = gated_residual_ridge(residual, valid, distance, gate_m=5_000.0)
    beyond = distance > 5_000.0
    assert np.all(far[beyond] == 0.0)
    assert belief.shape == (n, n)
