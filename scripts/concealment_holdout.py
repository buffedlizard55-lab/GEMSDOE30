#!/usr/bin/env python3
"""Leakage-canary and hide/recover screen for a basin-concealment prior.

This is an exploratory, label-blind screen, not a competition-score estimate.
It deliberately stops before writing a submission TIFF: only a validated,
non-duplicate candidate that beats a comparable holdout best may be published.

The candidate uses two numeric competition bands only:
  * depth_to_base_surf (deep basement / thick cover proxy), and
  * absolute det_elev_slope (low-relief cover proxy).
The fixed score is the mean of their empirical percentile ranks, with slope rank
reversed. No catalogue-derived feature is used to build the score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe30.holdout import masked_dti, split_components  # noqa: E402


def auc_higher_is_positive(values: np.ndarray, positive: np.ndarray, negative: np.ndarray) -> float:
    """Tie-correct empirical AUC, where larger feature values indicate positives."""
    p = np.asarray(values).ravel()[positive]
    n = np.asarray(values).ravel()[negative]
    p, n = p[np.isfinite(p)], n[np.isfinite(n)]
    if not p.size or not n.size:
        return float("nan")
    ranks = rankdata(np.concatenate((p, n)), method="average")
    np_, nn = len(p), len(n)
    return float((ranks[:np_].sum() - np_ * (np_ + 1) / 2) / (np_ * nn))


def percentile_field(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    vals = np.asarray(field[valid], dtype=np.float32)
    vals = vals[np.isfinite(vals)]
    if not vals.size:
        raise ValueError("candidate band has no finite values in the footprint")
    q = np.linspace(0, 1, 1001)
    knots = np.quantile(vals, q).astype(np.float32)
    # Repeated quantiles are harmless: np.interp produces a monotone empirical-rank proxy.
    out = np.zeros(field.shape, dtype=np.float32)
    finite = valid & np.isfinite(field)
    out[finite] = np.interp(field[finite], knots, q).astype(np.float32)
    return out


def exact_binary_dti(pred: np.ndarray, hidden: np.ndarray, known: np.ndarray,
                     footprint: np.ndarray, *, pixel_m: float = 100.0,
                     radius_m: float = 300.0, alpha: float = 0.2) -> tuple[dict, np.ndarray]:
    """Exact triangular-kernel DTI for binary dots; also return additive segment stats.

    For binary predictions, max_x max(1-d(x,y)/R, 0) equals the triangular
    transform of the EDT to the nearest predicted pixel. False-positive weights
    are assigned to the nearest held-out component for a paired component bootstrap.
    """
    pred = np.asarray(pred, dtype=bool) & footprint & ~known
    hidden = np.asarray(hidden, dtype=bool) & footprint & ~known
    if not hidden.any():
        raise ValueError("holdout split has no hidden positive pixels")
    distance_pred = ndimage.distance_transform_edt(~pred, sampling=(pixel_m, pixel_m))
    credit = np.maximum(1.0 - distance_pred / radius_m, 0.0)
    tp = float(credit[hidden].sum())
    g = float(hidden.sum())

    dist_truth, nearest = ndimage.distance_transform_edt(
        ~hidden, sampling=(pixel_m, pixel_m), return_indices=True
    )
    fp_field = np.where(footprint & ~known, pred * np.minimum(dist_truth / radius_m, 1.0), 0.0)
    fp = float(fp_field.sum())
    score = tp / (alpha * tp + alpha * fp + (1.0 - alpha) * g)

    component_ids, component_count = ndimage.label(hidden, structure=np.ones((3, 3), dtype=np.uint8))
    ids = np.arange(1, component_count + 1)
    tp_by = np.bincount(component_ids[hidden], weights=credit[hidden], minlength=component_count + 1)[1:]
    g_by = np.bincount(component_ids[hidden], minlength=component_count + 1)[1:].astype(np.float64)
    nearest_ids = component_ids[tuple(nearest)]
    fp_by = np.bincount(nearest_ids.ravel(), weights=fp_field.ravel(), minlength=component_count + 1)[1:]
    stats = np.column_stack((tp_by, fp_by, g_by))
    return ({"dti": float(score), "tp_weight": tp, "fp_weight": fp,
             "hidden_positive_pixels": int(hidden.sum()), "emitted_pixels": int(pred.sum()),
             "heldout_component_count": int(component_count)}, stats)


def bootstrap_ci(stats: np.ndarray, *, seed: int, draws: int = 1000) -> list[float]:
    """95% component-cluster bootstrap CI from additive sufficient statistics."""
    if not len(stats):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    n = len(stats)
    out = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        sample = rng.integers(0, n, size=n)
        tp, fp, g = stats[sample].sum(axis=0)
        den = 0.2 * tp + 0.2 * fp + 0.8 * g
        out[i] = tp / den if den > 0 else np.nan
    lo, hi = np.nanquantile(out, [0.025, 0.975])
    return [float(lo), float(hi)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    ap.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    ap.add_argument("--seed", type=int, default=31)
    ap.add_argument("--negative-sample", type=int, default=200000)
    ap.add_argument("--dots", type=int, default=37654)
    ap.add_argument("--output", type=Path, default=Path("docs/research/candidate-screens/concealment-screen.json"))
    args = ap.parse_args()

    manifest = json.loads((args.data_dir / "manifest.json").read_text())
    features = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
    footprint = np.load(args.data_dir / "valid.npy").astype(bool) & np.load(args.data_dir / "label_valid.npy").astype(bool)
    labels = (np.load(args.data_dir / "labels.npy") > 0.5) & footprint
    hidden, known, total_components = split_components(labels, seed=args.seed, stratify=32)
    hidden &= footprint
    known &= footprint

    # Pixel-exact visible-fault mask; negative AUC sample is outside hidden and visible positives.
    positives = np.flatnonzero(hidden)
    negatives_all = np.flatnonzero(footprint & ~hidden & ~known)
    rng = np.random.default_rng(args.seed + 100)
    negatives = rng.choice(negatives_all, min(args.negative_sample, len(negatives_all)), replace=False)
    pos_mask = np.zeros(footprint.size, dtype=bool); pos_mask[positives] = True
    neg_mask = np.zeros(footprint.size, dtype=bool); neg_mask[negatives] = True

    band_names = manifest["feature_band_names"]
    short_names = [str(x).split(" - ")[0].strip() for x in band_names]
    depth_i, slope_i = short_names.index("depth_to_base_surf"), short_names.index("det_elev_slope")
    feature_aucs = []
    for i, name in enumerate(band_names):
        auc = auc_higher_is_positive(np.asarray(features[i]), pos_mask, neg_mask)
        feature_aucs.append({"band": name, "auc_higher_means_fault": auc,
                             "leakage_canary": "INVESTIGATE" if auc > 0.90 else "below 0.90 threshold"})

    depth = np.asarray(features[depth_i], dtype=np.float32)
    slope = np.abs(np.asarray(features[slope_i], dtype=np.float32))
    depth_pct = percentile_field(depth, footprint)
    slope_pct = percentile_field(slope, footprint)
    score = 0.5 * (depth_pct + (1.0 - slope_pct))
    score[~footprint] = -np.inf
    candidate_auc = auc_higher_is_positive(score, pos_mask, neg_mask)

    # Fixed output budget and no visible-catalogue pixels. This is only a holdout mask, not a TIFF.
    eligible = footprint & ~known & np.isfinite(score)
    eligible_idx = np.flatnonzero(eligible)
    n = min(args.dots, eligible_idx.size)
    order = np.argpartition(score.ravel()[eligible_idx], -n)[-n:]
    candidate = np.zeros(footprint.shape, dtype=bool)
    candidate.ravel()[eligible_idx[order]] = True

    # The candidate uses no catalogue-derived inputs. Still compute the requested
    # 300 m exclusion buffer around hidden segments; visible labels inside it are
    # ineligible for any future training fold. This exploratory screen does not fit.
    hidden_distance = ndimage.distance_transform_edt(~hidden, sampling=(100.0, 100.0))
    buffered_visible_train = known & (hidden_distance > 300.0)

    from scipy.ndimage import distance_transform_edt
    distance_to_known = distance_transform_edt(~known, sampling=(100.0, 100.0))
    random_pool = np.flatnonzero(eligible)
    matched_idx = np.flatnonzero(candidate)
    matched_control_flat = np.zeros(footprint.size, dtype=bool)
    target_d = distance_to_known.ravel()[matched_idx]
    edges = np.unique(np.quantile(target_d, np.linspace(0, 1, 11)))
    if len(edges) > 1:
        bins = np.clip(np.digitize(distance_to_known.ravel()[random_pool], edges[1:-1]), 0, len(edges)-2)
        target_bins = np.clip(np.digitize(target_d, edges[1:-1]), 0, len(edges)-2)
        desired = np.bincount(target_bins, minlength=len(edges)-1)
        for b, count in enumerate(desired):
            available = random_pool[bins == b]
            take = min(int(count), len(available))
            if take:
                matched_control_flat[rng.choice(available, take, replace=False)] = True
    # Fill any bin shortage from unused eligible pixels, deterministically.
    shortfall = n - int(matched_control_flat.sum())
    if shortfall > 0:
        remaining = random_pool[~matched_control_flat[random_pool]]
        matched_control_flat[rng.choice(remaining, min(shortfall, len(remaining)), replace=False)] = True
    matched_control = matched_control_flat.reshape(footprint.shape)

    scored = {"concealment_prior": candidate,
              "distance_profile_matched_random": matched_control}
    scores = {}
    boot_seed = args.seed + 300
    for name, prediction in scored.items():
        result, stats = exact_binary_dti(prediction, hidden, known, footprint)
        shared = masked_dti(prediction, hidden, known)
        parity_error = abs(float(result["dti"]) - float(shared["dti"]))
        if not np.isclose(result["dti"], shared["dti"], rtol=0, atol=2e-7):
            raise RuntimeError(f"local fast DTI disagrees with shared holdout.py: {result['dti']} vs {shared['dti']}")
        # The shared project evaluator is authoritative; the fast path only supplies
        # additive segment statistics for the cluster-bootstrap confidence interval.
        result["dti"] = float(shared["dti"])
        result["evaluator_parity_max_abs_error"] = parity_error
        result["component_bootstrap_95_ci"] = bootstrap_ci(stats, seed=boot_seed)
        scores[name] = result

    # Hash local source inputs to anchor this run. They remain owner mirrors, not organizer-authenticated.
    def sha(path):
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    inputs = {name: sha(args.raw_dir / path) for name, path in {
        "training_features": "training_features.tif", "labels": "labels.tif",
        "sample_submission": "sample_submission.tif"}.items()}
    report = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment": "H-34-01 reduced-input basin-concealment screen (exploratory; no TIFF written)",
        "evaluator": "scripts/concealment_holdout.py v1; exact binary triangular DTI, 100m pixels, 300m radius, alpha=.2 beta=.8; local owner-mirror inputs",
        "holdout_protocol": {"whole_connected_components": True, "split_seed": args.seed,
            "component_total": int(total_components), "withheld_positive_pixels": int(hidden.sum()),
            "visible_positive_pixels_masked_exactly": int(known.sum()),
            "visible_positive_pixels_excluded_from_training_by_buffer": int((known & ~buffered_visible_train).sum()),
            "buffer_m": 300, "buffer_note": "Whole connected components are withheld. A 300m exclusion buffer around hidden positives is applied to the hypothetical visible-label training set; this screen itself is label-blind and fits no supervised model. Visible known-fault pixels are separately masked pixel-exactly from evaluation."},
        "leakage_canary": {"negative_sample_n": int(len(negatives)), "feature_auc": feature_aucs,
            "candidate_surface_auc_higher_means_fault": candidate_auc,
            "threshold": 0.90, "status": "pass" if max([x["auc_higher_means_fault"] for x in feature_aucs] + [candidate_auc]) <= 0.90 else "investigate"},
        "hypothesis": {"layers": [short_names[depth_i], short_names[slope_i]],
            "signature": "equal-weight mean of empirical percentile rank for basement depth and inverse absolute detrended-elevation slope",
            "mechanism": "thick basin fill and low surface relief may reduce mapping observability of blind/subdued faults",
            "named_non_fault_mimic": "alluvial basin fill, lithologic contacts, and low-relief depositional surfaces; this score may primarily identify concealment rather than faults"},
        "emission_budget": {"pixels": n, "fixed_to_user-reported_H33-2-B2_count_for_comparison_only": True},
        "scores": scores,
        "data_provenance": {"mirror_status": "SHA-pinned owner mirrors, not organizer-authenticated", "sha256": inputs,
                            "prepared_manifest_dataset_signature": manifest["dataset_signature"]},
        "submission": {"written": False, "reason": "negative screen; candidate DTI is below distance-matched random, is not comparable to the archived spatial-holdout best, and the complete registry-raster duplicate gate is unavailable"},
        "limitations": ["Catalogued withheld components are a biased proxy for faults absent from USGS/INGENIOUS.",
            "Owner-mirror score claims are not organizer receipts.",
            "This first screen is not a confirmation split and does not establish hidden-test or leaderboard gain.",
            "The D2.8 TIFF was not scored as a holdout comparator: it is a previous submission and its training provenance cannot be proven label-blind for this withheld split.",
            "Rank-correlation/3px overlap checks against every requested site's registry must pass before any TIFF is written."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
