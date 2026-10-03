"""Spatial holdout helpers; ordinary random pixel splits are intentionally avoided."""

from __future__ import annotations

from typing import Any

from .metric import (
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    DEFAULT_RADIUS_M,
    distance_weighted_tversky,
)


def validate_checkpoint_fold(checkpoint_fold: int | None, requested_fold: int | None) -> None:
    """Reject OOF inference unless checkpoint and requested held-out fold agree.

    ``None`` denotes a full-label fit and is valid only for full-grid inference.
    """

    if requested_fold is not None and requested_fold not in (0, 1, 2, 3):
        raise ValueError("requested fold must be 0, 1, 2, 3, or None")
    if checkpoint_fold is not None and checkpoint_fold not in (0, 1, 2, 3):
        raise ValueError("checkpoint fold metadata must be 0, 1, 2, 3, or None")
    if checkpoint_fold != requested_fold:
        raise ValueError(
            f"checkpoint was trained for fold {checkpoint_fold!r}, but inference requested {requested_fold!r}; "
            "fold-specific models cannot be relabeled or used for full-grid submission"
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
    """Compare two out-of-fold prediction mosaics under buffered spatial folds.

    Fold-isolated scores are diagnostics for spatial heterogeneity. The exact
    aggregate score is computed once over the complete valid OOF grid, preserving
    the metric's 300 m interactions across fold boundaries. Combining components
    from separately masked quadrants would omit those interactions and is not
    equivalent to the official full-grid metric.
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

    if not valid.any():
        raise ValueError("valid_mask contains no evaluation pixels")

    rows = []
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
        # These are useful localization diagnostics, but a quadrant-isolated DTI
        # drops kernel interactions across quadrant edges. Do not add these counts
        # together to estimate the full-grid score.
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
        rows.append(
            {
                "fold": fold,
                "fold_isolated_baseline_dti": base_part.score,
                "fold_isolated_candidate_dti": candidate_part.score,
                "fold_isolated_delta_dti": candidate_part.score - base_part.score,
                "heldout_valid_pixels": int(eval_mask.sum()),
                "heldout_truth_pixels": int(np.count_nonzero((labels == 1) & eval_mask)),
                "score_scope": "quadrant-isolated diagnostic; excludes cross-quadrant 300 m interactions",
            }
        )

    # The official metric has a local radius, so a truth pixel can receive credit
    # from an OOF prediction on the other side of a quadrant boundary. Conversely,
    # false-positive distance weights can use truth on either side of that edge.
    # The only exact pooled score is therefore a single evaluation over the entire
    # valid OOF mosaic, not a sum of independently masked quadrant components.
    baseline_full = distance_weighted_tversky(
        baseline,
        labels,
        valid,
        pixel_size_x_m=pixel_size_x_m,
        pixel_size_y_m=pixel_size_y_m,
        radius_m=radius_m,
        alpha=alpha,
        beta=beta,
    )
    candidate_full = distance_weighted_tversky(
        candidate,
        labels,
        valid,
        pixel_size_x_m=pixel_size_x_m,
        pixel_size_y_m=pixel_size_y_m,
        radius_m=radius_m,
        alpha=alpha,
        beta=beta,
    )
    pooled_baseline = {
        "tp_weight": baseline_full.tp_weight,
        "fp_weight": baseline_full.fp_weight,
        "fn_weight": baseline_full.fn_weight,
        "dti": baseline_full.score,
    }
    pooled_candidate = {
        "tp_weight": candidate_full.tp_weight,
        "fp_weight": candidate_full.fp_weight,
        "fn_weight": candidate_full.fn_weight,
        "dti": candidate_full.score,
    }
    return {
        "folds": rows,
        "pooled_baseline": pooled_baseline,
        "pooled_candidate": pooled_candidate,
        "pooled_delta_dti": pooled_candidate["dti"] - pooled_baseline["dti"],
        "aggregation": "exact full-grid DTI on the stitched out-of-fold mosaic; cross-quadrant kernel interactions retained",
        "scope": "catalogue-derived spatial proxy; not private-test truth or a competition score",
    }
