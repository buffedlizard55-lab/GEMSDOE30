"""Reference implementation of the published GEMS distance-weighted Tversky metric.

The public competition description specifies a triangular kernel with 300 m support,
alpha=0.2 and beta=0.8.  The implementation uses pixel-centre Euclidean distances;
for raster workloads it uses SciPy's exact Euclidean distance transform when available.
A deliberately slow pure-Python path keeps small analytic tests dependency-free.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

DEFAULT_RADIUS_M = 300.0
DEFAULT_ALPHA = 0.2
DEFAULT_BETA = 0.8
DEFAULT_EPSILON = 1e-7


@dataclass(frozen=True)
class DTIComponents:
    """Sufficient statistics and the resulting distance-weighted Tversky score."""

    tp_weight: float
    fp_weight: float
    fn_weight: float
    score: float


def triangular_kernel(distance_m: float, radius_m: float = DEFAULT_RADIUS_M) -> float:
    """Return ``max(1 - distance / radius, 0)`` for a non-negative distance."""

    if not math.isfinite(float(radius_m)) or radius_m <= 0:
        raise ValueError("radius_m must be finite and positive")
    if not math.isfinite(float(distance_m)) or distance_m < 0:
        raise ValueError("distance_m must be finite and non-negative")
    return max(1.0 - float(distance_m) / float(radius_m), 0.0)


def dti_from_counts(
    tp_weight: float,
    fp_weight: float,
    fn_weight: float,
    *,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    epsilon: float = DEFAULT_EPSILON,
) -> float:
    """Compute the published weighted Tversky ratio from weighted counts."""

    if not all(math.isfinite(float(value)) for value in (tp_weight, fp_weight, fn_weight)):
        raise ValueError("weighted counts must be finite")
    if min(tp_weight, fp_weight, fn_weight) < 0:
        raise ValueError("weighted counts must be non-negative")
    if not all(math.isfinite(float(value)) for value in (alpha, beta, epsilon)):
        raise ValueError("alpha, beta, and epsilon must be finite")
    if alpha < 0 or beta < 0 or epsilon <= 0:
        raise ValueError("alpha/beta must be non-negative and epsilon positive")
    denominator = tp_weight + alpha * fp_weight + beta * fn_weight + epsilon
    return float(tp_weight / denominator)


def _as_python_grid(values: Any, name: str) -> list[list[float]]:
    """Convert a rectangular nested sequence to Python floats without NumPy."""

    try:
        rows = [list(row) for row in values]
    except TypeError as exc:
        raise ValueError(f"{name} must be a two-dimensional rectangular grid") from exc
    if not rows:
        raise ValueError(f"{name} must not be empty")
    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows):
        raise ValueError(f"{name} must be a non-empty rectangular grid")
    out: list[list[float]] = []
    for row in rows:
        converted: list[float] = []
        for value in row:
            if value is None:
                converted.append(float("nan"))
            else:
                try:
                    converted.append(float(value))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{name} contains a non-numeric value") from exc
        out.append(converted)
    return out


def _validate_parameters(
    pixel_size_x_m: float,
    pixel_size_y_m: float,
    radius_m: float,
    alpha: float,
    beta: float,
    epsilon: float,
) -> None:
    parameters = (pixel_size_x_m, pixel_size_y_m, radius_m, alpha, beta, epsilon)
    if not all(math.isfinite(float(value)) for value in parameters):
        raise ValueError("metric parameters must be finite")
    if pixel_size_x_m <= 0 or pixel_size_y_m <= 0:
        raise ValueError("pixel sizes must be positive")
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    if alpha < 0 or beta < 0:
        raise ValueError("alpha and beta must be non-negative")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")


def _distance_weighted_tversky_python(
    prediction: Any,
    truth: Any,
    valid_mask: Any,
    *,
    pixel_size_x_m: float,
    pixel_size_y_m: float,
    radius_m: float,
    alpha: float,
    beta: float,
    epsilon: float,
) -> DTIComponents:
    pred = _as_python_grid(prediction, "prediction")
    labels = _as_python_grid(truth, "truth")
    if len(pred) != len(labels) or len(pred[0]) != len(labels[0]):
        raise ValueError("prediction and truth shapes differ")
    height, width = len(pred), len(pred[0])

    if valid_mask is None:
        valid = [[math.isfinite(labels[y][x]) for x in range(width)] for y in range(height)]
    else:
        valid_values = _as_python_grid(valid_mask, "valid_mask")
        if len(valid_values) != height or len(valid_values[0]) != width:
            raise ValueError("valid_mask shape differs from prediction")
        valid = [[bool(valid_values[y][x]) for x in range(width)] for y in range(height)]

    truth_points: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if not valid[y][x]:
                continue
            p = pred[y][x]
            g = labels[y][x]
            if not math.isfinite(p) or p < 0.0 or p > 1.0:
                raise ValueError("prediction must be finite and in [0, 1] on valid pixels")
            if not math.isfinite(g) or g not in (0.0, 1.0):
                raise ValueError("truth must be binary (0/1) and finite on valid pixels")
            if g == 1.0:
                truth_points.append((y, x))

    radius_y = math.ceil(radius_m / pixel_size_y_m)
    radius_x = math.ceil(radius_m / pixel_size_x_m)
    offsets: list[tuple[int, int, float]] = []
    for dy in range(-radius_y, radius_y + 1):
        for dx in range(-radius_x, radius_x + 1):
            distance = math.hypot(dy * pixel_size_y_m, dx * pixel_size_x_m)
            if distance <= radius_m:
                offsets.append((dy, dx, triangular_kernel(distance, radius_m)))

    tp = 0.0
    fn = 0.0
    for gy, gx in truth_points:
        best_credit = 0.0
        for dy, dx, kernel in offsets:
            py, px = gy + dy, gx + dx
            if 0 <= py < height and 0 <= px < width and valid[py][px]:
                best_credit = max(best_credit, pred[py][px] * kernel)
        tp += best_credit
        fn += 1.0 - best_credit

    fp = 0.0
    for y in range(height):
        for x in range(width):
            if not valid[y][x] or pred[y][x] == 0.0:
                continue
            if truth_points:
                nearest = min(
                    math.hypot((y - gy) * pixel_size_y_m, (x - gx) * pixel_size_x_m)
                    for gy, gx in truth_points
                )
                fp += pred[y][x] * (1.0 - triangular_kernel(nearest, radius_m))
            else:
                fp += pred[y][x]

    return DTIComponents(tp, fp, fn, dti_from_counts(tp, fp, fn, alpha=alpha, beta=beta, epsilon=epsilon))


def _distance_weighted_tversky_numpy(
    prediction: Any,
    truth: Any,
    valid_mask: Any,
    *,
    pixel_size_x_m: float,
    pixel_size_y_m: float,
    radius_m: float,
    alpha: float,
    beta: float,
    epsilon: float,
) -> DTIComponents:
    import numpy as np

    pred = np.asarray(prediction, dtype=np.float64)
    labels = np.asarray(truth)
    if pred.ndim != 2 or labels.ndim != 2 or pred.shape != labels.shape:
        raise ValueError("prediction and truth must have the same two-dimensional shape")
    labels = labels.astype(np.float64, copy=False)
    if valid_mask is None:
        valid = np.isfinite(labels)
    else:
        valid = np.asarray(valid_mask, dtype=bool)
        if valid.shape != pred.shape:
            raise ValueError("valid_mask shape differs from prediction")
        if np.any(valid & ~np.isfinite(labels)):
            raise ValueError("truth must be finite on valid pixels")
    if np.any(~np.isfinite(pred[valid])) or np.any((pred[valid] < 0.0) | (pred[valid] > 1.0)):
        raise ValueError("prediction must be finite and in [0, 1] on valid pixels")
    if np.any(~np.isin(labels[valid], (0.0, 1.0))):
        raise ValueError("truth must be binary (0/1) and finite on valid pixels")

    p = np.where(valid, pred, 0.0)
    positive = valid & (labels == 1.0)
    radius_y = math.ceil(radius_m / pixel_size_y_m)
    radius_x = math.ceil(radius_m / pixel_size_x_m)
    credit = np.zeros(pred.shape, dtype=np.float64)
    height, width = pred.shape

    for dy in range(-radius_y, radius_y + 1):
        for dx in range(-radius_x, radius_x + 1):
            distance = math.hypot(dy * pixel_size_y_m, dx * pixel_size_x_m)
            if distance > radius_m:
                continue
            kernel = triangular_kernel(distance, radius_m)
            dst_y0, dst_y1 = max(0, -dy), min(height, height - dy)
            dst_x0, dst_x1 = max(0, -dx), min(width, width - dx)
            if dst_y0 >= dst_y1 or dst_x0 >= dst_x1:
                continue
            src_y0, src_y1 = dst_y0 + dy, dst_y1 + dy
            src_x0, src_x1 = dst_x0 + dx, dst_x1 + dx
            dst = credit[dst_y0:dst_y1, dst_x0:dst_x1]
            candidate = p[src_y0:src_y1, src_x0:src_x1] * kernel
            np.maximum(dst, candidate, out=dst)

    tp = float(np.sum(credit[positive], dtype=np.float64))
    fn = float(np.sum(1.0 - credit[positive], dtype=np.float64))

    if np.any(positive):
        try:
            from scipy.ndimage import distance_transform_edt
        except ImportError:
            if pred.size > 1_000_000:
                raise ImportError("SciPy is required for efficient DTI on large rasters")
            coords = np.argwhere(positive)
            yy, xx = np.indices(pred.shape)
            distance = np.full(pred.shape, np.inf, dtype=np.float64)
            for gy, gx in coords:
                candidate = np.hypot((yy - gy) * pixel_size_y_m, (xx - gx) * pixel_size_x_m)
                np.minimum(distance, candidate, out=distance)
        else:
            distance = distance_transform_edt(~positive, sampling=(pixel_size_y_m, pixel_size_x_m))
        fp_weight = np.minimum(distance / radius_m, 1.0)
    else:
        fp_weight = np.ones(pred.shape, dtype=np.float64)
    fp = float(np.sum(p[valid] * fp_weight[valid], dtype=np.float64))
    score = dti_from_counts(tp, fp, fn, alpha=alpha, beta=beta, epsilon=epsilon)
    return DTIComponents(tp, fp, fn, score)


def distance_weighted_tversky(
    prediction: Any,
    truth: Any,
    valid_mask: Any | None = None,
    *,
    pixel_size_x_m: float = 100.0,
    pixel_size_y_m: float = 100.0,
    radius_m: float = DEFAULT_RADIUS_M,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
    epsilon: float = DEFAULT_EPSILON,
) -> DTIComponents:
    """Evaluate a probability raster against binary truth using the GEMS geometry.

    ``valid_mask`` selects the pixels included in scoring and in the truth-distance
    field. If omitted, finite labels define the valid footprint, so NaN outside a
    raster footprint is ignored. Prediction values must be finite and in [0, 1]
    wherever the mask is true. Pixel sizes are supplied separately to support
    anisotropic projected grids; the competition grid is 100 m by 100 m.

    For large arrays, install NumPy and SciPy. The dependency-free fallback is
    intended for analytic examples and unit tests, not full competition rasters.
    """

    _validate_parameters(pixel_size_x_m, pixel_size_y_m, radius_m, alpha, beta, epsilon)
    if find_spec("numpy") is None:
        return _distance_weighted_tversky_python(
            prediction,
            truth,
            valid_mask,
            pixel_size_x_m=pixel_size_x_m,
            pixel_size_y_m=pixel_size_y_m,
            radius_m=radius_m,
            alpha=alpha,
            beta=beta,
            epsilon=epsilon,
        )
    # NumPy can be present while inputs are plain Python sequences; the vector
    # path handles both and keeps the full-raster implementation practical.
    return _distance_weighted_tversky_numpy(
        prediction,
        truth,
        valid_mask,
        pixel_size_x_m=pixel_size_x_m,
        pixel_size_y_m=pixel_size_y_m,
        radius_m=radius_m,
        alpha=alpha,
        beta=beta,
        epsilon=epsilon,
    )


def score_dti(prediction: Any, truth: Any, valid_mask: Any | None = None, **kwargs: Any) -> float:
    """Convenience wrapper returning only the distance-weighted Tversky score."""

    return distance_weighted_tversky(prediction, truth, valid_mask, **kwargs).score
