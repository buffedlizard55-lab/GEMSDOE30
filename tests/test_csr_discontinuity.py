"""Unit tests for CSR-1 transforms, dispersed EDGE spacing, and malformed-exclusion registry audits."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scipy.spatial import cKDTree

from gemsdoe30.csr_discontinuity import (
    CSR_STATIC_FEATURE_NAMES,
    GUARD_PX,
    SUPPORT_PX,
    _radon_12az_chunked,
    calibrate_weighted_case_control_probabilities,
    compute_csr_static_features,
    compute_csr_structural_gate,
    concentrate_ridge_belief,
    fit_csr_gate_scales,
    fit_kd_alteration_residual,
    select_csr_dispersed_dots,
)
from gemsdoe30.emitter_opt import edge_select


def test_csr_support_strictly_inside_17px_guard():
    assert SUPPORT_PX == 16
    assert SUPPORT_PX < GUARD_PX
    rng = np.random.default_rng(101)
    h, w = 72, 72
    valid = np.ones((h, w), dtype=bool)
    raw_a = rng.normal(size=(19, h, w)).astype(np.float32)
    raw_a[2] = np.abs(raw_a[2]) * 20.0
    raw_a[14] = np.abs(raw_a[14]) * 600.0
    up150 = rng.integers(1, 255, size=(h, w), dtype=np.uint8)

    # Perturb every pixel strictly outside Euclidean radius SUPPORT_PX (16.0 px) from center (36, 36)
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    dist = np.hypot(yy - 36.0, xx - 36.0)
    raw_b = raw_a.copy()
    outside = dist > float(SUPPORT_PX)
    for ch in range(19):
        raw_b[ch][outside] += 500.0
    up150_b = up150.copy()
    up150_b[outside] = 250

    feat_a = compute_csr_static_features(raw_a, valid, tmi_up150_u8=up150)
    feat_b = compute_csr_static_features(raw_b, valid, tmi_up150_u8=up150_b)
    assert feat_a.shape == (len(CSR_STATIC_FEATURE_NAMES), h, w)
    assert np.all(np.isfinite(feat_a[:, 36, 36]))
    np.testing.assert_allclose(feat_a[:, 36, 36], feat_b[:, 36, 36], rtol=0.0, atol=1e-6)


def test_csr_radon_chunking_is_seam_free_and_detects_linear_ridge():
    h, w = 96, 80
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    # Narrow north-south linear ridge along col 40
    field = np.exp(-0.5 * ((xx - 40.0) / 1.2) ** 2).astype(np.float32)
    ok = np.zeros((h, w), dtype=bool)
    ok[18:-18, 18:-18] = True

    p_full, i_full, s_full, o_full = _radon_12az_chunked(
        field, ok, chunk_rows=256, return_selectivity_and_ortho=True
    )
    p_chunk, i_chunk, s_chunk, o_chunk = _radon_12az_chunked(
        field, ok, chunk_rows=21, return_selectivity_and_ortho=True
    )
    assert np.array_equal(p_full, p_chunk, equal_nan=True)
    assert np.array_equal(i_full, i_chunk)
    assert np.array_equal(s_full, s_chunk, equal_nan=True)
    assert np.array_equal(o_full, o_chunk, equal_nan=True)
    # Crest at (48, 40) must strongly exceed background at (48, 25)
    assert float(p_full[48, 40]) > 0.5
    assert float(p_full[48, 25]) < 0.05
    assert float(s_full[48, 40]) > 0.5


def test_kd_residual_ignores_heldout_pixels():
    rng = np.random.default_rng(7)
    h, w = 40, 40
    valid = np.ones((h, w), dtype=bool)
    train = np.zeros((h, w), dtype=bool)
    train[:20, :] = True
    th = rng.integers(20, 200, size=(h, w), dtype=np.uint8)
    k = np.clip((0.5 * th + 15.0), 1, 255).astype(np.uint8)
    res_a, meta_a = fit_kd_alteration_residual(k, th, train, valid)

    k_perturbed = k.copy()
    k_perturbed[20:, :] = 255  # Corrupt held-out half completely
    res_b, meta_b = fit_kd_alteration_residual(k_perturbed, th, train, valid)
    assert meta_a == meta_b
    np.testing.assert_array_equal(res_a[:20, :], res_b[:20, :])


def test_ridge_concentration_and_dispersed_edge_enforce_spacing():
    h, w = 64, 64
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    # Blurry 6-px wide ridge along col=32
    belief = (0.35 * np.exp(-0.5 * ((xx - 32.0) / 2.5) ** 2)).astype(np.float32)
    active = np.ones((h, w), dtype=bool)

    conc = concentrate_ridge_belief(belief, active, gamma=1.25)
    # Crest preserved, lateral flank at +2 px attenuated
    np.testing.assert_allclose(conc[32, 32], belief[32, 32], rtol=1e-4)
    assert float(conc[32, 34]) < float(belief[32, 34])

    dots = select_csr_dispersed_dots(belief, active, dot_budget=18, gamma=1.25, min_sq_dist_excl=6)
    assert int(np.count_nonzero(dots)) == 18
    pts = np.argwhere(dots > 0.5).astype(np.float64)
    dists, _ = cKDTree(pts).query(pts, k=2)
    # Minimum squared integer distance > 6 => minimum Euclidean distance >= sqrt(8) = 2.828427...
    assert float(dists[:, 1].min()) >= math.sqrt(8.0) - 1e-9

    # Default min_sq_dist_excl=0 in edge_select remains unblocked
    m0 = edge_select(belief, support=active, truth_mass=1e9, max_dots=18)
    assert int(np.count_nonzero(m0)) == 18


def test_weighted_calibration_and_gate_bounds():
    probs = np.array([[0.1, 0.5, 0.9]], dtype=np.float32)
    cal = calibrate_weighted_case_control_probabilities(
        probs,
        population_positives=100.0,
        population_negatives=9900.0,
        effective_sample_positives=200.0,
        effective_sample_negatives=600.0,
    )
    assert cal.shape == probs.shape
    assert np.all((cal > 0.0) & (cal < 1.0))
    assert float(cal[0, 0]) < float(cal[0, 1]) < float(cal[0, 2])

    rng = np.random.default_rng(13)
    fake_csr = np.abs(rng.normal(size=(len(CSR_STATIC_FEATURE_NAMES), 24, 24))).astype(np.float32)
    valid = np.ones((24, 24), dtype=bool)
    scales = fit_csr_gate_scales(fake_csr, valid)
    gate = compute_csr_structural_gate(fake_csr, valid, scales, floor=0.08)
    assert np.all((gate >= 0.08 - 1e-6) & (gate <= 1.0))


def test_malformed_footprint_exclusion_classified_and_audited(tmp_path: Path):
    from scripts.check_novelty import audit
    from scripts.sync_priority_registry import classify_footprint_validity

    profile = {
        "driver": "GTiff",
        "height": 16,
        "width": 16,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32611",
        "transform": from_origin(243350.0, 4508550.0, 100.0, 100.0),
        "nodata": None,
    }
    tpl = tmp_path / "tpl.tif"
    cand = tmp_path / "cand.tif"
    good_ref = tmp_path / "good.tif"
    bad_ref = tmp_path / "bad_nan.tif"

    with rasterio.open(tpl, "w", **profile) as ds:
        ds.write(np.zeros((1, 16, 16), dtype=np.float32))
    cand_arr = np.zeros((16, 16), dtype=np.float32)
    cand_arr[2, 2] = 1.0
    with rasterio.open(cand, "w", **profile) as ds:
        ds.write(cand_arr[None])
    good_arr = np.zeros((16, 16), dtype=np.float32)
    good_arr[12, 12] = 1.0
    with rasterio.open(good_ref, "w", **profile) as ds:
        ds.write(good_arr[None])
    bad_arr = np.zeros((16, 16), dtype=np.float32)
    bad_arr[:8, :] = np.nan
    bad_arr[10, 10] = 1.0
    with rasterio.open(bad_ref, "w", **profile) as ds:
        ds.write(bad_arr[None])

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()

    footprint = np.ones((16, 16), dtype=bool)
    classified = classify_footprint_validity(
        {"aligned": True, "path": str(bad_ref), "sha256": sha(bad_ref), "site": "GEMSDOE31"},
        footprint,
    )
    assert classified["footprint_complete"] is False
    assert classified["invalid_in_footprint_cells"] == 128
    assert classified["positive_dots_in_footprint"] == 1

    reg = tmp_path / "reg.json"
    reg.write_text(
        json.dumps(
            {
                "complete": True,
                "rasters": [{"path": str(good_ref), "sha256": sha(good_ref), "site": "GEMSDOE30"}],
                "exclusions": [classified],
            }
        )
    )
    res = audit(cand, tpl, reg, "dots")
    # Inspecting a finite subset cannot establish full-registry uniqueness.
    assert res["decision"] == "blocked-incomplete-evidence"
    assert res["registry_complete"] is False
    assert res["errors"] == []
    assert len(res["malformed_exclusions_audited"]) == 1
    assert res["malformed_exclusions_audited"][0]["invalid_in_footprint_cells"] == 128
