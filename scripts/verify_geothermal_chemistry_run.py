#!/usr/bin/env python3
"""Independently validate GDX-1 bytes, sufficient statistics and negative decision.

Does not refit, upload, choose a slot, rewrite historical receipts, or equate
readiness with format. Original continuous-surface bytes remain in the ignored
research cache; CI verifies their hash-bound receipts, not a reopened surface.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from gemsdoe30.experiments import contract
from gemsdoe30.geothermal_chemistry import CANDIDATE_COLUMNS, GUARD_PX, SUPPORT_PX
from gemsdoe30.readiness import assess, with_current_inventory
from gemsdoe30.holdout import EVALUATOR_VERSION, SEGMENT_PROTOCOL_VERSION, spatial_bootstrap
from gemsdoe30.submission import validate_submission_file, valid_template_mask
from scripts.verify_current_run import check_equal

REPORT = ROOT / "docs/research/2026-10-26-gdx"
INVALID = "774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546"
EXPECTED_PARITY = 0.13982063017811727


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_audit(audit, registry, candidate_sha, stage, *, allow_invalid):
    require(audit.get("candidate_sha256") == candidate_sha and audit.get("stage") == stage,
            "novelty candidate/stage identity mismatch")
    require(audit.get("submission_approved") is False and audit.get("registry_complete") is False,
            "novelty coverage/approval cannot be silently upgraded")
    allowed = {INVALID} if allow_invalid else set()
    expected = {row["sha256"] for row in registry["rasters"]}
    rows = audit.get("comparisons", [])
    observed = {row.get("reference_sha256") for row in rows}
    require(observed == expected - allowed and len(rows) == len(observed), "novelty reference inventory mismatch")
    require(expected - observed == allowed, "malformed-reference UNKNOWN must be preserved")
    errors = audit.get("errors", [])
    require(len(errors) == len(allowed) and (not errors or "non-finite values inside footprint" in str(errors)),
            "unexpected novelty error")
    if allow_invalid:
        bad = next(row for row in registry["rasters"] if row["sha256"] == INVALID)
        # The original surface receipt predates path-prefixed diagnostics.
        require(bad["path"] == "data/raw/registry-expanded/GEMSDOE31-ed22e5c02a6d659b69ebf2d7084cd01061963e02.tif",
                "malformed reference identity changed")
    for row in rows:
        rho = row.get("spearman_full_footprint")
        overlap = row.get("candidate_fraction_within_3px_of_reference")
        require(row.get("stage") == stage and isinstance(rho, (float, int)) and np.isfinite(rho),
                "undefined or wrong-stage comparison")
        require(bool(row.get("correlation_duplicate")) == (rho > .90), "correlation flag contradicts number")
        require(bool(row.get("dot_duplicate")) == (stage == "dots" and overlap is not None and overlap > .70),
                "dot flag contradicts number")
        require(not row.get("undefined") and not row.get("identical_inside_footprint")
                and rho <= .90 and (stage != "dots" or (overlap is not None and 0 <= overlap <= .70)),
                "mandatory duplicate-stop or undefined novelty comparison")
    require(audit.get("decision") == "blocked-incomplete-evidence", "incomplete registry cannot be a novelty pass")


def verify(directory=REPORT, template=None):
    directory = Path(directory)
    template = template or ROOT / "data/raw/sample_submission.tif"
    c = load(directory / "run-card.json")
    r = load(directory / "results.json")
    registry = load(directory / "registry.json")
    frozen = load(directory / "started.json")
    resume = load(directory / "resumed.json")
    feature = load(directory / "feature-receipt.json")
    spec = contract(c)
    require(spec["id"] == r.get("experiment_spec") == "gdx1", "wrong experiment contract")
    for key, filename in (("preregistration_sha256", "preregistration.md"), ("registry_sha256", "registry.json")):
        require(c.get(key) == frozen.get(key) == resume.get(key) == sha(directory / filename), "frozen plan/registry hash mismatch")
    require(c.get("amendment_sha256") == resume.get("amendment_sha256") == sha(directory / "amendment-A1.md"),
            "A1 recovery amendment mismatch")
    require(resume.get("runner_sha256") == sha(ROOT / "scripts/run_geothermal_chemistry.py"), "recovery runner changed after lock")
    require(frozen.get("transform_sha256") == resume.get("transform_sha256") == feature.get("transform_sha256")
            == sha(ROOT / "src/gemsdoe30/geothermal_chemistry.py"), "feature transform changed after lock")
    start = datetime.fromisoformat(frozen["started_utc"])
    recovery = datetime.fromisoformat(resume["started_utc"])
    end = datetime.fromisoformat(c["created_utc"])
    require(start < recovery < end and abs((end - start).total_seconds() - c["experimental_elapsed_seconds"]) < 3,
            "timer restarted or inconsistent chronology")
    require(c.get("experiments_run") == resume.get("planned_experiments") == c.get("experiment_cap") == 3
            and 0 < c["experimental_elapsed_seconds"] <= resume["max_seconds"] <= 7200, "experiment/time cap breached")
    cache = load(directory / "cache-verification.json")
    require(cache.get("all_cells_match_raw_sources") is True and cache.get("dataset_signature") == c.get("dataset_signature")
            == feature.get("dataset_signature"), "prepared-data provenance mismatch")
    require(feature.get("support_px") == SUPPORT_PX == 43 and feature.get("guard_px") == GUARD_PX == 46
            and not feature.get("forbidden_fields_read") and tuple(feature.get("candidate_columns", [])) == CANDIDATE_COLUMNS
            and tuple(feature.get("feature_names", [])) == spec["features"],
            "feature/support contract mismatch")
    extra_array = ROOT / "outputs/geothermal-chemistry/extra.npy"
    if extra_array.is_file():
        require(sha(extra_array) == feature["all_feature_array_sha256"], "saved recovery feature array changed")
    require(r.get("preregistration_sha256") == c["preregistration_sha256"], "results unbound to preregistration")
    recomputed = spatial_bootstrap(r["bootstrap_sufficient_statistics"], candidate="gdx12", replicates=2000, seed=3071)
    check_equal(recomputed, r["summary"], "recomputed holdout and paired CI")
    check_equal(recomputed["arms"]["gdx12"], {k: c["holdout"][k] for k in recomputed["arms"]["gdx12"]}, "run-card holdout")
    check_equal(recomputed["candidate_minus"], c["holdout"]["candidate_minus"], "run-card paired CI")
    check_equal({k: recomputed["arms"][k] for k in ("core19", "effort6")}, c["holdout"]["comparators"], "run-card comparators")
    require(c["holdout"].get("evaluator_version") == EVALUATOR_VERSION == recomputed["evaluator_version"]
            and c["holdout"].get("protocol_version") == SEGMENT_PROTOCOL_VERSION
            and c["holdout"].get("buffer_px") == GUARD_PX, "evaluator/protocol/guard mismatch")
    folds = r["folds"]
    require(len(folds) == 4 and {f["fold"] for f in folds} == set(range(4))
            and sum(f["withheld_positives"] for f in folds) == c["holdout"]["withheld_positives"] == 60988,
            "withheld-positive coverage mismatch")
    hidden = [h for f in folds for h in f["hidden_component_ids"]]
    require(len(hidden) == len(set(hidden)), "whole fault component withheld twice")
    for f in folds:
        require(f["buffer_px"] == GUARD_PX and f["metric_halo_px"] == 3
                and f["protocol_version"] == SEGMENT_PROTOCOL_VERSION, "fold protocol mismatch")
        for name in spec["arms"]:
            require(f["arms"][name]["emitted_pixels"] == f["dot_budget_each_arm"]
                    and f["arms"][name]["truth_pixels"] == f["withheld_positives"], "unequal arm budgets/truth")
    check_equal({name: {k: sum(b[k] for b in r["bootstrap_sufficient_statistics"][name])
                          for k in ("truth_pixels", "tp_weight", "fp_weight")}
                 for name in spec["arms"]},
                {name: {k: sum(f["arms"][name][k] for f in folds)
                          for k in ("truth_pixels", "tp_weight", "fp_weight")}
                 for name in spec["arms"]}, "pooled fold/block sums", tol=1e-8)
    names = feature["feature_names"]
    require(len(names) == len(set(names)) == 28 and len(r["feature_canaries"]) == 4
            and {f["fold"] for f in r["feature_canaries"]} == set(range(4)), "missing feature-alone canaries")
    alarms = []
    for fold in r["feature_canaries"]:
        require({x["feature"] for x in fold["features"]} == set(names) and len(fold["features"]) == 28,
                "each exact feature must have a univariate canary")
        for x in fold["features"]:
            require(x.get("heldout_positives") == next(f["withheld_positives"] for f in folds if f["fold"] == fold["fold"]),
                    "canary fold truth count mismatch")
            raw, nonlinear = x["raw_auc"], x["univariate_training_only_hgb_auc"]
            require(all(isinstance(v, (int, float)) and np.isfinite(v) and 0 <= v <= 1 for v in (raw, nonlinear)),
                    "undefined canary")
            alarm = max(raw, 1 - raw, nonlinear, 1 - nonlinear) > .90
            require(x["alarm_above_0_90"] == alarm, "canary alarm contradicts AUC")
            if alarm:
                alarms.append(x["feature"])
    require(not alarms and c["feature_canaries"].get("alarm_count") == 0, "leakage not cleared")
    scientific = all(d["ci95"][0] > 0 for d in recomputed["candidate_minus"].values())
    require(scientific is r.get("scientific_gate_passed") is c.get("scientific_gate_passed"), "scientific verdict contradicts paired CI")
    parity = load(directory / "comparator-parity.json")
    require(len(parity["folds"]) == 4 and {f["fold"] for f in parity["folds"]} == set(range(4))
            and all(f["buffer_px"] == 17 and f["protocol_version"] == SEGMENT_PROTOCOL_VERSION for f in parity["folds"])
            and sum(f["withheld_positives"] for f in parity["folds"]) == 60988,
            "parity fold protocol mismatch")
    parity_now = spatial_bootstrap(parity["bootstrap_sufficient_statistics"], candidate="core19", replicates=2000, seed=3071)
    check_equal(parity_now, parity["summary"], "parity bootstrap")
    require(abs(parity_now["arms"]["core19"]["value"] - EXPECTED_PARITY) < 1e-9
            and parity.get("exact_archive_parity") is True and c.get("archive_core19_parity_verified") is True,
            "archived comparator parity failed")
    raster = (ROOT / c["published_tiff"]).resolve()
    require(raster.is_relative_to(ROOT / "docs") and raster.stem == c["submission_name"] and 0 < len(c["note"]) <= 140,
            "public path/name/note invalid")
    require(sha(raster) == c["raster_sha256"], "raster hash mismatch")
    sidecar = load(raster.with_suffix(".json"))
    require(sidecar.get("output_sha256") == c["raster_sha256"] and sidecar.get("run_name") == c["submission_name"]
            and sidecar.get("note") == c["note"], "sidecar identity mismatch")
    require(all(sidecar.get(k) is False for k in ("ok_to_submit", "slot_selected", "submission_approved")),
            "sidecar cannot override negative decision")
    validator = c["validator_output"]
    require(all(validator.get(k) is True for k in ("no_nan_inside_footprint", "values_in_0_1", "crs_match",
                "shape_match", "transform_match", "single_float32_band", "nan_nodata_outside_footprint"))
            and validator.get("emitted_dots") == 44090 and validator.get("organizer_acceptance_confirmed") is False,
            "run-card validator contradicts current file contract")
    report = validate_submission_file(raster, template)
    require(report.passed and c["validator_output"].get("status") == "passed", "current file fails shared format validator")
    check_equal(report.to_dict()["checks"], load(directory / "validation.json")["checks"], "stored/current format checks")
    with rasterio.open(raster) as ds, rasterio.open(template) as tpl:
        a = ds.read(1)
        valid = valid_template_mask(tpl, np)
        require(ds.dtypes == ("float32",) and np.isfinite(a[valid]).all()
                and set(np.unique(a[valid])) == {0, 1} and np.isnan(a[~valid]).all()
                and np.count_nonzero(a[valid] > 0) == 44090, "binary probability/mask/count contract failed")
    labels_path = ROOT / "data/raw/labels.tif"
    require(sha(labels_path) == cache["raw_source_sha256"]["labels"], "catalogue source hash mismatch")
    with rasterio.open(labels_path) as source, rasterio.open(template) as tpl:
        require((source.shape, source.crs, source.transform) == (tpl.shape, tpl.crs, tpl.transform),
                "catalogue grid mismatch")
        catalogue = (source.read(1) > .5) & valid
    dots_xy = np.column_stack(np.nonzero((a > 0) & valid))
    require(np.count_nonzero(catalogue) == 60988
            and np.count_nonzero((a > 0) & (distance_transform_edt(~catalogue) <= 2)) == 0
            and c["validator_output"].get("positive_catalogue_pixels") == 0
            and c["validator_output"].get("dots_within_2px_of_catalogue") == 0
            and cKDTree(dots_xy).query(dots_xy, k=2)[0][:, 1].min() >= 3,
            "pixel-exact catalogue mask/2px halo/3px spacing failed")
    surface = load(directory / "novelty-surface.json")
    dots = load(directory / "novelty-dots.json")
    for stage, audit, digest in (("surface", surface, c["surface_sha256"]), ("dots", dots, c["raster_sha256"])):
        require(audit.get("registry_sha256") == c["registry_sha256"]
                and audit.get("template_sha256") == sha(template), "novelty registry/template binding mismatch")
        validate_audit(audit, registry, digest, stage, allow_invalid=True)
    require(surface["candidate_sha256"] != dots["candidate_sha256"], "binary file substituted for continuous surface")
    saved_surface = ROOT / "outputs/geothermal-chemistry/gdx1-surface.tif"
    if saved_surface.is_file():
        require(sha(saved_surface) == c["surface_sha256"], "saved pre-placement surface changed")
    ready = assess(c, r, format_passed=True, hash_matches=True, surface_audit=surface, dots_audit=dots, registry=registry)
    check_equal(ready, load(directory / "readiness.json"), "archived readiness")
    require(c.get("verdict") == ready["research_verdict"] == "negative"
            and all(c.get(k) is False for k in ("ok_to_submit", "slot_selected", "submission_approved"))
            and c.get("organizer_score") is None and c.get("leaderboard_estimate") is None,
            "negative decision/score class changed")
    # A post-run byte audit adds the local FFL file without changing archived evidence.
    extra = load(directory / "registry-local-addendum.json")
    require(extra.get("original_registry_sha256") == c["registry_sha256"], "local registry addendum unbound")
    for row in extra["rasters"]:
        require(sha(ROOT / row["path"]) == row["sha256"], "local reference bytes changed")
    for stage, digest in (("surface", c["surface_sha256"]), ("dots", c["raster_sha256"])):
        extra_audit = load(directory / f"novelty-local-{stage}.json")
        require(extra_audit.get("registry_sha256") == sha(directory / "registry-local-addendum.json")
                and extra_audit.get("template_sha256") == sha(template), "local novelty registry/template binding mismatch")
        validate_audit(extra_audit, extra, digest, stage, allow_invalid=False)
    known = {row["sha256"] for row in registry["rasters"] + extra["rasters"]} | {c["raster_sha256"]}
    current = {sha(p) for p in (ROOT / "docs").rglob("*") if p.is_file() and p.suffix.lower() in (".tif", ".tiff")}
    ready = with_current_inventory(ready, recorded_hashes=known, current_hashes=current)
    ready["verification_scope"] = "Current TIFF reopened; CIs recomputed; historical continuous-surface receipts verified, not reopened in CI"
    ready["saved_surface_reopened"] = saved_surface.is_file()
    ready["catalogue_bytes_reopened"] = True
    ready["local_additional_comparisons_per_stage"] = len(extra["rasters"])
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=REPORT)
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    try:
        ready = verify(args.directory, args.template)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"GDX verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(ready, indent=2))
    return 2 if args.require_promote and ready["research_verdict"] != "promote" else 0


if __name__ == "__main__":
    raise SystemExit(main())
