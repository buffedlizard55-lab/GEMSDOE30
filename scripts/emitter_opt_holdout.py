#!/usr/bin/env python3
"""EDGE emitter holdout: does marginal-credit greedy beat belief-ordered thinning?

Registered design (frozen before running; recorded in
``docs/research/emitter-opt-preregistration.md``)
----------------------------------------------------------------------
Frame: the real 3730 x 3292 competition grid.  Whole 8-connected catalogue
components are split deterministically into a stand-in *hidden* half and a
*known* half (``holdout.split_components``, seed 31, 3.2 km interleaving tiles).
Known pixels are masked out of every metric term exactly as the organizer masks
USGS/INGENIOUS pixels; hidden components are the stand-in "new faults".  Four
spatial quadrant blocks are scored separately and pooled, so no rule is scored
only in one corner of the map.

Belief fields (inputs to the emitters; never contain hidden components):

* ``proximity``  - exp(-d_1km) around known traces, cut at 3 km.
* ``external``   - exp(-d_0.7km) around free official external layers already on
  the grid (USGS SGMC fault lines, GDR paleo-geothermal, GDR 2 m temperature
  probes, GDR Quaternary volcanics).  The INGENIOUS-derived Qfaults raster is
  deliberately excluded: 59,037 of its 59,065 pixels sit on the training
  catalogue, so it is a copy of the answer key, not evidence.
* ``hybrid``     - geometric mean of the two, which requires both to support a cell.
* ``gbm``        - the published OOF GBM emission (``docs/downloads/*oof-gbm*.tif``)
  diffused with a 1.5-pixel Gaussian to recover a graded surface.  This field is
  **leak-contaminated** on this frame: the shipped model saw the whole catalogue,
  including the components that this holdout treats as hidden.  It is included
  only to compare *emitters on one identical field*, never to support a claim
  that a rule generalises.

Emitter families, each choosing its own operating point:

* ``dense``    - belief threshold at quantiles of the scored domain.
* ``uniform``  - Poisson-disk thinning at fixed radii (the owner-dotted family).
* ``adaptive`` - confidence-adaptive Poisson-disk thinning.
* ``metric``   - existing belief-ordered marginal rule (pool-capped at 120k).
* ``edge``     - this session's expected-marginal-credit greedy (:mod:`gemsdoe30.emitter_opt`).

Selection is leave-one-fold-out: for fold *f* each family's parameter is chosen on
the pooled other three folds and reported on *f*.  The pooled cross-validated index
sums the sufficient statistics of each fold at its own held-out choice.  Oracle
(method-selected-on-the-scored-fold) values are reported separately and are not
selectable results.

Interpretation limits
---------------------
The hidden truth is a catalogue split, not the organizer's expert-labelled new
faults, so a family that wins here has passed a *necessary* proxy gate only.  The
catalogue is exactly the inventory the official metric masks out, so absolute
values are not competition scores and the ordering is not guaranteed to transfer.
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

from gemsdoe30.emission import (  # noqa: E402
    adaptive_disk_select,
    metric_optimal_emission,
    poisson_disk_select,
)
from gemsdoe30.emitter_opt import (  # noqa: E402
    edge_select,
    mask_from_order,
    stop_index,
)
from gemsdoe30.fields import geometric_mean, layer_belief, proximity_belief  # noqa: E402
from gemsdoe30.holdout import fp_weight_field, masked_dti, split_components  # noqa: E402

EXTERNAL_LAYERS = (
    "derived_sgmc_faults_100m_u8",
    "derived_gdr_paleo_100m_u8",
    "derived_gdr_2m_probes_100m_u8",
    "derived_gdr_volcanics_100m_u8",
)


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


PIXEL_HALO = 3  # ceil(300 m / 100 m): a block's credit depends only on this halo


def block_slices(block: np.ndarray) -> tuple[slice, slice]:
    rows = np.flatnonzero(block.any(axis=1))
    cols = np.flatnonzero(block.any(axis=0))
    return (slice(int(rows[0]), int(rows[-1]) + 1), slice(int(cols[0]), int(cols[-1]) + 1))


def score_folds(prediction: np.ndarray, truth: np.ndarray, known: np.ndarray,
                blocks: list[np.ndarray], fp_weight: np.ndarray) -> list[dict]:
    """Score one emission independently inside each block (masked domain).

    The metric is evaluated on a cropped view of each block expanded by the kernel
    halo, which is exact for a prediction that is zero outside the block and keeps
    29-offset credit loops off the full 12.3 M-pixel rectangle.
    """

    height, width = prediction.shape
    out = []
    for block in blocks:
        row_slice, col_slice = block_slices(block)
        r0 = max(0, row_slice.start - PIXEL_HALO)
        r1 = min(height, row_slice.stop + PIXEL_HALO)
        c0 = max(0, col_slice.start - PIXEL_HALO)
        c1 = min(width, col_slice.stop + PIXEL_HALO)
        cropped_prediction = np.where(block[r0:r1, c0:c1], prediction[r0:r1, c0:c1], 0.0)
        result = masked_dti(cropped_prediction.astype(np.float32),
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--output", type=Path,
                        default=Path("docs/research/emitter-opt-holdout.json"))
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--stratify", type=int, default=32)
    parser.add_argument("--max-dots", type=int, default=200_000)
    parser.add_argument("--prefix-step", type=int, default=5_000)
    parser.add_argument("--truth-mass", type=float, default=80_000.0,
                        help="belief normalisation used while sweeping (the loosest stop)")
    parser.add_argument("--fields", default="proximity,external,hybrid",
                        help="comma-separated subset of proximity,external,hybrid,gbm")
    parser.add_argument("--gbm-path", type=Path, default=None,
                        help="published OOF GBM raster used by the optional 'gbm' field")
    args = parser.parse_args()

    import rasterio

    with rasterio.open(args.raw_dir / "labels.tif") as dataset:
        labels = dataset.read(1)
    with rasterio.open(args.raw_dir / "sample_submission.tif") as dataset:
        template = dataset.read(1)
    footprint = np.isfinite(template)
    catalogue = labels == 1

    hidden, known, components = split_components(catalogue, seed=args.seed,
                                                 stratify=args.stratify)
    scored = footprint & ~known
    blocks = quadrant_blocks(footprint)
    # One distance transform against the whole stand-in hidden truth set, matching
    # the official metric (which weights false positives by distance to the scored
    # truth) and reused by every rule and every fold.
    fp_weight = fp_weight_field(hidden, known)

    report: dict = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "component holdout (seed %d, %d-pixel interleaving tiles); known catalogue "
                    "masked; four spatial quadrant blocks pooled; leave-one-fold-out parameter "
                    "selection per family" % (args.seed, args.stratify),
        "frame": {
            "catalogue_pixels": int(catalogue.sum()),
            "components": int(components),
            "hidden_pixels": int(hidden.sum()),
            "known_pixels": int(known.sum()),
            "scored_pixels": int(scored.sum()),
        },
        "fields": {},
        "rules": {},
    }

    fields: dict[str, np.ndarray] = {}
    t0 = time.time()
    fields["proximity"] = proximity_belief(known, footprint=footprint, decay_m=1000.0,
                                           cutoff_m=3000.0)
    report["fields"]["proximity"] = {
        "definition": "exp(-d/1 km) around known traces, cut at 3 km",
        "nonzero": int((fields["proximity"] > 0).sum()),
        "seconds": round(time.time() - t0, 2),
    }
    t0 = time.time()
    layer_arrays = {}
    for name in EXTERNAL_LAYERS:
        path = args.external_dir / f"{name}.tif"
        if not path.exists():
            raise SystemExit(f"missing external layer {path}; run the fetch workflow first")
        with rasterio.open(path) as dataset:
            layer_arrays[name] = dataset.read(1)
    fields["external"] = layer_belief(layer_arrays, footprint=footprint, decay_m=700.0,
                                      cutoff_m=2100.0)
    report["fields"]["external"] = {
        "definition": "exp(-d/0.7 km) around " + ", ".join(EXTERNAL_LAYERS),
        "excluded": "derived_gdr_qfaults_v2_100m_u8 (59,037/59,065 px on the training catalogue)",
        "nonzero": int((fields["external"] > 0).sum()),
        "seconds": round(time.time() - t0, 2),
    }
    t0 = time.time()
    fields["hybrid"] = geometric_mean(fields["proximity"], fields["external"])
    report["fields"]["hybrid"] = {
        "definition": "geometric mean of proximity and external",
        "nonzero": int((fields["hybrid"] > 0).sum()),
        "seconds": round(time.time() - t0, 2),
    }
    del layer_arrays

    requested = [name.strip() for name in args.fields.split(",") if name.strip()]
    unknown = [name for name in requested if name not in ("proximity", "external", "hybrid", "gbm")]
    if unknown:
        raise SystemExit(f"unknown field(s): {unknown}")
    if "gbm" in requested:
        from scipy.ndimage import gaussian_filter

        gbm_path = args.gbm_path
        if gbm_path is None:
            candidates = sorted((ROOT / "docs" / "downloads").glob("*oof-gbm*.tif"))
            if not candidates:
                raise SystemExit("no published OOF GBM raster found; pass --gbm-path")
            gbm_path = candidates[0]
        t0 = time.time()
        with rasterio.open(gbm_path) as dataset:
            gbm = dataset.read(1).astype(np.float32)
        gbm = np.where(np.isfinite(gbm), np.clip(gbm, 0.0, None), 0.0)
        gbm[~footprint] = 0.0
        fields["gbm"] = gaussian_filter(gbm, 1.5).astype(np.float32)
        report["fields"]["gbm"] = {
            "definition": f"1.5-px Gaussian diffusion of {Path(gbm_path).name}",
            "leak_warning": "the shipped model trained on the whole catalogue, so this "
                            "field is contaminated on this frame; operator comparison only",
            "nonzero": int((fields["gbm"] > 0).sum()),
            "seconds": round(time.time() - t0, 2),
        }
    fields = {name: fields[name] for name in requested}
    report["fields_requested"] = requested

    quantiles = (0.90, 0.95, 0.98, 0.99, 0.995)
    radii = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0)
    adaptive_gammas = (0.5, 1.0)

    curves: dict[str, dict[str, list[dict]]] = {}
    for field_name, field in fields.items():
        values = np.where(scored, field, -np.inf).astype(np.float32)
        curves[field_name] = {}
        entry: dict[str, dict] = {}

        def record(name: str, mask: np.ndarray) -> None:
            entry[name] = score_folds(mask.astype(np.float32), hidden, known, blocks,
                                      fp_weight)

        print(f"[{field_name}] dense thresholds", flush=True)
        for quantile in quantiles:
            threshold = float(np.quantile(field[scored], quantile))
            record(f"dense@q{quantile:g}", scored & (field >= threshold))

        print(f"[{field_name}] uniform / adaptive thinning", flush=True)
        for radius in radii:
            record(f"uniform@r{radius:g}", poisson_disk_select(values, radius, mask=scored))
        for radius in (3.0, 5.0):
            for gamma in adaptive_gammas:
                record(f"adaptive@r{radius:g}@g{gamma:g}",
                       adaptive_disk_select(values, radius, gamma=gamma, mask=scored))

        print(f"[{field_name}] belief-ordered marginal rule (existing)", flush=True)
        record("metric@pool120k", metric_optimal_emission(field, scored, pool_limit=120_000))

        print(f"[{field_name}] EDGE greedy sweep", flush=True)
        sweep_start = time.time()
        _, diagnostics = edge_select(field, scored, truth_mass=args.truth_mass,
                                     max_dots=args.max_dots, return_diagnostics=True)
        order = diagnostics["order_flat"]
        cumulative_tp = diagnostics["cumulative_tp"]
        cumulative_fp = diagnostics["cumulative_fp"]
        accepted = int(order.size)
        print(f"[{field_name}] EDGE accepted {accepted} dots in {time.time() - sweep_start:.0f}s",
              flush=True)
        keep_grid = list(range(args.prefix_step, accepted + 1, args.prefix_step))
        if accepted:
            keep_grid.append(accepted)
        for keep in keep_grid:
            record(f"edge@keep{keep}", mask_from_order(order, keep, field.shape))
        report["rules"].setdefault("edge", {})[field_name] = {
            "accepted": accepted,
            "sweep_seconds": round(time.time() - sweep_start, 1),
            "expected_dti_at_sweep": float(diagnostics["expected_dti"]),
            "expected_tp_at_sweep": float(diagnostics["expected_tp"]),
            "expected_fp_at_sweep": float(diagnostics["expected_fp"]),
            "stop_index_by_truth_mass": {
                str(int(mass)): int(stop_index(cumulative_tp, cumulative_fp, float(mass)))
                for mass in (5_000, 10_000, 20_000, 40_000, 80_000)
            },
        }
        report["rules"].setdefault("curves", {})[field_name] = {
            name: [{"dti": row["dti"], "tp_weight": row["tp_weight"],
                    "fp_weight": row["fp_weight"], "emitted_pixels": row["emitted_pixels"]}
                   for row in rows]
            for name, rows in entry.items()
        }
        curves[field_name] = entry
        (args.output.parent / "emitter-opt-holdout.partial.json").write_text(
            json.dumps(report, indent=1), encoding="utf-8")

    # Leave-one-fold-out selection inside each field, per family.
    shared_families = ("dense", "uniform", "adaptive", "metric", "edge")
    selection: dict[str, dict] = {}
    pooled_cv: dict[str, dict] = {}
    for field_name, entry in curves.items():
        selection[field_name] = {}
        pooled_cv[field_name] = {}
        for family in shared_families:
            names = sorted(name for name in entry if name.split("@")[0] == family)
            if not names:
                continue
            choices = []
            pooled_tp = pooled_fp = pooled_truth = 0.0
            pooled_emitted = 0
            for fold in range(4):
                other = [index for index in range(4) if index != fold]
                best_name, best_value = None, -np.inf
                for name in names:
                    rows = entry[name]
                    others = [rows[index] for index in other]
                    value = pooled(others)
                    if np.isfinite(value) and value > best_value:
                        best_name, best_value = name, value
                chosen = entry[best_name][fold]
                tp, fp = chosen["tp_weight"], chosen["fp_weight"]
                truth = chosen["hidden_truth_pixels"]
                pooled_tp += tp
                pooled_fp += fp
                pooled_truth += truth
                pooled_emitted += chosen["emitted_pixels"]
                choices.append({
                    "fold": fold,
                    "chosen_on_other_folds": best_name,
                    "pooled_other_folds_dti": best_value,
                    "held_out_dti": chosen["dti"],
                    "held_out_emitted_pixels": chosen["emitted_pixels"],
                    "held_out_tp_weight": tp,
                    "held_out_fp_weight": fp,
                })
            selection[field_name][family] = choices
            pooled_cv[field_name][family] = {
                "pooled_tp_weight": pooled_tp,
                "pooled_fp_weight": pooled_fp,
                "pooled_truth_pixels": pooled_truth,
                "pooled_emitted_pixels": pooled_emitted,
                "pooled_dti": (pooled_tp / (0.2 * (pooled_tp + pooled_fp) + 0.8 * pooled_truth)
                               if pooled_truth > 0 else None),
            }

    report["selection"] = selection
    report["pooled_cross_validated"] = pooled_cv

    oracle: dict[str, dict] = {}
    for field_name, entry in curves.items():
        oracle[field_name] = {}
        for family in shared_families:
            names = [name for name in entry if name.split("@")[0] == family]
            if not names:
                continue
            per_fold = {}
            for fold in range(4):
                best_name = max(names, key=lambda name: entry[name][fold]["dti"])
                per_fold[str(fold)] = {"rule": best_name, "dti": entry[best_name][fold]["dti"]}
            oracle[field_name][family] = per_fold
    report["oracle_on_holdout_not_selectable"] = oracle

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1), encoding="utf-8")
    partial = args.output.parent / "emitter-opt-holdout.partial.json"
    partial.unlink(missing_ok=True)
    summary = {field: {family: (None if row["pooled_dti"] is None else round(row["pooled_dti"], 5))
                       for family, row in families.items()}
               for field, families in pooled_cv.items()}
    print(json.dumps({"pooled_cross_validated": summary}, indent=1))
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
