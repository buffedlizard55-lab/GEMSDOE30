#!/usr/bin/env python3
"""Re-verify the FFL-1 artifact and decision from recorded receipts (no human inspection).

Exit 0 = every recorded receipt is consistent with the TIFF on disk.
Exit 2 = receipts consistent but the verdict is not promote (with --require-promote).
This follows the lane-specific verifier precedent of scripts/verify_lsm_run.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gemsdoe30.submission import validate_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-fflidar"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_expanded_dot_receipt(audit: dict, expected_sha256: str) -> dict:
    """Check that expanded-registry evidence is bound to the file and decision.

    A negative duplicate-stop is a valid verified outcome: this function checks
    that the recorded decision agrees with the measured maximum, rather than
    treating a duplicate as a verifier failure.
    """
    if audit.get("stage") != "dots":
        raise ValueError("expanded novelty receipt is not a dot-stage audit")
    if audit.get("candidate_sha256") != expected_sha256:
        raise ValueError("expanded dot novelty receipt is not bound to the published TIFF")
    if audit.get("errors"):
        raise ValueError("expanded dot novelty receipt records errors")
    rows = audit.get("comparisons")
    if not isinstance(rows, list) or not rows:
        raise ValueError("expanded dot novelty receipt has no comparisons")
    correlations = []
    overlaps = []
    for row in rows:
        rho = row.get("spearman_full_footprint")
        overlap = row.get("candidate_fraction_within_3px_of_reference")
        if (not isinstance(rho, Real) or isinstance(rho, bool)
                or not math.isfinite(float(rho))):
            raise ValueError("expanded dot novelty receipt has undefined/non-finite correlation")
        if (not isinstance(overlap, Real) or isinstance(overlap, bool)
                or not math.isfinite(float(overlap)) or not 0.0 <= float(overlap) <= 1.0):
            raise ValueError("expanded dot novelty receipt has undefined/invalid dot overlap")
        correlations.append(float(rho))
        overlaps.append(float(overlap))
    max_rho = max(correlations)
    max_overlap = max(overlaps)
    duplicate = max_rho > 0.90 or max_overlap > 0.70
    expected_decision = "duplicate-stop" if duplicate else None
    if duplicate and audit.get("decision") != expected_decision:
        raise ValueError("expanded dot novelty decision contradicts measured duplicate threshold")
    if not duplicate and audit.get("decision") == "duplicate-stop":
        raise ValueError("expanded dot novelty reports duplicate-stop without a threshold breach")
    return {"comparisons": len(rows), "max_spearman": max_rho,
            "max_fraction_within_3px": max_overlap, "duplicate": duplicate}


def verify() -> dict:
    card = json.loads((REPORT / "run-card.json").read_text())
    readiness = json.loads((REPORT / "readiness.json").read_text())
    results = json.loads((REPORT / "results.json").read_text())
    confirmation = json.loads((REPORT / "results-confirmation.json").read_text())
    raster = ROOT / card["published_tiff"]
    template = ROOT / "data/raw/sample_submission.tif"
    if sha(raster) != card["raster_sha256"]:
        raise ValueError("TIFF SHA-256 does not match run card")
    sidecar = json.loads(raster.with_suffix(".json").read_text())
    if sidecar.get("output_sha256") != card["raster_sha256"]:
        raise ValueError("download sidecar SHA-256 does not match run card")
    if not validate_submission_file(raster, template, require_finite_all_cells=True).passed:
        raise ValueError("TIFF fails strict all-finite [0,1] validator")
    for stage in ("surface", "dots"):
        audit = json.loads((REPORT / f"novelty-{stage}.json").read_text())
        if audit["decision"] == "duplicate-stop" or audit.get("errors"):
            raise ValueError(f"{stage} novelty audit is a duplicate-stop / has errors")
        rows = audit["comparisons"]
        if max(r["spearman_full_footprint"] for r in rows) > 0.90:
            raise ValueError(f"{stage} surface correlation exceeds 0.90")
        if stage == "dots" and not (REPORT / "results-stratified.json").is_file():
            if audit["candidate_sha256"] != card["raster_sha256"]:
                raise ValueError("dot novelty receipt is not bound to the published TIFF")
            if max(r["candidate_fraction_within_3px_of_reference"] for r in rows) > 0.70:
                raise ValueError("dot overlap exceeds 70%")
    if results["canary_alarms"]:
        raise ValueError("leakage canary alarms recorded")
    expanded_dots_path = REPORT / "novelty-dots-expanded.json"
    expanded_dots = json.loads(expanded_dots_path.read_text())
    expanded_stats = validate_expanded_dot_receipt(expanded_dots, card["raster_sha256"])
    if expanded_stats["duplicate"]:
        failed_duplicate_gates = [
            gate for gate in readiness.get("gates", [])
            if gate.get("name") == "duplicate_stop_fusion_edge_emission"
            and gate.get("status") == "failed"
        ]
        if not failed_duplicate_gates or card["verdict"] != "negative":
            raise ValueError("expanded duplicate-stop is not reflected in readiness and run-card verdict")
    stratified_path = REPORT / "results-stratified.json"
    if stratified_path.is_file():
        stratified = json.loads(stratified_path.read_text())
        prod = stratified.get("production")
        expected_promote = bool(
            stratified["gate"]["passed"] and prod
            and prod["dots_audit_max_spearman"] <= 0.90
            and prod["dots_audit_max_fraction_within_3px"] <= 0.70
            and prod["surface_audit_max_spearman"] <= 0.90
            and card["candidate_arm"] == "fusion_ffstrat")
        if (card["verdict"] == "promote") != expected_promote:
            raise ValueError("card verdict contradicts recorded gate outcomes")
        if expected_promote:
            audit = json.loads((REPORT / "novelty-dots-expanded.json").read_text())
            if audit["candidate_sha256"] != card["raster_sha256"]:
                raise ValueError("expanded dot novelty receipt is not bound to the published TIFF")
            rows = audit["comparisons"]
            if max(r["candidate_fraction_within_3px_of_reference"] for r in rows) > 0.70:
                raise ValueError("expanded dot overlap exceeds 70%")
    else:
        e1 = results["summary_experiment_1"]["candidate_minus"]["msdb_edge"]
        expected_promote = bool(e1["value"] > 0 and confirmation["gate"]["passed"])
        if (card["verdict"] == "promote") != expected_promote:
            raise ValueError("card verdict contradicts recorded gate outcomes")
    if card["note"] != sidecar.get("note") or len(card["note"]) > 140:
        raise ValueError("submission note mismatch / too long")
    if card["submission_approved"] is not False or card["slot_selected"] is not False:
        raise ValueError("card must not select or spend a competition slot")
    if readiness["research_verdict"] != card["verdict"] or readiness["raster_sha256"] != card["raster_sha256"]:
        raise ValueError("readiness receipt contradicts run card")
    with rasterio.open(raster) as ds:
        arr = ds.read(1)
    if not np.isfinite(arr).all() or arr.min() < 0.0 or arr.max() > 1.0:
        raise ValueError("whole-array [0,1] finite contract violated")
    return readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    try:
        readiness = verify()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"Verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(readiness, indent=2))
    if args.require_promote and readiness["research_verdict"] != "promote":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
