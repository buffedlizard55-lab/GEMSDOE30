#!/usr/bin/env python3
"""H-34-01 holdout: does the SGMC substrate-concealment prior raise the masked DTI?

Frozen design: ``docs/research/h34-01-concealment-preregistration.md``.  Read that
file first; this script implements it and nothing else.  Summary:

* Frame: the registered component holdout (seed 31, 32-pixel interleaving tiles),
  known catalogue masked, four spatial quadrant blocks pooled, one shared
  ``fp_weight_field`` over the hidden stand-in truth.
* Emitter: EDGE, ``truth_mass = 80,000``, count-matched at exactly ``--dots`` per arm.
* Arms: ``hybrid`` (baseline), ``proximity``, ``proximity_cover``, ``hybrid_cover``,
  ``hybrid_matched_control`` (count- and distance-matched random prior), and the
  secondary ``external_concealed`` (concealed/inferred SGMC linework added to the
  external evidence field).
* Gate: ``hybrid_cover`` ≥ +0.005 over the best comparator, with ≥ 3/4 folds positive
  and count matching intact.  A failure is a published falsification, not a bug.

The script never writes a submission, never contacts drivendata.org, and never
promotes an artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.concealment import NODATA as COVER_NODATA, cover_weight  # noqa: E402
from gemsdoe30.emitter_opt import edge_select, mask_from_order  # noqa: E402
from gemsdoe30.fields import (  # noqa: E402
    distance_to_mask,
    geometric_mean,
    layer_belief,
    proximity_belief,
)
from gemsdoe30.holdout import (  # noqa: E402
    distance_matched_draw,
    fp_weight_field,
    masked_dti,
    split_components,
)

EXTERNAL_LAYERS = (
    "derived_sgmc_faults_100m_u8",
    "derived_gdr_paleo_100m_u8",
    "derived_gdr_2m_probes_100m_u8",
    "derived_gdr_volcanics_100m_u8",
)
COVER_LAYER = "derived_sgmc_cover_100m_u8"
CONCEALED_LAYER = "derived_sgmc_concealed_100m_u8"
PIXEL_HALO = 3  # ceil(300 m / 100 m); a block's credit depends only on this halo
GATE_MARGIN = 0.005
GATE_FOLDS = 3
COMPARATORS = ("hybrid", "proximity", "proximity_cover", "hybrid_matched_control")


def quadrant_blocks(valid: np.ndarray) -> list[np.ndarray]:
    """Four spatial blocks of the footprint (row/column halves)."""

    rows, cols = valid.shape
    half_r, half_c = rows // 2, cols // 2
    blocks = []
    for row_slice in (slice(0, half_r), slice(half_r, rows)):
        for col_slice in (slice(0, half_c), slice(half_c, cols)):
            block = np.zeros(valid.shape, dtype=bool)
            block[row_slice, col_slice] = True
            blocks.append(block & valid)
    return blocks


def block_slices(block: np.ndarray) -> tuple[slice, slice]:
    rows = np.flatnonzero(block.any(axis=1))
    cols = np.flatnonzero(block.any(axis=0))
    return (slice(int(rows[0]), int(rows[-1]) + 1), slice(int(cols[0]), int(cols[-1]) + 1))


def score_folds(prediction: np.ndarray, truth: np.ndarray, known: np.ndarray,
                blocks: list[np.ndarray], fp_weight: np.ndarray) -> list[dict]:
    """Score one emission per spatial block (cropped to the kernel halo)."""

    height, width = prediction.shape
    out = []
    for block in blocks:
        row_slice, col_slice = block_slices(block)
        r0 = max(0, row_slice.start - PIXEL_HALO)
        r1 = min(height, row_slice.stop + PIXEL_HALO)
        c0 = max(0, col_slice.start - PIXEL_HALO)
        c1 = min(width, col_slice.stop + PIXEL_HALO)
        cropped = np.where(block[r0:r1, c0:c1], prediction[r0:r1, c0:c1], 0.0)
        result = masked_dti(cropped.astype(np.float32),
                            truth[r0:r1, c0:c1], known[r0:r1, c0:c1],
                            fp_weight=fp_weight[r0:r1, c0:c1])
        result["block_truth_pixels"] = int((truth & block & ~known).sum())
        out.append(result)
    return out


def pooled(fold_rows: list[dict]) -> float:
    tp = sum(row["tp_weight"] for row in fold_rows)
    fp = sum(row["fp_weight"] for row in fold_rows)
    truth = sum(row["hidden_truth_pixels"] for row in fold_rows)
    if truth <= 0:
        return float("nan")
    return float(tp / (0.2 * (tp + fp) + 0.8 * truth))


def distance_summary(distance: np.ndarray, mask: np.ndarray) -> dict:
    values = np.asarray(distance)[mask]
    if values.size == 0:
        return {"pixels": 0}
    return {
        "pixels": int(values.size),
        "mean_px": float(values.mean()),
        "median_px": float(np.median(values)),
        "p90_px": float(np.quantile(values, 0.9)),
        "fraction_within_300m": float((values <= 3.0).mean()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/h34-01-concealment-holdout.json"))
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--stratify", type=int, default=32)
    parser.add_argument("--dots", type=int, default=80_000)
    parser.add_argument("--truth-mass", type=float, default=80_000.0)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--control-seed", type=int, default=20261003)
    parser.add_argument("--arms", default="hybrid,proximity,proximity_cover,hybrid_cover,"
                                        "hybrid_matched_control,external_concealed")
    args = parser.parse_args()

    import rasterio

    with rasterio.open(args.raw_dir / "labels.tif") as dataset:
        labels = dataset.read(1)
    with rasterio.open(args.raw_dir / "sample_submission.tif") as dataset:
        template = dataset.read(1)
    footprint = np.isfinite(template)
    catalogue = labels == 1

    cover_path = args.external_dir / f"{COVER_LAYER}.tif"
    if not cover_path.exists():
        raise SystemExit(f"missing {cover_path}; run the fetch-external-layers workflow first")
    with rasterio.open(cover_path) as dataset:
        cover = dataset.read(1)
    unexpected = sorted({int(v) for v in np.unique(cover)} - set(range(5)) - {COVER_NODATA})
    if unexpected:
        raise SystemExit(f"{cover_path} carries undocumented class values {unexpected}")

    hidden, known, components = split_components(catalogue, seed=args.seed,
                                                 stratify=args.stratify)
    scored = footprint & ~known
    blocks = quadrant_blocks(footprint)
    fp_weight = fp_weight_field(hidden, known)

    report: dict = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "H-34-01 preregistered concealment test (docs/research/"
                    "h34-01-concealment-preregistration.md); component holdout "
                    f"(seed {args.seed}, {args.stratify}-pixel tiles); EDGE emitter, "
                    f"count-matched at {args.dots} dots, truth_mass={args.truth_mass:g}",
        "frame": {
            "catalogue_pixels": int(catalogue.sum()),
            "components": int(components),
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "scored_pixels": int(scored.sum()),
        },
        "cover_layer": str(cover_path),
        "gamma": float(args.gamma),
        "dots": int(args.dots),
        "control_seed": int(args.control_seed),
        "fields": {},
        "arms": {},
        "gate": {},
    }

    # ---- fields -------------------------------------------------------------
    t0 = time.time()
    proximity = proximity_belief(known, footprint=footprint, decay_m=1000.0, cutoff_m=3000.0)
    report["fields"]["proximity"] = {"seconds": round(time.time() - t0, 2),
                                     "nonzero": int((proximity > 0).sum())}
    layer_arrays = {}
    for name in EXTERNAL_LAYERS:
        path = args.external_dir / f"{name}.tif"
        if not path.exists():
            raise SystemExit(f"missing external layer {path}; run the fetch workflow first")
        with rasterio.open(path) as dataset:
            layer_arrays[name] = dataset.read(1)
    t0 = time.time()
    external = layer_belief(layer_arrays, footprint=footprint, decay_m=700.0, cutoff_m=2100.0)
    report["fields"]["external"] = {"seconds": round(time.time() - t0, 2),
                                    "nonzero": int((external > 0).sum())}
    hybrid = geometric_mean(proximity, external)
    report["fields"]["hybrid"] = {"definition": "geometric_mean(proximity, external)"}

    # ---- concealment prior and its matched control ---------------------------
    weights = cover_weight(cover, gamma=args.gamma)
    report["cover"] = {
        "class_pixels": {str(value): int((cover == value).sum()) for value in range(5)},
        "nodata_pixels": int((cover == COVER_NODATA).sum()),
        "weight_min": float(weights.min()),
        "weight_max": float(weights.max()),
    }
    distance_to_known = distance_to_mask(known, pixel_m=100.0)
    report["cover"]["stratified_distance_to_known"] = {
        str(value): distance_summary(distance_to_known, (cover == value) & footprint)
        for value in range(1, 5)
    }

    rng = np.random.default_rng(args.control_seed)
    bedrock_flat = np.flatnonzero(((cover == 0) & footprint).ravel())
    control = np.zeros(cover.shape, dtype=np.uint8)
    control_stats = {}
    for value in range(1, 5):
        target = (cover == value) & footprint
        target_flat = np.flatnonzero(target.ravel())
        if target_flat.size == 0:
            control_stats[str(value)] = {"target_pixels": 0, "drawn_pixels": 0}
            continue
        drawn = distance_matched_draw(bedrock_flat, target_flat, distance_to_known,
                                      int(target_flat.size), rng, bins=10)
        drawn = drawn.reshape(cover.shape)
        control[drawn] = value
        control_stats[str(value)] = {
            "target_pixels": int(target_flat.size),
            "drawn_pixels": int(drawn.sum()),
            "target_distance": distance_summary(distance_to_known, target),
            "control_distance": distance_summary(distance_to_known, drawn),
        }
    report["matched_control"] = {
        "construction": "per class, the same number of bedrock (class 0) cells drawn with "
                        "a distance-to-known profile matched in 10 quantile bins",
        "per_class": control_stats,
        "class_pixels": {str(value): int((control == value).sum()) for value in range(5)},
    }
    control_weights = cover_weight(control, gamma=args.gamma)

    fields = {
        "hybrid": hybrid,
        "proximity": proximity,
        "proximity_cover": proximity * weights,
        "hybrid_cover": hybrid * weights,
        "hybrid_matched_control": hybrid * control_weights,
    }
    if (args.external_dir / f"{CONCEALED_LAYER}.tif").exists():
        with rasterio.open(args.external_dir / f"{CONCEALED_LAYER}.tif") as dataset:
            layer_arrays[CONCEALED_LAYER] = dataset.read(1)
        fields["external_concealed"] = layer_belief(layer_arrays, footprint=footprint,
                                                    decay_m=700.0, cutoff_m=2100.0)
    else:
        print(f"[warn] {CONCEALED_LAYER}.tif absent; external_concealed arm skipped", flush=True)

    requested = [name.strip() for name in args.arms.split(",") if name.strip()]
    for name in requested:
        if name not in fields:
            raise SystemExit(f"arm {name!r} has no field (available: {sorted(fields)})")

    # ---- emission and scoring -----------------------------------------------
    for name in requested:
        t0 = time.time()
        mask, diagnostics = edge_select(fields[name], scored, truth_mass=args.truth_mass,
                                        max_dots=args.dots, return_diagnostics=True)
        accepted = int(diagnostics["accepted"])
        keep = int(min(args.dots, accepted))
        prediction = (mask_from_order(diagnostics["order_flat"], keep, cover.shape)
                      if keep > 0 else np.zeros(cover.shape, dtype=bool))
        folds = score_folds(prediction, hidden, known, blocks, fp_weight)
        arm = {
            "accepted": accepted,
            "dots_kept": keep,
            "count_matched": bool(accepted >= args.dots),
            "pooled_dti": pooled(folds),
            "fold_dti": [float(row["dti"]) for row in folds],
            "fold_tp_weight": [float(row["tp_weight"]) for row in folds],
            "fold_fp_weight": [float(row["fp_weight"]) for row in folds],
            "fold_hidden_truth_pixels": [int(row["hidden_truth_pixels"]) for row in folds],
            "seconds": round(time.time() - t0, 2),
            "belief_definition": ("base field x concealment weight"
                                 if name.endswith("cover") or name.endswith("control")
                                 else "base field"),
        }
        report["arms"][name] = arm
        print(f"[arm] {name}: accepted={accepted} pooled={arm['pooled_dti']:.5f} "
              f"folds={['%.4f' % value for value in arm['fold_dti']]} "
              f"({arm['seconds']:.0f}s)", flush=True)

    # ---- frozen gate ---------------------------------------------------------
    primary = report["arms"].get("hybrid_cover")
    gate: dict = {"comparators": {}, "passed": False, "reasons": []}
    if primary is None:
        gate["reasons"].append("primary arm hybrid_cover was not run")
    else:
        best_name, best_value = None, -1.0
        for name in COMPARATORS:
            arm = report["arms"].get(name)
            if arm is None:
                continue
            gate["comparators"][name] = arm["pooled_dti"]
            if arm["pooled_dti"] > best_value:
                best_name, best_value = name, arm["pooled_dti"]
        gate["best_comparator"] = best_name
        gate["best_comparator_dti"] = best_value
        gate["margin"] = float(primary["pooled_dti"] - best_value)
        if best_name is not None:
            wins = sum(1 for a, b in zip(primary["fold_dti"],
                                         report["arms"][best_name]["fold_dti"]) if a > b)
            gate["folds_positive_vs_best_comparator"] = int(wins)
        gate["count_matched"] = bool(primary["count_matched"])
        if gate.get("margin", 0.0) < GATE_MARGIN:
            gate["reasons"].append(f"margin {gate.get('margin', float('nan')):.5f} < {GATE_MARGIN}")
        if gate.get("folds_positive_vs_best_comparator", 0) < GATE_FOLDS:
            gate["reasons"].append(
                f"positive folds {gate.get('folds_positive_vs_best_comparator', 0)} < {GATE_FOLDS}")
        if not gate["count_matched"]:
            gate["reasons"].append("primary arm not count-matched (accepted < dots)")
        gate["passed"] = not gate["reasons"]
    report["gate"] = gate

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}", flush=True)
    print(f"gate: {'PASS' if gate['passed'] else 'FAIL'} {gate.get('reasons', [])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
