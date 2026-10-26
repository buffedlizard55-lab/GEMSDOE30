"""Tests for the deterministic, non-promotional nine-site executive audit."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts.priority_site_summary import PRIORITY_SITES, build_summary, canonical_json

ROOT = Path(__file__).resolve().parents[1]


def test_priority_summary_covers_every_requested_site_and_never_selects_a_historical_upload():
    summary = build_summary(ROOT)
    assert tuple(row["site"] for row in summary["sites"]) == PRIORITY_SITES
    assert summary["selection_decision"]["recommended_historical_priority_site_submission"] is None
    current = summary["selection_decision"]["current_research_artifact"]
    assert current["competition_upload_approved"] is False
    assert current["research_verdict"] == "negative"
    assert current["paired_improvement_status"] == "failed"
    assert all(row["re_use_decision"] == "DO NOT COPY, RENAME, OR SUBMIT" for row in summary["sites"])
    assert len(summary["distinct_strategy_assessment"]["ranked_hypotheses"]) == 4
    assert summary["distinct_strategy_assessment"]["ranked_hypotheses"][0]["id"] == "MSDB-1"
    assert "no evidence" in summary["distinct_strategy_assessment"]["conclusion"]
    winner = summary["highest_owner_reported_claim_among_priority_sites"]
    assert winner == {
        "site": "GEMSDOE32",
        "submission": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros",
        "score": "0.2778",
        "label": "OWNER-REPORTED / UNVERIFIED (not HOLDOUT-DTI; not ORGANIZER-CONFIRMED)",
    }


def test_priority_summary_preserves_known_byte_lineage_and_is_deterministic():
    first = canonical_json(build_summary(ROOT))
    second = canonical_json(build_summary(ROOT))
    assert first == second
    summary = json.loads(first)
    relations = summary["forensic_lineage"]
    assert relations[0]["sites"] == ["GEMSDOE25", "GEMSDOE30"]
    assert relations[0]["measured"] is True
    assert relations[1]["sites"] == ["GEMSDOE28", "GEMSDOE31"]
    assert relations[1]["measured"] is True
    assert relations[2]["sites"] == ["GEMSDOE28", "GEMSDOE32"]
    assert relations[2]["measured"] is True
    assert relations[2]["mismatching_pixels"] == 0


def test_priority_summary_fails_closed_if_the_forensic_receipt_is_tampered(tmp_path):
    # The builder reads only a small, explicit evidence set; copying those files
    # makes the failure mode independent of the full repository checkout.
    for rel in (
        "docs/score-ledger.csv",
        "docs/current-run.json",
        "docs/research/2026-10-25/recipe-reconstruction.json",
        "docs/research/msdb-piedmont/run-card.json",
        "docs/research/msdb-piedmont/readiness.json",
    ):
        source = ROOT / rel
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    receipt = tmp_path / "docs/research/2026-10-25/recipe-reconstruction.json"
    payload = json.loads(receipt.read_text())
    payload["mismatching_pixels"] = 1
    receipt.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="mismatching_pixels"):
        build_summary(tmp_path)


def test_priority_summary_fails_closed_without_the_corrected_msdb_paired_gate(tmp_path):
    for rel in (
        "docs/score-ledger.csv",
        "docs/current-run.json",
        "docs/research/2026-10-25/recipe-reconstruction.json",
        "docs/research/msdb-piedmont/run-card.json",
        "docs/research/msdb-piedmont/readiness.json",
    ):
        source = ROOT / rel
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)
    receipt = tmp_path / "docs/research/msdb-piedmont/readiness.json"
    payload = json.loads(receipt.read_text())
    next(gate for gate in payload["gates"] if gate["name"] == "paired_improvement")["status"] = "passed"
    receipt.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="corrected failed MSDB paired-improvement gate"):
        build_summary(tmp_path)
