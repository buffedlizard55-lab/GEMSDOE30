"""Guard the dated 2026-10-30 public leaderboard receipt without attributing files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/research/2026-10-30-leaderboard-snapshot.json"


def _receipt():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_20261030_receipt_is_a_complete_visible_top_fifty():
    data = _receipt()
    rows = data["rows"]
    assert data["retrieved_utc_date"] == "2026-10-30"
    assert data["source_url"] == "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
    assert data["score_evidence_class"].startswith("OFFICIAL-PUBLIC-LEADERBOARD-SNAPSHOT")
    assert [row["rank"] for row in rows] == list(range(1, 51))
    scores = [row["score"] for row in rows]
    assert all(a >= b for a, b in zip(scores, scores[1:]))
    assert data["visible_ranks"] == [1, 50]


def test_20261030_public_claims_are_dated_and_not_submission_receipts():
    rows = _receipt()["rows"]
    assert rows[0] == {"rank": 1, "score": 0.4544}
    assert rows[-1] == {"rank": 50, "score": 0.3195}
    assert [row["rank"] for row in rows if row["score"] == 0.3195] == [50]
    assert all(row["score"] != 0.4413 for row in rows)
    assert 0.2778 < rows[-1]["score"]


def test_20261030_receipt_does_not_claim_site_or_file_attribution():
    data = _receipt()
    assert "no mapping to a repository file" in data["score_evidence_class"]
    assert any("no organizer submission-page receipt" in claim["result"]
               for claim in data["claim_checks"])
    assert data["slot_selected"] is False
