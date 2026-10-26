#!/usr/bin/env python3
"""Verify a quarantined duplicate's receipts; never approve or distribute its TIFF.

CI can recompute the holdout, canaries and duplicate decision without distributing
the stopped raster. ``--inspect-quarantine`` additionally reopens private local
bytes if available; it is explicit about receipt-only versus byte-level evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from gemsdoe30.experiments import contract
from gemsdoe30.holdout import spatial_bootstrap
from gemsdoe30.readiness import assess, number
from gemsdoe30.submission import validate_submission_file
from scripts.verify_current_run import check_equal, load


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(directory: Path, template: Path, *, write=False, inspect_quarantine=False):
    card = load(directory / "run-card.json")
    spec = contract(card)
    if (card.get("duplicate_stopped") is not True or card.get("published_tiff") is not None
            or card.get("download_ok") is not False or card.get("submission_approved") is not False
            or card.get("slot_selected") is not False or card.get("verdict") != "negative"):
        raise ValueError("stopped artifact must remain unpublished, non-downloadable and unapproved")
    stopped = load(directory / "duplicate-stop.json")
    stage = card.get("stop_stage")
    if (stopped.get("decision") != "duplicate-stop" or stopped.get("stage") != stage
            or stopped.get("no_further_experiment") is not True or stage not in ("surface", "dots")):
        raise ValueError("stop-stage receipt mismatch")
    results = load(directory / "results.json")
    if results.get("experiment_spec") != spec["id"]:
        raise ValueError("card/results experiment contract mismatch")
    summary = spatial_bootstrap(results["bootstrap_sufficient_statistics"], candidate=spec["candidate"],
                                 replicates=2000, seed=3071)
    check_equal(results["summary"], summary, "stopped/results/summary")
    h = card["holdout"]
    card_summary = {k: h[k] for k in ("evaluator_version", "protocol_version", "bootstrap", "candidate_minus")}
    card_summary["arms"] = {spec["candidate"]: {k: h[k] for k in summary["arms"][spec["candidate"]]},
                            **h["comparators"]}
    check_equal(card_summary, summary, "stopped/card/holdout")
    digest = card["raster_sha256"]
    if results.get("raster_sha256") != digest:
        raise ValueError("results do not bind to the quarantined bytes")
    prereg = sha(directory / "preregistration.md")
    started, registration = load(directory / "started.json"), load(directory / "registration.json")
    if any(r.get("preregistration_sha256") != prereg for r in (card, results, started)) or registration.get("registered_plan_sha256") != prereg:
        raise ValueError("frozen plan/start/results/card registration mismatch")
    if (started.get("experiment_count") != card.get("experiments_run")
            or started.get("fixed_arms") != list(spec["arms"]) or card.get("fixed_arms") != list(spec["arms"])
            or card.get("source_execution_script_sha256") != started.get("script_sha256")):
        raise ValueError("execution count/arms/source identity mismatch")
    failure = load(directory / "failure.json")
    elapsed = (datetime.fromisoformat(failure["created_utc"]) - datetime.fromisoformat(started["started_utc"])).total_seconds()
    check_equal(card.get("experimental_elapsed_seconds"), elapsed, "stopped/card/elapsed")
    check_equal(results.get("experimental_elapsed_seconds"), elapsed, "stopped/results/elapsed")
    if card.get("created_utc") != failure.get("created_utc"):
        raise ValueError("card does not record the actual stop time")
    features, cache = load(directory / "feature-receipt.json"), load(directory / "cache-verification.json")
    signature = features["signature"]
    if (signature.get("transform_code_sha256") != sha(ROOT / spec["transform_path"])
            or signature.get("transform_version") != spec["transform_version"]
            or signature.get("parent_transform_code_sha256") != sha(ROOT / spec["parent_transform_path"])
            or signature.get("parent_transform_version") != spec["parent_transform_version"]
            or features.get("support_px") != spec["support_px"] or card.get("physical_support_px") != spec["support_px"]
            or any(f.get("buffer_px") != spec["support_px"] for f in results["folds"])):
        raise ValueError("transform/source support guard mismatch")
    if (cache.get("all_cells_match_raw_sources") is not True
            or cache.get("dataset_signature") != card.get("dataset_signature")
            or signature.get("dataset_signature") != card.get("dataset_signature")):
        raise ValueError("prepared cache signature mismatch")
    registry = load(directory / "registry.json")
    registry_sha = sha(directory / "registry.json")
    if registration.get("registry_sha256") != registry_sha:
        raise ValueError("registry changed after preregistration")
    expected = {r["sha256"] for r in registry["rasters"]}
    audits = {}
    for which in ("surface", "dots"):
        path = directory / f"novelty-{which}.json"
        if not path.exists() and which == "dots" and stage == "surface":
            audits[which] = {"comparisons": [], "errors": ["Stopped before dot placement"]}
            continue
        report = load(path)
        rows = report["comparisons"]
        if (report.get("stage") != which or any(r.get("stage") != which for r in rows)
                or len(rows) != len(expected) or {r.get("reference_sha256") for r in rows} != expected
                or report.get("registry_sha256") != registry_sha or report.get("template_sha256") != sha(template)
                or report.get("registry_complete") != registry.get("complete")):
            raise ValueError("novelty stage/inventory/template/registry identity mismatch")
        expected_summary = {
            "decision": report["decision"], "registry_entries_compared": len(rows),
            "max_spearman": max((r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None), default=None),
            "max_fraction_within_3px": max((r["candidate_fraction_within_3px_of_reference"] for r in rows
                                            if r["candidate_fraction_within_3px_of_reference"] is not None), default=None),
            "errors": report["errors"],
        }
        check_equal(card["registry"][which], expected_summary, f"stopped/card/registry/{which}")
        audits[which] = report
    if audits[stage].get("candidate_sha256") != digest:
        raise ValueError("duplicate receipt does not bind to stopped artifact")
    raw_alarms = []
    for fold in results["feature_canaries"]:
        for row in fold["features"]:
            values = (row["raw_auc"], row["univariate_training_only_hgb_auc"])
            if any(not number(v) or not 0 <= v <= 1 for v in values):
                raise ValueError("feature canary AUC must be finite in [0,1]")
            alarm = max(*values, *(1 - v for v in values)) > .90
            if alarm != row.get("alarm_above_0_90"):
                raise ValueError("feature canary boolean contradicts numeric AUC")
            if alarm:
                raw_alarms.append(dict(fold=fold["fold"], **row))
    expected_canaries = {"features_per_fold": len(spec["features"]), "folds": 4,
                         "alarm_count": len(raw_alarms), "alarms": raw_alarms,
                         "receipt": str((directory / "results.json").relative_to(ROOT))}
    check_equal(card["feature_canaries"], expected_canaries, "stopped/card/canaries")
    science_pass = not raw_alarms and all(d["ci95"][0] > 0 for d in summary["candidate_minus"].values())
    if any(r.get("scientific_gate_passed") is not science_pass for r in (card, results)):
        raise ValueError("scientific gate boolean contradicts paired numeric evidence")
    validation = load(directory / "validation.json")
    if sha(directory / "validation.json") != card.get("recorded_validation_sha256") or validation.get("raster_sha256") != digest:
        raise ValueError("recorded validator hash/identity mismatch")
    check_equal(card["validator_output"], validation.get("facts"), "stopped/card/validator")
    # Integrating another session must not silently omit newly public local
    # references. Keep the original pre-placement registry immutable, then check
    # the SAME saved states against explicitly labelled post-stop arrivals.
    known = expected | {r["sha256"] for r in registry.get("exclusions", [])} | {digest}
    # Every downloadable artifact in the repository is verified under its own
    # run card (the stopped attempt's registry covers only its own references).
    # Those are not late references for this stopped experiment.
    registered_tiffs = {str(digest)}
    for run_card in (ROOT / "docs/research").rglob("*run-card.json"):
        try:
            rc = json.loads(run_card.read_text())
        except Exception:
            continue
        for key in ("submission_file", "published_tiff", "artifact_path"):
            value = rc.get(key)
            if isinstance(value, str) and value:
                registered_tiffs.add(value)
    extra_hashes = {sha(path) for path in (ROOT / "docs/downloads").glob("*.tif")
                    if sha(path) not in known and str(path.relative_to(ROOT)) not in registered_tiffs}
    additional_path = directory / "registry-parallel-addendum.json"
    combined = audits
    if extra_hashes or additional_path.exists():
        if not additional_path.is_file():
            raise ValueError("new local references require a post-stop late-registry audit")
        additional = load(additional_path)
        extra_rows = additional["rasters"]
        extra_expected = {r["sha256"] for r in extra_rows}
        if (additional.get("original_registry_sha256") != registry_sha
                or extra_expected != extra_hashes or len(extra_rows) != len(extra_expected)):
            raise ValueError("late-registry identity/inventory mismatch")
        for row in extra_rows:
            path = (ROOT / row["path"]).resolve()
            if not path.is_relative_to(ROOT) or sha(path) != row["sha256"]:
                raise ValueError("late reference file identity mismatch")
        combined = {}
        for which in ("surface", "dots"):
            late = load(directory / f"novelty-parallel-{which}.json")
            rows = late["comparisons"]
            if (late.get("stage") != which or any(r.get("stage") != which for r in rows)
                    or len(rows) != len(extra_expected) or {r.get("reference_sha256") for r in rows} != extra_expected
                    or late.get("candidate_sha256") != audits[which].get("candidate_sha256")
                    or late.get("template_sha256") != sha(template) or late.get("registry_sha256") != sha(additional_path)
                    or late.get("registry_complete") is not False):
                raise ValueError("post-stop novelty stage/inventory/identity mismatch")
            combined[which] = {**audits[which], "comparisons": audits[which]["comparisons"] + rows,
                               "errors": audits[which].get("errors", []) + late.get("errors", [])}
    # A duplicate can have passed every file-format check. That must never become
    # permission to download, nor a claim that absent bytes were re-read by CI.
    decision = assess(card, results, format_passed=False, hash_matches=False,
                      surface_audit=combined["surface"], dots_audit=combined["dots"], registry=registry,
                      artifact_public=False)
    if additional_path.exists():
        addition = {"registry": str(additional_path.relative_to(ROOT)),
                    "surface_receipt": str((directory / "novelty-parallel-surface.json").relative_to(ROOT)),
                    "dots_receipt": str((directory / "novelty-parallel-dots.json").relative_to(ROOT)),
                    "timing": "Post-stop late-reference audit of saved states; no refit, replacement, new placement or original-registry rewrite",
                    "combined_observed_registry": decision["observed_registry"]}
        check_equal(card.get("additional_novelty_evidence"), addition, "stopped/card/additional_novelty_evidence")
    if decision["observed_registry"][stage]["status"] != "failed":
        raise ValueError("a duplicate-stop must be justified by numeric duplicate evidence")
    if any(decision[k] is not False for k in ("download_ok", "submission_approved", "slot_selected", "eligible_for_separate_slot_selector")):
        raise ValueError("stopped artifact unexpectedly eligible")
    for path in (ROOT / "docs/downloads").glob("*.tif"):
        if sha(path) == digest:
            raise ValueError("quarantined duplicate has been published under a download name")
    decision["recorded_local_validation"] = {"status": "passed" if validation.get("passed") is True else "failed",
                                               "receipt_sha256": sha(directory / "validation.json"),
                                               "current_bytes_reopened": False,
                                               "scope": "Stored validator receipt only; duplicate raster is not distributed"}
    reinspection = None
    if inspect_quarantine:
        relative = Path(card["artifact_path"])
        artifact = (ROOT / relative).resolve()
        if relative.is_absolute() or not artifact.is_relative_to(ROOT / "outputs") or sha(artifact) != digest:
            raise ValueError("quarantined artifact missing, outside quarantine, or changed")
        if not validate_submission_file(artifact, template).passed:
            raise ValueError("quarantined bytes fail shared file validation")
        reinspection = {"passed": True, "raster_sha256": digest, "public_download": False}
    # Complete all assertions, including optional private-byte checks, before
    # replacing canonical evidence. Never leave a partial green write on failure.
    target = directory / "readiness.json"
    if write:
        temp = target.with_suffix(".partial.json")
        temp.write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n")
        temp.replace(target)
    elif not target.exists() or load(target) != decision:
        raise ValueError("stopped readiness receipt missing/stale; regenerate with --write")
    if reinspection is not None:
        decision = {**decision, "quarantined_byte_reinspection": reinspection}
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "docs/research/texture-controls")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--inspect-quarantine", action="store_true")
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.directory, args.template, write=args.write, inspect_quarantine=args.inspect_quarantine)
    except (ValueError, KeyError, OSError) as exc:
        print(f"Stopped-attempt verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 2 if args.require_promote else 0


if __name__ == "__main__":
    raise SystemExit(main())
