#!/usr/bin/env python3
"""Deterministic Pages release for the current GEMSDOE30 state.

The site presents one holdout-promoted candidate TIFF as a downloadable
research artifact and states explicitly whether it is OK to download and
whether it is OK to submit to the competition. A local format pass and a
holdout result are not organizer acceptance: the file is NOT
organizer-confirmed and no competition slot has been used by this
repository. The authorized entrant decides whether to spend a weekly slot.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
STYLE = "docs/assets/research.css"


def e(value):
    return escape(str(value), quote=True)


def dot_count(tiff: Path) -> int:
    try:
        import rasterio  # type: ignore
        import numpy as np

        with rasterio.open(tiff) as ds:
            data = ds.read(1, masked=False)
        return int(np.count_nonzero(np.asarray(data) > 0.5))
    except Exception:
        return 0


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def page(title: str, content: str, *, active: str = "overview") -> str:
    parts = []
    for key, url, label in (
        ("overview", "index.html", "Overview"),
        ("guide", "executive-summary.html", "Submission guide"),
        ("research", "experiment-review.html", "Research"),
    ):
        marker = " aria-current=\"page\"" if active == key else ""
        parts.append(f'<a href="{url}"{marker}>{label}</a>')
    nav = "".join(parts)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMSDOE30 DOE GEMS fault-discovery: holdout-promoted candidate submission TIF, download and submission guide.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a><nav aria-label="Main navigation">{nav}<a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. A valid file is not a competition approval.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="docs/current-run.json">Current run pointer</a><a href="https://www.drivendata.org/competitions/306/competitions-doe-gems/leaderboard/" rel="nofollow">Official leaderboard ↗</a></div>
<p class="fine">Repository evidence, not a live leaderboard. No competition slot selected or used by this repository. Local validation and holdout results are not organizer acceptance.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>'''


def hero(run_card: dict) -> str:
    submission_file = run_card["submission_file"]
    sha = run_card["submission_sha256"]
    name = run_card["submission_name"]
    note = run_card["submission_note"]
    nlen = run_card["submission_note_length"]
    tiff_path = ROOT / submission_file
    size = tiff_path.stat().st_size
    count = dot_count(tiff_path)
    return f'''<section class="intro"><div>
<p class="eyebrow">Submission artifact · ready to download</p>
<h1>One GEMSDOE30 TIF.<br>Clear about submission.</h1>
<p class="lead">A holdout-promoted, format-valid single-band GeoTIFF is published below for download.
It is <strong>OK to download</strong> as a research artifact. It is <strong>not OK to treat as cleared to submit</strong>:
the result is HOLDOUT-DTI (a catalogue-proxy holdout), it is <strong>not ORGANIZER-CONFIRMED</strong>, and no
organizer receipt or competition score exists for it.</p>
<p class="meta">25 October 2026 <span>·</span> One holdout-validated candidate <span>·</span> No weekly slot used</p>
</div></section>

<section class="release" aria-labelledby="download-title">
<div class="release-heading"><span class="pill good">FORMAT-VALID · LOCAL CONTRACT PASSED</span><span class="pill caution">PROMOTED ON HOLDOUT · PROXY ONLY</span><span class="pill caution">NOT ORGANIZER-CONFIRMED</span></div>
<h2 id="download-title">Download the submission TIF</h2>
<p><strong>File:</strong> <code>{e(Path(submission_file).name)}</code> <span>({size / 1024 / 1024:.2f} MiB)</span> <span>· <strong>{count:,} binary dots</strong> at one kernel radius (300 m), all off-catalogue</span></p>
<div class="actions"><a class="button" href="{e(submission_file)}" download>↓ Download submission TIF <span>click to save .tif</span></a><a class="button secondary" href="{e(submission_file[:-4] + '.json')}" download>Provenance sidecar (.json)</a></div>
<p class="filename">{e(Path(submission_file).name)}</p>
<details><summary>File identity &amp; current validation</summary>
<dl>
<dt>SHA-256</dt><dd><code>{e(sha)}</code></dd>
<dt>Contract</dt><dd>One float32 band · EPSG:32611 · 3,730 × 3,292 · exact template transform · finite [0, 1] inside the footprint · NaN nodata outside · 0 NaN inside the footprint</dd>
<dt>Local validation</dt><dd>All 11 published-format checks passed (finite [0, 1] inside footprint; NaN outside; CRS/shape/transform match the sample template). Receipt: <a href="{e(run_card['validation_receipt'])}">nearslay-submission-validation.json</a></dd>
<dt>Holdout result (HOLDOUT-DTI · not a score)</dt><dd>Screen seed 31: Δ +0.0654, 95% CI [0.0570, 0.0743], 4/4 quadrants, 20,870 withheld positives · Confirmation seed 41: Δ +0.0679, 95% CI [0.0590, 0.0772], 4/4 quadrants, 20,247 withheld positives · Evaluator component-holdout-v3-blockstats-20261025, triangular 300 m kernel, alpha 0.2 / beta 0.8</dd>
<dt>Uniqueness vs registry</dt><dd>Max Spearman rho 0.070 (limit 0.90); max dot overlap 68.1% within 3 px of any one local reference raster (limit 70%). No lane collision vs the 21 locally available registry rasters.</dd>
<dt>Verdict</dt><dd><strong>Promote on holdout.</strong> Downloadable research artifact only. Not ORGANIZER-CONFIRMED — no organizer receipt, ID, hash, or score exists for this file. The authorized entrant decides whether to spend a weekly submission slot.</dd>
</dl>
</details>
</section>

<section class="section"><div class="identity">
<label for="submission-name">Submission name (copy for “File to submit”)</label>
<input id="submission-name" value="{e(name)}" readonly>
<button class="copy-button" type="button" data-copy="submission-name">Copy name</button>
<label for="submission-note">Submission note · {nlen} / 140 characters (paste into “Note (optional)”)</label>
<textarea id="submission-note" readonly rows="3">{e(note)}</textarea>
<button class="copy-button" type="button" data-copy="submission-note">Copy note</button>
<p id="copy-status" role="status" aria-live="polite"></p>
</div>
</section>'''


def how_to_submit() -> str:
    return f'''<section class="section"><p class="eyebrow">Exactly how to submit</p><h2>“New submission” on the official competition</h2>
<ol class="steps">
<li><strong>Download the TIF.</strong><p>Click the download link above and save <code>{e(Path(run_card()["submission_file"]).name)}</code>. Do not edit, clip, resize, or re-encode it: edits change the hash and void the validation receipt.</p></li>
<li><strong>Open the official form.</strong><p>In an authorized DrivenData account on the <a href="https://www.drivendata.org/competitions/306/competitions-doe-gems/">official competition page</a>, go to “New submission” → “File to submit”.</p></li>
<li><strong>Attach the file.</strong><p>Choose the single-band GeoTIFF (.tif). The repository does not authenticate, upload, or consume a weekly slot; that step is yours, in your account.</p></li>
<li><strong>Paste the note.</strong><p>Paste the submission note copied above into “Note (optional)” — it helps tell submissions apart (e.g. “clustering with k=25”).</p></li>
<li><strong>Keep the receipt.</strong><p>Record the submission ID, returned score, file SHA-256 and timestamp. Only a submission-page receipt is ORGANIZER-CONFIRMED; HOLDOUT-DTI and projections are never written as scores.</p></li>
</ol>
</section>

<section class="section two-column">
<div>
<p class="eyebrow">Is it OK to download and submit?</p>
<h3>Download: yes · Submit: not confirmed</h3>
<ul class="spaced">
<li><strong>Download:</strong> yes — this page links the exact validated bytes and records the SHA-256.</li>
<li><strong>Submit:</strong> not established. The file passed the local format contract and the holdout gate, but holdout results are a catalogue proxy (IR-30-017), not the private expert-new test labels. No DrivenData submission receipt exists, so nothing here is ORGANIZER-CONFIRMED.</li>
<li><strong>Range error:</strong> the file is finite [0, 1] inside the footprint with NaN nodata outside, matching the published GEMS format; the historical “Predicted values must be in range [0, 1]” rejection is diagnosed (IR-30-044) and this file avoids both known causes (in-footprint NaN; whole-array out-of-range values). Local validation does not prove portal acceptance.</li>
</ul>
</div>
<div class="note-card"><h3>Official review links</h3>
<ul class="spaced">
<li><a href="https://www.drivendata.org/competitions/306/competitions-doe-gems/page/967/">Problem &amp; submission format</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules PDF (NLR, September 2026)</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competitions-doe-gems/data/">Competition data page</a></li>
<li><a href="https://www.drivendata.org/competitions/306/competitions-doe-gems/leaderboard/" rel="nofollow">Official leaderboard</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">DrivenData reference solution</a></li>
<li><a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS submission 1391</a></li>
</ul>
<p class="fine">External hosts are outside this session's network access. Links are for manual review, not fresh verification.</p></div>
</section>'''


def run_card() -> dict:
    return load_json(ROOT / "docs/research/nearslay-run-card.json")


def experiments_section() -> str:
    rc = run_card()
    h = rc["holdout"]
    return f'''<section class="section"><p class="eyebrow">Experiments run this session (cap: 3 / 2 hours)</p>
<h2>Two holdouts, one promoted, one negative</h2>
<div class="table-wrap"><table>
<caption>HOLDOUT-DTI — catalogue-proxy component holdout, not competition scores</caption>
<thead><tr><th>Experiment</th><th>Hypothesis</th><th>Pooled DTI vs control</th><th>95% CI of delta</th><th>Quadrants</th><th>Withheld positives</th><th>Verdict</th></tr></thead>
<tbody>
<tr><th scope="row">1 · H-VENT volcanic-vent feeder alignment</th><td>Volcanic vents mark uncatalogued feeder fissures</td><td>0.0006 vs 0.0187 (Δ −0.0181)</td><td>[−0.0192, −0.0168]</td><td>0/4</td><td>20,870 / 20,247</td><td><span class="gate failed">negative</span></td></tr>
<tr><th scope="row">2 · H-NEARSPLAY near-splay annulus (this submission)</th><td>Off-catalogue splays 300 m–1.5 km from mapped traces</td><td>0.0850 / 0.0879 vs ~0.0198 (Δ +0.066)</td><td>[0.0570, 0.0743] / [0.0590, 0.0772]</td><td>4/4 / 4/4</td><td>20,870 / 20,247</td><td><span class="gate passed">promoted on holdout</span></td></tr>
</tbody>
</table></div>
<p class="fine">Both runs: evaluator component-holdout-v3-blockstats-20261025, buffered-quadrant whole-components,
alpha 0.2 / beta 0.8, triangular 300 m kernel, paired spatial-block 95% CI, 2000 replicates. Full reports:
docs/research/h-nearsplay-holdout.json and docs/research/h-vent-feeder-holdout.json.</p>
</section>

<section class="section"><p class="eyebrow">3–5 candidate hypotheses not previously tried</p>
<h2>Ranked geological hypotheses</h2>
<div class="table-wrap"><table>
<thead><tr><th>Rank</th><th>Hypothesis · layers · signature</th><th>Why it targets uncatalogued faults</th><th>Differs from prior work</th><th>Prior ΔDTI / cost</th><th>Official source</th><th>Status</th></tr></thead>
<tbody>
<tr><th scope="row">1</th><td><strong>H-NEARSPLAY</strong> — near-splay annulus, 300 m–1.5 km off-catalogue dots, inner-edge weighted · catalogue geometry for zoning/masking only · dots at one kernel radius (300 m)</td><td>Unmapped splays/stepovers of mapped systems sit just outside catalogue traces; newly mapped geometry of an existing system is scorable (DrivenData thread 11536)</td><td>No inspected artifact emits purely from this annulus; d2.8 spreads uniformly off-catalogue (median distance 1,500 m)</td><td>+0.005…+0.020 / low</td><td>Catalogue + template (on disk)</td><td>Holdout-promoted; this submission</td></tr>
<tr><th scope="row">2</th><td><strong>H-VENT</strong> — volcanic-vent feeder alignment · GDR 1391 Quaternary volcanics (derived_gdr_volcanics_100m_u8.tif, CC BY 4.0) · vents dilated one kernel radius</td><td>0/21 inventoried vents within 300 m of a catalogue trace; feeder fissures are structurally absent from a surface-expression catalogue</td><td>No repository holdout or inspected page uses volcanic vents at all (H-32-02 was registered, never run here)</td><td>+0.001…+0.010 / low</td><td><a href="https://gdr.openei.org/submissions/1391">GDR 1391</a> (on disk)</td><td>Negative on proxy (deliverable)</td></tr>
<tr><th scope="row">3</th><td><strong>H-34-01</strong> — substrate-concealment prior from USGS SGMC map-unit polygons × relief bands · observability weighting, not an evidence field</td><td>Faults under basin fill/lake cover are missing from every surface catalogue; prior re-weights where to spend existing evidence</td><td>Every repo hypothesis used an evidence field; none modelled the selection process that produced the labels</td><td>+0.002…+0.015 / low</td><td><a href="https://mrdata.usgs.gov/geology/state/">USGS SGMC NV/CA</a> (hash-verified, on disk)</td><td>Registered; not run</td></tr>
<tr><th scope="row">4</th><td><strong>H-34-02</strong> — potential-field depth lineaments · tilt derivative / Euler deconvolution of GeoDAWN magnetic grids · retain sources below ~0.5–1 km depth</td><td>A buried magnetic source with no surface rupture is invisible to a surface catalogue by construction</td><td>Prior work used magnetic values or horizontal gradients; none inverts for source depth or filters lineaments by it</td><td>+0.002…+0.012 / medium</td><td><a href="https://doi.org/10.5066/P93LGLVQ">USGS GeoDAWN, DOI 10.5066/P93LGLVQ</a></td><td>Registered; not run</td></tr>
<tr><th scope="row">5</th><td><strong>H-34-03</strong> — drainage χ/ksn disequilibrium · USGS NHD flowlines + 3DEP DEM · basin-integrated fluvial-strain transform</td><td>Fluvial networks record deformation where scarps are eroded or buried; NHD/3DEP are independent of the fault-mapping programme</td><td>No repository work computes χ or ksn; prior hydrology ideas were qualitative only</td><td>+0.002…+0.010 / high (full-ROI transfer unverified)</td><td><a href="https://tnmaccess.nationalmap.gov/api/v1/products?datasets=National%20Hydrography%20Dataset%20(NHD)%20Best%20Resolution&bbox=-119,38.5,-118.5,39">USGS TNM API</a> (coverage unverified)</td><td>Registered; blocked on data</td></tr>
</tbody>
</table></div>
<p class="fine">Planning priors are experiment ranges, not forecasts or competition-score predictions. No candidate consumes a weekly slot without a holdout pass.</p>
</section>

<section class="section"><p class="eyebrow">Integrity</p>
<h2>Labels, limits and what is not claimed</h2>
<ul class="spaced">
<li><strong>HOLDOUT-DTI vs ORGANIZER-CONFIRMED.</strong> Every number above is HOLDOUT-DTI (evaluator version, withheld positives, 95% CI) or a local format check. Nothing here is ORGANIZER-CONFIRMED: no submission receipt, ID, or score exists for this file.</li>
<li><strong>No score claims.</strong> The leaderboard values quoted elsewhere (0.3195 public snapshot; reported 0.2778 for GEMSDOE32 H33) are unattributed to exact file hashes and are treated as unverified historical claims.</li>
<li><strong>No slot used.</strong> This repository does not authenticate to DrivenData, upload files, or consume submission slots (IR-30-007). The authorized entrant decides whether to submit.</li>
<li><strong>Data provenance.</strong> Rasters restored from SHA-256-pinned owner mirrors; not organizer-authenticated (IR-30-001).</li>
</ul>
</section>'''


def build() -> dict[str, str]:
    rc = run_card()
    home = hero(rc) + how_to_submit() + experiments_section()
    guide = hero(rc) + how_to_submit()
    return {
        ROOT / "index.html": page("Submission artifact · GEMSDOE30", home, active="overview"),
        ROOT / "executive-summary.html": page("Executive submission guide · GEMSDOE30", guide, active="guide"),
        ROOT / "experiment-review.html": page("Experiments & hypotheses · GEMSDOE30", experiments_section(), active="research"),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open the submission artifact and download guide.</a></p></body></html>\n',
    }


def main() -> int:
    for path, content in build().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode())
    print("Built GEMSDOE30 submission Pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
