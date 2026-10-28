"""Render the current fail-closed, nine-site preflight Pages from frozen receipts."""
from __future__ import annotations

import html
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
<nav aria-label="Primary"><a href="index.html">Overview</a><a href="priority-executive-summary.html">Nine sites</a><a href="csr-discontinuity-review.html">Research</a><a href="executive-summary.html">Submission guide</a><a href="pool1-executive-summary.html">POOL-1 history</a></nav>
</div></header><main id="main">{body}</main><footer><div><strong>GEMS30 · research, not a selector</strong><p>Static evidence snapshot · verified 27 Oct 2026 · parallel work may change.</p></div><div><a href="{REPORT}/run-card.json">Current run card</a><a href="docs/status.json">GitHub status snapshot</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Organizer leaderboard</a></div>
<p class="fine">No automated organizer-page monitoring. Hash-pinned public mirrors are not organizer-authenticated. No competition slot selected.</p></footer></body></html>'''


def hero() -> str:
    return '''<section class="intro"><div><p class="eyebrow">GEMS30 / current decision / 27 Oct 2026</p>
<h1>Protect the next submission.</h1><p class="lead">A verified registry conflict stops the proposed run before a new model or TIFF is made. The older CSR-1 file must not be submitted.</p>
<div class="meta"><span>One-witness proof, not a complete registry</span><span>0 experiments run</span><span>No slot selected</span></div></div></section>'''


def stop_card(card: dict) -> str:
    m = card["registry"]["measurement"]
    b, old = m["bound"], m["previous_candidate"]
    ctd, fc = m["parallel_candidates_merged_during_audit"]
    return f'''<section class="stop-notice" aria-labelledby="stop-title"><div class="release-heading"><span class="pill failed">DUPLICATE-STOP</span><span class="pill caution">NOT APPROVED FOR SUBMISSION</span><span class="pill caution">No new TIFF</span></div>
<h2 id="stop-title">Do not submit. One published reference is enough to stop.</h2>
<p><strong>File to download for a new submission: NONE.</strong> No new candidate exists, no defensible public-score estimate is available, and no slot is approved. Historical downloads below are research-only.</p>
<p>The pinned 13GEMSDOE lattice covers all but <strong>{b['uncovered_pixels']:,}</strong> valid cells within 3 pixels. Any {b['candidate_dot_budget']:,}-dot candidate must overlap by at least <strong>{b['minimum_overlapping_dots']:,}/{b['candidate_dot_budget']:,} ({100*b['minimum_fraction_within_radius']:.4f}%)</strong>, above the strict 70% rule. We measured <strong>{old['matching_dots']:,}/{b['candidate_dot_budget']:,} ({100*old['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong> on the historical CSR-1 file.</p>
<p>The older 357-reference screen omitted this lattice. CSR-1 also fails the published-format validator because it has zeros outside the footprint. Its whole-array finite/range diagnostic passed; that is <em>not</em> proof of organizer acceptance or a remedy for the reported portal error.</p>
<p>Two files merged during this audit are also stopped: <strong>CTD-1 {ctd['matching_dots']:,}/{ctd['comparison']['candidate_dots']:,} ({100*ctd['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong> and <strong>FC-1 {fc['matching_dots']:,}/{fc['comparison']['candidate_dots']:,} ({100*fc['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong>. Their format checks pass, but their archived holdout used full-catalogue predictions before hiding faults and is not leakage-safe. <a href="{REPORT}/review.md#parallel-work-merged-during-this-audit">Details</a>.</p>
<div class="actions"><a class="button" href="{REPORT}/run-card.json">Open current run card</a><a class="button secondary" href="docs/research/2026-10-27-followup-review.md">Follow-up: nine sites &amp; hypotheses</a><a class="button secondary" href="{REPORT}/review.md">Read proof &amp; reproduction</a><a class="button secondary" href="{e(old['path'])}" download>Historical CSR-1 · research only</a></div>
<p class="fine">Historical download only, not a new or approved candidate. SHA-256 <code>{e(old['raster_sha256'])}</code>. No submission identity or note was generated.</p></section>'''


def current_decision() -> str:
    return '''<section class="section" id="current-decision"><div class="section-heading"><h2>Current submission answer · 27 Oct follow-up</h2><p>Review-only; no lane or candidate was authorized.</p></div><div class="table-wrap"><table><caption>Current file / estimate / uniqueness / slot decision</caption><thead><tr><th scope="col">File to download for submission</th><th scope="col">Defensible public-score estimate</th><th scope="col">Uniqueness</th><th scope="col">Holdout / slot</th></tr></thead><tbody><tr><td><strong>None.</strong><br><small>Historical links are research references only.</small></td><td><strong>Not estimable.</strong><br><small>No new candidate or organizer receipt.</small></td><td><strong>Not cleared.</strong><br><small>No new raster; the 44,090-dot bound is 84.9195% within 3 px of the lattice.</small></td><td><strong>No new holdout; no slot selected.</strong><br><small>Do not upload historical bytes.</small></td></tr></tbody></table></div><p class="fine">See the <a href="docs/research/2026-10-27-followup-review.md">full follow-up review</a> and <a href="docs/research/2026-10-27-followup-run-card.json">negative run card</a>. No local validator applies because no candidate was written.</p></section>'''


def pool1_summary() -> str:
    return '''<section class="section" id="pool1"><div class="section-heading"><h2>Archived POOL-1: best holdout method, duplicate-stopped raster.</h2><p>Historical evidence only; no submission file was published.</p></div><p><strong>HOLDOUT-DTI</strong> E1 0.186699 [0.173113, 0.200171] and E2 0.187694 [0.173631, 0.201989]; evaluator <code>component-holdout-v3-blockstats-20261025</code>, 60,988 withheld positives. The paired HOLDOUT-DTI differences vs same-protocol <code>msdb_edge</code> were +0.017231 [+0.010515, +0.023980] and +0.013446 [+0.006993, +0.019757]. The final raster was duplicate-stopped at 88.74% / 75.81% / 71.08% within 3 px of FFL1 / MSDB1-edge / CSR-1 (70% threshold), so no TIFF was published and no slot was selected. This is catalogue-recovery evidence, not an organizer score or public-score estimate. <a href="pool1-executive-summary.html">POOL-1 executive page</a> · <a href="docs/research/2026-10-27-pool/run-card.json">frozen run card</a> · <a href="docs/research/2026-10-27-followup-review.md">current follow-up</a>.</p></section>'''


def evidence_strip(card: dict) -> str:
    h = card["historical_holdout_reference"]
    c, base, diff = h["candidate"], h["matched_control"], h["paired_difference"]
    return f'''<div class="evidence-strip" aria-label="Historical holdout evidence"><article><span>Historical CSR-1 · HOLDOUT-DTI</span><strong>{c['value']:.6f}</strong><small>95% CI [{c['ci95'][0]:.6f}, {c['ci95'][1]:.6f}]</small></article>
<article><span>Same-run msdb_edge · HOLDOUT-DTI</span><strong>{base['value']:.6f}</strong><small>95% CI [{base['ci95'][0]:.6f}, {base['ci95'][1]:.6f}]</small></article>
<article><span>HOLDOUT-DTI paired difference</span><strong>{diff['value']:+.6f}</strong><small>95% CI [{diff['ci95'][0]:+.6f}, {diff['ci95'][1]:+.6f}]</small></article></div>
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
<td><a href="{e(row['source_url'])}">{e(row['historical_file'])}</a><br><small>Historical source only · local format {fmt}{alias}</small></td>
<td><strong>{e(row['quoted_owner_claim'])}</strong><br><small>unverified owner claim; no receipt</small></td>
<td><strong>STOP</strong><br><small>≥{100*lower:.2f}% lattice bound</small></td><td><strong>DO NOT RESUBMIT</strong><br><small>no new candidate or slot approved here</small></td></tr>''')
    return '''<div class="table-wrap"><table><caption>Frozen nine-site historical selections · 26 Oct 2026, not live leadership or a complete registry</caption><thead><tr><th scope="col">Site</th><th scope="col">Historical file (research only; do not upload)</th><th scope="col">Historical owner-reported value (unverified)</th><th scope="col">Uniqueness under literal rule</th><th scope="col">Current submit status</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div>
<p class="fine">Values are unverified owner reports, not HOLDOUT-DTI or ORGANIZER-CONFIRMED scores. No defensible leaderboard forecast. Each bound is mathematical, not an individually measured overlap; the earlier fleet audit verified each file's aligned footprint and dot count. Historical bytes are not new submissions. Remote pages may have changed; no fleet-wide selector has approved a slot.</p>'''


def h33(fleet: dict) -> str:
    lin = fleet['lineage']
    return f'''<section class="section" id="h33"><p class="eyebrow">What the bytes establish</p><h2>H33-B2 is a lineage, not a proven causal gain.</h2>
<p>The historical audit found value-identical G25/G30 rasters and a 40,199-dot G28 r1 intermediate identical to the selected G31 raster. H33-B2 is that intermediate with {lin['r1_to_h33_removed']:,} dots near mapped faults removed ({lin['h33_dots']:,} remain); the G36 reference contains H33-B2 plus {lin['pinn_additional_dots']:,} dots. The 37,660-dot G28 historical selection is a different file.</p>
<p>The owner reports <strong>0.2778</strong> for H33-B2, but no organizer receipt or hidden truth is available. We cannot infer hidden true/false positives, prove that pruning caused an improvement, or forecast a future score. The prior CSR review's numerical causal inversion and TP formula are not reliable.</p>
<a class="text-link" href="{CSR}/fleet-audit.json">Inspect frozen lineage evidence ↗</a></section>'''


def research_section() -> str:
    return '''<section class="section" id="hypotheses"><div class="section-heading"><div><p class="eyebrow">Prospective work / no lane assigned</p><h2>Four ranked, previously proposed-but-unrun mechanisms.</h2></div><p>Qualitative experiment priority only.<br>No numeric score estimate or run authorization.</p></div>
<div class="resource-grid"><article><h3>1. CSR-2 regime-gated experts</h3><p>Combine a piedmont scarp expert with a cover-blind magnetic/gravity/MT expert under one frozen regional gate. This differs from CSR-1’s single global model; mimics include eroded fan scarps, lava fronts, lithologic boundaries and survey seams. Low–medium modeling cost after restoration; the pinned inputs are not present in this checkout.</p></article>
<article><h3>2. GeoDAWN alteration-ratio persistence</h3><p>Test K/Th/U log-ratio residuals with cross-line persistence and a within-survey-block null. Mimics include soil/lithology, moisture and flight-line seams. The official source is recorded as CC0 in an earlier receipt, but the pinned TIFFs are missing now and metadata were not rechecked; not ready.</p></article>
<article><h3>3. Drainage deflection across a field edge</h3><p>Measure repeated channel offsets and knickpoint alignments from official 3DEP/NHD, then require independent magnetic/gravity support. This differs from LiDAR scarp amplitude. Mimics include terraces, roads, lava dams and lithology. A prior query covered one test bbox only; full ROI bytes/coverage are unverified, so not viable yet.</p></article>
<article><h3>4. GeMS/SGMC unit-contact discordance</h3><p>Project geology-unit contacts beneath alluvium and compare with independent geophysical edges, excluding fault lines. Mimics include unconformities and unfaulted stratigraphic terminations. The updated official GeMS product and unit polygons are not locally verified; acquisition and GIS cost is medium–high, so not viable yet.</p></article></div>
<p><a class="text-link" href="docs/research/2026-10-27-followup-review.md#ranked-untried-hypotheses">Full mechanisms, evidence, source availability, and costs ↗</a></p></section>'''


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


def render(card: dict, fleet: dict) -> dict[str, str]:
    common = hero() + stop_card(card)
    overview = common + pool1_summary() + evidence_strip(card) + '''<section class="section"><div class="section-heading"><div><p class="eyebrow">Historical evidence / nine priority sites</p><h2>A fleet snapshot, not a leaderboard.</h2></div><p>Historic sources are linked.<br>No upload is authorized.</p></div>''' + table(fleet, card) + '</section>' + h33(fleet) + research_section() + links_and_protocol()
    summary = common + pool1_summary() + evidence_strip(card) + '''<section class="section"><p class="eyebrow">Submission guide</p><h2>There is no file to submit.</h2><p>Do not upload the historical CSR-1 file, rename an old prediction, or use a weekly slot. Its published-format failure and duplicate stop are independently sufficient blockers. A future submission requires the protocol and separate selector approval below.</p><p><strong>Public-score estimate: none.</strong> No defensible mapping from these catalogue-recovery holdouts to the organizer leaderboard is available.</p></section>''' + links_and_protocol()
    research = common + pool1_summary() + evidence_strip(card) + research_section() + h33(fleet) + links_and_protocol()
    priority = '''<section class="intro"><div><p class="eyebrow">Priority sites / frozen 26 Oct 2026</p><h1>Nine sites. One clear stop.</h1><p class="lead">Owner-reported historical scores, immutable source files and the literal lattice bound; not a live registry or submit selector.</p></div></section>''' + current_decision() + table(fleet, card) + h33(fleet) + research_section() + links_and_protocol()
    pages = {'index.html': layout('Research overview', overview),
             'executive-summary.html': layout('Submission guide', summary),
             'csr-discontinuity-review.html': layout('Research review', research),
             'priority-executive-summary.html': layout('Nine-site evidence', priority)}
    for row in fleet['rows']:
        pages[row['review_url']] = priority_page(row, card)
    return pages
