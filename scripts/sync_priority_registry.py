#!/usr/bin/env python3
"""Snapshot public priority TIFFs without silently mutating frozen experiment evidence.

A fresh public-source snapshot is discovery evidence only: it inventories GeoTIFFs
published under ``docs/downloads/`` in the nine named repositories, records their
immutable Git commits/blob identities, and notes *path-level* continuous-surface
candidates. It never attests global parallel coverage or organizer authentication.

The frozen registries bound to historic experiments must remain byte-identical. A
new snapshot therefore requires an explicit ``--output`` outside those paths;
``--restore-only`` is the only operation allowed against a frozen registry. Large
restored rasters stay under ignored ``data/raw/registry-expanded``. No competition
website monitoring or competition authentication is performed.
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

# These reports bind historical cards, novelty receipts and run-card hashes. A
# discovery refresh must never overwrite them: doing so would turn an old
# experiment into an untraceable mixture of old model bytes and new references.
FROZEN_REGISTRY_RELATIVES = (
    Path("docs/research/texture-displacement/registry.json"),
    Path("docs/research/texture-controls/registry.json"),
)
DEFAULT_RESTORE_REGISTRY = FROZEN_REGISTRY_RELATIVES[0]
SURFACE_ARRAY_SUFFIXES = frozenset((".npy", ".npz", ".zarr"))
SURFACE_RASTER_SUFFIXES = frozenset((".tif", ".tiff"))
SURFACE_NAME_TOKENS = ("surface", "prediction", "oof", "belief", "probability")


def frozen_registry_paths() -> set[Path]:
    """Return frozen-registry paths relative to the current (testable) ROOT."""
    return {(ROOT / relative).resolve() for relative in FROZEN_REGISTRY_RELATIVES}


def require_new_snapshot_target(output: Path) -> Path:
    """Fail before network access if a refresh targets historic/private evidence."""
    target = output.resolve()
    root = ROOT.resolve()
    if not target.is_relative_to(root):
        raise ValueError("snapshot output must remain inside the repository")
    if target in frozen_registry_paths():
        names = ", ".join(str(path.relative_to(root)) for path in sorted(frozen_registry_paths()))
        raise ValueError(
            "a fresh snapshot may not overwrite a frozen experiment registry "
            f"({names}); use --restore-only to verify it or choose a new --output"
        )
    return target


def repo_path(path: Path) -> Path:
    """Interpret command-line relative paths from the repository, not the shell CWD."""
    return path if path.is_absolute() else ROOT / path


def is_surface_candidate(path: str) -> bool:
    """Classify likely stored arrays/rasters, without claiming usable data.

    Plain text, code and JSON reports can contain words such as ``score`` or
    ``surface`` but cannot be aligned continuous rasters. Keep the discovery
    list intentionally narrow: binary-array formats, plus GeoTIFFs whose path
    names indicate an intermediate probability/prediction surface.
    """
    candidate = Path(path)
    suffix = candidate.suffix.lower()
    lower = candidate.as_posix().lower()
    return suffix in SURFACE_ARRAY_SUFFIXES or (
        suffix in SURFACE_RASTER_SUFFIXES and any(token in lower for token in SURFACE_NAME_TOKENS)
    )


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


def verified_cached_blob(row: dict, directory: Path) -> Path:
    """Restore one immutable Git blob only after checking its Git identity.

    Both final-dot reference TIFFs and possible pre-placement surfaces use this
    one implementation. A content-addressed cache prevents a later source-path
    rename from being mistaken for the bytes already inspected.
    """
    suffix = Path(row["source_path"]).suffix.lower() or ".blob"
    path = ROOT / directory / f"{row['site']}-{row['git_blob_sha1']}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        content = api(f"repos/{row['repo']}/contents/{row['source_path']}?ref={row['ref']}", raw=True)
        blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
        if len(content) != row["expected_bytes"] or blob != row["git_blob_sha1"]:
            raise ValueError(f"Git blob mismatch: {row['source_path']}")
        temp = path.with_suffix(path.suffix + ".partial")
        temp.write_bytes(content)
        temp.replace(path)
    content = path.read_bytes()
    blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    if len(content) != row["expected_bytes"] or blob != row["git_blob_sha1"]:
        raise ValueError(f"cached Git blob mismatch: {path}")
    return path


def restore_row(row: dict, grid) -> dict:
    import rasterio

    path = verified_cached_blob(row, Path("data/raw/registry-expanded"))
    result = {**row, "path": str(path.relative_to(ROOT)), "sha256": sha(path),
              "source_url": f"https://github.com/{row['repo']}/blob/{row['ref']}/{row['source_path']}"}
    with rasterio.open(path) as ds:
        aligned = ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid
        result["aligned"] = aligned
        result["shape"] = list(ds.shape)
        if not aligned:
            result["excluded_reason"] = "Not a single-band raster on the competition template grid"
    return result


def inspect_surface_candidate(row: dict, grid) -> dict:
    """Inspect *metadata* for a likely stored surface; never score or reuse it.

    This lets the protocol distinguish an absent original surface from a public
    array worth a later provenance review. It deliberately returns ``unknown``
    eligibility even when grid shape matches: model lineage, label leakage and
    lane ownership remain unproven.
    """
    import numpy as np
    import rasterio

    path = verified_cached_blob(row, Path("data/raw/registry-surfaces"))
    result = {**row, "path": str(path.relative_to(ROOT)), "sha256": sha(path),
              "source_url": f"https://github.com/{row['repo']}/blob/{row['ref']}/{row['source_path']}",
              "inspection_scope": "metadata only; values were not ranked, compared, or used as model inputs",
              "future_surface_comparison_eligibility": "unknown",
              "eligibility_blockers": [
                  "Model/experiment provenance not established", "No independent leakage audit",
                  "No assigned-lane release or owner authorization", "Not a global parallel registry",
              ]}
    suffix = path.suffix.lower()
    if suffix in SURFACE_RASTER_SUFFIXES:
        with rasterio.open(path) as ds:
            result.update({"format": "GeoTIFF", "band_count": ds.count, "shape": list(ds.shape),
                           "dtype": list(ds.dtypes), "crs": str(ds.crs),
                           "grid_matches_template": ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid})
    elif suffix == ".npz":
        with np.load(path, allow_pickle=False) as archive:
            arrays = {key: {"shape": list(archive[key].shape), "dtype": str(archive[key].dtype)}
                      for key in archive.files}
        result.update({"format": "NPZ", "arrays": arrays,
                       "any_array_matches_template_shape": any(tuple(value["shape"][-2:]) == grid[0]
                                                                 for value in arrays.values() if len(value["shape"]) >= 2)})
    elif suffix == ".npy":
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        result.update({"format": "NPY", "shape": list(array.shape), "dtype": str(array.dtype),
                       "array_matches_template_shape": tuple(array.shape[-2:]) == grid[0] if array.ndim >= 2 else False})
    else:
        result.update({"format": "unsupported", "inspection_error": f"Unsupported candidate suffix: {suffix}"})
    return result



def snapshot(output: Path, template: Path, *, inspect_surfaces: bool = False) -> dict:
    """Create a new, explicitly named public-source snapshot.

    The output guard runs before reading a source tree or downloading a TIFF. It
    protects historic novelty/holdout receipts even if a caller accidentally
    supplies their filename as a refresh target.
    """
    import rasterio

    output = require_new_snapshot_target(output)
    pins = json.loads((ROOT / "docs/research/priority-site-pins.json").read_text())
    with rasterio.open(template) as ds:
        grid = (ds.shape, ds.crs, ds.transform)
    inventory, snapshots, surface_candidates = [], [], []
    seen_repos = set()
    for row in pins["rasters"]:
        repo = row["repo"]
        if repo in seen_repos:
            continue
        seen_repos.add(repo)
        # Resolve once, then pin every tree and blob request to this exact commit.
        ref = json.loads(api(f"repos/{repo}/commits/main"))["sha"]
        tree = json.loads(api(f"repos/{repo}/git/trees/{ref}?recursive=1"))
        if tree.get("truncated"):
            raise ValueError(f"truncated source tree: {repo}")
        blobs = [item for item in tree["tree"] if item["type"] == "blob"]
        items = [item for item in blobs if item["path"].startswith("docs/downloads/")
                 and item["path"].lower().endswith((".tif", ".tiff"))]
        # This is deliberately path-level inventory only. Array contents may be
        # intermediate tensors, use another grid, or leak labels; no candidate is
        # restored, aligned, scored, or compared at this stage.
        discovered = [
            {"site": row["site"], "repo": repo, "ref": ref, "source_path": item["path"],
             "git_blob_sha1": item["sha"], "expected_bytes": item["size"],
             "discovery_scope": "path-name only; not downloaded, grid-checked, or treated as a continuous prediction surface"}
            for item in blobs if is_surface_candidate(item["path"])
            and not item["path"].startswith("docs/downloads/")
        ]
        surface_candidates.extend(discovered)
        snapshots.append({
            "site": row["site"], "repo": repo, "ref": ref, "tree_sha": tree["sha"],
            "published_tiffs": len(items),
            "continuous_surface_path_candidates": [item["source_path"] for item in discovered],
        })
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
    surface_inspection = None
    if inspect_surfaces:
        # This can only inspect public source metadata. It does not turn an
        # array into a registry reference, and it cannot retroactively satisfy
        # the pre-placement gate of an already-stopped experiment.
        with ThreadPoolExecutor(max_workers=4) as executor:
            surface_inspection = list(executor.map(lambda row: inspect_surface_candidate(row, grid), surface_candidates))
    result = {
        "schema_version": 4,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complete": False,
        "coverage": "All docs/downloads/**/*.tif[f] at the recorded nine main-branch snapshots; NOT the complete parallel-run registry.",
        "published_tiff_snapshot_inventory_complete": True,
        "continuous_surface_discovery": {
            "status": "metadata-inspected" if inspect_surfaces else "path-inventory-only",
            "candidate_count": len(surface_candidates),
            "candidates": surface_candidates,
            "inspections": surface_inspection,
            "not_evidence": "A matching filename does not establish a continuous prediction surface, alignment, safe provenance, or availability for pre-placement novelty testing.",
        },
        "missing_evidence": ["Other parallel sessions and repositories", "Original continuous surfaces for most published dots"],
        "organizer_authenticated": False,
        "snapshots": snapshots, "source_files": len(restored),
        "unique_aligned_byte_sequences": len(rasters), "rasters": rasters, "exclusions": exclusions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Snapshotted {len(restored)} TIFFs; {len(rasters)} unique aligned files; {len(exclusions)} excluded; "
          f"{len(surface_candidates)} unverified surface-path candidates. Global coverage incomplete.")
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
    parser.add_argument("--output", type=Path,
                        help="new output for a fresh snapshot; required unless --restore-only")
    parser.add_argument("--template", type=Path, default=Path("data/raw/sample_submission.tif"))
    parser.add_argument("--restore-only", action="store_true",
                        help=("restore/verify exact references in --output without changing it; "
                              "defaults to the TDX-1 frozen registry"))
    parser.add_argument("--inspect-surfaces", action="store_true",
                        help=("fetch and inspect metadata for likely public continuous-surface files; "
                              "never scores, compares, or approves them"))
    args = parser.parse_args()
    template = repo_path(args.template)
    if args.restore_only:
        if args.inspect_surfaces:
            parser.error("--inspect-surfaces requires a fresh explicitly named snapshot, not --restore-only")
        output = repo_path(args.output or DEFAULT_RESTORE_REGISTRY)
        restore_frozen(output, template)
        return
    if args.output is None:
        parser.error("fresh snapshots require an explicit --output outside the frozen experiment registries")
    snapshot(repo_path(args.output), template, inspect_surfaces=args.inspect_surfaces)


if __name__ == "__main__":
    main()
