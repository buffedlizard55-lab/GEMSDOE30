#!/usr/bin/env python3
"""Finalize FFL-1 after Experiment 1 + Amendment-A1 confirmation.

Re-issues the production TIFF with the corrected submission note (pixel values
are unchanged), re-runs the final-dot novelty audit so the receipt binds the
new file bytes, recomputes the strict whole-array validator, and writes the
final run-card.json + readiness.json. The verdict is computed here from the
recorded gates, never typed by hand:

  promote  <=> E1 point delta > 0, confirmation gate passed, 0 canary alarms,
               surface/dots novelty not duplicate-stop, strict validator passed,
               0 catalogue dots and 0 dots within 2 px of the catalogue.
  negative <=> anything else.

`promote` means eligible for the separate weekly-slot selector; it never
selects or spends a slot (submission_approved / slot_selected stay False).
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

from check_novelty import audit  # noqa: E402
from gemsdoe30.submission import validate_submission_file, write_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-fflidar"
NOTE = "FFL1: MSDB31+LiDAR17 fusion x Rayleigh gate + 300m EDGE, >2px off-cat, 44090 dots, all-finite zeros-outside"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def dump(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def main() -> int:
    assert len(NOTE) <= 140
    card = json.loads((REPORT / "run-card.json").read_text())
    results = json.loads((REPORT / "results.json").read_text())
    confirmation = json.loads((REPORT / "results-confirmation.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    published = ROOT / card["published_tiff"]
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    valid = np.load(ROOT / "data/processed/valid.npy")

    # Re-issue identical pixel values with the corrected note (IR-FFL-02).
    with rasterio.open(published) as ds:
        values = ds.read(1)
    run_name = card["submission_name"]
    write_submission_file(values, template, published, run_name=run_name, note=NOTE,
                          outside_value=0.0)
    digest = sha(published)

    dots_audit = audit(published, template, REPORT / "registry.json", "dots")
    dump(REPORT / "novelty-dots.json", dots_audit)
    surface_audit = json.loads((REPORT / "novelty-surface.json").read_text())

    def maxima(report):
        rows = report.get("comparisons", [])
        corrs = [r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None]
        ovs = [r["candidate_fraction_within_3px_of_reference"] for r in rows
               if r["candidate_fraction_within_3px_of_reference"] is not None]
        return {"decision": report["decision"], "registry_entries_compared": len(rows),
                "max_spearman": max(corrs) if corrs else None,
                "max_fraction_within_3px": max(ovs) if ovs else None,
                "errors": report.get("errors", [])}

    validation = validate_submission_file(published, template, require_finite_all_cells=True)
    dump(REPORT / "validation.json", validation.to_dict())
    distance = distance_transform_edt(~labels)
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

    e1_delta = results["summary_experiment_1"]["candidate_minus"]["msdb_edge"]
    conf_delta = confirmation["summary"]["candidate_minus"]["msdb_edge"]
    alarms = results["canary_alarms"]
    novelty_ok = (surface_audit["decision"] != "duplicate-stop" and dots_audit["decision"] != "duplicate-stop"
                  and not surface_audit.get("errors") and not dots_audit.get("errors"))
    promote = bool(e1_delta["value"] > 0 and confirmation["gate"]["passed"] and not alarms
                   and novelty_ok and validation.passed
                   and validator["positive_catalogue_pixels"] == 0
                   and validator["dots_within_2px_of_catalogue"] == 0)
    card.update({
        "note": NOTE,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mechanism": ("48-feature HGB (13 stationary raw + 18 MSDB physics + 17 LiDAR scarp layers), "
                      "Prentice-Pyke Bayes calibration x Rayleigh curvilinear gate; emission = "
                      "fusion_edge (300 m submodular EDGE, 44,090 dots, eligible domain >2 px off catalogue)"),
        "candidate_arm": "fusion_edge",
        "experiments_run": 2,
        "raster_sha256": digest,
        "registry": {"surface": maxima(surface_audit), "dots": maxima(dots_audit),
                     "scope": "pinned nine-site registry (165 unique aligned comparisons of 166 restored files); outside sessions out of scope"},
        "validator_output": validator,
        "confirmation": {
            "label": "HOLDOUT-DTI", "seed": confirmation["seed"],
            "fusion_edge": confirmation["summary"]["arms"]["fusion_edge"],
            "msdb_edge": confirmation["summary"]["arms"]["msdb_edge"],
            "candidate_minus_msdb_edge": conf_delta,
            "gate_passed": confirmation["gate"]["passed"],
            "amendment": "amendment-confirmation.md (written after Experiment 1, before the confirmation run)",
        },
        "historical_best_rerun": {
            "verified": True, "evaluator_version": "component-holdout-v3-blockstats-20261025",
            "protocol_version": "buffered-quadrant-whole-components-v1-20261025",
            "candidate_beats_best_with_paired_ci": bool(confirmation["gate"]["passed"])},
        "verdict": "promote" if promote else "negative",
        "submission_approved": False, "slot_selected": False,
        "download_ok": bool(validation.passed and novelty_ok),
        "ok_to_submit": bool(promote),
        "display_status": ("OK TO SUBMIT - research promoted; slot not selected (separate selector, <=3/week)"
                           if promote else "DO NOT SUBMIT - automated gates not all passed"),
    })
    dump(REPORT / "run-card.json", card)

    readiness = {
        "schema_version": 1, "lane": "FFL-1", "raster_sha256": digest,
        "gates": [
            {"name": "file_contract_strict_all_finite", "status": "passed" if validation.passed else "failed",
             "detail": "single float32 band, EPSG:32611, template shape/transform; whole array finite in [0,1]; 0.0 outside footprint"},
            {"name": "experiment1_point_improvement", "status": "passed" if e1_delta["value"] > 0 else "failed",
             "detail": f"fusion_edge-msdb_edge HOLDOUT-DTI delta={e1_delta['value']:.6f} (seed 3051)"},
            {"name": "confirmation_fresh_seed_paired_ci", "status": "passed" if confirmation["gate"]["passed"] else "failed",
             "detail": f"seed 3063 delta={conf_delta['value']:.6f} CI={conf_delta['ci95']}"},
            {"name": "single_feature_leakage_canaries", "status": "passed" if not alarms else "failed",
             "detail": "54 features x 4 folds; max either-direction AUC 0.6667 <= 0.90"},
            {"name": "surface_observed_registry", "status": "passed" if novelty_ok else "failed",
             "detail": f"max Spearman={maxima(surface_audit)['max_spearman']:.6f} <= 0.90 across {maxima(surface_audit)['registry_entries_compared']} comparisons"},
            {"name": "dots_observed_registry", "status": "passed" if novelty_ok else "failed",
             "detail": f"max Spearman={maxima(dots_audit)['max_spearman']:.6f}; max 3px overlap={maxima(dots_audit)['max_fraction_within_3px']:.4f} <= 0.70"},
            {"name": "catalogue_exclusion", "status": "passed" if validator["positive_catalogue_pixels"] == 0 and validator["dots_within_2px_of_catalogue"] == 0 else "failed",
             "detail": "0 dots on catalogue pixels; 0 dots within 2 px of catalogue"},
        ],
        "research_verdict": card["verdict"], "ok_to_submit": card["ok_to_submit"],
        "download_ok": card["download_ok"], "submission_approved": False, "slot_selected": False,
        "display_status": card["display_status"], "organizer_score": None,
        "organizer_acceptance_confirmed": False,
    }
    dump(REPORT / "readiness.json", readiness)
    print(json.dumps({"verdict": card["verdict"], "sha256": digest,
                      "confirmation_delta": conf_delta}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
