#!/usr/bin/env python3
"""Compose the run card JSON from machine-readable receipts (no hand-typed numbers).

Reads the holdout receipts, duplicate receipts, the candidate sidecar, and re-runs the
shared validator on the final TIFF. Fails if the note exceeds 140 characters or any
receipt is missing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe30.submission import validate_submission_file  # noqa: E402

REC = ROOT / "docs/research/2026-10-25"
DOWN = ROOT / "docs/downloads"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    sidecars = sorted(DOWN.glob("gemsdoe30-h3a-residual-ridge-gate-p400-*-nan.json"))
    if len(sidecars) != 1:
        raise SystemExit(f"expected exactly one candidate sidecar, found {len(sidecars)}")
    sidecar_path = sidecars[0]
    tif = sidecar_path.with_suffix(".tif")
    side = load(sidecar_path)
    zero = load(REC / "residual-gate-holdout-buffer0.json")
    strict = load(REC / "residual-gate-holdout-buffer3500.json")
    novelty = load(REC / "residual-gate-novelty-dots.json")
    downloads = load(REC / "residual-gate-downloads-novelty.json")
    template = ROOT / "data/raw/sample_submission.tif"
    report = validate_submission_file(tif, template)
    if not report.passed:
        raise SystemExit("validator failed; refusing to write run card")

    note = side["submission_note"]
    if len(note) > 140:
        raise SystemExit("note exceeds 140 characters")
    arms0 = zero["arms"]
    arms3 = strict["arms"]
    card = {
        "schema_version": 2,
        "run_id": "gems30-review-hyp3-residual-ridge-gate-20261025",
        "generated_by": "scripts/make_run_card.py",
        "lane": None,
        "lane_status": ("No method-lane paragraph is identifiable in the current message. This session "
                        "chose review hypothesis 3 (docs/research/2026-10-25/review.md) as its own method; "
                        "no other session's lane was assumed."),
        "hypothesis": side["run_card"]["hypothesis"],
        "mechanism": side["run_card"]["mechanism"],
        "non_fault_mimic": side["run_card"]["non_fault_mimic"],
        "experiments_run": 3,
        "experiment_cap": 3,
        "time_cap_hours": 2,
        "design_doc": "docs/research/2026-10-25/candidate-residual-gate.md",
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": zero["evaluator_version"],
            "protocol_0m_stand_in": {
                "withheld_positives": zero["withheld_positive_pixels"],
                "dots_per_arm": zero["dots"]["A_residual_ridge_gate"],
                "candidate_A_dti": arms0["A_residual_ridge_gate"]["pooled_dti"],
                "candidate_A_ci95": arms0["A_residual_ridge_gate"]["ci95_tile_bootstrap"],
                "comparator_B_proximity_dti": arms0["B_proximity_comparator"]["pooled_dti"],
                "comparator_B_ci95": arms0["B_proximity_comparator"]["ci95_tile_bootstrap"],
                "ablation_D_raw_rtp_dti": arms0["D_ablation_raw_rtp_ridge"]["pooled_dti"],
                "random_control_R_dti": arms0["R_random_control"]["pooled_dti"],
                "paired_A_minus_B": zero["paired_A_minus_B_proximity_comparator"],
                "paired_A_minus_D": zero["paired_A_minus_D_ablation_raw_rtp_ridge"],
            },
            "protocol_strict_buffer_3500m": {
                "withheld_positives": strict["withheld_positive_pixels"],
                "candidate_A_dti": arms3["A_residual_ridge_gate"]["pooled_dti"],
                "note": "Gated arms are structurally zero under a 3.5 km buffer; see design doc.",
                "catalogue_free_E_dti": arms3["E_catalogue_free_residual_ridge"]["pooled_dti"],
                "catalogue_free_E_ci95": arms3["E_catalogue_free_residual_ridge"]["ci95_tile_bootstrap"],
                "random_control_R_dti": arms3["R_random_control"]["pooled_dti"],
                "random_control_R_ci95": arms3["R_random_control"]["ci95_tile_bootstrap"],
            },
            "stand_in_caveat": "Catalogue component split, not organizer labels; favours proximity; not a competition score.",
        },
        "feature_canaries": {
            "rule": "AUC outside [0.10, 0.90] = leakage review",
            "flagged": sorted(k for k, v in zero["feature_canaries"].items() if v["status"] != "ok"),
            "max_auc_0m": max(v["auc"] for v in zero["feature_canaries"].values()),
            "min_auc_0m": min(v["auc"] for v in zero["feature_canaries"].values()),
        },
        "registry_comparison": {
            "registry": "docs/research/priority-site-pins.json (complete=false, 9 rasters)",
            "stage_dots": {
                "decision": novelty["decision"],
                "max_spearman": max(c["spearman_full_footprint"] for c in novelty["comparisons"]),
                "max_fraction_within_3px": max(c["candidate_fraction_within_3px_of_reference"] for c in novelty["comparisons"]),
                "thresholds": "Spearman > 0.90 or > 70% within 3 px = duplicate",
            },
            "stage_surface": "blocked: continuous surfaces for registry rasters not reconstructed",
        },
        "repository_downloads_comparison": {
            "compared": downloads["references_compared"],
            "duplicates": downloads["duplicates"],
            "max_spearman": downloads["max_spearman"],
            "max_fraction_within_3px": downloads["max_fraction_within_3px"],
        },
        "raster": {
            "path": str(tif.relative_to(ROOT)),
            "sha256": side["raster_sha256"],
            "dots": side["dots"],
        },
        "validator_output": report.to_dict(),
        "submission_name": side["submission_name"],
        "submission_note": note,
        "note_length": len(note),
        "verdict": "negative",
        "verdict_reason": ("Below the count-matched proximity comparator on the 0 m stand-in and not "
                           "distinguishable from random dot density under the strict buffer. File is valid "
                           "and unique; not recommended for a weekly slot."),
        "organizer_score": None,
        "label": "NOT ORGANIZER-CONFIRMED",
        "submission_approved": False,
        "slot_selected": False,
        "generated_utc": side["generated_utc"],
    }
    out = REC / "run-card-residual-gate.json"
    out.write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {out} sha256={side['raster_sha256']} verdict=negative note_len={len(note)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
