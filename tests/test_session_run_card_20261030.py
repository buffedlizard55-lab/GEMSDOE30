"""Fail-closed contract for the cumulative 2026-10-30 repository review."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "docs/research/2026-10-30-session-run-card.json"


def test_20261030_run_card_is_a_negative_no_candidate_decision():
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["verdict"] == "negative"
    assert card["unique_tiff_generated"] is False
    assert card["raster_sha256"] is None
    assert card["download_ok"] is False
    assert card["ok_to_submit"] is False
    assert card["slot_selected"] is False
    assert card["experiment_budget"]["experiments_run"] == 0
    assert card["experiment_budget"]["experiment_cap"] == 3
    assert "Full-resolution USGS 3DEP 1 m DEM" in card["hypothesis"]["rank_1_proposal"]
    assert "H-31-01" in card["hypothesis"]["explicit_exclusion"]


def test_20261030_run_card_never_upgrades_owner_claims_or_fabricates_holdout():
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["holdout_dti"]["status"] == "NOT RUN"
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["ci95"] is None
    assert card["organizer_confirmed_score"]["value"] is None
    assert card["reported_h33_b2"]["evidence_class"].startswith("OWNER-REPORTED, UNVERIFIED")
    assert len(card["historical_best_by_site"]) == 9
    assert all(row["evidence_class"] == "OWNER-REPORTED, UNVERIFIED"
               for row in card["historical_best_by_site"])


def test_20261030_run_card_distinguishes_partial_leakage_alarm_from_candidate_screen():
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["registry_novelty"]["surface_checked_before_placement"] is False
    assert card["registry_novelty"]["final_dots_checked_after_placement"] is False
    canary = card["feature_level_leakage_canary"]
    assert canary["auc_alarm_threshold"] == 0.90
    assert canary["candidate_features_tested"] is False
    separate = canary["independent_repository_canary"]
    assert separate["features_tested_individually"] == 5
    assert separate["flagged_feature"] == "derived_gdr_qfaults_v2_100m_u8.tif"
    assert separate["auc_sign_free"] == 0.984002 > canary["auc_alarm_threshold"]
    assert separate["leakage_alarm_triggered"] is True
    assert card["format_gate"]["status"] == "NOT RUN — no new TIFF"


def test_20261030_repository_audit_pointer_is_separate_from_scientific_review():
    pointer = json.loads((ROOT / "docs/current-run.json").read_text(encoding="utf-8"))
    assert pointer["latest_review"]["run_card"] == "docs/research/2026-10-27-registry-preflight/run-card.json"
    assert pointer["latest_repository_audit"]["run_card"] == "docs/research/2026-10-30-session-run-card.json"
    assert pointer["latest_repository_audit"]["date_utc"] == "2026-10-30"
    assert pointer["latest_repository_audit"]["site_page"] == "priority-executive-summary.html"


def test_h33_historical_analysis_is_relabelled_with_staff_caveat():
    text = (ROOT / "docs/research/2026-10-25-lsm/why-h33-scored-0.2778.md").read_text(encoding="utf-8")
    assert "new-fault truth may lie within 300 m" in text
    assert "The deleted dots could remove either FP mass or TP credit" in text
    assert "Those dots earned almost no TP but paid full FP" not in text


def test_20261030_prompt_is_persisted_in_readme():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "### Session Prompt 2026-10-30" in text
    assert "A measured score must be labelled HOLDOUT-DTI" in text
    assert "AUC above 0.90 is a leakage alarm" in text
    assert "Do not select a weekly submission slot" in text


def test_merged_tree_verification_and_parallel_id_collision_are_disclosed():
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["parallel_review_integration"]["merged_base_commit"] == "f285b77"
    collision = card["parallel_review_integration"]["cross_review_irregularity_id_collision"]
    assert collision["this_review_assignments"]["leaderboard_drift"] == "IR-30-110"
    assert collision["this_review_assignments"]["H33_B2_staff_scoring_correction"] == "IR-30-120"
    assert collision["status"].startswith("OPEN")
    verification = card["merged_tree_verification"]
    assert verification["registry_preflight"]["exit_code"] == 0
    assert verification["generated_site"]["exit_code"] == 0
    assert verification["full_pytest"]["passed"] + verification["full_pytest"]["skipped"] == verification["full_pytest"]["collected"]
    assert card["slot_selected"] is False and card["ok_to_submit"] is False
