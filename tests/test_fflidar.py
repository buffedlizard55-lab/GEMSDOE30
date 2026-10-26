"""FFL-1 lane: frozen strata arithmetic and experiment contract."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from gemsdoe30.experiments import contract

ROOT = Path(__file__).resolve().parents[1]
FFL_DIR = ROOT / "docs/research/2026-10-26-fflidar"


def test_fflidar_contract_candidate_and_features():
    spec = contract({"experiment_spec": "fflidar1"})
    assert spec["candidate"] == "fusion_ffstrat"
    assert spec["arms"] == ("msdb_edge", "fusion_edge", "fusion_ffstrat")
    assert spec["required_positive_deltas"] == ("msdb_edge", "fusion_edge")
    assert len(spec["features"]) == 54  # 19 raw + 18 MSDB + 17 LiDAR
    assert len(set(spec["features"])) == 54
    assert spec["support_px"] <= spec["guard_px"]


def test_stratified_counts_sum_exactly_and_match_frozen_shares():
    from scripts.lane_fflidar import stratified_counts

    for count in (1, 7, 44090, 20902, 11661, 4821, 6728):
        quotas = stratified_counts(count)
        assert sum(quotas) == count
        assert all(q >= 0 for q in quotas)
    quotas = stratified_counts(44090)
    shares = [q / 44090 for q in quotas]
    for got, want in zip(shares, (0.14, 0.15, 0.34, 0.16, 0.21)):
        assert got == pytest.approx(want, abs=1 / 44090)


def test_expanded_dot_audit_verifier_requires_hash_bound_duplicate_evidence():
    from scripts.verify_fflidar_run import verify_expanded_receipt

    audit = json.loads((FFL_DIR / "novelty-dots-expanded.json").read_text())
    card = json.loads((FFL_DIR / "run-card.json").read_text())
    assert verify_expanded_receipt(audit, card["raster_sha256"], promote=False) is True
    wrong_hash = dict(audit, candidate_sha256="0" * 64)
    with pytest.raises(ValueError, match="not bound"):
        verify_expanded_receipt(wrong_hash, card["raster_sha256"], promote=False)
    cleared_audit = dict(audit, decision="blocked-incomplete-evidence")
    with pytest.raises(ValueError, match="contradicts measured novelty"):
        verify_expanded_receipt(cleared_audit, card["raster_sha256"], promote=False)


def test_expanded_surface_receipt_is_not_misrepresented_as_preplacement():
    readiness = json.loads((FFL_DIR / "readiness.json").read_text())
    surface = json.loads((FFL_DIR / "novelty-surface-expanded.json").read_text())
    card = json.loads((FFL_DIR / "run-card.json").read_text())
    assert surface["candidate_sha256"] == card["raster_sha256"]
    assert readiness["surface_audit"]["preplacement_surface_valid"] is False
    assert readiness["surface_audit"]["status"] == "invalid_as_preplacement_evidence"


def test_fflidar_final_artifact_is_duplicate_stopped_and_never_submittable():
    card = json.loads((FFL_DIR / "run-card.json").read_text())
    readiness = json.loads((FFL_DIR / "readiness.json").read_text())
    audit = json.loads((FFL_DIR / "novelty-dots-expanded.json").read_text())
    raster = ROOT / card["published_tiff"]
    assert raster.is_file()
    with raster.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    assert digest == card["raster_sha256"] == audit["candidate_sha256"]
    assert audit["decision"] == "duplicate-stop"
    assert max(
        row["candidate_fraction_within_3px_of_reference"] for row in audit["comparisons"]
    ) == pytest.approx(0.7828078929462463)
    assert card["verdict"] == readiness["research_verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["submission_approved"] is False and card["slot_selected"] is False
    assert card["organizer_score"] is None
    assert len(card["note"]) <= 140


def test_fflidar_archive_download_is_marked_do_not_upload():
    card = json.loads((FFL_DIR / "run-card.json").read_text())
    for relative in ("research-history.html", "experiment-review.html"):
        html = (ROOT / relative).read_text()
        main = html[html.index('<main id="main">'):]
        assert main.index("Latest lane FFL-1") < main.index('<section class="intro"')
        assert "Do not submit it." in html
        assert "78.280789%" in html
        assert "pre-placement surface novelty against the expanded registry is <strong>unverified</strong>" in html
        assert card["published_tiff"] in html
        assert "Download FFL-1 research artifact — do not upload" in html
        assert card["submission_name"] in html


def test_fflidar_stratified_experiment_records_v3_infeasibility_without_production():
    receipt = json.loads((FFL_DIR / "results-stratified.json").read_text())
    assert receipt["infeasible_as_frozen"] is True
    assert receipt["folds_scored"] == 0
    assert receipt["production"] is None
    assert receipt["gate"]["passed"] is False
    assert len(receipt["fold_stratum_availability"]) == 4
    for fold in receipt["fold_stratum_availability"]:
        assert fold["eligible_by_stratum"]["(2.0,5.0]"] == 0
        assert fold["eligible_by_stratum"]["(5.0,10.0]"] == 0


def test_stratified_select_respects_strata_exclusion_and_spacing():
    from scripts.lane_fflidar import stratified_select

    rng = np.random.default_rng(0)
    surface = rng.random((160, 160), dtype=np.float32)
    yy, xx = np.mgrid[0:160, 0:160]
    distance = np.abs(xx - 80).astype(np.float32)  # distance to a vertical fault line
    active = np.ones((160, 160), dtype=bool)
    dots, placed = stratified_select(surface, active & (distance > 2.0), distance, 100)
    assert int(np.count_nonzero(dots)) == 100
    assert sum(placed) == 100
    placed_at = np.argwhere(dots > 0)
    d = distance[dots > 0]
    assert (d > 2.0).all()
    # within-stratum 3px spacing: no two dots from the same stratum within <3px
    edges = [(2, 5), (5, 10), (10, 30), (30, 50), (50, None)]
    for (low, high), quota in zip(edges, placed):
        sel = placed_at[(d > low) & ((d <= high) if high else True)]
        assert len(sel) == quota
        if len(sel) > 1:
            diff = sel[:, None, :] - sel[None, :, :]
            dist2 = (diff ** 2).sum(-1)
            dist2[dist2 == 0] = 10**9
            assert dist2.min() >= 9


def test_current_front_pages_do_not_offer_stopped_ffl_as_the_new_submission():
    card = json.loads((FFL_DIR / "run-card.json").read_text())
    for name in ("index.html", "executive-summary.html"):
        html = (ROOT / name).read_text()
        assert card["published_tiff"] not in html
        assert "GDX-1" in html and "NOT APPROVED FOR SUBMISSION" in html
