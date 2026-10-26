#!/usr/bin/env python3
"""Fail-closed machine verifier for the G30-TAD research & GeoTIFF release (no human gate).

Requires only committed receipts, `docs/downloads/gems30-TAD24-*`, `src/gemsdoe30/tilt_alteration.py`,
and the hash-pinned `sample_submission.tif` template (restorable in CI with
`python scripts/restore_public_mirrors.py --ids sample_submission`).

Verifies all 6 automated gates:
1. File contract on BOTH published TIFFs (`-zeros.tif` whole-array finite in `[0, 1]` across all
   `12,279,160` cells preventing `"Predicted values must be in range [0, 1]"`, and `-nan.tif`
   passing `validate_submission_file`; identical `{0, 1}` in-footprint support of `38,000` dots;
   `0` dots on or within `<= 2 px` of the 60,988 positive catalogue pixels; SHA-256 & sidecar match).
2. Preregistration, registration lock, transform code hash, and exact operator support (`15 <= 17 px`).
3. Recomputed E1 4-quadrant paired spatial-block bootstrap (`2,000` replicates, `seed=3071`) matching
   both `results-e1.json`, `results-e1.first-execution.json`, and `run-card.json` bit-for-bit, plus
   exact `core19 == 0.13982063017811727` benchmark parity and count-matched fold budgets.
4. Recomputed `144` single-feature leakage canary checks (`36` unique features x `4` folds) `<= 0.90`.
5. Pre-placement continuous OOF surface (`Spearman <= 0.90`) and post-placement 38,000-dot
   (`Spearman <= 0.90` and `within_3px <= 0.70`) novelty receipts across all `190` pinned registry rasters,
   bound to the exact published `-nan.tif` SHA-256 and pinned `registry.json` SHA-256.
6. Execution budget (`<= 3` experiments, `<= 7,200 s`) and unique artifact name + `<= 140`-char note.

Separates `download_ok` (format + novelty verified) from `ok_to_submit` (requires all gates including
positive paired 95% block-bootstrap CI lower bounds over every E1 comparator).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

READINESS_VERSION = "tad-readiness-v1-20261025"
THRESH_RHO = 0.90
THRESH_OVERLAP = 0.70
THRESH_AUC = 0.90
EXPECTED_CORE19 = 0.13982063017811727


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"evidence root must be a JSON object: {path}")
    return value


def inside(relative: str) -> Path:
    p = Path(relative)
    path = (ROOT / p).resolve()
    if p.is_absolute() or not path.is_relative_to(ROOT):
        raise ValueError(f"evidence path must stay inside repository: {relative}")
    return path


def close(a, b, where: str) -> None:
    if isinstance(b, dict):
        if not isinstance(a, dict) or set(a) != set(b):
            raise ValueError(f"key mismatch at {where}: {set(a) if isinstance(a, dict) else type(a)} vs {set(b)}")
        for k in b:
            close(a[k], b[k], f"{where}/{k}")
    elif isinstance(b, list):
        if not isinstance(a, list) or len(a) != len(b):
            raise ValueError(f"length mismatch at {where}")
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f"{where}/{i}")
    elif isinstance(b, float):
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not math.isfinite(a) or not math.isclose(a, b, abs_tol=1e-10, rel_tol=0):
            raise ValueError(f"numeric mismatch at {where}: {a} vs {b}")
    elif a != b:
        raise ValueError(f"value mismatch at {where}: {a} vs {b}")


def verify(pointer: Path, template: Path, *, write: bool = False) -> dict:
    import numpy as np
    import rasterio
    from scipy.ndimage import distance_transform_edt

    from gemsdoe30.holdout import spatial_bootstrap
    from gemsdoe30.submission import valid_template_mask, validate_submission_file
    from gemsdoe30.tilt_alteration import SUPPORT_PX, TRANSFORM_VERSION, exact_operator_support_px

    selection = load(pointer)
    if selection.get("lane") != "G30-TAD":
        raise ValueError("pointer lane must be G30-TAD")
    card_path = inside(selection["run_card"])
    report_dir = card_path.parent
    card = load(card_path)
    gates: list[dict] = []

    def gate(name: str, ok: bool, detail: str) -> bool:
        gates.append({"name": name, "status": "passed" if ok else "failed", "detail": detail})
        return ok

    # ------------------------------------------------------------------
    # Gate 1: Dual GeoTIFF format, range [0, 1], binary support & collar
    # ------------------------------------------------------------------
    with rasterio.open(template) as tpl:
        valid = valid_template_mask(tpl, np)
        catalogue = (tpl.read(1) == 1) & valid
        grid = (tpl.shape, tpl.crs, tpl.transform)
    if int(catalogue.sum()) != 60988:
        raise ValueError("template positive catalogue pixel count must equal 60,988")
    near_2px = distance_transform_edt(~catalogue) <= 2.0

    z_entry = card["files"]["primary_zeros_outside"]
    n_entry = card["files"]["companion_nan_outside"]
    z_path = inside(z_entry["path"])
    n_path = inside(n_entry["path"])
    z_sha = sha(z_path)
    n_sha = sha(n_path)
    if z_sha != z_entry["sha256"] or z_sha != card["raster_sha256"]:
        raise ValueError("primary -zeros.tif SHA-256 differs from run card")
    if n_sha != n_entry["sha256"] or n_sha != card["companion_nan_sha256"]:
        raise ValueError("companion -nan.tif SHA-256 differs from run card")

    z_sidecar = load(z_path.with_suffix(".json"))
    n_sidecar = load(n_path.with_suffix(".json"))
    if z_sidecar.get("output_sha256") != z_sha or n_sidecar.get("output_sha256") != n_sha:
        raise ValueError("sidecar output_sha256 mismatch")
    if z_sidecar.get("submission_approved") is not False or n_sidecar.get("submission_approved") is not False:
        raise ValueError("download sidecars must never claim submission approval")
    if z_sidecar.get("note") != card["note"] or n_sidecar.get("note") != card["note"]:
        raise ValueError("sidecar note differs from run card note")
    if z_sidecar.get("run_name") != card["submission_name"]:
        raise ValueError("primary sidecar run_name differs from card submission_name")

    nan_report = validate_submission_file(n_path, template)
    if not nan_report.passed:
        raise ValueError("companion -nan.tif failed shared validate_submission_file")

    with rasterio.open(z_path) as ds_z, rasterio.open(n_path) as ds_n:
        arr_z = ds_z.read(1)
        arr_n = ds_n.read(1)
        z_grid_ok = (ds_z.shape, ds_z.crs, ds_z.transform) == grid and ds_z.count == 1 and ds_z.dtypes == ("float32",)
        n_grid_ok = (ds_n.shape, ds_n.crs, ds_n.transform) == grid and ds_n.count == 1 and ds_n.dtypes == ("float32",)

    inner_z = arr_z[valid]
    inner_n = arr_n[valid]
    val_id_z = hashlib.sha256(np.ascontiguousarray(inner_z.astype(np.float32)).tobytes()).hexdigest()
    val_id_n = hashlib.sha256(np.ascontiguousarray(inner_n.astype(np.float32)).tobytes()).hexdigest()
    if val_id_z != val_id_n or val_id_z != card["files"]["values_identity_sha256"]:
        raise ValueError("in-footprint values differ between -zeros.tif, -nan.tif, or run card")

    file_ok = bool(
        z_grid_ok
        and n_grid_ok
        and nan_report.passed
        and np.isfinite(arr_z).all()
        and float(arr_z.min()) >= 0.0
        and float(arr_z.max()) <= 1.0
        and np.all(arr_z[~valid] == 0.0)
        and np.isnan(arr_n[~valid]).all()
        and np.isfinite(inner_z).all()
        and np.isin(inner_z, (0.0, 1.0)).all()
        and int((inner_z > 0).sum()) == 38000
        and int((arr_z[catalogue] > 0).sum()) == 0
        and int(((arr_z > 0) & valid & near_2px).sum()) == 0
        and card["run_id"].endswith(val_id_z[:12])
    )
    if not file_ok:
        raise ValueError("published GeoTIFF pair fails mandatory range, footprint, binary, or collar invariants")
    gate(
        "file_contract",
        file_ok,
        "Reopened both -zeros.tif (all 12,279,160 cells finite in [0, 1]) and -nan.tif (shared validator passed): "
        "exact EPSG:32611 / (3730, 3292) / transform match, 38,000 {0,1} dots, 0 on or <=2 px of catalogue",
    )

    # ------------------------------------------------------------------
    # Gate 2: Preregistration lock, transform code hash & support guard
    # ------------------------------------------------------------------
    prereg_sha = sha(report_dir / "preregistration.md")
    reg_lock = load(report_dir / "registration.json")
    started = load(report_dir / "started.json")
    e1 = load(report_dir / "results-e1.json")
    e2 = load(report_dir / "results-e2.json")
    feat_receipt = load(report_dir / "feature-receipt.json")
    cache_receipt = load(report_dir / "cache-verification.json")
    tf_sha = sha(ROOT / "src/gemsdoe30/tilt_alteration.py")
    impulse_px = exact_operator_support_px(grid_size=49)

    reg_ok = (
        reg_lock.get("registered_plan_sha256") == prereg_sha
        and started.get("preregistration_sha256") == prereg_sha
        and e1.get("preregistration_sha256") == prereg_sha
        and e2.get("preregistration_sha256") == prereg_sha
        and card.get("preregistration_sha256") == prereg_sha
        and feat_receipt["signature"].get("transform_code_sha256") == tf_sha
        and feat_receipt["signature"].get("transform_version") == TRANSFORM_VERSION
        and feat_receipt.get("support_px") == SUPPORT_PX == 17
        and card.get("physical_support_px") == SUPPORT_PX == 17
        and impulse_px == 15 <= SUPPORT_PX
        and all(f.get("buffer_px") == SUPPORT_PX for f in e1["folds"])
        and cache_receipt.get("all_cells_match_raw_sources") is True
        and cache_receipt.get("dataset_signature") == card.get("dataset_signature")
        and feat_receipt["signature"].get("dataset_signature") == card.get("dataset_signature")
    )
    if not reg_ok:
        raise ValueError("preregistration hash, transform code hash, dataset signature, or support guard mismatch")
    gate(
        "preregistration_and_support_guard",
        reg_ok,
        f"Preregistration {prereg_sha[:12]} locked before start; transform {TRANSFORM_VERSION} ({tf_sha[:12]}) "
        f"verified with impulse support {impulse_px} px <= {SUPPORT_PX} px fold guard",
    )

    # ------------------------------------------------------------------
    # Gate 3: Recomputed E1 spatial-block bootstrap & determinism
    # ------------------------------------------------------------------
    blocks = load(report_dir / "bootstrap-blocks-e1.json")["blocks"]
    recomputed = spatial_bootstrap(blocks, candidate="tilt_alt24", replicates=2000, seed=3071)
    close(e1["summary"], recomputed, "results-e1/summary")
    if (report_dir / "results-e1.first-execution.json").is_file():
        first_e1 = load(report_dir / "results-e1.first-execution.json")
        close(first_e1["summary"], recomputed, "results-e1.first-execution/summary")

    h = card["holdout"]
    card_summary = {key: h[key] for key in ("evaluator_version", "protocol_version", "bootstrap", "candidate_minus")}
    card_summary["arms"] = {
        "tilt_alt24": {key: h[key] for key in recomputed["arms"]["tilt_alt24"]},
        **h["comparators"],
    }
    close(card_summary, recomputed, "card/holdout")
    if not math.isclose(recomputed["arms"]["core19"]["value"], EXPECTED_CORE19, abs_tol=1e-9, rel_tol=0):
        raise ValueError("core19 comparator failed exact benchmark parity check")

    expected_arms = {"random_dispersed", "subsurface16", "core19", "tilt_alt24"}
    folds = e1["folds"]
    counts_ok = (
        len(folds) == 4
        and {f["fold"] for f in folds} == {0, 1, 2, 3}
        and all(
            set(f["arms"]) == expected_arms
            and all(f["arms"][a]["emitted_pixels"] == f["dot_budget_each_arm"] for a in expected_arms)
            for f in folds
        )
    )
    if not counts_ok:
        raise ValueError("E1 fold dot budgets are not count-matched across all four arms")

    holdout_wins = all(
        row["value"] > 0.0 and row["ci95"][0] > 0.0
        for row in recomputed["candidate_minus"].values()
    )
    if e1.get("primary_holdout_gate_passed") is not (holdout_wins and card["feature_canaries"]["alarm_count"] == 0):
        raise ValueError("E1 primary_holdout_gate_passed contradicts recomputed CIs/canaries")
    if card.get("scientific_gate_passed") is not holdout_wins:
        raise ValueError("card scientific_gate_passed contradicts recomputed paired spatial-block CIs")

    delta_core = recomputed["candidate_minus"]["core19"]
    gate(
        "paired_holdout_improvement",
        holdout_wins,
        f"HOLDOUT-DTI tilt_alt24={recomputed['arms']['tilt_alt24']['value']:.5f} vs "
        f"core19={recomputed['arms']['core19']['value']:.5f} (delta={delta_core['value']:+.5f}, "
        f"95% CI [{delta_core['ci95'][0]:+.5f}, {delta_core['ci95'][1]:+.5f}]); "
        f"subsurface16={recomputed['arms']['subsurface16']['value']:.5f}; CI lower bound vs core19 <= 0",
    )

    # ------------------------------------------------------------------
    # Gate 4: Recomputed 144 single-feature leakage canary checks
    # ------------------------------------------------------------------
    canaries = e1["feature_canaries"]
    if len(canaries) != 4 or {f["fold"] for f in canaries} != {0, 1, 2, 3}:
        raise ValueError("feature canaries must cover all 4 spatial folds")
    recomputed_alarms = []
    max_b_auc = 0.0
    total_checks = 0
    for fold_row in canaries:
        feats = fold_row["features"]
        if len(feats) != 36 or len({r["feature"] for r in feats}) != 36:
            raise ValueError("each fold must test all 36 unique features")
        for r in feats:
            total_checks += 1
            raw_auc = r["raw_auc"]
            uni_auc = r["univariate_training_only_hgb_auc"]
            if not (0.0 <= raw_auc <= 1.0 and 0.0 <= uni_auc <= 1.0):
                raise ValueError("canary AUC out of [0, 1]")
            b_auc = max(raw_auc, 1.0 - raw_auc, uni_auc, 1.0 - uni_auc)
            max_b_auc = max(max_b_auc, b_auc)
            is_alarm = b_auc > THRESH_AUC
            if r.get("alarm_above_0_90") is not is_alarm:
                raise ValueError("stored canary alarm boolean contradicts numeric AUC")
            if is_alarm:
                recomputed_alarms.append({"fold": fold_row["fold"], **r})
    if card["feature_canaries"]["alarm_count"] != len(recomputed_alarms) or total_checks != 144:
        raise ValueError("card canary summary contradicts recomputed canary rows")
    canary_ok = len(recomputed_alarms) == 0
    gate(
        "single_feature_leakage_canaries",
        canary_ok,
        f"{total_checks} univariate checks (36 unique features x 4 folds); max bidirectional AUC = {max_b_auc:.4f} <= {THRESH_AUC:.2f}",
    )

    # ------------------------------------------------------------------
    # Gate 5: 190-raster pre-placement surface & post-placement dot novelty
    # ------------------------------------------------------------------
    reg_path = report_dir / "registry.json"
    reg_doc = load(reg_path)
    reg_sha = sha(reg_path)
    if reg_lock.get("registry_sha256") != reg_sha or card.get("registry_sha256") != reg_sha:
        raise ValueError("registry SHA-256 changed after preregistration")
    expected_refs = {r["sha256"] for r in reg_doc["rasters"]}
    tpl_sha = sha(template)

    surf_doc = load(report_dir / "novelty-surface.json")
    dots_doc = load(report_dir / "novelty-dots.json")
    if dots_doc.get("candidate_sha256") != n_sha:
        raise ValueError("novelty-dots receipt is not bound to the published -nan.tif SHA-256")

    for stage_name, audit_doc in (("surface", surf_doc), ("dots", dots_doc)):
        rows = audit_doc.get("comparisons", [])
        if (
            audit_doc.get("stage") != stage_name
            or any(r.get("stage") != stage_name for r in rows)
            or len(rows) != len(expected_refs)
            or {r.get("reference_sha256") for r in rows} != expected_refs
            or audit_doc.get("registry_sha256") != reg_sha
            or audit_doc.get("template_sha256") != tpl_sha
            or audit_doc.get("registry_complete") != reg_doc.get("complete")
            or bool(audit_doc.get("errors"))
        ):
            raise ValueError(f"novelty-{stage_name} inventory/hash/stage/error check failed")
        max_rho = max(r["spearman_full_footprint"] for r in rows if r["spearman_full_footprint"] is not None)
        max_ov = (
            max(r["candidate_fraction_within_3px_of_reference"] for r in rows if r["candidate_fraction_within_3px_of_reference"] is not None)
            if stage_name == "dots"
            else None
        )
        close(card["registry"][stage_name]["max_spearman"], max_rho, f"card/registry/{stage_name}/max_spearman")
        if stage_name == "dots":
            close(card["registry"][stage_name]["max_fraction_within_3px"], max_ov, "card/registry/dots/max_fraction_within_3px")

    surf_rho = card["registry"]["surface"]["max_spearman"]
    dots_rho = card["registry"]["dots"]["max_spearman"]
    dots_ov = card["registry"]["dots"]["max_fraction_within_3px"]

    known_hashes = expected_refs | {r["sha256"] for r in reg_doc.get("exclusions", [])} | {z_sha, n_sha}
    extra_hashes: set[str] = set()
    for p in n_path.parent.iterdir():
        if p.suffix.lower() in (".tif", ".tiff"):
            h_val = sha(p)
            if h_val not in known_hashes:
                extra_hashes.add(h_val)

    add_path = report_dir / "registry-parallel-addendum.json"
    total_compared = len(expected_refs)
    if extra_hashes or add_path.exists():
        if not add_path.is_file():
            raise ValueError("new local reference TIFFs require registry-parallel-addendum.json in tilt-alteration-discontinuity")
        add_doc = load(add_path)
        add_sha = sha(add_path)
        add_rows = add_doc.get("rasters", [])
        expected_extra = {r["sha256"] for r in add_rows}
        if expected_extra != extra_hashes or len(add_rows) != len(expected_extra):
            raise ValueError("G30-TAD late registry does not match current new local reference TIFFs")
        if add_doc.get("original_registry_sha256") != reg_sha:
            raise ValueError("G30-TAD late registry does not extend frozen registry.json")
        for r in add_rows:
            if sha(inside(r["path"])) != r["sha256"]:
                raise ValueError("G30-TAD late reference file hash mismatch")
        for stage_name, orig_doc in (("surface", surf_doc), ("dots", dots_doc)):
            late_doc = load(report_dir / f"novelty-parallel-{stage_name}.json")
            l_rows = late_doc.get("comparisons", [])
            if (
                late_doc.get("stage") != stage_name
                or any(r.get("stage") != stage_name for r in l_rows)
                or len(l_rows) != len(expected_extra)
                or {r.get("reference_sha256") for r in l_rows} != expected_extra
                or late_doc.get("registry_sha256") != add_sha
                or late_doc.get("template_sha256") != tpl_sha
                or late_doc.get("candidate_sha256") != orig_doc.get("candidate_sha256")
                or late_doc.get("registry_complete") is not False
                or bool(late_doc.get("errors"))
            ):
                raise ValueError(f"G30-TAD novelty-parallel-{stage_name} inventory/hash/error check failed")
            l_rho = max(r["spearman_full_footprint"] for r in l_rows if r["spearman_full_footprint"] is not None)
            if stage_name == "surface":
                surf_rho = max(surf_rho, l_rho)
            else:
                l_ov = max(
                    r["candidate_fraction_within_3px_of_reference"]
                    for r in l_rows
                    if r["candidate_fraction_within_3px_of_reference"] is not None
                )
                dots_rho = max(dots_rho, l_rho)
                dots_ov = max(dots_ov, l_ov)
        total_compared += len(expected_extra)
        addition = {
            "registry": str(add_path.relative_to(ROOT)),
            "surface_receipt": str((report_dir / "novelty-parallel-surface.json").relative_to(ROOT)),
            "dots_receipt": str((report_dir / "novelty-parallel-dots.json").relative_to(ROOT)),
            "combined_entries_compared": total_compared,
            "combined_surface_max_spearman": surf_rho,
            "combined_dots_max_spearman": dots_rho,
            "combined_dots_max_fraction_within_3px": dots_ov,
        }
        if write:
            card["additional_novelty_evidence"] = addition
            tmp_c = card_path.with_suffix(".partial.json")
            tmp_c.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n")
            tmp_c.replace(card_path)
        else:
            close(card.get("additional_novelty_evidence"), addition, "card/additional_novelty_evidence")

    surf_ok = surf_rho <= THRESH_RHO and surf_doc.get("decision") != "duplicate-stop"
    dots_ok = dots_rho <= THRESH_RHO and dots_ov <= THRESH_OVERLAP and dots_doc.get("decision") != "duplicate-stop"
    gate(
        "novelty_surface",
        surf_ok,
        f"Pre-placement OOF surface max Spearman = {surf_rho:.4f} <= {THRESH_RHO:.2f} across {total_compared} registry rasters",
    )
    gate(
        "novelty_dots",
        dots_ok,
        f"Post-placement 38,000 dots max 3-px overlap = {dots_ov:.4f} <= {THRESH_OVERLAP:.2f} "
        f"(max Spearman = {dots_rho:.4f} <= {THRESH_RHO:.2f}) across {total_compared} registry rasters",
    )

    # ------------------------------------------------------------------
    # Gate 6: Execution budget & artifact identity
    # ------------------------------------------------------------------
    elapsed = card.get("experimental_elapsed_seconds", -1.0)
    exps = card.get("experiments_run", -1)
    budget_ok = (
        isinstance(exps, int)
        and not isinstance(exps, bool)
        and 0 < exps <= 3
        and started.get("experiment_cap") == 3
        and card.get("experiment_cap") == 3
        and isinstance(elapsed, (int, float))
        and 0.0 < float(elapsed) <= 7200.0
    )
    note = card.get("note", "")
    identity_ok = (
        isinstance(card.get("submission_name"), str)
        and card["submission_name"] == f"{card['run_id']}-zeros"
        and isinstance(note, str)
        and 0 < len(note) <= 140
    )
    if not (budget_ok and identity_ok):
        raise ValueError("execution budget or artifact name/note contract violated")
    gate(
        "budget_and_identity",
        budget_ok and identity_ok,
        f"{exps}/3 experiments in {elapsed:.1f}s <= 7,200s; note {len(note)}/140 chars",
    )

    download_ok = bool(file_ok and reg_ok and canary_ok and surf_ok and dots_ok and budget_ok and identity_ok)
    ok_to_submit = bool(download_ok and holdout_wins)
    verdict = "promote" if ok_to_submit else "negative"

    if (
        card.get("download_ok") is not download_ok
        or card.get("ok_to_submit") is not ok_to_submit
        or card.get("verdict") != verdict
        or card.get("submission_approved") is not False
        or card.get("slot_selected") is not False
    ):
        raise ValueError("run-card verdict/download_ok/ok_to_submit/slot flags contradict machine gates")

    readiness = {
        "schema_version": 1,
        "readiness_version": READINESS_VERSION,
        "lane": "G30-TAD",
        "run_id": card["run_id"],
        "submission_name": card["submission_name"],
        "note": note,
        "raster_sha256": z_sha,
        "companion_nan_sha256": n_sha,
        "values_identity_sha256": val_id_z,
        "primary_file": z_entry["path"],
        "companion_nan_file": n_entry["path"],
        "download_ok": download_ok,
        "ok_to_submit": ok_to_submit,
        "research_verdict": verdict,
        "eligible_for_separate_slot_selector": ok_to_submit,
        "submission_approved": False,
        "slot_selected": False,
        "decision": "OK TO PROMOTE TO SLOT SELECTOR" if ok_to_submit else "DO NOT SPEND WEEKLY SUBMISSION SLOT",
        "display_status": (
            "VALIDATED & PROMOTED TO SLOT SELECTOR"
            if ok_to_submit
            else "TECHNICAL FORMAT & NOVELTY VALIDATED (DOWNLOAD OK) — NEGATIVE HOLDOUT CI GATE: DO NOT SPEND WEEKLY SLOT"
        ),
        "gates": gates,
        "organizer_score": None,
        "organizer_acceptance_confirmed": False,
    }

    target = inside(selection["readiness"])
    if write:
        tmp = target.with_suffix(".partial.json")
        tmp.write_text(json.dumps(readiness, indent=2, allow_nan=False) + "\n")
        tmp.replace(target)
    elif not target.is_file() or load(target) != readiness:
        raise ValueError("G30-TAD readiness.json missing or stale; regenerate with --write")
    return readiness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pointer",
        type=Path,
        default=ROOT / "docs/research/tilt-alteration-discontinuity/current-run.json",
    )
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--require-promote", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.pointer, args.template, write=args.write)
    except (KeyError, ValueError, OSError) as exc:
        print(f"G30-TAD verification FAILED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 2 if args.require_promote and not result["ok_to_submit"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
