"""Independent checks and deliberate tampering of the new negative deliverable."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/research/2026-10-26-gdx"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"


def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def inputs_available():
    if not TEMPLATE.exists() or not (ROOT / "data/raw/labels.tif").exists():
        pytest.skip("restore pinned template and catalogue to run exact-byte checks")


def test_real_gdx_bytes_ci_receipts_and_negative_cli_are_immutable():
    inputs_available()
    from scripts.verify_geothermal_chemistry_run import verify
    before = {p.name: p.read_bytes() for p in REPORT.glob("*.json")}
    ready = verify()
    assert ready["research_verdict"] == "negative" and ready["download_ok"]
    assert not ready["eligible_for_separate_slot_selector"]
    assert ready["catalogue_bytes_reopened"] is True
    assert ready["local_additional_comparisons_per_stage"] == 1
    assert ready["observed_registry"]["surface"]["status"] == "unknown"
    assert ready["observed_registry"]["dots"]["registry_entries_compared"] == 327
    assert {p.name: p.read_bytes() for p in REPORT.glob("*.json")} == before
    for require, code in [(False, 0), (True, 2)]:
        command = [sys.executable, "scripts/verify_geothermal_chemistry_run.py"]
        if require:
            command.append("--require-promote")
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        assert run.returncode == code, run.stderr


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    inputs_available()
    from scripts import verify_geothermal_chemistry_run as v
    directory = tmp_path / "docs/research/2026-10-26-gdx"
    shutil.copytree(REPORT, directory)
    for name in ("src/gemsdoe30/geothermal_chemistry.py", "scripts/run_geothermal_chemistry.py", "data/raw/labels.tif"):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, dest)
    for row in load(REPORT / "registry-local-addendum.json")["rasters"]:
        dest = tmp_path / row["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / row["path"], dest)
    monkeypatch.setattr(v, "ROOT", tmp_path)
    return v, directory, tmp_path


@pytest.mark.parametrize("file,mutation,message", [
    ("run-card.json", lambda x: x["holdout"].update(value=.99), "numeric mismatch"),
    ("run-card.json", lambda x: x.update(ok_to_submit=True), "negative decision"),
    ("run-card.json", lambda x: x.update(experiments_run=4), "cap breached"),
    ("run-card.json", lambda x: x.update(raster_sha256="0" * 64), "raster hash"),
    ("run-card.json", lambda x: x.update(note="x" * 141), "path/name/note"),
    ("run-card.json", lambda x: x["validator_output"].update(emitted_dots=44091), "validator contradicts"),
    ("results.json", lambda x: x["summary"]["candidate_minus"]["core19"].update(ci95=[.01, .02]), "numeric mismatch"),
    ("results.json", lambda x: x["feature_canaries"][0]["features"][0].update(raw_auc=.99), "canary alarm"),
    ("results.json", lambda x: x["feature_canaries"][1].update(fold=0), "missing feature-alone"),
    ("novelty-dots.json", lambda x: x["comparisons"].pop(), "reference inventory"),
    ("novelty-dots.json", lambda x: x["comparisons"][0].update(candidate_fraction_within_3px_of_reference=.71), "dot flag contradicts"),
    ("novelty-surface.json", lambda x: x.update(candidate_sha256=load(REPORT / "run-card.json")["raster_sha256"]), "candidate/stage identity"),
    ("novelty-surface.json", lambda x: x.update(errors=[]), "unexpected novelty error"),
    ("novelty-surface.json", lambda x: x.update(decision="observed-novelty-pass"), "incomplete registry"),
    ("comparator-parity.json", lambda x: x.update(exact_archive_parity=False), "archive.*parity"),
    ("comparator-parity.json", lambda x: x["folds"][0].update(buffer_px=46), "parity fold protocol"),
])
def test_tampering_cannot_promote_or_hide_missing_evidence(isolated, file, mutation, message):
    v, directory, _ = isolated
    path = directory / file
    data = deepcopy(load(path))
    mutation(data)
    dump(path, data)
    with pytest.raises(ValueError, match=message):
        v.verify(directory, TEMPLATE)


def test_later_research_tiff_is_unknown_not_retrospective_green(isolated):
    v, directory, root = isolated
    before = (directory / "readiness.json").read_bytes()
    arrival = root / "docs/research/another-lane/new.tif"
    arrival.parent.mkdir(parents=True)
    arrival.write_bytes(b"new byte identity is not scientific evidence")
    ready = v.verify(directory, TEMPLATE)
    assert ready["current_inventory_coverage"] == "unknown"
    assert ready["eligible_for_separate_slot_selector"] is False
    assert len(ready["unassessed_current_reference_sha256"]) == 1
    assert (directory / "readiness.json").read_bytes() == before


def test_repeat_execution_is_blocked_before_fitting(monkeypatch):
    from scripts import run_geothermal_chemistry as runner
    monkeypatch.setattr(runner, "fit_model", lambda *a, **k: pytest.fail("must never fit again"))
    for recovery in (False, True):
        with pytest.raises(FileExistsError, match="experiment cap reached"):
            runner.run(6000, incomplete_recovery=recovery)


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls, self.ids, self.downloads = [], set(), []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            assert attrs["id"] not in self.ids, f"duplicate id: {attrs['id']}"
            self.ids.add(attrs["id"])
        self.urls.extend(attrs[a] for a in ("href", "src") if attrs.get(a))
        if tag == "a" and "download" in attrs:
            self.downloads.append(attrs["href"])


@pytest.mark.parametrize("name", ["index.html", "executive-summary.html", "geothermal-chemistry-review.html",
                                  "priority-executive-summary.html", "research-history.html"]
                         + [f"priority-GEMSDOE{s}.html" for s in (24, 25, 27, 28, 30, 31, 32, 33, 36)])
def test_all_current_pages_have_real_links_unique_ids_and_clear_scope(name):
    path = ROOT / name
    text = path.read_text()
    parsed = Links(text)
    for url in parsed.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
        assert target.is_relative_to(ROOT) and target.is_file(), url
        if parts.fragment and target.suffix == ".html":
            assert unquote(parts.fragment) in Links(target.read_text()).ids, url
    if name in {"index.html", "executive-summary.html", "geothermal-chemistry-review.html"}:
        assert parsed.downloads == [load(REPORT / "run-card.json")["published_tiff"]]
        assert text.count("NOT APPROVED FOR SUBMISSION") == 1
        assert "HOLDOUT-DTI" in text and "60,988" in text
    elif name.startswith("priority-"):
        assert "unverified" in text.lower() and "not a" in text.lower()
        assert not parsed.downloads


def test_historical_claims_are_never_promoted_to_organizer_or_forecast():
    fleet = load(REPORT / "fleet-audit.json")
    assert len(fleet["rows"]) == 9
    for row in fleet["rows"]:
        assert row["organizer_confirmed"] is None and row["leaderboard_estimate"] is None
        assert row["safe_to_resubmit"] is False and row["unique_new_submission"] is False
        assert (ROOT / row["review_url"]).is_file()
    assert fleet["lineage"]["G25_equals_G30_inside_footprint"]
    assert fleet["lineage"]["h33_equals_r1_distance_gt_2"]
    assert fleet["lineage"]["pinn_additional_dots"] == 1200


def test_complete_owner_prompt_is_preserved_and_workflows_cover_research_tiff():
    import hashlib
    text = (ROOT / "README.md").read_text()
    section = text[text.index('<a id="current-owner-prompt">'):]
    receipt = load(REPORT / "prompt-preservation.json")
    assert hashlib.sha256(section.encode()).hexdigest() == receipt["sha256"]
    for name in ("review-tests.yml", "status-feed.yml"):
        workflow = (ROOT / ".github/workflows" / name).read_text()
        assert "--ids sample_submission labels" in workflow
        assert "scripts/verify_geothermal_chemistry_run.py" in workflow
    assert "find docs -type f" in (ROOT / ".github/workflows/status-feed.yml").read_text()
