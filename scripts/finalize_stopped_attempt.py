#!/usr/bin/env python3
"""Log a duplicate-stopped execution without refitting, placing, or publishing TIFFs.

The duplicate stop intentionally interrupts the builder before its success-only
release path. This audit-only finalizer preserves the mandatory negative run card
and local validator output. It never copies the quarantined raster to downloads.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
import numpy as np
import rasterio
from gemsdoe30.experiments import contract
from gemsdoe30.submission import valid_template_mask, validate_submission_file
from scripts.verify_current_run import local_path

EXECUTED_REF = "79d1be92e578f4e555fe5a5ae8d273728221c8af"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def finalize(directory: Path, template: Path, *, execution_ref: str | None = None):
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT):
        raise ValueError("report directory must stay in repository")
    stopped = load(directory / "duplicate-stop.json")
    if stopped.get("decision") != "duplicate-stop" or stopped.get("no_further_experiment") is not True:
        raise ValueError("only a recorded mandatory duplicate stop can be finalized")
    started = load(directory / "started.json")
    if execution_ref is not None:
        source = subprocess.check_output(["git", "show", f"{execution_ref}:scripts/run_texture_controls.py"], cwd=ROOT, timeout=30)
        if hashlib.sha256(source).hexdigest() != started.get("script_sha256"):
            raise ValueError("execution commit does not contain the exact executed script")
    stage = stopped["stage"]
    if stage not in ("surface", "dots"):
        raise ValueError("unknown stop stage")
    source = load(directory / f"novelty-{stage}.json")
    artifact = Path(source["candidate"])
    artifact = artifact.resolve() if artifact.is_absolute() else local_path(str(artifact))
    if not artifact.is_relative_to(ROOT / "outputs"):
        raise ValueError("a stopped artifact must remain quarantined under ignored outputs/")
    if sha(artifact) != source["candidate_sha256"]:
        raise ValueError("quarantined artifact differs from its exact novelty receipt")
    sidecar = load(artifact.with_suffix(".json"))
    if sidecar["output_sha256"] != source["candidate_sha256"]:
        raise ValueError("writer sidecar identity mismatch")
    report = validate_submission_file(artifact, template).to_dict()
    report.update({"raster_sha256": sha(artifact), "inspection_scope": "Post-stop local byte re-read; raster deliberately not published"})
    with rasterio.open(template) as reference, rasterio.open(artifact) as ds:
        valid = valid_template_mask(reference, np)
        values = ds.read(1)
        labels_path = ROOT / "data/raw/labels.tif"
        with rasterio.open(labels_path) as labels:
            catalogue = labels.read(1) == 1
        validator = {"status": "passed" if report["passed"] else "failed",
                     "no_nan_inside_footprint": bool(np.isfinite(values[valid]).all()),
                     "values_in_0_1": bool(np.all((values[valid] >= 0) & (values[valid] <= 1))),
                     "crs_match": ds.crs == reference.crs, "shape_match": ds.shape == reference.shape,
                     "transform_match": ds.transform == reference.transform,
                     "single_float32_band": ds.count == 1 and ds.dtypes == ("float32",),
                     "nan_nodata_outside_footprint": bool(np.isnan(values[~valid]).all()),
                     "positive_catalogue_pixels": int(np.count_nonzero(values[catalogue & valid] > 0)),
                     "emitted_dots": int(np.count_nonzero(values[valid] > 0)) if stage == "dots" else None,
                     "organizer_acceptance_confirmed": False,
                     "scope": "Recorded local validation, not organizer acceptance; artifact not distributed"}
    report["facts"] = validator
    dump(directory / "validation.json", report)
    results, started = load(directory / "results.json"), load(directory / "started.json")
    failure = load(directory / "failure.json")
    spec = contract({"experiment_spec": "tdxc2"})
    summary = results["summary"]
    preregistration = sha(directory / "preregistration.md")
    if preregistration != started["preregistration_sha256"] or preregistration != results["preregistration_sha256"]:
        raise ValueError("plan/start/results registration mismatch")
    elapsed = (datetime.fromisoformat(failure["created_utc"]) - datetime.fromisoformat(started["started_utc"])).total_seconds()
    if elapsed <= 0 or elapsed > 7200:
        raise ValueError("recorded execution violates time budget")
    alarms = [dict(fold=f["fold"], **r) for f in results["feature_canaries"] for r in f["features"] if r["alarm_above_0_90"]]
    audits = {s: load(directory / f"novelty-{s}.json") for s in ("surface", "dots")
              if (directory / f"novelty-{s}.json").is_file()}
    registry = load(directory / "registry.json")
    def summary_of(audit):
        rows = audit["comparisons"]
        return {"decision": audit["decision"], "registry_entries_compared": len(rows),
                "max_spearman": max((r["spearman_full_footprint"] for r in rows
                                      if r["spearman_full_footprint"] is not None), default=None),
                "max_fraction_within_3px": max((r["candidate_fraction_within_3px_of_reference"] for r in rows
                                                if r["candidate_fraction_within_3px_of_reference"] is not None), default=None),
                "errors": audit["errors"]}
    original_signature = load(directory / "feature-receipt.json")["signature"]
    science_pass = not alarms and all(row["ci95"][0] > 0 for row in summary["candidate_minus"].values())
    card = {"schema_version": 3, "experiment_spec": "tdxc2", "run_id": sidecar["run_name"],
            "hypothesis": "Nonzero-lag magnetic profile correspondence adds displacement-specific fault recovery beyond the full 19-band stack.",
            "mechanism": "Full-stack HGB plus cross-scale opposite-flank lag gain; matched zero-lag and local Fourier-phase controls.",
            "non_fault_mimic": "Intrusive lithologic contact; survey/gridding seam",
            "lane": "TDX-C2 magnetic profile displacement continuation; not externally assigned",
            "experiments_run": 1, "fixed_arms": list(spec["arms"]), "experiment_cap": 3,
            "experimental_elapsed_seconds": elapsed, "elapsed_scope": "UTC start-to-duplicate-stop, one-second timestamp precision",
            "time_cap_hours": 2, "physical_support_px": 17,
            "confirmation_scope": "Previously inspected catalogue folds; exploratory continuation, NOT independent confirmation",
            "holdout": {**summary["arms"][spec["candidate"]],
                        **{k: summary[k] for k in ("evaluator_version", "protocol_version", "bootstrap", "candidate_minus")},
                        "scope": "buffered whole-segment catalogue recovery; NOT organizer performance",
                        "comparators": {n: summary["arms"][n] for n in spec["arms"] if n != spec["candidate"]}},
            "feature_canaries": {"features_per_fold": len(spec["features"]), "folds": 4,
                                  "alarm_count": len(alarms), "alarms": alarms,
                                  "receipt": str((directory / "results.json").relative_to(ROOT))},
            "registry": {"complete": False, **{s: summary_of(a) for s, a in audits.items()},
                         "coverage": f"{len(registry['rasters'])} observed aligned byte identities; missing private lanes and most original surfaces"},
            "raster_sha256": sha(artifact), "validator_output": validator,
            "recorded_validation_sha256": sha(directory / "validation.json"),
            "submission_name": sidecar["run_name"], "note": sidecar["note"],
            "artifact_path": str(artifact.relative_to(ROOT)), "published_tiff": None,
            "artifact_disposition": "quarantined-duplicate; NOT a unique competition submission",
            "download_ok": False, "submission_approved": False, "slot_selected": False,
            "duplicate_stopped": True, "stop_stage": stage, "verdict": "negative",
            "scientific_gate_passed": science_pass,
            "blockers": ["Mandatory duplicate-stop; no further experiment or raster publication",
                         "Candidate did not beat all matched controls with positive paired confidence intervals",
                         "Complete parallel registry, assigned lane and comparable historical-best rerun unavailable",
                         "Current organizer portal allowance, eligibility, deadline and acceptance unverified"],
            "preregistration_sha256": preregistration,
            "dataset_signature": original_signature["dataset_signature"],
            "source_execution_script_sha256": started["script_sha256"],
            "source_execution_ref": execution_ref,
            "created_utc": failure["created_utc"],
            "logging_scope": "Audit-only finalization after mandatory stop; no refit, reselection or TIFF publication"}
    previous_card = directory / "run-card.json"
    if previous_card.exists():
        previous = load(previous_card)
        if previous.get("raster_sha256") != card["raster_sha256"]:
            raise ValueError("audit finalization cannot replace another artifact identity")
        if "additional_novelty_evidence" in previous:
            card["additional_novelty_evidence"] = previous["additional_novelty_evidence"]
    if len(card["note"]) > 140:
        raise ValueError("note exceeds 140 characters")
    # Bind already computed holdout statistics to the stopped bytes; this is not
    # another experiment or a replacement of the frozen scientific measurements.
    results["raster_sha256"] = card["raster_sha256"]
    results["experimental_elapsed_seconds"] = elapsed
    dump(directory / "results.json", results)
    dump(directory / "run-card.json", card)
    (directory / "canaries-partial.json").unlink(missing_ok=True)
    return card


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "docs/research/texture-controls")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--execution-ref", default=EXECUTED_REF)
    args = parser.parse_args()
    card = finalize(args.directory, args.template, execution_ref=args.execution_ref)
    print(json.dumps(card, indent=2))


if __name__ == "__main__":
    main()
