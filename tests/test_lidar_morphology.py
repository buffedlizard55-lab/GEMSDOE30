"""Unit tests for the label-free G30-LSM layers and the leaderboard-calibration algebra."""
import math

import numpy as np
import pytest

from gemsdoe30.lidar_morphology import (GEO_LAYERS, LIDAR_BANDS, LIDAR_LAYERS, StackedFeatures,
                                        axial_persistence, decode, geo_layers, lidar_layers)


def test_decode_round_trip_and_missing():
    q = np.array([0, 1, 128, 255], dtype=np.uint8)
    lin = decode(q, "coh100")
    assert math.isnan(lin[0]) and lin[1] == 0.0 and abs(lin[3] - 1.0) < 1e-6
    sq = decode(q, "step_max")
    # sqrt encoding: x = xmax * ((q-1)/254)^2
    assert abs(sq[2] - ((127 / 254) ** 2)) < 1e-6
    with pytest.raises(ValueError):
        decode(q.astype(np.int16), "coh100")
    with pytest.raises(KeyError):
        decode(q, "not_a_channel")


def test_axial_persistence_is_axial_and_convention_free():
    theta = np.full((7, 7), 10.0)
    w = np.ones((7, 7))
    a = axial_persistence(theta, w)
    b = axial_persistence(theta + 180.0, w)          # 0 == 180 degrees
    c = axial_persistence(-theta + 37.0, w)          # reflection + rotation of the convention
    assert np.allclose(a, b) and np.allclose(a[3, 3], 1.0) and np.allclose(a, c)
    mixed = theta.copy()
    mixed[::2, :] += 90.0                             # orthogonal stripes -> low persistence
    assert axial_persistence(mixed, w)[3, 3] < 0.3
    nan = axial_persistence(np.full((5, 5), np.nan), w[:5, :5])
    assert np.isnan(nan).all()
    with pytest.raises(ValueError):
        axial_persistence(theta, w, size=4)


def test_lidar_layers_names_bounds_and_missing():
    rng = np.random.default_rng(0)
    stack = rng.integers(1, 256, size=(len(LIDAR_BANDS), 16, 16), dtype=np.uint8)
    stack[:, :4, :] = 0                               # no-LiDAR strip
    valid = np.ones((16, 16), dtype=bool)
    valid[-1, -1] = False
    names, layers = zip(*lidar_layers(stack, valid))
    assert names == LIDAR_LAYERS
    cover = layers[0]
    assert np.all(cover[:4] == 0) and np.all(np.isfinite(cover))
    for name, layer in zip(names[1:], layers[1:]):
        assert layer.dtype == np.float32 and layer.shape == (16, 16)
        assert np.isnan(layer[:4]).all(), name       # missing LiDAR stays missing (imputed later)
        finite = layer[np.isfinite(layer)]
        assert finite.size and (finite >= 0).all(), name
    persistence = layers[names.index("strike_persistence_5x5")]
    assert np.nanmax(persistence) <= 1.0


def test_geo_layers_are_label_free_and_finite_inside():
    rng = np.random.default_rng(1)
    base = rng.normal(size=(19, 24, 24)).astype(np.float32)
    base[:, 0, 0] = np.nan
    valid = np.ones((24, 24), dtype=bool)
    valid[0, :] = False
    names, layers = zip(*geo_layers(base, valid))
    assert names == GEO_LAYERS
    for layer in layers:
        assert np.isfinite(layer[valid]).all() and np.isnan(layer[~valid]).all()
    coherence = layers[names.index("tensor_coherence_rtp")]
    assert (coherence[valid] >= 0).all() and (coherence[valid] <= 1 + 1e-5).all()


def test_stacked_features_matches_concatenation():
    a = np.arange(2 * 5 * 6, dtype=np.float32).reshape(2, 5, 6)
    b = -np.arange(3 * 5 * 6, dtype=np.float32).reshape(3, 5, 6)
    s = StackedFeatures(a, b, names=list("abcde"))
    full = np.concatenate([a, b])
    rows, cols = np.array([0, 4, 2]), np.array([5, 0, 3])
    assert s.shape == (5, 5, 6) and len(s) == 5
    assert np.array_equal(s[:, rows, cols], full[:, rows, cols])
    assert np.array_equal(s[:, 1:4, 2:6], full[:, 1:4, 2:6])
    assert np.array_equal(s[3], full[3]) and np.array_equal(s[-1], full[-1])
    with pytest.raises(TypeError):
        s[1:2]
    with pytest.raises(ValueError):
        StackedFeatures(a, b[:, :4])


def test_implied_tp_density_inverts_the_metric():
    from scripts.leaderboard_calibration import implied_tp_density
    rho, n = 0.0024, 0.0074
    t = implied_tp_density(0.2778, n, rho)
    # Re-evaluate DTI per unit area with F = N - T/3 and G = rho.
    s = t / (0.2 * t + 0.2 * (n - t / 3) + 0.8 * rho)
    assert abs(s - 0.2778) < 1e-9
    assert 0 < t / rho < 1


def test_crest_mask_finds_line_centre_not_zone_flanks():
    from gemsdoe30.emission import crest_mask
    rr, cc = np.mgrid[0:40, 0:40]
    for angle in (0.0, 30.0, 90.0, 135.0):
        t = np.deg2rad(angle)
        d = (rr - 20) * np.cos(t) - (cc - 20) * np.sin(t)       # signed distance to a line
        surface = np.exp(-(d ** 2) / (2 * 3.0 ** 2)).astype(np.float32)
        m = crest_mask(surface)
        inner = m[5:-5, 5:-5]
        dist = np.abs(d[5:-5, 5:-5])
        assert inner.sum() > 20, angle
        assert dist[inner].max() <= 1.0, angle                 # crest pixels hug the centre line
        assert not (inner & (dist >= 3)).any(), angle          # flanks rejected
    flat = crest_mask(np.ones((10, 10), dtype=np.float32))
    assert not flat[2:-2, 2:-2].any()                          # no curvature -> no crest
    with pytest.raises(ValueError):
        crest_mask(np.ones(5))
