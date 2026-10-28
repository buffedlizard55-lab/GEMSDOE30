#!/usr/bin/env python3
"""Reopen nine frozen historical leaders against the pinned duplicate witness.

No fitting, placement, prediction writing, leaderboard access, or slot selection.
--restore fetches only SHA-256-pinned historical bytes through the shared GitHub
transport. --check recomputes measurements offline, never trusts a saved verdict.
"""
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from gemsdoe30.github_data import stream_raw
from gemsdoe30.novelty import compare, dot_budget_bound
from gemsdoe30.submission import valid_template_mask, validate_submission_file
from scripts.verify_registry_preflight import same_measurement

FLEET = ROOT / "docs/research/2026-10-26-csr/fleet-audit.json"
PINS = ROOT / "docs/research/2026-10-27-registry-preflight/lattice-pin.json"
CORE_PINS = ROOT / "docs/research/mirror-pins.json"
OUTPUT = ROOT / "docs/research/2026-10-28-priority-audit.json"
PAGE = ROOT / "priority-readiness-audit.html"
SITES = tuple(f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36))


def sha(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def source_endpoint(row: dict) -> str:
    """Only the named fleet repository, immutable commit and GeoTIFF path."""
    site = row["site"]
    if site not in SITES:
        raise ValueError("unexpected priority site")
    prefix = f"https://github.com/buffedlizard55-lab/{site}/blob/"
    url = row["source_url"]
    if not url.startswith(prefix):
        raise ValueError("source repository does not match site")
    ref, sep, path = url[len(prefix):].partition("/")
    if (not re.fullmatch(r"[0-9a-f]{40}", ref) or not sep
            or not path.endswith(".tif") or any(p in ("", ".", "..") for p in path.split("/"))
            or re.search(r"[^A-Za-z0-9_./-]", path)):
        raise ValueError("immutable GeoTIFF source required")
    if not re.fullmatch(r"[0-9a-f]{64}", row["raster_sha256"]):
        raise ValueError("SHA-256 pin required")
    return f"repos/buffedlizard55-lab/{site}/contents/{path}?ref={ref}"


def historical_path(row: dict, cache: Path, *, restore: bool) -> Path:
    endpoint = source_endpoint(row)
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{row['site']}-{row['raster_sha256']}.tif"
    if dest.exists():
        if sha(dest) != row["raster_sha256"]:
            raise ValueError(f"cached historical SHA-256 mismatch: {row['site']}")
        return dest
    if not restore:
        raise FileNotFoundError(f"{dest}; restore pinned historical bytes with --restore")
    with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
        tmp = Path(stream.name)
        try:
            stream_raw(endpoint, stream)
            stream.flush()
            if sha(tmp) != row["raster_sha256"]:
                raise ValueError(f"downloaded historical SHA-256 mismatch: {row['site']}")
            tmp.replace(dest)
        finally:
            tmp.unlink(missing_ok=True)
    return dest


def audit(*, template: Path, lattice: Path, cache: Path, restore: bool = False) -> dict:
    fleet = load(FLEET)
    if tuple(r["site"] for r in fleet["rows"]) != SITES:
        raise ValueError("expected exactly the nine frozen historical selections")
    ref_pin = load(PINS)["files"][0]
    tpl_pin = next(r for r in load(CORE_PINS)["files"] if r["id"] == "sample_submission")
    if sha(template) != tpl_pin["sha256"] or sha(lattice) != ref_pin["sha256"]:
        raise ValueError("template or duplicate-witness SHA-256 mismatch")
    with rasterio.open(template) as tpl, rasterio.open(lattice) as ref:
        grid = (tpl.shape, tpl.crs, tpl.transform)
        if ref.count != 1 or (ref.shape, ref.crs, ref.transform) != grid:
            raise ValueError("witness grid mismatch")
        mask, reference = valid_template_mask(tpl, np), ref.read(1)
    rows = []
    for row in fleet["rows"]:
        path = historical_path(row, cache, restore=restore)
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != grid:
                raise ValueError(f"historical grid mismatch: {row['site']}")
            values = ds.read(1)
        inside = values[mask]
        if not np.isfinite(inside).all() or not np.all((inside == 0) | (inside == 1)):
            raise ValueError(f"expected finite binary historical raster: {row['site']}")
        comparison = compare(values, reference, mask, stage="dots")
        k = comparison["candidate_dots"]
        if k != row["dots"]:
            raise ValueError(f"historical dot-count mismatch: {row['site']}")
        bound = dot_budget_bound(reference, mask, k)
        report = validate_submission_file(path, template).to_dict()
        # Paths are a local cache implementation detail, not provenance.
        report.pop("path")
        rows.append({
            "site": row["site"], "historical_file": row["historical_file"],
            "source_url": row["source_url"], "raster_sha256": sha(path),
            "reported_historical_value": row["quoted_owner_claim"],
            "reported_value_evidence": "UNVERIFIED OWNER CLAIM; not ORGANIZER-CONFIRMED or HOLDOUT-DTI",
            "new_submission_score_estimate": None,
            "comparison": comparison,
            "matching_dots": round(k * comparison["candidate_fraction_within_3px_of_reference"]),
            "bound": bound, "validator_output": report,
            "finite_inside": bool(np.isfinite(inside).all()),
            "inside_range": [float(inside.min()), float(inside.max())],
            "preplacement_surface_checked": False,
            "exact_value_alias_sites": row["exact_value_alias_sites"],
            "unique_submission": False if comparison["dot_duplicate"] else None,
            "download_for_submission": False, "ok_to_submit": False,
        })
    return {
        "schema_version": 1, "audit_version": "priority-readiness-v1-20261028",
        "scope": "Exact bytes of nine frozen owner-identified historical leaders; not live leadership or a complete registry",
        "fleet_manifest_sha256": sha(FLEET), "witness_pin_sha256": sha(PINS),
        "template_sha256": sha(template), "witness_raster_sha256": sha(lattice),
        "witness_source": ref_pin["provenance"], "witness_source_url": load(PINS)["source"],
        "rows": rows, "new_raster_generated": False, "experiments_run": 0,
        "holdout_dti": None, "holdout_ci95": None, "organizer_confirmed_score": None,
        "preplacement_surface_checked": False, "complete_registry_checked": False,
        "remote_sites_modified": False, "slot_selected": False, "ok_to_submit": False,
        "verdict": "negative", "decision": "DO NOT DOWNLOAD FOR SUBMISSION; historical references only",
    }


def render(receipt: dict) -> str:
    e = escape
    rows = []
    for row in receipt["rows"]:
        c = row["comparison"]
        failed = ", ".join(x["name"] for x in row["validator_output"]["checks"] if not x["passed"])
        fmt = "PASS" if row["validator_output"]["passed"] else f"FAIL: {failed}"
        rows.append(f'<tr><th>{e(row["site"])}</th><td><a href="{e(row["source_url"])}">{e(row["historical_file"])}</a><br><small>{e(row["raster_sha256"])}</small></td>'
                    f'<td>{e(row["reported_historical_value"])}<br>Unverified owner claim</td><td>Unavailable; no forecast</td>'
                    f'<td>{row["matching_dots"]:,}/{c["candidate_dots"]:,} ({100*c["candidate_fraction_within_3px_of_reference"]:.4f}%)<br>Spearman {c["spearman_full_footprint"]:.6f}</td>'
                    f'<td>{e(fmt)}</td><td><strong>NO — duplicate-stop</strong></td></tr>')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nine-site byte audit · GEMSDOE30</title><link rel="stylesheet" href="docs/assets/research.css"></head><body>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html">G30 · Fault discovery lab</a><nav><a href="priority-executive-summary.html">Nine-site executive summary</a><a href="executive-summary.html">Submission guide</a></nav></div></header><main id="main">
<section class="intro"><div><p class="eyebrow">Reproducible byte audit · 28 Oct 2026</p><h1>No approved submission download.</h1><p class="lead">All nine historical references fail the literal dot-overlap rule. A valid GeoTIFF is not necessarily unique, competitive, or approved.</p></div></section>
<section class="stop-notice"><h2>Do not submit these historical files.</h2><p>This audit reopens SHA-256-pinned rasters and measures each against the pinned 13GEMSDOE lattice, rather than merely quoting a budget lower bound. It creates no prediction and uses no weekly slot. Source links below are for audit only; there is no submission download button.</p><p>Rank correlation and overlap are geometric diagnostics, not performance scores. Pre-placement surfaces are unavailable. One duplicate witness suffices to stop; this does not certify complete registry coverage. No remote GEMSDOE website was modified.</p></section>
<section class="section"><div class="table-wrap"><table><caption>Frozen historical leaders, freshly reopened bytes — not a live leaderboard</caption><thead><tr><th>Site</th><th>Historical file / SHA-256</th><th>Reported historical value</th><th>New score estimate</th><th>Measured final-dot overlap within 3 px / correlation</th><th>Shared format validator</th><th>Unique / OK to download and submit?</th></tr></thead><tbody>''' + "".join(rows) + '''</tbody></table></div><p><a href="docs/research/2026-10-28-priority-audit.json">Complete machine receipt and validator checks</a> · <a href="docs/research/2026-10-28-review.md">Repository findings, hypotheses and limitations</a></p></section>
<section class="section"><h2>What does H33-B2 establish?</h2><p>The archived byte audit found H33-B2 is an earlier 40,199-dot r1 raster with 2,545 dots near the mapped-fault halo removed, leaving 37,654 dots. GEMSDOE36 adds 1,200 dots to H33-B2; GEMSDOE25 and GEMSDOE30 have identical in-footprint values despite different file hashes. These are file-lineage findings, not independent geological discoveries or causal proof of score improvement.</p><p>The reported 0.2778 is not an organizer-confirmed receipt here. Pruning could reduce false-positive cost while retaining distance-kernel coverage, but the hidden TP/FP changes are unknown. No defensible estimate establishes that a new method will exceed it. <a href="docs/research/2026-10-26-csr/fleet-audit.json">Archived lineage evidence</a>.</p></section>
<section class="section"><h2>Reproduce without a human inspector</h2><pre>python scripts/audit_priority_readiness.py --restore
python scripts/audit_priority_readiness.py --check</pre><p>Restore the pinned template and lattice first using the README commands. Check mode performs no network access. Hashes, integer counts, verdicts and generated HTML must match exactly; floating-point diagnostics use the shared verifier's 1e-12 tolerance for numerical roundoff. Neither successful execution nor a format PASS selects a slot. There is no leaderboard estimate, no new HOLDOUT-DTI result, and no ORGANIZER-CONFIRMED score in this audit.</p><p>Official context: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">organizer reference solution</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">submission specification</a>. GitHub owner mirrors are not official data authentication or submission receipts.</p></section></main></body></html>\n'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--lattice", type=Path, default=ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif")
    parser.add_argument("--cache", type=Path, default=ROOT / "data/raw/priority-readiness")
    parser.add_argument("--restore", action="store_true", help="restore pinned historical bytes and write audit")
    parser.add_argument("--restore-only", action="store_true", help="restore historical inputs without rewriting evidence")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if sum((args.restore, args.restore_only, args.check)) > 1:
        parser.error("choose only one of --restore, --restore-only, --check; --check is offline")
    if args.restore_only:
        for row in load(FLEET)["rows"]:
            historical_path(row, args.cache, restore=True)
        print("Restored historical inputs only; no evidence or prediction written")
        return 0
    result = audit(template=args.template, lattice=args.lattice, cache=args.cache, restore=args.restore)
    content = json.dumps(result, indent=2, allow_nan=False) + "\n"
    html = render(result)
    if args.check:
        if not same_measurement(load(OUTPUT), result) or PAGE.read_text() != html:
            raise SystemExit("stale priority byte audit or generated page")
    else:
        OUTPUT.write_text(content)
        PAGE.write_text(html)
    print("Verified nine historical references; no new raster, forecast, or slot approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
