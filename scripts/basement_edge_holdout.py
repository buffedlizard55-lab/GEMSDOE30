#!/usr/bin/env python3
"""Component-holdout test of H-32-05: do buried range-front pinch-out edges in the
depth-to-basement surface carry information about faults the catalogue does not?

Design and gate are frozen in docs/research/h32-05-preregistration.md (read it first).
Nothing in this file may be retuned after the fact without a new preregistration.

Physical target
---------------
A normal fault offsetting basin fill against crystalline basement leaves an abrupt
step in the depth-to-basement surface even where the ground surface is flat and the
trace is unmappable. The arms therefore target the *edge* of that surface, with
structure-tensor coherence to require an oriented (linear) feature, corroborated by
an independent density-contrast edge field (|iso_grav_anom_hg|).

Controls, scored on the same masked domain with the same hidden truth
--------------------------------------------------------------------
* ``dbs_magnitude``      - top-N of the basement-depth *value*, not its edge. This is
                           how every prior use of the band worked; the primary arm
                           must beat it or the transform is not doing the work.
* ``basement_edge_only`` - top-N of the edge alone (corroboration ablation).
* ``grav_edge_only``     - top-N of |iso_grav_anom_hg| alone (basement ablation).
* ``random_near_matched``- count-matched draws whose distance-to-known-fault profile
                           matches the primary arm's (removes generic proximity).
* ``far_random``         - count-matched uniform draws (unmatched baseline).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import (
    distance_transform_edt,
    median_filter,
    sobel,
    uniform_filter,
)

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

PRIMARY_ARM = "basement_edge_corroborated"
PRIMARY_BUDGET = 15000
GATE_DELTA = 0.002
COHERENCE_FLOOR = 0.5
BAND_DEPTH = "depth_to_base_surf"
BAND_GRAV_HG = "iso_grav_anom_hg"


def band_index(manifest: dict, name: str) -> int:
    """Resolve a band short name to its 0-based channel index in the prepared array."""

    names = manifest["feature_band_names"]
    for index, description in enumerate(names):
        if description.split(" - ")[0].strip() == name:
            return index
    raise KeyError(f"band {name!r} not in prepared manifest")


def edge_fields(features: np.ndarray, depth_index: int, grav_index: int, footprint: np.ndarray):
    """Median-filtered basement-surface edge, structure-tensor coherence, gravity edge."""

    depth = np.array(features[depth_index], dtype=np.float64)
    finite = footprint & np.isfinite(depth)
    if not finite.any():
        raise ValueError("depth_to_base_surf has no finite values inside the footprint")
    fill = float(np.median(depth[finite]))
    filled = np.where(np.isfinite(depth), depth, fill)
    smooth = median_filter(filled, size=3, mode="nearest")

    gx = sobel(smooth, axis=1, mode="nearest")
    gy = sobel(smooth, axis=0, mode="nearest")
    dbs_edge = np.hypot(gx, gy)
    dbs_edge[~footprint] = 0.0

    jxx = uniform_filter(gx * gx, size=3, mode="nearest")
    jyy = uniform_filter(gy * gy, size=3, mode="nearest")
    jxy = uniform_filter(gx * gy, size=3, mode="nearest")
    trace = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(trace * trace - 4.0 * det, 0.0))
    lam1 = 0.5 * (trace + disc)
    lam2 = 0.5 * (trace - disc)
    coherence = (lam1 - lam2) / (trace + 1e-9)
    coherence[~footprint] = 0.0

    grav = np.array(features[grav_index], dtype=np.float64)
    grav_edge = np.abs(np.where(np.isfinite(grav), grav, 0.0))
    grav_edge[~footprint] = 0.0

    return dbs_edge, coherence, grav_edge, finite


def descending_rank(field: np.ndarray, support: np.ndarray) -> np.ndarray:
    """0-based rank by descending value inside ``support``; +inf outside it.

    Deterministic: ties are broken by flat index because ``np.lexsort`` is keyed on
    (flat index, negated value), so identical values order by ascending index.
    """

    rank = np.full(field.size, np.inf, dtype=np.float64)
    idx = np.flatnonzero(support.ravel())
    if idx.size == 0:
        return rank.reshape(field.shape)
    values = field.ravel()[idx]
    # Negate so that the largest value gets rank 1; the index term only breaks exact ties.
    order = np.lexsort((idx, -values))
    rank[idx[order]] = np.arange(idx.size, dtype=np.float64)
    return rank.reshape(field.shape)


def top_n_emission(score: np.ndarray, support: np.ndarray, count: int) -> np.ndarray:
    """Deterministic top-``count`` pixels of ``score`` (lower is better) inside ``support``."""

    flat_score = np.where(support.ravel(), score.ravel(), np.inf)
    take = min(int(count), int(np.isfinite(flat_score).sum()))
    emission = np.zeros(flat_score.size, dtype=bool)
    if take <= 0:
        return emission.reshape(support.shape)
    picked = np.argpartition(flat_score, take - 1)[:take]
    picked = picked[np.isfinite(flat_score[picked])]
    emission[picked] = True
    return emission.reshape(support.shape)


def summarize(draws: list[dict]) -> dict:
    dtis = [d["dti"] for d in draws if np.isfinite(d["dti"])]
    return {
        "mean_dti": float(np.mean(dtis)) if dtis else float("nan"),
        "std_dti": float(np.std(dtis)) if dtis else float("nan"),
        "mean_tp_weight": float(np.mean([d["tp_weight"] for d in draws])),
        "mean_fp_weight": float(np.mean([d["fp_weight"] for d in draws])),
        "mean_hidden_credit_fraction": float(np.mean([d["hidden_credit_fraction"] for d in draws])),
        "draws": draws,
    }


def quad_means(draws: list[dict]) -> dict:
    out: dict = {}
    for key in draws[0]:
        values = [d[key]["dti"] for d in draws
                  if key in d and np.isfinite(d[key].get("dti", float("nan")))]
        out[key] = {"mean_dti": float(np.mean(values)) if values else float("nan"),
                    "n_draws": len(values)}
    return out


def run_split(args, features, footprint, catalogue, split_seed: int, draw_seed: int) -> dict:
    hidden, known, component_count = split_components(catalogue, seed=split_seed)
    hidden &= footprint
    known &= footprint
    distance_to_known = distance_transform_edt(~known, sampling=(PIXEL_M, PIXEL_M))
    depth_index = band_index(args.manifest_json, BAND_DEPTH)
    grav_index = band_index(args.manifest_json, BAND_GRAV_HG)
    dbs_edge, coherence, grav_edge, depth_finite = edge_fields(features, depth_index, grav_index, footprint)

    rank_edge = descending_rank(dbs_edge, footprint)
    rank_grav = descending_rank(grav_edge, footprint)
    rank_depth = descending_rank(features[depth_index].astype(np.float64), footprint & depth_finite)
    corroborated = rank_edge + rank_grav
    oriented = coherence >= COHERENCE_FLOOR

    emittable = footprint & ~known & depth_finite
    fpw = fp_weight_field(hidden, known)
    rng = np.random.default_rng(draw_seed)
    far_rows = np.flatnonzero(emittable.ravel())

    result: dict = {
        "split_seed": split_seed,
        "draw_seed": draw_seed,
        "components": int(component_count),
        "hidden_pixels": int(hidden.sum()),
        "known_pixels": int(known.sum()),
        "oriented_pixels": int((oriented & footprint).sum()),
        "arms": {},
    }

    arm_scores = {
        PRIMARY_ARM: np.where(oriented, corroborated, np.inf),
        "basement_edge_only": rank_edge,
        "dbs_magnitude": rank_depth,
        "grav_edge_only": rank_grav,
    }

    for budget in args.budgets:
        primary_emission = top_n_emission(arm_scores[PRIMARY_ARM], emittable, budget)
        primary_rows = np.flatnonzero(primary_emission.ravel())
        matched = distance_matched_draw(far_rows, primary_rows, distance_to_known.ravel(),
                                        min(budget, primary_rows.size), rng)
        matched = matched.reshape(emittable.shape) & emittable
        uniform = np.zeros(emittable.size, dtype=bool)
        if far_rows.size:
            uniform[rng.choice(far_rows, size=min(budget, far_rows.size), replace=False)] = True
        uniform = uniform.reshape(emittable.shape) & emittable

        arms_at_budget = {
            "random_near_matched": summarize([masked_dti(matched, hidden, known, fp_weight=fpw)]),
            "far_random": summarize([masked_dti(uniform, hidden, known, fp_weight=fpw)]),
        }
        for name, score in arm_scores.items():
            emission = top_n_emission(score, emittable, budget)
            arms_at_budget[name] = summarize([masked_dti(emission, hidden, known, fp_weight=fpw)])
            arms_at_budget[name]["emitted_pixels"] = int(emission.sum())
        result["arms"][str(budget)] = arms_at_budget

        if budget == PRIMARY_BUDGET:
            result["quadrant_diagnostics"] = {
                "note": "per-quadrant DTI keeps cross-quadrant 300 m credit; diagnostic only",
                PRIMARY_ARM: quad_means([masked_dti_by_blocks(primary_emission, hidden, known,
                                                             footprint, fp_weight=fpw)]),
                "random_near_matched": quad_means([masked_dti_by_blocks(matched, hidden, known,
                                                                       footprint, fp_weight=fpw)]),
            }
    return result


def pooled(split: dict, budget: int, arm: str) -> float:
    return split["arms"][str(budget)][arm]["mean_dti"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/h32-05-basement-edge-holdout.json"))
    parser.add_argument("--budgets", type=int, nargs="+", default=[PRIMARY_BUDGET, 40000])
    parser.add_argument("--split-seed", type=int, default=31)
    parser.add_argument("--confirm-split-seed", type=int, default=41)
    parser.add_argument("--draw-seed", type=int, default=17)
    parser.add_argument("--confirm-draw-seed", type=int, default=23)
    args = parser.parse_args()
    if PRIMARY_BUDGET not in args.budgets:
        raise SystemExit(
            f"the registered gate is defined at N={PRIMARY_BUDGET}; --budgets must include it"
        )

    args.manifest_json = json.loads((args.data_dir / "manifest.json").read_text())
    features = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
    footprint = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    catalogue = (np.load(args.data_dir / "labels.npy") == 1) & footprint

    started = time.time()
    report: dict = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": "H-32-05 buried range-front pinch-out edges (basement-surface step detector)",
        "preregistration": "docs/research/h32-05-preregistration.md",
        "design": "component holdout (3.2 km-tile interleave); arms from competition bands only; "
                  "proximity-matched and magnitude controls; exact masked DTI on hidden components",
        "metric": {"radius_m": RADIUS_M, "alpha": ALPHA, "pixel_m": PIXEL_M},
        "coherence_floor": COHERENCE_FLOOR,
        "gate": {
            "primary_arm": PRIMARY_ARM,
            "primary_budget": PRIMARY_BUDGET,
            "required_pooled_delta_vs_random_near_matched": GATE_DELTA,
            "required_quadrant_sign_consistency": "3 of 4",
            "confirmation": "pooled-positive on fresh split seed 41",
            "transform_clause": "primary must beat dbs_magnitude on both splits",
        },
        "params": {k: (str(v) if isinstance(v, Path) else v)
                   for k, v in vars(args).items() if k != "manifest_json"},
        "screen": run_split(args, features, footprint, catalogue, args.split_seed, args.draw_seed),
    }
    report["confirmation"] = run_split(args, features, footprint, catalogue,
                                       args.confirm_split_seed, args.confirm_draw_seed)

    screen = report["screen"]
    confirm = report["confirmation"]
    delta_screen = pooled(screen, PRIMARY_BUDGET, PRIMARY_ARM) - pooled(screen, PRIMARY_BUDGET, "random_near_matched")
    delta_confirm = pooled(confirm, PRIMARY_BUDGET, PRIMARY_ARM) - pooled(confirm, PRIMARY_BUDGET, "random_near_matched")
    transform_screen = pooled(screen, PRIMARY_BUDGET, PRIMARY_ARM) - pooled(screen, PRIMARY_BUDGET, "dbs_magnitude")
    transform_confirm = pooled(confirm, PRIMARY_BUDGET, PRIMARY_ARM) - pooled(confirm, PRIMARY_BUDGET, "dbs_magnitude")

    quads = screen["quadrant_diagnostics"]
    quad_positive = quad_total = 0
    for key, value in quads[PRIMARY_ARM].items():
        if not key.startswith("quadrant_"):
            continue
        control = quads["random_near_matched"].get(key, {}).get("mean_dti", float("nan"))
        arm = value.get("mean_dti", float("nan"))
        if np.isfinite(arm) and np.isfinite(control):
            quad_total += 1
            quad_positive += int(arm > control)
    quad_ok = quad_total > 0 and quad_positive >= 3

    screen_pass = bool(delta_screen >= GATE_DELTA)
    confirm_pass = bool(delta_confirm > 0)
    transform_pass = bool(transform_screen > 0 and transform_confirm > 0)
    report["gate_result"] = {
        "screen_pooled_delta_vs_matched": float(delta_screen),
        "confirmation_pooled_delta_vs_matched": float(delta_confirm),
        "screen_pooled_delta_vs_dbs_magnitude": float(transform_screen),
        "confirmation_pooled_delta_vs_dbs_magnitude": float(transform_confirm),
        "quadrants_primary_above_matched_control": f"{quad_positive}/{quad_total}",
        "screen_pass": screen_pass,
        "quadrant_pass": bool(quad_ok),
        "confirmation_pass": confirm_pass,
        "transform_clause_pass": transform_pass,
        "promoted": bool(screen_pass and quad_ok and confirm_pass and transform_pass),
        "note": "catalogue-proxy holdout only; not a competition score",
    }
    report["runtime_seconds"] = round(time.time() - started, 2)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["gate_result"], indent=2))
    print(f"Full report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
