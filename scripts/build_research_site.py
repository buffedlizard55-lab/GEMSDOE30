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
from scripts.verify_lsm_run import verify as verify_lsm
from scripts.priority_site_summary import build_summary, canonical_json

STYLE = "docs/assets/research.css"


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

    # Small standard-library PNG encoder: no plot/image dependency or remote asset.
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
    return f'<tr><th scope="row">{e(name)}</th><td>{row["value"]:.6f}</td><td>[{lo:.6f}, {hi:.6f}]</td></tr>'


def delta_row(name: str, row: dict) -> str:
    lo, hi = row["ci95"]
    sign = "+" if row["value"] >= 0 else ""
    s_lo = "+" if lo >= 0 else ""
    s_hi = "+" if hi >= 0 else ""
    return f'<tr><th scope="row">{e(name)}</th><td>{sign}{row["value"]:.6f}</td><td>[{s_lo}{lo:.6f}, {s_hi}{hi:.6f}]</td></tr>'


def page(title: str, content: str, card: dict, research_dir: str, *, active: str = "home") -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="A newly generated GEMS fault-prediction TIFF, reproducible holdout evidence, and an explicit automated submission decision.">
<title>{e(title)} · GEMSDOE30</title><link rel="stylesheet" href="{STYLE}"></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">G30</span> Fault discovery lab</a>
<nav aria-label="Main navigation"><a href="index.html"{' aria-current="page"' if active == "home" else ''}>Overview</a><a href="executive-summary.html"{' aria-current="page"' if active == "guide" else ''}>Submission guide</a><a href="priority-site-executive-summary.html"{' aria-current="page"' if active == "priority" else ''}>Priority audit</a><a href="experiment-review.html"{' aria-current="page"' if active == "research" else ''}>Research</a><a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated machine gates require zero human raster inspection.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{e(research_dir)}/run-card.json">Run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Experiment recorded {e(card['created_utc'])}. Repository evidence only; not a live leaderboard projection. No competition slot selected or used.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release(card: dict, readiness: dict, research_dir: str) -> str:
    """Render the decision boundary before any download control.

    A locally valid file and an observed-registry novelty pass are useful evidence,
    but neither is a competition-slot decision.  Keep each state visible so that a
    reader cannot mistake a green format check for permission to upload.
    """
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    v = card["validator_output"]
    obs = readiness["observed_registry"]
    h = card["holdout"]
    core_delta = h["candidate_minus"]["core19"]
    gate_map = {gate["name"]: gate for gate in readiness["gates"]}
    failed = [gate["name"] for gate in readiness["gates"] if gate["status"] == "failed"]
    unknown = [gate["name"] for gate in readiness["gates"] if gate["status"] == "unknown"]
    passed = sum(gate["status"] == "passed" for gate in readiness["gates"])
    paired = gate_map["paired_improvement"]
    observed_novelty = (
        f"{obs['dots']['registry_entries_compared']} observed comparisons; max 3-px overlap "
        f"{100 * obs['dots']['max_fraction_within_3px']:.2f}% &le; 70%"
    )
    failed_text = ", ".join(failed) if failed else "none"
    unknown_text = ", ".join(unknown) if unknown else "none"
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill caution">COMPETITION UPLOAD: NOT APPROVED</span><span class="pill good">RESEARCH DOWNLOAD: {"YES" if readiness["download_ok"] else "NO"}</span><span class="pill unknown">ORGANIZER ACCEPTANCE: UNCONFIRMED</span></div>
<h2 id="release-title">Download for audit/reproducibility · <span>Do not submit this file. NOT APPROVED FOR SUBMISSION.</span></h2>
<p><strong>Decision first:</strong> the exact GeoTIFF passes the local file contract and is distinct against the <em>observed</em> registry, so it may be downloaded for research. It is <strong>not</strong> approved for competition upload: the preregistered <code>msdb_edge − msdb_poisson</code> paired <code>HOLDOUT-DTI</code> CI crosses zero, and the complete parallel registry, external lane assignment, and comparable historical-best rerun remain unknown. Local validation cannot confirm private portal acceptance.</p>
<div class="evidence-strip" aria-label="Upload decision facts"><article><span>Research download</span><strong>{"YES" if readiness["download_ok"] else "NO"}</strong><small>Exact bytes reopened and hash-bound</small></article><article><span>Competition upload</span><strong>NO</strong><small>Research verdict: {e(readiness["research_verdict"])}</small></article><article><span>Observed novelty</span><strong>PASS</strong><small>{observed_novelty}</small></article></div>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download research GeoTIFF — DO NOT SUBMIT <span>{size:.2f} MiB</span></a><a class="button secondary" href="{e(research_dir)}/readiness.json">View machine gate receipt (JSON)</a><a class="button secondary" href="priority-site-executive-summary.html">Review 9-site selection audit</a></div>
<p class="filename">{e(file.name)}</p><details open><summary>Automated validation, evidence limits &amp; file identity</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Submission Note ({len(card['note'])}/140 chars)</dt><dd><code>{e(card['note'])}</code></dd><dt>File contract</dt><dd><code>PASSED</code> · 1 band <code>float32</code> · <code>EPSG:32611</code> · <code>3,730 × 3,292</code> · in-footprint finite: <code>{e(v['no_nan_inside_footprint'])}</code> · in <code>[0, 1]</code>: <code>{e(v['values_in_0_1'])}</code> · outside <code>NaN</code>: <code>{e(v['nan_nodata_outside_footprint'])}</code> · off-catalogue dots: <code>{v['emitted_dots']:,}</code> (<code>{v['positive_catalogue_pixels']}</code> on known faults)</dd><dt>Promotion gate</dt><dd><code>{e(paired['status']).upper()}</code> · {e(paired['detail'])}; <code>msdb_edge − msdb_poisson = +0.001135</code>, 95% CI <code>[−0.002173, +0.004628]</code>.</dd><dt>All machine gates</dt><dd><code>{passed}</code> passed · <code>{len(failed)}</code> failed ({e(failed_text)}) · <code>{len(unknown)}</code> unknown ({e(unknown_text)}).</dd><dt>Receipts</dt><dd><a href="{e(research_dir)}/validation.json">Reopened-file validation</a> · <a href="{e(card['published_tiff'][:-4])}.json">Provenance sidecar</a> · <a href="{e(research_dir)}/run-card.json">Run card</a></dd></dl></details></section>'''


def arm_display_name(key: str) -> str:
    mapping = {
        "core19": "core19 · 19 raw bands + HGB + r=3.0 px Poisson-disk",
        "msdb_poisson": "msdb_poisson · 31 stationary MSDB × Rayleigh gate + r=3.0 px Poisson-disk",
        "msdb_edge": "msdb_edge · 31 stationary MSDB × Rayleigh gate + Bayes 300 m EDGE (Candidate)",
        "physics3": "physics3 · Three raw physics bands",
        "tdx6": "TDX-1 · Six-feature displacement candidate",
    }
    return mapping.get(key, key)


def build(template: Path) -> dict[Path, str | bytes]:
    pointer = ROOT / "docs/current-run.json"
    readiness = verify(pointer, template)
    selected = json.loads(pointer.read_text())
    card_path = local_path(selected["run_card"])
    research_dir = card_path.parent.relative_to(ROOT).as_posix()
    card = json.loads(card_path.read_text())
    h = card["holdout"]
    v = card["validator_output"]
    observed = readiness["observed_registry"]
    if readiness["research_verdict"] != "negative" or card["submission_approved"] is not False:
        raise ValueError("This negative-result site template must not be used to advertise a promoted/selected file")

    cand_key = card.get("candidate_arm", "tdx6")
    comp_keys = list(h["comparators"].keys())
    rows = "".join(score_row(arm_display_name(k), h["comparators"][k]) for k in comp_keys)
    rows += score_row(arm_display_name(cand_key), h)

    delta_rows = "".join(
        delta_row(f"{cand_key} minus {k}", h["candidate_minus"][k]) for k in comp_keys if k in h["candidate_minus"]
    )
    if "feature_only_ablation_msdb_poisson_minus_core19" in h:
        delta_rows += delta_row(
            "msdb_poisson minus core19 (pure geological representation gain)",
            h["feature_only_ablation_msdb_poisson_minus_core19"],
        )

    labels = {
        "file_contract": "GeoTIFF grid, EPSG:32611, [0,1] range & SHA-256",
        "labelled_holdout_evidence": "Pooled HOLDOUT-DTI & 2,000-rep spatial bootstrap CI",
        "paired_improvement": "Beat all same-protocol comparators (95% CI > 0)",
        "single_feature_leakage_canaries": "Single-feature leakage canaries (AUC <= 0.90)",
        "count_matched_construction": "Exact count-matched active dot budget per fold",
        "surface_observed_registry": "Continuous surface novelty vs. 9-site registry",
        "dots_observed_registry": "Final dots novelty vs. 9-site registry",
        "complete_parallel_registry": "Global unobserved session registry completeness",
        "assigned_lane": "External lane-allocation attestation",
        "comparable_historical_best": "Same-protocol historical UNet checkpoint rerun",
        "experimental_budget": "Experiment & runtime budget (<= 3 runs, <= 2 h)",
        "artifact_identity": "Unique submission name & <= 140-char note",
    }
    gates = "".join(
        f'<tr><th scope="row">{e(labels.get(g["name"], g["name"]))}</th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in readiness["gates"]
    )

    score_table = f'''<div class="table-wrap"><table><caption>HOLDOUT-DTI · {h['withheld_positives']:,} withheld fault pixels · 371 geographic blocks · 2,000 paired bootstrap draws</caption><thead><tr><th>Fixed count-matched arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="table-wrap"><table><caption>Paired Spatial-Block Differences (same folds, identical active dot counts)</caption><thead><tr><th>Comparison</th><th>Δ HOLDOUT-DTI</th><th>95% Paired CI</th></tr></thead><tbody>{delta_rows}</tbody></table></div>
<p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code> (<code>{e(h['protocol_version'])}</code>, <code>17 px</code> regional buffer &ge; <code>{card.get('physical_support_px', 13)} px</code> physical filter support). Catalogue-recovery proxy measurements only—<strong>never organizer scores or leaderboard projections</strong>. Full derivation: <a href="{e(research_dir)}/review.md">scientific review</a>.</p>'''

    preview_rel = "docs/assets/msdb1-support.png"
    canary_n = card["feature_canaries"]["features_per_fold"]
    canary_folds = card["feature_canaries"]["folds"]
    extra_reg_link = ""
    if (ROOT / research_dir / "registry-parallel-addendum.json").is_file():
        extra_reg_link = f' · <a href="{e(research_dir)}/registry-parallel-addendum.json">Late-reference addendum</a>'

    home = f'''{release(card, readiness, research_dir)}
<section class="intro"><div><p class="eyebrow">DOE GEMS · Lane MSDB-1v2 · 25 October 2026</p><h1>Steerable piedmont discontinuities.<br>Positive feature result; no upload approval.</h1><p class="lead">Correcting two competition band-metadata errors (<code>Band 6 tc</code> = GeoDAWN Radiometric Total Count; <code>Bands 18/11</code> = signed <code>∇g</code>) and gating a stationary 31-feature discontinuity habitat by a Rayleigh 1-D curvilinear envelope lifts buffered whole-segment <code>HOLDOUT-DTI</code> from <code>0.133628</code> to <code>0.170462</code> across all 4 disjoint quadrants. The fixed <code>EDGE</code> artifact remains unapproved because its paired advantage over <code>msdb_poisson</code> is not resolved by the preregistered 95% CI.</p><p class="meta">Experiments run: {card['experiments_run']} / {card['experiment_cap']} <span>·</span> {card['experimental_elapsed_seconds']:.1f}s / 7,200s budget <span>·</span> No competition slot selected or used</p></div><a class="text-link" href="{e(research_dir)}/preregistration.md">Read the frozen preregistration ↗</a></section>
<section class="evidence-strip" aria-label="Research diagnostics"><article><span>Unique off-catalogue dots</span><strong>{v['emitted_dots']:,} dots</strong><small>0 on 60,988 known fault pixels</small></article><article><span>9-site novelty audit</span><strong>{observed["dots"]["registry_entries_compared"]} unique TIFFs</strong><small>Max 3-px overlap {100 * observed["dots"]["max_fraction_within_3px"]:.2f}% (&le; 70%)</small></article><article><span>Leakage canaries</span><strong>{canary_n} features × {canary_folds} folds</strong><small>{card["feature_canaries"]["alarm_count"]} alarms above 0.90 AUC</small></article></section>
<section class="two-column section"><div><p class="eyebrow">01 / Controlled 4-fold spatial holdout</p><h2>4 of 4 quadrants improved.<br>97% from physics features.</h2><p>Across 60,988 withheld USGS/INGENIOUS fault pixels in four whole-component buffered quadrants (<code>buffer_px = 17 &ge; support_px = 13</code>), <code>msdb_edge</code> achieves <code>HOLDOUT-DTI = 0.170462 [0.156227, 0.184168]</code> vs. <code>core19 = 0.133628 [0.118285, 0.148875]</code> (<code>+0.036834</code>, 95% CI <code>[+0.022322, +0.050315]</code>), adding <code>+2,193.7</code> weighted true-positive fault credits while reducing false-positive weight by <code>-1,018.9</code>.</p><p class="fine">Experiment 1 (<a href="{e(research_dir)}/experiment-1-duplicate-stop/receipt.json">archived duplicate-stop receipt</a>) halted before any fold evaluation when raw regional bands caused <code>71.44%</code> overlap with <code>G30-S19</code>. Experiment 2 removed the 6 regional coordinate-proxy/DC-level bands and added the fold-local Rayleigh curvilinear gate.</p>{score_table}<a class="text-link" href="{e(research_dir)}/results.json">All fold sufficient statistics &amp; 148 canary AUCs ↗</a></div><figure><img src="{preview_rel}" width="823" height="933" loading="lazy" alt="New MSDB-1v2 prediction dots in dark green over the pale green competition footprint"><figcaption><span class="legend-dot"></span> New MSDB-1v2 support (44,090 binary off-catalogue dots) · downsampled preview; downloadable GeoTIFF preserves exact 100 m EPSG:32611 grid.</figcaption></figure></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated machine inspection</p><h2>Every gate has a deterministic state.</h2></div><p>Passed, failed, or unknown.<br>Zero human raster inspection.</p></div><div class="table-wrap"><table><thead><tr><th>Automated gate</th><th>State</th><th>Machine rule</th></tr></thead><tbody>{gates}</tbody></table></div></section>
<section class="section two-column"><div><p class="eyebrow">03 / Forensic root cause of GEMSDOE32 H33 (0.2778)</p><h2>Why H33 topped our sites—and how to beat it.</h2><p>Byte-exact reconstruction (<a href="docs/research/2026-10-25/recipe-reconstruction.json">receipt</a>) proves <code>GEMSDOE32</code> <code>H33</code> (<code>37,654</code> dots, <code>0.2778</code> <code>OWNER-REPORTED</code>) equals <code>GEMSDOE28</code> solo <code>d=2.8</code> (<code>40,199</code> dots, <code>0.2708</code> <code>OWNER-REPORTED</code>, thinned from <code>GEMSDOE27</code> <code>H27-4</code>'s <code>121,150</code> dots at <code>0.1922</code>) minus the exact <code>2,545</code> dots within <code>&le; 2 px</code> (<code>200 m</code>) of <code>labels.tif</code> (<code>0</code> pixel diffs).</p><p>Under official pooled DW-Tversky (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page/967</a>; known faults masked per <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum t/11516</a>; splays/continuations counted per <a href="https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536">t/11536</a>), <code>TP_w</code> uses a 300 m <code>max</code> while <code>FP_w</code> uses a linear <code>sum</code>: spacing dots at ~300 m and stripping <code>&le; 200 m</code> digitization halos slashes <code>FP_w</code> without losing <code>TP_w</code>. Surpassing <code>0.2778</code> toward the live 2026-10-25 leaderboard top (<code>0.4413</code> #1, <code>0.3379</code> #10) requires raising true recall <code>TP_w/|G|</code> via corrected multi-physics discontinuity features like <code>MSDB-1v2</code> paired with multi-km convolutional context.</p><a class="text-link" href="{e(research_dir)}/review.md">Full equations, 4 ranked hypotheses &amp; metadata audit ↗</a></div><div class="note-card"><h3>Novelty &amp; metadata discoveries</h3><p><strong>Irregularity 1:</strong> <code>Band 6 (tc)</code> is GeoDAWN Radiometric Total Count (<code>Spearman = 0.999957</code>), not magnetic tilt (<code>0.0160</code>). <code>MSDB-1v2</code> computes true Miller–Singh tilt <code>arctan2(tmi_vg, tmi_hg)</code> and Salem contact inverse-depth.</p><p><strong>Irregularity 2:</strong> <code>Bands 18 &amp; 11</code> are signed grid derivatives <code>(+dg/dx, +dg/dy)</code>, enabling azimuthally symmetric 2-D vector gravity strike concordance.</p><p>Max surface Spearman vs. 165 registry TIFFs: <b>{observed['surface']['max_spearman']:.6f}</b>.<br>Max final-dot 3-px overlap: <b>{100 * observed['dots']['max_fraction_within_3px']:.4f}%</b>.</p><a href="{e(research_dir)}/registry.json">Frozen 180-file / 165-unique 9-site registry</a>{extra_reg_link}</div></section>
<section class="section"><p class="eyebrow">04 / Preserved prior &amp; concurrent lanes</p><h2>Full repository audit trail.</h2><div class="resource-grid"><article><h3>TDX-1 &amp; TDX-C2 · displacement</h3><p>Preserved negative displacement runs (<a href="docs/research/texture-displacement/run-card.json">TDX-1 card</a>; <a href="docs/research/texture-controls/run-card.json">TDX-C2 duplicate-stop card</a>).</p><a href="experiment-review.html">Full cross-lane review ↗</a></article><article><h3>G30-S19 &amp; G30-S20 · habitat</h3><p>Concurrent lanes (<a href="docs/research/2026-10-25/lane-g30s19-run-card.json">G30-S19</a>; <a href="docs/research/2026-10-25-s20/run-card.json">G30-S20 duplicate-stop</a>). Audited in <code>MSDB-1v2</code>'s {observed["dots"]["registry_entries_compared"]}-raster novelty check (<code>64.78% &le; 70%</code>).</p><a href="docs/research/msdb-piedmont/novelty-parallel-dots.json">Late S20 audit ↗</a></article><article><h3>H-CC1 &amp; Residual-ridge gate</h3><p>Preserved negative records on contact coincidence and catalogue-corridor magnetic residuals.</p><a href="docs/research/2026-10-25/h-cc1-run-card.json">H-CC1 card ↗</a> · <a href="docs/research/2026-10-25/run-card-residual-gate.json">Residual-gate card ↗</a></article></div></section>
<section class="section"><p class="eyebrow">05 / Verified official sources &amp; data catalog</p><h2>Primary DOIs, licenses, and code receipts.</h2><div class="resource-grid"><article><h3>Competition &amp; rules</h3><p>DrivenData GEMS overview, metric spec, forum clarifications, and NLR Official Rules (3/week cap, Dec 3 2026 close).</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem spec ↗</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Rules PDF ↗</a></article><article><h3>USGS GeoDAWN &amp; GDR 1391</h3><p>USGS GeoDAWN (DOI <code>10.5066/P93LGLVQ</code>, CC0) and GBCGE INGENIOUS compilation (DOI <code>10.15121/1881483</code>, CC BY 4.0).</p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN ↗</a> · <a href="https://gdr.openei.org/submissions/1391">OpenEI GDR 1391 ↗</a></article><article><h3>Machine status &amp; quarantined ledger</h3><p>Live-recomputed JSON status feed and all 119 quarantined owner-reported score rows.</p><a href="docs/status.json">Status JSON ↗</a> · <a href="docs/research/texture-displacement/owner-claims.csv">119 owner claims CSV ↗</a></article></div></section>'''

    guide = f'''{release(card, readiness, research_dir)}
<section class="intro"><div><p class="eyebrow">Executive Summary &amp; Zero-Human-Inspection Validation Guide</p><h1>Format-valid research GeoTIFF.<br>Not approved for competition upload.</h1><p class="lead">The exact file passes local GeoTIFF, <code>[0, 1]</code>, footprint, catalogue-exclusion, leakage-canary, and observed-registry checks. It does <strong>not</strong> pass the full preregistered promotion rule: the primary <code>msdb_edge</code> artifact does not have a positive paired 95% CI over its count-matched <code>msdb_poisson</code> control. Global registry coverage, lane assignment, historical-best comparability, and organizer acceptance also remain unverified.</p></div></section>
<section class="section"><p class="eyebrow">01 / Automated gate breakdown</p><h2>Why research download is available and why slot approval stays conservative.</h2>{score_table}<ul class="spaced"><li><strong>Technical file contract — PASSED locally:</strong> Single-band <code>float32</code> GeoTIFF on <code>EPSG:32611</code> (<code>3,730 × 3,292</code>, exact 100 m transform), 100% finite values in <code>[0.0, 1.0]</code> across all <code>5,167,373</code> in-footprint cells, <code>NaN</code> nodata outside, and <code>0</code> dots on known USGS/INGENIOUS faults. This does not prove private portal acceptance.</li><li><strong>Observed-registry novelty — PASSED, not global certification:</strong> Audited on both saved states against <code>{observed["dots"]["registry_entries_compared"]}</code> aligned GeoTIFF comparisons across <code>GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36</code> and merged <code>main</code> lanes: max surface Spearman <code>0.1545 &le; 0.90</code>, max dot 3-px overlap <code>64.78% &le; 70.00%</code>. Missing parallel and original continuous surfaces remain <code>unknown</code>.</li><li><strong>Representation gain — PASSED; primary artifact gate — FAILED:</strong> <code>msdb_edge</code> beats <code>core19</code> in all 4 disjoint quadrants (<code>+0.036834</code>, 95% CI <code>[+0.022322, +0.050315]</code>) with <code>0 / 148</code> leakage-canary alarms. But its predeclared comparison with <code>msdb_poisson</code> is <code>+0.001135</code>, 95% CI <code>[−0.002173, +0.004628]</code>, so the lower bound is not positive.</li><li><strong>Why <code>readiness.py</code> keeps <code>NOT APPROVED FOR SUBMISSION</code>:</strong> The failed <code>paired_improvement</code> gate plus the unknown <code>complete_parallel_registry</code>, <code>assigned_lane</code>, and <code>comparable_historical_best</code> gates preclude promotion. Run <code>.venv/bin/python scripts/verify_current_run.py --require-promote</code> (exits <code>2</code> by design; exits <code>0</code> without <code>--require-promote</code>).</li></ul></section>
<section class="section"><p class="eyebrow">02 / Artifact identity &amp; copyable metadata</p><h2>Unique submission filename &amp; &le; 140-character note.</h2><div class="identity"><label for="submission-name">Unique artifact name</label><input id="submission-name" value="{e(card['submission_name'])}" readonly><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Note · {len(card['note'])} / 140 characters</label><textarea id="submission-note" readonly rows="3">{e(card['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></section>
<section class="section"><p class="eyebrow">03 / Competition submission protocol</p><h2>How weekly slot selection &amp; portal upload work.</h2><ol class="steps"><li><strong>Verify automated receipts (`exit 0`).</strong><p>Run <code>.venv/bin/python scripts/verify_current_run.py</code> to re-verify SHA-256 hashes, <code>[0, 1]</code> bounds, {observed["dots"]["registry_entries_compared"]}-raster novelty, and 2,000-draw paired spatial bootstrap CIs directly from disk.</p></li><li><strong>Separate weekly-slot selector (`3 submissions / week` cap).</strong><p>Under NLR Official Rules §3.4 (<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">96647.pdf</a>), teams have at most 3 submissions per rolling week and select 1 final submission before December 3, 2026. No slot was selected or spent by this repository.</p></li><li><strong>Download the raw <code>.tif</code> binary only.</strong><p>Never upload JSON sidecars, HTML pages, or copied registry files. Upload a single-band <code>float32</code> GeoTIFF directly.</p></li><li><strong>Record organizer receipts honestly.</strong><p>Only scores copied from an official DrivenData submission receipt may be labeled <code>ORGANIZER-CONFIRMED</code>; local <code>HOLDOUT-DTI</code> values are never projected onto leaderboard scores.</p></li></ol></section>
<section class="section two-column"><div><p class="eyebrow">04 / Portal range-error prevention</p><h2>Strict <code>[0, 1]</code> clipping &amp; sentinel sanitization.</h2><p><code>training_features.tif</code> contains <code>-3.4028235e+38</code> float32 nodata sentinels at <code>3,061</code> in-footprint pixels. Deriving masks from raw feature bands rather than <code>sample_submission.tif</code> or writing unclipped logits can trigger DrivenData's <code>"Predicted values must be in range [0, 1]"</code> rejection.</p><p><code>src/gemsdoe30/msdb.py</code> sanitizes all non-finite cells within exact <code>12.73 px</code> Euclidean reach, and <code>src/gemsdoe30/submission.py</code> reopens the written GeoTIFF to verify every in-footprint pixel lies strictly in <code>[0.0, 1.0]</code>.</p><a href="{e(research_dir)}/validation.json">Exact reopened-file validator receipt ↗</a></div><div class="note-card"><h3>Verified external links</h3><ul class="spaced"><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem &amp; DW-Tversky metric</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official public leaderboard</a></li><li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules PDF (Sept 2026)</a></li><li><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Staff ruling: known faults masked (t/11516)</a></li><li><a href="https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536">Staff ruling: splays &amp; continuations (t/11536)</a></li></ul></div></section>'''

    pins_path = ROOT / "docs/research/texture-controls/historical-reference-audit.json"
    sites_rows = ""
    if pins_path.is_file():
        pins = json.loads(pins_path.read_text())["rasters"]
        sites_rows = "".join(
            f'<tr><th scope="row"><a href="{e(r["source_url"])}">{e(r["site"])}</a></th><td>{r["positive_pixels"]:,}</td><td>{"Passed" if r["local_format_validation"]["passed"] else "Failed: outside encoding"}</td><td><code>{e(r["sha256"][:16])}…</code></td></tr>'
            for r in pins
        )

    research_html = f'''<section class="intro"><div><p class="eyebrow">Scientific Review · MSDB-1v2 &amp; Peer Lane Audit</p><h1>Physics discontinuities work.<br>Mandatory duplicate-stops protect novelty.</h1><p class="lead">Across this repository's 2026-10-25 experiments, two peer attempts (<code>G30-S20</code> and <code>TDX-C2</code>) collided with <code>G30-S19</code> (&gt; 70% overlap) and halted cleanly, whereas <code>MSDB-1v2</code> cleared the {observed["dots"]["registry_entries_compared"]}-file novelty audit (<code>64.78% &le; 70%</code>) and beat <code>core19</code> by <strong>+27.6%</strong> across all 4 quadrants.</p></div></section>
<section class="section"><p class="eyebrow">01 / Current candidate (MSDB-1v2)</p><h2>Correcting two geophysical band-metadata errors unlocked +0.036834 HOLDOUT-DTI.</h2><p>Direct cross-correlation against official USGS GeoDAWN (DOI <code>10.5066/P93LGLVQ</code>) and numerical differentiation of Band 13 proved two critical metadata errors in <code>training_features.tif</code>: <code>Band 6 (tc)</code> is GeoDAWN Radiometric Total Count (<code>Spearman = 0.999957</code>, not magnetic tilt), and <code>Bands 18 &amp; 11</code> are signed grid derivatives <code>(+dg/dx, +dg/dy)</code> of isostatic gravity. <code>MSDB-1v2</code> restores true Miller–Singh tilt, Salem contact inverse-depth, 2-D vector gravity strike concordance, and piedmont alluvial-ramp cover-breach indices, gated by a fold-local Rayleigh curvilinear discontinuity envelope.</p>{score_table}<div class="actions"><a class="text-link" href="{e(research_dir)}/review.md">Complete MSDB-1v2 technical report &amp; 4 ranked hypotheses ↗</a><a class="text-link" href="{e(research_dir)}/results.json">All fold statistics &amp; 148 canary AUCs ↗</a></div></section>
<section class="section"><p class="eyebrow">02 /Nine priority sites &amp; H33 forensic audit</p><h2>Educational audit of GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36.</h2><p>No historical raster was reused as predictions. Byte-exact reconstruction (<a href="docs/research/2026-10-25/recipe-reconstruction.json">receipt</a>) proved <code>GEMSDOE32</code> <code>H33</code> (<code>37,654</code> dots) equals <code>GEMSDOE28</code> solo <code>d=2.8</code> (<code>40,199</code> dots) minus <code>2,545</code> dots within <code>&le; 2 px</code> (<code>200 m</code>) of <code>labels.tif</code>.</p><div class="table-wrap"><table><caption>Pinned priority-site reference diagnostics (counts &amp; format checks, not organizer scores)</caption><thead><tr><th>Priority site</th><th>Positive pixels</th><th>Published-spec format</th><th>SHA-256 prefix</th></tr></thead><tbody>{sites_rows}</tbody></table></div></section>
<section class="section"><p class="eyebrow">03 / Preserved negative &amp; duplicate-stopped peer lanes</p><h2>Falsification and novelty enforcement across concurrent runs.</h2><ul class="spaced"><li><strong>MSDB-1 Experiment 1 (<a href="docs/research/msdb-piedmont/experiment-1-duplicate-stop/receipt.json">archived pre-holdout stop</a>):</strong> Including 6 regional DC-level/coordinate bands caused <code>71.44%</code> dot overlap with <code>G30-S19</code>; halted before any holdout fold ran.</li><li><strong>TDX-C2 (<a href="docs/research/texture-controls/review.md">PR #30</a>):</strong> Conditional magnetic-displacement features did not improve <code>core19</code> (<code>-0.003760</code>) and hit <code>79.09%</code> dot overlap; quarantined with no public TIFF.</li><li><strong>G30-S20 (<a href="docs/research/2026-10-25-s20/analysis.md">PR #29</a>) &amp; TDX-1 (<a href="docs/research/texture-displacement/review.md">PR #28</a>):</strong> Preserved intact with immutable pre-placement registries and post-merge late-reference audits.</li></ul><p><a href="docs/irregularities.md">Complete irregularities ledger ↗</a> · <a href="docs/status.json">Machine status JSON ↗</a></p></section>'''

    for extra in selected.get("additional_stopped_attempts", []):
        if extra.get("lane") == "G30-LSM":
            lsm_ready = verify_lsm(local_path(extra["pointer"]), template)
            if lsm_ready["ok_to_submit"] is not False:
                raise ValueError("G30-LSM stopped attempt must remain non-submittable")

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
    registry_review_html = f'''<section class="intro"><div><p class="eyebrow">Public Source Registry · 25 October 2026</p><h1>Immutable nine-site inventory.<br>Metadata, not scores.</h1><p class="lead">Immutable GitHub snapshots across all nine priority sites (<code>{public_snapshot["source_files"]}</code> TIFF source blobs, <code>{public_snapshot["unique_aligned_byte_sequences"]}</code> unique aligned byte sequences) preserved without altering any frozen experiment registry.</p></div><a class="text-link" href="docs/research/2026-10-25/priority-site-public-snapshot.json">Open machine receipt ↗</a></section>
<section class="section"><p class="eyebrow">01 / Byte-verified public inventory</p><h2>Nine requested repositories at immutable commits.</h2><div class="table-wrap"><table><caption>Public source scope only</caption><thead><tr><th>Repository</th><th>Immutable commit</th><th>TIFF source blobs</th><th>Candidate surface paths</th></tr></thead><tbody>{pub_rows}</tbody></table></div></section>
<section class="section"><p class="eyebrow">02 / Surface metadata groundwork</p><h2>Inspected public arrays remain conservatively marked unknown.</h2><div class="table-wrap"><table><caption>Potential public surfaces · never used as predictions</caption><thead><tr><th>Repository</th><th>Object</th><th>Container</th><th>Eligibility</th></tr></thead><tbody>{surf_rows}</tbody></table></div><p><a href="docs/research/2026-10-25/priority-site-public-review.md">Full source-sync review ↗</a> · <a href="experiment-review.html">Back to scientific review ↗</a></p></section>'''

    priority_summary = build_summary(ROOT)
    priority_rows = "".join(
        f'<tr><th scope="row">{e(row["site"])}</th><td><a href="{e(row["source_url"])}"><code>{e(row["highest_owner_reported_submission"])}</code></a></td><td>{e(row["highest_owner_reported_score"])}</td><td>{e(row["score_label"])}</td><td><strong>{e(row["re_use_decision"])}</strong><br><span class="fine">{e(row["executive_assessment"])}</span></td></tr>'
        for row in priority_summary["sites"]
    )
    lineage_rows = "".join(
        f'<tr><th scope="row">{e(" + ".join(row["sites"]))}</th><td>{e(row["finding"])}</td><td>{e(row["measured"])}</td></tr>'
        for row in priority_summary["forensic_lineage"]
    )
    historical_winner = priority_summary["highest_owner_reported_claim_among_priority_sites"]
    current_decision = priority_summary["selection_decision"]["current_research_artifact"]
    h33_interpretation = priority_summary["h33_interpretation"]
    strategy_assessment = priority_summary["distinct_strategy_assessment"]
    hypothesis_rows = "".join(
        f'<tr><th scope="row">{item["rank"]} · {e(item["id"])}</th><td><strong>{e(item["name"])}</strong><br><span class="fine">{e(item["physical_signal"])}</span></td><td>{e(item["expected_dti_benefit"])}<br><span class="fine">Cost: {e(item["implementation_cost"])}</span></td><td>{e(item["current_status"])}</td></tr>'
        for item in strategy_assessment["ranked_hypotheses"]
    )
    strategy_requirements = "".join(
        f"<li>{e(requirement)}</li>" for requirement in strategy_assessment["mandatory_evidence_before_any_upload"]
    )
    priority_html = f'''<section class="release" aria-labelledby="priority-release-title"><div class="release-heading"><span class="pill caution">NO HISTORICAL FILE APPROVED FOR UPLOAD</span><span class="pill unknown">9-SITE SCORE ATTRIBUTION: UNVERIFIED</span></div><h2 id="priority-release-title">Clear recommendation: <span>submit none of the historical priority-site TIFFs.</span></h2><p>The table below ranks only the <strong>owner-reported</strong> values supplied in the ledger. It does not authenticate a score-to-file association, and it does not select a weekly slot. The highest reported claim is <code>{e(historical_winner["site"])} {e(historical_winner["submission"])}</code> at <code>{e(historical_winner["score"])}</code>; it is explicitly <strong>not</strong> an organizer-confirmed score or a recommended upload.</p><div class="evidence-strip" aria-label="Priority-site audit decision"><article><span>Historical upload recommendation</span><strong>NONE</strong><small>No receipt-bound, unique priority-site artifact</small></article><article><span>Current research artifact</span><strong>DO NOT SUBMIT</strong><small>{e(current_decision["run_id"])}</small></article><article><span>Live leaderboard status</span><strong>NOT REFRESHED</strong><small>Last local evidence is a dated snapshot, not a live read</small></article></div></section>
<section class="intro"><div><p class="eyebrow">Executive review · nine requested GEMSDOE sites</p><h1>Best reported is not<br>a valid submission choice.</h1><p class="lead">The useful lesson from the H33 family is metric-aware sparse placement; the unsafe lesson is to reuse a historically high-looking raster. Exact byte audits identify known aliases and a catalogue-flank-pruning derivative. A new candidate must use a distinct physical mechanism, pass the shared holdout, and clear novelty before a separate slot selector can consider it.</p></div><a class="text-link" href="docs/research/priority-site-executive.json">Open machine-readable decision ↗</a></section>
<section class="section"><p class="eyebrow">01 / Highest ledger claim per requested site</p><h2>Every reported number is quarantined.</h2><div class="table-wrap"><table><caption>Owner-reported / unverified values from <code>docs/score-ledger.csv</code> · never HOLDOUT-DTI or ORGANIZER-CONFIRMED</caption><thead><tr><th>Site</th><th>Highest reported submission</th><th>Reported score</th><th>Evidence class</th><th>Executive decision</th></tr></thead><tbody>{priority_rows}</tbody></table></div><p class="fine">“Highest” means numerically highest among the matching owner-report rows in the committed ledger as of 2026-10-25. It does not mean current leaderboard rank, verified performance, or permission to reuse the artifact.</p></section>
<section class="section"><p class="eyebrow">02 / Byte-level findings that change the decision</p><h2>Aliases and pruning cannot become a new method.</h2><div class="table-wrap"><table><caption>Measured from the pinned historical forensic reconstruction</caption><thead><tr><th>Sites</th><th>Finding</th><th>Measured</th></tr></thead><tbody>{lineage_rows}</tbody></table></div><p class="fine">The final H33 relation has <code>{priority_summary["forensic_lineage"][2]["base_dots"]:,}</code> base dots, <code>{priority_summary["forensic_lineage"][2]["h33_dots"]:,}</code> H33 dots, and <code>{priority_summary["forensic_lineage"][2]["mismatching_pixels"]}</code> support mismatches. These are raster diagnostics, not competition results.</p></section>
<section class="section two-column"><div><p class="eyebrow">03 / What actually explains the H33 claim</p><h2>Sparse, de-redundant emission can help; copying it cannot.</h2><p>The distance-weighted Tversky metric credits each truth pixel through a local maximum but accumulates false-positive mass across emitted pixels. Thus 300 m-scale spacing and removal of catalogue-adjacent redundant dots can improve a score if lost weighted coverage is smaller than false-positive penalty saved. This is a mechanism-level explanation of the exact H28→H33 transformation, not proof of an organizer score, a generalizable geological signal, or a way to certify a copied file.</p><p>To move beyond the historical family, improve the belief surface with independently motivated fault physics, then test it using buffered whole-segment hide-and-recover folds, feature canaries, count-matched controls, and the pre-placement/final-dot novelty checks.</p></div><div class="note-card"><h3>Manual-review sources</h3><ul class="spaced"><li><a href="docs/score-ledger.csv">Quarantined score ledger</a></li><li><a href="docs/research/2026-10-25/recipe-reconstruction.json">Exact H33 lineage receipt</a></li><li><a href="docs/research/msdb-piedmont/registry.json">Observed 9-site registry</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official metric/problem page ↗</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official live leaderboard ↗</a></li></ul><p class="fine">The official links are for manual review. This repository does not scrape them or claim a fresh live leaderboard value.</p></div></section>
<section class="section two-column"><div><p class="eyebrow">04 / What H33 establishes — and what it does not</p><h2>Pruning is a measured lineage fact, not a verified score receipt.</h2><p>{e(h33_interpretation["measured_byte_fact"])}</p><p>{e(h33_interpretation["plausible_mechanism_not_score_proof"])}</p><p class="fine"><strong>Boundary:</strong> {e(h33_interpretation["not_established"])}</p></div><div class="note-card"><h3>Could a distinct strategy improve?</h3><p>{e(strategy_assessment["conclusion"])}</p><p class="fine">{e(strategy_assessment["last_local_leaderboard_context"])}</p><h4>Evidence required before an upload</h4><ul class="spaced">{strategy_requirements}</ul></div></section>
<section class="section"><p class="eyebrow">05 / Pre-implementation geological shortlist</p><h2>Four ranked, falsifiable mechanisms — no score promise.</h2><p class="lead">These are the four hypotheses ranked before the MSDB implementation. Their expected benefits are qualitative planning priors, not HOLDOUT-DTI values or organizer-score projections. Rank 1 has been run and is not promoted; ranks 2–4 require a new frozen plan and source verification.</p><div class="table-wrap"><table><caption>Frozen planning hypotheses; official/free source checks are recorded in the machine-readable decision and must be repeated before use</caption><thead><tr><th>Rank</th><th>Mechanism</th><th>Expected benefit / cost</th><th>Current state</th></tr></thead><tbody>{hypothesis_rows}</tbody></table></div><p class="fine">Full layers, non-fault mimics, distinctions, source details, and falsifiable gates: <a href="docs/research/msdb-piedmont/experiment-1-duplicate-stop/preregistration-exp1.md">frozen MSDB preregistration</a>. No historical TIFF is a template for this work.</p></section>'''

    return {
        ROOT / "index.html": page("MSDB-1v2 research GeoTIFF & automated gate decision", home, card, research_dir, active="home"),
        ROOT / "executive-summary.html": page("Executive summary & validation guide", guide, card, research_dir, active="guide"),
        ROOT / "experiment-review.html": page("Scientific review & nine-site audit", research_html, card, research_dir, active="research"),
        ROOT / "priority-site-executive-summary.html": page("Nine-site executive selection audit", priority_html, card, research_dir, active="priority"),
        ROOT / "priority-registry-review.html": page("Public priority registry review", registry_review_html, card, research_dir, active="research"),
        ROOT / "docs/research/priority-site-executive.json": canonical_json(priority_summary),
        ROOT / preview_rel: png_preview(template, local_path(card["published_tiff"])),
        ROOT / "docs/index.html": '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=../index.html"><title>GEMSDOE30</title><link rel="canonical" href="../index.html"></head><body><p><a href="../index.html">Open current research download and submission decision.</a></p></body></html>\n',
    }


def main() -> None:
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
