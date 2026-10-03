#!/usr/bin/env python3
"""Run the frozen H-31-02b full-pool scarp-emitter screens without tuning labels.

The primary result follows the archived fold-local catalogue-proxy protocol and
matches the adaptive baseline's exact per-fold emission counts. The independent
SGMC screen uses the saved component draws and 80,392-dot global budget. All scores
are research proxies, not DrivenData competition scores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.cv import spatial_quadrant_masks  # noqa: E402
from gemsdoe30.emission import dti_components_masked, dti_from_components, poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.scarp import scarp_orientation_score  # noqa: E402

SCARP_SHA256 = "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"
OWNER_COMMIT = "07345ea0604953d7efb858d9cfbc21e20c7aca0b"
EXPECTED_BANDS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
    "downface_max", "upface_max", "cross_max", "relief", "coh100",
    "strike", "valid",
)
BAND_INDEX = {
    "step_max": 3,
    "downface_max": 6,
    "upface_max": 7,
    "coh100": 10,
    "strike": 11,
    "valid": 12,
}
FOLD_BUDGETS = (29_114, 22_102, 18_009, 24_165)
SPATIAL_BEST_DTI = 0.1892699400542499
SGMC_GLOBAL_BUDGET = 80_392
SGMC_BEST_DTI = 0.09525705977964063
SPACING_PX = 3.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mask_sha256(mask: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(mask, dtype=np.uint8).tobytes()).hexdigest()


def _show_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _read_scarp_stack(path: Path, template_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    import rasterio

    if not path.is_file():
        raise FileNotFoundError(f"scarp feature stack missing: {path}")
    actual_sha = _sha256(path)
    if actual_sha != SCARP_SHA256:
        raise ValueError(f"scarp stack SHA mismatch: {actual_sha} != pinned {SCARP_SHA256}")

    with rasterio.open(template_path) as template:
        template_grid = (
            template.width,
            template.height,
            template.crs.to_string() if template.crs else None,
            tuple(float(value) for value in template.transform),
        )
    with rasterio.open(path) as dataset:
        stack_grid = (
            dataset.width,
            dataset.height,
            dataset.crs.to_string() if dataset.crs else None,
            tuple(float(value) for value in dataset.transform),
        )
        if stack_grid != template_grid:
            raise ValueError(f"scarp/template grid mismatch: {stack_grid!r} != {template_grid!r}")
        if dataset.count != len(EXPECTED_BANDS) or tuple(dataset.descriptions) != EXPECTED_BANDS:
            raise ValueError(f"scarp band order/count mismatch: {dataset.descriptions!r}")
        if dataset.dtypes != ("uint8",) * len(EXPECTED_BANDS):
            raise ValueError(f"expected uint8 scarp bands; found {dataset.dtypes!r}")
        channels = {
            name: dataset.read(index).astype(np.uint8, copy=False)
            for name, index in BAND_INDEX.items()
        }
        nodata = dataset.nodata
    return channels, {
        "path": _show_path(path),
        "sha256": actual_sha,
        "width": stack_grid[0],
        "height": stack_grid[1],
        "crs": stack_grid[2],
        "transform": list(stack_grid[3]),
        "nodata": nodata,
        "band_descriptions": list(EXPECTED_BANDS),
        "owner_commit": OWNER_COMMIT,
        "owner_authenticated_by_organizer": False,
    }


def _make_score(channels: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    return scarp_orientation_score(
        channels["step_max"],
        channels["downface_max"],
        channels["upface_max"],
        channels["coh100"],
        channels["strike"],
        channels["valid"],
        window_size=3,
        minimum_center_coverage=0.5,
        min_support_cells=3.0,
    )


def _candidate_mask(score: np.ndarray, eligible_domain: np.ndarray, budget: int) -> tuple[np.ndarray, int]:
    eligible = np.asarray(eligible_domain, dtype=bool) & np.isfinite(score) & (score > 0.0)
    rows, cols = poisson_disk_select_ordered(
        np.asarray(score, dtype=np.float32),
        SPACING_PX,
        mask=eligible,
        limit=None,
        max_kept=budget,
    )
    capacity = int(rows.size)
    if capacity < budget:
        return np.zeros(score.shape, dtype=bool), capacity
    output = np.zeros(score.shape, dtype=bool)
    output[rows, cols] = True
    return output, capacity


def _uniform_mask(domain: np.ndarray, count: int, seed: int) -> np.ndarray:
    flat = np.flatnonzero(domain)
    if count > flat.size:
        raise ValueError(f"uniform budget {count} exceeds domain capacity {flat.size}")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(flat, size=count, replace=False)
    output = np.zeros(domain.shape, dtype=bool)
    output.flat[chosen] = True
    return output


def _score_mask(prediction: np.ndarray, truth: np.ndarray, scored_domain: np.ndarray) -> dict[str, Any]:
    result: dict[str, Any] = dti_components_masked(
        prediction.astype(np.float32),
        truth.astype(np.uint8),
        scored_domain,
        pixel_size_m=100.0,
        radius_m=300.0,
        alpha=0.2,
    )
    result["emitted_pixels"] = int((prediction & scored_domain).sum())
    result["global_emitted_pixels"] = int(prediction.sum())
    return result


def _pooled(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = float(sum(row["tp_weight"] for row in rows))
    fp = float(sum(row["fp_weight"] for row in rows))
    truth = float(sum(row["truth_pixels"] for row in rows))
    return {
        "tp_weight": tp,
        "fp_weight": fp,
        "truth_pixels": truth,
        "emitted_pixels": int(sum(row["emitted_pixels"] for row in rows)),
        "global_emitted_pixels": int(sum(row["global_emitted_pixels"] for row in rows)),
        "dti": dti_from_components(tp, fp, truth, alpha=0.2),
    }


def _top_component_examples(
    truth: np.ndarray,
    candidate: np.ndarray,
    uniform: np.ndarray,
    score: np.ndarray,
    transform: Any,
    fold: int,
    limit: int = 3,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from scipy.ndimage import center_of_mass, label

    components, n_components = label(truth, structure=np.ones((3, 3), dtype=np.uint8))
    if n_components == 0:
        return [], []
    ids = np.arange(1, n_components + 1, dtype=np.int32)
    truth_component_ids = components[truth]
    counts = np.bincount(truth_component_ids, minlength=n_components + 1)
    score_sums = np.bincount(
        truth_component_ids,
        weights=score[truth].astype(np.float64),
        minlength=n_components + 1,
    )
    candidate_hits = np.bincount(components[candidate & truth], minlength=n_components + 1)
    uniform_hits = np.bincount(components[uniform & truth], minlength=n_components + 1)
    centers = center_of_mass(truth.astype(np.uint8), labels=components, index=ids)
    records: list[dict[str, Any]] = []
    for component_id in ids:
        count = int(counts[component_id])
        if not count:
            continue
        row_center, col_center = (float(value) for value in centers[component_id - 1])
        x, y = transform * (col_center + 0.5, row_center + 0.5)
        candidate_count = int(candidate_hits[component_id])
        uniform_count = int(uniform_hits[component_id])
        records.append({
            "fold": fold,
            "component_id_within_fold": int(component_id),
            "truth_pixels": count,
            "centroid_row": row_center,
            "centroid_col": col_center,
            "centroid_easting_m": float(x),
            "centroid_northing_m": float(y),
            "mean_scarp_score_on_component": float(score_sums[component_id] / count),
            "candidate_dots_on_component": candidate_count,
            "uniform_dots_on_component": uniform_count,
            "direct_dot_count_delta": candidate_count - uniform_count,
            "diagnostic_scope": "direct component overlap and mean feature score; not distance-weighted DTI credit",
        })
    positive = sorted(
        (row for row in records if row["direct_dot_count_delta"] > 0),
        key=lambda row: (row["direct_dot_count_delta"], row["mean_scarp_score_on_component"]),
        reverse=True,
    )[:limit]
    negative = sorted(
        (row for row in records if row["direct_dot_count_delta"] < 0),
        key=lambda row: (row["direct_dot_count_delta"], row["mean_scarp_score_on_component"]),
    )[:limit]
    return positive, negative


def _validate_baselines(metric_path: Path, novelty_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metric = _read_json(metric_path)
    adaptive = metric.get("pooled_cross_validated", {}).get("adaptive", {})
    selection = metric.get("selection", {}).get("adaptive", [])
    budgets = tuple(int(row["held_out_emitted_pixels"]) for row in selection)
    baseline_dti = float(adaptive.get("pooled_dti", float("nan")))
    if budgets != FOLD_BUDGETS:
        raise ValueError(f"archived adaptive fold budgets changed: {budgets!r} != {FOLD_BUDGETS!r}")
    if not np.isclose(baseline_dti, SPATIAL_BEST_DTI, rtol=0.0, atol=1e-12):
        raise ValueError(f"archived spatial baseline changed: {baseline_dti} != {SPATIAL_BEST_DTI}")
    spatial = {
        "path": _show_path(metric_path),
        "sha256": _sha256(metric_path),
        "adaptive_dti": baseline_dti,
        "adaptive_fold_dti": [float(row["held_out_dti"]) for row in selection],
        "adaptive_fold_counts": list(budgets),
        "aggregation_scope": "archived fold-local catalogue-proxy DTI; not a competition score",
    }

    novelty = _read_json(novelty_path)
    repeats = novelty.get("repeats_detail", [])
    if len(repeats) != 5:
        raise ValueError(f"expected five archived SGMC screen repeats, found {len(repeats)}")
    best_values: list[float] = []
    random_values: list[float] = []
    for repeat, entry in enumerate(repeats):
        try:
            best_values.append(float(entry["emitters"]["cand_t04s4"]["dti"]))
            random_values.append(float(entry["emitters"]["blind_random_80392"]["dti"]))
        except (KeyError, TypeError) as exc:
            raise ValueError(f"missing archived SGMC baseline values in repeat {repeat}") from exc
    best_mean = float(np.mean(best_values))
    if not np.isclose(best_mean, SGMC_BEST_DTI, rtol=0.0, atol=1e-12):
        raise ValueError(f"archived SGMC baseline mean changed: {best_mean}")
    independent = {
        "path": _show_path(novelty_path),
        "sha256": _sha256(novelty_path),
        "best_emitter": "cand_t04s4",
        "best_per_repeat_dti": best_values,
        "best_mean_dti": best_mean,
        "blind_random_80392_per_repeat_dti": random_values,
        "best_prediction_mask_available": False,
        "comparison_scope": "archived numeric values only; cand_t04s4 mask is absent and cannot be recomputed",
    }
    return spatial, independent


def _capacity_preflight(score: np.ndarray, valid: np.ndarray) -> tuple[dict[str, Any], list[np.ndarray], np.ndarray]:
    folds: list[dict[str, Any]] = []
    candidate_masks: list[np.ndarray] = []
    for fold, budget in enumerate(FOLD_BUDGETS):
        _, block = spatial_quadrant_masks(valid, fold, buffer_m=300.0)
        domain = block & valid
        candidate, capacity = _candidate_mask(score, domain, budget)
        uniform_capacity = int(domain.sum())
        candidate_masks.append(candidate)
        folds.append({
            "fold": fold,
            "valid_pixels": uniform_capacity,
            "frozen_budget": budget,
            "accepted_spacing_capacity": capacity,
            "candidate_capacity_pass": capacity >= budget,
            "uniform_capacity_pass": uniform_capacity >= budget,
            "candidate_mask_sha256": _mask_sha256(candidate),
        })
        print(
            f"preflight fold {fold}: accepted={capacity:,} required={budget:,} "
            f"uniform_domain={uniform_capacity:,}",
            flush=True,
        )
    global_candidate, global_capacity = _candidate_mask(score, valid, SGMC_GLOBAL_BUDGET)
    global_preflight = {
        "valid_pixels": int(valid.sum()),
        "frozen_budget": SGMC_GLOBAL_BUDGET,
        "accepted_spacing_capacity": global_capacity,
        "candidate_capacity_pass": global_capacity >= SGMC_GLOBAL_BUDGET,
        "uniform_capacity_pass": int(valid.sum()) >= SGMC_GLOBAL_BUDGET,
        "candidate_mask_sha256": _mask_sha256(global_candidate),
    }
    all_ready = (
        all(row["candidate_capacity_pass"] and row["uniform_capacity_pass"] for row in folds)
        and global_preflight["candidate_capacity_pass"]
        and global_preflight["uniform_capacity_pass"]
    )
    result = {
        "status": "ready" if all_ready else "void_capacity_limited",
        "spacing_px": SPACING_PX,
        "candidate_pool_limit": None,
        "candidate_pool_scope": "all eligible finite positive-score cells; early stop at the frozen accepted-dot budget",
        "capacity_semantics": "if budget is reached, accepted_spacing_capacity is a lower bound equal to the frozen count; if not reached, the complete eligible pool was exhausted",
        "folds": folds,
        "independent_global": global_preflight,
        "all_frozen_budgets_available": bool(all_ready),
        "dti_scoring_performed": False,
    }
    return result, candidate_masks, global_candidate


def _spatial_screen(
    score: np.ndarray,
    labels: np.ndarray,
    valid: np.ndarray,
    transform: Any,
    candidate_masks: list[np.ndarray],
    *,
    channels: dict[str, np.ndarray],
) -> dict[str, Any]:
    fold_rows: list[dict[str, Any]] = []
    uniform_masks: list[np.ndarray] = []
    domains: list[np.ndarray] = []
    candidate_rows: list[dict[str, Any]] = []
    uniform_rows: list[dict[str, Any]] = []

    for fold, (budget, candidate) in enumerate(zip(FOLD_BUDGETS, candidate_masks)):
        _, block = spatial_quadrant_masks(valid, fold, buffer_m=300.0)
        domain = block & valid
        if int(candidate.sum()) != budget:
            raise RuntimeError(f"preflight candidate count changed for fold {fold}")
        uniform = _uniform_mask(domain, budget, 20261003 + fold)
        domains.append(domain)
        uniform_masks.append(uniform)
        truth = (labels == 1) & domain
        cand_stats = _score_mask(candidate, truth, domain)
        rand_stats = _score_mask(uniform, truth, domain)
        candidate_rows.append(cand_stats)
        uniform_rows.append(rand_stats)
        fold_rows.append({
            "fold": fold,
            "frozen_budget": budget,
            "accepted_spacing_capacity": int(candidate.sum()),
            "truth_pixels": int(truth.sum()),
            "candidate": cand_stats,
            "uniform_control": rand_stats,
            "candidate_minus_uniform_dti": float(cand_stats["dti"] - rand_stats["dti"]),
            "candidate_mask_sha256": _mask_sha256(candidate),
            "uniform_mask_sha256": _mask_sha256(uniform),
            "candidate_uniform_masks_distinct": not np.array_equal(candidate, uniform),
        })
        print(
            f"scored fold {fold}: candidate={cand_stats['dti']:.6f} "
            f"uniform={rand_stats['dti']:.6f} n={budget:,}",
            flush=True,
        )

    candidate_pool = _pooled(candidate_rows)
    uniform_pool = _pooled(uniform_rows)
    gain = float(candidate_pool["dti"] - uniform_pool["dti"])
    positive_folds = sum(row["candidate_minus_uniform_dti"] > 0.0 for row in fold_rows)
    baseline_delta = float(candidate_pool["dti"] - SPATIAL_BEST_DTI)
    primary_pass = (
        candidate_pool["dti"] >= SPATIAL_BEST_DTI + 0.005
        and gain >= 0.005
        and positive_folds >= 3
        and all(row["candidate_uniform_masks_distinct"] for row in fold_rows)
    )

    permutation_folds: list[dict[str, Any]] = []
    permutation_rows: list[dict[str, Any]] = []
    for fold, (budget, domain, uniform) in enumerate(zip(FOLD_BUDGETS, domains, uniform_masks)):
        strike_permuted = channels["strike"].copy()
        eligible = domain & (channels["valid"] > 1) & (channels["strike"] > 0)
        indices = np.flatnonzero(eligible)
        values = strike_permuted.flat[indices].copy()
        np.random.default_rng(20261003 + 300 + fold).shuffle(values)
        strike_permuted.flat[indices] = values
        altered_channels = dict(channels)
        altered_channels["strike"] = strike_permuted
        altered_score, _ = _make_score(altered_channels)
        altered_candidate, capacity = _candidate_mask(altered_score, domain, budget)
        if capacity < budget:
            permutation_folds.append({
                "fold": fold,
                "status": "capacity_limited",
                "accepted_spacing_capacity": capacity,
                "frozen_budget": budget,
            })
            print(f"strike permutation fold {fold}: capacity limited ({capacity:,} < {budget:,})", flush=True)
            continue
        truth = (labels == 1) & domain
        altered_stats = _score_mask(altered_candidate, truth, domain)
        permutation_rows.append(altered_stats)
        permutation_folds.append({
            "fold": fold,
            "status": "scored",
            "accepted_spacing_capacity": capacity,
            "frozen_budget": budget,
            "candidate": altered_stats,
            "candidate_minus_uniform_dti": float(altered_stats["dti"] - uniform_rows[fold]["dti"]),
            "candidate_mask_sha256": _mask_sha256(altered_candidate),
        })
        print(f"strike permutation fold {fold}: candidate={altered_stats['dti']:.6f}", flush=True)

    if len(permutation_rows) == len(FOLD_BUDGETS):
        permutation_pool = _pooled(permutation_rows)
        permutation_gain = float(permutation_pool["dti"] - uniform_pool["dti"])
        fraction_removed = (gain - permutation_gain) / gain if gain > 0.0 else None
        perturbation = {
            "status": "complete",
            "permuted_strike_pooled": permutation_pool,
            "original_gain_over_uniform": gain,
            "permuted_gain_over_uniform": permutation_gain,
            "fraction_of_positive_gain_removed": fraction_removed,
            "required_fraction_removed_if_original_gain_positive": 0.5,
            "per_fold": permutation_folds,
            "passes_preregistered_perturbation_gate": gain <= 0.0 or fraction_removed >= 0.5,
        }
    else:
        perturbation = {
            "status": "void_capacity_limited",
            "per_fold": permutation_folds,
            "passes_preregistered_perturbation_gate": False,
        }

    positive_examples: list[dict[str, Any]] = []
    negative_examples: list[dict[str, Any]] = []
    for fold, (domain, candidate, uniform) in enumerate(zip(domains, candidate_masks, uniform_masks)):
        truth = (labels == 1) & domain
        positive, negative = _top_component_examples(
            truth, candidate, uniform, score, transform, fold,
        )
        positive_examples.extend(positive)
        negative_examples.extend(negative)
    positive_examples.sort(
        key=lambda row: (row["direct_dot_count_delta"], row["mean_scarp_score_on_component"]),
        reverse=True,
    )
    negative_examples.sort(
        key=lambda row: (row["direct_dot_count_delta"], row["mean_scarp_score_on_component"]),
    )

    return {
        "status": "scored",
        "folds": fold_rows,
        "pooled_candidate": candidate_pool,
        "pooled_uniform_control": uniform_pool,
        "candidate_minus_uniform_dti": gain,
        "candidate_minus_archived_best_dti": baseline_delta,
        "archived_best_dti": SPATIAL_BEST_DTI,
        "positive_lift_folds": int(positive_folds),
        "screen_pass": bool(primary_pass),
        "gate_results": {
            "candidate_at_least_archived_best_plus_0_005": candidate_pool["dti"] >= SPATIAL_BEST_DTI + 0.005,
            "candidate_at_least_uniform_plus_0_005": gain >= 0.005,
            "positive_candidate_minus_uniform_in_at_least_3_of_4_folds": positive_folds >= 3,
            "exact_frozen_counts_and_distinct_masks": all(
                row["candidate"]["emitted_pixels"] == row["frozen_budget"]
                and row["uniform_control"]["emitted_pixels"] == row["frozen_budget"]
                and row["candidate_uniform_masks_distinct"]
                for row in fold_rows
            ),
        },
        "feature_perturbation": perturbation,
        "qualitative_top_direct_dot_hit_components": positive_examples[:12],
        "qualitative_missed_or_lower_dot_count_components": negative_examples[:12],
        "qualitative_scope": "direct component overlap and score summaries are descriptive only; no visual or qualitative finding overrides the DTI gate",
    }


def _sgmc_screen(
    score: np.ndarray,
    labels: np.ndarray,
    valid: np.ndarray,
    inventory_path: Path,
    candidate: np.ndarray,
    archived: dict[str, Any],
    archived_raw: dict[str, Any],
) -> dict[str, Any]:
    import rasterio
    from scipy.ndimage import binary_dilation, label

    with rasterio.open(inventory_path) as dataset:
        inventory_codes = dataset.read(1)
        inventory = (inventory_codes > 0) & (inventory_codes != dataset.nodata) & valid
        grid = {
            "width": dataset.width,
            "height": dataset.height,
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "transform": [float(value) for value in dataset.transform],
            "nodata": dataset.nodata,
        }
    domain = valid & ~binary_dilation((labels == 1) & valid, iterations=3)
    uniform = _uniform_mask(valid, SGMC_GLOBAL_BUDGET, 1000 + SGMC_GLOBAL_BUDGET)
    components, component_count = label(inventory, structure=np.ones((3, 3), dtype=np.uint8))
    component_ids = np.arange(1, component_count + 1, dtype=np.int32)
    if not component_ids.size:
        raise ValueError("SGMC inventory contains no 8-connected components")

    candidate_rows: list[dict[str, Any]] = []
    random_rows: list[dict[str, Any]] = []
    repeats_out: list[dict[str, Any]] = []
    random_reproduced_flags: list[bool] = []
    historic_best = archived["best_per_repeat_dti"]
    historic_random = archived["blind_random_80392_per_repeat_dti"]
    for repeat in range(5):
        rng = np.random.default_rng(30 * 31 + repeat)
        shuffled = rng.permutation(component_ids)
        held = shuffled[: int(round(0.3 * shuffled.size))]
        truth = np.isin(components, held) & domain
        if not truth.any():
            raise ValueError(f"SGMC holdout repeat {repeat} has no truth in the scored domain")
        cand_stats = _score_mask(candidate, truth, domain)
        rand_stats = _score_mask(uniform, truth, domain)
        candidate_rows.append(cand_stats)
        random_rows.append(rand_stats)
        archived_entry = archived_raw["repeats_detail"][repeat]["emitters"]["blind_random_80392"]
        random_reproduced = (
            np.isclose(rand_stats["dti"], historic_random[repeat], rtol=0.0, atol=1e-12)
            and rand_stats["emitted_pixels"] == int(archived_entry["emitted_pixels"])
        )
        random_reproduced_flags.append(bool(random_reproduced))
        repeats_out.append({
            "repeat": repeat,
            "hidden_components": int(held.size),
            "truth_pixels_in_domain": int(truth.sum()),
            "candidate": cand_stats,
            "uniform_control": rand_stats,
            "archived_cand_t04s4_dti": historic_best[repeat],
            "candidate_minus_archived_dti": float(cand_stats["dti"] - historic_best[repeat]),
            "archived_blind_random_dti": historic_random[repeat],
            "blind_random_reproduces_archived_dti_and_count": bool(random_reproduced),
            "candidate_minus_uniform_dti": float(cand_stats["dti"] - rand_stats["dti"]),
        })
        print(
            f"SGMC repeat {repeat}: candidate={cand_stats['dti']:.6f} "
            f"uniform={rand_stats['dti']:.6f} archived_best={historic_best[repeat]:.6f}",
            flush=True,
        )

    candidate_mean = float(np.mean([row["dti"] for row in candidate_rows]))
    random_mean = float(np.mean([row["dti"] for row in random_rows]))
    wins = sum(row["candidate"]["dti"] > row["archived_cand_t04s4_dti"] for row in repeats_out)
    gain = candidate_mean - random_mean
    screen_pass = candidate_mean >= SGMC_BEST_DTI + 0.005 and wins >= 4 and gain >= 0.005
    return {
        "status": "screened",
        "inventory": {
            "path": _show_path(inventory_path),
            "sha256": _sha256(inventory_path),
            "grid": grid,
            "pixels_in_template_footprint": int(inventory.sum()),
            "connected_components_8": int(component_count),
            "scored_domain_pixels": int(domain.sum()),
            "source": "USGS State Geologic Map Compilation; public-domain receipt at data/external/external_receipt.json",
            "independence_caveat": "an independent but imperfect inventory proxy, not competition truth",
        },
        "global_budget": SGMC_GLOBAL_BUDGET,
        "spacing_px": SPACING_PX,
        "accepted_capacity": int(candidate.sum()),
        "candidate_mask_sha256": _mask_sha256(candidate),
        "uniform_mask_sha256": _mask_sha256(uniform),
        "candidate_uniform_masks_distinct": not np.array_equal(candidate, uniform),
        "archived_baseline": archived,
        "candidate_mean_dti": candidate_mean,
        "blind_random_mean_dti": random_mean,
        "archived_blind_random_reproduced_per_repeat": all(random_reproduced_flags),
        "candidate_minus_uniform_dti": gain,
        "candidate_minus_archived_mean_dti": candidate_mean - SGMC_BEST_DTI,
        "wins_vs_archived_best": int(wins),
        "screen_pass": bool(screen_pass),
        "gate_results": {
            "candidate_at_least_archived_best_plus_0_005": candidate_mean >= SGMC_BEST_DTI + 0.005,
            "candidate_beats_archived_best_in_at_least_4_of_5": wins >= 4,
            "candidate_at_least_blind_random_plus_0_005": gain >= 0.005,
            "historical_best_mask_recomputed": False,
        },
        "repeats": repeats_out,
        "confirmation": {
            "required_if_screen_pass": True,
            "fresh_seed_31_run_performed": False,
            "promotion_eligible": False,
            "blocker": "cand_t04s4 OOF mask absent; archived numeric screen cannot stand in for a paired, freshly regenerated baseline",
        },
    }


def _data_provenance(
    args: argparse.Namespace,
    metadata: dict[str, Any],
    stack_info: dict[str, Any],
    prepared_manifest: dict[str, Any],
    external_receipt: dict[str, Any],
    raw_hashes: dict[str, str],
    valid: np.ndarray,
    labels: np.ndarray,
    channels: dict[str, np.ndarray],
) -> dict[str, Any]:
    footprint_count = int(valid.sum())
    lidar_code_count = int((channels["valid"] > 0).sum())
    positive_coverage_count = int((channels["valid"] > 1).sum())
    metadata_count = int(metadata.get("grid_cells_with_lidar", -1))
    receipt_path = ROOT / "data/external/external_receipt.json"
    manifest_path = ROOT / "docs/research/prepared-manifest.json"
    return {
        "scarp_stack": stack_info,
        "owner_metadata_path": _show_path(args.metadata),
        "owner_metadata_sha256": _sha256(args.metadata),
        "owner_metadata_commit": OWNER_COMMIT,
        "organizer_authenticated": False,
        "mirror_pin": {
            "sha256": SCARP_SHA256,
            "repo": "buffedlizard55-lab/GEMSDOE24",
            "ref": OWNER_COMMIT,
        },
        "coverage": {
            "template_valid_pixels": footprint_count,
            "stack_valid_code_gt_0_pixels": lidar_code_count,
            "stack_decoded_coverage_gt_0_pixels": positive_coverage_count,
            "stack_valid_code_fraction_of_template": lidar_code_count / max(footprint_count, 1),
            "owner_metadata_grid_cells_with_lidar": metadata_count,
            "metadata_vs_raster_count_delta": lidar_code_count - metadata_count,
            "metadata_count_match": lidar_code_count == metadata_count,
            "irregularity_note": (
                "owner metadata grid_cells_with_lidar differs from raster valid-band q>0 count; "
                "the transform uses the pinned raster bytes directly"
                if lidar_code_count != metadata_count else None
            ),
        },
        "template_sha256": _sha256(args.template),
        "raw_source_hashes_verified_against_prepared_manifest": raw_hashes,
        "processed_valid_sha256": _sha256(args.data_dir / "valid.npy"),
        "processed_labels_sha256": _sha256(args.data_dir / "labels.npy"),
        "label_valid_sha256": _sha256(args.data_dir / "label_valid.npy"),
        "prepared_manifest": {
            "path": _show_path(manifest_path),
            "sha256": _sha256(manifest_path),
            "dataset_signature": prepared_manifest.get("dataset_signature"),
            "valid_mask_sha256": prepared_manifest.get("valid_mask_sha256"),
            "positive_label_pixels": int(np.count_nonzero((labels == 1) & valid)),
        },
        "external_source_receipt": {
            "path": _show_path(receipt_path),
            "sha256": _sha256(receipt_path),
            "sgmc_output": external_receipt.get("derived", {}).get("sgmc_faults"),
            "sgmc_official_sources": {
                key: external_receipt.get("downloads", {}).get(key)
                for key in ("sgmc_nv", "sgmc_ca")
            },
        },
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--scarp-stack", type=Path, default=ROOT / "data/raw/external/lidar_scarp_features_u8.tif")
    parser.add_argument("--metadata", type=Path, default=ROOT / "docs/research/lidar-scarp-stack-owner-metadata.json")
    parser.add_argument("--metric-baseline", type=Path,
                        default=ROOT / "docs/research/metric-emission-holdout-results.json")
    parser.add_argument("--novelty-baseline", type=Path,
                        default=ROOT / "docs/research/novelty-holdout.json")
    parser.add_argument("--sgmc", type=Path, default=ROOT / "data/external/derived_sgmc_faults_100m_u8.tif")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/research/h31-02b-scarp-full-pool-holdout.json")
    parser.add_argument("--preflight-output", type=Path,
                        default=ROOT / "docs/research/h31-02b-scarp-full-pool-preflight.json")
    parser.add_argument("--cache-score", type=Path,
                        default=ROOT / "runs/h31-02/scarp-orientation-score.npy")
    parser.add_argument("--preflight-only", action="store_true",
                        help="verify frozen candidate capacities and exit without any DTI calculation")
    args = parser.parse_args()

    started = time.time()
    import rasterio
    import scipy

    for path in (args.template, args.scarp_stack, args.metadata, args.metric_baseline,
                 args.novelty_baseline, args.sgmc):
        if not path.is_file():
            raise FileNotFoundError(f"required experiment input missing: {path}")
    prepared_manifest_path = ROOT / "docs/research/prepared-manifest.json"
    receipt_path = ROOT / "data/external/external_receipt.json"
    if not prepared_manifest_path.is_file() or not receipt_path.is_file():
        raise FileNotFoundError("prepared-data manifest or external-source receipt is missing")

    metadata = _read_json(args.metadata)
    prepared_manifest = _read_json(prepared_manifest_path)
    external_receipt = _read_json(receipt_path)
    archived_spatial, archived_sgmc = _validate_baselines(args.metric_baseline, args.novelty_baseline)
    archived_sgmc_raw = _read_json(args.novelty_baseline)

    with rasterio.open(args.template) as template:
        template_plane = template.read(1)
        valid = np.isfinite(template_plane)
        template_grid = (
            template.width,
            template.height,
            template.crs.to_string() if template.crs else None,
            tuple(float(value) for value in template.transform),
        )
        template_transform = template.transform
        template_gdal = [float(value) for value in template.transform.to_gdal()]
    if prepared_manifest.get("shape_hw") != [template.height, template.width]:
        raise ValueError("prepared manifest shape does not match the template")
    if prepared_manifest.get("epsg") != 32611 or prepared_manifest.get("transform_gdal") != template_gdal:
        raise ValueError("prepared manifest CRS/transform does not match the template")

    raw_hashes: dict[str, str] = {}
    for name, record in prepared_manifest.get("source_files", {}).items():
        raw_path = ROOT / str(record["path"])
        actual_hash = _sha256(raw_path)
        if actual_hash != record.get("sha256"):
            raise ValueError(f"prepared source hash mismatch for {name}: {actual_hash}")
        raw_hashes[name] = actual_hash
    if raw_hashes.get("sample_submission") != _sha256(args.template):
        raise ValueError("template bytes differ from the prepared-data source manifest")

    labels = np.load(args.data_dir / "labels.npy", allow_pickle=False).astype(np.float32)
    prepared_valid = np.load(args.data_dir / "valid.npy", allow_pickle=False).astype(bool)
    label_valid = np.load(args.data_dir / "label_valid.npy", allow_pickle=False).astype(bool)
    if not (labels.shape == prepared_valid.shape == label_valid.shape == valid.shape):
        raise ValueError("prepared arrays and template do not share one grid")
    if not np.array_equal(valid, prepared_valid) or not np.array_equal(valid, label_valid):
        raise ValueError("prepared masks do not exactly match the finite template footprint")
    if np.any(~np.isin(labels[valid], (0.0, 1.0))):
        raise ValueError("prepared labels are not binary inside the valid footprint")
    with rasterio.open(ROOT / "data/raw/labels.tif") as label_source:
        raw_labels = label_source.read(1)
    if raw_labels.shape != labels.shape or not np.array_equal(raw_labels[valid].astype(np.float32), labels[valid]):
        raise ValueError("prepared labels do not reproduce the pinned raw catalogue labels")

    with rasterio.open(args.sgmc) as sgmc_source:
        sgmc_grid = (
            sgmc_source.width,
            sgmc_source.height,
            sgmc_source.crs.to_string() if sgmc_source.crs else None,
            tuple(float(value) for value in sgmc_source.transform),
        )
    if sgmc_grid != template_grid:
        raise ValueError(f"SGMC/template grid mismatch before scoring: {sgmc_grid!r} != {template_grid!r}")
    receipt_sgmc = external_receipt.get("derived", {}).get("sgmc_faults", {})
    if receipt_sgmc.get("path") != _show_path(args.sgmc) or receipt_sgmc.get("sha256") != _sha256(args.sgmc):
        raise ValueError("SGMC raster path/hash does not match the public-source receipt")

    channels, stack_info = _read_scarp_stack(args.scarp_stack, args.template)
    pins = _read_json(ROOT / "docs/research/mirror-pins-extra.json").get("files", [])
    scarp_pin = next((row for row in pins if row.get("id") == "ext_lidar_scarp_features_u8"), None)
    if not scarp_pin or scarp_pin.get("sha256") != SCARP_SHA256 or scarp_pin.get("ref") != OWNER_COMMIT:
        raise ValueError("scarp stack pin record missing or inconsistent")
    if tuple(metadata.get("bands", [])) != EXPECTED_BANDS:
        raise ValueError("owner metadata band order does not match the raster")
    expected_encoding = {
        "step_max": [1.0, "sqrt"],
        "downface_max": [1.0, "sqrt"],
        "upface_max": [1.0, "sqrt"],
        "coh100": [1.0, "linear"],
        "strike": [180.0, "linear"],
        "valid": [1.0, "linear"],
    }
    for name, expected in expected_encoding.items():
        if metadata.get("quantisation", {}).get(name) != expected:
            raise ValueError(f"owner metadata quantisation mismatch for {name}")

    score, orientation = _make_score(channels)
    args.cache_score.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.cache_score, score)
    provenance = _data_provenance(
        args, metadata, stack_info, prepared_manifest, external_receipt, raw_hashes,
        valid, labels, channels,
    )
    score_summary = {
        "positive_score_pixels_in_template": int(np.count_nonzero((score > 0.0) & valid)),
        "score_min_positive": float(score[(score > 0.0) & valid].min())
        if np.any((score > 0.0) & valid) else None,
        "score_max": float(score.max(initial=0.0)),
        "score_quantiles_positive": {
            str(q): float(np.quantile(score[(score > 0.0) & valid], q))
            for q in (0.5, 0.9, 0.99)
        } if np.any((score > 0.0) & valid) else {},
        "orientation_consensus_positive_pixels": int(np.count_nonzero((orientation > 0.0) & valid)),
    }

    preflight, candidate_masks, global_candidate = _capacity_preflight(score, valid)
    preflight_report = {
        "experiment": "H-31-02b full-pool scarp-emitter capacity preflight",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": "scripts/scarp_orientation_holdout.py",
        "script_sha256": _sha256(ROOT / "scripts/scarp_orientation_holdout.py"),
        "preregistration": "docs/research/h31-02b-scarp-full-pool-preregistration-2026-10-03.md",
        "preregistration_sha256": _sha256(ROOT / "docs/research/h31-02b-scarp-full-pool-preregistration-2026-10-03.md"),
        "status": preflight["status"],
        "grid": {
            "shape_hw": [template.height, template.width],
            "crs": template_grid[2],
            "transform": list(template_grid[3]),
        },
        "data_provenance": provenance,
        "frozen_transform": {
            "channels": list(BAND_INDEX),
            "window_size_cells": 3,
            "minimum_center_coverage": 0.5,
            "minimum_orientation_support_cell_equivalents": 3.0,
            "score_is_probability": False,
            "score_summary": score_summary,
            "score_cache_path": _show_path(args.cache_score),
            "score_cache_sha256": _sha256(args.cache_score),
        },
        "capacity_preflight": preflight,
        "dti_scoring_performed": False,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    if args.preflight_only:
        _write_json(args.preflight_output, preflight_report)
        print(json.dumps({
            "preflight_output": _show_path(args.preflight_output),
            "status": preflight["status"],
            "fold_capacities": [row["accepted_spacing_capacity"] for row in preflight["folds"]],
            "fold_budgets": list(FOLD_BUDGETS),
            "sgmc_global_capacity": preflight["independent_global"]["accepted_spacing_capacity"],
            "sgmc_global_budget": SGMC_GLOBAL_BUDGET,
            "dti_scoring_performed": False,
        }, indent=2), flush=True)
        return 0

    if not preflight["all_frozen_budgets_available"]:
        report = {
            **preflight_report,
            "status": "capacity_limited_no_scoring",
            "spatial_holdout": {"status": "void_capacity_limited", "screen_pass": False},
            "independent_sgmc_holdout": {"status": "void_capacity_limited", "screen_pass": False},
            "promotion": {"promotion_eligible": False, "submission_slot_used": False},
        }
        _write_json(args.output, report)
        print(json.dumps({"output": _show_path(args.output), "status": report["status"]}, indent=2), flush=True)
        return 0

    print("All frozen dot budgets pass capacity preflight; starting registered holdouts.", flush=True)
    spatial = _spatial_screen(
        score, labels, valid, template_transform, candidate_masks, channels=channels,
    )
    sgmc = _sgmc_screen(
        score, labels, valid, args.sgmc, global_candidate, archived_sgmc, archived_sgmc_raw,
    )
    report = {
        "experiment": "H-31-02b full-pool scarp-orientation persistence",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "script": "scripts/scarp_orientation_holdout.py",
        "script_sha256": _sha256(ROOT / "scripts/scarp_orientation_holdout.py"),
        "preregistration": "docs/research/h31-02b-scarp-full-pool-preregistration-2026-10-03.md",
        "preregistration_sha256": _sha256(ROOT / "docs/research/h31-02b-scarp-full-pool-preregistration-2026-10-03.md"),
        "status": "complete",
        "result_scope": "fold-local catalogue proxy and SGMC component proxy; neither is competition truth or leaderboard score",
        "grid": {
            "shape_hw": [template.height, template.width],
            "crs": template_grid[2],
            "transform": list(template_grid[3]),
        },
        "dependencies": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "rasterio": rasterio.__version__,
        },
        "data_provenance": provenance,
        "frozen_transform": {
            "channels": list(BAND_INDEX),
            "window_size_cells": 3,
            "minimum_center_coverage": 0.5,
            "minimum_orientation_support_cell_equivalents": 3.0,
            "score_description": "sqrt(step_max * max(upface_max, downface_max)) * sqrt(coh100 * axial_strike_consensus) * decoded_valid_coverage",
            "score_is_probability": False,
            "score_summary": score_summary,
            "score_cache_path": _show_path(args.cache_score),
            "score_cache_sha256": _sha256(args.cache_score),
        },
        "capacity_preflight": preflight,
        "archived_spatial_baseline": archived_spatial,
        "spatial_holdout": spatial,
        "independent_sgmc_holdout": sgmc,
        "promotion": {
            "primary_spatial_gate_pass": bool(spatial.get("screen_pass", False)),
            "independent_sgmc_screen_pass": bool(sgmc.get("screen_pass", False)),
            "feature_perturbation_gate_pass": bool(
                spatial.get("feature_perturbation", {}).get("passes_preregistered_perturbation_gate", False)
            ),
            "fresh_seed_confirmation_performed": False,
            "submission_slot_used": False,
            "promotion_eligible": False,
            "reason": "A screen pass is not promotion; the archived cand_t04s4 mask is absent, so a fresh paired confirmation and baseline regeneration are required.",
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    _write_json(args.output, report)
    print(json.dumps({
        "output": _show_path(args.output),
        "status": report["status"],
        "spatial_candidate_dti": spatial["pooled_candidate"]["dti"],
        "spatial_uniform_dti": spatial["pooled_uniform_control"]["dti"],
        "spatial_baseline_dti": SPATIAL_BEST_DTI,
        "spatial_screen_pass": spatial["screen_pass"],
        "strike_permutation_pass": spatial["feature_perturbation"].get("passes_preregistered_perturbation_gate"),
        "sgmc_candidate_mean_dti": sgmc["candidate_mean_dti"],
        "sgmc_archived_best_mean_dti": SGMC_BEST_DTI,
        "sgmc_screen_pass": sgmc["screen_pass"],
        "promotion_eligible": False,
        "elapsed_seconds": report["elapsed_seconds"],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
