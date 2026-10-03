#!/usr/bin/env python3
"""Component-holdout test of H-31-01: are intra-zone gaps between mapped strands
enriched in held-out (stand-in "new") fault pixels?

Design
------
1. Split the catalogue into 8-connected components, then assign whole components to a
   **hidden** half and a **known** half using a deterministic 1024-pixel (102.4 km)
   checkerboard of component centroids.  The hidden half is the stand-in "new fault"
   set; the known half is masked exactly as the organizer masks USGS/INGENIOUS pixels.
2. Build the H-31-01 candidate map from the **known** half only:
   * dilate the known traces by Z metres, label the resulting zones, and keep zones
     that contain at least two distinct known components;
   * remove any pixel within 300 m of a known trace (the kernel's own tolerance);
   * the remainder is the "relay / step-over connector" candidate map.
3. Controls, all evaluated on the same masked domain with the same hidden truth:
   * `random_near`: the same number of pixels drawn uniformly from all pixels within Z
     of the known traces (matched proximity, no pairing requirement), averaged over draws;
   * `zone_all`: every pixel within Z of a known trace and >300 m from it;
   * `far_random`: the same number of pixels drawn uniformly from the whole footprint
     (unmatched proximity).
4. Score the exact published index on the masked domain (truth = hidden components,
   known components excluded from all terms).

A win means the *paired-strand* geometry carries information beyond mere proximity to
mapped faults; a null means rank 1's prior is not supported and the hypothesis must be
withdrawn before any model is built on it.  Predictions are binary 1.0 emissions, so
the test isolates geometry from any model.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, label

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import dti_from_components  # noqa: E402

PIXEL_M = 100.0
RADIUS_M = 300.0
ALPHA = 0.2


def split_components(catalogue: np.ndarray, seed: int = 31, stratify: int = 32) -> tuple[np.ndarray, np.ndarray, int]:
    """Deterministic, spatially interleaved split of whole 8-connected components.

    Components are grouped into ``stratify``-pixel (3.2 km) tiles by centroid, and within
    each populated tile half of the components (deterministically shuffled) become the
    stand-in "new" faults and half stay mapped.  Interleaving at the 3.2 km scale is what
    makes the test meaningful for H-31-01: a relay/step-over strand must be able to fall on
    the *opposite* side of the split from the two boundary strands of its own zone.  A
    1024-pixel (102 km) checkerboard instead separates whole fault zones and produces a
    regional split, which measures nothing about intra-zone geometry (learned the hard way -
    the first run of this script returned every near-known arm below the far-field control).
    """

    components, count = label(catalogue, structure=np.ones((3, 3), dtype=int))
    if count == 0:
        raise ValueError("catalogue is empty")
    rows, cols = np.nonzero(catalogue)
    component_ids = components[rows, cols]
    # Centroid tile of each component.
    order = np.argsort(component_ids, kind="stable")
    ids_sorted = component_ids[order]
    rows_sorted, cols_sorted = rows[order], cols[order]
    boundaries = np.searchsorted(ids_sorted, np.arange(1, count + 1))
    starts = np.concatenate([[0], boundaries[:-1]])
    centroid_row = np.add.reduceat(rows_sorted, starts) / np.maximum(np.diff(np.concatenate([starts, [ids_sorted.size]])), 1)
    centroid_col = np.add.reduceat(cols_sorted, starts) / np.maximum(np.diff(np.concatenate([starts, [ids_sorted.size]])), 1)
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


def masked_dti(prediction: np.ndarray, truth: np.ndarray, known: np.ndarray) -> dict:
    """Exact published index with the known-fault domain masked out."""

    scored = ~known
    positive = truth & scored
    if not positive.any():
        return {"dti": float("nan"), "note": "no hidden truth inside the masked domain"}
    p = np.where(scored, prediction.astype(np.float64), 0.0)
    credit = np.zeros(p.shape, dtype=np.float64)
    reach = int(math.ceil(RADIUS_M / PIXEL_M))
    height, width = p.shape
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            distance = PIXEL_M * math.hypot(dy, dx)
            if distance > RADIUS_M:
                continue
            kernel = 1.0 - distance / RADIUS_M
            y0d, y1d = max(0, -dy), min(height, height - dy)
            x0d, x1d = max(0, -dx), min(width, width - dx)
            if y0d >= y1d or x0d >= x1d:
                continue
            candidate = p[y0d + dy:y1d + dy, x0d + dx:x1d + dx] * kernel
            np.maximum(credit[y0d:y1d, x0d:x1d], candidate, out=credit[y0d:y1d, x0d:x1d])
    tp = float(credit[positive].sum())
    truth_count = float(positive.sum())
    distance_to_truth = distance_transform_edt(~positive, sampling=(PIXEL_M, PIXEL_M))
    fp_weight = np.minimum(distance_to_truth / RADIUS_M, 1.0)
    fp = float((p * fp_weight).sum())
    near = credit[positive] > 0.0
    return {
        "dti": dti_from_components(tp, fp, truth_count, alpha=ALPHA),
        "tp_weight": tp,
        "fp_weight": fp,
        "hidden_truth_pixels": truth_count,
        "hidden_pixels_with_credit": int(near.sum()),
        "hidden_credit_fraction": float(near.mean()),
        "emitted_pixels": int(prediction.sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/relay-connector-holdout.json"))
    parser.add_argument("--zone-m", type=float, default=1500.0)
    parser.add_argument("--random-draws", type=int, default=8)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--budget", type=int, default=15000,
                        help="emitted-pixel budget for every arm (matched-count comparison)")
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & valid
    hidden, known, component_count = split_components(catalogue, seed=args.seed)
    hidden &= valid
    known &= valid

    distance_to_known = distance_transform_edt(~known, sampling=(PIXEL_M, PIXEL_M))
    near_known = valid & ~known & (distance_to_known <= args.zone_m)
    outside_kernel = distance_to_known > RADIUS_M

    # Zones = connected regions of the Z-metre dilation of the known traces that contain
    # at least two distinct known components.
    zones = near_known | known
    zone_labels, zone_count = label(zones, structure=np.ones((3, 3), dtype=int))
    known_components, _ = label(known, structure=np.ones((3, 3), dtype=int))
    pairs = np.unique(np.stack([zone_labels[known & valid].ravel(),
                                known_components[known & valid].ravel()], axis=1), axis=0)
    pairs = pairs[pairs[:, 0] > 0]
    counts = np.bincount(pairs[:, 0], minlength=zone_count + 1)
    multi_strand_zones = counts >= 2
    connector = multi_strand_zones[zone_labels] & valid & ~known & outside_kernel & ~hidden

    rng = np.random.default_rng(args.seed)
    n_connector = int(connector.sum())
    candidates_random = np.flatnonzero((near_known & outside_kernel & ~hidden).ravel())
    far_pool = np.flatnonzero((valid & ~known & ~hidden).ravel())

    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "design": "component holdout; hidden half = stand-in new faults; known half masked; "
                  "connector map built from known geometry only",
        "params": {"zone_m": args.zone_m, "random_draws": args.random_draws, "seed": args.seed},
        "catalogue": {
            "positive_pixels": int(catalogue.sum()),
            "components": int(component_count),
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "multi_strand_zones": int((counts[1:] >= 2).sum()),
            "zones": int(zone_count),
        },
        "emissions": {},
    }

    def sampled(pool_rows: np.ndarray, count: int, rng) -> np.ndarray:
        emission = np.zeros(valid.shape, dtype=bool)
        if pool_rows.size == 0 or count <= 0:
            return emission
        take = min(count, pool_rows.size)
        pick = rng.choice(pool_rows, size=take, replace=False)
        emission.ravel()[pick] = True
        return emission

    budget = int(args.budget)
    connector_rows = np.flatnonzero(connector.ravel())
    near_rows = np.flatnonzero((near_known & outside_kernel & ~hidden).ravel())
    far_rows = np.flatnonzero((valid & ~known & ~hidden).ravel())

    report["budget"] = budget
    report["candidate_pools"] = {
        "connector_pixels": int(connector_rows.size),
        "near_known_pixels": int(near_rows.size),
        "far_pixels": int(far_rows.size),
    }
    if connector_rows.size:
        report["emissions"]["connector_h31_01_full"] = masked_dti(connector, hidden, known)
    report["emissions"]["zone_all_full"] = masked_dti(near_known & outside_kernel & ~hidden, hidden, known)

    connector_draws = [masked_dti(sampled(connector_rows, budget, rng), hidden, known)
                       for _ in range(args.random_draws)]
    report["emissions"]["connector_h31_01"] = {
        "draws": connector_draws,
        "mean_dti": float(np.mean([d["dti"] for d in connector_draws])),
        "std_dti": float(np.std([d["dti"] for d in connector_draws])),
        "mean_tp_weight": float(np.mean([d["tp_weight"] for d in connector_draws])),
        "mean_fp_weight": float(np.mean([d["fp_weight"] for d in connector_draws])),
    }
    report["emissions"]["zone_all_matched"] = masked_dti(sampled(near_rows, budget, rng), hidden, known)
    draws = []
    for _ in range(args.random_draws):
        draws.append(masked_dti(sampled(near_rows, budget, rng), hidden, known))
    report["emissions"]["random_near_matched"] = {
        "draws": draws,
        "mean_dti": float(np.mean([d["dti"] for d in draws])),
        "std_dti": float(np.std([d["dti"] for d in draws])),
        "mean_tp_weight": float(np.mean([d["tp_weight"] for d in draws])),
        "mean_fp_weight": float(np.mean([d["fp_weight"] for d in draws])),
    }
    report["emissions"]["far_random_matched"] = masked_dti(sampled(far_rows, budget, rng), hidden, known)
    connector_row = report["emissions"]["connector_h31_01"]
    random_row = report["emissions"]["random_near_matched"]
    zone_row = report["emissions"]["zone_all_matched"]
    far_row = report["emissions"]["far_random_matched"]

    def per_pixel(row: dict) -> dict:
        emitted = max(int(row.get("emitted_pixels", budget)), 1)
        tp = row["tp_weight"] if "tp_weight" in row else row["mean_tp_weight"]
        fp = row["fp_weight"] if "fp_weight" in row else row["mean_fp_weight"]
        return {
            "credit_per_emitted_pixel": tp / emitted,
            "fp_weight_per_emitted_pixel": fp / emitted,
        }

    report["per_emitted_pixel"] = {
        "connector": per_pixel(connector_row),
        "random_near_mean": per_pixel(random_row),
        "zone_all": per_pixel(zone_row),
        "far_random": per_pixel(far_row),
    }
    gain = connector_row["mean_dti"] - random_row["mean_dti"]
    credit_ratio = (connector_row["mean_tp_weight"] / random_row["mean_tp_weight"]
                    if random_row["mean_tp_weight"] else None)
    report["gate"] = {
        "registered_question": "at a matched emitted-pixel budget, does paired-strand gap geometry earn "
                               "more hidden-truth credit than a proximity-matched random control?",
        "budget": budget,
        "connector_minus_random_near_dti": gain,
        "connector_minus_zone_all_dti": connector_row["mean_dti"] - zone_row["dti"],
        "credit_ratio_connector_over_random": credit_ratio,
        "connector_credit_per_pixel": per_pixel(connector_row)["credit_per_emitted_pixel"],
        "random_near_credit_per_pixel": per_pixel(random_row)["credit_per_emitted_pixel"],
        "passed": bool(credit_ratio is not None and credit_ratio > 1.0 and gain > 0.0),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1))
    print(json.dumps({k: report[k] for k in ("catalogue", "gate")}, indent=1))
    for name, row in report["emissions"].items():
        if "dti" in row:
            print(f"{name}: dti={row['dti']:.5f} tp={row['tp_weight']:.0f} fp={row['fp_weight']:.0f} "
                  f"emitted={row['emitted_pixels']}")
        else:
            print(f"{name}: mean_dti={row['mean_dti']:.5f} mean_tp={row['mean_tp_weight']:.0f} "
                  f"mean_fp={row['mean_fp_weight']:.0f}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
