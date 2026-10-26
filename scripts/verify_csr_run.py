#!/usr/bin/env python3
"""Independently verify CSR-1 GeoTIFF bytes, novelty/canary receipts, and fail-closed decision.

Operates strictly from committed receipts plus ``sample_submission.tif`` and ``labels.tif``
so GitHub Actions CI can execute full end-to-end verification in <5 seconds without
downloading ``training_features.tif`` or 357 reference rasters.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

from gemsdoe30.csr_discontinuity import GUARD_PX, SUPPORT_PX, TRANSFORM_VERSION  # noqa: E402
from gemsdoe30.experiments import contract  # noqa: E402
from gemsdoe30.holdout import EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION  # noqa: E402
from gemsdoe30.readiness import assess  # noqa: E402
from gemsdoe30.submission import valid_template_mask, validate_submission_file  # noqa: E402

REPORT = ROOT / "docs/research/2026-10-26-csr"
MALFORMED_GEMS31_SHA = "774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _validate_novelty_receipt(audit_doc: dict, registry: dict, cand_sha: str | None, stage: str) -> None:
    require(audit_doc.get("stage") == stage, f"wrong novelty stage: {audit_doc.get('stage')} != {stage}")
    if cand_sha is not None:
        require(audit_doc.get("candidate_sha256") == cand_sha, "novelty candidate_sha256 mismatch")
    require(audit_doc.get("submission_approved") is False and audit_doc.get("registry_complete") is False,
            "novelty receipt cannot upgrade incomplete registry to global approval")
    require(audit_doc.get("errors") == [], f"unexpected novelty errors: {audit_doc.get('errors')}")
    expected = {r["sha256"] for r in registry["rasters"]}
    rows = audit_doc.get("comparisons", [])
    observed = {r["reference_sha256"] for r in rows}
    require(len(rows) == len(expected) == 357 and observed == expected,
            f"novelty comparison inventory mismatch: {len(rows)} vs {len(expected)}")
    for row in rows:
        rho = float(row["spearman_full_footprint"])
        require(math.isfinite(rho) and abs(rho) <= 0.90 and not row.get("identical_inside_footprint"),
                f"Spearman/identical novelty violation on {row.get('reference')}")
        if stage == "dots":
            ov = float(row["candidate_fraction_within_3px_of_reference"])
            require(0.0 <= ov <= 0.70, f"dot 3-px overlap violation ({ov}) on {row.get('reference')}")

    mal = audit_doc.get("malformed_exclusions_audited", [])
    require(len(mal) == 1 and mal[0]["reference_sha256"] == MALFORMED_GEMS31_SHA
            and mal[0]["invalid_in_footprint_cells"] == 2610312,
            "malformed GEMSDOE31 exclusion audit missing or altered")


def verify(directory: Path = REPORT, template: Path | None = None, labels_path: Path | None = None) -> dict:
    directory = Path(directory)
    template = Path(template or ROOT / "data/raw/sample_submission.tif")
    labels_path = Path(labels_path or ROOT / "data/raw/labels.tif")

    card = load_json(directory / "run-card.json")
    results = load_json(directory / "results.json")
    readiness = load_json(directory / "readiness.json")
    registry = load_json(directory / "registry.json")
    started = load_json(directory / "started.json")
    prereg = load_json(directory / "preregistration.json")
    cache_ver = load_json(directory / "cache-verification.json")
    feat_rec = load_json(directory / "feature-receipt.json")
    nov_surf = load_json(directory / "novelty-surface.json")
    nov_dots = load_json(directory / "novelty-dots.json")

    spec = contract(card)
    require(spec["id"] == results.get("experiment_spec") == "csr1", "wrong CSR-1 contract")
    prereg_md_sha = sha256_file(directory / "preregistration.md")
    prereg_json_sha = sha256_file(directory / "preregistration.json")
    reg_sha = sha256_file(directory / "registry.json")
    require(
        card["lane_preregistration_sha256"] == results["preregistration_md_sha256"]
        == started["preregistration_md_sha256"] == prereg_md_sha,
        "preregistration.md SHA-256 mismatch",
    )
    require(
        results["preregistration_json_sha256"] == started["preregistration_json_sha256"] == prereg_json_sha,
        "preregistration.json SHA-256 mismatch",
    )
    require(
        card["registry"]["registry_sha256"] == prereg["registry_sha256"] == started["registry_sha256"] == reg_sha,
        "registry.json SHA-256 mismatch",
    )
    require(
        cache_ver["all_cells_match_raw_sources"] is True
        and cache_ver["dataset_signature"] == card["dataset_signature"] == feat_rec["dataset_signature"],
        "dataset_signature provenance mismatch",
    )
    require(
        feat_rec["support_px"] == SUPPORT_PX == 16
        and feat_rec["guard_px"] == GUARD_PX == 17
        and feat_rec["transform_version"] == TRANSFORM_VERSION,
        "CSR-1 support/guard/version mismatch",
    )

    t_start = datetime.fromisoformat(started["started_utc"])
    t_end = datetime.fromisoformat(card["created_utc"])
    require(t_start < t_end, "chronology violation: started_utc >= created_utc")
    require(0 < int(card["experiments_run"]) <= int(card["experiment_cap"]) == 3, "experiment cap violated")
    require(0.0 < float(card["experimental_elapsed_seconds"]) <= 7200.0, "2-hour runtime cap violated")
    require(
        bool(card.get("submission_name"))
        and isinstance(card.get("note"), str)
        and 0 < len(card["note"]) <= 140,
        "submission identity/note contract violated",
    )

    # Verify holdout structure and exact match between results.json and run-card.json
    summary = results["summary"]
    require(
        summary["evaluator_version"] == EVALUATOR_VERSION
        and summary["protocol_version"] == SEGMENT_PROTOCOL_VERSION,
        "holdout evaluator/protocol mismatch",
    )
    require(
        math.isclose(float(card["holdout"]["value"]), float(summary["arms"]["csr_dispersed"]["value"]), abs_tol=1e-12)
        and math.isclose(float(card["holdout_dti"]), float(summary["arms"]["csr_dispersed"]["value"]), abs_tol=1e-12),
        "holdout metric mismatch between run-card.json and results.json",
    )
    folds = results["folds"]
    require(
        len(folds) == 4
        and {f["fold"] for f in folds} == {0, 1, 2, 3}
        and sum(int(f["withheld_positives"]) for f in folds) == 60988,
        "fold coverage / withheld_positives mismatch",
    )
    for f in folds:
        b = int(f["dot_budget_each_arm"])
        require(set(f["arms"]) == set(spec["arms"]), "missing arm in fold results")
        for arm_stats in f["arms"].values():
            require(int(arm_stats["emitted_pixels"]) == b, "count-matched fold budget violated")

    # Verify 81 x 4 = 324 leakage canaries
    canaries = results["feature_canaries"]
    require(len(canaries) == 4 and results["canary_alarms"] == [], "canary alarm or missing fold")
    for fc in canaries:
        require(len(fc["features"]) == len(spec["features"]) == 81, "incomplete canary feature list")
        for row in fc["features"]:
            raw_a = float(row["raw_auc"])
            uni_a = float(row["univariate_training_only_hgb_auc"])
            sym_a = float(row["max_symmetric_auc"])
            computed_sym = max(raw_a, 1.0 - raw_a, uni_a, 1.0 - uni_a)
            require(
                math.isclose(sym_a, computed_sym, abs_tol=1e-9)
                and sym_a <= 0.90
                and row["alarm_above_0_90"] is False,
                f"canary alarm or inconsistent AUC on {row['feature']}",
            )

    # Verify published GeoTIFF bytes, whole-array [0, 1], off-catalogue collar, and >= sqrt(8) spacing
    tif_path = ROOT / card["published_tiff"]
    require(tif_path.is_file(), f"missing published GeoTIFF: {tif_path}")
    actual_sha = sha256_file(tif_path)
    require(actual_sha == card["raster_sha256"] == card["sha256"], "published GeoTIFF SHA-256 mismatch")

    report = validate_submission_file(tif_path, template, require_finite_all_cells=True, portal_safe=True)
    require(report.passed, f"GeoTIFF format validation failed: {report.to_dict()}")

    with rasterio.open(template) as tpl_ds:
        fp_mask = valid_template_mask(tpl_ds, np)
    with rasterio.open(tif_path) as sub_ds:
        arr = sub_ds.read(1)
    with rasterio.open(labels_path) as lab_ds:
        cat = (lab_ds.read(1) > 0.5) & fp_mask

    require(np.isfinite(arr).all() and float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0,
            "whole-array finite [0, 1] guarantee failed")
    values_sha = hashlib.sha256(np.ascontiguousarray(arr[fp_mask], dtype=np.float32).tobytes()).hexdigest()
    require(values_sha == card["values_sha256"], "in-footprint values_sha256 mismatch")
    dots = arr > 0.5
    require(int(np.count_nonzero(dots)) == 44090, "unexpected emitted dot count")
    dist_cat = distance_transform_edt(~cat)
    require(int(np.count_nonzero(dist_cat[dots] <= 2.0)) == 0, "dots found within <= 2 px of catalogue")
    pts = np.argwhere(dots).astype(np.float64)
    nn, _ = cKDTree(pts).query(pts, k=2)
    require(float(nn[:, 1].min()) >= math.sqrt(8.0) - 1e-9, "inter-dot spacing below sqrt(8) px")

    # Verify both novelty receipts (and guarantee pre-placement surface SHA != binary dots raster SHA)
    require(
        bool(nov_surf.get("candidate_sha256")) and nov_surf.get("candidate_sha256") != actual_sha,
        "surface SHA cannot equal binary dots raster SHA",
    )
    _validate_novelty_receipt(nov_surf, registry, None, "surface")
    _validate_novelty_receipt(nov_dots, registry, actual_sha, "dots")

    reassessed = assess(
        card,
        results,
        format_passed=True,
        hash_matches=True,
        surface_audit=nov_surf,
        dots_audit=nov_dots,
        registry=registry,
        artifact_public=True,
    )
    require(reassessed == readiness, "recomputed readiness.json differs from committed receipt")
    require(
        card["verdict"] == "negative"
        and card["download_ok"] is True
        and card["ok_to_submit"] is False
        and card["submission_approved"] is False
        and card["slot_selected"] is False,
        "fail-closed negative submission flags violated",
    )
    return readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=REPORT)
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--labels", type=Path, default=ROOT / "data/raw/labels.tif")
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    res = verify(args.directory, args.template, args.labels)
    print(f"CSR-1 verified: research_verdict={res['research_verdict']} download_ok={res['download_ok']} ({len(res['gates'])} gates)")
    if args.require_promote and res.get("research_verdict") != "promote":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
