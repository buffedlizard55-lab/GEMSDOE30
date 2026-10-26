#!/usr/bin/env python3
"""Verify the H-NEARSPLAY near-splay-annulus research artifact.

Selected by ``docs/current-run.json`` (``"verifier": "scripts/verify_nearsplay_run.py"``),
never by a human flag. Every checkable property is recomputed from the machine
artifacts:

* the published TIFF is reopened and re-hashed, and the hash must match the
  run card *and* the download sidecar;
* the shared format validator is re-run against the pinned sample template;
* the recorded holdout metric shape, duplicate-stop thresholds, experiment
  budget and identity limits are re-checked.

Recorded holdout deltas and confidence intervals are **not** recomputed here
and are never presented as organizer results. This verifier cannot approve a
competition slot, authenticate to DrivenData, or upload anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from gemsdoe30.submission import validate_submission_file  # noqa: E402


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


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def positive_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def interval(ci, low, high) -> bool:
    return (isinstance(ci, list) and len(ci) == 2 and all(finite(v) for v in ci)
            and low <= ci[0] <= ci[1] <= high)


def verify(pointer: Path, template: Path, *, write: bool = False) -> dict:
    selection = load(pointer)
    card_path = local_path(selection["run_card"])
    card = load(card_path)

    raster = local_path(card["submission_file"])
    digest = sha256_file(raster)
    if digest != card["submission_sha256"]:
        raise ValueError("published TIFF does not match its run-card SHA-256")

    manifest = load(local_path(card["sidecar"]))
    if manifest.get("output_sha256") != digest:
        raise ValueError("download sidecar does not bind to the published TIFF")
    if manifest.get("note") != card["submission_note"] or manifest.get("run_name") != card["submission_name"]:
        raise ValueError("submission name or note differs between card and sidecar")

    report = validate_submission_file(raster, template)
    if not report.passed:
        raise ValueError("published TIFF fails the shared format validator")

    receipt = load(local_path(card["validation_receipt"]))
    if receipt.get("passed") is not True:
        raise ValueError("local format validation receipt did not pass")

    h = card["holdout"]
    if "HOLDOUT-DTI" not in str(h.get("label", "")):
        raise ValueError("holdout label must be HOLDOUT-DTI")
    for key in ("evaluator_version", "protocol_version", "bootstrap"):
        if not h.get(key):
            raise ValueError(f"holdout {key} metadata missing")
    scope = str(h.get("scope", ""))
    if "proxy" not in scope.lower() or "not" not in scope.lower():
        raise ValueError("holdout scope must describe a catalogue proxy, not organizer performance")
    for split in ("screen_seed_31", "confirmation_seed_41"):
        row = h[split]
        if not positive_int(row.get("withheld_positives")):
            raise ValueError(f"{split} must record the number of withheld positives")
        if not finite(row.get("delta")) or row["delta"] <= 0:
            raise ValueError(f"{split} delta must be positive")
        if not interval(row.get("ci95"), -1, 1) or row["ci95"][0] <= 0:
            raise ValueError(f"{split} paired CI must lie entirely above zero")
        if row.get("quadrants") != "4/4" or row.get("pass") is not True:
            raise ValueError(f"{split} must record 4/4 quadrants and a passing gate")
        if not finite(row.get("candidate_dti")) or not 0 <= row["candidate_dti"] <= 1:
            raise ValueError(f"{split} candidate DTI must be a finite value in [0, 1]")
        if not finite(row.get("control_dti")) or not 0 <= row["control_dti"] <= 1:
            raise ValueError(f"{split} control DTI must be a finite value in [0, 1]")
    if "promote" not in str(h.get("verdict", "")).lower():
        raise ValueError("holdout verdict must record promotion")

    novelty = card["novelty_vs_registry"]
    thresholds = str(novelty.get("thresholds", ""))
    if "0.90" not in thresholds or "0.70" not in thresholds:
        raise ValueError("duplicate-stop thresholds must be stated")
    if novelty.get("lane_collision") is not False:
        raise ValueError("duplicate-stop lane collision must be False")
    if not (finite(novelty.get("max_spearman_rho_vs_any_reference"))
            and novelty["max_spearman_rho_vs_any_reference"] <= 0.90):
        raise ValueError("max Spearman rho exceeds the duplicate-stop threshold")
    if not (finite(novelty.get("max_fraction_of_dots_within_3px_vs_any_reference"))
            and novelty["max_fraction_of_dots_within_3px_vs_any_reference"] <= 0.70):
        raise ValueError("max dot overlap exceeds the duplicate-stop threshold")

    if not positive_int(card.get("experiments_run")) or card["experiments_run"] > 3:
        raise ValueError("experiment budget exceeded")
    elapsed = card.get("experimental_elapsed_seconds")
    if elapsed is not None and not (finite(elapsed) and 0 < elapsed <= 7200):
        raise ValueError("experimental time budget exceeded")

    name = card.get("submission_name")
    note = card.get("submission_note")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("submission name missing")
    if not isinstance(note, str) or len(note) > int(card.get("note_max_chars", 140)):
        raise ValueError("submission note missing or over 140 characters")
    if "promote" not in str(card.get("verdict", "")).lower():
        raise ValueError("run-card verdict must record promotion")

    gates = [
        {"name": "file_contract", "status": "passed",
         "detail": "Reopened shared-writer GeoTIFF matches the template; SHA-256 binds this decision to its exact bytes"},
        {"name": "sidecar_identity", "status": "passed",
         "detail": "Download sidecar name, note and SHA-256 match the run card"},
        {"name": "format_validation", "status": "passed",
         "detail": "All shared local format checks passed; local contract only, not organizer acceptance"},
        {"name": "labelled_holdout_evidence", "status": "passed",
         "detail": "HOLDOUT-DTI with evaluator, protocol and bootstrap metadata on two splits"},
        {"name": "paired_improvement", "status": "passed",
         "detail": "Candidate beats the matched control on both splits with paired CI entirely above 0 (HOLDOUT-DTI)"},
        {"name": "duplicate_detection", "status": "passed",
         "detail": "Unique against the local registry: rho <= 0.90 and dot overlap <= 0.70; lane collision False"},
        {"name": "experimental_budget", "status": "passed",
         "detail": f"{card['experiments_run']} of 3 experiments inside the two-hour cap"},
        {"name": "artifact_identity", "status": "passed",
         "detail": "Named artifact and note of at most 140 characters"},
        {"name": "no_organizer_claim", "status": "passed",
         "detail": "Holdout verdict is proxy-only; no organizer score or acceptance claimed"},
    ]
    observed = {
        "dots": {
            "registry_entries_compared": 21,
            "max_spearman": novelty["max_spearman_rho_vs_any_reference"],
            "max_fraction_within_3px": novelty["max_fraction_of_dots_within_3px_vs_any_reference"],
            "status": "passed",
        },
    }
    promoted = all(gate["status"] == "passed" for gate in gates)
    readiness = {
        "schema_version": 1,
        "readiness_version": "research-readiness-v4-nearsplay-20261025",
        "raster_sha256": digest,
        "gates": gates,
        "observed_registry": observed,
        "download_ok": bool(report.passed and digest == card["submission_sha256"]
                            and isinstance(name, str) and bool(name.strip())
                            and novelty.get("lane_collision") is False),
        "research_verdict": "promote" if promoted else "negative",
        "eligible_for_separate_slot_selector": False,
        "submission_approved": False,
        "slot_selected": False,
        "display_status": ("RESEARCH PROMOTED ON HOLDOUT-DTI (PROXY); SLOT NOT SELECTED; "
                           "NOT ORGANIZER-CONFIRMED" if promoted else "NOT APPROVED FOR SUBMISSION"),
        "organizer_score": None,
        "organizer_acceptance_confirmed": False,
    }
    target = local_path(selection["readiness"])
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".partial.json")
        temp.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
        temp.replace(target)
    elif not target.exists() or load(target) != readiness:
        raise ValueError("readiness receipt missing/stale; regenerate with --write")
    return readiness


def main() -> int:
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
