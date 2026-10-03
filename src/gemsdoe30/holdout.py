"""Shared component-holdout utilities for hypothesis tests on the catalogue.

The official metric scores only faults *outside* the USGS/INGENIOUS catalogue
and masks known-fault pixels out of every term. We cannot see the hidden expert
labels, so hypothesis screens use the catalogue itself: whole 8-connected
catalogue components are hidden from the feature builder and used as stand-in
"new" faults, while the remaining components are masked exactly as the
organizer masks known faults. This is a necessary but biased proxy (it can
reward predictions on catalogue-like faults the competition ignores) and must
never be reported as a competition score.
"""

from __future__ import annotations

import math
from typing import Any

PIXEL_M = 100.0
RADIUS_M = 300.0
ALPHA = 0.2


def split_components(
    catalogue: Any,
    *,
    seed: int = 31,
    stratify: int = 32,
) -> tuple[Any, Any, int]:
    """Deterministic, spatially interleaved split of whole 8-connected components.

    Components are grouped into ``stratify``-pixel (3.2 km) tiles by centroid, and
    within each populated tile half of the components (deterministically shuffled)
    become stand-in "new" faults (``hidden``) and half stay mapped (``known``).
    Interleaving at the fault-zone scale is required: a regional checkerboard split
    separates whole fault zones and measures proximity effects instead of the
    within-zone geometry under test.
    """

    import numpy as np
    from scipy.ndimage import label

    catalogue = np.asarray(catalogue, dtype=bool)
    components, count = label(catalogue, structure=np.ones((3, 3), dtype=int))
    if count == 0:
        raise ValueError("catalogue is empty")
    rows, cols = np.nonzero(catalogue)
    component_ids = components[rows, cols]
    order = np.argsort(component_ids, kind="stable")
    ids_sorted = component_ids[order]
    rows_sorted = rows[order]
    cols_sorted = cols[order]
    boundaries = np.searchsorted(ids_sorted, np.arange(1, count + 1))
    starts = np.concatenate([[0], boundaries[:-1]])
    sizes = np.diff(np.concatenate([starts, [ids_sorted.size]]))
    centroid_row = np.add.reduceat(rows_sorted, starts) / np.maximum(sizes, 1)
    centroid_col = np.add.reduceat(cols_sorted, starts) / np.maximum(sizes, 1)
    tile_row = (centroid_row // stratify).astype(np.int64)
    tile_col = (centroid_col // stratify).astype(np.int64)
    rng = np.random.default_rng(seed)
    hidden_components = np.zeros(count + 1, dtype=bool)
    for key in sorted(set(zip(tile_row.tolist(), tile_col.tolist()))):
        members = np.flatnonzero((tile_row == key[0]) & (tile_col == key[1])) + 1
        shuffled = rng.permutation(members)
        hidden_components[shuffled[: shuffled.size // 2]] = True
    hidden = hidden_components[components]
    known = (components > 0) & ~hidden
    return hidden, known, count


def fp_weight_field(truth: Any, known: Any, *,
                    pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M) -> Any:
    """Distance-derived false-positive weight for the masked domain (reusable per split)."""

    import numpy as np
    from scipy.ndimage import distance_transform_edt

    truth = np.asarray(truth, dtype=bool)
    known = np.asarray(known, dtype=bool)
    positive = truth & ~known
    if not positive.any():
        return np.ones(truth.shape, dtype=np.float64)
    distance = distance_transform_edt(~positive, sampling=(pixel_m, pixel_m))
    return np.minimum(distance / radius_m, 1.0)


def masked_dti(prediction: Any, truth: Any, known: Any, *,
               pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M,
               alpha: float = ALPHA,
               fp_weight: Any = None) -> dict[str, float]:
    """Exact published index on the masked domain (known-fault pixels excluded).

    Pass ``fp_weight`` from :func:`fp_weight_field` to avoid recomputing the truth
    distance transform when scoring many emissions against the same hidden truth.
    """

    import numpy as np

    from .emission import dti_from_components

    prediction = np.asarray(prediction)
    truth = np.asarray(truth, dtype=bool)
    known = np.asarray(known, dtype=bool)
    scored = ~known
    positive = truth & scored
    if not positive.any():
        return {"dti": float("nan"), "note": "no hidden truth inside the masked domain"}
    p = np.where(scored, prediction.astype(np.float64), 0.0)
    credit = np.zeros(p.shape, dtype=np.float64)
    reach = int(math.ceil(radius_m / pixel_m))
    height, width = p.shape
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            distance = pixel_m * math.hypot(dy, dx)
            if distance > radius_m:
                continue
            kernel = 1.0 - distance / radius_m
            y0d, y1d = max(0, -dy), min(height, height - dy)
            x0d, x1d = max(0, -dx), min(width, width - dx)
            if y0d >= y1d or x0d >= x1d:
                continue
            candidate = p[y0d + dy:y1d + dy, x0d + dx:x1d + dx] * kernel
            np.maximum(credit[y0d:y1d, x0d:x1d], candidate, out=credit[y0d:y1d, x0d:x1d])
    tp = float(credit[positive].sum())
    truth_count = float(positive.sum())
    if fp_weight is None:
        fp_weight = fp_weight_field(truth, known, pixel_m=pixel_m, radius_m=radius_m)
    fp = float((p * fp_weight).sum())
    near = credit[positive] > 0.0
    return {
        "dti": dti_from_components(tp, fp, truth_count, alpha=alpha),
        "tp_weight": tp,
        "fp_weight": fp,
        "hidden_truth_pixels": truth_count,
        "hidden_pixels_with_credit": int(near.sum()),
        "hidden_credit_fraction": float(near.mean()),
        "emitted_pixels": int(np.count_nonzero(prediction)),
    }


def distance_matched_draw(
    pool: Any,
    target_pool: Any,
    distance_to_known: Any,
    count: int,
    rng: Any,
    *,
    bins: int = 10,
) -> Any:
    """Draw ``count`` pixels from ``pool`` matching ``target_pool``'s distance profile.

    Both pools are flat index arrays into ``distance_to_known``'s grid. The target
    pool's distances to known faults are binned into quantiles; the draw takes the
    same bin counts from the full pool. This removes generic "near mapped faults"
    proximity as an explanation for any target-pool advantage.
    """

    import numpy as np

    pool = np.asarray(pool, dtype=np.int64)
    target_pool = np.asarray(target_pool, dtype=np.int64)
    flat_distance = np.asarray(distance_to_known).ravel()
    out = np.zeros(flat_distance.size, dtype=bool)
    if pool.size == 0 or count <= 0 or target_pool.size == 0:
        return out
    target_d = flat_distance[target_pool]
    edges = np.unique(np.quantile(target_d, np.linspace(0.0, 1.0, bins + 1)))
    if edges.size < 2:
        picked = rng.choice(pool, size=min(count, pool.size), replace=False)
        out[picked] = True
        return out
    target_counts, _ = np.histogram(target_d, bins=edges)
    pool_d = flat_distance[pool]
    pool_bin = np.clip(np.digitize(pool_d, edges[1:-1], right=False), 0, edges.size - 2)
    taken: list[np.ndarray] = []
    deficit = count
    for b in range(edges.size - 1):
        want = int(round(target_counts[b] * (count / max(target_pool.size, 1))))
        want = min(want, deficit)
        members = pool[pool_bin == b]
        members = members[~out[members]]
        if members.size and want > 0:
            take = min(want, members.size)
            picked = rng.choice(members, size=take, replace=False)
            taken.append(picked)
            out[picked] = True
            deficit -= take
    if deficit > 0:
        remaining = pool[~out[pool]]
        if remaining.size:
            take = min(deficit, remaining.size)
            picked = rng.choice(remaining, size=take, replace=False)
            taken.append(picked)
            out[picked] = True
    return out


def masked_dti_by_blocks(prediction: Any, truth: Any, known: Any, valid: Any, *,
                         pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M,
                         alpha: float = ALPHA,
                         fp_weight: Any = None) -> dict[str, Any]:
    """Full-grid masked DTI plus per-quadrant diagnostics from one kernel pass.

    Quadrant diagnostics keep cross-quadrant 300 m credit (predictions in one
    quadrant may cover truth in another) and are informational only; the pooled
    full-grid value is the decision statistic.
    """

    import numpy as np

    from .emission import dti_from_components

    prediction = np.asarray(prediction)
    truth = np.asarray(truth, dtype=bool)
    known = np.asarray(known, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    scored = ~known
    positive = truth & scored
    p = np.where(scored, prediction.astype(np.float64), 0.0)
    credit = np.zeros(p.shape, dtype=np.float64)
    reach = int(math.ceil(radius_m / pixel_m))
    height, width = p.shape
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            distance = pixel_m * math.hypot(dy, dx)
            if distance > radius_m:
                continue
            kernel = 1.0 - distance / radius_m
            y0d, y1d = max(0, -dy), min(height, height - dy)
            x0d, x1d = max(0, -dx), min(width, width - dx)
            if y0d >= y1d or x0d >= x1d:
                continue
            candidate = p[y0d + dy:y1d + dy, x0d + dx:x1d + dx] * kernel
            np.maximum(credit[y0d:y1d, x0d:x1d], candidate, out=credit[y0d:y1d, x0d:x1d])
    if fp_weight is None:
        fp_weight = fp_weight_field(truth, known, pixel_m=pixel_m, radius_m=radius_m)
    fp_field = p * fp_weight
    result: dict[str, Any] = {
        "pooled": {
            "dti": dti_from_components(float(credit[positive].sum()), float(fp_field.sum()),
                                       float(positive.sum()), alpha=alpha),
            "tp_weight": float(credit[positive].sum()),
            "fp_weight": float(fp_field.sum()),
            "truth_pixels": float(positive.sum()),
            "emitted_pixels": int(np.count_nonzero(prediction)),
        }
    }
    half_r, half_c = height // 2, width // 2
    for qi, (r0, r1, c0, c1) in enumerate(
        ((0, half_r, 0, half_c), (0, half_r, half_c, width),
         (half_r, height, 0, half_c), (half_r, height, half_c, width))
    ):
        block = np.zeros(prediction.shape, dtype=bool)
        block[r0:r1, c0:c1] = True
        block_scored = block & scored & valid
        truth_block = positive & block
        if not truth_block.any():
            result[f"quadrant_{qi}"] = {"dti": float("nan"), "note": "no hidden truth in block"}
            continue
        tp = float(credit[truth_block].sum())
        fp = float(fp_field[block_scored].sum())
        n = float(truth_block.sum())
        result[f"quadrant_{qi}"] = {"dti": dti_from_components(tp, fp, n, alpha=alpha),
                                    "tp_weight": tp, "fp_weight": fp, "truth_pixels": n}
    return result
