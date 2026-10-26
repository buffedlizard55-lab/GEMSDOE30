#!/usr/bin/env python3
"""Reopen the nine historical leaders; report byte/value aliases, never select a slot.

Score claims are quoted strings, not measurements. No leaderboard forecasting or
cross-protocol ranking is performed. All raster paths come from the frozen
public registry or previously pinned educational references.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from gemsdoe30.novelty import compare, rank_cache
from gemsdoe30.submission import valid_template_mask, validate_submission_file

REPORT = ROOT / "docs/research/2026-10-26-gdx"
# Deliberately strings: these are user-provided claims, NOT local metrics.
CLAIMS = {
    "GEMSDOE24": ("989f59505db1", "0.2477"),
    "GEMSDOE25": ("e56ea318af89", "0.2600"),
    "GEMSDOE27": ("5512495c6bd1", "0.2449"),
    "GEMSDOE28": ("b531dae0a36f", "0.2710"),
    "GEMSDOE30": ("91eae1ca", "0.2600"),
    "GEMSDOE31": ("8acb75e1", "0.2708"),
    "GEMSDOE32": ("e5eb6e7e", "0.2778"),
    "GEMSDOE33": ("cb490425926e", "0.2632"),
    "GEMSDOE36": ("9b9ea4e6", "0.2750"),
}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(row, grid):
    path = ROOT / row["path"]
    if sha(path) != row["sha256"]:
        raise ValueError("historical reference hash mismatch")
    with rasterio.open(path) as ds:
        if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
            raise ValueError("historical reference grid mismatch")
        return ds.read(1)


def audit(registry_path: Path = REPORT / "registry.json", candidate_path: Path | None = None):
    registry = json.loads(Path(registry_path).read_text())
    snapshots = {s["site"]: s for s in registry["snapshots"]}
    pins = json.loads((ROOT / "docs/research/priority-site-pins.json").read_text())
    template = ROOT / "data/raw/sample_submission.tif"
    with rasterio.open(template) as ds:
        valid = valid_template_mask(ds, np)
        grid = (ds.shape, ds.crs, ds.transform)
    labels = np.load(ROOT / "data/processed/labels.npy") > 0.5
    distance = distance_transform_edt(~labels)
    arrays, rows = {}, []
    for site, (token, claim) in CLAIMS.items():
        # Prefer the original educational bytes to a newly re-encoded alias.
        historical = next((r for r in pins["rasters"] if r["site"] == site and token in r["source_path"]), None)
        if historical is None:
            choices = [r for r in registry["rasters"] if r["site"] == site and token in r["source_path"]]
            if not choices:
                raise ValueError(f"missing named historical leader for {site}")
            historical = sorted(choices, key=lambda r: ("-nan.tif" not in r["source_path"], r["source_path"]))[0]
        a = read(historical, grid)
        arrays[site] = a
        finite = np.isfinite(a[valid])
        validation = validate_submission_file(ROOT / historical["path"], template)
        r = {
            "site": site,
            "site_url": f"https://buffedlizard55-lab.github.io/{site}/",
            "public_snapshot_commit": snapshots[site]["ref"],
            "review_url": f"priority-{site}.html",
            "historical_file": Path(historical["source_path"]).name,
            "source_url": f"https://github.com/{historical['repo']}/blob/{historical['ref']}/{historical['source_path']}",
            "raster_sha256": historical["sha256"],
            "values_sha256": hashlib.sha256(np.ascontiguousarray(a[valid], dtype=np.float32).tobytes()).hexdigest(),
            "dots": int(np.count_nonzero(a[valid] > 0)),
            "nan_or_inf_inside_footprint": int((~finite).sum()),
            "format_validation_passed": validation.passed,
            "failed_format_checks": [c.name for c in validation.checks if not c.passed],
            "quoted_owner_claim": claim,
            "claim_class": "UNVERIFIED OWNER CLAIM — NOT a performance measurement",
            "organizer_confirmed": None, "holdout_dti": None, "leaderboard_estimate": None,
            "unique_new_submission": False, "safe_to_resubmit": False,
            "decision": "DO NOT RESUBMIT historical bytes; no organizer receipt / no new hypothesis",
        }
        rows.append(r)
    pairs = []
    for i, left in enumerate(rows):
        cached = rank_cache(arrays[left["site"]], valid)
        for right in rows[i + 1:]:
            comparison = compare(arrays[left["site"]], arrays[right["site"]], valid,
                                 stage="dots", cached_ranks=cached)
            pairs.append({"candidate_site": left["site"], "reference_site": right["site"], **comparison})
    for row in rows:
        row["exact_value_alias_sites"] = [r["site"] for r in rows
                                          if r["site"] != row["site"] and r["values_sha256"] == row["values_sha256"]]
    if candidate_path is not None:
        with rasterio.open(candidate_path) as cds:
            cand_arr = cds.read(1)
        cand_cache = rank_cache(cand_arr, valid)
        for row in rows:
            comp = compare(cand_arr, arrays[row["site"]], valid, stage="dots", cached_ranks=cand_cache)
            row["csr1_spearman"] = float(comp["spearman_full_footprint"])
            row["csr1_fraction_within_3px"] = float(comp["candidate_fraction_within_3px_of_reference"])
    d28 = arrays["GEMSDOE25"] > 0
    h33 = arrays["GEMSDOE32"] > 0
    r1_pin = next(r for r in pins["rasters"] if r["site"] == "GEMSDOE28")
    r1 = read(r1_pin, grid) > 0
    pinn = arrays["GEMSDOE36"] > 0
    lineage = {
        "classification": "RASTER AUDIT (not a score or causal proof)",
        "G25_equals_G30_inside_footprint": bool(np.array_equal(arrays["GEMSDOE25"][valid], arrays["GEMSDOE30"][valid])),
        "G28_r1_equals_G31_inside_footprint": bool(np.array_equal(r1[valid], (arrays["GEMSDOE31"] > 0)[valid])),
        "r1_equals_d28_distance_gt_1": bool(np.array_equal(r1 & valid, d28 & valid & (distance > 1))),
        "h33_equals_r1_distance_gt_2": bool(np.array_equal(h33 & valid, r1 & valid & (distance > 2))),
        "h33_subset_of_pinn": bool(not np.any(h33 & valid & ~pinn)),
        "pinn_additional_dots": int(np.count_nonzero(pinn & valid & ~h33)),
        "d28_to_r1_removed": int(np.count_nonzero(d28 & valid & ~r1)),
        "r1_to_h33_removed": int(np.count_nonzero(r1 & valid & ~h33)),
        "h33_dots": int(np.count_nonzero(h33 & valid)),
        "causal_limit": "File lineage is verified. Actual hidden TP/FP changes cannot be recovered uniquely without organizer truth/receipts.",
    }
    return {
        "schema_version": 1, "snapshot_utc": registry["generated_utc"],
        "scope": "Nine historical leaders named in owner prompt, not a live leaderboard or a selector",
        "registry_sha256": sha(registry_path), "template_sha256": sha(template),
        "rows": rows, "pairwise_diagnostics": pairs, "lineage": lineage,
        "organizer_receipts_present": False,
        "no_defensible_leaderboard_forecast": True,
        "remote_sites_modified": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=REPORT / "registry.json")
    parser.add_argument("--candidate", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=REPORT / "fleet-audit.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(audit(args.registry, args.candidate), indent=2, allow_nan=False) + "\n"
    if args.check:
        if args.output.read_text() != content:
            raise SystemExit("fleet audit stale")
    else:
        args.output.write_text(content)
    print("Nine-site raster identities, aliases, lineage and evidence classes checked; no slot selected")


if __name__ == "__main__":
    main()
