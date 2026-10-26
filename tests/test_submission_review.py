from scripts.review_submission_readiness import ARTIFACTS, adjudicate, apply_expanded_registry_audit
import json
from pathlib import Path
import pytest


def test_current_run_artifact_is_in_format_review_inventory():
    root = Path(__file__).resolve().parents[1]
    current = json.loads((root / "docs/current-run.json").read_text())
    selected = root / current["run_card"]
    published = json.loads(selected.read_text())["published_tiff"]
    assert any(raster == published and hash_key == "raster_sha256"
               for _, _, _, raster, hash_key in ARTIFACTS)


def test_late_duplicate_stop_overrides_older_positive_readiness():
    row = adjudicate(format_passed=True, hash_matches=True,
                     readiness={"research_verdict": "promote", "gates": []})
    row["sha256"] = "candidate"
    result = apply_expanded_registry_audit(row, {
        "candidate_sha256": "candidate", "registry_entries_compared": 196,
        "max_fraction_within_3px": 0.7126,
        "duplicate_threshold_fraction_within_3px": 0.70,
        "exceeds_duplicate_threshold": True,
        "decision": "duplicate_on_expanded_registry",
    })
    assert result["effective_research_verdict"] == "negative"
    assert result["recorded_failed_or_unknown_gates"]["expanded_registry_dot_novelty"] == "failed"
    assert result["decision"] == "DO NOT SUBMIT: expanded-registry duplicate stop"


def test_expanded_duplicate_receipt_must_match_candidate_bytes():
    row = {"sha256": "candidate", "recorded_failed_or_unknown_gates": {}}
    with pytest.raises(ValueError, match="does not bind"):
        apply_expanded_registry_audit(row, {"candidate_sha256": "other"})


def test_expanded_duplicate_flag_must_match_numeric_threshold():
    row = {"sha256": "candidate", "recorded_failed_or_unknown_gates": {}}
    with pytest.raises(ValueError, match="contradicts"):
        apply_expanded_registry_audit(row, {
            "candidate_sha256": "candidate", "registry_entries_compared": 1,
            "max_fraction_within_3px": 0.5,
            "duplicate_threshold_fraction_within_3px": 0.7,
            "exceeds_duplicate_threshold": True,
            "decision": "duplicate_on_expanded_registry",
        })


@pytest.mark.parametrize('format_ok,hash_ok', [(True, True), (True, False), (False, True), (False, False)])
def test_format_never_selects_slot(format_ok, hash_ok):
    result = adjudicate(format_passed=format_ok, hash_matches=hash_ok,
                        readiness={'research_verdict': 'promote', 'submission_approved': True})
    assert result['download_ok'] == (format_ok and hash_ok)
    assert result['submission_approved'] is False
    assert result['slot_selected'] is False
    assert result['identical_protocol_current_best_beaten'] is False


def test_missing_evidence_is_not_promoted():
    result = adjudicate(format_passed=True, hash_matches=True, readiness={})
    assert result['recorded_research_verdict'] == 'unknown'
    assert not result['complete_parallel_registry_verified']


def test_negative_receipt_is_preserved():
    result = adjudicate(format_passed=True, hash_matches=True, readiness={
        'research_verdict': 'negative', 'gates': [
            {'name': 'assigned_lane', 'status': 'unknown'},
            {'name': 'format', 'status': 'passed'}]})
    assert result['recorded_research_verdict'] == 'negative'
    assert result['recorded_failed_or_unknown_gates'] == {'assigned_lane': 'unknown'}
