#!/usr/bin/env python3
"""H-33-01 — placement-policy holdout on the independent-inventory (novelty) frame.

Preregistered 2026-10-03 in ``docs/research/h33-01-preregistration.md``; this file implements
exactly that design.  Question: given one ranking field and one fixed emission budget, how
should dots be stratified by distance to the public fault catalogue — ``near`` = (300 m,
600 m], ``mid`` = (600 m, 1200 m], ``far`` = beyond — and does the winning split beat the
standing budget-matched controls?

Frame: USGS SGMC components, 30 % hidden; domain = footprint minus the catalogue dilated by
3 px (the organizer's masking rule); exact masked DTI (alpha = 0.2, triangular kernel,
R = 300 m).  Arms fill exact per-band quotas from greedy 4 px Poisson-disk pools ordered by
the stitched OOF UNet score (threshold 0.4); controls are budget-matched uniform random dots
over the whole domain and budget-matched uniform random dots within the same strata.  No arm
uses the SGMC layer except as hidden truth.

Nothing here is a competition score; a pass promotes a *placement rule for candidate
construction on this frame*, nothing more.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import (  # noqa: E402
    _select,  # private, imported deliberately for the legacy-order reference emulation
    dti_from_components,
    kernel_credit,
    poisson_disk_select_ordered,
)

BANDS = ("near", "mid", "far")
FRACTIONS = {"P0": 0.0, "P25": 0.25, "P50": 0.5, "P75": 0.75, "P100": 1.0}
ARM_NAMES = ["blind_random_B", "historical_d28", "f_nat", "f_nat_legacy", "P_rank"] \
    + list(FRACTIONS) + [f"rand_{name}" for name in FRACTIONS]


def legacy_ordered_pool(score: np.ndarray, mask: np.ndarray, radius_px: float,
                        pool_limit: int | None, max_kept: int | None):
    """Reference emulation of the pre-fix *column-major* visit order (IR-30-031) so this
    run can be compared against the 2026-10-03 emitter benchmarks that used it.  The
    deliberately legacy ``np.lexsort`` key below is the bug under documentation, not an
    accident of this script."""
    values = np.where(mask, np.asarray(score, dtype=np.float32), -np.inf)
    rows, cols = np.nonzero(np.isfinite(values))
    if rows.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    if pool_limit is not None and rows.size > pool_limit:
        flat = np.argpartition(-values[rows, cols], pool_limit)[:pool_limit]
        rows, cols = rows[flat], cols[flat]
    order = np.lexsort((-values[rows, cols], rows, cols))  # legacy key on purpose
    rows, cols = rows[order], cols[order]
    radii = np.full(rows.size, float(radius_px), dtype=np.float32)
    kept = _select(np.zeros(score.shape, dtype=np.float32), radii, rows, cols,
                   max_kept=int(max_kept) if max_kept is not None else None)
    accepted = np.nonzero(kept[rows, cols])[0]
    if max_kept is not None:
        accepted = accepted[:int(max_kept)]
    return rows[accepted], cols[accepted]


def build_band_masks(catalogue: np.ndarray, domain: np.ndarray, buffer_px: int = 3):
    """Return (band_masks, distance_px).  ``distance_px`` is Euclidean pixel distance to the
    nearest catalogue pixel (0 on the catalogue itself).  near = (buffer, 2*buffer],
    mid = (2*buffer, 4*buffer], far = beyond; all intersected with ``domain``."""
    from scipy.ndimage import distance_transform_edt

    distance = distance_transform_edt(~catalogue)
    near = domain & (distance > buffer_px) & (distance <= 2 * buffer_px)
    mid = domain & (distance > 2 * buffer_px) & (distance <= 4 * buffer_px)
    far = domain & (distance > 4 * buffer_px)
    return {"near": near, "mid": mid, "far": far}, distance


def greedy_ordered_pool(score: np.ndarray, mask: np.ndarray, radius_px: float,
                        pool_limit: int | None, max_kept: int | None):
    """Descending-score greedy Poisson-disk selection restricted to ``mask``, returning the
    kept pixels **in acceptance order** (rows, cols).  Thin wrapper over
    :func:`gemsdoe30.emission.poisson_disk_select_ordered` with the score floor applied via
    the caller's ``mask`` (so the pool is exactly "pixels the arm is allowed to emit").
    ``max_kept`` early-stops at the first K acceptances; no score cap is applied by default
    (the earlier 200 k candidate cap made every quota arm degenerate to the same union —
    recorded in the run's ``capacity`` block)."""
    allowed = mask & np.isfinite(score)
    return poisson_disk_select_ordered(np.asarray(score, dtype=np.float32), float(radius_px),
                                       mask=allowed, limit=pool_limit, max_kept=max_kept)


def quotas_for(frac: float, budget: int) -> dict:
    near = int(round(frac * budget))
    rest = budget - near
    return {"near": near, "mid": rest // 2, "far": rest - rest // 2}


def fill_quotas(pools: dict, quotas: dict, total: int):
    """Take ``quotas[band]`` prefix pixels from each band pool; distribute any shortfall in
    the frozen order mid -> far -> near (continuing each pool's descending order).  Returns
    concatenated (rows, cols), actual per-band counts, and overflow bookkeeping."""
    taken = {band: min(int(quotas.get(band, 0)), len(pools[band][0])) for band in BANDS}
    overflow = {"mid": 0, "far": 0, "near": 0}
    short = total - sum(taken.values())
    for band in ("mid", "far", "near"):
        if short <= 0:
            break
        extra = min(short, len(pools[band][0]) - taken[band])
        if extra > 0:
            taken[band] += extra
            overflow[band] += extra
            short -= extra
    if short > 0:  # pools exhausted overall: emit fewer than B, recorded not hidden
        overflow["unfilled"] = int(short)
    parts_rows = [pools[band][0][: taken[band]] for band in BANDS]
    parts_cols = [pools[band][1][: taken[band]] for band in BANDS]
    rows = np.concatenate(parts_rows) if any(taken.values()) else np.empty(0, np.int64)
    cols = np.concatenate(parts_cols) if any(taken.values()) else np.empty(0, np.int64)
    return rows, cols, taken, overflow


def score_emitter(rows, cols, shape, domain: np.ndarray, truth: np.ndarray,
                  fp_weight: np.ndarray, truth_count: float, alpha: float = 0.2,
                  bands: dict | None = None):
    """Exact masked-DTI sufficient statistics for a unit-valued dot emitter sharing the
    per-repeat truth-distance field (the emitter side is the kernel max and masked sums)."""
    field = np.zeros(shape, dtype=np.float32)
    if len(rows):
        field[rows, cols] = 1.0
    field[~domain] = 0.0
    if not field.any():
        out = {"dti": 0.0, "tp_weight": 0.0, "fp_weight": 0.0, "dots": 0,
               "truth_pixels": float(truth_count)}
    else:
        credit = kernel_credit(field, pixel_size_m=100.0, radius_m=300.0)
        tp = float(credit[truth].sum(dtype=np.float64))
        fp = float((field * fp_weight).sum(dtype=np.float64))
        out = {
            "dti": float(dti_from_components(tp, fp, truth_count, alpha=alpha)),
            "tp_weight": tp,
            "fp_weight": fp,
            "dots": int(field.sum()),
            "truth_pixels": float(truth_count),
        }
    if bands is not None:
        for name, band in bands.items():
            out[f"dots_{name}"] = int(np.count_nonzero(field[band]))
    return out


def random_pixels(mask: np.ndarray, count: int, rng: np.random.Generator):
    flat = np.flatnonzero(mask.ravel())
    if count <= 0 or flat.size == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    pick = rng.choice(flat, size=min(count, flat.size), replace=False)
    width = mask.shape[1]
    return pick // width, pick % width


def aggregate(detail: list, arms: list) -> dict:
    out = {}
    for arm in arms:
        values = np.array([entry["arms"][arm]["dti"] for entry in detail], dtype=np.float64)
        dots = np.array([entry["arms"][arm]["dots"] for entry in detail], dtype=np.float64)
        out[arm] = {
            "mean_dti": float(values.mean()),
            "min_dti": float(values.min()),
            "max_dti": float(values.max()),
            "mean_dots": float(dots.mean()),
            "mean_dots_near": float(np.mean([entry["arms"][arm].get("dots_near", 0)
                                             for entry in detail])),
            "mean_dots_mid": float(np.mean([entry["arms"][arm].get("dots_mid", 0)
                                            for entry in detail])),
            "mean_dots_far": float(np.mean([entry["arms"][arm].get("dots_far", 0)
                                            for entry in detail])),
            "repeats": len(values),
        }
    return out


def paired(detail: list, a: str, b: str) -> dict:
    da = np.array([entry["arms"][a]["dti"] for entry in detail])
    db = np.array([entry["arms"][b]["dti"] for entry in detail])
    delta = da - db
    return {"arm": a, "control": b,
            "mean_delta": float(delta.mean()),
            "wins": int((delta > 0).sum()), "repeats": int(delta.size),
            "per_repeat_delta": [round(float(v), 6) for v in delta]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--external-dir", type=Path, default=ROOT / "data/external")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--model-oof", type=Path, default=ROOT / "runs/oof/regional-oof.npy")
    parser.add_argument("--artefact", type=Path,
                        default=ROOT / "docs/downloads/"
                                       "gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "docs/research/h33-01-placement-policy-holdout.json")
    parser.add_argument("--budgets", default="80000,40000")
    parser.add_argument("--spacing-px", type=float, default=4.0)
    parser.add_argument("--threshold", type=float, default=0.4)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--screen-seed", type=int, default=30)
    parser.add_argument("--confirm-seed", type=int, default=31)
    parser.add_argument("--holdout-fraction", type=float, default=0.3)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--pool-limit", type=int, default=0,
                        help="legacy score cap on pool candidates; 0 = no cap (the cap made "
                             "quota arms degenerate; kept only for reproducing old runs)")
    parser.add_argument("--diagnostic-budgets", default="12000,30000",
                        help="secondary un-gated budgets where band capacities are not "
                             "(12000) or only partly (30000) binding")
    parser.add_argument("--buffer-px", type=int, default=3)
    args = parser.parse_args()

    import rasterio
    from scipy.ndimage import binary_dilation, label

    t0 = time.time()
    with rasterio.open(args.template) as dataset:
        footprint = np.isfinite(dataset.read(1))
    labels = np.load(args.data_dir / "labels.npy")
    catalogue = (labels == 1) & footprint
    domain = footprint & ~binary_dilation(catalogue, iterations=args.buffer_px)

    with rasterio.open(args.external_dir / "derived_sgmc_faults_100m_u8.tif") as dataset:
        inventory = (dataset.read(1) > 0) & footprint
    components, component_count = label(inventory, structure=np.ones((3, 3), dtype=np.uint8))
    component_ids = np.nonzero(np.bincount(components.ravel()))[0]
    component_ids = component_ids[component_ids != 0]

    if not args.model_oof.is_file():
        raise FileNotFoundError(f"missing stitched OOF field: {args.model_oof} "
                                "(run scripts/run_oof_inference.sh for the regional arm first)")
    mosaic = np.load(args.model_oof)
    score = np.where(footprint, np.nan_to_num(np.asarray(mosaic, dtype=np.float32), nan=0.0), 0.0)
    score = np.clip(score, 0.0, 1.0)

    with rasterio.open(args.artefact) as dataset:
        plane = np.nan_to_num(dataset.read(1), nan=0.0)
    artefact_field = footprint & (plane > 0)

    bands, distance_px = build_band_masks(catalogue, domain, buffer_px=args.buffer_px)
    shape = footprint.shape
    budgets = [int(v) for v in args.budgets.split(",")]
    gate_budget = budgets[0]

    emittable = domain & (score > args.threshold)
    print(f"domain {int(domain.sum())} px; band areas near {int(bands['near'].sum())}, "
          f"mid {int(bands['mid'].sum())}, far {int(bands['far'].sum())}; "
          f"score>{args.threshold} in domain {int(emittable.sum())}", flush=True)

    max_kept = max(budgets)
    pool_limit = args.pool_limit if args.pool_limit > 0 else None
    pools = {}
    for band in BANDS:
        rr, cc = greedy_ordered_pool(score, bands[band] & emittable, args.spacing_px,
                                     pool_limit, max_kept)
        pools[band] = (rr, cc)
        print(f"  pool {band}: {rr.size} spaced candidates (max_kept {max_kept})", flush=True)
    full_rows, full_cols = greedy_ordered_pool(score, emittable, args.spacing_px, pool_limit,
                                               max_kept)
    pools["__full__"] = (full_rows, full_cols)
    # NOTE: full-domain pool uses the same early-stop bound
    print(f"  pool full-domain: {full_rows.size} spaced candidates", flush=True)
    pools["__full_legacy__"] = legacy_ordered_pool(score, emittable, args.spacing_px,
                                                    pool_limit, max_kept)

    # deterministic whole-grid proximity order for P_rank (computed once)
    prox_key = np.lexsort((np.arange(distance_px.size, dtype=np.int64), distance_px.ravel()))
    prox_key = prox_key[domain.ravel()[prox_key]]

    def truth_of_factory(repeat_seed: int):
        cache: dict[int, np.ndarray] = {}

        def truth_of(r: int):
            if r not in cache:
                rng = np.random.default_rng(repeat_seed * 31 + r)
                shuffled = rng.permutation(component_ids)
                held = shuffled[: int(round(args.holdout_fraction * shuffled.size))]
                cache[r] = np.isin(components, held) & domain
            return cache[r]
        return truth_of

    def run_arms(seed: int, budget: int):
        from scipy.ndimage import distance_transform_edt

        truth_of = truth_of_factory(seed)
        detail = []
        for r in range(args.repeats):
            truth = truth_of(r)
            fp_weight = np.minimum(distance_transform_edt(~truth, sampling=(100.0, 100.0))
                                   / 300.0, 1.0)
            truth_count = float(np.count_nonzero(truth))
            rng_rep = np.random.default_rng(seed * 7919 + r)
            entry = {"repeat": r, "hidden_truth_pixels_in_domain": truth_count, "arms": {}}

            def emit(rows, cols):
                return score_emitter(rows, cols, shape, domain, truth, fp_weight, truth_count,
                                     args.alpha, bands)

            for name in ARM_NAMES:
                if name in FRACTIONS:
                    quotas = quotas_for(FRACTIONS[name], budget)
                    rows, cols, _taken, overflow = fill_quotas(pools, quotas, budget)
                    record = emit(rows, cols)
                    record["quota_target"] = quotas
                    record["overflow_added"] = {k: int(v) for k, v in overflow.items()}
                elif name.startswith("rand_"):
                    quotas = quotas_for(FRACTIONS[name[5:]], budget)
                    rr_parts, cc_parts = [], []
                    for band in BANDS:
                        a, b = random_pixels(bands[band], int(quotas.get(band, 0)), rng_rep)
                        rr_parts.append(a)
                        cc_parts.append(b)
                    record = emit(np.concatenate(rr_parts), np.concatenate(cc_parts))
                elif name == "blind_random_B":
                    rows, cols = random_pixels(domain, budget, rng_rep)
                    record = emit(rows, cols)
                elif name == "P_rank":
                    key = prox_key[:budget]
                    record = emit(key // shape[1], key % shape[1])
                elif name == "f_nat":
                    record = emit(full_rows[:budget], full_cols[:budget])
                elif name == "f_nat_legacy":
                    lr, lc = pools["__full_legacy__"]
                    record = emit(lr[:budget], lc[:budget])
                elif name == "historical_d28":
                    rr, cc = np.nonzero(artefact_field & domain)
                    record = emit(rr, cc)
                else:
                    raise ValueError(name)
                entry["arms"][name] = record
            detail.append(entry)
            print(f"[seed {seed} B{budget} r{r}] " + "  ".join(
                f"{n}={entry['arms'][n]['dti']:.5f}" for n in ARM_NAMES), flush=True)
        return detail

    screen = run_arms(args.screen_seed, gate_budget)

    means = {name: float(np.mean([e["arms"][name]["dti"] for e in screen])) for name in FRACTIONS}
    # Frozen rule from the preregistration: if P100 cannot even fill a quarter of the budget
    # from the near pool, it is reported but excluded from f*-selection.
    p100_near = float(np.mean([e["arms"]["P100"].get("dots_near", 0) for e in screen]))
    p100_excluded = p100_near < 0.25 * gate_budget
    selection_means = dict(means)
    if p100_excluded:
        selection_means.pop("P100")
    f_star = max(selection_means, key=selection_means.get)

    g1 = paired(screen, f_star, "blind_random_B")
    g2 = paired(screen, f_star, "P0")
    g3 = paired(screen, f_star, f"rand_{f_star}")
    capacity_block = {
        "pool_sizes": {b: int(pools[b][0].size) for b in BANDS},
        "pool_full": int(full_rows.size),
        "pool_full_legacy": int(pools["__full_legacy__"][0].size),
        "mean_dots_by_arm_at_gate_budget": {
            name: float(np.mean([e["arms"][name]["dots"] for e in screen]))
            for name in FRACTIONS},
        "gate_budget": gate_budget,
        "gate_arms_collapse_identical": False,
        "total_pool_capacity_all_bands": int(sum(pools[b][0].size for b in BANDS)),
    }
    capacity_block["gate_arms_collapse_identical"] = bool(
        len({round(v, 6) for v in
             capacity_block["mean_dots_by_arm_at_gate_budget"].values()}) == 1
        and max(capacity_block["mean_dots_by_arm_at_gate_budget"].values()) < gate_budget)
    report = {
        "script": "scripts/placement_policy_holdout.py",
        "preregistration": "docs/research/h33-01-preregistration.md",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": {"shape_hw": list(shape), "footprint_pixels": int(footprint.sum()),
                 "domain_pixels": int(domain.sum()), "band_areas_px":
                 {b: int(bands[b].sum()) for b in BANDS}},
        "field": {"model_oof": str(args.model_oof),
                  "sha256": hashlib.sha256(args.model_oof.read_bytes()).hexdigest()},
        "protocol": {"frame": "SGMC hidden-component novelty frame; catalogue dilated by "
                              f"{args.buffer_px} px excluded from the scored domain",
                     "budgets": budgets, "gate_budget": gate_budget,
                     "spacing_px": args.spacing_px, "threshold": args.threshold,
                     "repeats": args.repeats, "screen_seed": args.screen_seed,
                     "confirm_seed": args.confirm_seed,
                     "holdout_fraction": args.holdout_fraction, "alpha": args.alpha,
                     "radius_m": 300.0, "pool_limit": args.pool_limit,
                     "inventory_components": int(component_ids.size)},
        "screen_summary": aggregate(screen, sorted(ARM_NAMES)),
        "screen_repeats": screen,
        "capacity": capacity_block,
        "f_star": {"arm": f_star, "fraction_near": FRACTIONS[f_star], "arm_means_at_gate_budget": means,
                   "p100_excluded_from_selection_shortfall": p100_excluded,
                   "p100_mean_dots_near": p100_near},
    }

    g4 = None
    # Void guard: the frozen arm table requires every arm to "fill the exact budget B".
    # If every P-arm collapsed onto the same union (pool capacity < B) the same-count
    # standard inherited from the verification protocol is violated and no gate can be
    # adjudicated at the gate budget; record it as VOID rather than a pass.
    collapsed = bool(report["capacity"]["gate_arms_collapse_identical"])
    screen_ok = (not collapsed
                 and g1["mean_delta"] >= 0.005 and g1["wins"] >= 4
                 and g2["mean_delta"] > 0 and g2["wins"] >= 4
                 and g3["mean_delta"] >= 0.0)
    if collapsed:
        report["gates_void_reason"] = (
            "gate-budget arms are capacity-collapsed (mean dots "
            f"{max(report['capacity']['mean_dots_by_arm_at_gate_budget'].values()):,} < "
            f"{gate_budget:,}); comparisons against exactly-B controls are not count-"
            "matched, violating the frozen 'fill the exact budget B' construction; the "
            "diagnostic budgets below are the substantive evidence and the next "
            "preregistration must choose a gate budget at which all arms are realisable")
    if screen_ok:
        confirm = run_arms(args.confirm_seed, gate_budget)
        g4 = paired(confirm, f_star, "blind_random_B")
        g4b = paired(confirm, f_star, "P0")
        means_c = {name: float(np.mean([e["arms"][name]["dti"] for e in confirm]))
                   for name in FRACTIONS}
        if float(np.mean([e["arms"]["P100"].get("dots_near", 0) for e in confirm])) \
                < 0.25 * gate_budget:
            means_c.pop("P100")
        f_star_c = max(means_c, key=means_c.get)
        g4 = {"vs_blind": g4, "vs_P0": g4b,
              "confirm_f_star": f_star_c,
              "f_star_agrees_within_one_step":
                  abs(list(FRACTIONS).index(f_star_c) - list(FRACTIONS).index(f_star)) <= 1}
        report["confirm_summary"] = aggregate(confirm, sorted(ARM_NAMES))
        report["confirm_repeats"] = confirm
        report["confirm_f_star"] = {"arm": f_star_c, "means": means_c}
    else:
        report["confirmation_note"] = ("screen gates failed; confirmation seed 31 was not "
                                      "run (the frozen rule requires the screen first)")

    pass_all = (screen_ok and g4 is not None and g4["vs_blind"]["mean_delta"] > 0
                and g4["vs_blind"]["wins"] >= 3 and g4["f_star_agrees_within_one_step"])
    sensitivity: dict = {}
    for budget in budgets[1:]:
        detail_b = run_arms(args.screen_seed, budget)
        means_b = {name: float(np.mean([e["arms"][name]["dti"] for e in detail_b]))
                   for name in FRACTIONS}
        sensitivity[f"B{budget}"] = {
            "summary": aggregate(detail_b, sorted(ARM_NAMES)),
            "means_by_fraction": means_b,
            "f_star_at_this_budget": max(means_b, key=means_b.get),
        }
    report["sensitivity_budgets"] = sensitivity

    # Degeneracy audit of the gate-budget screen: at B=80k the score-thresholded, 4 px
    # thinned pools can be smaller than the quota, which collapses all P-arms onto the same
    # union.  We record this instead of hiding it, and add an un-gated diagnostic at a
    # smaller budget where the bands are not capacity-bound.
    diags = {}
    for db in [int(v) for v in args.diagnostic_budgets.split(",") if v.strip()]:
        diag_detail = run_arms(args.screen_seed, db)
        means_d = {name: float(np.mean([e["arms"][name]["dti"] for e in diag_detail]))
                   for name in FRACTIONS}
        dots_d = {name: float(np.mean([e["arms"][name]["dots"] for e in diag_detail]))
                  for name in FRACTIONS}
        f_star_d = max(means_d, key=means_d.get)
        diags[f"B{db}"] = {
            "budget": db,
            "note": ("un-gated diagnostic at a budget the frozen band capacities can "
                     "supply; informs the *next* preregistration, never this promotion "
                     "decision"),
            "summary": aggregate(diag_detail, sorted(ARM_NAMES)),
            "means_by_fraction": means_d,
            "mean_dots_by_arm": dots_d,
            "all_arms_fill_budget": all(abs(v - db) < 1e-9 for v in dots_d.values()),
            "f_star_diagnostic": f_star_d,
            "vs_blind": paired(diag_detail, f_star_d, "blind_random_B"),
            "vs_P0": paired(diag_detail, f_star_d, "P0"),
            "vs_rand_same_split": paired(diag_detail, f_star_d, f"rand_{f_star_d}"),
            "gated": False,
        }
    report["diagnostic_budgets"] = diags

    report["gates"] = {
        "G1_vs_blind_random": g1, "G2_vs_all_far": g2, "G3_ranking_value_at_fstar": g3,
        "G4_confirmation": g4,
        "sensitivity_P_rank_minus_fstar": paired(screen, "P_rank", f_star),
        "sensitivity_fnat_vs_fstar": paired(screen, "f_nat", f_star),
        "pass": bool(pass_all),
    }
    report["decision"] = (
        "Placement split promoted on this frame for candidate construction (a placement rule, "
        "not a submission approval)" if pass_all else
        "Not promoted; the incumbent whole-domain model-score emission stands")
    report["notes"] = [
        "Frame limitation: hidden truth is USGS SGMC components, a proxy for the organizers'",
        "private expert faults; no number here is a competition score or a slot approval.",
        "Emitters are budget-matched at the gate budget; the historical D2.8 artefact is",
        "reported at its own count and is a calibration reference only.",
    ]
    report["elapsed_seconds"] = round(time.time() - t0, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"f_star": f_star, "G1": g1["mean_delta"], "G2": g2["mean_delta"],
                      "G3": g3["mean_delta"], "pass": bool(pass_all),
                      "elapsed": report["elapsed_seconds"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
