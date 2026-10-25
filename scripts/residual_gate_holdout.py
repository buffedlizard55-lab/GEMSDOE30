#!/usr/bin/env python3
"""Holdout test of the residual-ridge gate (review hypothesis 3) against a proximity comparator.

PRE-REGISTERED PARAMETERS (fixed before the first run; see
docs/research/2026-10-25/candidate-residual-gate.md):

* Hidden split: ``holdout.split_components(catalogue, seed=31)`` (stand-in "new" faults).
* Known/masked domain: every visible catalogue pixel is excluded from scoring, exactly as
  the organizer masks known faults. Hidden pixels are the withheld positives.
* Buffer (feature visibility): visible catalogue pixels closer than ``--buffer-m`` to any
  hidden pixel are removed from feature construction (they stay masked for scoring).
  Primary arm: 3500 m (= 3 km gate + 300 m metric reach + 200 m margin). Sensitivity arm:
  0 m, which is the existing stand-in protocol.
* Candidate A: gated residual ridge (``gemsdoe30.residual_gate``) with a 3 km gate.
* Comparator B: proximity belief ``exp(-d/1 km)`` cut at 3 km (``gemsdoe30.fields``),
  same Poisson radius, count-matched to A by taking the first N accepted dots.
* Ablation D: the same ridge+gate on RAW rtp (no residualisation), count-matched to A.
* Control R (random): uniform random scores on the scored domain, same Poisson radius,
  count-matched to A. Any arm must beat R to show signal beyond dot density.
* Arm E (catalogue-free): residual ridge with NO distance gate (gate radius 1e9 m), so
  it uses no visible-catalogue distance at all. This is the only arm that is structurally
  testable under the strict buffer: a gated dot is at most 3 km from visible faults, and a
  3.5 km buffer puts every gated dot >= 0.5 km from hidden pixels, beyond the 300 m reach.
  Count-matched to A.
* Emitter: ordered greedy Poisson-disk, radius 4 px (400 m), binary 0/1 dots.
* Metric: shared pooled masked DTI (alpha 0.2, beta 0.8, 300 m triangular kernel) with
  whole-tile (32 px = 3.2 km) block bootstrap, 2000 draws, seed 31.
* Feature canaries: each feature alone, AUC on hidden-vs-scored pixels. AUC outside
  [0.10, 0.90] is flagged for leakage review.

Nothing here reads hidden labels to build a feature; hidden pixels are used only as truth.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emission import dti_from_components, poisson_disk_select_ordered  # noqa: E402
from gemsdoe30.fields import distance_to_mask, proximity_belief  # noqa: E402
from gemsdoe30.holdout import (  # noqa: E402
    EVALUATOR_VERSION,
    masked_dti_by_blocks,
    masked_tile_sums,
    split_components,
)
from gemsdoe30.residual_gate import fit_residual, gated_residual_ridge  # noqa: E402
from gemsdoe30.submission import valid_template_mask  # noqa: E402

RADIUS_PX = 4
GATE_M = 3000.0
BOOTSTRAP = 2000
SEED = 31
REGRESSORS = ("iso_grav_anom", "det_elev", "depth_to_base_surf")
TARGET = "rtp"


def band_index(names: list[str]) -> dict[str, int]:
    return {n.split(" - ")[0]: i for i, n in enumerate(names)}


def auc_rank(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC via average ranks (ties handled)."""
    from scipy.stats import rankdata

    values = np.concatenate([pos, neg])
    ranks = rankdata(values)
    n1, n0 = pos.size, neg.size
    return float((ranks[:n1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def emit(belief: np.ndarray, scored: np.ndarray, max_kept: int | None):
    mask = scored & (belief > 0)
    rows, cols = poisson_disk_select_ordered(belief, RADIUS_PX, threshold=0.0, mask=mask,
                                             max_kept=max_kept)
    pred = np.zeros(belief.shape, dtype=np.float64)
    pred[rows, cols] = 1.0
    return pred


def run(buffer_m: float, features_path: Path, labels_path: Path, template_path: Path,
        manifest_path: Path) -> dict:
    import rasterio

    manifest = json.loads(manifest_path.read_text())
    names = band_index(manifest["feature_band_names"])
    feats = np.load(features_path, mmap_mode="r")
    with rasterio.open(template_path) as ds:
        footprint = valid_template_mask(ds, np)
    with rasterio.open(labels_path) as ds:
        labels = ds.read(1)
    catalogue = (labels == 1) & footprint

    hidden, known, n_components = split_components(catalogue, seed=SEED)
    visible = known & footprint
    scored = footprint & ~visible
    dist_hidden = distance_to_mask(hidden & footprint)
    feature_visible = visible & (dist_hidden > buffer_m) if buffer_m > 0 else visible.copy()
    if not feature_visible.any():
        raise SystemExit("no visible features remain after buffering")
    dist_visible = distance_to_mask(feature_visible)

    rtp = np.asarray(feats[names[TARGET]], dtype=np.float64)
    regs = [np.asarray(feats[names[r]], dtype=np.float64) for r in REGRESSORS]
    residual, fit_info = fit_residual(rtp, regs, footprint)

    belief_a = gated_residual_ridge(residual, footprint, dist_visible, gate_m=GATE_M)
    belief_a[~scored] = 0.0
    pred_a = emit(belief_a, scored, max_kept=None)
    n_a = int(pred_a.sum())

    belief_b = proximity_belief(feature_visible, footprint=scored, decay_m=1000.0, cutoff_m=GATE_M)
    pred_b = emit(belief_b, scored, max_kept=n_a)

    belief_d = gated_residual_ridge(rtp.astype(np.float32), footprint, dist_visible, gate_m=GATE_M)
    belief_d[~scored] = 0.0
    pred_d = emit(belief_d, scored, max_kept=n_a)

    belief_e = gated_residual_ridge(residual, footprint, dist_visible, gate_m=1e9)
    belief_e[~scored] = 0.0
    pred_e = emit(belief_e, scored, max_kept=n_a)

    rng_r = np.random.default_rng(SEED)
    belief_r = np.where(scored, rng_r.random(footprint.shape), 0.0).astype(np.float32)
    pred_r = emit(belief_r, scored, max_kept=n_a)

    truth = hidden & footprint
    arms = {"A_residual_ridge_gate": pred_a, "B_proximity_comparator": pred_b,
            "D_ablation_raw_rtp_ridge": pred_d, "E_catalogue_free_residual_ridge": pred_e,
            "R_random_control": pred_r}
    result: dict = {
        "evaluator_version": EVALUATOR_VERSION,
        "buffer_m": buffer_m,
        "withheld_positive_pixels": int((truth & scored).sum()),
        "visible_catalogue_pixels": int(visible.sum()),
        "feature_visible_pixels": int(feature_visible.sum()),
        "hidden_components": int(n_components),
        "residual_fit": fit_info,
        "dots": {k: int(v.sum()) for k, v in arms.items()},
        "arms": {},
    }

    tiles = {}
    for name, pred in arms.items():
        pooled = masked_dti_by_blocks(pred, truth, visible, footprint)
        tiles[name] = masked_tile_sums(pred, truth, visible, footprint, tile_px=32)
        result["arms"][name] = {
            "pooled_dti": pooled["pooled"]["dti"],
            "tp_weight": pooled["pooled"]["tp_weight"],
            "fp_weight": pooled["pooled"]["fp_weight"],
            "truth_pixels": pooled["pooled"]["truth_pixels"],
            "emitted_pixels": pooled["pooled"]["emitted_pixels"],
        }

    occupied = tiles["A_residual_ridge_gate"]["occupied"]
    idx_occ = np.flatnonzero(occupied)
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, idx_occ.size, size=(BOOTSTRAP, idx_occ.size))

    def boot(name):
        t = tiles[name]
        tp = t["tp"][idx_occ][draws].sum(axis=1)
        fp = t["fp"][idx_occ][draws].sum(axis=1)
        n = t["truth"][idx_occ][draws].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(n > 0, tp / (0.2 * tp + 0.2 * fp + 0.8 * n + 1e-8), np.nan)

    boots = {name: boot(name) for name in arms}
    for name in arms:
        lo, hi = np.nanpercentile(boots[name], [2.5, 97.5])
        result["arms"][name]["ci95_tile_bootstrap"] = [float(lo), float(hi)]
    for other in ("B_proximity_comparator", "D_ablation_raw_rtp_ridge",
                  "E_catalogue_free_residual_ridge", "R_random_control"):
        diff = boots["A_residual_ridge_gate"] - boots[other]
        lo, hi = np.nanpercentile(diff, [2.5, 97.5])
        result[f"paired_A_minus_{other}"] = {
            "delta_pooled": float(result["arms"]["A_residual_ridge_gate"]["pooled_dti"]
                                  - result["arms"][other]["pooled_dti"]),
            "ci95_tile_bootstrap": [float(lo), float(hi)],
            "fraction_draws_A_above": float(np.nanmean(diff > 0)),
        }

    # Feature canaries: each feature alone against hidden positives in the scored domain.
    pos_mask = truth & scored
    neg_mask = scored & ~truth
    rng2 = np.random.default_rng(SEED)
    neg_idx = np.flatnonzero(neg_mask)
    neg_sample = rng2.choice(neg_idx, size=min(400_000, neg_idx.size), replace=False)
    pos_idx = np.flatnonzero(pos_mask)

    # Lazy, sampled evaluation: never copy a full grid per feature (memory-safe).
    sources = {name: ("band", i) for name, i in names.items()}
    sources["residual_rtp"] = ("array", residual)
    sources["distance_to_visible_m"] = ("array", dist_visible)
    sources["belief_A_residual_ridge"] = ("array", belief_a)
    sources["belief_B_proximity"] = ("array", belief_b)
    sources["belief_E_catalogue_free_ridge"] = ("array", belief_e)
    canaries = {}
    for name, (kind, ref) in sources.items():
        grid = feats[ref] if kind == "band" else ref
        flat_grid = np.asarray(grid).reshape(-1)
        values_pos = flat_grid[pos_idx].astype(np.float64)
        values_neg = flat_grid[neg_sample].astype(np.float64)
        ok_p = np.isfinite(values_pos)
        ok_n = np.isfinite(values_neg)
        if ok_p.sum() < 10 or ok_n.sum() < 10:
            canaries[name] = {"auc": None, "status": "insufficient finite values"}
            continue
        auc = auc_rank(values_pos[ok_p], values_neg[ok_n])
        status = "LEAKAGE-REVIEW (AUC outside [0.10, 0.90])" if (auc > 0.90 or auc < 0.10) else "ok"
        canaries[name] = {"auc": round(auc, 4), "status": status,
                          "positives": int(ok_p.sum()), "negatives": int(ok_n.sum())}
    result["feature_canaries"] = canaries
    result["generated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buffer-m", type=float, required=True)
    parser.add_argument("--features", type=Path, default=ROOT / "data/processed/features_raw.npy")
    parser.add_argument("--labels", type=Path, default=ROOT / "data/raw/labels.tif")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/processed/manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.buffer_m, args.features, args.labels, args.template, args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("buffer_m", "withheld_positive_pixels", "dots")}, indent=1))
    for name, arm in result["arms"].items():
        print(name, round(arm["pooled_dti"], 5), arm["ci95_tile_bootstrap"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
