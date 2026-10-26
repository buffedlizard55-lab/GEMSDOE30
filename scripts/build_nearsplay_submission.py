#!/usr/bin/env python3
"""Build the unique GEMSDOE30 submission TIF: H-NEARSPLAY near-splay annulus.

Recipe (frozen by docs/research/h-nearsplay-holdout.json, promoted on the
catalogue-proxy component holdout):
  * Zone: valid footprint pixels off the USGS/INGENIOUS catalogue with
    300 m < distance-to-catalogue <= 1 500 m (the near-splay annulus where
    unmapped splays of mapped systems sit; scorable as newly mapped geometry
    of an existing system per DrivenData thread 11536).
  * Score field: inner-edge weighted, 1 / distance-to-catalogue, so visits
    start just outside mapped traces.
  * Emission: binary dots, Poisson-disk thinned at 3 px (300 m, the kernel
    radius), capped at 40 000 dots, off-catalogue only.
  * Output: one float32 band, 1.0 at dots, 0.0 elsewhere inside the footprint,
    NaN nodata outside — the published GEMS null/NaN-outside contract.

This is not a copy of any prior GEMSDOE artifact: every inspected submission
emits either uniformly off-catalogue (d2.8 family, median catalogue distance
1 500 m), on habitat/ridge/scarp density, or on catalogue-proximal mass. This
one concentrates off-catalogue dots in the 300 m-1.5 km annulus with an
inner-edge bias — a different spatial support.

Holdout (catalogue proxy, NOT an organizer score):
  component-holdout-v3-blockstats-20261025, buffered-quadrant whole components,
  alpha 0.2 / beta 0.8 / 300 m triangular kernel:
  screen seed 31: DTI 0.08502 vs proximity-matched control 0.01965,
  Delta +0.06537, 95% CI [0.05698, 0.07435], 4/4 quadrants, 20,870 withheld
  positives; confirmation seed 41: DTI 0.08788 vs 0.01994, Delta +0.06794,
  95% CI [0.05898, 0.07724], 4/4 quadrants, 20,247 withheld positives.
  Verdict: promoted on holdout. Not ORGANIZER-CONFIRMED; no organizer receipt
  exists and no competition slot has been used.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.submission import write_submission_file  # noqa: E402

MAX_DOTS = 40000
RADIUS_PX = 3  # 300 m kernel radius
INNER_PX = 3  # 300 m
OUTER_PX = 15  # 1.5 km


def main() -> int:
    import rasterio

    template_path = ROOT / "data/raw/sample_submission.tif"
    labels_path = ROOT / "data/raw/labels.tif"
    with rasterio.open(template_path) as template:
        raw = template.read(1, masked=False)
        valid_mask = np.isfinite(raw)
        height, width = template.height, template.width
        transform = template.transform
        crs = template.crs
    with rasterio.open(labels_path) as ds:
        labels = ds.read(1, masked=False)
    catalogue = (np.asarray(labels) == 1.0) & valid_mask

    distance_to_catalogue = distance_transform_edt(
        ~catalogue, sampling=(100.0, 100.0)
    )
    zone = valid_mask & ~catalogue \
        & (distance_to_catalogue > INNER_PX * 100.0) \
        & (distance_to_catalogue <= OUTER_PX * 100.0)

    # Inner-edge weighted: visits start just outside mapped traces, where
    # unmapped splays are most likely.
    score = np.where(
        zone, 1.0 / np.maximum(distance_to_catalogue, 1.0), -np.inf
    ).astype(np.float32)

    rows, cols = poisson_disk_select_ordered(
        score, RADIUS_PX, mask=zone, limit=int(zone.sum()), max_kept=MAX_DOTS,
    )
    dots = np.zeros((height, width), dtype=bool)
    if rows.size:
        dots[rows, cols] = True
    print(f"Selected {int(dots.sum())} dots in the near-splay annulus zone "
          f"({int(zone.sum())} eligible pixels).")

    probabilities = np.zeros((height, width), dtype=np.float32)
    probabilities[dots & valid_mask] = 1.0
    # Outside the footprint stays the default NaN nodata written by the shared
    # writer; inside the footprint, non-dot cells are exactly 0.0.

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    array_digest = hashlib.sha256(np.ascontiguousarray(probabilities).tobytes()).hexdigest()[:8]
    slug = "nearslay-annulus-d3-offcat"
    run_name = f"GEMSDOE30-{slug}-{timestamp}-{array_digest}-nan"
    note = (
        "NEARSPLAY annulus 300m-1.5km off-cat dots; holdout DTI +0.066 "
        "[0.057,0.074] vs matched control; proxy holdout, not org-confirmed"
    )
    if len(note) > 140:
        raise ValueError(f"note is {len(note)} chars, over the 140 limit")

    output_path = ROOT / "docs/downloads" / f"{run_name}.tif"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = write_submission_file(
        probabilities,
        template_path,
        output_path,
        note=note,
        run_name=run_name,
        outside_value=float("nan"),
    )

    # Uniqueness vs every locally available registry raster.
    from scipy.stats import spearmanr

    reference_tiffs = []
    for directory in (ROOT / "docs/downloads", ROOT / "data/raw/scored"):
        if directory.is_dir():
            reference_tiffs.extend(sorted(directory.glob("*.tif")))
    reference_tiffs = [p for p in reference_tiffs
                       if p != output_path and "nearslay" not in p.name]

    def raster_dots(path: Path) -> np.ndarray:
        with rasterio.open(path) as ds:
            data = ds.read(1, masked=False)
        return (np.asarray(data) > 0.5) & np.isfinite(np.asarray(data))

    my_dots = dots
    my_dist = distance_transform_edt(~my_dots, sampling=(100.0, 100.0)) if my_dots.any() \
        else np.full(my_dots.shape, np.inf)
    uniqueness = []
    for ref_path in reference_tiffs:
        try:
            ref_dots = raster_dots(ref_path)
        except Exception as exc:  # noqa: BLE001 - report, do not stop the build
            uniqueness.append({"file": ref_path.name, "error": str(exc)})
            continue
        ref_dist = distance_transform_edt(~ref_dots, sampling=(100.0, 100.0)) \
            if ref_dots.any() else np.full(ref_dots.shape, np.inf)
        within_3px = int(np.count_nonzero(my_dots & (ref_dist <= 300.0)))
        fraction = within_3px / max(int(my_dots.sum()), 1)
        # Rank correlation over the overlapping finite footprint of both rasters.
        with rasterio.open(ref_path) as ds:
            ref_data = ds.read(1, masked=False)
        if ref_data.shape == probabilities.shape:
            finite = np.isfinite(probabilities) & np.isfinite(ref_data)
            if finite.sum() > 1000:
                rho = float(spearmanr(
                    probabilities[finite].ravel(), ref_data[finite].ravel()
                ).statistic)
            else:
                rho = None
        else:
            rho = None
        uniqueness.append({
            "file": ref_path.name,
            "my_dots_within_3px_of_reference": within_3px,
            "fraction_of_my_dots_within_3px": float(fraction),
            "spearman_rho_full_raster": rho,
        })
    max_overlap = max((u["fraction_of_my_dots_within_3px"] for u in uniqueness
                       if isinstance(u.get("fraction_of_my_dots_within_3px"), float)),
                      default=0.0)
    max_rho = max((u["spearman_rho_full_raster"] for u in uniqueness
                   if isinstance(u.get("spearman_rho_full_raster"), float)),
                  default=0.0)
    uniqueness_summary = {
        "max_fraction_within_3px_vs_any_reference": float(max_overlap),
        "max_spearman_rho_vs_any_reference": float(max_rho),
        "lane_collision": bool(max_overlap > 0.70 or max_rho > 0.90),
        "references_compared": len(uniqueness),
    }
    print(json.dumps(uniqueness_summary, indent=2))

    sidecar = output_path.with_suffix(".json")
    payload = json.loads(sidecar.read_text()) if sidecar.exists() else {}
    payload["uniqueness_vs_local_registry"] = uniqueness_summary
    payload["uniqueness_details"] = uniqueness
    payload["holdout"] = {
        "evaluator_version": "component-holdout-v3-blockstats-20261025",
        "protocol": "buffered-quadrant-whole-components-v1-20261025",
        "kernel": "triangular 300 m, alpha=0.2, beta=0.8",
        "screen_seed_31": {
            "dti": 0.08502081258697522,
            "control_dti": 0.019653522940025436,
            "delta": 0.06536728964694978,
            "ci95": [0.056983238130653695, 0.07434696611947941],
            "withheld_positives": 20870,
            "quadrants": "4/4",
        },
        "confirmation_seed_41": {
            "dti": 0.0878801185469148,
            "control_dti": 0.019941819710194774,
            "delta": 0.06793829883672002,
            "ci95": [0.05897694667908524, 0.07724278724681792],
            "withheld_positives": 20247,
            "quadrants": "4/4",
        },
        "verdict": "promoted on catalogue-proxy holdout; NOT ORGANIZER-CONFIRMED",
    }
    payload["submission_name"] = run_name
    payload["note"] = note
    payload["note_length"] = len(note)
    sidecar.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Re-validate the written bytes from disk (fail-closed).
    from gemsdoe30.submission import validate_submission_file  # noqa: E402
    report = validate_submission_file(output_path, template_path)
    print(json.dumps(report.to_dict(), indent=2))
    if not report.passed:
        print("SUBMISSION BUILD BLOCKED: written TIFF failed format validation",
              file=sys.stderr)
        return 2
    print(f"\nGeoTIFF file: {output_path}")
    print(f"SHA-256: {manifest['output_sha256']}")
    print(f"Note ({len(note)}/140 chars): {note}")
    print(f"Published format compliant: {manifest['published_format_compliant']}")
    print(f"Lane collision vs local registry: {uniqueness_summary['lane_collision']}")
    if uniqueness_summary["lane_collision"]:
        print("WARNING: lane-collision thresholds crossed; do not treat as unique.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
