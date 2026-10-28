"""End-to-end release, tamper-resistance, HTML link/ID, and workflow checks for CSR-1."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/research/2026-10-26-csr"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LABELS = ROOT / "data/raw/labels.tif"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n")


def inputs_available() -> None:
    if not (TEMPLATE.exists() and LABELS.exists()):
        pytest.skip("pinned sample_submission.tif and labels.tif required")


def test_csr_verifier_cli_contract():
    inputs_available()
    ok = subprocess.run([sys.executable, "scripts/verify_csr_run.py"], cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert "research_verdict=negative" in ok.stdout and "download_ok=True" in ok.stdout

    promo = subprocess.run(
        [sys.executable, "scripts/verify_csr_run.py", "--require-promote"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert promo.returncode == 2


@pytest.fixture
def isolated_csr(tmp_path, monkeypatch):
    inputs_available()
    from scripts import verify_csr_run as v

    directory = tmp_path / "docs/research/2026-10-26-csr"
    shutil.copytree(REPORT, directory)
    card = load(REPORT / "run-card.json")
    for rel in (
        card["published_tiff"],
        card["published_tiff"][:-4] + ".json",
        "src/gemsdoe30/csr_discontinuity.py",
        "scripts/run_csr_discontinuity.py",
        "data/raw/labels.tif",
    ):
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dest)
    monkeypatch.setattr(v, "ROOT", tmp_path)
    return v, directory, tmp_path


@pytest.mark.parametrize(
    "file,mutation,message",
    [
        ("run-card.json", lambda x: x.update(ok_to_submit=True), "recomputed readiness.json|submission flags violated"),
        ("run-card.json", lambda x: x.update(verdict="promote"), "recomputed readiness.json|submission flags violated"),
        ("run-card.json", lambda x: x.update(experiments_run=4), "experiment cap violated"),
        ("run-card.json", lambda x: x.update(raster_sha256="0" * 64), "GeoTIFF SHA-256 mismatch"),
        ("run-card.json", lambda x: x.update(note="z" * 141), "submission identity/note contract violated"),
        ("run-card.json", lambda x: x["holdout"].update(value=0.95), "holdout metric mismatch"),
        ("results.json", lambda x: x["feature_canaries"][0]["features"][0].update(max_symmetric_auc=0.95), "canary alarm"),
        ("novelty-dots.json", lambda x: x["comparisons"][0].update(candidate_fraction_within_3px_of_reference=0.75), "dot 3-px overlap violation"),
        ("novelty-surface.json", lambda x: x.update(candidate_sha256=load(REPORT / "run-card.json")["raster_sha256"]), "surface SHA"),
    ],
)
def test_csr_tampering_fails_closed(isolated_csr, file, mutation, message):
    v, directory, _ = isolated_csr
    path = directory / file
    payload = deepcopy(load(path))
    mutation(payload)
    dump(path, payload)
    with pytest.raises(ValueError, match=message):
        v.verify(directory, TEMPLATE)


def test_csr_runner_blocks_repeat_execution():
    from scripts import run_csr_discontinuity as runner

    with pytest.raises(RuntimeError, match="already exists"):
        runner.main()


class PageLinks(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.urls: list[str] = []
        self.ids: set[str] = set()
        self.downloads: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if d.get("id"):
            assert d["id"] not in self.ids, f"duplicate HTML id: {d['id']}"
            self.ids.add(d["id"])
        for attr in ("href", "src"):
            if d.get(attr):
                self.urls.append(d[attr])
        if tag == "a" and "download" in d and d.get("href"):
            self.downloads.append(d["href"])


@pytest.mark.parametrize(
    "name",
    [
        "index.html",
        "executive-summary.html",
        "csr-discontinuity-review.html",
        "priority-executive-summary.html",
    ]
    + [f"priority-GEMSDOE{s}.html" for s in (24, 25, 27, 28, 30, 31, 32, 33, 36)],
)
def test_csr_pages_links_downloads_and_decision_badges(name: str):
    path = ROOT / name
    text = path.read_text()
    parsed = PageLinks(text)
    for url in parsed.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
        assert target.is_relative_to(ROOT) and target.is_file(), f"{name} -> {url}"
        if parts.fragment and target.suffix == ".html":
            assert unquote(parts.fragment) in PageLinks(target.read_text()).ids, f"{name} -> {url}"

    research_tiff = "docs/downloads/gems30-offlattice-geothermal-structural-20261028-s7.tif"
    if name in {"index.html", "executive-summary.html", "csr-discontinuity-review.html"}:
        assert parsed.downloads == [load(REPORT / "run-card.json")["published_tiff"], research_tiff]
        assert "DUPLICATE-STOP" in text and "99.9864%" in text
        assert "Historical CSR-1 · research only" in text
        assert "fails the published-format validator" in text
        assert "OK TO DOWNLOAD: YES" not in text
        assert text.count("NOT APPROVED FOR SUBMISSION") == 1
        assert "HOLDOUT-DTI" in text and "60,988" in text
    elif name == "priority-executive-summary.html":
        assert "unverified" in text.lower() and "not a" in text.lower()
        assert parsed.downloads == [research_tiff]
        assert "Download research TIFF — NOT OK TO SUBMIT" in text
    elif name.startswith("priority-"):
        assert "unverified" in text.lower() and "not a" in text.lower()
        assert not parsed.downloads


def test_csr_fleet_audit_and_workflows_wired():
    fleet = load(REPORT / "fleet-audit.json")
    assert len(fleet["rows"]) == 9
    for row in fleet["rows"]:
        assert row["organizer_confirmed"] is None and row["leaderboard_estimate"] is None
        assert 0.30 <= row["csr1_fraction_within_3px"] <= 0.45
    readme = (ROOT / "README.md").read_text()
    prompt_tail = readme[readme.index('<a id="current-owner-prompt">') :]
    expected_sha = load(ROOT / "docs/research/2026-10-26-gdx/prompt-preservation.json")["sha256"]
    assert hashlib.sha256(prompt_tail.encode()).hexdigest() == expected_sha
    for wf in ("review-tests.yml", "status-feed.yml"):
        wf_text = (ROOT / ".github/workflows" / wf).read_text()
        assert "scripts/verify_csr_run.py" in wf_text  # preserved historical verifier
        assert "scripts/verify_registry_preflight.py" in wf_text
        assert "lattice-pin.json" in wf_text
