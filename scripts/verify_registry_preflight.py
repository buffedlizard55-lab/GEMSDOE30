#!/usr/bin/env python3
"""Recompute the one-witness duplicate proof and verify the negative run card.

This is NOT a model experiment, a registry-wide pass, or an upload selector.
The candidate is the *previously published* CSR-1 file. The proposed continuation
is stopped without fitting or placement. All source rasters are hash-pinned; the
reference and template can be restored from GitHub without competition credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from gemsdoe30.novelty import compare, dot_budget_bound  # noqa: E402
from gemsdoe30.submission import valid_template_mask, validate_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-27-registry-preflight"
CARD = REPORT / "run-card.json"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LATTICE = ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif"
HISTORIC_CARD = ROOT / "docs/research/2026-10-26-csr/run-card.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def independent_three_pixel_coverage(reference, footprint) -> int:
    """Count coverage by explicit 29-offset disk dilation, independent of EDT.

    Source and target slices are clipped, not rolled, so opposite edges never
    wrap. Outside-footprint reference values are excluded as possible sources.
    """
    mask = np.asarray(footprint, dtype=bool)
    dots = mask & (np.asarray(reference) > 0)
    covered = np.zeros(mask.shape, dtype=bool)
    h, w = mask.shape
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            if dr * dr + dc * dc > 9 or abs(dr) >= h or abs(dc) >= w:
                continue
            src_r = slice(max(0, -dr), min(h, h - dr))
            src_c = slice(max(0, -dc), min(w, w - dc))
            dst_r = slice(max(0, dr), min(h, h + dr))
            dst_c = slice(max(0, dc), min(w, w + dc))
            covered[dst_r, dst_c] |= dots[src_r, src_c]
    return int(np.count_nonzero(mask & covered))


def inspect(template: Path = TEMPLATE, lattice: Path = LATTICE) -> dict:
    """Inspect actual bytes; return bounded evidence rather than a recommendation."""
    template, lattice = Path(template), Path(lattice)
    pins = load(ROOT / "docs/research/mirror-pins.json")
    template_pin = next(r for r in pins["files"] if r["id"] == "sample_submission")
    ref_pin = load(REPORT / "lattice-pin.json")["files"][0]
    historical = load(HISTORIC_CARD)
    candidate = ROOT / historical["published_tiff"]
    require(sha(template) == template_pin["sha256"], "template SHA-256 mismatch")
    require(sha(lattice) == ref_pin["sha256"] and lattice.stat().st_size == ref_pin["bytes"],
            "lattice SHA-256 or size mismatch")
    require(sha(candidate) == historical["raster_sha256"], "historic CSR-1 SHA-256 mismatch")
    with rasterio.open(template) as tpl, rasterio.open(lattice) as ref, rasterio.open(candidate) as old:
        require(tpl.count == ref.count == old.count == 1, "expected single-band GeoTIFFs")
        grid = (tpl.shape, tpl.crs, tpl.transform)
        require((ref.shape, ref.crs, ref.transform) == grid, "lattice/template grid mismatch")
        require((old.shape, old.crs, old.transform) == grid, "historic candidate/template grid mismatch")
        footprint = valid_template_mask(tpl, np)
        reference = ref.read(1)
        prediction = old.read(1)
        values = prediction[footprint]
        require(np.isfinite(values).all() and np.all((values == 0) | (values == 1)),
                "historic CSR-1 is not a finite binary-dot raster")
        budget = int(np.count_nonzero(values))
        # Check the count claimed in the archived receipt before applying its budget.
        require(budget == historical["validator_output"]["emitted_dots"], "historical dot count mismatch")
        proof = dot_budget_bound(reference, footprint, budget)
        independent_covered = independent_three_pixel_coverage(reference, footprint)
        require(independent_covered == proof["covered_within_radius_pixels"],
                "independent integer-disk coverage disagrees with distance transform")
        comparison = compare(prediction, reference, footprint, stage="dots")
        # Match count is an integer; the exact compare fraction is retained too.
        matching = int(round(comparison["candidate_fraction_within_3px_of_reference"] * budget))
        require(proof["decision"] == "duplicate-stop" and comparison["dot_duplicate"] is True,
                "expected strict duplicate witness not reproduced")
        require(matching >= proof["minimum_overlapping_dots"], "observed overlap violates bound")
        grid_record = {"shape_hw": list(tpl.shape), "crs": str(tpl.crs),
                       "transform": list(tpl.transform)[:6]}
    published = validate_submission_file(candidate, template)
    diagnostic = validate_submission_file(candidate, template, require_finite_all_cells=True)
    return {
        "template_sha256": sha(template),
        "reference_sha256": sha(lattice),
        "reference_source": load(REPORT / "lattice-pin.json")["source"],
        "grid": grid_record,
        "bound": proof,
        "independent_coverage": {"method": "explicit clipped 29-offset Euclidean integer disk, no wrap",
                                 "covered_within_radius_pixels": independent_covered},
        "previous_candidate": {
            "path": historical["published_tiff"], "raster_sha256": sha(candidate),
            "matching_dots": matching, "comparison": comparison,
            "outside_convention": "zero outside the template footprint",
            "published_format_validator_passed": published.passed,
            "whole_array_finite_range_diagnostic_passed": diagnostic.passed,
            "published_failed_checks": [x.name for x in published.checks if not x.passed],
            "organizer_acceptance_confirmed": False,
        },
    }


def make_card(measured: dict) -> dict:
    old = load(HISTORIC_CARD)
    results = load(ROOT / "docs/research/2026-10-26-csr/results.json")
    return {
        "schema_version": 1,
        "run_id": "gems30-registry-preflight-20261027",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": "Prior-session CSR-2 proposal: preserve piedmont-scarp evidence while gating the cover-blind potential-field expert to transtensional regions.",
        "mechanism": "Regime-weighted combination of terrain/MSDB and cover-blind potential-field/Radon evidence; proposal only, never fitted here.",
        "named_non_fault_process": "Erosional fan or paleoshoreline scarps and non-fault lithologic boundaries can mimic the targeted edges.",
        "lane_assignment": "unknown: this prompt supplies no single assigned method paragraph; CSR-2 is a prior-session proposal only",
        "new_holdout": {"label": "HOLDOUT-DTI", "value": None, "ci95": None,
                        "evaluator_version": None, "withheld_positives": None,
                        "reason": "No new model or holdout experiment after the preflight stop."},
        "historical_holdout_reference": {
            "source": "docs/research/2026-10-26-csr/results.json",
            "label": "HOLDOUT-DTI", "evaluator_version": results["summary"]["evaluator_version"],
            "protocol_version": results["summary"]["protocol_version"],
            "candidate": results["summary"]["arms"]["csr_dispersed"],
            "matched_control": results["summary"]["arms"]["msdb_edge"],
            "paired_difference": results["summary"]["candidate_minus"]["msdb_edge"],
            "scope": "Archived catalogue proxy, not a hidden-test score or a CSR-2 result.",
        },
        "registry": {
            "pre_placement_surface": None,
            "new_final_dots": None,
            "scope": "One valid registered 13GEMSDOE witness is sufficient to prove STOP; this is not a complete inventory.",
            "measurement": measured,
        },
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "note": None,
        "experiments_run": 0,
        "experiment_cap": 3,
        "time_cap_seconds": 7200,
        "verdict": "negative",
        "decision": "DUPLICATE-STOP: no new raster produced, no weekly slot selected or used",
        "download_ok": False,
        "ok_to_submit": False,
        "submission_approved": False,
        "slot_selected": False,
        "organizer_score": None,
        "historical_organizer_score_receipt": None,
        "historical_raster_sha256": old["raster_sha256"],
    }


def same_measurement(saved, actual) -> bool:
    """Match integer evidence exactly; tolerate only roundoff in float statistics."""
    if isinstance(actual, dict):
        return isinstance(saved, dict) and saved.keys() == actual.keys() and all(
            same_measurement(saved[k], actual[k]) for k in actual)
    if isinstance(actual, list):
        return isinstance(saved, list) and len(saved) == len(actual) and all(
            same_measurement(a, b) for a, b in zip(saved, actual))
    if isinstance(actual, float):
        return (isinstance(saved, (int, float)) and not isinstance(saved, bool)
                and math.isfinite(saved) and math.isclose(saved, actual, rel_tol=1e-12, abs_tol=1e-12))
    return type(saved) is type(actual) and saved == actual


def verify(template: Path = TEMPLATE, lattice: Path = LATTICE) -> dict:
    card = load(CARD)
    measured = inspect(template, lattice)
    require(same_measurement(card["registry"]["measurement"], measured), "saved preflight measurement does not match source bytes")
    require(card.get("verdict") == "negative" and card.get("experiments_run") == 0,
            "preflight must remain a zero-experiment negative")
    require(all(card.get(k) is False for k in ("download_ok", "ok_to_submit", "submission_approved", "slot_selected")),
            "preflight cannot approve a new file or slot")
    require(all(card.get(k) is None for k in ("raster_sha256", "validator_output", "submission_name", "note", "organizer_score")),
            "preflight cannot claim a new file or organizer score")
    h = card["new_holdout"]
    require(h["label"] == "HOLDOUT-DTI" and all(h.get(k) is None for k in
            ("value", "ci95", "evaluator_version", "withheld_positives")), "new holdout was not run")
    results = load(ROOT / "docs/research/2026-10-26-csr/results.json")["summary"]
    historic = card["historical_holdout_reference"]
    require(historic["candidate"] == results["arms"]["csr_dispersed"]
            and historic["matched_control"] == results["arms"]["msdb_edge"]
            and historic["paired_difference"] == results["candidate_minus"]["msdb_edge"]
            and historic["evaluator_version"] == results["evaluator_version"]
            and historic["protocol_version"] == results["protocol_version"],
            "historical holdout must match the archived receipt")
    require(card["historical_raster_sha256"] == measured["previous_candidate"]["raster_sha256"],
            "historical candidate identity mismatch")
    return {"research_verdict": "negative", "display_status": card["decision"],
            "download_ok": False, "ok_to_submit": False, "submission_approved": False,
            "slot_selected": False, "measurement": measured}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--lattice", type=Path, default=LATTICE)
    parser.add_argument("--create", action="store_true", help="write the new run card once; never overwrite")
    parser.add_argument("--require-promote", action="store_true", help="exit 2 unless the run was promoted")
    args = parser.parse_args()
    if args.create:
        if CARD.exists():
            raise SystemExit("run card already exists; refusing to rewrite evidence")
        CARD.parent.mkdir(parents=True, exist_ok=True)
        CARD.write_text(json.dumps(make_card(inspect(args.template, args.lattice)), indent=2, allow_nan=False) + "\n")
    result = verify(args.template, args.lattice)
    b = result["measurement"]["bound"]
    o = result["measurement"]["previous_candidate"]
    print(f"VERIFIED NEGATIVE: {b['minimum_overlapping_dots']}/{b['candidate_dot_budget']} minimum; "
          f"historic CSR-1 {o['matching_dots']}/{b['candidate_dot_budget']} within 3 px; no submission")
    return 2 if args.require_promote else 0


if __name__ == "__main__":
    raise SystemExit(main())
