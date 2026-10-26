"""Small deterministic fixtures for frozen restore, cache integrity and public preview."""
from __future__ import annotations

import hashlib
import io
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


def test_fresh_priority_snapshot_cannot_overwrite_a_frozen_experiment_registry(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    frozen = tmp_path / "docs/research/texture-controls/registry.json"
    frozen.parent.mkdir(parents=True); frozen.write_text('{"frozen": true}\n')
    template = raster(tmp_path / "template.tif", np.zeros((4, 5)))
    with pytest.raises(ValueError, match="frozen experiment registry"):
        sync.snapshot(frozen, template)
    # The fail-closed guard runs before pins/API work and leaves historic bytes intact.
    assert frozen.read_text() == '{"frozen": true}\n'
    with pytest.raises(ValueError, match="inside the repository"):
        sync.require_new_snapshot_target(tmp_path.parent / "outside.json")


def test_priority_snapshot_records_surface_paths_without_claiming_they_are_usable(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    source = raster(tmp_path / "source.tif", np.eye(4, 5))
    content = source.read_bytes()
    blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    pins = tmp_path / "docs/research/priority-site-pins.json"
    pins.parent.mkdir(parents=True)
    pins.write_text(json.dumps({"rasters": [{"site": "SYNTHETIC", "repo": "test/synthetic",
                                                "ref": "not-used"}]}))
    ref = "b" * 40
    tree = {"sha": "tree-1", "truncated": False, "tree": [
        {"type": "blob", "path": "docs/downloads/candidate.tif", "sha": blob, "size": len(content)},
        {"type": "blob", "path": "outputs/oof_surface.npy", "sha": "c" * 40, "size": 99},
        {"type": "blob", "path": "models/predictions.npz", "sha": "d" * 40, "size": 88},
    ]}

    def fake_api(endpoint, *, raw=False):
        if endpoint.endswith("/commits/main"):
            return json.dumps({"sha": ref}).encode()
        if "/git/trees/" in endpoint:
            return json.dumps(tree).encode()
        assert raw and "docs/downloads/candidate.tif" in endpoint
        return content

    monkeypatch.setattr(sync, "api", fake_api)
    template = raster(tmp_path / "template.tif", np.zeros((4, 5)))
    output = tmp_path / "docs/research/registry-snapshots/synthetic.json"
    report = sync.snapshot(output, template)
    assert report["schema_version"] == 4
    discovery = report["continuous_surface_discovery"]
    assert discovery["status"] == "path-inventory-only" and discovery["candidate_count"] == 2
    assert {row["source_path"] for row in discovery["candidates"]} == {
        "outputs/oof_surface.npy", "models/predictions.npz"}
    assert all("not downloaded" in row["discovery_scope"] for row in discovery["candidates"])
    assert output.is_file() and len(report["rasters"]) == 1


def test_surface_metadata_inspection_never_promotes_or_compares_a_public_array(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    source = raster(tmp_path / "source.tif", np.eye(4, 5))
    tiff_bytes = source.read_bytes()
    tiff_blob = hashlib.sha1(f"blob {len(tiff_bytes)}\0".encode() + tiff_bytes).hexdigest()
    array_stream = io.BytesIO(); np.savez(array_stream, belief=np.zeros((4, 5), dtype="float32"))
    npz_bytes = array_stream.getvalue()
    npz_blob = hashlib.sha1(f"blob {len(npz_bytes)}\0".encode() + npz_bytes).hexdigest()
    pins = tmp_path / "docs/research/priority-site-pins.json"
    pins.parent.mkdir(parents=True)
    pins.write_text(json.dumps({"rasters": [{"site": "SYNTHETIC", "repo": "test/synthetic",
                                                "ref": "not-used"}]}))
    ref = "b" * 40
    tree = {"sha": "tree-1", "truncated": False, "tree": [
        {"type": "blob", "path": "docs/downloads/candidate.tif", "sha": tiff_blob, "size": len(tiff_bytes)},
        {"type": "blob", "path": "evidence/prediction_surface.tif", "sha": tiff_blob, "size": len(tiff_bytes)},
        {"type": "blob", "path": "evidence/oof_belief.npz", "sha": npz_blob, "size": len(npz_bytes)},
    ]}

    def fake_api(endpoint, *, raw=False):
        if endpoint.endswith("/commits/main"):
            return json.dumps({"sha": ref}).encode()
        if "/git/trees/" in endpoint:
            return json.dumps(tree).encode()
        assert raw
        return npz_bytes if endpoint.endswith("oof_belief.npz?ref=" + ref) else tiff_bytes

    monkeypatch.setattr(sync, "api", fake_api)
    template = raster(tmp_path / "template.tif", np.zeros((4, 5)))
    report = sync.snapshot(tmp_path / "docs/research/registry-snapshots/surface.json", template,
                           inspect_surfaces=True)
    inspected = report["continuous_surface_discovery"]
    assert inspected["status"] == "metadata-inspected"
    assert len(inspected["inspections"]) == 2
    geo = next(row for row in inspected["inspections"] if row["format"] == "GeoTIFF")
    archive = next(row for row in inspected["inspections"] if row["format"] == "NPZ")
    assert geo["grid_matches_template"] is True
    assert archive["any_array_matches_template_shape"] is True
    assert all(row["future_surface_comparison_eligibility"] == "unknown"
               and "not ranked" in row["inspection_scope"]
               for row in inspected["inspections"])


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


def test_newer_lane_and_generic_snapshot_cannot_be_overwritten(tmp_path, monkeypatch):
    from scripts import sync_priority_registry as sync
    monkeypatch.setattr(sync, "ROOT", tmp_path)
    monkeypatch.setattr(sync, "api", lambda *a, **k: pytest.fail("must fail before network"))
    for relative in ("docs/research/2026-10-26-gdx/registry.json", "docs/research/registry-snapshots/another.json"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'{"immutable": true}\n')
        with pytest.raises(ValueError, match="existing snapshot"):
            sync.require_new_snapshot_target(target)
        assert target.read_bytes() == b'{"immutable": true}\n'
