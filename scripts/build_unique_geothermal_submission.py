#!/usr/bin/env python3
"""
Build a *unique* GEMS submission GeoTIFF targeting concealed geothermal structures
using free official external layers, with an off-lattice uniqueness constraint.

Scientific rationale (PhD-level):
---------------------------------
The h19-5 family dominating GEMSDOE24/25/27/28/30/31/32/33/36 (owner-reported
0.1922 → 0.2600 → 0.2708 → 0.2778 → 0.2750) gains purely by "denominator hygiene":
each step removes dots within 1–2 px of catalogue faults, cutting the alpha=0.2
false-positive term. No new dots are added and no new geology is recovered. The
pruning ceiling is exhausted; further gains require RECALL of concealed faults,
which carry beta=0.8 false-negative weight (4× the FP weight).

This script takes the opposite lane: instead of avoiding catalogue faults, it
places dots in *geothermal-plausible structural settings* where concealed faults
are most likely but least mapped — near Quaternary faults, young volcanism, and
surface fluid indicators (paleo-springs, 2 m temperature probes) — using free
official external layers (USGS GDR Quaternary faults, USGS GDR Quaternary
volcanics, USGS GDR paleo-geothermal springs/probes, USGS SGMC state geologic-map
faults). Every layer is a public USGS/DOE product; nothing is copied from a prior
GEMSDOE submission.

Uniqueness mechanism:
- Dots are placed only in valid-footprint pixels that are NOT within 3 px of any
  dot in the pinned 13GEMSDOE lattice (docs/downloads/gems30-PTA1-...tif).
  This guarantees 0.0000% within-3-px overlap with the lattice reference, well
  below the 70% duplicate-stop threshold.
- The scoring function uses external geological indicators independent of the
  USGS/INGENIOUS training catalogue, producing a spatial pattern distinct from
  catalogue-avoidance strategies.

Output: single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m, NaN outside
the footprint, values in [0,1] inside — matching the published GEMS format.

STATUS: RESEARCH ARTIFACT. Format-valid locally. Holdout validation requires
organizer labels.tif (DrivenData login-gated). Not OK to submit to DrivenData
until holdout gate (paired CI > 0 vs control) and both novelty stages pass.
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
from scipy.ndimage import distance_transform_edt

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
        if abs(src.transform.a - 100.0) > 1e-6 or abs(src.transform.e + 100.0) > 1e-6:
            raise ValueError(f"external layer {path.name} transform not 100 m north-up")
    if nodata_val is not None:
        data = np.where(data == nodata_val, 0.0, data)
    return np.clip(data, 0.0, 1.0)


def build_concealed_geothermal_score(
    template_path: Path,
    lattice_path: Path,
    external_dir: Path,
    *,
    dot_budget: int = 37654,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Construct a fault-probability raster targeting concealed geothermal structures.

    Strategy (unique vs h19-5 family):
      * Work only in valid-footprint pixels NOT within 3 px of any lattice dot
        (off-lattice mask). This guarantees 0% within-3-px overlap with the
        pinned 13GEMSDOE lattice reference.
      * Score = distance-weighted combination of independent geothermal indicators:
          - qfaults / sgmc_faults: mapped Quaternary/state geologic fault traces
            (potential concealed extensions not in USGS/INGENIOUS catalogue)
          - volcanics: young volcanic centers where blind feeder faults exist
          - paleo_springs / probes_2m: surface expression of deep fluid ascent
        Distance transforms convert each binary layer into a continuous
        "proximity to geothermal structure" score (closer = higher).
      * Multiplicative boost where multiple indicators co-occur: co-location of
        fault + volcanics + fluid marks high-probability concealed geothermal
        structures (step-overs, relay ramps, blind feeders).
      * Score-ordered Poisson-disk thinning places sparse, well-separated dots at
        the top quantile — controlling FP mass while maximizing recall of
        concealed faults.

    Returns (probs, valid_mask, info_dict).
    """
    rng = np.random.default_rng(seed)

    with rasterio.open(template_path) as tpl:
        template_data = tpl.read(1, masked=False)
        valid = np.isfinite(template_data)
        profile = tpl.profile.copy()
        transform = tpl.transform
        crs = tpl.crs

    height, width = template_data.shape

    # ---- Lattice reference for uniqueness ----
    with rasterio.open(lattice_path) as src:
        lattice = src.read(1, masked=False)
    lattice_valid = np.isfinite(lattice)
    lattice_dots = lattice_valid & (lattice > 0)
    dist_to_lattice = distance_transform_edt(
        ~lattice_dots, sampling=(100.0, 100.0)
    )
    off_lattice = (dist_to_lattice > 300.0) & valid
    print(f"  valid footprint pixels: {valid.sum():,}")
    print(f"  lattice dots: {lattice_dots.sum():,}")
    print(f"  off-lattice pixels (>300 m from any lattice dot): {off_lattice.sum():,} "
          f"({off_lattice.sum()/valid.sum()*100:.2f}% of valid)")

    # ---- Load official external structural layers ----
    layer_files = {
        "qfaults": "derived_gdr_qfaults_v2_100m_u8.tif",
        "volcanics": "derived_gdr_volcanics_100m_u8.tif",
        "paleo_springs": "derived_gdr_paleo_100m_u8.tif",
        "probes_2m": "derived_gdr_2m_probes_100m_u8.tif",
        "sgmc_faults": "derived_sgmc_faults_100m_u8.tif",
    }
    layers: dict[str, np.ndarray] = {}
    for key, fname in layer_files.items():
        p = external_dir / fname
        if p.is_file():
            layers[key] = load_external_layer(p, (height, width))
            present_frac = (layers[key] > 0).mean()
            print(f"  loaded {key}: {p.name}  present_frac={present_frac:.6f}")
        else:
            print(f"  MISSING external layer {fname} — treated as zero")
            layers[key] = np.zeros((height, width), dtype=np.float32)

    # ---- Distance transforms: proximity to each geothermal indicator ----
    # Closer to an indicator = higher score. Distance in meters, kernel radius 300 m.
    RADIUS_M = 300.0
    PIXEL_M = 100.0

    def proximity_score(binary: np.ndarray) -> np.ndarray:
        """Return 1 - d/R clipped to [0,1] where d = distance to nearest 1-pixel."""
        if not binary.any():
            return np.zeros(binary.shape, dtype=np.float32)
        dist = distance_transform_edt(~binary, sampling=(PIXEL_M, PIXEL_M))
        return np.clip(1.0 - dist / RADIUS_M, 0.0, 1.0).astype(np.float32)

    fault_prox = np.maximum(
        proximity_score(layers["qfaults"] > 0),
        proximity_score(layers["sgmc_faults"] > 0),
    )
    volcanic_prox = proximity_score(layers["volcanics"] > 0)
    fluid_prox = np.maximum(
        proximity_score(layers["paleo_springs"] > 0),
        proximity_score(layers["probes_2m"] > 0),
    )

    # ---- Co-location boost: multiplicative interaction where indicators coincide ----
    # A concealed fault is most probable where multiple independent indicators
    # co-occur. The interaction term is high only when two or more indicators
    # are simultaneously close — targeting step-overs, relay ramps, blind feeders.
    fault_volc = fault_prox * volcanic_prox
    fault_fluid = fault_prox * fluid_prox
    volc_fluid = volcanic_prox * fluid_prox
    all_three = fault_prox * volcanic_prox * fluid_prox

    # ---- Final structural score (weighted, in [0,1]) ----
    # Weights: fault proximity (0.30), volcanic (0.25), fluid (0.20),
    # co-location boosts (0.15 each for pairwise, 0.10 for triple).
    W_FAULT, W_VOLC, W_FLUID = 0.30, 0.25, 0.20
    W_FV, W_FF, W_VF, W_ALL = 0.15, 0.15, 0.10, 0.10

    structural = (
        W_FAULT * fault_prox
        + W_VOLC * volcanic_prox
        + W_FLUID * fluid_prox
        + W_FV * fault_volc
        + W_FF * fault_fluid
        + W_VF * volc_fluid
        + W_ALL * all_three
    )
    structural = np.clip(structural, 0.0, 1.0)

    # ---- Restrict to off-lattice areas for uniqueness ----
    structural = np.where(off_lattice, structural, 0.0)

    # ---- Dot placement: score-ordered Poisson-disk thinning ----
    flat_scores = structural.ravel()
    valid_idx = np.flatnonzero(off_lattice.ravel() & (flat_scores > 0))
    print(f"  off-lattice pixels with structural score > 0: {valid_idx.size:,}")

    if valid_idx.size == 0:
        raise RuntimeError("no valid off-lattice pixels with positive structural score")

    k = min(dot_budget, valid_idx.size)

    # Score-ordered: take highest-scoring pixels first, then thin.
    order = np.argsort(-flat_scores[valid_idx], kind="stable")
    # Oversample 5x for thinning to ensure we reach the budget
    top_idx = valid_idx[order[: min(k * 5, valid_idx.size)]]

    from gemsdoe30.emission import poisson_disk_select

    top_scores = flat_scores[top_idx]
    rows, cols = np.unravel_index(top_idx, (height, width))

    # Build a temporary score surface for thinning (only at candidate pixels)
    candidate_surface = np.full((height, width), -np.inf, dtype=np.float32)
    candidate_surface[rows, cols] = top_scores

    # Try radius 3.0 px first (300 m, matches metric kernel)
    kept_mask = poisson_disk_select(
        candidate_surface,
        radius_px=3.0,
        mask=off_lattice,
        limit=len(top_idx),
    )
    kept_rows, kept_cols = np.nonzero(kept_mask)
    print(f"  placed dots after Poisson-disk thinning (r=3.0px): {len(kept_rows):,} (budget {dot_budget:,})")

    # If too few dots, try smaller radius
    if len(kept_rows) < dot_budget * 0.6:
        kept_mask = poisson_disk_select(
            candidate_surface,
            radius_px=2.0,
            mask=off_lattice,
            limit=len(top_idx),
        )
        kept_rows, kept_cols = np.nonzero(kept_mask)
        print(f"  retry with radius 2.0 px: {len(kept_rows):,} dots")

    if len(kept_rows) < dot_budget * 0.6:
        kept_mask = poisson_disk_select(
            candidate_surface,
            radius_px=1.5,
            mask=off_lattice,
            limit=len(top_idx),
        )
        kept_rows, kept_cols = np.nonzero(kept_mask)
        print(f"  retry with radius 1.5 px: {len(kept_rows):,} dots")

    # Cap at budget if needed - keep highest-scoring subset
    if len(kept_rows) > dot_budget:
        kept_scores = flat_scores[np.ravel_multi_index((kept_rows, kept_cols), (height, width))]
        sub_order = np.argsort(-kept_scores, kind="stable")[:dot_budget]
        kept_rows, kept_cols = kept_rows[sub_order], kept_cols[sub_order]

    probs = np.zeros((height, width), dtype=np.float32)
    probs[kept_rows, kept_cols] = 1.0

    # ---- Validate in-footprint range ----
    inside = probs[valid]
    if not np.all(np.isfinite(inside)):
        raise ValueError("in-footprint values not finite")
    if np.any((inside < 0) | (inside > 1)):
        raise ValueError("in-footprint values not in [0,1]")

    info = {
        "valid_pixels": int(valid.sum()),
        "lattice_dots": int(lattice_dots.sum()),
        "off_lattice_pixels": int(off_lattice.sum()),
        "off_lattice_with_score": int(valid_idx.size),
        "dots_placed": int(len(kept_rows)),
        "dot_budget": int(dot_budget),
        "seed": int(seed),
    }
    return probs, valid, info


def novelty_audit(probs: np.ndarray, valid: np.ndarray, repo_root: Path, output_name: str = "") -> dict:
    """Compare dot support against locally available TIFs for 3 px overlap."""
    dot_coords = np.argwhere(probs > 0)
    download_dir = repo_root / "docs" / "downloads"
    results = []
    max_overlap = 0.0
    max_name = ""

    if download_dir.is_dir() and dot_coords.size > 0:
        from scipy.ndimage import distance_transform_edt

        for tif in sorted(download_dir.glob("*.tif")):
            # Skip self-comparison
            if output_name and tif.name == output_name:
                continue
            try:
                with rasterio.open(tif) as src:
                    other = src.read(1, masked=False)
                if other.shape != probs.shape:
                    continue
                other_valid = np.isfinite(other)
                other_dots = np.argwhere(other_valid & (other > 0))
                if other_dots.size == 0:
                    continue
                other_mask = np.zeros(probs.shape, dtype=bool)
                other_mask[tuple(other_dots.T)] = True
                dist = distance_transform_edt(~other_mask, sampling=(100.0, 100.0))
                within3 = dist[tuple(dot_coords.T)] <= 300.0
                frac = float(within3.mean())
                results.append({"file": tif.name, "dots": int(other_dots.size), "within3px": frac})
                if frac > max_overlap:
                    max_overlap = frac
                    max_name = tif.name
            except Exception as exc:  # noqa: BLE001
                results.append({"file": tif.name, "error": str(exc)})

    return {
        "dots_in_submission": int(dot_coords.size),
        "max_within3px_overlap": max_overlap,
        "max_overlap_file": max_name,
        "below_70pct_threshold": max_overlap < 0.70,
        "details": results,
    }


def rank_correlation_audit(probs: np.ndarray, repo_root: Path, output_name: str = "") -> dict:
    """Compute Spearman rank correlation of the score surface against each local raster."""
    from scipy.stats import spearmanr

    flat_probs = probs.ravel()
    valid_mask = np.isfinite(flat_probs)
    results = []
    max_rho = 0.0
    max_name = ""

    download_dir = repo_root / "docs" / "downloads"
    if download_dir.is_dir():
        for tif in sorted(download_dir.glob("*.tif")):
            if output_name and tif.name == output_name:
                continue
            try:
                with rasterio.open(tif) as src:
                    other = src.read(1, masked=False)
                if other.shape != probs.shape:
                    continue
                flat_other = other.ravel()
                # Only compare where both are finite
                both_valid = valid_mask & np.isfinite(flat_other)
                if both_valid.sum() < 100:
                    continue
                rho, _ = spearmanr(flat_probs[both_valid], flat_other[both_valid])
                if np.isnan(rho):
                    rho = 0.0
                results.append({"file": tif.name, "spearman_rho": float(rho)})
                if abs(rho) > max_rho:
                    max_rho = abs(rho)
                    max_name = tif.name
            except Exception as exc:  # noqa: BLE001
                results.append({"file": tif.name, "error": str(exc)})

    return {
        "max_abs_spearman_rho": max_rho,
        "max_rho_file": max_name,
        "below_90pct_threshold": max_rho < 0.90,
        "details": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True,
                        help="sample_submission.tif grid template")
    parser.add_argument("--lattice", type=Path, required=True,
                        help="pinned 13GEMSDOE lattice TIF for uniqueness check")
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--output", type=Path, required=True, help="output GeoTIFF path")
    parser.add_argument("--sidecar", type=Path, default=None, help="JSON receipt path")
    parser.add_argument("--run-name", required=True, help="submission run name")
    parser.add_argument("--note", required=True, help="submission note, ≤140 chars")
    parser.add_argument("--dot-budget", type=int, default=37654)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if len(args.note) > 140:
        raise ValueError("note must be at most 140 characters")

    if not args.template.is_file():
        raise FileNotFoundError(f"template not found: {args.template}")
    if not args.lattice.is_file():
        raise FileNotFoundError(f"lattice not found: {args.lattice}")

    output_name = args.output.name

    probs, valid, info = build_concealed_geothermal_score(
        args.template,
        args.lattice,
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

    # ---- Novelty self-audit ----
    print("\n--- Local novelty self-audit (3 px dot overlap vs available rasters) ---")
    audit = novelty_audit(probs, valid, _REPO_ROOT, output_name=output_name)
    for detail in audit["details"]:
        if "error" in detail:
            print(f"  {detail['file']:70s} audit skipped ({detail['error']})")
        else:
            print(f"  {detail['file']:70s} dots={detail['dots']:,} within3px={detail['within3px']:.3f}")
    print(f"\nMAX 3-px dot overlap vs any local raster: {audit['max_within3px_overlap']:.3f} ({audit['max_overlap_file']})")
    if audit["below_70pct_threshold"]:
        print("  >>> Below 70% threshold — not a literal duplicate of any local raster <<<")
    else:
        print("  >>> ABOVE 70% duplicate-stop threshold — treat as duplicate candidate <<<")

    # ---- Rank correlation audit ----
    print("\n--- Rank correlation audit (Spearman vs available rasters) ---")
    corr_audit = rank_correlation_audit(probs, _REPO_ROOT, output_name=output_name)
    for detail in corr_audit["details"]:
        if "error" in detail:
            print(f"  {detail['file']:70s} audit skipped ({detail['error']})")
        else:
            print(f"  {detail['file']:70s} rho={detail['spearman_rho']:+.3f}")
    print(f"\nMAX |Spearman rho| vs any local raster: {corr_audit['max_abs_spearman_rho']:.3f} ({corr_audit['max_rho_file']})")
    if corr_audit["below_90pct_threshold"]:
        print("  >>> Below 0.90 threshold — not drift into another lane <<<")
    else:
        print("  >>> ABOVE 0.90 threshold — drift into another lane, stop <<<")

    # ---- Format re-validation ----
    print("\n--- Format re-validation ---")
    report = validate_submission_file(args.output, args.template)
    print(json.dumps(report.to_dict(), indent=2))
    if not report.passed:
        print("FORMAT VALIDATION FAILED — not OK to submit")
        return 2

    print(f"\nGeoTIFF written: {args.output}")
    print(f"SHA-256: {manifest['output_sha256']}")
    print(f"Published GEMS format compliant: {manifest['published_format_compliant']}")
    print(f"Active pixels: {info['dots_placed']:,}")
    print(f"Off-lattice pixels: {info['off_lattice_pixels']:,} ({info['off_lattice_pixels']/info['valid_pixels']*100:.2f}% of valid)")
    print(f"Max within-3px overlap vs registry: {audit['max_within3px_overlap']:.3f}")
    print(f"Max |Spearman rho| vs registry: {corr_audit['max_abs_spearman_rho']:.3f}")

    print("\nSTATUS: RESEARCH ARTIFACT — NOT OK TO SUBMIT TO DRIVENDATA.")
    print("  Requires: holdout gate (paired CI > 0 vs control), both novelty stages,")
    print("  fresh lane assignment, and separate selector approval before any slot.")
    print("  Holdout validation requires organizer labels.tif (login-gated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())