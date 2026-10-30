"""Guards the 2026-10-30 repository-review receipts.

Receipt-only checks always run. Checks that re-measure rasters skip unless the
pinned inputs are restored (see docs/research/2026-10-30-verification-receipts/review.md).
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/research/2026-10-30-verification-receipts"
sys.path.insert(0, str(ROOT / "scripts"))


def _load(name):
    return json.loads((REVIEW / name).read_text(encoding="utf-8"))


# ---------- leaderboard receipt (official board, 2026-10-30) ----------

def test_leaderboard_receipt_is_a_complete_descending_top_fifty():
    data = _load("leaderboard-snapshot.json")
    assert data["source_url"] == "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
    rows = data["rows"]
    assert [r["rank"] for r in rows] == list(range(1, 51))
    scores = [r["score"] for r in rows]
    assert all(a >= b for a, b in zip(scores, scores[1:]))


def test_leaderboard_receipt_top_and_claims():
    data = _load("leaderboard-snapshot.json")
    rows = data["rows"]
    assert rows[0]["score"] == 0.4544
    assert all(r["score"] != 0.4413 for r in rows), "owner's 0.4413 must not appear on the board"
    assert [r["rank"] for r in rows if r["score"] == 0.3195] == [50]
    assert rows[-1]["score"] == 0.3195
    assert data["ok_to_submit"] is False and data["slot_selected"] is False


def test_leaderboard_receipt_documents_the_drift_from_2026_10_29():
    data = _load("leaderboard-snapshot.json")
    assert "rank #47" in data["comparison_with_2026-10-29_receipt"]
    old = json.loads((ROOT / "docs/research/2026-10-29-leaderboard-snapshot.json").read_text(encoding="utf-8"))
    assert [r for r in old["rows"] if r["score"] == 0.3195][0]["rank"] == 47, "2026-10-29 receipt must stay unchanged"


# ---------- lattice random-dot control ----------

def test_lattice_control_receipt_shows_random_dots_flagged_as_duplicates():
    data = _load("lattice-random-control.json")
    trials = data["trials"]
    assert len(trials) == 15
    assert {t["budget"] for t in trials} == {9652, 22164, 44090}
    assert all(t["dot_duplicate_by_literal_rule"] for t in trials)
    assert all(0.998 < t["fraction_within_3px"] < 1.0 for t in trials)
    assert data["ok_to_submit"] is False and data["slot_selected"] is False


def test_lattice_control_pins_match_the_lattice_pin_file():
    import lattice_random_control as ctl

    pin = json.loads((ROOT / "docs/research/2026-10-27-registry-preflight/lattice-pin.json").read_text(encoding="utf-8"))
    lattice = [f for f in pin["files"] if f["id"] == "registry_lattice"][0]
    assert ctl.EXPECTED_LATTICE_SHA == lattice["sha256"]


@pytest.mark.skipif(
    not (ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif").exists()
    or not (ROOT / "data/raw/sample_submission.tif").exists(),
    reason="restore sample_submission and registry_lattice to re-measure the control",
)
def test_lattice_control_reproduces_when_inputs_are_restored():
    import lattice_random_control as ctl

    fresh = ctl.run()
    stored = _load("lattice-random-control.json")
    for a, b in zip(fresh["trials"], stored["trials"]):
        assert a["budget"] == b["budget"] and a["seed"] == b["seed"]
        assert abs(a["fraction_within_3px"] - b["fraction_within_3px"]) < 1e-12


# ---------- nine-site family audit ----------

def test_nine_site_family_identity_and_containment_are_as_recorded():
    data = _load("nine-site-family.json")
    assert data["identical_pairs"] == [["GEMSDOE25", "GEMSDOE30"]]
    contained = {(p["a"], p["b"]) for p in data["pairs_with_identity_or_containment"] if p["smaller_set_contained_in_other"]}
    assert ("GEMSDOE25", "GEMSDOE32") in contained
    assert ("GEMSDOE32", "GEMSDOE36") in contained
    assert ("GEMSDOE24", "GEMSDOE27") in contained


def test_h33b2_decomposition_is_the_recorded_halo_removal():
    d = _load("nine-site-family.json")["h33b2_vs_d28"]
    assert d["dots_in_25_not_in_32"] == 6436
    assert d["dots_in_32_not_in_25"] == 0
    assert d["removed_dots_max_distance_to_labelled_fault_px"] == 2.0
    assert d["removed_dots_share_within_2px_of_labelled_fault"] == 1.0


def test_nine_site_sharing_ranges_match_the_table():
    s = _load("nine-site-family.json")["own_dot_sharing_by_site"]
    assert s["GEMSDOE28"]["min_percent_of_own_dots_found_in_other_site"] == pytest.approx(67.54)
    assert s["GEMSDOE28"]["max_percent_of_own_dots_found_in_other_site"] == pytest.approx(73.96)
    assert s["GEMSDOE33"]["min_percent_of_own_dots_found_in_other_site"] == pytest.approx(65.94)
    assert s["GEMSDOE33"]["max_percent_of_own_dots_found_in_other_site"] == pytest.approx(83.25)
    assert s["GEMSDOE36"]["max_percent_of_own_dots_found_in_other_site"] == pytest.approx(96.91)


def test_nine_site_receipt_keeps_gates_closed():
    data = _load("nine-site-family.json")
    assert data["ok_to_submit"] is False and data["slot_selected"] is False
    assert "owner-reported" in data["scores"]


# ---------- reference-writer check ----------

def test_reference_check_pins_the_commit_and_records_the_corrections():
    data = _load("reference-writer-check.json")
    assert data["source"]["commit"] == "aebe92f7c8a990f0e3443451b7a825d9afd6336b"
    assert len(data["source"]["file_sha256"]) == 64
    ids = {f["id"] for f in data["findings"]}
    assert {"R1", "R2", "R2a", "R3", "R4", "R5"} <= ids
    assert "NOT executed" in data["method"]
    assert data["ok_to_submit"] is False and data["slot_selected"] is False


def test_reference_check_quotes_the_organizer_rule_verbatim():
    quotes = _load("reference-writer-check.json")["organizer_rules_quoted"]["quotes"]
    assert "data outside the bounds is null or nan." in quotes[0]
    assert "datatype of 32-bit float (float32)" in quotes[1]


# ---------- run card ----------

def test_run_card_is_a_negative_with_no_slot_and_no_experiments():
    card = _load("run-card.json")
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False and card["slot_selected"] is False
    assert card["submission_name"] is None and card["submission_note"] is None
    assert card["budget"]["experiments_used"] == 0
    assert card["holdout_dti_and_ci"]["status"] == "NOT MEASURED"
    assert card["organizer_confirmed_scores"]["status"] == "NONE"


def test_leakage_canary_receipt_flags_qfaults_and_nothing_else():
    receipt = json.loads((REVIEW / "leakage-canary.json").read_text())
    assert receipt["rule"].startswith("single-feature AUC > 0.90")
    assert receipt["score_class"].startswith("NOT a score")
    flagged = [f["feature"] for f in receipt["features"] if f.get("leakage_flag")]
    assert flagged == ["derived_gdr_qfaults_v2_100m_u8.tif"]
    qf = next(f for f in receipt["features"] if f["feature"] == flagged[0])
    assert abs(qf["auc"] - 0.984002) < 1e-6
    assert receipt["any_leakage_flag"] is True
