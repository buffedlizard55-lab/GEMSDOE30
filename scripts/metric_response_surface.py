#!/usr/bin/env python3
"""Response-surface analysis of the official GEMS distance-weighted Tversky index (DTI).

Purpose
-------
Answer, with exact arithmetic on the real competition grid, three questions:

1. How does the official metric reward *spatial dispersion* of a prediction
   (dense masks vs. dotted traces) when the truth is a sparse set of thin
   linear features?
2. How much of a score is obtainable from geometry alone ("blind lattice") and
   how much requires *localisation* towards true faults?
3. What (TPw, FPw) operating points produce a target DTI, i.e. what marginal
   false-positive mass can one afford per unit of new true-positive mass?

The official metric, quoted verbatim from the competition problem description
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):

    TPw = sum_{g in G} max_{x : d(x,g) <= R} p(x) * k(d(x,g))
    FPw = sum_{x : p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FNw = sum_{g in G} [1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g))]
    DTI = TPw / (TPw + alpha*FPw + beta*FNw + eps),  alpha=0.2, beta=0.8, R=300 m

IMPORTANT HONESTY BOUND.  The labels available in this checkout are the public
USGS/INGENIOUS *known-fault* catalogue.  The Initial Prize Round is scored
against a *private* set of new expert-labelled faults that is not in that
catalogue.  Every number below computed against the catalogue is therefore a
PROXY; previous work in this repo (docs/research/artifact-structure.json)
already found that catalogue-proxy ordering can be inverted relative to
owner-reported leaderboard ordering.  Proxy values are used here only to study
the *geometry of the metric* (which is exact and label-independent), never to
claim a competition score.
"""

from __future__ import annotations

import sys
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage


# Run from an uninstalled checkout exactly as documented (`python scripts/<name>.py`):
# make the in-repo package importable without `pip install -e .`.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.metric import distance_weighted_tversky

PIXEL_M = 100.0
RADIUS_M = 300.0
ALPHA = 0.2
BETA = 0.8


# --------------------------------------------------------------------------- #
# exact DTI components, specialised for speed on the full 3730x3292 grid
# --------------------------------------------------------------------------- #
def dti_components(pred: np.ndarray, truth: np.ndarray, valid: np.ndarray) -> dict:
    """Exact official DTI components. Thin wrapper over the repo implementation."""
    components = distance_weighted_tversky(
        np.where(valid, pred, np.nan).astype(np.float32),
        np.where(valid, truth, np.nan).astype(np.float32),
        valid,
        pixel_size_x_m=PIXEL_M,
        pixel_size_y_m=PIXEL_M,
        radius_m=RADIUS_M,
        alpha=ALPHA,
        beta=BETA,
    )
    return {
        "tp_weight": components.tp_weight,
        "fp_weight": components.fp_weight,
        "fn_weight": components.fn_weight,
        "dti": components.score,
    }


def dti_fast(pred: np.ndarray, truth: np.ndarray, valid: np.ndarray) -> dict:
    """Vectorised exact DTI for binary/probability rasters (same maths, faster)."""
    p = np.where(valid, pred, 0.0).astype(np.float64)
    g = (truth > 0.5) & valid
    truth_count = float(g.sum())

    # TPw: for every truth pixel, best nearby prediction times triangular kernel.
    credit = np.zeros_like(p)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            distance = math.hypot(dy, dx) * PIXEL_M
            if distance > RADIUS_M:
                continue
            kernel = 1.0 - distance / RADIUS_M
            shifted = np.roll(np.roll(p, dy, axis=0), dx, axis=1) * kernel
            np.maximum(credit, shifted, out=credit)
    if truth_count:
        tp = float(credit[g].sum())
        fn = float(truth_count - tp)
        # FPw: p(x) * min(distance to nearest truth / R, 1)
        distance_px, _ = ndimage.distance_transform_edt(~g, return_indices=True)
        fp = float((p * np.minimum(distance_px * PIXEL_M / RADIUS_M, 1.0)).sum())
    else:
        tp, fn = 0.0, 0.0
        fp = float(p.sum())
    denominator = tp + ALPHA * fp + BETA * fn + 1e-7
    return {"tp_weight": tp, "fp_weight": fp, "fn_weight": fn, "dti": tp / denominator}


# --------------------------------------------------------------------------- #
# prediction constructors
# --------------------------------------------------------------------------- #
def lattice(shape, valid, spacing: int) -> np.ndarray:
    """Blind uniform dot lattice: p=1 on every spacing-th pixel inside the footprint."""
    pred = np.zeros(shape, dtype=np.float32)
    pred[::spacing, ::spacing] = 1.0
    return np.where(valid, pred, 0.0).astype(np.float32)


def zone_lattice(shape, valid, truth, spacing: int, zone_px: int) -> np.ndarray:
    """Blind lattice restricted to a corridor within `zone_px` of *training* faults."""
    if zone_px == 0:
        return np.zeros(shape, dtype=np.float32)
    corridor = ndimage.binary_dilation(truth > 0.5, iterations=zone_px)
    pred = np.zeros(shape, dtype=np.float32)
    pred[::spacing, ::spacing] = 1.0
    return np.where(valid & corridor, pred, 0.0).astype(np.float32)


def dot_paint(mask: np.ndarray, spacing: float, valid: np.ndarray) -> np.ndarray:
    """Coverage-preserving thinning: keep lattice points *on* a mask, drop the rest.

    This is the emission operator implied by the metric's geometry: TPw saturates
    per truth pixel (max over nearby predictions) while FPw accumulates linearly
    with predicted mass, so redundant coverage of the same truth pixel is a pure
    loss.  Keeping a subset of mask pixels with a minimum separation still leaves
    most truth pixels within the 300 m kernel support.
    """
    ys, xs = np.nonzero(mask & valid)
    if not len(ys):
        return np.zeros(mask.shape, dtype=np.float32)
    keep = np.zeros(mask.shape, dtype=bool)
    cell = max(int(round(spacing)), 1)
    occupied = np.zeros(mask.shape, dtype=bool)
    order = np.lexsort((xs, ys))
    for index in order:
        y, x = int(ys[index]), int(xs[index])
        y0, y1 = max(0, y - cell), min(mask.shape[0], y + cell + 1)
        x0, x1 = max(0, x - cell), min(mask.shape[1], x + cell + 1)
        if occupied[y0:y1, x0:x1].any():
            continue
        keep[y, x] = True
        occupied[y, x] = True
    return keep.astype(np.float32)


def kernel_credit_curve() -> list[dict]:
    """Analytic near-miss credit for a single unit-probability prediction."""
    rows = []
    for offset_px in range(0, 6):
        distance = offset_px * PIXEL_M
        # one truth pixel, one prediction pixel offset laterally
        k = max(1.0 - distance / RADIUS_M, 0.0)
        tp = k
        fp = 1.0 - k
        fn = 1.0 - k
        rows.append(
            {
                "offset_m": distance,
                "kernel": k,
                "tp_weight": tp,
                "fp_weight": fp,
                "fn_weight": fn,
                "dti": tp / (tp + ALPHA * fp + BETA * fn + 1e-7),
            }
        )
    return rows


def iso_score_table(targets=(0.20, 0.24, 0.26, 0.28, 0.30, 0.3195, 0.35, 0.40)) -> list[dict]:
    """For each target DTI, report the (TPw, FPw) frontier on a unit truth set.

    DTI = T / (T + 0.2F + 0.8(N - T)) with N = 1.  Rearranged:
        T = (0.2 F + 0.8) * DTI / (1 - 0.8*DTI - 0.2*DTI)
    """
    rows = []
    for target in targets:
        denominator = 1.0 - target * (ALPHA + BETA)
        if denominator <= 0:
            rows.append({"target_dti": target, "feasible": False})
            continue
        row = {"target_dti": target, "feasible": True, "points": []}
        for fp_mass in (0.0, 1.0, 5.0, 20.0, 50.0, 100.0, 200.0):
            tp = (ALPHA * fp_mass + BETA) * target / denominator
            row["points"].append(
                {"fp_mass": fp_mass, "required_tp_mass": min(tp, 1.0), "recall": min(tp, 1.0)}
            )
        # marginal substitution: dF/dT at a reference point (T=target*N... use frontier)
        # dDTI = [(0.2F+0.8N) dT - 0.2T dF] / D^2  ->  dF/dT = (0.2F+0.8N)/(0.2T)
        fp0 = 0.0
        tp0 = (ALPHA * fp0 + BETA) * target / denominator
        row["fp_per_extra_tp_at_fp0"] = (ALPHA * fp0 + BETA) / (ALPHA * tp0)
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=Path("data/raw/labels.tif"))
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--owner-tif", type=Path,
                        default=Path("docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/metric-response-surface.json"))
    args = parser.parse_args()

    started = time.time()
    with rasterio.open(args.labels) as ds:
        labels = ds.read(1).astype(np.int8)
        profile = ds.profile
    with rasterio.open(args.template) as ds:
        template = ds.read(1)
    valid = labels >= 0
    footprint = np.isfinite(template) & valid
    truth = (labels == 1) & valid
    truth_count = int(truth.sum())
    catalog_density = truth_count / float(valid.sum())

    result: dict = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "grid": {
            "height": int(profile["height"]),
            "width": int(profile["width"]),
            "valid_pixels": int(valid.sum()),
            "scored_footprint_pixels": int(footprint.sum()),
            "catalogue_truth_pixels": truth_count,
            "catalogue_density": catalog_density,
            "pixel_m": PIXEL_M,
            "radius_m": RADIUS_M,
            "alpha": ALPHA,
            "beta": BETA,
        },
        "proxy_caveat": (
            "All DTIs computed against the public catalogue. The Initial Prize Round is scored "
            "against a private set of NEW expert-labelled faults; catalogue density is almost "
            "certainly an upper bound on that set's density, so geometry-only numbers here are "
            "an OPTIMISTIC bound for the real private test."
        ),
        "analytic_near_miss_curve": kernel_credit_curve(),
        "iso_score_table": iso_score_table(),
    }

    # ---- 1. blind lattice sweep -------------------------------------------------
    lattice_sweep = []
    for spacing in (1, 2, 3, 4, 5, 6, 8):
        pred = lattice(labels.shape, footprint, spacing)
        metrics = dti_fast(pred, truth, footprint)
        lattice_sweep.append(
            {
                "spacing_px": spacing,
                "spacing_m": spacing * PIXEL_M,
                "emitted_pixels": int((pred > 0).sum()),
                **metrics,
            }
        )
        print("lattice", spacing, round(metrics["dti"], 4), flush=True)
    result["blind_lattice_sweep"] = lattice_sweep

    # ---- 2. localised lattice sweep (accuracy vs dispersion) --------------------
    localised = []
    for zone_px in (0, 1, 2, 4, 8, 16):
        for spacing in (2, 3, 4):
            pred = zone_lattice(labels.shape, footprint, truth, spacing, zone_px)
            if pred.sum() == 0:
                continue
            metrics = dti_fast(pred, truth, footprint)
            localised.append(
                {
                    "zone_px": zone_px,
                    "spacing_px": spacing,
                    "emitted_pixels": int((pred > 0).sum()),
                    **metrics,
                }
            )
            print("zone", zone_px, "spacing", spacing, round(metrics["dti"], 4), flush=True)
    result["corridor_lattice_sweep"] = localised

    # ---- 3. re-emission of the owner's archived D2.8 prediction -----------------
    owner_rows = []
    if args.owner_tif.exists():
        with rasterio.open(args.owner_tif) as ds:
            owner = ds.read(1).astype(np.float32)
        owner = np.nan_to_num(owner, nan=0.0)
        owner_mask = owner > 0.5
        base = dti_fast(owner, truth, footprint)
        owner_rows.append({"variant": "as-published", "emitted_pixels": int(owner_mask.sum()), **base})
        for spacing in (1.5, 2.0, 2.8, 3.5, 4.0, 5.0):
            thinned = dot_paint(owner_mask, spacing, footprint)
            metrics = dti_fast(thinned, truth, footprint)
            owner_rows.append(
                {
                    "variant": f"dot-thinned-{spacing}px",
                    "emitted_pixels": int(thinned.sum()),
                    **metrics,
                }
            )
            print("owner thinning", spacing, round(metrics["dti"], 4), flush=True)
        # recovery: the metric-optimal re-emission of a *perfect* mask
        ideal = dot_paint(truth, 3.0, footprint)
        owner_rows.append(
            {
                "variant": "oracle-thinned-3px (perfect localisation, dotted)",
                "emitted_pixels": int(ideal.sum()),
                **dti_fast(ideal, truth, footprint),
            }
        )
        ideal_dense = truth.astype(np.float32)
        owner_rows.append(
            {
                "variant": "oracle-dense (perfect localisation, solid)",
                "emitted_pixels": int(ideal_dense.sum()),
                **dti_fast(ideal_dense, truth, footprint),
            }
        )
    result["emission_operator_study"] = owner_rows

    # ---- 4. truth-density sensitivity ------------------------------------------
    # Sparse the catalogue by keeping whole connected components (emulates a test
    # set of a *few* new faults rather than the full catalogue), then compare a
    # blind lattice with a perfect-localisation / limited-recall oracle.
    components, count = ndimage.label(truth, structure=np.ones((3, 3)))
    rng = np.random.default_rng(20261003)
    density_rows = []
    for fraction in (1.0, 0.5, 0.25, 0.10, 0.04):
        if fraction >= 1.0:
            subset = truth.copy()
        else:
            keep = rng.random(count + 1) < fraction
            keep[0] = False
            subset = keep[components]
        subset_count = float(subset.sum())
        if subset_count == 0:
            continue
        blind = dti_fast(lattice(labels.shape, footprint, 4), subset, footprint)
        # "oracle-localised, limited recall": emit dots on a random 60% of truth
        partial = subset & (rng.random(subset.shape) < 0.6)
        oracle = dti_fast(dot_paint(partial, 3.0, footprint), subset, footprint)
        density_rows.append(
            {
                "truth_fraction_of_catalogue": fraction,
                "truth_pixels": int(subset_count),
                "density": subset_count / float(footprint.sum()),
                "blind_lattice_4px_dti": blind["dti"],
                "oracle_60pct_recall_3px_dots_dti": oracle["dti"],
            }
        )
        print("density", fraction, round(blind["dti"], 4), round(oracle["dti"], 4), flush=True)
    result["density_sensitivity"] = density_rows

    result["elapsed_s"] = round(time.time() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {args.output} in {result['elapsed_s']}s")


if __name__ == "__main__":
    main()
