#!/usr/bin/env python3
"""Pre-registered holdout for the potential-field contact-coincidence candidate (H-CC1).

Hypothesis (H-CC1): where the high-pass horizontal-gradient maxima of the reduced-to-pole
magnetic anomaly (layer ``rtp``) and of the isostatic gravity anomaly (layer
``iso_grav_anom``) coincide, a juxtaposition of rock with contrasting susceptibility AND
density is more likely to be a discontinuity (fault) than either gradient alone.

Design (fixed before any holdout score was computed; see docs/research/2026-10-25/):
- Uses NO catalogue-derived feature. The catalogue (labels == 1) is used only as the
  truth set for the shared hide-and-recover evaluator, so feature leakage is impossible
  by construction; the single-feature canary is still run and reported.
- Feature: high-pass with a Gaussian sigma of 5 px (500 m), Sobel horizontal-gradient
  magnitude, robust z-score over valid pixels, 3-px erosion of the footprint edge.
- Coincidence score: geometric mean of the two positive z-scores.
- Selection: top 1.0 % of eligible valid pixels by score (budget fixed a priori).
- Probability: 0.5 + 0.5 * clip((c - t) / (c_max - t), 0, 1) on selected pixels, 0 elsewhere.
- Arms: candidate; single-layer comparator (rtp gradient only, same budget);
  matched-count random control (5 seeds).
- Evaluation: shared ``gemsdoe30.holdout.split_components`` (whole 8-connected catalogue
  components, interleaved per 3.2 km tile) with ``masked_dti`` / ``fp_weight_field``
  (exact 300 m triangular kernel, alpha 0.2, beta 0.8). Five split seeds (31-35) give a
  t-based 95 % CI over split randomness.

Usage: python scripts/contact_coincidence_holdout.py --raw data/raw --out docs/research/2026-10-25
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage  # noqa: E402

from gemsdoe30.holdout import EVALUATOR_VERSION, fp_weight_field, masked_dti, split_components  # noqa: E402

PRE = {
    "hp_sigma_px": 5.0,
    "edge_erode_px": 3,
    "top_fraction": 0.01,
    "exp3_pool_fraction": 0.05,
    "exp3_min_spacing_px": 3.0,
    "floor_p": 0.5,
    "split_seeds": [31, 32, 33, 34, 35],
    "random_control_seeds": [101, 102, 103, 104, 105],
    "t_crit_df4_95": 2.776,
}


def sha256(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def read_layer(src, name: str) -> np.ndarray:
    names = [d.split(" - ")[0] if d else "" for d in src.descriptions]
    if name not in names:
        raise KeyError(f"layer {name!r} not found; available: {names}")
    arr = src.read(names.index(name) + 1, masked=True).astype(np.float64).filled(np.nan)
    arr[np.abs(arr) > 1e30] = np.nan
    return arr


def robust_z(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    values = field[valid]
    med = np.median(values)
    mad = 1.4826 * np.median(np.abs(values - med))
    if not np.isfinite(mad) or mad <= 0:
        raise ValueError("degenerate MAD in robust z-score")
    return (field - med) / mad


def gradient_magnitude_z(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """High-pass the field, then Sobel horizontal-gradient magnitude, robust-z over valid cells."""
    filled = np.where(valid, field, np.median(field[valid]))
    highpass = filled - ndimage.gaussian_filter(filled, sigma=sigma, mode="nearest")
    gx = ndimage.sobel(highpass, axis=1, mode="nearest")
    gy = ndimage.sobel(highpass, axis=0, mode="nearest")
    mag = np.hypot(gx, gy)
    return robust_z(mag, valid)


def select_top(score: np.ndarray, eligible: np.ndarray, fraction: float, floor_p: float) -> tuple[np.ndarray, float]:
    threshold = float(np.quantile(score[eligible], 1.0 - fraction))
    selected = eligible & (score >= threshold)
    top = float(np.max(score[eligible]))
    span = max(top - threshold, 1e-12)
    prob = np.zeros(score.shape, dtype=np.float64)
    prob[selected] = floor_p + (1.0 - floor_p) * np.clip((score[selected] - threshold) / span, 0.0, 1.0)
    return prob, threshold


def greedy_dispersed(score: np.ndarray, eligible: np.ndarray, pool_fraction: float, budget: int,
                     min_spacing_px: float) -> np.ndarray:
    """Experiment 3: greedy thinning in score order, Euclidean spacing >= min_spacing_px.

    The pool is the top ``pool_fraction`` of eligible cells; accepted cells are taken in
    descending score order and capped at ``budget`` so the dot count matches the
    candidate exactly. Only dispersion changes relative to the top-1 % candidate.
    """
    threshold = float(np.quantile(score[eligible], 1.0 - pool_fraction))
    rows, cols = np.nonzero(eligible & (score >= threshold))
    order = np.argsort(-score[rows, cols], kind="stable")
    reach = int(math.ceil(min_spacing_px)) - 1
    occupied = np.zeros(score.shape, dtype=bool)
    accepted = np.zeros(score.shape, dtype=bool)
    count = 0
    for k in order:
        y, x = int(rows[k]), int(cols[k])
        y0, y1 = max(0, y - reach), min(score.shape[0], y + reach + 1)
        x0, x1 = max(0, x - reach), min(score.shape[1], x + reach + 1)
        window = occupied[y0:y1, x0:x1]
        wy, wx = np.mgrid[y0:y1, x0:x1]
        too_close = window & (((wy - y) ** 2 + (wx - x) ** 2) < min_spacing_px ** 2)
        if too_close.any():
            continue
        accepted[y, x] = True
        occupied[y, x] = True
        count += 1
        if count >= budget:
            break
    return accepted


def auc(scores: np.ndarray, labels: np.ndarray, rng: np.random.Generator, max_neg: int = 400_000) -> float:
    pos = scores[labels]
    neg = scores[~labels]
    if pos.size == 0 or neg.size == 0:
        return float("nan")
    if neg.size > max_neg:
        neg = rng.choice(neg, size=max_neg, replace=False)
    ranks = np.argsort(np.argsort(np.concatenate([pos, neg]))) + 1.0
    r_pos = ranks[: pos.size].sum()
    return float((r_pos - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size))


def t_ci(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    half = PRE["t_crit_df4_95"] * sd / math.sqrt(arr.size)
    return {"mean": mean, "sd": sd, "ci95_low": mean - half, "ci95_high": mean + half, "n": int(arr.size)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=REPO / "data/raw")
    ap.add_argument("--out", type=Path, default=REPO / "docs/research/2026-10-25")
    ap.add_argument("--candidate-tif", type=Path, default=None,
                    help="optional path to write the candidate probability raster (float32, NaN outside)")
    args = ap.parse_args()

    feats_path = args.raw / "training_features.tif"
    labels_path = args.raw / "labels.tif"
    tmpl_path = args.raw / "sample_submission.tif"

    with rasterio.open(tmpl_path) as t:
        template_valid = np.isfinite(t.read(1))
        grid = (t.crs.to_string(), t.transform, t.width, t.height)
    with rasterio.open(labels_path) as lab:
        labels = lab.read(1)
        if (lab.crs.to_string(), lab.transform, lab.width, lab.height) != grid:
            raise ValueError("labels grid differs from template")
    valid = template_valid
    if not np.array_equal(valid, labels >= 0):
        raise ValueError("template footprint differs from label footprint")
    catalogue = labels == 1

    with rasterio.open(feats_path) as f:
        if (f.crs.to_string(), f.transform, f.width, f.height) != grid:
            raise ValueError("feature grid differs from template")
        rtp = read_layer(f, "rtp")
        grav = read_layer(f, "iso_grav_anom")
        feature_names = [d.split(" - ")[0] for d in f.descriptions]

    # Source gaps: the same in-footprint cells are NaN in both layers. They cannot be
    # scored for this candidate, so they keep probability 0 but stay in the scored domain.
    feat_ok = np.isfinite(rtp) & np.isfinite(grav)
    gap_in_footprint = int(np.count_nonzero(valid & ~feat_ok))
    gap_mismatch = int(np.count_nonzero(valid & (np.isfinite(rtp) != np.isfinite(grav))))
    analysis = valid & feat_ok

    eligible = ndimage.binary_erosion(analysis, iterations=PRE["edge_erode_px"])
    z_mag = gradient_magnitude_z(rtp, analysis, PRE["hp_sigma_px"])
    z_grav = gradient_magnitude_z(grav, analysis, PRE["hp_sigma_px"])
    coincidence = np.sqrt(np.clip(z_mag, 0, None) * np.clip(z_grav, 0, None))
    coincidence = np.where(eligible, coincidence, 0.0)
    rtp_only = np.where(eligible, np.clip(z_mag, 0, None), 0.0)

    cand_prob, cand_t = select_top(coincidence, eligible, PRE["top_fraction"], PRE["floor_p"])
    single_prob, single_t = select_top(rtp_only, eligible, PRE["top_fraction"], PRE["floor_p"])
    n_budget = int(np.count_nonzero(cand_prob))

    # Canary: single features alone, on the hide-and-recover domain, before trusting results.
    rng = np.random.default_rng(7)
    canary_seed = PRE["split_seeds"][0]
    hidden0, known0, _ = split_components(catalogue, seed=canary_seed)
    scored0 = valid & ~known0
    hidden_pos = hidden0 & scored0
    canary = {}
    for name, arr in (("H-CC1 coincidence", coincidence), ("rtp gradient only", rtp_only),
                      ("z_grav gradient only", np.where(eligible, np.clip(z_grav, 0, None), 0.0))):
        canary[name] = auc(arr[scored0], hidden_pos[scored0], rng)
    canary_flag = {k: (v > 0.90) for k, v in canary.items()}

    def evaluate(prob: np.ndarray, label: str) -> tuple[list[dict], dict]:
        rows = []
        for seed in PRE["split_seeds"]:
            hidden, known, n_comp = split_components(catalogue, seed=seed)
            fpw = fp_weight_field(catalogue, known)
            pred = np.where(valid, prob, 0.0)
            res = masked_dti(pred, catalogue, known, fp_weight=fpw)
            res.update({"arm": label, "split_seed": seed, "components": int(n_comp)})
            rows.append(res)
        summary = t_ci([r["dti"] for r in rows])
        summary["withheld_positives_per_seed"] = [int(r["hidden_truth_pixels"]) for r in rows]
        return rows, summary

    cand_rows, cand_sum = evaluate(cand_prob, "H-CC1 coincidence top1pct")
    single_rows, single_sum = evaluate(single_prob, "rtp gradient only top1pct")
    # Ablation (experiment 2): identical selection, binary p = 1 on selected cells.
    # Separates ranking quality from the 0.5-1 probability floor used by the candidate.
    binary_prob = (cand_prob > 0).astype(np.float64)
    bin_rows, bin_sum = evaluate(binary_prob, "H-CC1 binary p=1 ablation")
    # Experiment 3 (last allowed): same score, greedy 3-px dispersion, matched dot budget, p=1.
    disp_mask = greedy_dispersed(coincidence, eligible, PRE["exp3_pool_fraction"], n_budget,
                                 PRE["exp3_min_spacing_px"])
    disp_prob = disp_mask.astype(np.float64)
    disp_rows, disp_sum = evaluate(disp_prob, "H-CC1 dispersed 3px matched-budget (exp3)")

    rand_summaries = []
    rand_rows_all = []
    for rseed in PRE["random_control_seeds"]:
        rr = np.random.default_rng(rseed)
        idx = np.flatnonzero(eligible.ravel())
        pick = rr.choice(idx, size=n_budget, replace=False)
        rprob = np.zeros(valid.size, dtype=np.float64)
        rprob[pick] = 1.0
        rprob = rprob.reshape(valid.shape)
        rows, summ = evaluate(rprob, f"matched random control seed {rseed}")
        rand_rows_all.extend(rows)
        rand_summaries.append(summ["mean"])
    rand_sum = t_ci(rand_summaries)

    # Candidate raster hash and format checks (no NaN inside footprint, values in [0,1]).
    inside = cand_prob[valid]
    fmt = {
        "finite_inside_footprint": bool(np.isfinite(inside).all()),
        "values_in_0_1": bool(np.all((inside >= 0) & (inside <= 1))),
        "selected_pixels": n_budget,
        "selected_fraction_of_valid": n_budget / int(valid.sum()),
        "valid_pixels": int(valid.sum()),
    }

    out = {
        "schema_version": 1,
        "hypothesis_id": "H-CC1",
        "name": "potential-field contact coincidence (RTP magnetic x isostatic gravity gradient)",
        "evaluator_version": EVALUATOR_VERSION,
        "preregistered_parameters": PRE,
        "inputs": {
            "training_features_sha256": sha256(feats_path),
            "labels_sha256": sha256(labels_path),
            "template_sha256": sha256(tmpl_path),
            "grid": {"crs": grid[0], "width": grid[2], "height": grid[3], "pixel_m": grid[1].a},
            "feature_layers_used": ["rtp", "iso_grav_anom"],
            "feature_band_count": len(feature_names),
        },
        "thresholds": {"coincidence_top1pct": cand_t, "rtp_only_top1pct": single_t},
        "canary_auc_seed31": canary,
        "canary_flags_gt_0_90": canary_flag,
        "arms": {
            "H-CC1_candidate": {"summary": cand_sum, "per_seed": cand_rows},
            "rtp_only_comparator": {"summary": single_sum, "per_seed": single_rows},
            "H-CC1_binary_ablation": {"summary": bin_sum, "per_seed": bin_rows},
            "H-CC1_dispersed_exp3": {"summary": disp_sum, "per_seed": disp_rows,
                                     "dots": int(disp_mask.sum()), "matched_budget": n_budget},
            "matched_random_control": {"summary_of_mean_dti": rand_sum, "per_seed": rand_rows_all},
        },
        "format_checks": fmt,
        "source_gaps": {"in_footprint_nan_cells": gap_in_footprint, "rtp_vs_grav_mismatch_cells": gap_mismatch,
                         "outside_footprint_finite_cells_ignored": int(np.count_nonzero(~valid & np.isfinite(rtp)))},
        "label_convention": {
            "HOLDOUT-DTI": {
                "evaluator_version": EVALUATOR_VERSION,
                "withheld_positives": "per split seed, see per_seed.hidden_truth_pixels",
                "ci95": "t-interval over 5 split seeds (n=5)",
                "scope": "catalogue stand-in holdout, NOT organizer score",
            }
        },
    }

    if args.candidate_tif is not None:
        args.candidate_tif.parent.mkdir(parents=True, exist_ok=True)
        out_arr = np.where(valid, cand_prob, np.nan).astype(np.float32)
        profile = {"driver": "GTiff", "dtype": "float32", "count": 1, "width": grid[2], "height": grid[3],
                   "crs": rasterio.crs.CRS.from_string(grid[0]), "transform": grid[1], "nodata": None,
                   "compress": "deflate", "predictor": 3}
        with rasterio.open(args.candidate_tif, "w", **profile) as dst:
            dst.write(out_arr, 1)
        out["candidate_raster"] = {"path": str(args.candidate_tif), "sha256": sha256(args.candidate_tif)}

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "contact-coincidence-holdout.json"
    dest.write_text(json.dumps(out, indent=2, allow_nan=True) + "\n")
    print(json.dumps({"candidate": cand_sum, "rtp_only": single_sum, "random": rand_sum,
                      "canary": canary, "format": fmt}, indent=2))
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
