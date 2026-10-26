"""Render the latest QPC-1 negative decision from machine-verified receipts."""
from __future__ import annotations

from html import escape as e
import json
from pathlib import Path

from scripts.render_gdx_review import (
    archive_note, frame as base_frame, lineage, metric, priority_relationship, priority_table,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'docs/research/2026-10-26-qpc'
BASE = 'docs/research/2026-10-26-qpc/'
GDX = ROOT / 'docs/research/2026-10-26-gdx'


def load(path):
    return json.loads(Path(path).read_text())


def frame(title, body, active='Overview'):
    html = base_frame(title, body, 'GDX-1 science' if active == 'QPC-1 science' else active)
    return html.replace('GDX-1 science', 'QPC-1 science').replace(
        'geothermal-chemistry-review.html', 'geothermal-quadrature-review.html', 1
    ).replace('docs/research/2026-10-26-gdx/run-card.json', BASE + 'run-card.json')


def release(card, fallback):
    published = card.get('published_tiff')
    if published:
        file = ROOT / published
        primary = f'''<a class="button" href="{e(published)}" download>Download QPC-1 research TIFF <span>{file.stat().st_size/1024:.0f} KiB · do not upload</span></a>'''
        intro = 'The new TIFF is a research artifact, not a competition recommendation.'
        details = f'''<p class="filename">{e(file.name)}</p><details><summary>Byte identity and local guarantees</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Local format</dt><dd>1 float32 band; EPSG:32611; exact mirrored-template grid; finite [0,1] inside; NaN outside; 44,090 dots; visible catalogue pixels masked.</dd><dt>Scope</dt><dd>Local checks do not establish portal acceptance, global uniqueness or an organizer score.</dd></dl></details>'''
    else:
        primary = f'''<a class="button secondary" href="{e(fallback['published_tiff'])}" download>Download earlier GDX-1 research TIFF <span>previous lane · do not upload</span></a>'''
        intro = 'QPC-1 stopped without publishing a replacement TIFF. The download is the earlier negative GDX-1 artifact, not a new QPC result.'
        details = f'''<p class="filename">{e(Path(fallback['published_tiff']).name)}</p><p class="fine">Earlier GDX-1 SHA-256 <code>{e(fallback['raster_sha256'])}</code>. It must not be resubmitted as a new hypothesis.</p>'''
    return f'''<section class="release" aria-labelledby="release-title"><div class="release-heading"><span class="pill failed">NOT APPROVED FOR SUBMISSION</span><span class="pill caution">QPC-1 · negative research decision</span></div><h2 id="release-title">Protect the slot. <span>{e(intro)}</span></h2><p><strong>Do not spend a weekly slot.</strong> Global/private novelty, an externally assigned method lane and organizer authentication remain unresolved. No automated upload or slot selection has occurred.</p><div class="actions">{primary}<a class="button secondary" href="{BASE}run-card.json">Read JSON run card</a></div>{details}</section>'''


def holdout(card, results):
    if not results:
        return '''<section class="section" id="holdout"><h2>No trusted QPC-1 HOLDOUT-DTI.</h2><p>The lane stopped before producing a complete paired result; no QPC score or leaderboard projection is available. The strongest previously recorded comparable FFL-1 confirmation was HOLDOUT-DTI <strong>0.183949 [0.169419, 0.197874]</strong>, evaluator <code>component-holdout-v3-blockstats-20261025</code>, 60,988 withheld positives. FFL-1 was duplicate-stopped and is not a submission.</p></section>'''
    summary = results['summary']
    names = [('qpc23', 'QPC-1 candidate'), ('persistence21', 'Within-field persistence'),
             ('msdb_edge', 'MSDB edge control'), ('ffl_confirm', 'FFL confirmation replay'), ('core19', 'Core19 control')]
    rows = ''.join(f'<tr><th scope="row">{e(label)}</th><td>{metric(summary["arms"][key])}</td><td>{summary["arms"][key]["withheld_positives"]:,}</td></tr>' for key, label in names)
    deltas = ''.join(f'<li>QPC − {e(key)}: <strong>{metric(summary["candidate_minus"][key])}</strong></li>'
                     for key in ('persistence21', 'msdb_edge', 'ffl_confirm'))
    gate = 'passed' if results['scientific_gate_passed'] else 'failed'
    return f'''<section class="section" id="holdout"><div class="section-heading"><h2>Paired holdout, not a leaderboard score.</h2><p>Preregistered three-comparator gate: <strong>{gate}</strong>.</p></div><div class="table-wrap"><table><caption>HOLDOUT-DTI · paired geographic-block 95% confidence intervals</caption><thead><tr><th>System</th><th>DTI [95% CI]</th><th>Withheld positives</th></tr></thead><tbody>{rows}</tbody></table></div><ul class="spaced">{deltas}</ul><p class="fine">Evaluator <code>{e(summary['evaluator_version'])}</code>; protocol <code>{e(summary['protocol_version'])}</code>; whole fault segments, 17 px guard, visible faults pixel-masked, α = 0.2, β = 0.8, 300 m triangular kernel. {summary['bootstrap']['replicates']:,} paired block bootstrap draws. The fixed FFL confirmation was replayed and matched each fold; MSDB masks and blocks were verified before pooling. Mapped-catalogue recovery is a conditional proxy, not a hidden competition score.</p><p class="fine">Post-stop, <a href="{BASE}parallel-inventory.json">unmerged PR #41</a> was found to report HOLDOUT-DTI 0.186687 [0.173326, 0.200317], 60,988 positives, evaluator <code>component-holdout-v3-blockstats-20261025</code>. Its 20 px guard and training sets differ from QPC’s 17 px; it was not independently reproduced or paired, and its TIFFs were not in the frozen registry. No approval is implied.</p></section>'''


def novelty_section(card):
    items = []
    for stage in ('surface', 'dots'):
        path = REPORT / f'novelty-{stage}.json'
        if not path.is_file():
            items.append(f'<tr><th scope="row">{stage.title()}</th><td>Not reached</td><td>Unknown</td><td>Unknown</td></tr>')
            continue
        r = load(path)
        rows = r['comparisons']
        rho = max((x['spearman_full_footprint'] for x in rows if x.get('spearman_full_footprint') is not None), default=None)
        overlap = max((x['candidate_fraction_within_3px_of_reference'] for x in rows if x.get('candidate_fraction_within_3px_of_reference') is not None), default=None)
        items.append(f'<tr><th scope="row"><a href="{BASE}novelty-{stage}.json">{stage.title()} receipt</a></th><td>{len(rows)} compared; {len(r["errors"])} error(s)</td><td>{rho:.6f}</td><td>{"—" if overlap is None else f"{100*overlap:.4f}%"}</td></tr>')
    reason = f'<p><strong>Stop:</strong> {e(card["reason"])}</p>' if card.get('reason') else ''
    dots_file = REPORT / 'novelty-dots.json'
    if dots_file.is_file():
        audit = load(dots_file)
        top = max(audit['comparisons'], key=lambda x: x.get('candidate_fraction_within_3px_of_reference') or 0)
        ref = next(r for r in load(REPORT / 'registry.json')['rasters'] if r['sha256'] == top['reference_sha256'])
        count = sum(r['dot_duplicate'] or r['correlation_duplicate'] or r['identical_inside_footprint'] for r in audit['comparisons'])
        reason += f'<p>The maximum overlap is with <code>{e(Path(ref["source_path"]).name)}</code>; {count} registry entries triggered duplicate-stop. The QPC TIFF was withheld and not format-validated after the stop.</p>'
    return f'''<section class="section" id="novelty"><h2>Observed comparisons are not global uniqueness.</h2>{reason}<div class="table-wrap"><table><caption>Continuous surface audited before final dots; final dots audited separately if reached</caption><thead><tr><th>Stage</th><th>Frozen public references</th><th>Maximum Spearman ρ</th><th>Maximum candidate dots within 3 px</th></tr></thead><tbody>{''.join(items)}</tbody></table></div><p>One pinned GEMSDOE31 reference has 2,610,312 non-finite cells inside the footprint and cannot be compared without invalid imputation. A <a href="{BASE}parallel-heads-inventory.json">post-stop inventory</a> listed 25 public open-PR heads across the nine repositories, but their trees were not systematically scanned or compared. Private work, original surfaces and predictions outside enumerated public paths are also unknown. A surface correlation &gt;0.90 or directional dot overlap &gt;70% is a mandatory duplicate stop. No complete uniqueness claim follows from a partial snapshot.</p><p class="fine">The registry contains 370 tracked TIFF source paths and 354 deduplicated aligned references from nine pinned public snapshots. Each observation is a frozen dated record, not a live inventory. <a href="{BASE}registry.json">Frozen registry</a> · <a href="{BASE}preregistration.md">Preregistered protocol</a></p></section>'''


def instructions(card, fallback):
    identity = card if card.get('published_tiff') else fallback
    label = 'QPC-1 research artifact' if card.get('published_tiff') else 'previous GDX-1 research artifact (not QPC-1)'
    return f'''<section class="section" id="identity"><h2>Exact {e(label)} identity.</h2><p>These fields identify the research bytes only; they do not authorize an upload. The note is {len(identity['note'])}/140 characters.</p><div class="identity"><label for="submission-name">Run / file stem</label><input id="submission-name" readonly value="{e(identity['submission_name'], quote=True)}"><button class="copy-button" data-copy="submission-name">Copy name</button><label for="submission-note">Research note</label><textarea id="submission-note" rows="3" readonly>{e(identity['note'])}</textarea><button class="copy-button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></section><section class="section" id="instructions"><h2>What to do now.</h2><ol class="steps"><li><strong>Download only for research.</strong><p>Never rename, re-encode or perturb an earlier raster as a supposedly novel hypothesis.</p></li><li><strong>Recheck automatically.</strong><p><code>python scripts/verify_quadrature_phase_run.py</code> verifies the QPC evidence; <code>--require-promote</code> exits 2 for a valid negative decision. No human-inspector gate.</p></li><li><strong>Do not upload or select a slot.</strong><p>For any future candidate, first establish an assigned lane, complete two-stage registry coverage, matched strongest-control improvement, provenance and an independent confirmation. Only a separate selector may consider a competition slot.</p></li><li><strong>Check applicable current rules and eligibility.</strong><p>No portal acceptance, receipt, weekly-cap state or deadline is verified here. Historical references to “5:00 p.m. ET” and a 0.4413 leader are not current commitments or an organizer-confirmed score for this file.</p></li></ol><p class="fine">“Predicted values must be in range [0, 1]”: finite [0,1] values and the footprint mask are checked locally. The exact rejected upload and portal receipt are missing; its cause and acceptance of any replacement remain unproven.</p></section>'''


def science(card, results):
    canary_note = 'No complete individual-feature canary set was recorded.'
    if results:
        entries = [r for key in ('feature_canaries', 'ffl_feature_canaries') for fold in results[key] for r in fold['features']]
        maximum = max(max(r['raw_auc'], 1-r['raw_auc'], r['univariate_training_only_hgb_auc'],
                          1-r['univariate_training_only_hgb_auc']) for r in entries)
        canary_note = f'{len(entries)} individual checks completed; maximum bidirectional AUC {maximum:.6f} (alarm threshold &gt;0.90).'
    return f'''<section class="section"><h2>Physics with competing explanations.</h2><p>QPC-1 uses reduced-to-pole magnetic and isostatic-gravity bands at 1- and 3-pixel scales, forming normalized high-pass/gradient vector concordance and within-field persistence. The proxies may identify co-located concealed boundaries but are not calibrated monogenic phase, a direct dip estimate, or proof of a geothermal vent.</p><p>Non-fault alternatives include volcanic or intrusive contacts, dike swarms and survey-leveling seams. All 19 base channels and four new channels are tested individually in each holdout fold; the fixed FFL replay requires 54 additional individual-feature canaries per fold. {canary_note} AUC over 0.90 in either direction stops evaluation.</p><p><a href="{BASE}preregistration.md">Four ranked pre-execution hypotheses, exact layers, costs and protocol</a> · <a href="{BASE}source-audit.md">Official sources, license and knowledge audit</a> · <a href="https://pubs.usgs.gov/publication/70032258">USGS on non-unique gravity/magnetic interpretations ↗</a></p></section>'''


def fleet_markdown(fleet, card):
    rows = ['# Nine-site executive summary — 26 October 2026', '',
            '**Read-only pinned public snapshots; no separate site was modified.** All claims below are unverified owner reports, not organizer-confirmed scores. Estimated leaderboard score: unknown for every file.', '',
            '| Site | Owner claim (unverified) | Exact historical filename | Dots | Relation to selected files | Estimated score / submit? |',
            '|---|---:|---|---:|---|---|']
    for r in fleet['rows']:
        relation = priority_relationship(r, fleet['pairwise_diagnostics'])
        rows.append(f"| [{r['site']}](../../../priority-{r['site']}.html) | {r['quoted_owner_claim']} | [`{r['historical_file']}`]({r['source_url']}?raw=true) | {r['dots']:,} | {relation} | Unknown; **do not submit** |")
    rows += ['', '“Near” means within 3 pixels in the stated candidate direction. All nine selected files have a directional relationship above the 70% duplicate-stop threshold. These comparisons do not cover all private surfaces.', '',
             '## GEMSDOE32 H33 finding', '',
             'The 44,090-dot d28 base was reduced to 40,199 dots, then to the 37,654-dot H33 after a >2 px mapped-fault-distance prune. GEMSDOE36 adds 1,200 dots. Reducing low-yield false positives is a plausible explanation for the owner-reported 0.2778, not proof of causation; hidden TP/FP, organizer receipts and a defensible numeric improvement forecast are unavailable.', '',
             f"## Current QPC-1 decision", '',
             f"**Negative / DO NOT SUBMIT.** {'Research TIFF: `'+card['published_tiff']+'`.' if card.get('published_tiff') else 'No QPC-1 TIFF was published.'} Global uniqueness unknown; no slot selected. [Run card](run-card.json) · [full protocol](preregistration.md) · [site guide](../../../executive-summary.html).", '']
    return '\n'.join(rows)


def pages(ready):
    card, fallback = load(REPORT / 'run-card.json'), load(GDX / 'run-card.json')
    results_path = REPORT / 'results.json'
    results = load(results_path) if results_path.is_file() else None
    fleet = load(GDX / 'fleet-audit.json')
    if ready.get('research_verdict') != 'negative' or ready.get('submission_approved') is not False:
        raise ValueError('QPC renderer expects independently verified negative readiness')
    intro = '''<section class="intro"><div><p class="eyebrow">DOE GEMS / 26 October 2026 / evidence first</p><h1>New hypothesis.<br>No submission approval.</h1><p class="lead">QPC-1 tests magnetic–gravity phase proxies against the strongest matched main-branch control found before execution. The decision is negative: research evidence is useful, but a scarce competition slot is not justified.</p><div class="meta"><span>Slot selected: none</span><span>Global uniqueness: unknown</span><span>Organizer score: none</span></div></div></section>'''
    earlier = archive_note() + '''<p class="fine">GDX-1 is an earlier negative research artifact. The G30-TAD 51.44% overlap referred only to an archived subset; neither is a fallback competition submission.</p>'''
    home = frame('Current research decision', intro + release(card, fallback) + holdout(card, results) + novelty_section(card) + '''<section class="section"><h2>Nine repositories. One evidence standard.</h2><p>Selected historical filenames, user-reported numbers, pairwise relationships and unknown estimates are shown together. The other repositories were read, not modified.</p><a class="button secondary" href="priority-executive-summary.html">Review all nine priority sites</a></section>''' + science(card, results) + earlier)
    guide = frame('Research download and submission decision', intro + release(card, fallback) + instructions(card, fallback) + holdout(card, results) + novelty_section(card) + earlier, 'Submission guide')
    scientific = frame('QPC-1 science and audit', intro + release(card, fallback) + science(card, results) + holdout(card, results) + novelty_section(card) + earlier, 'QPC-1 science')
    priority_intro = '''<section class="intro"><div><p class="eyebrow">Nine pinned public repositories / read-only</p><h1>Nine files.<br>Related, not a live ranking.</h1><p class="lead">Numbers are unverified owner claims, not organizer-confirmed scores. No historical file is a fresh submission; score estimates and global uniqueness are unknown.</p></div></section>'''
    priority = frame('Nine-site executive summary', priority_intro + '<section class="section">' + priority_table(fleet) + '</section>' + lineage() + '<section class="section"><p>See the <a href="executive-summary.html">current QPC-1 decision</a>. No slot has been selected.</p></section>', 'Nine-site review')
    return {'index.html': home, 'executive-summary.html': guide, 'geothermal-quadrature-review.html': scientific,
            'priority-executive-summary.html': priority, BASE + 'nine-site-executive-summary.md': fleet_markdown(fleet, card)}
