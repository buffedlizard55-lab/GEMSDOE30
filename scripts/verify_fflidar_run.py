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


def verify_expanded_dot_audit(audit: dict, expected_sha256: str) -> float:
    """Require the expanded dot receipt to be bound to the TIFF and prove a stop.

    A passing/blocked partial audit is not enough for this artifact: its final
    negative decision depends on the recorded >70% overlap against an observed
    prior raster. This validates that evidence without claiming registry
    completeness.
    """
    if audit.get("stage") != "dots":
        raise ValueError("expanded novelty receipt is not a dot-stage audit")
    if audit.get("candidate_sha256") != expected_sha256:
        raise ValueError("expanded dot novelty receipt is not bound to the published TIFF")
    if audit.get("errors"):
        raise ValueError("expanded dot novelty audit contains comparison errors")
    rows = audit.get("comparisons")
    if not isinstance(rows, list) or not rows:
        raise ValueError("expanded dot novelty audit has no comparisons")
    overlaps = []
    max_rho = 0.0
    for row in rows:
        try:
            rho = float(row["spearman_full_footprint"])
            overlap = float(row["candidate_fraction_within_3px_of_reference"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("expanded dot novelty row is incomplete") from exc
        if not np.isfinite(rho) or not np.isfinite(overlap) or not 0.0 <= overlap <= 1.0:
            raise ValueError("expanded dot novelty row has invalid statistics")
        max_rho = max(max_rho, rho)
        overlaps.append(overlap)
    max_overlap = max(overlaps)
    duplicate = max_rho > 0.90 or max_overlap > 0.70
    if not duplicate or audit.get("decision") != "duplicate-stop":
        raise ValueError("expanded dot novelty receipt does not support the duplicate-stop")
    if audit.get("submission_approved") is not False:
        raise ValueError("expanded dot novelty receipt must not approve submission")
    return max_overlap


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
        if not rows or max(r["spearman_full_footprint"] for r in rows) > 0.90:
            raise ValueError(f"{stage} novelty audit is empty or exceeds correlation threshold")
    expanded_dots = json.loads((REPORT / "novelty-dots-expanded.json").read_text())
    max_expanded_overlap = verify_expanded_dot_audit(expanded_dots, card["raster_sha256"])
    if card["verdict"] != "negative" or card["submission_approved"] is not False:
        raise ValueError("duplicate-stopped expanded dots must remain a negative, unapproved artifact")
    # The purported expanded 'surface' receipt is actually bound to the final
    # binary submission TIFF, not the pre-placement continuous score raster.
    # Do not present it as evidence of pre-placement surface novelty.
    expanded_surface = json.loads((REPORT / "novelty-surface-expanded.json").read_text())
    if expanded_surface.get("stage") != "surface":
        raise ValueError("expanded surface receipt has an invalid stage")
    preplacement_surface_valid = (
        expanded_surface.get("candidate_sha256") != card["raster_sha256"]
        and not expanded_surface.get("errors")
        and bool(expanded_surface.get("comparisons"))
        and max(r["spearman_full_footprint"] for r in expanded_surface["comparisons"]) <= 0.90
    )
    if readiness.get("surface_audit", {}).get("preplacement_surface_valid") != preplacement_surface_valid:
        raise ValueError("readiness does not reflect the expanded pre-placement surface audit status")
    if readiness.get("surface_audit", {}).get("preplacement_surface_valid") is not False:
        raise ValueError("mis-bound expanded surface receipt must not count as pre-placement evidence")
    if max_expanded_overlap <= 0.70:
        raise ValueError("expanded dot audit no longer supports duplicate-stop")
    if results["canary_alarms"]:
        raise ValueError("leakage canary alarms recorded")
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
