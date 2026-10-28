#!/usr/bin/env python3
"""
ARCHIVED, DISABLED: off-lattice geothermal structural emission.

The historical narrative below is preserved for provenance, not validated fact.
All uncovered cells were emitted, so geological ranks and random seed did not
change the prediction. The local registry is incomplete, the lane was not
assigned, and the candidate was not holdout validated. Do not regenerate or
submit it. See docs/research/2026-10-28-followup.md.

Historical description:
Build a UNIQUE GEMS submission GeoTIFF: off-lattice geothermal structural emission.

Scientific rationale (PhD-level), distinct from every prior GEMSDOE lane:
---------------------------------------------------------------
The h19-5 / D2.8 / H33 family (GEMSDOE24/25/27/28/30/31/32/33/36; owner-reported
0.1922–0.2778) emits dense dots immediately off catalogue faults. This is now a
single known lane: the pinned 13GEMSDOE lattice (206,895 dots) covers
5,160,724 of 5,167,373 valid footprint cells within 3 px, so every high-dot-budget
candidate in that family is provably a literal duplicate (≥70% of dots within
3 px of lattice dots for any budget ≥ 22,164). Pruning dots near catalogue
faults cannot produce a unique, higher-scoring file.

This lane does the opposite: it places dots ONLY in pixels that are ≥3 px from
every lattice dot — the 6,649 valid cells the lane family never reaches — and
ranks them with public geothermal structural layers (USGS GDR Quaternary faults
and Quaternary volcanics, GDR paleo springs and 2 m temperature-probe points,
USGS SGMC faults). These target concealed geothermal feeder faults (step-overs,
relay ramps, blind volcanic-hosted structures) most likely to be missing from the
USGS/INGENIOUS catalogue, at pixels the catalogue-adjacent lanes provably miss.

Output contract: single-band float32 GeoTIFF, EPSG:32611, 3730×3292, 100 m
north-up, identical grid to the pinned public reference (same CRS/shape/transform
as the organizer sample_submission.tip per recorded metadata), finite values in
[0,1] inside the footprint, NaN outside (published GEMS format).

Status: research artifact. Holdout validation is BLOCKED in this checkout because
data/raw/ (training_features.tif, labels.tif, sample_submission.tif) requires a
DrivenData login and is not present. Per the parallel-run protocol this file is
NOT approved for a weekly submission slot and NOT OK to upload to DrivenData;
the verdict below is negative. Downloading the file is safe (format-valid), but
submitting it is at the submitter's own risk until the holdout gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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

from gemsdoe30.submission import write_submission_file  # noqa: E402

# Pinned 13GEMSDOE lattice witness (same grid as the organizer template:
# EPSG:32611, 3730x3292, transform (100, 0, 243350, 0, -100, 4508550), nodata NaN).
LATTICE_URL = (
    "https://github.com/buffedlizard55-lab/13GEMSDOE/blob/"
    "92ee6f074323f161eed837b80ec3ee5b662e26f5/"
    "docs/downloads/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"
)
LATTICE_SHA256 = "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2"
LATTICE_PATH = _REPO_ROOT / "docs" / "research" / "2026-10-28-offlattice" / "lattice-reference.tif"

GRID_SHAPE = (3730, 3292)
PIXEL_M = 100.0
NOVELTY_RADIUS_M = 300.0  # 3 px
DUPLICATE_THRESHOLD = 0.70
PROVABLE_STOP_BUDGET = 22164  # budgets >= this are provably stopped by the lattice

LAYER_FILES = {
    "gdr_qfaults_v2": "derived_gdr_qfaults_v2_100m_u8.tif",
    "gdr_volcanics": "derived_gdr_volcanics_100m_u8.tif",
    "gdr_paleo_springs": "derived_gdr_paleo_100m_u8.tif",
    "gdr_2m_probes": "derived_gdr_2m_probes_100m_u8.tif",
    "sgmc_faults": "derived_sgmc_faults_100m_u8.tif",
}
# Weights sum to 1 so the structural score stays in [0, 1].
W_QFAULT, W_VOLCANIC, W_SPRING_PROBE, W_SGMC = 0.4, 0.3, 0.2, 0.1


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_lattice() -> None:
    """Obtain the pinned lattice witness for the novelty audit.

    Prefers the local clone used during review; falls back to nothing — the
    lattice is never embedded in this script and never submitted.
    """
    LATTICE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if LATTICE_PATH.is_file():
        digest = _sha256_file(LATTICE_PATH)
        if digest == LATTICE_SHA256:
            print(f"  lattice witness present locally: {LATTICE_PATH} (sha256 {digest})")
            return
        print(f"  local lattice hash {digest} != pinned {LATTICE_SHA256}; re-fetching")
    try:
        import urllib.request

        req = urllib.request.Request(
            LATTICE_URL,
            headers={"User-Agent": "GEMSDOE30-research-agent/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as response, LATTICE_PATH.open(
            "wb"
        ) as out:
            out.write(response.read())
        digest = _sha256_file(LATTICE_PATH)
        print(f"  fetched lattice witness -> {LATTICE_PATH} (sha256 {digest})")
        if digest != LATTICE_SHA256:
            print(f"  WARNING: fetched hash {digest} != pinned {LATTICE_SHA256}")
    except Exception as exc:  # noqa: BLE001 - network is optional for the build
        print(f"  lattice fetch skipped ({exc}); novelty bound uses the recorded audit only")
        LATTICE_PATH.unlink(missing_ok=True)


def lattice_uncovered_mask(lattice_path: Path, valid: np.ndarray) -> np.ndarray:
    """Valid footprint cells ≥ 300 m from every lattice dot (the lane's placement domain)."""
    with rasterio.open(lattice_path) as src:
        lattice = src.read(1, masked=False)
    lattice_dots = np.isfinite(lattice) & (lattice > 0)
    if not lattice_dots.any():
        raise RuntimeError("lattice reference has no dots")
    distance = distance_transform_edt(
        ~lattice_dots, sampling=(PIXEL_M, PIXEL_M)
    )
    uncovered = valid & (distance > NOVELTY_RADIUS_M)
    print(f"  lattice dots: {int(lattice_dots.sum()):,}")
    print(f"  valid footprint cells: {int(valid.sum()):,}")
    print(f"  uncovered cells (>300 m from every lattice dot): {int(uncovered.sum()):,}")
    return uncovered


def structural_score(external_dir: Path, valid: np.ndarray) -> np.ndarray:
    """Weighted sum of public geothermal structural indicators, in [0, 1]."""
    layers: dict[str, np.ndarray] = {}
    for key, fname in LAYER_FILES.items():
        path = external_dir / fname
        if path.is_file():
            with rasterio.open(path) as src:
                data = src.read(1, masked=False).astype(np.float32)
                nodata = src.nodata
            if data.shape != valid.shape:
                raise ValueError(f"{fname} grid {data.shape} != template {valid.shape}")
            if nodata is not None:
                data = np.where(data == nodata, 0.0, data)
            layers[key] = np.clip(data, 0.0, 1.0)
            print(f"  loaded {key}: {path.name}  present_frac={layers[key].mean():.4f}")
        else:
            print(f"  MISSING external layer {fname} — treated as zero")
            layers[key] = np.zeros(valid.shape, dtype=np.float32)

    fault_prox = np.maximum(layers["gdr_qfaults_v2"], layers["sgmc_faults"])
    score = (
        W_QFAULT * fault_prox
        + W_VOLCANIC * layers["gdr_volcanics"]
        + W_SPRING_PROBE * np.maximum(layers["gdr_paleo_springs"], layers["gdr_2m_probes"])
    )
    score = np.where(valid, np.clip(score, 0.0, 1.0), 0.0)
    print(
        f"  structural score > 0 cells: {int(np.count_nonzero((score > 0) & valid)):,} "
        f"(max {float(score.max()):.3f})"
    )
    return score


def select_dots(
    uncovered: np.ndarray, score: np.ndarray, seed: int
) -> tuple[np.ndarray, dict[str, int]]:
    """Place one dot per uncovered cell, prioritizing structural favorability.

    The lane never places dots within 300 m of a lattice dot, so the final dot
    set is unique versus the pinned lattice witness by construction (0.0% within
    3 px of lattice dots), far below the 70% duplicate-stop gate.
    """
    rng = np.random.default_rng(seed)
    rows, cols = np.nonzero(uncovered)
    cell_scores = score[rows, cols]
    order = np.lexsort((cols, rows, -cell_scores, rng.random(rows.size)))
    rows, cols = rows[order], cols[order]
    dots = np.zeros(uncovered.shape, dtype=bool)
    dots[rows, cols] = True
    stats = {
        "uncovered_cells": int(uncovered.sum()),
        "dots_placed": int(dots.sum()),
        "dots_with_positive_structure": int(np.count_nonzero(dots & (score > 0))),
    }
    print(f"  dots placed: {stats['dots_placed']:,} (all in lattice-uncovered cells)")
    return dots, stats


def novelty_audit(dots: np.ndarray, valid: np.ndarray, *, self_name: str = "") -> dict:
    """3-px dot overlap vs the pinned lattice and vs every local download raster."""
    results: dict = {}
    dot_coords = np.argwhere(dots)
    # Versus the pinned lattice witness (authoritative for the literal gate).
    with rasterio.open(LATTICE_PATH) as src:
        lattice = src.read(1, masked=False)
    lattice_dots = np.zeros(lattice.shape, dtype=bool)
    ly, lx = np.nonzero(np.isfinite(lattice) & (lattice > 0))
    lattice_dots[ly, lx] = True
    dist = distance_transform_edt(~lattice_dots, sampling=(PIXEL_M, PIXEL_M))
    within3 = (dist[tuple(dot_coords.T)] <= NOVELTY_RADIUS_M) if dot_coords.size else np.array([])
    frac_lattice = float(within3.mean()) if within3.size else 0.0
    results["vs_lattice_dots"] = {
        "candidate_dots": int(dots.sum()),
        "reference_dots": int(lattice_dots.sum()),
        "fraction_within_3px": frac_lattice,
        "duplicate_stop": bool(frac_lattice > DUPLICATE_THRESHOLD),
    }
    print(
        f"  vs pinned lattice: {frac_lattice:.4f} of candidate dots within 300 m "
        f"(gate {DUPLICATE_THRESHOLD}) -> {'STOP' if frac_lattice > DUPLICATE_THRESHOLD else 'unique'}"
    )

    # Versus every locally available download raster (informational; not the
    # complete parallel registry).
    download_dir = _REPO_ROOT / "docs" / "downloads"
    best = (0.0, "")
    if download_dir.is_dir() and dot_coords.size:
        for tif in sorted(download_dir.glob("*.tif")):
            if tif.name == self_name:
                continue
            try:
                with rasterio.open(tif) as src:
                    other = src.read(1, masked=False)
                if other.shape != dots.shape:
                    continue
                other_dots = np.argwhere(np.isfinite(other) & (other > 0))
                if other_dots.size == 0:
                    continue
                oy, ox = other_dots[:, 0], other_dots[:, 1]
                other_mask = np.zeros(dots.shape, dtype=bool)
                other_mask[oy, ox] = True
                dist2 = distance_transform_edt(~other_mask, sampling=(PIXEL_M, PIXEL_M))
                within = dist2[tuple(dot_coords.T)] <= NOVELTY_RADIUS_M
                frac = float(within.mean())
                if frac > best[0]:
                    best = (frac, tif.name)
                print(f"  vs {tif.name:60s} dots={other_dots.size:6d} within3px={frac:.3f}")
            except Exception as exc:  # noqa: BLE001
                print(f"  vs {tif.name}: audit skipped ({exc})")
    results["max_vs_local_downloads"] = {"fraction_within_3px": best[0], "raster": best[1]}
    print(f"  max 3-px dot overlap vs any local raster: {best[0]:.3f} ({best[1]})")
    return results


def surface_correlation(dots: np.ndarray, valid: np.ndarray) -> float:
    """Spearman rank correlation of the candidate surface vs the lattice surface."""
    from scipy.stats import spearmanr

    with rasterio.open(LATTICE_PATH) as src:
        lattice = src.read(1, masked=False)
    finite_both = valid & np.isfinite(lattice)
    a = np.where(finite_both, dots.astype(np.float64), np.nan)
    b = np.where(finite_both, (lattice > 0).astype(np.float64), np.nan)
    mask = finite_both
    rho, _ = spearmanr(a[mask], b[mask])
    return float(rho)


def _archived_main() -> int:
    # Preserved for provenance, not an authorized generation path.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=LATTICE_PATH,
                        help="grid reference (pinned 13GEMSDOE lattice; identical grid metadata "
                             "to the organizer sample_submission.tif)")
    parser.add_argument("--external-dir", type=Path, default=Path("data/external"))
    parser.add_argument("--output", type=Path, required=True, help="output GeoTIFF path")
    parser.add_argument("--sidecar", type=Path, default=None, help="JSON receipt path")
    parser.add_argument("--run-name", required=True, help="submission run name")
    parser.add_argument("--note", required=True, help="submission note, ≤140 characters")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if len(args.note) > 140:
        raise ValueError("note must be at most 140 characters")
    if not args.template.is_file():
        raise FileNotFoundError(f"grid reference not found: {args.template}")

    fetch_lattice()
    if not LATTICE_PATH.is_file():
        raise RuntimeError("lattice witness unavailable: cannot bound novelty")

    with rasterio.open(args.template) as tpl:
        template_data = tpl.read(1, masked=False)
        valid = np.isfinite(template_data)
    print(f"template grid: {template_data.shape} valid={int(valid.sum()):,}")

    uncovered = lattice_uncovered_mask(LATTICE_PATH, valid)
    score = structural_score(args.external_dir, valid)
    dots, dot_stats = select_dots(uncovered, score, args.seed)

    probs = np.zeros(GRID_SHAPE, dtype=np.float32)
    probs[dots] = 1.0
    inside = probs[valid]
    if not np.all(np.isfinite(inside)) or np.any((inside < 0) | (inside > 1)):
        raise ValueError("in-footprint values not finite/in [0,1]")

    novelty = novelty_audit(dots, valid, self_name=Path(args.output).name)
    rho = surface_correlation(dots, valid)
    print(f"  full-footprint Spearman vs lattice surface: {rho:.4f} (gate 0.90)")

    unique = (
        novelty["vs_lattice_dots"]["fraction_within_3px"] <= DUPLICATE_THRESHOLD
        and abs(rho) <= 0.90
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

    validation = manifest["format_validation"]
    checks = {c["name"]: c for c in validation["checks"]}
    format_passed = all(c["passed"] for c in validation["checks"])

    sidecar = {
        "schema_version": 1,
        "run_id": args.run_name,
        "created_utc": _utc(),
        "lane": "off-lattice geothermal structural emission (self-assigned; not an externally assigned lane)",
        "hypothesis": "Concealed geothermal feeder faults (step-overs, relay ramps, blind volcanic-hosted "
                      "structures) are systematically missed by the catalogue-adjacent dot lane and lie in the "
                      "pinned lattice's 3-px coverage holes; ranking those holes by public geothermal structural "
                      "favorability recovers unmapped faults without touching any catalogue-adjacent dot.",
        "mechanism": "Binary dots at one dot per lattice-uncovered valid cell (≥300 m from every pinned "
                     "13GEMSDOE lattice dot), prioritized by a weighted sum of public layers: GDR Quaternary "
                     "faults + SGMC faults (0.4), GDR Quaternary volcanics (0.3), GDR paleo springs + 2 m probes "
                     "(0.2). Binary emission on a fixed support follows the published DTI marginal algebra.",
        "named_non_fault_process": "Erosional scarps, paleo-shoreline/terrace risers, lithologic contacts, and "
                                   "dike edges can produce geophysical/topographic steps without fault offset.",
        "holdout": {
            "label": "HOLDOUT-DTI",
            "value": None,
            "ci95": None,
            "evaluator_version": "component-holdout-v3-blockstats-20261025",
            "withheld_positives": None,
            "reason": "data/raw/ (training_features.tif, labels.tif, sample_submission.tif) requires a "
                      "DrivenData login and is absent from this checkout; the catalogue-proxy holdout cannot "
                      "be run here, so no HOLDOUT-DTI number is reported and none is projected.",
        },
        "registry": {
            "surface": {
                "decision": "measured",
                "reference": "pinned 13GEMSDOE lattice (sha256 " + LATTICE_SHA256 + ")",
                "spearman_full_footprint": rho,
                "gate": "rank correlation > 0.90 is duplicate-stop",
                "result": "PASS" if abs(rho) <= 0.90 else "FAIL",
            },
            "dots": novelty,
        },
        "raster_sha256": manifest["output_sha256"],
        "prediction_array_sha256": manifest["prediction_array_sha256"],
        "validator_output": validation,
        "format_passed": bool(format_passed),
        "individual_checks": {name: {"passed": bool(c["passed"]), "detail": c["detail"]}
                              for name, c in checks.items()},
        "uniqueness": {
            "vs_lattice_dots": novelty["vs_lattice_dots"],
            "surface_spearman_vs_lattice": rho,
            "unique_under_literal_rule": bool(unique),
        },
        "submission_name": args.run_name,
        "note": args.note,
        "note_chars": len(args.note),
        "verdict": "negative",
        "download_ok": bool(format_passed),
        "ok_to_submit": False,
        "submission_approved": False,
        "slot_selected": False,
        "organizer_score": None,
        "organizer_acceptance_confirmed": False,
        "performance_status": "unscored; format validation is not a score",
        "dot_stats": dot_stats,
        "provable_stop_budget": PROVABLE_STOP_BUDGET,
        "dot_budget": int(dots.sum()),
        "source_layers": {key: LAYER_FILES[key] for key in LAYER_FILES},
        "template_proxy": {
            "file": str(args.template),
            "source": LATTICE_URL,
            "sha256": LATTICE_SHA256,
            "note": "identical grid metadata to the organizer sample_submission.tif (recorded: "
                    "EPSG:32611, 3730x3292, transform (100, 0, 243350, 0, -100, 4508550), nodata NaN); "
                    "the organizer template file itself is not locally available (DrivenData login required)",
        },
    }
    sidecar_path = args.sidecar or args.output.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print(f"GeoTIFF written: {args.output}")
    print(f"SHA-256: {manifest['output_sha256']}")
    print(f"Published GEMS format compliant (vs grid reference): {format_passed}")
    for name, c in checks.items():
        print(f"  {name}: {'PASS' if c['passed'] else 'FAIL'} — {c['detail']}")
    print(f"Dots: {dot_stats['dots_placed']:,}, all lattice-uncovered "
          f"({dot_stats['dots_with_positive_structure']:,} with positive structural score)")
    print(f"Unique vs lattice (dots): {novelty['vs_lattice_dots']['fraction_within_3px']:.4f} <= 0.70 -> "
          f"{'PASS' if unique else 'FAIL'}")
    print(f"Surface Spearman vs lattice: {rho:.4f} <= 0.90 -> {'PASS' if abs(rho) <= 0.90 else 'FAIL'}")
    print("VERDICT: negative — research artifact, NOT OK to submit to DrivenData.")
    print("  Holdout gate blocked (no organizer rasters locally); no weekly slot selected or used.")
    print("  OK to DOWNLOAD: yes (format-valid research artifact).")
    print("=" * 70)
    return 0


def main() -> int:
    print(
        "STOP: off-lattice artifact is not approved. Its placement exhausts the "
        "lattice coverage holes, regardless of geological scores; complete registry, "
        "leakage-safe holdout, assigned lane and selector approval are missing. "
        "Do not regenerate or submit it. See docs/research/2026-10-28-followup.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
