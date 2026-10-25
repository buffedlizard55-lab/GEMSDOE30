#!/usr/bin/env python3
"""Build deterministic Pages entry points from verified research receipts, not prose flags."""
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
RESEARCH = "docs/research/texture-displacement"


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
    # Small standard-library PNG encoder: no plot/image dependency or remote asset.
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


def page(title, content, card, *, guide=False):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A newly generated GEMS fault-prediction TIFF, reproducible holdout evidence, and an explicit automated submission decision.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a>
<nav aria-label="Main navigation"><a href="index.html"{' aria-current="page"' if not guide else ''}>Overview</a><a href="executive-summary.html"{' aria-current="page"' if guide else ''}>Submission guide</a><a href="{RESEARCH}/review.md">Research</a><a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. A valid file is not a competition approval.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{RESEARCH}/run-card.json">Run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Experiment recorded {e(card['created_utc'])}. Repository evidence only; not a live leaderboard. No competition slot selected or used.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release(card, readiness):
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill caution">NOT APPROVED FOR SUBMISSION</span><span class="pill good">Local TIFF contract passed</span></div>
<h2 id="release-title">Download for research. <span>Do not submit.</span></h2>
<p>This is a <strong>newly generated model output</strong>, not a renamed reference. It failed the paired performance gate; complete parallel-run evidence is also missing. Automated inspection has already made the decision—no human inspector is required.</p>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download new research TIFF <span>{size:.2f} MiB</span></a><a class="button secondary" href="{RESEARCH}/readiness.json">View automated decision</a></div>
<p class="filename">{e(file.name)}</p><details><summary>File identity &amp; validation receipt</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Contract</dt><dd>One float32 band · EPSG:32611 · 3,730 × 3,292 · exact template transform · finite [0,1] inside · NaN nodata outside</dd><dt>Receipt</dt><dd><a href="{RESEARCH}/validation.json">Reopened-file validation</a> · <a href="{e(card['published_tiff'][:-4])}.json">Provenance sidecar</a></dd></dl></details></section>'''


def build(template):
    pointer = ROOT / "docs/current-run.json"
    readiness = verify(pointer, template)
    selected = json.loads(pointer.read_text())
    card = json.loads(local_path(selected["run_card"]).read_text())
    h = card["holdout"]
    v = card["validator_output"]
    observed = readiness["observed_registry"]
    # A negative release must NEVER be presented using a green submit/download CTA.
    if readiness["research_verdict"] != "negative" or card["submission_approved"] is not False:
        raise ValueError("This negative-result site template must not be used to advertise a promoted/selected file")
    rows = score_row("Three raw physics bands", h["comparators"]["physics3"])
    rows += score_row("TDX-1 · fixed new candidate", h)
    rows += score_row("Core 19-band comparator", h["comparators"]["core19"])
    labels = {"file_contract": "TIFF contract & exact hash", "labelled_holdout_evidence": "Pooled holdout & confidence interval",
              "paired_improvement": "Beat same-protocol comparators", "single_feature_leakage_canaries": "Single-feature leakage canaries",
              "count_matched_construction": "Count-matched experiment", "surface_observed_registry": "Surface · observed registry",
              "dots_observed_registry": "Final dots · observed registry", "complete_parallel_registry": "Complete parallel registry",
              "assigned_lane": "External lane-allocation evidence", "comparable_historical_best": "Comparable historical-best rerun",
              "experimental_budget": "Experiment budget", "artifact_identity": "Submission name & short note"}
    gates = ''.join(f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>' for g in readiness["gates"])
    score_table = f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld positive pixels · 95% spatial-bootstrap CI</caption><thead><tr><th>Fixed arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table></div><p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code>; buffered whole-component regional trials. These are catalogue-recovery proxy measurements, <strong>not organizer scores or leaderboard forecasts</strong>. Full protocol and uncertainty: <a href="{RESEARCH}/review.md">scientific review</a>.</p>'''
    home = f'''<section class="intro"><div><p class="eyebrow">DOE GEMS / Research release 01</p><h1>A new TIFF.<br>Not a new claim.</h1><p class="lead">Testing whether magnetic texture offsets across gravity edges reveal concealed faults—without recycling the strongest historical submissions.</p><p class="meta">25 October 2026 <span>·</span> CPU experiment + guard correction <span>·</span> No submission slot used</p></div><a class="text-link" href="{RESEARCH}/preregistration.md">Read the frozen plan ↗</a></section>
{release(card, readiness)}
<section class="evidence-strip" aria-label="Research diagnostics"><article><span>New prediction support</span><strong>{v['emitted_dots']:,} dots</strong><small>Zero positive catalogue pixels</small></article><article><span>Observed novelty</span><strong>{observed["dots"]["registry_entries_compared"]} files compared</strong><small>No duplicate-stop threshold crossed</small></article><article><span>Leakage canaries</span><strong>22 features × 4 folds</strong><small>No AUC alarm above 0.90</small></article></section>
<section class="two-column section"><div><p class="eyebrow">01 / The experiment</p><h2>A useful signal.<br>Not a competitive model yet.</h2><p>Two-scale profile matching added information beyond the three raw physics inputs. But the six-feature candidate lost to the stronger 19-band comparator on identical buffered holdouts. We preserve that negative result instead of spending a weekly slot.</p><p class="fine">The final run uses the corrected 17-pixel physical-support and training guard. One registered engineering correction followed the first negative result; the same inspected folds are not fresh independent confirmation. <a href="{RESEARCH}/correction-v1-retirement.json">Correction &amp; original-run provenance</a>.</p>{score_table}<a class="text-link" href="{RESEARCH}/results.json">All sufficient statistics &amp; canaries ↗</a></div><figure><img src="docs/assets/tdx1-support.png" width="823" height="933" loading="lazy" alt="New TDX-1 prediction dots in dark green over the pale green competition footprint"><figcaption><span class="legend-dot"></span> New TDX-1 support · footprint view, not a geothermal-vent map. Display is downsampled; the downloadable TIFF retains the exact grid.</figcaption></figure></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated inspection</p><h2>Every gate has a state.</h2></div><p>Passed, failed, or unknown.<br>Unknown never means approved.</p></div><div class="table-wrap"><table><thead><tr><th>Gate</th><th>State</th><th>Evidence rule</th></tr></thead><tbody>{gates}</tbody></table></div></section>
<section class="section two-column"><div><p class="eyebrow">03 / Learning from H33</p><h2>Why pruning may have helped.</h2><p>The historical H33 support can be reproduced exactly by removing catalogue-adjacent dots from the GEMSDOE28 base. Under the max-credit kernel, redundant predictions can add penalty without adding coverage. That is a plausible metric mechanism—not proof of hidden fault discovery.</p><p>The owner's <b>0.2778</b> attribution remains an <b>unverified historical claim</b>, not ORGANIZER-CONFIRMED. No live leaderboard value or higher-score forecast is asserted.</p><a class="text-link" href="{RESEARCH}/review.md">Read the source-linked analysis ↗</a></div><div class="note-card"><h3>What makes this file different?</h3><p>New gravity-normal profile features, a newly fitted six-feature HGB, and no historical raster inputs to the model.</p><p>Maximum observed surface Spearman: <b>{observed['surface']['max_spearman']:.6f}</b>.<br>Maximum final-dot overlap within 3 px: <b>{100 * observed['dots']['max_fraction_within_3px']:.4f}%</b>.</p><p class="fine">Similarity diagnostics, not DTI. Coverage includes nine frozen public snapshots and explicitly audited late-arriving TIFFs, not all runs or original surfaces. Global uniqueness remains unverified.</p><a href="{RESEARCH}/registry.json">Pinned registry &amp; exclusions</a> · <a href="{RESEARCH}/registry-parallel-addendum.json">Late-reference addendum</a></div></section>
<section class="section"><p class="eyebrow">04 / Parallel research preserved</p><h2>Other lanes. Separate evidence.</h2><p>These records arrived through concurrent main-branch merges. Their holdouts are different: we do not rank them against TDX-1 or select a weekly submission here. “Promote” in a peer receipt is that lane's reported research verdict, not competition approval.</p><div class="resource-grid"><article><h3>G30-S19 · habitat + EDGE</h3><p>Its lane reports research promotion under an interleaved-component protocol. Not rerun or adjudicated by TDX-1; its conditional uncertainty is not interchangeable with this page's spatial-block CI.</p><a href="docs/research/2026-10-25/lane-g30s19-run-card.json">Peer run card ↗</a></article><article><h3>H-CC1 · contact coincidence</h3><p>Preserved negative record. Its emitted count missed the registered budget; do not reinterpret that comparison as count-matched evidence.</p><a href="docs/research/2026-10-25/h-cc1-run-card.json">Peer run card ↗</a></article><article><h3>Residual-ridge gate</h3><p>Preserved negative and buffered-reach findings. Different geometry and buffer assumptions require a new design, not cross-protocol score selection.</p><a href="docs/research/2026-10-25/run-card-residual-gate.json">Peer run card ↗</a></article></div></section>
<section class="section"><p class="eyebrow">05 / Evidence you can trace</p><h2>Sources, not invented certainty.</h2><div class="resource-grid"><article><h3>Official reference</h3><p>Band meanings, source grid and reference training/export code, freshly read at an immutable commit.</p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb">Organizer notebook ↗</a></article><article><h3>Scientific record</h3><p>Four ranked hypotheses, one fixed method with a recorded guard correction, non-fault confounds and reproducible evidence.</p><a href="{RESEARCH}/review.md">Source-linked review ↗</a></article><article><h3>Current evidence feed</h3><p>Generated from repository receipts. No automated competition scraping or invented current scores.</p><a href="docs/status.json">Status JSON ↗</a><p><a href="{RESEARCH}/owner-claims.csv">119 unverified owner-reported entries ↗</a></p></article></div></section>'''
    guide = f'''<section class="intro"><div><p class="eyebrow">Executive summary / Submission guide</p><h1>The file is valid.<br>The upload is not approved.</h1><p class="lead">Automated project inspection separates a well-formed TIFF from a method worth submitting. This negative result is available for research, not a weekly competition slot.</p></div></section>{release(card, readiness)}
<section class="section"><p class="eyebrow">Current decision</p><h2>Why this file must stay out of the submission queue.</h2>{score_table}<ul class="spaced"><li>The candidate failed to beat the stronger same-protocol comparator.</li><li>The complete parallel-run registry and most original continuous surfaces are unavailable.</li><li>No identifiable external lane assignment or comparable historical-best checkpoint rerun was supplied.</li><li>Current portal limits, eligibility obligations and organizer acceptance are not verified.</li></ul><p>Run <code>python scripts/verify_current_run.py --require-promote</code>: it deliberately exits <b>2</b> for this negative result. There is no human-inspector override and no uploader.</p></section>
<section class="section"><p class="eyebrow">Artifact identity</p><h2>A unique name. A short, honest note.</h2><div class="identity"><label for="submission-name">Research artifact name</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></section>
<section class="section"><p class="eyebrow">Future approved artifact only</p><h2>Exactly how a later submission would work.</h2><ol class="steps"><li><strong>Pass project research gates.</strong><p>The exact artifact must beat the comparable holdout best, clear feature canaries, pass both novelty stages against a complete registry, and pass the shared TIFF validator. Unknown evidence blocks promotion.</p></li><li><strong>Use the separate slot selector.</strong><p>Research promotion is not a slot allocation. Current weekly allowance and required entrant/rules evidence must be established by that separate step. No slot was selected in this session.</p></li><li><strong>Download the selected <code>.tif</code>, not this guide.</strong><p>Use the selected file's one-click download and machine-bound receipt. Do not upload a JSON run card, web page, copied historical reference or this negative candidate. A single-band GeoTIFF is sufficient; no ZIP is needed.</p></li><li><strong>Open the official competition's “New submission” form.</strong><p>Use an authorized account at the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">official GEMS competition</a>. Choose the selected TIFF under “File to submit” and paste that artifact's short note. This repository does not authenticate to DrivenData, upload, or consume weekly slots.</p></li><li><strong>Retain the organizer receipt.</strong><p>Bind the returned submission ID, file hash, result and timestamp before recording an <b>ORGANIZER-CONFIRMED</b> score. A local HOLDOUT-DTI or projection cannot be relabelled as a competition score.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">About the range error</p><h2>No silent clipping.<br>No guessed diagnosis.</h2><p>The exact earlier rejected upload is unknown. This new file was reopened and checked for finite [0,1] predictions inside the template footprint, one float32 band, and exact CRS/shape/transform. NaN nodata outside follows the documented published format.</p><p>A stricter whole-array-finite diagnostic is not the same contract. We do not claim “range-error immunity” or current organizer acceptance.</p><a href="{RESEARCH}/validation.json">Exact validator output ↗</a></div><div class="note-card"><h3>Official review links</h3><ul class="spaced"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; submission format</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Competition data page</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard</a></li></ul><p class="fine">These web hosts are outside this session's network access. Links are for review; no fresh portal verification or live score is implied.</p></div></section>'''
    return {
        ROOT / "index.html": page("New research TIFF & readiness", home, card),
        ROOT / "executive-summary.html": page("Executive submission guide", guide, card, guide=True),
        ROOT / "docs/assets/tdx1-support.png": png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open current research download and submission decision.</a></p></body></html>\n',
    }


def main():
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
