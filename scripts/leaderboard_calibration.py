#!/usr/bin/env python3
"""Leaderboard-calibrated truth density and marginal hit-rate decomposition.

Uses only (a) owner-reported public-leaderboard scores (UNVERIFIED, labelled as such),
(b) the exact published metric, and (c) the scored rasters themselves. No hidden labels.

1. Calibrate the hidden new-fault pixel density rho from the exact 5-px uniform lattice
   ``r13-lattice-s5`` (owner-reported 0.0904). A uniform lattice is label-blind, so its
   score depends on the truth only through rho (and weakly on line geometry, which we
   take from the catalogue itself).
2. Convert every isolated-dot raster's reported score into an implied TP mass per scored
   pixel and an implied per-dot hit rate.
3. For nested pairs (base -> modification) decompose the score change into the implied
   hit rate of the *changed* dots (e.g. the near-catalogue prune behind H33).

Every derived number is a PROJECTION conditional on the owner-reported scores and on the
stated approximations; none is a score.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

LATTICE = "data/raw/scored/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
LATTICE_SCORE = 0.0904
# Isolated-dot rasters with owner-reported scores (site, score, path).
DOTTED = [
    ("GEMSDOE24 d1.5", 0.2477, "data/raw/scored/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE25/30 d2.8", 0.2600, "data/raw/scored/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE28 r1-solo-d2.8", 0.2708, "gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif"),
    ("GEMSDOE31 solo-d28", 0.2708, "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32 H33-B2", 0.2778, "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE28 prethin-tip-euler", 0.2649, "gems28-h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-allfinite.tif"),
    ("GEMSDOE28 rung30-blind-r1", 0.2710, "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif"),
    ("GEMSDOE28 hf-euler-r30-r1", 0.2707, "gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-allfinite.tif"),
    ("GEMSDOE33 tip-stepover-r30", 0.2632, "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e-nanoutside.tif"),
    ("GEMSDOE36 anderson-pinn", 0.2750, "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-nan.tif"),
    ("GEMSDOE27 gap-closure-on-d1.5", 0.2449, "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif"),
]
PAIRS = [
    ("GEMSDOE25/30 d2.8", "GEMSDOE28 r1-solo-d2.8"),
    ("GEMSDOE28 r1-solo-d2.8", "GEMSDOE32 H33-B2"),
    ("GEMSDOE25/30 d2.8", "GEMSDOE32 H33-B2"),
    ("GEMSDOE24 d1.5", "GEMSDOE25/30 d2.8"),
    ("GEMSDOE24 d1.5", "GEMSDOE27 gap-closure-on-d1.5"),
    ("GEMSDOE25/30 d2.8", "GEMSDOE33 tip-stepover-r30"),
    ("GEMSDOE25/30 d2.8", "GEMSDOE28 prethin-tip-euler"),
    ("GEMSDOE28 r1-solo-d2.8", "GEMSDOE28 rung30-blind-r1"),
    ("GEMSDOE28 r1-solo-d2.8", "GEMSDOE28 hf-euler-r30-r1"),
    ("GEMSDOE32 H33-B2", "GEMSDOE36 anderson-pinn"),
]
BINS = [0, 1.5, 2.5, 5.5, 10.5, 15.5, 30.5, 50.5, 1e9]
BIN_NAMES = ["1", "2", "3-5", "6-10", "11-15", "16-30", "31-50", ">50"]


def read(path: Path):
    import rasterio
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float32)
    return np.where(np.isfinite(a), a, 0.0)


def resolve(name: str) -> Path:
    p = ROOT / name
    if p.exists():
        return p
    reg = json.loads((ROOT / "docs/research/texture-displacement/registry.json").read_text())["rasters"]
    for r in reg:
        if r["source_path"].endswith(name):
            return ROOT / r["path"]
    raise FileNotFoundError(name)


def implied_tp_density(score: float, n: float, rho: float, sk_over_t: float = 1 / 3) -> float:
    """T/A from s = T/(0.2T + 0.2(N - Sk) + 0.8G), Sk = sk_over_t*T, G = rho*A."""
    return score * (0.2 * n + 0.8 * rho) / (1.0 - 0.2 * score + 0.2 * sk_over_t * score)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "docs/research/2026-10-25-lsm/leaderboard-calibration.json")
    args = ap.parse_args()
    from scipy.ndimage import distance_transform_edt
    from gemsdoe30.holdout import max_kernel_credit

    labels = np.load(ROOT / "data/processed/labels.npy")
    valid = np.load(ROOT / "data/processed/valid.npy")
    cat = labels == 1
    domain = valid & ~cat
    area = float(domain.sum())
    dist = distance_transform_edt(~cat)

    lattice = read(ROOT / LATTICE) > 0
    lam = float((lattice & domain).sum()) / area
    credit = max_kernel_credit(lattice.astype(np.float32))
    c_line = float(credit[cat].mean())  # coverage per truth pixel for line-like truth
    k_dot = np.clip(1 - dist / 3.0, 0, None)
    kappa = float(k_dot[lattice & domain].sum()) / float(cat.sum())
    s = LATTICE_SCORE

    def rho_for(c):
        return 0.2 * lam * s / (c - 0.2 * c * s + 0.2 * kappa * s - 0.8 * s)

    rho = rho_for(c_line)
    sens = {f"c_x{f}": rho_for(c_line * f) for f in (0.9, 1.1)}
    out = {
        "label": "PROJECTION from OWNER-REPORTED UNVERIFIED scores; not a score",
        "metric": "DTI = T/(0.2T+0.2F+0.8G), 300 m triangular kernel, pooled (official forum t/11550)",
        "lattice": {"path": LATTICE, "owner_reported_score": s, "dots_per_scored_px": lam,
                    "line_coverage_per_truth_px_c": c_line, "kappa_sum_k_per_truth_px": kappa,
                    "implied_truth_density_rho": rho, "rho_sensitivity_c_pm10pct": sens,
                    "implied_truth_px_if_all_scored_area": rho * area,
                    "catalogue_density": float(cat.sum()) / float(valid.sum())},
        "rasters": {}, "pairs": [],
    }
    masks = {}
    for name, score, path in DOTTED:
        a = read(resolve(path))
        m = (a > 0) & domain
        masks[name] = m
        n = float(a[m].sum()) / area
        t = implied_tp_density(score, n, rho)
        hist = np.histogram(dist[m], bins=BINS)[0]
        out["rasters"][name] = {
            "owner_reported_score": score, "path": path, "dots_in_scored_domain": int(m.sum()),
            "values": sorted(set(np.unique(a[valid]).round(6).tolist()))[:6],
            "implied_tp_per_scored_px": t, "implied_coverage_T_over_G": t / rho,
            "implied_hit_rate_per_dot": t / n, "uniform_random_hit_rate": 9.42 * rho,
            "dots_by_catalogue_distance_px": dict(zip(BIN_NAMES, hist.tolist())),
        }
    for base, mod in PAIRS:
        b, m = masks[base], masks[mod]
        rb, rm = out["rasters"][base], out["rasters"][mod]
        added, removed = m & ~b, b & ~m
        dn = (int(added.sum()) - int(removed.sum())) / area
        dt = rm["implied_tp_per_scored_px"] - rb["implied_tp_per_scored_px"]
        row = {"base": base, "modified": mod,
               "score_change": round(rm["owner_reported_score"] - rb["owner_reported_score"], 4),
               "dots_added": int(added.sum()), "dots_removed": int(removed.sum()),
               "added_by_distance": dict(zip(BIN_NAMES, np.histogram(dist[added], bins=BINS)[0].tolist())),
               "removed_by_distance": dict(zip(BIN_NAMES, np.histogram(dist[removed], bins=BINS)[0].tolist())),
               "implied_delta_tp_per_scored_px": dt}
        if added.sum() == 0 and removed.sum() > 0:
            row["implied_hit_rate_of_removed_dots"] = -dt / (removed.sum() / area)
        elif removed.sum() == 0 and added.sum() > 0:
            row["implied_hit_rate_of_added_dots"] = dt / (added.sum() / area)
        elif dn != 0:
            row["implied_net_hit_rate_of_changed_dots"] = dt / dn
        out["pairs"].append(row)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1))
    print(json.dumps({"rho": rho, "rho_sens": sens, "c_line": c_line, "kappa": kappa, "lambda": lam}, indent=1))
    for k, v in out["rasters"].items():
        print(f"{k:32s} s={v['owner_reported_score']:.4f} N={v['dots_in_scored_domain']:6d} cov={v['implied_coverage_T_over_G']:.3f} hit/dot={v['implied_hit_rate_per_dot']:.4f} dist={list(v['dots_by_catalogue_distance_px'].values())}")
    for r in out["pairs"]:
        hr = {k: round(v, 4) for k, v in r.items() if k.startswith("implied_") and "hit" in k}
        print(f"{r['base']:26s} -> {r['modified']:30s} ds={r['score_change']:+.4f} +{r['dots_added']} -{r['dots_removed']} {hr}")
        print("    added", list(r["added_by_distance"].values()), " removed", list(r["removed_by_distance"].values()))


if __name__ == "__main__":
    main()
