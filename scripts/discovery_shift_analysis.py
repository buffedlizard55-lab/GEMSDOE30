#!/usr/bin/env python3
"""Does the loss ablation survive the shift from catalogue density to a sparse, clustered truth?

The local holdout scores the two loss arms against the *catalogue*, which is dense and
spread across the whole footprint.  The competition scores against a small set of newly
identified faults, which is sparse and geographically localised.  A model can win the
first and lose the second.  This script re-scores the identical stitched out-of-fold
predictions under controlled realisations of that shift:

``density``      keep a uniform-random fraction of the held-out truth pixels;
                 isolates the effect of target-set *density*.
``cluster``      keep truth pixels that fall inside ``k`` randomly placed discs;
                 isolates *spatial non-uniformity* at matched density.
``catalogue_masked``  apply the organizer's masking rule to the predictions themselves:
                 every predicted pixel that sits on the known catalogue is removed before
                 scoring against a truth set that also excludes it.  This measures how much
                 of each arm's score is genuinely off-catalogue novelty rather than
                 restatement of the catalogue.

All arms see the same truth realisations (same seeds), so the comparison is paired.
The metric is the official kernel rule with ``alpha = 0.2`` and a 300 m triangular support.
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

from gemsdoe30.cv import spatial_quadrant_masks  # noqa: E402
from gemsdoe30.emission import dti_components_masked  # noqa: E402

ARMS = ("regional", "combined")
DEFAULT_DENSITIES = (1.0, 0.5, 0.25, 0.1, 0.04)


def _components(prediction, truth_binary, scored_mask, radius_m, alpha, pixel_m=100.0):
    return dti_components_masked(
        prediction, truth_binary.astype(np.uint8), scored_mask,
        pixel_size_m=pixel_m, radius_m=radius_m, alpha=alpha,
    )


def _summarise(components: dict) -> dict:
    tp = float(components["tp_weight"])
    fp = float(components["fp_weight"])
    truth = float(components["truth_pixels"])
    return {
        "dti": float(components["dti"]),
        "tp_weight": tp,
        "fp_weight": fp,
        "truth_pixels": truth,
        "fn_weight": float(components["fn_weight"]),
        "dti_denominator": tp + 0.2 * fp + 0.8 * (truth - tp),
    }


def _paired_delta(a: dict, b: dict) -> dict:
    """Report the combined-minus-regional difference and a paired sign test."""

    keys = sorted(set(a) & set(b))
    deltas = {key: a[key] - b[key] for key in keys}
    positive = sum(1 for key in keys if a[key] > b[key])
    negative = sum(1 for key in keys if a[key] < b[key])
    return {
        "delta_mean": float(np.mean(list(deltas.values()))) if deltas else float("nan"),
        "delta_min": float(min(deltas.values())) if deltas else float("nan"),
        "delta_max": float(max(deltas.values())) if deltas else float("nan"),
        "realisations_combined_better": positive,
        "realisations_regional_better": negative,
        "per_realisation": deltas,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--oof-dir", type=Path, default=ROOT / "runs/oof")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/research/discovery-shift.json")
    parser.add_argument("--seed", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--radius-m", type=float, default=300.0)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--cluster-radius-km", type=float, default=3.0)
    parser.add_argument("--densities", type=float, nargs="+", default=list(DEFAULT_DENSITIES))
    parser.add_argument("--lattice-spacing-px", type=float, default=4.0,
                        help="spacing of the internal blind-lattice reference arm")
    parser.add_argument("--no-lattice", action="store_true",
                        help="skip the blind-lattice reference arm")
    args = parser.parse_args()

    valid = np.load(args.data_dir / "valid.npy", mmap_mode="r").astype(bool, copy=False)
    labels = np.load(args.data_dir / "labels.npy", mmap_mode="r")
    manifest = json.loads((args.data_dir / "manifest.json").read_text(encoding="utf-8"))
    truth = np.asarray(labels) == 1

    predictions: dict[str, np.ndarray] = {}
    for arm in ARMS:
        path = args.oof_dir / f"{arm}-oof.npy"
        if not path.is_file():
            raise FileNotFoundError(f"stitched OOF mosaic missing for arm {arm!r}: {path}")
        mosaic = np.load(path)
        if mosaic.shape != valid.shape:
            raise ValueError(f"{path}: shape {mosaic.shape} != footprint {valid.shape}")
        plane = np.where(valid, np.nan_to_num(np.asarray(mosaic, dtype=np.float32), nan=0.0), 0.0)
        if plane.min() < 0.0 or plane.max() > 1.0:
            raise ValueError(f"{path}: predictions outside [0, 1]")
        predictions[arm] = plane

    arms = list(ARMS)
    if not args.no_lattice:
        spacing = max(1, int(round(args.lattice_spacing_px)))
        lattice = np.zeros(valid.shape, dtype=np.float32)
        lattice[np.arange(0, valid.shape[0], spacing)[:, None],
                np.arange(0, valid.shape[1], spacing)[None, :]] = 1.0
        predictions["blind_lattice"] = np.where(valid, lattice, 0.0)
        arms.append("blind_lattice")

    rng = np.random.default_rng(args.seed)
    report: dict[str, object] = {
        "script": "scripts/discovery_shift_analysis.py",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metric": {"radius_m": args.radius_m, "alpha": args.alpha, "pixel_size_m": 100.0},
        "dataset_signature": manifest.get("dataset_signature"),
        "footprint_pixels": int(valid.sum()),
        "catalogue_truth_pixels": int(truth.sum()),
        "arms": arms,
        "lattice_spacing_px": None if args.no_lattice else args.lattice_spacing_px,
        "density_shift": {},
        "cluster_shift": {},
        "catalogue_masked": {},
        "fold_slices": {},
    }
    started = time.time()

    def score_all(truth_binary, scored_mask, tag, bucket):
        for arm in arms:
            components = _components(predictions[arm], truth_binary, scored_mask,
                                     args.radius_m, args.alpha)
            bucket.setdefault(arm, {})[tag] = _summarise(components)

    # ---- full catalogue reference -------------------------------------------------
    for arm in arms:
        components = _components(predictions[arm], truth, valid, args.radius_m, args.alpha)
        report["density_shift"].setdefault(arm, {})["1.000"] = _summarise(components)

    truth_rows, truth_cols = np.nonzero(truth)
    total_truth = truth_rows.size

    # ---- density sweep ------------------------------------------------------------
    for density in args.densities:
        if density >= 1.0:
            continue
        for repeat in range(args.repeats):
            local = np.random.default_rng(args.seed * 1000 + repeat)
            keep = local.random(total_truth) < density
            retained = np.zeros(truth.shape, dtype=bool)
            retained[truth_rows[keep], truth_cols[keep]] = True
            removed = truth & ~retained
            # organizer semantics: pixels at known/removed faults are not scored at all
            scored = valid & ~removed
            score_all(retained, scored, f"{density:.3f}#{repeat}", report["density_shift"])
            report["density_shift"].setdefault("_retained", {})[f"{density:.3f}#{repeat}"] = int(retained.sum())

    # ---- spatial cluster sweep ----------------------------------------------------
    height, width = truth.shape
    radius_px = args.cluster_radius_km * 10.0
    for repeat in range(args.repeats):
        local = np.random.default_rng(args.seed * 7000 + repeat)
        # target approximately the 25 % density realisation
        wanted = 0.25 * total_truth
        centres: list[tuple[int, int]] = []
        retained = np.zeros(truth.shape, dtype=bool)
        attempts = 0
        while retained.sum() < wanted and attempts < 400:
            attempts += 1
            centre_row = int(local.integers(0, height))
            centre_col = int(local.integers(0, width))
            row0 = max(0, int(centre_row - radius_px))
            row1 = min(height, int(centre_row + radius_px) + 1)
            col0 = max(0, int(centre_col - radius_px))
            col1 = min(width, int(centre_col + radius_px) + 1)
            block = retained[row0:row1, col0:col1]
            rows = np.arange(row0, row1)[:, None]
            cols = np.arange(col0, col1)[None, :]
            disc = (rows - centre_row) ** 2 + (cols - centre_col) ** 2 <= radius_px**2
            block |= disc & truth[row0:row1, col0:col1]
            centres.append((centre_row, centre_col))
        removed = truth & ~retained
        scored = valid & ~removed
        tag = f"r{args.cluster_radius_km:g}km#{repeat}"
        score_all(retained, scored, tag, report["cluster_shift"])
        report["cluster_shift"].setdefault("_meta", {})[tag] = {
            "discs": len(centres),
            "retained_truth_pixels": int(retained.sum()),
            "retained_fraction": float(retained.sum() / total_truth),
        }

    # ---- catalogue-masked novelty test -------------------------------------------
    from scipy.ndimage import binary_dilation

    catalogue_dilated = binary_dilation(truth, iterations=3)
    for arm in arms:
        masked_prediction = np.where(catalogue_dilated, 0.0, predictions[arm])
        hidden_truth = truth & ~catalogue_dilated
        scored = valid & ~catalogue_dilated
        components = _components(masked_prediction, hidden_truth, scored, args.radius_m, args.alpha)
        report["catalogue_masked"][arm] = _summarise(components)
    report["catalogue_masked"]["_meta"] = {
        "dilation_pixels": 3,
        "hidden_truth_pixels": int((truth & ~catalogue_dilated).sum()),
        "scored_pixels": int((valid & ~catalogue_dilated).sum()),
        "note": "the catalogue is erased from both the prediction and the truth, so only "
                "off-catalogue novelty can earn credit",
    }

    # ---- per-fold paired comparison ------------------------------------------------
    for fold in range(4):
        _, fold_mask = spatial_quadrant_masks(valid, fold, buffer_m=args.radius_m)
        entry: dict[str, object] = {"scored_pixels": int(fold_mask.sum())}
        for arm in arms:
            components = _components(predictions[arm], truth & fold_mask, fold_mask,
                                     args.radius_m, args.alpha)
            entry[arm] = _summarise(components)
        entry["delta_combined_minus_regional"] = entry["combined"]["dti"] - entry["regional"]["dti"]
        if "blind_lattice" in entry:
            entry["delta_lattice_minus_regional"] = entry["blind_lattice"]["dti"] - entry["regional"]["dti"]
        report["fold_slices"][f"fold{fold}"] = entry

    paired: dict[str, object] = {}
    for other in arms:
        if other == ARMS[0]:
            continue
        paired[other] = {
            "density_shift": _paired_delta(
                {k: v["dti"] for k, v in report["density_shift"][other].items()
                 if not k.startswith("_")},
                {k: v["dti"] for k, v in report["density_shift"][ARMS[0]].items()
                 if not k.startswith("_")},
            ),
            "cluster_shift": _paired_delta(
                {k: v["dti"] for k, v in report["cluster_shift"][other].items()
                 if not k.startswith("_")},
                {k: v["dti"] for k, v in report["cluster_shift"][ARMS[0]].items()
                 if not k.startswith("_")},
            ),
            "fold_slices": _paired_delta(
                {k: v[other]["dti"] for k, v in report["fold_slices"].items()},
                {k: v[ARMS[0]]["dti"] for k, v in report["fold_slices"].items()},
            ),
        }
    report["paired"] = paired
    report["elapsed_seconds"] = round(time.time() - started, 1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} in {report['elapsed_seconds']}s")
    for bucket in ("density_shift", "cluster_shift"):
        for tag in sorted(k for k in report[bucket][ARMS[0]] if not k.startswith("_")):
            line = f"  {bucket:14s} {tag:12s}"
            for arm in arms:
                line += f" {arm}={report[bucket][arm][tag]['dti']:.6f}"
            print(line)
    for fold, entry in sorted(report["fold_slices"].items()):
        line = f"  {fold}"
        for arm in arms:
            line += f" {arm}={entry[arm]['dti']:.6f}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
