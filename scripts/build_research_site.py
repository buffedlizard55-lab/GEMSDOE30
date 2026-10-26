#!/usr/bin/env python3
"""Deterministic Pages release from inspected PTA-1 artifact, 194-raster novelty receipts, and archived run records.

Re-inspects the current unique downloadable PTA-1 GeoTIFF (`download_ok = true`,
`verdict = negative`, `submission_approved = false`) and the archived TDX-C2
stopped-attempt receipts before writing `index.html`, `executive-summary.html`,
`experiment-review.html`, `docs/index.html`, and `docs/assets/pta1-support.png`.
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

STYLE = "docs/assets/research.css"
CURRENT = "docs/research/phase-tilt-asymmetry"
PREVIOUS = "docs/research/texture-displacement"
STOPPED = "docs/research/texture-controls"


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
            ("research", "experiment-review.html", "Deep research & audit"),
        )
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="DOE GEMS concealed-fault discovery: unique PTA-1 GeoTIFF validated across 194 registry rasters, automated submission gates, H33 0.2778 mathematical analysis, and cross-site audit.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a><header class="site-header"><div class="nav-wrap">
<a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a><nav aria-label="Main navigation">{nav}<a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main><footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated file validation and scientific slot promotion are distinct machine-verified gates.</p></div>
<div><a href="docs/status.json">Live status feed (JSON)</a><a href="{CURRENT}/run-card.json">PTA-1 run card (JSON)</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Repository evidence, not a live leaderboard scraper. No competition slot selected or used. PTA-1 GeoTIFF passed all local format and 194-raster uniqueness checks (`download_ok = true`), while competition slot promotion remains withheld (`verdict = negative`).</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release_banner(card: dict, readiness: dict) -> str:
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    surf_rho = readiness["observed_registry"]["surface"]["max_spearman"]
    dots_ov = readiness["observed_registry"]["dots"]["max_fraction_within_3px"]
    n_reg = readiness["observed_registry"]["dots"]["registry_entries_compared"]
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill good">UNIQUE TIFF · FILE &amp; NOVELTY GATES PASSED</span><span class="pill caution">NOT APPROVED FOR SUBMISSION · SLOT PROTECTED</span></div>
<h2 id="release-title">Unique PTA-1 GeoTIFF ready for download. <span>Do not submit to spend a weekly slot.</span></h2>
<p><strong>Automated verdict (zero human inspection required):</strong> <code>{e(file.name)}</code> is a genuinely new, single-band <code>float32</code> GeoTIFF produced from unit-consistent 3D potential-field phase-tilt curvature and signed Grauch–Hudson hanging-wall dip-asymmetry (<code>PTA-1</code>). It <strong>passed every local format check</strong> (<code>5,167,373</code> finite cells strictly in <code>[0, 1]</code> inside footprint, <code>0</code> NaN inside, <code>NaN</code> nodata outside, <code>EPSG:32611</code>, <code>3,730 × 3,292</code>, <code>0</code> positive catalogue pixels, <code>44,090</code> Poisson-thinned dots) and <strong>passed both two-stage novelty gates across all {n_reg} observed registry rasters</strong> (continuous surface max Spearman <code>{surf_rho:.4f} ≤ 0.90</code>; final dots max 3 px overlap <code>{100 * dots_ov:.2f}% ≤ 70%</code>; only <code>19.74%</code> within 3 px of <code>GEMSDOE32</code> H33).</p>
<p><strong>Why competition upload is withheld (<code>verdict = negative</code>):</strong> <code>PTA-1</code> statistically significantly beats the raw 8-band subsurface baseline (<code>+0.00887</code> HOLDOUT-DTI, paired 95% CI <code>[+0.00156, +0.01598]</code>) and improves our prior subsurface benchmark <code>TDX-1</code> by <code>+32.7%</code> (<code>0.09668</code> vs <code>0.07284</code>), but as a pure zero-topography subsurface specialist it trails scarp-inclusive <code>core19</code> (<code>0.13982</code>) on the public Quaternary scarp catalogue proxy. Per protocol Rule 5, negative promotion decisions protect weekly portal slots.</p>
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
        "surface_observed_registry": "Pre-placement surface novelty (194 rasters)",
        "dots_observed_registry": "Final-dots 3 px novelty (194 rasters)",
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
        ("DrivenData GEMS Problem & Metric", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/", "Single-band float32 [0,1], EPSG:32611, 100 m, DTI (α=0.2, β=0.8, 300 m triangular kernel); official 19-band glossary (`tc` = gravity terrain correction, `depth_to_base_surf` = MT conductive base)."),
        ("DrivenData Live Leaderboard (2026-10-25)", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/", "Retrieved 2026-10-25: #1 xiaofanhu 0.4413, #2 cfld__ 0.3916, #3 Batik Shirt Brothers 0.3904, #9 DARD 0.3398 (0.3195 on 2026-10-03 snapshot). Deadline Dec. 3, 2026, 11:59 p.m. UTC."),
        ("DOE / NLR Official Prize Rules PDF", "https://docs.nlr.gov/docs/fy26osti/96647.pdf", "Sept 2026 rules: up to 3 platform feedback submissions/week; ONE final selected submission scored on BOTH Phase 1 ($50k) and expert-updated Phase 2 ($250k); AI disclosure & reproducible code required."),
        ("DrivenData Forum Clarifications (chrisk-dd)", "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516", "Threads 11516, 11536, 11550, 11556, 11557, 11563: pixel-exact `labels == 1` masking (zero buffer), new faults allowed <300 m of known traces, pooled TP/FP/FN, `deq`/`ieq` earthquake rate densities."),
        ("USGS GeoDAWN Airborne Survey (CC0)", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and", "DOI 10.5066/P93LGLVQ: E–W (90°) 200–400 m flight-line magnetic & gamma-ray spectrometry across NW Great Basin; motivates E–W leveling mimic check and `1000× tmi_vg` unit normalization."),
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
        ("1 · Executed (`PTA-1`)", "Unit-Consistent 3D Potential-Field Phase-Tilt Curvature & Signed Dip-Contact Asymmetry", "8 subsurface bands (`tmi_anom`, `tmi_hg`, `1000× tmi_vg`, `rtp`, `iso_grav_anom`, `iso_grav_anom_slope`, `tc`, `depth_to_base_surf`)", "3D Miller–Singh tilt ridge + signed Grauch–Hudson hanging-wall offset across `-∇g / ||∇g||` (`pta_dip_cover_step` raw AUC 0.5988)", "Executed (`HOLDOUT-DTI = 0.09668`; `+0.00887` over `sub8_raw` with 95% CI `[+0.00156, +0.01598]`; `54.60%` max 3 px overlap across 194 rasters)"),
        ("2 · Prospective (`PGR-2`)", "Piedmont Geomorphic-Scarp vs Range-Front Relief Decoupling", "`det_elev`, `det_elev_slope`, `dem_1m_med_slope`, `dem_1m_std_slope`, `iso_grav_anom`", "High 1 m sub-cell scarp roughness inside low regional slope (`<4°`) aligned with basinward gravity gradient", "Untried single-lane candidate; directly targets eroded piedmont fault scarps without range-front slope saturation"),
        ("3 · Prospective (`KUS-3`)", "Potassium-to-Uranium/Thorium Alteration Halo Along Subsurface Tilt Contacts", "`k_pct`, `eu_ppm`, `eth_ppm` (GeoDAWN GDR/USGS), `rtp`, `iso_grav_anom`", "Illite/adularia K-enrichment (`K/eTh` residual) focused along steep magnetic/gravity phase-tilt contacts", "Requires aligning external CC0 GeoDAWN radiometric grids (`10.5066/P93LGLVQ`) to EPSG:32611"),
        ("4 · Prospective (`MCS-4`)", "Transtensional Geodetic Shear × Microseismic Rate Partitioning", "`geod_2nd_inv`, `geod_dilatrate`, `geod_shearrate`, `deq_n100a15`, `ieq_n100a15`, `rtp`", "High background independent seismicity (`ieq`) relative to aftershock-dominated `deq` along transtensional shear corridors", "Low resolution (~km GPS/seismicity kernels); best suited as regional prior rather than 100 m locator"),
    ]
    body = "".join(
        f"<tr><th scope='row'>{e(rk)}</th><td><strong>{e(title)}</strong></td><td>{e(layers)}</td><td>{e(sig)}</td><td>{e(outcome)}</td></tr>"
        for rk, title, layers, sig, outcome in rows
    )
    return f'<div class="table-wrap"><table><caption>Preregistered geological hypotheses (frozen in <code>{CURRENT}/preregistration.md</code> before running)</caption><thead><tr><th>Rank</th><th>Hypothesis</th><th>Layers</th><th>Physical signature</th><th>Status / measured outcome</th></tr></thead><tbody>{body}</tbody></table></div>'


def build(template: Path) -> dict[Path, str | bytes]:
    pointer = ROOT / "docs/current-run.json"
    retained = verify(pointer, template)
    selection = json.loads(pointer.read_text())
    card = json.loads(local_path(selection["run_card"]).read_text())
    stopped_key = "archived_stopped_attempt" if selection.get("archived_stopped_attempt") else "latest_attempt"
    stopped_path = local_path(selection[stopped_key])
    stopped = verify_stopped(stopped_path.parent, template)
    if (
        retained["research_verdict"] != "negative"
        or retained["download_ok"] is not True
        or retained["submission_approved"] is not False
        or stopped["download_ok"] is not False
    ):
        raise ValueError("Site builder expects verified downloadable PTA-1 (negative promotion) + verified quarantined TDX-C2")

    banner = release_banner(card, retained)
    scores = pta1_score_table(card)
    n_reg = retained["observed_registry"]["dots"]["registry_entries_compared"]
    max_ov = 100.0 * retained["observed_registry"]["dots"]["max_fraction_within_3px"]

    home = f'''<section class="intro"><div><p class="eyebrow">DOE GEMS / autonomous research &amp; validation</p><h1>Unique subsurface TIFF.<br>Honest slot protection.</h1><p class="lead"><code>PTA-1</code> generated a brand-new, format-validated 44,090-dot GeoTIFF from unit-consistent 3D magnetic/gravity phase-tilt and hanging-wall conductive-cover asymmetry—passing all 194 cross-site novelty checks and beating raw subsurface features while preserving weekly competition slots.</p><p class="meta">25 October 2026 <span>·</span> 1 of 3 experiments used (304.9 s) <span>·</span> No competition slot used</p></div><a class="text-link" href="{CURRENT}/preregistration.md">Read the frozen PTA-1 preregistration ↗</a></section>
{banner}
<section class="evidence-strip" aria-label="PTA-1 automated diagnostics"><article><span>Observed registry</span><strong>{n_reg} rasters cleared</strong><small>Max 3 px overlap {max_ov:.2f}% (≤70%); 19.74% vs H33</small></article><article><span>Subsurface gain</span><strong>+0.00887 HOLDOUT-DTI</strong><small>95% CI [+0.00156, +0.01598] over sub8_raw</small></article><article><span>Leakage canaries</span><strong>37 features × 4 folds</strong><small>0 alarms above 0.90; pta_dip_cover_step AUC 0.5988</small></article></section>
<section class="section"><p class="eyebrow">01 / Preregistered holdout experiment</p><h2>3D phase-tilt &amp; dip-contact asymmetry improved concealed subsurface recovery by +32.7% over TDX-1.</h2><p>By correcting the <code>1,000×</code> length-unit mismatch between <code>tmi_vg</code> (<code>nT/m</code>) and <code>tmi_hg</code> (<code>nT/km</code>) (<code>IR-PTA-01</code>) and measuring signed hanging-wall thickening of MT conductive cover (<code>depth_to_base_surf</code>) across gravity-inferred normal-fault dip vectors, <code>PTA-1</code> achieved <code>HOLDOUT-DTI = 0.09668</code> with a strictly positive paired 95% spatial-bootstrap CI over <code>sub8_raw</code> (<code>0.08781</code>). Because public catalogue labels are dominated by range-front LiDAR scarps, pure subsurface detection remains <code>−0.04314</code> below <code>core19</code> (<code>0.13982</code>) on the catalogue proxy, triggering automatic slot protection.</p>{scores}<a class="text-link" href="experiment-review.html">Full PhD analysis of GEMSDOE32 (0.2778), live leaderboard (0.4413) &amp; 9-site audit ↗</a></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated 12-gate inspection</p><h2>Zero human-inspector handoff.</h2></div><p>Every byte, coordinate transform, range bound,<br>canary AUC, and registry comparison is machine-verified.</p></div>{gate_table(retained)}</section>
<section class="section two-column"><div><p class="eyebrow">03 / Why GEMSDOE32 scored 0.2778 &amp; how to beat 0.2778 / 0.4413</p><h2>Exact masking mechanics + orthogonal basin physics.</h2><p>DrivenData Staff (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">thread 11516/4</a>) confirmed known faults are masked pixel-exactly (<code>labels == 1</code>, zero buffer) while hidden splays can lie <code>&lt;300 m</code> from mapped traces. <code>GEMSDOE32</code> H33 (<code>0.2778</code> owner-reported) deletes the <code>2,545</code> dots at <code>0 &lt; d_cat ≤ 2 px</code> from <code>GEMSDOE28</code>'s <code>40,199</code>-dot base (<code>37,654</code> dots), stripping unmasked flank false positives (<code>0.2 · FP_w</code>) while dots at <code>d_cat = 3 px</code> retain triangular-kernel reach across the flank.</p><p>Surpassing <code>0.2778</code> and closing the recall gap toward the live public leader (<code>0.4413</code> on 2026-10-25; <code>0.3195</code> on 2026-10-03) requires pairing spatial multi-scale scarp UNets in range-front terrain with an orthogonal concealed-basin specialist like <code>PTA-1</code> (<code>54.15%</code> of dots in <code>&lt;5°</code> low-slope basins; only <code>19.74%</code> overlap with H33) under metric-exact <code>EDGE</code> emission.</p><a class="text-link" href="experiment-review.html">Read the complete mathematical derivation &amp; 9-site comparison ↗</a></div><div class="note-card"><h3>Archived session records</h3><ul class="spaced"><li><strong>PTA-1 (current unique TIFF):</strong> <a href="{CURRENT}/run-card.json">run-card.json</a> · <code>download_ok = true</code>, <code>verdict = negative</code>.</li><li><strong>TDX-C2 (archived DUPLICATE-STOP):</strong> <a href="{STOPPED}/run-card.json">run-card.json</a> · 79.09% 3 px overlap with G30-S19; quarantined, no public TIFF.</li><li><strong>TDX-1 (archived subsurface v1):</strong> <a href="{PREVIOUS}/run-card.json">run-card.json</a> · <code>HOLDOUT-DTI = 0.07284</code>.</li></ul><a href="README.md#current-owner-prompt">Complete verbatim owner prompt ↗</a></div></section>'''

    guide = f'''<section class="intro"><div><p class="eyebrow">Executive submission guide</p><h1>Validated GeoTIFF.<br>Clear portal rules.</h1><p class="lead"><code>gems30-PTA1-44090-20261025-9a3f7f9535a4.tif</code> passed every automated format, CRS, <code>[0, 1]</code> range, and 194-raster uniqueness gate without human intervention—and is clearly flagged <strong>NOT APPROVED FOR SUBMISSION</strong> so you do not waste one of your 3 weekly DrivenData slots.</p></div></section>{banner}
<section class="section"><p class="eyebrow">Unique artifact identity · copy-ready metadata</p><h2>Unique submission name &amp; ≤140-character portal note.</h2><div class="identity"><label for="submission-name">Unique PTA-1 artifact name (research record · do not upload to spend a weekly slot)</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Portal note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div><p class="fine">Archived negative artifacts remain documented separately: <a href="{STOPPED}/run-card.json">TDX-C2 (DUPLICATE-STOP, private)</a> and <a href="{PREVIOUS}/run-card.json">TDX-1 (archived research TIFF)</a>.</p></section>
<section class="section"><p class="eyebrow">Step-by-step DrivenData portal procedure</p><h2>How to submit once a candidate earns <code>verdict = promote</code>.</h2><ol class="steps"><li><strong>Verify automated promotion status at the top of this page.</strong><p>Only upload when the top badge reads <b>PROMOTED FOR SLOT SELECTION</b> and <code>python scripts/verify_current_run.py --require-promote</code> exits <code>0</code> (today it deliberately exits <code>2</code> because <code>PTA-1</code> is a pure subsurface specialist with <code>verdict = negative</code>).</p></li><li><strong>Confirm weekly submission allowance &amp; rules compliance.</strong><p>Per <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules (96647.pdf)</a>, teams may upload up to <b>3 feedback submissions per 7-day rolling window</b>, and must select <b>exactly 1 final submission</b> before <b>Dec. 3, 2026, 11:59 p.m. UTC</b> for both Phase 1 ($50k) and expert-updated Phase 2 ($250k).</p></li><li><strong>Download the validated single-band <code>.tif</code> file.</strong><p>Use the one-click GeoTIFF button above (never upload HTML, JSON, PNG, or multi-band rasters). Re-verify locally anytime via <code>.venv/bin/python scripts/validate_submission.py {e(card['published_tiff'])} --template data/raw/sample_submission.tif</code>.</p></li><li><strong>Upload on DrivenData “New submission”.</strong><p>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS competition portal</a>, click <b>Submit</b>, choose the <code>.tif</code> (or single-file <code>.zip</code>) under <b>File to submit</b>, and paste the ≤140-character <b>Note</b> above so every run stays uniquely traceable.</p></li><li><strong>Record the organizer receipt triple.</strong><p>Save the returned submission timestamp/ID, exact <code>raster_sha256</code>, and portal score together before labelling any number <b>ORGANIZER-CONFIRMED</b>.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">Portal error <code>"Predicted values must be in range [0, 1]"</code></p><h2>Root cause &amp; automated prevention.</h2><p><code>training_features.tif</code> stores <code>-3.4028235e+38</code> float32 nodata sentinels on <strong>3,061 pixels inside the valid scoring footprint</strong> (<code>3,073</code> on Band 5 <code>tc</code>; <code>IR-30-044</code> / <code>IR-PTA-02</code>). Masking from feature bands instead of <code>np.isfinite(sample_submission.tif)</code> or leaking unscaled logits/NaNs inside those 3,061 cells triggers the portal range rejection.</p><p><code>src/gemsdoe30/submission.py</code> derives the valid mask exclusively from <code>sample_submission.tif</code>, enforces finite <code>float32</code> values strictly in <code>[0.0, 1.0]</code> on all <code>5,167,373</code> footprint cells, writes <code>NaN</code> nodata outside, zeroes known catalogue pixels (<code>labels == 1</code>), and re-opens the written GeoTIFF from disk before publishing.</p></div><div class="note-card"><h3>Autonomous data &amp; verification commands</h3><p>Fresh clones restore SHA-256-pinned mirrors, build caches, and verify every receipt without manual input:</p><p><code>bash scripts/download_competition_data.sh</code><br><code>.venv/bin/python scripts/prepare_data.py</code><br><code>.venv/bin/python scripts/verify_current_run.py</code><br><code>.venv/bin/python scripts/verify_stopped_attempt.py</code></p><p class="fine">Restored files are hash-verified owner mirrors, not organizer-authenticated DrivenData downloads.</p></div></section>'''

    research = f'''<section class="intro"><div><p class="eyebrow">Deep scientific review / PTA-1 &amp; 9-site audit</p><h1>Physics of blind faults &amp;<br>why H33 scored 0.2778.</h1><p class="lead">A line-by-line synthesis of official DOE/USGS/INGENIOUS sources, exact Distance-Tversky calculus, 9 priority GEMSDOE sites, newly discovered dataset unit/sign irregularities, and our preregistered <code>PTA-1</code> subsurface experiment.</p></div></section>{banner}
<section class="section"><p class="eyebrow">01 / PhD analysis of GEMSDOE32 (0.2778) &amp; leaderboard gap (0.3195 → 0.4413)</p><h2>Why <code>h33-h33-2-b2</code> topped the GEMSDOE sites—and how to beat it.</h2><p>Under the official metric <code>DTI = TP_w / (0.2·TP_w + 0.2·FP_w + 0.8·G + ε)</code> (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem Description</a>; <a href="https://community.drivendata.org/t/clarification-on-metric-pooling-across-connected-components-or-samples/11550">Forum 11550</a>), truth coverage <code>TP_w</code> is a <strong>spatial maximum</strong> over a <code>R = 300 m</code> (<code>3 px</code>) triangular kernel, whereas false-positive penalty <code>0.2 · FP_w</code> sums linearly across unmasked background predictions. DrivenData Staff (<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Forum 11516/4</a>) confirmed that known USGS/INGENIOUS faults are masked <strong>pixel-exactly</strong> (<code>labels == 1</code> only, zero buffer) while new hidden faults can lie <code>&lt;300 m</code> from mapped traces (<a href="https://community.drivendata.org/t/clarification-on-spatial-relationship-between-existing-and-new-faults/11536">Forum 11536</a>).</p><p>Byte-exact audit (<a href="docs/research/2026-10-25/recipe-reconstruction.json">zero mismatching pixels</a>) proves <code>GEMSDOE32</code>'s <code>h33-h33-2-b2</code> (<code>37,654</code> dots; <code>0.2778</code> owner-reported, unverified) equals <code>GEMSDOE28</code>'s <code>h27-4-r1-solo-d2-8</code> (<code>40,199</code> dots; <code>0.2708</code> owner-reported) after deleting the <code>2,545</code> dots at <code>0 &lt; d_cat ≤ 2 px</code>. Those flank dots were unmasked (<code>FP_w ≈ 1.0</code> each, saving <code>~509</code> weighted penalty units when removed) while surviving dots at <code>d_cat = 3 px</code> still extend triangular kernel support across <code>d_cat ∈ [1, 2] px</code>. Conversely, <code>GEMSDOE36</code> added <code>1,200</code> extra dots onto H33 (<code>38,854</code> dots → <code>0.2750</code> owner-reported), diluting precision.</p><p><strong>How to beat 0.2778, 0.3195 (Oct 3 snapshot), and approach 0.4413 (Oct 25 live leader):</strong> All <code>0.2449–0.2778</code> family rasters place <code>70–81%</code> of their dots on steep range-front scarps (<code>det_elev_slope ≥ 5°</code>; H33 has only <code>19.1%</code> of dots in <code>&lt;5°</code> terrain), missing concealed intrabasin geothermal faults beneath quaternary playas and alluvial fans. Conversely, pointwise GBDTs fed raw regional levels collapse onto the same range fronts (<code>TDX-C2</code> stopped at <code>79.09%</code> overlap). Breaking past <code>0.32–0.44</code> requires: (1) a <strong>multi-scale 2D spatial encoder (UNet/ConvNeXt with 6.4–12.8 km receptive field)</strong> trained with regional + 300 m kernel-aware loss to bridge stepovers and tips, fused with (2) an <strong>orthogonal low-slope basin subsurface specialist (`PTA-1`, `54.15%` dots in `&lt;5°` basins, `19.74%` overlap with H33)</strong> gated strictly by low topographic slope, followed by (3) <code>d_cat &gt; 2 px</code> flank pruning + metric-exact <code>EDGE</code> marginal-gain stopping.</p></section>
<section class="section"><p class="eyebrow">02 / Verified primary sources &amp; candidate hypotheses</p><h2>Official data/rules synthesis &amp; 4 ranked geological hypotheses.</h2>{sources_table()}{hypotheses_table()}</section>
<section class="section"><p class="eyebrow">03 / PTA-1 experiment &amp; 9-priority-site novelty audit</p><h2>Statistically significant subsurface gain (+0.00887) &amp; genuine cross-site uniqueness.</h2>{scores}<p>Across <code>148</code> univariate canary evaluations (<code>37</code> features × <code>4</code> folds; <a href="{CURRENT}/results.json">full JSON</a>), zero features approached the <code>0.90</code> leakage threshold (max <code>0.6434</code> on <code>det_elev_slope</code>). Among all 18 subsurface inputs, <strong><code>pta_dip_cover_step</code></strong>—signed hanging-wall thickening of MT conductive cover (<code>depth_to_base_surf</code>) across <code>300–600 m</code> down the gravity dip vector—achieved the strongest fault signal (bidirectional raw AUC <code>0.5988</code> in Fold 3, <code>0.5933</code> in Fold 1 vs <code>0.5181</code> for raw <code>depth_to_base_surf</code>).</p>{priority_nine_table()}<p class="fine">Across the entire 9-repo expanded registry (<code>194</code> unique grid-aligned TIFFs out of <code>209</code> discovered; <a href="{CURRENT}/registry.json">registry.json</a>), max surface Spearman is <code>0.1055</code> and max 3 px dot overlap is <code>54.60%</code> (against an 80,000-dot research raster). All 119 owner-supplied historical claims remain quarantined as unverified in <a href="{PREVIOUS}/owner-claims.csv">owner-claims.csv</a>.</p></section>
<section class="section"><p class="eyebrow">04 / Newly flagged irregularities &amp; next-session roadmap</p><h2>Dataset unit/sign traps discovered (`IR-PTA-01..09`) &amp; remaining limitations.</h2><ul class="spaced"><li><strong><code>IR-PTA-01</code> — 1,000× unit mismatch (<code>tmi_hg</code> nT/km vs <code>tmi_vg</code> nT/m):</strong> Unscaled <code>atan2(tmi_vg, tmi_hg)</code> collapses magnetic tilt dynamic range by <code>&gt;20×</code>; fixed and unit-tested in <code>src/gemsdoe30/phase_tilt.py</code>.</li><li><strong><code>IR-PTA-02</code> — Embedded GDAL band-description errors:</strong> Band 5 <code>tc</code> is gravity terrain correction (with 12 extra in-footprint nodata cells), Bands 9/15 <code>deq</code>/<code>ieq</code> are earthquake rate densities (Forum 11557), and Band 14 <code>depth_to_base_surf</code> is MT conductive-base depth—not pre-Tertiary basement depth.</li><li><strong><code>IR-PTA-03</code> — Signed <code>iso_grav_anom_hg</code>:</strong> Band 17 spans <code>[-10.41, +11.45]</code> rather than unsigned gradient magnitude; <code>PTA-1</code> differentiates smoothed Band 6 <code>iso_grav_anom</code> directly.</li><li><strong><code>IR-PTA-05 &amp; IR-PTA-06</code> — Cross-site &amp; licensing cautions:</strong> <code>GEMSDOE32</code> mislabels owner-reported <code>0.2778</code> as organizer-confirmed and promotes a <code>&gt;94%</code> D2.8 duplicate; <code>GEMSDOE33</code> <code>/docs/index.html</code> 404s (root <code>/</code> works); NBMG vector maps carry unresolved non-commercial notices (Forum 11563—avoided).</li><li><strong>Remaining limitations &amp; next session:</strong> (1) CPU-only 3.8 GiB sandbox precludes multi-hour GPU UNet retraining here; next GPU session should train a 2D multi-scale UNet fusing scarp dipoles in <code>≥3°</code> terrain with <code>PTA-1</code> phase-tilt + <code>pta_dip_cover_step</code> in <code>&lt;3°</code> basins; (2) complete private surfaces from unindexed repos and organizer-authenticated DrivenData downloads remain external to this sandbox.</li></ul><p><a href="{CURRENT}/analysis.md">PTA-1 scientific analysis</a> · <a href="{CURRENT}/verification.md">Three-pass verification journal</a> · <a href="docs/irregularities.md">Complete irregularities ledger</a> · <a href="{STOPPED}/review.md">Archived TDX-C2 duplicate-stop review</a></p></section>'''

    return {
        ROOT / "index.html": page("Unique PTA-1 GeoTIFF validated; slot protected", home),
        ROOT / "executive-summary.html": page("Executive submission guide", guide, active="guide"),
        ROOT / "experiment-review.html": page("PTA-1 physics, H33 0.2778 analysis & 9-site audit", research, active="research"),
        ROOT / "docs/assets/pta1-support.png": png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open current research download and submission decision.</a></p></body></html>\n',
    }


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
    print("Verified exact generated Pages" if args.check else "Built PTA-1 research Pages")


if __name__ == "__main__":
    main()
