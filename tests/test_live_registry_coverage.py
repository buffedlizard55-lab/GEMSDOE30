"""A new public TIFF must block selection, not falsify archived receipts."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gemsdoe30.readiness import with_current_inventory


def test_new_reference_is_unknown_and_can_never_promote_or_mutate_archive():
    archive = {"research_verdict": "promote", "download_ok": True, "ok_to_submit": True,
               "eligible_for_separate_slot_selector": True, "submission_approved": False,
               "slot_selected": False, "gates": [{"name": "novelty_dots", "status": "passed"}]}
    before = deepcopy(archive)
    result = with_current_inventory(archive, recorded_hashes={"a"}, current_hashes={"a", "b"})
    assert archive == before
    assert result["download_ok"] is True  # mechanical file download != upload approval
    assert result["research_verdict"] == "negative"
    assert result["ok_to_submit"] is False
    assert result["eligible_for_separate_slot_selector"] is False
    assert result["archived_research_verdict"] == "promote"
    assert result["current_inventory_coverage"] == "unknown"
    assert result["unassessed_current_reference_sha256"] == ["b"]
    assert result["gates"][-1]["status"] == "unknown"


def test_no_new_reference_preserves_recorded_decision_exactly():
    archive = {"research_verdict": "negative", "gates": []}
    assert with_current_inventory(archive, recorded_hashes={"a", "b"}, current_hashes={"a"}) == archive


@pytest.mark.parametrize("kind", ["current", "tad", "stopped"])
def test_real_verifiers_preserve_base_readiness_bytes_and_block_live_inventory(kind):
    root = Path(__file__).resolve().parents[1]
    template = root / "data/raw/sample_submission.tif"
    if not template.exists():
        pytest.skip("pinned template required")
    if kind == "current":
        from scripts.verify_current_run import verify
        pointer = root / "docs/current-run.json"
        readiness = root / json.loads(pointer.read_text())["readiness"]
        run = lambda: verify(pointer, template)
    elif kind == "tad":
        from scripts.verify_tad_run import verify
        directory = root / "docs/research/tilt-alteration-discontinuity"
        readiness = directory / "readiness.json"
        run = lambda: verify(directory / "current-run.json", template)
    else:
        from scripts.verify_stopped_attempt import verify
        directory = root / "docs/research/texture-controls"
        readiness = directory / "readiness.json"
        run = lambda: verify(directory, template)
    before = readiness.read_bytes()
    result = run()
    assert readiness.read_bytes() == before
    assert result["research_verdict"] == "negative"
    assert result["eligible_for_separate_slot_selector"] is False
    assert result["current_inventory_coverage"] == "unknown"
