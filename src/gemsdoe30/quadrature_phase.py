"""Compact-support potential-field quadrature proxies for the QPC-1 lane.

This transform uses no catalogue information.  The local vector consists of a
high-pass component and the two normalized spatial derivatives of one field.
It is a scale-dependent phase *proxy*, not a physical dip/depth estimate or a
validated monogenic signal. Missing neighborhoods fail closed to NaN.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import gaussian_filter, minimum_filter

VERSION = "qpc1-highpass-gradient-v1-20261026"
SCALES = (1.0, 3.0)
TRUNCATE = 3.0
MAX_AXIAL_SUPPORT_PX = 9
SUPPORT_PX = math.ceil(math.sqrt(2.0) * MAX_AXIAL_SUPPORT_PX)
GUARD_PX = 17
EPSILON = 1e-12
RTP_INDEX = 1
GRAVITY_INDEX = 12
FEATURE_NAMES = (
    "qpc_mag_grav_phase_sigma1",
    "qpc_mag_grav_phase_sigma3",
    "qpc_mag_scale_persistence",
    "qpc_grav_scale_persistence",
)


def _unit_vector(field: np.ndarray, footprint: np.ndarray, sigma: float) -> tuple[np.ndarray, ...]:
    """Return three normalized components, NaN where support is incomplete.

    ``minimum_filter`` erodes the full square Gaussian window: no interpolation
    from a missing source cell or the outside-of-footprint fill reaches a
    feature used by the classifier. The window has a bounded Euclidean radius.
    """
    values = np.asarray(field, dtype=np.float32)
    valid = np.asarray(footprint, dtype=bool)
    if values.ndim != 2 or values.shape != valid.shape:
        raise ValueError("field and footprint must be same-shaped 2D arrays")
    if sigma not in SCALES:
        raise ValueError("scale was not preregistered")
    radius = int(TRUNCATE * sigma + 0.5)
    if radius > MAX_AXIAL_SUPPORT_PX:
        raise ValueError("source support exceeds the registered guard")
    ok = valid & np.isfinite(values) & (np.abs(values) < 1e30)
    interior = minimum_filter(ok.astype(np.uint8), size=2 * radius + 1,
                              mode="constant", cval=0).astype(bool)
    clean = np.where(ok, values, np.float32(0.0))
    smooth = gaussian_filter(clean, sigma=sigma, truncate=TRUNCATE, mode="constant", cval=0.0)
    even = clean - smooth
    del smooth
    gx = gaussian_filter(clean, sigma=sigma, order=(0, 1), truncate=TRUNCATE,
                         mode="constant", cval=0.0) * np.float32(sigma)
    gy = gaussian_filter(clean, sigma=sigma, order=(1, 0), truncate=TRUNCATE,
                         mode="constant", cval=0.0) * np.float32(sigma)
    norm = np.hypot(np.hypot(even, gx), gy)
    supported = interior & np.isfinite(norm) & (norm > EPSILON)
    for component in (even, gx, gy):
        np.divide(component, norm, out=component, where=supported)
        component[~supported] = np.nan
    return even, gx, gy


def _cosine(a: tuple[np.ndarray, ...], b: tuple[np.ndarray, ...]) -> np.ndarray:
    """Normalized signed co-location dot product; undefined support is NaN."""
    if len(a) != 3 or len(b) != 3 or any(x.shape != a[0].shape for x in (*a, *b)):
        raise ValueError("three matching vector components required")
    out = a[0] * b[0]
    out += a[1] * b[1]
    out += a[2] * b[2]
    np.clip(out, -1.0, 1.0, out=out)
    return out.astype(np.float32, copy=False)


def compute_features(base: np.ndarray, valid: np.ndarray, out: np.ndarray | None = None) -> np.ndarray:
    """Compute four frozen QPC-1 fields into an optional float32 memmap."""
    if base.ndim != 3 or base.shape[0] <= GRAVITY_INDEX or base.shape[1:] != valid.shape:
        raise ValueError("expected aligned [channels, height, width] stack and footprint")
    shape = (len(FEATURE_NAMES), *valid.shape)
    if out is None:
        out = np.empty(shape, dtype=np.float32)
    elif out.shape != shape or out.dtype != np.float32:
        raise ValueError("out must be a correctly shaped float32 array")
    mag1 = _unit_vector(base[RTP_INDEX], valid, SCALES[0])
    mag3 = _unit_vector(base[RTP_INDEX], valid, SCALES[1])
    grav1 = _unit_vector(base[GRAVITY_INDEX], valid, SCALES[0])
    grav3 = _unit_vector(base[GRAVITY_INDEX], valid, SCALES[1])
    out[0] = _cosine(mag1, grav1)
    out[1] = _cosine(mag3, grav3)
    out[2] = _cosine(mag1, mag3)
    out[3] = _cosine(grav1, grav3)
    return out
