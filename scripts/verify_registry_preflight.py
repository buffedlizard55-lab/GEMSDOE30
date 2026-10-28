#!/usr/bin/env python3
"""Recompute the one-witness duplicate proof and verify the negative run card.

This is NOT a model experiment, a registry-wide pass, or an upload selector.
The candidate is the *previously published* CSR-1 file. The proposed continuation
is stopped without fitting or placement. All source rasters are hash-pinned; the
reference and template can be restored from GitHub without competition credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from gemsdoe30.novelty import compare, dot_budget_bound  # noqa: E402
from gemsdoe30.submission import valid_template_mask, validate_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-27-registry-preflight"
CARD = REPORT / "run-card.json"
TEMPLATE = ROOT / "data/raw/sample_submission.tif"
LATTICE = ROOT / "data/raw/registry-extra/13gems-lattice-s5.tif"
HISTORIC_CARD = ROOT / "docs/research/2026-10-26-csr/run-card.json"
# These were independently merged into main in PR #54 while this audit was in
# progress. We inspect their original saved bytes, never generate replacements.
PARALLEL_CANDIDATES = (
    {"lane": "CTD-1", "path": "docs/downloads/gems30-ctd1-concealed-stepper-20261027T172620Z-c39a9264.tif",
     "sha256": "13074a02b38e7edea5faaccbaa18f382dffd395fd211139becb7d66278f02297"},
    {"lane": "FC-1", "path": "docs/downloads/gems30-fc1-concealed-flank-20261027T172846Z-f182c780.tif",
     "sha256": "d6dadb9c6119767f0b4af2f2122e73529829b3c1b36cf1131165cb68b8da2612"},
)
PARALLEL_SOURCE_COMMIT = "99b9cc9693bd19c474f298a99618599ade6f3c60"
POSTMERGE_ADDENDUM = REPORT / "postmerge-addendum.json"
POSTMERGE_CANDIDATES = (
    {"lane": "GC-1", "path": "docs/downloads/GEMSDOE30-geothermal-corridor-offcat-d3-20261026T160300Z.tif",
     "sha256": "0ed2670200159cab23436a5033a90d7582accc63811756d3393441c6bbdac564",
     "source_commit": "48d4b0f0c997e3f033d7c1e0cfc9f4533a974fe5"},
    {"lane": "VS-1", "path": "docs/downloads/GEMSDOE30-vent-structural-offcat-d3-20261027T000000Z.tif",
     "sha256": "e701076a93df45ae911b15519bcce66d88cca318686fa39df4117e921dd1876b",
     "source_commit": "d3435433ca015a84ff2eaf41a1304a301dca0f47"},
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def independent_three_pixel_coverage(reference, footprint) -> int:
    """Count coverage by explicit 29-offset disk dilation, independent of EDT.

    Source and target slices are clipped, not rolled, so opposite edges never
    wrap. Outside-footprint reference values are excluded as possible sources.
    """
    mask = np.asarray(footprint, dtype=bool)
    dots = mask & (np.asarray(reference) > 0)
    covered = np.zeros(mask.shape, dtype=bool)
    h, w = mask.shape
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            if dr * dr + dc * dc > 9 or abs(dr) >= h or abs(dc) >= w:
                continue
            src_r = slice(max(0, -dr), min(h, h - dr))
            src_c = slice(max(0, -dc), min(w, w - dc))
            dst_r = slice(max(0, dr), min(h, h + dr))
            dst_c = slice(max(0, dc), min(w, w + dc))
            covered[dst_r, dst_c] |= dots[src_r, src_c]
    return int(np.count_nonzero(mask & covered))


def inspect(template: Path = TEMPLATE, lattice: Path = LATTICE) -> dict:
    """Inspect actual bytes; return bounded evidence rather than a recommendation."""
    template, lattice = Path(template), Path(lattice)
    pins = load(ROOT / "docs/research/mirror-pins.json")
    template_pin = next(r for r in pins["files"] if r["id"] == "sample_submission")
    ref_pin = load(REPORT / "lattice-pin.json")["files"][0]
    historical = load(HISTORIC_CARD)
    candidate = ROOT / historical["published_tiff"]
    require(sha(template) == template_pin["sha256"], "template SHA-256 mismatch")
    require(sha(lattice) == ref_pin["sha256"] and lattice.stat().st_size == ref_pin["bytes"],
            "lattice SHA-256 or size mismatch")
    require(sha(candidate) == historical["raster_sha256"], "historic CSR-1 SHA-256 mismatch")
    with rasterio.open(template) as tpl, rasterio.open(lattice) as ref, rasterio.open(candidate) as old:
        require(tpl.count == ref.count == old.count == 1, "expected single-band GeoTIFFs")
        grid = (tpl.shape, tpl.crs, tpl.transform)
        require((ref.shape, ref.crs, ref.transform) == grid, "lattice/template grid mismatch")
        require((old.shape, old.crs, old.transform) == grid, "historic candidate/template grid mismatch")
        footprint = valid_template_mask(tpl, np)
        reference = ref.read(1)
        prediction = old.read(1)
        values = prediction[footprint]
        require(np.isfinite(values).all() and np.all((values == 0) | (values == 1)),
                "historic CSR-1 is not a finite binary-dot raster")
        budget = int(np.count_nonzero(values))
        # Check the count claimed in the archived receipt before applying its budget.
        require(budget == historical["validator_output"]["emitted_dots"], "historical dot count mismatch")
        proof = dot_budget_bound(reference, footprint, budget)
        independent_covered = independent_three_pixel_coverage(reference, footprint)
        require(independent_covered == proof["covered_within_radius_pixels"],
                "independent integer-disk coverage disagrees with distance transform")
        comparison = compare(prediction, reference, footprint, stage="dots")
        # Match count is an integer; the exact compare fraction is retained too.
        matching = int(round(comparison["candidate_fraction_within_3px_of_reference"] * budget))
        require(proof["decision"] == "duplicate-stop" and comparison["dot_duplicate"] is True,
                "expected strict duplicate witness not reproduced")
        require(matching >= proof["minimum_overlapping_dots"], "observed overlap violates bound")
        grid_record = {"shape_hw": list(tpl.shape), "crs": str(tpl.crs),
                       "transform": list(tpl.transform)[:6]}
        parallel = []
        for entry in PARALLEL_CANDIDATES:
            path = ROOT / entry["path"]
            require(sha(path) == entry["sha256"], f"{entry['lane']} historic SHA-256 mismatch")
            with rasterio.open(path) as ds:
                require(ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid,
                        f"{entry['lane']} grid/band mismatch")
                values = ds.read(1)
            inside = values[footprint]
            require(np.isfinite(inside).all() and np.all((inside == 0) | (inside == 1)),
                    f"{entry['lane']} is not a finite binary-dot raster")
            dot_count = int(np.count_nonzero(inside))
            require(dot_count > 0, f"{entry['lane']} has no dots")
            stats = compare(values, reference, footprint, stage="dots")
            matched = int(round(stats["candidate_fraction_within_3px_of_reference"] * dot_count))
            require(stats["dot_duplicate"] is True, f"{entry['lane']} duplicate not reproduced")
            min_matches = max(0, dot_count - proof["uncovered_pixels"])
            parallel.append({
                "lane": entry["lane"], "path": entry["path"], "raster_sha256": entry["sha256"],
                "source_commit": PARALLEL_SOURCE_COMMIT,
                "matching_dots": matched, "comparison": stats,
                "budget_bound_decision": "duplicate-stop" if 10 * min_matches > 7 * dot_count else "not-proven",
                "minimum_overlapping_dots": min_matches,
                "published_format_validator_passed": validate_submission_file(path, template).passed,
                "whole_array_finite_range_diagnostic_passed": validate_submission_file(
                    path, template, require_finite_all_cells=True).passed,
                "produced_by_this_audit": False,
            })
    published = validate_submission_file(candidate, template)
    diagnostic = validate_submission_file(candidate, template, require_finite_all_cells=True)
    return {
        "template_sha256": sha(template),
        "reference_sha256": sha(lattice),
        "reference_source": load(REPORT / "lattice-pin.json")["source"],
        "grid": grid_record,
        "bound": proof,
        "independent_coverage": {"method": "explicit clipped 29-offset Euclidean integer disk, no wrap",
                                 "covered_within_radius_pixels": independent_covered},
        "parallel_candidates_merged_during_audit": parallel,
        "previous_candidate": {
            "path": historical["published_tiff"], "raster_sha256": sha(candidate),
            "matching_dots": matching, "comparison": comparison,
            "outside_convention": "zero outside the template footprint",
            "published_format_validator_passed": published.passed,
            "whole_array_finite_range_diagnostic_passed": diagnostic.passed,
            "published_failed_checks": [x.name for x in published.checks if not x.passed],
            "organizer_acceptance_confirmed": False,
        },
    }


def make_card(measured: dict) -> dict:
    old = load(HISTORIC_CARD)
    results = load(ROOT / "docs/research/2026-10-26-csr/results.json")
    return {
        "schema_version": 1,
        "run_id": "gems30-registry-preflight-20261027",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": "Prior-session CSR-2 proposal: preserve piedmont-scarp evidence while gating the cover-blind potential-field expert to transtensional regions.",
        "mechanism": "Regime-weighted combination of terrain/MSDB and cover-blind potential-field/Radon evidence; proposal only, never fitted here.",
        "named_non_fault_process": "Erosional fan or paleoshoreline scarps and non-fault lithologic boundaries can mimic the targeted edges.",
        "lane_assignment": "unknown: this prompt supplies no single assigned method paragraph; CSR-2 is a prior-session proposal only",
        "new_holdout": {"label": "HOLDOUT-DTI", "value": None, "ci95": None,
                        "evaluator_version": None, "withheld_positives": None,
                        "reason": "No new model or holdout experiment after the preflight stop."},
        "historical_holdout_reference": {
            "source": "docs/research/2026-10-26-csr/results.json",
            "label": "HOLDOUT-DTI", "evaluator_version": results["summary"]["evaluator_version"],
            "protocol_version": results["summary"]["protocol_version"],
            "candidate": results["summary"]["arms"]["csr_dispersed"],
            "matched_control": results["summary"]["arms"]["msdb_edge"],
            "paired_difference": results["summary"]["candidate_minus"]["msdb_edge"],
            "scope": "Archived catalogue proxy, not a hidden-test score or a CSR-2 result.",
        },
        "parallel_holdout_review": {
            "source_commit": PARALLEL_SOURCE_COMMIT,
            "candidates": ["CTD-1", "FC-1"],
            "valid_leakage_safe_holdout": False,
            "finding": "Both saved rasters used the full catalogue for emission before the evaluator hid components; the evaluator then re-emitted those saved rasters. Its random component split is not the claimed four buffered regional folds. FC-1 also has unequal candidate/control dot counts. Archived scores are not valid evidence for the requested protocol.",
            "source_files": ["scripts/build_concealed_stepper_submission.py", "scripts/build_flank_concealed_submission.py", "scripts/evaluate_ctd1_holdout.py"],
        },
        "registry": {
            "pre_placement_surface": None,
            "new_final_dots": None,
            "scope": "One valid registered 13GEMSDOE witness is sufficient to prove STOP; this is not a complete inventory.",
            "measurement": measured,
        },
        "raster_sha256": None,
        "validator_output": None,
        "submission_name": None,
        "note": None,
        "experiments_run": 0,
        "experiment_cap": 3,
        "time_cap_seconds": 7200,
        "verdict": "negative",
        "decision": "DUPLICATE-STOP: no new raster produced, no weekly slot selected or used",
        "download_ok": False,
        "ok_to_submit": False,
        "submission_approved": False,
        "slot_selected": False,
        "organizer_score": None,
        "historical_organizer_score_receipt": None,
        "historical_raster_sha256": old["raster_sha256"],
    }


def same_measurement(saved, actual) -> bool:
    """Match integer evidence exactly; tolerate only roundoff in float statistics."""
    if isinstance(actual, dict):
        return isinstance(saved, dict) and saved.keys() == actual.keys() and all(
            same_measurement(saved[k], actual[k]) for k in actual)
    if isinstance(actual, list):
        return isinstance(saved, list) and len(saved) == len(actual) and all(
            same_measurement(a, b) for a, b in zip(saved, actual))
    if isinstance(actual, float):
        return (isinstance(saved, (int, float)) and not isinstance(saved, bool)
                and math.isfinite(saved) and math.isclose(saved, actual, rel_tol=1e-12, abs_tol=1e-12))
    return type(saved) is type(actual) and saved == actual


def verify(template: Path = TEMPLATE, lattice: Path = LATTICE) -> dict:
    card = load(CARD)
    measured = inspect(template, lattice)
    require(same_measurement(card["registry"]["measurement"], measured), "saved preflight measurement does not match source bytes")
    require(card.get("verdict") == "negative" and card.get("experiments_run") == 0,
            "preflight must remain a zero-experiment negative")
    require(all(card.get(k) is False for k in ("download_ok", "ok_to_submit", "submission_approved", "slot_selected")),
            "preflight cannot approve a new file or slot")
    require(all(card.get(k) is None for k in ("raster_sha256", "validator_output", "submission_name", "note", "organizer_score")),
            "preflight cannot claim a new file or organizer score")
    h = card["new_holdout"]
    require(h["label"] == "HOLDOUT-DTI" and all(h.get(k) is None for k in
            ("value", "ci95", "evaluator_version", "withheld_positives")), "new holdout was not run")
    results = load(ROOT / "docs/research/2026-10-26-csr/results.json")["summary"]
    historic = card["historical_holdout_reference"]
    require(historic["candidate"] == results["arms"]["csr_dispersed"]
            and historic["matched_control"] == results["arms"]["msdb_edge"]
            and historic["paired_difference"] == results["candidate_minus"]["msdb_edge"]
            and historic["evaluator_version"] == results["evaluator_version"]
            and historic["protocol_version"] == results["protocol_version"],
            "historical holdout must match the archived receipt")
    require(card["historical_raster_sha256"] == measured["previous_candidate"]["raster_sha256"],
            "historical candidate identity mismatch")
    parallel_review = card.get("parallel_holdout_review", {})
    require(parallel_review.get("valid_leakage_safe_holdout") is False
            and parallel_review.get("source_commit") == PARALLEL_SOURCE_COMMIT,
            "parallel holdout cannot be presented as leakage-safe evidence")
    postmerge = inspect_postmerge(template, lattice)
    if POSTMERGE_ADDENDUM.is_file():
        saved_postmerge = load(POSTMERGE_ADDENDUM)
        expected = [
            {k: v for k, v in row.items() if k in saved_row}
            for row, saved_row in zip(postmerge, saved_postmerge.get("candidates", []))
        ]
        require(len(expected) == len(postmerge) and same_measurement(saved_postmerge["candidates"], postmerge)
                or (not (ROOT / "data/raw/labels.tif").is_file()
                    and same_measurement([{k: v for k, v in r.items() if k not in ("dots_on_catalogue_d0", "dots_within_2px_of_catalogue")}
                                          for r in saved_postmerge["candidates"]], postmerge)),
                "saved postmerge addendum does not match source bytes")
        require(saved_postmerge.get("renamed_duplicate_removed") is True,
                "postmerge addendum must record removal of renamed GC-1 duplicate")
    return {"research_verdict": "negative", "display_status": card["decision"],
            "download_ok": False, "ok_to_submit": False, "submission_approved": False,
            "slot_selected": False, "measurement": measured, "postmerge_candidates": postmerge}


def inspect_postmerge(template: Path = TEMPLATE, lattice: Path = LATTICE) -> list[dict]:
    """Verify PR #58/#59 candidates against the pinned lattice without mutating frozen run-card.json."""
    from scipy.ndimage import distance_transform_edt

    template, lattice = Path(template), Path(lattice)
    renamed_dup = ROOT / "docs/downloads/GEMSDOE30-geothermal-corridor-offcat-d3-20261027T233111Z.tif"
    require(not renamed_dup.exists(), "renamed byte-identical duplicate of GC-1 must not remain in docs/downloads")
    labels_path = ROOT / "data/raw/labels.tif"
    pins = load(ROOT / "docs/research/mirror-pins.json")
    labels_pin = next(r for r in pins["files"] if r["id"] == "labels")
    with rasterio.open(template) as tpl, rasterio.open(lattice) as ref:
        grid = (tpl.shape, tpl.crs, tpl.transform)
        footprint = valid_template_mask(tpl, np)
        reference = ref.read(1)
        uncovered = dot_budget_bound(reference, footprint, 44090)["uncovered_pixels"]
        catalogue = None
        d_catalogue = None
        if labels_path.is_file():
            require(sha(labels_path) == labels_pin["sha256"], "labels.tif SHA-256 mismatch")
            with rasterio.open(labels_path) as lab_ds:
                require((lab_ds.shape, lab_ds.crs, lab_ds.transform) == grid, "labels.tif grid mismatch")
                catalogue = (lab_ds.read(1) > 0.5) & footprint
            d_catalogue = distance_transform_edt(~catalogue)
        rows = []
        for entry in POSTMERGE_CANDIDATES:
            path = ROOT / entry["path"]
            require(sha(path) == entry["sha256"], f"{entry['lane']} historic SHA-256 mismatch")
            with rasterio.open(path) as ds:
                require(ds.count == 1 and (ds.shape, ds.crs, ds.transform) == grid,
                        f"{entry['lane']} grid/band mismatch")
                values = ds.read(1)
            inside = values[footprint]
            require(np.isfinite(inside).all() and np.all((inside == 0) | (inside == 1)),
                    f"{entry['lane']} is not a finite binary-dot raster")
            dot_count = int(np.count_nonzero(inside))
            require(dot_count > 0, f"{entry['lane']} has no dots")
            stats = compare(values, reference, footprint, stage="dots")
            matched = int(round(stats["candidate_fraction_within_3px_of_reference"] * dot_count))
            require(stats["dot_duplicate"] is True, f"{entry['lane']} duplicate not reproduced")
            min_matches = max(0, dot_count - uncovered)
            row = {
                "lane": entry["lane"],
                "path": entry["path"],
                "raster_sha256": entry["sha256"],
                "source_commit": entry["source_commit"],
                "matching_dots": matched,
                "comparison": stats,
                "budget_bound_decision": "duplicate-stop" if 10 * min_matches > 7 * dot_count else "not-proven",
                "minimum_overlapping_dots": min_matches,
                "published_format_validator_passed": validate_submission_file(path, template).passed,
                "whole_array_finite_range_diagnostic_passed": validate_submission_file(
                    path, template, require_finite_all_cells=True).passed,
                "produced_by_this_audit": False,
                "ok_to_submit": False,
            }
            if catalogue is not None and d_catalogue is not None:
                dots_mask = footprint & (np.nan_to_num(values, nan=0.0) > 0.5)
                row["dots_on_catalogue_d0"] = int(np.count_nonzero(dots_mask & catalogue))
                row["dots_within_2px_of_catalogue"] = int(np.count_nonzero(dots_mask & (d_catalogue <= 2.0)))
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--lattice", type=Path, default=LATTICE)
    parser.add_argument("--create", action="store_true", help="write the new run card once; never overwrite")
    parser.add_argument("--require-promote", action="store_true", help="exit 2 unless the run was promoted")
    args = parser.parse_args()
    if args.create:
        if CARD.exists():
            raise SystemExit("run card already exists; refusing to rewrite evidence")
        CARD.parent.mkdir(parents=True, exist_ok=True)
        CARD.write_text(json.dumps(make_card(inspect(args.template, args.lattice)), indent=2, allow_nan=False) + "\n")
    result = verify(args.template, args.lattice)
    b = result["measurement"]["bound"]
    o = result["measurement"]["previous_candidate"]
    print(f"VERIFIED NEGATIVE: {b['minimum_overlapping_dots']}/{b['candidate_dot_budget']} minimum; "
          f"historic CSR-1 {o['matching_dots']}/{b['candidate_dot_budget']} within 3 px; no submission")
    return 2 if args.require_promote else 0


if __name__ == "__main__":
    raise SystemExit(main())
