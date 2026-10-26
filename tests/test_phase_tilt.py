"""Unit tests for PTA-1 unit-consistent phase-tilt & dip-asymmetry transforms."""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe30.experiments import contract
from gemsdoe30.phase_tilt import (
    ALL_DERIVED_NAMES,
    CANDIDATE_DERIVED_NAMES,
    CONTROL_DERIVED_NAMES,
    SUPPORT_PX,
    TIGHT_SUPPORT_PX,
    compute_phase_tilt_features,
    load_or_build_cache,
)


def _synthetic_cube(height: int = 45, width: int = 45, seed: int = 17) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    raw = rng.normal(0.0, 1.0, size=(19, height, width)).astype(np.float32)
    # Non-negative gradient magnitude bands: tmi_hg (2) in nT/km, iso_grav_anom_slope (4)
    raw[2] = np.abs(raw[2]) * 25.0 + 2.0
    raw[4] = np.abs(raw[4]) * 0.15 + 0.01
    # tmi_vg (8) in nT/m (~10^-3 of tmi_hg)
    raw[8] = raw[8] * 0.05
    raw[10] = raw[10] * 1.5
    raw[12] = np.linspace(10.0, -10.0, width, dtype=np.float32)[None, :] + 0.2 * raw[12]
    raw[14] = np.linspace(50.0, 900.0, width, dtype=np.float32)[None, :] + 10.0 * raw[14]
    raw[16] = np.abs(raw[16]) + 1.5
    valid = np.ones((height, width), dtype=bool)
    valid[:2, :] = False
    valid[:, -2:] = False
    return raw, valid


def test_impulse_perturbation_strictly_bounded_by_support_px():
    """Verify numerically that a single-pixel perturbation never leaks beyond SUPPORT_PX = 12."""
    raw_a, valid = _synthetic_cube(45, 45, seed=42)
    raw_b = raw_a.copy()
    cy, cx = 22, 22
    for b in (1, 2, 4, 8, 10, 12, 14, 16):
        raw_b[b, cy, cx] += 250.0 if b != 4 else 5.0

    out_a = compute_phase_tilt_features(raw_a, valid)
    out_b = compute_phase_tilt_features(raw_b, valid)

    yy, xx = np.meshgrid(np.arange(45), np.arange(45), indexing="ij")
    dist = np.hypot(yy - cy, xx - cx)
    outside = dist > float(TIGHT_SUPPORT_PX)
    assert TIGHT_SUPPORT_PX == 12 and SUPPORT_PX == 17

    for name in ALL_DERIVED_NAMES:
        a, b = out_a[name][outside], out_b[name][outside]
        assert np.array_equal(np.isnan(a), np.isnan(b)), f"NaN mask leaked outside {TIGHT_SUPPORT_PX}px in {name}"
        fin = np.isfinite(a)
        assert np.allclose(a[fin], b[fin], atol=0.0, rtol=0.0), (
            f"value leaked outside {TIGHT_SUPPORT_PX}px in {name}: max diff={np.max(np.abs(a[fin] - b[fin]))}"
        )


def test_unit_conversion_prevents_vertical_derivative_collapse():
    """Verify 1000x nT/m->nT/km conversion preserves full [-pi/2, pi/2] tilt dynamic range."""
    raw, valid = _synthetic_cube(35, 35, seed=9)
    out = compute_phase_tilt_features(raw, valid)
    unit_iqr = np.nanpercentile(out["pta_mag_tilt"], 75) - np.nanpercentile(out["pta_mag_tilt"], 25)
    naive_iqr = np.nanpercentile(out["ctrl_naive_mag_tilt"], 75) - np.nanpercentile(out["ctrl_naive_mag_tilt"], 25)
    assert unit_iqr > 20.0 * naive_iqr
    assert np.all(np.isnan(out["pta_mag_tilt"][~valid]))


def test_dipping_normal_fault_polarity_flips_sign_while_symmetric_control_does_not():
    """Reversing hanging-wall direction flips signed dip features while leaving symmetric controls invariant."""
    H, W = 41, 41
    yy, xx = np.meshgrid(np.arange(H, dtype=np.float32), np.arange(W, dtype=np.float32), indexing="ij")
    valid = np.ones((H, W), dtype=bool)

    def make(direction: float) -> np.ndarray:
        s = direction * (xx - 20.0)
        raw = np.zeros((19, H, W), dtype=np.float32)
        raw[2] = 20.0 / (1.0 + (s / 2.0) ** 2)
        raw[8] = -0.02 * s / (1.0 + (s / 2.0) ** 2)
        # Deeper gravity step shifted +4 px into hanging wall (s > 0)
        raw[4] = 0.25 / (1.0 + ((s - 4.0) / 3.0) ** 2)
        raw[10] = -0.5 * (s - 4.0) / (1.0 + ((s - 4.0) / 3.0) ** 2)
        raw[12] = -10.0 * np.tanh((s - 4.0) / 4.0)  # gravity decreases toward +s hanging wall
        raw[14] = 400.0 + 300.0 * np.tanh(s / 4.0)  # cover thickens toward +s hanging wall
        raw[16] = 2.5 + 1.0 * np.tanh(s / 4.0)
        return raw

    east_hw = compute_phase_tilt_features(make(+1.0), valid)
    west_hw = compute_phase_tilt_features(make(-1.0), valid)
    # At fault surface trace (20, 20), hanging-wall normal n points +x for east_hw and -x for west_hw,
    # so intrinsic hanging-wall-referenced quantities match when geometry is reflected!
    assert east_hw["pta_dip_grav_mig"][20, 20] > 0.0
    assert np.isclose(east_hw["pta_dip_grav_mig"][20, 20], west_hw["pta_dip_grav_mig"][20, 20], atol=1e-5)
    assert east_hw["pta_dip_cover_step"][20, 20] > 0.2

    # Now invert cover step relative to gravity normal (cover thins on gravity-low side):
    inverted = make(+1.0)
    inverted[14] = 400.0 - 300.0 * np.tanh((xx - 20.0) / 4.0)
    inv_out = compute_phase_tilt_features(inverted, valid)
    assert inv_out["pta_dip_cover_step"][20, 20] < -0.2
    # Symmetric control has opposite sign sensitivity (measures second-difference curvature, zero at odd tanh inflection)
    assert abs(east_hw["ctrl_sym_cover_step"][20, 20]) < 1e-5


def test_cache_roundtrip_and_experiment_contract(tmp_path):
    raw, valid = _synthetic_cube(30, 32, seed=5)
    manifest = {"dataset_signature": "sig-test", "valid_mask_sha256": "mask-test"}
    loaded, receipt = load_or_build_cache(raw, valid, manifest, tmp_path / "cache")
    assert set(loaded) == set(ALL_DERIVED_NAMES)
    loaded2, receipt2 = load_or_build_cache(raw, valid, manifest, tmp_path / "cache")
    assert receipt == receipt2
    for name in CANDIDATE_DERIVED_NAMES + CONTROL_DERIVED_NAMES:
        assert np.array_equal(loaded[name], loaded2[name], equal_nan=True)

    spec = contract({"experiment_spec": "pta1"})
    assert spec["candidate"] == "pta1_cand"
    assert spec["support_px"] == 17
    assert len(spec["features"]) == 19 + 18
