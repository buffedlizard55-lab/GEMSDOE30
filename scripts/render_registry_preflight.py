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
<nav aria-label="Primary"><a href="index.html">Overview</a><a href="priority-executive-summary.html">Nine sites</a><a href="csr-discontinuity-review.html">Research</a><a href="executive-summary.html">Submission guide</a><a href="pool1-executive-summary.html">POOL-1</a></nav>
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
<p>The pinned 13GEMSDOE lattice covers all but <strong>{b['uncovered_pixels']:,}</strong> valid cells within 3 pixels. Any {b['candidate_dot_budget']:,}-dot candidate must overlap by at least <strong>{b['minimum_overlapping_dots']:,}/{b['candidate_dot_budget']:,} ({100*b['minimum_fraction_within_radius']:.4f}%)</strong>, above the strict 70% rule. We measured <strong>{old['matching_dots']:,}/{b['candidate_dot_budget']:,} ({100*old['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong> on the historical CSR-1 file.</p>
<p>The older 357-reference screen omitted this lattice. CSR-1 also fails the published-format validator because it has zeros outside the footprint. Its whole-array finite/range diagnostic passed; that is <em>not</em> proof of organizer acceptance or a remedy for the reported portal error.</p>
<p>Four parallel rasters merged on 26–27 Oct 2026 are also duplicate-stopped against the same witness: <strong>CTD-1 {ctd['matching_dots']:,}/{ctd['comparison']['candidate_dots']:,} ({100*ctd['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong>, <strong>FC-1 {fc['matching_dots']:,}/{fc['comparison']['candidate_dots']:,} ({100*fc['comparison']['candidate_fraction_within_3px_of_reference']:.4f}%)</strong>, <strong>GC-1 39,960/40,000 (99.9000%)</strong>, and <strong>VS-1 37,654/37,654 (100.0000%)</strong> (which also places 13,098/37,654 dots directly on known catalogue pixels). Their format checks pass, but CTD-1/FC-1/GC-1 archived holdouts scored saved full-grid rasters without rebuilding per fold, and VS-1 ran no holdout. <a href="{REPORT}/review.md#parallel-work-merged-during-this-audit">Details</a> · <a href="{REPORT}/postmerge-addendum.json">Post-merge addendum</a>.</p>
<div class="actions"><a class="button" href="{REPORT}/run-card.json">Open current run card</a><a class="button secondary" href="{REPORT}/review.md">Read proof &amp; reproduction</a><a class="button secondary" href="{e(old['path'])}" download>Historical CSR-1 · research only</a></div>
<p class="fine">Historical download only, not a new or approved candidate. SHA-256 <code>{e(old['raster_sha256'])}</code>. No submission identity or note was generated.</p></section>'''


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
<td><strong>STOP</strong><br><small>≥{100*lower:.2f}% lattice bound</small></td><td><strong>DO NOT RESUBMIT</strong><br><small>no new candidate or slot approved here</small></td></tr>''')
    return '''<div class="table-wrap"><table><caption>Frozen nine-site historical selections · 26 Oct 2026, not live leadership or a complete registry</caption><thead><tr><th scope="col">Site</th><th scope="col">Owner-identified best / pinned source</th><th scope="col">Reported value</th><th scope="col">Uniqueness under literal rule</th><th scope="col">Submit status</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></div>
<p class="fine">Values are unverified owner reports, not HOLDOUT-DTI or ORGANIZER-CONFIRMED scores. No defensible leaderboard forecast. Each bound is mathematical, not an individually measured overlap; the earlier fleet audit verified each file's aligned footprint and dot count. Historical bytes are not new submissions. Remote pages may have changed; no fleet-wide selector has approved a slot.</p>'''


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
<p><a class="text-link" href="{REPORT}/review.md#ranked-geological-hypotheses--proposals-not-runs">Full mechanisms, physical rationale, costs, and official sources ↗</a></p></section>'''


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


def pool1_section() -> str:
    return '''<section class="section" id="pool1"><div class="section-heading"><div><p class="eyebrow">Parallel lane POOL-1 · 27 Oct 2026</p><h2>Best holdout mechanism, duplicate-stopped raster.</h2></div><p>Same evaluator, two-seed confirmation — and no TIFF published.</p></div>
<p><strong>POOL-1</strong> (pooled 75-feature MSDB-18 + CSR-27 + LiDAR-17 HGB, preregistered 2026-10-27) scored <code>HOLDOUT-DTI</code> <strong>0.186699</strong> [0.172547, 0.200797] (seed 4201) and <strong>0.187694</strong> [0.173154, 0.201655] (seed 4219) vs same-protocol <code>msdb_edge</code> (paired Δ <strong>+0.017231</strong> [+0.010515, +0.023980] and <strong>+0.013446</strong> [+0.006993, +0.019757]; evaluator <code>component-holdout-v3-blockstats-20261025</code>, 60,988 withheld positives; max single-feature symmetric AUC 0.6805 ≤ 0.90) — the first lane in this repository to beat the standing best with paired CIs excluding zero on both preregistered seeds. Its 44,090 production dots then breached the 70% duplicate-stop on its frozen 394-raster registry (<strong>88.74%</strong> within 3 px of FFL1; 75.81% of MSDB1-edge; 71.08% of CSR-1; and <strong>100.0000%</strong> vs the pinned 13GEMSDOE lattice), so <strong>no TIFF was published</strong> and no slot is approved. <a href="pool1-executive-summary.html">POOL-1 executive summary</a> · <a href="docs/research/2026-10-27-pool/run-card.json">POOL-1 run card</a> · <a href="docs/research/2026-10-27-pool/postmerge-addendum.json">post-merge addendum</a>.</p></section>'''


def submission_howto_section() -> str:
    return '''<section class="section" id="submission-guide"><p class="eyebrow">Submission guide &amp; range-error diagnosis</p><h2>There is no file to submit right now.</h2>
<p>Do not upload the historical CSR-1 file, rename an old prediction (`CTD-1`, `FC-1`, `GC-1`, `VS-1`), or spend a weekly slot. CSR-1's published-format failure (zeros outside the template footprint instead of <code>NaN</code>) and its 99.9864% lattice overlap are independently sufficient blockers. A future submission requires passing all scientific, novelty, and format gates plus separate slot-selector approval below.</p>
<div class="resource-grid">
<article><h3>Why the portal returned <code>"Predicted values must be in range [0, 1]"</code></h3><p>The official problem description specifies single-band <code>float32</code> GeoTIFF probabilities in <code>[0, 1]</code> inside the data bounds and <code>null</code>/<code>NaN</code> outside (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem page</a>). A portal range error can occur if (1) sentinel nodata values such as <code>-9999.0</code> or unclipped float predictions outside <code>[0, 1]</code> remain in the band, (2) a candidate defines its footprint from a feature channel rather than <code>sample_submission.tif</code> (leaving <code>NaN</code> inside the organizer's 5,167,373 valid cells), or (3) the portal checks values before applying the template mask. The exact historical upload that triggered the error is not archived here, so its specific cause remains undiagnosed (<a href="docs/research/range-error-root-cause-2026-10-03.md">root-cause note</a>).</p></article>
<article><h3>Automated local format gate (zero human inspection)</h3><p>Every candidate is checked automatically by <code>src/gemsdoe30/submission.py</code> (<code>python scripts/validate_submission.py &lt;file.tif&gt; --template data/raw/sample_submission.tif</code>): single-band <code>float32</code>, <code>EPSG:32611</code>, shape <code>3730×3292</code>, 100 m north-up geotransform, finite values in <code>[0, 1]</code> on all 5,167,373 valid footprint cells, and <code>NaN</code> on all 7,111,787 outside cells. Local format validation is a necessary precondition, never an organizer score or upload approval.</p></article>
<article><h3>How to submit when a future run is promoted</h3><p>Only when <code>verdict == "promote"</code> and <code>ok_to_submit == true</code> in the current run card: (1) download the promoted <code>.tif</code> (or single-GeoTIFF <code>.zip</code>), (2) verify its SHA-256 against the sidecar receipt, (3) open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS submission form</a>, choose the file under <em>File to submit</em>, paste the ≤140-character <em>Note</em> from the run card (e.g., lane ID, dot count, and seed), and record the returned organizer score with a submission-page receipt. Up to 3 feedback submissions are allowed per week; 1 final submission is selected for both evaluation rounds.</p></article>
<article><h3>2026-10-27 external fleet check (21 named-prefix sites)</h3><p>In addition to the 92 numbered repositories (<code>GEMSDOE</code>..<code>GEMSDOE92</code>, all 92 reachable via GitHub API in <a href="docs/research/2026-10-27-pool/registry.json">POOL-1's registry</a>), the 21 named-prefix sites in the 2026-10-27 prompt (<code>KANLERGEMSDOE1..3</code>, <code>EUGGEMSDOE1..3</code>, <code>WBGGEMSDOE1..3</code>, <code>GINNYGEMSDOE1..3</code>, <code>GEMSDOEkarage1..3</code>, <code>ApartGEMSDOE1..3</code>, <code>GEMSDOESASS1..3</code>) were queried against <code>api.github.com/repos/buffedlizard55-lab/&lt;repo&gt;</code> on 2026-10-27 and all 21 returned <code>HTTP 404 Not Found</code> (not publicly created or inaccessible to the sandbox token). Their prompt annotations (15 <code>no tif</code>, 1 <code>duplicate stop</code>, 5 <code>Unique ready?</code>) remain unverified owner text logged in <a href="docs/score-ledger.csv"><code>docs/score-ledger.csv</code></a>.</p></article>
</div></section>'''


def render(card: dict, fleet: dict) -> dict[str, str]:
    common = hero() + stop_card(card) + pool1_section() + evidence_strip(card)
    overview = common + '''<section class="section"><div class="section-heading"><div><p class="eyebrow">Historical evidence / nine priority sites</p><h2>A fleet snapshot, not a leaderboard.</h2></div><p>Historic sources are linked.<br>No upload is authorized.</p></div>''' + table(fleet, card) + '</section>' + h33(fleet) + research_section() + links_and_protocol()
    summary = common + submission_howto_section() + '''<section class="section"><div class="section-heading"><div><p class="eyebrow">Nine priority sites / master reference table</p><h2>Historical files, score classes, and submit status.</h2></div><p>Every priority site is duplicate-stopped under the literal lattice rule.</p></div>''' + table(fleet, card) + '</section>' + h33(fleet) + research_section() + links_and_protocol()
    research = common + research_section() + h33(fleet) + links_and_protocol()
    priority = '''<section class="intro"><div><p class="eyebrow">Priority sites / frozen 26 Oct 2026</p><h1>Nine sites. One clear stop.</h1><p class="lead">Owner-reported historical scores, immutable source files and the literal lattice bound; not a live registry or submit selector.</p></div></section>''' + pool1_section() + table(fleet, card) + h33(fleet) + links_and_protocol()
    pages = {'index.html': layout('Research overview', overview),
             'executive-summary.html': layout('Submission guide', summary),
             'csr-discontinuity-review.html': layout('Research review', research),
             'priority-executive-summary.html': layout('Nine-site evidence', priority)}
    for row in fleet['rows']:
        pages[row['review_url']] = priority_page(row, card)
    return pages
