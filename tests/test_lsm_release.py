"""Tamper tests for the G30-LSM machine decision (runs from committed receipts only)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LSM = ROOT / "docs/research/2026-10-25-lsm"


@pytest.fixture
def lsm(tmp_path, monkeypatch):
    from scripts import verify_lsm_run as v
    shutil.copytree(LSM, tmp_path / "docs/research/2026-10-25-lsm")
    pointer = tmp_path / "docs/current-run.json"
    pointer.write_text(json.dumps({"schema_version": 2, "run_card": "docs/research/2026-10-25-lsm/run-card.json",
                                   "readiness": "docs/research/2026-10-25-lsm/readiness.json",
                                   "verifier": "scripts/verify_lsm_run.py"}))
    monkeypatch.setattr(v, "ROOT", tmp_path)
    return v, tmp_path / "docs/research/2026-10-25-lsm", pointer


def test_committed_decision_is_reproducible_and_says_do_not_submit(lsm):
    v, directory, pointer = lsm
    result = v.verify(pointer, ROOT / "data/raw/sample_submission.tif")
    assert result == json.loads((directory / "readiness.json").read_text())
    assert result["ok_to_submit"] is False and result["decision"] == "DO NOT SUBMIT"
    status = {g["name"]: g["status"] for g in result["gates"]}
    assert status["beats_current_holdout_best"] == "passed"
    assert status["single_feature_leakage_canaries"] == "passed"
    assert status["novelty_dots"] == "failed" and status["file_contract"] == "failed"


def test_forged_overlap_cannot_hide_or_fake_a_duplicate(lsm):
    v, directory, pointer = lsm
    dots = json.loads((directory / "novelty-dots.json").read_text())
    for row in dots["rows"]:
        row["candidate_fraction_within_3px_of_reference"] = 0.1
    (directory / "novelty-dots.json").write_text(json.dumps(dots))
    with pytest.raises(ValueError, match="not supported"):
        v.verify(pointer, ROOT / "data/raw/sample_submission.tif")


def test_forged_holdout_summary_is_caught_by_bootstrap_recomputation(lsm):
    v, directory, pointer = lsm
    e1 = json.loads((directory / "results-e1.json").read_text())
    e1["summary"]["primary"]["candidate_minus"]["core19"]["ci95"][0] = 0.05
    (directory / "results-e1.json").write_text(json.dumps(e1))
    with pytest.raises(ValueError, match="mismatch"):
        v.verify(pointer, ROOT / "data/raw/sample_submission.tif")


def test_changed_preregistration_breaks_the_binding(lsm):
    v, directory, pointer = lsm
    with (directory / "preregistration.md").open("a") as fh:
        fh.write("\nedited after the fact\n")
    result = v.verify(pointer, ROOT / "data/raw/sample_submission.tif", write=True)
    assert {g["name"]: g["status"] for g in result["gates"]}["preregistration_binding"] == "failed"
    assert result["ok_to_submit"] is False


def test_stale_readiness_receipt_is_rejected(lsm):
    v, directory, pointer = lsm
    ready = json.loads((directory / "readiness.json").read_text())
    ready["ok_to_submit"] = True
    (directory / "readiness.json").write_text(json.dumps(ready))
    with pytest.raises(ValueError, match="stale"):
        v.verify(pointer, ROOT / "data/raw/sample_submission.tif")
