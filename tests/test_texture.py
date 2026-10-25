"""Synthetic falsification/edge cases for the registered profile transform."""
import numpy as np
import pytest
from gemsdoe30.texture import profile_lag, combine_scales, displacement_features, fold_consensus


def test_stationary_and_flat_profiles_are_not_displacements():
    rng = np.random.default_rng(6)
    a = rng.normal(size=(13, 8)).astype('float32')
    evidence, lag = profile_lag(a, a)
    assert np.all(evidence == 0)
    assert np.all(lag == 0)
    evidence, lag = profile_lag(np.ones((13, 4)), np.ones((13, 4)))
    assert np.all(evidence == 0) and np.all(lag == 0)


def test_known_shift_is_recovered_and_cross_scale_sign_is_required():
    a = np.random.default_rng(6).normal(size=(13, 12)).astype('float32')
    b = np.roll(a, 2, axis=0)
    evidence, lag = profile_lag(a, b)
    assert np.all(lag == 2)
    assert np.all(evidence > 0)
    assert np.all(combine_scales(evidence, lag, evidence, -lag) == 0)
    assert np.allclose(combine_scales(evidence, lag, evidence, lag), evidence)


def test_profiles_reject_bad_shapes_and_nan():
    with pytest.raises(ValueError): profile_lag(np.zeros((9, 2)), np.zeros((9, 2)))
    with pytest.raises(ValueError): profile_lag(np.full((13, 2), np.nan), np.zeros((13, 2)))


def test_transform_requires_finite_supported_data_and_does_not_use_labels():
    yy, xx = np.indices((80, 80), dtype='float32')
    gravity = np.tanh((xx - 40) / 3)
    mag = np.sin((yy + (xx > 40) * 2) * 0.6) + 0.4 * np.cos(yy * 1.2)
    valid = np.ones_like(xx, dtype=bool)
    fields = displacement_features(mag, mag, gravity, valid, batch_size=128)
    assert not fields['supported'][:16].any()
    assert np.nanmax(fields['rtp_texture']) > 0
    assert np.nanmin(fields['rtp_texture']) >= 0
    assert np.nanmax(fields['rtp_texture']) <= 1
    assert np.isnan(fields['mag_texture'][~fields['supported']]).all()
    with pytest.raises(ValueError):
        displacement_features(mag[:10, :10], mag[:10, :10], gravity[:10, :10], valid[:10, :10])


def test_gravity_normalization_is_training_only():
    a = np.ones((10, 10), dtype='float32') * .3
    edge = np.arange(1, 101, dtype='float32').reshape(10, 10)
    train = np.zeros_like(edge, dtype=bool); train[:5] = True
    _, receipt = fold_consensus(a, a, edge, train)
    edge[~train] = 1e10
    _, changed = fold_consensus(a, a, edge, train)
    assert receipt == changed
    with pytest.raises(ValueError): fold_consensus(a, a, edge, ~np.ones_like(train))


def test_euclidean_support_covers_square_gaussian_corners_and_interpolation():
    from gemsdoe30.texture import MAX_SOURCE_REACH_PX, SUPPORT_PX
    assert 16 < MAX_SOURCE_REACH_PX <= SUPPORT_PX == 17
    # A legal profile sample can interpolate cell (6, 5). Adding the square
    # Gaussian corner (6, 6) reaches (12, 11): sqrt(265) > the old 16px guard.
    assert np.hypot(5.2, np.sqrt(45 - 5.2**2)) <= np.sqrt(45) + 1e-12
    assert np.hypot(12, 11) > 16
    yy, xx = np.indices((90, 90), dtype='float32')
    valid = np.ones((90, 90), dtype=bool); valid[40, 40] = False
    field = np.sin(yy * .6)
    fields = displacement_features(field, field, xx, valid)
    assert not fields['supported'][56, 45]  # sqrt(281) lies between 16 and 17.
