"""Mechanism falsification and memory-safe reuse checks, without competition data."""
import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from gemsdoe30.texture import displacement_features, SUPPORT_PX
from gemsdoe30.texture_controls import phase_scramble, zero_lag, control_features
from gemsdoe30.experiments import LayerStack, contract


def test_local_fourier_control_preserves_each_profile_mean_and_power_not_order():
    a = np.random.default_rng(2).normal(size=(13, 31)).astype(np.float32)
    b = phase_scramble(a)
    assert b.shape == a.shape and b.dtype == np.float32
    assert_allclose(a.mean(axis=0), b.mean(axis=0), atol=1e-7)
    assert_allclose(np.abs(np.fft.rfft(a, axis=0)), np.abs(np.fft.rfft(b, axis=0)), atol=2e-6)
    assert not np.allclose(a, b)
    assert_array_equal(b, phase_scramble(a))
    assert_array_equal(phase_scramble(np.ones((13, 2), np.float32)), np.ones((13, 2), np.float32))


def test_zero_lag_control_returns_coherence_not_displacement_for_identical_profiles():
    a = np.random.default_rng(3).normal(size=(13, 5)).astype(np.float32)
    assert_allclose(zero_lag(a, a), 1, atol=2e-7)
    assert_array_equal(zero_lag(a, -a), np.zeros(5))
    assert_array_equal(zero_lag(np.ones_like(a), a), np.zeros(5))
    with pytest.raises(ValueError):
        zero_lag(a, a[:-1])
    with pytest.raises(ValueError):
        phase_scramble(np.full((13, 2), np.nan))


def test_control_support_matches_parent_and_does_not_borrow_remote_samples():
    y, x = np.mgrid[:80, :82]
    mag = (np.sin(x * .7) + np.cos(y * .4)).astype(np.float32)
    gravity = (x + .1 * y).astype(np.float32)
    valid = np.ones(mag.shape, bool)
    original = displacement_features(mag, mag * 2, gravity, valid, batch_size=200)
    controls = control_features(mag, mag * 2, gravity, valid, original['supported'], batch_size=150)
    assert set(controls) == {'zero_mag', 'zero_rtp', 'phase_mag', 'phase_rtp'}
    for values in controls.values():
        assert_array_equal(np.isfinite(values), original['supported'])
        assert np.all((values[original['supported']] >= 0) & (values[original['supported']] <= 1))
    # Local Fourier scrambling cannot increase the registered spatial reach.
    changed = mag.copy(); changed[:4] += 1000
    remote = control_features(changed, mag * 2, gravity, valid, original['supported'], batch_size=900)
    for key in controls:
        assert_allclose(controls[key][35:45, 35:45], remote[key][35:45, 35:45], atol=0, rtol=0)
    with pytest.raises(ValueError, match='exactly'):
        control_features(mag, mag, gravity, valid, valid)
    assert SUPPORT_PX == 17


def test_layer_stack_matches_existing_sampler_and_predictor_indexing():
    a = np.arange(5 * 8 * 9, dtype=np.float32).reshape(5, 8, 9)
    stack = LayerStack([a[i] for i in range(5)])
    assert stack.shape == a.shape
    rr, cc = np.array([1, 4, 7]), np.array([2, 6, 1])
    assert_array_equal(stack[:, rr, cc], a[:, rr, cc])
    assert_array_equal(stack[[0, 3], 1:6, 2:8], a[[0, 3], 1:6, 2:8])
    assert_array_equal(stack[2, rr, cc], a[2, rr, cc])
    with pytest.raises(ValueError):
        LayerStack([np.ones((2, 2)), np.ones((2, 3))])
    with pytest.raises(ValueError):
        contract({'experiment_spec': 'arbitrary-green-contract'})


def test_full_stack_arms_share_all_core_features_and_have_predeclared_derived_slots():
    from scripts.run_texture_controls import arm_columns
    for arm in contract({'experiment_spec': 'tdxc2'})['arms']:
        cols = arm_columns(arm)
        assert cols[:19] == list(range(19))
        assert len(cols) == (19 if arm == 'core19' else 22)
    all_features = contract({'experiment_spec': 'tdxc2'})['features']
    assert len(all_features) == len(set(all_features)) == 28
