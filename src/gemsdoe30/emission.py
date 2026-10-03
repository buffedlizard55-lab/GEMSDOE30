"""Metric-aware emission rules and the official masked evaluation domain.

The GEMS distance-weighted Tversky index (see :mod:`gemsdoe30.metric`) credits each
truth pixel from the *best* nearby prediction, so redundant prediction pixels add
false-positive mass without adding true-positive credit.  Competitive entries in
this competition are therefore not smooth probability maps but sparse binary
emissions ("dots").  This module implements the two consequences of the published
metric algebra and the selection rules that use them.

Metric algebra (exact, from the published equations)
----------------------------------------------------
With ``T = TP_w``, ``F = FP_w`` and ``G`` the number of truth pixels,
``FN_w = G - T`` always holds because the true-positive and false-negative terms
partition the truth pixels.  Therefore

    DTI = T / (0.2*T + 0.2*F + 0.8*G)                                        (1)

Two consequences are used throughout this project:

1. **Binary emission is optimal on a fixed support.**  Rescaling every predicted
   value by ``lambda <= 1`` scales ``T`` and ``F`` by ``lambda`` while ``G`` is
   fixed, and ``DTI(lambda)`` from (1) is increasing in ``lambda``.  A graded
   probability map cannot beat the same support emitted as 1.0.
2. **Marginal inclusion rule.**  Adding prediction mass ``dT`` at false-positive
   cost ``dF`` raises the score iff ``dT/dF > 0.2*DTI/(1 - 0.2*DTI)``; at the
   group's reported operating point (DTI ~ 0.25) that threshold is ~0.052.

Masked evaluation domain (official clarification)
-------------------------------------------------
DrivenData staff answered on 2026-09-16 (community thread 11516) that pixels of
*known* USGS/INGENIOUS faults are masked / excluded from evaluation, in both the
Initial and Final rounds.  The hide-and-recover proxy below therefore scores only
pixels that are neither masked-known nor hidden truth, and treats hidden catalogue
components as stand-in truth.  This is stricter (and more honest) than scoring the
whole footprint, which silently rewards predicting the training catalogue.
"""

from __future__ import annotations

import math
from typing import Any

DEFAULT_ALPHA = 0.2
DEFAULT_BETA = 0.8
DEFAULT_RADIUS_M = 300.0
DEFAULT_EPSILON = 1e-7


def marginal_inclusion_ratio(dti: float, alpha: float = DEFAULT_ALPHA) -> float:
    """Return the credit/false-positive slope above which adding mass helps.

    Derived from ``DTI = T / (alpha*T + alpha*F + (1-alpha)*G)``:
    ``dT/dF`` must exceed ``alpha*DTI / (1 - alpha*DTI)``.
    """

    if not 0.0 <= dti < 1.0 / alpha:
        raise ValueError("dti must be in [0, 1/alpha)")
    return alpha * dti / (1.0 - alpha * dti)


def dti_from_components(tp: float, fp: float, truth_count: float, *,
                        alpha: float = DEFAULT_ALPHA, epsilon: float = DEFAULT_EPSILON) -> float:
    """Evaluate equation (1) from the three sufficient statistics."""

    if min(tp, fp, truth_count) < 0:
        raise ValueError("components must be non-negative")
    fn = truth_count - tp
    if fn < -1e-6:
        raise ValueError("tp cannot exceed the truth count")
    return float(tp / (alpha * tp + alpha * fp + (1.0 - alpha) * truth_count + epsilon))


def _offsets(radius_m: float, pixel_m: float) -> list[tuple[int, int]]:
    radius_px = int(math.ceil(radius_m / pixel_m))
    return [(dy, dx)
            for dy in range(-radius_px, radius_px + 1)
            for dx in range(-radius_px, radius_px + 1)
            if pixel_m * math.hypot(dy, dx) <= radius_m]


def kernel_credit(prediction: Any, *, pixel_size_m: float = 100.0,
                  radius_m: float = DEFAULT_RADIUS_M) -> Any:
    """Return per-pixel ``max_x p(x) k(d)`` credit (the numerator's integrand).

    The maximum is taken over neighbouring prediction pixels exactly as the
    published metric defines it; shifts are done by slicing so no wrap-around
    credit is created at raster borders.
    """

    import numpy as np

    p = np.asarray(prediction, dtype=np.float32)
    height, width = p.shape
    credit = np.zeros(p.shape, dtype=np.float32)
    for dy, dx in _offsets(radius_m, pixel_size_m):
        kernel = max(1.0 - pixel_size_m * math.hypot(dy, dx) / radius_m, 0.0)
        src_y0, src_y1 = max(0, -dy), min(height, height - dy)
        src_x0, src_x1 = max(0, -dx), min(width, width - dx)
        if src_y0 >= src_y1 or src_x0 >= src_x1:
            continue
        dst = credit[src_y0 + dy:src_y1 + dy, src_x0 + dx:src_x1 + dx]
        candidate = p[src_y0:src_y1, src_x0:src_x1] * kernel
        np.maximum(dst, candidate, out=dst)
    return credit


def dti_components_masked(prediction: Any, truth: Any, scored_mask: Any, *,
                          pixel_size_m: float = 100.0, radius_m: float = DEFAULT_RADIUS_M,
                          alpha: float = DEFAULT_ALPHA,
                          epsilon: float = DEFAULT_EPSILON) -> dict[str, float]:
    """Exact metric components on a masked domain.

    ``scored_mask`` selects the pixels that participate in the metric (official
    domain = valid footprint minus masked known-fault pixels).  ``truth`` must be
    binary and is expected to already be restricted to hidden (non-masked) truth.
    """

    import numpy as np
    from scipy.ndimage import distance_transform_edt

    p = np.asarray(prediction, dtype=np.float32)
    g = np.asarray(truth)
    mask = np.asarray(scored_mask, dtype=bool)
    if p.shape != g.shape or p.shape != mask.shape:
        raise ValueError("prediction, truth and scored_mask must share one shape")
    if np.any(~np.isfinite(p[mask])) or np.any((p[mask] < 0.0) | (p[mask] > 1.0)):
        raise ValueError("prediction must be finite and inside [0, 1] on the scored mask")

    # Prediction pixels outside the scored domain must not radiate credit into it
    # (the reference implementation zeroes them before applying the kernel), and
    # truth pixels outside the domain can never be matched.
    scored_prediction = np.where(mask, p, 0.0)
    credit = kernel_credit(scored_prediction, pixel_size_m=pixel_size_m, radius_m=radius_m)
    positive = mask & (np.asarray(g) == 1)
    tp = float(credit[positive].sum(dtype=np.float64))
    truth_count = float(positive.sum())

    if positive.any():
        distance = distance_transform_edt(~positive, sampling=(pixel_size_m, pixel_size_m))
        fp_weight = np.minimum(distance / radius_m, 1.0)
    else:
        fp_weight = np.ones(p.shape, dtype=np.float64)
    fp = float((scored_prediction * fp_weight).sum(dtype=np.float64))
    return {
        "tp_weight": tp,
        "fp_weight": fp,
        "fn_weight": truth_count - tp,
        "truth_pixels": truth_count,
        "scored_pixels": float(mask.sum()),
        "dti": dti_from_components(tp, fp, truth_count, alpha=alpha, epsilon=epsilon),
    }


def candidate_pool(score: Any, mask: Any, limit: int) -> tuple[Any, Any]:
    """Return the highest-scoring candidate pixels inside ``mask`` (at most ``limit``)."""

    import numpy as np

    values = np.where(mask, np.asarray(score, dtype=np.float32), -np.inf)
    rows, cols = np.nonzero(np.isfinite(values))
    if rows.size == 0:
        return rows, cols
    if rows.size > limit:
        flat = np.argpartition(-values[rows, cols], limit)[:limit]
        rows, cols = rows[flat], cols[flat]
    return rows, cols


def _select(score: Any, radii: Any, rows: Any, cols: Any) -> Any:
    """Shared greedy kernel: keep a candidate when its cell is not yet blocked."""

    import numpy as np

    import math

    kept = np.zeros(score.shape, dtype=bool)
    blocked = np.zeros(score.shape, dtype=bool)
    height, width = score.shape
    offset_cache: dict[int, tuple[float, list[tuple[int, int]]]] = {}

    def _disk(radius: float) -> tuple[float, list[tuple[int, int]]]:
        # Quantise so the cache stays small even when every candidate has its own radius.
        key = int(round(float(radius) * 20.0))
        entry = offset_cache.get(key)
        if entry is None:
            limit = key / 20.0
            reach = max(int(math.ceil(limit)), 1)
            entry = (limit,
                     [(dy, dx) for dy in range(-reach, reach + 1)
                      for dx in range(-reach, reach + 1)
                      if dy * dy + dx * dx < limit * limit])
            offset_cache[key] = entry
        return entry

    for row, col, radius in zip(rows.tolist(), cols.tolist(), radii.tolist()):
        if blocked[row, col]:
            continue
        kept[row, col] = True
        _, offsets = _disk(radius)
        for dy, dx in offsets:
            y, x = row + dy, col + dx
            if 0 <= y < height and 0 <= x < width:
                blocked[y, x] = True
    return kept


def poisson_disk_select(score: Any, radius_px: float, *, threshold: float | None = None,
                        mask: Any = None, limit: int | None = None) -> Any:
    """Greedy Poisson-disk thinning in descending score order.

    Reproduces the family used by the group's scored artifacts: visit candidates
    from highest score to lowest and keep a pixel when no already-kept pixel lies
    within ``radius_px`` (Euclidean).  Ties break deterministically by raster order.
    """

    import numpy as np

    values = np.asarray(score, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("score must be two-dimensional")
    if radius_px <= 0:
        raise ValueError("radius_px must be positive")
    floor = float(values.min()) if threshold is None else float(threshold)
    if mask is None:
        rows, cols = np.nonzero(np.isfinite(values) & (values > floor))
    else:
        rows, cols = candidate_pool(values, np.asarray(mask, dtype=bool) & np.isfinite(values),
                                    int(limit or values.size))
    if rows.size == 0:
        return np.zeros(values.shape, dtype=bool)
    order = np.lexsort((-values[rows, cols], rows, cols))
    radii = np.full(rows.size, float(radius_px), dtype=np.float32)
    return _select(values, radii, rows[order], cols[order])


def adaptive_disk_select(score: Any, radius_px: float, *, gamma: float = 1.0,
                         mask: Any = None, limit: int | None = None,
                         floor_ratio: float = 0.25) -> Any:
    """Confidence-adaptive Poisson-disk thinning.

    The exclusion radius shrinks where the surface is confident:
    ``r(i) = radius_px * (1 - gamma * s_hat(i))`` with ``s_hat`` the surface value
    normalised to the observed [min, max] range.  ``gamma = 0`` reproduces
    :func:`poisson_disk_select`, so the rules can be compared at equal emitted
    counts by calibrating ``radius_px``.
    """

    import numpy as np

    values = np.asarray(score, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("score must be two-dimensional")
    if radius_px <= 0 or not 0.0 <= gamma <= 1.0:
        raise ValueError("radius_px must be positive and gamma in [0, 1]")
    if not 0.0 < floor_ratio <= 1.0:
        raise ValueError("floor_ratio must be in (0, 1]")
    finite = np.isfinite(values)
    if mask is None:
        rows, cols = np.nonzero(finite)
    else:
        rows, cols = candidate_pool(values, np.asarray(mask, dtype=bool) & finite,
                                    int(limit or values.size))
    if rows.size == 0:
        return np.zeros(values.shape, dtype=bool)
    order = np.lexsort((-values[rows, cols], rows, cols))
    rows, cols = rows[order], cols[order]
    lo = float(values[finite].min())
    hi = float(values[finite].max())
    span = max(hi - lo, 1e-12)
    confidence = np.clip((values[rows, cols] - lo) / span, 0.0, 1.0)
    radii = float(radius_px) * np.maximum(1.0 - gamma * confidence, floor_ratio)
    return _select(values, radii.astype(np.float32), rows, cols)


def credit_retention(prediction_pixels: Any, reference_pixels: Any, *,
                     pixel_size_m: float = 100.0, radius_m: float = DEFAULT_RADIUS_M) -> float:
    """Mean kernel credit of a reference binary emission under a candidate emission."""

    import numpy as np
    from scipy.ndimage import distance_transform_edt

    reference = np.asarray(reference_pixels, dtype=bool)
    candidate = np.asarray(prediction_pixels, dtype=bool)
    if reference.shape != candidate.shape:
        raise ValueError("shapes differ")
    if reference.sum() == 0:
        return float("nan")
    distance = distance_transform_edt(~candidate, sampling=(pixel_size_m, pixel_size_m))
    credit = np.maximum(1.0 - distance / radius_m, 0.0)
    return float(credit[reference].mean())


def required_coverage_multiplier(current_dti: float, target_dti: float,
                                 alpha: float = DEFAULT_ALPHA) -> float:
    """Coverage gain needed to reach ``target_dti`` at an unchanged FP ratio.

    From (1), with coverage ``x = T/G`` and false-positive ratio ``rho = F/G``,
    ``DTI = x / (alpha*x + alpha*rho + (1-alpha))`` is linear in ``x`` for fixed
    ``rho``, so the required relative coverage gain is
    ``(target/(1-alpha*target)) / (current/(1-alpha*current)) - 1``.
    """

    for value in (current_dti, target_dti):
        if not 0.0 <= value < 1.0 / alpha:
            raise ValueError("DTI values must be in [0, 1/alpha)")
    adjusted = lambda v: v / (1.0 - alpha * v)  # noqa: E731 - short local helper
    return adjusted(target_dti) / adjusted(current_dti) - 1.0


def required_fp_reduction(current_dti: float, target_dti: float, coverage: float,
                          alpha: float = DEFAULT_ALPHA) -> float:
    """Relative FP-mass reduction needed at fixed coverage ``x = T/G``."""

    def rho(dti: float) -> float:
        return (coverage / dti - alpha * coverage - (1.0 - alpha)) / alpha

    before, after = rho(current_dti), rho(target_dti)
    if before <= 0:
        raise ValueError("implied FP ratio is not positive; check coverage/DTI")
    return 1.0 - after / before


def _kernel_offsets(radius_m: float, pixel_size_m: float) -> list[tuple[int, int, float]]:
    """Exact triangular-kernel offsets: ``(dy, dx, k)`` with ``k = 1 - d/R``."""

    reach = int(math.ceil(radius_m / pixel_size_m))
    offsets: list[tuple[int, int, float]] = []
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            distance = pixel_size_m * math.hypot(dy, dx)
            if distance <= radius_m:
                offsets.append((dy, dx, 1.0 - distance / radius_m))
    return offsets


def metric_optimal_emission(
    score: Any,
    mask: Any = None,
    *,
    alpha: float = DEFAULT_ALPHA,
    radius_m: float = DEFAULT_RADIUS_M,
    pixel_size_m: float = 100.0,
    belief_cut: float = 0.0,
    pool_limit: int | None = None,
    max_dots: int | None = None,
    return_diagnostics: bool = False,
) -> Any:
    """Greedy dot selection driven by the published index's marginal algebra.

    Candidates are visited in descending belief order (ties broken by raster
    order, so the result is deterministic).  A candidate ``x`` is kept only when
    its *expected marginal* effect on the index is positive.  With
    ``A = sum_g belief(g) * credit(g)``, ``F = sum kept cost(x)`` and
    ``T = sum belief`` in the scored domain, the published index is

        DTI = A / (alpha*(A + F) + (1 - alpha)*T),

    so adding mass ``dA`` at expected false-positive cost ``dF = cost(x)`` and
    unchanged ``T`` improves it exactly when

        dA > lambda * dF,      lambda = alpha*s / (1 - alpha*s),  s = DTI_now.

    ``gain(x)`` uses the metric's maximum rule: it is the *extra* weighted credit
    the pixel supplies for the modelled truth field beyond the credit already
    supplied by accepted neighbours.  Duplicating credit therefore yields zero
    gain, which is why the metric prefers spaced dots over dense lines, while the
    spacing adapts to the local belief instead of being a fixed radius.

    ``score`` is a belief/confidence surface in ``[0, 1]`` (a calibrated
    probability, a rank score or a binary base mask all work).  ``mask`` limits
    candidates to the scored domain (official domain = valid footprint minus
    masked known-fault pixels).  ``max_dots`` stops the sweep early; ``pool_limit``
    caps the candidate pool for speed (highest-belief pixels win).
    """

    import numpy as np

    belief = np.asarray(score, dtype=np.float32)
    if belief.ndim != 2:
        raise ValueError("score must be two-dimensional")
    if not 0.0 <= belief_cut < 1.0:
        raise ValueError("belief_cut must be in [0, 1)")
    if pool_limit is not None and pool_limit <= 0:
        raise ValueError("pool_limit must be positive")
    if max_dots is not None and max_dots <= 0:
        raise ValueError("max_dots must be positive")

    domain = np.isfinite(belief)
    if mask is not None:
        mask_array = np.asarray(mask, dtype=bool)
        if mask_array.shape != belief.shape:
            raise ValueError("mask shape differs from score")
        domain &= mask_array
    values = np.where(domain, belief, 0.0).astype(np.float32, copy=True)
    if values.size and values.max() <= belief_cut:
        empty = np.zeros(belief.shape, dtype=bool)
        return {"selected": empty, "credit": np.zeros(belief.shape, dtype=np.float32),
                "dots": 0, "surrogate_dti": 0.0} if return_diagnostics else empty

    rows, cols = np.nonzero(domain & (values > belief_cut))
    if pool_limit is not None and rows.size > pool_limit:
        flat = np.argpartition(-values[rows, cols], pool_limit)[:pool_limit]
        rows, cols = rows[flat], cols[flat]
    if rows.size == 0:
        empty = np.zeros(belief.shape, dtype=bool)
        return {"selected": empty, "credit": np.zeros(belief.shape, dtype=np.float32),
                "dots": 0, "surrogate_dti": 0.0} if return_diagnostics else empty
    order = np.lexsort((cols, rows, -values[rows, cols]))
    rows, cols = rows[order], cols[order]

    offsets = _kernel_offsets(radius_m, pixel_size_m)
    height, width = values.shape
    credit = np.zeros(values.shape, dtype=np.float32)
    selected = np.zeros(values.shape, dtype=bool)

    truth_mass = float(values.sum(dtype=np.float64))
    achieved = 0.0
    fp_mass = 0.0
    dots = 0
    scale = alpha * radius_m  # weights kernel credit of a unit-belief neighbour

    # The emitted value is 1.0 (binary emission is optimal on a fixed support), so a
    # kept pixel offers ``kernel`` credit to each truth pixel in its window.  The
    # expected false-positive weight of that pixel is the probability that no truth
    # pixel lies within the kernel: prod(1 - belief(g)*kernel) over the window.
    for row, col, belief_value in zip(rows.tolist(), cols.tolist(), values[rows, cols].tolist()):
        gain = 0.0
        cost = 1.0
        window = []
        for dy, dx, kernel in offsets:
            y, x = row + dy, col + dx
            if 0 <= y < height and 0 <= x < width:
                neighbour = float(values[y, x])
                if neighbour > 0.0:
                    offered = kernel
                    already = float(credit[y, x])
                    if offered > already:
                        gain += neighbour * (offered - already)
                    cost *= 1.0 - neighbour * kernel
                    window.append((y, x, offered))
        if cost < 0.0:
            cost = 0.0
        elif cost > 1.0:
            cost = 1.0
        denominator = alpha * (achieved + fp_mass) + (1.0 - alpha) * truth_mass
        current = achieved / denominator if denominator > 0.0 else 0.0
        threshold = alpha * current / (1.0 - alpha * current) if current < 1.0 / alpha else float("inf")
        if gain <= threshold * cost or gain <= 0.0:
            continue
        selected[row, col] = True
        achieved += gain
        fp_mass += cost
        for y, x, offered in window:
            if offered > credit[y, x]:
                credit[y, x] = offered
        dots += 1
        if max_dots is not None and dots >= max_dots:
            break

    if not return_diagnostics:
        return selected
    denominator = alpha * (achieved + fp_mass) + (1.0 - alpha) * truth_mass
    return {
        "selected": selected,
        "credit": credit,
        "dots": dots,
        "achieved_credit": achieved,
        "fp_mass": fp_mass,
        "truth_mass": truth_mass,
        "surrogate_dti": achieved / denominator if denominator > 0.0 else 0.0,
    }
