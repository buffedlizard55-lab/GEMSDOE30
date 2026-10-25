"""TDX-1: gravity-normal magnetic profile correspondence, independent of fault labels.

A nonzero lag that improves profile correlation at two scales is a *candidate
signature*, not an estimated geological displacement. Intrusive contacts, gridding
artifacts and unrelated magnetic sources can produce the same signature.
"""
from __future__ import annotations

import math
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates

TRANSFORM_VERSION = "tdx1-profiles-v2-euclidean-support-20261025"
# scipy's separable Gaussian has SQUARE support. Its diagonal, the farthest
# profile sample, and bilinear interpolation must all fit a Euclidean guard.
MAX_SOURCE_REACH_PX = math.sqrt(2) * 6 + math.hypot(3, 6) + math.sqrt(2)
SUPPORT_PX = math.ceil(MAX_SOURCE_REACH_PX)  # 17, not the former 16


def profile_lag(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compare nine-sample profiles, allowing +/-2 samples of tangential lag.

    Inputs have shape (13, N), spanning tangent offsets -6..6. The left profile
    uses -4..4; the right is shifted by each proposed lag. Flat/undefined texture
    returns zero evidence, never invented correspondence. Exact ties prefer zero
    lag, then smaller absolute lags, so periodic/flat textures are not evidence.
    """
    left, right = np.asarray(left, dtype=np.float32), np.asarray(right, dtype=np.float32)
    if left.ndim != 2 or left.shape != right.shape or left.shape[0] != 13:
        raise ValueError("profiles must have the same (13, N) shape")
    if not (np.isfinite(left).all() and np.isfinite(right).all()):
        raise ValueError("profiles must be finite")
    a = left[2:11] - left[2:11].mean(axis=0)
    anorm = np.sqrt(np.sum(a * a, axis=0))
    corrs = []
    lags = np.array([0, -1, 1, -2, 2], dtype=np.int8)
    for lag in lags:
        b = right[2 + int(lag):11 + int(lag)]
        b = b - b.mean(axis=0)
        denom = anorm * np.sqrt(np.sum(b * b, axis=0))
        correlation = np.divide(np.sum(a * b, axis=0), denom,
                                out=np.zeros_like(denom), where=denom > 1e-12)
        corrs.append(np.clip(correlation, -1.0, 1.0))
    correlations = np.stack(corrs)
    best = np.argmax(correlations, axis=0)
    peak = np.take_along_axis(correlations, best[None], axis=0)[0]
    gain = np.maximum(peak - correlations[0], 0.0) / 2.0
    evidence = gain * np.maximum(peak, 0.0)
    return evidence.astype(np.float32), lags[best]


def combine_scales(evidence1, lag1, evidence2, lag2):
    """Require nonzero same-sign winning lags at the two registered scales."""
    same_direction = (np.sign(lag1) == np.sign(lag2)) & (lag1 != 0) & (lag2 != 0)
    return np.where(same_direction, np.sqrt(evidence1 * evidence2), 0.0).astype(np.float32)


def _profiles(field, rows, cols, ny, nx):
    tangent_y, tangent_x = -nx, ny
    profiles = []
    for flank in (-3.0, 3.0):
        samples = []
        for offset in range(-6, 7):
            y = rows + flank * ny + offset * tangent_y
            x = cols + flank * nx + offset * tangent_x
            samples.append(map_coordinates(field, [y, x], order=1, mode="constant", cval=0.0,
                                           prefilter=False))
        profiles.append(np.stack(samples))
    return profiles


def displacement_features(mag_anom, rtp, gravity, valid, *, batch_size=131072):
    """Construct two magnetic correspondence features and gravity-gradient amplitude.

    No labels, catalogue geometry, template values or registry data are accepted.
    Only fully supported finite physical data are used. Outputs are NaN where the
    17-pixel physical support is unavailable. No missing source values are silently
    converted into candidate evidence. Float32 batches bound memory consumption.
    """
    arrays = [np.asarray(x, dtype=np.float32) for x in (mag_anom, rtp, gravity)]
    valid = np.asarray(valid, dtype=bool)
    if valid.ndim != 2 or any(x.shape != valid.shape for x in arrays) or batch_size <= 0:
        raise ValueError("same-shaped 2D inputs and a positive batch size required")
    finite = valid.copy()
    for a in arrays:
        finite &= np.isfinite(a)
    # Pad explicitly: distance_transform_edt on an all-True array otherwise has
    # unintuitive implicit boundaries. Filters/sampling must not see raster edges.
    padded = np.pad(finite, 1, constant_values=False)
    supported = distance_transform_edt(padded)[1:-1, 1:-1] > SUPPORT_PX
    if not supported.any():
        raise ValueError("no pixels have the required physical support")
    g = gaussian_filter(np.where(finite, arrays[2], 0.0), 2.0, truncate=3.0)
    gy, gx = np.gradient(g)
    magnitude = np.hypot(gy, gx)
    normal_y = np.divide(gy, magnitude, out=np.zeros_like(gy), where=magnitude > 1e-12)
    normal_x = np.divide(gx, magnitude, out=np.zeros_like(gx), where=magnitude > 1e-12)
    supported &= magnitude > 1e-12
    rows_all, cols_all = np.nonzero(supported)
    outputs = {}
    for name, source in (("mag_texture", arrays[0]), ("rtp_texture", arrays[1])):
        smooth = [gaussian_filter(np.where(finite, source, 0.0), sigma, truncate=3.0)
                  for sigma in (1.0, 2.0)]
        output = np.full(valid.shape, np.nan, dtype=np.float32)
        for start in range(0, rows_all.size, batch_size):
            rr = rows_all[start:start + batch_size]
            cc = cols_all[start:start + batch_size]
            rows, cols = rr.astype(np.float32), cc.astype(np.float32)
            ny, nx = normal_y[rr, cc], normal_x[rr, cc]
            e1, l1 = profile_lag(*_profiles(smooth[0], rows, cols, ny, nx))
            e2, l2 = profile_lag(*_profiles(smooth[1], rows, cols, ny, nx))
            output[rr, cc] = combine_scales(e1, l1, e2, l2)
        outputs[name] = output
    outputs["gravity_edge"] = np.where(supported, magnitude, np.nan).astype(np.float32)
    outputs["supported"] = supported
    return outputs


def fold_consensus(mag_texture, rtp_texture, gravity_edge, train_mask):
    """Combine displacement evidence with training-only gravity normalization."""
    a, b, edge = (np.asarray(x, dtype=np.float32) for x in (mag_texture, rtp_texture, gravity_edge))
    train = np.asarray(train_mask, dtype=bool)
    if not (a.shape == b.shape == edge.shape == train.shape):
        raise ValueError("consensus inputs must share a shape")
    sample = edge[train & np.isfinite(edge) & (edge > 0)]
    if not sample.size:
        raise ValueError("no training-only gravity support")
    scale = float(np.quantile(sample, 0.95))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("invalid training-only gravity normalization")
    result = np.sqrt(a * b) * np.clip(edge / scale, 0.0, 1.0)
    return result.astype(np.float32), {"gravity_p95_training_only": scale,
                                      "normalization_pixels": int(sample.size)}
