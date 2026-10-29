import json
import sys
from pathlib import Path

from scripts import build_research_site, build_status
from scripts.render_registry_preflight import render

ROOT = Path(__file__).resolve().parents[1]


def _receipt(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_nine_site_table_separates_claims_from_new_score_estimates():
    pages = render(
        _receipt("docs/research/2026-10-27-registry-preflight/run-card.json"),
        _receipt("docs/research/2026-10-26-csr/fleet-audit.json"),
    )
    page = pages["priority-executive-summary.html"]
    assert "New submission score estimate" in page
    assert page.count("no validated new candidate; no forecast") == 9
    assert "unverified owner claim; no receipt" in page
    assert "DO NOT DOWNLOAD FOR SUBMISSION" in page
    assert "does not prove all other comparisons" in page


def test_current_overview_discloses_merged_tiffs_as_stopped_without_download_controls():
    pages = render(
        _receipt("docs/research/2026-10-27-registry-preflight/run-card.json"),
        _receipt("docs/research/2026-10-26-csr/fleet-audit.json"),
    )
    for name, overlap in (
        ("GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif", "99.90%"),
        ("GEMSDOE30-vent-structural-offcat-d3-20261027T000000Z.tif", "100.00%"),
    ):
        for page_name in ("index.html", "executive-summary.html", "csr-discontinuity-review.html", "priority-executive-summary.html"):
            page = pages[page_name]
            assert name in page
            assert overlap in page
            assert f'href="docs/downloads/{name}"' not in page
            assert f'href="{name}"' not in page
    assert "NOT APPROVED TO DOWNLOAD OR SUBMIT" in pages["index.html"]
    assert "No verified HOLDOUT-DTI receipt located" in pages["index.html"]
    assert "60,988 withheld positives" in pages["index.html"]
    assert "whole-array finite-range diagnostic fails" in pages["index.html"]


def test_current_overview_discloses_pool_duplicate_stop_not_submission():
    pages = render(
        _receipt("docs/research/2026-10-27-registry-preflight/run-card.json"),
        _receipt("docs/research/2026-10-26-csr/fleet-audit.json"),
    )
    page = pages["index.html"]
    assert "88.74% / 75.81% / 71.08%" in page
    assert "No TIFF was published; no slot is approved." in page
    assert "POOL-1 review" in page
    assert "New submission score estimate" in page


def test_status_feed_reports_pool1_as_verified_negative(tmp_path, monkeypatch):
    output = tmp_path / "status.json"
    monkeypatch.setattr(sys, "argv", ["build_status.py", "--skip-tests", "--output", str(output)])
    assert build_status.main() == 0
    status = json.loads(output.read_text(encoding="utf-8"))
    pool = next(row for row in status["additional_stopped_attempts"] if row["lane"] == "POOL-1")
    assert pool["verified_now"] is True
    assert pool["error"] is None
    assert pool["ok_to_submit"] is False
    assert "duplicate-stop" in pool["decision"]
    assert status["promotion_gates"]["stopped_attempt_pool-1"]["decision"] == pool["decision"]
    for filename in (
        "GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif",
        "GEMSDOE30-vent-structural-offcat-d3-20261027T000000Z.tif",
    ):
        candidate = next(row for row in status["downloads"] if row["file"].endswith(filename))
        assert candidate["site_linked"] is False
        assert candidate["mentioned_on_site"] is True
        assert candidate["submission_recommendation"] is False
        assert candidate["organizer_acceptance_confirmed"] is False


def test_site_builder_routes_through_current_receipt_verifiers(monkeypatch):
    def obsolete_path_must_not_run(*args, **kwargs):
        raise AssertionError("legacy PTA/TAD builder ran before current receipt routing")

    monkeypatch.setattr(build_research_site, "verify", obsolete_path_must_not_run)
    pages = build_research_site.build(ROOT / "data/raw/sample_submission.tif")
    assert ROOT / "index.html" in pages
    assert ROOT / "priority-executive-summary.html" in pages
    assert pages[ROOT / "index.html"].find("DUPLICATE-STOP") >= 0
    assert "DO NOT DOWNLOAD FOR SUBMISSION" in pages[ROOT / "priority-executive-summary.html"]


def test_submission_guide_is_single_document_and_keeps_fail_closed_table():
    from html.parser import HTMLParser

    class Structure(HTMLParser):
        def __init__(self):
            super().__init__()
            self.ids = []
            self.tags = []

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)
            attrs = dict(attrs)
            if 'id' in attrs:
                self.ids.append(attrs['id'])

    text = (ROOT / 'executive-summary.html').read_text()
    page = Structure()
    page.feed(text)
    assert page.tags.count('html') == page.tags.count('main') == 1
    assert len(page.ids) == len(set(page.ids))
    assert 'submit' in page.ids
    assert 'No approved download or reliable score estimate' in text
    assert 'cause of “Predicted values must be in range [0, 1]” is not established' in text
    for site in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f'priority-GEMSDOE{site}.html' in text
    assert 'scope=\\"row\\"' not in text
