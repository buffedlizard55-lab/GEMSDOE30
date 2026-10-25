#!/usr/bin/env python3
"""Reopen the current TIFF, recompute pooled uncertainty, and adjudicate release gates.

Exit 0 means the published research decision is internally verified, NOT permission
to submit. ``--require-promote`` exits 2 unless all research promotion gates pass.
There is no override, human-inspector field, uploader or weekly-slot selector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe30.holdout import spatial_bootstrap
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file


def local_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or Path(relative).is_absolute():
        raise ValueError("evidence path must stay inside the repository")
    return path


def load(path: Path):
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"evidence root must be a JSON object: {path.name}")
    return value


def check_equal(actual, expected, where="evidence"):
    """Check every recomputed value, including paired CIs; never zip-truncate CIs."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"evidence key mismatch: {where}")
        for key in expected:
            check_equal(actual[key], expected[key], f"{where}/{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"evidence list length mismatch: {where}")
        for i, (a, b) in enumerate(zip(actual, expected)):
            check_equal(a, b, f"{where}/{i}")
    elif isinstance(expected, float):
        if (isinstance(actual, bool) or not isinstance(actual, (float, int))
                or not math.isfinite(actual) or not math.isclose(actual, expected, abs_tol=1e-10, rel_tol=0)):
            raise ValueError(f"recomputed numeric mismatch: {where}")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"evidence value mismatch: {where}")


def verify(pointer: Path, template: Path, *, write=False):
    selection = load(pointer)
    card_path = local_path(selection["run_card"])
    directory = card_path.parent
    card = load(card_path)
    results = load(directory / "results.json")
    raster = local_path(card["published_tiff"])
    with raster.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = load(raster.with_suffix(".json"))
    hashes_match = digest == card["raster_sha256"] == manifest["output_sha256"]
    if not hashes_match:
        raise ValueError("published TIFF does not match its run-card/sidecar hash")
    if manifest["note"] != card["note"] or manifest["run_name"] != card["submission_name"]:
        raise ValueError("submission name or note differs between card and sidecar")
    report = validate_submission_file(raster, template)
    if not report.passed:
        raise ValueError("published TIFF fails the shared format validator")
    recomputed = spatial_bootstrap(results["bootstrap_sufficient_statistics"], candidate="tdx6",
                                    replicates=2000, seed=3071)
    # Check the complete pooled summary, not only the candidate point estimate.
    # A changed paired CI must not silently turn a negative result into promotion.
    check_equal(results["summary"], recomputed, "results/summary")
    h = card["holdout"]
    card_summary = {key: h[key] for key in ("evaluator_version", "protocol_version", "bootstrap", "candidate_minus")}
    card_summary["arms"] = {"tdx6": {key: h[key] for key in recomputed["arms"]["tdx6"]},
                            **h["comparators"]}
    check_equal(card_summary, recomputed, "card/holdout")
    preregistration = hashlib.sha256((directory / "preregistration.md").read_bytes()).hexdigest()
    started = load(directory / "started.json")
    if any(row.get("preregistration_sha256") != preregistration for row in (card, results, started)):
        raise ValueError("frozen preregistration hash differs between plan/start/results/card")
    if results.get("raster_sha256") != digest:
        raise ValueError("holdout results do not bind to the published TIFF")
    surface = load(directory / "novelty-surface.json")
    dots = load(directory / "novelty-dots.json")
    registry = load(directory / "registry.json")
    if dots.get("candidate_sha256") != digest:
        raise ValueError("final-dot novelty receipt is not bound to the published TIFF")
    with template.open("rb") as stream:
        template_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    expected_registry = {row["sha256"] for row in registry["rasters"]}
    for stage, audit in (("surface", surface), ("dots", dots)):
        rows = audit.get("comparisons", [])
        if (audit.get("stage") != stage or any(row.get("stage") != stage for row in rows)
                or len(rows) != len(expected_registry)
                or {row.get("reference_sha256") for row in rows} != expected_registry):
            raise ValueError("novelty receipt inventory/stage differs from the pinned registry")
        claimed = audit.get("registry_sha256")
        actual = hashlib.sha256((directory / "registry.json").read_bytes()).hexdigest()
        if claimed != actual or audit.get("template_sha256") != template_hash:
            raise ValueError("novelty receipt registry/template hash mismatch")
        if audit.get("registry_complete") != registry.get("complete"):
            raise ValueError("novelty completeness flag contradicts its pinned registry")
    readiness = assess(card, results, format_passed=report.passed, hash_matches=hashes_match,
                       surface_audit=surface, dots_audit=dots, registry=registry)
    if card.get("verdict") != readiness["research_verdict"] or card.get("submission_approved") is not False:
        raise ValueError("card approval/verdict contradicts machine-adjudicated gates")
    if manifest.get("submission_approved") is not False:
        raise ValueError("download sidecar must not grant a competition slot")
    target = directory / "readiness.json"
    if local_path(selection["readiness"]) != target:
        raise ValueError("current pointer must select this exact run's readiness receipt")
    if card.get("download_ok") != readiness["download_ok"] or card.get("slot_selected") is not False:
        raise ValueError("card download/slot fields contradict automated research-only decision")
    if write:
        target.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
    elif not target.exists() or load(target) != readiness:
        raise ValueError("readiness receipt missing/stale; regenerate with --write")
    return readiness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pointer", type=Path, default=ROOT / "docs/current-run.json")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.pointer, args.template, write=args.write)
    except (KeyError, ValueError, OSError) as exc:
        print(f"Verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 2 if args.require_promote and not result["eligible_for_separate_slot_selector"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
