"""Small deterministic fixtures for frozen restore, cache integrity and public preview."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import pytest
import rasterio
from affine import Affine


TRANSFORM = Affine(100, 0, 243350, 0, -100, 4508550)


def raster(path, values, *, nodata=float("nan")):
    values = np.asarray(values, dtype="float32")
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(path, "w", driver="GTiff", height=values.shape[1], width=values.shape[2],
                       count=values.shape[0], dtype="float32", crs="EPSG:32611", transform=TRANSFORM,
                       nodata=nodata) as ds:
        ds.write(values)
    return path


def registry_row(path, name, *, aligned=True):
    content = path.read_bytes()
    blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    return {"site": "SYNTHETIC", "repo": "test/synthetic-not-a-real-source", "ref": "a" * 40,
            "source_path": f"docs/downloads/{name}.tif", "git_blob_sha1": blob,
            "expected_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "path": f"data/raw/registry-expanded/SYNTHETIC-{blob}.tif", "aligned": aligned}


def test_restore_only_uses_frozen_refs_preserves_json_and_rechecks_cached_blobs(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    template = raster(tmp_path / "template.tif", np.zeros((7, 8)))
    good = raster(tmp_path / "source.tif", np.eye(7, 8))
    off_grid = raster(tmp_path / "toy.tif", np.zeros((2, 3)))
    rows = [registry_row(good, "good"), registry_row(off_grid, "off-grid", aligned=False)]
    frozen = tmp_path / "registry.json"
    frozen.write_text(json.dumps({"rasters": [rows[0]], "exclusions": [rows[1]], "complete": False}, indent=2))
    original = frozen.read_bytes(); calls = []

    def api(endpoint, *, raw=False):
        assert raw and "?ref=" + "a" * 40 in endpoint
        assert "/commits/main" not in endpoint and "/git/trees/" not in endpoint
        calls.append(endpoint)
        return off_grid.read_bytes() if "off-grid" in endpoint else good.read_bytes()

    monkeypatch.setattr(sync, "api", api)
    sync.restore_frozen(frozen, template)
    assert len(calls) == 2 and frozen.read_bytes() == original
    monkeypatch.setattr(sync, "api", lambda *a, **kw: pytest.fail("cached restore must not fetch"))
    sync.restore_frozen(frozen, template)
    assert frozen.read_bytes() == original
    cached = tmp_path / rows[0]["path"]
    content = cached.read_bytes(); cached.write_bytes(content[:-1] + bytes([content[-1] ^ 1]))
    with pytest.raises(ValueError, match="cached Git blob mismatch"):
        sync.restore_frozen(frozen, template)
    assert frozen.read_bytes() == original


def test_restore_rejects_wrong_download_before_publishing_a_cached_file(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    source = raster(tmp_path / "source.tif", np.zeros((4, 5)))
    row = registry_row(source, "source")
    monkeypatch.setattr(sync, "api", lambda *a, **kw: b"wrong Git blob")
    with rasterio.open(source) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    with pytest.raises(ValueError, match="Git blob mismatch"):
        sync.restore_row(row, grid)
    assert not (tmp_path / row["path"]).exists()


@pytest.fixture
def prepared(tmp_path):
    from scripts.prepare_data import prepare
    shape = (8, 9); template_values = np.zeros(shape, dtype="float32"); template_values[0, 0] = np.nan
    template = raster(tmp_path / "template.tif", template_values)
    features = np.arange(2 * 8 * 9, dtype="float32").reshape(2, 8, 9)
    features[:, 1, 1] = np.nan
    feature_path = raster(tmp_path / "features.tif", features)
    labels = np.zeros(shape, dtype="float32"); labels[3, 4] = 1; labels[0, 0] = -1
    labels_path = raster(tmp_path / "labels.tif", labels, nodata=-1)
    output = tmp_path / "processed"
    prepare(feature_path, labels_path, template, output)
    return output


def test_full_cell_cache_verification_hashes_all_four_arrays(prepared):
    from scripts.verify_prepared_cache import verify
    receipt = verify(prepared)
    assert receipt["all_cells_match_raw_sources"] is True
    assert receipt["windows_checked"] == 1
    assert set(receipt["array_sha256"]) == {"features_raw.npy", "labels.npy", "valid.npy", "label_valid.npy"}
    assert receipt["organizer_authenticated"] is False and receipt["is_performance_measurement"] is False


@pytest.mark.parametrize("name", ["features_raw.npy", "labels.npy", "valid.npy", "label_valid.npy"])
def test_cache_verifier_detects_changed_values_not_just_unchanged_source_hashes(prepared, name):
    from scripts.verify_prepared_cache import verify
    array = np.load(prepared / name, mmap_mode="r+")
    if array.ndim == 3:
        array[0, 4, 4] += 1
    else:
        array[4, 4] = not array[4, 4]
    array.flush()
    with pytest.raises(ValueError, match="value mismatch"):
        verify(prepared)


def test_static_preview_accepts_preview_hosts_but_never_serves_private_paths(tmp_path, monkeypatch):
    from http.server import ThreadingHTTPServer
    from scripts import serve_research_site as preview
    (tmp_path / "index.html").write_text("public overview")
    (tmp_path / ".git").mkdir(); (tmp_path / ".git/config").write_text("private config")
    (tmp_path / "public-looking.txt").symlink_to(tmp_path / ".git/config")
    monkeypatch.setattr(preview, "ROOT", tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), preview.PublicHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        req = Request(origin + "/", headers={"Host": "8000-example.e2b.app"})
        with urlopen(req, timeout=5) as response:
            assert response.status == 200 and response.read() == b"public overview"
            assert response.headers.get("X-Frame-Options") is None
        for path in ("/.git/config", "/%2Egit/config", "/data/raw/labels.tif", "/outputs/x", "/public-looking.txt"):
            with pytest.raises(HTTPError) as exc:
                urlopen(origin + path, timeout=5)
            assert exc.value.code == 403
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
