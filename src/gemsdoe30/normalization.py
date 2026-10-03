"""Fold-local robust feature scaling for honest spatial validation."""

from __future__ import annotations

from typing import Any


def fit_robust_feature_stats(
    features: Any,
    fit_mask: Any,
    *,
    seed: int = 30,
    tile_size: int = 512,
    max_samples_per_tile: int = 512,
) -> list[dict[str, float | int]]:
    """Fit deterministic, spatially balanced median/IQR statistics on fit pixels only.

    Sampling is capped independently in each spatial tile so large tiles do not
    dominate the normalization. ``fit_mask`` should contain training-fold pixels
    only; held-out labels and feature values outside that mask are never sampled.
    """

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional training dependency
        raise RuntimeError("NumPy is required for feature normalization") from exc

    values = np.asanyarray(features)
    mask = np.asarray(fit_mask, dtype=bool)
    if values.ndim != 3:
        raise ValueError("features must have shape [channels, height, width]")
    if mask.ndim != 2 or values.shape[1:] != mask.shape:
        raise ValueError("fit_mask must match the feature grid")
    if tile_size < 1 or max_samples_per_tile < 1:
        raise ValueError("tile_size and max_samples_per_tile must be positive")
    if not mask.any():
        raise ValueError("feature normalization fit mask is empty")

    rng = np.random.default_rng(seed)
    channel_samples: list[list[Any]] = [[] for _ in range(values.shape[0])]
    height, width = mask.shape
    for row in range(0, height, tile_size):
        row_end = min(row + tile_size, height)
        for col in range(0, width, tile_size):
            col_end = min(col + tile_size, width)
            local_mask = mask[row:row_end, col:col_end]
            if not local_mask.any():
                continue
            for channel in range(values.shape[0]):
                band = np.asarray(values[channel, row:row_end, col:col_end], dtype=np.float32)
                good = local_mask & np.isfinite(band)
                samples = band[good]
                if samples.size > max_samples_per_tile:
                    samples = samples[rng.choice(samples.size, max_samples_per_tile, replace=False)]
                if samples.size:
                    channel_samples[channel].append(samples)

    stats: list[dict[str, float | int]] = []
    for channel, parts in enumerate(channel_samples, start=1):
        if not parts:
            raise ValueError(f"feature channel {channel} has no finite training-fold samples")
        samples = np.concatenate(parts).astype(np.float64, copy=False)
        q25, median, q75 = (float(item) for item in np.percentile(samples, [25, 50, 75]))
        iqr = q75 - q25
        if not np.isfinite(iqr) or iqr < 1e-6:
            iqr = 1.0
        stats.append(
            {
                "median": median,
                "iqr": iqr,
                "sampled_min": float(samples.min()),
                "sampled_max": float(samples.max()),
                "sample_count": int(samples.size),
            }
        )
    return stats


def normalize_feature_block(
    block: Any,
    feature_stats: list[dict[str, Any]],
    *,
    clip: float = 8.0,
) -> Any:
    """Apply checkpointed per-channel median/IQR scaling; map missing values to 0."""

    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - optional training dependency
        raise RuntimeError("NumPy is required for feature normalization") from exc

    values = np.asarray(block, dtype=np.float32).copy()
    if values.ndim != 3 or values.shape[0] != len(feature_stats):
        raise ValueError("feature block must be [channels, height, width] and match feature_stats")
    if clip <= 0:
        raise ValueError("clip must be positive")
    for channel, stats in enumerate(feature_stats):
        median, iqr = float(stats["median"]), float(stats["iqr"])
        if not np.isfinite(median) or not np.isfinite(iqr) or iqr <= 0:
            raise ValueError(f"invalid normalization statistics for feature channel {channel + 1}")
        band = values[channel]
        finite = np.isfinite(band)
        band[finite] = np.clip((band[finite] - median) / iqr, -clip, clip)
        band[~finite] = 0.0
    return values
