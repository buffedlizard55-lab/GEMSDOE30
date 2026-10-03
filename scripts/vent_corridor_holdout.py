#!/usr/bin/env python3
"""Component-holdout test of H-32-01: do geothermal-discharge corridors carry
information about faults that the USGS/INGENIOUS catalogue does not?

Design (frozen in docs/research/h32-01-preregistration.md before this run)
------------------------------------------------------------------------
1. Split the catalogue into 8-connected components and assign whole components to
   a hidden half and a known half using the deterministic 3.2 km-tile interleave
   (gemsdoe30.holdout.split_components). Hidden = stand-in "new faults"; known is
   masked exactly as the organizer masks USGS/INGENIOUS pixels.
2. Candidate zones are built from spring/vent data ONLY (never from catalogue
   geometry): buffer zones of R px around hot-spring cells (temp_c >= 60 C,
   deduplicated per grid cell keeping the maximum temperature) and alignment
   corridors between hot-cell pairs separated by 2-8 km.
3. Controls, all scored on the same masked domain with the same hidden truth:
   * `random_near_matched` - draws from the whole non-truth footprint whose
     distance-to-known-fault profile matches the target zone's (this removes the
     generic "near mapped faults" proximity prior measured at ~2.3x in the relay
     experiment);
   * `far_random` - uniform draws from the footprint (unmatched proximity).
4. Predictions are binary emissions at matched pixel budgets; the exact published
   index runs on the masked domain (truth = hidden components only).

Registered gate (see the preregistration document): the primary arm (hot-spring
buffer, R = 10 px = 1 km, budget 15,000 px) must beat `random_near_matched` by
>= +0.002 pooled DTI on the screen split (seed 31) with >= 3 of 4 quadrant
diagnostics positive, and stay pooled-positive on the fresh confirmation split
(seed 41, fresh draws). Failure of any clause => not promoted, no submission slot.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.holdout import (  # noqa: E402
    ALPHA,
    PIXEL_M,
    RADIUS_M,
    distance_matched_draw,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    split_components,
)

PRIMARY_ARM = "spring_buf_r10"
PRIMARY_BUDGET = 15000
GATE_DELTA = 0.002


def load_hot_cells(csv_path: Path, shape: tuple[int, int], threshold: float) -> np.ndarray:
    """Deduplicated hot-spring grid cells (row, col) at or above ``threshold`` °C."""

    best: dict[tuple[int, int], float] = {}
    with csv_path.open() as handle:
        for row in csv.DictReader(handle):
            try:
                temp = float(row["temp_c"])
            except (KeyError, ValueError, TypeError):
                continue
            cell = (int(row["row"]), int(row["col"]))
            if not (0 <= cell[0] < shape[0] and 0 <= cell[1] < shape[1]):
                continue
            if cell not in best or temp > best[cell]:
                best[cell] = temp
    cells = np.array([c for c, t in best.items() if t >= threshold], dtype=np.int64)
    return cells.reshape(-1, 2)


def rasterize_cells(cells: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    if cells.size:
        mask[cells[:, 0], cells[:, 1]] = True
    return mask


def dilate_cells(cells: np.ndarray, shape: tuple[int, int], radius_px: int) -> np.ndarray:
    zone = rasterize_cells(cells, shape)
    if not cells.size or radius_px <= 0:
        return zone
    distance = distance_transform_edt(~zone, sampling=(PIXEL_M, PIXEL_M))
    return distance <= radius_px * PIXEL_M


def corridor_zone(cells: np.ndarray, shape: tuple[int, int], *,
                  min_sep_m: float, max_sep_m: float, buffer_px: int) -> np.ndarray:
    """Union of straight segments joining hot-cell pairs 2-8 km apart, buffered."""

    zone = np.zeros(shape, dtype=bool)
    if cells.size < 2:
        return zone
    xy = np.stack([cells[:, 0] * PIXEL_M, cells[:, 1] * PIXEL_M], axis=1)
    tree = cKDTree(xy)
    pairs = tree.query_pairs(r=max_sep_m, output_type="ndarray")
    if pairs.size == 0:
        return zone
    delta = xy[pairs[:, 0]] - xy[pairs[:, 1]]
    sep = np.hypot(delta[:, 0], delta[:, 1])
    keep = (sep >= min_sep_m) & (sep <= max_sep_m)
    pairs = pairs[keep]
    for a, b in pairs:
        r0, c0 = cells[a]
        r1, c1 = cells[b]
        steps = max(abs(int(r1 - r0)), abs(int(c1 - c0)), 1)
        for s in range(steps + 1):
            rr = int(round(r0 + (r1 - r0) * s / steps))
            cc = int(round(c0 + (c1 - c0) * s / steps))
            r_lo, r_hi = max(0, rr - buffer_px), min(shape[0], rr + buffer_px + 1)
            c_lo, c_hi = max(0, cc - buffer_px), min(shape[1], cc + buffer_px + 1)
            zone[r_lo:r_hi, c_lo:c_hi] = True
    return zone


def sampled(mask_pool: np.ndarray, budget: int, rng: np.random.Generator) -> np.ndarray:
    emission = np.zeros(mask_pool.shape, dtype=bool)
    rows = np.flatnonzero(mask_pool.ravel())
    if rows.size == 0 or budget <= 0:
        return emission
    take = min(budget, rows.size)
    pick = rng.choice(rows, size=take, replace=False)
    emission.ravel()[pick] = True
    return emission


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--springs", type=Path, default=Path("data/external/gdr_wellspring_in_footprint.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/h32-01-vent-corridor-holdout.json"))
    parser.add_argument("--split-seed", type=int, default=31, help="screen split seed (confirmation uses --confirm-split-seed)")
    parser.add_argument("--confirm-split-seed", type=int, default=41)
    parser.add_argument("--draw-seed", type=int, default=131)
    parser.add_argument("--confirm-draw-seed", type=int, default=231)
    parser.add_argument("--draws", type=int, default=6)
    parser.add_argument("--budgets", type=int, nargs="*", default=[5000, 15000, 45000])
    parser.add_argument("--threshold-c", type=float, default=60.0)
    parser.add_argument("--confirm-threshold-c", type=float, default=100.0,
                        help="hot-cell threshold (°C) for the confirmation split's sensitivity arm")
    parser.add_argument("--screen-only", action="store_true",
                        help="run a single split (used for supplementary sensitivity runs)")
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & valid
    shape = valid.shape

    def run_split(split_seed: int, draw_seed: int, threshold_c: float) -> dict:
        hidden, known, component_count = split_components(catalogue, seed=split_seed)
        hidden &= valid
        known &= valid
        distance_to_known = distance_transform_edt(~known, sampling=(PIXEL_M, PIXEL_M))
        hot_cells = load_hot_cells(args.springs, shape, threshold_c)
        zones = {
            "spring_buf_r3": dilate_cells(hot_cells, shape, 3),
            "spring_buf_r10": dilate_cells(hot_cells, shape, 10),
            "spring_buf_r20": dilate_cells(hot_cells, shape, 20),
            "spring_corr_2_8km": corridor_zone(hot_cells, shape, min_sep_m=2000.0, max_sep_m=8000.0, buffer_px=3),
        }
        # Never emit on truth or masked pixels; pools are the emittable support.
        emittable = valid & ~known & ~hidden
        fpw = fp_weight_field(hidden, known)
        rng = np.random.default_rng(draw_seed)
        far_rows = np.flatnonzero(emittable.ravel())
        result: dict = {
            "split_seed": split_seed,
            "draw_seed": draw_seed,
            "threshold_c": threshold_c,
            "components": int(component_count),
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "hot_cells": int(hot_cells.shape[0]),
            "arms": {},
        }
        for name, zone in zones.items():
            pool = zone & emittable
            pool_rows = np.flatnonzero(pool.ravel())
            entry: dict = {"pool_pixels": int(pool_rows.size)}
            for budget in args.budgets:
                arm_draws = []
                control_draws = []
                far_draws = []
                for _ in range(args.draws):
                    arm_draws.append(masked_dti(sampled(pool, budget, rng), hidden, known, fp_weight=fpw))
                    matched = distance_matched_draw(
                        far_rows, pool_rows, distance_to_known.ravel(), min(budget, pool_rows.size), rng)
                    emission = matched.reshape(shape)
                    control_draws.append(masked_dti(emission, hidden, known, fp_weight=fpw))
                    far_draws.append(masked_dti(sampled(emittable, min(budget, pool_rows.size), rng), hidden, known, fp_weight=fpw))

                def summarize(draws: list[dict]) -> dict:
                    dtis = [d["dti"] for d in draws if np.isfinite(d["dti"])]
                    return {
                        "mean_dti": float(np.mean(dtis)) if dtis else float("nan"),
                        "std_dti": float(np.std(dtis)) if dtis else float("nan"),
                        "mean_tp_weight": float(np.mean([d["tp_weight"] for d in draws])),
                        "mean_fp_weight": float(np.mean([d["fp_weight"] for d in draws])),
                        "mean_hidden_credit_fraction": float(np.mean([d.get("hidden_credit_fraction", float("nan")) for d in draws])),
                        "draws": draws,
                    }

                entry[str(budget)] = {
                    "spring": summarize(arm_draws),
                    "random_near_matched": summarize(control_draws),
                    "far_random": summarize(far_draws),
                }
            if name == PRIMARY_ARM:
                quad_spring = [masked_dti_by_blocks(sampled(pool, PRIMARY_BUDGET, rng), hidden, known, valid, fp_weight=fpw)
                               for _ in range(args.draws)]
                quad_control = []
                for _ in range(args.draws):
                    matched = distance_matched_draw(
                        far_rows, pool_rows, distance_to_known.ravel(), min(PRIMARY_BUDGET, pool_rows.size), rng)
                    quad_control.append(masked_dti_by_blocks(matched.reshape(shape), hidden, known, valid, fp_weight=fpw))

                def quad_means(draws: list[dict]) -> dict:
                    out: dict = {}
                    for key in draws[0]:
                        values = [d[key]["dti"] for d in draws if key in d and np.isfinite(d[key].get("dti", float("nan")))]
                        out[key] = {"mean_dti": float(np.mean(values)) if values else float("nan"),
                                    "n_draws": len(values)}
                    return out

                entry["quadrant_diagnostics"] = {
                    "note": "per-quadrant DTI keeps cross-quadrant 300 m credit; diagnostic only",
                    "spring": quad_means(quad_spring),
                    "random_near_matched": quad_means(quad_control),
                }
            result["arms"][name] = entry
        return result

    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "H-32-01 geothermal-discharge corridors (hot-spring clusters)",
        "design": "component holdout (3.2 km-tile interleave); zones from spring data only; "
                  "proximity-matched controls; exact masked DTI on hidden components",
        "metric": {"radius_m": RADIUS_M, "alpha": ALPHA, "pixel_m": PIXEL_M},
        "gate": {
            "primary_arm": PRIMARY_ARM,
            "primary_budget": PRIMARY_BUDGET,
            "required_pooled_delta_vs_random_near_matched": GATE_DELTA,
            "required_quadrant_sign_consistency": "3 of 4",
            "confirmation": "pooled-positive on fresh split seed 41 with fresh draws",
        },
        "params": vars(args) | {"springs": str(args.springs), "data_dir": str(args.data_dir),
                                "output": str(args.output)},
        "screen": run_split(args.split_seed, args.draw_seed, args.threshold_c),
    }
    if args.screen_only:
        report["confirmation"] = {"note": "skipped (--screen-only)"}
    else:
        # Confirmation: fresh split + fresh draws at the primary threshold, plus the
        # preregistered ≥100 °C sensitivity arm on the same fresh split.
        report["confirmation"] = run_split(args.confirm_split_seed, args.confirm_draw_seed, args.threshold_c)
        report["confirmation_sensitivity_threshold_c"] = run_split(
            args.confirm_split_seed, args.confirm_draw_seed, args.confirm_threshold_c)

    # Registered gate evaluation (screen + confirmation).
    def pooled(arm: dict, budget: int, key: str) -> float:
        return arm[str(budget)][key]["mean_dti"]

    screen_arm = report["screen"]["arms"][PRIMARY_ARM]
    delta_screen = pooled(screen_arm, PRIMARY_BUDGET, "spring") - pooled(screen_arm, PRIMARY_BUDGET, "random_near_matched")
    if args.screen_only:
        confirm_arm = None
        delta_confirm = float("nan")
    else:
        confirm_arm = report["confirmation"]["arms"][PRIMARY_ARM]
        delta_confirm = pooled(confirm_arm, PRIMARY_BUDGET, "spring") - pooled(confirm_arm, PRIMARY_BUDGET, "random_near_matched")
    quads = screen_arm.get("quadrant_diagnostics", {})
    quad_positive = 0
    quad_total = 0
    for key, value in quads.get("spring", {}).items():
        if not key.startswith("quadrant_"):
            continue
        control_value = quads.get("random_near_matched", {}).get(key, {}).get("mean_dti", float("nan"))
        arm_value = value.get("mean_dti", float("nan"))
        if np.isfinite(arm_value) and np.isfinite(control_value):
            quad_total += 1
            quad_positive += int(arm_value > control_value)
    quad_ok = quad_total > 0 and quad_positive >= 3
    report["gate_result"] = {
        "screen_pooled_delta": float(delta_screen),
        "confirmation_pooled_delta": float(delta_confirm),
        "quadrants_spring_above_matched_control": f"{quad_positive}/{quad_total}",
        "screen_pass": bool(delta_screen >= GATE_DELTA),
        "quadrant_pass": bool(quad_ok),
        "confirmation_pass": bool(delta_confirm > 0) if not args.screen_only else None,
        "promoted": (bool(delta_screen >= GATE_DELTA and quad_ok and delta_confirm > 0)
                     if not args.screen_only else False),
        "note": "catalogue-proxy holdout only; not a competition score",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["gate_result"], indent=2))
    print(f"Full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
