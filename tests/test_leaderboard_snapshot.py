"""Guards the historical 2026-10-29 public-leaderboard receipt."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/research/2026-10-29-leaderboard-snapshot.json"


def _rows():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return data, data["rows"]


def test_20261029_snapshot_is_a_complete_descending_top_fifty():
    data, rows = _rows()
    assert data["source_url"] == "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
    assert [row["rank"] for row in rows] == list(range(1, 51))
    scores = [row["score"] for row in rows]
    assert all(a >= b for a, b in zip(scores, scores[1:])), "leaderboard must be non-increasing by rank"


def test_20261029_snapshot_does_not_show_0_4413_as_the_high():
    _, rows = _rows()
    assert rows[0]["score"] == 0.4544
    assert all(row["score"] != 0.4413 for row in rows)


def test_20261029_snapshot_places_0_3195_at_rank_47_not_the_top():
    _, rows = _rows()
    assert [row["rank"] for row in rows if row["score"] == 0.3195] == [47]
    assert rows[0]["score"] > 0.3195


def test_20261029_snapshot_places_0_2778_below_its_visible_cutoff():
    _, rows = _rows()
    assert rows[-1]["score"] == 0.3167
    assert 0.2778 < rows[-1]["score"]


def test_20261029_snapshot_keeps_submission_gates_closed():
    data, _ = _rows()
    assert data["ok_to_submit"] is False
    assert data["slot_selected"] is False
