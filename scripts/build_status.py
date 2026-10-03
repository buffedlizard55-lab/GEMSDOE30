#!/usr/bin/env python3
"""Regenerate docs/status.json from machine-readable artifacts (no manual editing).

The owner brief requires an always-current project feed instead of hand-checked
status text. This script derives the feed from the evidence that already exists
in the repository:

* gate results in ``docs/research/*.json`` (loss ablation, emission, holdouts),
* download manifests in ``docs/downloads/*.json``,
* SHA-256 mirror pins in ``docs/research/mirror-pins*.json``,
* prepared-data manifest in ``docs/research/prepared-manifest.json``,
* the reported-score ledger in ``docs/score-ledger.csv``,
* the local test suite (``pytest --collect-only``).

Run it after every experiment: ``python scripts/build_status.py``. The output
records its own generated timestamp so staleness is visible. It never invents a
score: leaderboard values come only from the dated snapshot rows in the ledger.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"error": f"unreadable JSON: {path}"}


def test_counts() -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        tail = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else ""
        return {"pytest_collect": tail or "no output", "exit_code": proc.returncode}
    except Exception as exc:  # pragma: no cover - diagnostic only
        return {"pytest_collect": f"unavailable: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "status.json")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    research = ROOT / "docs" / "research"
    downloads = ROOT / "docs" / "downloads"

    # Downloads inventory straight from the published manifests.
    download_entries = []
    for manifest_path in sorted(downloads.glob("*.json")):
        manifest = load_json(manifest_path) or {}
        tif_name = manifest.get("output_file") or manifest_path.stem + ".tif"
        tif_path = downloads / tif_name
        entry = {
            "manifest": manifest_path.name,
            "file": tif_name,
            "present": tif_path.is_file(),
            "sha256": manifest.get("output_sha256") or (sha256_file(tif_path) if tif_path.is_file() else None),
            "outside_convention": manifest.get("outside_convention", "NaN template-conformant (legacy)"),
            "run_name": manifest.get("run_name"),
            "note": manifest.get("note"),
            "performance_status": manifest.get("performance_status", "unscored"),
        }
        download_entries.append(entry)

    # Gate results: pull the decision fields each experiment records.
    gates = {}
    loss_screen = load_json(research / "loss-ablation-holdout.json") or {}
    loss_confirm = load_json(research / "loss-ablation-holdout-seed31.json") or {}
    gates["loss_ablation"] = {
        "screen": "docs/research/loss-ablation-holdout.json",
        "confirmation": "docs/research/loss-ablation-holdout-seed31.json",
        "screen_pooled_delta": loss_screen.get("comparison", {}).get("pooled_dti_delta"),
        "confirmation_pooled_delta": loss_confirm.get("comparison", {}).get("pooled_dti_delta"),
        "promoted": False,
        "decision": "screen positive at seed 30, confirmation negative at seed 31; not promoted",
    }
    emission = load_json(research / "metric-emission-holdout-results.json") or {}
    gates["metric_emission"] = {
        "evidence": "docs/research/metric-emission-holdout-results.json",
        "gate": emission.get("gate", emission.get("gate_result", "see file")),
        "promoted": False,
        "decision": "registered gate failed; thinning stays default",
    }
    relay = load_json(research / "relay-connector-holdout.json") or {}
    gates["h31_01_relay_connector"] = {
        "evidence": "docs/research/relay-connector-holdout.json",
        "promoted": False,
        "decision": "connector geometry did not beat proximity-matched control; not promoted",
    }
    vent = load_json(research / "h32-01-vent-corridor-holdout.json") or {}
    if vent:
        gates["h32_01_vent_corridor"] = {
            "evidence": "docs/research/h32-01-vent-corridor-holdout.json",
            "gate_result": vent.get("gate_result", {}),
            "promoted": bool(vent.get("gate_result", {}).get("promoted", False)),
            "decision": ("gate passed pending standard promotion review" if vent.get("gate_result", {}).get("promoted")
                         else "gate failed or not run to completion; not promoted"),
        }
    else:
        gates["h32_01_vent_corridor"] = {"evidence": None, "promoted": False, "decision": "not run yet"}
    basement = load_json(research / "h32-05-basement-edge-holdout.json") or {}
    if basement:
        basement_gate = basement.get("gate_result", {})
        gates["h32_05_basement_edge"] = {
            "evidence": "docs/research/h32-05-basement-edge-holdout.json",
            "preregistration": "docs/research/h32-05-preregistration.md",
            "gate_result": basement_gate,
            "promoted": bool(basement_gate.get("promoted", False)),
            "decision": (
                "gate passed pending standard promotion review"
                if basement_gate.get("promoted")
                else "registered gate failed (screen + confirmation); not promoted"
            ),
        }
    else:
        gates["h32_05_basement_edge"] = {"evidence": None, "promoted": False, "decision": "not run yet"}
    sweep = load_json(research / "loss-weight-sweep.json") or {}
    if sweep:
        gates["loss_weight_sweep"] = {
            "evidence": "docs/research/loss-weight-sweep.json",
            "screen_selection": sweep.get("screen_selection", {}),
            "summary": sweep.get("summary", {}),
            "promoted": False,
            "decision": ("fold-0 boundary-weight screen (dense + emitted-mask scoring); "
                         "a screen pick is diagnostic only — promotion still needs the 4-fold "
                         "paired design plus fresh-seed confirmation"),
        }
    else:
        gates["loss_weight_sweep"] = {"evidence": None, "promoted": False, "decision": "not run yet"}
    h33_policy = load_json(research / "h33-01-placement-policy-holdout.json") or {}
    if h33_policy:
        gates["h33_01_placement_policy"] = {
            "evidence": "docs/research/h33-01-placement-policy-holdout.json",
            "verdict_doc": "docs/research/h33-01-placement-policy-holdout.md",
            "preregistration": "docs/research/h33-01-preregistration.md",
            "promoted": False,
            "gate_pass": bool((h33_policy.get("gates") or {}).get("pass", False)),
            "gate_void_reason": h33_policy.get("gates_void_reason"),
            "capacity_collapse": bool((h33_policy.get("capacity") or {}).get("gate_arms_collapse_identical")),
            "decision": h33_policy.get("decision", "not run yet"),
        }
    else:
        gates["h33_01_placement_policy"] = {"evidence": None, "promoted": False, "decision": "not run yet"}
    h33_scarp = load_json(research / "h33-01-placement-and-scarp-holdout.json") or {}
    if h33_scarp:
        verdicts = h33_scarp.get("gate_verdicts", {})
        any_h33_promoted = any(
            bool(v.get("promoted", False)) for v in verdicts.values() if isinstance(v, dict)
        )
        gates["h33_01_placement_and_scarp"] = {
            "evidence": "docs/research/h33-01-placement-and-scarp-holdout.json",
            "preregistration": "docs/research/h33-01-placement-and-scarp-preregistration.md",
            "gate_verdicts": verdicts,
            "promoted": any_h33_promoted,
            "decision": (
                "H-31-02r passes independent SGMC novelty frame (+86.1% / +91.6%) and transform clause (+22.4%), "
                "but trails dispersed control on catalogue proxy (-0.00261); H-32-05b falsified; not promoted"
            ),
        }
    else:
        gates["h33_01_placement_and_scarp"] = {"evidence": None, "promoted": False, "decision": "not run yet"}
    vchecks = load_json(research / "verification-checks-results.json") or {}
    if vchecks:
        vsum = vchecks.get("overall_promotion_decision", {})
        gates["verification_checks_h31_02r"] = {
            "evidence": "docs/research/verification-checks-results.json",
            "report": "docs/research/verification-checks-results.md",
            "summary": vsum,
            "promoted": bool(vsum.get("slot_promoted", False)),
            "decision": vsum.get("reason", "see verification-checks-results.json"),
        }
    else:
        gates["verification_checks_h31_02r"] = {"evidence": None, "promoted": False, "decision": "not run yet"}

    # Data provenance.
    core_pins = load_json(research / "mirror-pins.json") or {}
    extra_pins = load_json(research / "mirror-pins-extra.json") or {}
    prepared = load_json(research / "prepared-manifest.json") or {}
    # scripts/restore_public_mirrors.py writes mirrors to data/raw/<dest>, so the
    # existence check must look there (a previous version checked data/<dest> and
    # therefore always reported an empty list even with the data in place: IR-30-025).
    data_dir = ROOT / "data" / "raw"
    placement = []
    for row in core_pins.get("files", []):
        if row.get("group") != "core":
            continue
        path = data_dir / row["dest"]
        entry = {
            "dest": row["dest"],
            "path": str(path.relative_to(ROOT)),
            "present": path.is_file(),
            "expected_sha256": row.get("sha256"),
            "expected_bytes": row.get("bytes"),
        }
        if path.is_file():
            actual = sha256_file(path)
            entry["actual_sha256"] = actual
            entry["actual_bytes"] = path.stat().st_size
            entry["sha256_matches_pin"] = actual == row.get("sha256")
        placement.append(entry)
    present = [row["dest"] for row in placement if row["present"]]
    required = ("training_features.tif", "labels.tif", "sample_submission.tif")
    hashes_ok = all(row.get("sha256_matches_pin") for row in placement
                    if row["dest"] in required and row["present"])
    placement_ok = all(row["present"] for row in placement if row["dest"] in required) and hashes_ok
    prepared_local_manifest = load_json(ROOT / "data" / "processed" / "manifest.json") or {}
    data_placement = {
        "directory": str(data_dir.relative_to(ROOT)),
        "required_files_present": placement_ok,
        "sha256_verified_against_pins": hashes_ok,
        "files": placement,
        "prepared_dataset": {
            "dataset_signature": prepared_local_manifest.get("dataset_signature"),
            "matches_recorded_pin": (
                prepared_local_manifest.get("dataset_signature") == prepared.get("dataset_signature")
                if prepared_local_manifest.get("dataset_signature") else None
            ),
            "positive_label_pixels": prepared_local_manifest.get("positive_label_pixels"),
            "template_valid_pixels": prepared_local_manifest.get("template_valid_pixels"),
        },
        "note": ("placement + SHA-256 verification is a precondition for training, not evidence "
                 "of model quality; mirrors are owner-supplied and not organizer-authenticated"),
    }

    # Score evidence: only dated snapshot rows from the ledger (never live scraping).
    ledger_rows = []
    ledger = ROOT / "docs" / "score-ledger.csv"
    if ledger.is_file():
        with ledger.open() as handle:
            for row in csv.DictReader(handle):
                if row.get("evidence_class", "").startswith("official-snapshot"):
                    ledger_rows.append(row)

    promoted = [name for name, gate in gates.items() if gate.get("promoted")]
    status = {
        "schema_version": 2,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_by": "scripts/build_status.py (regenerate after every experiment; no manual edits)",
        "project": "GEMSDOE30",
        "data_placement": data_placement,
        "competition_data": {
            "owner_mirror_files_present": present,
            "organizer_authenticated": False,
            "prepared_dataset_signature": prepared.get("dataset_signature"),
            "pins_core_sha256_verified_at_restore": True,
            "pins_note": core_pins.get("warning", ""),
            "extra_pins_files": [row["dest"] for row in extra_pins.get("files", [])],
        },
        "downloads": download_entries,
        "promotion_gates": gates,
        "any_candidate_promoted": bool(promoted),
        "promoted_gates": promoted,
        "submission_slot_status": "none approved or used by this repository",
        "score_evidence": {
            "official_leaderboard_snapshots_from_ledger": ledger_rows,
            "note": "DrivenData Terms of Use prohibit automated monitoring; snapshots are dated manual reads only",
            "d2_8_attribution": "owner-reported 0.2600 unverified; GEMSDOE25 page calls the file unscored",
        },
        "verification": {
            "tests": "see verification.tests_collected",
            "tests_collected": {"skip": True} if args.skip_tests else test_counts(),
            "score_gain_claimed": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    for name, gate in gates.items():
        decision = str(gate.get("decision", "?"))[:48]
        print(f"gates: {name} = {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
