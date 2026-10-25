#!/usr/bin/env python3
"""Snapshot all published TIFFs in the nine priority repos; never attest global coverage.

Uses immutable GitHub tree/contents API reads, stores large rasters under ignored
``data/raw/registry-expanded``, and records hashes, grids, aliases and exclusions.
No competition website monitoring or competition authentication is performed.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsdoe30.github_data import stream_raw


def api(endpoint: str, *, raw: bool = False) -> bytes:
    command = ["gh", "api", endpoint]
    if raw:
        with tempfile.TemporaryFile() as stream:
            stream_raw(endpoint, stream)
            stream.seek(0)
            return stream.read()
    return subprocess.check_output(command, timeout=120)


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def restore_row(row: dict, grid) -> dict:
    import rasterio
    path = ROOT / "data/raw/registry-expanded" / f"{row['site']}-{row['git_blob_sha1']}.tif"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        content = api(f"repos/{row['repo']}/contents/{row['source_path']}?ref={row['ref']}", raw=True)
        # Verify Git's own blob identity as well as local SHA-256.
        blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        if len(content) != row["expected_bytes"] or blob != row["git_blob_sha1"]:
            raise ValueError(f"Git blob mismatch: {row['source_path']}")
        temp = path.with_suffix(".partial")
        temp.write_bytes(content)
        temp.replace(path)
    content = path.read_bytes()
    blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    if len(content) != row["expected_bytes"] or blob != row["git_blob_sha1"]:
        raise ValueError(f"cached Git blob mismatch: {path}")
    result = {**row, "path": str(path.relative_to(ROOT)), "sha256": sha(path),
              "source_url": f"https://github.com/{row['repo']}/blob/{row['ref']}/{row['source_path']}"}
    with rasterio.open(path) as ds:
        aligned = ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid
        result["aligned"] = aligned
        result["shape"] = list(ds.shape)
        if not aligned:
            result["excluded_reason"] = "Not a single-band raster on the competition template grid"
    return result



def snapshot(output: Path, template: Path) -> dict:
    import rasterio

    pins = json.loads((ROOT / "docs/research/priority-site-pins.json").read_text())
    with rasterio.open(template) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    inventory, snapshots = [], []
    for row in pins["rasters"]:
        repo = row["repo"]
        # Resolve once, then pin every tree and blob request to this exact commit.
        ref = json.loads(api(f"repos/{repo}/commits/main"))["sha"]
        tree = json.loads(api(f"repos/{repo}/git/trees/{ref}?recursive=1"))
        if tree.get("truncated"):
            raise ValueError(f"truncated source tree: {repo}")
        items = [item for item in tree["tree"] if item["type"] == "blob"
                 and item["path"].startswith("docs/downloads/")
                 and item["path"].lower().endswith((".tif", ".tiff"))]
        surfaces = [item["path"] for item in tree["tree"]
                    if item["type"] == "blob" and item["path"].endswith((".npz", ".npy"))
                    and any(word in item["path"].lower() for word in ("oof", "surface", "prob"))]
        snapshots.append({"site": row["site"], "repo": repo, "ref": ref,
                          "tree_sha": tree["sha"], "published_tiffs": len(items),
                          "other_array_paths_not_assumed_grid_aligned": surfaces})
        for item in items:
            inventory.append({"site": row["site"], "repo": repo, "ref": ref,
                              "source_path": item["path"], "git_blob_sha1": item["sha"],
                              "expected_bytes": item["size"]})

    with ThreadPoolExecutor(max_workers=4) as executor:
        restored = list(executor.map(lambda row: restore_row(row, grid), inventory))
    # Keep every source alias but avoid repeating byte-identical comparisons.
    rasters, by_sha, exclusions = [], {}, []
    for row in restored:
        if not row["aligned"]:
            exclusions.append(row)
            continue
        if row["sha256"] in by_sha:
            by_sha[row["sha256"]]["aliases"].append(row["source_url"])
        else:
            row["aliases"] = [row["source_url"]]
            by_sha[row["sha256"]] = row
            rasters.append(row)
    result = {
        "schema_version": 2,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": False,
        "coverage": "All docs/downloads/**/*.tif[f] at the recorded nine main-branch snapshots; NOT the complete parallel-run registry.",
        "published_tiff_snapshot_inventory_complete": True,
        "missing_evidence": ["Other parallel sessions and repositories", "Underlying continuous surfaces for most published dots"],
        "organizer_authenticated": False,
        "snapshots": snapshots, "source_files": len(restored),
        "unique_aligned_byte_sequences": len(rasters), "rasters": rasters, "exclusions": exclusions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Snapshotted {len(restored)} TIFFs; {len(rasters)} unique aligned files; {len(exclusions)} excluded. Global coverage incomplete.")
    return result


def restore_frozen(path: Path, template: Path) -> None:
    """Restore exact recorded references without changing the frozen JSON bytes."""
    import rasterio
    manifest = json.loads(path.read_text())
    with rasterio.open(template) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    rows = manifest["rasters"] + manifest.get("exclusions", [])
    def check(row):
        restored = restore_row(row, grid)
        if restored["sha256"] != row["sha256"] or restored["aligned"] != row["aligned"]:
            raise ValueError(f"frozen registry identity mismatch: {row['path']}")
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(check, rows))
    print(f"Restored/verified {len(rows)} frozen files; registry JSON unchanged; no new inventory or experiment")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/research/texture-displacement/registry.json"))
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--restore-only", action="store_true",
                        help="restore/verify exact references in --output; never refresh or rewrite that snapshot")
    args = parser.parse_args()
    if args.restore_only:
        restore_frozen(args.output, args.template)
    else:
        snapshot(args.output, args.template)


if __name__ == "__main__":
    main()
