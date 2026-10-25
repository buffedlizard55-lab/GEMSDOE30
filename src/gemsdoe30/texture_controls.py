"""TDX-C2 falsification controls on exactly the TDX-1 physical sample support.

These controls test signal specificity, not geology ground truth. Fourier phases
are fixed before seeing outcomes. No raster is translated, no labels are accepted,
and no sample is borrowed from another geographic/training region.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter

from .texture import SUPPORT_PX, _profiles, combine_scales, profile_lag

TRANSFORM_VERSION = "tdxc2-local-profile-controls-v1-20261025"
PHASES = (0.73, -1.21, 2.33, -2.02, 1.07, -0.48)
CONTROL_FEATURES = ("zero_mag", "zero_rtp", "phase_mag", "phase_rtp")


def phase_scramble(profile: np.ndarray) -> np.ndarray:
    """Preserve each 13-sample profile's mean/power, destroy its ordered phase.

    This is a deterministic matched negative control, NOT random null replicates.
    The same fixed phases at each physical scale permit the same scale-combination
    rule as the candidate. Returning float32 matches the original profile code.
    """
    profile = np.asarray(profile, dtype=np.float32)
    if profile.ndim != 2 or profile.shape[0] != 13 or not np.isfinite(profile).all():
        raise ValueError("finite profiles with shape (13, N) required")
    spectrum = np.fft.rfft(profile, axis=0)
    spectrum[1:] *= np.exp(1j * np.asarray(PHASES))[:, None]
    return np.fft.irfft(spectrum, n=13, axis=0).astype(np.float32)


def zero_lag(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Positive zero-lag correlation on the same nine central samples as TDX-1."""
    left, right = np.asarray(left, dtype=np.float32), np.asarray(right, dtype=np.float32)
    if left.ndim != 2 or left.shape != right.shape or left.shape[0] != 13:
        raise ValueError("same-shaped (13, N) profiles required")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("finite profiles required")
    a, b = left[2:11], right[2:11]
    a, b = a - a.mean(axis=0), b - b.mean(axis=0)
    denominator = np.sqrt(np.sum(a * a, axis=0) * np.sum(b * b, axis=0))
    correlation = np.divide(np.sum(a * b, axis=0), denominator,
                            out=np.zeros_like(denominator), where=denominator > 1e-12)
    return np.clip(correlation, 0, 1).astype(np.float32)


def control_features(mag_anom, rtp, gravity, valid, supported, *, batch_size=131072):
    """Construct zero-lag and phase-null features without changing physical reach.

    ``supported`` is the original TDX-1 finite support, reused exactly; passing a
    broader mask is rejected. The parent transform's 17 px support bounds gravity
    smoothing/gradient, flank sampling, magnetic smoothing and interpolation.
    """
    from scipy.ndimage import distance_transform_edt

    arrays = [np.asarray(x, dtype=np.float32) for x in (mag_anom, rtp, gravity)]
    valid, supported = np.asarray(valid, dtype=bool), np.asarray(supported, dtype=bool)
    if (valid.ndim != 2 or any(x.shape != valid.shape for x in [*arrays, supported])
            or not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1):
        raise ValueError("same-shaped 2D arrays and a positive integer batch size required")
    finite = valid & np.isfinite(arrays[0]) & np.isfinite(arrays[1]) & np.isfinite(arrays[2])
    support_limit = distance_transform_edt(np.pad(finite, 1, constant_values=False))[1:-1, 1:-1] > SUPPORT_PX
    g = gaussian_filter(np.where(finite, arrays[2], 0.0), 2.0, truncate=3.0)
    gy, gx = np.gradient(g)
    magnitude = np.hypot(gy, gx)
    expected_support = support_limit & (magnitude > 1e-12)
    if not np.array_equal(supported, expected_support) or not supported.any():
        raise ValueError("controls must reuse exactly the original nonempty TDX-1 support")
    ny = np.divide(gy, magnitude, out=np.zeros_like(gy), where=magnitude > 1e-12)
    nx = np.divide(gx, magnitude, out=np.zeros_like(gx), where=magnitude > 1e-12)
    rows_all, cols_all = np.nonzero(supported)
    outputs = {name: np.full(valid.shape, np.nan, dtype=np.float32) for name in CONTROL_FEATURES}
    for name, source in (("mag", arrays[0]), ("rtp", arrays[1])):
        smooth = [gaussian_filter(np.where(finite, source, 0.0), sigma, truncate=3.0)
                  for sigma in (1.0, 2.0)]
        for start in range(0, rows_all.size, batch_size):
            rr, cc = rows_all[start:start + batch_size], cols_all[start:start + batch_size]
            zeros, phases, lags = [], [], []
            for field in smooth:
                left, right = _profiles(field, rr.astype(np.float32), cc.astype(np.float32),
                                        ny[rr, cc], nx[rr, cc])
                zeros.append(zero_lag(left, right))
                evidence, lag = profile_lag(left, phase_scramble(right))
                phases.append(evidence); lags.append(lag)
            outputs[f"zero_{name}"][rr, cc] = np.sqrt(zeros[0] * zeros[1])
            outputs[f"phase_{name}"][rr, cc] = combine_scales(phases[0], lags[0], phases[1], lags[1])
    return outputs
