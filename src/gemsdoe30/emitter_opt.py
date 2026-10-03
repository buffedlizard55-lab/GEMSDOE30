"""EDGE: expected-marginal-DTI greedy emitter for the published GEMS index.

Why this module exists
----------------------
Every previously tested emission rule in this repository visits *candidate
pixels* in an order fixed before any metric is evaluated:

* ``dense``    - keep everything above a belief threshold (order = belief value),
* ``uniform``  - Poisson-disk thinning at a fixed radius (order = belief value),
* ``adaptive`` - belief-adaptive thinning (order = belief value),
* ``metric``   - accept a belief-ordered candidate when its marginal rule
  ``dA > lambda * dF`` holds (order = belief value, truncated by a pool cap).

The published index is ``DTI = A / (alpha*(A + F) + (1 - alpha)*G)`` with
``A`` the kernel credit delivered to the truth field, ``F`` the distance-weighted
false-positive mass and ``G`` the truth count.  The quantity that decides whether
an added dot helps is its *marginal credit per unit of false-positive mass*, not
its belief value, and the credit of a dot depends on what neighbours were already
emitted (the metric takes a maximum, so duplicate credit is worth nothing).  A
belief-ordered sweep therefore stops at an arbitrary point of the exchange curve;
it cannot see that a low-belief pixel in an empty neighbourhood can beat a
high-belief pixel in a crowded one.

:func:`edge_select` provides the missing operator.  It ranks candidates by their
*expected marginal credit gain*

    dT(x) = sum_delta pi(x + delta) * max(0, k(delta) - C(x + delta))

with ``pi`` the belief field (expected truth mass per pixel), ``k`` the official
triangular kernel and ``C`` the credit already delivered to each truth pixel by
the accepted dots.  Greedy maximisation of a monotone submodular coverage
function is the classical (1 - 1/e) approximation, and ``dT`` is exactly that
coverage gain; the accepted set is therefore order-optimal up to that bound,
independent of any belief ranking.  The sweep then stops at the *exact* marginal
stopping point of the published index,

    dT > alpha * s / (1 - alpha * s) * dF,      s = DTI of the accepted set,

evaluated with the accumulated expected statistics, so every rule (including this
one) chooses its own dot count.  Match-count designs cannot compare emitters here
(the previous registered emission gate failed for exactly that reason).

Honest scope
------------
``pi`` is a *belief* field: this module optimises the expected index given that
belief, and it inherits every error in the belief.  A holdout pass is necessary
evidence, never a competition score, and the catalogue-based stand-in truth used
by the repository's holdouts is biased because the organizer masks known
USGS/INGENIOUS pixels out of the real evaluation.
"""

from __future__ import annotations

import math
from typing import Any

DEFAULT_ALPHA = 0.2
DEFAULT_BETA = 0.8
DEFAULT_EPSILON = 1e-7
DEFAULT_RADIUS_M = 300.0
DEFAULT_PIXEL_M = 100.0


def kernel_offsets(
    pixel_m: float = DEFAULT_PIXEL_M,
    radius_m: float = DEFAULT_RADIUS_M,
) -> list[tuple[int, int, float]]:
    """Return ``(dy, dx, k)`` for every pixel centre within the kernel support.

    ``k = max(1 - d / radius_m, 0)`` is the published triangular kernel, exactly as
    in :mod:`gemsdoe30.metric`; the list is symmetric in ``(dy, dx)``.
    """

    if not math.isfinite(float(pixel_m)) or pixel_m <= 0:
        raise ValueError("pixel_m must be finite and positive")
    if not math.isfinite(float(radius_m)) or radius_m <= 0:
        raise ValueError("radius_m must be finite and positive")
    reach_y = int(math.ceil(radius_m / pixel_m))
    reach_x = int(math.ceil(radius_m / pixel_m))
    offsets: list[tuple[int, int, float]] = []
    for dy in range(-reach_y, reach_y + 1):
        for dx in range(-reach_x, reach_x + 1):
            distance = pixel_m * math.hypot(dy, dx)
            if distance <= radius_m:
                offsets.append((dy, dx, max(1.0 - distance / radius_m, 0.0)))
    if not offsets:
        raise ValueError("kernel support is empty")
    return offsets


def marginal_threshold(dti: float, alpha: float = DEFAULT_ALPHA) -> float:
    """Return ``alpha*s / (1 - alpha*s)``, the credit/cost ratio that pays off.

    Derived from ``DTI = A / (alpha*(A + F) + (1 - alpha)*G)``: adding ``dA`` at
    false-positive cost ``dF`` raises the index exactly when
    ``dA/dF > alpha*s/(1 - alpha*s)`` for the current value ``s``.
    """

    if not math.isfinite(float(dti)) or not 0.0 <= dti < 1.0 / alpha:
        raise ValueError("dti must be finite and inside [0, 1/alpha)")
    return alpha * dti / (1.0 - alpha * dti)


def expected_dti(tp: float, fp: float, truth_mass: float, *,
                 alpha: float = DEFAULT_ALPHA,
                 epsilon: float = DEFAULT_EPSILON) -> float:
    """Expected index from expected sufficient statistics (beta = 1 - alpha)."""

    if min(tp, fp, truth_mass) < 0:
        raise ValueError("statistics must be non-negative")
    if tp > truth_mass + 1e-6:
        raise ValueError("tp cannot exceed the modelled truth mass")
    return float(tp / (alpha * (tp + fp) + (1.0 - alpha) * truth_mass + epsilon))


def _kernel_array(offsets: list[tuple[int, int, float]]) -> Any:
    import numpy as np

    rows = [offset[0] for offset in offsets]
    cols = [offset[1] for offset in offsets]
    kernels = np.array([offset[2] for offset in offsets], dtype=np.float32)
    height = max(rows) - min(rows) + 1
    width = max(cols) - min(cols) + 1
    array = np.zeros((height, width), dtype=np.float32)
    array[np.array(rows) - min(rows), np.array(cols) - min(cols)] = kernels
    return array


def coverage_credit(selected: Any, *,
                    pixel_m: float = DEFAULT_PIXEL_M,
                    radius_m: float = DEFAULT_RADIUS_M,
                    offsets: list[tuple[int, int, float]] | None = None) -> Any:
    """Return the per-pixel credit ``C(g) = max_x p(x) k(d(g, x))`` of a mask.

    This mirrors the published metric's maximum rule (as in
    :func:`gemsdoe30.emission.kernel_credit`) and is used both to score emitters
    and to verify the incremental update inside :func:`edge_select`.
    """

    import numpy as np

    values = np.asarray(selected)
    if values.ndim != 2:
        raise ValueError("selected must be two-dimensional")
    offsets = offsets if offsets is not None else kernel_offsets(pixel_m, radius_m)
    reach_y = max(abs(offset[0]) for offset in offsets)
    reach_x = max(abs(offset[1]) for offset in offsets)
    credit = np.zeros(values.shape, dtype=np.float32)
    source = values.astype(np.float32)
    padded = np.pad(source, ((reach_y, reach_y), (reach_x, reach_x)), mode="constant")
    height, width = values.shape
    for dy, dx, weight in offsets:
        window = padded[reach_y + dy: reach_y + dy + height,
                       reach_x + dx: reach_x + dx + width] * weight
        np.maximum(credit, window, out=credit)
    return credit


def edge_select(
    belief: Any,
    support: Any | None = None,
    *,
    truth_mass: float | None = None,
    max_dots: int = 200_000,
    alpha: float = DEFAULT_ALPHA,
    epsilon: float = DEFAULT_EPSILON,
    pixel_m: float = DEFAULT_PIXEL_M,
    radius_m: float = DEFAULT_RADIUS_M,
    offsets: list[tuple[int, int, float]] | None = None,
    return_diagnostics: bool = False,
) -> Any:
    """Greedily emit dots by *expected marginal index gain* (see module docstring).

    Args:
        belief: non-negative belief surface; interpreted up to a global scale.
        support: boolean candidate domain (e.g. the scored footprint).  Pixels
            outside it are never emitted and deliver no credit.
        truth_mass: expected number of truth pixels represented by ``belief``.
            ``None`` uses the raw belief sum, which is only meaningful when the
            input is already calibrated as expected truth mass.  The greedy order
            does **not** depend on this value, so a single call can be re-stopped
            at another mass with :func:`stop_index`.
        max_dots: hard cap on accepted dots (safety bound for the sweep).
        alpha, epsilon: published index parameters.
        pixel_m, radius_m, offsets: kernel geometry.
        return_diagnostics: also return the trajectory dictionary.

    Returns:
        A boolean emission mask, or ``(mask, diagnostics)`` when
        ``return_diagnostics`` is true.  Diagnostics carry the acceptance order,
        the cumulative expected credit/cost and the stopping statistics.  A belief
        surface that is identically zero inside the support returns an empty mask
        rather than raising, which keeps degenerate sweeps safe to run.

    Note:
        Where the belief is certain (``pi`` near 1) the expected false-positive
        weight of a dot is zero and EDGE will tile the ridge: no spacing constraint
        is imposed, and spacing is an emergent consequence of *uncertainty* — a
        property the published metric shares, because a prediction placed exactly
        on a truth pixel pays no false-positive penalty at all.
    """

    import numpy as np
    from scipy.ndimage import correlate

    values = np.asarray(belief, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("belief must be two-dimensional")
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("belief must be finite and non-negative")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be inside (0, 1)")
    if int(max_dots) < 1:
        raise ValueError("max_dots must be a positive integer")

    offsets = offsets if offsets is not None else kernel_offsets(pixel_m, radius_m)
    # Zero-weight offsets (distance exactly at the support radius) carry no credit
    # and no cost; dropping them is metric-preserving and shrinks the update box.
    offsets = [offset for offset in offsets if offset[2] > 0.0]
    if not offsets:
        raise ValueError("kernel has no positive-weight offsets")
    reach_y = max(abs(offset[0]) for offset in offsets)
    reach_x = max(abs(offset[1]) for offset in offsets)

    domain = np.isfinite(values)
    if support is not None:
        support_array = np.asarray(support, dtype=bool)
        if support_array.shape != values.shape:
            raise ValueError("support shape differs from belief")
        domain &= support_array

    pi = np.where(domain, values, 0.0).astype(np.float32)
    total_belief = float(pi.sum(dtype=np.float64))
    if total_belief <= 0.0:
        empty = np.zeros(values.shape, dtype=bool)
        diagnostics = {
            "accepted": 0, "truth_mass": 0.0, "expected_tp": 0.0,
            "expected_fp": 0.0, "expected_dti": 0.0,
            "order_flat": np.zeros(0, dtype=np.int64),
            "cumulative_tp": np.zeros(0, dtype=np.float64),
            "cumulative_fp": np.zeros(0, dtype=np.float64),
        }
        return (empty, diagnostics) if return_diagnostics else empty
    if truth_mass is None:
        truth_mass = total_belief
    if not math.isfinite(float(truth_mass)) or truth_mass <= 0:
        raise ValueError("truth_mass must be finite and positive")
    pi *= np.float32(float(truth_mass) / total_belief)

    kernel = _kernel_array(offsets)

    # Expected credit delivered by exactly one dot at each pixel centre, and the
    # expected false-positive weight of a dot placed there:
    #   wF(x) = clip(1 - sum_g pi(g) k(d(x, g)), 0, 1)
    # A dot whose expected credit already reaches 1 is inside the modelled truth
    # support and costs nothing.
    potential = correlate(pi, kernel, mode="constant", cval=0.0).astype(np.float32)
    fp_weight = np.clip(1.0 - potential, 0.0, 1.0).astype(np.float32)

    credit = np.zeros(values.shape, dtype=np.float32)          # credit already delivered
    gain = potential.copy()                                     # marginal credit of a new dot
    gain[~domain] = -np.inf

    flat_gain = gain.ravel()
    eligible = np.flatnonzero(domain.ravel())
    if eligible.size == 0:
        empty = np.zeros(values.shape, dtype=bool)
        diagnostics = {
            "accepted": 0, "truth_mass": float(truth_mass), "expected_tp": 0.0,
            "expected_fp": 0.0, "expected_dti": 0.0,
            "order_flat": np.zeros(0, dtype=np.int64),
            "cumulative_tp": np.zeros(0, dtype=np.float64),
            "cumulative_fp": np.zeros(0, dtype=np.float64),
        }
        return (empty, diagnostics) if return_diagnostics else empty
    eligible_gain = flat_gain[eligible]

    offset_rows = np.array([offset[0] for offset in offsets], dtype=np.int64)
    offset_cols = np.array([offset[1] for offset in offsets], dtype=np.int64)
    offset_weights = np.array([offset[2] for offset in offsets], dtype=np.float32)

    box_rows = np.arange(-2 * reach_y, 2 * reach_y + 1, dtype=np.int64)
    box_cols = np.arange(-2 * reach_x, 2 * reach_x + 1, dtype=np.int64)
    box_dy, box_dx = np.meshgrid(box_rows, box_cols, indexing="ij")
    box_dy = box_dy.ravel()
    box_dx = box_dx.ravel()

    height, width = values.shape
    flat_width = width
    chosen = np.zeros(eligible.size, dtype=bool)
    order: list[int] = []
    cumulative_tp = [0.0]
    cumulative_fp = [0.0]
    total_tp = 0.0
    total_fp = 0.0
    current = 0.0

    for _ in range(int(max_dots)):
        index = int(np.argmax(eligible_gain))
        best_gain = float(eligible_gain[index])
        if not math.isfinite(best_gain) or best_gain <= 0.0:
            break
        flat = int(eligible[index])
        row, col = divmod(flat, flat_width)
        cost = float(fp_weight[row, col])
        candidate = (total_tp + best_gain) / (
            alpha * (total_tp + best_gain + total_fp + cost)
            + (1.0 - alpha) * float(truth_mass) + epsilon
        )
        if candidate <= current:
            break

        order.append(flat)
        chosen[index] = True
        total_tp += best_gain
        total_fp += cost
        current = candidate
        cumulative_tp.append(total_tp)
        cumulative_fp.append(total_fp)
        eligible_gain[index] = -np.inf

        neighbour_rows = row + offset_rows
        neighbour_cols = col + offset_cols
        in_grid = ((neighbour_rows >= 0) & (neighbour_rows < height)
                   & (neighbour_cols >= 0) & (neighbour_cols < width))
        neighbour_rows = neighbour_rows[in_grid]
        neighbour_cols = neighbour_cols[in_grid]
        # Out-of-raster neighbours do not exist in the published metric (the kernel
        # is applied by in-bounds slicing), so they must never receive credit.
        credit[neighbour_rows, neighbour_cols] = np.maximum(
            credit[neighbour_rows, neighbour_cols], offset_weights[in_grid])

        # Only candidates whose own kernel support meets the updated credit can change.
        box_r = row + box_dy
        box_c = col + box_dx
        inside = (box_r >= 0) & (box_r < height) & (box_c >= 0) & (box_c < width)
        if not inside.any():
            continue
        box_r = box_r[inside]
        box_c = box_c[inside]
        neighbour_r = box_r[:, None] + offset_rows[None, :]
        neighbour_c = box_c[:, None] + offset_cols[None, :]
        neighbour_valid = ((neighbour_r >= 0) & (neighbour_r < height)
                           & (neighbour_c >= 0) & (neighbour_c < width))
        neighbour_r = np.clip(neighbour_r, 0, height - 1)
        neighbour_c = np.clip(neighbour_c, 0, width - 1)
        neighbour_pi = np.where(neighbour_valid, pi[neighbour_r, neighbour_c], 0.0)
        neighbour_credit = np.where(neighbour_valid, credit[neighbour_r, neighbour_c], 1.0)
        updated = (neighbour_pi * np.maximum(offset_weights[None, :] - neighbour_credit, 0.0)).sum(axis=1)
        flat_positions = box_r * flat_width + box_c
        positions = np.searchsorted(eligible, flat_positions)
        in_range = positions < eligible.size
        positions = positions[in_range]
        flat_positions = flat_positions[in_range]
        matched = eligible[positions] == flat_positions
        updated = updated[in_range][matched]
        positions = positions[matched]
        if positions.size:
            eligible_gain[positions] = updated.astype(np.float32)
            # Accepted pixels are never candidates again, even if a later dot would
            # have raised their neighbourhood gain.
            eligible_gain[positions[chosen[positions]]] = -np.inf

    mask = np.zeros(values.shape, dtype=bool)
    if order:
        rows, cols = np.divmod(np.array(order, dtype=np.int64), flat_width)
        mask[rows, cols] = True
    diagnostics = {
        "accepted": len(order),
        "truth_mass": float(truth_mass),
        "expected_tp": float(cumulative_tp[-1]),
        "expected_fp": float(cumulative_fp[-1]),
        "expected_dti": float(current),
        "order_flat": np.array(order, dtype=np.int64),
        "cumulative_tp": np.array(cumulative_tp, dtype=np.float64),
        "cumulative_fp": np.array(cumulative_fp, dtype=np.float64),
        "marginal_threshold_at_stop": marginal_threshold(current, alpha) if current > 0 else 0.0,
    }
    return (mask, diagnostics) if return_diagnostics else mask


def stop_index(cumulative_tp: Any, cumulative_fp: Any, truth_mass: float, *,
               alpha: float = DEFAULT_ALPHA,
               epsilon: float = DEFAULT_EPSILON) -> int:
    """Return how many accepted dots to keep for a different ``truth_mass``.

    The greedy acceptance order does not depend on ``truth_mass``; only the
    stopping point does.  ``cumulative_*`` are the arrays returned by
    :func:`edge_select`, so one greedy sweep supports a whole family of truth-mass
    assumptions without re-running the sweep.
    """

    import numpy as np

    tp = np.asarray(cumulative_tp, dtype=np.float64)
    fp = np.asarray(cumulative_fp, dtype=np.float64)
    if tp.shape != fp.shape or tp.ndim != 1:
        raise ValueError("cumulative arrays must be one-dimensional and equal length")
    if not math.isfinite(float(truth_mass)) or truth_mass <= 0:
        raise ValueError("truth_mass must be finite and positive")
    best_index = 0
    best_score = 0.0
    for index in range(1, tp.size):
        # A prefix whose accumulated credit exceeds the modelled truth mass is
        # inconsistent with that mass (credit is bounded by the truth it describes),
        # so it cannot be a valid stop for this assumption and is skipped.
        if tp[index] > truth_mass:
            continue
        score = expected_dti(tp[index], fp[index], truth_mass, alpha=alpha, epsilon=epsilon)
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def mask_from_order(order_flat: Any, keep: int, shape: tuple[int, int]) -> Any:
    """Rebuild a boolean emission mask from an acceptance order prefix."""

    import numpy as np

    order = np.asarray(order_flat, dtype=np.int64)
    keep = int(keep)
    if keep < 0 or keep > order.size:
        raise ValueError("keep must lie inside [0, len(order)]")
    mask = np.zeros(shape, dtype=bool)
    if keep:
        rows, cols = np.divmod(order[:keep], shape[1])
        mask[rows, cols] = True
    return mask
