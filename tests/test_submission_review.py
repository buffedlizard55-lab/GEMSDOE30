from scripts.review_submission_readiness import adjudicate
import pytest


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
