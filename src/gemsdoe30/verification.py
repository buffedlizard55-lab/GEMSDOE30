"""Standing three-check verification protocol (docs/research/verification-protocol.md).

Implements Check 2 (probability calibration + fold-local monotone bin calibrator),
Check 3 (held-out feature-perturbation stability), and the qualitative block-atlas
extractor required alongside Check 1 (spatial block-validation).
"""

from __future__ import annotations

from typing import Any, Callable


def fit_bin_calibrator(
    scores: Any,
    truth: Any,
    train_mask: Any,
    *,
    n_bins: int = 20,
) -> dict[str, Any]:
    """Fit a fold-local monotone empirical quantile calibrator on ``train_mask`` only.

    Uses Pool-Adjacent-Violators (isotonic regression on quantile bins) so that
    calibrated probabilities are monotonically non-decreasing in ``scores`` and
    match empirical positive rates on the training fold without touching held-out data.
    """
    import numpy as np

    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(truth, dtype=np.float64)
    m = np.asarray(train_mask, dtype=bool) & np.isfinite(s) & np.isfinite(y)
    if not m.any():
        raise ValueError("train_mask contains no finite pixels")
    s_train = s[m]
    y_train = y[m]
    quantiles = np.linspace(0.0, 1.0, n_bins + 1)
    edges = np.unique(np.quantile(s_train, quantiles))
    if edges.size < 2:
        base_rate = float(np.mean(y_train))
        return {
            "edges": [float(s_train.min()), float(s_train.max() + 1e-9)],
            "values": [base_rate],
            "base_rate": base_rate,
        }
    bin_idx = np.clip(np.digitize(s_train, edges[1:-1], right=False), 0, edges.size - 2)
    counts = np.bincount(bin_idx, minlength=edges.size - 1).astype(np.float64)
    pos = np.bincount(bin_idx, weights=y_train, minlength=edges.size - 1).astype(np.float64)
    rates = np.where(counts > 0, pos / np.maximum(counts, 1.0), float(np.mean(y_train)))

    # Pool-Adjacent-Violators (PAV) for monotone non-decreasing bin rates
    blocks: list[list[float]] = [[float(rates[i]), float(max(counts[i], 1.0)), i, i] for i in range(rates.size)]
    idx = 0
    while idx < len(blocks) - 1:
        if blocks[idx][0] > blocks[idx + 1][0]:
            w1, w2 = blocks[idx][1], blocks[idx + 1][1]
            v = (blocks[idx][0] * w1 + blocks[idx + 1][0] * w2) / (w1 + w2)
            blocks[idx] = [v, w1 + w2, blocks[idx][2], blocks[idx + 1][3]]
            blocks.pop(idx + 1)
            if idx > 0:
                idx -= 1
        else:
            idx += 1
    iso_rates = np.zeros_like(rates)
    for val, _, start_i, end_i in blocks:
        iso_rates[int(start_i) : int(end_i) + 1] = val

    return {
        "edges": [float(v) for v in edges],
        "values": [float(np.clip(v, 0.0, 1.0)) for v in iso_rates],
        "base_rate": float(np.mean(y_train)),
    }


def apply_bin_calibrator(calibrator: dict[str, Any], scores: Any) -> Any:
    """Apply a calibrator returned by :func:`fit_bin_calibrator`."""
    import numpy as np

    s = np.asarray(scores, dtype=np.float64)
    edges = np.asarray(calibrator["edges"], dtype=np.float64)
    values = np.asarray(calibrator["values"], dtype=np.float64)
    out = np.full(s.shape, np.nan, dtype=np.float64)
    finite = np.isfinite(s)
    if not finite.any():
        return out
    idx = np.clip(np.digitize(s[finite], edges[1:-1], right=False), 0, values.size - 1)
    out[finite] = values[idx]
    return np.clip(out, 0.0, 1.0)


def evaluate_probability_calibration(
    predicted: Any,
    truth: Any,
    train_mask: Any,
    val_mask: Any,
    *,
    n_bins: int = 10,
    min_bin_pixels: int = 500,
) -> dict[str, Any]:
    """Evaluate Check 2 (probability calibration) on held-out ``val_mask``.

    Criteria from docs/research/verification-protocol.md:
    1. OLS reliability slope of empirical-vs-predicted bin frequencies in [0.8, 1.2]
       across bins with >= ``min_bin_pixels`` pixels.
    2. Top-decile realized fault rate on ``val_mask`` >= 70% of the top-decile
       realized fault rate on ``train_mask``.
    """
    import numpy as np

    p = np.asarray(predicted, dtype=np.float64)
    y = np.asarray(truth, dtype=np.float64)
    tr = np.asarray(train_mask, dtype=bool) & np.isfinite(p) & np.isfinite(y)
    va = np.asarray(val_mask, dtype=bool) & np.isfinite(p) & np.isfinite(y)
    if not tr.any() or not va.any():
        raise ValueError("train_mask and val_mask must both have finite pixels")

    p_tr, y_tr = p[tr], y[tr]
    p_va, y_va = p[va], y[va]

    # Fold-local quantile edges from training fold
    edges = np.unique(np.quantile(p_tr, np.linspace(0.0, 1.0, n_bins + 1)))
    if edges.size < 2:
        edges = np.linspace(float(p_va.min()), float(p_va.max()) + 1e-9, n_bins + 1)

    va_bin = np.clip(np.digitize(p_va, edges[1:-1], right=False), 0, edges.size - 2)
    tr_bin = np.clip(np.digitize(p_tr, edges[1:-1], right=False), 0, edges.size - 2)

    bins_detail = []
    pred_means = []
    emp_means = []
    for b in range(edges.size - 1):
        m_b = va_bin == b
        cnt = int(m_b.sum())
        if cnt > 0:
            pm = float(np.mean(p_va[m_b]))
            em = float(np.mean(y_va[m_b]))
        else:
            pm, em = float("nan"), float("nan")
        bins_detail.append({
            "bin": b,
            "count": cnt,
            "predicted_mean": pm,
            "empirical_rate": em,
            "used_for_slope": cnt >= min_bin_pixels,
        })
        if cnt >= min_bin_pixels:
            pred_means.append(pm)
            emp_means.append(em)

    if len(pred_means) >= 2 and np.var(pred_means) > 1e-12:
        x = np.asarray(pred_means, dtype=np.float64)
        yv = np.asarray(emp_means, dtype=np.float64)
        xm, ym = float(x.mean()), float(yv.mean())
        slope = float(np.sum((x - xm) * (yv - ym)) / np.sum((x - xm) ** 2))
        intercept = float(ym - slope * xm)
    else:
        slope = 0.0
        intercept = float("nan")

    top_b = edges.size - 2
    tr_top_mask = tr_bin == top_b
    va_top_mask = va_bin == top_b
    train_top_rate = float(np.mean(y_tr[tr_top_mask])) if tr_top_mask.any() else 0.0
    val_top_rate = float(np.mean(y_va[va_top_mask])) if va_top_mask.any() else 0.0
    top_bin_ratio = float(val_top_rate / train_top_rate) if train_top_rate > 0 else 0.0

    slope_pass = 0.8 <= slope <= 1.2
    top_bin_pass = top_bin_ratio >= 0.70
    return {
        "reliability_slope": slope,
        "reliability_intercept": intercept,
        "slope_in_0_8_to_1_2": bool(slope_pass),
        "train_top_decile_rate": train_top_rate,
        "val_top_decile_rate": val_top_rate,
        "top_decile_val_to_train_ratio": top_bin_ratio,
        "top_bin_stability_ge_0_70": bool(top_bin_pass),
        "check2_pass": bool(slope_pass and top_bin_pass),
        "bins": bins_detail,
    }


def evaluate_oof_calibration_across_folds(
    raw_score: Any,
    truth: Any,
    eval_domain: Any,
    *,
    buffer_m: float = 300.0,
    n_bins: int = 10,
    min_bin_pixels: int = 500,
) -> dict[str, Any]:
    """Run fold-local isotonic calibration across all 4 buffered spatial quadrants and score Check 2.

    Unlike passing ``train_mask == val_mask`` on a stitched surface (which would make the
    top-decile val/train ratio trivially 1.0), this function evaluates the top-decile
    realized fault rate on each held-out fold ``val_f`` against the training fold ``train_f``
    that fitted its calibrator, then pools the 4 out-of-fold calibrated quadrants to compute
    the pooled OOF reliability slope.
    """
    import numpy as np

    from .cv import spatial_quadrant_masks

    score = np.asarray(raw_score, dtype=np.float64)
    y = np.asarray(truth, dtype=np.float64)
    domain = np.asarray(eval_domain, dtype=bool) & np.isfinite(score) & np.isfinite(y)

    oof_cal = np.full(score.shape, np.nan, dtype=np.float64)
    oof_decile_bin = np.full(score.shape, -1, dtype=np.int64)
    per_fold: dict[str, Any] = {}
    fold_ratios: list[float] = []

    for fold in range(4):
        tr_mask, va_mask = spatial_quadrant_masks(domain, fold, buffer_m=buffer_m)
        cal_f = fit_bin_calibrator(score, y, tr_mask, n_bins=n_bins)
        pred_f = apply_bin_calibrator(cal_f, score)
        oof_cal[va_mask] = pred_f[va_mask]

        # Assign fold-local score decile index (0..n_bins-1) using training-fold quantiles
        edges_f = np.unique(np.quantile(score[tr_mask], np.linspace(0.0, 1.0, n_bins + 1)))
        if edges_f.size >= 2:
            oof_decile_bin[va_mask] = np.clip(
                np.digitize(score[va_mask], edges_f[1:-1], right=False), 0, edges_f.size - 2
            )

        uncal_eval = evaluate_probability_calibration(
            score, y, tr_mask, va_mask, n_bins=n_bins, min_bin_pixels=min_bin_pixels
        )
        cal_eval = evaluate_probability_calibration(
            pred_f, y, tr_mask, va_mask, n_bins=n_bins, min_bin_pixels=min_bin_pixels
        )
        fold_ratios.append(float(uncal_eval["top_decile_val_to_train_ratio"]))
        per_fold[f"fold_{fold}"] = {
            "uncalibrated_slope": uncal_eval["reliability_slope"],
            "calibrated_slope": cal_eval["reliability_slope"],
            "train_top_decile_rate": uncal_eval["train_top_decile_rate"],
            "val_top_decile_rate": uncal_eval["val_top_decile_rate"],
            "top_decile_val_to_train_ratio": uncal_eval["top_decile_val_to_train_ratio"],
            "fold_check2_pass": cal_eval["check2_pass"],
        }

    # Compute pooled OOF reliability slope across fold-local decile bins 0..n_bins-1
    valid_oof = domain & np.isfinite(oof_cal) & (oof_decile_bin >= 0)
    bins_detail = []
    pred_means = []
    emp_means = []
    for b in range(n_bins):
        m_b = valid_oof & (oof_decile_bin == b)
        cnt = int(m_b.sum())
        if cnt > 0:
            pm = float(np.mean(oof_cal[m_b]))
            em = float(np.mean(y[m_b]))
        else:
            pm, em = float("nan"), float("nan")
        bins_detail.append({
            "bin": b,
            "count": cnt,
            "predicted_mean": pm,
            "empirical_rate": em,
            "used_for_slope": cnt >= min_bin_pixels,
        })
        if cnt >= min_bin_pixels:
            pred_means.append(pm)
            emp_means.append(em)

    if len(pred_means) >= 2 and np.var(pred_means) > 1e-12:
        x = np.asarray(pred_means, dtype=np.float64)
        yv = np.asarray(emp_means, dtype=np.float64)
        xm, ym = float(x.mean()), float(yv.mean())
        oof_slope = float(np.sum((x - xm) * (yv - ym)) / np.sum((x - xm) ** 2))
        oof_intercept = float(ym - oof_slope * xm)
    else:
        oof_slope = 0.0
        oof_intercept = float("nan")

    mean_ratio = float(np.mean(fold_ratios)) if fold_ratios else 0.0
    min_ratio = float(np.min(fold_ratios)) if fold_ratios else 0.0
    folds_ratio_pass = sum(1 for r in fold_ratios if r >= 0.70)
    slope_pass = 0.8 <= oof_slope <= 1.2
    top_bin_pass = mean_ratio >= 0.70 and folds_ratio_pass >= 3
    return {
        "pooled_oof_reliability_slope": oof_slope,
        "pooled_oof_reliability_intercept": oof_intercept,
        "slope_in_0_8_to_1_2": bool(slope_pass),
        "mean_fold_top_decile_val_to_train_ratio": mean_ratio,
        "min_fold_top_decile_val_to_train_ratio": min_ratio,
        "folds_with_top_decile_ratio_ge_0_70": f"{folds_ratio_pass}/{len(fold_ratios)}",
        "top_bin_stability_pass": bool(top_bin_pass),
        "check2_pass": bool(slope_pass and top_bin_pass),
        "per_fold": per_fold,
        "oof_decile_bins": bins_detail,
    }


def evaluate_perturbation_stability(
    score_fn: Callable[[dict[str, Any]], float],
    features_dict: dict[str, Any],
    heldout_mask: Any,
    *,
    baseline_dti: float,
    candidate_dti: float,
    own_family: list[str],
    unrelated_family: list[str],
    per_fold_deltas: list[float],
    seed: int = 30,
) -> dict[str, Any]:
    """Evaluate Check 3 (feature-perturbation stability on held-out pixels only).

    Criteria from docs/research/verification-protocol.md:
    1. Permuting ``own_family`` channels on held-out pixels removes >= 50% of the
       candidate's gain over ``baseline_dti``.
    2. Permuting ``unrelated_family`` channels on held-out pixels retains a positive
       gain (> 0) over ``baseline_dti``.
    3. Per-fold gain is positive in >= 3 of 4 quadrant folds.
    """
    import numpy as np

    mask = np.asarray(heldout_mask, dtype=bool)
    rng = np.random.default_rng(seed)
    raw_gain = float(candidate_dti - baseline_dti)

    def _permute_keys(keys: list[str], perm_rng: np.random.Generator) -> dict[str, Any]:
        out = {k: np.array(v, copy=True) for k, v in features_dict.items()}
        for k in keys:
            if k not in out:
                continue
            arr = out[k]
            vals = arr[mask].copy()
            perm_rng.shuffle(vals)
            arr[mask] = vals
        return out

    own_perturbed_dti = float(score_fn(_permute_keys(own_family, rng)))
    unrelated_perturbed_dti = float(score_fn(_permute_keys(unrelated_family, rng)))

    gain_after_own_perm = float(own_perturbed_dti - baseline_dti)
    gain_after_unrelated_perm = float(unrelated_perturbed_dti - baseline_dti)
    if raw_gain > 1e-9:
        fraction_removed = float((candidate_dti - own_perturbed_dti) / raw_gain)
    else:
        fraction_removed = 0.0

    own_clause_pass = raw_gain > 0.0 and fraction_removed >= 0.50
    unrelated_clause_pass = gain_after_unrelated_perm > 0.0
    folds_positive = sum(1 for d in per_fold_deltas if d > 0.0)
    fold_clause_pass = folds_positive >= 3

    return {
        "baseline_dti": float(baseline_dti),
        "candidate_dti": float(candidate_dti),
        "raw_gain_over_baseline": raw_gain,
        "own_family_perturbed_dti": own_perturbed_dti,
        "own_family_gain_removed_fraction": fraction_removed,
        "own_family_removes_ge_50pct": bool(own_clause_pass),
        "unrelated_family_perturbed_dti": unrelated_perturbed_dti,
        "unrelated_family_retained_gain": gain_after_unrelated_perm,
        "unrelated_family_retains_positive_gain": bool(unrelated_clause_pass),
        "per_fold_deltas": [float(d) for d in per_fold_deltas],
        "folds_positive": f"{folds_positive}/{len(per_fold_deltas)}",
        "fold_sign_consistency_ge_3_of_4": bool(fold_clause_pass),
        "check3_pass": bool(own_clause_pass and unrelated_clause_pass and fold_clause_pass),
    }


def extract_qualitative_atlas(
    candidate_credit: Any,
    control_credit: Any,
    truth_mask: Any,
    valid_mask: Any,
    transform_gdal: list[float] | tuple[float, ...],
    *,
    block_size_px: int = 64,
    top_k: int = 2,
) -> dict[str, list[dict[str, Any]]]:
    """Identify top ``top_k`` blocks where the candidate helps most and fails most."""
    import numpy as np

    cand = np.asarray(candidate_credit, dtype=np.float64)
    ctrl = np.asarray(control_credit, dtype=np.float64)
    truth = np.asarray(truth_mask, dtype=bool)
    valid = np.asarray(valid_mask, dtype=bool)
    height, width = valid.shape
    x0, dx, _, y0, _, dy = [float(v) for v in transform_gdal]

    blocks: list[dict[str, Any]] = []
    for r0 in range(0, height, block_size_px):
        r1 = min(height, r0 + block_size_px)
        for c0 in range(0, width, block_size_px):
            c1 = min(width, c0 + block_size_px)
            sub_truth = truth[r0:r1, c0:c1] & valid[r0:r1, c0:c1]
            t_cnt = int(sub_truth.sum())
            if t_cnt < 10:
                continue
            cand_tp = float(cand[r0:r1, c0:c1][sub_truth].sum())
            ctrl_tp = float(ctrl[r0:r1, c0:c1][sub_truth].sum())
            delta_tp = cand_tp - ctrl_tp
            rc = 0.5 * (r0 + r1)
            cc = 0.5 * (c0 + c1)
            easting = x0 + cc * dx
            northing = y0 + rc * dy
            quad = (2 if rc >= height / 2 else 0) + (1 if cc >= width / 2 else 0)
            blocks.append({
                "row_bounds": [int(r0), int(r1)],
                "col_bounds": [int(c0), int(c1)],
                "centroid_utm11n_m": [round(easting, 1), round(northing, 1)],
                "quadrant": int(quad),
                "truth_pixels": t_cnt,
                "candidate_tp_weight": round(cand_tp, 3),
                "control_tp_weight": round(ctrl_tp, 3),
                "delta_tp_weight": round(delta_tp, 3),
            })

    blocks_sorted = sorted(blocks, key=lambda b: b["delta_tp_weight"], reverse=True)
    helps = [b for b in blocks_sorted if b["delta_tp_weight"] > 0][:top_k]
    fails = [b for b in reversed(blocks_sorted) if b["delta_tp_weight"] < 0][:top_k]
    return {"where_it_helps": helps, "where_it_fails": fails}
