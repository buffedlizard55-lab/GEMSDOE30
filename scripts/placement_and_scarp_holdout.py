#!/usr/bin/env python3
"""Preregistered holdout for H-33-01 (placement policy), H-31-02r (LiDAR scarp dipole +
strike continuity), and H-32-05b (spacing-matched p90 1.5 km basement step ridge).

Design and promotion gates are frozen in:
  docs/research/h33-01-placement-and-scarp-preregistration.md

Key methodological guarantees (fixing IR-30-029 and IR-30-033):
1. Every feature arm and every random/proximity control is emitted with 300 m (r = 3.0 px)
   Poisson-disk spacing at identical dot count N = 15,000 (plus a diagnostic legacy
   un-thinned arm quantifying the IR-30-033a clumping confounder).
2. Emittable support is strictly ``footprint & (distance_to_known > 300 m)``, matching the
   organizer's 300 m known-fault masking rule and never consulting held-out truth.
3. Evaluated on three frames:
   - Frame 1A: Catalogue component-holdout (screen seed 31, confirmation seed 41)
   - Frame 1B: Independent USGS SGMC fault inventory (unclustered 30% component holdout)
   - Frame 1C: Independent USGS SGMC fault inventory (spatially clustered 5 km disc holdout)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import (
    binary_dilation,
    distance_transform_edt,
    label,
    laplace,
    median_filter,
    sobel,
    uniform_filter,
)
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.holdout import (  # noqa: E402
    ALPHA,
    PIXEL_M,
    RADIUS_M,
    fp_weight_field,
    masked_dti,
    masked_dti_by_blocks,
    split_components,
)

PRIMARY_BUDGET = 15000
POISSON_RADIUS_PX = 3.0
GATE_DELTA = 0.002


def band_index(manifest: dict, name: str) -> int:
    for idx, desc in enumerate(manifest["feature_band_names"]):
        if desc.split(" - ")[0].strip() == name:
            return idx
    raise KeyError(f"band {name!r} not found in manifest")


def _disk_offsets(radius_px: float) -> list[tuple[int, int]]:
    reach = max(int(math.ceil(radius_px)), 1)
    r2 = radius_px * radius_px
    return [
        (dy, dx)
        for dy in range(-reach, reach + 1)
        for dx in range(-reach, reach + 1)
        if dy * dy + dx * dx < r2
    ]


def poisson_disk_top_n(
    score: np.ndarray,
    support: np.ndarray,
    count: int,
    *,
    radius_px: float = POISSON_RADIUS_PX,
    pool_limit: int = 450_000,
) -> np.ndarray:
    """Deterministic greedy Poisson-disk selection of top ``count`` dots (higher score is better)."""
    height, width = support.shape
    kept = np.zeros((height, width), dtype=bool)
    if count <= 0 or not support.any():
        return kept
    valid_mask = support & np.isfinite(score)
    flat_idx = np.flatnonzero(valid_mask.ravel())
    if flat_idx.size == 0:
        return kept
    flat_scores = score.ravel()[flat_idx]
    if flat_idx.size > pool_limit:
        top_sub = np.argpartition(-flat_scores, pool_limit - 1)[:pool_limit]
        flat_idx = flat_idx[top_sub]
        flat_scores = flat_scores[top_sub]
    order = np.lexsort((flat_idx, -flat_scores))
    sorted_idx = flat_idx[order]
    rows = (sorted_idx // width).tolist()
    cols = (sorted_idx % width).tolist()

    blocked = np.zeros((height, width), dtype=bool)
    offsets = _disk_offsets(radius_px)
    selected = 0
    for r, c in zip(rows, cols):
        if blocked[r, c]:
            continue
        kept[r, c] = True
        selected += 1
        if selected >= count:
            break
        for dy, dx in offsets:
            y, x = r + dy, c + dx
            if 0 <= y < height and 0 <= x < width:
                blocked[y, x] = True
    return kept


def poisson_random_draw(
    support: np.ndarray,
    count: int,
    rng: np.random.Generator,
    *,
    radius_px: float = POISSON_RADIUS_PX,
) -> np.ndarray:
    """Random Poisson-disk draw of ``count`` dots inside ``support``."""
    height, width = support.shape
    kept = np.zeros((height, width), dtype=bool)
    flat_idx = np.flatnonzero(support.ravel())
    if flat_idx.size == 0 or count <= 0:
        return kept
    perm = rng.permutation(flat_idx)
    rows = (perm // width).tolist()
    cols = (perm % width).tolist()
    blocked = np.zeros((height, width), dtype=bool)
    offsets = _disk_offsets(radius_px)
    selected = 0
    for r, c in zip(rows, cols):
        if blocked[r, c]:
            continue
        kept[r, c] = True
        selected += 1
        if selected >= count:
            break
        for dy, dx in offsets:
            y, x = r + dy, c + dx
            if 0 <= y < height and 0 <= x < width:
                blocked[y, x] = True
    return kept


def poisson_distance_matched_draw(
    support: np.ndarray,
    target_mask: np.ndarray,
    distance_to_known: np.ndarray,
    count: int,
    rng: np.random.Generator,
    *,
    radius_px: float = POISSON_RADIUS_PX,
    bins: int = 10,
) -> np.ndarray:
    """Spacing-matched (Poisson-disk) AND distance-profile-matched random control."""
    height, width = support.shape
    kept = np.zeros((height, width), dtype=bool)
    pool = np.flatnonzero(support.ravel())
    target_idx = np.flatnonzero(target_mask.ravel())
    if pool.size == 0 or target_idx.size == 0 or count <= 0:
        return kept
    flat_d = distance_to_known.ravel()
    target_d = flat_d[target_idx]
    edges = np.unique(np.quantile(target_d, np.linspace(0.0, 1.0, bins + 1)))
    if edges.size < 2:
        return poisson_random_draw(support, count, rng, radius_px=radius_px)
    target_counts, _ = np.histogram(target_d, bins=edges)
    pool_d = flat_d[pool]
    pool_bin = np.clip(np.digitize(pool_d, edges[1:-1], right=False), 0, edges.size - 2)

    blocked = np.zeros((height, width), dtype=bool)
    offsets = _disk_offsets(radius_px)
    total_selected = 0

    for b in range(edges.size - 1):
        want = int(round(target_counts[b] * (count / max(target_idx.size, 1))))
        want = min(want, count - total_selected)
        if want <= 0:
            continue
        members = pool[pool_bin == b]
        if members.size == 0:
            continue
        perm = rng.permutation(members)
        rows = (perm // width).tolist()
        cols = (perm % width).tolist()
        bin_selected = 0
        for r, c in zip(rows, cols):
            if blocked[r, c] or kept[r, c]:
                continue
            kept[r, c] = True
            bin_selected += 1
            total_selected += 1
            for dy, dx in offsets:
                y, x = r + dy, c + dx
                if 0 <= y < height and 0 <= x < width:
                    blocked[y, x] = True
            if bin_selected >= want or total_selected >= count:
                break

    if total_selected < count:
        perm = rng.permutation(pool)
        rows = (perm // width).tolist()
        cols = (perm % width).tolist()
        for r, c in zip(rows, cols):
            if blocked[r, c] or kept[r, c]:
                continue
            kept[r, c] = True
            total_selected += 1
            for dy, dx in offsets:
                y, x = r + dy, c + dx
                if 0 <= y < height and 0 <= x < width:
                    blocked[y, x] = True
            if total_selected >= count:
                break
    return kept


def median_nn_spacing_px(mask: np.ndarray) -> dict[str, float]:
    pts = np.argwhere(mask)
    if pts.shape[0] < 2:
        return {"median_nn_px": float("nan"), "frac_within_3px": 0.0}
    tree = cKDTree(pts)
    dists, _ = tree.query(pts, k=2)
    nn = dists[:, 1]
    return {
        "median_nn_px": float(np.median(nn)),
        "frac_within_3px": float(np.mean(nn <= 3.0)),
    }


def normalized_rank_score(field: np.ndarray, support: np.ndarray) -> np.ndarray:
    """Return [0, 1] rank score inside ``support`` (1.0 = highest value, 0.0 = lowest)."""
    out = np.zeros(field.shape, dtype=np.float64)
    idx = np.flatnonzero((support & np.isfinite(field)).ravel())
    if idx.size == 0:
        return out
    vals = field.ravel()[idx]
    order = np.lexsort((idx, vals))
    out.ravel()[idx[order]] = np.linspace(1.0 / idx.size, 1.0, idx.size, dtype=np.float64)
    return out


def compute_scarp_dipole_fields(
    scarp_path: Path,
    features: np.ndarray,
    manifest: dict,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute H-31-02r LiDAR scarp dipole + 500 m strike continuity score and step_max ablation."""
    import rasterio

    slope_idx = band_index(manifest, "det_elev_slope")
    dem_slope = np.where(footprint & np.isfinite(features[slope_idx]), features[slope_idx], 0.0)
    slope_rank = normalized_rank_score(dem_slope, footprint)

    with rasterio.open(scarp_path) as ds:
        step_max = ds.read(3).astype(np.float64)
        lapneg = ds.read(4).astype(np.float64)
        lappos = ds.read(5).astype(np.float64)
        coh100 = ds.read(10).astype(np.float64) / 255.0
        strike_u8 = ds.read(11).astype(np.float64)
        lidar_valid = (ds.read(12) > 0) & footprint

    # Crest-toe curvature dipole * step height * local 100 m orientation coherence
    dipole = np.sqrt(np.maximum(lapneg * lappos, 0.0)) * step_max * coh100
    dipole[~lidar_valid] = 0.0

    # 500 m (5x5 px) strike-vector persistence: |<exp(2i * theta)>| weighted by step_max
    theta = strike_u8 * (math.pi / 255.0)
    w = np.where(lidar_valid, step_max + 1.0, 0.0)
    c2 = uniform_filter(w * np.cos(2.0 * theta), size=5, mode="nearest")
    s2 = uniform_filter(w * np.sin(2.0 * theta), size=5, mode="nearest")
    w_mean = uniform_filter(w, size=5, mode="nearest") + 1e-9
    strike_persistence = np.hypot(c2, s2) / w_mean
    strike_persistence[~lidar_valid] = 0.0

    # Smooth dipole over 3x3 and weight by 500 m strike persistence
    dipole_cont = uniform_filter(dipole, size=3, mode="nearest") * strike_persistence
    dipole_rank = normalized_rank_score(dipole_cont, lidar_valid)
    step_rank = normalized_rank_score(step_max, lidar_valid)

    # Combine with det_elev_slope rank so non-LiDAR footprint cells (24.6%) have a clean fallback
    primary_score = np.where(lidar_valid, 0.75 * dipole_rank + 0.25 * slope_rank, 0.5 * slope_rank)
    ablation_score = np.where(lidar_valid, 0.75 * step_rank + 0.25 * slope_rank, 0.5 * slope_rank)
    return primary_score, ablation_score


def compute_basement_step_ridge_p90(
    features: np.ndarray,
    manifest: dict,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    """Compute H-32-05b 1.5 km coherent basement step ridge score and p90 gate diagnostics."""
    d_idx = band_index(manifest, "depth_to_base_surf")
    g_idx = band_index(manifest, "iso_grav_anom_hg")
    m_idx = band_index(manifest, "tmi_hg")

    depth = np.array(features[d_idx], dtype=np.float64)
    finite = footprint & np.isfinite(depth)
    fill = float(np.median(depth[finite]))
    smooth = median_filter(np.where(np.isfinite(depth), depth, fill), size=3, mode="nearest")
    gx = sobel(smooth, axis=1, mode="nearest")
    gy = sobel(smooth, axis=0, mode="nearest")
    dbs_edge = np.hypot(gx, gy)
    dbs_edge[~footprint] = 0.0

    # Cross-gradient step ridge: positive downward concavity (-Laplacian) of edge magnitude
    edge_ridge = np.maximum(-laplace(dbs_edge, mode="nearest"), 0.0)
    edge_ridge[~footprint] = 0.0

    # 1.5 km (15x15 px) structure tensor on the step-ridge field (fixes IR-30-029)
    rgx = sobel(dbs_edge, axis=1, mode="nearest")
    rgy = sobel(dbs_edge, axis=0, mode="nearest")
    jxx = uniform_filter(rgx * rgx, size=15, mode="nearest")
    jyy = uniform_filter(rgy * rgy, size=15, mode="nearest")
    jxy = uniform_filter(rgx * rgy, size=15, mode="nearest")
    trace = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(trace * trace - 4.0 * det, 0.0))
    coherence_1500m = np.sqrt(np.maximum(trace * trace - 4.0 * det, 0.0)) / (trace + 1e-9)
    coherence_1500m[~footprint] = 0.0

    p90_floor = float(np.percentile(coherence_1500m[finite], 90.0))
    oriented_p90 = (coherence_1500m >= p90_floor) & finite

    grav_hg = np.abs(np.where(np.isfinite(features[g_idx]), features[g_idx], 0.0))
    tmi_hg = np.abs(np.where(np.isfinite(features[m_idx]), features[m_idx], 0.0))

    r_ridge = normalized_rank_score(dbs_edge + 0.5 * edge_ridge, finite)
    r_grav = normalized_rank_score(grav_hg, finite)
    r_mag = normalized_rank_score(tmi_hg, finite)
    combined = 0.50 * r_ridge + 0.35 * r_grav + 0.15 * r_mag

    p90_score = np.where(oriented_p90, combined, -np.inf)
    ungated_score = np.where(finite, r_ridge + r_grav, -np.inf)
    diagnostics = {
        "coherence_1500m_p50": float(np.percentile(coherence_1500m[finite], 50.0)),
        "coherence_1500m_p90_floor": p90_floor,
        "oriented_p90_pixels": int(oriented_p90.sum()),
        "oriented_p90_fraction": float(oriented_p90.sum() / max(int(finite.sum()), 1)),
    }
    return p90_score, ungated_score, finite, diagnostics


def allocate_stratum_dots(
    score: np.ndarray | None,
    near_mask: np.ndarray,
    mid_mask: np.ndarray,
    far_mask: np.ndarray,
    counts: tuple[int, int, int],
    rng: np.random.Generator,
) -> np.ndarray:
    """Allocate (n_near, n_mid, n_far) Poisson-disk dots across distance strata."""
    n_near, n_mid, n_far = counts
    if score is None:
        m_near = poisson_random_draw(near_mask, n_near, rng)
        m_mid = poisson_random_draw(mid_mask, n_mid, rng)
        m_far = poisson_random_draw(far_mask, n_far, rng)
    else:
        m_near = poisson_disk_top_n(score, near_mask, n_near)
        m_mid = poisson_disk_top_n(score, mid_mask, n_mid)
        m_far = poisson_disk_top_n(score, far_mask, n_far)
    return m_near | m_mid | m_far


def score_arm_with_quads(
    emission: np.ndarray,
    hidden: np.ndarray,
    known_masked: np.ndarray,
    footprint: np.ndarray,
    fpw: np.ndarray,
) -> dict:
    base = masked_dti(emission, hidden, known_masked, fp_weight=fpw)
    blocks = masked_dti_by_blocks(emission, hidden, known_masked, footprint, fp_weight=fpw)
    quads = {
        k: float(v["dti"])
        for k, v in blocks.items()
        if k.startswith("quadrant_")
    }
    spacing = median_nn_spacing_px(emission)
    return base | {"quadrants": quads} | spacing


def run_catalogue_split(
    split_seed: int,
    draw_seed: int,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    scarp_primary: np.ndarray,
    scarp_ablation: np.ndarray,
    basement_p90: np.ndarray,
    basement_ungated: np.ndarray,
    basement_finite: np.ndarray,
    budget: int = PRIMARY_BUDGET,
) -> dict:
    hidden, known, comp_count = split_components(catalogue, seed=split_seed)
    hidden &= footprint
    known &= footprint
    known_masked = binary_dilation(known, iterations=3) & footprint
    d2k = distance_transform_edt(~known, sampling=(PIXEL_M, PIXEL_M))
    emittable = footprint & (d2k > RADIUS_M)
    fpw = fp_weight_field(hidden, known_masked)
    rng = np.random.default_rng(draw_seed)

    near_mask = emittable & (d2k <= 1500.0)
    mid_mask = emittable & (d2k > 1500.0) & (d2k <= 4000.0)
    far_mask = emittable & (d2k > 4000.0)
    hedge_counts = (int(0.60 * budget), int(0.25 * budget), budget - int(0.60 * budget) - int(0.25 * budget))

    # 1. Placement-policy arms (H-33-01)
    placement_arms = {
        "policy_near_splay": poisson_random_draw(near_mask, budget, rng),
        "policy_mid_relay": poisson_random_draw(mid_mask, budget, rng),
        "policy_far_basin": poisson_random_draw(far_mask, budget, rng),
        "policy_powerlaw_hedge": allocate_stratum_dots(None, near_mask, mid_mask, far_mask, hedge_counts, rng),
        "policy_uniform_domain": poisson_random_draw(emittable, budget, rng),
    }

    # 2. H-31-02r LiDAR scarp dipole + strike continuity arms
    em_scarp_primary = poisson_disk_top_n(scarp_primary, emittable, budget)
    em_scarp_hedge = allocate_stratum_dots(scarp_primary, near_mask, mid_mask, far_mask, hedge_counts, rng)
    em_scarp_ablation = poisson_disk_top_n(scarp_ablation, emittable, budget)
    em_scarp_matched_ctrl = poisson_distance_matched_draw(
        emittable, em_scarp_primary, d2k, budget, rng
    )
    em_scarp_hedge_ctrl = poisson_distance_matched_draw(
        emittable, em_scarp_hedge, d2k, budget, rng
    )

    # 3. H-32-05b spacing-matched basement step ridge (p90 1.5 km coherence) + legacy un-thinned
    em_base_p90 = poisson_disk_top_n(basement_p90, emittable & basement_finite, budget)
    em_base_ungated_poisson = poisson_disk_top_n(basement_ungated, emittable & basement_finite, budget)
    em_base_matched_ctrl = poisson_distance_matched_draw(
        emittable & basement_finite, em_base_p90, d2k, budget, rng
    )
    # Legacy un-thinned top-N (IR-30-033a demonstration)
    flat_u = np.where((emittable & basement_finite).ravel(), -basement_ungated.ravel(), np.inf)
    pick_u = np.argpartition(flat_u, budget - 1)[:budget]
    em_base_legacy_unthinned = np.zeros(footprint.size, dtype=bool)
    em_base_legacy_unthinned[pick_u] = True
    em_base_legacy_unthinned = em_base_legacy_unthinned.reshape(footprint.shape)

    all_arms = {
        **placement_arms,
        "scarp_dipole_continuity": em_scarp_primary,
        "scarp_dipole_near_hedge": em_scarp_hedge,
        "step_max_only": em_scarp_ablation,
        "scarp_matched_control": em_scarp_matched_ctrl,
        "scarp_hedge_matched_control": em_scarp_hedge_ctrl,
        "basement_step_ridge_p90": em_base_p90,
        "basement_ungated_poisson": em_base_ungated_poisson,
        "basement_unthinned_legacy": em_base_legacy_unthinned,
        "basement_matched_control": em_base_matched_ctrl,
    }

    scored = {
        name: score_arm_with_quads(mask, hidden, known_masked, footprint, fpw)
        for name, mask in all_arms.items()
    }
    return {
        "split_seed": split_seed,
        "draw_seed": draw_seed,
        "components": int(comp_count),
        "hidden_pixels": int((hidden & ~known_masked).sum()),
        "known_masked_pixels": int(known_masked.sum()),
        "stratum_emittable_pixels": {
            "near_300_1500m": int(near_mask.sum()),
            "mid_1500_4000m": int(mid_mask.sum()),
            "far_gt_4000m": int(far_mask.sum()),
        },
        "arms": scored,
    }


def run_sgmc_novelty_frames(
    sgmc_path: Path,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    scarp_primary: np.ndarray,
    budget: int = PRIMARY_BUDGET,
    seed: int = 31,
) -> dict:
    """Evaluate placement policies and scarp continuity on SGMC (unclustered AND 5 km clustered)."""
    import rasterio

    with rasterio.open(sgmc_path) as ds:
        sgmc = (ds.read(1) > 0) & footprint
    known_masked = binary_dilation(catalogue, iterations=3) & footprint
    d2k = distance_transform_edt(~catalogue, sampling=(PIXEL_M, PIXEL_M))
    emittable = footprint & ~known_masked
    near_mask = emittable & (d2k <= 1500.0)
    mid_mask = emittable & (d2k > 1500.0) & (d2k <= 4000.0)
    far_mask = emittable & (d2k > 4000.0)
    hedge_counts = (int(0.60 * budget), int(0.25 * budget), budget - int(0.60 * budget) - int(0.25 * budget))

    rng = np.random.default_rng(seed)
    emissions = {
        "policy_near_splay": poisson_random_draw(near_mask, budget, rng),
        "policy_mid_relay": poisson_random_draw(mid_mask, budget, rng),
        "policy_far_basin": poisson_random_draw(far_mask, budget, rng),
        "policy_powerlaw_hedge": allocate_stratum_dots(None, near_mask, mid_mask, far_mask, hedge_counts, rng),
        "policy_uniform_domain": poisson_random_draw(emittable, budget, rng),
        "scarp_dipole_continuity": poisson_disk_top_n(scarp_primary, emittable, budget),
        "scarp_dipole_near_hedge": allocate_stratum_dots(scarp_primary, near_mask, mid_mask, far_mask, hedge_counts, rng),
    }
    emissions["scarp_matched_control"] = poisson_distance_matched_draw(
        emittable, emissions["scarp_dipole_continuity"], d2k, budget, rng
    )

    # Frame 1B: Unclustered 30% SGMC component holdout (2 splits: seed 31 and 41)
    comp, comp_count = label(sgmc & emittable, structure=np.ones((3, 3), dtype=int))
    comp_ids = np.arange(1, comp_count + 1)

    unclustered_splits = {}
    for s in (31, 41):
        r_s = np.random.default_rng(s)
        held = r_s.permutation(comp_ids)[: int(round(0.30 * comp_ids.size))]
        hidden_sgmc = np.isin(comp, held) & emittable
        visible_sgmc = (sgmc & emittable) & ~hidden_sgmc
        domain_mask = known_masked | (binary_dilation(visible_sgmc, iterations=3) & footprint)
        fpw = fp_weight_field(hidden_sgmc, domain_mask)
        unclustered_splits[f"seed_{s}"] = {
            "hidden_pixels": int((hidden_sgmc & ~domain_mask).sum()),
            "arms": {
                name: masked_dti(em, hidden_sgmc, domain_mask, fp_weight=fpw)
                for name, em in emissions.items()
            },
        }

    # Frame 1C: Spatially clustered SGMC holdout (8 regional 5 km discs centered on SGMC faults)
    sgmc_pts = np.argwhere(sgmc & emittable)
    clustered_splits = {}
    for s in (31, 41):
        r_s = np.random.default_rng(s + 100)
        centers = sgmc_pts[r_s.choice(sgmc_pts.shape[0], size=8, replace=False)]
        cluster_zone = np.zeros(footprint.shape, dtype=bool)
        for cr, cc in centers:
            r0, r1 = max(0, cr - 50), min(footprint.shape[0], cr + 51)
            c0, c1 = max(0, cc - 50), min(footprint.shape[1], cc + 51)
            yy, xx = np.ogrid[r0 - cr : r1 - cr, c0 - cc : c1 - cc]
            cluster_zone[r0:r1, c0:c1] |= (yy * yy + xx * xx) <= 50 * 50
        hidden_clust = sgmc & emittable & cluster_zone
        visible_clust = (sgmc & emittable) & ~hidden_clust
        domain_mask = known_masked | (binary_dilation(visible_clust, iterations=3) & footprint)
        fpw = fp_weight_field(hidden_clust, domain_mask)
        clustered_splits[f"seed_{s}"] = {
            "hidden_pixels": int((hidden_clust & ~domain_mask).sum()),
            "arms": {
                name: masked_dti(em, hidden_clust, domain_mask, fp_weight=fpw)
                for name, em in emissions.items()
            },
        }

    return {
        "unclustered_sgmc_holdout": unclustered_splits,
        "clustered_5km_sgmc_holdout": clustered_splits,
    }


def evaluate_gate_clauses(
    screen_cat: dict,
    confirm_cat: dict,
    arm_name: str,
    ctrl_name: str,
    ablation_name: str | None = None,
) -> dict:
    s_arm = screen_cat["arms"][arm_name]
    s_ctrl = screen_cat["arms"][ctrl_name]
    c_arm = confirm_cat["arms"][arm_name]
    c_ctrl = confirm_cat["arms"][ctrl_name]

    delta_screen = float(s_arm["dti"] - s_ctrl["dti"])
    delta_confirm = float(c_arm["dti"] - c_ctrl["dti"])
    quad_pos = sum(
        int(s_arm["quadrants"][q] > s_ctrl["quadrants"][q])
        for q in s_arm["quadrants"]
    )
    quad_total = len(s_arm["quadrants"])
    screen_pass = delta_screen >= GATE_DELTA
    quad_pass = quad_pos >= 3
    confirm_pass = delta_confirm > 0.0

    result = {
        "arm": arm_name,
        "control": ctrl_name,
        "screen_dti": float(s_arm["dti"]),
        "screen_control_dti": float(s_ctrl["dti"]),
        "screen_pooled_delta": delta_screen,
        "confirmation_dti": float(c_arm["dti"]),
        "confirmation_control_dti": float(c_ctrl["dti"]),
        "confirmation_pooled_delta": delta_confirm,
        "quadrants_positive": f"{quad_pos}/{quad_total}",
        "screen_pass": bool(screen_pass),
        "quadrant_pass": bool(quad_pass),
        "confirmation_pass": bool(confirm_pass),
    }
    if ablation_name is not None:
        t_screen = float(s_arm["dti"] - screen_cat["arms"][ablation_name]["dti"])
        t_confirm = float(c_arm["dti"] - confirm_cat["arms"][ablation_name]["dti"])
        t_pass = bool(t_screen > 0.0 and t_confirm > 0.0)
        result["transform_delta_screen"] = t_screen
        result["transform_delta_confirmation"] = t_confirm
        result["transform_clause_pass"] = t_pass
        result["promoted"] = bool(screen_pass and quad_pass and confirm_pass and t_pass)
    else:
        result["promoted"] = bool(screen_pass and quad_pass and confirm_pass)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--scarp-tif", type=Path, default=Path("data/raw/external/lidar_scarp_features_u8.tif"))
    parser.add_argument("--sgmc-tif", type=Path, default=Path("data/external/derived_sgmc_faults_100m_u8.tif"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/h33-01-placement-and-scarp-holdout.json"))
    parser.add_argument("--budget", type=int, default=PRIMARY_BUDGET)
    parser.add_argument("--split-seed", type=int, default=31)
    parser.add_argument("--confirm-split-seed", type=int, default=41)
    args = parser.parse_args()

    started = time.time()
    manifest = json.loads((args.data_dir / "manifest.json").read_text())
    features = np.load(args.data_dir / "features_raw.npy", mmap_mode="r")
    footprint = np.load(args.data_dir / "valid.npy") & np.load(args.data_dir / "label_valid.npy")
    catalogue = (np.load(args.data_dir / "labels.npy") == 1) & footprint

    scarp_primary, scarp_ablation = compute_scarp_dipole_fields(
        args.scarp_tif, features, manifest, footprint
    )
    basement_p90, basement_ungated, basement_finite, base_diag = compute_basement_step_ridge_p90(
        features, manifest, footprint
    )

    screen_cat = run_catalogue_split(
        args.split_seed, 17, footprint, catalogue,
        scarp_primary, scarp_ablation, basement_p90, basement_ungated, basement_finite,
        budget=args.budget,
    )
    confirm_cat = run_catalogue_split(
        args.confirm_split_seed, 23, footprint, catalogue,
        scarp_primary, scarp_ablation, basement_p90, basement_ungated, basement_finite,
        budget=args.budget,
    )
    sgmc_frames = run_sgmc_novelty_frames(
        args.sgmc_tif, footprint, catalogue, scarp_primary, budget=args.budget, seed=args.split_seed
    )

    # Evaluate gates
    gate_h31_02r = evaluate_gate_clauses(
        screen_cat, confirm_cat, "scarp_dipole_continuity", "scarp_matched_control", "step_max_only"
    )
    gate_h31_02r_hedge = evaluate_gate_clauses(
        screen_cat, confirm_cat, "scarp_dipole_near_hedge", "scarp_hedge_matched_control", None
    )
    gate_h32_05b = evaluate_gate_clauses(
        screen_cat, confirm_cat, "basement_step_ridge_p90", "basement_matched_control", None
    )

    # Placement policy cross-frame check (H-33-01)
    cat_s_hedge = screen_cat["arms"]["policy_powerlaw_hedge"]["dti"] - screen_cat["arms"]["policy_uniform_domain"]["dti"]
    cat_c_hedge = confirm_cat["arms"]["policy_powerlaw_hedge"]["dti"] - confirm_cat["arms"]["policy_uniform_domain"]["dti"]
    sgmc_u_s = (
        sgmc_frames["unclustered_sgmc_holdout"]["seed_31"]["arms"]["policy_powerlaw_hedge"]["dti"]
        - sgmc_frames["unclustered_sgmc_holdout"]["seed_31"]["arms"]["policy_uniform_domain"]["dti"]
    )
    sgmc_c_s = (
        sgmc_frames["clustered_5km_sgmc_holdout"]["seed_31"]["arms"]["policy_powerlaw_hedge"]["dti"]
        - sgmc_frames["clustered_5km_sgmc_holdout"]["seed_31"]["arms"]["policy_uniform_domain"]["dti"]
    )
    gate_h33_01 = {
        "policy": "policy_powerlaw_hedge vs policy_uniform_domain",
        "catalogue_screen_delta": float(cat_s_hedge),
        "catalogue_confirm_delta": float(cat_c_hedge),
        "sgmc_unclustered_seed31_delta": float(sgmc_u_s),
        "sgmc_clustered_5km_seed31_delta": float(sgmc_c_s),
        "cross_frame_consistent": bool(
            cat_s_hedge >= GATE_DELTA and cat_c_hedge > 0 and sgmc_u_s >= GATE_DELTA and sgmc_c_s >= GATE_DELTA
        ),
        "promoted": bool(
            cat_s_hedge >= GATE_DELTA and cat_c_hedge > 0 and sgmc_u_s >= GATE_DELTA and sgmc_c_s >= GATE_DELTA
        ),
    }

    clumping_recovery = {
        "legacy_unthinned_dti_screen": float(screen_cat["arms"]["basement_unthinned_legacy"]["dti"]),
        "legacy_unthinned_median_nn_px": float(screen_cat["arms"]["basement_unthinned_legacy"]["median_nn_px"]),
        "legacy_unthinned_frac_within_3px": float(screen_cat["arms"]["basement_unthinned_legacy"]["frac_within_3px"]),
        "poisson_thinned_dti_screen": float(screen_cat["arms"]["basement_ungated_poisson"]["dti"]),
        "poisson_thinned_median_nn_px": float(screen_cat["arms"]["basement_ungated_poisson"]["median_nn_px"]),
        "poisson_thinned_frac_within_3px": float(screen_cat["arms"]["basement_ungated_poisson"]["frac_within_3px"]),
        "clumping_fix_multiplier": float(
            screen_cat["arms"]["basement_ungated_poisson"]["dti"]
            / max(screen_cat["arms"]["basement_unthinned_legacy"]["dti"], 1e-9)
        ),
    }

    report = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration": "docs/research/h33-01-placement-and-scarp-preregistration.md",
        "budget": args.budget,
        "poisson_radius_px": POISSON_RADIUS_PX,
        "basement_coherence_diagnostics": base_diag,
        "clumping_confounder_audit_ir_30_033": clumping_recovery,
        "catalogue_component_holdout": {
            "screen": screen_cat,
            "confirmation": confirm_cat,
        },
        "sgmc_novelty_frames": sgmc_frames,
        "gate_results": {
            "h33_01_placement_policy": gate_h33_01,
            "h31_02r_lidar_scarp_continuity": gate_h31_02r,
            "h31_02r_lidar_scarp_near_hedge": gate_h31_02r_hedge,
            "h32_05b_basement_step_p90": gate_h32_05b,
        },
        "any_promoted": bool(
            gate_h33_01["promoted"]
            or gate_h31_02r["promoted"]
            or gate_h31_02r_hedge["promoted"]
            or gate_h32_05b["promoted"]
        ),
        "runtime_seconds": round(time.time() - started, 2),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["gate_results"], indent=2))
    print(json.dumps(report["clumping_confounder_audit_ir_30_033"], indent=2))
    print(f"Wrote {args.output} in {report['runtime_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
