#!/usr/bin/env python3
"""Forensically audit the already-tracked 2026-10-29 research TIFF.

This is a read-only raster audit apart from writing/checking its JSON receipt.
It never fits a model, places dots, changes a TIFF, uses organizer credentials,
selects a slot, or certifies a complete registry. The frozen nine-site files and
one pinned 13GEMSDOE raster are read only after their SHA-256 pins are checked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from gemsdoe30.novelty import compare, decision
from gemsdoe30.submission import valid_template_mask, validate_submission_file
from scripts.verify_registry_preflight import same_measurement

SITES = tuple(f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36))
CANDIDATE = ROOT / "docs/downloads/GEMSDOE30-concealed-geothermal-unique-20261029.tif"
CANDIDATE_SHA256 = "b319577b30e9d1d238abc00ee8fad5a389794962c6bc60db11c24a363fdcff73"
SIDECAR = CANDIDATE.with_suffix(".json")
SIDECAR_SHA256 = "586567af41964a296e65d4342ef07b28545169409c05d398abfdb6dcfb8b6d4d"
FLEET = ROOT / "docs/research/2026-10-26-csr/fleet-audit.json"
CORE_PINS = ROOT / "docs/research/mirror-pins.json"
LATTICE_PINS = ROOT / "docs/research/2026-10-27-registry-preflight/lattice-pin.json"
OUTPUT = ROOT / "docs/research/2026-10-29-candidate-audit.json"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LATTICE = ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif"
CACHE = ROOT / "data/raw/priority-readiness"


def sha256(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pin_by_id(path: Path, pin_id: str) -> dict:
    rows = load_json(path).get("files", [])
    found = [row for row in rows if row.get("id") == pin_id]
    if len(found) != 1:
        raise ValueError(f"expected exactly one {pin_id!r} pin in {path}")
    return found[0]


def _grid(path: Path, expected: tuple) -> np.ndarray:
    with rasterio.open(path) as ds:
        if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != expected:
            raise ValueError(f"single-band grid mismatch: {path}")
        return ds.read(1, masked=False)


def _comparison(candidate: np.ndarray, reference: np.ndarray, mask: np.ndarray) -> dict:
    row = compare(candidate, reference, mask, stage="dots")
    n = row["candidate_dots"]
    fraction = row["candidate_fraction_within_3px_of_reference"]
    row["matching_candidate_dots"] = int(round(n * fraction))
    row["thresholds"] = {
        "absolute_spearman_greater_than": 0.90,
        "fraction_within_3px_greater_than": 0.70,
        "measurement_scope": "final saved raster only; not the missing pre-placement surface",
    }
    return row


def audit(
    *, candidate: Path = CANDIDATE, template: Path = TEMPLATE,
    lattice: Path = LATTICE, cache: Path = CACHE,
) -> dict:
    """Recompute the format and final-dot evidence from exact local bytes."""
    def resolve_inside_root(path: Path) -> Path:
        path = Path(path)
        resolved = (path if path.is_absolute() else ROOT / path).resolve()
        if not resolved.is_relative_to(ROOT):
            raise ValueError(f"audit input escapes repository root: {path}")
        return resolved

    candidate = resolve_inside_root(candidate)
    template = resolve_inside_root(template)
    lattice = resolve_inside_root(lattice)
    cache = resolve_inside_root(cache)
    if not all(path.is_file() for path in (candidate, template, lattice, SIDECAR, FLEET, CORE_PINS, LATTICE_PINS)):
        missing = [str(p) for p in (candidate, template, lattice, SIDECAR, FLEET, CORE_PINS, LATTICE_PINS) if not p.is_file()]
        raise FileNotFoundError("missing required pinned audit input(s): " + ", ".join(missing))

    sidecar = load_json(SIDECAR)
    sidecar_sha = sha256(SIDECAR)
    if sidecar_sha != SIDECAR_SHA256:
        raise ValueError("original candidate sidecar no longer matches its frozen SHA-256")
    candidate_sha = sha256(candidate)
    if candidate_sha != CANDIDATE_SHA256:
        raise ValueError("candidate raster no longer matches the tracked 2026-10-29 audit target SHA-256")
    if sidecar.get("output_sha256") != candidate_sha:
        raise ValueError("candidate SHA-256 differs from its original sidecar")
    if sidecar.get("output_file") != candidate.name:
        raise ValueError("candidate basename differs from its original sidecar")

    template_pin = _pin_by_id(CORE_PINS, "sample_submission")
    lattice_pin = _pin_by_id(LATTICE_PINS, "registry_lattice")
    if sha256(template) != template_pin["sha256"]:
        raise ValueError("sample template does not match its frozen owner-mirror SHA-256 pin")
    if sha256(lattice) != lattice_pin["sha256"]:
        raise ValueError("registry witness does not match its frozen SHA-256 pin")

    with rasterio.open(template) as ds:
        if ds.count != 1:
            raise ValueError("template must be single-band")
        mask = valid_template_mask(ds, np)
        expected_grid = (ds.shape, ds.crs, ds.transform)
        grid_summary = {
            "shape": [int(ds.height), int(ds.width)],
            "crs": ds.crs.to_string() if ds.crs else None,
            "transform_gdal": [float(x) for x in ds.transform.to_gdal()],
            "resolution_m": [float(ds.transform.a), float(-ds.transform.e)],
            "valid_pixels": int(mask.sum()),
        }

    candidate_array = _grid(candidate, expected_grid)
    inside = candidate_array[mask]
    if not np.isfinite(inside).all() or np.any((inside < 0) | (inside > 1)):
        raise ValueError("candidate contains NaN/Inf or values outside [0,1] inside the footprint")
    candidate_dots = int(np.count_nonzero(mask & (candidate_array > 0)))
    whole_raster_finite_range_passed = bool(
        np.isfinite(candidate_array).all()
        and np.all((candidate_array >= 0) & (candidate_array <= 1))
    )
    outside_nan_pixels = int(np.count_nonzero(~np.isfinite(candidate_array[~mask])))

    validation = validate_submission_file(candidate, template).to_dict()
    validation.pop("path", None)
    if validation["passed"] is not True:
        raise ValueError("tracked candidate no longer passes the shared published-format validator")

    fleet = load_json(FLEET)
    rows = fleet.get("rows", [])
    if tuple(row.get("site") for row in rows) != SITES:
        raise ValueError("frozen historical fleet does not contain exactly the nine requested sites in order")

    site_comparisons = []
    for row in rows:
        reference_path = cache / f"{row['site']}-{row['raster_sha256']}.tif"
        if not reference_path.is_file():
            raise FileNotFoundError(
                f"missing historical source for {row['site']}: restore with "
                "python scripts/audit_priority_readiness.py --restore-only"
            )
        reference_sha = sha256(reference_path)
        if reference_sha != row["raster_sha256"]:
            raise ValueError(f"historical source SHA-256 mismatch for {row['site']}")
        reference = _grid(reference_path, expected_grid)
        comparison = _comparison(candidate_array, reference, mask)
        site_comparisons.append({
            "site": row["site"],
            "historical_file": row["historical_file"],
            "historical_sha256": reference_sha,
            "reported_historical_value": row["quoted_owner_claim"],
            "reported_value_evidence": "UNVERIFIED OWNER CLAIM; not HOLDOUT-DTI or ORGANIZER-CONFIRMED",
            **comparison,
        })

    lattice_array = _grid(lattice, expected_grid)
    lattice_comparison = _comparison(candidate_array, lattice_array, mask)
    site_decision = decision(site_comparisons, stage="dots", registry_complete=False)
    lattice_decision = decision([lattice_comparison], stage="dots", registry_complete=True)
    max_site = max(site_comparisons, key=lambda row: row["candidate_fraction_within_3px_of_reference"])
    duplicate = site_decision == "duplicate-stop" or lattice_decision == "duplicate-stop"
    verdict = "negative" if duplicate else "blocked-incomplete-evidence"

    note = sidecar.get("note") or ""
    if len(note) > 140:
        raise ValueError("stored note is longer than the portal's 140-character example limit")
    matched = lattice_comparison["matching_candidate_dots"]
    overlap_fraction = lattice_comparison["candidate_fraction_within_3px_of_reference"]

    return {
        "schema_version": 1,
        "run_id": "GEMSDOE30-candidate-byte-audit-20261029",
        "audit_scope": "Forensic audit of an already-tracked research TIFF; no new experiment or prediction generated.",
        "hypothesis": "No new hypothesis executed. The tracked geothermal candidate has no assigned lane and its final dots must stop if they duplicate a pinned registry raster.",
        "mechanism": "Reopen the exact saved TIFF, validate its bytes against the pinned owner-mirror template, and measure final-dot overlap against the nine frozen priority-site leaders plus one duplicate-stop witness.",
        "named_non_fault_process": "Erosional scarps, paleo-shoreline or terrace risers, lithologic contacts, and volcanic flow fronts can mimic structural/geothermal signatures; not tested in this byte audit.",
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "value": None,
            "ci95": None,
            "evaluator_version": None,
            "withheld_positives": None,
            "reason": "Not run: no authorized new lane; the complete training feature raster/cache is absent, and a duplicate-stop makes promotion ineligible.",
        },
        "organizer_confirmed_score": {
            "label": "ORGANIZER-CONFIRMED",
            "value": None,
            "receipt": None,
            "reason": "No submission-page receipt is present in this repository.",
        },
        "score_estimate": None,
        "score_estimate_reason": "No defensible leaderboard estimate: the historical values are unverified owner claims and do not calibrate this unvalidated artifact.",
        "candidate": {
            "path": str(candidate.relative_to(ROOT)),
            "sha256": candidate_sha,
            "sidecar_path": str(SIDECAR.relative_to(ROOT)),
            "original_sidecar_sha256": sha256(SIDECAR),
            "original_sidecar_note": note,
            "original_sidecar_note_chars": len(note),
            "original_note_uniqueness_claim_is_supported": False,
            "submission_name": sidecar.get("run_name"),
            "submission_note": note,
        },
        "registry": {
            "surface_stage": {
                "decision": "blocked-unavailable",
                "preplacement_surface_path": None,
                "preplacement_surface_sha256": None,
                "correlation_vs_registry": None,
                "reason": "No separately saved continuous pre-placement surface or surface-stage receipt exists; final binary-raster correlation is not substituted.",
            },
            "final_dot_stage": {
                "decision_vs_nine_priority_files": site_decision,
                "priority_site_comparisons_complete_for_requested_nine": len(site_comparisons) == len(SITES),
                "requested_nine_registry_complete": False,
                "max_overlap_vs_requested_nine": {
                    "site": max_site["site"],
                    "fraction": max_site["candidate_fraction_within_3px_of_reference"],
                    "matching_dots": max_site["matching_candidate_dots"],
                    "candidate_dots": candidate_dots,
                    "interpretation": "final-dot audit metric, not a score",
                },
                "pinned_lattice": {
                    "sha256": lattice_pin["sha256"],
                    "source_url": load_json(LATTICE_PINS)["source"],
                    "provenance": lattice_pin["provenance"],
                    "decision": lattice_decision,
                    "spearman_on_final_binary_raster": lattice_comparison["spearman_full_footprint"],
                    "fraction_within_3px": overlap_fraction,
                    "matching_candidate_dots": matched,
                    "candidate_dots": candidate_dots,
                    "threshold_fraction_strictly_greater_than": 0.70,
                    "threshold_spearman_strictly_greater_than": 0.90,
                    "interpretation": "final-dot audit metric, not a score; dot overlap alone triggers duplicate-stop",
                },
                "all_reference_comparisons": site_comparisons,
                "complete_parallel_registry_checked": False,
            },
            "overall_decision": "duplicate-stop" if duplicate else "blocked-incomplete-evidence",
            "overall_unique_submission": False,
            "reason": "The candidate exceeds the strict 70% final-dot overlap threshold against the pinned 13GEMSDOE lattice, even though it is below that threshold against each of the nine frozen priority-site files.",
        },
        "raster_sha256": candidate_sha,
        "validator_output": {
            "passed": validation["passed"],
            "single_band_float32": True,
            "no_nan_inside_footprint": bool(np.isfinite(inside).all()),
            "values_in_0_1_inside_footprint": bool(np.all((inside >= 0) & (inside <= 1))),
            "crs_shape_transform_match": True,
            "grid": grid_summary,
            "outside_nan_pixels": outside_nan_pixels,
            "whole_raster_finite_range_diagnostic_passed": whole_raster_finite_range_passed,
            "whole_raster_diagnostic_note": "Outside-footprint NaNs are required by the published null-outside convention; this advisory is not an organizer-validator diagnosis.",
            "checks": validation["checks"],
        },
        "experiments_run_this_review": 0,
        "experiment_cap": 3,
        "time_cap_seconds": 7200,
        "submission_name": sidecar.get("run_name"),
        "submission_note": note,
        "submission_note_characters": len(note),
        "download_control": False,
        "ok_to_download_for_submission": False,
        "ok_to_submit": False,
        "slot_selected": False,
        "verdict": verdict,
        "decision": "DUPLICATE-STOP: do not download or submit; the pre-placement surface is unavailable and no HOLDOUT-DTI or organizer score receipt exists.",
        "irregularities": [
            {
                "id": "IR-CAND-001",
                "finding": "The original sidecar note describes off-lattice uniqueness, but the exact raster has more than 99% of its dots within 3 px of the pinned lattice.",
                "evidence": "The hash-bound final-dot comparison in registry.final_dot_stage.pinned_lattice.",
                "status": "verified inconsistency; preserve original sidecar and do not reuse its claim.",
            },
            {
                "id": "IR-CAND-002",
                "finding": "No saved independent pre-placement surface, leakage-safe holdout receipt, or organizer submission receipt is bound to this TIFF.",
                "evidence": "No files in the tracked candidate's provenance bundle provide these receipts.",
                "status": "unavailable; not inferred from absence of a score.",
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="recompute offline and compare against the saved receipt")
    parser.add_argument("--require-promote", action="store_true", help="exit 2 unless the result is a promotion")
    args = parser.parse_args()
    result = audit()
    if args.check:
        saved = load_json(OUTPUT)
        if not same_measurement(saved, result):
            raise SystemExit("stale or inconsistent candidate audit receipt")
    else:
        OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"VERIFIED {result['verdict'].upper()}: format-valid candidate duplicate-stopped vs pinned witness; no submission approval")
    return 2 if args.require_promote and result["verdict"] != "promote" else 0


if __name__ == "__main__":
    raise SystemExit(main())
