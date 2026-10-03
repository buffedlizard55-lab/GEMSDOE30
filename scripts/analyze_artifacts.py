#!/usr/bin/env python3
"""Structure audit of the scored owner-mirror artifacts plus exact metric arithmetic.

Produces ``docs/research/artifact-structure.json``.  Two things are deliberately
separated:

* **COMPUTED** facts measured from the restored bytes with the exact published
  metric (emitted-pixel counts, spacing, redundancy, catalogue-proxy credit).
* **REPORTED** scores supplied by the owner/user; they are never treated as
  verified, and the script quantifies what they would imply.

The catalogue proxy is *not* the competition truth: the organizer scores only the
expert-labelled faults that are absent from the USGS/INGENIOUS catalogue and masks
the known-fault pixels (DrivenData staff, community thread 11516, 2026-09-16).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemsdoe30.emission import (  # noqa: E402
    marginal_inclusion_ratio,
    required_coverage_multiplier,
    required_fp_reduction,
)
from gemsdoe30.metric import distance_weighted_tversky  # noqa: E402

ARTIFACTS = [
    ("h19_5", "gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", 0.1922),
    ("d1_5", "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("d2_8", "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    ("h25_ctx_ridge", "gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif", 0.1280),
    ("h28_dotted_ridge", "gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif", 0.1839),
]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def spacing_stats(binary: np.ndarray, sample: int, seed: int) -> dict[str, float]:
    from scipy.spatial import cKDTree

    idx = np.argwhere(binary).astype(np.float64)
    if idx.shape[0] < 3:
        return {"pixels_sampled": float(idx.shape[0])}
    rng = np.random.default_rng(seed)
    sel = rng.choice(idx.shape[0], min(sample, idx.shape[0]), replace=False)
    distances, _ = cKDTree(idx).query(idx[sel], k=2)
    nearest = distances[:, 1]
    return {
        "pixels_sampled": float(sel.size),
        "median_px": float(np.median(nearest)),
        "p10_px": float(np.percentile(nearest, 10)),
        "p90_px": float(np.percentile(nearest, 90)),
        "fraction_under_1px": float((nearest < 1.0).mean()),
        "fraction_under_2px": float((nearest < 2.0).mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/artifact-structure.json"))
    parser.add_argument("--sample", type=int, default=6000)
    args = parser.parse_args()

    labels = rasterio.open(args.raw_dir / "labels.tif").read(1)
    template = rasterio.open(args.raw_dir / "sample_submission.tif").read(1)
    valid = np.isfinite(template)
    truth = (labels == 1) & valid
    catalogue_pixels = int(truth.sum())

    report: dict[str, object] = {
        "generated_utc": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "catalogue_pixels": catalogue_pixels,
        "valid_pixels": int(valid.sum()),
        "metric": "DTI = TPw / (TPw + 0.2*FPw + 0.8*FNw + 1e-7); TPw/FNw split the truth set, "
                  "so DTI = T / (0.2*T + 0.2*F + 0.8*G)",
        "proxy_caveat": "catalogue-proxy credit is computed against the training labels; the "
                        "competition scores only unmapped expert-labelled faults with known faults masked",
        "artifacts": {},
    }
    for key, filename, reported in ARTIFACTS:
        path = args.raw_dir / "scored" / filename
        if not path.exists():
            report["artifacts"][key] = {"file": filename, "present": False}
            continue
        with rasterio.open(path) as dataset:
            values = dataset.read(1)
        finite = np.isfinite(values)
        binary = finite & (values > 0)
        unique = np.unique(values[finite])
        evaluated = np.where(binary, 1.0, 0.0).astype(np.float64)
        scored_mask = valid & finite
        components = distance_weighted_tversky(evaluated, truth, scored_mask)
        distance_to_truth = _distance(truth)
        dot_distances = distance_to_truth[binary]
        entry = {
            "file": filename,
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "emitted_pixels": int(binary.sum()),
            "values": [float(v) for v in unique[:4]],
            "is_binary": bool(unique.size <= 2 and np.isin(unique, (0.0, 1.0)).all()),
            "on_catalogue_pixel": int((binary & truth).sum()),
            "within_300m_of_catalogue": int((dot_distances <= 300).sum()) if binary.any() else 0,
            "median_distance_to_catalogue_m": float(np.median(dot_distances)) if binary.any() else None,
            "mean_fp_weight_vs_catalogue": (float(components.fp_weight) / float(binary.sum()))
            if binary.any() else None,
            "spacing": spacing_stats(binary, args.sample, 30),
            "catalogue_proxy": {
                "tp_weight": components.tp_weight,
                "fp_weight": components.fp_weight,
                "fn_weight": components.fn_weight,
                "dti": components.score,
            },
            "owner_reported_score": reported,
            "owner_reported_status": "unverified claim; no organizer receipt was accessed",
        }
        report["artifacts"][key] = entry
        print(f"{key:16s} emitted={entry['emitted_pixels']:7d} proxy_dti={components.score:.5f} "
              f"on_catalogue={entry['on_catalogue_pixel']} reported={reported}", flush=True)

    report["arithmetic"] = {
        "marginal_inclusion_ratio_at_0p26": marginal_inclusion_ratio(0.26),
        "coverage_multiplier_0p26_to_0p3195": required_coverage_multiplier(0.26, 0.3195),
        "fp_reduction_at_coverage_0p41": required_fp_reduction(0.26, 0.3195, 0.41),
        "coverage_multiplier_0p26_to_0p2941": required_coverage_multiplier(0.26, 0.2941),
        "note": "coverage = T/G; the multiplier is exact for the published metric at fixed FP ratio",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1))
    print(json.dumps(report["arithmetic"], indent=1))
    return 0


def _distance(truth: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt
    return distance_transform_edt(~truth, sampling=(100.0, 100.0))


if __name__ == "__main__":
    raise SystemExit(main())
