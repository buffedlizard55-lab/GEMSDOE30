"""Magnetic residual-ridge belief field, gated to the mapped-fault neighbourhood.

Review hypothesis 3 of ``docs/research/2026-10-25/review.md`` (design: ``docs/research/2026-10-25/candidate-residual-gate.md``):

1. Remove the part of the reduced-to-pole magnetic response (``rtp``) that is
   explained linearly by isostatic gravity, detrended elevation and basement depth.
   The fit uses NO fault labels, only the 19-band feature cube.
2. Negative residual ribbons (magnetically quiet, gravity-consistent corridors) are
   bright ridges of ``-residual``. A Hessian ridge detector (largest across-ridge
   curvature, scale-normalised) scores them.
3. The ridge score is multiplied by a gate that is zero beyond ``gate_m`` from the
   *visible* catalogue. Everything inside the gate is catalogue-adjacent; the
   magnetic ridge then chooses where inside that corridor to emit.

Non-fault mimic named in advance: nonmagnetic sediment fill (basin infill also gives
magnetic lows that are gravity-consistent). The gate deliberately does not remove it.

Nothing here reads hidden labels. Callers must pass only the visible catalogue.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

DEFAULT_SIGMA_PX = 2.0  # 200 m at the 100 m competition grid
DEFAULT_GATE_M = 3000.0


def _nan_gaussian(values: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Normalised Gaussian smoothing that ignores invalid cells (no NaN bleed)."""
    from scipy.ndimage import gaussian_filter

    weight = gaussian_filter(valid.astype(np.float64), sigma=sigma, mode="constant", truncate=8.0)
    filled = np.where(valid, values, 0.0).astype(np.float64)
    smooth = gaussian_filter(filled, sigma=sigma, mode="constant", truncate=8.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(weight > 1e-6, smooth / weight, np.nan)
    return out


def fit_residual(target: np.ndarray, regressors: Sequence[np.ndarray],
                 footprint: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    """Least-squares residual of ``target`` on ``regressors`` over the footprint.

    Returns ``(residual, info)``. Residual is NaN wherever any input is non-finite or
    outside ``footprint``. ``info`` records the coefficients and the fit's R^2 so the
    residual can be audited.
    """
    target = np.asarray(target, dtype=np.float64)
    footprint = np.asarray(footprint, dtype=bool)
    stack = [np.asarray(r, dtype=np.float64) for r in regressors]
    if any(r.shape != target.shape for r in stack) or target.shape != footprint.shape:
        raise ValueError("target, regressors and footprint must share one 2D shape")
    good = footprint & np.isfinite(target)
    for r in stack:
        good &= np.isfinite(r)
    if good.sum() < len(stack) + 10:
        raise ValueError("too few finite pixels to fit the residual")
    design = np.column_stack([np.ones(good.sum())] + [r[good] for r in stack])
    coef, *_ = np.linalg.lstsq(design, target[good], rcond=None)
    predicted = np.full(target.shape, np.nan)
    full = np.ones(target.shape, dtype=bool)
    for r in stack:
        full &= np.isfinite(r)
    full &= footprint
    predicted[full] = coef[0] + sum(c * r[full] for c, r in zip(coef[1:], stack))
    residual = np.where(good, target - predicted, np.nan)
    ss_res = float(np.nansum(residual[good] ** 2))
    ss_tot = float(np.sum((target[good] - target[good].mean()) ** 2))
    info = {
        "fit_pixels": int(good.sum()),
        "coefficients": [float(c) for c in coef],
        "r_squared": float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan"),
    }
    return residual.astype(np.float32), info


def ridge_strength(field: np.ndarray, valid: np.ndarray, sigma_px: float = DEFAULT_SIGMA_PX) -> np.ndarray:
    """Scale-normalised bright-ridge strength of ``field`` (>= 0, 0 outside ``valid``).

    Uses the most negative Hessian eigenvalue of the Gaussian-smoothed field. A bright
    ridge has strongly negative curvature across its crest.
    """
    from scipy.ndimage import gaussian_filter

    smooth = _nan_gaussian(np.asarray(field, dtype=np.float64), np.asarray(valid, dtype=bool), sigma_px)
    filled = np.where(np.isfinite(smooth), smooth, 0.0)
    hxx = gaussian_filter(filled, sigma=sigma_px, order=(0, 2), mode="reflect", truncate=8.0)
    hyy = gaussian_filter(filled, sigma=sigma_px, order=(2, 0), mode="reflect", truncate=8.0)
    hxy = gaussian_filter(filled, sigma=sigma_px, order=(1, 1), mode="reflect", truncate=8.0)
    half_trace = (hxx + hyy) / 2.0
    root = np.sqrt(((hxx - hyy) / 2.0) ** 2 + hxy ** 2)
    lambda_min = half_trace - root
    ridge = np.maximum(0.0, -lambda_min) * (sigma_px ** 2)
    ridge = np.where(np.asarray(valid, dtype=bool) & np.isfinite(ridge), ridge, 0.0)
    return ridge


def robust_zscore(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """(x - median) / (1.4826 MAD) over ``valid`` cells; zero elsewhere."""
    valid = np.asarray(valid, dtype=bool) & np.isfinite(values)
    med = float(np.median(values[valid]))
    mad = float(np.median(np.abs(values[valid] - med))) * 1.4826
    if not np.isfinite(mad) or mad <= 0:
        raise ValueError("degenerate scale: MAD is zero")
    return np.where(valid, (np.asarray(values, dtype=np.float64) - med) / mad, 0.0)


def gated_residual_ridge(residual: np.ndarray, valid: np.ndarray, distance_visible_m: np.ndarray,
                         *, sigma_px: float = DEFAULT_SIGMA_PX,
                         gate_m: float = DEFAULT_GATE_M) -> np.ndarray:
    """Belief = (negative-residual z-score >= 0) x normalised ridge x corridor gate.

    ``distance_visible_m`` must be the distance to VISIBLE catalogue traces only.
    The result is in [0, 1]; exactly 0 outside the gate and outside ``valid``.
    """
    valid = np.asarray(valid, dtype=bool)
    residual = np.asarray(residual, dtype=np.float64)
    distance = np.asarray(distance_visible_m, dtype=np.float64)
    if residual.shape != valid.shape or distance.shape != valid.shape:
        raise ValueError("residual, valid and distance must share one shape")
    if gate_m <= 0:
        raise ValueError("gate_m must be positive")
    usable = valid & np.isfinite(residual)
    z_quiet = robust_zscore(-residual, usable)  # high where residual is strongly negative
    z_smooth = _nan_gaussian(z_quiet, usable, sigma_px)
    z_smooth = np.where(usable & np.isfinite(z_smooth), z_smooth, 0.0)
    quiet = np.maximum(z_smooth, 0.0)
    ridge = ridge_strength(z_smooth, usable, sigma_px)
    in_footprint_ridge = ridge[usable]
    scale = float(np.percentile(in_footprint_ridge, 99.0)) if in_footprint_ridge.size else 0.0
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError("ridge scale is degenerate")
    ridge_norm = np.clip(ridge / scale, 0.0, 1.0)
    quiet_norm = np.clip(quiet / 3.0, 0.0, 1.0)  # 3 robust sigma saturates
    gate = (distance <= gate_m) & usable
    belief = np.where(gate, quiet_norm * ridge_norm, 0.0)
    return belief.astype(np.float32)
