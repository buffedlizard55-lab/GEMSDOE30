"""Diagnostics for whether metric geometry changes held-out near-miss behavior."""

from __future__ import annotations

import math
from typing import Any

from .metric import DEFAULT_RADIUS_M


def near_miss_profile(
    prediction: Any,
    truth: Any,
    valid_mask: Any,
    *,
    pixel_size_x_m: float = 100.0,
    pixel_size_y_m: float = 100.0,
    radius_m: float = DEFAULT_RADIUS_M,
) -> dict[str, Any]:
    """Summarize best kernel-credit distances and false-positive distance costs.

    The best-distance histogram is computed per held-out truth pixel using the same
    ``max_x p(x) k(d(x,g))`` operation as the scorer. The FP table bins ``p(x)``
    by distance to the nearest held-out truth pixel and reports the associated
    ``p(x) * (1-k(d))`` mass. It is a diagnostic, not a separate score.
    """

    try:
        import numpy as np
        from scipy.ndimage import distance_transform_edt
    except ImportError as exc:  # pragma: no cover - optional analysis dependencies
        raise RuntimeError("NumPy and SciPy are required for near-miss profiles") from exc

    p = np.asarray(prediction, dtype=np.float64)
    g = np.asarray(truth)
    valid = np.asarray(valid_mask, dtype=bool)
    if p.ndim != 2 or g.shape != p.shape or valid.shape != p.shape:
        raise ValueError("prediction, truth, and valid_mask must have identical 2D shapes")
    if np.any(~np.isfinite(p[valid])) or np.any((p[valid] < 0.0) | (p[valid] > 1.0)):
        raise ValueError("prediction must be finite and within [0, 1] on valid pixels")
    if np.any(~np.isin(g[valid], (0, 1, 0.0, 1.0))):
        raise ValueError("truth must be binary on valid pixels")
    if radius_m <= 0 or pixel_size_x_m <= 0 or pixel_size_y_m <= 0:
        raise ValueError("radius and pixel sizes must be positive")

    positive = valid & (g == 1)
    if not positive.any():
        return {
            "heldout_truth_pixels": 0,
            "best_credit_distance_bins": {},
            "false_positive_cost_by_distance": [],
            "note": "no positive truth in this spatial fold; distance profile is undefined",
        }

    radius_x = math.ceil(radius_m / pixel_size_x_m)
    radius_y = math.ceil(radius_m / pixel_size_y_m)
    offsets = []
    for dy in range(-radius_y, radius_y + 1):
        for dx in range(-radius_x, radius_x + 1):
            distance = math.hypot(dy * pixel_size_y_m, dx * pixel_size_x_m)
            if distance <= radius_m:
                offsets.append((dy, dx, distance, max(1.0 - distance / radius_m, 0.0)))

    best_bins = {
        "exact_0m": 0,
        "near_0_to_100m": 0,
        "100_to_200m": 0,
        "200_to_300m": 0,
        "no_positive_credit": 0,
    }
    for gy, gx in np.argwhere(positive):
        best_value = 0.0
        best_distance = None
        for dy, dx, distance, kernel in offsets:
            py, px = int(gy + dy), int(gx + dx)
            if 0 <= py < p.shape[0] and 0 <= px < p.shape[1] and valid[py, px]:
                credit = p[py, px] * kernel
                if credit > best_value:
                    best_value = float(credit)
                    best_distance = distance
        if best_distance is None or best_value <= 0.0:
            best_bins["no_positive_credit"] += 1
        elif best_distance == 0:
            best_bins["exact_0m"] += 1
        elif best_distance < 100:
            best_bins["near_0_to_100m"] += 1
        elif best_distance < 200:
            best_bins["100_to_200m"] += 1
        else:
            best_bins["200_to_300m"] += 1

    distance_to_truth = distance_transform_edt(
        ~positive,
        sampling=(pixel_size_y_m, pixel_size_x_m),
    )
    edges = ((0.0, 100.0), (100.0, 200.0), (200.0, 300.0), (300.0, math.inf))
    names = ("0_to_100m", "100_to_200m", "200_to_300m", "300m_or_more")
    fp_rows = []
    for (lo, hi), name in zip(edges, names):
        band = valid & (distance_to_truth >= lo) & (distance_to_truth < hi)
        d = distance_to_truth[band]
        probs = p[band]
        kernel = np.maximum(1.0 - d / radius_m, 0.0)
        fp_rows.append(
            {
                "distance_bin": name,
                "pixels": int(band.sum()),
                "probability_mass": float(probs.sum()),
                "weighted_false_positive_mass": float(np.sum(probs * (1.0 - kernel))),
            }
        )
    return {
        "heldout_truth_pixels": int(positive.sum()),
        "best_credit_distance_bins": best_bins,
        "false_positive_cost_by_distance": fp_rows,
        "note": "a changed profile is evidence about proxy error allocation, not new-fault truth",
    }
