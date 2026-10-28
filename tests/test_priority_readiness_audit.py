"""Current audit must inspect pinned bytes, never convert format validity into approval."""
import copy
import json
from pathlib import Path
import sys

import pytest

from scripts import audit_priority_readiness as audit

ROOT = Path(__file__).resolve().parents[1]


def row():
    return copy.deepcopy(audit.load(audit.FLEET)["rows"][0])


def test_source_is_exact_immutable_and_in_named_repository():
    r = row()
    assert audit.source_endpoint(r).startswith("repos/buffedlizard55-lab/GEMSDOE24/contents/")
    assert "?ref=07345ea0604953d7efb858d9cfbc21e20c7aca0b" in audit.source_endpoint(r)
    for url in (r["source_url"].replace("/GEMSDOE24/", "/GEMSDOE25/"),
                r["source_url"].replace("07345ea0604953d7efb858d9cfbc21e20c7aca0b", "main"),
                r["source_url"] + "?redirect=bad", r["source_url"].replace("/docs/", "/../")):
        bad = dict(r, source_url=url)
        with pytest.raises(ValueError):
            audit.source_endpoint(bad)
    with pytest.raises(ValueError):
        audit.source_endpoint(dict(r, raster_sha256=""))


def test_missing_corrupt_or_bad_download_never_passes(tmp_path, monkeypatch):
    r = row()
    with pytest.raises(FileNotFoundError):
        audit.historical_path(r, tmp_path, restore=False)
    def wrong_bytes(endpoint, stream):
        stream.write(b"not the pinned raster")
    monkeypatch.setattr(audit, "stream_raw", wrong_bytes)
    with pytest.raises(ValueError, match="downloaded historical SHA-256"):
        audit.historical_path(r, tmp_path, restore=True)
    assert list(tmp_path.iterdir()) == []  # atomic failure, no orphan or false cache hit
    cache = tmp_path / f"{r['site']}-{r['raster_sha256']}.tif"
    cache.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="cached historical SHA-256"):
        audit.historical_path(r, tmp_path, restore=True)


def test_valid_cache_does_not_request_network(tmp_path, monkeypatch):
    r = row()
    r["raster_sha256"] = audit.hashlib.sha256(b"fixture").hexdigest()
    cache = tmp_path / f"{r['site']}-{r['raster_sha256']}.tif"
    cache.write_bytes(b"fixture")
    def unexpected(*args):
        pytest.fail("a pinned cache hit made a network request")
    monkeypatch.setattr(audit, "stream_raw", unexpected)
    assert audit.historical_path(r, tmp_path, restore=False) == cache


def test_saved_audit_labels_diagnostics_and_preserves_stop():
    receipt = audit.load(audit.OUTPUT)
    assert tuple(r["site"] for r in receipt["rows"]) == audit.SITES
    assert receipt["experiments_run"] == 0
    assert receipt["new_raster_generated"] is False
    assert receipt["holdout_dti"] is None
    assert receipt["organizer_confirmed_score"] is None
    for r in receipt["rows"]:
        assert r["unique_submission"] is False
        assert r["ok_to_submit"] is False
        assert r["comparison"]["dot_duplicate"] is True
        assert r["comparison"]["candidate_fraction_within_3px_of_reference"] > .99
        assert r["new_submission_score_estimate"] is None
        assert r["finite_inside"] is True
        assert r["inside_range"] == [0.0, 1.0]
        assert r["preplacement_surface_checked"] is False
    page = audit.render(receipt)
    assert "no submission download button" in page
    assert "not performance scores" in page
    assert "No remote GEMSDOE website was modified" in page
    assert ' download=' not in page
    assert ' download>' not in page
    assert 'href="docs/downloads/' not in page
    assert page.count("NO — duplicate-stop") == 9
    assert page.count("Unavailable; no forecast") == 9


def test_restore_only_does_not_rewrite_receipts(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(audit, "historical_path", lambda *a, **k: calls.append((a, k)))
    output = tmp_path / "do-not-write.json"
    monkeypatch.setattr(audit, "OUTPUT", output)
    monkeypatch.setattr(sys, "argv", ["audit", "--restore-only"])
    assert audit.main() == 0
    assert len(calls) == 9
    assert all(k == {"restore": True} for _, k in calls)
    assert not output.exists()


def test_check_recomputes_and_rejects_changed_evidence(tmp_path, monkeypatch):
    original = audit.load(audit.OUTPUT)
    output = tmp_path / "audit.json"
    page = tmp_path / "page.html"
    output.write_text(json.dumps(original, indent=2, allow_nan=False) + "\n")
    page.write_text(audit.render(original))
    monkeypatch.setattr(audit, "OUTPUT", output)
    monkeypatch.setattr(audit, "PAGE", page)
    monkeypatch.setattr(audit, "audit", lambda **kwargs: original)
    monkeypatch.setattr(sys, "argv", ["audit", "--check"])
    assert audit.main() == 0
    before = page.read_text()
    page.write_text(before + "stale")
    with pytest.raises(SystemExit, match="stale priority"):
        audit.main()
    page.write_text(before)
    tampered = copy.deepcopy(original)
    tampered["rows"][0]["ok_to_submit"] = True
    output.write_text(json.dumps(tampered, indent=2) + "\n")
    with pytest.raises(SystemExit, match="stale priority"):
        audit.main()


def test_conflicting_modes_are_rejected(monkeypatch):
    for flags in (("--restore", "--check"), ("--restore-only", "--check"), ("--restore-only", "--restore")):
        monkeypatch.setattr(sys, "argv", ["audit", *flags])
        with pytest.raises(SystemExit) as exc:
            audit.main()
        assert exc.value.code == 2


def test_real_bytes_reproduce_audit_offline():
    cache = ROOT / "data/raw/priority-readiness"
    if not cache.is_dir():
        pytest.skip("restore the nine pinned historical references to remeasure")
    result = audit.audit(template=ROOT / "data/raw/sample_submission.tif",
                         lattice=ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif", cache=cache)
    assert audit.same_measurement(audit.load(audit.OUTPUT), result)
    assert audit.render(result) == audit.PAGE.read_text()
