"""The 29 Oct artifact audit is reproducible and keeps format separate from approval."""
from __future__ import annotations

import pytest

from scripts import audit_candidate_readiness as audit

REQUIRED = (
    audit.CANDIDATE,
    audit.TEMPLATE,
    audit.LATTICE,
    audit.FLEET,
    audit.CORE_PINS,
    audit.LATTICE_PINS,
)


def test_hash_bound_candidate_audit_reproduces_duplicate_stop():
    if not all(path.is_file() for path in REQUIRED):
        pytest.skip("restore the pinned candidate, template, lattice and historical references")
    saved = audit.load_json(audit.OUTPUT)
    measured = audit.audit()

    assert audit.same_measurement(saved, measured)
    assert measured["candidate"]["sha256"] == measured["raster_sha256"]
    assert measured["validator_output"]["passed"] is True
    assert measured["registry"]["surface_stage"]["decision"] == "blocked-unavailable"
    dots = measured["registry"]["final_dot_stage"]
    assert dots["complete_parallel_registry_checked"] is False
    lattice = dots["pinned_lattice"]
    assert lattice["decision"] == "duplicate-stop"
    assert lattice["fraction_within_3px"] > 0.70
    assert lattice["matching_candidate_dots"] == 29657
    assert lattice["candidate_dots"] == 29707
    assert measured["holdout_dti"]["value"] is None
    assert measured["score_estimate"] is None
    assert measured["organizer_confirmed_score"]["value"] is None
    assert measured["candidate"]["original_note_uniqueness_claim_is_supported"] is False
    assert measured["download_control"] is False
    assert measured["ok_to_download_for_submission"] is False
    assert measured["ok_to_submit"] is False
    assert measured["slot_selected"] is False
    assert measured["verdict"] == "negative"


@pytest.mark.parametrize("pin_name", ["CANDIDATE_SHA256", "SIDECAR_SHA256"])
def test_audit_refuses_changed_frozen_candidate_identity(monkeypatch, pin_name):
    if not all(path.is_file() for path in REQUIRED):
        pytest.skip("restore the pinned candidate, template, lattice and historical references")
    monkeypatch.setattr(audit, pin_name, "0" * 64)
    with pytest.raises(ValueError, match="frozen SHA-256|audit target SHA-256"):
        audit.audit()
