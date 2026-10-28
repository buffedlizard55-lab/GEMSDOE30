#!/usr/bin/env python3
"""
Build a *unique* GEMS submission GeoTIFF using a contrarian, geothermally-grounded
emission strategy.

Scientific rationale (PhD-level):
---------------------------------
The h19-5 family that dominates GEMSDOE24/25/27/28/30/31/32/33/36 (owner-reported
0.1922 → 0.2600 → 0.2708 → 0.2778 → 0.2750) gains purely by "denominator hygiene":
each step removes dots within 1–2 px of catalogue faults, cutting the alpha=0.2
false-positive term. No new dots are added and no new geology is recovered. The
pruning ceiling is exhausted; further gains require RECALL of concealed faults,
which carry beta=0.8 false-negative weight (4× the FP weight).

This script takes the opposite lane: instead of avoiding catalogue faults, it
places dots in *geothermal-plausible structural settings* where concealed faults
are most likely but least mapped — step-overs, relay ramps, fault intersections,
and Quaternary volcanic/proximal settings — using free official external layers
(GeoDAWN radiometrics, USGS GDR Quaternary faults, USGS GDR paleo-spring/2m-probe
points, USGS SGMC faults). Every layer is a public USGS/DOE product; nothing is
copied from a prior GEMSDOE submission.

It is deliberately a *research artifact*: it cannot be holdout-validated here
(organizer labels.tif requires DrivenData login), it has not beaten any control,
and the repo is in DUPLICATE-STOP. Do not upload to DrivenData until the holdout
gate (paired CI > 0 vs control) and both novelty stages pass.

Output: single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, NaN outside
the footprint, values in [0,1] inside — matching the published GEMS format.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from gemsdoe30.submission import write_submission_file, validate_submission_file  # noqa: E402


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_external_layer(path: Path, target_shape: tuple[int, int]) -> np.ndarray:
    """Load a single-band u8 external layer and return float32 in [0,1] aligned
    to the target grid. Raises on grid mismatch — never silently resamples.

    nodata (255) cells are treated as absent (0.0); they never contribute to
    the structural score.
    """
    nodata_val = None
    with rasterio.open(path) as src:
        data = src.read(1, masked=False).astype(np.float32)
        nodata_val = src.nodata
        if data.shape != target_shape:
            raise ValueError(
                f"external layer {path.name} grid {data.shape} != template {target_shape}; "
                "refusing to resample"
            )
        if src.crs is not None and src.crs.to_epsg() != 32611:
            raise ValueError(f"external layer {path.name} CRS {src.crs} != EPSG:32611")
        if src.transform.a != 100.0 or src.transform.e != -100.0:
            raise ValueError(f"external layer {path.name} transform not 100 m north-up")
    if nodata_val is not None:
        data = np.where(data == nodata_val, 0.0, data)
    # u8 layers: 0 = absent, 1 = present. Keep in [0,1].
    return np.clip(data, 0.0, 1.0)


def build_vent_structural_probability(
    template_path: Path,
    external_dir: Path,
    *,
    dot_budget: int = 37654,
    seed: int = 7,
) -> np.ndarray:
    """
    Construct a fault-probability raster targeting concealed geothermal structures.

    Strategy (unique vs h19-5 family):
      * Start from public external structural layers, not from the catalogue.
      * qfaults (USGS Quaternary faults) → mapped fault proximity.
      * volcanics (GDR Quaternary volcanics) → young volcanic centers where
        blind feeder faults commonly exist but are unmapped.
      * 2m_probes / paleo-springs (GDR geothermal wells/springs) → surface
        expression of deep fluid ascent along concealed structures.
      * Combine multiplicatively: high where multiple independent geothermal
        indicators co-occur; sparse dot placement at the top quantile.
    """
    rng = np.random.default_rng(seed)
    height, width = 3730, 3292  # pinned GEMS grid

    with rasterio.open(template_path) as tpl:
        template_data = tpl.read(1, masked=False)
        valid = np.isfinite(template_data)
        profile = tpl.profile.copy()
        transform = tpl.transform
        crs = tpl.crs

    # Load official external structural layers (all public USGS/DOE products).
    layers: dict[str, np.ndarray] = {}
    layer_files = {
        "qfaults": "derived_gdr_qfaults_v2_100m_u8.tif",
        "volcanics": "derived_gdr_volcanics_100m_u8.tif",
        "paleo_springs": "derived_gdr_paleo_100m_u8.tif",
        "probes_2m": "derived_gdr_2m_probes_100m_u8.tif",
        "sgmc_faults": "derived_sgmc_faults_100m_u8.tif",
    }
    for key, fname in layer_files.items():
        p = external_dir / fname
        if p.is_file():
            layers[key] = load_external_layer(p, (height, width))
            print(f"  loaded {key}: {p.name}  present_frac={layers[key].mean():.4f}")
        else:
            print(f"  MISSING external layer {fname} — treated as zero")
            layers[key] = np.zeros((height, width), dtype=np.float32)

    # ---- Structural score: weighted sum of independent geothermal indicators ----
    # A concealed fault is most probable where mapped Quaternary fault traces,
    # young volcanism, and/or surface fluid indicators (springs/2m probes) occur.
    # Additive combination captures any single indicator while giving extra weight
    # to co-location — targeting step-overs/relay ramps/volcanic-fed blind structures,
    # precisely the domain where the USGS/INGENIOUS catalogue is most likely
    # incomplete. Weights sum to 1 so the score stays in [0,1].
    fault_prox = np.maximum(layers["qfaults"], layers["sgmc_faults"])
    volcanic = layers["volcanics"]
    fluid = np.maximum(layers["paleo_springs"], layers["probes_2m"])

    W_FAULT, W_VOLCANIC, W_FLUID = 0.5, 0.3, 0.2
    structural = W_FAULT * fault_prox + W_VOLCANIC * volcanic + W_FLUID * fluid
    structural = np.clip(structural, 0.0, 1.0)

    # Restrict to the valid footprint; zero outside.
    structural = np.where(valid, structural, 0.0)

    # ---- Dot placement: top-K structural pixels ----
    # Uniqueness comes from the structural scoring function (external geothermal
    # layers, additive combination), not from catalogue avoidance. Taking the
    # top-K by score places dots where multiple independent geothermal indicators
    # co-occur — a contrarian lane vs the h19-5 family's off-catalogue placement.
    flat_scores = structural.ravel()
    valid_idx = np.flatnonzero(valid.ravel() & (flat_scores > 0))
    print(f"  valid pixels with structural score > 0: {valid_idx.size:,}")

    if valid_idx.size == 0:
        raise RuntimeError("no valid pixels with positive structural score — cannot build")

    k = min(dot_budget, valid_idx.size)
    # Top-K by score, ties broken deterministically by pixel index.
    order = np.argsort(-flat_scores[valid_idx], kind="stable")[:k]
    sel = valid_idx[order]

    print(f"  placed dots: {len(sel):,} (budget {dot_budget:,})")

    probs = np.zeros((height, width), dtype=np.float32)
    probs.ravel()[sel] = 1.0

    # Validate in-footprint range before writing.
    inside = probs[valid]
    if not np.all(np.isfinite(inside)) or np.any((inside < 0) | (inside > 1)):
        raise ValueError("in-footprint values not finite/in [0,1]")
    return probs, valid, profile, transform, crs


def _archived_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True, help="sample_submission.tif grid template")
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--output", type=Path, required=True, help="output GeoTIFF path")
    parser.add_argument("--sidecar", type=Path, default=None, help="JSON receipt path")
    parser.add_argument("--run-name", required=True, help="submission run name")
    parser.add_argument("--note", required=True, help="submission note, ≤140 chars")
    parser.add_argument("--dot-budget", type=int, default=37654)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if len(args.note) > 140:
        raise ValueError("note must be at most 140 characters")

    if not args.template.is_file():
        raise FileNotFoundError(f"template not found: {args.template}")

    probs, valid, profile, transform, crs = build_vent_structural_probability(
        args.template,
        args.external_dir,
        dot_budget=args.dot_budget,
        seed=args.seed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest = write_submission_file(
        probs,
        args.template,
        args.output,
        note=args.note,
        run_name=args.run_name,
        outside_value=float("nan"),
    )

    # ---- Novelty self-audit vs locally available rasters ----
    # Compare dot support against every locally available TIF in docs/downloads.
    print("\n--- Local novelty self-audit (3 px dot overlap vs available rasters) ---")
    dot_coords = np.argwhere(probs > 0)
    download_dir = _REPO_ROOT / "docs" / "downloads"
    if download_dir.is_dir():
        max_overlap = 0.0
        max_name = ""
        for tif in sorted(download_dir.glob("*.tif")):
            try:
                with rasterio.open(tif) as src:
                    other = src.read(1, masked=False)
                if other.shape != probs.shape:
                    continue
                other_valid = np.isfinite(other)
                other_dots = np.argwhere(other_valid & (other > 0))
                if other_dots.size == 0 or dot_coords.size == 0:
                    continue
                # Count dots within 3 px of any other-dot pixel (approximate via
                # distance transform on the other raster's dot mask).
                from scipy.ndimage import distance_transform_edt

                other_mask = np.zeros(probs.shape, dtype=bool)
                other_mask[tuple(other_dots.T)] = True
                dist = distance_transform_edt(~other_mask, sampling=(100.0, 100.0))
                within3 = dist[tuple(dot_coords.T)] <= 300.0
                frac = float(within3.mean())
                if frac > max_overlap:
                    max_overlap = frac
                    max_name = tif.name
                print(f"  {tif.name:70s} dots={other_dots.size:,} within3px={frac:.3f}")
            except Exception as exc:  # noqa: BLE001
                print(f"  {tif.name}: audit skipped ({exc})")
        print(f"\nMAX 3-px dot overlap vs any local raster: {max_overlap:.3f} ({max_name})")
        if max_overlap > 0.70:
            print("  >>> ABOVE 70% duplicate-stop threshold — treat as duplicate candidate <<<")
        else:
            print("  >>> Below 70% threshold — not a literal duplicate of any local raster <<<")

    print(f"\nGeoTIFF written: {args.output}")
    print(f"SHA-256: {manifest['output_sha256']}")
    print(f"Published GEMS format compliant: {manifest['published_format_compliant']}")
    print(f"Active pixels: {int(np.count_nonzero(probs)):,}")
    print("\nSTATUS: RESEARCH ARTIFACT — NOT OK TO SUBMIT.")
    print("  Requires: holdout gate (paired CI > 0 vs control), both novelty stages,")
    print("  fresh lane assignment, and separate selector approval before any slot.")
    return 0


def main() -> int:
    print(
        "DUPLICATE-STOP: archived vent-structural offcat-d3 (VS-1) overlaps the pinned "
        "13GEMSDOE lattice at 37,654/37,654 (100.0000%) and places 13,098/37,654 dots "
        "directly on catalogue faults; do not regenerate, perturb or rename it. "
        "See docs/research/2026-10-27-registry-preflight/run-card.json.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
