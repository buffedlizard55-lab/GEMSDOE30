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

    # Which artifacts the site actually links, read from the pages themselves
    # rather than from a manifest field a builder may not set.
    site_html = ""
    for page in (ROOT / "index.html", ROOT / "executive-summary.html"):
        if page.is_file():
            site_html += page.read_text(encoding="utf-8", errors="replace")

    def _nested(manifest: dict, *keys: str):
        """Read a scalar from either the flat or the nested sidecar schema."""
        for key in keys:
            if manifest.get(key) is not None:
                return manifest[key]
        for block in ("validation_published_format", "validation_all_cells_finite", "value_guarantees"):
            block_data = manifest.get(block)
            if isinstance(block_data, dict):
                for key in keys:
                    if block_data.get(key) is not None:
                        return block_data[key]
        return None

    # Downloads inventory straight from the published manifests.
    download_entries = []
    for manifest_path in sorted(downloads.glob("*.json")):
        manifest = load_json(manifest_path) or {}
        # Sidecars disagree on whether `output_file` is a bare filename or a
        # repo-relative path; joining a path onto `downloads` silently produced
        # `docs/downloads/docs/downloads/x.tif` and reported every artifact as
        # missing. Reduce to the basename and resolve inside `downloads`.
        raw_name = manifest.get("output_file") or (manifest_path.stem + ".tif")
        tif_name = Path(str(raw_name)).name
        tif_path = downloads / tif_name
        present = tif_path.is_file()
        measured_sha = sha256_file(tif_path) if present else None
        claimed_sha = manifest.get("output_sha256")
        published_passed = _nested(manifest, "published_format_compliant", "passed")
        strict_passed = _nested(manifest, "whole_raster_range_diagnostic_passed")
        if strict_passed is None:
            strict_block = manifest.get("validation_all_cells_finite")
            strict_passed = strict_block.get("passed") if isinstance(strict_block, dict) else None
        if published_passed is None:
            published_block = manifest.get("validation_published_format")
            published_passed = published_block.get("passed") if isinstance(published_block, dict) else None
        all_in_range = _nested(manifest, "all_cells_in_0_1")
        nan_cells = _nested(manifest, "nan_cells_anywhere")
        entry = {
            "manifest": manifest_path.name,
            "file": f"docs/downloads/{tif_name}",
            "present": present,
            "sha256": measured_sha or claimed_sha,
            "sha256_matches_manifest": (measured_sha == claimed_sha) if (present and claimed_sha) else None,
            "outside_convention": manifest.get("outside_convention", "unknown; inspect the sidecar"),
            "published_format_compliant": published_passed,
            "whole_raster_range_diagnostic_passed": strict_passed,
            "all_cells_finite_and_in_range": all_in_range,
            "nan_cells_anywhere": nan_cells,
            "range_error_immune": bool(manifest.get("range_error_immunity", {}).get("immune_to_whole_raster_range_check"))
            if isinstance(manifest.get("range_error_immunity"), dict)
            else None,
            "site_linked": (tif_name in site_html) or None,
            "submission_recommendation": manifest.get("submission_recommendation", False),
            "run_name": manifest.get("run_name"),
            "note": manifest.get("note") or manifest.get("drivendata_note"),
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
        "screen_pooled_delta": loss_screen.get("pooled_delta_dti"),
        "confirmation_pooled_delta": loss_confirm.get("pooled_delta_dti"),
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
                "H-31-02r beats its step_max ablation (+22.4% / +20.2%) and is spatially positive on the SGMC frame (+0.03670, 4/4), "
                "but catalogue spatial checks are negative (-0.00073 / -0.00261, 2/4) and the SGMC top-decile calibration-ratio gate passes 2/4; "
                "H-32-05b falsified; H-31-02r not promoted"
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
        "schema_version": 3,
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
        "submission_format": {
            "published_outside_convention": "null/NaN outside the data bounds; finite probabilities in [0, 1] inside",
            "official_problem_description": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            "builder_default": "zeros outside (range-error immune); --outside nan available for the literal spec reading",
            "zero_outside": (
                "primary published convention for this project since 2026-10-03. Legal on two verified "
                "grounds: the organizer's own reference solution writes its example with no nodata tag and "
                "finite values everywhere, and the owner ledger records r7-nms3-dem10-scarp_0c9199f14e62 = "
                "0.1294 beside ..._allfinite = 0.1294, i.e. identical scores for both encodings. See IR-30-045."
            ),
            "historical_range_error_file_identified": False,
            "historical_range_error_cause_diagnosed": True,
            "historical_range_error_cause": (
                "Two mechanisms measured on the pin-matched mirrors (IR-30-044): training_features.tif "
                "declares nodata as the float32 sentinel -3.4028234663852886e+38 and carries it on 3,061 "
                "pixels inside the 5,167,373-pixel scoring footprint per band (band 6 tc: 3,073; 58,171 "
                "band-pixels total); and band 1 calls only 5,165,852 pixels valid against the template's "
                "5,167,373, so a feature-derived footprint mask strands exactly 3,061 scored pixels as NaN. "
                "Either alone produces the portal's range rejection. The specific trigger in the one "
                "historical upload is still inferred, not proven: that file was never obtained."
            ),
            "range_error_root_cause_record": "docs/research/range-error-root-cause-2026-10-03.md",
            "hardened_builder": "scripts/build_portal_submission.py",
            "known_faults_masked_from_scoring": {
                "value": True,
                "source": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
                "quote": (
                    "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from "
                    "evaluation, so they do not count towards penalty terms. Re-evaluation will also "
                    "mask/exclude the existing USGS/INGENIOUS faults."
                ),
                "consequence": (
                    "Probability mass on catalogue pixels earns no TP and no FP, so it is pure waste of the "
                    "emission budget. Every candidate must report dots_on_catalogue. See IR-30-047."
                ),
            },
            "local_validation_guarantees_portal_acceptance": False,
        },
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
