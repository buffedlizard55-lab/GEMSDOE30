"""End-to-end and tamper-rejection regression tests for lane G30-TAD."""

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
TAD = ROOT / "docs/research/tilt-alteration-discontinuity"
POINTER = TAD / "current-run.json"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"


class PageLinks(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.urls: list[str] = []
        self.ids: set[str] = set()
        self.downloads: list[str] = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs):
        d = dict(attrs)
        if "id" in d:
            self.ids.add(d["id"])
        for k in ("href", "src"):
            if k in d:
                self.urls.append(d[k])
        if tag == "a" and "download" in d and "href" in d:
            self.downloads.append(d["href"])


@pytest.mark.parametrize(
    "relative",
    [
        "index.html",
        "executive-summary.html",
        "geothermal-tilt-alteration-review.html",
        "experiment-review.html",
        "priority-registry-review.html",
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/geothermal-tilt-alteration-review.html",
    ],
)
def test_tad_pages_have_valid_links_anchors_and_gate_banners(relative: str):
    path = ROOT / relative
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    parsed = PageLinks(text)
    for url in parsed.urls:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
        assert target.is_relative_to(ROOT), url
        assert target.is_file(), url
        if parts.fragment and target.suffix == ".html":
            assert unquote(parts.fragment) in PageLinks(target.read_text(encoding="utf-8")).ids, url


def test_tad_subpage_and_executive_summary_expose_clear_gate_and_deadline_facts():
    card = json.loads((TAD / "run-card.json").read_text())
    sub = (ROOT / "geothermal-tilt-alteration-review.html").read_text(encoding="utf-8")
    guide = (ROOT / "executive-summary.html").read_text(encoding="utf-8")
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    parsed_sub = PageLinks(sub)

    assert set(parsed_sub.downloads) == {card["published_tiff"], card["companion_nan_tiff"]}
    assert {"tad-name", "tad-note", "copy-status"} <= parsed_sub.ids
    assert card["submission_name"] in sub
    assert card["note"] in sub and len(card["note"]) <= 140
    assert (ROOT / "docs/assets/tad24-support.png").is_file()

    for html in (home, guide, sub):
        assert "G30-TAD" in html
        assert "Do not spend a weekly slot." in html
        assert "51.44%" in html

    assert "5:00 p.m. ET" in guide
    assert "0.4413" in guide
    assert "Predicted values must be in range [0, 1]" in guide


def test_tad_real_verifier_and_cli_exit_codes():
    if not TEMPLATE.is_file():
        pytest.skip("sample_submission.tif required")
    from scripts.verify_tad_run import verify as verify_tad
    from scripts.verify_current_run import verify as verify_dispatch

    ready = verify_tad(POINTER, TEMPLATE)
    dispatched = verify_dispatch(POINTER, TEMPLATE)
    assert ready == dispatched
    assert ready["download_ok"] is True
    assert ready["ok_to_submit"] is False
    assert ready["research_verdict"] == "negative"
    assert ready["submission_approved"] is False
    assert ready["slot_selected"] is False

    p_ok = subprocess.run([sys.executable, str(ROOT / "scripts/verify_tad_run.py")], cwd=ROOT, capture_output=True, text=True)
    assert p_ok.returncode == 0, p_ok.stderr

    p_req = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_tad_run.py"), "--require-promote"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert p_req.returncode == 2


def test_tad_published_geotiffs_obey_strict_binary_range_and_collar_contracts():
    if not TEMPLATE.is_file():
        pytest.skip("sample_submission.tif required")
    np = pytest.importorskip("numpy")
    rasterio = pytest.importorskip("rasterio")
    from scipy.ndimage import distance_transform_edt
    from gemsdoe30.submission import valid_template_mask, validate_submission_file

    card = json.loads((TAD / "run-card.json").read_text())
    z_path = ROOT / card["published_tiff"]
    n_path = ROOT / card["companion_nan_tiff"]

    with rasterio.open(TEMPLATE) as tpl:
        valid = valid_template_mask(tpl, np)
        cat = (tpl.read(1) == 1) & valid
        tpl_grid = (tpl.shape, tpl.crs, tpl.transform)

    near = distance_transform_edt(~cat) <= 2.0
    assert validate_submission_file(n_path, TEMPLATE).passed

    with rasterio.open(z_path) as dsz, rasterio.open(n_path) as dsn:
        az = dsz.read(1)
        an = dsn.read(1)
        assert (dsz.shape, dsz.crs, dsz.transform) == tpl_grid
        assert (dsn.shape, dsn.crs, dsn.transform) == tpl_grid
        assert dsz.nodata is None
        assert np.isfinite(az).all()
        assert float(az.min()) == 0.0 and float(az.max()) == 1.0
        assert np.all(az[~valid] == 0.0)
        assert np.isnan(an[~valid]).all()
        assert np.array_equal(az[valid], an[valid])
        assert np.isin(az[valid], (0.0, 1.0)).all()
        assert int((az[valid] > 0).sum()) == 38000
        assert int((az[cat] > 0).sum()) == 0
        assert int(((az > 0) & valid & near).sum()) == 0


@pytest.fixture
def isolated_tad(tmp_path, monkeypatch):
    if not TEMPLATE.is_file():
        pytest.skip("sample_submission.tif required")
    from scripts import verify_tad_run as vtad

    tad_dst = tmp_path / "docs/research/tilt-alteration-discontinuity"
    shutil.copytree(TAD, tad_dst)
    (tmp_path / "src/gemsdoe30").mkdir(parents=True)
    for mod in ("__init__.py", "tilt_alteration.py", "holdout.py", "submission.py", "emission.py"):
        shutil.copy(ROOT / "src/gemsdoe30" / mod, tmp_path / "src/gemsdoe30" / mod)

    card = json.loads((tad_dst / "run-card.json").read_text())
    for key in ("published_tiff", "companion_nan_tiff"):
        rel = card[key]
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dst)
        shutil.copy((ROOT / rel).with_suffix(".json"), dst.with_suffix(".json"))

    add_path = tad_dst / "registry-parallel-addendum.json"
    if add_path.is_file():
        for row in json.loads(add_path.read_text())["rasters"]:
            dst = tmp_path / row["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / row["path"], dst)

    monkeypatch.setattr(vtad, "ROOT", tmp_path)
    return vtad, tad_dst, tad_dst / "current-run.json", TEMPLATE


def test_tad_verifier_rejects_forged_promotion_or_ci_or_canary_or_overlap(isolated_tad):
    vtad, tad_dst, ptr, tpl = isolated_tad
    assert vtad.verify(ptr, tpl)["ok_to_submit"] is False

    # 1. Forged ok_to_submit / verdict on run card
    orig_card = json.loads((tad_dst / "run-card.json").read_text())
    bad_card = deepcopy(orig_card)
    bad_card["ok_to_submit"] = True
    bad_card["verdict"] = "promote"
    (tad_dst / "run-card.json").write_text(json.dumps(bad_card))
    with pytest.raises(ValueError, match="contradict machine gates"):
        vtad.verify(ptr, tpl)
    (tad_dst / "run-card.json").write_text(json.dumps(orig_card))

    # 2. Forged positive paired CI against core19
    orig_e1 = json.loads((tad_dst / "results-e1.json").read_text())
    bad_e1 = deepcopy(orig_e1)
    bad_e1["summary"]["candidate_minus"]["core19"]["ci95"] = [0.005, 0.025]
    (tad_dst / "results-e1.json").write_text(json.dumps(bad_e1))
    with pytest.raises(ValueError, match="numeric mismatch"):
        vtad.verify(ptr, tpl)

    # 3. Forged canary AUC > 0.90 masked as alarm=False
    bad_e1_canary = deepcopy(orig_e1)
    bad_e1_canary["feature_canaries"][0]["features"][0]["raw_auc"] = 0.94
    bad_e1_canary["feature_canaries"][0]["features"][0]["alarm_above_0_90"] = False
    (tad_dst / "results-e1.json").write_text(json.dumps(bad_e1_canary))
    with pytest.raises(ValueError, match="canary alarm boolean"):
        vtad.verify(ptr, tpl)
    (tad_dst / "results-e1.json").write_text(json.dumps(orig_e1))

    # 4. Duplicate reference row in novelty-dots.json
    orig_dots = json.loads((tad_dst / "novelty-dots.json").read_text())
    bad_dots = deepcopy(orig_dots)
    bad_dots["comparisons"][1] = deepcopy(bad_dots["comparisons"][0])
    (tad_dst / "novelty-dots.json").write_text(json.dumps(bad_dots))
    with pytest.raises(ValueError, match="novelty-dots"):
        vtad.verify(ptr, tpl)


def test_tad_rerun_preflight_preserves_all_frozen_receipts():
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in TAD.glob("*.json")}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_tilt_alteration.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "refusing to overwrite frozen experiment receipts" in proc.stderr
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in TAD.glob("*.json")}

