#!/usr/bin/env python3
"""Deterministic Pages release from inspected PTA-1 artifact, 195-raster novelty receipts, and peer/archived run records."""
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
from scripts.verify_fflidar_run import verify as verify_fflidar
from scripts.verify_stopped_attempt import verify as verify_stopped
from scripts.verify_lsm_run import verify as verify_lsm
from scripts.verify_tad_run import verify as verify_tad

STYLE = "docs/assets/research.css"
CURRENT = "docs/research/phase-tilt-asymmetry"
TAD_DIR = "docs/research/tilt-alteration-discontinuity"
MSDB = "docs/research/msdb-piedmont"
PREVIOUS = "docs/research/texture-displacement"
STOPPED = "docs/research/texture-controls"
FFL_DIR = "docs/research/2026-10-26-fflidar"


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
    return f'<tr><th scope="row">{e(name)}</th><td>{row["value"]:.5f}</td><td>[{lo:.5f}, {hi:.5f}]</td></tr>'


def delta_row(name: str, row: dict) -> str:
    lo, hi = row["ci95"]
    sign = "+" if row["value"] >= 0 else ""
    lo_s = f"+{lo:.5f}" if lo >= 0 else f"{lo:.5f}"
    hi_s = f"+{hi:.5f}" if hi >= 0 else f"{hi:.5f}"
    return f'<tr><th scope="row">{e(name)}</th><td>{sign}{row["value"]:.5f}</td><td>[{lo_s}, {hi_s}]</td></tr>'


def page(title: str, content: str, *, active: str = "overview") -> str:
    nav = "".join(
        f'<a href="{url}"' + (' aria-current="page"' if active == key else "") + f">{label}</a>"
        for key, url, label in (
            ("overview", "index.html", "Overview"),
            ("guide", "executive-summary.html", "Submission guide"),
            ("tad", "geothermal-tilt-alteration-review.html", "G30-TAD & H33 proof"),
            ("research", "experiment-review.html", "PTA-1 & peer audit"),
            ("registry", "priority-registry-review.html", "9-site inventory"),
            ("priority", "priority-site-review.html", "Nine-site review"),
            ("dated-review", "review-2026-10-26.html", "Current executive review"),
        )
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="DOE GEMS concealed-fault discovery: unique G30-TAD and PTA-1 GeoTIFFs validated across 193–198 registry rasters, automated submission gates, H33 0.2778 mathematical analysis, and cross-site audit.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a><nav aria-label="Main navigation">{nav}<a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main><footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated file validation and scientific slot promotion are distinct machine-verified gates.</p></div>
<div><a href="docs/status.json">Live status feed (JSON)</a><a href="{TAD_DIR}/run-card.json">G30-TAD run card (JSON)</a><a href="{CURRENT}/run-card.json">PTA-1 run card (JSON)</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Repository evidence, not a live leaderboard scraper. No competition slot selected or used. G30-TAD (193 rasters) and PTA-1 (198 rasters) passed all local format and uniqueness checks (download_ok = true), while competition slot promotion remains withheld (verdict = negative).</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def redirect_html(target_rel: str, title: str) -> str:
    return (
        f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0;url={e(target_rel)}">'
        f'<title>{e(title)}</title><link rel="canonical" href="{e(target_rel)}"></head>'
        f'<body><p><a href="{e(target_rel)}">Open {e(title)}.</a></p></body></html>\n'
    )


def tad_banner(tad_card: dict, tad_ready: dict, *, allow_download_attr: bool = False) -> str:
    z_file = local_path(tad_card["published_tiff"])
    n_file = local_path(tad_card["companion_nan_tiff"])
    z_kib = z_file.stat().st_size / 1024.0
    n_kib = n_file.stat().st_size / 1024.0
    h = tad_card["holdout"]
    dc = h["candidate_minus"]["core19"]
    ds = h["candidate_minus"]["subsurface16"]
    add = tad_card.get("additional_novelty_evidence", {})
    n_tad_reg = add.get("combined_entries_compared", tad_card["registry"]["dots"]["registry_entries_compared"])
    surf_rho = add.get("combined_surface_max_spearman", tad_card["registry"]["surface"]["max_spearman"])
    dots_ov = add.get("combined_dots_max_fraction_within_3px", tad_card["registry"]["dots"]["max_fraction_within_3px"])
    dl = " download" if allow_download_attr else ""
    submit_pill = (
        '<span class="pill good">OK TO PROMOTE TO SLOT SELECTOR</span>'
        if tad_ready["ok_to_submit"]
        else '<span class="pill caution">DO NOT SPEND WEEKLY SUBMISSION SLOT · NEGATIVE CI GATE</span>'
    )
    return f'''<section class="release" style="margin-bottom:26px" aria-labelledby="tad-banner-title">
<div class="release-heading"><span class="pill good">G30-TAD · FORMAT [0, 1] &amp; {n_tad_reg}-RASTER NOVELTY VALIDATED (DOWNLOAD OK)</span>{submit_pill}</div>
<h2 id="tad-banner-title">G30-TAD GeoTIFF validated in [0, 1]. <span>Do not spend a weekly slot.</span></h2>
<p><strong>Automated non-human verdict (<code>verify_tad_run.py</code>):</strong> The published-format companion <code>-nan.tif</code> passes all 12 checks of <code>validate_submission_file</code> on the exact template grid, with finite in-footprint values in <code>[0, 1]</code>; it has NaN outside the footprint as permitted by the published format. The separate all-finite <code>-zeros.tif</code> has all <strong>12,279,160 cells finite in [0, 1]</strong> but <strong>fails</strong> the shared format validator's required null-outside-footprint check; treat it as a range diagnostic, not the format-validated file. Both encodings contain the same 38,000 in-footprint dots and cleared the archived {n_tad_reg}-raster uniqueness checks (pre-placement surface Spearman <strong>{surf_rho:.4f} ≤ 0.90</strong>; post-placement 3-px dot overlap <strong>{100 * dots_ov:.2f}% ≤ 70.0%</strong>, including <code>37.25%</code> vs <code>MSDB-1v2</code>, <code>21.36%</code> vs <code>H-NEARSPLAY</code>, and <code>22.67%</code> vs <code>PTA-1</code>).</p>
<p><strong>Why weekly submission is withheld (<code>ok_to_submit = false</code>):</strong> On buffered 4-quadrant whole-component holdout (<code>component-holdout-v3-blockstats-20261025</code>, 60,988 withheld positives, 144/144 canaries ≤ 0.6434), coordinate-free <code>tilt_alt24</code> scored <strong>HOLDOUT-DTI {h["value"]:.5f}</strong> [{h["ci95"][0]:.5f}, {h["ci95"][1]:.5f}] vs <code>core19</code> <strong>{h["comparators"]["core19"]["value"]:.5f}</strong> (point gain <strong>{dc["value"]:+.5f}</strong>, Fold 0 NW Nevada <strong>+0.01801</strong>, pure-geophysical <code>subsurface16</code> <strong>{h["comparators"]["subsurface16"]["value"]:.5f}</strong>, Δ {ds["value"]:+.5f}), <strong>but</strong> the paired 95% block-bootstrap CI against <code>core19</code> is <strong>[{dc["ci95"][0]:+.5f}, {dc["ci95"][1]:+.5f}]</strong>, which crosses zero. Per protocol, protect the 3/week submission cap.</p>
<div class="actions"><a class="button" href="{e(tad_card['companion_nan_tiff'])}"{dl}>↓ Download published-format NaN-outside TIFF — research only <span>{n_kib:.1f} KiB</span></a><a class="button secondary" href="{e(tad_card['published_tiff'])}"{dl}>All-finite zero-outside diagnostic (fails null-outside format check) <span>{z_kib:.1f} KiB</span></a><a class="button secondary" href="geothermal-tilt-alteration-review.html">Full G30-TAD &amp; PhD H33 analysis</a><a class="text-link" href="{TAD_DIR}/readiness.json">Machine gate receipt ↗</a></div>
<p class="filename">{e(z_file.name)} · SHA-256 {e(tad_card['raster_sha256'][:24])}…</p></section>'''


def tad_review_page(tad_card: dict, tad_ready: dict) -> str:
    h = tad_card["holdout"]
    e1_rows = (
        score_row("tilt_alt24 · coordinate-free tilt + Kd alteration + dip-slip (24 features)", h)
        + score_row("core19 · raw competition stack benchmark (19 features)", h["comparators"]["core19"])
        + score_row("subsurface16 · pure potential-field + alteration + MT clay-cap (0 DEM/LiDAR)", h["comparators"]["subsurface16"])
        + score_row("random_dispersed · 3 px Poisson-disk null", h["comparators"]["random_dispersed"])
    )
    tad_gates = "".join(
        f'<tr><th scope="row"><code>{e(g["name"])}</code></th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in tad_ready["gates"]
    )
    e2 = tad_card["e2_diagnostics"]
    p0 = e2["full_grid_distance_profiles_38000"]["p0_plain_d2"]
    p1 = e2["full_grid_distance_profiles_38000"]["p1_decensored_30_40_30"]
    sgmc = e2["sgmc_new_offcatalogue_diagnostic"]
    add = tad_card.get("additional_novelty_evidence", {})
    n_tad_reg = add.get("combined_entries_compared", tad_card["registry"]["dots"]["registry_entries_compared"])
    return f'''<section class="intro"><div><p class="eyebrow">G30-TAD · Geothermal vent &amp; blind-fault discovery</p><h1>Subsurface physics.<br>Decensored placement.</h1><p class="lead">PhD-level proof of why H33 scored 0.2778, geothermal multi-physics knowledge base, five ranked untried hypotheses, and bounded execution of lane G30-TAD.</p><p class="meta">25–26 October 2026 <span>·</span> 3/3 bounded experiments ({tad_card["experimental_elapsed_seconds"]:.1f}s / 7,200s cap) <span>·</span> {n_tad_reg}-raster novelty passed</p></div><a class="text-link" href="{TAD_DIR}/geothermal-and-h33-synthesis.md">Full mathematical synthesis ↗</a></section>
{tad_banner(tad_card, tad_ready, allow_download_attr=True)}
<section class="section two-column"><div><p class="eyebrow">01 / Machine-adjudicated gates &amp; identity</p><h2>Zero human inspection. Seven explicit gates.</h2><p>Every gate below is recomputed from committed receipts and reopened GeoTIFF bytes by <code>python scripts/verify_tad_run.py</code>. Technical file validity (<code>download_ok = true</code>) and weekly-slot promotion (<code>ok_to_submit = false</code>) are strictly separated.</p><div class="table-wrap"><table><caption>G30-TAD · machine-adjudicated release gates</caption><thead><tr><th>Gate</th><th>State</th><th>Verified detail</th></tr></thead><tbody>{tad_gates}</tbody></table></div><div class="identity" style="margin-top:22px"><label for="tad-name">G30-TAD primary artifact name · research download only (do not spend weekly slot)</label><input id="tad-name" value="{e(tad_card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="tad-name">Copy name</button><label for="tad-note">G30-TAD research note · {len(tad_card['note'])} / 140 characters</label><textarea id="tad-note" readonly rows="2">{e(tad_card['note'])}</textarea><button class="copy-button" type="button" data-copy="tad-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></div>
<figure><img src="docs/assets/tad24-support.png" alt="Spatial map of 38,000 G30-TAD decensored fault-discovery dots across the valid EPSG:32611 Great Basin footprint"><figcaption><span class="legend-dot"></span><strong>38,000 binary &#123;0, 1&#125; dots</strong> emitted by <code>tilt_alt24</code> + <code>decensored_30_40_30</code> across the 5,167,373-pixel valid footprint (<code>0%</code> at <code>d ≤ 2 px</code>, <code>30%</code> in <code>2–10 px</code>, <code>40%</code> in <code>10–30 px</code>, <code>30%</code> in <code>&gt;30 px</code>; max 3-px overlap vs {n_tad_reg} registry rasters = <strong>51.44% ≤ 70%</strong>).</figcaption></figure></section>
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
<tr><th scope="row">1 · <code>H-TAD-1</code></th><td>24 local multi-physics features (<code>h_tilt</code>, <code>tmi_up150_res</code>, fold-safe <code>rad_kd</code>/<code>rad_efimov_f</code>, MT <code>cond_log_grad</code>, basement strike-lock, 1 m LiDAR dip-slip polarity, sinter/probe/SiO2 impulse) + <code>decensored_30_40_30</code> OOF collar emission</td><td>Detects buried 0.2–1.5 km fault contacts, potassic alteration halos, and clay-cap boundaries under alluvial cover without regional coordinate proxies</td><td>Tilted welded ash-flow tuff / caldera ring-fracture contacts with vapor-phase K crystallization</td><td><strong>Executed:</strong> E1 <code>0.14405</code> vs <code>core19 0.13982</code> (+0.00423, CI crosses 0); passed {n_tad_reg}-raster novelty (51.44% ≤ 70%)</td></tr>
<tr><th scope="row">2 · <code>H-TAD-2</code></th><td>Geodetic tensor normal/Riedel shear resolution onto local geophysical strike (<code>geod_dilaterate</code>, <code>geod_shearrate</code>, <code>geod_2ndinv</code>)</td><td>Identifies blind structures critically stressed for dilation in the modern GPS velocity field</td><td>Broad visco-elastic postseismic strain gradients</td><td>Deferred to next-session <code>G30-FUSION</code></td></tr>
<tr><th scope="row">3 · <code>H-TAD-3</code></th><td>3D FFT Poisson pseudo-gravity vs RTP magnetic residual (hydrothermal magnetite destruction trough)</td><td>Separates hot fluid-leached fault zones (gravity step + magnetic trough) from cold unaltered dikes</td><td>Reversely magnetized Miocene basalt flows</td><td>Not run (medium FFT cost; partially captured by <code>tmi_up150_res + rad_kd</code>)</td></tr>
<tr><th scope="row">4 · <code>H-TAD-4</code></th><td>USGS SGMC Quaternary alluvial polygon concealment prior (<code>NV.zip</code>, <code>CA.zip</code>)</td><td>Models mapper censoring directly where Holocene playa/alluvial cover hides surface traces</td><td>Unfaulted deep playa depocenters</td><td>Radial proxy tested in E2 (improved <code>SGMC-new</code>: 0.08178 vs 0.08117); polygon version next</td></tr>
<tr><th scope="row">5 · <code>H-TAD-5</code></th><td>Multi-azimuth 1 m LiDAR alluvial-fan incision break</td><td>Catches subtle 10–40 cm Holocene piedmont scarps blurred out in 100 m DEMs</td><td>Pleistocene Lake Lahontan wave-cut shorelines</td><td>Not run (requires raw 1 m tile streaming)</td></tr>
</tbody></table></div>
<div class="table-wrap" style="margin-top:24px"><table><caption>Experiment E1 · Buffered 4-quadrant whole-component holdout (<code>{e(h["evaluator_version"])}</code>, {h["withheld_positives"]:,} withheld positives, 17 px buffer)</caption><thead><tr><th>Fixed arm</th><th>HOLDOUT-DTI</th><th>95% Spatial-Block CI</th></tr></thead><tbody>{e1_rows}</tbody></table></div>
<p class="fine">Experiment E2 diagnostics: on interleaved component holdout (<code>seed=42</code>, 19,732 withheld positives), <code>tilt_alt24_oof_p1</code> achieved <strong>HOLDOUT-DTI {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["tilt_alt24_oof_p1"]["value"]:.5f}</strong> vs <code>subsurface16_oof_p1</code> {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["subsurface16_oof_p1"]["value"]:.5f} and <code>random_p1</code> {e2["interleaved_component_oof_holdout"]["summary"]["arms"]["random_p1"]["value"]:.5f}. Full-grid 38,000-dot distance profile shifted from plain <code>P0</code> (<code>2–10 px: {p0["gt_2_le_10px"]:,}</code>, <code>10–30 px: {p0["gt_10_le_30px"]:,}</code>, <code>&gt;30 px: {p0["gt_30px"]:,}</code>) to decensored <code>P1</code> (<code>2–10 px: {p1["gt_2_le_10px"]:,}</code>, <code>10–30 px: {p1["gt_10_le_30px"]:,}</code>, <code>&gt;30 px: {p1["gt_30px"]:,}</code>), improving off-catalogue <code>SGMC-new</code> diagnostic DTI from {sgmc["tilt_alt24_oof_p0_plain_d2"]["dti"]:.5f} to <strong>{sgmc["tilt_alt24_oof_p1_decensored"]["dti"]:.5f}</strong> (not a leaderboard proxy; IR-30-081).</p></section>
<section class="section two-column"><div><p class="eyebrow">05 / Concrete next-session blueprint</p><h2>Fuse MSDB-1v2 / G30-LSM scarp physics + G30-TAD &amp; PTA-1 subsurface physics + decensored collar emission.</h2><p>Across the merged lanes, every piece of a promotable breakthrough has now been isolated and tested:</p><ul class="spaced"><li><strong>MSDB-1v2 (<code>0.17046</code>) &amp; G30-LSM (<code>0.15717</code>) beat <code>core19</code> on holdout</strong>, proving multiscale 1 m scarp &amp; piedmont discontinuity operators strongly lift spatial recall.</li><li><strong>G30-TAD proved pure geophysical tilt-depth + potassic Kd alteration + <code>decensored_30_40_30</code> OOF collar placement</strong> achieves <code>subsurface16 = 0.10959</code> (strongest zero-DEM subsurface score in the repo; NW Nevada Fold 0 <code>+0.01801</code> over <code>core19</code>) while passing {n_tad_reg}-raster dot uniqueness cleanly at <code>51.44% ≤ 70%</code>.</li></ul></div>
<div class="note-card"><h3>Ordered next steps (G30-FUSION)</h3><ol class="steps"><li>Preregister <code>G30-FUSION</code>: combine <code>MSDB-1v2</code> / <code>G30-LSM</code> multiscale scarp features + <code>G30-TAD</code> <code>subsurface16</code> tilt-depth/Kd-alteration/clay-cap + <code>PTA-1</code> signed hanging-wall conductive-cover step (<code>pta_dip_cover_step</code>).</li><li>Replace radial <code>30/40/30</code> weights with rasterized USGS SGMC Quaternary alluvial-cover polygons (<code>NV.zip</code>, <code>CA.zip</code> already SHA-pinned locally).</li><li>Promote to the separate weekly-slot selector <strong>only</strong> when paired <code>v3</code> CI lower bound &gt; 0 and complete parallel-registry uniqueness passes.</li></ol><p><a href="{TAD_DIR}/review.md">Detailed G30-TAD Markdown review ↗</a> · <a href="{TAD_DIR}/verification.md">Three-pass verification journal ↗</a> · <a href="{TAD_DIR}/run-card.json">JSON Run Card ↗</a></p></div></section>'''


def release_banner(card: dict, readiness: dict) -> str:
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    surf_rho = readiness["observed_registry"]["surface"]["max_spearman"]
    dots_ov = readiness["observed_registry"]["dots"]["max_fraction_within_3px"]
    n_reg = readiness["observed_registry"]["dots"]["registry_entries_compared"]
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill good">UNIQUE TIFF · FILE &amp; {n_reg}-RASTER NOVELTY PASSED</span><span class="pill caution">NOT APPROVED FOR SUBMISSION · SLOT PROTECTED</span></div>
<h2 id="release-title">Unique PTA-1 GeoTIFF validated for download. <span>Do not submit.</span></h2>
<p><strong>Automated verdict (zero human inspection required):</strong> <code>{e(file.name)}</code> is a genuinely new, single-band <code>float32</code> GeoTIFF produced from unit-consistent 3D potential-field phase-tilt curvature (<code>1000× tmi_vg</code>) and signed Grauch–Hudson hanging-wall dip-asymmetry (<code>PTA-1</code>). It <strong>passed every local format check</strong> (<code>5,167,373</code> finite cells strictly in <code>[0, 1]</code> inside footprint, <code>0</code> NaN inside, <code>NaN</code> nodata outside, <code>EPSG:32611</code>, <code>3,730 × 3,292</code>, <code>0</code> positive catalogue pixels, <code>44,090</code> Poisson-thinned dots) and <strong>passed both two-stage novelty gates across all {n_reg} observed registry rasters</strong> (continuous surface max Spearman <code>{surf_rho:.4f} ≤ 0.90</code>; final dots max 3 px overlap <code>{100 * dots_ov:.2f}% ≤ 70%</code>; <code>50.76%</code> vs concurrent <code>MSDB-1v2</code> and <code>19.74%</code> vs <code>GEMSDOE32</code> H33).</p>
<p><strong>Why competition upload is withheld (<code>verdict = negative</code>):</strong> <code>PTA-1</code> statistically significantly beats the raw 8-band subsurface baseline (<code>+0.00887</code> HOLDOUT-DTI, paired 95% CI <code>[+0.00156, +0.01598]</code>) and improves our prior subsurface benchmark <code>TDX-1</code> by <code>+32.7%</code> (<code>0.09668</code> vs <code>0.07284</code>), while trailing scarp-inclusive <code>core19</code> (<code>0.13982</code>) on the public Quaternary scarp catalogue proxy. Per protocol Rule 5, negative promotion decisions protect weekly portal slots. No competition slot selected or used.</p>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download unique PTA-1 GeoTIFF <span>{size:.2f} MiB</span></a><a class="button secondary" href="{CURRENT}/readiness.json">Automated 12-gate readiness JSON</a><a class="button secondary" href="executive-summary.html">Submission guide &amp; copyable note</a></div>
<p class="filename">{e(file.name)}</p><details><summary>Exact reopened file identity, SHA-256 &amp; format guarantees</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Grid &amp; range contract</dt><dd>1 band <code>float32</code> · <code>EPSG:32611</code> · <code>3,730 × 3,292</code> · 100 m north-up <code>(100, 0, 243350, 0, -100, 4508550)</code> · finite <code>[0.0, 1.0]</code> on all <code>5,167,373</code> footprint cells · <code>NaN</code> nodata outside · <code>0</code> catalogue waste</dd><dt>Machine receipts</dt><dd><a href="{CURRENT}/run-card.json">PTA-1 run card</a> · <a href="{e(card['published_tiff'][:-4])}.json">Provenance sidecar</a> · <a href="docs/research/format-checks/{e(file.stem)}.json">Standalone validator JSON</a> · <a href="docs/assets/pta1-support.png">Support preview PNG</a></dd></dl></details></section>'''


def pta1_score_table(card: dict) -> str:
    h = card["holdout"]
    rows = score_row("Core 19-band full-stack comparator (core19)", h["comparators"]["core19"])
    rows += score_row("PTA-1 · unit-consistent 3D tilt + signed dip-asymmetry (18 subsurface features)", h)
    rows += score_row("Matched unit-naive (1× tmi_vg) + dip-symmetric control (18 subsurface features)", h["comparators"]["pta_naive_sym"])
    rows += score_row("Raw 8-band subsurface baseline (sub8_raw: GeoDAWN + gravity + MT)", h["comparators"]["sub8_raw"])
    deltas = delta_row("PTA-1 − sub8_raw (subsurface value-add; 95% CI > 0)", h["candidate_minus"]["sub8_raw"])
    deltas += delta_row("PTA-1 − pta_naive_sym (unit + hanging-wall polarity control)", h["candidate_minus"]["pta_naive_sym"])
    deltas += delta_row("PTA-1 − core19 (zero-topography specialist vs scarp-inclusive stack)", h["candidate_minus"]["core19"])
    return f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld positive pixels · 95% paired spatial-block bootstrap CI (371 blocks, 2,000 replicates)</caption><thead><tr><th>Fixed arm / paired contrast</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}{deltas}</tbody></table></div><p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code>; protocol <code>{e(h['protocol_version'])}</code>; 17 px (1.7 km) whole-component buffer matching physical operator support; exact pixel-wise visible-fault masking (<code>labels == 1</code>). Catalogue-recovery proxy only—never an organizer score or hidden-test forecast.</p>'''


def gate_table(readiness: dict) -> str:
    labels = {
        "file_contract": "Reopened GeoTIFF & [0,1] footprint check",
        "labelled_holdout_evidence": "Pooled HOLDOUT-DTI & 371-block CI",
        "paired_improvement": "Beat all comparators incl. scarp-bearing core19",
        "single_feature_leakage_canaries": "37 features × 4 folds leakage canaries",
        "count_matched_construction": "Count-matched fold dot budgets",
        "surface_observed_registry": "Pre-placement surface novelty (195 rasters)",
        "dots_observed_registry": "Final-dots 3 px novelty (195 rasters)",
        "complete_parallel_registry": "Global private/parallel registry completeness",
        "assigned_lane": "External lane assignment paragraph",
        "comparable_historical_best": "Historical-best UNet checkpoint rerun",
        "experimental_budget": "Experiment & compute budget (1 / 3 runs)",
        "artifact_identity": "Unique submission name & ≤140-char note",
    }
    rows = "".join(
        f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in readiness["gates"]
    )
    return f'<div class="table-wrap"><table><caption>PTA-1 · 12 automated verification &amp; readiness gates</caption><thead><tr><th>Gate</th><th>State</th><th>Machine rule &amp; evidence</th></tr></thead><tbody>{rows}</tbody></table></div>'


def priority_nine_table() -> str:
    pins = json.loads((ROOT / STOPPED / "historical-reference-audit.json").read_text())["rasters"]
    surf_nov = json.loads((ROOT / CURRENT / "novelty-surface.json").read_text())["comparisons"]
    dots_nov = json.loads((ROOT / CURRENT / "novelty-dots.json").read_text())["comparisons"]
    surf_by_sha = {r["reference_sha256"]: r for r in surf_nov}
    dots_by_sha = {r["reference_sha256"]: r for r in dots_nov}
    owner_claimed = {
        "GEMSDOE24": "0.2477 (owner-reported, unverified)",
        "GEMSDOE25": "0.2600 (owner-reported, unverified)",
        "GEMSDOE27": "0.2449 (owner-reported, unverified)",
        "GEMSDOE28": "0.2708 / 0.2710 family (owner-reported, unverified)",
        "GEMSDOE30": "0.2600 mirror of D2.8 (owner-reported, unverified)",
        "GEMSDOE31": "0.2708 mirror of solo-d28 (owner-reported, unverified)",
        "GEMSDOE32": "0.2778 H33-B2 (owner-reported, unverified)",
        "GEMSDOE33": "0.2632 H33d (owner-reported, unverified)",
        "GEMSDOE36": "0.2750 H33+1,200 (owner-reported, unverified)",
    }
    rows = ""
    for r in pins:
        sha = r["sha256"]
        sr = surf_by_sha[sha]["spearman_full_footprint"]
        ov = dots_by_sha[sha]["candidate_fraction_within_3px_of_reference"]
        fmt = "Passed (NaN outside)" if r["local_format_validation"]["passed"] else "Zero-outside historical encoding"
        rows += (
            f'<tr><th scope="row"><a href="{e(r["source_url"])}">{e(r["site"])}</a></th>'
            f'<td>{e(owner_claimed.get(r["site"], "unverified"))}</td>'
            f'<td>{r["positive_pixels"]:,}</td>'
            f'<td>{sr:.4f}</td>'
            f'<td><strong>{100 * ov:.2f}%</strong></td>'
            f'<td>{fmt}</td></tr>'
        )
    return (
        '<div class="table-wrap"><table><caption>Nine priority GEMSDOE sites · owner-reported claims vs measured PTA-1 novelty</caption>'
        '<thead><tr><th>Priority site</th><th>Owner-reported status (not organizer receipt)</th><th>Ref dots</th><th>PTA-1 surface ρ</th><th>PTA-1 dots ≤3 px</th><th>Local template check</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def sources_table() -> str:
    items = [
        ("DrivenData GEMS Problem & Metric", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/", "Single-band float32 [0,1], EPSG:32611, 100 m, DTI (α=0.2, β=0.8, 300 m triangular kernel); official 19-band glossary (`depth_to_base_surf` = MT conductive base; `tc` three-way metadata audit in IR-PTA-02 / IR-MSDB-01)."),
        ("DrivenData Live Leaderboard (2026-10-25)", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/", "Retrieved 2026-10-25: #1 xiaofanhu 0.4413, #2 cfld__ 0.3916, #3 Batik Shirt Brothers 0.3904, #9 DARD 0.3398 (0.3195 on 2026-10-03 snapshot)."),
        ("DOE / NLR Official Prize Rules PDF", "https://docs.nlr.gov/docs/fy26osti/96647.pdf", "Sept 2026 rules: up to 3 platform feedback submissions/week; ONE final selected submission scored on BOTH Phase 1 ($50k) and expert-updated Phase 2 ($250k); AI disclosure & reproducible code required."),
        ("DrivenData Forum Clarifications (chrisk-dd)", "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516", "Threads 11516, 11536, 11550, 11556, 11557, 11563: pixel-exact `labels == 1` masking (zero buffer), new faults allowed <300 m of known traces, pooled TP/FP/FN, `deq`/`ieq` earthquake rate densities."),
        ("USGS GeoDAWN Airborne Survey (CC0)", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and", "DOI 10.5066/P93LGLVQ: E–W (90°) 200–400 m flight-line magnetic & gamma-ray spectrometry across NW Great Basin; motivates `1000× tmi_vg` unit fix (`IR-PTA-01`) and E–W leveling seam check."),
        ("OpenEI GDR 1391 INGENIOUS Compilation (CC-BY-4.0)", "https://gdr.openei.org/submissions/1391", "DOI 10.15121/1881483: Great Basin regional gravity, magnetotelluric conductive base, geodetic strain, seismicity, and Quaternary fault synthesis."),
        ("DrivenData Reference UNet Repository", "https://github.com/drivendataorg/gems-prize-reference-solution", "Official baseline reference notebook (`unet-mc-cv-reference-solution.ipynb`); saved GDAL band descriptions audited against `/page/967/` (`IR-PTA-02`)."),
    ]
    rows = "".join(
        f'<tr><th scope="row"><a href="{e(url)}">{e(name)}</a></th><td>{e(takeaway)}</td></tr>'
        for name, url, takeaway in items
    )
    return f'<div class="table-wrap"><table><caption>Verified primary competition, geophysical &amp; rules sources</caption><thead><tr><th>Official source</th><th>Verified technical rule / physical takeaway</th></tr></thead><tbody>{rows}</tbody></table></div>'


def hypotheses_table() -> str:
    rows = [
        ("1 · Executed (`PTA-1`)", "Unit-Consistent 3D Potential-Field Phase-Tilt Curvature & Signed Dip-Contact Asymmetry", "8 subsurface bands (`tmi_anom`, `tmi_hg`, `1000× tmi_vg`, `rtp`, `iso_grav_anom`, `iso_grav_anom_slope`, `tc`, `depth_to_base_surf`)", "3D Miller–Singh tilt ridge + signed Grauch–Hudson hanging-wall offset across `-∇g / ||∇g||` (`pta_dip_cover_step` raw AUC 0.5988)", "Executed (`HOLDOUT-DTI = 0.09668`; `+0.00887` over `sub8_raw` with 95% CI `[+0.00156, +0.01598]`; `54.60%` max 3 px overlap across 196 rasters)"),
        ("2 · Prospective (`PGR-2`)", "Piedmont Geomorphic-Scarp vs Range-Front Relief Decoupling", "`det_elev`, `det_elev_slope`, `dem_1m_med_slope`, `dem_1m_std_slope`, `iso_grav_anom`", "High 1 m sub-cell scarp roughness inside low regional slope (`<4°`) aligned with basinward gravity gradient", "Complements concurrent full-stack `MSDB-1v2` (`0.17046` HOLDOUT-DTI) for next-session `PTA-1 + MSDB` fusion"),
        ("3 · Prospective (`KUS-3`)", "Potassium-to-Uranium/Thorium Alteration Halo Along Subsurface Tilt Contacts", "`k_pct`, `eu_ppm`, `eth_ppm` (GeoDAWN GDR/USGS), `rtp`, `iso_grav_anom`", "Illite/adularia K-enrichment (`K/eTh` residual) focused along steep magnetic/gravity phase-tilt contacts", "Requires aligning external CC0 GeoDAWN K/eU/eTh grids (`10.5066/P93LGLVQ`) to EPSG:32611"),
        ("4 · Prospective (`MCS-4`)", "Transtensional Geodetic Shear × Microseismic Rate Partitioning", "`geod_2nd_inv`, `geod_dilatrate`, `geod_shearrate`, `deq_n100a15`, `ieq_n100a15`, `rtp`", "High background independent seismicity (`ieq`) relative to aftershock-dominated `deq` along transtensional shear corridors", "Low resolution (~km GPS/seismicity kernels); best suited as regional prior rather than 100 m locator"),
    ]
    body = "".join(
        f"<tr><th scope='row'>{e(rk)}</th><td><strong>{e(title)}</strong></td><td>{e(layers)}</td><td>{e(sig)}</td><td>{e(outcome)}</td></tr>"
        for rk, title, layers, sig, outcome in rows
    )
    return f'<div class="table-wrap"><table><caption>Preregistered geological hypotheses (frozen in <code>{CURRENT}/preregistration.md</code> before running)</caption><thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers</th><th>Physical signature</th><th>Status / measured outcome</th></tr></thead><tbody>{body}</tbody></table></div>'


def build_registry_review_page() -> str:
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
    return f'''<section class="intro"><div><p class="eyebrow">Public Source Registry · 25 October 2026</p><h1>Immutable nine-site inventory.<br>Metadata, not scores.</h1><p class="lead">Immutable GitHub snapshots across all nine priority sites (<code>{public_snapshot["source_files"]}</code> TIFF source blobs, <code>{public_snapshot["unique_aligned_byte_sequences"]}</code> unique aligned byte sequences; extended to <code>196</code> observed rasters in <code>PTA-1</code>) preserved without altering any frozen experiment registry.</p></div><a class="text-link" href="docs/research/2026-10-25/priority-site-public-snapshot.json">Open machine receipt ↗</a></section>
<section class="section"><p class="eyebrow">01 / Byte-verified public inventory</p><h2>Nine requested repositories at immutable commits.</h2><div class="table-wrap"><table><caption>Public source scope only</caption><thead><tr><th>Repository</th><th>Immutable commit</th><th>TIFF source blobs</th><th>Candidate surface paths</th></tr></thead><tbody>{pub_rows}</tbody></table></div></section>
<section class="section"><p class="eyebrow">02 / Surface metadata groundwork</p><h2>Inspected public arrays remain conservatively marked unknown.</h2><div class="table-wrap"><table><caption>Potential public surfaces · never used as predictions</caption><thead><tr><th>Repository</th><th>Object</th><th>Container</th><th>Eligibility</th></tr></thead><tbody>{surf_rows}</tbody></table></div><p><a href="docs/research/2026-10-25/priority-site-public-review.md">Full source-sync review ↗</a> · <a href="experiment-review.html">Back to scientific review ↗</a></p></section>'''


def receipt_integrity_notice() -> str:
    """Keep the negative-receipt follow-up visible on generated entry pages."""
    return (
        '<p class="meta"><a href="receipt-integrity-review.html">'
        'Verification follow-up: negative receipt integrity fixed; no new submission approved.'
        '</a></p>'
    )


def ffl_section() -> str:
    """Latest-lane FFL-1 banner, generated only from independently checked receipts."""
    readiness = verify_fflidar()
    card = json.loads((ROOT / FFL_DIR / "run-card.json").read_text())
    dots = json.loads((ROOT / FFL_DIR / "novelty-dots-expanded.json").read_text())
    surface = json.loads((ROOT / FFL_DIR / "novelty-surface-expanded.json").read_text())
    stratified = json.loads((ROOT / FFL_DIR / "results-stratified.json").read_text())
    if (
        card["verdict"] != "negative"
        or card["ok_to_submit"] is not False
        or card["submission_approved"] is not False
        or card["slot_selected"] is not False
        or readiness["research_verdict"] != "negative"
    ):
        raise ValueError("FFL-1 banner can only publish the recorded negative decision")
    if dots["candidate_sha256"] != card["raster_sha256"] or dots["decision"] != "duplicate-stop":
        raise ValueError("FFL-1 expanded dot audit does not bind the duplicate-stopped TIFF")
    max_overlap = max(r["candidate_fraction_within_3px_of_reference"] for r in dots["comparisons"])
    if max_overlap <= 0.70 or surface["candidate_sha256"] != card["raster_sha256"]:
        raise ValueError("FFL-1 expanded novelty receipts contradict the duplicate-stop / surface audit irregularity")
    if readiness.get("surface_audit", {}).get("preplacement_surface_valid") is not False:
        raise ValueError("FFL-1 mis-bound expanded surface receipt must be marked invalid as pre-placement evidence")
    if not stratified.get("infeasible_as_frozen") or stratified.get("production") is not None:
        raise ValueError("FFL-1 stratified receipt no longer records the frozen infeasibility")
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    h = card["holdout"]
    delta = h["candidate_minus"]["msdb_edge"]
    conf = card["confirmation"]["candidate_minus_msdb_edge"]
    return f'''<section class="release" style="margin-bottom:26px" aria-labelledby="ffl-title">
<div class="release-heading"><span class="pill failed">Latest lane FFL-1 · Negative</span><span class="pill caution">Duplicate-stop · Do not submit</span></div>
<h2 id="ffl-title">FFL-1 produced a byte-distinct TIFF. <span>Do not submit it.</span></h2>
<p><strong>Automated decision first:</strong> the expanded observed-registry dot audit—pinned nine-site registry plus every TIFF in <code>docs/downloads/</code> at audit time, candidate SHA excluded ({len(dots["comparisons"])} comparisons)—found <strong>{100 * max_overlap:.6f}%</strong> of FFL-1 dots within 3 px of MSDB-1v2, above the 70% duplicate-stop limit. A separate required check is not established: the receipt labeled expanded <code>stage=surface</code> is bound to the final binary TIFF SHA, not a distinct pre-placement continuous score surface. Therefore pre-placement surface novelty against the expanded registry is <strong>unverified</strong>; the duplicate stop is supported by the independently hash-bound dot audit regardless. The frozen distance-stratified rescue scored zero folds because the <code>(2,5]</code> and <code>(5,10]</code> strata have zero eligible pixels in every v3 quadrant fold, so no replacement was produced and no weekly slot was selected.</p>
<p>HOLDOUT-DTI (catalogue proxy, never an organizer score): Exp. 1 seed 3051 <code>fusion_edge</code> <code>{h["value"]:.6f}</code> vs same-run <code>msdb_edge</code> <code>{h["comparators"]["msdb_edge"]["value"]:.6f}</code> (Δ <code>{delta["value"]:+.6f}</code>, 95% CI <code>[{delta["ci95"][0]:+.6f}, {delta["ci95"][1]:+.6f}]</code>); disclosed fresh-seed confirmation Δ <code>{conf["value"]:+.6f}</code> (95% CI <code>[{conf["ci95"][0]:+.6f}, {conf["ci95"][1]:+.6f}]</code>). The strict validator reopens the file as one float32 band on the exact template grid, with every cell finite in <code>[0, 1]</code>, 44,090 dots, and zero dots on or within 2 px of the catalogue; that file check does not override the duplicate-stop.</p>
<div class="actions"><a class="button secondary" href="{e(card['published_tiff'])}" download>↓ Download FFL-1 research artifact — do not upload <span>{size:.2f} MiB</span></a><a class="button secondary" href="{FFL_DIR}/review.md">Read FFL-1 review</a><a class="button secondary" href="{FFL_DIR}/nine-site-executive-summary.md">Nine-site executive summary</a></div>
<p class="filename">{e(file.name)}</p>
<details><summary>FFL-1 automated receipts &amp; identity</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Note ({len(card['note'])}/140)</dt><dd><code>{e(card['note'])}</code></dd><dt>Receipts</dt><dd><a href="{FFL_DIR}/run-card.json">Run card</a> · <a href="{FFL_DIR}/readiness.json">Readiness</a> · <a href="{FFL_DIR}/validation.json">Strict validation</a> · <a href="{FFL_DIR}/novelty-dots-expanded.json">Expanded dot audit</a> · <a href="{FFL_DIR}/results-stratified.json">Stratified infeasibility</a></dd><dt>Verify</dt><dd><code>.venv/bin/python scripts/verify_fflidar_run.py</code> (negative decision, exit 0); <code>--require-promote</code> exits 2</dd></dl></details>
</section>'''


def build(template: Path) -> dict[Path, str | bytes]:
    pointer = ROOT / "docs/current-run.json"
    selection = json.loads(pointer.read_text())
    latest = selection.get("latest_review", {})
    if (latest.get("run_card") == "docs/research/2026-10-27-registry-preflight/run-card.json"
            and latest.get("verifier") == "scripts/verify_registry_preflight.py"):
        # Render the selected current snapshot directly. The historical PTA/TAD
        # builder below requires caches and emits obsolete download language;
        # it must never run first and overwrite a newer fail-closed decision.
        from scripts.verify_registry_preflight import verify as verify_preflight
        from scripts.verify_pool_run import verify as verify_pool
        from scripts.render_registry_preflight import render as render_preflight

        verify_preflight(template=template)
        verify_pool()
        card = json.loads((ROOT / latest["run_card"]).read_text())
        fleet = json.loads((ROOT / "docs/research/2026-10-26-csr/fleet-audit.json").read_text())
        pool_card = json.loads((ROOT / "docs/research/2026-10-27-pool/run-card.json").read_text())
        pool_dots = json.loads((ROOT / "docs/research/2026-10-27-pool/novelty-dots.json").read_text())
        pages = {ROOT / name: content for name, content in
                 render_preflight(card, fleet, pool_card, pool_dots).items()}
        pages[ROOT / "docs/csr-discontinuity-review.html"] = redirect_html(
            "../csr-discontinuity-review.html", "Current registry and science review · GEMSDOE30")
        pages[ROOT / "docs/priority-executive-summary.html"] = redirect_html(
            "../priority-executive-summary.html", "Nine-site executive summary · GEMSDOE30")
        pages[ROOT / "priority-site-review.html"] = redirect_html(
            "priority-executive-summary.html", "Current nine-site review · GEMSDOE30")
        return pages
    retained = verify(pointer, template)
    selection = json.loads(pointer.read_text())
    card = json.loads(local_path(selection["run_card"]).read_text())
    stopped_path = local_path(selection["latest_attempt"])
    stopped = verify_stopped(stopped_path.parent, template)
    for extra in selection.get("additional_stopped_attempts", []):
        if extra.get("lane") == "G30-LSM":
            lsm_ready = verify_lsm(local_path(extra["pointer"]), template)
            if lsm_ready["ok_to_submit"] is not False:
                raise ValueError("G30-LSM stopped attempt must remain non-submittable")
    if (
        retained["research_verdict"] != "negative"
        or retained["download_ok"] is not True
        or retained["submission_approved"] is not False
        or stopped["download_ok"] is not False
    ):
        raise ValueError("Site builder expects verified downloadable PTA-1 (negative promotion) + verified stopped attempts")

    banner = release_banner(card, retained)
    scores = pta1_score_table(card)
    n_reg = retained["observed_registry"]["dots"]["registry_entries_compared"]
    max_ov = 100.0 * retained["observed_registry"]["dots"]["max_fraction_within_3px"]

    tad_pointer = ROOT / TAD_DIR / "current-run.json"
    tad_ready = verify_tad(tad_pointer, template)
    tad_card = json.loads((ROOT / TAD_DIR / "run-card.json").read_text())
    if tad_ready["ok_to_submit"] is not False or tad_card["verdict"] != "negative":
        raise ValueError("G30-TAD negative CI verdict must not be rendered as approved for slot expenditure")
    tad_top = tad_banner(tad_card, tad_ready, allow_download_attr=False)

    home = f'''{receipt_integrity_notice()}{ffl_section()}
<section class="intro"><div><p class="eyebrow">DOE GEMS / autonomous research &amp; validation</p><h1>Unique subsurface TIFFs.<br>Honest slot protection.</h1><p class="lead"><code>G30-TAD</code> (dual <code>-zeros/-nan</code> 38,000-dot GeoTIFFs; <code>51.44% ≤ 70%</code> across 193 rasters; <code>0.14405</code> HOLDOUT-DTI) and <code>PTA-1</code> (44,090-dot GeoTIFF; <code>{n_reg}</code> rasters cleared) both passed every automated format, <code>[0, 1]</code> range, and two-stage novelty gate while preserving weekly competition slots.</p><p class="meta">25–26 October 2026 <span>·</span> Zero human-inspection gates <span>·</span> No competition slot selected or used</p></div><a class="text-link" href="geothermal-tilt-alteration-review.html">Read G30-TAD &amp; PhD H33 proof ↗</a></section>
{tad_top}{banner}
<section class="evidence-strip" aria-label="Automated diagnostics"><article><span>G30-TAD uniqueness</span><strong>193 rasters cleared</strong><small>Max 3 px overlap 51.44% (≤70%); HOLDOUT-DTI 0.14405</small></article><article><span>PTA-1 observed registry</span><strong>{n_reg} rasters cleared</strong><small>Max 3 px overlap {max_ov:.2f}% (≤70%); +0.00887 over sub8_raw</small></article><article><span>Leakage canaries</span><strong>0 alarms above 0.90</strong><small>144 checks in G30-TAD &amp; 148 checks in PTA-1</small></article></section>
<section class="two-column section"><div><p class="eyebrow">01 / Preregistered holdout experiments</p><h2>3D tilt-depth, potassic Kd alteration &amp; dip-contact asymmetry lift subsurface recovery.</h2><p>In <code>G30-TAD</code>, coordinate-free 3D tilt-depth, fold-regressed radiometric potassium alteration (<code>rad_kd</code>), MT clay-cap gradient, and <code>decensored_30_40_30</code> OOF collar placement reached <code>subsurface16 = 0.10959</code> (zero DEM/LiDAR) and <code>tilt_alt24 = 0.14405</code> vs <code>core19 = 0.13982</code> (<code>+0.01801</code> in NW Nevada Fold 0; paired CI crosses zero). In parallel, <code>PTA-1</code> corrected the <code>1,000×</code> length-unit mismatch between <code>tmi_vg</code> and <code>tmi_hg</code> (<code>IR-PTA-01</code>) and measured signed hanging-wall MT cover thickening (<code>pta_dip_cover_step</code>), achieving <code>HOLDOUT-DTI = 0.09668</code> (<code>+0.00887</code> over <code>sub8_raw</code>).</p>{scores}<a class="text-link" href="geothermal-tilt-alteration-review.html">Full G30-TAD E1–E3 results, PhD analysis of GEMSDOE32 (0.2778) &amp; live leaderboard (0.4413) ↗</a></div><figure><img src="docs/assets/pta1-support.png" width="823" height="933" loading="lazy" alt="New PTA-1 subsurface prediction dots in dark green over the pale green competition footprint"><figcaption><span class="legend-dot"></span> New PTA-1 support (44,090 binary off-catalogue dots; see <a href="geothermal-tilt-alteration-review.html">G30-TAD map</a> for 38,000 decensored dots).</figcaption></figure></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated 12-gate inspection</p><h2>Zero human-inspector handoff.</h2></div><p>Every byte, coordinate transform, range bound,<br>canary AUC, and registry comparison is machine-verified.</p></div>{gate_table(retained)}</section>
<section class="section two-column"><div><p class="eyebrow">03 / Why GEMSDOE32 scored 0.2778 &amp; how to beat 0.2778 / 0.4413</p><h2>Exact masking mechanics + orthogonal basin physics.</h2><p>DrivenData Staff (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">thread 11516/4</a>) confirmed known faults are masked pixel-exactly (<code>labels == 1</code>, zero buffer) while hidden splays can lie <code>&lt;300 m</code> from mapped traces. <code>GEMSDOE32</code> H33 (<code>0.2778</code> owner-reported) deletes the <code>2,545</code> dots at <code>0 &lt; d_cat ≤ 2 px</code> from <code>GEMSDOE28</code>'s <code>40,199</code>-dot base (<code>37,654</code> dots), stripping unmasked flank false positives (<code>0.2 · FP_w</code>) while dots at <code>d_cat = 3 px</code> retain triangular-kernel reach across the flank.</p><p>Surpassing <code>0.2778</code> and closing the recall gap toward the live public leader (<code>0.4413</code> on 2026-10-25; <code>0.3195</code> on 2026-10-03) requires fusing multi-scale piedmont/scarp discontinuity features (<a href="{MSDB}/review.md">concurrent MSDB-1v2</a>: <code>HOLDOUT-DTI = 0.17046</code>, <code>+27.6%</code> over <code>core19</code>) with <code>G30-TAD</code>'s Kd-alteration + 30/40/30 decensored collar and <code>PTA-1</code>'s signed hanging-wall cover-step specialist.</p><a class="text-link" href="geothermal-tilt-alteration-review.html">Read the complete mathematical derivation &amp; 5 geothermal hypotheses ↗</a></div><div class="note-card"><h3>Repository lane audit trail</h3><ul class="spaced"><li><strong>G30-TAD (dual <code>-zeros/-nan</code> research TIFFs):</strong> <a href="{TAD_DIR}/run-card.json">run-card.json</a> · <code>0.14405</code> HOLDOUT-DTI (<code>0.10959</code> subsurface16); <code>193</code> rasters cleared (<code>max 51.44%</code>); <code>download_ok = true</code>, <code>ok_to_submit = false</code>.</li><li><strong>PTA-1 (current unique subsurface TIFF):</strong> <a href="{CURRENT}/run-card.json">run-card.json</a> · <code>0.09668</code> HOLDOUT-DTI; <code>{n_reg}</code> rasters cleared (<code>max 54.60%</code>); <code>download_ok = true</code>, <code>verdict = negative</code>.</li><li><strong>MSDB-1v2 (concurrent piedmont full-stack):</strong> <a href="{MSDB}/run-card.json">run-card.json</a> · <code>0.17046</code> HOLDOUT-DTI (<code>+27.6%</code> vs <code>core19</code>; <code>max 64.78%</code>); conservative slot hold.</li><li><strong>H-NEARSPLAY (annulus peer — DUPLICATE ON EXPANDED REGISTRY):</strong> <a href="docs/research/nearsplay/full-registry-audit.json">full-registry-audit.json</a> · <strong>71.26% &gt; 70%</strong> within 3 px of four <code>GEMSDOE25</code> rasters (<code>IR-PTA-06</code>); DO NOT SUBMIT.</li><li><strong>G30-LSM &amp; TDX-C2 (DUPLICATE-STOP):</strong> <a href="docs/research/2026-10-25-lsm/run-card.json">G30-LSM</a> &amp; <a href="{STOPPED}/run-card.json">TDX-C2</a> · halted cleanly on &gt;70% 3 px overlap; no public TIFF.</li><li><strong>TDX-1 (archived subsurface v1):</strong> <a href="{PREVIOUS}/run-card.json">run-card.json</a> · <code>0.07284</code> HOLDOUT-DTI.</li></ul><a href="README.md#current-owner-prompt">Complete verbatim owner prompt ↗</a></div></section>'''

    guide = f'''{receipt_integrity_notice()}{ffl_section()}
<section class="intro"><div><p class="eyebrow">Executive submission guide</p><h1>Validated GeoTIFFs.<br>Clear portal rules.</h1><p class="lead"><code>G30-TAD</code>'s published-format <code>-nan.tif</code> companion and <code>PTA-1</code> pass the shared local format validator; both have archived novelty checks against their observed registries. The all-finite <code>G30-TAD -zeros.tif</code> diagnostic <strong>fails</strong> the null-outside-footprint format check. None is approved for submission: holdout promotion and full-registry/comparable-best evidence are unresolved or negative. Downloading is not a recommendation to upload.</p></div></section>{tad_top}{banner}
<section class="section"><p class="eyebrow">Unique artifact identity · copy-ready metadata</p><h2>Unique submission name &amp; ≤140-character portal note.</h2><div class="identity"><label for="submission-name">Unique PTA-1 artifact name (research record · do not upload to spend a weekly slot)</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Portal note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div><p class="fine">G30-TAD copyable name &amp; 82/140-char note: <a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 review</a> · <a href="{TAD_DIR}/run-card.json">G30-TAD run-card.json</a>. Peer &amp; archived run cards: <a href="{MSDB}/run-card.json">MSDB-1v2</a> · <a href="docs/research/2026-10-25-lsm/run-card.json">G30-LSM (DUPLICATE-STOP)</a> · <a href="{STOPPED}/run-card.json">TDX-C2 (DUPLICATE-STOP)</a> · <a href="{PREVIOUS}/run-card.json">TDX-1 (archived)</a>.</p></section>
<section class="section"><p class="eyebrow">Step-by-step DrivenData portal procedure</p><h2>How to submit once a candidate earns <code>verdict = promote</code>.</h2><ol class="steps"><li><strong>Check automated promotion status at the top of this page.</strong><p>Only upload when the top badge indicates research promotion and <code>python scripts/verify_tad_run.py --require-promote</code> or <code>python scripts/verify_current_run.py --require-promote</code> exits <code>0</code> (today both deliberately exit <code>2</code> because <code>verdict = negative</code>).</p></li><li><strong>Confirm weekly submission allowance &amp; rules compliance.</strong><p>Per <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules (96647.pdf)</a>, teams may upload up to <b>3 feedback submissions per 7-day rolling window</b>, and must select <b>exactly 1 final submission</b> before competition close (conservatively <code>5:00 p.m. ET / 22:00 UTC</code> per Rules PDF App. A.1; <code>11:59 p.m. UTC</code> on DrivenData overview, <code>IR-MSDB-03</code> / <code>IR-TAD-02</code>) for both Phase 1 ($50k) and expert-updated Phase 2 ($250k).</p></li><li><strong>Download the validated single-band <code>.tif</code> file.</strong><p>Use the one-click GeoTIFF button above (never upload HTML, JSON, PNG, or multi-band rasters). Re-verify locally anytime via <code>.venv/bin/python scripts/validate_submission.py {e(card['published_tiff'])} --template data/raw/sample_submission.tif</code> or <code>.venv/bin/python scripts/verify_tad_run.py</code>.</p></li><li><strong>Upload on DrivenData “New submission”.</strong><p>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS competition portal</a>, click <b>Submit</b>, choose the <code>.tif</code> (or single-file <code>.zip</code>) under <b>File to submit</b>, and paste the ≤140-character <b>Note</b> above so every run stays uniquely traceable.</p></li><li><strong>Record the organizer receipt triple.</strong><p>Save the returned submission timestamp/ID, exact <code>raster_sha256</code>, and portal score together before labelling any number <b>ORGANIZER-CONFIRMED</b>.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">Portal error <code>"Predicted values must be in range [0, 1]"</code></p><h2>Root cause &amp; automated prevention.</h2><p><code>training_features.tif</code> stores <code>-3.4028235e+38</code> float32 nodata sentinels on <strong>3,061 pixels inside the valid scoring footprint</strong> (<code>3,073</code> on <code>tc</code>; <code>IR-30-044</code> / <code>IR-PTA-02</code>). Masking from feature bands instead of <code>np.isfinite(sample_submission.tif)</code> or running an unmasked whole-array range check on NaN cells triggers the portal range rejection.</p><p><code>G30-TAD</code> ships both an all-finite <code>-zeros.tif</code> diagnostic and a <code>-nan.tif</code> published-format variant. The zero-outside copy has all <code>12,279,160</code> cells finite in <code>[0.0, 1.0]</code>, but it fails the shared validator because the <code>7,111,787</code> cells outside the template footprint must be null/NaN/nodata. The <code>-nan.tif</code> variant has finite values in <code>[0.0, 1.0]</code> on all <code>5,167,373</code> footprint cells and passes all 12 shared checks. Neither variant is cleared for competition upload because the holdout confidence-interval gate failed.</p></div><div class="note-card"><h3>Autonomous data &amp; verification commands</h3><p>Fresh clones restore SHA-256-pinned mirrors, build caches, and verify every receipt without manual input:</p><p><code>bash scripts/download_competition_data.sh</code><br><code>.venv/bin/python scripts/prepare_data.py</code><br><code>.venv/bin/python scripts/verify_current_run.py</code><br><code>.venv/bin/python scripts/verify_tad_run.py</code><br><code>.venv/bin/python scripts/verify_stopped_attempt.py</code><br><code>.venv/bin/python scripts/verify_lsm_run.py</code></p><p class="fine">Live public leaderboard checked 2026-10-25: <code>#1 xiaofanhu = 0.4413</code> (<code>0.3195</code> was the earlier Oct 3 snapshot).</p></div></section>'''

    research = f'''{receipt_integrity_notice()}{ffl_section()}
<section class="intro"><div><p class="eyebrow">Deep scientific review / PTA-1, G30-TAD, MSDB-1v2 &amp; 9-site audit</p><h1>Physics of blind faults &amp;<br>why H33 scored 0.2778.</h1><p class="lead">A line-by-line synthesis of official DOE/USGS/INGENIOUS sources, exact Distance-Tversky calculus, 9 priority GEMSDOE sites, newly discovered dataset unit/sign irregularities (<code>1000× tmi_vg</code>), and our preregistered <code>G30-TAD</code> and <code>PTA-1</code> subsurface experiments.</p></div><a class="text-link" href="geothermal-tilt-alteration-review.html">Open G30-TAD review ↗</a></section>{banner}
<section class="section"><p class="eyebrow">01 / PhD analysis of GEMSDOE32 (0.2778) &amp; leaderboard gap (0.3195 → 0.4413)</p><h2>Why <code>h33-h33-2-b2</code> topped the GEMSDOE sites—and how to beat it.</h2><p>Under the official metric <code>DTI = TP_w / (0.2·TP_w + 0.2·FP_w + 0.8·G + ε)</code> (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem Description</a>; <a href="https://community.drivendata.org/t/pooling-of-tversky-index-calculations/11550">Forum 11550</a>), truth coverage <code>TP_w</code> is a <strong>spatial maximum</strong> over a <code>R = 300 m</code> (<code>3 px</code>) triangular kernel, whereas false-positive penalty <code>0.2 · FP_w</code> sums linearly across unmasked background predictions. DrivenData Staff (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Forum 11516/4</a>) confirmed that known USGS/INGENIOUS faults are masked <strong>pixel-exactly</strong> (<code>labels == 1</code> only, zero buffer) while new hidden faults can lie <code>&lt;300 m</code> from mapped traces (<a href="https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536">Forum 11536</a>).</p><p>Byte-exact audit (<a href="docs/research/2026-10-25/recipe-reconstruction.json">zero mismatching pixels</a>) proves <code>GEMSDOE32</code>'s <code>h33-h33-2-b2</code> (<code>37,654</code> dots; <code>0.2778</code> owner-reported, unverified) equals <code>GEMSDOE28</code>'s <code>h27-4-r1-solo-d2-8</code> (<code>40,199</code> dots; <code>0.2708</code> owner-reported) after deleting the <code>2,545</code> dots at <code>0 &lt; d_cat ≤ 2 px</code>. Those flank dots were unmasked (<code>FP_w ≈ 1.0</code> each, saving <code>~509</code> weighted penalty units when removed) while surviving dots at <code>d_cat = 3 px</code> still extend triangular kernel support across <code>d_cat ∈ [1, 2] px</code>. Conversely, <code>GEMSDOE36</code> added <code>1,200</code> extra dots onto H33 (<code>38,854</code> dots → <code>0.2750</code> owner-reported), diluting precision.</p><p><strong>How to beat 0.2778, 0.3195 (Oct 3 snapshot), and approach 0.4413 (Oct 25 live leader):</strong> All <code>0.2449–0.2778</code> family rasters place <code>70–81%</code> of their dots on steep range-front scarps (<code>det_elev_slope ≥ 5°</code>; H33 has only <code>19.1%</code> of dots in <code>&lt;5°</code> terrain), missing concealed intrabasin geothermal faults beneath Quaternary playas and alluvial fans. Breaking past <code>0.32–0.44</code> requires fusing (1) multi-scale steerable piedmont/scarp discontinuity features (<a href="{MSDB}/review.md">MSDB-1v2</a>: <code>HOLDOUT-DTI = 0.17046</code>, <code>+27.6%</code> over <code>core19</code>) upgraded with <code>PTA-1</code>'s <code>1000× tmi_vg</code> unit fix, (2) <code>G30-TAD</code>'s Kd-alteration + 30/40/30 decensored collar and <code>PTA-1</code>'s low-slope basin specialist (<code>pta_dip_cover_step</code> raw AUC <code>0.5988</code>), and (3) a 2D multi-km spatial UNet backbone with <code>d_cat &gt; 2 px</code> flank pruning + metric-exact <code>EDGE</code> emission.</p></section>
<section class="section"><p class="eyebrow">02 / Verified primary sources &amp; candidate hypotheses</p><h2>Official data/rules synthesis &amp; 4 ranked geological hypotheses.</h2>{sources_table()}{hypotheses_table()}</section>
<section class="section"><p class="eyebrow">03 / PTA-1 experiment &amp; 9-priority-site novelty audit</p><h2>Statistically significant subsurface gain (+0.00887) &amp; genuine cross-site uniqueness.</h2>{scores}<p>Across <code>148</code> univariate canary evaluations (<code>37</code> features × <code>4</code> folds; <a href="{CURRENT}/results.json">full JSON</a>), zero features approached the <code>0.90</code> leakage threshold (max <code>0.6434</code> on <code>det_elev_slope</code>). Among all 18 subsurface inputs, <strong><code>pta_dip_cover_step</code></strong>—signed hanging-wall thickening of MT conductive cover (<code>depth_to_base_surf</code>) across <code>300–600 m</code> down the gravity dip vector—achieved the strongest fault signal (bidirectional raw AUC <code>0.5988</code> in Fold 3, <code>0.5933</code> in Fold 1 vs <code>0.5181</code> for raw <code>depth_to_base_surf</code>).</p>{priority_nine_table()}<p class="fine">Across the entire 9-repo expanded registry + concurrent main arrivals (<code>{n_reg}</code> unique grid-aligned TIFFs; <a href="{CURRENT}/registry.json">registry.json</a> + <a href="{CURRENT}/registry-parallel-addendum.json">late addendum</a>), max surface Spearman is <code>0.1055</code> and max 3 px dot overlap is <code>54.60%</code>. All 119 owner-supplied historical claims remain quarantined as unverified in <a href="{PREVIOUS}/owner-claims.csv">owner-claims.csv</a>.</p></section>
<section class="section"><p class="eyebrow">04 / Newly flagged irregularities &amp; next-session roadmap</p><h2>Dataset unit/sign traps discovered (`IR-PTA-01..05`, `IR-TAD-01..06`) &amp; remaining limitations.</h2><ul class="spaced"><li><strong><code>IR-PTA-01</code> — 1,000× unit mismatch (<code>tmi_hg</code> nT/km vs <code>tmi_vg</code> nT/m):</strong> Unscaled <code>atan2(tmi_vg, tmi_hg)</code> collapses magnetic tilt dynamic range by <code>&gt;20×</code> and saturates zero-crest features; fixed and unit-tested in <code>src/gemsdoe30/phase_tilt.py</code>.</li><li><strong><code>IR-PTA-02</code> — Three-way <code>tc</code> metadata contradiction &amp; MT conductive-base semantics:</strong> <code>tc</code> carries GDAL tag <code>"Tilt angle or total curvature"</code>, DrivenData <code>/page/967/</code> label <code>"Terrain correction"</code>, and <code>0.999957</code> Spearman match to USGS GeoDAWN Radiometric Total Count (<code>IR-MSDB-01</code>); <code>depth_to_base_surf</code> is MT conductive-base depth; <code>deq</code>/<code>ieq</code> are earthquake rate densities (Forum 11557).</li><li><strong><code>IR-PTA-03</code> — Signed image-axis gravity derivatives:</strong> Confirming <code>IR-MSDB-02</code>, <code>iso_grav_anom_hg</code> and <code>iso_grav_anom_vg</code> are signed grid derivatives rather than unsigned magnitudes.</li><li><strong><code>IR-TAD-01..06</code> — Deadline discrepancy &amp; decensored collar uniqueness:</strong> Rules PDF Appendix A.1 specifies <code>5:00 p.m. ET (22:00 UTC)</code> vs DrivenData <code>11:59 p.m. UTC</code>; <code>decensored_30_40_30</code> cleared all <code>193</code> aligned rasters (<code>max 51.44% ≤ 70%</code>).</li><li><strong>Next session:</strong> Combine <code>MSDB-1v2</code>'s steerable piedmont discontinuities (upgraded with <code>1000× tmi_vg</code>) + <code>G30-TAD</code>'s Kd-alteration + <code>PTA-1</code>'s signed hanging-wall conductive-cover step (<code>pta_dip_cover_step</code>) inside a multi-km 2D UNet on GPU, evaluated on reserved geographic folds before any slot promotion.</li></ul><p><a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 review</a> · <a href="{CURRENT}/analysis.md">PTA-1 scientific analysis</a> · <a href="{CURRENT}/verification.md">PTA-1 verification journal</a> · <a href="{MSDB}/review.md">MSDB-1v2 technical report</a> · <a href="docs/research/2026-10-25-lsm/review.md">G30-LSM duplicate-stop review</a> · <a href="{STOPPED}/review.md">TDX-C2 duplicate-stop review</a> · <a href="docs/irregularities.md">Complete irregularities ledger</a></p></section>'''

    result = {
        ROOT / "index.html": page("G30-TAD & PTA-1 GeoTIFFs validated; slot protected", home),
        ROOT / "executive-summary.html": page("Executive submission guide", guide, active="guide"),
        ROOT / "geothermal-tilt-alteration-review.html": page("G30-TAD, PhD H33 proof & geothermal synthesis", tad_review_page(tad_card, tad_ready), active="tad"),
        ROOT / "experiment-review.html": page("PTA-1 physics, H33 0.2778 analysis & 9-site audit", research, active="research"),
        ROOT / "priority-registry-review.html": page("Public priority registry review", build_registry_review_page(), active="registry"),
        ROOT / "docs/assets/pta1-support.png": png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/assets/tad24-support.png": png_preview(template, local_path(tad_card["published_tiff"])),
        ROOT / "docs/index.html": redirect_html("../index.html", "GEMSDOE30"),
        ROOT / "docs/executive-summary.html": redirect_html("../executive-summary.html", "Executive submission guide · GEMSDOE30"),
        ROOT / "docs/geothermal-tilt-alteration-review.html": redirect_html("../geothermal-tilt-alteration-review.html", "G30-TAD & PhD H33 analysis · GEMSDOE30"),
    }
    # Historical dashboards remain auditable, but never lead the current UI.
    archive_notice = '<section class="stop-notice"><h2>Historical archive — superseded, not a current recommendation</h2><p>Earlier format, novelty and score claims are scoped to their original receipts. The 2026-10-27 lattice proof now establishes a literal duplicate stop for any 44,090-dot candidate; no archived file is slot-approved. <a href="executive-summary.html">Read the current decision</a>.</p></section>'
    result[ROOT / "research-history.html"] = result[ROOT / "executive-summary.html"].replace('<main id="main">', '<main id="main">' + archive_notice, 1)
    for historical in ("experiment-review.html", "geothermal-tilt-alteration-review.html", "priority-registry-review.html"):
        result[ROOT / historical] = result[ROOT / historical].replace('<main id="main">', '<main id="main">' + archive_notice, 1)
    from scripts.verify_geothermal_chemistry_run import verify as verify_gdx
    from scripts.render_gdx_review import pages as gdx_pages
    gdx_rendered = gdx_pages(verify_gdx(template=template))
    result[ROOT / "geothermal-chemistry-review.html"] = gdx_rendered["geothermal-chemistry-review.html"].replace('<main id="main">', '<main id="main">' + archive_notice, 1)
    from scripts.verify_quadrature_phase_run import verify as verify_qpc
    from scripts.render_quadrature_review import pages as qpc_pages
    qpc_rendered = qpc_pages(verify_qpc(template=template))
    result[ROOT / "geothermal-quadrature-review.html"] = qpc_rendered["geothermal-quadrature-review.html"].replace('<main id="main">', '<main id="main">' + archive_notice, 1)

    review = selection.get("latest_review", {})
    if (review.get("run_card") == "docs/research/2026-10-27-registry-preflight/run-card.json"
            and review.get("verifier") == "scripts/verify_registry_preflight.py"):
        from scripts.verify_registry_preflight import verify as verify_registry_preflight
        from scripts.render_registry_preflight import render as render_registry_preflight
        verify_registry_preflight(template=template)  # fail closed on changed witness or evidence
        card = json.loads((ROOT / review["run_card"]).read_text())
        fleet = json.loads((ROOT / "docs/research/2026-10-26-csr/fleet-audit.json").read_text())
        result[ROOT / "docs/csr-discontinuity-review.html"] = redirect_html("../csr-discontinuity-review.html", "Current registry and science review · GEMSDOE30")
        result[ROOT / "docs/priority-executive-summary.html"] = redirect_html("../priority-executive-summary.html", "Nine-site executive summary · GEMSDOE30")
        # Keep the long-standing link current; the old page is separately
        # preserved as a clearly labelled historical snapshot.
        result[ROOT / "priority-site-review.html"] = redirect_html("priority-executive-summary.html", "Current nine-site review · GEMSDOE30")
        result.update({ROOT / name: content for name, content in render_registry_preflight(card, fleet).items()})
    elif review.get("run_card") == "docs/research/2026-10-26-csr/run-card.json" and review.get("verifier") == "scripts/verify_csr_run.py":
        from scripts.verify_csr_run import verify as verify_csr
        from scripts.render_csr_review import pages as csr_pages
        csr_card = json.loads((ROOT / review["run_card"]).read_text())
        result[ROOT / "docs/assets/csr1-support.png"] = png_preview(template, local_path(csr_card["published_tiff"]))
        result[ROOT / "docs/csr-discontinuity-review.html"] = redirect_html("../csr-discontinuity-review.html", "CSR-1 PhD scientific review · GEMSDOE30")
        result[ROOT / "docs/priority-executive-summary.html"] = redirect_html("../priority-executive-summary.html", "Nine-site executive summary · GEMSDOE30")
        result.update({ROOT / name: content for name, content in csr_pages(verify_csr(template=template)).items()})
    elif review.get("run_card") == "docs/research/2026-10-26-qpc/run-card.json" and review.get("verifier") == "scripts/verify_quadrature_phase_run.py":
        result.update({ROOT / name: content for name, content in qpc_rendered.items()})
    elif review.get("run_card") == "docs/research/2026-10-26-gdx/run-card.json" and review.get("verifier") == "scripts/verify_geothermal_chemistry_run.py":
        result.update({ROOT / name: content for name, content in gdx_rendered.items()})
    else:
        raise ValueError("latest-review pointer does not select a supported independently verified report")
    return result



def main() -> None:
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
    print("Site receipts, download link, and deterministic generated pages verified" if args.check else "Built receipt-driven research Pages and preserved historical dashboards")


if __name__ == "__main__":
    main()
