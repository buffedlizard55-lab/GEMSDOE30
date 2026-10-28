"""Render the current fail-closed, nine-site preflight Pages from frozen receipts."""
from __future__ import annotations

import html
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = "docs/research/2026-10-27-registry-preflight"
CSR = "docs/research/2026-10-26-csr"


def e(value):
    return html.escape(str(value), quote=True)


def layout(title: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · GEMS30</title><meta name="description" content="Evidence-based GEMS30 research status, registry preflight and submission decision.">
<link rel="stylesheet" href="docs/assets/research.css"></head><body>
<a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> GEMS research</a>
<nav aria-label="Primary"><a href="index.html">Overview</a><a href="priority-executive-summary.html">Nine sites</a><a href="priority-readiness-audit.html">28 Oct byte audit</a><a href="csr-discontinuity-review.html">Research</a><a href="executive-summary.html">Submission guide</a><a href="pool1-executive-summary.html">POOL-1</a></nav>
</div></header><main id="main"><aside class="stop-notice" aria-label="Latest byte audit"><strong>28 Oct 2026: no approved submission download.</strong> <a href="priority-readiness-audit.html">Measured nine-site audit: exact files, format checks, uniqueness stops and unavailable score estimates</a>. No new TIFF or weekly slot.</aside>{body}</main><footer><div><strong>GEMS30 · research, not a selector</strong><p>Static evidence snapshot · verified 27 Oct 2026 · parallel work may change.</p></div><div><a href="{REPORT}/run-card.json">Current run card</a><a href="docs/status.json">GitHub status snapshot</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Organizer leaderboard</a></div>
<p class="fine">No automated organizer-page monitoring. Hash-pinned public mirrors are not organizer-authenticated. No competition slot selected.</p></footer></body></html>'''


def hero() -> str:
    return '''<section class="intro"><div><p class="eyebrow">GEMS30 / current decision / 27 Oct 2026</p>
<h1>Protect the next submission.</h1><p class="lead">A verified registry conflict stops the proposed run before a new model or TIFF is made. The older CSR-1 file must not be submitted.</p>
<div class="meta"><span>One-witness proof, not a complete registry</span><span>0 experiments run</span><span>No slot selected</span></div></div></section>'''


def upstream_artifacts_section(session_card: dict) -> str:
    """Disclose research TIFFs merged from upstream without presenting them as downloads."""
    rows = []
    candidates = session_card.get("upstream_merged_candidates", [])
    if len(candidates) != 2:
        raise ValueError("Current review must account for both upstream merged research TIFFs")
    for item in candidates:
        file = ROOT / item["path"]
        sidecar_file = file.with_suffix(".json")
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != item["raster_sha256"]:
            raise ValueError(f"Upstream candidate bytes do not match the review run card: {item['path']}")
        sidecar = json.loads(sidecar_file.read_text())
        if (sidecar.get("output_sha256") != item["raster_sha256"]
                or sidecar.get("format_validation", {}).get("passed") is not True
                or sidecar.get("whole_raster_range_diagnostic_passed") is not False):
            raise ValueError(f"Upstream candidate format/range evidence changed: {item['path']}")
        holdout = item.get("holdout_dti")
        if holdout:
            evaluation = json.loads((ROOT / "docs/research/candidate-holdout-evaluation.json").read_text())
            candidate_result = evaluation.get("candidate", {})
            if (evaluation.get("prediction_sha256") != item["raster_sha256"]
                    or evaluation.get("evaluator_version") != holdout["evaluator_version"]
                    or candidate_result.get("value") != holdout["value"]
                    or candidate_result.get("ci95") != holdout["ci95"]
                    or candidate_result.get("withheld_positives") != holdout["withheld_positives"]):
                raise ValueError(f"Upstream HOLDOUT-DTI receipt does not bind to the reviewed TIFF: {item['path']}")
        holdout_text = (
            f"HOLDOUT-DTI {holdout['value']:.6f} (not organizer score); "
            f"{holdout['withheld_positives']:,} withheld positives; spatial-block 95% CI "
            f"[{holdout['ci95'][0]:.6f}, {holdout['ci95'][1]:.6f}]"
            if holdout else "No verified HOLDOUT-DTI receipt located"
        )
        overlap = item["fraction_within_3px_of_13gems_lattice"]
        rows.append(
            f"<tr><th scope=\\\"row\\\"><code>{e(Path(item['path']).name)}</code></th>"
            f"<td>{item['dots']:,}</td><td><strong>{100*overlap:.2f}%</strong> within 3 px; "
            f"rank correlation {item['rank_correlation_vs_13gems_lattice']:.6f}</td>"
            f"<td>{e(holdout_text)}</td><td>Unavailable; no leaderboard forecast</td>"
            f"<td><strong>NO — duplicate-stopped; research only.</strong> File exists in the repository, "
            f"but this page offers no download control.</td></tr>"
        )
    return f'''<section class="stop-notice" id="upstream-artifacts"><div class="release-heading"><span class="pill failed">2 upstream TIFFs · DUPLICATE-STOP</span><span class="pill caution">NOT APPROVED TO DOWNLOAD OR SUBMIT</span></div>
<h2>Existing TIFFs are research artifacts, not approved entries.</h2>
<p>Two files arrived from upstream PRs #58/#59. Both pass the published-format checks, but their final-dot overlap with the pinned lattice exceeds the strict 70% stop. The low rank correlations do not cancel this independent dot-overlap failure. Pre-placement surface arrays were not available here, so surface novelty remains unverified. No competition score estimate is justified.</p>
<div class="table-wrap"><table><caption>Upstream research artifacts already present in this checkout; no download links</caption><thead><tr><th>File</th><th>Dots</th><th>3 px lattice audit</th><th>Catalogue holdout</th><th>Leaderboard estimate</th><th>Download / submit status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="fine">Each sidecar's published-format validation passes. The separate whole-array finite-range diagnostic fails because outside-footprint cells are NaN; portal behavior is unverified. These receipts are not a claim that DrivenData accepted either file. Details: <a href="docs/research/2026-10-27-current-session-review.md#upstream-research-artifacts-now-present-in-this-checkout--do-not-submit">current review</a> · <a href="docs/research/2026-10-27-current-session-run-card.json">audit run card</a>.</p></section>'''


def stop_card(card: dict) -> str:
    m = card["registry"]["measurement"]
    b, old = m["bound"], m["previous_candidate"]
    ctd, fc = m["parallel_candidates_merged_during_audit"]
    return f'''<section class="stop-notice" aria-labelledby="stop-title"><div class="release-heading"><span class="pill failed">DUPLICATE-STOP</span><span class="pill caution">NOT APPROVED FOR SUBMISSION</span><span class="pill caution">No new TIFF in this review</span></div>
<h2 id="stop-title">Do not submit. One published reference is enough to stop.</h2>
<p>The pinned 13GEMSDOE lattice covers all but <strong>{b['uncovered_pixels']:,}</strong> valid cells within 3 pixels. Any {b['candidate_dot_budget']:,}-dot candidate must overlap by at least <strong>{b['minimum_overlapping_dots']:,}/{b['candidate_dot_budget']:,} ({100*b['minimum_fraction_within_radius']:.4f}%)</strong>, above the strict 70% rule. We measured <strong>{old['matching_dots']:,}/{b['candidate_dot_budget']:,} ({100*old['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong> on the historical CSR-1 file.</p>
<p>The older 357-reference screen omitted this lattice. CSR-1 also fails the published-format validator because it has zeros outside the footprint. Its whole-array finite/range diagnostic passed; that is <em>not</em> proof of organizer acceptance or a remedy for the reported portal error.</p>
<p>Two files merged during this audit are also stopped: <strong>CTD-1 {ctd['matching_dots']:,}/{ctd['comparison']['candidate_dots']:,} ({100*ctd['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong> and <strong>FC-1 {fc['matching_dots']:,}/{fc['comparison']['candidate_dots']:,} ({100*fc['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong>. Their format checks pass, but their archived holdout used full-catalogue predictions before hiding faults and is not leakage-safe. <a href="{REPORT}/review.md#parallel-work-merged-during-this-audit">Details</a>.</p>
<div class="actions"><a class="button" href="{REPORT}/run-card.json">Open current run card</a><a class="button secondary" href="{REPORT}/review.md">Read proof &amp; reproduction</a><a class="button secondary" href="{e(old['path'])}" download>Historical CSR-1 · research only</a></div>
<p class="fine">Historical download only, not a new or approved candidate. SHA-256 <code>{e(old['raster_sha256'])}</code>. No submission identity or note was generated.</p></section>'''


def pool1_summary(pool_card: dict, dot_receipt: dict, *, detail: bool) -> str:
    """Render the independently verified POOL-1 negative without implying promotion."""
    h = pool_card["holdout"]
    d1 = h["candidate_minus"]["msdb_edge"]
    h2 = h["confirmation_seed4219"]
    d2 = h2["candidate_minus"]["msdb_edge"]
    matches = {}
    for row in dot_receipt["comparisons"]:
        ref = row["reference"]
        if "gems30-FFL1-fusion_edge" in ref:
            matches["FFL1"] = row["candidate_fraction_within_3px_of_reference"]
        elif "gems30-MSDB1-edge" in ref:
            matches["MSDB1-edge"] = row["candidate_fraction_within_3px_of_reference"]
        elif "gems30-CSR1-44090" in ref:
            matches["CSR1"] = row["candidate_fraction_within_3px_of_reference"]
    if set(matches) != {"FFL1", "MSDB1-edge", "CSR1"}:
        raise ValueError("POOL-1 duplicate references are missing from the frozen dot receipt")
    metrics = (f"{100*matches['FFL1']:.2f}% / {100*matches['MSDB1-edge']:.2f}% / "
               f"{100*matches['CSR1']:.2f}%")
    if detail:
        return f'''<section class="section" id="pool1"><div class="section-heading"><h2>Parallel lane POOL-1: best holdout mechanism, stopped raster.</h2><p>HOLDOUT-DTI improved twice; duplication blocks publication.</p></div><p><strong>POOL-1</strong> scored HOLDOUT-DTI <strong>{h['value']:.6f}</strong> and <strong>{h2['arms']['pool_dispersed']['value']:.6f}</strong> vs same-protocol <code>msdb_edge</code> (paired differences {d1['value']:+.6f} [{d1['ci95'][0]:+.6f}, {d1['ci95'][1]:+.6f}] and {d2['value']:+.6f} [{d2['ci95'][0]:+.6f}, {d2['ci95'][1]:+.6f}]; <code>{e(h['evaluator_version'])}</code>, {h['withheld_positives']:,} withheld positives). Final dots were within 3 px of FFL1 / MSDB1-edge / CSR1 at <strong>{metrics}</strong>, exceeding the 70% gate. <strong>No TIFF was published; no slot is approved.</strong> See <a href="pool1-executive-summary.html">POOL-1 review</a> · <a href="docs/research/2026-10-27-pool/run-card.json">run card</a> · verifier <code>scripts/verify_pool_run.py</code>.</p></section>'''
    return f'''<p class="fine"><strong>Parallel lane POOL-1:</strong> two-seed holdout improvement is not an upload approval. Its dots overlap FFL1 / MSDB1-edge / CSR1 at {metrics} within 3 px, above the 70% stop; no TIFF was published. See <a href="pool1-executive-summary.html">POOL-1 review</a>.</p>'''


def evidence_strip(card: dict) -> str:
    h = card["historical_holdout_reference"]
    c, base, diff = h["candidate"], h["matched_control"], h["paired_difference"]
    return f'''<div class="evidence-strip" aria-label="Historical holdout evidence"><article><span>Historical CSR-1 · HOLDOUT-DTI</span><strong>{c['value']:.6f}</strong><small>95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}]</small></article>
<article><span>Same-run msdb_edge · HOLDOUT-DTI</span><strong>{base['value']:.6f}</strong><small>95% CI [{base['ci95'][0]:.6f}, {base['ci95'][1]:.6f}]</small></article>
<article><span>Paired difference</span><strong>{diff['value']:+.6f}</strong><small>95% CI [{diff['ci95'][0]:+.6f}, {diff['ci95'][1]:+.6f}]</small></article></div>
<p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code> · {c['withheld_positives']:,} withheld positives · archived mapped-catalogue proxy, not an organizer score. The observed fold-3 gain was exploratory, not a confirmed breakthrough. No new holdout was run.</p>'''


def table(fleet: dict, card: dict) -> str:
    uncovered = card['registry']['measurement']['bound']['uncovered_pixels']
    rows = []
    for row in fleet['rows']:
        k = row['dots']
        lower = max(0, k - uncovered) / k
        aliases = ', '.join(row['exact_value_alias_sites'])
        alias = f' · value alias: {e(aliases)}' if aliases else ''
        fmt = 'passed' if row['format_validation_passed'] else 'outside-null failed'
        rows.append(f'''<tr><th scope="row"><a href="{e(row['review_url'])}">{e(row['site'])}</a><br><small>{k:,} dots</small></th>
<td><a href="{e(row['source_url'])}">{e(row['historical_file'])}</a><br><small>Historical file · {fmt}{alias}</small></td>
<td><strong>{e(row['quoted_owner_claim'])}</strong><br><small>unverified owner claim; no receipt</small></td>
<td><strong>Not available</strong><br><small>no validated new candidate; no forecast</small></td>
<td><strong>STOP</strong><br><small>≥{100*lower:.2f}% lower-bound overlap vs lattice</small></td><td><strong>DO NOT DOWNLOAD FOR SUBMISSION</strong><br><small>historical bytes only; no new file or slot approved</small></td></tr>''')
    return '''<div class="table-wrap"><table><caption>Frozen nine-site historical selections · 26 Oct 2026, not live leadership or a complete registry</caption><thead><tr><th scope="col">Site</th><th scope="col">Historical file / source</th><th scope="col">Reported value</th><th scope="col">New submission score estimate</th><th scope="col">Unique under literal rule?</th><th scope="col">Download / submit status</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div>
<p class="fine">Values are unverified owner reports, not HOLDOUT-DTI or ORGANIZER-CONFIRMED scores. “Not available” is deliberate: the listed historical scores cannot validly estimate an untested candidate. The lattice bound proves the literal duplicate stop for every listed historical dot budget; it does not prove all other comparisons or provide a novelty clearance. No fleet-wide selector has approved a slot.</p>'''


def h33(fleet: dict) -> str:
    lin = fleet['lineage']
    return f'''<section class="section" id="h33"><p class="eyebrow">What the bytes establish</p><h2>H33-B2 is a lineage, not a proven causal gain.</h2>
<p>The historical audit found value-identical G25/G30 rasters and a 40,199-dot G28 r1 intermediate identical to the selected G31 raster. H33-B2 is that intermediate with {lin['r1_to_h33_removed']:,} dots near mapped faults removed ({lin['h33_dots']:,} remain); the G36 reference contains H33-B2 plus {lin['pinn_additional_dots']:,} dots. The 37,660-dot G28 historical selection is a different file.</p>
<p>The owner reports <strong>0.2778</strong> for H33-B2, but no organizer receipt or hidden truth is available. We cannot infer hidden true/false positives, prove that pruning caused an improvement, or forecast a future score. The prior CSR review's numerical causal inversion and TP formula are not reliable.</p>
<a class="text-link" href="{CSR}/fleet-audit.json">Inspect frozen lineage evidence ↗</a></section>'''


def research_section() -> str:
    return f'''<section class="section" id="hypotheses"><div class="section-heading"><div><p class="eyebrow">Next work / subject to explicit lane assignment</p><h2>Four distinct research mechanisms.</h2></div><p>Qualitative priorities only.<br>No score forecasts or new experiments.</p></div>
<div class="resource-grid"><article><h3>1. Regime-gated experts</h3><p>Combine piedmont scarps with a cover-blind magnetic/gravity/MT expert; gate by a preregistered regime. Mimics: fan scarps, lava fronts and lithology. Cached layers; moderate modeling cost. Similar gating has been discussed in parallel work.</p></article>
<article><h3>2. Buried contact discordance</h3><p>Project geology-unit contacts beneath alluvium and compare with independent geophysical edges. Mimics: unfaulted unconformities. New geology data and moderate GIS work; exclude fault-derived tables.</p></article>
<article><h3>3. Drainage deflection</h3><p>Find repeated channel offsets/knickpoint alignments coincident with an independent geophysical edge. Mimics: terraces, roads and lava dams. Requires DEM conditioning and catchments.</p></article>
<article><h3>4. Alteration persistence</h3><p>Test GeoDAWN K/Th/U log-ratio residuals along coherent lines with a survey-block null. Mimics: soil, rock and flight-line seams. Cached radiometry; survey masks still needed.</p></article></div>
<p><a class="text-link" href="{REPORT}/review.md#ranked-geological-hypotheses--proposals-not-runs">Prior mechanisms, physical rationale, costs, and official sources ↗</a> · <a class="text-link" href="docs/research/2026-10-27-current-session-review.md">Current four-candidate ranking, source-access blockers, and three-pass review ↗</a> · <a class="text-link" href="docs/hypotheses.html">Full hypothesis register ↗</a></p></section>'''


def links_and_protocol() -> str:
    return f'''<section class="section two-column" id="protocol"><div><p class="eyebrow">Protocol &amp; sources</p><h2>What happens before a future slot.</h2><ol class="spaced"><li>Obtain a single assigned scientific lane and an explicit resolution of the literal registry constraint; do not reduce the budget merely to evade it.</li><li>Pre-register whole-segment, spatially buffered hide-and-recover folds; use visible faults only for catalogue-derived features, and audit each feature for leakage.</li><li>Beat the current same-protocol control with uncertainty, check surface and final dots against the complete current registry, and validate the exact saved bytes.</li><li>Require separate slot-selector approval. A missing gate, incomplete inventory or local format pass is not an upload authorization.</li></ol></div>
<div class="note-card"><h3>Authoritative links</h3><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Competition problem and format</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition and deadline</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules</a></p>
<p><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">GeoDAWN</a> · <a href="https://gdr.openei.org/submissions/1391">DOE INGENIOUS</a></p>
<p><strong>Deadline discrepancy:</strong> the competition page listed <strong>3 Dec 2026, 23:59 UTC</strong>, but the official rules PDF Appendix A.1 says 5:00 p.m. ET on the deadline date (22:00 UTC on 3 Dec). Confirm with the organizer and plan for the earlier time. The PDF allows up to three feedback submissions per week; one selected submission is scored on both label sets. Licensed, shareable external data are permitted.</p>
<p>Single float32 GeoTIFF, aligned to the organizer template, finite [0,1] in footprint and null outside. Mapped-fault pixels are masked in scoring. Portal rejection cause and upload acceptance are unknown.</p>
<p>Historical work: <a href="geothermal-chemistry-review.html">GDX-1</a> · <a href="geothermal-quadrature-review.html">QPC-1</a> · <a href="geothermal-tilt-alteration-review.html">G30-TAD</a>. Old status is not current approval.</p>
<p>The <a href="docs/status.json">GitHub-only status feed</a> regenerates from repository artifacts; it is not a live parallel registry. <a href="https://www.drivendata.org/termsofuse/">DrivenData terms</a> restrict automated access and monitoring, so the organizer page is linked, not scraped.</p></div></section>'''


def priority_page(row: dict, card: dict) -> str:
    site, k = row['site'], row['dots']
    uncovered = card['registry']['measurement']['bound']['uncovered_pixels']
    lower = max(0, k-uncovered)/k
    aliases = ', '.join(row['exact_value_alias_sites']) or 'none recorded in the selected nine files'
    check = 'passed' if row['format_validation_passed'] else 'failed: ' + ', '.join(row['failed_format_checks'])
    body = f'''<section class="intro"><div><p class="eyebrow">Pinned priority-site review · 26 Oct 2026</p><h1>{e(site)}</h1><p class="lead">Historical owner-identified best; not a current selector decision.</p></div></section>
<section class="stop-notice"><div class="release-heading"><span class="pill failed">Literal rule: duplicate-stop</span><span class="pill caution">No approved submission</span></div><h2>Do not resubmit historical bytes.</h2><p>The {k:,}-dot historical reference has a ≥{100*lower:.2f}% lower-bound overlap with the pinned 13GEMSDOE lattice. This bound uses the aligned footprint and the historical dot count; it is not an individual overlap measurement. Below-bound budgets are not automatically unique.</p>
<p>Owner-reported value <strong>{e(row['quoted_owner_claim'])}</strong> is unverified, not an organizer receipt or a HOLDOUT-DTI result. Latest parallel-site status is unknown from this frozen snapshot.</p>
<div class="actions"><a class="button secondary" href="{e(row['source_url'])}">Pinned historical source · not for upload</a><a class="button secondary" href="{e(row['site_url'])}">Open {e(site)} live page</a><a class="button secondary" href="priority-executive-summary.html">All nine sites</a></div></section>
<section class="section"><h2>Evidence and limitations.</h2><div class="table-wrap"><table><tbody><tr><th scope="row">Historical file</th><td><code>{e(row['historical_file'])}</code></td></tr><tr><th scope="row">SHA-256</th><td><code>{e(row['raster_sha256'])}</code></td></tr><tr><th scope="row">Pinned public snapshot</th><td><code>{e(row['public_snapshot_commit'])}</code></td></tr><tr><th scope="row">Historical format check</th><td>{e(check)}; local validation is not organizer acceptance.</td></tr><tr><th scope="row">Exact-value aliases</th><td>{e(aliases)}</td></tr><tr><th scope="row">New candidate / forecast</th><td>None validated or selected in this review.</td></tr></tbody></table></div><p><a href="{CSR}/fleet-audit.json">Nine-site frozen audit</a> · <a href="{REPORT}/review.md">Proof and source notes</a></p></section>'''
    return layout(site, body)


def render(card: dict, fleet: dict, pool_card: dict | None = None,
           pool_dots: dict | None = None, session_card: dict | None = None) -> dict[str, str]:
    if pool_card is None:
        pool_card = json.loads((ROOT / "docs/research/2026-10-27-pool/run-card.json").read_text())
    if pool_dots is None:
        pool_dots = json.loads((ROOT / "docs/research/2026-10-27-pool/novelty-dots.json").read_text())
    if session_card is None:
        session_card = json.loads((ROOT / "docs/research/2026-10-27-current-session-run-card.json").read_text())
    common = hero() + stop_card(card) + upstream_artifacts_section(session_card) + evidence_strip(card)
    overview = common + pool1_summary(pool_card, pool_dots, detail=True) + '''<section class="section"><div class="section-heading"><div><p class="eyebrow">Historical evidence / nine priority sites</p><h2>A fleet snapshot, not a leaderboard.</h2></div><p>Historic sources are linked.<br>No upload is authorized.</p></div>''' + table(fleet, card) + '</section>' + h33(fleet) + research_section() + links_and_protocol()
    summary = pool1_summary(pool_card, pool_dots, detail=False) + common + '''<section class="section"><p class="eyebrow">Submission guide</p><h2>There is no approved file to submit.</h2><p>Two upstream research TIFFs are present, but both are explicitly duplicate-stopped and have no download controls on this page. Do not upload them, the historical CSR-1 file, or a renamed old prediction, and do not use a weekly slot. CSR-1’s published-format failure and duplicate stop are independently sufficient blockers. A future submission requires the protocol and separate selector approval below.</p></section>''' + links_and_protocol()
    research = common + research_section() + h33(fleet) + links_and_protocol()
    priority = '''<section class="intro"><div><p class="eyebrow">Priority sites / frozen 26 Oct 2026</p><h1>Nine sites. One clear stop.</h1><p class="lead">Owner-reported historical scores, immutable source files and the literal lattice bound; not a live registry or submit selector.</p></div></section>''' + upstream_artifacts_section(session_card) + table(fleet, card) + h33(fleet) + links_and_protocol()
    pages = {'index.html': layout('Research overview', overview),
             'executive-summary.html': layout('Submission guide', summary),
             'csr-discontinuity-review.html': layout('Research review', research),
             'priority-executive-summary.html': layout('Nine-site evidence', priority)}
    for row in fleet['rows']:
        pages[row['review_url']] = priority_page(row, card)
    return pages
