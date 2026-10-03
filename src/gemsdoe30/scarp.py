"""Deterministic transforms for the reduced 3DEP-derived scarp descriptor stack.

The channel encodings documented by the owner mirror are decoded explicitly here;
these transforms are exploratory geology features, not organizer-provided layers or
fault labels.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.ndimage import uniform_filter


def _as_u8_grid(values: Any, name: str) -> np.ndarray:
    """Validate a 2-D uint8-encoded channel without silently clipping bad inputs."""

    array = np.asarray(values)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional grid")
    if not np.issubdtype(array.dtype, np.number):
        raise ValueError(f"{name} must be numeric")
    numeric = np.asarray(array, dtype=np.float32)
    if not np.all(np.isfinite(numeric)):
        raise ValueError(f"{name} must contain only finite uint8 codes")
    if np.any((numeric < 0.0) | (numeric > 255.0)):
        raise ValueError(f"{name} values must be within [0, 255]")
    if np.any(numeric != np.floor(numeric)):
        raise ValueError(f"{name} values must be integer uint8 codes")
    return numeric


def decode_sqrt_band(values: Any, *, xmax: float = 1.0) -> np.ndarray:
    """Decode the documented ``q = 1 + round(254*sqrt(x/xmax))`` encoding.

    Code 0 means missing data and decodes to 0. Code 1 is a valid encoded zero.
    """

    if not math.isfinite(float(xmax)) or xmax <= 0.0:
        raise ValueError("xmax must be finite and positive")
    codes = _as_u8_grid(values, "values")
    transformed = np.clip((codes - 1.0) / 254.0, 0.0, 1.0)
    return (transformed * transformed) * np.float32(xmax)


def decode_linear_band(values: Any, *, xmax: float = 1.0) -> np.ndarray:
    """Decode the documented ``q = 1 + round(254*x/xmax)`` encoding.

    Code 0 means missing data and decodes to 0. Code 1 is a valid encoded zero.
    """

    if not math.isfinite(float(xmax)) or xmax <= 0.0:
        raise ValueError("xmax must be finite and positive")
    codes = _as_u8_grid(values, "values")
    transformed = np.clip((codes - 1.0) / 254.0, 0.0, 1.0)
    return transformed.astype(np.float32) * np.float32(xmax)


def axial_strike_consensus(
    strike_u8: Any,
    valid_u8: Any,
    *,
    window_size: int = 3,
    min_support_cells: float = 3.0,
) -> np.ndarray:
    """Return a coverage-weighted, doubled-angle strike-persistence score.

    The source channel encodes an axial angle in [0, 180] degrees. Doubling the
    angle makes 0 and 180 equivalent and avoids requiring an undocumented compass
    convention. A support factor prevents a single valid cell from scoring as a
    persistent orientation.
    """

    if isinstance(window_size, bool) or not isinstance(window_size, (int, np.integer)):
        raise ValueError("window_size must be an odd positive integer")
    if window_size < 1 or window_size % 2 == 0:
        raise ValueError("window_size must be an odd positive integer")
    if not math.isfinite(float(min_support_cells)) or min_support_cells <= 0.0:
        raise ValueError("min_support_cells must be finite and positive")

    strike = _as_u8_grid(strike_u8, "strike_u8")
    coverage_codes = _as_u8_grid(valid_u8, "valid_u8")
    if strike.shape != coverage_codes.shape:
        raise ValueError("strike_u8 and valid_u8 shapes differ")

    coverage = decode_linear_band(coverage_codes)
    has_strike = (strike > 0.0) & (coverage > 0.0)
    theta = np.pi * np.clip((strike - 1.0) / 254.0, 0.0, 1.0)
    weight = np.where(has_strike, coverage, 0.0).astype(np.float32)
    cos_sum = uniform_filter(
        (weight * np.cos(2.0 * theta)).astype(np.float32),
        size=window_size,
        mode="constant",
        cval=0.0,
    )
    sin_sum = uniform_filter(
        (weight * np.sin(2.0 * theta)).astype(np.float32),
        size=window_size,
        mode="constant",
        cval=0.0,
    )
    mean_weight = uniform_filter(
        weight,
        size=window_size,
        mode="constant",
        cval=0.0,
    )
    norm = np.hypot(cos_sum, sin_sum)
    raw_consensus = np.divide(
        norm,
        mean_weight,
        out=np.zeros_like(norm, dtype=np.float32),
        where=mean_weight > 1e-6,
    )
    cell_equivalents = mean_weight * np.float32(window_size * window_size)
    support = np.clip(cell_equivalents / np.float32(min_support_cells), 0.0, 1.0)
    consensus = np.clip(raw_consensus * support, 0.0, 1.0)
    consensus[~has_strike] = 0.0
    return consensus.astype(np.float32, copy=False)


def scarp_orientation_score(
    step_max_u8: Any,
    downface_max_u8: Any,
    upface_max_u8: Any,
    coh100_u8: Any,
    strike_u8: Any,
    valid_u8: Any,
    *,
    window_size: int = 3,
    minimum_center_coverage: float = 0.5,
    min_support_cells: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the preregistered rank score and return ``(score, strike_consensus)``.

    ``step_max``, ``downface_max``, and ``upface_max`` are square-root encoded;
    ``coh100``, ``strike``, and ``valid`` are linear encoded. The score combines a
    relative slope step, the stronger of the two face responses, broad-orientation
    coherence, and LiDAR coverage. It is a ranking field in [0, 1], not a calibrated
    probability.
    """

    if not math.isfinite(float(minimum_center_coverage)) or not 0.0 <= minimum_center_coverage <= 1.0:
        raise ValueError("minimum_center_coverage must lie in [0, 1]")

    step = decode_sqrt_band(step_max_u8)
    downface = decode_sqrt_band(downface_max_u8)
    upface = decode_sqrt_band(upface_max_u8)
    coherence_band = decode_linear_band(coh100_u8)
    coverage = decode_linear_band(valid_u8)
    strike_codes = _as_u8_grid(strike_u8, "strike_u8")
    arrays = (downface, upface, coherence_band, coverage, strike_codes)
    if any(array.shape != step.shape for array in arrays):
        raise ValueError("all scarp channels must have the same two-dimensional shape")

    strike_consensus = axial_strike_consensus(
        strike_codes,
        valid_u8,
        window_size=window_size,
        min_support_cells=min_support_cells,
    )
    face = np.maximum(downface, upface)
    with np.errstate(invalid="ignore", over="ignore"):
        score = np.sqrt(step * face) * np.sqrt(coherence_band * strike_consensus) * coverage
    usable = (coverage >= np.float32(minimum_center_coverage)) & (strike_codes > 0)
    score = np.where(usable, score, 0.0).astype(np.float32)
    score = np.clip(np.nan_to_num(score, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    return score, strike_consensus
