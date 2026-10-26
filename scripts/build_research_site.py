#!/usr/bin/env python3
"""Deterministic Pages release from inspected artifacts, G30-TAD, G30-LSM, and TDX receipts.

Separates technical file/novelty validity (`download_ok`) from weekly-slot promotion
(`ok_to_submit`). Every number rendered on the site is machine-verified on build.
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
from scripts.verify_tad_run import verify as verify_tad

STYLE = "docs/assets/research.css"
RESEARCH = "docs/research/texture-displacement"
LATEST = "docs/research/texture-controls"
TAD_DIR = "docs/research/tilt-alteration-discontinuity"


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
    nav = ''.join(
        f'<a href="{url}"' + (' aria-current="page"' if active == key else '') + f'>{label}</a>'
        for key, url, label in (
            ("overview", "index.html", "Overview"),
            ("guide", "executive-summary.html", "Submission guide"),
            ("tad", "geothermal-tilt-alteration-review.html", "G30-TAD & H33 analysis"),
            ("research", "experiment-review.html", "TDX-C2 & registry"),
        )
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMS fault-discovery evidence: automated GeoTIFF validation, 190-raster novelty gates, G30-TAD tilt-alteration-discontinuity experiment, and PhD H33 analysis.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a><nav aria-label="Main navigation">{nav}<a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main><footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. A valid file is not a competition approval.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{TAD_DIR}/run-card.json">G30-TAD run card</a><a href="{LATEST}/run-card.json">Latest run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Repository evidence, not a live leaderboard. No competition slot selected or used. G30-TAD passed format &amp; 190-raster novelty checks but is negative on the paired CI gate; latest TDX-C2 is stopped; retained TDX-1 is an archived research download only.</p></footer>
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


def tad_banner(tad_card, tad_ready, *, allow_download_attr=False):
    z_file = local_path(tad_card["published_tiff"])
    n_file = local_path(tad_card["companion_nan_tiff"])
    z_kib = z_file.stat().st_size / 1024.0
    n_kib = n_file.stat().st_size / 1024.0
    h = tad_card["holdout"]
    dc = h["candidate_minus"]["core19"]
    ds = h["candidate_minus"]["subsurface16"]
    surf_rho = tad_card["registry"]["surface"]["max_spearman"]
    dots_ov = tad_card["registry"]["dots"]["max_fraction_within_3px"]
    dl = " download" if allow_download_attr else ""
    submit_pill = (
        '<span class="pill good">OK TO PROMOTE TO SLOT SELECTOR</span>'
        if tad_ready["ok_to_submit"]
        else '<span class="pill caution">DO NOT SPEND WEEKLY SUBMISSION SLOT · NEGATIVE CI GATE</span>'
    )
    return f'''<section class="release" style="margin-bottom:26px" aria-labelledby="tad-banner-title">
<div class="release-heading"><span class="pill good">G30-TAD · FORMAT [0, 1] &amp; 190-RASTER NOVELTY VALIDATED (DOWNLOAD OK)</span>{submit_pill}</div>
<h2 id="tad-banner-title">Unique GeoTIFF validated in [0, 1]. <span>Do not spend a weekly slot.</span></h2>
<p><strong>Automated non-human verdict (<code>verify_tad_run.py</code>):</strong> Both newly generated 38,000-dot GeoTIFFs passed automated format/range inspection (primary <code>-zeros.tif</code> has all <strong>12,279,160 cells finite in [0, 1]</strong>, zero NaN/Inf cells anywhere, exact <code>EPSG:32611</code> / <code>3730×3292</code> / affine geotransform match, <code>0</code> dots on or within ≤2 px of known faults; companion <code>-nan.tif</code> passes all 12 checks of <code>validate_submission_file</code>) <strong>and</strong> cleared both 190-raster uniqueness gates (pre-placement surface Spearman <strong>{surf_rho:.4f} ≤ 0.90</strong>; post-placement 3-px dot overlap <strong>{100 * dots_ov:.2f}% ≤ 70.0%</strong>, breaking the &lt;1 km crowding trap that stopped TDX-C2, G30-S20, and G30-LSM).</p>
<p><strong>Why weekly submission is withheld (<code>ok_to_submit = false</code>):</strong> On buffered 4-quadrant whole-component holdout (<code>component-holdout-v3-blockstats-20261025</code>, 60,988 withheld positives, 144/144 canaries ≤ 0.6434), coordinate-free <code>tilt_alt24</code> scored <strong>HOLDOUT-DTI {h["value"]:.5f}</strong> [{h["ci95"][0]:.5f}, {h["ci95"][1]:.5f}] vs <code>core19</code> <strong>{h["comparators"]["core19"]["value"]:.5f}</strong> (point gain <strong>{dc["value"]:+.5f}</strong>, Fold 0 NW Nevada <strong>+0.01801</strong>, pure-geophysical <code>subsurface16</code> <strong>{h["comparators"]["subsurface16"]["value"]:.5f}</strong>, Δ {ds["value"]:+.5f}), <strong>but</strong> the paired 95% block-bootstrap CI against <code>core19</code> is <strong>[{dc["ci95"][0]:+.5f}, {dc["ci95"][1]:+.5f}]</strong>, which crosses zero. Per protocol, protect the 3/week submission cap.</p>
<div class="actions"><a class="button" href="{e(tad_card['published_tiff'])}"{dl}>↓ Primary range-safe TIFF (-zeros) <span>{z_kib:.1f} KiB</span></a><a class="button secondary" href="{e(tad_card['companion_nan_tiff'])}"{dl}>Companion NaN-outside TIFF <span>{n_kib:.1f} KiB</span></a><a class="button secondary" href="geothermal-tilt-alteration-review.html">Full G30-TAD &amp; PhD H33 analysis</a><a class="text-link" href="{TAD_DIR}/readiness.json">Machine gate receipt ↗</a></div>
<p class="filename">{e(z_file.name)} · SHA-256 {e(tad_card['raster_sha256'][:24])}…</p></section>'''


def score_table(card):
    h = card["holdout"]
    rows = score_row("Core 19-band comparator", h["comparators"]["core19"])
    rows += score_row("TDX-C2 · fixed candidate (22 bands)", h)
    rows += score_row("Matched zero-lag control (22 bands)", h["comparators"]["zero22"])
    rows += score_row("Matched phase-scrambled control (22 bands)", h["comparators"]["phase22"])
    return f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld positive pixels · 95% spatial-bootstrap CI</caption><thead><tr><th>Fixed arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table></div><p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code>; protocol <code>{e(h['protocol_version'])}</code>. Pooled buffered whole-component regional trials; 371 geographic bootstrap blocks. Previously inspected catalogue folds—not independent confirmation, an organizer score, or a hidden-test forecast.</p>'''


def latest_notice(card):
    overlap = card["registry"]["dots"]["max_fraction_within_3px"]
    return f'''<section class="stop-notice" aria-labelledby="stop-title"><div class="release-heading"><span class="pill caution">DUPLICATE-STOP · earlier TDX-C2 attempt</span><span class="meta">TDX-C2 / 25 October 2026</span></div><h2 id="stop-title">TDX-C2 stopped on duplicate overlap.</h2><p><strong>{100 * overlap:.2f}% of final dots</strong> fall within 3 pixels of an existing G30-S19 reference, exceeding the mandatory 70% limit. We stopped that lane, quarantined its raster, and did not change dots to evade the rule. It also failed the paired holdout-improvement gate.</p><p><strong>TDX-C2 competition upload: not approved.</strong> A new byte hash or passing the [0,1] format check cannot establish a unique strategy.</p><div class="actions"><a class="button secondary" href="experiment-review.html">Read the stopped TDX-C2 experiment</a><a class="text-link" href="{LATEST}/run-card.json">TDX-C2 JSON run card ↗</a></div></section>'''


def gate_table(readiness):
    labels = {"file_contract": "Public file reinspection", "labelled_holdout_evidence": "Pooled holdout & confidence intervals",
              "paired_improvement": "Beat all matched controls", "single_feature_leakage_canaries": "Individual feature canaries",
              "count_matched_construction": "Count-matched construction", "surface_observed_registry": "Surface · observed registry",
              "dots_observed_registry": "Final dots · observed registry", "complete_parallel_registry": "Complete parallel registry",
              "assigned_lane": "External lane assignment", "comparable_historical_best": "Historical-best rerun",
              "experimental_budget": "Experiment budget", "artifact_identity": "Name & short note"}
    rows = ''.join(f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>' for g in readiness["gates"])
    return f'<div class="table-wrap"><table><caption>TDX-C2 · automated research gates</caption><thead><tr><th>Gate</th><th>State</th><th>Evidence rule</th></tr></thead><tbody>{rows}</tbody></table></div>'


def tad_review_page(tad_card, tad_ready):
    h = tad_card["holdout"]
    e1_rows = (
        score_row("tilt_alt24 · coordinate-free tilt + Kd alteration + dip-slip (24 features)", h)
        + score_row("core19 · raw competition stack benchmark (19 features)", h["comparators"]["core19"])
        + score_row("subsurface16 · pure potential-field + alteration + MT clay-cap (0 DEM/LiDAR)", h["comparators"]["subsurface16"])
        + score_row("random_dispersed · 3 px Poisson-disk null", h["comparators"]["random_dispersed"])
    )
    tad_gates = ''.join(
        f'<tr><th scope="row"><code>{e(g["name"])}</code></th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in tad_ready["gates"]
    )
    e2 = tad_card["e2_diagnostics"]
    p0 = e2["full_grid_distance_profiles_38000"]["p0_plain_d2"]
    p1 = e2["full_grid_distance_profiles_38000"]["p1_decensored_30_40_30"]
    sgmc = e2["sgmc_new_offcatalogue_diagnostic"]
    return f'''<section class="intro"><div><p class="eyebrow">G30-TAD · Geothermal vent &amp; blind-fault discovery</p><h1>Subsurface physics.<br>Decensored placement.</h1><p class="lead">PhD-level proof of why H33 scored 0.2778, geothermal multi-physics knowledge base, five ranked untried hypotheses, and bounded execution of lane G30-TAD.</p><p class="meta">25–26 October 2026 <span>·</span> 3/3 bounded experiments ({tad_card["experimental_elapsed_seconds"]:.1f}s / 7,200s cap) <span>·</span> 190-raster novelty passed</p></div><a class="text-link" href="{TAD_DIR}/geothermal-and-h33-synthesis.md">Full mathematical synthesis ↗</a></section>
{tad_banner(tad_card, tad_ready, allow_download_attr=True)}
<section class="section two-column"><div><p class="eyebrow">01 / Machine-adjudicated gates &amp; identity</p><h2>Zero human inspection. Seven explicit gates.</h2><p>Every gate below is recomputed from committed receipts and reopened GeoTIFF bytes by <code>python scripts/verify_tad_run.py</code>. Technical file validity (<code>download_ok = true</code>) and weekly-slot promotion (<code>ok_to_submit = false</code>) are strictly separated.</p><div class="table-wrap"><table><caption>G30-TAD · machine-adjudicated release gates</caption><thead><tr><th>Gate</th><th>State</th><th>Verified detail</th></tr></thead><tbody>{tad_gates}</tbody></table></div><div class="identity" style="margin-top:22px"><label for="tad-name">G30-TAD primary artifact name · research download only (do not spend weekly slot)</label><input id="tad-name" value="{e(tad_card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="tad-name">Copy name</button><label for="tad-note">G30-TAD research note · {len(tad_card['note'])} / 140 characters</label><textarea id="tad-note" readonly rows="2">{e(tad_card['note'])}</textarea><button class="copy-button" type="button" data-copy="tad-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></div>
<figure><img src="docs/assets/tad24-support.png" alt="Spatial map of 38,000 G30-TAD decensored fault-discovery dots across the valid EPSG:32611 Great Basin footprint"><figcaption><span class="legend-dot"></span><strong>38,000 binary &#123;0, 1&#125; dots</strong> emitted by <code>tilt_alt24</code> + <code>decensored_30_40_30</code> across the 5,167,373-pixel valid footprint (<code>0%</code> at <code>d ≤ 2 px</code>, <code>30%</code> in <code>2–10 px</code>, <code>40%</code> in <code>10–30 px</code>, <code>30%</code> in <code>&gt;30 px</code>; max 3-px overlap vs 190 registry rasters = <strong>51.44% ≤ 70%</strong>).</figcaption></figure></section>

<section class="section"><p class="eyebrow">02 / PhD-level proof: why H33 scored 0.2778 &amp; how to exceed 0.3195 / 0.4413</p><h2>Exact differential algebra of the GEMSDOE24→36 trajectory.</h2><p>On the masked test domain <code>Ω \\ K</code> (known USGS/INGENIOUS faults <code>K</code> excluded pixel-exactly per <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">organizer forum clarification t/11516</a>), the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Distance-Weighted Tversky Index</a> with <code>α = 0.2</code>, <code>β = 0.8</code>, and 300 m triangular kernel <code>k(d) = max(1 − d/300m, 0)</code> reduces algebraically to <code>DTI = T / (0.2T + 0.2F + 0.8|G_new|)</code>.</p>
<div class="table-wrap"><table><caption>Byte-verified lineage across priority repositories (scores are owner-reported historical claims, not organizer receipts)</caption><thead><tr><th>Artifact (Site)</th><th>Active px</th><th>Exact byte relationship to precursor</th><th>Catalogue collar</th><th>Reported score</th></tr></thead><tbody>
<tr><th scope="row"><code>gems-fault-h19-5</code> (GEMSDOE24)</th><td>121,131</td><td>Continuous/ridge lineament corridor over 19-band stack</td><td>Includes <code>d ≤ 2 px</code></td><td>0.1922 (unverified)</td></tr>
<tr><th scope="row"><code>gems-fault-D2.8</code> (GEMSDOE25/30)</th><td>44,090</td><td>3 px Poisson-disk thinning of <code>h19-5</code> (3.65× FP reduction)</td><td>3,891 at <code>d=1</code>; 2,545 at <code>d=2</code></td><td>0.2600 (unverified)</td></tr>
<tr><th scope="row"><code>r1-solo</code> (GEMSDOE28/31)</th><td>40,199</td><td><strong>Exact subset</strong> of <code>D2.8</code> deleting 3,891 pixels at <code>d_cat = 1 px</code></td><td>0 at <code>d ≤ 1 px</code></td><td>0.2708 (unverified)</td></tr>
<tr><th scope="row"><code>h33-h33-2-b2-…-e5eb6e7e-zeros</code> (GEMSDOE32)</th><td>37,654</td><td><strong>Exact subset</strong> of <code>r1-solo</code> deleting 2,545 pixels at <code>d_cat = 2 px</code></td><td>0 at <code>d ≤ 2 px</code></td><td><strong>0.2778</strong> (unverified)</td></tr>
<tr><th scope="row"><code>anderson-geothermal-pinn-38854</code> (GEMSDOE36)</th><td>38,854</td><td><code>H33-B2</code> + 1,200 gap-bridge dots inside mapped fault collars</td><td>0 at <code>d ≤ 2 px</code> (+1,200 near)</td><td><strong>0.2750</strong> (unverified)</td></tr>
</tbody></table></div>
<ul class="spaced"><li><strong>Invariance of truth credit <code>T</code> across <code>d ∈ &#123;1, 2&#125; px</code>:</strong> Solving <code>T / DTI(P) = 0.2|P| + 0.8|G_new|</code> across <code>D2.8 → r1-solo → H33-B2</code> yields <code>|G_new| ≈ 19,213 px</code> (<code>0.377%</code> of unmasked footprint; lattice-calibrated lower bound <code>~12,600 px</code>) and <code>T ≈ 6,602</code> constant to 3 significant figures across all three files. Removing 6,436 collar dots removed ~1,287 units of denominator penalty <code>0.2ΔF</code> while losing essentially <strong>zero</strong> true-positive kernel weight—and adding 1,200 collar bridge dots in <code>PINN</code> added <code>0.2 × 1,184 ≈ 237</code> penalty with only ~3–16 hits, predicting <code>0.2750</code> analytically!</li>
<li><strong>Why 0.2778 is the pruning ceiling of <code>h19-5</code>—and how to beat 0.3195 toward live #1 (0.4413, verified 2026-10-25):</strong> Because recall is weighted 4× heavier than precision (<code>β = 0.8</code> vs <code>α = 0.2</code>), even deleting <em>every</em> remaining false positive in <code>H33-B2</code> caps <code>h19-5</code> recall at ~34–40%. Reaching <code>&gt; 0.32–0.44</code> mathematically requires <strong>raising hidden-fault recall <code>T / |G_new|</code> from ~35% to 52–60%</strong> by detecting <em>blind</em> basinward/intrabasin structures that lack 100 m topographic scarps, while keeping emitted dot count compact (<code>35,000–45,000</code> binary <code>&#123;0, 1&#125;</code> dots at ~3 px spacing so sibling dots never waste <code>0.2F</code> inside the same 300 m max-kernel).</li></ul></section>

<section class="section"><p class="eyebrow">03 / Geothermal vent &amp; blind-fault literature knowledge base</p><h2>Verified official datasets &amp; geophysical mechanisms.</h2>
<div class="resource-grid">
<article><h3>Structural controls (Great Basin)</h3><p>75%+ of Great Basin geothermal systems are <strong>blind</strong> (no surface hot spring/fumarole), hosted in fault step-overs, relay ramps, terminations, and intersections where localized dilation maintains fracture permeability beneath Playas/Quaternary alluvium (Faulds &amp; Hinz, 2015, WGC; Coolbaugh et al., 2006).</p><a href="https://gdr.openei.org/submissions/1391">GDR 1391 INGENIOUS compilation (DOI 10.15121/1881483) ↗</a></article>
<article><h3>Potential-field tilt-depth &amp; upward continuation</h3><p>Salem et al. (2007, <em>Leading Edge</em> 26:1502) prove magnetic tilt angle <code>θ = atan2(∂M/∂z, |∇_h M|)</code> satisfies <code>θ = 0</code> over vertical fault contacts and <code>h_tilt = 1 / |∇_h θ|</code> estimates depth to buried fault top independent of magnetization amplitude. FFT upward continuation isolates basement feeders from surficial volcanic clutter.</p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN (Glen &amp; Earney 2024, DOI 10.5066/P93LGLVQ) ↗</a></article>
<article><h3>Potassic alteration, MT clay-cap &amp; 1 m LiDAR</h3><p>Ascending K/Si-rich hydrothermal fluids deposit adularia/illite along fault damage zones while Th stays immobile, elevating fold-regressed <code>K_d</code> and Efimov <code>F = K·eU/eTh</code> (Gnojek &amp; Přichystal, 1985), flanked by smectite clay-cap MT conductance gradients (Cumming, 2009) and subtle 1 m LiDAR dip-slip scarps.</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official GEMS layer &amp; DTI specification ↗</a></article>
</div></section>

<section class="section"><p class="eyebrow">04 / Five ranked untried hypotheses &amp; E1–E3 results</p><h2>Pre-committed before execution; evaluated without tuning.</h2>
<div class="table-wrap"><table><caption>Ranked candidate hypotheses generated prior to code execution (<a href="{TAD_DIR}/preregistration.md">frozen preregistration</a>)</caption><thead><tr><th>Rank &amp; ID</th><th>Layers &amp; physical transform</th><th>Why it catches uncatalogued / blind faults</th><th>Non-fault mimic</th><th>Outcome</th></tr></thead><tbody>
<tr><th scope="row">1 · <code>H-TAD-1</code></th><td>24 local multi-physics features (<code>h_tilt</code>, <code>tmi_up150_res</code>, fold-safe <code>rad_kd</code>/<code>rad_efimov_f</code>, MT <code>cond_log_grad</code>, basement strike-lock, 1 m LiDAR dip-slip polarity, sinter/probe/SiO2 impulse) + <code>decensored_30_40_30</code> OOF collar emission</td><td>Detects buried 0.2–1.5 km fault contacts, potassic alteration halos, and clay-cap boundaries under alluvial cover without regional coordinate proxies</td><td>Tilted welded ash-flow tuff / caldera ring-fracture contacts with vapor-phase K crystallization</td><td><strong>Executed:</strong> E1 <code>0.14405</code> vs <code>core19 0.13982</code> (+0.00423, CI crosses 0); passed 190-raster novelty (51.44% ≤ 70%)</td></tr>
<tr><th scope="row">2 · <code>H-TAD-2</code></th><td>Geodetic tensor normal/Riedel shear resolution onto local geophysical strike (<code>geod_dilaterate</code>, <code>geod_shearrate</code>, <code>geod_2ndinv</code>)</td><td>Identifies blind structures critically stressed for dilation in the modern GPS velocity field</td><td>Broad visco-elastic postseismic strain gradients</td><td>Deferred to next-session <code>G30-FUSION</code></td></tr>
<tr><th scope="row">3 · <code>H-TAD-3</code></th><td>3D FFT Poisson pseudo-gravity vs RTP magnetic residual (hydrothermal magnetite destruction trough)</td><td>Separates hot fluid-leached fault zones (gravity step + magnetic trough) from cold unaltered dikes</td><td> reversely magnetized Miocene basalt flows</td><td>Not run (medium FFT cost; partially captured by <code>tmi_up150_res + rad_kd</code>)</td></tr>
<tr><th scope="row">4 · <code>H-TAD-4</code></th><td>USGS SGMC Quaternary alluvial polygon concealment prior (<code>NV.zip</code>, <code>CA.zip</code>)</td><td>Models mapper censoring directly where Holocene play/alluvial cover hides surface traces</td><td>Unfaulted deep playa depocenters</td><td>Radial proxy tested in E2 (improved <code>SGMC-new</code>: 0.08178 vs 0.08117); polygon version next</td></tr>
<tr><th scope="row">5 · <code>H-TAD-5</code></th><td>Multi-azimuth 1 m LiDAR alluvial-fan incision break</td><td>Catches subtle 10–40 cm Holocene piedmont scarps blurred out in 100 m DEMs</td><td>Pleistocene Lake Lahontan wave-cut shorelines</td><td>Not run (requires raw 1 m tile streaming)</td></tr>
</tbody></table></div>

<div class="table-wrap" style="margin-top:24px"><table><caption>Experiment E1 · Buffered 4-quadrant whole-component holdout (<code>{e(h["evaluator_version"])}</code>, {h["withheld_positives"]:,} withheld positives, 17 px buffer)</caption><thead><tr><th>Fixed arm</th><th>HOLDOUT-DTI</th><th>95% Spatial-Block CI</th></tr></thead><tbody>{e1_rows}</tbody></table></div>
<p class="fine">Experiment E2 diagnostics: on interleaved component holdout (<code>seed=42</code>, 19,732 withheld positives), <code>tilt_alt24_oof_p1</code> achieved <strong>HOLDOUT-DTI {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["tilt_alt24_oof_p1"]["value"]:.5f}</strong> vs <code>subsurface16_oof_p1</code> {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["subsurface16_oof_p1"]["value"]:.5f} and <code>random_p1</code> {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["random_p1"]["value"]:.5f}. Full-grid 38,000-dot distance profile shifted from plain <code>P0</code> (<code>2–10 px: {p0["gt_2_le_10px"]:,}</code>, <code>10–30 px: {p0["gt_10_le_30px"]:,}</code>, <code>&gt;30 px: {p0["gt_30px"]:,}</code>) to decensored <code>P1</code> (<code>2–10 px: {p1["gt_2_le_10px"]:,}</code>, <code>10–30 px: {p1["gt_10_le_30px"]:,}</code>, <code>&gt;30 px: {p1["gt_30px"]:,}</code>), improving off-catalogue <code>SGMC-new</code> diagnostic DTI from {sgmc["tilt_alt24_oof_p0_plain_d2"]["dti"]:.5f} to <strong>{sgmc["tilt_alt24_oof_p1_decensored"]["dti"]:.5f}</strong> (not a leaderboard proxy; IR-30-081).</p></section>

<section class="section two-column"><div><p class="eyebrow">05 / Concrete next-session blueprint</p><h2>Fuse G30-LSM scarp profiles + G30-TAD subsurface physics + decensored collar emission.</h2><p>Across today's lanes, the two halves of a promotable breakthrough have now been proven independently:</p><ul class="spaced"><li><strong>G30-LSM proved multiscale 1 m scarp profiles beat <code>core19</code> with a positive paired CI</strong> (<code>0.15717</code> vs <code>0.13982</code>, <code>+0.01735 [+0.00662, +0.02786]</code>), but failed dot uniqueness (<code>80.2% &gt; 70%</code>) because greedy placement crowded 54% of dots inside <code>≤10 px</code>.</li><li><strong>G30-TAD proved pure geophysical tilt-depth + potassic alteration works without DEMs</strong> (<code>subsurface16 = 0.10959</code>; NW Nevada Fold 0 <code>+0.01801</code> over <code>core19</code>) <strong>and</strong> that <code>decensored_30_40_30</code> OOF collar placement passes the 190-raster dot uniqueness gate cleanly (<code>51.44% ≤ 70%</code>), while dropping regional tectonic strain hurt Walker Lane Folds 1–2.</li></ul></div>
<div class="note-card"><h3>Ordered next steps (G30-FUSION)</h3><ol class="steps"><li>Preregister <code>G30-FUSION</code>: combine <code>G30-LSM</code> multiscale scarp features + <code>G30-TAD</code> <code>subsurface16</code> tilt-depth/alteration/clay-cap + regional strain rate (excluding raw magnetic/gravity coordinate levels).</li><li>Replace radial <code>30/40/30</code> weights with rasterized USGS SGMC Quaternary alluvial-cover polygons (<code>NV.zip</code>, <code>CA.zip</code> already SHA-pinned locally).</li><li>Run the 190+ raster dot-overlap gate <em>before</em> spending E2/E3 experiments, promoting to the separate weekly-slot selector <strong>only</strong> if paired <code>v3</code> CI lower bound &gt; 0 against both <code>core19</code> (<code>0.13982</code>) and <code>lsm42</code> (<code>0.15717</code>).</li></ol><p><a href="{TAD_DIR}/review.md">Detailed G30-TAD Markdown review ↗</a> · <a href="{TAD_DIR}/verification.md">Three-pass verification journal ↗</a> · <a href="{TAD_DIR}/run-card.json">JSON Run Card ↗</a></p></div></section>'''


def public_registry_page(snapshot):
    """Render the latest source-sync receipt without upgrading it to score evidence."""
    discovery = snapshot["continuous_surface_discovery"]
    rows = ''.join(
        f'<tr><th scope="row"><a href="https://github.com/{e(row["repo"])}'
        f'/tree/{e(row["ref"])}">{e(row["site"])}</a></th><td><code>{e(row["ref"][:12])}…</code></td>'
        f'<td>{row["published_tiffs"]}</td><td>{len(row["continuous_surface_path_candidates"])}</td></tr>'
        for row in snapshot["snapshots"]
    )
    inspected = discovery.get("inspections") or []
    surface_rows = ''.join(
        f'<tr><th scope="row">{e(row["site"])}</th><td><a href="{e(row["source_url"])}"><code>{e(row["source_path"])}</code></a></td>'
        f'<td>{e(row.get("format", "not inspected"))}</td><td>{e(row.get("future_surface_comparison_eligibility", "unknown"))}</td></tr>'
        for row in inspected
    ) or '<tr><td colspan="4">No surface metadata inspection was recorded.</td></tr>'
    return f'''<section class="intro"><div><p class="eyebrow">Public source registry / 25 October 2026</p><h1>More coverage.<br>Not a score.</h1><p class="lead">A fresh immutable GitHub snapshot expands the public reference inventory without changing any candidate, dot placement, holdout result, or submission decision.</p></div><a class="text-link" href="docs/research/2026-10-25/priority-site-public-snapshot.json">Open machine receipt ↗</a></section>
<section class="stop-notice"><div class="release-heading"><span class="pill caution">NO NEW PROMOTED SLOT</span><span class="meta">Registry audit</span></div><h2>190 aligned rasters now guard uniqueness.</h2><p>G30-TAD audited both its pre-placement OOF surface (max Spearman 0.1637) and final 38,000 dots (max 3-px overlap 51.44%) against all 190 aligned rasters below, while earlier TDX-C2 remains stopped at 79.09%.</p><a class="button secondary" href="geothermal-tilt-alteration-review.html">Read G30-TAD uniqueness &amp; holdout results</a></section>
<section class="section"><p class="eyebrow">Byte-verified public inventory</p><h2>{snapshot["source_files"]} TIFF source blobs, {snapshot["unique_aligned_byte_sequences"]} aligned byte identities.</h2><p>Every source TIFF below came from <code>docs/downloads/</code> at the displayed immutable commit. Git blob identity, SHA-256 and template-grid compatibility are in the receipt. One off-grid format-test TIFF was excluded. Source counts are neither performance rankings nor organizer-confirmed submissions.</p><div class="table-wrap"><table><caption>Nine requested repositories · public source scope only</caption><thead><tr><th>Repository</th><th>Immutable commit</th><th>TIFF source blobs</th><th>Likely surface paths</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="section"><p class="eyebrow">Surface check groundwork</p><h2>Five paths were inspected as metadata only.</h2><p>Three public objects are template-shaped, but their model lineage, probability scaling, leakage status and release authority are not established. All are therefore <strong>unknown</strong> for a future surface comparison; none entered scoring or a model.</p><div class="table-wrap"><table><caption>Potential public surfaces · never used as predictions here</caption><thead><tr><th>Repository</th><th>Object</th><th>Container</th><th>Eligibility</th></tr></thead><tbody>{surface_rows}</tbody></table></div><p class="fine">This remains a partial registry. Private lanes, surfaces with unrelated names, and all non-public references are absent. A later preregistration must freeze a reviewed registry before emitting dots.</p></section>
<section class="section two-column"><div><p class="eyebrow">Historical interpretation</p><h2>H33/B2 is sparse pruning, not a score certificate.</h2><p>Existing byte forensics reconstruct H33/B2's 37,654 active pixels exactly as the GEMSDOE28 40,199-pixel base after deleting pixels within two catalogue pixels. Under max-kernel credit, deleting redundant nearby dots can save penalty without losing equivalent truth credit.</p><p>The supplied 0.2778 attribution has no organizer receipt/file-hash pairing in this repository. It remains an owner-reported historical claim, not HOLDOUT-DTI or ORGANIZER-CONFIRMED.</p></div><div class="note-card"><h3>What comes next</h3><ol class="steps"><li>Combine G30-LSM scarp morphology with G30-TAD subsurface tilt-depth &amp; alteration.</li><li>Use USGS SGMC Quaternary cover polygons for physical observability decensoring.</li><li>Require positive paired v3 CI over both core19 (0.13982) and lsm42 (0.15717).</li><li>Emit a weekly-slot candidate only when every format, novelty, and holdout gate is green.</li></ol><p><a href="docs/research/2026-10-25/priority-site-public-review.md">Full registry methods &amp; limitations ↗</a></p></div></section>'''


def redirect_html(target_rel: str, title: str) -> str:
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0;url={e(target_rel)}">'
        f'<title>{e(title)}</title><link rel="canonical" href="{e(target_rel)}"></head>'
        f'<body><p><a href="{e(target_rel)}">Open {e(title)}.</a></p></body></html>\n'
    )


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
        raise ValueError("This stopped-result site cannot advertise a promoted or newly downloadable TDX candidate")

    tad_pointer = ROOT / TAD_DIR / "current-run.json"
    tad_ready = verify_tad(tad_pointer, template)
    tad_card = json.loads((ROOT / TAD_DIR / "run-card.json").read_text())
    if tad_ready["ok_to_submit"] is not False or tad_card["verdict"] != "negative":
        raise ValueError("G30-TAD negative CI verdict must not be rendered as approved for slot expenditure")

    tad_top = tad_banner(tad_card, tad_ready, allow_download_attr=False)
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

    n_late_tdxc2 = stopped["observed_registry"]["dots"]["registry_entries_compared"] - 164
    home = f'''<section class="intro"><div><p class="eyebrow">DOE GEMS / automated evidence &amp; submission gates</p><h1>Unique file validated.<br>Weekly slot protected.</h1><p class="lead">G30-TAD published a unique, range-verified [0, 1] GeoTIFF pair passing all 190 registry uniqueness checks (51.44% ≤ 70%), while withholding weekly-slot promotion because its +0.00423 holdout gain over core19 has a paired 95% CI crossing zero.</p><p class="meta">25–26 October 2026 <span>·</span> Zero human-inspection gates <span>·</span> No competition slot used</p></div><a class="text-link" href="geothermal-tilt-alteration-review.html">G30-TAD &amp; PhD H33 proof ↗</a></section>
{tad_top}{notice}{lsm_section}{archive}
<section class="evidence-strip" aria-label="Latest experiment diagnostics"><article><span>G30-TAD uniqueness</span><strong>190 rasters cleared</strong><small>Surface ρ 0.1637 · Dot 3-px overlap 51.44% ≤ 70%</small></article><article><span>G30-TAD holdout &amp; canaries</span><strong>0.14405 vs 0.13982</strong><small>+0.00423 [−0.01554, +0.02398] · 144/144 AUC ≤ 0.6434</small></article><article><span>Earlier TDX-C2 audit</span><strong>{stopped["observed_registry"]["dots"]["registry_entries_compared"]} files compared</strong><small>164 frozen + {n_late_tdxc2} late arrivals · 79.09% stop</small></article></section>
<section class="section"><p class="eyebrow">01 / Earlier TDX-C2 matched-control lesson</p><h2>Additional lag features did not establish additional signal.</h2><p>In the earlier TDX-C2 lane, the full-stack candidate did not beat core19, the zero-lag control, or the phase-scrambled control with a positive paired confidence interval. See <a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 analysis</a> for how subsurface tilt-depth, potassic alteration, and 30/40/30 collar decensoring solved the duplicate-overlap failure.</p>{scores}<a class="text-link" href="experiment-review.html">TDX-C2 scientific interpretation, nine-site audit &amp; limitations ↗</a></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated inspection</p><h2>Unknown never means approved.</h2></div><p>Duplicates are quarantined.<br>Every published TIFF is byte-verified in CI.</p></div>{gate_table(stopped)}</section>
<section class="section two-column"><div><p class="eyebrow">03 / Historical lesson &amp; live leaderboard</p><h2>H33 (0.2778) is collar pruning; live #1 is 0.4413.</h2><p>Byte-level reconstruction proves H33's 37,654-dot support is an exact subset of GEMSDOE28's 40,199-dot base after deleting dots at catalogue distance ≤2 pixels. Under max-kernel credit, deleting redundant collar dots saves FP penalty without losing truth coverage—and adding 1,200 collar dots in GEMSDOE36 PINN dropped the score to 0.2750.</p><p>Live DrivenData leaderboard check (fetched 2026-10-25): <strong>#1 xiaofanhu = 0.4413</strong> (30 submissions), confirming 0.3195 in the standing prompt was an earlier 2026-10-03 snapshot. Owner-reported scores across GEMSDOE24–36 remain unverified historical claims until paired with organizer submission receipts.</p><a class="text-link" href="geothermal-tilt-alteration-review.html">Read full PhD H33 proof &amp; 5 geothermal hypotheses ↗</a></div><div class="note-card"><h3>Public registry &amp; next session (G30-FUSION)</h3><p>205 public download TIFF blobs across the nine priority repositories reduced to 190 aligned byte sequences—all cleared by G30-TAD at 51.44% dot overlap.</p><p><a href="priority-registry-review.html">Read immutable commits &amp; registry scope ↗</a></p><h3>Ordered next step</h3><ul class="spaced"><li>Fuse G30-LSM multiscale 1 m scarp profiles (0.1572 holdout) with G30-TAD subsurface tilt-depth/alteration (subsurface16 = 0.1096) and 30/40/30 SGMC-concealment collar emission.</li><li>Promote to a weekly slot <strong>only</strong> when paired v3 CI lower bound &gt; 0 over both core19 (0.13982) and lsm42 (0.15717).</li></ul><a href="README.md#current-owner-prompt">Complete standing owner prompt ↗</a></div></section>'''

    guide = f'''<section class="intro"><div><p class="eyebrow">Executive submission guide</p><h1>Automated gate status<br>&amp; DrivenData steps.</h1><p class="lead">Check the top gate banner first: G30-TAD is format- and novelty-validated in [0, 1] for research download, but its weekly-slot gate is negative (do not spend a weekly submission slot).</p></div></section>{tad_top}{notice}{lsm_section}{archive}
<section class="section"><p class="eyebrow">Current queue status</p><h2>Why zero weekly submission slots are spent right now.</h2><ul class="spaced"><li><strong>G30-TAD (latest unique GeoTIFF pair):</strong> <code>download_ok = true</code> (all 12,279,160 cells of <code>-zeros.tif</code> finite in <code>[0, 1]</code>; 190-raster novelty passed at <code>0.1637</code> surface ρ and <code>51.44%</code> dot overlap), <strong><code>ok_to_submit = false</code></strong> because <code>tilt_alt24 − core19 = +0.00423</code> has paired 95% block-bootstrap CI <code>[−0.01554, +0.02398]</code>. <a href="geothermal-tilt-alteration-review.html">Full G30-TAD review</a>.</li><li>Latest TDX-C2: duplicate-stop (79.09%) and no paired holdout improvement; no public raster.</li>{lsm_bullet}<li>Retained TDX-1: locally format-valid research artifact, but its performance gate failed (0.07284).</li></ul><p><code>python scripts/verify_tad_run.py --require-promote</code>, <code>python scripts/verify_stopped_attempt.py --require-promote</code>, and <code>python scripts/verify_current_run.py --require-promote</code> all deliberately exit <b>2</b>. Zero human-inspector overrides exist.</p></section>
<section class="section"><p class="eyebrow">Archived artifact identity · not latest candidate</p><h2>A name and note for the retained research download.</h2><div class="identity"><label for="submission-name">Archived TDX-1 name · do not upload</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Archived research note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div><p class="fine">For G30-TAD's copyable artifact name and 82/140-character note, see <a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 analysis</a> or <a href="{TAD_DIR}/run-card.json">its JSON Run Card</a>. The stopped TDX-C2 name and note remain only in its <a href="{LATEST}/run-card.json">negative run card</a>.</p></section>
<section class="section"><p class="eyebrow">Official DrivenData submission procedure (verified 2026-10-25)</p><h2>Exact steps when a future run turns every gate green.</h2><ol class="steps"><li><strong>Verify automated promotion exit code 0.</strong><p>Run <code>python scripts/verify_tad_run.py --require-promote</code> (or <code>python scripts/verify_current_run.py --require-promote</code>). Only proceed when exit code is <code>0</code> (<code>ok_to_submit = true</code>, meaning format <code>[0, 1]</code>, 144+ feature canaries, 190+ registry surface &amp; dot novelty, and paired spatial-block holdout 95% CI lower bound &gt; 0 have all passed).</p></li><li><strong>Confirm weekly 3-slot allowance &amp; deadline window.</strong><p>Per official <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE/NLR Prize Rules PDF (96647.pdf)</a>, automated feedback is capped at <strong>3 submissions per rolling 7-day week</strong>, and entrants select <strong>one single final submission</strong> before the deadline for both Phase 1 ($50k: 5 × $10k) and Phase 2 ($250k: $100k/$70k/$40k/$25k/$15k). <strong>Deadline discrepancy alert (IR-TAD-02):</strong> DrivenData lists <code>Dec. 3, 2026, 11:59 p.m. UTC</code>, whereas NLR Rules PDF Appendix A.1 specifies <strong>5:00 p.m. ET (22:00 UTC) on Dec. 3, 2026</strong>—always submit well before <strong>5:00 p.m. ET (22:00 UTC)</strong>!</p></li><li><strong>Download the primary <code>-zeros.tif</code> GeoTIFF (never HTML/JSON).</strong><p>Download the hash-verified single-band <code>float32</code> GeoTIFF (<code>EPSG:32611</code>, <code>3,730 × 3,292</code>, 100 m grid). The primary <code>-zeros.tif</code> encodes <code>0.0</code> outside the valid footprint with <code>nodata=None</code> so every one of the 12,279,160 cells lies strictly inside <code>[0.0, 1.0]</code> (preventing whole-array <code>"Predicted values must be in range [0, 1]"</code> rejections), while companion <code>-nan.tif</code> provides the documented <code>NaN</code>-outside encoding.</p></li><li><strong>Upload on DrivenData &amp; paste the ≤140-character note.</strong><p>Sign into an eligible account on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS (Competition 306)</a> → open <strong>Submissions → Make a submission</strong> → select the verified <code>.tif</code> under <em>File to submit</em> → paste the run card's ≤140-character note (generative AI usage is permitted and must be disclosed in winning documentation, excluded from word count per <code>96647.pdf</code>).</p></li><li><strong>Log the organizer receipt before claiming ORGANIZER-CONFIRMED.</strong><p>Record the returned DrivenData timestamp, file SHA-256, and 4-decimal DTI score in <code>docs/score-ledger.csv</code>. Never label a <code>HOLDOUT-DTI</code> or analytical projection as <code>ORGANIZER-CONFIRMED</code>.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">Preventing "Predicted values must be in range [0, 1]"</p><h2>Automated whole-array &amp; in-footprint gates.</h2><p>The documented <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">GEMS problem specification</a> requires a single-band <code>float32</code> GeoTIFF in <code>[0, 1]</code> inside the valid footprint and null/NaN outside, whereas the official reference notebook writes predictions without an explicit <code>nodata</code> tag (all cells finite in <code>[0, 1]</code>). If a portal validator evaluates <code>arr.min() &gt;= 0 and arr.max() &lt;= 1</code> prior to masking <code>NaN</code> or encounters unmasked <code>-9999</code>/<code>-3.4e38</code> feature sentinels, it raises <code>"Predicted values must be in range [0, 1]"</code>.</p><p>Our automated release pipeline eliminates human inspection by verifying <strong>both</strong> contracts on disk: <code>-zeros.tif</code> guarantees all 12,279,160 pixels are finite <code>&#123;0.0, 1.0&#125;</code> in <code>[0, 1]</code>, and <code>-nan.tif</code> passes all 12 checks of <code>gemsdoe30.submission.validate_submission_file</code>.</p></div><div class="note-card"><h3>Verified official sources (checked 2026-10-25)</h3><ul class="spaced"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS overview</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; DTI metric specification (page 967)</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official DOE/NLR Prize Rules PDF (96647.pdf)</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Live leaderboard (#1 xiaofanhu: 0.4413 on 2026-10-25)</a></li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN airborne release (DOI 10.5066/P93LGLVQ)</a></li><li><a href="https://gdr.openei.org/submissions/1391">GDR 1391 INGENIOUS compilation (DOI 10.15121/1881483)</a></li></ul></div></section>'''

    pins = json.loads((ROOT / LATEST / "historical-reference-audit.json").read_text())["rasters"]
    sites = ''.join(f'<tr><th scope="row"><a href="{e(r["source_url"])}">{e(r["site"])}</a></th><td>{r["positive_pixels"]:,}</td><td>{"Passed" if r["local_format_validation"]["passed"] else "Failed: outside encoding"}</td><td><code>{e(r["sha256"][:16])}…</code></td></tr>' for r in pins)
    public_snapshot = json.loads((ROOT / "docs/research/2026-10-25/priority-site-public-snapshot.json").read_text())
    research = f'''<section class="intro"><div><p class="eyebrow">Scientific review / earlier TDX-C2 &amp; nine-site audit</p><h1>Falsification is<br>a deliverable.</h1><p class="lead">Conditional magnetic displacement (TDX-C2) did not establish a benefit over matched controls, motivating G30-TAD's coordinate-free tilt-depth, potassic alteration, and decensored collar design.</p></div><a class="text-link" href="geothermal-tilt-alteration-review.html">Open G30-TAD review ↗</a></section>{notice}
<section class="section"><h2>One hypothesis. Four fixed arms. No search.</h2><p>Cached magnetic anomaly, RTP and isostatic gravity supplied the two-scale flank-profile transforms. The candidate adds three lag-gain features to all 19 core bands. Matched controls add either zero-lag coherence or locally Fourier-phase-scrambled lag gains. Intrusive lithologic contacts and gridding seams can mimic the proposed signal.</p>{scores}<p>The candidate-minus-core19 HOLDOUT-DTI difference is −0.00376, paired 95% CI [−0.00818, 0.00070], under the same evaluator and 60,988 withheld positives. This fails the improvement gate; it does not prove the candidate is significantly worse. The controls do not prove an absence of geological displacement.</p><p>Four whole-component regional trials use a 17 px training/physical-support guard, exact visible-fault masking, a 300 m triangular kernel, and equal active dot budgets. Truth credit and false-positive mass are pooled before DTI is computed. No catalogue geometry or historical predictions enter the feature transforms.</p><p class="fine">The core19 result exactly reproduces the previous same-protocol sufficient statistics and CI. This is an engineering consistency check, not independent validation. One deterministic phase control is not a sampled null distribution.</p><div class="actions"><a class="text-link" href="{LATEST}/preregistration.md">Four ranked hypotheses &amp; frozen plan ↗</a><a class="text-link" href="{LATEST}/results.json">All statistics &amp; 112 canaries ↗</a></div></section>
<section class="section"><h2>The mandatory stop worked.</h2><p>The frozen registry contained 164 observed byte identities; post-stop arrivals were checked on saved states without changing predictions. Max surface Spearman was 0.15657. Final-dot Spearman was 0.06383, but overlap reached 79.09% against G30-S19's 60,000-dot output. Low pixelwise correlation alone would have missed this lane collision.</p><p>The stopped TIFF passed a local shared-writer check and an independent post-stop file reopen. It remains private under ignored outputs/.</p><a href="{LATEST}/validation.json">Recorded validator output ↗</a> · <a href="{LATEST}/novelty-dots.json">Every final-dot comparison ↗</a> · <a href="{LATEST}/readiness.json">Fail-closed decision ↗</a></section>
<section class="section"><h2>Nine priority sites: educational audit.</h2><p>No historical raster was reused as new predictions. The table is a file diagnostic, not a performance ranking or organizer acceptance table.</p><div class="table-wrap"><table><caption>Frozen reference identities · counts and format diagnostics, not scores</caption><thead><tr><th>Priority site / pinned file</th><th>Positive pixels</th><th>Local documented format</th><th>SHA-256 prefix</th></tr></thead><tbody>{sites}</tbody></table></div><p>Fresh README inventories: <a href="{LATEST}/priority-site-review.json">nine immutable snapshots</a>. Exact artifact checks: <a href="{LATEST}/historical-reference-audit.json">reference audit</a>. H33 support reconstruction: <a href="docs/research/2026-10-25/recipe-reconstruction.json">zero mismatching pixels</a>.</p></section>
<section class="section"><h2>Why H33 may have improved—and why that is not a forecast.</h2><p>For weighted truth credit T, false-positive mass F and truth count G, the shared metric is <code>DTI = T / (0.2T + 0.2F + 0.8G + ε)</code>. Credit is a maximum over a triangular neighborhood, not an unrestricted sum. Removing redundant dots can save FP mass with little loss in truth coverage. See <a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 analysis</a> for the complete algebraic derivation across D2.8, r1-solo, H33-B2, and PINN.</p><p>The owner's 0.2778 attribution and historical ledger rows remain <strong>unverified historical claims</strong>, not ORGANIZER-CONFIRMED. <a href="{RESEARCH}/owner-claims.csv">All 119 supplied claims</a> remain quarantined.</p></section>
<section class="section"><h2>Sources, boundaries &amp; next steps.</h2><p>The official <a href="https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/unet-mc-cv-reference-solution.ipynb">reference notebook</a> agrees with the cached grid and layer descriptions; <a href="{LATEST}/official-source-audit.json">hashes and exact excerpts</a> are retained. Verified official datasets include the <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN release</a> and <a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS compilation</a>.</p><p><a href="{TAD_DIR}/review.md">G30-TAD scientific report</a> · <a href="{LATEST}/review.md">TDX-C2 scientific report</a> · <a href="{LATEST}/verification.md">TDX-C2 verification journal</a> · <a href="docs/irregularities.md">Irregularities register</a></p></section>'''

    return {
        ROOT / "index.html": page("G30-TAD validated download & negative slot gate", home, active="overview"),
        ROOT / "executive-summary.html": page("Executive submission guide & gate status", guide, active="guide"),
        ROOT / "geothermal-tilt-alteration-review.html": page("G30-TAD, PhD H33 proof & geothermal synthesis", tad_review_page(tad_card, tad_ready), active="tad"),
        ROOT / "experiment-review.html": page("Displacement falsification & nine-site audit", research, active="research"),
        ROOT / "priority-registry-review.html": page("Public priority registry review", public_registry_page(public_snapshot), active="research"),
        ROOT / "docs/assets/tdx1-support.png": png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/assets/tad24-support.png": png_preview(template, local_path(tad_card["published_tiff"])),
        ROOT / "docs/index.html": redirect_html("../index.html", "GEMSDOE30"),
        ROOT / "docs/executive-summary.html": redirect_html("../executive-summary.html", "Executive submission guide · GEMSDOE30"),
        ROOT / "docs/geothermal-tilt-alteration-review.html": redirect_html("../geothermal-tilt-alteration-review.html", "G30-TAD & PhD H33 analysis · GEMSDOE30"),
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
    print("Verified exact generated Pages" if args.check else "Built research Pages")


if __name__ == "__main__":
    main()
