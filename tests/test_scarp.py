import numpy as np
import pytest

from gemsdoe30.scarp import (
    axial_strike_consensus,
    decode_linear_band,
    decode_sqrt_band,
    scarp_orientation_score,
)


def test_uint8_decoders_follow_owner_quantisation_and_missing_code():
    codes = np.array([[0, 1, 128, 255]], dtype=np.uint8)

    linear = decode_linear_band(codes)
    curved = decode_sqrt_band(codes)

    assert linear[0, 0] == 0.0
    assert linear[0, 1] == 0.0
    assert linear[0, 3] == 1.0
    assert curved[0, 0] == 0.0
    assert curved[0, 1] == 0.0
    assert curved[0, 2] == pytest.approx(0.25, abs=1e-6)
    assert curved[0, 3] == 1.0


def test_axial_strike_consensus_treats_zero_and_180_degrees_as_equivalent():
    coverage = np.full((5, 5), 255, dtype=np.uint8)
    strike_zero = np.ones((5, 5), dtype=np.uint8)
    strike_180 = np.full((5, 5), 255, dtype=np.uint8)
    strike_mixed = strike_zero.copy()
    strike_mixed[::2, ::2] = 255

    a = axial_strike_consensus(strike_zero, coverage)
    b = axial_strike_consensus(strike_180, coverage)
    c = axial_strike_consensus(strike_mixed, coverage)

    assert a[2, 2] == pytest.approx(1.0, abs=1e-6)
    assert b[2, 2] == pytest.approx(1.0, abs=1e-6)
    assert c[2, 2] == pytest.approx(1.0, abs=1e-6)
    assert np.all((a >= 0.0) & (a <= 1.0))


def test_single_pixel_cannot_masquerade_as_persistent_strike():
    strike = np.zeros((3, 3), dtype=np.uint8)
    coverage = np.zeros((3, 3), dtype=np.uint8)
    strike[1, 1] = 1
    coverage[1, 1] = 255

    consensus = axial_strike_consensus(strike, coverage, window_size=3, min_support_cells=3.0)

    assert consensus[1, 1] == pytest.approx(1.0 / 3.0, abs=1e-6)
    assert np.count_nonzero(consensus) == 1


def test_scarp_score_is_bounded_and_masks_low_coverage_and_missing_strike():
    shape = (5, 5)
    full = np.full(shape, 255, dtype=np.uint8)
    strike = np.ones(shape, dtype=np.uint8)
    valid = full.copy()
    strike[1, 1] = 0
    valid[2, 2] = 1  # encoded zero coverage

    score, orientation = scarp_orientation_score(
        full, full, full, full, strike, valid,
        window_size=3,
        minimum_center_coverage=0.5,
    )

    assert score.dtype == np.float32
    assert orientation.dtype == np.float32
    assert score.shape == shape
    assert np.isfinite(score).all()
    assert np.all((score >= 0.0) & (score <= 1.0))
    assert score[3, 3] == pytest.approx(1.0, abs=1e-6)
    assert score[1, 1] == 0.0
    assert score[2, 2] == 0.0


def test_scarp_score_rejects_mismatched_shapes_bad_window_and_invalid_codes():
    base = np.full((3, 3), 255, dtype=np.uint8)
    with pytest.raises(ValueError, match="same two-dimensional shape"):
        scarp_orientation_score(base, base, base, base, base[:2], base)
    with pytest.raises(ValueError, match="odd positive"):
        axial_strike_consensus(base, base, window_size=2)
    with pytest.raises(ValueError, match=r"within \[0, 255\]"):
        decode_linear_band(np.full((2, 2), 256, dtype=np.uint16))
