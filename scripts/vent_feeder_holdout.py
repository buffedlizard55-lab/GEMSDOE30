#!/usr/bin/env python3
"""Component-holdout test of H-VENT: volcanic-vent feeder alignment.

Hypothesis (registered before the run, this file):
  Quaternary volcanic vents and flows mark feeder fissures that are absent from
  the USGS/INGENIOUS surface-fault catalogue (measured: only 615 of 6,776
  vent pixels, ~9%, lie within 300 m of a catalogue trace; vents' median
  distance to catalogue is ~1.6 km). Dots aligned with volcanics, emitted
  off-catalogue only, should recover hidden stand-in faults (withheld whole
  catalogue components) better than proximity-matched random off-catalogue dots
  and uniform off-catalogue dots.

Why it targets faults missing from USGS/INGENIOUS:
  Volcanic feeder fissures are blind or young structures with little or no
  surface rupture; a surface-expression catalogue structurally cannot contain
  them. Measured 0/21 inventoried vents lie within 300 m of a catalogue trace
  (docs/hypotheses.md H-32-02), so the feeder population is essentially
  uncatalogued.

Difference from everything implemented in this repo:
  No holdout script, feature stack or submitted artifact in this repository or
  on the inspected GEMSDOE pages uses volcanic vents/flows at all (H-32-02 was
  registered but never executed here). All existing arms use scalar geophysical
  fields, LiDAR scarps, springs/geochemistry, strain or catalogue geometry.

Layers: data/external/derived_gdr_volcanics_100m_u8.tif (Quaternary volcanics,
GDR 1391, CC BY 4.0; on disk and hash-recorded in data/external/external_receipt.json).
Signature: dots aligned with volcanics (dilated 300 m = one kernel radius),
Poisson-disk thinned at 3 px (300 m), binary, off-catalogue only.

Planning prior: +0.001 to +0.010 DTI (low statistical power, n=21 vents);
implementation cost: low (all data on disk, CPU, <10 min).

Falsifiable gate (screen seed 31, confirmation seed 41):
  primary arm = vent-aligned emission, budget 15,000 dots; must beat the
  count-matched distance-to-known control by >= +0.002 pooled DTI with the
  paired spatial-block 95% CI lower bound above 0, in >= 3 of 4 quadrant
  diagnostics, and stay pooled-positive on the fresh confirmation split.
  Failure of any clause => not promoted, no submission slot. Negative results
  are deliverables: a catalogue holdout is a biased proxy for uncatalogued
  faults (IR-30-017), so a negative proxy is expected and reported honestly.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.holdout import (  # noqa: E402
    ALPHA,
    PIXEL_M,
    RADIUS_M,
    distance_matched_draw,
    fp_weight_field,
    masked_dti_by_blocks,
    split_components,
    spatial_bootstrap,
)
from gemsdoe30.emission import dti_from_components, poisson_disk_select_ordered  # noqa: E402

PRIMARY_ARM = "vent_aligned"
PRIMARY_BUDGET = 15000
RADIUS_PX = int(round(RADIUS_M / PIXEL_M))  # 3 px = 300 m
GATE_DELTA = 0.002
BLOCK_PX = 64
DRAWS = 6


def load_volcanics(path: Path, shape: tuple[int, int]) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as ds:
        array = ds.read(1, masked=False)
    if array.shape != shape:
        raise ValueError(f"volcanics shape {array.shape} != grid {shape}")
    return np.asarray(array, dtype=np.float32) > 0.5


def dilate(zone: np.ndarray, radius_px: int) -> np.ndarray:
    if not zone.any() or radius_px <= 0:
        return zone.copy()
    distance = distance_transform_edt(~zone, sampling=(PIXEL_M, PIXEL_M))
    return distance <= radius_px * PIXEL_M


def quadrant_positive(quad_a: dict, quad_c: dict) -> tuple[int, int]:
    positive = total = 0
    for key in quad_a:
        if not key.startswith("quadrant_"):
            continue
        a = quad_a[key].get("dti", float("nan"))
        c = quad_c[key].get("dti", float("nan"))
        if np.isfinite(a) and np.isfinite(c):
            total += 1
            positive += int(a > c)
    return positive, total


def summarize_blocks(rows: list[dict]) -> dict:
    tp = float(sum(r["tp_weight"] for r in rows))
    fp = float(sum(r["fp_weight"] for r in rows))
    truth = float(sum(r["truth_pixels"] for r in rows))
    return {"tp_weight": tp, "fp_weight": fp, "truth_pixels": truth,
            "dti": dti_from_components(tp, fp, truth, alpha=ALPHA)}


def emit_vent_aligned(zone: np.ndarray, vent_score: np.ndarray, budget: int,
                      rng: np.random.Generator) -> np.ndarray:
    rows, cols = poisson_disk_select_ordered(
        vent_score, RADIUS_PX, mask=zone, limit=int(zone.sum()), max_kept=budget,
    )
    emission = np.zeros(zone.shape, dtype=bool)
    if rows.size:
        emission[rows, cols] = True
    return emission


def run_split(split_seed: int, draw_seed: int, catalogues: dict) -> dict:
    catalogue = catalogues["catalogue"]
    valid = catalogues["valid"]
    hidden, known, component_count = split_components(catalogue, seed=split_seed)
    hidden &= valid
    known &= valid
    distance_to_known = distance_transform_edt(~known, sampling=(PIXEL_M, PIXEL_M))
    emittable = valid & ~known & ~hidden

    volcanics = load_volcanics(catalogues["volcanics_path"], valid.shape)
    zone = dilate(volcanics, RADIUS_PX) & emittable

    fpw = fp_weight_field(hidden, known)

    vent_distance = distance_transform_edt(~volcanics, sampling=(PIXEL_M, PIXEL_M))
    vent_score = np.where(zone, -vent_distance, -np.inf).astype(np.float32)

    report = {
        "split_seed": split_seed,
        "draw_seed": draw_seed,
        "components": int(component_count),
        "hidden_pixels": int(hidden.sum()),
        "known_pixels": int(known.sum()),
        "vent_pixels": int(volcanics.sum()),
        "zone_pixels": int(zone.sum()),
        "arms": {},
    }
    for name in (PRIMARY_ARM, "random_near_matched", "uniform_off_catalogue"):
        entry = {"draws": []}
        rng = np.random.default_rng(draw_seed)
        for draw in range(DRAWS):
            if name == PRIMARY_ARM:
                draw_rng = np.random.default_rng(draw_seed + 1000 + draw)
                emission = emit_vent_aligned(zone, vent_score, PRIMARY_BUDGET, draw_rng)
            elif name == "random_near_matched":
                pool_rows = np.flatnonzero(zone.ravel())
                reference = emit_vent_aligned(zone, vent_score, PRIMARY_BUDGET, rng)
                target_rows = np.flatnonzero(reference.ravel())
                matched = distance_matched_draw(
                    np.flatnonzero(emittable.ravel()), pool_rows,
                    distance_to_known.ravel(), min(PRIMARY_BUDGET, pool_rows.size),
                    rng,
                )
                emission = matched.reshape(valid.shape)
            else:
                rows, cols = poisson_disk_select_ordered(
                    np.ones(valid.shape, dtype=np.float32), RADIUS_PX, mask=emittable,
                    limit=int(emittable.sum()), max_kept=PRIMARY_BUDGET,
                )
                emission = np.zeros(valid.shape, dtype=bool)
                if rows.size:
                    emission[rows, cols] = True
            stats = masked_dti_by_blocks(
                emission.astype(np.float64), hidden, known, valid,
                block_size_px=BLOCK_PX, fp_weight=fpw,
            )
            entry["draws"].append(stats)
        all_blocks = [b for d in entry["draws"] for b in d.get("spatial_blocks", [])]
        entry["pooled"] = summarize_blocks(all_blocks)
        report["arms"][name] = entry

    comparisons = {
        name: [b for d in spec["draws"] for b in d.get("spatial_blocks", [])]
        for name, spec in report["arms"].items()
    }
    keys = {(b["block_row"], b["block_col"]) for b in comparisons[PRIMARY_ARM]}
    if all({(b["block_row"], b["block_col"]) for b in rows} == keys
           for rows in comparisons.values()):
        bootstrap = spatial_bootstrap(comparisons, candidate=PRIMARY_ARM,
                                      replicates=2000, seed=3071)
    else:
        bootstrap = {"note": "block inventories differ across arms; bootstrap skipped"}

    first = {name: spec["draws"][0] for name, spec in report["arms"].items()}
    qpos, qtot = quadrant_positive(first[PRIMARY_ARM], first["random_near_matched"])

    candidate = report["arms"][PRIMARY_ARM]["pooled"]["dti"]
    control = report["arms"]["random_near_matched"]["pooled"]["dti"]
    delta_point = candidate - control
    delta_ci = bootstrap.get("candidate_minus", {}).get("random_near_matched", {}).get(
        "ci95", [float("nan"), float("nan")]) if isinstance(bootstrap, dict) \
        else [float("nan"), float("nan")]

    screen_pass = bool(
        delta_point >= GATE_DELTA
        and np.isfinite(delta_ci[0]) and float(delta_ci[0]) > 0
        and qpos >= 3 and qtot > 0,
    )
    report["gate_result"] = {
        "primary_arm": PRIMARY_ARM,
        "primary_budget": PRIMARY_BUDGET,
        "required_delta_vs_random_near_matched": GATE_DELTA,
        "required_quadrant_sign_consistency": "3 of 4",
        "screen_pooled_dti_candidate": float(candidate),
        "screen_pooled_dti_control": float(control),
        "screen_point_delta": float(delta_point),
        "screen_delta_ci95": [float(x) for x in delta_ci],
        "quadrants_candidate_above_control": f"{qpos}/{qtot}",
        "screen_pass": screen_pass,
        "confirmation_pass": None,
        "promoted": False,
        "note": "catalogue-proxy holdout only; not a competition score. Negative results are deliverables.",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--volcanics", type=Path,
                        default=Path("data/external/derived_gdr_volcanics_100m_u8.tif"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/h-vent-feeder-holdout.json"))
    parser.add_argument("--screen-seed", type=int, default=31)
    parser.add_argument("--confirm-seed", type=int, default=41)
    parser.add_argument("--draw-seed", type=int, default=131)
    parser.add_argument("--confirm-draw-seed", type=int, default=231)
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & valid
    catalogues = {
        "catalogue": catalogue,
        "valid": valid,
        "volcanics_path": args.volcanics,
    }

    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "H-VENT volcanic-vent feeder alignment (off-catalogue dotted emission)",
        "design": "component holdout (3.2 km-tile interleave, whole components); "
                  "volcanics zone from GDR 1391 raster only; proximity-matched and "
                  "uniform off-catalogue controls; exact masked DTI on hidden components",
        "metric": {"radius_m": RADIUS_M, "alpha": ALPHA, "pixel_m": PIXEL_M,
                   "kernel": "triangular 300 m"},
        "gate": {
            "primary_arm": PRIMARY_ARM,
            "primary_budget": PRIMARY_BUDGET,
            "required_pooled_delta_vs_control": GATE_DELTA,
            "required_quadrant_sign_consistency": "3 of 4",
            "confirmation": "pooled-positive on fresh split seed 41 with fresh draws",
        },
        "params": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "screen": run_split(args.screen_seed, args.draw_seed, catalogues),
    }
    report["confirmation"] = run_split(args.confirm_seed, args.confirm_draw_seed, catalogues)

    g_screen = report["screen"]["gate_result"]
    g_confirm = report["confirmation"]["gate_result"]
    promoted = bool(g_screen["screen_pass"] and g_confirm["screen_pass"])
    report["verdict"] = {
        "screen_pass": g_screen["screen_pass"],
        "confirmation_pass": g_confirm["screen_pass"],
        "promoted": promoted,
        "note": "catalogue-proxy holdout only; not a competition score",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["verdict"], indent=2))
    print(json.dumps(g_screen, indent=2))
    print(json.dumps(g_confirm, indent=2))
    print(f"Full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
