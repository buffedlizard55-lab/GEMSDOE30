#!/usr/bin/env python3
"""Re-verify the currently published research artifact and refresh its decision.

This intentionally uses only standard library, rasterio/numpy, and tracked receipts.
It does not touch portals, credentials, or training arrays.
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

from gemsdoe30.experiments import contract
from gemsdoe30.holdout import spatial_bootstrap
from gemsdoe30.readiness import assess
from gemsdoe30.submission import validate_submission_file


def local_path(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError("evidence pointer paths must be relative to the repository")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("evidence pointer resolves outside the repository")
    return resolved


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def check_equal(left, right, label: str = "summary", tol: float = 1e-12) -> None:
    if type(left) is bool or type(right) is bool:
        if left != right:
            raise ValueError(f"{label} boolean mismatch: {left!r} != {right!r}")
        return
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not (math.isfinite(left) and math.isfinite(right) and abs(left - right) <= tol):
            raise ValueError(f"{label} numeric mismatch: {left!r} != {right!r}")
        return
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            raise ValueError(f"{label} length mismatch")
        for idx, (a, b) in enumerate(zip(left, right)):
            check_equal(a, b, f"{label}[{idx}]", tol)
        return
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise ValueError(f"{label} keys mismatch: {sorted(left)} != {sorted(right)}")
        for key in left:
            check_equal(left[key], right[key], f"{label}.{key}", tol)
        return
    if left != right:
        raise ValueError(f"{label} value mismatch: {left!r} != {right!r}")


def verify(pointer: Path, template: Path, *, write=False):
    selection = load(pointer)
    # Lane-specific verifiers are selected by the pointer, never by a human flag.
    if selection.get("verifier") == "scripts/verify_lsm_run.py":
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.verify_lsm_run import verify as verify_lsm
        return verify_lsm(pointer, template, write=write)
    if selection.get("verifier") == "scripts/verify_nearsplay_run.py":
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.verify_nearsplay_run import verify as verify_nearsplay
        return verify_nearsplay(pointer, template, write=write)
    card_path = local_path(selection["run_card"])
    directory = card_path.parent
    card = load(card_path)
    spec = contract(card)
    candidate = spec["candidate"]
    results = load(directory / "results.json")
    default_spec = spec["id"] if spec["id"] == "ms_cape" else "tdx1"
    if results.get("experiment_spec", default_spec) != spec["id"]:
        raise ValueError("card/results experiment contract mismatch")
    raster = local_path(card["published_tiff"])
    with raster.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    hashes_match = digest == card["raster_sha256"]
    manifest = load(raster.with_suffix(".json"))
    sidecar_hash = manifest.get("sha256") or manifest.get("output_sha256")
    hashes_match &= sidecar_hash == digest
    if not hashes_match:
        raise ValueError("published TIFF SHA-256 does not match card and download sidecar")
    report = validate_submission_file(raster, template)
    if not report.passed:
        raise ValueError("published TIFF fails the shared format validator")
    zeros_digest_set: set[str] = set()
    if card.get("portal_zeros_tiff"):
        zeros_raster = local_path(card["portal_zeros_tiff"])
        with zeros_raster.open("rb") as stream:
            zdigest = hashlib.file_digest(stream, "sha256").hexdigest()
        zmanifest = load(zeros_raster.with_suffix(".json"))
        zsidecar_hash = zmanifest.get("sha256") or zmanifest.get("output_sha256")
        if zdigest != card.get("portal_zeros_sha256") or zsidecar_hash != zdigest:
            raise ValueError("portal-zeros TIFF SHA-256 does not match card and sidecar")
        zreport = validate_submission_file(zeros_raster, template, require_finite_all_cells=True)
        if not zreport.passed:
            raise ValueError("portal-zeros TIFF fails whole-array [0,1] validator")
        if zmanifest.get("submission_approved") is not False:
            raise ValueError("portal-zeros sidecar must not grant a competition slot")
        zeros_digest_set.add(zdigest)
    recomputed = spatial_bootstrap(
        results["bootstrap_sufficient_statistics"],
        candidate=candidate,
        replicates=2000,
        seed=3071,
    )
    check_equal(results["summary"], recomputed, "results/summary")
    h = card["holdout"]
    card_summary = {key: h[key] for key in ("evaluator_version", "protocol_version", "bootstrap", "candidate_minus")}
    card_summary["arms"] = {
        candidate: {key: h[key] for key in recomputed["arms"][candidate]},
        **h["comparators"],
    }
    check_equal(card_summary, recomputed, "card/holdout")
    preregistration = hashlib.sha256((directory / "preregistration.md").read_bytes()).hexdigest()
    started = load(directory / "started.json")
    if any(row.get("preregistration_sha256") != preregistration for row in (card, results, started)):
        raise ValueError("frozen preregistration hash differs between plan/start/results/card")
    prereg_json_path = directory / "preregistration.json"
    if prereg_json_path.is_file():
        prereg_json_hash = hashlib.sha256(prereg_json_path.read_bytes()).hexdigest()
        for row in (card, results, started):
            if "preregistration_json_sha256" in row and row["preregistration_json_sha256"] != prereg_json_hash:
                raise ValueError("frozen preregistration.json hash differs between plan/start/results/card")
    if results.get("raster_sha256") != digest:
        raise ValueError("holdout results do not bind to the published TIFF")
    features = load(directory / "feature-receipt.json")
    cache = load(directory / "cache-verification.json")
    transform_hash = hashlib.sha256((ROOT / spec["transform_path"]).read_bytes()).hexdigest()
    expected_guard = spec.get("guard_px", spec["support_px"])
    if (features["signature"]["transform_code_sha256"] != transform_hash
            or features["signature"]["transform_version"] != spec["transform_version"]
            or features.get("support_px") != spec["support_px"]
            or card.get("physical_support_px") != spec["support_px"]
            or any(fold.get("buffer_px") != expected_guard for fold in results["folds"])):
        raise ValueError("transform identity or physical-support/training guard mismatch")
    if "parent_transform_path" in spec:
        parent_hash = hashlib.sha256((ROOT / spec["parent_transform_path"]).read_bytes()).hexdigest()
        if (features["signature"].get("parent_transform_code_sha256") != parent_hash
                or features["signature"].get("parent_transform_version") != spec["parent_transform_version"]):
            raise ValueError("parent transform identity mismatch")
    if (cache.get("all_cells_match_raw_sources") is not True
            or cache.get("dataset_signature") != card.get("dataset_signature")
            or features["signature"].get("dataset_signature") != card.get("dataset_signature")):
        raise ValueError("full-cell prepared-cache verification is missing or for another dataset")
    if started.get("experiment_count") != card.get("experiments_run"):
        raise ValueError("execution budget count differs between start receipt and card")
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
        expected_summary = {
            "decision": audit["decision"], "registry_entries_compared": len(rows),
            "max_spearman": max((row["spearman_full_footprint"] for row in rows
                                  if row.get("spearman_full_footprint") is not None), default=None),
            "max_fraction_within_3px": max((row["candidate_fraction_within_3px_of_reference"] for row in rows
                                            if row.get("candidate_fraction_within_3px_of_reference") is not None), default=None),
            "errors": audit["errors"],
        }
        check_equal(card["registry"][stage], expected_summary, f"card/registry/{stage}")
    known = expected_registry | {row["sha256"] for row in registry.get("exclusions", [])} | {digest} | zeros_digest_set
    extra_hashes = set()
    for path in raster.parent.iterdir():
        if path.suffix.lower() not in (".tif", ".tiff"):
            continue
        with path.open("rb") as stream:
            value = hashlib.file_digest(stream, "sha256").hexdigest()
        if value not in known:
            extra_hashes.add(value)
    combined_surface, combined_dots = surface, dots
    assessment_registry = registry
    additional_path = directory / "registry-parallel-addendum.json"
    if extra_hashes or additional_path.exists():
        if not additional_path.is_file():
            raise ValueError("new local reference TIFFs require an explicit late-registry audit")
        additional = load(additional_path)
        extra_rows = additional["rasters"]
        expected_extra = {row["sha256"] for row in extra_rows}
        if expected_extra != extra_hashes or len(extra_rows) != len(expected_extra):
            raise ValueError("late registry no longer covers every new local reference identity")
        parent_hash = hashlib.sha256((directory / "registry.json").read_bytes()).hexdigest()
        if additional.get("original_registry_sha256") != parent_hash:
            raise ValueError("late registry does not extend this exact frozen snapshot")
        for row in extra_rows:
            with local_path(row["path"]).open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError("late reference file hash mismatch")
        merged = {}
        for stage, original in (("surface", surface), ("dots", dots)):
            late = load(directory / f"novelty-parallel-{stage}.json")
            rows = late["comparisons"]
            if (late.get("stage") != stage or any(r.get("stage") != stage for r in rows)
                    or len(rows) != len(expected_extra)
                    or {r.get("reference_sha256") for r in rows} != expected_extra
                    or late.get("registry_sha256") != hashlib.sha256(additional_path.read_bytes()).hexdigest()
                    or late.get("template_sha256") != template_hash
                    or late.get("candidate_sha256") != original.get("candidate_sha256")
                    or late.get("registry_complete") != bool(additional.get("complete"))):
                raise ValueError("late novelty receipt stage/inventory/identity mismatch")
            merged[stage] = {**original, "comparisons": original["comparisons"] + rows,
                             "errors": original.get("errors", []) + late.get("errors", [])}
        combined_surface, combined_dots = merged["surface"], merged["dots"]
        if additional.get("complete") is not True or additional.get("missing_evidence"):
            assessment_registry = {**registry, "complete": False,
                                   "missing_evidence": additional.get("missing_evidence", ["late coverage incomplete"])}
    readiness = assess(card, results, format_passed=report.passed, hash_matches=hashes_match,
                       surface_audit=combined_surface, dots_audit=combined_dots, registry=assessment_registry)
    if additional_path.exists():
        addition = {"registry": str((directory / "registry-parallel-addendum.json").relative_to(ROOT)),
                    "surface_receipt": str((directory / "novelty-parallel-surface.json").relative_to(ROOT)),
                    "dots_receipt": str((directory / "novelty-parallel-dots.json").relative_to(ROOT)),
                    "timing": "Late-arriving references; checked both saved states without refitting or replacing dots",
                    "combined_observed_registry": readiness["observed_registry"]}
        if write:
            card["additional_novelty_evidence"] = addition
        else:
            check_equal(card.get("additional_novelty_evidence"), addition, "card/additional_novelty_evidence")
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
        if additional_path.exists():
            temp = card_path.with_suffix(".partial.json")
            temp.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
            temp.replace(card_path)
        temp = target.with_suffix(".partial.json")
        temp.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
        temp.replace(target)
    elif not target.exists() or load(target) != readiness:
        raise ValueError("readiness receipt missing/stale; regenerate with --write")
    return readiness


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pointer", type=Path, default=ROOT / "docs/current-run.json")
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--write", action="store_true", help="refresh readiness.json from current evidence")
    parser.add_argument("--require-promote", action="store_true",
                        help="exit 2 unless the research verdict is promote")
    args = parser.parse_args()
    try:
        readiness = verify(args.pointer, args.template, write=args.write)
    except (ValueError, KeyError, OSError) as exc:
        print(f"Verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(readiness, indent=2))
    if args.require_promote and readiness["research_verdict"] != "promote":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
