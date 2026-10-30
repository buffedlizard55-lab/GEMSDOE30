"""Single-feature leakage canary (partial).

For each available feature raster on the labels grid, compute the exact,
tie-aware ROC AUC of that single feature alone against the labelled positives
(label==1) and negatives (label==0) inside the footprint. Owner rule: a
single-feature AUC > 0.90 is leakage. No model is fitted and no holdout is
used, so this is a leakage screen only, not HOLDOUT-DTI.

Limitation: the model's own training_features.tif is absent from this
checkout, so only the derived geology layers in data/external are screened.
Receipt written to docs/research/2026-10-30-verification-receipts/leakage-canary.json.
"""
from __future__ import annotations
import glob, json, pathlib, sys
import numpy as np
import rasterio

ROOT = pathlib.Path(__file__).resolve().parents[1]
LABELS = ROOT / "data/raw/labels.tif"
FEATURES = sorted(glob.glob(str(ROOT / "data/external/derived_*.tif")))
OUT = ROOT / "docs/research/2026-10-30-verification-receipts/leakage-canary.json"
THRESHOLD = 0.90


def auc_from_hist(pos_hist: np.ndarray, neg_hist: np.ndarray) -> float:
    """Exact tie-aware AUC from per-value class histograms (P(pos>neg)+0.5*P(tie))."""
    n_pos, n_neg = pos_hist.sum(), neg_hist.sum()
    cum_neg_below = np.concatenate(([0], np.cumsum(neg_hist)[:-1]))
    wins = (pos_hist * cum_neg_below).sum() + 0.5 * (pos_hist * neg_hist).sum()
    return float(wins / (n_pos * n_neg))


def main() -> int:
    with rasterio.open(LABELS) as lab_src:
        labels = lab_src.read(1)
        lab_grid = (lab_src.crs.to_string(), lab_src.shape, lab_src.transform)
    pos_mask = labels == 1
    neg_mask = labels == 0
    results = []
    for path in FEATURES:
        with rasterio.open(path) as src:
            grid = (src.crs.to_string(), src.shape, src.transform)
            if grid != lab_grid:
                print(f"grid mismatch: {path}", file=sys.stderr)
                return 1
            feat = src.read(1)
            nodata = src.nodata
        valid = (feat != nodata) if nodata is not None else np.ones(feat.shape, bool)
        p = pos_mask & valid
        n = neg_mask & valid
        if p.sum() == 0 or n.sum() == 0:
            results.append({"feature": pathlib.Path(path).name, "error": "no valid pos/neg"})
            continue
        levels = 256 if feat.dtype == np.uint8 else int(feat.max()) + 1
        pos_hist = np.bincount(feat[p].astype(np.int64), minlength=levels)
        neg_hist = np.bincount(feat[n].astype(np.int64), minlength=levels)
        auc = auc_from_hist(pos_hist, neg_hist)
        auc_oriented = max(auc, 1.0 - auc)
        results.append({
            "feature": pathlib.Path(path).name,
            "dtype": str(feat.dtype),
            "nodata": nodata,
            "n_positive": int(p.sum()),
            "n_negative": int(n.sum()),
            "auc": round(auc, 6),
            "auc_sign_free": round(auc_oriented, 6),
            "leakage_flag": bool(auc_oriented > THRESHOLD),
        })
    receipt = {
        "schema_version": 1,
        "rule": "single-feature AUC > 0.90 (sign-free) means leakage",
        "scope": "partial: derived geology layers in data/external only; training_features.tif absent from checkout",
        "label_source": "data/raw/labels.tif (pinned mirror; provenance unresolved, IR-30-114)",
        "evaluator": "none: single-feature AUC, no model, no holdout",
        "score_class": "NOT a score (no HOLDOUT-DTI, not ORGANIZER-CONFIRMED)",
        "any_leakage_flag": any(r.get("leakage_flag") for r in results),
        "features": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n")
    for r in results:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
