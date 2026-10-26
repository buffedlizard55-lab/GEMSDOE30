#!/usr/bin/env python3
"""Build deterministic Pages entry points from verified research receipts, not prose flags."""
from __future__ import annotations

import argparse
import csv
from html import escape
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.verify_current_run import verify, local_path
from scripts.verify_lsm_run import verify as verify_lsm

STYLE = "docs/assets/research.css"


def png_preview(template: Path, candidate: Path) -> bytes:
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(template) as ds:
        h, w = (ds.height + 3) // 4, (ds.width + 3) // 4
        sample = ds.read(1, out_shape=(h, w), masked=True, resampling=Resampling.nearest)
        footprint = ~np.ma.getmaskarray(sample) & np.isfinite(sample.filled(np.nan))
    with rasterio.open(candidate) as ds:
        dots = ds.read(1, out_shape=(h, w), masked=True, resampling=Resampling.average).filled(0) > 0
    image = np.full((h, w, 3), [244, 247, 245], dtype=np.uint8)
    image[footprint] = [216, 229, 223]
    image[dots] = [13, 104, 81]

    # Small standard-library PNG encoder: no plot/image dependency or remote asset.
    def chunk(kind: bytes, content: bytes) -> bytes:
        return struct.pack("!I", len(content)) + kind + content + struct.pack("!I", zlib.crc32(kind + content))

    raw = b"".join(b"\x00" + row.tobytes() for row in image)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def e(value) -> str:
    return escape(str(value), quote=True)


def score_row(name: str, row: dict) -> str:
    lo, hi = row["ci95"]
    return f'<tr><th scope="row">{e(name)}</th><td>{row["value"]:.6f}</td><td>[{lo:.6f}, {hi:.6f}]</td></tr>'


def delta_row(name: str, row: dict) -> str:
    lo, hi = row["ci95"]
    sign = "+" if row["value"] >= 0 else ""
    s_lo = "+" if lo >= 0 else ""
    s_hi = "+" if hi >= 0 else ""
    return f'<tr><th scope="row">{e(name)}</th><td>{sign}{row["value"]:.6f}</td><td>[{s_lo}{lo:.6f}, {s_hi}{hi:.6f}]</td></tr>'


def load_site_summary() -> dict:
    """Load the curated nine-site page data and reconcile scores to the ledger."""
    path = ROOT / "docs/research/2026-10-26/site-score-summary.json"
    summary = json.loads(path.read_text())
    expected = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    if [row["site"] for row in summary["sites"]] != expected:
        raise ValueError("priority-site summary must contain exactly the nine requested sites in order")
    if summary.get("score_class") != "OWNER-REPORTED / UNVERIFIED":
        raise ValueError("priority-site score values must remain owner-reported and unverified")
    if summary.get("organizer_confirmed_scores") != [] or summary.get("organizer_receipts_audited") != 0:
        raise ValueError("no organizer-confirmed site score is backed by a receipt in this review")
    ledger_path = ROOT / "docs/score-ledger.csv"
    claims = {}
    with ledger_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            try:
                score = float(row["score"])
            except (TypeError, ValueError):
                continue
            if row.get("evidence_class") == "user-report" and row.get("site") in expected:
                claims.setdefault(row["site"], []).append((score, row["submission"]))
    for site in summary["sites"]:
        records = claims.get(site["site"], [])
        if not records:
            raise ValueError(f"no owner-reported score-ledger row for {site['site']}")
        best = max(records)
        if best[1] != site["highest"]["submission"] or abs(best[0] - site["highest"]["score"]) > 1e-9:
            raise ValueError(f"site summary does not match highest ledger claim for {site['site']}")
        if site.get("organizer_confirmed_score") is not None:
            raise ValueError(f"organizer-confirmed claim requires an official receipt: {site['site']}")
        recent = site.get("newer_claim")
        if recent is not None and not any(
            submission == recent["submission"] and abs(score - recent["score"]) < 1e-9
            for score, submission in records
        ):
            raise ValueError(f"newer owner claim is missing from the score ledger: {site['site']}")
    return summary


def page(title: str, content: str, card: dict, research_dir: str, *, active: str = "home") -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMSDOE30 research evidence, owner-reported score audit, and an explicit notice that no contest upload is approved.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery research</a>
<nav aria-label="Main navigation"><a href="index.html"{' aria-current="page"' if active == "home" else ''}>Overview</a><a href="executive-summary.html"{' aria-current="page"' if active == "guide" else ''}>Research summary</a><a href="submission-process.html"{' aria-current="page"' if active == "process" else ''}>Submission process</a><a href="site-summaries.html"{' aria-current="page"' if active == "sites" else ''}>Site scores</a><a href="experiment-review.html"{' aria-current="page"' if active == "research" else ''}>Research review</a><a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated checks are local research validation, not organizer acceptance.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{e(research_dir)}/run-card.json">Run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Experiment recorded {e(card['created_utc'])}. Repository evidence only; not a live leaderboard projection. No competition slot selected or used.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release(card: dict, readiness: dict, research_dir: str, post_snapshot: dict) -> str:
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    v = card["validator_output"]
    h = card["holdout"]
    core_delta = h["candidate_minus"]["core19"]
    matched = h["candidate_minus"].get("msdb_poisson")
    passed = sum(g["status"] == "passed" for g in readiness["gates"])
    unknown = sum(g["status"] == "unknown" for g in readiness["gates"])
    post = post_snapshot["decision"]
    post_rows = len(post_snapshot["comparisons"])
    post_overlap = max((r["candidate_fraction_within_3px_of_reference"] for r in post_snapshot["comparisons"]
                        if r.get("candidate_fraction_within_3px_of_reference") is not None), default=0.0)
    matched_summary = (f'<p><strong>Matched-control result remains inconclusive:</strong> <code>msdb_edge − msdb_poisson = +{matched["value"]:.6f}</code>, paired 95% CI <code>[{matched["ci95"][0]:+.6f}, {matched["ci95"][1]:+.6f}]</code>, which crosses zero. This matched difference is inconclusive and is not a promotion gate. The formal paired-improvement readiness gate is against <code>core19</code>; no equivalence conclusion follows.</p>' if matched else '')
    return f'''<section class="release" aria-labelledby="release-title">
<aside class="no-upload-banner" role="alert"><strong>RESEARCH TIFF — NOT APPROVED FOR SUBMISSION. DO NOT UPLOAD TO DRIVENDATA.</strong><span>Downloadable only for research/reproducibility. Do not submit. <code>submission_approved=false</code>; no contest slot was selected.</span></aside>
<div class="release-heading"><span class="pill caution">NOT APPROVED FOR CONTEST SUBMISSION</span><span class="pill caution">{passed}/{len(readiness["gates"])} recorded gates passed · {unknown} unknown</span></div>
<h2 id="release-title">Research copy available for download.<br><span>Not an approved contest upload.</span></h2>
<p><strong>Local machine checks are not organizer acceptance.</strong> The existing validator reopened <code>{e(file.name)}</code> and checked a single-band <code>float32</code> grid, <code>EPSG:32611</code>, <code>3,730 × 3,292</code>, finite in-footprint values in <code>[0, 1]</code>, null outside, and <code>0</code> catalogue pixels. These checks do not confirm that DrivenData will accept the TIFF. The current decision is negative; the lane assignment and complete parallel registry remain unknown. An additional post-placement screen against {post_rows} other public TIFFs did not cross the duplicate thresholds (max 3-px overlap <code>{100 * post_overlap:.2f}%</code>), but its result is <code>{e(post)}</code> because the inventory is incomplete and it cannot be a pre-placement certificate.</p>
{matched_summary}
<p><strong>Existing catalogue-proxy result only:</strong> <code>HOLDOUT-DTI {h['value']:.6f}</code>, evaluator <code>{e(h['evaluator_version'])}</code>, <code>{h['withheld_positives']:,}</code> withheld positives, 95% CI <code>[{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]</code>; versus the preregistered <code>core19</code> comparator, Δ <code>{core_delta['value']:+.6f}</code>, 95% CI <code>[{core_delta['ci95'][0]:+.6f}, {core_delta['ci95'][1]:+.6f}]</code>. This is not a leaderboard score or projection.</p>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download research TIFF — NOT FOR CONTEST UPLOAD <span>{size:.2f} MiB</span></a><a class="button secondary" href="{e(research_dir)}/readiness.json">View local gate receipt (JSON)</a><a class="button secondary" href="submission-process.html">Read submission process &amp; blockers</a></div>
<p class="filename">{e(file.name)}</p><details><summary>Local validation receipt &amp; exact file identity</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Run name</dt><dd><code>{e(card['submission_name'])}</code></dd><dt>Note</dt><dd><code>{e(card['note'])}</code></dd><dt>Local validator</dt><dd><code>PASSED locally</code> · 1 band <code>float32</code> · <code>EPSG:32611</code> · <code>3,730 × 3,292</code> · in-footprint finite: <code>{e(v['no_nan_inside_footprint'])}</code> · in <code>[0, 1]</code>: <code>{e(v['values_in_0_1'])}</code> · outside <code>NaN</code>: <code>{e(v['nan_nodata_outside_footprint'])}</code> · emitted dots: <code>{v['emitted_dots']:,}</code> (<code>{v['positive_catalogue_pixels']}</code> on known faults)</dd><dt>Receipt status</dt><dd><a href="{e(research_dir)}/validation.json">Local reopened-file check</a> · <a href="{e(research_dir)}/run-card.json">Run card</a> · organizer receipt: <strong>none</strong></dd></dl></details></section>'''


def arm_display_name(key: str) -> str:
    mapping = {
        "core19": "core19 · 19 raw bands + HGB + r=3.0 px Poisson-disk",
        "msdb_poisson": "msdb_poisson · 31 stationary MSDB × Rayleigh gate + r=3.0 px Poisson-disk",
        "msdb_edge": "msdb_edge · 31 stationary MSDB × Rayleigh gate + Bayes 300 m EDGE (Candidate)",
        "physics3": "physics3 · Three raw physics bands",
        "tdx6": "TDX-1 · Six-feature displacement candidate",
    }
    return mapping.get(key, key)


def site_score_page(summary: dict) -> str:
    rows = []
    for site in summary["sites"]:
        highest = site["highest"]
        latest = site.get("newer_claim")
        latest_html = (
            f'<strong>{latest["score"]:.4f}</strong> <span class="pill caution">OWNER-REPORTED / UNVERIFIED</span>'
            f'<br><code>{e(latest["submission"])}</code><br><a href="{e(latest["artifact_url"])}">Pinned artifact ↗</a>'
            f'<br><code class="hash">SHA-256 {e(latest.get("artifact_sha256", "not pinned"))}</code>'
            if latest else '<span class="fine">No newer lower claim supplied for this site.</span>'
        )
        rows.append(
            f'<tr><th scope="row"><a href="{e(site["owner_page_url"])}">{e(site["site"])}</a></th>'
            f'<td><strong>{highest["score"]:.4f}</strong> <span class="pill caution">OWNER-REPORTED / UNVERIFIED</span>'
            f'<br><code>{e(highest["submission"])}</code><br><a href="{e(highest["artifact_url"])}">Pinned artifact ↗</a>'
            f'<br><code class="hash">SHA-256 {e(highest["artifact_sha256"])}</code></td>'
            f'<td>{latest_html}</td><td>{e(site["executive_summary"])}</td>'
            f'<td><strong>None found.</strong><br><span class="fine">No organizer submission-page receipt in this repository review.</span></td></tr>'
        )
    h33 = next(row for row in summary["sites"] if row["site"] == "GEMSDOE32")
    return f'''<section class="critical-callout" role="note"><strong>Score classification:</strong> Every numeric site value below is an <strong>OWNER-REPORTED / UNVERIFIED</strong> claim, not an organizer-confirmed score. The review found no official submission-page receipts tying scores to exact TIFF bytes. The owner-site artifacts are useful provenance links, not score receipts.</section>
<section class="intro"><div><p class="eyebrow">Nine-site score digest · evidence snapshot 2026-10-26</p><h1>Highest reported claims,<br>with receipt status explicit.</h1><p class="lead">This page reports the highest numeric owner claim recorded for each requested site, plus the newer lower claim supplied for five sites. It is not a live leaderboard and makes no claim that the ledger covers every historical submission.</p></div><a class="text-link" href="docs/research/2026-10-26/site-score-summary.json">Open machine-readable summary ↗</a></section>
<section class="section"><p class="eyebrow">01 / Per-site claims</p><h2>None of these is organizer-confirmed.</h2><div class="table-wrap"><table><caption>Highest owner-reported value in the repository ledger per site; the score-to-file link is not receipt-authenticated</caption><thead><tr><th>Site</th><th>Highest recorded owner claim</th><th>Newer lower claim supplied</th><th>Executive summary / attribution limit</th><th>Organizer-confirmed score</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p class="fine">Historical values are shown only to answer the request and are not HOLDOUT-DTI measurements or projections. For a claim to be `ORGANIZER-CONFIRMED`, retain the official submission-page receipt and exact file identity.</p></section>
<section class="section two-column"><div><p class="eyebrow">02 / GEMSDOE32 H33: 0.2778 owner claim</p><h2>H33's bytes show pruning lineage, not a distinct geological method.</h2><p>The stored claim is <strong>{h33["highest"]["score"]:.4f} OWNER-REPORTED / UNVERIFIED</strong>. Its pinned 37,654-dot support is byte-exactly reconstructed as the GEMSDOE28 d=2.8 support (40,199 dots) minus 2,545 pixels within 2 pixels of catalogue labels; the reconstruction has zero pixel mismatches. That is consistent with spacing/pruning under the metric, not proof of a new geological discovery. The missing organizer receipt also means the reported score is not bound to those exact bytes.</p><p>A genuinely different method could beat this claim in principle. The repository has no organizer-confirmed result showing that one has done so. Catalogue-proxy HOLDOUT-DTI values cannot be compared numerically with this owner-reported contest claim.</p><p><a href="docs/research/2026-10-25/recipe-reconstruction.json">Byte-level recipe reconstruction ↗</a> · <a href="docs/research/h33-historical-duplicate-audit.json">Historical duplicate audit ↗</a></p></div><div class="note-card"><h3>D2.8 attribution caveat</h3><p>The historical D2.8 raster is pinned under GEMSDOE25 and appears as a byte alias under GEMSDOE24; the inspected current GEMSDOE25 main snapshot no longer lists that old path. An owner-page note also calls a related D2.8 file unscored/not slot-approved. The name, site attribution, and claimed score-to-file association therefore remain uncertain.</p><a href="docs/research/texture-controls/historical-reference-audit.json">Pinned historical reference audit ↗</a></div></section>
<section class="section"><p class="eyebrow">03 / Current GEMSDOE30 research TIFF</p><h2>Downloadable does not mean upload-approved.</h2><p>The current MSDB-1v2 research TIFF has a user-supplied 0.1462 score claim, unverified. Its separate catalogue-proxy <code>HOLDOUT-DTI 0.170462</code> is from evaluator <code>component-holdout-v3-blockstats-20261025</code>, with 60,988 withheld positives and 95% CI [0.156227, 0.184168]; this is not a contest score. The matched <code>msdb_edge − msdb_poisson</code> delta is +0.001135 with 95% CI [−0.002173, +0.004628], inconclusive.</p><p><a href="submission-process.html">Read the submission process and exact no-upload decision ↗</a> · <a href="index.html">Return to the research download page ↗</a></p></section>'''


def submission_process_page(card: dict, research_dir: str) -> str:
    return f'''<section class="critical-callout" role="alert"><strong>Current file status: NOT APPROVED FOR CONTEST UPLOAD.</strong> The TIFF linked from this site is a research/reproducibility download. Local format validation is not portal acceptance; no contest slot has been selected or spent.</section>
<section class="intro"><div><p class="eyebrow">Contest process · source-linked · no portal submission performed</p><h1>Research artifact first.<br>Portal receipt only after approval.</h1><p class="lead">The repository does not upload files, spend a weekly slot, or certify acceptance. The official rules and problem page control; check their live versions for deadlines, eligibility, and current portal instructions.</p></div><a class="text-link" href="docs/research/2026-10-26/data-source-check.md">Official-source and access notes ↗</a></section>
<section class="section"><p class="eyebrow">01 / The current artifact</p><h2>Do not upload this downloadable research TIFF.</h2><ul class="spaced"><li><strong>Not approved:</strong> <code>submission_approved=false</code>, overall research verdict negative, and no lane assignment or complete parallel registry.</li><li><strong>Local-only checks:</strong> the shared validator checked the exact TIFF's grid, type, in-footprint range, null outside, and catalogue exclusion. This does not establish that the DrivenData portal will accept it or that the owner-reported 0.1462 claim is genuine.</li><li><strong>Research evidence:</strong> existing <code>HOLDOUT-DTI {card['holdout']['value']:.6f}</code> is a catalogue-recovery proxy with evaluator <code>{e(card['holdout']['evaluator_version'])}</code>, <code>{card['holdout']['withheld_positives']:,}</code> withheld positives, and 95% CI <code>[{card['holdout']['ci95'][0]:.6f}, {card['holdout']['ci95'][1]:.6f}]</code>. It is not a leaderboard score.</li></ul><p class="callout"><strong>Downloadable research TIFF ≠ approved contest upload.</strong> Use the download only for research/reproducibility. Do not upload this file.</p></section>
<section class="section"><p class="eyebrow">02 / Official competition flow</p><h2>When a future candidate is genuinely ready.</h2><ol class="steps"><li><strong>Read the official problem page and rules.</strong><p>Use the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem specification</a> and the <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules</a>. Confirm live deadlines, eligibility, permitted data, and the actual portal instructions there; the repository does not invent a current deadline.</p></li><li><strong>Resolve the research and lane gates first.</strong><p>Before any experiment, obtain the assigned method lane and complete parallel registry; freeze a pre-placement continuous-surface registry; use whole-segment buffered holdout, exact visible-pixel masking, shared evaluator/writer, 2,000 paired geographic-block bootstrap draws, and single-feature leakage canaries. Stop for Spearman &gt; 0.90 or &gt;70% of dots within 3 px of a registered raster before or after placement.</p></li><li><strong>Promote and choose a slot as separate decisions.</strong><p>A future candidate must pass its exact-file local validator and the predeclared HOLDOUT-DTI gate against its assigned comparator(s). The existing <code>msdb_edge − msdb_poisson</code> interval is inconclusive and is not a promotion gate; it does not justify adding a new gate retroactively. Only a separate, authorized selector can choose or spend a weekly submission slot. The official rules describe a rolling weekly submission limit and a single final entry across the prize phases; re-check the official document for the controlling text.</p></li><li><strong>Upload only the exact authorized TIFF through the official portal.</strong><p>Do not upload JSON sidecars, HTML, score ledgers, or public reference rasters. The repository has no portal uploader and has not accessed the private submission page.</p></li><li><strong>Retain the organizer receipt and bind it to exact bytes.</strong><p>Record the official receipt, file identity, timestamp, and organizer-reported score. Only then may the score be labelled <code>ORGANIZER-CONFIRMED</code>. Without that receipt, retain the label <code>OWNER-REPORTED / UNVERIFIED</code>.</p></li></ol></section>
<section class="section"><p class="eyebrow">03 / What this page does not claim</p><h2>No acceptance guarantee, score projection, or slot selection.</h2><p>The local validator receipt is linked for reproducibility: <a href="{e(research_dir)}/validation.json">reopened-file validation</a>. It is not a portal response. The repository has not verified the latest leaderboard, current submission-page state, or any organizer score receipt in this review.</p><p><a href="site-summaries.html">Review the nine-site owner-claim digest ↗</a> · <a href="docs/research/2026-10-26/priority-site-public-review.md">Read the pinned evidence review ↗</a></p></section>'''


def build(template: Path) -> dict[Path, str | bytes]:
    pointer = ROOT / "docs/current-run.json"
    readiness = verify(pointer, template)
    selected = json.loads(pointer.read_text())
    card_path = local_path(selected["run_card"])
    research_dir = card_path.parent.relative_to(ROOT).as_posix()
    card = json.loads(card_path.read_text())
    h = card["holdout"]
    v = card["validator_output"]
    post_snapshot = json.loads((ROOT / "docs/research/2026-10-26/msdb1-postsnapshot-dot-audit.json").read_text())
    site_summary = load_site_summary()
    if post_snapshot.get("decision") != "blocked-incomplete-evidence" or post_snapshot.get("registry_complete") is not False:
        raise ValueError("post-placement novelty receipt must retain its incomplete-evidence blocker")
    post_overlap = max((row["candidate_fraction_within_3px_of_reference"] for row in post_snapshot["comparisons"]
                        if row.get("candidate_fraction_within_3px_of_reference") is not None), default=0.0)
    if readiness["research_verdict"] != "negative" or card["submission_approved"] is not False:
        raise ValueError("This negative-result site template must not be used to advertise a promoted/selected file")

    cand_key = card.get("candidate_arm", "tdx6")
    comp_keys = list(h["comparators"].keys())
    rows = "".join(score_row(arm_display_name(k), h["comparators"][k]) for k in comp_keys)
    rows += score_row(arm_display_name(cand_key), h)

    delta_rows = "".join(
        delta_row(f"{cand_key} minus {k}", h["candidate_minus"][k]) for k in comp_keys if k in h["candidate_minus"]
    )
    if "feature_only_ablation_msdb_poisson_minus_core19" in h:
        delta_rows += delta_row(
            "msdb_poisson minus core19 (pure geological representation gain)",
            h["feature_only_ablation_msdb_poisson_minus_core19"],
        )

    labels = {
        "file_contract": "Local GeoTIFF grid, EPSG:32611, [0,1] range & SHA-256 (not portal acceptance)",
        "labelled_holdout_evidence": "Pooled HOLDOUT-DTI & 2,000-rep spatial-bootstrap CI",
        "paired_improvement": "Beat preregistered core19 comparator (does not resolve msdb_poisson tie)",
        "single_feature_leakage_canaries": "Single-feature leakage canaries (AUC <= 0.90)",
        "count_matched_construction": "Exact count-matched active dot budget per fold",
        "surface_observed_registry": "Continuous surface check vs. recorded partial registry",
        "dots_observed_registry": "Final-dot check vs. recorded partial registry",
        "complete_parallel_registry": "Complete parallel-run registry (unknown)",
        "assigned_lane": "External lane-allocation attestation",
        "comparable_historical_best": "Same-protocol historical model checkpoint rerun",
        "experimental_budget": "Experiment & runtime budget (<= 3 runs, <= 2 h)",
        "artifact_identity": "Artifact name & <= 140-char note",
    }
    gates = "".join(
        f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in readiness["gates"]
    )

    score_table = f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld fault pixels · 371 geographic blocks · 2,000 paired bootstrap draws</caption><thead><tr><th>Fixed count-matched arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="table-wrap"><table><caption>Paired Spatial-Block Differences (same folds, identical active dot counts)</caption><thead><tr><th>Comparison</th><th>Δ HOLDOUT-DTI</th><th>95% Paired CI</th></tr></thead><tbody>{delta_rows}</tbody></table></div>
<p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code> (<code>{e(h['protocol_version'])}</code>, <code>17 px</code> regional buffer &ge; <code>{card.get('physical_support_px', 13)} px</code> physical filter support). Catalogue-recovery proxy measurements only—<strong>never organizer scores or leaderboard projections</strong>. Full derivation: <a href="{e(research_dir)}/review.md">scientific review</a>.</p>'''

    preview_rel = "docs/assets/msdb1-support.png"
    canary_n = card["feature_canaries"]["features_per_fold"]
    canary_folds = card["feature_canaries"]["folds"]
    home = f'''{release(card, readiness, research_dir, post_snapshot)}
<section class="intro"><div><p class="eyebrow">DOE GEMS · Existing MSDB-1v2 research result · 25 October 2026</p><h1>Steerable piedmont discontinuities.<br>+0.036834 HOLDOUT-DTI vs. core19.</h1><p class="lead">The existing spatially blocked run improves on its preregistered <code>core19</code> baseline. Its separate <code>msdb_edge − msdb_poisson</code> delta is <code>+0.001135</code> with 95% CI <code>[−0.002173, +0.004628]</code>, crossing zero. This is research evidence, not an organizer score or proof that the matched arms are equivalent.</p><p class="meta">Experiments run: {card['experiments_run']} / {card['experiment_cap']} <span>·</span> {card['experimental_elapsed_seconds']:.1f}s / 7,200s recorded budget <span>·</span> No slot selected or used</p></div><a class="text-link" href="{e(research_dir)}/preregistration.md">Read the frozen preregistration ↗</a></section>
<section class="evidence-strip" aria-label="Research diagnostics"><article><span>Emitted research dots</span><strong>{v['emitted_dots']:,} binary dots</strong><small>0 on known catalogue pixels; not contest approval</small></article><article><span>Post-placement public TIFF screen</span><strong>{len(post_snapshot['comparisons'])} other rasters</strong><small>Max 3-px overlap {100 * post_overlap:.2f}%; decision blocked because registry is incomplete</small></article><article><span>Leakage canaries</span><strong>{canary_n} features × {canary_folds} folds</strong><small>{card["feature_canaries"]["alarm_count"]} alarms above 0.90 AUC</small></article></section>
<section class="two-column section"><div><p class="eyebrow">01 / Controlled 4-fold spatial holdout</p><h2>Four quadrants improve vs. core19.<br>Matched control unresolved.</h2><p>The existing evaluator <code>component-holdout-v3-blockstats-20261025</code> scored <code>60,988</code> withheld positives across four whole-component buffered quadrants (<code>buffer_px = 17 &ge; support_px = 13</code>). <code>msdb_edge</code> reaches <code>HOLDOUT-DTI 0.170462</code> (95% CI <code>[0.156227, 0.184168]</code>) versus <code>core19 0.133628</code> (95% CI <code>[0.118285, 0.148875]</code>), paired Δ <code>+0.036834</code> (95% CI <code>[+0.022322, +0.050315]</code>). This is a catalogue-recovery proxy result. The separate <code>msdb_edge − msdb_poisson</code> Δ is <code>+0.001135</code> (95% CI <code>[−0.002173, +0.004628]</code>), inconclusive and not a promotion gate.</p><p class="fine">Experiment 1 (<a href="{e(research_dir)}/experiment-1-duplicate-stop/receipt.json">archived duplicate-stop receipt</a>) halted before any fold evaluation when raw regional bands caused <code>71.44%</code> overlap with <code>G30-S19</code>. Experiment 2 removed the 6 regional coordinate-proxy/DC-level bands and added the fold-local Rayleigh curvilinear gate.</p>{score_table}<a class="text-link" href="{e(research_dir)}/results.json">All fold sufficient statistics &amp; 148 canary AUCs ↗</a></div><figure><img src="{preview_rel}" width="823" height="933" loading="lazy" alt="MSDB-1v2 research dots in dark green over the pale green competition footprint"><figcaption><span class="legend-dot"></span> MSDB-1v2 research support (44,090 binary off-catalogue dots) · downsampled preview; downloadable research TIFF preserves the exact 100 m EPSG:32611 grid and is not approved for contest upload.</figcaption></figure></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated machine inspection</p><h2>Every gate has a deterministic state.</h2></div><p>Passed, failed, or unknown.<br>Zero human raster inspection.</p></div><div class="table-wrap"><table><thead><tr><th>Automated gate</th><th>State</th><th>Machine rule</th></tr></thead><tbody>{gates}</tbody></table></div></section>
<section class="section two-column"><div><p class="eyebrow">03 / Forensic root cause of GEMSDOE32 H33 (owner claim 0.2778)</p><h2>H33's support follows a d=2.8 pruning recipe.</h2><p>The <code>0.2778</code> value is <strong>OWNER-REPORTED / UNVERIFIED</strong>; no organizer receipt binds it to exact TIFF bytes. Byte-level reconstruction (<a href="docs/research/2026-10-25/recipe-reconstruction.json">receipt</a>) shows the named <code>GEMSDOE32</code> <code>H33</code> support (<code>37,654</code> dots) equals <code>GEMSDOE28</code> solo <code>d=2.8</code> (<code>40,199</code> dots) minus <code>2,545</code> dots within <code>&le; 2 px</code> (<code>200 m</code>) of catalogue labels, with zero pixel mismatches. This establishes spacing/pruning lineage, not an independently verified geological discovery.</p><p>A distinct method could beat the H33 claim in principle, but no organizer-confirmed evidence shows that it has. Catalogue-proxy <code>HOLDOUT-DTI</code> cannot be compared with an owner-reported portal claim. Re-encoding, re-thinning, or slightly shifting the H33 support would not be a distinct method.</p><p>The official pooled DW-Tversky definition and organizer clarifications are linked for review; the current leaderboard was not refreshed in this review. See the full <a href="site-summaries.html">nine-site score digest</a> and the <a href="docs/research/2026-10-26/priority-site-public-review.md">pinned evidence review</a>.</p><a class="text-link" href="{e(research_dir)}/review.md">Full equations, holdout results &amp; band-metadata audit ↗</a></div><div class="note-card"><h3>Matched-control and novelty limits</h3><p><strong>HOLDOUT-DTI vs. core19:</strong> <code>+0.036834</code>, 95% CI <code>[+0.022322, +0.050315]</code>.</p><p><strong>Matched msdb_edge − msdb_poisson:</strong> <code>+0.001135</code>, 95% CI <code>[−0.002173, +0.004628]</code>; inconclusive, not equivalent.</p><p>Post-placement check: {len(post_snapshot['comparisons'])} other public TIFFs; maximum dot overlap <code>{100 * post_overlap:.2f}%</code>. Decision remains <code>blocked-incomplete-evidence</code>; it is not global novelty certification.</p><a href="docs/research/2026-10-26/msdb1-postsnapshot-dot-audit.json">Post-snapshot machine receipt ↗</a> · <a href="docs/research/2026-10-26/untried-hypotheses.md">Ranked untried hypotheses ↗</a></div></section>
<section class="section"><p class="eyebrow">04 / Preserved prior &amp; concurrent lanes</p><h2>Full repository audit trail.</h2><div class="resource-grid"><article><h3>TDX-1 &amp; TDX-C2 · displacement</h3><p>Preserved negative displacement runs (<a href="docs/research/texture-displacement/run-card.json">TDX-1 card</a>; <a href="docs/research/texture-controls/run-card.json">TDX-C2 duplicate-stop card</a>).</p><a href="experiment-review.html">Full cross-lane review ↗</a></article><article><h3>G30-S19 &amp; G30-S20 · habitat</h3><p>Concurrent lanes (<a href="docs/research/2026-10-25/lane-g30s19-run-card.json">G30-S19</a>; <a href="docs/research/2026-10-25-s20/run-card.json">G30-S20 duplicate-stop</a>). A post-placement dot-only screen against 204 public TIFFs peaked at <code>64.78%</code> within 3 px, but the complete registry remains unavailable; the receipt is <code>blocked-incomplete-evidence</code>, not a global novelty pass.</p><a href="docs/research/2026-10-26/msdb1-postsnapshot-dot-audit.json">Post-snapshot audit ↗</a></article><article><h3>H-CC1 &amp; Residual-ridge gate</h3><p>Preserved negative records on contact coincidence and catalogue-corridor magnetic residuals.</p><a href="docs/research/2026-10-25/h-cc1-run-card.json">H-CC1 card ↗</a> · <a href="docs/research/2026-10-25/run-card-residual-gate.json">Residual-gate card ↗</a></article></div></section>
<section class="section"><p class="eyebrow">05 / Verified official sources &amp; data catalog</p><h2>Primary DOIs, licenses, and code receipts.</h2><div class="resource-grid"><article><h3>Competition &amp; rules</h3><p>DrivenData problem page and NLR Official Rules. Check live deadline, eligibility, weekly limits, and portal instructions at the official sources; no live portal/leaderboard check was made in this review.</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem spec ↗</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Rules PDF ↗</a></article><article><h3>USGS GeoDAWN &amp; GDR 1391</h3><p>USGS GeoDAWN (DOI <code>10.5066/P93LGLVQ</code>, CC0) and GBCGE INGENIOUS compilation (DOI <code>10.15121/1881483</code>, CC BY 4.0).</p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN ↗</a> · <a href="https://gdr.openei.org/submissions/1391">OpenEI GDR 1391 ↗</a></article><article><h3>Machine status &amp; quarantined ledger</h3><p>Live-recomputed JSON status feed and all 119 quarantined owner-reported score rows.</p><a href="docs/status.json">Status JSON ↗</a> · <a href="docs/research/texture-displacement/owner-claims.csv">119 owner claims CSV ↗</a></article></div></section>'''

    guide_template = (ROOT / "docs/research/2026-10-26/pages/research-summary.html").read_text(encoding="utf-8")
    guide = guide_template
    guide_values = {
        "__RELEASE__": release(card, readiness, research_dir, post_snapshot),
        "__SCORE_TABLE__": score_table,
        "__EVALUATOR__": e(h["evaluator_version"]),
        "__WITHHELD__": f"{h['withheld_positives']:,}",
        "__RESEARCH_DIR__": e(research_dir),
        "__NAME__": e(card["submission_name"]),
        "__NOTE_LENGTH__": str(len(card["note"])),
        "__NOTE__": e(card["note"]),
        "__HASH__": e(card["raster_sha256"]),
    }
    for token, value in guide_values.items():
        guide = guide.replace(token, value)

    review_template = (ROOT / "docs/research/2026-10-26/pages/experiment-review.html").read_text(encoding="utf-8")
    core_delta = h["candidate_minus"]["core19"]
    matched_delta = h["candidate_minus"]["msdb_poisson"]
    review_values = {
        "__RESEARCH_DIR__": e(research_dir),
        "__SCORE_TABLE__": score_table,
        "__VALUE__": f"{h['value']:.6f}",
        "__EVALUATOR__": e(h["evaluator_version"]),
        "__POSITIVES__": f"{h['withheld_positives']:,}",
        "__CI_LOW__": f"{h['ci95'][0]:.6f}",
        "__CI_HIGH__": f"{h['ci95'][1]:.6f}",
        "__CORE_DELTA__": f"{core_delta['value']:+.6f}",
        "__CORE_CI_LOW__": f"{core_delta['ci95'][0]:+.6f}",
        "__CORE_CI_HIGH__": f"{core_delta['ci95'][1]:+.6f}",
        "__MATCHED_DELTA__": f"{matched_delta['value']:+.6f}",
        "__MATCHED_CI_LOW__": f"{matched_delta['ci95'][0]:+.6f}",
        "__MATCHED_CI_HIGH__": f"{matched_delta['ci95'][1]:+.6f}",
        "__POST_COUNT__": str(len(post_snapshot["comparisons"])),
        "__POST_MAX__": f"{100 * post_overlap:.2f}",
        "__POST_DECISION__": e(post_snapshot["decision"]),
    }
    research_html = review_template
    for token, value in review_values.items():
        research_html = research_html.replace(token, value)

    for extra in selected.get("additional_stopped_attempts", []):
        if extra.get("lane") == "G30-LSM":
            lsm_ready = verify_lsm(local_path(extra["pointer"]), template)
            if lsm_ready["ok_to_submit"] is not False:
                raise ValueError("G30-LSM stopped attempt must remain non-submittable")

    public_snapshot = json.loads((ROOT / "docs/research/2026-10-25/priority-site-public-snapshot.json").read_text())
    pub_rows = "".join(
        f'<tr><th scope="row"><a href="https://github.com/{e(row["repo"])}/tree/{e(row["ref"])}">{e(row["site"])}</a></th>'
        f'<td><code>{e(row["ref"][:12])}…</code></td><td>{row["published_tiffs"]}</td><td>{len(row["continuous_surface_path_candidates"])}</td></tr>'
        for row in public_snapshot["snapshots"]
    )
    inspected = public_snapshot["continuous_surface_discovery"].get("inspections") or []
    surf_rows = "".join(
        f'<tr><th scope="row">{e(row["site"])}</th><td><a href="{e(row["source_url"])}"><code>{e(row["source_path"])}</code></a></td>'
        f'<td>{e(row.get("format", "not inspected"))}</td><td>{e(row.get("future_surface_comparison_eligibility", "unknown"))}</td></tr>'
        for row in inspected
    ) or '<tr><td colspan="4">No surface metadata inspection recorded.</td></tr>'
    registry_review_html = f'''<section class="intro"><div><p class="eyebrow">Public Source Registry · 25 October 2026</p><h1>Immutable nine-site inventory.<br>Metadata, not scores.</h1><p class="lead">Immutable GitHub snapshots across all nine priority sites (<code>{public_snapshot["source_files"]}</code> TIFF source blobs, <code>{public_snapshot["unique_aligned_byte_sequences"]}</code> unique aligned byte sequences) preserved without altering any frozen experiment registry.</p></div><a class="text-link" href="docs/research/2026-10-25/priority-site-public-snapshot.json">Open machine receipt ↗</a></section>
<section class="section"><p class="eyebrow">01 / Byte-verified public inventory</p><h2>Nine requested repositories at immutable commits.</h2><div class="table-wrap"><table><caption>Public source scope only</caption><thead><tr><th>Repository</th><th>Immutable commit</th><th>TIFF source blobs</th><th>Candidate surface paths</th></tr></thead><tbody>{pub_rows}</tbody></table></div></section>
<section class="section"><p class="eyebrow">02 / Surface metadata groundwork</p><h2>Inspected public arrays remain conservatively marked unknown.</h2><div class="table-wrap"><table><caption>Potential public surfaces · never used as predictions</caption><thead><tr><th>Repository</th><th>Object</th><th>Container</th><th>Eligibility</th></tr></thead><tbody>{surf_rows}</tbody></table></div><p><a href="docs/research/2026-10-25/priority-site-public-review.md">Full source-sync review ↗</a> · <a href="experiment-review.html">Back to scientific review ↗</a></p></section>'''

    return {
        ROOT / "index.html": page("Research overview & no-upload decision", home, card, research_dir, active="home"),
        ROOT / "executive-summary.html": page("Research summary & holdout evidence", guide, card, research_dir, active="guide"),
        ROOT / "submission-process.html": page("Contest submission process & approval gates", submission_process_page(card, research_dir), card, research_dir, active="process"),
        ROOT / "site-summaries.html": page("Nine-site owner-reported score summary", site_score_page(site_summary), card, research_dir, active="sites"),
        ROOT / "experiment-review.html": page("Scientific review & nine-site audit", research_html, card, research_dir, active="research"),
        ROOT / "priority-registry-review.html": page("Public priority registry review", registry_review_html, card, research_dir, active="research"),
        ROOT / preview_rel: png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open current research download and submission decision.</a></p></body></html>\n',
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    p.add_argument("--check", action="store_true", help="fail if generated Pages files are stale")
    args = p.parse_args()
    outputs = build(args.template)
    for path, content in outputs.items():
        data = content.encode() if isinstance(content, str) else content
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"stale generated site file: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Site receipts, download link, and deterministic generated pages verified" if args.check else "Built current research Pages site")


if __name__ == "__main__":
    main()
