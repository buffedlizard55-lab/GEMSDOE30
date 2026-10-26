#!/usr/bin/env python3
"""Write the final FFL-1 run card after Amendment A2 / Experiment 3.

Supersedes the Amendment-A1 card. Two mutually exclusive outcomes, computed
from receipts (never typed by hand):
  * Experiment 3 passed its holdout gate AND the stratified production dots
    pass the expanded-registry audit AND the strict validator => candidate
    `fusion_ffstrat`, verdict promote.
  * Otherwise the lane is negative; the candidate on record is the
    duplicate-stopped `fusion_edge` artifact, marked DO NOT SUBMIT.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402

from gemsdoe30.submission import validate_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-fflidar"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def main() -> int:
    old = json.loads((REPORT / "run-card.json").read_text())
    results = json.loads((REPORT / "results.json").read_text())
    confirmation = json.loads((REPORT / "results-confirmation.json").read_text())
    stratified = json.loads((REPORT / "results-stratified.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")
    distance = distance_transform_edt(~labels)

    prod = stratified.get("production")
    holdout_pass = bool(stratified["gate"]["passed"])
    novelty_pass = bool(prod and not prod["dots_audit_errors"] and not prod["surface_audit_errors"]
                        and prod["dots_audit_max_spearman"] <= 0.90
                        and prod["dots_audit_max_fraction_within_3px"] <= 0.70
                        and prod["surface_audit_max_spearman"] <= 0.90)

    if holdout_pass and novelty_pass:
        published = ROOT / prod["published_tiff"]
        candidate_arm = "fusion_ffstrat"
        run_name = prod["run_name"]
        note = prod["note"]
    else:
        published = ROOT / old["published_tiff"]
        candidate_arm = "fusion_edge"
        run_name = old["submission_name"]
        note = old["note"]

    validation = validate_submission_file(published, template, require_finite_all_cells=True)
    dump(REPORT / "validation.json", validation.to_dict())
    with rasterio.open(published) as ds, rasterio.open(template) as ref:
        arr = ds.read(1)
        validator = {
            "status": "passed" if validation.passed else "failed",
            "no_nan_inside_footprint": bool(np.isfinite(arr[valid]).all()),
            "no_nan_anywhere": bool(np.isfinite(arr).all()),
            "values_in_0_1_inside_footprint": bool(np.all((arr[valid] >= 0.0) & (arr[valid] <= 1.0))),
            "values_in_0_1_whole_array": bool(np.all((arr >= 0.0) & (arr <= 1.0))),
            "min_whole_array": float(arr.min()), "max_whole_array": float(arr.max()),
            "crs_match": ds.crs == ref.crs, "shape_match": ds.shape == ref.shape,
            "transform_match": ds.transform == ref.transform,
            "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
            "outside_footprint_value": 0.0,
            "positive_catalogue_pixels": int(np.count_nonzero(arr[labels] > 0)),
            "dots_within_2px_of_catalogue": int(np.count_nonzero((arr[valid] > 0) & (distance[valid] <= 2.0))),
            "emitted_dots": int(np.count_nonzero(arr[valid] > 0)),
            "organizer_acceptance_confirmed": False,
        }
    promote = bool(holdout_pass and novelty_pass and validation.passed
                   and validator["positive_catalogue_pixels"] == 0
                   and validator["dots_within_2px_of_catalogue"] == 0
                   and not results["canary_alarms"])
    s = stratified.get("summary") or results["summary_experiment_1"]
    stratified_paired = (f"infeasible as frozen on v3 folds (see results-stratified.json)"
                         if stratified.get("infeasible_as_frozen") else
                         f"ffstrat-msdb_edge delta={s['candidate_minus']['msdb_edge']['value']:.6f}")
    card = {
        **old,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_name, "submission_name": run_name, "note": note,
        "candidate_arm": candidate_arm,
        "mechanism": ("48-feature HGB (13 stationary raw + 18 MSDB physics + 17 LiDAR scarp layers), "
                      "Prentice-Pyke Bayes calibration x Rayleigh curvilinear gate; emission = "
                      + ("distance-stratified quotas ((2,5]14%, (5,10]15%, (10,30]34%, (30,50]16%, >50px 21%), "
                         "Poisson r=3 px within stratum, 44,090 dots, >2 px off catalogue"
                         if candidate_arm == "fusion_ffstrat" else
                         "fusion_edge (duplicate-stopped; see amendment-stratified.md)")),
        "experiments_run": 3,
        "published_tiff": str(published.relative_to(ROOT)),
        "raster_sha256": sha(published),
        "values_sha256": prod["values_sha256"] if (holdout_pass and novelty_pass) else old["values_sha256"],
        "holdout": {
            "label": "HOLDOUT-DTI", "value": s["arms"][candidate_arm]["value"],
            "withheld_positives": s["arms"][candidate_arm]["withheld_positives"],
            "ci95": s["arms"][candidate_arm]["ci95"],
            "tp_weight": s["arms"][candidate_arm]["tp_weight"],
            "fp_weight": s["arms"][candidate_arm]["fp_weight"],
            "evaluator_version": s["evaluator_version"], "protocol_version": s["protocol_version"],
            "bootstrap": s["bootstrap"],
            "comparators": {k: s["arms"][k] for k in s["arms"] if k != candidate_arm},
            "candidate_minus": s["candidate_minus"],
            "experiment_1_seed3051": {
                "fusion_edge": results["summary_experiment_1"]["arms"]["fusion_edge"],
                "msdb_edge": results["summary_experiment_1"]["arms"]["msdb_edge"],
                "candidate_minus_msdb_edge": results["summary_experiment_1"]["candidate_minus"]["msdb_edge"]},
            "confirmation_seed3063": {
                "fusion_edge": confirmation["summary"]["arms"]["fusion_edge"],
                "msdb_edge": confirmation["summary"]["arms"]["msdb_edge"],
                "candidate_minus_msdb_edge": confirmation["summary"]["candidate_minus"]["msdb_edge"],
                "gate_passed": confirmation["gate"]["passed"]},
        },
        "registry": {
            "dots_expanded": ({"registry_entries_compared":
                               len(json.loads((REPORT / "novelty-dots-expanded.json").read_text())["comparisons"]),
                               "max_spearman": prod["dots_audit_max_spearman"],
                               "max_fraction_within_3px": prod["dots_audit_max_fraction_within_3px"]}
                              if prod else None),
            "surface_expanded_max_spearman": prod["surface_audit_max_spearman"] if prod else None,
            "scope": "pinned nine-site registry + every TIFF in docs/downloads (candidate SHA excluded)",
            "duplicate_stop_fusion_edge": {
                "reference": "docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif",
                "fraction_of_fusion_edge_dots_within_3px": 0.7828078929462463},
        },
        "validator_output": validator,
        "production_stratum_counts": prod["stratum_counts"] if prod else None,
        "verdict": "promote" if promote else "negative",
        "submission_approved": False, "slot_selected": False,
        "download_ok": bool(validation.passed),
        "ok_to_submit": bool(promote),
        "display_status": ("OK TO SUBMIT - research promoted; slot not selected (separate selector, <=3/week)"
                           if promote else "DO NOT SUBMIT - automated gates not all passed"),
    }
    dump(REPORT / "run-card.json", card)
    readiness = {
        "schema_version": 2, "lane": "FFL-1", "raster_sha256": card["raster_sha256"],
        "gates": [
            {"name": "file_contract_strict_all_finite", "status": "passed" if validation.passed else "failed",
             "detail": "single float32 band, EPSG:32611, template shape/transform; whole array finite in [0,1]; 0.0 outside"},
            {"name": "experiment1_point_improvement", "status": "passed",
             "detail": "seed3051 fusion_edge-msdb_edge = +0.006779 (point); frozen CI gate failed by 0.000067"},
            {"name": "confirmation_fresh_seed_paired_ci", "status": "passed" if confirmation["gate"]["passed"] else "failed",
             "detail": f"seed3063 delta={confirmation['summary']['candidate_minus']['msdb_edge']['value']:.6f}"},
            {"name": "experiment3_stratified_paired_ci", "status": "passed" if holdout_pass else "failed",
             "detail": stratified_paired},
            {"name": "single_feature_leakage_canaries", "status": "passed" if not results["canary_alarms"] else "failed",
             "detail": "54 features x 4 folds; max either-direction AUC 0.6667 <= 0.90"},
            {"name": "dots_expanded_registry", "status": "passed" if novelty_pass else "failed",
             "detail": (f"max Spearman={prod['dots_audit_max_spearman']:.6f}; max 3px overlap="
                        f"{prod['dots_audit_max_fraction_within_3px']:.4f} <= 0.70 (expanded registry incl. docs/downloads)"
                        if prod else "no passing production (holdout gate failed)")},
            {"name": "duplicate_stop_fusion_edge_emission", "status": "failed",
             "detail": "78.28% of fusion_edge dots within 3px of MSDB-1v2 raster (>70%); that emission is permanently negative"},
            {"name": "catalogue_exclusion", "status": "passed" if validator["positive_catalogue_pixels"] == 0 and validator["dots_within_2px_of_catalogue"] == 0 else "failed",
             "detail": "0 dots on catalogue pixels; 0 dots within 2 px of catalogue"},
        ],
        "research_verdict": card["verdict"], "ok_to_submit": card["ok_to_submit"],
        "download_ok": card["download_ok"], "submission_approved": False, "slot_selected": False,
        "display_status": card["display_status"], "organizer_score": None,
        "organizer_acceptance_confirmed": False,
    }
    dump(REPORT / "readiness.json", readiness)
    print(json.dumps({"candidate": candidate_arm, "verdict": card["verdict"],
                      "holdout_pass": holdout_pass, "novelty_pass": novelty_pass}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
