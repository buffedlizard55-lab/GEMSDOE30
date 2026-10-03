"""Spatial holdout helpers; ordinary random pixel splits are intentionally avoided."""

from __future__ import annotations

from typing import Any

from .metric import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_RADIUS_M,
    DTIComponents,
    distance_weighted_tversky,
    dti_from_counts,
)


def spatial_quadrant_masks(
    valid_mask: Any,
    fold: int,
    *,
    pixel_size_x_m: float = 100.0,
    pixel_size_y_m: float = 100.0,
    buffer_m: float = DEFAULT_RADIUS_M,
) -> tuple[Any, Any]:
    """Return ``(train_mask, validation_mask)`` for one buffered spatial quadrant.

    The held-out block is one of four fixed quadrants. Training is excluded from
    the whole held-out block and from a metric-radius buffer around its boundary.
    This is a deliberately conservative spatial proxy, not a reconstruction of the
    organizer's private test split and not independent new-fault truth.
    """

    try:
        import numpy as np
        from scipy.ndimage import distance_transform_edt
    except ImportError as exc:  # pragma: no cover - optional geospatial dependencies
        raise RuntimeError("NumPy and SciPy are required for spatial fold construction") from exc

    valid = np.asarray(valid_mask, dtype=bool)
    if valid.ndim != 2 or min(valid.shape) < 2:
        raise ValueError("valid_mask must be a 2D grid at least 2 by 2")
    if fold not in (0, 1, 2, 3):
        raise ValueError("fold must be 0, 1, 2, or 3")
    if pixel_size_x_m <= 0 or pixel_size_y_m <= 0 or buffer_m < 0:
        raise ValueError("pixel sizes must be positive and buffer_m non-negative")

    height, width = valid.shape
    row_mid, col_mid = height // 2, width // 2
    row_slices = (slice(0, row_mid), slice(row_mid, height))
    col_slices = (slice(0, col_mid), slice(col_mid, width))
    quadrant = np.zeros(valid.shape, dtype=bool)
    quadrant[row_slices[fold // 2], col_slices[fold % 2]] = True
    validation = quadrant & valid

    if buffer_m == 0:
        train = valid & ~quadrant
    else:
        # Distance-transform input is false inside the held-out block. EDT therefore
        # returns distance from every outside pixel to that block's nearest cell.
        distance_to_validation = distance_transform_edt(
            ~quadrant,
            sampling=(pixel_size_y_m, pixel_size_x_m),
        )
        train = valid & ~quadrant & (distance_to_validation > buffer_m)
    return train, validation


def _pool_components(parts: list[DTIComponents], *, alpha: float, beta: float) -> dict[str, float]:
    tp = sum(part.tp_weight for part in parts)
    fp = sum(part.fp_weight for part in parts)
    fn = sum(part.fn_weight for part in parts)
    return {
        "tp_weight": tp,
        "fp_weight": fp,
        "fn_weight": fn,
        "dti": dti_from_counts(tp, fp, fn, alpha=alpha, beta=beta),
    }


def compare_spatial_holdout(
    truth: Any,
    baseline_prediction: Any,
    candidate_prediction: Any,
    valid_mask: Any,
    *,
    pixel_size_x_m: float = 100.0,
    pixel_size_y_m: float = 100.0,
    radius_m: float = DEFAULT_RADIUS_M,
    buffer_m: float = DEFAULT_RADIUS_M,
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> dict[str, Any]:
    """Compare two full-grid predictions on four buffered spatial folds.

    DTI is computed from the public metric implementation. Fold scores are reported
    for heterogeneity, while ``pooled`` combines weighted counts before dividing,
    which is the correct way to aggregate DTI rather than averaging ratios.
    """

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional geospatial dependency
        raise RuntimeError("NumPy is required for spatial holdout scoring") from exc

    labels = np.asarray(truth)
    baseline = np.asarray(baseline_prediction)
    candidate = np.asarray(candidate_prediction)
    valid = np.asarray(valid_mask, dtype=bool)
    if labels.ndim != 2 or baseline.shape != labels.shape or candidate.shape != labels.shape or valid.shape != labels.shape:
        raise ValueError("truth, predictions, and valid_mask must share a 2D grid")

    rows = []
    baseline_parts: list[DTIComponents] = []
    candidate_parts: list[DTIComponents] = []
    for fold in range(4):
        _, eval_mask = spatial_quadrant_masks(
            valid,
            fold,
            pixel_size_x_m=pixel_size_x_m,
            pixel_size_y_m=pixel_size_y_m,
            buffer_m=buffer_m,
        )
        if not np.any(eval_mask):
            raise ValueError(f"spatial fold {fold} has no valid evaluation pixels")
        base_part = distance_weighted_tversky(
            baseline,
            labels,
            eval_mask,
            pixel_size_x_m=pixel_size_x_m,
            pixel_size_y_m=pixel_size_y_m,
            radius_m=radius_m,
            alpha=alpha,
            beta=beta,
        )
        candidate_part = distance_weighted_tversky(
            candidate,
            labels,
            eval_mask,
            pixel_size_x_m=pixel_size_x_m,
            pixel_size_y_m=pixel_size_y_m,
            radius_m=radius_m,
            alpha=alpha,
            beta=beta,
        )
        baseline_parts.append(base_part)
        candidate_parts.append(candidate_part)
        rows.append(
            {
                "fold": fold,
                "baseline_dti": base_part.score,
                "candidate_dti": candidate_part.score,
                "delta_dti": candidate_part.score - base_part.score,
                "heldout_valid_pixels": int(eval_mask.sum()),
                "heldout_truth_pixels": int(np.count_nonzero((labels == 1) & eval_mask)),
            }
        )

    pooled_baseline = _pool_components(baseline_parts, alpha=alpha, beta=beta)
    pooled_candidate = _pool_components(candidate_parts, alpha=alpha, beta=beta)
    return {
        "folds": rows,
        "pooled_baseline": pooled_baseline,
        "pooled_candidate": pooled_candidate,
        "pooled_delta_dti": pooled_candidate["dti"] - pooled_baseline["dti"],
        "scope": "catalogue-derived spatial proxy; not private-test truth or a competition score",
    }
