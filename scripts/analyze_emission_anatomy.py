#!/usr/bin/env python3
"""Anatomy of the reported best-scoring owner rasters (the "dotted D2.8" family).

What this script does and does not do
-------------------------------------
* It measures **local raster pixels only** (values, counts, spacing, redundancy,
  distance transforms). Those measurements are reproducible facts.
* It uses the *published* metric algebra to convert each owner-reported score
  into the constraint ``A = 0.2*s*(4t + F) / (1 - 0.2*s)``, where ``A`` is the
  achieved distance-weighted true-positive credit, ``F`` the distance-weighted
  false-positive mass, ``t`` the (unknown) hidden-truth pixel count and ``s`` the
  reported score.  Reported scores are user/owner claims and are never treated as
  verified organizer results.
* It never assumes that a score belongs to a particular file.

Outputs ``docs/research/emission-anatomy.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemsdoe30.emission import dti_from_components  # noqa: E402

ALPHA = 0.2
BETA = 0.8
RADIUS_M = 300.0
PIXEL_M = 100.0

# Owner-reported claims.  ``score`` is unverified (no organizer receipt); the file
# hashes below are SHA-256 of the local bytes.  ``None`` means "no score claimed".
CLAIMED = [
    ("gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan.tif", 0.1922),
    ("gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477),
    ("gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
]


def implied_credit(score: float, truth_pixels: float, fp_mass: float) -> float:
    """Exact rearrangement of ``s = A / (alpha*(A+F) + (1-alpha)*t)``.

    ``A = 0.2*s*(4*t + F) / (1 - 0.2*s)``.
    """

    return 0.2 * score * (4.0 * truth_pixels + fp_mass) / (1.0 - 0.2 * score)


def marginal_credit_per_fp(score: float) -> float:
    """``dA/dF`` that leaves the score unchanged at ``score``.

    From ``A = 0.2*s*(4t+F)/(1-0.2*s)`` the derivative with respect to ``F`` at
    fixed score is ``0.2*s/(1-0.2*s)``: one extra unit of false-positive mass must
    be paid for with this much extra true-positive credit.
    """

    return 0.2 * score / (1.0 - 0.2 * score)


def coverage_for_score(score: float) -> float:
    """Truth-coverage fraction needed to reach ``score`` when FP mass is zero.

    With ``F = 0`` and ``A = c*t``: ``s = c*t / (0.2*c*t + 0.8*t)`` so
    ``c = 0.8*s / (1 - 0.2*s)``.
    """

    return 0.8 * score / (1.0 - 0.2 * score)


def fp_mass_for(score: float, truth_pixels: float, coverage: float) -> float:
    """False-positive mass implied by ``(score, truth size, coverage)``.

    ``F = 5*A*(1/s - 0.2) - 4*t`` with ``A = coverage * t``.
    """

    credit = coverage * truth_pixels
    return 5.0 * credit * (1.0 / score - 0.2) - 4.0 * truth_pixels


def raster_stats(path: Path, valid: np.ndarray, catalogue: np.ndarray, footprint_px: int) -> dict:
    import rasterio

    with rasterio.open(path) as dataset:
        data = dataset.read(1).astype(np.float32)
        meta = {
            "width": dataset.width,
            "height": dataset.height,
            "crs": str(dataset.crs),
            "transform": list(dataset.transform)[:6],
            "dtype": dataset.dtypes[0],
            "nodata": None if dataset.nodata is None else float(dataset.nodata),
        }
    finite = np.isfinite(data)
    inside_positive = finite & (data > 0.0)
    emitted = inside_positive & valid
    outside_finite_positive = inside_positive & ~valid
    values = np.unique(data[finite])
    positive_pixels = int(emitted.sum())
    truth = catalogue

    def _distance_to(mask: np.ndarray) -> np.ndarray:
        if not mask.any():
            return np.full(mask.shape, np.inf, dtype=np.float64)
        return distance_transform_edt(~mask, sampling=(PIXEL_M, PIXEL_M))

    dot_distance = _distance_to(emitted)
    catalogue_distance = _distance_to(truth)
    # Distance from every catalogue (catalogue-proxy truth) pixel to the nearest dot.
    truth_to_dot = dot_distance[truth] if truth.any() else np.array([np.inf])
    # Redundancy: a dot is redundant if another dot sits within the 300 m kernel.
    if positive_pixels:
        dot_nn = dot_distance[emitted]
        redundant = float((dot_nn <= RADIUS_M + 1e-9).mean())
    else:
        redundant = float("nan")
    # Enrichment of emission near the known catalogue.
    near_catalogue = catalogue_distance[emitted] <= RADIUS_M if positive_pixels else np.array([False])
    baseline_fraction = float((catalogue_distance[valid] <= RADIUS_M).mean())
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "metadata": meta,
        "distinct_values": [float(v) for v in values[:8]],
        "distinct_value_count": int(values.size),
        "binary": bool(values.size <= 2),
        "nan_outside_footprint_only": bool(finite[valid].all() and not finite[~valid].any()),
        "positive_inside_footprint": positive_pixels,
        "positive_outside_footprint": int(outside_finite_positive.sum()),
        "share_of_footprint": positive_pixels / float(footprint_px),
        "min_value": float(np.min(data[finite])) if finite.any() else None,
        "max_value": float(np.max(data[finite])) if finite.any() else None,
        "values_in_unit_interval": bool(finite.any() and np.all((data[finite] >= 0.0) & (data[finite] <= 1.0))),
        "on_catalogue_pixels": int((emitted & truth).sum()),
        "fraction_within_300m_of_catalogue": float(near_catalogue.mean()) if positive_pixels else None,
        "footprint_fraction_within_300m_of_catalogue": baseline_fraction,
        "enrichment_near_catalogue": (float(near_catalogue.mean()) / baseline_fraction) if (positive_pixels and baseline_fraction > 0) else None,
        "redundant_dot_fraction": redundant,
        "nearest_neighbour_m_p10_median_p90": [float(np.percentile(dot_nn, q)) for q in (10, 50, 90)] if positive_pixels else None,
        "catalogue_truth_to_emission_m": {
            "p10": float(np.percentile(truth_to_dot, 10)),
            "median": float(np.percentile(truth_to_dot, 50)),
            "p90": float(np.percentile(truth_to_dot, 90)),
            "fraction_within_300m": float((truth_to_dot <= RADIUS_M).mean()),
        },
    }


def proxy_split(catalogue: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split catalogue pixels into a hidden half and a masked-known half.

    Spatial checkerboard split of 8-connected catalogue components: components in
    even 2D blocks become stand-in "new faults", components in odd blocks become
    the masked known faults — the local analogue of the organizer's rule that
    pixels of known USGS/INGENIOUS faults are excluded from evaluation.  The
    ordering is deterministic and is reported so the split can be reproduced.
    """

    from scipy.ndimage import label

    components, count = label(catalogue, structure=np.ones((3, 3), dtype=int))
    rows, cols = np.nonzero(catalogue)
    block = 1024  # 102.4 km tiles: coarse enough to keep whole fault zones together
    parity = ((rows // block) + (cols // block)) % 2
    hidden = np.zeros_like(catalogue)
    known = np.zeros_like(catalogue)
    hidden[rows[parity == 0], cols[parity == 0]] = True
    known[rows[parity == 1], cols[parity == 1]] = True
    return hidden, known


def proxy_dti(prediction: np.ndarray, valid: np.ndarray, hidden: np.ndarray, known: np.ndarray) -> dict:
    """Exact DTI of the stand-in hidden truth on the masked domain.

    ``hidden`` is the stand-in truth; ``known`` is masked exactly as the organizer
    masks USGS/INGENIOUS pixels.  This is the repository's registered
    hide-and-recover proxy, not a competition score.
    """

    emitted = valid & (prediction > 0.0)
    truth = hidden
    scored = valid & ~known  # masked-known pixels never count
    credit = np.zeros(prediction.shape, dtype=np.float64)
    radius_px = int(math.ceil(RADIUS_M / PIXEL_M))
    values = np.where(scored, prediction, 0.0).astype(np.float64)
    height, width = prediction.shape
    for dy in range(-radius_px, radius_px + 1):
        for dx in range(-radius_px, radius_px + 1):
            distance = PIXEL_M * math.hypot(dy, dx)
            if distance > RADIUS_M:
                continue
            kernel = 1.0 - distance / RADIUS_M
            y0d, y1d = max(0, -dy), min(height, height - dy)
            x0d, x1d = max(0, -dx), min(width, width - dx)
            if y0d >= y1d or x0d >= x1d:
                continue
            candidate = values[y0d + dy:y1d + dy, x0d + dx:x1d + dx] * kernel
            np.maximum(credit[y0d:y1d, x0d:x1d], candidate, out=credit[y0d:y1d, x0d:x1d])
    scored_truth = truth & scored
    tp = float(credit[scored_truth].sum())
    truth_count = float(scored_truth.sum())
    if truth_count == 0:
        return {"dti": float("nan"), "note": "no proxy truth inside the scored domain"}
    distance = distance_transform_edt(~scored_truth, sampling=(PIXEL_M, PIXEL_M))
    fp_weight = np.minimum(distance / RADIUS_M, 1.0)
    fp = float((values * fp_weight).sum())
    return {
        "dti": dti_from_components(tp, fp, truth_count, alpha=ALPHA),
        "tp_weight": tp,
        "fp_weight": fp,
        "proxy_truth_pixels": truth_count,
        "emitted_pixels": int(emitted.sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--scored-dir", type=Path, default=Path("data/raw/scored"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/emission-anatomy.json"))
    parser.add_argument("--proxy", action="store_true", help="also compute catalogue-proxy DTI per raster")
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = labels == 1
    footprint_px = int(valid.sum())

    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "warning": (
            "All competition scores referenced here are user/owner-reported and unverified. "
            "Raster statistics are local measurements of local bytes. No file-to-score "
            "attribution is asserted."
        ),
        "metric_algebra": {
            "official_form": "DTI = TPw / (0.2*FPw + 0.8*G) with FNw = G - TPw substituted",
            "simplified": "DTI = A / (0.2*(A + F) + 0.8*G), A=TPw, F=FPw, G=truth pixels",
            "implied_credit": "A = 0.2*s*(4*G + F) / (1 - 0.2*s) for a reported score s",
            "zero_fp_coverage_for_score": {str(s): coverage_for_score(s) for s in (0.1922, 0.2477, 0.2600, 0.3195, 0.40, 0.50)},
            "marginal_credit_per_unit_fp": {str(s): marginal_credit_per_fp(s) for s in (0.1922, 0.2477, 0.2600, 0.3195, 0.40)},
            "interpretation": (
                "At a reported score of 0.26, one unit of extra false-positive mass must be paid for "
                "with 0.0549 units of additional distance-weighted true-positive credit; equivalently a "
                "false-positive pixel is affordable whenever its expected credit exceeds ~5.5% of its "
                "false-positive weight. A scoring of 0.2600 with negligible false-positive mass requires "
                "covering ~22% of the hidden truth pixels; 0.3195 requires ~27.3%."
            ),
        },
        "footprint": {
            "valid_pixels": footprint_px,
            "catalogue_positive_pixels": int(catalogue.sum()),
            "share_within_300m_of_catalogue": float((distance_transform_edt(~catalogue, sampling=(PIXEL_M, PIXEL_M))[valid] <= RADIUS_M).mean()),
        },
        "rasters": {},
    }

    for name, score in CLAIMED:
        path = args.scored_dir / name
        if not path.is_file():
            report["rasters"][name] = {"error": "missing file", "path": str(path)}
            continue
        stats = raster_stats(path, valid, catalogue, footprint_px)
        stats["reported_score"] = score
        stats["reported_score_source"] = "user/owner-reported; unverified"
        stats["implied_credit_equation"] = (
            f"A = {0.2 * score / (1 - 0.2 * score):.5f} * (4*G + F)"
        )
        claim_rows = []
        emitted = stats["positive_inside_footprint"]
        for truth_pixels in (5_000, 10_000, 20_000, 40_000, 80_000, 160_000, 320_000):
            # For an assumed hidden-truth size G, the reported score pins coverage
            # to a feasible band: the lower edge is the zero-FP reading, the upper
            # edge is the reading in which every emitted pixel is pure FP mass.
            min_coverage = coverage_for_score(score)
            max_coverage = min(1.0, (emitted / float(truth_pixels) + 4.0) / (5.0 * (1.0 / score - 0.2)))
            row = {
                "assumed_hidden_truth_pixels": truth_pixels,
                "implied_credit_lower_edge": min_coverage * truth_pixels,
                "implied_coverage_lower_edge": min_coverage,
                "implied_coverage_upper_edge": max_coverage,
                "fp_mass_lower_edge": 0.0,
                "fp_mass_upper_edge": fp_mass_for(score, truth_pixels, max_coverage),
                "emitted_pixels": emitted,
                "feasible": bool(min_coverage <= max_coverage),
            }
            claim_rows.append(row)
        stats["score_consistency_grid"] = claim_rows
        report["rasters"][name] = stats

    # Nesting structure: are the thinned rasters subsets of the fuller ones?
    def _mask(path: Path) -> np.ndarray:
        import rasterio
        with rasterio.open(path) as dataset:
            return dataset.read(1) > 0.0

    masks = {name: _mask(args.scored_dir / name) for name, _ in CLAIMED if (args.scored_dir / name).is_file()}
    nesting = {}
    names = list(masks)
    for a in names:
        for b in names:
            if a == b:
                continue
            inter = int((masks[a] & masks[b]).sum())
            nesting[f"{a} ∩ {b}"] = {
                "intersection": inter,
                "a_pixels": int(masks[a].sum()),
                "subset": bool(inter == int(masks[a].sum())),
            }
    report["nesting"] = nesting

    if args.proxy:
        hidden, known = proxy_split(catalogue)
        report["proxy_split"] = {
            "design": "8-connected catalogue components split by 1024-pixel checkerboard parity",
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "hidden_share": float(hidden.sum() / catalogue.sum()),
        }
        for name, score in CLAIMED:
            path = args.scored_dir / name
            if not path.is_file():
                continue
            import rasterio
            with rasterio.open(path) as dataset:
                prediction = dataset.read(1).astype(np.float32)
            prediction = np.where(np.isfinite(prediction), prediction, 0.0)
            report["rasters"][name]["catalogue_proxy_dti"] = proxy_dti(prediction, valid, hidden, known)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1))
    print(f"wrote {args.output}")
    for name in report["rasters"]:
        row = report["rasters"][name]
        if "error" in row:
            print(name, "MISSING")
            continue
        print(f"{name}\n  pixels={row['positive_inside_footprint']} reported={row['reported_score']} "
              f"near_catalogue={row['fraction_within_300m_of_catalogue']} redundant={row['redundant_dot_fraction']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
