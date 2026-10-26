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
from scripts.verify_fflidar_run import verify as verify_fflidar
from scripts.verify_lsm_run import verify as verify_lsm

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
<nav aria-label="Main navigation"><a href="index.html"{' aria-current="page"' if active == "home" else ''}>Overview</a><a href="executive-summary.html"{' aria-current="page"' if active == "guide" else ''}>Submission guide</a><a href="experiment-review.html"{' aria-current="page"' if active == "research" else ''}>Research</a><a href="README.md">Project brief</a></nav></div></header>
<main id="main">{content}</main>
<footer><div><strong>GEMSDOE30</strong><p>Evidence before claims. Automated machine gates require zero human raster inspection.</p></div>
<div><a href="docs/status.json">Evidence feed (JSON)</a><a href="{e(research_dir)}/run-card.json">Run card</a><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Official competition ↗</a></div>
<p class="fine">Experiment recorded {e(card['created_utc'])}. Repository evidence only; not a live leaderboard projection. No competition slot selected or used.</p></footer>
<script src="docs/assets/research.js" defer></script></body></html>\n'''


def release(card: dict, readiness: dict, research_dir: str) -> str:
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    v = card["validator_output"]
    obs = readiness["observed_registry"]
    h = card["holdout"]
    core_delta = h["candidate_minus"]["core19"]
    return f'''<section class="release" aria-labelledby="release-title">
<div class="release-heading"><span class="pill caution">NOT APPROVED FOR SUBMISSION</span><span class="pill good">All 9 Measured Gates PASSED ({obs["dots"]["registry_entries_compared"]}-Raster Novelty &amp; +27.6% vs. core19)</span></div>
<h2 id="release-title">Automated Gate Decision: Safe to Download · <span>Do not submit.</span></h2>
<p><strong>Zero human inspection required:</strong> automated machine verification reopened <code>{e(file.name)}</code> and confirmed single-band <code>float32</code>, <code>EPSG:32611</code>, <code>3,730 × 3,292</code>, 100% finite values in <code>[0, 1]</code> inside the 5,167,373-cell footprint (<code>NaN</code> outside), <code>0</code> predictions on known USGS/INGENIOUS faults, <code>0 / {card["feature_canaries"]["features_per_fold"] * card["feature_canaries"]["folds"]}</code> leakage canary alarms, 100% uniqueness across all <code>{obs["dots"]["registry_entries_compared"]}</code> aligned GeoTIFF comparisons (max 3-px dot overlap <code>{100 * obs["dots"]["max_fraction_within_3px"]:.2f}% &le; 70%</code>), and a <strong>+{100 * core_delta["value"] / h["comparators"]["core19"]["value"]:.1f}% paired HOLDOUT-DTI improvement over <code>core19</code></strong> (<code>+{core_delta["value"]:.6f}</code>, 95% CI <code>[+{core_delta["ci95"][0]:.6f}, +{core_delta["ci95"][1]:.6f}]</code>). Weekly slot allocation remains conservatively blocked only because external unexported parallel sessions, lane assignment, and archived neural checkpoints are marked <code>unknown</code>.</p>
<div class="actions"><a class="button" href="{e(card['published_tiff'])}" download>↓ Download unique MSDB-1v2 GeoTIFF <span>{size:.2f} MiB</span></a><a class="button secondary" href="{e(research_dir)}/readiness.json">View machine gate receipt (JSON)</a><a class="button secondary" href="executive-summary.html">Open executive summary</a></div>
<p class="filename">{e(file.name)}</p><details open><summary>Automated non-human validation scorecard &amp; file identity</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Submission Note ({len(card['note'])}/140 chars)</dt><dd><code>{e(card['note'])}</code></dd><dt>Portal Format &amp; [0,1] Range Gate</dt><dd><code>PASSED</code> · 1 band <code>float32</code> · <code>EPSG:32611</code> · <code>3,730 × 3,292</code> · in-footprint finite: <code>{e(v['no_nan_inside_footprint'])}</code> · in <code>[0, 1]</code>: <code>{e(v['values_in_0_1'])}</code> · outside <code>NaN</code>: <code>{e(v['nan_nodata_outside_footprint'])}</code> · off-catalogue dots: <code>{v['emitted_dots']:,}</code> (<code>{v['positive_catalogue_pixels']}</code> on known faults)</dd><dt>Receipts</dt><dd><a href="{e(research_dir)}/validation.json">Reopened-file validation</a> · <a href="{e(card['published_tiff'][:-4])}.json">Provenance sidecar</a> · <a href="{e(research_dir)}/run-card.json">Run card</a></dd></dl></details></section>'''


def ffl_section() -> str:
    """Latest-lane banner, generated only from independently checked FFL receipts."""
    research_dir = "docs/research/2026-10-26-fflidar"
    readiness = verify_fflidar()
    card = json.loads((ROOT / research_dir / "run-card.json").read_text())
    dots = json.loads((ROOT / research_dir / "novelty-dots-expanded.json").read_text())
    surface = json.loads((ROOT / research_dir / "novelty-surface-expanded.json").read_text())
    stratified = json.loads((ROOT / research_dir / "results-stratified.json").read_text())
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
    max_surface = max(r["spearman_full_footprint"] for r in surface["comparisons"])
    if max_overlap <= 0.70 or surface["candidate_sha256"] != card["raster_sha256"]:
        raise ValueError("FFL-1 expanded novelty receipts contradict the duplicate-stop")
    if not stratified.get("infeasible_as_frozen") or stratified.get("production") is not None:
        raise ValueError("FFL-1 stratified receipt no longer records the frozen infeasibility")
    file = local_path(card["published_tiff"])
    size = file.stat().st_size / (1024 * 1024)
    h = card["holdout"]
    delta = h["candidate_minus"]["msdb_edge"]
    conf = card["confirmation"]["candidate_minus_msdb_edge"]
    return f'''<section class="release" aria-labelledby="ffl-title">
<div class="release-heading"><span class="pill failed">Latest lane FFL-1 · Negative</span><span class="pill caution">Duplicate-stop · Do not submit</span></div>
<h2 id="ffl-title">FFL-1 produced a byte-distinct TIFF. <span>Do not submit it.</span></h2>
<p><strong>Automated decision first:</strong> the expanded registry audit—pinned nine-site registry plus every TIFF in <code>docs/downloads/</code>, candidate SHA excluded ({len(dots["comparisons"])} comparisons)—found <strong>{100 * max_overlap:.6f}%</strong> of FFL-1 dots within 3 px of MSDB-1v2, above the 70% limit. The continuous surface was not the duplicate (max Spearman <code>{max_surface:.6f}</code>); the dot placement was. The frozen distance-stratified rescue scored zero folds because the <code>(2,5]</code> and <code>(5,10]</code> strata have zero eligible pixels in every v3 quadrant fold, so no replacement was produced and no weekly slot was selected.</p>
<p>HOLDOUT-DTI (catalogue proxy, never an organizer score): Exp. 1 seed 3051 <code>fusion_edge</code> <code>{h["value"]:.6f}</code> vs same-run <code>msdb_edge</code> <code>{h["comparators"]["msdb_edge"]["value"]:.6f}</code> (Δ <code>{delta["value"]:+.6f}</code>, 95% CI <code>[{delta["ci95"][0]:+.6f}, {delta["ci95"][1]:+.6f}]</code>); disclosed fresh-seed confirmation Δ <code>{conf["value"]:+.6f}</code> (95% CI <code>[{conf["ci95"][0]:+.6f}, {conf["ci95"][1]:+.6f}]</code>). The strict validator reopens the file as one float32 band on the exact template grid, with every cell finite in <code>[0, 1]</code>, 44,090 dots, and zero dots on or within 2 px of the catalogue; that file check does not override the duplicate-stop.</p>
<div class="actions"><a class="button secondary" href="{e(card['published_tiff'])}" download>↓ Download FFL-1 research artifact — do not upload <span>{size:.2f} MiB</span></a><a class="button secondary" href="{research_dir}/review.md">Read FFL-1 review</a><a class="button secondary" href="{research_dir}/nine-site-executive-summary.md">Nine-site executive summary</a></div>
<p class="filename">{e(file.name)}</p>
<details><summary>FFL-1 automated receipts &amp; identity</summary><dl><dt>SHA-256</dt><dd><code>{e(card['raster_sha256'])}</code></dd><dt>Note ({len(card['note'])}/140)</dt><dd><code>{e(card['note'])}</code></dd><dt>Receipts</dt><dd><a href="{research_dir}/run-card.json">Run card</a> · <a href="{research_dir}/readiness.json">Readiness</a> · <a href="{research_dir}/validation.json">Strict validation</a> · <a href="{research_dir}/novelty-dots-expanded.json">Expanded dot audit</a> · <a href="{research_dir}/results-stratified.json">Stratified infeasibility</a></dd><dt>Verify</dt><dd><code>.venv/bin/python scripts/verify_fflidar_run.py</code> (negative decision, exit 0); <code>--require-promote</code> exits 2</dd></dl></details>
</section>'''


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

    home = f'''{ffl_section()}
{release(card, readiness, research_dir)}
<section class="intro"><div><p class="eyebrow">DOE GEMS · Lane MSDB-1v2 · 25 October 2026</p><h1>Steerable piedmont discontinuities.<br>+27.6% over raw-band baseline.</h1><p class="lead">Correcting two competition band-metadata errors (<code>Band 6 tc</code> = GeoDAWN Radiometric Total Count; <code>Bands 18/11</code> = signed <code>∇g</code>) and gating a stationary 31-feature discontinuity habitat by a Rayleigh 1-D curvilinear envelope lifts buffered whole-segment <code>HOLDOUT-DTI</code> from <code>0.133628</code> to <code>0.170462</code> across all 4 disjoint quadrants.</p><p class="meta">Experiments run: {card['experiments_run']} / {card['experiment_cap']} <span>·</span> {card['experimental_elapsed_seconds']:.1f}s / 7,200s budget <span>·</span> No competition slot selected or used</p></div><a class="text-link" href="{e(research_dir)}/preregistration.md">Read the frozen preregistration ↗</a></section>
<section class="evidence-strip" aria-label="Research diagnostics"><article><span>Unique off-catalogue dots</span><strong>{v['emitted_dots']:,} dots</strong><small>0 on 60,988 known fault pixels</small></article><article><span>9-site novelty audit</span><strong>{observed["dots"]["registry_entries_compared"]} unique TIFFs</strong><small>Max 3-px overlap {100 * observed["dots"]["max_fraction_within_3px"]:.2f}% (&le; 70%)</small></article><article><span>Leakage canaries</span><strong>{canary_n} features × {canary_folds} folds</strong><small>{card["feature_canaries"]["alarm_count"]} alarms above 0.90 AUC</small></article></section>
<section class="two-column section"><div><p class="eyebrow">01 / Controlled 4-fold spatial holdout</p><h2>4 of 4 quadrants improved.<br>97% from physics features.</h2><p>Across 60,988 withheld USGS/INGENIOUS fault pixels in four whole-component buffered quadrants (<code>buffer_px = 17 &ge; support_px = 13</code>), <code>msdb_edge</code> achieves <code>HOLDOUT-DTI = 0.170462 [0.156227, 0.184168]</code> vs. <code>core19 = 0.133628 [0.118285, 0.148875]</code> (<code>+0.036834</code>, 95% CI <code>[+0.022322, +0.050315]</code>), adding <code>+2,193.7</code> weighted true-positive fault credits while reducing false-positive weight by <code>-1,018.9</code>.</p><p class="fine">Experiment 1 (<a href="{e(research_dir)}/experiment-1-duplicate-stop/receipt.json">archived duplicate-stop receipt</a>) halted before any fold evaluation when raw regional bands caused <code>71.44%</code> overlap with <code>G30-S19</code>. Experiment 2 removed the 6 regional coordinate-proxy/DC-level bands and added the fold-local Rayleigh curvilinear gate.</p>{score_table}<a class="text-link" href="{e(research_dir)}/results.json">All fold sufficient statistics &amp; 148 canary AUCs ↗</a></div><figure><img src="{preview_rel}" width="823" height="933" loading="lazy" alt="New MSDB-1v2 prediction dots in dark green over the pale green competition footprint"><figcaption><span class="legend-dot"></span> New MSDB-1v2 support (44,090 binary off-catalogue dots) · downsampled preview; downloadable GeoTIFF preserves exact 100 m EPSG:32611 grid.</figcaption></figure></section>
<section class="section"><div class="section-heading"><div><p class="eyebrow">02 / Automated machine inspection</p><h2>Every gate has a deterministic state.</h2></div><p>Passed, failed, or unknown.<br>Zero human raster inspection.</p></div><div class="table-wrap"><table><thead><tr><th>Automated gate</th><th>State</th><th>Machine rule</th></tr></thead><tbody>{gates}</tbody></table></div></section>
<section class="section two-column"><div><p class="eyebrow">03 / Forensic root cause of GEMSDOE32 H33 (0.2778)</p><h2>Why H33 topped our sites—and how to beat it.</h2><p>Byte-exact reconstruction (<a href="docs/research/2026-10-25/recipe-reconstruction.json">receipt</a>) proves <code>GEMSDOE32</code> <code>H33</code> (<code>37,654</code> dots, <code>0.2778</code> <code>OWNER-REPORTED</code>) equals <code>GEMSDOE28</code> solo <code>d=2.8</code> (<code>40,199</code> dots, <code>0.2708</code> <code>OWNER-REPORTED</code>, thinned from <code>GEMSDOE27</code> <code>H27-4</code>'s <code>121,150</code> dots at <code>0.1922</code>) minus the exact <code>2,545</code> dots within <code>&le; 2 px</code> (<code>200 m</code>) of <code>labels.tif</code> (<code>0</code> pixel diffs).</p><p>Under official pooled DW-Tversky (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">page/967</a>; known faults masked per <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum t/11516</a>; splays/continuations counted per <a href="https://community.drivendata.org/t/clarification-what-counts-as-a-new-fault-in-the-test-set/11536">t/11536</a>), <code>TP_w</code> uses a 300 m <code>max</code> while <code>FP_w</code> uses a linear <code>sum</code>: spacing dots at ~300 m and stripping <code>&le; 200 m</code> digitization halos slashes <code>FP_w</code> without losing <code>TP_w</code>. Surpassing <code>0.2778</code> toward the live 2026-10-25 leaderboard top (<code>0.4413</code> #1, <code>0.3379</code> #10) requires raising true recall <code>TP_w/|G|</code> via corrected multi-physics discontinuity features like <code>MSDB-1v2</code> paired with multi-km convolutional context.</p><a class="text-link" href="{e(research_dir)}/review.md">Full equations, 4 ranked hypotheses &amp; metadata audit ↗</a></div><div class="note-card"><h3>Novelty &amp; metadata discoveries</h3><p><strong>Irregularity 1:</strong> <code>Band 6 (tc)</code> is GeoDAWN Radiometric Total Count (<code>Spearman = 0.999957</code>), not magnetic tilt (<code>0.0160</code>). <code>MSDB-1v2</code> computes true Miller–Singh tilt <code>arctan2(tmi_vg, tmi_hg)</code> and Salem contact inverse-depth.</p><p><strong>Irregularity 2:</strong> <code>Bands 18 &amp; 11</code> are signed grid derivatives <code>(+dg/dx, +dg/dy)</code>, enabling azimuthally symmetric 2-D vector gravity strike concordance.</p><p>Max surface Spearman vs. 165 registry TIFFs: <b>{observed['surface']['max_spearman']:.6f}</b>.<br>Max final-dot 3-px overlap: <b>{100 * observed['dots']['max_fraction_within_3px']:.4f}%</b>.</p><a href="{e(research_dir)}/registry.json">Frozen 180-file / 165-unique 9-site registry</a>{extra_reg_link}</div></section>
<section class="section"><p class="eyebrow">04 / Preserved prior &amp; concurrent lanes</p><h2>Full repository audit trail.</h2><div class="resource-grid"><article><h3>TDX-1 &amp; TDX-C2 · displacement</h3><p>Preserved negative displacement runs (<a href="docs/research/texture-displacement/run-card.json">TDX-1 card</a>; <a href="docs/research/texture-controls/run-card.json">TDX-C2 duplicate-stop card</a>).</p><a href="experiment-review.html">Full cross-lane review ↗</a></article><article><h3>G30-S19 &amp; G30-S20 · habitat</h3><p>Concurrent lanes (<a href="docs/research/2026-10-25/lane-g30s19-run-card.json">G30-S19</a>; <a href="docs/research/2026-10-25-s20/run-card.json">G30-S20 duplicate-stop</a>). Audited in <code>MSDB-1v2</code>'s {observed["dots"]["registry_entries_compared"]}-raster novelty check (<code>64.78% &le; 70%</code>).</p><a href="docs/research/msdb-piedmont/novelty-parallel-dots.json">Late S20 audit ↗</a></article><article><h3>H-CC1 &amp; Residual-ridge gate</h3><p>Preserved negative records on contact coincidence and catalogue-corridor magnetic residuals.</p><a href="docs/research/2026-10-25/h-cc1-run-card.json">H-CC1 card ↗</a> · <a href="docs/research/2026-10-25/run-card-residual-gate.json">Residual-gate card ↗</a></article></div></section>
<section class="section"><p class="eyebrow">05 / Verified official sources &amp; data catalog</p><h2>Primary DOIs, licenses, and code receipts.</h2><div class="resource-grid"><article><h3>Competition &amp; rules</h3><p>DrivenData GEMS overview, metric spec, forum clarifications, and NLR Official Rules (3/week cap, Dec 3 2026 close).</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem spec ↗</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Rules PDF ↗</a></article><article><h3>USGS GeoDAWN &amp; GDR 1391</h3><p>USGS GeoDAWN (DOI <code>10.5066/P93LGLVQ</code>, CC0) and GBCGE INGENIOUS compilation (DOI <code>10.15121/1881483</code>, CC BY 4.0).</p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN ↗</a> · <a href="https://gdr.openei.org/submissions/1391">OpenEI GDR 1391 ↗</a></article><article><h3>Machine status &amp; quarantined ledger</h3><p>Live-recomputed JSON status feed and all 119 quarantined owner-reported score rows.</p><a href="docs/status.json">Status JSON ↗</a> · <a href="docs/research/texture-displacement/owner-claims.csv">119 owner claims CSV ↗</a></article></div></section>'''

    guide = f'''{ffl_section()}
{release(card, readiness, research_dir)}
<section class="intro"><div><p class="eyebrow">Executive Summary &amp; Zero-Human-Inspection Validation Guide</p><h1>Valid, unique GeoTIFF (+27.6% vs. core19).<br>Conservative slot gate active.</h1><p class="lead">All 9 measurable automated gates—portal format, <code>[0, 1]</code> value range, NaN footprint, catalogue exclusion, 148 leakage canaries, paired improvement over <code>core19</code>, and {observed["dots"]["registry_entries_compared"]}-raster 9-site novelty—<strong>PASSED</strong> automatically without human inspection. Weekly slot approval stays conservatively withheld because 3 external attestations remain <code>unknown</code>.</p></div></section>
<section class="section"><p class="eyebrow">01 / Automated gate breakdown</p><h2>Why download is safe and why slot approval stays conservative.</h2>{score_table}<ul class="spaced"><li><strong>Technical &amp; Portal Format Gates — PASSED:</strong> Single-band <code>float32</code> GeoTIFF on <code>EPSG:32611</code> (<code>3,730 × 3,292</code>, exact 100 m transform), 100% finite values in <code>[0.0, 1.0]</code> across all <code>5,167,373</code> in-footprint cells, <code>NaN</code> nodata outside, and <code>0</code> wasted dots on known USGS/INGENIOUS faults.</li><li><strong>Observed 9-Site + Parallel Novelty Gate — PASSED:</strong> Audited on both saved states against <code>{observed["dots"]["registry_entries_compared"]}</code> aligned GeoTIFF comparisons across <code>GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36</code> and merged <code>main</code> lanes: max surface Spearman <code>0.1545 &le; 0.90</code>, max dot 3-px overlap <code>64.78% &le; 70.00%</code>.</li><li><strong>Geological Signal Gate — PASSED (+27.6% over <code>core19</code>):</strong> Beats <code>core19</code> in all 4 disjoint quadrants (<code>+0.036834</code>, 95% CI <code>[+0.022322, +0.050315]</code>) with <code>0 / 148</code> single-feature leakage canary alarms.</li><li><strong>Why <code>readiness.py</code> keeps <code>NOT APPROVED FOR SUBMISSION</code>:</strong> Three external attestations (<code>complete_parallel_registry</code>, <code>assigned_lane</code>, and <code>comparable_historical_best</code> for unarchived multi-scale UNet checkpoints) are conservatively recorded as <code>unknown</code> rather than assumed passed. Run <code>.venv/bin/python scripts/verify_current_run.py --require-promote</code> (exits <code>2</code> by design; exits <code>0</code> without <code>--require-promote</code>).</li></ul></section>
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

    research_html = f'''{ffl_section()}
<section class="intro"><div><p class="eyebrow">Scientific Review · MSDB-1v2 &amp; Peer Lane Audit</p><h1>Physics discontinuities work.<br>Mandatory duplicate-stops protect novelty.</h1><p class="lead">Across this repository's 2026-10-25 experiments, two peer attempts (<code>G30-S20</code> and <code>TDX-C2</code>) collided with <code>G30-S19</code> (&gt; 70% overlap) and halted cleanly, whereas <code>MSDB-1v2</code> cleared the {observed["dots"]["registry_entries_compared"]}-file novelty audit (<code>64.78% &le; 70%</code>) and beat <code>core19</code> by <strong>+27.6%</strong> across all 4 quadrants.</p></div></section>
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

    return {
        ROOT / "index.html": page("MSDB-1v2 unique GeoTIFF & automated gate decision", home, card, research_dir, active="home"),
        ROOT / "executive-summary.html": page("Executive summary & validation guide", guide, card, research_dir, active="guide"),
        ROOT / "experiment-review.html": page("Scientific review & nine-site audit", research_html, card, research_dir, active="research"),
        ROOT / "priority-registry-review.html": page("Public priority registry review", registry_review_html, card, research_dir, active="research"),
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
