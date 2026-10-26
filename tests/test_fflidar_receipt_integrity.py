"""Negative decisions must verify their decisive evidence, not bypass it."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.verify_fflidar_run import verify_expanded_receipt

REPORT = Path(__file__).resolve().parents[1] / "docs/research/2026-10-26-fflidar"


def receipt():
    return json.loads((REPORT / "novelty-dots-expanded.json").read_text())


def test_archived_negative_duplicate_is_verified():
    audit = receipt()
    assert verify_expanded_receipt(audit, audit["candidate_sha256"], promote=False)
    with pytest.raises(ValueError, match="complete, nonduplicate"):
        verify_expanded_receipt(audit, audit["candidate_sha256"], promote=True)


@pytest.mark.parametrize("field,value", [
    ("candidate_sha256", "0" * 64), ("stage", "surface"),
    ("comparisons", []), ("errors", ["missing reference"]),
    ("decision", "blocked-incomplete-evidence"),
])
def test_negative_receipt_tampering_is_rejected(field, value):
    audit = receipt()
    digest = audit["candidate_sha256"]
    audit[field] = value
    with pytest.raises(ValueError):
        verify_expanded_receipt(audit, digest, promote=False)


@pytest.mark.parametrize("field,value", [
    ("spearman_full_footprint", float("nan")),
    ("spearman_full_footprint", float("inf")),
    ("spearman_full_footprint", 1.01),
    ("spearman_full_footprint", True),
    ("candidate_fraction_within_3px_of_reference", -0.1),
    ("candidate_fraction_within_3px_of_reference", 1.1),
    ("candidate_fraction_within_3px_of_reference", float("nan")),
])
def test_invalid_measurements_never_pass(field, value):
    audit = receipt()
    audit["comparisons"][0][field] = value
    with pytest.raises(ValueError, match="invalid correlation / overlap"):
        verify_expanded_receipt(audit, audit["candidate_sha256"], promote=False)


def test_threshold_equality_is_not_duplicate_but_incomplete_blocks_promotion():
    audit = deepcopy(receipt())
    audit["comparisons"] = [{"spearman_full_footprint": 0.90,
                             "candidate_fraction_within_3px_of_reference": 0.70}]
    audit["decision"] = "blocked-incomplete-evidence"
    digest = audit["candidate_sha256"]
    assert not verify_expanded_receipt(audit, digest, promote=False)
    with pytest.raises(ValueError, match="complete, nonduplicate"):
        verify_expanded_receipt(audit, digest, promote=True)


def test_full_verifier_rejects_tampered_negative_receipt(tmp_path, monkeypatch):
    import scripts.verify_fflidar_run as verifier

    for name in ("run-card.json", "readiness.json", "results.json",
                 "results-confirmation.json", "novelty-dots-expanded.json"):
        (tmp_path / name).write_text((REPORT / name).read_text())
    audit = receipt()
    audit["candidate_sha256"] = "0" * 64
    (tmp_path / "novelty-dots-expanded.json").write_text(json.dumps(audit))
    monkeypatch.setattr(verifier, "REPORT", tmp_path)
    with pytest.raises(ValueError, match="not bound"):
        verifier.verify()
