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

    # Published manifests include the newest small research TIFF outside downloads/.
    download_entries = []
    selection = load_json(ROOT / "docs/current-run.json") or {}
    manifest_paths = list(downloads.glob("*.json"))
    latest_pointer = selection.get("latest_review", {})
    latest_card = load_json(ROOT / latest_pointer["run_card"]) if latest_pointer.get("run_card") else None
    if latest_card and latest_card.get("published_tiff"):
        latest_tiff = (ROOT / latest_card["published_tiff"]).resolve()
        if latest_tiff.is_relative_to(ROOT / "docs"):
            manifest_paths.append(latest_tiff.with_suffix(".json"))
    for manifest_path in sorted(set(manifest_paths)):
        manifest = load_json(manifest_path) or {}
        # Sidecars may contain a basename or a repo-relative output_file.
        # Resolve only the basename next to its public sidecar, avoiding a
        # duplicated path or an escape into unrelated workspace files.
        raw_name = manifest.get("output_file") or (manifest_path.stem + ".tif")
        tif_name = Path(str(raw_name)).name
        tif_path = manifest_path.parent / tif_name
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
            "file": str(tif_path.relative_to(ROOT)),
            "present": present,
            "sha256": measured_sha or claimed_sha,
            "sha256_matches_manifest": (measured_sha == claimed_sha) if (present and claimed_sha) else None,
            "outside_convention": manifest.get("outside_convention", "unknown; inspect the sidecar"),
            "published_format_compliant": published_passed,
            "whole_raster_range_diagnostic_passed": strict_passed,
            "all_cells_finite_and_in_range": all_in_range,
            "nan_cells_anywhere": nan_cells,
            # A legacy sidecar's whole-array diagnostic is not immunity from
            # an unobserved private portal validator. Retain it as a named claim.
            "range_error_immune": None,
            "legacy_manifest_claim_range_error_immunity": bool(manifest.get("range_error_immunity", {}).get("immune_to_whole_raster_range_check"))
            if isinstance(manifest.get("range_error_immunity"), dict)
            else None,
            "organizer_acceptance_confirmed": False,
            "site_linked": (tif_name in site_html) or None,
            # Sidecars are historical records, never a current slot selector.
            "historical_manifest_recommendation": manifest.get("submission_recommendation"),
            "submission_recommendation": False,
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
    required_rows = {row["dest"]: row for row in placement if row["dest"] in required}
    hashes_ok = all(required_rows.get(name, {}).get("sha256_matches_pin") is True
                    for name in required)
    placement_ok = all(required_rows.get(name, {}).get("present") is True
                       for name in required) and hashes_ok
    prepared_local_manifest = load_json(ROOT / "data" / "processed" / "manifest.json") or {}
    data_placement = {
        "directory": str(data_dir.relative_to(ROOT)),
        "availability_scope": "This describes files present in the build worktree at generated_utc; data/raw and data/processed are Git-ignored and are not distributed by GitHub Pages.",
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

    # Current artifact is selected by one explicit evidence pointer, not a stale
    # hard-coded dated card. Re-inspect its exact TIFF without training data.
    selection = load_json(ROOT / "docs/current-run.json") or {}
    current_card = load_json(ROOT / selection.get("run_card", "docs/research/2026-10-25/run-card.json"))
    current_release = None
    current_inspection = {"verified_now": False, "error": "no current artifact pointer"}
    if selection:
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from scripts.verify_current_run import verify
            current_release = verify(ROOT / "docs/current-run.json", data_dir / "sample_submission.tif")
            current_inspection = {"verified_now": True, "error": None}
        except Exception as exc:
            # The feed records missing access instead of laundering a previously
            # green receipt into a current validation result.
            current_inspection = {"verified_now": False, "error": str(exc)}
        gates["current_research_artifact"] = {
            "evidence": selection.get("run_card"),
            "promoted": bool(current_release and current_release.get("research_verdict") == "promote"),
            "decision": current_release.get("display_status") if current_release else "blocked: current inspection unavailable",
        }
    # A stopped latest attempt is not the retained downloadable artifact. Verify
    # its receipts without pretending unavailable private bytes were reopened.
    additional_attempts = []
    for extra in selection.get("additional_stopped_attempts", []):
        row = {"lane": extra.get("lane"), "pointer": extra.get("pointer") or extra.get("run_card"), "verifier": extra.get("verifier")}
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            if extra.get("verifier") == "scripts/verify_quadrature_phase_run.py":
                from scripts.verify_quadrature_phase_run import verify as verify_qpc
                ready = verify_qpc(template=data_dir / "sample_submission.tif")
                row.update({"verified_now": True, "error": None, "decision": ready.get("reason", "duplicate-stop"),
                            "ok_to_submit": False, "research_verdict": ready["research_verdict"],
                            "gates": ready.get("gates", [])})
            elif extra.get("verifier") == "scripts/verify_pool_run.py":
                from scripts.verify_pool_run import verify as verify_pool
                ready = verify_pool()
                row.update({"verified_now": True, "error": None,
                            "decision": "POOL-1 verified negative: duplicate-stop; no TIFF published",
                            "ok_to_submit": False, "research_verdict": "negative",
                            "holdout_dti_e1": ready["holdout_dti_e1"],
                            "delta_vs_msdb_e1": ready["delta_vs_msdb_e1"],
                            "delta_vs_msdb_e2": ready["delta_vs_msdb_e2"],
                            "breaching_references": ready["breaching_references"]})
            else:
                from scripts.verify_lsm_run import verify as verify_lsm
                ready = verify_lsm(ROOT / extra["pointer"], data_dir / "sample_submission.tif")
                row.update({"verified_now": True, "error": None, "decision": ready["decision"],
                            "ok_to_submit": ready["ok_to_submit"], "research_verdict": ready["research_verdict"],
                            "gates": ready["gates"]})
        except Exception as exc:  # record missing access, never a stale green receipt
            row.update({"verified_now": False, "error": str(exc), "ok_to_submit": False})
        additional_attempts.append(row)
        gates[f"stopped_attempt_{str(extra.get('lane')).lower()}"] = {
            "evidence": extra.get("pointer") or extra.get("run_card"), "promoted": False,
            "decision": row.get("decision", "blocked: inspection unavailable")}
    additional_verified_lanes = []
    for extra in selection.get("additional_verified_lanes", []):
        row = {"lane": extra.get("lane"), "pointer": extra.get("pointer"), "verifier": extra.get("verifier")}
        try:
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from scripts.verify_current_run import verify as verify_by_pointer
            ready = verify_by_pointer(ROOT / extra["pointer"], data_dir / "sample_submission.tif")
            row.update({
                "verified_now": True,
                "error": None,
                "decision": ready.get("decision", ready.get("display_status")),
                "download_ok": ready.get("download_ok"),
                "ok_to_submit": ready.get("ok_to_submit", False),
                "research_verdict": ready.get("research_verdict"),
                "primary_file": ready.get("primary_file"),
                "companion_nan_file": ready.get("companion_nan_file"),
                "raster_sha256": ready.get("raster_sha256"),
                "gates": ready.get("gates", []),
            })
        except Exception as exc:
            row.update({"verified_now": False, "error": str(exc), "ok_to_submit": False})
        additional_verified_lanes.append(row)
        gates[f"verified_lane_{str(extra.get('lane')).lower().replace('-', '_')}"] = {
            "evidence": extra.get("pointer"),
            "promoted": bool(row.get("ok_to_submit") is True and row.get("research_verdict") == "promote"),
            "decision": row.get("decision", "blocked: inspection unavailable"),
        }
    latest_attempt = None
    if selection.get("latest_attempt"):
        latest_path = ROOT / selection["latest_attempt"]
        latest_card = load_json(latest_path)
        latest_attempt = {"run_card": selection["latest_attempt"], "card": latest_card,
                          "receipt_inspection": {"verified_now": False, "error": None},
                          "decision": None, "public_download": False}
        try:
            from scripts.verify_stopped_attempt import verify as verify_stopped
            latest_attempt["decision"] = verify_stopped(latest_path.resolve().parent, data_dir / "sample_submission.tif")
            latest_attempt["receipt_inspection"] = {"verified_now": True, "error": None,
                                                    "private_raster_reopened": False}
        except Exception as exc:
            latest_attempt["receipt_inspection"]["error"] = str(exc)
        gates["latest_scientific_attempt"] = {
            "evidence": selection["latest_attempt"], "promoted": False,
            "decision": "duplicate-stop; no public TIFF" if latest_attempt["receipt_inspection"]["verified_now"]
                        else "blocked: latest stopped-attempt inspection unavailable"}
    latest_review = None
    if selection.get("latest_review"):
        ref = selection["latest_review"]
        latest_review = {**ref, "card": load_json(ROOT / ref["run_card"]), "verified_now": False,
                         "error": None, "decision": None, "ok_to_submit": False}
        try:
            verifier = ref.get("verifier")
            if verifier == "scripts/verify_registry_preflight.py":
                from scripts.verify_registry_preflight import verify as verify_latest
            elif verifier == "scripts/verify_csr_run.py":
                from scripts.verify_csr_run import verify as verify_latest
            elif verifier == "scripts/verify_geothermal_chemistry_run.py":
                from scripts.verify_geothermal_chemistry_run import verify as verify_latest
            elif verifier == "scripts/verify_quadrature_phase_run.py":
                from scripts.verify_quadrature_phase_run import verify as verify_latest
            else:
                raise ValueError(f"unsupported latest-review verifier: {verifier}")
            decision = verify_latest(template=data_dir / "sample_submission.tif")
            latest_review.update(verified_now=True, decision=decision, ok_to_submit=bool(decision.get("ok_to_submit", False)))
        except Exception as exc:
            latest_review["error"] = str(exc)
        gates["latest_scientific_review"] = {
            "evidence": ref["run_card"], "promoted": False,
            "decision": (decision.get("display_status") or "NOT APPROVED FOR SUBMISSION")
                        if latest_review["verified_now"] else "blocked: newest review inspection unavailable"}
    promoted = [name for name, gate in gates.items() if gate.get("promoted")]
    peer_reports = []
    for name, filename in (("G30-S19 habitat + EDGE", "lane-g30s19-run-card.json"),
                           ("H-CC1 contact coincidence", "h-cc1-run-card.json"),
                           ("Residual-ridge gate", "run-card-residual-gate.json")):
        path = research / "2026-10-25" / filename
        payload = load_json(path)
        if payload:
            peer_reports.append({"lane": name, "run_card": str(path.relative_to(ROOT)),
                                 "recorded_research_verdict": payload.get("verdict"),
                                 "reassessed_by_current_lane": False, "slot_selected_here": False,
                                 "comparison_warning": "Different protocol; not ranked against the current artifact or treated as organizer confirmation"})
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
            "pins_core_sha256_verified_now": hashes_ok,
            "historical_restore_receipt": "docs/research/2026-10-25/prepared-manifest.json",
            "pins_note": core_pins.get("warning", ""),
            "extra_pins_files": [row["dest"] for row in extra_pins.get("files", [])],
        },
        "downloads": download_entries,
        "submission_format": {
            "published_outside_convention": "null/NaN outside the data bounds; finite probabilities in [0, 1] inside",
            "official_problem_description": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
            "builder_default": "Current shared writer / retained TDX1 archive: NaN nodata outside, finite [0,1] inside; no range-error-immunity claim",
            "zero_outside": (
                "Historical all-finite convention. The official reference notebook writes without an "
                "explicit nodata argument; owner-reported scores are not organizer confirmation. "
                "A whole-array range check does not prove portal acceptance or scientific readiness."
            ),
            "historical_range_error_file_identified": False,
            "historical_range_error_cause_diagnosed": False,
            "historical_range_error_cause": (
                "Unknown exact upload. Feature sentinels and feature-derived footprint masks are "
                "documented possible failure modes, not a proven diagnosis of the historical rejection."
            ),
            "range_error_root_cause_record": "docs/research/range-error-root-cause-2026-10-03.md",
            "shared_writer": "src/gemsdoe30/submission.py",
            "legacy_diagnostic_builder": "scripts/build_portal_submission.py",
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
        "current_run_pointer": selection,
        "latest_scientific_review": latest_review,
        "current_readiness_scope": "Archived retained research artifact only; latest_scientific_review is the current zero-experiment duplicate-stop preflight. Neither field selects a slot.",
        "current_readiness": current_card,
        "current_artifact_inspection": current_inspection,
        "current_release_decision": current_release,
        "latest_scientific_attempt": latest_attempt,
        "additional_stopped_attempts": additional_attempts,
        "additional_verified_lanes": additional_verified_lanes,
        "lane_g30_tad_run_card": load_json(
            research / "tilt-alteration-discontinuity" / "run-card.json"
        ),
        "legacy_readiness_2026_10_25": load_json(research / "2026-10-25" / "run-card.json"),
        "lane_g30s19_run_card": load_json(
            research / "2026-10-25" / "lane-g30s19-run-card.json"
        ),
        "lane_g30s20_run_card": load_json(
            research / "2026-10-25-s20" / "run-card.json"
        ),
        "historical_promotion_warning": "Prior results require same-protocol re-evaluation after the shared footprint correction.",
        "promotion_gates": gates,
        "any_candidate_promoted": bool(promoted),
        "promotion_scope": "Automatically adjudicated current artifact and listed legacy gates only; peer reports are separate, not re-adjudicated or selected",
        "peer_lane_reports": peer_reports,
        "any_peer_lane_reports_promotion": any(r["recorded_research_verdict"] == "promote" for r in peer_reports),
        "promoted_gates": promoted,
        "submission_slot_status": "none approved or used by this repository",
        "score_evidence": {
            "historical_leaderboard_snapshot_claims_from_ledger": ledger_rows,
            "validated_organizer_submission_receipts": [],
            "note": "Historical ledger assertions are not freshly verified or submission-page receipts. No current leaderboard scraping or score projection.",
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
