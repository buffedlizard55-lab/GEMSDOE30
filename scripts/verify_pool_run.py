#!/usr/bin/env python3
"""Independently verify the POOL-1 negative (duplicate-stop) decision from receipts.

Exit 0 verifies the recorded outcome: science gates passed on two seeds, but the
final-dot novelty gate breached 70% vs three GEMSDOE30 rasters, so NO GeoTIFF was
published to docs/downloads/ and verdict = negative. ``--require-promote`` exits 2.
Works from committed receipts plus data/raw/{sample_submission,labels}.tif; the
quarantined runs/pool1 raster is re-inspected only if present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

REPORT = ROOT / "docs/research/2026-10-27-pool"
BREACHING = {
    "docs/research/2026-10-26-fflidar/gems30-FFL1-fusion_edge-44090-20261026-eacd73e854a3.tif",
    "docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif",
    "docs/downloads/gems30-CSR1-44090-20261026-502fb5948335-zeros.tif",
}


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def sha(p: Path) -> str:
    with p.open("rb") as s:
        return hashlib.file_digest(s, "sha256").hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def verify() -> dict:
    card = load(REPORT / "run-card.json")
    results = load(REPORT / "results.json")
    prereg = load(REPORT / "preregistration.json")
    registry = load(REPORT / "registry.json")
    readiness = load(REPORT / "readiness.json")
    surf = load(REPORT / "novelty-surface.json")
    dots = load(REPORT / "novelty-dots.json")
    started = load(REPORT / "started.json")

    require(sha(REPORT / "preregistration.md") == started["preregistration_md_sha256"] == card["lane_preregistration_sha256"],
            "preregistration.md hash drift")
    require(sha(REPORT / "registry.json") == prereg["registry_sha256"], "registry hash drift vs preregistration")
    require(registry["counts"] == {"aligned_rasters": 394, "exclusions": 2, "calibration_exclusions": 6},
            f"registry counts drift: {registry['counts']}")
    require(registry["complete"] is False, "registry must not claim complete parallel coverage")
    require(card["experiments_run"] == 3 and 0 < card["experimental_elapsed_seconds"] <= 7200, "budget breach")
    require(len(card["note"]) <= 140, "note >140 chars")

    s = results["summary"]
    require(set(s["arms"]) == {"msdb_edge", "pool_dense_edge", "pool_dispersed"}, "E1 arms drift")
    d1 = s["candidate_minus"]["msdb_edge"]
    require(d1["value"] > 0 and d1["ci95"][0] > 0, "E1 paired gate should have passed")
    conf = results["confirmation_seed4219"]
    require(conf is not None, "E2 confirmation missing")
    d2 = conf["candidate_minus"]["msdb_edge"]
    require(d2["value"] > 0 and d2["ci95"][0] > 0, "E2 paired gate should have passed")
    require(results["canary_alarms"] == [] and results["max_feature_symmetric_auc"] <= 0.90, "canary drift")
    require(all(row["withheld_positives"] == 60988 for row in s["arms"].values()), "withheld count drift")
    for fold in results["folds"]:
        require(all(a["emitted_pixels"] == fold["dot_budget_each_arm"] for a in fold["arms"].values()),
                "count-matched construction drift")

    expected = Counter(r["sha256"] for r in registry["rasters"])
    for stage, doc in (("surface", surf), ("dots", dots)):
        require(doc["stage"] == stage and doc["errors"] == [] and doc["submission_approved"] is False,
                f"{stage} novelty receipt drift")
        require(Counter(r["reference_sha256"] for r in doc["comparisons"]) == expected
                and len(doc["comparisons"]) == 394, f"{stage} novelty inventory drift")
        for row in doc["comparisons"]:
            rho = row["spearman_full_footprint"]
            require(rho is not None and math.isfinite(rho) and abs(rho) <= 0.90
                    and not row["identical_inside_footprint"], f"{stage} rho/identical drift: {row['reference']}")
    breaches = {r["reference"] for r in dots["comparisons"]
                if float(r["candidate_fraction_within_3px_of_reference"] or 0.0) > 0.70}
    require(breaches == BREACHING, f"dot-overlap breach set drift: {sorted(breaches)}")
    require(dots["decision"] == "duplicate-stop", f"dots decision drift: {dots['decision']}")
    require(len(dots["malformed_exclusions_audited"]) == 1
            and dots["malformed_exclusions_audited"][0]["invalid_in_footprint_cells"] == 2610312,
            "malformed GEMSDOE31 finite-subset audit drift")

    gates = {g["name"]: g["status"] for g in readiness["gates"]}
    require(gates["paired_improvement"] == "passed" and gates["dots_observed_registry"] == "failed"
            and gates["surface_observed_registry"] == "passed", f"readiness gate drift: {gates}")
    require(readiness["research_verdict"] == "negative" and readiness["download_ok"] is False, "readiness verdict drift")
    require(card["verdict"] == "negative" and card["download_ok"] is False and card["ok_to_submit"] is False
            and card["submission_approved"] is False and card["slot_selected"] is False
            and card["published_tiff"] is None and card["organizer_score"] is None, "run-card decision drift")
    require(not list((ROOT / "docs/downloads").glob("*POOL1*")), "a POOL1 TIFF was published despite duplicate-stop")

    raster_check = "runs raster absent (receipt-only verification)"
    runs_tif = ROOT / "runs/pool1" / f"{card['run_id']}-zeros.tif"
    if runs_tif.is_file():
        import numpy as np
        import rasterio
        from scipy.ndimage import distance_transform_edt
        from scipy.spatial import cKDTree
        from gemsdoe30.submission import validate_submission_file
        require(sha(runs_tif) == card["raster_sha256"], "runs raster hash drift vs run card")
        rep = validate_submission_file(runs_tif, ROOT / "data/raw/sample_submission.tif",
                                       require_finite_all_cells=True, portal_safe=True)
        require(rep.passed, f"runs raster failed format validation: {rep.to_dict()}")
        with rasterio.open(runs_tif) as ds:
            whole = ds.read(1)
        with rasterio.open(ROOT / "data/raw/labels.tif") as ds:
            labels = ds.read(1) > 0.5
        d = distance_transform_edt(~labels)[whole > 0.5]
        pts = np.argwhere(whole > 0.5).astype(float)
        require(int((whole > 0.5).sum()) == 44090 and int((d <= 2.0).sum()) == 0
                and float(cKDTree(pts).query(pts, k=2)[0][:, 1].min()) >= 2.82842712474619,
                "runs raster dot geometry drift")
        raster_check = "runs raster re-inspected: format/dots/off-catalogue/spacing all match run card"
    return {"verified": "POOL-1 negative (duplicate-stop) decision",
            "holdout_dti_e1": card["holdout_dti"], "delta_vs_msdb_e1": d1, "delta_vs_msdb_e2": d2,
            "breaching_references": sorted(BREACHING), "raster_check": raster_check}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--require-promote", action="store_true")
    args = p.parse_args()
    try:
        out = verify()
    except (ValueError, KeyError, OSError) as exc:
        print(f"VERIFY FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2))
    if args.require_promote:
        print("NOT PROMOTED: verdict=negative (duplicate-stop); slot not selected", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
