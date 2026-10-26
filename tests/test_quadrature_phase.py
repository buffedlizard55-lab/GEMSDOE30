"""QPC-1 transform, support, and provenance invariants on small synthetic grids."""
import math

import numpy as np
import pytest

from gemsdoe30.quadrature_phase import (
    FEATURE_NAMES, GRAVITY_INDEX, GUARD_PX, MAX_AXIAL_SUPPORT_PX, RTP_INDEX,
    SUPPORT_PX, _unit_vector, compute_features,
)


def stack(size=71):
    y, x = np.mgrid[:size, :size]
    signal = (np.sin(x / 3.0) + .4 * np.cos(y / 5.0)).astype(np.float32)
    base = np.zeros((19, size, size), dtype=np.float32)
    base[RTP_INDEX] = signal
    base[GRAVITY_INDEX] = 5 * signal + 13
    return base, np.ones((size, size), dtype=bool)


def test_aligned_scaled_fields_have_signed_unit_concordance():
    base, valid = stack()
    fields = compute_features(base, valid)
    assert fields.shape == (len(FEATURE_NAMES), *valid.shape)
    for channel in fields[:2]:
        finite = channel[np.isfinite(channel)]
        assert finite.size > 100
        assert np.allclose(finite, 1, atol=3e-4)
        assert np.all((-1 <= finite) & (finite <= 1))
    base[GRAVITY_INDEX] = -base[RTP_INDEX]
    reverse = compute_features(base, valid)
    assert np.allclose(reverse[0][np.isfinite(reverse[0])], -1, atol=3e-4)


def test_missing_source_or_outside_footprint_never_creates_an_edge_signal():
    base, valid = stack()
    base[RTP_INDEX, 35, 35] = np.nan
    valid[20, 20] = False
    fields = compute_features(base, valid)
    assert np.isnan(fields[1, 35, 35])
    assert np.isnan(fields[1, 35, 35 + MAX_AXIAL_SUPPORT_PX])
    assert np.isnan(fields[:, 0, :]).all()
    assert np.isnan(fields[:, 20, 20]).all()
    # A nonfinite source in either field invalidates cross-field features only.
    assert np.isfinite(fields[3, 35, 35])


def test_zero_energy_is_undefined_and_guard_covers_operator():
    base = np.zeros((19, 61, 61), dtype=np.float32)
    fields = compute_features(base, np.ones((61, 61), dtype=bool))
    assert np.isnan(fields).all()
    assert SUPPORT_PX == math.ceil(math.sqrt(2) * MAX_AXIAL_SUPPORT_PX)
    assert SUPPORT_PX + 3 <= GUARD_PX


def test_perturbations_outside_fixed_kernel_do_not_change_center():
    base, valid = stack()
    before = _unit_vector(base[RTP_INDEX], valid, 3.0)
    base[RTP_INDEX, 35 + MAX_AXIAL_SUPPORT_PX + 1, 35] += 1e4
    after = _unit_vector(base[RTP_INDEX], valid, 3.0)
    assert all(a[35, 35] == b[35, 35] for a, b in zip(before, after))
    with pytest.raises(ValueError, match='scale'):
        _unit_vector(base[RTP_INDEX], valid, 2.0)


def test_input_contract_and_mmap_output(tmp_path):
    base, valid = stack()
    out = np.lib.format.open_memmap(tmp_path / 'features.npy', mode='w+', dtype='float32',
                                    shape=(4, *valid.shape))
    assert compute_features(base, valid, out=out) is out
    out.flush()
    assert np.array_equal(np.load(tmp_path / 'features.npy'), np.asarray(out), equal_nan=True)
    with pytest.raises(ValueError, match='aligned'):
        compute_features(base[:3], valid)
    with pytest.raises(ValueError, match='float32'):
        compute_features(base, valid, out=np.zeros((4, *valid.shape), dtype='float64'))
