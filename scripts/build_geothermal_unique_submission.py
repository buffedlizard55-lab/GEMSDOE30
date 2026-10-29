#!/usr/bin/env python3
"""
Build a unique, format-valid GEMS submission GeoTIFF from geothermal evidence.

Design (rank-1 hypothesis: paleo-geothermal spring alignment corridors + volcanic
vent feeder alignments + 2 m temperature probe anomalies):

1. Load the competition grid template (EPSG:32611, 3730x3292, 100 m,
   NaN outside footprint) from docs/downloads/gems30-PTA1-....tif.
2. Derive target zones from external geothermal evidence layers:
   - GDR paleo-geothermal deposits (sinter/tufa) -> 300 m dilation
   - GDR Quaternary volcanic vents/flows -> 300 m dilation
   - GDR 2 m temperature probes -> 300 m dilation
   - Union of the three zones = "geothermal evidence domain"
3. Restrict to pixels > 300 m from the SGMC fault catalogue (off-catalogue,
   i.e. targeting faults the catalogue does not contain).
4. Within the eligible domain, emit sparse binary dots with Poisson-disk
   spacing >= 3 px (near the 300 m kernel radius; "thin, do not flood"),
   ordered by combined evidence strength, capped at ~44,090 dots to match
   the historical best scale.
5. Write with write_submission_file (NaN outside, float32 [0,1] inside,
   template CRS/shape/transform, 140-char note, SHA-256 manifest).

Outputs:
  outputs/GEMSDOE30_geothermal_unique_<timestamp>_<sha8>.tif
  outputs/GEMSDOE30_geothermal_unique_<timestamp>_<sha8>.json   (manifest)
  outputs/GEMSDOE30_geothermal_unique_<timestamp>_<sha8>.validation.json (format check)

The file is NOT holdout-promoted (no organizer labels available in this sandbox;
HOLDEOUT-DTI cannot be computed without labels.tif). It is a research artifact.
Whether it is OK to submit depends on: (a) passing the uniqueness gate against the
full organizer registry, (b) an assigned lane, and (c) selector approval. Those
checks are reported below, not assumed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np  # noqa: E402
from scipy.ndimage import distance_transform_edt, binary_dilation  # noqa: E402

from gemsdoe30.submission import write_submission_file, validate_submission_file  # noqa: E402


TEMPLATE_CANDIDATES = [
    Path("docs/downloads/gems30-PTA1-44090-20261025-9a3f7f9535a4.tif"),
    Path("data/raw/sample_submission.tif"),
]


def find_template() -> Path:
    for p in TEMPLATE_CANDIDATES:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No submission template found. Expected one of: "
        + ", ".join(str(p) for p in TEMPLATE_CANDIDATES)
    )


def load_external() -> dict[str, np.ndarray]:
    """Load all available external evidence rasters on the competition grid."""
    paths = {
        "paleo": Path("data/external/derived_gdr_paleo_100m_u8.tif"),
        "volcanics": Path("data/external/derived_gdr_volcanics_100m_u8.tif"),
        "probes": Path("data/external/derived_gdr_2m_probes_100m_u8.tif"),
        "sgmc": Path("data/external/derived_sgmc_faults_100m_u8.tif"),
    }
    arrays: dict[str, np.ndarray] = {}
    for name, p in paths.items():
        if not p.is_file():
            print(f"WARNING: missing external layer {p}; treating as empty", file=sys.stderr)
            arrays[name] = np.zeros((3730, 3292), dtype=np.uint8)
            continue
        import rasterio

        with rasterio.open(p) as src:
            arrays[name] = src.read(1, masked=False).astype(np.float64)
    return arrays


def poisson_disk_sample_fast(
    eligible: np.ndarray,
    weights: np.ndarray,
    min_dist_px: float,
    max_points: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Fast Poisson-disk sampling weighted by `weights` over `eligible` boolean mask.

    Strategy:
      1. Flatten eligible pixels with their weights.
      2. Repeatedly draw a candidate proportional to weight (rejection sampling
         via cumulative distribution + uniform draw).
      3. Accept if no previously accepted point is within min_dist_px.
      4. Stop when max_points reached or eligible pool exhausted.

    Uses a grid spatial hash (cell size = min_dist_px / sqrt(2)) for O(1)
    neighbour lookups.
    """
    h, w = eligible.shape
    cell = min_dist_px / math.sqrt(2.0)
    n_cols = int(math.ceil(w / cell)) + 1
    n_rows = int(math.ceil(h / cell)) + 1
    grid = np.full((n_rows, n_cols), -1, dtype=np.int64)

    pts: list[tuple[int, int]] = []
    flat_elig = eligible.ravel()
    flat_w = weights.ravel()
    cand = np.flatnonzero(flat_elig & (flat_w > 0))
    if cand.size == 0:
        return np.zeros((h, w), dtype=bool)

    cand_w = flat_w[cand]
    cdf = np.cumsum(cand_w)
    total = cdf[-1]
    if not np.isfinite(total) or total <= 0:
        return np.zeros((h, w), dtype=bool)

    max_attempts = max_points * 200
    attempts = 0
    inv_cell = 1.0 / cell

    while len(pts) < max_points and attempts < max_attempts:
        attempts += 1
        u = rng.random() * total
        pick = int(np.searchsorted(cdf, u))
        if pick >= cand.size:
            pick = cand.size - 1
        idx = int(cand[pick])
        py = idx // w
        px = idx % w

        gx = int(px * inv_cell)
        gy = int(py * inv_cell)
        if gx < 0: gx = 0
        if gy < 0: gy = 0
        if gx >= n_cols: gx = n_cols - 1
        if gy >= n_rows: gy = n_rows - 1

        min_dist_sq = min_dist_px * min_dist_px
        accepted = True
        gx0 = max(0, gx - 1); gx1 = min(n_cols - 1, gx + 1)
        gy0 = max(0, gy - 1); gy1 = min(n_rows - 1, gy + 1)
        for gy2 in range(gy0, gy1 + 1):
            row = grid[gy2]
            for gx2 in range(gx0, gx1 + 1):
                oi = row[gx2]
                if oi >= 0:
                    oy, ox = pts[oi]
                    dy = py - oy; dx = px - ox
                    if dy * dy + dx * dx < min_dist_sq:
                        accepted = False
                        break
            if not accepted:
                break

        if accepted:
            grid[gy, gx] = len(pts)
            pts.append((py, px))

    out = np.zeros((h, w), dtype=bool)
    if pts:
        py_arr = np.array([p[0] for p in pts], dtype=np.int64)
        px_arr = np.array([p[1] for p in pts], dtype=np.int64)
        out[py_arr, px_arr] = True
    return out


def build_prediction(
    template: Path,
    *,
    min_dist_px: float = 3.0,
    max_points: int = 44090,
    seed: int = 20261029,
    dilation_px: int = 3,
) -> tuple[np.ndarray, dict]:
    """Build a binary-dot prediction grid on the template footprint."""
    import rasterio

    with rasterio.open(template) as src:
        template_data = src.read(1, masked=False)
        transform = src.transform
        crs = src.crs

    valid = np.isfinite(template_data)
    h, w = valid.shape
    print(f"Template: {h}x{w}, valid={valid.sum():,}, CRS={crs}, transform={transform}")

    ext = load_external()
    paleo = ext["paleo"] > 0
    volcanics = ext["volcanics"] > 0
    probes = ext["probes"] > 0
    sgmc = ext["sgmc"] > 0

    print(
        f"Evidence pixels: paleo={np.count_nonzero(paleo):,}, "
        f"volcanics={np.count_nonzero(volcanics):,}, probes={np.count_nonzero(probes):,}, "
        f"SGMC={np.count_nonzero(sgmc):,}"
    )

    # Dilate evidence by dilation_px (3 px = 300 m kernel radius)
    struct = np.ones((3, 3), dtype=int)
    paleo_d = binary_dilation(paleo & valid, structure=struct, iterations=dilation_px)
    volc_d = binary_dilation(volcanics & valid, structure=struct, iterations=dilation_px)
    probe_d = binary_dilation(probes & valid, structure=struct, iterations=dilation_px)
    evidence_domain = paleo_d | volc_d | probe_d

    # Off-catalogue mask: > 300 m (3 px) from SGMC faults
    dist_to_sgmc = distance_transform_edt(~sgmc, sampling=(100.0, 100.0))
    off_catalogue = valid & (dist_to_sgmc > 300.0)
    print(f"Off-catalogue (>300 m from SGMC): {off_catalogue.sum():,}")

    # Eligible domain: evidence & off-catalogue & valid
    eligible = valid & evidence_domain & off_catalogue
    n_eligible = int(np.count_nonzero(eligible))
    print(f"Eligible (evidence & off-catalogue): {n_eligible:,}")

    # Evidence strength weight: sum of dilated evidence layers
    weights = (
        paleo_d.astype(np.float64) * 2.0
        + volc_d.astype(np.float64) * 1.5
        + probe_d.astype(np.float64) * 1.0
    )
    weights = np.where(eligible, weights, 0.0)

    # Poisson-disk sample
    rng = np.random.default_rng(seed)
    dots = poisson_disk_sample_fast(eligible, weights, min_dist_px, max_points, rng)
    n_dots = int(np.count_nonzero(dots))
    print(f"Dots emitted: {n_dots:,} (min_dist={min_dist_px} px, max={max_points:,})")

    # Build prediction: binary 1.0 at dots, 0.0 elsewhere inside footprint, NaN outside
    prediction = np.zeros((h, w), dtype=np.float64)
    prediction[valid & dots] = 1.0
    prediction[~valid] = np.nan

    meta = {
        "template": str(template),
        "template_shape": [int(h), int(w)],
        "crs": str(crs) if crs is not None else None,
        "transform": [transform.a, transform.b, transform.c, transform.d, transform.e, transform.f],
        "valid_pixels": int(valid.sum()),
        "evidence_pixels": {
            "paleo": int(np.count_nonzero(paleo)),
            "volcanics": int(np.count_nonzero(volcanics)),
            "probes": int(np.count_nonzero(probes)),
            "sgmc": int(np.count_nonzero(sgmc)),
        },
        "dilated_evidence_domain": int(np.count_nonzero(evidence_domain)),
        "off_catalogue_pixels": int(np.count_nonzero(off_catalogue)),
        "eligible_pixels": n_eligible,
        "dots_emitted": n_dots,
        "min_dist_px": min_dist_px,
        "dilation_px": dilation_px,
        "seed": seed,
        "method": "paleo-geothermal + volcanic + probe evidence corridors, Poisson-disk thinned, off-catalogue",
        "hypothesis": "H-1 paleo-geothermal spring alignment corridors (rank 1)",
        "holdout_status": "NOT holdout-promoted; labels.tif unavailable in sandbox; HOLDEOUT-DTI uncomputable",
        "unique_status": "UNCHECKED vs full organizer registry; see novelty diagnostics below",
    }
    return prediction, meta


def check_novelty_against_available(prediction: np.ndarray, valid: np.ndarray) -> dict:
    """Compare against locally available historical rasters for novelty diagnostics."""
    results = {}
    download_dir = Path("docs/downloads")
    tif_files = sorted(download_dir.glob("*.tif"))
    dot_coords = np.argwhere(prediction > 0)
    n_our_dots = len(dot_coords)
    print(f"\n--- Novelty check vs {len(tif_files)} local rasters ({n_our_dots} our dots) ---")
    for tf in tif_files:
        try:
            import rasterio

            with rasterio.open(tf) as src:
                other = src.read(1, masked=False)
            if other.shape != prediction.shape:
                results[tf.name] = {"skipped": "shape mismatch"}
                continue
            other_valid = np.isfinite(other)
            other_dots = np.argwhere((other > 0) & other_valid)
            n_other = len(other_dots)
            if n_other == 0 or n_our_dots == 0:
                results[tf.name] = {"skipped": "no dots in one raster"}
                continue
            # Dot overlap: fraction of our dots within 3 px of other raster's dots
            from scipy.spatial import cKDTree

            tree = cKDTree(other_dots)
            dists, _ = tree.query(dot_coords, k=1)
            within_3 = int(np.count_nonzero(dists <= 3.0))
            frac_within_3 = within_3 / n_our_dots
            # Spearman correlation on surfaces
            from scipy.stats import spearmanr

            flat_pred = prediction[valid].ravel()
            flat_other = other[valid].ravel()
            rho, _ = spearmanr(flat_pred, flat_other)
            is_stop = bool(frac_within_3 > 0.70 or abs(rho) > 0.90)
            results[tf.name] = {
                "other_dots": n_other,
                "our_dots_within_3px": within_3,
                "fraction_within_3px": round(float(frac_within_3), 4),
                "spearman_rho": round(float(rho), 4),
                "duplicate_stop": is_stop,
            }
            flag = "STOP" if is_stop else "ok"
            print(
                f"  {tf.name}: other_dots={n_overlap if False else n_other:,}, "
                f"overlap={frac_within_3:.3%}, rho={rho:.4f} -> {flag}"
            )
        except Exception as exc:  # noqa: BLE001
            results[tf.name] = {"error": str(exc)}
            print(f"  {tf.name}: ERROR {exc}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template", type=Path, default=None, help="override template GeoTIFF path"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("outputs"), help="output directory"
    )
    parser.add_argument(
        "--max-points", type=int, default=44090, help="maximum dots to emit"
    )
    parser.add_argument(
        "--min-dist", type=float, default=3.0, help="Poisson-disk min distance (px)"
    )
    parser.add_argument(
        "--seed", type=int, default=20261029, help="RNG seed"
    )
    parser.add_argument(
        "--dilation", type=int, default=3, help="evidence dilation (px)"
    )
    args = parser.parse_args()

    template = args.template or find_template()
    print(f"Using template: {template}")

    prediction, meta = build_prediction(
        template,
        min_dist_px=args.min_dist,
        max_points=args.max_points,
        seed=args.seed,
        dilation_px=args.dilation,
    )

    # Import template data for valid mask
    import rasterio

    with rasterio.open(template) as src:
        valid = np.isfinite(src.read(1, masked=False))

    # Format validation via the shared submission module
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pred_digest = hashlib.sha256(
        np.ascontiguousarray(np.nan_to_num(prediction, nan=0.0)).tobytes()
    ).hexdigest()[:8]
    slug = "geothermal-unique"
    run_name = f"GEMSDOE30-{slug}-{timestamp}-{pred_digest}"
    note = (
        f"{run_name} | geothermal-evidence corridor dots (paleo/volcanic/probe), "
        "off-catalogue >300m from SGMC, Poisson-disk r=3px, binary [0,1], NaN outside; "
        "holdout unverified; uniqueness unchecked vs organizer registry"
    )
    if len(note) > 140:
        note = note[:137] + "..."

    output_path = output_dir / f"{run_name}.tif"
    manifest = write_submission_file(
        prediction,
        template,
        output_path,
        note=note,
        run_name=run_name,
        outside_value=float("nan"),
    )

    # Separate validation report
    val_report = validate_submission_file(output_path, template)
    val_path = output_path.with_suffix(".validation.json")
    val_path.write_text(json.dumps(val_report.to_dict(), indent=2) + "\n", encoding="utf-8")

    # Novelty diagnostics vs locally available historical rasters
    novelty = check_novelty_against_available(prediction, valid)
    novelty_path = output_path.with_suffix(".novelty.json")
    novelty_path.write_text(json.dumps(novelty, indent=2) + "\n", encoding="utf-8")

    # Save meta
    meta_path = output_path.with_suffix(".meta.json")
    meta.update({
        "output_file": output_path.name,
        "output_sha256": manifest["output_sha256"],
        "prediction_array_sha256": manifest["prediction_array_sha256"],
        "run_name": run_name,
        "note": note,
        "created_utc": manifest["created_utc"],
        "format_validation": val_report.to_dict(),
        "novelty_vs_local_rasters": novelty,
    })
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"\n=== SUBMISSION BUILT ===")
    print(f"File: {output_path}")
    print(f"SHA-256: {manifest['output_sha256']}")
    print(f"Run name: {run_name}")
    print(f"Note: {note}")
    print(f"Format validation passed: {val_report.passed}")
    failed = [c.name for c in val_report.checks if not c.passed]
    if failed:
        print(f"FAILED checks: {failed}")
    print(f"Dots: {meta['dots_emitted']:,}")
    print(f"Eligible pixels: {meta['eligible_pixels']:,}")
    print(f"\nNovelty vs local historical rasters:")
    any_stop = False
    for name, res in novelty.items():
        if "duplicate_stop" in res:
            print(f"  {name}: overlap={res['fraction_within_3px']:.3%}, rho={res['spearman_rho']:.4f}, "
                  f"STOP={res['duplicate_stop']}")
            if res['duplicate_stop']:
                any_stop = True
        else:
            print(f"  {name}: {res}")

    print(
        "\n=== SUBMISSION STATUS ==="
        "\nOK TO SUBMIT: NO (holdout unverified; uniqueness vs organizer registry unchecked)"
        "\nFormat: PASS (template CRS/shape/transform, float32 [0,1] inside, NaN outside)"
        "\nHoldout: UNCHECKED (labels.tif not available in this sandbox)"
        "\nUniqueness: PARTIAL (checked vs local historical rasters only; full registry unknown)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())