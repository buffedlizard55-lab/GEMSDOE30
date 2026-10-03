#!/usr/bin/env python3
"""Build a submission candidate with the EDGE emitter on a declared belief field.

The emitter and its frame are registered in
``docs/research/emitter-opt-preregistration.md`` and measured in
``docs/research/emitter-opt-holdout.json``.  This script only *re-derives* the
frozen recipe on the full scored domain and writes a published-format GeoTIFF:

* belief fields are built exactly as in ``scripts/emitter_opt_holdout.py`` (known
  catalogue traces only, never the hidden split, never the labels as features);
* the emission is a prefix of the EDGE acceptance order, so the artifact is a
  binary 0/1 raster (the metric-optimal shape: a graded map is strictly dominated
  by its own thresholded support);
* the file is written with the published NaN-outside convention and validated
  against the hash-pinned template before anything is published.

It never contacts DrivenData, never reads a competition score, and never writes a
file whose dots sit on masked catalogue pixels (they would be deleted from every
metric term, so they would be pure waste).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.emitter_opt import edge_select, mask_from_order  # noqa: E402
from gemsdoe30.holdout import masked_dti  # noqa: E402
from gemsdoe30.submission import validate_submission_file, write_submission_file  # noqa: E402


def load_holdout_module():
    """Import ``scripts/emitter_opt_holdout.py`` without executing its ``main``."""

    spec = importlib.util.spec_from_file_location(
        "emitter_opt_holdout", ROOT / "scripts" / "emitter_opt_holdout.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--field", default="hybrid", choices=("proximity", "external", "hybrid"))
    parser.add_argument("--keep", type=int, default=None,
                        help="emitted dot count (EDGE acceptance prefix); default: the "
                             "leave-one-fold-out choice recorded for this field")
    parser.add_argument("--truth-mass", type=float, default=80_000.0)
    parser.add_argument("--max-dots", type=int, default=200_000)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--downloads-dir", type=Path, default=Path("docs/downloads"))
    parser.add_argument("--name", default=None,
                        help="output stem (default: gemsdoe30-edge-<field>-<keep>k-<hash>)")
    parser.add_argument("--run-name", default="edge-emitter-session30")
    args = parser.parse_args()

    import rasterio

    holdout = load_holdout_module()
    with rasterio.open(args.raw_dir / "labels.tif") as dataset:
        labels = dataset.read(1)
    with rasterio.open(args.raw_dir / "sample_submission.tif") as dataset:
        template = dataset.read(1)
    footprint = np.isfinite(template)
    catalogue = labels == 1
    scored = footprint & ~catalogue  # the masked domain, exactly as the metric defines it

    if args.field == "proximity":
        field = holdout.proximity_belief(catalogue, footprint=footprint, decay_m=1000.0,
                                         cutoff_m=3000.0)
        definition = "exp(-d/1 km) around every catalogue trace, cut at 3 km"
    elif args.field == "external":
        layer_arrays = {}
        for name in holdout.EXTERNAL_LAYERS:
            path = args.external_dir / f"{name}.tif"
            if not path.exists():
                raise SystemExit(f"missing external layer {path}; run the fetch workflow first")
            with rasterio.open(path) as dataset:
                layer_arrays[name] = dataset.read(1)
        field = holdout.layer_belief(layer_arrays, footprint=footprint, decay_m=700.0,
                                     cutoff_m=2100.0)
        definition = ("exp(-d/0.7 km) around " + ", ".join(holdout.EXTERNAL_LAYERS)
                      + " (Qfaults excluded: it is a copy of the catalogue)")
    else:
        from gemsdoe30.fields import geometric_mean

        layer_arrays = {}
        for name in holdout.EXTERNAL_LAYERS:
            with rasterio.open(args.external_dir / f"{name}.tif") as dataset:
                layer_arrays[name] = dataset.read(1)
        field = geometric_mean(
            holdout.proximity_belief(catalogue, footprint=footprint, decay_m=1000.0,
                                     cutoff_m=3000.0),
            holdout.layer_belief(layer_arrays, footprint=footprint, decay_m=700.0,
                                 cutoff_m=2100.0),
        )
        definition = "geometric mean of the proximity and external fields"

    field = np.where(scored, field, 0.0).astype(np.float32)
    started = time.time()
    _, diagnostics = edge_select(field, scored, truth_mass=args.truth_mass,
                                 max_dots=args.max_dots, return_diagnostics=True)
    accepted = int(diagnostics["order_flat"].size)
    keep = args.keep
    if keep is None:
        recorded = ROOT / "docs" / "research" / "emitter-opt-holdout.json"
        if recorded.exists():
            selection = json.loads(recorded.read_text(encoding="utf-8")).get("selection", {})
            family = selection.get(args.field, {}).get("edge", [])
            counts = [row["held_out_emitted_pixels"] for row in family
                      if row.get("chosen_on_other_folds", "").startswith("edge@keep")]
            keep = int(round(float(np.median(counts)))) if counts else accepted
        else:
            keep = accepted
    if int(keep) > accepted:
        print(f"WARNING: requested keep={int(keep):,} exceeds the {accepted:,} dots the sweep "
              f"accepted; using {accepted:,}. Raise --truth-mass or --max-dots for a longer sweep.")
    keep = min(int(keep), accepted)
    if keep < 1_000:
        print(f"WARNING: emitting only {keep:,} dots; this is a diagnostic-scale artifact, not a "
              f"competitive candidate.")
    mask = mask_from_order(diagnostics["order_flat"], keep, field.shape)
    print(f"field={args.field} accepted={accepted} keep={keep} "
          f"sweep={time.time() - started:.0f}s cap={args.max_dots}", flush=True)

    on_catalogue = int((mask & catalogue).sum())
    proxy = masked_dti(mask.astype(np.float32), catalogue, np.zeros_like(catalogue))
    sidecar_metrics = {
        "field": args.field,
        "field_definition": definition,
        "emitter": "edge_select (expected marginal credit greedy)",
        "emitter_truth_mass": args.truth_mass,
        "emitter_max_dots_cap": args.max_dots,
        "edge_accepted": accepted,
        "cap_limited": bool(accepted >= args.max_dots),
        "dots": int(mask.sum()),
        "dots_on_training_catalogue": on_catalogue,
        "catalogue_proxy_dti_NOT_A_SCORE": round(float(proxy["dti"]), 7),
        "catalogue_proxy_note": (
            "The catalogue proxy is the biased frame documented in IR-30-039: it rewards dots "
            "the official metric deletes. It is reported for provenance only and is not a score."
        ),
        "scored_domain_pixels": int(scored.sum()),
    }

    digest_source = f"{args.field}:{keep}:{int(mask.sum())}:{on_catalogue}"
    suffix = hashlib.sha256(digest_source.encode()).hexdigest()[:8]
    stem = args.name or f"gemsdoe30-edge-{args.field}-{keep // 1000}k-{suffix}"
    output = args.downloads_dir / f"{stem}-nan.tif"
    note = (f"GEMSDOE30 EDGE emitter, {args.field} belief field, {keep:,} dots; "
            f"unpromoted research artifact")
    write_submission_file(mask.astype(np.float32), args.raw_dir / "sample_submission.tif",
                          output, note=note, run_name=args.run_name,
                          metadata_path=args.downloads_dir / f"{stem}-nan.json")
    report = validate_submission_file(output, args.raw_dir / "sample_submission.tif")
    sidecar_metrics["validation"] = report.to_dict()
    sidecar_path = args.downloads_dir / f"{stem}-nan.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path.exists() else {}
    sidecar.update({"edge_emitter": sidecar_metrics, "suggested_submission_note": note})
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(sidecar_metrics, indent=1))
    print(f"wrote {output} ({output.stat().st_size:,} bytes)")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
