#!/usr/bin/env python3
"""Build an auditable executive summary for the nine priority GEMS repositories.

The owner supplied historical score/name associations, but no organizer submission
receipt binds those claims to a file hash.  This module deliberately keeps that
boundary in the generated JSON: it can rank *owner-reported claims* for review, but
it must never turn a historical name into a recommended upload.

The summary is deterministic.  It reads only committed evidence:

* ``docs/score-ledger.csv`` for explicitly quarantined user-report rows;
* ``docs/research/2026-10-25/recipe-reconstruction.json`` for byte-level lineage;
* ``docs/current-run.json`` and its run/readiness receipts for the current decision.

It makes no network request and does not inspect, select, upload, or alter a TIFF.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRIORITY_SITES = (
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
)

# These are interpretation boundaries, not geological claims inferred from a file
# name. The exact byte relationships are validated below against the reconstruction
# receipt before they are shown to a reader.
SITE_ADVISORIES = {
    "GEMSDOE24": (
        "The reported name is retained only as a historical lead. No organizer receipt "
        "binds its score to a TIFF hash, and no independent-lineage claim is made here."
    ),
    "GEMSDOE25": (
        "The named GEMSDOE25/GEMSDOE30 reference pair is byte-identical inside the "
        "footprint in the forensic receipt; it is not two independent strategies."
    ),
    "GEMSDOE27": (
        "The ledger name suggests a topology gap-closure family, but a filename is not "
        "causal evidence and no organizer receipt binds this score to bytes."
    ),
    "GEMSDOE28": (
        "The highest reported row is H36-1, while the H33 lineage audit uses a separate "
        "H27-4 d=2.8 reference. These must not be conflated as one measured result."
    ),
    "GEMSDOE30": (
        "The historical d2.8 reference is the byte-identical partner of a GEMSDOE25 "
        "reference; it is not eligible to be relabelled as a new submission."
    ),
    "GEMSDOE31": (
        "The selected GEMSDOE28/GEMSDOE31 references are byte-identical inside the "
        "footprint in the forensic receipt, so they are not independent evidence."
    ),
    "GEMSDOE32": (
        "H33 is exactly the audited GEMSDOE28 reference after deleting dots within 2 px "
        "of the catalogue (zero mismatching pixels); this is emission pruning, not a new "
        "independent prediction surface."
    ),
    "GEMSDOE33": (
        "No organizer receipt or byte-level relationship sufficient to certify an "
        "independent, uploadable strategy is available in the committed evidence."
    ),
    "GEMSDOE36": (
        "No organizer receipt or byte-level relationship sufficient to certify an "
        "independent, uploadable strategy is available in the committed evidence."
    ),
}

# These were ranked before the MSDB implementation in the frozen experiment-one
# preregistration.  Rank 1 was exercised; it remains unpromoted because its
# emitter-control paired interval crosses zero.  The remaining items are research
# prospects, not score forecasts or implementation instructions for an upload.
RANKED_GEOLOGICAL_HYPOTHESES = (
    {
        "rank": 1,
        "id": "MSDB-1",
        "name": "Multi-scale steerable discontinuity and piedmont cover-breach habitat",
        "physical_signal": "Co-aligned 100–300 m magnetic-tilt, vector-gravity, basement-ramp, topographic, and radiometric discontinuities at concealed relay ramps and piedmont splays.",
        "expected_dti_benefit": "Highest qualitative expected HOLDOUT-DTI benefit at preregistration; not a competition-score forecast.",
        "implementation_cost": "low–moderate (estimated ~4 CPU minutes in the frozen plan)",
        "official_free_source_status": "Uses supplied competition layers; optional verification sources are USGS GeoDAWN (DOI 10.5066/P93LGLVQ, CC0) and GDR 1391. Local inputs remain owner-mirror, not organizer-authenticated.",
        "current_status": "Executed as MSDB-1v2; feature gain over core19 is HOLDOUT-DTI evidence, but the primary emitter-control CI crosses zero, so it is not promoted.",
    },
    {
        "rank": 2,
        "id": "MT-HF-Saddle",
        "name": "Subsurface hydrothermal-upflow saddle and magnetotelluric alteration decoupling",
        "physical_signal": "Deep-versus-shallow conductivity inversion paired with magnetic-demagnetization troughs and local conductivity-saddle breaches.",
        "expected_dti_benefit": "Moderate qualitative potential; coarse regional layers limit 300 m localization.",
        "implementation_cost": "low (estimated ~2 CPU minutes in the frozen plan)",
        "official_free_source_status": "Requires independently checked INGENIOUS magnetotelluric and heat-flow archives (DOIs 10.5066/P9TWT2LU and 10.5066/P9BZPVUC); availability/coverage must be verified before implementation.",
        "current_status": "Not separately tested under a frozen holdout protocol.",
    },
    {
        "rank": 3,
        "id": "RadTC-Fan",
        "name": "Radiometric–topographic alluvial-fan truncation and regolith-age offset",
        "physical_signal": "Coherent radiometric-total-count/K–Th–U steps across subtle piedmont slope breaks caused by fan truncation and differing regolith ages.",
        "expected_dti_benefit": "Moderate qualitative potential where subaerial piedmont coverage exists; not a score forecast.",
        "implementation_cost": "low (estimated ~2 CPU minutes in the frozen plan)",
        "official_free_source_status": "USGS GeoDAWN K, eU, and eTh grids are cited in the plan (DOI 10.5066/P93LGLVQ, CC0); exact source, schema, licensing, and ROI coverage require automated verification.",
        "current_status": "Not separately tested as this mechanism under a frozen holdout protocol.",
    },
    {
        "rank": 4,
        "id": "WL-Strain",
        "name": "Walker Lane transtensional strain-partitioning and slip/dilation reactivation",
        "physical_signal": "Orientation-resolved geodetic strain projected onto inferred local fault strike to locate short transfer faults and horse-tail splays.",
        "expected_dti_benefit": "Lower standalone 300 m precision expected because strain varies at >10 km scale; potentially useful as a habitat term only.",
        "implementation_cost": "moderate (estimated ~5 CPU minutes in the frozen plan)",
        "official_free_source_status": "Plan cites public geodetic strain (DOI 10.1785/0220220153) and GDR 1391/Faulds structural material (DOI 10.15121/1881483); exact availability and spatial coverage remain gates.",
        "current_status": "Not separately tested under a frozen holdout protocol.",
    },
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read required JSON evidence: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON evidence must be an object: {path}")
    return payload


def reported_score(row: dict[str, str]) -> Decimal:
    value = (row.get("score") or "").strip()
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"non-numeric priority score {value!r} for {row.get('site')}") from exc
    if not (Decimal("0") <= parsed <= Decimal("1")):
        raise ValueError(f"priority score outside [0,1]: {value!r}")
    return parsed


def priority_rows(ledger: Path) -> dict[str, dict[str, str]]:
    required_columns = {
        "site", "submission", "score", "provenance", "status", "source_url",
        "notes", "evidence_class", "as_of_utc",
    }
    try:
        with ledger.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if set(reader.fieldnames or ()) != required_columns:
                raise ValueError("score ledger columns changed; update the priority-summary parser")
            rows = list(reader)
    except OSError as exc:
        raise ValueError(f"cannot read score ledger: {ledger}") from exc

    winners: dict[str, dict[str, str]] = {}
    for site in PRIORITY_SITES:
        candidates = [
            row for row in rows
            if row.get("site") == site
            and row.get("evidence_class") == "user-report"
            and (row.get("score") or "").strip()
        ]
        if not candidates:
            raise ValueError(f"no owner-reported score row for required priority site {site}")
        # Preserve a deterministic choice if score ties ever occur. Submission names
        # are identifiers, not a criterion for estimating quality.
        candidates.sort(key=lambda row: (reported_score(row), row["submission"]), reverse=True)
        winners[site] = candidates[0]
    return winners


def build_summary(root: Path = ROOT) -> dict[str, Any]:
    ledger = root / "docs/score-ledger.csv"
    reconstruction_path = root / "docs/research/2026-10-25/recipe-reconstruction.json"
    current_pointer_path = root / "docs/current-run.json"
    winners = priority_rows(ledger)
    reconstruction = load_json(reconstruction_path)

    expected_reconstruction = {
        "h25_h30_identical_in_footprint": True,
        "h28_h31_identical_in_footprint": True,
        "h33_exactly_matches_h28_pruned_with_catalogue_distance_gt_2px": True,
        "mismatching_pixels": 0,
    }
    for key, expected in expected_reconstruction.items():
        if reconstruction.get(key) != expected:
            raise ValueError(f"forensic reconstruction does not establish expected fact {key!r}")
    if not isinstance(reconstruction.get("base_dots"), int) or not isinstance(reconstruction.get("h33_dots"), int):
        raise ValueError("forensic reconstruction is missing integer support counts")

    pointer = load_json(current_pointer_path)
    run_card_path = root / str(pointer.get("run_card", ""))
    readiness_path = root / str(pointer.get("readiness", ""))
    run_card = load_json(run_card_path)
    readiness = load_json(readiness_path)
    if run_card.get("submission_approved") is not False or readiness.get("submission_approved") is not False:
        raise ValueError("priority summary only supports an explicitly unapproved current artifact")
    if (run_card.get("verdict") != "negative" or readiness.get("research_verdict") != "negative"
            or readiness.get("slot_selected") is not False):
        raise ValueError("priority summary requires the explicit negative, no-slot current decision")
    paired_gate = next((gate for gate in readiness.get("gates", []) if gate.get("name") == "paired_improvement"), None)
    if not isinstance(paired_gate, dict) or paired_gate.get("status") != "failed":
        raise ValueError("priority summary requires the corrected failed MSDB paired-improvement gate")

    sites = []
    for site in PRIORITY_SITES:
        row = winners[site]
        sites.append({
            "site": site,
            "highest_owner_reported_submission": row["submission"],
            # Keep the ledger spelling to avoid silently changing the reported
            # precision (for example 0.2710 -> 0.271).
            "highest_owner_reported_score": row["score"],
            "score_label": "OWNER-REPORTED / UNVERIFIED (not HOLDOUT-DTI; not ORGANIZER-CONFIRMED)",
            "source_url": row["source_url"],
            "reported_provenance": row["provenance"],
            "ledger_status": row["status"],
            "as_of_utc": row["as_of_utc"] or None,
            "re_use_decision": "DO NOT COPY, RENAME, OR SUBMIT",
            "executive_assessment": SITE_ADVISORIES[site],
        })

    winner = max(sites, key=lambda item: Decimal(item["highest_owner_reported_score"]))
    return {
        "schema_version": 1,
        "scope": {
            "priority_sites": list(PRIORITY_SITES),
            "score_evidence_boundary": (
                "Scores are user/owner-reported ledger claims. No organizer submission-page receipt "
                "in this repository binds any listed score to a TIFF hash."
            ),
            "as_of_utc": "2026-10-25",
            "fresh_live_leaderboard_read": False,
            "organizer_submission_receipts": [],
        },
        "selection_decision": {
            "recommended_historical_priority_site_submission": None,
            "status": "NO HISTORICAL PRIORITY-SITE TIFF IS APPROVED FOR COMPETITION UPLOAD",
            "reason": (
                "A high owner-reported value is not a submission receipt; known byte-lineage duplicates "
                "also fail the unique-method requirement."
            ),
            "current_research_artifact": {
                "run_id": run_card.get("run_id"),
                "tiff": run_card.get("published_tiff"),
                "raster_sha256": run_card.get("raster_sha256"),
                "download_for_research": bool(readiness.get("download_ok")),
                "research_verdict": readiness.get("research_verdict"),
                "paired_improvement_status": paired_gate["status"],
                "competition_upload_approved": False,
                "slot_selected": False,
                "display_status": readiness.get("display_status"),
            },
        },
        "highest_owner_reported_claim_among_priority_sites": {
            "site": winner["site"],
            "submission": winner["highest_owner_reported_submission"],
            "score": winner["highest_owner_reported_score"],
            "label": winner["score_label"],
        },
        "h33_interpretation": {
            "measured_byte_fact": (
                "The audited H33 support is exactly the audited H28 reference after removing "
                "catalogue-distance <= 2 px dots (zero support mismatches)."
            ),
            "plausible_mechanism_not_score_proof": (
                "With a 300 m distance-weighted Tversky metric, redundant nearby emissions can add "
                "false-positive mass faster than they add max-pooled truth coverage. Catalogue-flank "
                "pruning therefore plausibly improved the reported result, conditional on the reported "
                "score attribution being correct."
            ),
            "not_established": (
                "No organizer submission receipt proves the 0.2778 score-to-file association, and the "
                "raster relationship does not establish a new independent prediction surface or a "
                "generalizable geological mechanism."
            ),
        },
        "distinct_strategy_assessment": {
            "conclusion": (
                "A genuinely distinct geological belief surface could plausibly improve a future "
                "artifact, but this repository has no evidence that it will exceed 0.2778 or any "
                "current leaderboard value; no numerical competition forecast is made."
            ),
            "last_local_leaderboard_context": (
                "The linked scientific review records an organizer-published public snapshot dated "
                "2026-10-25 with #1 = 0.4413. This summary does not refresh or extrapolate it."
            ),
            "mandatory_evidence_before_any_upload": [
                "Pre-register a distinct physical mechanism, non-fault mimic, source/license/coverage checks, and a count-matched comparator.",
                "Use buffered whole-segment spatial holdout with visible-fault-only catalogue features, pixel-exact visible-fault masking, and pooled 300 m HOLDOUT-DTI with CI.",
                "Run individual feature leakage canaries; AUC > 0.90 is leakage until disproven.",
                "Stop on either continuous-surface Spearman > 0.90 or >70% final-dot overlap within 3 px against the observed registry.",
                "Pass format, paired-improvement, novelty, and readiness gates; only then let a separate slot selector decide."
            ],
            "ranked_hypotheses": list(RANKED_GEOLOGICAL_HYPOTHESES),
        },
        "forensic_lineage": [
            {
                "sites": ["GEMSDOE25", "GEMSDOE30"],
                "finding": "Named historical references are identical inside the footprint",
                "measured": reconstruction["h25_h30_identical_in_footprint"],
            },
            {
                "sites": ["GEMSDOE28", "GEMSDOE31"],
                "finding": "Named historical references are identical inside the footprint",
                "measured": reconstruction["h28_h31_identical_in_footprint"],
            },
            {
                "sites": ["GEMSDOE28", "GEMSDOE32"],
                "finding": "H33 support equals the audited H28 reference after removing catalogue-distance <= 2 px dots",
                "measured": reconstruction["h33_exactly_matches_h28_pruned_with_catalogue_distance_gt_2px"],
                "base_dots": reconstruction["base_dots"],
                "h33_dots": reconstruction["h33_dots"],
                "mismatching_pixels": reconstruction["mismatching_pixels"],
            },
        ],
        "sites": sites,
        "provenance": {
            "score_ledger": str(ledger.relative_to(root)),
            "score_ledger_sha256": sha256(ledger),
            "forensic_reconstruction": str(reconstruction_path.relative_to(root)),
            "forensic_reconstruction_sha256": sha256(reconstruction_path),
            "current_run_pointer": str(current_pointer_path.relative_to(root)),
            "current_run_pointer_sha256": sha256(current_pointer_path),
            "current_run_card": str(run_card_path.relative_to(root)),
            "current_readiness": str(readiness_path.relative_to(root)),
        },
    }


def canonical_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "docs/research/priority-site-executive.json",
        help="deterministic JSON summary path",
    )
    parser.add_argument("--check", action="store_true", help="fail if the output is stale")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    content = canonical_json(build_summary(ROOT))
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != content:
            raise SystemExit(f"stale priority-site executive summary: {output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
    print("Priority-site executive summary verified" if args.check else f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
