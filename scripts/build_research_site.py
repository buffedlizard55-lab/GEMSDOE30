#!/usr/bin/env python3
"""Build deterministic Pages entry points from verified research receipts.

The site renders the artifact selected by ``docs/current-run.json`` (its own
verifier adjudicates it) and lists the registered peer artifacts and stopped
attempts without re-adjudicating or slot-selecting them. No page states an
organizer score unless an organizer receipt exists.

Two card schemas are supported:
  * ``schema_version: 3`` holdout-promoted placement cards (H-NEARSPLAY),
  * TDX/MSDB experiment cards with ``published_tiff`` + ``results.json``.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.verify_current_run import verify, local_path

STYLE = "docs/assets/research.css"

LATEST_REVIEW = '<section class="release" aria-label="Latest executive review"><h2>26 October: NOT cleared to submit</h2><p>Both existing primary downloads pass current local format and SHA checks. No new TIFF or experiment was generated: assigned lane, complete parallel registry and comparable-best validation remain unresolved. MSDB has a recorded negative overall readiness verdict.</p><p><a href="review-2026-10-26.html">Nine-site executive summary and next steps</a> · <a href="docs/research/review-2026-10-26/readiness.json">Current machine inspection</a></p></section>'


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

    def chunk(kind: bytes, content: bytes) -> bytes:
        return struct.pack("!I", len(content)) + kind + struct.pack("!I", zlib.crc32(content))

    raw = b"".join(b"\x00" + row.tobytes() for row in image)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def e(value) -> str:
    return escape(str(value), quote=True)


def page(title: str, content: str, *, active: str = "home", research_dir: str = "docs/research") -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMS fault-prediction artifacts, reproducible holdout evidence, and an explicit automated submission decision.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a>
<nav aria-label="Main navigation"><a href="index.html"{' aria-current="page"' if active == "home" else ''}>Overview</a><a href="executive-summary.html"{' aria-current="page"' if active == "guide" else ''}>Submission guide</a><a href="experiment-review.html"{' aria-current="page"' if active == "research" else ''}>Research</a><a href="priority-site-review.html">Priority sites</a><a href="README.md">Project brief</a></nav></div></header>
<main id="main">{LATEST_REVIEW if active in ("home", "guide") else ""}{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated machine gates require zero human raster inspection.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{e(research_dir)}/run-card.json">Run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Repository evidence only; not a live leaderboard projection. No competition slot selected or used by this repository. Local validation and holdout results are <strong>not</strong> organizer acceptance.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def nearsplay_release(card: dict, readiness: dict, research_dir: str) -> str:
    file = local_path(card["submission_file"])
    size = file.stat().st_size / (1024 * 1024)
    h = card["holdout"]
    obs = readiness["observed_registry"]["dots"]
    screen = h["screen_seed_31"]
    confirm = h["confirmation_seed_41"]
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill good">FORMAT-VALID · LOCAL CONTRACT PASSED</span><span class="pill caution">PROMOTED ON HOLDOUT-DTI · PROXY ONLY</span><span class="pill caution">NOT ORGANIZER-CONFIRMED</span></div>
<h2 id="release-title">Safe to download. <span>Not cleared to submit.</span></h2>
<p><strong>Zero human inspection required:</strong> automated machine verification reopened <code>{e(file.name)}</code> and confirmed a single <code>float32</code> band, <code>EPSG:32611</code>, <code>3,730 × 3,292</code>, the exact sample-template transform, finite values in <code>[0, 1]</code> across all 5,167,373 in-footprint cells (<code>NaN</code> nodata outside), 40,000 binary dots at one kernel radius (300 m), <strong>0</strong> dots on known USGS/INGENIOUS faults, uniqueness against the local registry (max Spearman <code>{obs['max_spearman']:.4f} &le; 0.90</code>, max 3-px dot overlap <code>{100 * obs['max_fraction_within_3px']:.2f}% &le; 70%</code>), and a <strong>paired HOLDOUT-DTI improvement of +{screen['delta']:.6f}</strong> (95% CI <code>[+{screen['ci95'][0]:.6f}, +{screen['ci95'][1]:.6f}]</code>) confirmed on a fresh split at <strong>+{confirm['delta']:.6f}</strong> (95% CI <code>[+{confirm['ci95'][0]:.6f}, +{confirm['ci95'][1]:.6f}]</code>).</p>
<div class="actions"><a class="button" href="{e(card['submission_file'])}" download>↓ Download the submission TIF <span>{size:.2f} MiB</span></a><a class="button secondary" href="{e(card['sidecar'])}" download>Provenance sidecar (.json)</a><a class="button secondary" href="executive-summary.html">Open the submission guide</a></div>
<p class="filename">{e(file.name)}</p>
<details open><summary>Automated validation scorecard &amp; file identity</summary><dl>
<dt>SHA-256</dt><dd><code>{e(card['submission_sha256'])}</code></dd>
<dt>Submission name</dt><dd><code>{e(card['submission_name'])}</code></dd>
<dt>Submission note ({len(card['submission_note'])}/140)</dt><dd><code>{e(card['submission_note'])}</code></dd>
<dt>Portal format gate</dt><dd><code>PASSED</code> · 1 band <code>float32</code> · <code>EPSG:32611</code> · <code>3,730 × 3,292</code> · finite in <code>[0, 1]</code> inside · <code>NaN</code> outside · <code>0</code> NaN inside</dd>
<dt>Receipts</dt><dd><a href="{e(card['validation_receipt'])}">Reopened-file validation</a> · <a href="{e(card['holdout_report'])}">Holdout report</a> · <a href="{e(research_dir)}/run-card.json">Run card</a> · <a href="{e(research_dir)}/readiness.json">Readiness receipt</a></dd>
</dl></details></section>'''


def nearsplay_identity(card: dict) -> str:
    return f'''<section class="section"><div class="identity">
<label for="submission-name">Submission name (copy into “File to submit”)</label>
<input id="submission-name" value="{e(card['submission_name'])}" readonly>
<button class="copy-button" type="button" data-copy="submission-name">Copy name</button>
<label for="submission-note">Submission note · {len(card['submission_note'])} / 140 characters (paste into “Note (optional)”)</label>
<textarea id="submission-note" readonly rows="3">{e(card['submission_note'])}</textarea>
<button class="copy-button" type="button" data-copy="submission-note">Copy note</button>
<p id="copy-status" role="status" aria-live="polite"></p>
</div></section>'''


def peer_table(peers: list[dict]) -> str:
    if not peers:
        return ""
    rows = "".join(
        f'<tr><th scope="row">{e(p["lane"])}</th><td>{e(p["decision"])}</td><td>{e(p.get("artifact", "—"))}</td><td>{e(p.get("verdict", "—"))}</td></tr>'
        for p in peers
    )
    return f'''<section class="section"><p class="eyebrow">Registered peer lanes</p>
<h2>Other artifacts in this repository — recorded, not re-adjudicated here.</h2>
<div class="table-wrap"><table><caption>Peer lanes and stopped attempts (no slot is selected by this page)</caption>
<thead><tr><th>Lane</th><th>Decision</th><th>Artifact</th><th>Verdict</th></tr></thead><tbody>{rows}</tbody></table></div></section>'''


def build(template: Path) -> dict[Path, str | bytes]:
    pointer = ROOT / "docs/current-run.json"
    readiness = verify(pointer, template)
    selected = json.loads(pointer.read_text())
    card_path = local_path(selected["run_card"])
    research_dir = card_path.parent.relative_to(ROOT).as_posix()
    card = json.loads(card_path.read_text())

    if card.get("schema_version") != 3:
        raise ValueError("this site template renders schema_version 3 holdout-promoted cards")
    if readiness["research_verdict"] != "promote" or readiness["submission_approved"] is not False:
        raise ValueError("the current artifact must be holdout-promoted and must not grant approval")
    if readiness["slot_selected"] is not False:
        raise ValueError("no competition slot may be marked selected by the site builder")

    h = card["holdout"]
    screen = h["screen_seed_31"]
    confirm = h["confirmation_seed_41"]
    obs = readiness["observed_registry"]["dots"]

    score_table = f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · catalogue-proxy component holdout · paired spatial-block 95% CI</caption>
<thead><tr><th>Split</th><th>Candidate DTI</th><th>Matched control DTI</th><th>Δ HOLDOUT-DTI</th><th>95% paired CI</th><th>Quadrants</th><th>Withheld positives</th></tr></thead>
<tbody>
<tr><th scope="row">Screen (seed 31)</th><td>{screen['candidate_dti']:.6f}</td><td>{screen['control_dti']:.6f}</td><td>+{screen['delta']:.6f}</td><td>[+{screen['ci95'][0]:.6f}, +{screen['ci95'][1]:.6f}]</td><td>{screen['quadrants']}</td><td>{screen['withheld_positives']:,}</td></tr>
<tr><th scope="row">Confirmation (seed 41, fresh split + fresh draws)</th><td>{confirm['candidate_dti']:.6f}</td><td>{confirm['control_dti']:.6f}</td><td>+{confirm['delta']:.6f}</td><td>[+{confirm['ci95'][0]:.6f}, +{confirm['ci95'][1]:.6f}]</td><td>{confirm['quadrants']}</td><td>{confirm['withheld_positives']:,}</td></tr>
</tbody></table></div>
<p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code> · protocol <code>{e(h['protocol_version'])}</code> · alpha 0.2 / beta 0.8 · triangular 300 m kernel · {e(h['bootstrap']['blocks'])} geographic blocks · {e(h['bootstrap']['replicates'])} paired replicates. <strong>Catalogue-recovery proxy only — never an organizer score or a leaderboard projection.</strong></p>'''

    gates = "".join(
        f'<tr><th scope="row">{e(g["name"].replace("_", " ").capitalize())}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in readiness["gates"]
    )

    peers: list[dict] = []
    for extra in selected.get("additional_research_artifacts", []):
        peers.append({"lane": extra.get("lane", "peer"),
                      "decision": extra.get("decision", "registered peer artifact"),
                      "artifact": extra.get("run_card", "—"),
                      "verdict": "holdout-promoted on its own protocol"})
    for extra in selected.get("additional_stopped_attempts", []):
        peers.append({"lane": extra.get("lane", "stopped attempt"),
                      "decision": extra.get("decision", "stopped"),
                      "artifact": extra.get("pointer", "—"),
                      "verdict": "negative / duplicate-stop; not published"})

    home = f'''<section class="intro"><div><p class="eyebrow">DOE GEMS · Lane H-NEARSPLAY · 25 October 2026</p>
<h1>Near-splay annulus.<br>+0.066 over the matched control.</h1>
<p class="lead">A new placement strategy: binary dots placed <strong>300 m–1.5 km off the USGS/INGENIOUS catalogue</strong>, inner-edge weighted and Poisson-disk thinned at one kernel radius (300 m). On the buffered whole-component catalogue holdout it beats the proximity-matched control on both a screen and a fresh confirmation split, with paired 95% confidence intervals entirely above zero and 4/4 quadrants positive on each.</p>
<p class="meta">Experiments run: {card['experiments_run']} / {card['experiment_cap']} <span>·</span> No competition slot selected or used</p></div>
<a class="text-link" href="{e(card['holdout_report'])}">Read the holdout report ↗</a></section>
{nearsplay_release(card, readiness, research_dir)}
<section class="evidence-strip" aria-label="Research diagnostics"><article><span>Off-catalogue dots</span><strong>40,000</strong><small>0 on the 60,988 known fault pixels</small></article><article><span>Uniqueness audit</span><strong>{obs['registry_entries_compared']} registry rasters</strong><small>Max 3-px overlap {100 * obs['max_fraction_within_3px']:.2f}% (&le; 70%)</small></article><article><span>Paired HOLDOUT-DTI</span><strong>+{screen['delta']:.3f}</strong><small>CI [+{screen['ci95'][0]:.3f}, +{screen['ci95'][1]:.3f}] · 4/4 quadrants</small></article></section>
<section class="section"><p class="eyebrow">01 / The mechanism</p><h2>Why unmapped faults sit just outside the catalogue.</h2>
<p>A surface-expression catalogue records where rock is exposed enough to map a trace. The faults the competition scores are by construction the ones the catalogue lacks, and the <em>nearest</em> places those can hide are the unmapped splays and stepovers of mapped systems — 300 m to 1.5 km off a mapped trace, close enough to share its damage zone. DrivenData staff confirmed that newly mapped geometry of an existing system counts as a new fault (<a href="https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536">thread 11536</a>) and that known USGS/INGENIOUS pixels are masked out of scoring (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">thread 11516</a>), so off-catalogue mass is the only mass that can earn credit.</p>
<p>Mechanically, the published index is <code>DTI = T / (0.2T + 0.2F + 0.8G)</code> with a 300 m triangular kernel applied as a <em>maximum</em> over neighbours. Redundant dots therefore add false-positive mass without adding true-positive credit: a binary dot at one kernel radius strictly dominates a graded map on the same support, and sparse spacing beats flooding.</p>
<p><strong>Non-fault process that could mimic this:</strong> erosional and drainage lineaments, cultural or road linear features, and volcanic contacts that happen to parallel mapped traces inside the annulus. That is why the control is proximity-matched and why the delta, not the raw score, is the decision statistic.</p>{score_table}</section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated machine inspection</p><h2>Every gate has a deterministic state.</h2></div><p>Passed, failed or unknown.<br>Zero human raster inspection.</p></div>
<div class="table-wrap"><table><thead><tr><th>Automated gate</th><th>State</th><th>Machine rule</th></tr></thead><tbody>{gates}</tbody></table></div></section>
<section class="section"><p class="eyebrow">03 / This session's experiments</p><h2>Two holdouts: one promoted, one negative.</h2>
<div class="table-wrap"><table><caption>HOLDOUT-DTI — catalogue-proxy component holdout, not competition scores</caption>
<thead><tr><th>Experiment</th><th>Hypothesis</th><th>Pooled DTI vs control</th><th>95% CI of Δ</th><th>Quadrants</th><th>Verdict</th></tr></thead><tbody>
<tr><th scope="row">1 · H-VENT</th><td>Volcanic vents mark uncatalogued feeder fissures</td><td>0.000609 vs 0.018679 (Δ −0.018071)</td><td>[−0.019188, −0.016825]</td><td>0/4</td><td><span class="gate failed">negative</span></td></tr>
<tr><th scope="row">2 · H-NEARSPLAY</th><td>Off-catalogue splays 300 m–1.5 km from mapped traces</td><td>0.085021 vs 0.019654 (Δ +0.065367)</td><td>[+0.056983, +0.074347]</td><td>4/4</td><td><span class="gate passed">promoted on holdout</span></td></tr>
</tbody></table></div>
<p class="fine">Both experiments: evaluator <code>component-holdout-v3-blockstats-20261025</code>, buffered whole-components, alpha 0.2 / beta 0.8, triangular 300 m kernel, paired spatial-block 95% CI. Full reports: <a href="docs/research/h-vent-feeder-holdout.json">H-VENT</a> · <a href="docs/research/h-nearsplay-holdout.json">H-NEARSPLAY</a>. <strong>Negative results are deliverables.</strong></p></section>
{peer_table(peers)}
<section class="section two-column"><div><p class="eyebrow">04 / Ranked hypotheses not previously tried</p><h2>What comes next if this artifact does not convert.</h2>
<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Hypothesis · signature</th><th>Why it targets uncatalogued faults</th><th>Prior ΔDTI / cost</th><th>Status</th></tr></thead><tbody>
<tr><th scope="row">1</th><td><strong>H-34-01</strong> substrate-concealment prior — SGMC map-unit polygons × relief bands</td><td>Faults under basin fill and lake cover are missing from every surface catalogue; the prior re-weights where to spend existing evidence</td><td>+0.002…+0.015 / low</td><td>Registered; not run</td></tr>
<tr><th scope="row">2</th><td><strong>H-34-02</strong> potential-field depth lineaments — tilt derivative + Euler deconvolution</td><td>A buried magnetic source with no surface rupture is invisible to a surface catalogue by construction</td><td>+0.002…+0.012 / medium</td><td>Registered; not run</td></tr>
<tr><th scope="row">3</th><td><strong>H-34-03</strong> drainage χ / ksn disequilibrium — NHD flowlines + 3DEP</td><td>Fluvial networks record deformation where scarps are eroded or buried, from an independent programme</td><td>+0.002…+0.010 / high</td><td>Registered; blocked on data</td></tr>
</tbody></table></div>
<p class="fine">Planning priors are experiment ranges, not forecasts or competition-score predictions.</p></div>
<div class="note-card"><h3>Verified official review links</h3><ul class="spaced">
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; DW-Tversky metric</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official public leaderboard</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR official rules PDF (Sept 2026)</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">DrivenData reference solution</a></li>
<li><a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS submission 1391</a></li>
</ul><p class="fine">These hosts are outside this session's network access. Links are for manual review, not fresh verification.</p></div></section>'''

    guide = f'''<section class="intro"><div><p class="eyebrow">Executive submission guide</p><h1>Exactly how to submit.<br>And what is still unproven.</h1>
<p class="lead">One holdout-promoted TIF is published below. It is <strong>OK to download</strong>. It is <strong>not established as cleared to submit</strong>: the evidence is HOLDOUT-DTI on a catalogue proxy, not ORGANIZER-CONFIRMED, and no competition slot has been used by this repository.</p></div></section>
{nearsplay_release(card, readiness, research_dir)}
{nearsplay_identity(card)}
<section class="section"><p class="eyebrow">Step by step</p><h2>Using the official “New submission” form</h2>
<ol class="steps">
<li><strong>Download the TIF.</strong><p>Click the download button above and save <code>{e(Path(card['submission_file']).name)}</code>. Do not edit, clip, resize, or re-encode it: any edit changes the SHA-256 and voids the validation receipt.</p></li>
<li><strong>Open the official form.</strong><p>In an authorized DrivenData account on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition page</a>, go to “New submission” → “File to submit”.</p></li>
<li><strong>Attach the file.</strong><p>Choose the single-band GeoTIFF (.tif). This repository does not authenticate, upload, or consume a weekly slot; that step belongs to you, in your account.</p></li>
<li><strong>Paste the note.</strong><p>Paste the copied submission note into “Note (optional)” so the submission can be told apart later (e.g. “clustering with k=25”).</p></li>
<li><strong>Keep the receipt.</strong><p>Record the submission ID, returned score, file SHA-256 and timestamp. <strong>Only</strong> a submission-page receipt is ORGANIZER-CONFIRMED; holdout deltas and projections are never written as scores.</p></li>
</ol></section>
<section class="section two-column"><div><p class="eyebrow">Is it OK to download and submit?</p><h3>Download: yes · Submit: not confirmed</h3>
<ul class="spaced">
<li><strong>Download:</strong> yes — the exact validated bytes are linked and the SHA-256 is recorded.</li>
<li><strong>Submit:</strong> not established. The file passed the local format contract and the holdout gate, but a catalogue proxy is not the private expert-new test labels (IR-30-017, IR-30-079), and no DrivenData receipt exists.</li>
<li><strong>Range error:</strong> this file is finite <code>[0, 1]</code> inside the footprint with NaN nodata outside, matching the published GEMS format, and avoids both known causes of the historical “Predicted values must be in range [0, 1]” rejection (in-footprint NaN; whole-array out-of-range values). Local validation does not prove portal acceptance (IR-30-019).</li>
<li><strong>Budget:</strong> at most one weekly slot on this file, and keep the receipt either way — a rejected upload is evidence too.</li>
</ul></div>
<div class="note-card"><h3>Official review links</h3><ul class="spaced">
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; submission format</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data page</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a></li>
</ul><p class="fine">External hosts are outside this session's network access. Links are for review, not fresh verification.</p></div></section>'''

    research_html = f'''<section class="intro"><div><p class="eyebrow">Scientific review · H-NEARSPLAY</p>
<h1>A placement result,<br>with its controls and limits.</h1>
<p class="lead">One hypothesis was promoted on a spatial holdout, one was falsified, and both receipts are published. No number on this page is an organizer score.</p></div></section>
<section class="section"><p class="eyebrow">01 / Registered design</p><h2>Hide-and-recover over whole fault components.</h2>
<p>Whole 8-connected catalogue components are withheld as stand-in “new” faults; the remaining components are masked exactly as the organizer masks known faults. Every catalogue-derived quantity is computed only from the visible half. Emissions are binary, Poisson-disk thinned at 300 m, and scored with the exact masked distance-weighted Tversky index (alpha 0.2, beta 0.8, triangular 300 m kernel), pooling truth credit and false-positive mass before the ratio is taken.</p>
<p><strong>Controls.</strong> The primary arm is compared against (a) a <em>proximity-matched</em> random emission whose distance-to-known profile matches the candidate's, and (b) a uniform off-catalogue emission. A positive result therefore cannot be explained by generic proximity to mapped faults, nor by the mere absence of a geographic prior.</p>
<p><strong>Zone definition (frozen).</strong> Dots sit 300 m–1.5 km from <em>known</em> traces, scored by inverse distance to the known set, so the inner edge starts immediately outside mapped traces. The inner exclusion band is what allows a dot to fall within 300 m of a withheld component without landing on mapped pixels.</p>{score_table}</section>
<section class="section"><p class="eyebrow">02 / The negative experiment</p><h2>H-VENT: a real hypothesis that the proxy could not validate.</h2>
<p>Volcanic feeder fissures are a genuinely uncatalogued population: only 615 of 6,776 vent pixels (≈9%) lie within 300 m of a catalogue trace, and 0 of 21 inventoried vents do. On the catalogue proxy the vent-aligned arm scored <strong>0.000609</strong> against a matched control of <strong>0.018679</strong> on screen and <strong>0.001403</strong> vs <strong>0.016792</strong> on confirmation — decisively worse, 0/4 quadrants, both paired CIs entirely below zero.</p>
<p>This is <strong>not</strong> evidence that volcanic vents do not mark faults. It is evidence that a catalogue-derived proxy <em>cannot</em> adjudicate a hypothesis about structures the catalogue does not contain (IR-30-017, IR-30-079). The line is closed on this proxy and the negative result is published as a deliverable.</p></section>
<section class="section"><p class="eyebrow">03 / Uniqueness and its limits</p><h2>Unique against 21 local rasters — with a stated margin.</h2>
<p>Against every locally available registry raster the maximum full-raster Spearman correlation is <code>{obs['max_spearman']:.4f}</code> (duplicate threshold 0.90) and the maximum share of candidate dots falling within 3 px of one reference is <code>{100 * obs['max_fraction_within_3px']:.2f}%</code> (duplicate threshold 70%). No lane collision. The margin on the overlap statistic is thin, and the complete parallel registry is unavailable here (IR-30-078), so a later session with the full registry must re-run the final-dot comparison before any upload.</p>
<p>An inverse-square inner-edge variant was also tried while building the artifact: it concentrated too hard and collided with a dense existing edge-hybrid reference. The frozen inverse-linear weighting was retained. That ablation is recorded here so the published support is reproducible rather than cherry-picked.</p></section>
<section class="section"><p class="eyebrow">04 / Boundaries</p><h2>What this is, and what it is not.</h2>
<ul class="spaced">
<li>It is a <strong>placement</strong> result on a catalogue proxy, not a new fault-physics detector. It does not claim to see faults a magnetometer or a lidar cannot.</li>
<li>It is <strong>not</strong> a leaderboard projection. The reported 0.2778 (GEMSDOE32 H33), 0.2600 (GEMSDOE25/30 D2.8) and 0.4413 (live leaderboard) remain unverified historical claims with no receipt binding a score to a file hash (IR-30-080).</li>
<li>It is <strong>not</strong> geothermal-vent detection. No temperature, permeability, flow or vent observation was used.</li>
<li>It does <strong>not</strong> use organizer-authenticated data: everything ran on SHA-256-pinned owner mirrors (IR-30-001).</li>
</ul></section>'''

    return {
        ROOT / "index.html": page("H-NEARSPLAY submission TIF & automated gate decision", home, active="home", research_dir=research_dir),
        ROOT / "executive-summary.html": page("Executive submission guide", guide, active="guide", research_dir=research_dir),
        ROOT / "experiment-review.html": page("Scientific review · H-NEARSPLAY", research_html, active="research", research_dir=research_dir),
        ROOT / "docs/assets/nearsplay-support.png": png_preview(template, local_path(card["submission_file"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open the current research download and submission decision.</a></p></body></html>\n',
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    p.add_argument("--check", action="store_true", help="fail if generated Pages files are stale")
    args = p.parse_args()
    for path, content in build(args.template).items():
        data = content.encode() if isinstance(content, str) else content
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"stale generated site file: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Built GEMSDOE30 submission Pages")


if __name__ == "__main__":
    main()
