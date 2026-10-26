"""Regression checks for PTA-1 unique downloadable release + archived TDX-1/TDX-C2 records."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "docs/research/phase-tilt-asymmetry"
ARCHIVED_TDX1 = ROOT / "docs/research/texture-displacement"


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.urls = []
        self.ids = set()
        self.downloads = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.ids.update([attrs["id"]] if "id" in attrs else [])
        for key in ("href", "src"):
            if key in attrs:
                self.urls.append(attrs[key])
        if tag == "a" and "download" in attrs:
            self.downloads.append(attrs.get("href"))


@pytest.mark.parametrize("relative", ["index.html", "executive-summary.html", "experiment-review.html", "docs/index.html"])
def test_generated_pages_have_real_local_links_and_valid_html_anchors(relative):
    path = ROOT / relative
    page = Links(path.read_text())
    for url in page.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
        assert target.is_relative_to(ROOT), url
        assert target.is_file(), url
        if parts.fragment and target.suffix == ".html":
            assert unquote(parts.fragment) in Links(target.read_text()).ids, url


@pytest.mark.parametrize("relative", ["index.html", "executive-summary.html"])
def test_download_and_copy_controls_bind_to_the_current_negative_artifact(relative):
    card = json.loads((CURRENT / "run-card.json").read_text())
    html = (ROOT / relative).read_text()
    parsed = Links(html)
    assert parsed.downloads == [card["published_tiff"]]
    assert "UNIQUE TIFF" in html
    assert "NOT APPROVED FOR SUBMISSION" in html and "Do not submit" in html
    assert card["submission_name"] in html
    assert "No competition slot selected or used" in html
    assert (ROOT / card["published_tiff"]).is_file()
    if relative == "executive-summary.html":
        assert card["note"] in html
        assert {"submission-name", "submission-note", "copy-status"} <= parsed.ids
        assert len(card["note"]) <= 140


def test_complete_current_prompt_and_every_reported_claim_remain_quarantined():
    import csv
    text = (ARCHIVED_TDX1 / "owner-prompt.txt").read_text()
    readme = (ROOT / "README.md").read_text()
    assert text.strip() in readme
    assert '<a id="current-owner-prompt"></a>' in readme
    assert "Maximize P(Win)" in text and "Own the Outcome" in text
    rows = list(csv.DictReader((ARCHIVED_TDX1 / "owner-claims.csv").open()))
    assert len(rows) == 119
    assert all("UNVERIFIED" in r["evidence"] and not r["organizer_receipt_url"] for r in rows)
    assert any(r["site"] == "GEMSDOE91" and r["claimed_score"] == "" for r in rows)
    assert any(r["site"] == "GEMSDOE32" and r["claimed_score"] == "0.2778" for r in rows)


def test_recomputed_evidence_cannot_use_a_truncated_ci_or_a_changed_paired_delta():
    from scripts.verify_current_run import check_equal
    expected = {"candidate_minus": {"core19": {"value": -.06, "ci95": [-.08, -.04]}}}
    check_equal(deepcopy(expected), expected)
    for changed in [
        {"candidate_minus": {"core19": {"value": -.06, "ci95": [-.08]}}},
        {"candidate_minus": {"core19": {"value": .06, "ci95": [.04, .08]}}},
        {"candidate_minus": {"core19": {"value": float("nan"), "ci95": [-.08, -.04]}}},
    ]:
        with pytest.raises(ValueError):
            check_equal(changed, expected)


@pytest.fixture
def isolated_evidence(tmp_path, monkeypatch):
    from scripts import verify_current_run as verifier
    shutil.copytree(CURRENT, tmp_path / "docs/research/phase-tilt-asymmetry")
    shutil.copy(ROOT / "docs/current-run.json", tmp_path / "docs/current-run.json")
    card = json.loads((CURRENT / "run-card.json").read_text())
    raster = tmp_path / card["published_tiff"]
    raster.parent.mkdir(parents=True)
    shutil.copy(ROOT / card["published_tiff"], raster)
    shutil.copy((ROOT / card["published_tiff"]).with_suffix(".json"), raster.with_suffix(".json"))
    template = tmp_path / "template.tif"
    template.write_bytes(b"synthetic pinned-template bytes")
    directory = tmp_path / "docs/research/phase-tilt-asymmetry"
    for name in ("novelty-surface.json", "novelty-dots.json"):
        d = json.loads((directory / name).read_text())
        d["template_sha256"] = hashlib.sha256(template.read_bytes()).hexdigest()
        (directory / name).write_text(json.dumps(d))
    recomputed = json.loads((directory / "results.json").read_text())["summary"]
    (tmp_path / "src/gemsdoe30").mkdir(parents=True)
    shutil.copy(ROOT / "src/gemsdoe30/phase_tilt.py", tmp_path / "src/gemsdoe30/phase_tilt.py")
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "validate_submission_file", lambda *args: SimpleNamespace(passed=True))
    monkeypatch.setattr(verifier, "spatial_bootstrap", lambda *args, **kwargs: deepcopy(recomputed))
    return verifier, directory, tmp_path / "docs/current-run.json", template


@pytest.fixture
def isolated_archived_tdx1(tmp_path, monkeypatch):
    from scripts import verify_current_run as verifier
    shutil.copytree(ARCHIVED_TDX1, tmp_path / "docs/research/texture-displacement")
    pointer = tmp_path / "docs/tdx1-pointer.json"
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({
        "run_card": "docs/research/texture-displacement/run-card.json",
        "readiness": "docs/research/texture-displacement/readiness.json",
    }))
    card = json.loads((ARCHIVED_TDX1 / "run-card.json").read_text())
    raster = tmp_path / card["published_tiff"]
    raster.parent.mkdir(parents=True)
    shutil.copy(ROOT / card["published_tiff"], raster)
    shutil.copy((ROOT / card["published_tiff"]).with_suffix(".json"), raster.with_suffix(".json"))
    template = tmp_path / "template.tif"
    template.write_bytes(b"synthetic pinned-template bytes")
    directory = tmp_path / "docs/research/texture-displacement"
    for name in ("novelty-surface.json", "novelty-dots.json", "novelty-parallel-surface.json", "novelty-parallel-dots.json"):
        d = json.loads((directory / name).read_text())
        d["template_sha256"] = hashlib.sha256(template.read_bytes()).hexdigest()
        (directory / name).write_text(json.dumps(d))
    recomputed = json.loads((directory / "results.json").read_text())["summary"]
    additional = json.loads((directory / "registry-parallel-addendum.json").read_text())
    for row in additional["rasters"]:
        dest = tmp_path / row["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / row["path"], dest)
    (tmp_path / "src/gemsdoe30").mkdir(parents=True)
    shutil.copy(ROOT / "src/gemsdoe30/texture.py", tmp_path / "src/gemsdoe30/texture.py")
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "validate_submission_file", lambda *args: SimpleNamespace(passed=True))
    monkeypatch.setattr(verifier, "spatial_bootstrap", lambda *args, **kwargs: deepcopy(recomputed))
    return verifier, directory, pointer, template


def test_full_verifier_rejects_forged_paired_confidence_intervals(isolated_evidence):
    verifier, directory, pointer, template = isolated_evidence
    decision = verifier.verify(pointer, template)
    assert decision["research_verdict"] == "negative"
    assert decision["download_ok"] is True
    assert decision["observed_registry"]["dots"]["registry_entries_compared"] == 194
    results = json.loads((directory / "results.json").read_text())
    results["summary"]["candidate_minus"]["core19"]["ci95"] = [.01, .1]
    (directory / "results.json").write_text(json.dumps(results))
    with pytest.raises(ValueError, match="numeric mismatch"):
        verifier.verify(pointer, template)


def test_full_verifier_rejects_repeated_reference_rows_despite_correct_count(isolated_evidence):
    verifier, directory, pointer, template = isolated_evidence
    audit = json.loads((directory / "novelty-dots.json").read_text())
    audit["comparisons"][1] = deepcopy(audit["comparisons"][0])
    (directory / "novelty-dots.json").write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="inventory/stage"):
        verifier.verify(pointer, template)


def test_full_verifier_rejects_changed_template_bytes(isolated_evidence):
    verifier, directory, pointer, template = isolated_evidence
    template.write_bytes(b"different bytes despite a hypothetical matching grid")
    with pytest.raises(ValueError, match="registry/template hash"):
        verifier.verify(pointer, template)


@pytest.mark.parametrize("directory", [CURRENT, ARCHIVED_TDX1])
def test_published_files_keep_original_binary_support_and_exact_hash(directory):
    np = pytest.importorskip("numpy")
    rasterio = pytest.importorskip("rasterio")
    card = json.loads((directory / "run-card.json").read_text())
    raster = ROOT / card["published_tiff"]
    with raster.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == card["raster_sha256"]
    manifest = json.loads(raster.with_suffix(".json").read_text())
    assert manifest["output_sha256"] == card["raster_sha256"]
    assert manifest["submission_approved"] is card["submission_approved"] is False
    assert card["slot_selected"] is False and card["verdict"] == "negative"
    with rasterio.open(raster) as ds:
        values = ds.read(1)
        finite = np.isfinite(values)
        assert ds.count == 1 and ds.dtypes == ("float32",) and ds.crs.to_epsg() == 32611
        assert ds.shape == (3730, 3292)
        assert np.array_equal(np.unique(values[finite]), [0., 1.])
        assert np.count_nonzero(values[finite]) == card["validator_output"]["emitted_dots"]
    registry = json.loads((directory / "registry.json").read_text())
    assert card["raster_sha256"] not in {r["sha256"] for r in registry["rasters"]}


def test_status_feed_uses_current_pointer_and_never_advertises_range_immunity(tmp_path):
    template = ROOT / "data/raw/sample_submission.tif"
    if not template.exists():
        pytest.skip("small pinned template required; CI restores it before tests")
    output = tmp_path / "status.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_status.py"), "--skip-tests", "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    status = json.loads(output.read_text())
    card = json.loads((CURRENT / "run-card.json").read_text())
    assert status["current_artifact_inspection"]["verified_now"] is True
    assert status["current_release_decision"]["raster_sha256"] == card["raster_sha256"]
    assert status["current_release_decision"]["download_ok"] is True
    assert status["current_release_decision"]["research_verdict"] == "negative"
    assert status["current_release_decision"]["submission_approved"] is False
    assert not status["any_candidate_promoted"]
    assert status["archived_stopped_attempt"]["receipt_inspection"]["verified_now"] is True
    assert status["archived_stopped_attempt"]["decision"]["download_ok"] is False
    assert status["archived_stopped_attempt"]["decision"]["research_verdict"] == "negative"
    assert status["archived_stopped_attempt"]["public_download"] is False
    assert all(row["range_error_immune"] is None for row in status["downloads"])
    assert status["submission_format"]["local_validation_guarantees_portal_acceptance"] is False
    assert status["score_evidence"]["validated_organizer_submission_receipts"] == []


def test_generated_site_is_exactly_reproducible_from_reopened_artifact():
    from scripts.build_research_site import build
    template = ROOT / "data/raw/sample_submission.tif"
    if not template.exists():
        pytest.skip("small pinned template required; CI restores it before tests")
    for path, content in build(template).items():
        assert path.read_bytes() == (content.encode() if isinstance(content, str) else content)


def test_new_local_rasters_cannot_be_silently_omitted_from_late_registry(isolated_archived_tdx1):
    verifier, directory, pointer, template = isolated_archived_tdx1
    decision = verifier.verify(pointer, template)
    # 104 frozen + 4 late (PR #28) + 2 G30-S20 late twins (PR #29) + 1 PTA-1 = 111.
    assert decision["observed_registry"]["dots"]["registry_entries_compared"] == 111
    (directory / "registry-parallel-addendum.json").unlink()
    with pytest.raises(ValueError, match="explicit late-registry audit"):
        verifier.verify(pointer, template)


def test_late_reference_deletion_or_tampering_does_not_restore_a_green_old_snapshot(isolated_archived_tdx1):
    verifier, directory, pointer, template = isolated_archived_tdx1
    additional = json.loads((directory / "registry-parallel-addendum.json").read_text())
    path = verifier.local_path(additional["rasters"][0]["path"])
    path.unlink()
    with pytest.raises(ValueError, match="every new local reference identity"):
        verifier.verify(pointer, template)


def test_failed_write_verification_does_not_change_any_canonical_receipt(isolated_evidence):
    verifier, directory, pointer, template = isolated_evidence
    card_path = directory / "run-card.json"
    card = json.loads(card_path.read_text())
    card["submission_approved"] = True
    card_path.write_text(json.dumps(card))
    before_card, before_ready = card_path.read_bytes(), (directory / "readiness.json").read_bytes()
    with pytest.raises(ValueError, match="approval/verdict"):
        verifier.verify(pointer, template, write=True)
    assert card_path.read_bytes() == before_card
    assert (directory / "readiness.json").read_bytes() == before_ready


def test_pta1_rerun_preflight_preserves_frozen_receipts():
    started = json.loads((CURRENT / "started.json").read_text())
    script = ROOT / "scripts/run_phase_tilt_asymmetry.py"
    assert hashlib.sha256(script.read_bytes()).hexdigest() == started["script_sha256"]
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CURRENT.glob("*.json")}
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0 and "frozen PTA-1 evidence already exists" in result.stderr
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in CURRENT.glob("*.json")}


def test_download_competition_data_check_only_exits_2_cleanly(tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/download_competition_data.sh"), "--data-dir", str(tmp_path), "--check-only"],
        cwd=ROOT, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2
    assert "CORE COMMANDS" not in result.stderr
