#!/usr/bin/env python3
"""Deterministic Pages release from inspected artifacts and stopped-run evidence.

The latest attempt and the retained downloadable artifact are separate identities.
A duplicate-stopped attempt can never be advertised as a new unique TIFF.
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
from scripts.verify_stopped_attempt import verify as verify_stopped
from scripts.verify_lsm_run import verify as verify_lsm

STYLE = "docs/assets/research.css"
RESEARCH = "docs/research/texture-displacement"
LATEST = "docs/research/texture-controls"


def png_preview(template, candidate):
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
    def chunk(kind, content):
        return struct.pack("!I", len(content)) + kind + content + struct.pack("!I", zlib.crc32(kind + content))
    raw = b"".join(b"\x00" + row.tobytes() for row in image)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def e(value):
    return escape(str(value), quote=True)


def score_row(name, row):
    lo, hi = row["ci95"]
    return f'<tr><th scope="row">{e(name)}</th><td>{row["value"]:.5f}</td><td>[{lo:.5f}, {hi:.5f}]</td></tr>'


def page(title, content, *, active="overview"):
    nav = ''.join(f'<a href="{url}"' + (' aria-current="page"' if active == key else '') + f'>{label}</a>'
                  for key, url, label in (("overview", "index.html", "Overview"),
                                          ("guide", "executive-summary.html", "Submission guide"),
                                          ("research", "experiment-review.html", "Research")))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMS fault-discovery evidence: latest experiment stopped as a duplicate, an archived research-only TIFF, and automated submission gates.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a><nav aria-label="Main navigation">{nav}<a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main><footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. A valid file is not a competition approval.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{LATEST}/run-card.json">Latest run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Repository evidence, not a live leaderboard. No competition slot selected or used. Latest attempt is stopped; retained TDX-1 is an archived research download only.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release(card):
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill caution">NOT APPROVED FOR SUBMISSION</span><span class="pill good">Archived TIFF · local contract passed</span></div>
<h2 id="release-title">Download for research. <span>Do not submit.</span></h2>
<p><strong>Retained TDX-1 artifact from the previous session—not a new submission from this attempt.</strong> It is available for reproducibility, but its performance gate failed. The latest TDX-C2 raster is a duplicate and is deliberately not downloadable. Automated checks made both decisions; there is no human-inspector override.</p>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download archived research TIFF <span>{size:.2f} MiB</span></a><a class="button secondary" href="{RESEARCH}/readiness.json">Archived artifact decision</a></div>
<p class="filename">{e(file.name)}</p><details><summary>Archived file identity &amp; current validation</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Contract</dt><dd>One float32 band · EPSG:32611 · 3,730 × 3,292 · exact template transform · finite [0,1] inside · NaN nodata outside</dd><dt>Receipt</dt><dd><a href="{RESEARCH}/validation.json">Recorded validation</a> · <a href="{e(card['published_tiff'][:-4])}.json">Provenance sidecar</a></dd></dl></details></section>'''


def score_table(card):
    h = card["holdout"]
    rows = score_row("Core 19-band comparator", h["comparators"]["core19"])
    rows += score_row("TDX-C2 · fixed candidate (22 bands)", h)
    rows += score_row("Matched zero-lag control (22 bands)", h["comparators"]["zero22"])
    rows += score_row("Matched phase-scrambled control (22 bands)", h["comparators"]["phase22"])
    return f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld positive pixels · 95% spatial-bootstrap CI</caption><thead><tr><th>Fixed arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table></div><p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code>; protocol <code>{e(h['protocol_version'])}</code>. Pooled buffered whole-component regional trials; 371 geographic bootstrap blocks. Previously inspected catalogue folds—not independent confirmation, an organizer score, or a hidden-test forecast.</p>'''


def latest_notice(card):
    overlap = card["registry"]["dots"]["max_fraction_within_3px"]
    return f'''<section class="stop-notice" aria-labelledby="stop-title"><div class="release-heading"><span class="pill caution">DUPLICATE-STOP · latest attempt</span><span class="meta">TDX-C2 / 25 October 2026</span></div><h2 id="stop-title">No new eligible TIFF was published.</h2><p><strong>{100 * overlap:.2f}% of final dots</strong> fall within 3 pixels of an existing G30-S19 reference, exceeding the mandatory 70% limit. We stopped all experimentation, quarantined the raster, and did not change dots to evade the rule. It also failed the paired holdout-improvement gate.</p><p><strong>New competition download: none. Competition upload: not approved.</strong> A new byte hash or passing the [0,1] format check cannot establish a unique strategy.</p><div class="actions"><a class="button secondary" href="experiment-review.html">Read the stopped experiment</a><a class="text-link" href="{LATEST}/run-card.json">Latest JSON run card ↗</a></div></section>'''


def gate_table(readiness):
    labels = {"file_contract": "Public file reinspection", "labelled_holdout_evidence": "Pooled holdout & confidence intervals",
              "paired_improvement": "Beat all matched controls", "single_feature_leakage_canaries": "Individual feature canaries",
              "count_matched_construction": "Count-matched construction", "surface_observed_registry": "Surface · observed registry",
              "dots_observed_registry": "Final dots · observed registry", "complete_parallel_registry": "Complete parallel registry",
              "assigned_lane": "External lane assignment", "comparable_historical_best": "Historical-best rerun",
              "experimental_budget": "Experiment budget", "artifact_identity": "Name & short note"}
    rows = ''.join(f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>' for g in readiness["gates"])
    return f'<div class="table-wrap"><table><caption>Latest attempt · automated research gates</caption><thead><tr><th>Gate</th><th>State</th><th>Evidence rule</th></tr></thead><tbody>{rows}</tbody></table></div>'


def build(template):
    pointer = ROOT / "docs/current-run.json"
    retained = verify(pointer, template)
    selection = json.loads(pointer.read_text())
    card = json.loads(local_path(selection["run_card"]).read_text())
    latest_path = local_path(selection["latest_attempt"])
    latest = json.loads(latest_path.read_text())
    stopped = verify_stopped(latest_path.parent, template)
    if (retained["research_verdict"] != "negative" or latest.get("duplicate_stopped") is not True
            or stopped["download_ok"] is not False):
        raise ValueError("This stopped-result site cannot advertise a promoted or newly downloadable candidate")
    notice, archive, scores = latest_notice(latest), release(card), score_table(latest)
    lsm_section, lsm_bullet = "", ""
    for extra in selection.get("additional_stopped_attempts", []):
        if extra.get("lane") != "G30-LSM":
            raise ValueError("unknown additional stopped attempt; add an explicit verified renderer")
        lsm_pointer = local_path(extra["pointer"])
        lsm_ready = verify_lsm(lsm_pointer, template)
        lsm_card = json.loads(local_path(json.loads(lsm_pointer.read_text())["run_card"]).read_text())
        if lsm_ready["ok_to_submit"] is not False or lsm_card["verdict"] != "duplicate-stop":
            raise ValueError("This stopped-result site cannot advertise a promoted G30-LSM candidate")
        lsm = "docs/research/2026-10-25-lsm"
        h = lsm_card["holdout"]
        d = h["lsm42_minus"]["core19"]
        prof = lsm_card["dots_by_catalogue_distance_px"]
        near = (prof["2"] + prof["3-5"] + prof["6-10"]) / sum(prof.values())
        top = max((f for f in lsm_card["duplicate_references"] if not f["dense_reference_non_discriminating"]),
                  key=lambda f: f["fraction_within_3px"])
        lsm_section = f'''<section class="stop-notice" aria-labelledby="lsm-title"><div class="release-heading"><span class="pill caution">DUPLICATE-STOP · G30-LSM</span><span class="meta">LiDAR scarp morphology + geophysics / 25 October 2026</span></div><h2 id="lsm-title">Holdout gate passed. Uniqueness failed. No TIFF.</h2><p>HOLDOUT-DTI <strong>{h["lsm42"]["value"]:.4f}</strong> vs the spatially blocked best core19 {h["core19"]["value"]:.4f}: paired difference <strong>{d["value"]:+.4f} [{d["ci95"][0]:+.4f}, {d["ci95"][1]:+.4f}]</strong> ({h["withheld_positives"]:,} withheld positives; catalogue proxy, not an organizer score). But <strong>{100 * top["fraction_within_3px"]:.1f}% of its final dots</strong> lie within 3 px of an existing raster ({e(Path(top["reference"]).name[:48])}…), so the protocol stopped it. The model has no proximity input yet put {near:.0%} of its dots 200 m–1 km from mapped faults: catalogue-trained habitat models crowd the same near-fault zone as G30-S19 — the zone owner-reported leaderboard differentials show earns about random hits.</p><p><strong>Why H33 scored 0.2778:</strong> a byte-exact pruning of the h19-5 lineament support; a label-blind 5-px lattice calibrates hidden new-fault density at about 0.244% of pixels, and D2.8, r1, H33 and PINN all cover the same ~40.5% of it — H33 just wastes the fewest dots (projections from unverified owner scores).</p><div class="actions"><a class="button secondary" href="{lsm}/why-h33-scored-0.2778.md">Why H33 scored 0.2778</a><a class="button secondary" href="{lsm}/review.md">G30-LSM review</a><a class="text-link" href="{lsm}/readiness.json">Machine decision ↗</a> <a class="text-link" href="{lsm}/leaderboard-calibration.json">Calibration data ↗</a></div></section>'''
        lsm_bullet = f'<li>G30-LSM: holdout gate passed ({d["value"]:+.4f}) but duplicate-stop ({100 * top["fraction_within_3px"]:.1f}% of dots within 3 px of an existing raster); no public raster. <a href="{lsm}/review.md">Review</a>.</li>'
    home = f'''<section class="intro"><div><p class="eyebrow">DOE GEMS / evidence-first research</p><h1>No new submission.<br>A clear decision.</h1><p class="lead">A fixed magnetic-displacement experiment failed the improvement gate and crossed the duplicate threshold. Protecting the submission budget is part of the result.</p><p class="meta">25 October 2026 <span>·</span> One fixed experiment <span>·</span> No slot used</p></div><a class="text-link" href="{LATEST}/preregistration.md">Read the frozen plan ↗</a></section>
{notice}{lsm_section}{archive}
<section class="evidence-strip" aria-label="Latest experiment diagnostics"><article><span>Observed registry</span><strong>{stopped["observed_registry"]["dots"]["registry_entries_compared"]} files compared</strong><small>164 frozen + 2 post-stop arrivals</small></article><article><span>Leakage canaries</span><strong>28 features × 4 folds</strong><small>No AUC alarm above 0.90</small></article><article><span>Mandatory stop</span><strong>79.09% dot overlap</strong><small>Above the 70% lane threshold</small></article></section>
<section class="section"><p class="eyebrow">01 / What we learned</p><h2>Additional features did not establish additional signal.</h2><p>The full-stack candidate did not beat core19, the zero-lag control, or the phase-scrambled control with a positive paired confidence interval. The phase control is not selected as a replacement. All point estimates below come from one preregistered, count-matched experiment.</p>{scores}<a class="text-link" href="experiment-review.html">Scientific interpretation, nine-site audit &amp; limitations ↗</a></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated inspection</p><h2>Unknown never means approved.</h2></div><p>The duplicate is not distributed.<br>Stored local validation is not a public-file re-read.</p></div>{gate_table(stopped)}</section>
<section class="section two-column"><div><p class="eyebrow">03 / Historical lesson</p><h2>H33 is a pruning lesson, not independent geology.</h2><p>Educational byte-level reconstruction reproduced H33's 37,654-dot support exactly from the 40,199-dot GEMSDOE28 base by removing dots at catalogue distance ≤2 pixels. Nearby predictions share max-kernel truth credit, so redundant support can add penalty without adding coverage.</p><p>The owner's historical result attribution is unverified: no submission-page receipt binds the score to those bytes. No live leaderboard value or higher-score promise is asserted.</p><a class="text-link" href="{LATEST}/historical-reference-audit.json">All nine pinned references &amp; local format checks ↗</a></div><div class="note-card"><h3>Next work, not another experiment today</h3><ul class="spaced"><li>Synchronize assigned lanes and original continuous surfaces.</li><li>Restore a comparable historical-best checkpoint and reserve untouched geographic validation.</li><li>Require displacement-specific controls to beat core19 before adding model complexity.</li><li>Keep fault-mapping evidence separate from claims about geothermal vents.</li></ul><a href="README.md#current-owner-prompt">Complete standing owner prompt ↗</a></div></section>'''
    guide = f'''<section class="intro"><div><p class="eyebrow">Executive submission guide</p><h1>The file is not<br>the approval.</h1><p class="lead">There is no new approved competition TIFF from this attempt. Downloadable research evidence and competition submission are separate states.</p></div></section>{notice}{lsm_section}{archive}
<section class="section"><p class="eyebrow">Current decision</p><h2>Why the queue stays empty.</h2><ul class="spaced"><li>Latest TDX-C2: duplicate-stop and no paired holdout improvement; no public raster.</li>{lsm_bullet}<li>Retained TDX-1: locally format-valid research artifact, but its performance gate failed.</li><li>Complete parallel registry, external lane assignment and comparable historical-best evidence remain unavailable.</li><li>Current portal cap, eligibility, deadline and organizer acceptance are not verified.</li></ul><p><code>python scripts/verify_stopped_attempt.py --require-promote</code> and <code>python scripts/verify_current_run.py --require-promote</code> both deliberately exit <b>2</b>. No human inspector or approval override is required or provided.</p></section>
<section class="section"><p class="eyebrow">Archived artifact identity · not latest candidate</p><h2>A name and note for the retained research download.</h2><div class="identity"><label for="submission-name">Archived TDX-1 name · do not upload</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Archived research note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div><p class="fine">The stopped TDX-C2 name and ≤140-character note are recorded only in its <a href="{LATEST}/run-card.json">negative run card</a>, not offered as a submission.</p></section>
<section class="section"><p class="eyebrow">Future approved artifact only</p><h2>Exactly how a later submission would work.</h2><ol class="steps"><li><strong>Pass project research gates.</strong><p>The exact artifact must beat a comparable holdout best, clear all feature canaries, pass both novelty stages against a complete registry, and match the template. Unknown blocks promotion.</p></li><li><strong>Use the separate slot selector.</strong><p>Verify the current weekly allowance and required entrant/rules evidence before allocating a slot. Research promotion is not an upload permission.</p></li><li><strong>Download the selected .tif, not this guide.</strong><p>The authorized selected artifact must have its own one-click link, hash-bound automated verdict, unique name and short note. Do not use an archived reference, JSON, HTML or either negative candidate here.</p></li><li><strong>Use the official “New submission” form.</strong><p>In an authorized account on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official competition</a>, choose the selected single-band GeoTIFF under “File to submit” and paste its note. The repository does not authenticate, upload, or use a weekly slot.</p></li><li><strong>Retain the organizer receipt.</strong><p>Record the returned submission ID, file SHA-256, score and timestamp before calling any result <b>ORGANIZER-CONFIRMED</b>. Never relabel HOLDOUT-DTI or a projection as a competition score.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">About the previous range error</p><h2>No silent clipping.<br>No guessed diagnosis.</h2><p>The exact rejected file and organizer receipt are unavailable. The retained TIFF is reopened against the template by the project: finite [0,1] inside, one float32 band, and exact CRS/shape/transform. NaN nodata outside follows the documented local contract.</p><p>That does not establish private portal acceptance or range-error immunity. Historical zero-outside files can fail the documented null-outside check even if their in-footprint range is valid.</p></div><div class="note-card"><h3>Official review links</h3><ul class="spaced"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; submission format</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data page</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a></li></ul><p class="fine">These hosts are outside this session's network access. Links are for review, not fresh verification or organizer receipts.</p></div></section>'''
    pins = json.loads((ROOT / LATEST / "historical-reference-audit.json").read_text())["rasters"]
    sites = ''.join(f'<tr><th scope="row"><a href="{e(r["source_url"])}">{e(r["site"])}</a></th><td>{r["positive_pixels"]:,}</td><td>{"Passed" if r["local_format_validation"]["passed"] else "Failed: outside encoding"}</td><td><code>{e(r["sha256"][:16])}…</code></td></tr>' for r in pins)
    research = f'''<section class="intro"><div><p class="eyebrow">Scientific review / TDX-C2</p><h1>Falsification is<br>a deliverable.</h1><p class="lead">Conditional magnetic displacement did not establish a benefit over matched controls, and its final placement drifted into the habitat lane.</p></div></section>{notice}
<section class="section"><h2>One hypothesis. Four fixed arms. No search.</h2><p>Cached magnetic anomaly, RTP and isostatic gravity supplied the two-scale flank-profile transforms. The candidate adds three lag-gain features to all 19 core bands. Matched controls add either zero-lag coherence or locally Fourier-phase-scrambled lag gains. Intrusive lithologic contacts and gridding seams can mimic the proposed signal.</p>{scores}<p>The candidate-minus-core19 HOLDOUT-DTI difference is −0.00376, paired 95% CI [−0.00818, 0.00070], under the same evaluator and 60,988 withheld positives. This fails the improvement gate; it does not prove the candidate is significantly worse. The controls do not prove an absence of geological displacement.</p><p>Four whole-component regional trials use a 17 px training/physical-support guard, exact visible-fault masking, a 300 m triangular kernel, and equal active dot budgets. Truth credit and false-positive mass are pooled before DTI is computed. No catalogue geometry or historical predictions enter the feature transforms.</p><p class="fine">The core19 result exactly reproduces the previous same-protocol sufficient statistics and CI. This is an engineering consistency check, not independent validation. One deterministic phase control is not a sampled null distribution.</p><div class="actions"><a class="text-link" href="{LATEST}/preregistration.md">Four ranked hypotheses &amp; frozen plan ↗</a><a class="text-link" href="{LATEST}/results.json">All statistics &amp; 112 canaries ↗</a></div></section>
<section class="section"><h2>The mandatory stop worked.</h2><p>The frozen registry contained 164 observed byte identities; two later S20 arrivals were checked on both saved states after the stop, without changing predictions. Across the 166 combined comparisons, max surface Spearman was 0.15657. Final-dot Spearman was 0.06383, but overlap reached 79.09% against G30-S19's 60,000-dot output. Low pixelwise correlation alone would have missed this lane collision. No later model, emitter, density or alternative hypothesis was tried.</p><p>The stopped TIFF passed a local shared-writer check and an independent post-stop file reopen. It has no NaN inside, values [0,1], matching CRS/shape/transform and zero positive catalogue pixels. It remains private under ignored outputs/. CI verifies stored receipts, not unavailable private bytes, and cannot call this a public-file reinspection.</p><a href="{LATEST}/validation.json">Recorded validator output ↗</a> · <a href="{LATEST}/novelty-dots.json">Every final-dot comparison ↗</a> · <a href="{LATEST}/readiness.json">Fail-closed decision ↗</a></section>
<section class="section"><h2>Nine priority sites: educational audit.</h2><p>No historical raster was reused as new predictions. The table is a file diagnostic, not a performance ranking or organizer acceptance table.</p><div class="table-wrap"><table><caption>Frozen reference identities · counts and format diagnostics, not scores</caption><thead><tr><th>Priority site / pinned file</th><th>Positive pixels</th><th>Local documented format</th><th>SHA-256 prefix</th></tr></thead><tbody>{sites}</tbody></table></div><p>Fresh README inventories: <a href="{LATEST}/priority-site-review.json">nine immutable snapshots</a>. Exact artifact checks: <a href="{LATEST}/historical-reference-audit.json">reference audit</a>. H33 support reconstruction: <a href="docs/research/2026-10-25/recipe-reconstruction.json">zero mismatching pixels</a>.</p></section>
<section class="section"><h2>Why H33 may have improved—and why that is not a forecast.</h2><p>For weighted truth credit T, false-positive mass F and truth count G, the shared metric is <code>DTI = T / (0.2T + 0.2F + 0.8G + ε)</code>. Credit is a maximum over a triangular neighborhood, not an unrestricted sum. Removing redundant dots can save FP mass with little loss in truth coverage. Catalogue-flank pruning can also delete genuine new splays; its hidden-test effect cannot be inferred from support alone.</p><p>The owner's 0.2778 attribution and conflicting leaderboard claims remain <strong>unverified historical claims</strong>, not ORGANIZER-CONFIRMED. <a href="{RESEARCH}/owner-claims.csv">All 119 supplied claims</a> remain quarantined. No measured evidence here supports a promise to exceed them.</p></section>
<section class="section"><h2>Sources, boundaries &amp; next steps.</h2><p>The official <a href="https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb">reference notebook</a> was retrieved again. Its saved band metadata agrees with the cached grid and layer descriptions; <a href="{LATEST}/official-source-audit.json">hashes and exact excerpts</a> are retained. Mirror consistency is not organizer authentication or an external-data license ruling.</p><p>This is a fault-detection proxy, not a geothermal-vent detector. No temperature, permeability, flow or vent observations were used. The official <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN release</a> and <a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS data page</a> are future review links, not newly fetched datasets. None of the four proposed tests required new external data.</p><p>Next session: synchronize externally assigned lanes and continuous-surface registry, recover the historical-best checkpoint, reserve untouched geographic evaluation, and preregister a genuinely distinct mechanism before any new run. Do not rename this duplicate or move dots to pass a gate.</p><p><a href="{LATEST}/review.md">Detailed scientific report</a> · <a href="{LATEST}/verification.md">Three-pass verification journal</a> · <a href="docs/irregularities.md">Irregularities register</a></p></section>'''
    return {
        ROOT / "index.html": page("Latest attempt stopped; research download only", home),
        ROOT / "executive-summary.html": page("Executive submission guide", guide, active="guide"),
        ROOT / "experiment-review.html": page("Displacement falsification & nine-site audit", research, active="research"),
        ROOT / "docs/assets/tdx1-support.png": png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open current research download and submission decision.</a></p></body></html>\n',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=ROOT / "data/raw/sample_submission.tif")
    parser.add_argument("--check", action="store_true", help="fail if generated Pages are stale")
    args = parser.parse_args()
    for path, content in build(args.template).items():
        data = content.encode() if isinstance(content, str) else content
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"stale generated site file: {path.relative_to(ROOT)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Verified exact generated Pages" if args.check else "Built stopped-result research Pages")


if __name__ == "__main__":
    main()
