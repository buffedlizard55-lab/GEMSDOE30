#!/usr/bin/env python3
"""Component-holdout test of H-NEARSPLAY: near-splay annulus dotted emission.

Hypothesis (registered before the run, this file):
  Hidden expert-new faults concentrate as splays and stepovers in the
  near-splay annulus (300 m - 1.5 km) around mapped traces: far enough to be
  absent from the surface-expression USGS/INGENIOUS catalogue, close enough to
  share the fault zone's damage structure. Off-catalogue dots concentrated in
  this annulus should recover withheld stand-in faults (hidden whole catalogue
  components) better than proximity-matched random off-catalogue dots and
  uniform off-catalogue dots.

Why it targets faults missing from USGS/INGENIOUS:
  The annulus excludes the catalogue itself; its inner edge is where unmapped
  splays of mapped systems sit (rules treat newly mapped geometry of an
  existing system as scorable "new fault"). Measured placement effect in this
  repo (docs/hypotheses.md H-33-01): near-slay placement 0.07234 / 0.07434 vs
  uniform 0.02674 / 0.02694 (~2.7x) on the catalogue screen.

Difference from everything implemented in this repo:
  No submission artifact or holdout in this repository emits purely from the
  300 m-1.5 km off-catalogue annulus with an inner-edge-weighted score field.
  The d2.8 family spreads dots uniformly off-catalogue (median catalogue
  distance exactly 1,500 m); this concentrates toward the inner annulus.

Layers: training labels (catalogue), template footprint — all on disk
(data/processed, data/raw). No external transfer required.

Planning prior: +0.005 to +0.020 DTI over uniform off-catalogue on the
catalogue proxy; implementation cost: low (CPU, <10 min).

Falsifiable gate (screen seed 31, confirmation seed 41):
  primary arm = inner-edge-weighted near-slay emission, budget 15,000 dots;
  must beat the count-matched distance-to-known control by >= +0.002 pooled
  DTI with paired spatial-block 95% CI lower bound above 0, in >= 3 of 4
  quadrant diagnostics, and stay pooled-positive on the fresh confirmation
  split. Failure of any clause => not promoted, no submission slot.
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

PRIMARY_ARM = "nearslay_inner_weighted"
PRIMARY_BUDGET = 15000
RADIUS_PX = int(round(RADIUS_M / PIXEL_M))  # 3 px = 300 m
INNER_PX = int(round(300.0 / PIXEL_M))      # 300 m exclusion from catalogue
OUTER_PX = int(round(1500.0 / PIXEL_M))     # 1.5 km annulus outer edge
GATE_DELTA = 0.002
BLOCK_PX = 64
DRAWS = 6


def build_zone(valid: np.ndarray, known: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Placement is keyed to distance from KNOWN (mapped) faults only: dots must
    # sit 300 m-1.5 km from mapped traces so they can fall within 300 m of a
    # WITHHeld (hidden) component without landing on mapped pixels.
    distance_to_known = distance_transform_edt(
        ~known, sampling=(PIXEL_M, PIXEL_M)
    )
    zone = valid & ~known & (distance_to_known > INNER_PX * PIXEL_M) \
        & (distance_to_known <= OUTER_PX * PIXEL_M)
    return zone, distance_to_known


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


def run_split(split_seed: int, draw_seed: int, valid: np.ndarray,
              catalogue: np.ndarray) -> dict:
    hidden, known, component_count = split_components(catalogue, seed=split_seed)
    hidden &= valid
    known &= valid
    zone, distance_to_known = build_zone(valid, known)
    emittable = valid & ~known & ~hidden
    fpw = fp_weight_field(hidden, known)

    # Inner-edge weighted score: closer to the catalogue (just outside it) is
    # more likely to hold unmapped splays; visits start at the inner edge.
    score = np.where(zone, 1.0 / np.maximum(distance_to_known, 1.0), -np.inf).astype(np.float32)

    report = {
        "split_seed": split_seed,
        "draw_seed": draw_seed,
        "components": int(component_count),
        "hidden_pixels": int(hidden.sum()),
        "known_pixels": int(known.sum()),
        "zone_pixels": int(zone.sum()),
        "arms": {},
    }
    for name in (PRIMARY_ARM, "random_near_matched", "uniform_off_catalogue"):
        entry = {"draws": []}
        rng = np.random.default_rng(draw_seed)
        for draw in range(DRAWS):
            draw_rng = np.random.default_rng(draw_seed + 1000 + draw)
            if name == PRIMARY_ARM:
                rows, cols = poisson_disk_select_ordered(
                    score, RADIUS_PX, mask=zone, limit=int(zone.sum()),
                    max_kept=PRIMARY_BUDGET,
                )
            elif name == "random_near_matched":
                ref_rows, ref_cols = poisson_disk_select_ordered(
                    score, RADIUS_PX, mask=zone, limit=int(zone.sum()),
                    max_kept=PRIMARY_BUDGET,
                )
                ref_emission = np.zeros(zone.shape, dtype=bool)
                if ref_rows.size:
                    ref_emission[ref_rows, ref_cols] = True
                target_rows = np.flatnonzero(ref_emission.ravel())
                matched = distance_matched_draw(
                    np.flatnonzero(emittable.ravel()), target_rows,
                    distance_to_known.ravel(), min(PRIMARY_BUDGET, target_rows.size),
                    rng,
                )
                emission = matched.reshape(valid.shape)
                entry["draws"].append(
                    masked_dti_by_blocks(emission.astype(np.float64), hidden, known,
                                         valid, block_size_px=BLOCK_PX, fp_weight=fpw)
                )
                continue
            else:
                rows, cols = poisson_disk_select_ordered(
                    np.ones(valid.shape, dtype=np.float32), RADIUS_PX, mask=emittable,
                    limit=int(emittable.sum()), max_kept=PRIMARY_BUDGET,
                )
            emission = np.zeros(valid.shape, dtype=bool)
            if rows.size:
                emission[rows, cols] = True
            entry["draws"].append(
                masked_dti_by_blocks(emission.astype(np.float64), hidden, known,
                                     valid, block_size_px=BLOCK_PX, fp_weight=fpw)
            )
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
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/h-nearsplay-holdout.json"))
    parser.add_argument("--screen-seed", type=int, default=31)
    parser.add_argument("--confirm-seed", type=int, default=41)
    parser.add_argument("--draw-seed", type=int, default=131)
    parser.add_argument("--confirm-draw-seed", type=int, default=231)
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & valid

    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "H-NEARSPLAY near-splay annulus dotted emission (off-catalogue)",
        "design": "component holdout (3.2 km-tile interleave, whole components); "
                  "inner-edge-weighted 300 m-1.5 km off-catalogue annulus keyed to "
                  "distance from KNOWN faults; proximity-matched and uniform "
                  "off-catalogue controls; exact masked DTI",
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
        "screen": run_split(args.screen_seed, args.draw_seed, valid, catalogue),
    }
    report["confirmation"] = run_split(args.confirm_seed, args.confirm_draw_seed, valid,
                                       catalogue)

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
