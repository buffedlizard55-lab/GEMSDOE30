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

EVALUATOR_VERSION = "component-holdout-v3-blockstats-20261025"

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


def max_kernel_credit(p: Any, *, pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M) -> Any:
    """Per-pixel ``max_x p(x) k(d)`` credit with the published triangular kernel.

    Single shared implementation used by every holdout statistic, so pooled values and
    per-tile sufficient statistics can never disagree.
    """
    import numpy as np

    p = np.asarray(p, dtype=np.float64)
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
    return credit


def masked_tile_sums(prediction: Any, truth: Any, known: Any, valid: Any, *,
                     tile_px: int = 32, pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M,
                     fp_weight: Any = None) -> dict[str, Any]:
    """Per-tile sufficient statistics (TP credit, FP mass, truth count) for block bootstraps.

    Pooling these tile sums reproduces the pooled full-grid statistics exactly, so a
    bootstrap over whole spatial tiles can give pooled DTI confidence intervals without
    recomputing the kernel for each resample.
    """
    import numpy as np

    prediction = np.asarray(prediction)
    truth = np.asarray(truth, dtype=bool)
    known = np.asarray(known, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    scored = valid & ~known
    positive = truth & scored
    p = np.where(scored, prediction.astype(np.float64), 0.0)
    credit = max_kernel_credit(p, pixel_m=pixel_m, radius_m=radius_m)
    if fp_weight is None:
        fp_weight = fp_weight_field(positive, ~scored, pixel_m=pixel_m, radius_m=radius_m)
    fp_field = p * np.where(scored, np.asarray(fp_weight), 0.0)
    height, width = p.shape
    tile_rows = (height + tile_px - 1) // tile_px
    tile_cols = (width + tile_px - 1) // tile_px
    tile_id = (np.arange(height)[:, None] // tile_px) * tile_cols + (np.arange(width)[None, :] // tile_px)
    n_tiles = tile_rows * tile_cols
    tp = np.bincount(tile_id[positive], weights=credit[positive], minlength=n_tiles)
    fp = np.bincount(tile_id.ravel(), weights=fp_field.ravel(), minlength=n_tiles)
    truth_n = np.bincount(tile_id[positive], minlength=n_tiles).astype(np.float64)
    occupied = np.bincount(tile_id.ravel(), weights=valid.ravel().astype(np.float64), minlength=n_tiles) > 0
    return {"tp": tp, "fp": fp, "truth": truth_n, "occupied": occupied,
            "tile_px": tile_px, "tile_rows": tile_rows, "tile_cols": tile_cols}


def masked_dti_by_blocks(prediction: Any, truth: Any, known: Any, valid: Any, *,
                         pixel_m: float = PIXEL_M, radius_m: float = RADIUS_M,
                         alpha: float = ALPHA,
                         fp_weight: Any = None,
                         block_size_px: int | None = None) -> dict[str, Any]:
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
    if prediction.ndim != 2 or not (prediction.shape == truth.shape == known.shape == valid.shape):
        raise ValueError("prediction, truth, known and valid must be same-shaped 2D arrays")
    if not math.isfinite(pixel_m) or not math.isfinite(radius_m) or pixel_m <= 0 or radius_m <= 0:
        raise ValueError("pixel size and kernel radius must be finite and positive")
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("alpha must be in [0, 1]")
    scored = valid & ~known
    if not np.isfinite(prediction[scored]).all() or np.any((prediction[scored] < 0) | (prediction[scored] > 1)):
        raise ValueError("scored predictions must be finite in [0, 1]")
    if fp_weight is not None and np.any(truth & ~valid):
        raise ValueError("cached FP weights cannot be trusted with out-of-footprint truth")
    positive = truth & scored
    p = np.where(scored, prediction.astype(np.float64), 0.0)
    credit = max_kernel_credit(p, pixel_m=pixel_m, radius_m=radius_m)
    height, width = p.shape
    if fp_weight is None:
        fp_weight = fp_weight_field(positive, ~scored, pixel_m=pixel_m, radius_m=radius_m)
    fp_weight = np.asarray(fp_weight)
    if fp_weight.shape != p.shape or not np.isfinite(fp_weight[scored]).all() or np.any((fp_weight[scored] < 0) | (fp_weight[scored] > 1)):
        raise ValueError("FP weights must match the grid and be finite in [0, 1]")
    fp_field = p * np.where(scored, fp_weight, 0.0)
    result: dict[str, Any] = {
        "evaluator_version": EVALUATOR_VERSION,
        "pooled": {
            "dti": dti_from_components(float(credit[positive].sum()), float(fp_field.sum()),
                                       float(positive.sum()), alpha=alpha),
            "tp_weight": float(credit[positive].sum()),
            "fp_weight": float(fp_field.sum()),
            "truth_pixels": float(positive.sum()),
            "emitted_pixels": int(np.count_nonzero(p)),
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
        tp = float(credit[truth_block].sum())
        fp = float(fp_field[block_scored].sum())
        n = float(truth_block.sum())
        result[f"quadrant_{qi}"] = {"dti": dti_from_components(tp, fp, n, alpha=alpha),
                                    "tp_weight": tp, "fp_weight": fp, "truth_pixels": n}
    if block_size_px is not None:
        if not isinstance(block_size_px, int) or block_size_px < 1:
            raise ValueError("block_size_px must be a positive integer")
        blocks = []
        for r0 in range(0, height, block_size_px):
            for c0 in range(0, width, block_size_px):
                section = np.s_[r0:r0 + block_size_px, c0:c0 + block_size_px]
                active = scored[section]
                if not active.any():
                    continue
                positives = positive[section]
                blocks.append({"block_row": r0 // block_size_px,
                               "block_col": c0 // block_size_px,
                               "tp_weight": float(credit[section][positives].sum()),
                               "fp_weight": float(fp_field[section].sum()),
                               "truth_pixels": int(positives.sum()),
                               "scored_pixels": int(active.sum())})
        result["spatial_blocks"] = blocks
        result["block_size_px"] = block_size_px
    return result


SEGMENT_PROTOCOL_VERSION = "buffered-quadrant-whole-components-v1-20261025"


def spatial_segment_folds(catalogue: Any, valid: Any, *, buffer_px: int = 16,
                          kernel_radius_px: int = 3):
    """Yield four spatially blocked trials without cutting catalogue components.

    Each complete 8-connected segment is assigned once, by its centroid quadrant.
    A fold scores that quadrant plus a metric halo around its complete withheld
    segments. Whole other segments that touch the training guard are withheld
    from *both* features/training and truth; only their exact pixels are excluded
    from scoring. This is a defined regional-trial protocol, not a disjoint OOF
    mosaic: a few negative/halo pixels can appear in more than one fold.
    """
    import numpy as np
    from scipy.ndimage import distance_transform_edt, label

    cat, valid = np.asarray(catalogue, dtype=bool), np.asarray(valid, dtype=bool)
    if cat.ndim != 2 or cat.shape != valid.shape or np.any(cat & ~valid):
        raise ValueError("catalogue must be a 2D subset of the same-shaped footprint")
    if not isinstance(buffer_px, int) or buffer_px < kernel_radius_px or kernel_radius_px < 1:
        raise ValueError("integer guard must cover the positive metric radius")
    components, count = label(cat, structure=np.ones((3, 3), dtype=int))
    if not count:
        raise ValueError("empty catalogue")
    rr, cc = np.nonzero(cat)
    ids = components[rr, cc]
    sizes = np.bincount(ids, minlength=count + 1)
    cy = np.bincount(ids, weights=rr, minlength=count + 1) / np.maximum(sizes, 1)
    cx = np.bincount(ids, weights=cc, minlength=count + 1) / np.maximum(sizes, 1)
    height, width = cat.shape
    assignment = (cy >= height // 2).astype(int) * 2 + (cx >= width // 2).astype(int)
    assignment[0] = -1
    for fold in range(4):
        core = np.zeros(cat.shape, dtype=bool)
        y0, y1 = (0, height // 2) if fold < 2 else (height // 2, height)
        x0, x1 = (0, width // 2) if fold % 2 == 0 else (width // 2, width)
        core[y0:y1, x0:x1] = True
        hidden_ids = np.flatnonzero(assignment == fold)
        hidden = assignment[components] == fold
        if not hidden.any():
            raise ValueError(f"fold {fold} has no complete withheld segments")
        region = valid & (core | (distance_transform_edt(~hidden) <= kernel_radius_px))
        near = distance_transform_edt(~region) <= buffer_px
        guard_ids = np.unique(components[near & cat & ~hidden])
        guard_lookup = np.zeros(count + 1, dtype=bool)
        guard_lookup[guard_ids] = True
        guard_lookup[0] = False
        guard = guard_lookup[components]
        visible = cat & ~hidden & ~guard
        train = valid & ~near & ~guard
        scored = region & ~guard
        if np.any(hidden & ~scored) or np.any(visible & near) or np.any(train & hidden):
            raise AssertionError("whole-segment/guard invariant failed")
        yield {
            "fold": fold, "hidden": hidden, "visible": visible, "guard": guard,
            "train_mask": train, "score_valid": scored,
            "metadata": {"protocol_version": SEGMENT_PROTOCOL_VERSION,
                         "fold": fold, "buffer_px": buffer_px,
                         "metric_halo_px": kernel_radius_px,
                         "withheld_components": int(hidden_ids.size),
                         "withheld_positives": int(hidden.sum()),
                         "visible_positives": int(visible.sum()),
                         "guard_positives_not_truth": int(guard.sum()),
                         "training_pixels": int(train.sum()),
                         "scored_pixels": int(scored.sum()),
                         "hidden_component_ids": hidden_ids.tolist()},
        }


def spatial_bootstrap(comparisons: dict[str, list[dict]], *, candidate: str,
                      replicates: int = 2000, seed: int = 3071) -> dict[str, Any]:
    """Paired geographic-block bootstrap of pooled sufficient statistics.

    Rows must come from ``masked_dti_by_blocks(..., block_size_px=...)``. The same
    geographic block is aggregated across trials before resampling, so overlapping
    fold regions do not masquerade as independent bootstrap units. All arms must
    include exactly the same geographic blocks, including truth-empty FP blocks.
    """
    import numpy as np
    from .emission import dti_from_components

    if candidate not in comparisons or replicates < 2 or not comparisons:
        raise ValueError("candidate and at least two bootstrap replicates required")
    aggregated = {}
    for name, rows in comparisons.items():
        blocks = {}
        for row in rows:
            key = (int(row["block_row"]), int(row["block_col"]))
            triple = np.array([row["tp_weight"], row["fp_weight"], row["truth_pixels"]], dtype=float)
            if not np.isfinite(triple).all() or np.any(triple < 0) or triple[0] > triple[2] + 1e-6:
                raise ValueError("invalid bootstrap sufficient statistics")
            blocks[key] = blocks.get(key, np.zeros(3)) + triple
        aggregated[name] = blocks
    keys = sorted(aggregated[candidate])
    if not keys or any(set(rows) != set(keys) for rows in aggregated.values()):
        raise ValueError("arms must have identical nonempty geographic block inventories")
    arrays = {name: np.array([rows[key] for key in keys]) for name, rows in aggregated.items()}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(keys), size=(replicates, len(keys)))
    samples, results = {}, {}
    for name, a in arrays.items():
        total = a.sum(axis=0)
        sample = a[draws].sum(axis=1)
        denominator = 0.2 * sample[:, 0] + 0.2 * sample[:, 1] + 0.8 * sample[:, 2] + 1e-7
        samples[name] = sample[:, 0] / denominator
        results[name] = {"label": "HOLDOUT-DTI", "value": dti_from_components(*total),
                         "withheld_positives": int(round(total[2])),
                         "ci95": np.quantile(samples[name], [0.025, 0.975]).tolist(),
                         "tp_weight": float(total[0]), "fp_weight": float(total[1])}
    deltas = {}
    for name in comparisons:
        if name == candidate:
            continue
        delta = samples[candidate] - samples[name]
        deltas[name] = {"label": "HOLDOUT-DTI difference",
                        "value": results[candidate]["value"] - results[name]["value"],
                        "ci95": np.quantile(delta, [0.025, 0.975]).tolist()}
    return {"evaluator_version": EVALUATOR_VERSION, "protocol_version": SEGMENT_PROTOCOL_VERSION,
            "bootstrap": {"unit": "geographic block aggregated across folds", "blocks": len(keys),
                          "replicates": replicates, "seed": seed,
                          "interval": "paired spatial-block percentile 95%; conditional catalogue proxy"},
            "arms": results, "candidate_minus": deltas}
