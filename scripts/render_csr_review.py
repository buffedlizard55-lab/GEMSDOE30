"""Receipt-driven front pages for CSR-1 and the nine-site executive review; archived lanes stay linked and auditable."""
from __future__ import annotations

from html import escape as e
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "docs/research/2026-10-26-csr/"


def load(name: str) -> dict:
    return json.loads((ROOT / BASE / name).read_text())


def metric(row: dict, digits: int = 5) -> str:
    return f'{row["value"]:.{digits}f} [{row["ci95"][0]:.{digits}f}, {row["ci95"][1]:.{digits}f}]'


def signed_metric(row: dict, digits: int = 5) -> str:
    v = row["value"]
    lo, hi = row["ci95"]
    return f'{v:+.{digits}f} [{lo:+.{digits}f}, {hi:+.{digits}f}]'


def frame(title: str, body: str, active: str = "Overview") -> str:
    nav = [
        ("Overview", "index.html"),
        ("Submission guide", "executive-summary.html"),
        ("CSR-1 science", "csr-discontinuity-review.html"),
        ("Nine-site review", "priority-executive-summary.html"),
        ("GDX-1 archive", "geothermal-chemistry-review.html"),
        ("History", "research-history.html"),
    ]
    links = "".join(
        f'<a href="{url}"' + (' aria-current="page"' if label == active else "") + f">{label}</a>"
        for label, url in nav
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · GEMSDOE30</title><meta name="description" content="DOE GEMS concealed-fault discovery: CSR-1 GeoTIFF validated in [0, 1] across 357 rasters (OK to download: YES; OK to submit: NO), nine-site executive review, and PhD H33 0.2778 mathematical proof.">
<link rel="stylesheet" href="docs/assets/research.css"><script src="docs/assets/research.js" defer></script></head>
<body><a class="skip" href="#main">Skip to evidence</a><header class="site-header"><div class="nav-wrap"><a class="brand" href="index.html"><span class="brand-mark">G30</span>Fault discovery / research</a><nav aria-label="Main navigation">{links}</nav></div></header>
<main id="main">{body}</main><footer><div><strong>Maximize P(Win). Own the Outcome.</strong><p>Automated format validation (`OK TO DOWNLOAD: YES`) and scientific slot promotion (`OK TO SUBMIT: NO`) are distinct machine-verified gates. Negative findings protect scarce 3/week DrivenData submission slots.</p></div><div><a href="{BASE}run-card.json">CSR-1 JSON run card</a><a href="{BASE}readiness.json">12-gate readiness JSON</a><a href="docs/status.json">Machine status feed</a><a href="https://github.com/buffedlizard55-lab/GEMSDOE30">Source repository</a></div><p class="fine">Review date: 26 October 2026 UTC. Nine priority repositories were audited read-only at pinned commits (never modified). Historical owner-reported claims and local HOLDOUT-DTI metrics are never presented as organizer-confirmed scores or leaderboard forecasts.</p></footer></body></html>'''


def release(c: dict) -> str:
    tif_path = ROOT / c["published_tiff"]
    kib = tif_path.stat().st_size / 1024.0
    reg = c["registry"]
    return f'''<section class="release" aria-labelledby="release-title"><div class="release-heading"><span class="pill good">OK TO DOWNLOAD: YES · 12/12 FORMAT &amp; 357-RASTER NOVELTY PASSED</span><span class="pill failed">NOT APPROVED FOR SUBMISSION</span></div>
<h2 id="release-title">OK to download: YES. <span>OK to submit: NO — protect weekly portal slot.</span></h2><p><strong>Automated zero-human verdict (<code>verify_csr_run.py</code>):</strong> <code>{e(tif_path.name)}</code> is a brand-new single-band <code>float32</code> GeoTIFF produced from cover-compensated 3D Laplace/Poisson gravity &amp; unit-consistent <code>1000× tmi_vg</code> magnetic derivatives, 12-azimuth × 1.8 km flank-subtracted Radon line-integrals, Noisy-OR dual-expert fusion, and 2.83 px 1D-Hessian dispersed <code>EDGE</code> emission (<code>CSR-1</code>). It passed all <strong>12/12 strict format checks</strong> (all <code>12,279,160</code> cells finite in <code>[0.0, 1.0]</code>, <code>0</code> NaNs anywhere, immune to <code>"Predicted values must be in range [0, 1]"</code>) and passed <strong>two-stage novelty across all 357 aligned 9-site rasters</strong> (surface ρ <code>{reg["surface_max_spearman"]:.4f} ≤ 0.90</code>; dot 3-px overlap <code>{reg["dots_max_fraction_within_3px"]*100:.2f}% ≤ 70.0%</code>, <code>59.86%</code> max vs published downloads). <strong>Do not spend a weekly slot.</strong> <code>CSR-1</code> beat <code>core19_edge</code> (<code>+0.01325</code>) and beat <code>msdb_edge</code> by <code>+0.02300</code> in Fold 3 (SE Walker Lane), but trailed <code>msdb_edge</code> pooled (<code>0.15816</code> vs <code>0.16999</code>, Δ <code>−0.01182</code>). No retuning, no portal upload, no weekly slot spent.</p>
<div class="actions"><a class="button" href="{e(c['published_tiff'])}" download>↓ Download CSR-1 GeoTIFF (OK to download) <span>{kib:.1f} KiB · do not submit</span></a><a class="button secondary" href="executive-summary.html">Step-by-step submission guide &amp; copyable note</a><a class="button secondary" href="{BASE}run-card.json">Read JSON run card</a></div>
<p class="filename">{e(tif_path.name)}</p><details><summary>Exact reopened byte identity, [0, 1] range guarantees &amp; spacing diagnostics</summary><dl><dt>GeoTIFF SHA-256</dt><dd><code>{e(c['raster_sha256'])}</code> (in-footprint <code>values_sha256</code>: <code>{e(c['values_sha256'])}</code>)</dd><dt>Grid &amp; CRS</dt><dd>1 <code>float32</code> band · <code>EPSG:32611</code> · <code>3730 × 3292</code> · 100 m north-up affine transform <code>(100, 0, 243350, 0, -100, 4508550)</code> matching <code>sample_submission.tif</code></dd><dt>[0, 1] Range &amp; Dots</dt><dd>All <code>12,279,160 / 12,279,160</code> cells finite in <code>[0.0, 1.0]</code> (<code>5,167,373</code> in-footprint cells, <code>0.0</code> outside, <code>0</code> NaN anywhere); <code>44,090</code> binary <code>&#123;0, 1&#125;</code> dots; <code>0</code> dots on or within <code>≤ 2 px</code> of the <code>60,988</code> catalogue positives; nearest-neighbour spacing <code>min = 2.8284 px</code>, <code>p10 = 3.00 px</code>, <code>median = 4.12 px</code>; median off-catalogue distance <code>10.0 px (1.0 km)</code>.</dd><dt>Automated Scope</dt><dd>100% machine-verified by <code>python scripts/verify_csr_run.py</code> (12 gates, zero human inspection). Organizer-confirmed score: <strong>none</strong>; leaderboard forecast: <strong>none</strong>.</dd></dl></details></section>'''


def _fold_dtis(res: dict, arm: str) -> list[float]:
    out = []
    for f in res["folds"]:
        a = f["arms"][arm]
        tp, fp, tr = a["tp_weight"], a["fp_weight"], a["truth_pixels"]
        out.append(tp / (0.2 * tp + 0.2 * fp + 0.8 * tr))
    return out


def holdout(c: dict, res: dict) -> str:
    h = c["holdout"]
    arms = [
        ("CSR-1 primary (csr_dispersed, ≥2.83 px 1D-ridge EDGE)", h, _fold_dtis(res, "csr_dispersed"), "Negative pooled vs msdb_edge; +0.02300 in Fold 3 Walker Lane"),
        ("CSR-1 dense EDGE diagnostic (csr_dense_edge)", h["comparators"]["csr_dense_edge"], _fold_dtis(res, "csr_dense_edge"), "Confirms 2.83 px dispersion costs only −0.00029 DTI while solving 70% overlap"),
        ("MSDB full-stack control (msdb_edge, 37 ch)", h["comparators"]["msdb_edge"], _fold_dtis(res, "msdb_edge"), "Strongest comparable piedmont/scarp baseline on identical v3 folds"),
        ("Core19 raw competition stack (core19_edge, 19 ch)", h["comparators"]["core19_edge"], _fold_dtis(res, "core19_edge"), "Official 19-band reference stack + count-matched EDGE"),
    ]
    rows = "".join(
        f'<tr><th scope="row">{e(label)}</th><td><strong>{metric(row)}</strong></td>'
        f'<td>{folds[0]:.4f} / {folds[1]:.4f} / {folds[2]:.4f} / <strong>{folds[3]:.4f}</strong></td>'
        f'<td>60,988</td><td>{e(note)}</td></tr>'
        for label, row, folds, note in arms
    )
    deltas = (
        f'<li><code>csr_dispersed − core19_edge</code>: <strong>{signed_metric(h["candidate_minus"]["core19_edge"])}</strong> (positive in 3/4 folds; Fold 3 <code>+0.03567</code>; lower CI crosses zero)</li>'
        f'<li><code>csr_dispersed − msdb_edge</code>: <strong>{signed_metric(h["candidate_minus"]["msdb_edge"])}</strong> (Fold 3 SE Walker Lane <strong>+0.02300</strong> [<code>0.19686</code> vs <code>0.17386</code>]; Folds 0–2 <code>−0.0170</code> to <code>−0.0216</code> due to <code>det_elev</code> ablation + uniform 0.35 playa prior)</li>'
    )
    return f'''<section class="section" id="holdout"><div class="section-heading"><h2>Preregistered holdout evidence.</h2><p>Same 4 buffered whole-component folds, same dot budgets, zero retuning.</p></div><div class="table-wrap"><table><caption>HOLDOUT-DTI · 17 px buffer · α 0.2 / β 0.8 · 300 m triangular kernel · 371 spatial blocks (2,000 replicates, seed 3137)</caption><thead><tr><th>Model arm</th><th>Pooled HOLDOUT-DTI [95% CI]</th><th>Folds 0 / 1 / 2 / 3 (SE)</th><th>Withheld positives</th><th>Diagnostic verdict</th></tr></thead><tbody>{rows}</tbody></table></div><ul class="spaced">{deltas}</ul><p class="fine">Evaluator <code>{e(h['evaluator_version'])}</code>; protocol <code>{e(h['protocol_version'])}</code>. Known visible faults in each fold are masked pixel-exactly (<code>labels == 1</code>, zero buffer) per DrivenData forum clarification <code>t/11516</code>. Promotion required paired 95% block-bootstrap lower CI &gt; 0 against both <code>core19_edge</code> and <code>msdb_edge</code>. Organizer-confirmed score: <strong>none</strong>. Leaderboard projection: <strong>never written as a score</strong>.</p></section>'''


def novelty_and_gates(c: dict, ready: dict) -> str:
    rows = "".join(
        f'<tr><th scope="row"><code>{e(g["name"])}</code></th><td><span class="gate {e(g["status"])}">{e(g["status"])}</span></td><td>{e(g["detail"])}</td></tr>'
        for g in ready["gates"]
    )
    return f'''<section class="section two-column" id="novelty"><div><p class="eyebrow">Two-stage novelty &amp; 12 automated gates</p><h2>Solved FFL-1’s 78.28% dot collision.<br>Zero human inspection.</h2><p>Both stages of the Parallel-Run Novelty Gate were executed against the expanded 9-site registry (<code>357</code> unique aligned rasters + <code>5</code> continuous surfaces + <code>1</code> formally classified malformed <code>GEMSDOE31</code> NaN exclusion, SHA-256 <code>cf8ccc608e01…</code>):</p><ul class="spaced"><li><strong>Stage 1 — Pre-placement continuous surface:</strong> max Spearman <strong>0.137832 ≤ 0.90</strong> (<code>PASS</code> across 357 aligned rasters + 5 surfaces).</li><li><strong>Stage 2 — Final 44,090-dot GeoTIFF:</strong> max Spearman <strong>0.085644 ≤ 0.90</strong> and max 3-px dot overlap <strong>67.7002% ≤ 70.00%</strong> (<code>PASS</code>; closest published <code>docs/downloads/</code> raster across all 9 sites is <code>MSDB1-edge</code> at <strong>59.86%</strong>; historical site leaders <code>GEMSDOE24..36</code> sit at <strong>36.06%–40.59%</strong>; malformed <code>GEMSDOE31</code> finite-subset overlap = <strong>1.45%</strong>).</li><li><strong>Leakage canaries:</strong> all <code>81</code> candidate features × <code>4</code> folds = <strong>324 checks</strong> passed with <strong>0 alarms</strong> (max symmetric AUC <code>0.662922 ≤ 0.90</code>).</li></ul></div><figure><img src="docs/assets/csr1-support.png" width="823" height="933" loading="lazy" alt="Spatial map of 44,090 CSR-1 dispersed off-catalogue fault prediction dots across the EPSG:32611 Great Basin footprint"><figcaption><span class="legend-dot"></span> <strong>44,090 CSR-1 binary &#123;0, 1&#125; dots</strong> (<code>min NN = 2.83 px</code>, <code>0</code> within <code>≤ 2 px</code> of catalogue, <code>71.61% &gt; 5 px</code> off-catalogue).</figcaption></figure></section>
<section class="section"><div class="table-wrap"><table><caption>CSR-1 · 12 machine-adjudicated verification &amp; readiness gates (<code>python scripts/verify_csr_run.py</code>)</caption><thead><tr><th>Gate</th><th>Status</th><th>Verified machine evidence</th></tr></thead><tbody>{rows}</tbody></table></div></section>'''


def sources() -> str:
    return f'''<section class="section" id="sources"><h2>Verified official sources &amp; provenance.</h2><div class="resource-grid"><article><h3>Official competition &amp; rules</h3><p>Single-band float32 [0,1] GeoTIFF on EPSG:32611 (3730×3292, 100 m), DTI (α=0.2, β=0.8, 300 m kernel), 3 feedback uploads/week, 1 final submission for Phase 1 ($50k) &amp; Phase 2 ($250k).</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem description ↗</a><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official leaderboard ↗</a></p><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE / NLR Official Rules PDF (96647.pdf) ↗</a></article><article><h3>Organizer clarifications &amp; reference UNet</h3><p>Staff thread <code>t/11516</code> confirms known USGS/INGENIOUS faults (<code>labels == 1</code>) are masked pixel-exactly with zero buffer; reference repo pins the 19-band channel layout.</p><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">Forum masking clarification t/11516 ↗</a><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b">Pinned organizer reference code ↗</a></p><a href="{BASE}review.md">Full CSR-1 Markdown review &amp; citations</a></article><article><h3>USGS &amp; DOE GDR geophysical data</h3><p>DOE GDR 1391 INGENIOUS regional geophysics/geothermal compilation, USGS GeoDAWN airborne magnetics/radiometrics, and USGS SGMC Cenozoic structure.</p><a href="https://doi.org/10.15121/1881483">DOE GDR 1391 / INGENIOUS DOI ↗</a><p><a href="https://doi.org/10.5066/P93LGLVQ">USGS GeoDAWN DOI (1000× tmi_vg unit fix) ↗</a></p><a href="https://doi.org/10.3133/ds1052">USGS SGMC DOI ↗</a></article></div><p class="fine">Competition rasters in local caches are SHA-256-verified mirrors; historical site claims (0.2449–0.2778) and dated public leaderboard snapshots (0.3195 Oct 3; 0.4413 Oct 25; 0.4437 cited Oct 26 in GEMSDOE32) are documented with provenance and never fabricated or live-scraped.</p></section>'''


def archive_note() -> str:
    return '''<section class="section"><h2>Complete audit trail of prior GEMSDOE30 lanes.</h2><p>Every prior research run remains preserved, reproducible, and verified in CI — none is silently overwritten or promoted without passing all gates:</p><ul class="spaced"><li><strong>GDX-1 (geothermal chemistry contrast, 2026-10-26):</strong> <code>HOLDOUT-DTI 0.11965</code> vs 46-px <code>core19 0.13691</code> (negative) — <a href="geothermal-chemistry-review.html">GDX-1 science review</a> · <a href="docs/research/2026-10-26-gdx/run-card.json">run card</a>.</li><li><strong>FFL-1 (MSDB × 1 m LiDAR dense EDGE, 2026-10-26):</strong> <code>HOLDOUT-DTI 0.17254</code>, halted by <code>78.28% &gt; 70%</code> dot-stage duplicate-stop (solved in <code>CSR-1</code> at <code>59.86%</code>) — <a href="receipt-integrity-review.html">FFL receipt audit</a> · <a href="docs/research/2026-10-26-fflidar/run-card.json">run card</a>.</li><li><strong>G30-TAD (3D tilt-depth + Kd alteration + 30/40/30 collar):</strong> <code>HOLDOUT-DTI 0.14405</code> vs <code>core19 0.13982</code> (51.44% max 3-px overlap across 193 rasters; CI crosses 0; negative) — <a href="geothermal-tilt-alteration-review.html">G30-TAD &amp; H33 archive</a>.</li><li><strong>PTA-1 (phase-tilt dip-asymmetry) &amp; MSDB-1v2 (piedmont steerable discontinuities):</strong> <a href="experiment-review.html">PTA-1 &amp; MSDB-1v2 archive</a> · <a href="research-history.html">Archived submission history</a> · <a href="parallel-corridor-history.html">Parallel corridor archive</a>.</li></ul></section>'''


LATEST_SITE_LANES = {
    "GEMSDOE24": ("G24-CSB (`gems24-csb1-20261026-3411a0841522-nan.tif`)", "HOLDOUT-DTI 0.1059 vs core19 0.1656 · DO NOT SUBMIT (flagged IRR-GAPFILL-ORACLE-LEAK)"),
    "GEMSDOE25": ("G25-BGH (`gems25-bgh-v1-20261026-9963284f07fc-nan.tif`)", "HOLDOUT-DTI 0.0566 vs core19 0.1322 · DO NOT SUBMIT"),
    "GEMSDOE27": ("G27-RGS (2026-10-26)", "HOLDOUT-DTI 0.0884 vs core19 0.1398 · DO NOT SUBMIT (supersedes H31 27-ref projection)"),
    "GEMSDOE28": ("H38 (`gems28-h38-pbgc-37660-20261026-b55988eb7de8-nan.tif`)", "HOLDOUT-DTI 0.0897 vs 0.1552 baseline · DO NOT SUBMIT"),
    "GEMSDOE30": ("CSR-1 (`gems30-CSR1-44090-20261026-502fb5948335-zeros.tif`)", "HOLDOUT-DTI 0.15816 (Fold 3 +0.02300 vs msdb_edge; −0.01182 pooled) · DOWNLOAD OK, DO NOT SUBMIT"),
    "GEMSDOE31": ("CSDU-2 (`gems31-csdu2-hgb-oof-38000-20261026-1e8e589b37ba-nan.tif`)", "HOLDOUT-DTI 0.1302 · DO NOT SUBMIT (prior CSDU file has 2,610,312 footprint NaNs, IR-CSR-01)"),
    "GEMSDOE32": ("H48 (`gems32-h48-gpse1-38918-20261026-d71058fb7cb6-nan.tif`)", "HOLDOUT-DTI 0.1456 vs H38 0.1497 · DO NOT SUBMIT (flagged ARENA47 perturb-h38-unique, IR-CSR-02)"),
    "GEMSDOE33": ("G33-PGR1 (2026-10-26)", "HOLDOUT-DTI 0.2134 (internal split) · DUPLICATE-STOP 74.4% > 70% · DO NOT SUBMIT"),
    "GEMSDOE36": ("H61 (`GEMSDOE36-h61-edge-hybrid-42499-20261026T192837Z-b5263d1e-nan.tif`)", "HOLDOUT-DTI 0.2191 (internal split), registry incomplete · DO NOT SUBMIT"),
}


def priority_table(fleet: dict) -> str:
    rows = []
    for r in fleet["rows"]:
        site = r["site"]
        latest_name, latest_status = LATEST_SITE_LANES[site]
        aliases = ", ".join(r["exact_value_alias_sites"]) or "Unique among the 9 historical leaders"
        ov = r.get("csr1_fraction_within_3px", 0.0) * 100.0
        rho = r.get("csr1_spearman", 0.0)
        file_cell = f'<a href="{e(r["source_url"])}?raw=true"><code>{e(r["historical_file"])}</code></a>'
        if site == "GEMSDOE30":
            file_cell = (
                f'<strong>New CSR-1:</strong> <a href="executive-summary.html"><code>gems30-CSR1-44090-20261026-502fb5948335-zeros.tif</code></a><br>'
                f'<small>Hist. D2.8: <a href="{e(r["source_url"])}?raw=true"><code>{e(r["historical_file"])}</code></a></small>'
            )
        rows.append(
            f'<tr><th scope="row"><a href="priority-{site}.html">{site}</a><br><small><code>{e(r["public_snapshot_commit"][:10])}</code></small></th>'
            f'<td><strong>{e(r["quoted_owner_claim"])}</strong><br><small>owner-reported, unverified (not a score receipt)</small></td>'
            f'<td>{file_cell}</td>'
            f'<td>{r["dots"]:,}</td>'
            f'<td>{e(aliases)}<br><small>CSR-1 ≤3 px: <strong>{ov:.2f}%</strong> (ρ {rho:+.4f})</small></td>'
            f'<td><code>{e(latest_name)}</code><br><small>{e(latest_status)}</small></td></tr>'
        )
    return (
        '<div class="table-wrap"><table><caption>Nine priority GEMSDOE sites · pinned 2026-10-26 commits · file to download, evidence status, uniqueness &amp; CSR-1 overlap</caption>'
        '<thead><tr><th>Site &amp; commit</th><th>Historical status (unverified)</th><th>File to download (reference / research)</th><th>Dots</th><th>Cross-site uniqueness &amp; CSR-1 overlap</th><th>Latest 2026-10-26 lane &amp; submit verdict</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def lineage() -> str:
    return f'''<section class="section" id="h33"><h2>PhD-level proof: why GEMSDOE32 (<code>H33-B2</code>, 0.2778) scored highest among the nine sites — and how to surpass 0.2778 / 0.3195 / 0.4413–0.4437.</h2>
<p>Reopening all nine historical leader rasters on the exact <code>EPSG:32611</code> grid (<a href="{BASE}fleet-audit.json">fleet-audit.json</a>) proves that the entire progression from <strong>0.1922 → 0.2477 → 0.2600 → 0.2708 → 0.2778</strong> came from <strong>metric-exact denominator pruning under DrivenData’s zero-buffer known-fault mask, not new subsurface geology</strong>:</p>
<ul class="spaced">
<li><strong>Exact subset chain (zero non-subset pixels):</strong> <code>h19-5</code> (<code>121,131</code> corridor px, <code>0.1922</code>) → <code>D1.5</code> (<code>60,069</code> dots, <code>0.2477</code>, <code>GEMSDOE24</code>) → <code>D2.8</code> (<code>44,090</code> dots, <code>0.2600</code>, value-identical across <code>GEMSDOE25</code> &amp; <code>GEMSDOE30</code>) → <code>r1</code> (<code>40,199</code> dots, <code>0.2708</code>, value-identical across <code>GEMSDOE28 r1</code> &amp; <code>GEMSDOE31</code>, deleting the exact <code>3,891</code> dots at <code>d_cat = 1 px</code>) → <strong><code>H33-B2</code> (<code>37,654</code> dots, <code>0.2778</code>, <code>GEMSDOE32</code>, deleting the next <code>2,545</code> dots at <code>d_cat = 2 px</code>)</strong>.</li>
<li><strong>Why deleting <code>6,436</code> near-catalogue dots raised DTI by +0.0178:</strong> Per organizer clarification <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516"><code>t/11516</code></a>, known USGS/INGENIOUS faults <code>K</code> are masked <strong>pixel-exactly at <code>d_cat = 0</code> with zero buffer</strong>. Under <code>DTI = T / (0.2T + 0.2F + 0.8|G_new|)</code> with <code>300 m</code> (<code>3 px</code>) triangular kernel, dots at <code>d_cat ∈ &#123;1, 2&#125; px</code> sit on unmasked background flanks of already-known faults, incurring full false-positive weight <code>0.2 × 6,436 ≈ 1,287</code> denominator units while surviving dots at <code>d_cat = 3 px</code> still extend triangular kernel coverage across <code>d_cat ∈ [1, 2] px</code>. Inverting the linear system across <code>D2.8 → r1 → H33-B2</code> shows truth coverage <code>T ≈ 6,602</code> stayed invariant to 3 significant figures—and adding <code>1,200</code> bridge dots onto <code>H33-B2</code> in <code>GEMSDOE36 PINN</code> (<code>38,854</code> dots) added <code>~237</code> penalty units with negligible new truth, explaining its drop to <code>0.2750</code>.</li>
<li><strong>Why 0.2778 is the pruning ceiling — and how to surpass 0.3195 (Oct 3) and 0.4413–0.4437 (Oct 25–26 #1):</strong> Because missed hidden faults carry <strong>4× the penalty weight of false positives</strong> (<code>β = 0.8</code> vs <code>α = 0.2</code>) and <code>80.9%</code> of <code>H33-B2</code> dots sit on steep range fronts (<code>det_elev_slope ≥ 5°</code>), denominator pruning alone hits an asymptotic ceiling near <code>~0.28–0.31</code>. Reaching <code>0.32–0.44+</code> requires raising hidden-fault recall from <code>~34%</code> to <code>52–60%</code> by fusing: (1) <strong>full-stack piedmont scarp features keeping <code>det_elev</code> intact</strong> (<code>msdb_edge = 0.1700</code> HOLDOUT-DTI), (2) <strong><code>CSR-1</code>’s 3D Laplace/Poisson cover-corrected gravity + 1.8 km Radon stepover expert</strong> gated specifically onto Walker Lane / transtensional shear domains where <code>CSR-1</code> beat <code>msdb_edge</code> by <strong>+0.02300</strong> in Fold 3, (3) a <strong>multi-kilometre 2D UNet / ConvNeXt-UNet</strong> trained directly on smoothed Tversky loss over the 80-channel physics stack, and (4) <strong><code>CSR-1</code>’s <code>&gt; 2 px</code> off-catalogue + <code>≥ 2.83 px</code> 1D-Hessian dispersed <code>EDGE</code> emitter</strong>.</li>
</ul>
<p><a href="{BASE}nine-site-executive-summary.md">Full nine-site Markdown report &amp; mathematical derivation</a> · <a href="{BASE}fleet-audit.json">Reproducible nine-site SHA-256 &amp; overlap receipt</a></p></section>'''


def pages(ready: dict) -> dict[str, str]:
    c = load("run-card.json")
    res = load("results.json")
    fleet = load("fleet-audit.json")

    intro = '''<section class="intro"><div><p class="eyebrow">DOE GEMS / 26 October 2026 / CSR-1 autonomous release</p><h1>OK to download: YES.<br>OK to submit: NO.</h1><p class="lead"><code>CSR-1</code> generated a brand-new, 100% machine-validated single-band <code>float32</code> GeoTIFF in <code>[0, 1]</code> that cleared all 357 aligned nine-site rasters on two-stage novelty and beat <code>msdb_edge</code> by <strong>+0.02300</strong> in Fold 3 (SE Walker Lane), while trailing <code>msdb_edge</code> pooled (<code>−0.01182</code>). Download the research GeoTIFF, keep the receipt, and save your weekly DrivenData slot.</p><div class="meta"><span>OK to download: YES (12/12 format checks)</span><span>OK to submit: NO (slot protected)</span><span>357-raster novelty: PASSED (max 67.70% ≤ 70%)</span><span>Organizer score: none</span></div></div></section>'''
    stats = '''<div class="evidence-strip"><article><span>CSR-1 HOLDOUT-DTI</span><strong>0.15816</strong><small>95% CI [0.14499, 0.17147]; +0.01325 vs core19_edge; 60,988 positives</small></article><article><span>Fold 3 (SE Walker Lane)</span><strong>0.19686</strong><small>+0.02300 over msdb_edge (0.17386) &amp; +0.03567 over core19_edge</small></article><article><span>357-raster 3-px novelty</span><strong>59.86% vs MSDB1</strong><small>67.70% max overall (≤70% gate PASSED); 36.1–40.6% vs 9 site leaders</small></article></div>'''
    home = frame(
        "CSR-1 decision: OK to download, do not submit",
        intro
        + release(c)
        + stats
        + holdout(c, res)
        + novelty_and_gates(c, ready)
        + '''<section class="section"><h2>Nine priority sites &amp; PhD H33 (0.2778) proof.</h2><p>All nine priority repositories (<code>GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36</code>) were audited at their latest 26 October 2026 commits for highest-claimed files, value-hash aliases, 2026-10-26 lane statuses, irregularities (<code>IR-CSR-01..05</code>), and exact overlap with <code>CSR-1</code>.</p><div class="actions"><a class="button secondary" href="priority-executive-summary.html">Open nine-site summary table &amp; H33 0.2778 proof</a><a class="button secondary" href="csr-discontinuity-review.html">Read CSR-1 hypotheses, equations &amp; CSR-2 plan</a></div></section>'''
        + archive_note()
        + sources(),
        "Overview",
    )

    guide_intro = '''<section class="intro"><div><p class="eyebrow">Executive submission guide · zero human inspection</p><h1>OK to download: YES.<br>Do not upload to DrivenData.</h1><p class="lead">Every format, coordinate, <code>[0, 1]</code> finite-value, canary, and 357-raster novelty check ran automatically with zero human intervention. <code>CSR-1</code> is format-ready and novel, so it is <strong>safe to download for research inspection</strong>, but its pooled holdout delta against <code>msdb_edge</code> is negative (<code>−0.01182</code>), so it is <strong>NOT approved to spend one of the 3 weekly DrivenData submission slots</strong>.</p></div></section>'''
    fields = f'''<section class="section" id="identity"><h2>Copy-ready unique artifact identity &amp; ≤140-character note.</h2><p>Unique run identifier and <code>{len(c['note'])}/140</code>-character note bound to <code>SHA-256: {e(c['raster_sha256'][:24])}…</code>. Copying these fields does not override <code>ok_to_submit = false</code>.</p><div class="identity"><label for="submission-name">Unique submission / artifact name</label><input id="submission-name" readonly value="{e(c['submission_name'], quote=True)}"><button class="copy-button" type="button" data-copy="submission-name">Copy name</button><label for="submission-note">Portal note ({len(c['note'])} / 140 characters)</label><textarea id="submission-note" rows="2" readonly>{e(c['note'])}</textarea><button class="copy-button" type="button" data-copy="submission-note">Copy note</button><p id="copy-status" role="status" aria-live="polite"></p></div></section>'''
    instructions = f'''<section class="section" id="instructions"><h2>Exact step-by-step contest submission procedure (when a candidate earns <code>promote</code>).</h2><ol class="steps"><li><strong>Step 1 — Check automated promotion gate at the top of this page (zero human inspection).</strong><p>Run <code>.venv/bin/python scripts/verify_csr_run.py</code> (exits <code>0</code> today, confirming valid negative research receipt) and <code>.venv/bin/python scripts/verify_csr_run.py --require-promote</code> (exits <code>2</code> today because <code>verdict = negative</code>). <strong>Stop here for CSR-1 — do not spend a weekly slot.</strong> Only proceed to Step 2 when a future run (such as <code>CSR-2</code>) achieves paired 95% CI lower bound &gt; 0 over <code>msdb_edge</code> and <code>--require-promote</code> exits <code>0</code>.</p></li><li><strong>Step 2 — Verify weekly DrivenData slot budget &amp; closing-time rule.</strong><p>Per <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">DOE / NLR Official Rules PDF (96647.pdf)</a>, teams are capped at <strong>3 feedback submissions per rolling 7-day window</strong> and must designate <strong>1 final submission</strong> before close (conservatively <code>5:00 p.m. ET / 22:00 UTC</code> per Rules PDF App. A.1 vs <code>11:59 p.m. UTC</code> on DrivenData overview) for both Phase 1 ($50k) and Phase 2 ($250k).</p></li><li><strong>Step 3 — Download the validated single-band <code>.tif</code> &amp; confirm <code>[0, 1]</code> finite-range immunity.</strong><p>Download the single-band <code>float32</code> GeoTIFF above (never upload multi-band stacks, PNGs, or JSON sidecars). <code>CSR-1</code> writes finite values in <code>[0.0, 1.0]</code> across <strong>all 12,279,160 cells</strong> (<code>5,167,373</code> footprint cells + <code>0.0</code> outside, <code>0</code> NaNs anywhere) and re-verifies <code>python scripts/validate_submission.py ... --finite-all-cells</code> so the portal error <code>"Predicted values must be in range [0, 1]"</code> (triggered historically by <code>-3.4028235e+38</code> feature nodata sentinels or unmasked NaNs) cannot occur.</p></li><li><strong>Step 4 — Upload on DrivenData “Submit” with exact traceable metadata.</strong><p>For a promoted candidate only: open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData DOE GEMS</a> → <strong>Submit</strong>, select the <code>.tif</code> file, paste the exact ≤140-character note from the box above, and submit once (never upload perturbed or renamed copies).</p></li><li><strong>Step 5 — Record the official receipt triple before citing any score.</strong><p>Log the portal submission timestamp/ID, exact <code>raster_sha256</code>, and returned DTI score in <code>docs/score-ledger.csv</code> before labelling any number <code>ORGANIZER-CONFIRMED</code>.</p></li></ol></section>'''
    guide = frame(
        "Executive submission guide · OK to download, do not submit",
        guide_intro + release(c) + fields + instructions + holdout(c, res) + archive_note() + sources(),
        "Submission guide",
    )

    hypotheses = f'''<section class="section" id="hypotheses"><h2>Four untried geological hypotheses, frozen before fitting.</h2><div class="table-wrap"><table><caption>Preregistered in <a href="{BASE}preregistration.md">preregistration.md</a> (SHA-256 <code>28383a271211…</code>) prior to <code>started.json</code></caption><thead><tr><th>Rank &amp; ID</th><th>Exact layers &amp; physical transform</th><th>Why it catches uncatalogued / blind faults</th><th>Primary non-fault mimic &amp; outcome</th></tr></thead><tbody><tr><th scope="row">1 · <code>CSR-1</code></th><td>3D Laplace SVD <code>−∇_H·∇_H g</code> + planar Poisson <code>∂g/∂z</code>, <code>1000× tmi_vg</code> 3D tilt/analytic signal, inverse cover gain <code>G_cover(z)=clip(1+z/300m,1,6)</code>, <code>|∇_H log(z+100m)|</code>, 12-azimuth × 1.8 km flank-subtracted Radon, dual-expert Noisy-OR (33+56 ch), <code>≥2.83 px</code> 1D-Hessian EDGE</td><td>Recovers concealed intrabasin horst/graben steps and Walker Lane transtensional stepovers beneath 200–2,000 m of Quaternary playafill</td><td>Pluton/caldera margins, paleochannels, playa pans &amp; Lahontan shorelines. <strong>Executed:</strong> <code>0.15816</code> pooled; <strong>+0.02300 over msdb_edge in Fold 3</strong>; 357-raster novelty PASSED (<code>67.70% ≤ 70%</code>).</td></tr><tr><th scope="row">2 · <code>KRA-1</code></th><td>Kinematic Conjugate Riedel &amp; Walker Lane Sinistral-Dextral Accommodation Tensor Alignment (<code>geod_shearrate</code>, <code>geod_dilaterate</code>, <code>geod_2ndinv</code>, gravity/LiDAR strike)</td><td>Highlights ENE sinistral-oblique accommodation faults &amp; Walker Lane relays with low vertical scarp relief</td><td>Pre-Cenozoic metamorphic foliation. Next-session spatial regime gate for <code>CSR-2</code>.</td></tr><tr><th scope="row">3 · <code>MCD-1</code></th><td>MT Smectite Clay-Cap Demagnetization (<code>−rtp_hp × |∇_H cond_surf|</code>) + Epithermal <code>K/Th</code> &amp; Paleogeothermal Sinter Saddle</td><td>Separates blind hydrothermal fault conduits (&gt;75% lack surface scarps) from cold unaltered volcanics</td><td>Saline evaporite playas. Core demagnetization×clay-cap term evaluated in <code>csr_demag_claycap_index</code>; sinter saddle deferred.</td></tr><tr><th scope="row">4 · <code>SLD-1</code></th><td>USGS SGMC Lithologic Unit-Contact (<code>Qa / Tv / Mz</code>) Sub-Alluvial Projection Discordance (<code>NV.zip</code>, <code>CA.zip</code>)</td><td>Detects concealed offsets truncating projected bedrock unit contacts beneath valley alluvium</td><td>Erosional buttress unconformities. Obtainability verified (requires future workflow rasterization of <code>SGMC_Geology</code>).</td></tr></tbody></table></div></section>'''
    irregularities = f'''<section class="section" id="irregularities"><h2>Irregularities caught &amp; next-session <code>CSR-2</code> blueprint.</h2><ul class="spaced"><li><strong><code>IR-CSR-01</code> (Malformed <code>GEMSDOE31</code> raster):</strong> <code>gems31-csdu-hgb-oof-38000-20261026-ab0230015224-nan.tif</code> (<code>774c7c5aa…</code>) has <code>2,610,312</code> non-finite cells inside the scoring footprint; formally classified by <code>sync_priority_registry.py</code> and finite-subset audited (<code>1.45%</code> overlap).</li><li><strong><code>IR-CSR-02</code> (<code>GEMSDOE32</code> perturbation record):</strong> <code>ARENA47 perturb-h38-unique</code> perturbed an existing raster; flagged and excluded from valid physical strategies.</li><li><strong><code>IR-CSR-03</code> (<code>13GEMSDOE</code> 5-px lattice):</strong> <code>206,895</code>-dot calibration grid covers <code>99.87%</code> of the footprint within 3 px mathematically.</li><li><strong><code>IR-CSR-04</code> (<code>GEMSDOE24</code> oracle leak audit):</strong> <code>IRR-GAPFILL-ORACLE-LEAK</code> documented in <code>GEMSDOE24</code>; <code>CSR-1</code> uses zero catalogue features (<code>324/324</code> canaries <code>≤ 0.6629</code>).</li><li><strong><code>IR-CSR-05</code> (<code>1000× tmi_vg</code> &amp; 3D <code>∂g/∂z</code> physics fix):</strong> Fixed <code>msdb.py</code>’s unscaled <code>nT/m</code> vs <code>nT/km</code> magnetic tilt compression and horizontal-slope gravity tilt substitution in <code>src/gemsdoe30/csr_discontinuity.py</code>.</li><li><strong>Next session (<code>CSR-2</code>):</strong> Restore <code>det_elev</code> (<code>band 11</code>) to Expert 2 to recover Folds 0–2 classic Basin-and-Range piedmont precision (<code>0.170+</code>), and spatially gate Expert 1’s 3D Laplace/Poisson + 1.8 km Radon stepover surface by transtensional geodetic shear (<code>H-CSR-2</code>) so Fold 3’s <strong>+0.02300</strong> Walker Lane gain stacks additively onto <code>msdb_edge</code>.</li></ul><p><a href="{BASE}review.md">Full CSR-1 Markdown review</a> · <a href="{BASE}three-pass-review.md">Three-pass cumulative verification journal</a></p></section>'''
    science = frame(
        "CSR-1 PhD scientific review",
        '''<section class="intro"><div><p class="eyebrow">CSR-1 · 3D Laplace/Poisson + 1.8 km Radon + dispersed EDGE</p><h1>Walker Lane +0.0230.<br>59.86% dot uniqueness.</h1><p class="lead">By deriving true 3D wavenumber vertical gravity derivatives, stripping conductive-basin drape, integrating 1.8 km Radon stepovers, and enforcing 2.83 px 1D-Hessian ridge spacing, <code>CSR-1</code> solved <code>FFL-1</code>’s 78.28% range-front collision and surged past <code>msdb_edge</code> in SE Walker Lane—while revealing why classic horst/graben folds still require <code>det_elev</code>.</p></div></section>'''
        + release(c)
        + hypotheses
        + holdout(c, res)
        + novelty_and_gates(c, ready)
        + irregularities
        + sources(),
        "CSR-1 science",
    )

    fleet_intro = '''<section class="intro"><div><p class="eyebrow">Read-only nine-repository executive audit · 26 October 2026</p><h1>Nine priority sites.<br>Every file &amp; score audited.</h1><p class="lead">Every repository in <code>GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36</code> was audited at its pinned 26 October 2026 commit for highest-claimed historical rasters, latest 2026-10-26 research lanes, exact footprint value aliases, and uniqueness against <code>CSR-1</code>. Historical numbers are owner-reported and unverified (not a competition receipt or forecast); every site’s latest 2026-10-26 lane is currently <strong>DO NOT SUBMIT</strong>.</p></div></section>'''
    fleet_page = frame(
        "Nine-site executive summary & H33 0.2778 proof",
        fleet_intro + priority_table(fleet) + lineage() + sources(),
        "Nine-site review",
    )

    result = {
        "index.html": home,
        "executive-summary.html": guide,
        "csr-discontinuity-review.html": science,
        "priority-executive-summary.html": fleet_page,
    }

    notes = {
        "GEMSDOE24": "Historical 60,069-dot D1.5 thinning of h19-5 (0.2477 owner-reported, unverified). Latest 2026-10-26 lane G24-CSB scored HOLDOUT-DTI 0.1059 vs core19 0.1656 (DO NOT SUBMIT) and flagged IRR-GAPFILL-ORACLE-LEAK.",
        "GEMSDOE25": "Historical 44,090-dot D2.8 raster is 100% value-identical inside the footprint to GEMSDOE30 D2.8 (0.2600 owner-reported, unverified; GEMSDOE25 page marks it unscored). Latest G25-BGH scored HOLDOUT-DTI 0.0566 vs core19 0.1322 (DO NOT SUBMIT).",
        "GEMSDOE27": "Historical 61,328-dot gap-closure raster on D1.5 (0.2449 owner-reported, unverified). Latest 2026-10-26 lane G27-RGS scored HOLDOUT-DTI 0.0884 vs core19 0.1398 (DO NOT SUBMIT), superseding an earlier 27-reference projection.",
        "GEMSDOE28": "Historical 37,660-dot SGER-R2 raster (0.2710 owner-reported, unverified) and 40,199-dot r1 intermediate (0.2708, value-identical to GEMSDOE31). Latest H38 scored HOLDOUT-DTI 0.0897 vs 0.1552 baseline (DO NOT SUBMIT).",
        "GEMSDOE30": "This repository. New CSR-1 (44,090 dots, all-finite [0,1]) passed 12/12 format checks and 357-raster two-stage novelty (OK TO DOWNLOAD: YES) and beat msdb_edge by +0.02300 in Fold 3, but trailed msdb_edge pooled (−0.01182 → OK TO SUBMIT: NO). Historical D2.8 equals GEMSDOE25.",
        "GEMSDOE31": "Historical 40,199-dot raster matches GEMSDOE28 r1 inside the footprint (0.2708 owner-reported, unverified). Latest CSDU-2 scored HOLDOUT-DTI 0.1302 (DO NOT SUBMIT); earlier CSDU file 774c7c5aa… has 2,610,312 in-footprint NaNs (IR-CSR-01).",
        "GEMSDOE32": "H33-B2 (37,654 dots; 0.2778 owner-reported, unverified — highest among the 9 sites) equals the exact d_cat > 2 px subset of r1. Latest H48 scored HOLDOUT-DTI 0.1456 vs H38 0.1497 (DO NOT SUBMIT); ARENA47 perturbation flagged (IR-CSR-02).",
        "GEMSDOE33": "Historical H36-1 SGER-H33d contains 41,865 dots (0.2632 owner-reported, unverified). Latest G33-PGR1 was halted by a 74.4% > 70% dot-overlap duplicate-stop (DO NOT SUBMIT).",
        "GEMSDOE36": "Historical Anderson-Geothermal-PINN contains H33-B2 plus exactly 1,200 near-catalogue dots (38,854 dots; 0.2750 owner-reported, unverified). Latest H61 remains blocked on incomplete cross-site registry coverage (DO NOT SUBMIT).",
    }
    for r in fleet["rows"]:
        site = r["site"]
        latest_name, latest_status = LATEST_SITE_LANES[site]
        aliases = ", ".join(r["exact_value_alias_sites"]) or "No exact value alias among the nine historical leaders"
        ov = r.get("csr1_fraction_within_3px", 0.0) * 100.0
        rho = r.get("csr1_spearman", 0.0)
        format_text = (
            "Passes shared local NaN-outside format checks"
            if r["format_validation_passed"]
            else "All-finite zero-outside historical encoding (in-footprint values finite in [0, 1])"
        )
        body = f'''<section class="intro"><div><p class="eyebrow">Pinned public snapshot · {e(r['public_snapshot_commit'][:12])}</p><h1>{site}<br>Executive review.</h1><p class="lead">{e(notes[site])}</p></div></section><section class="release"><div class="release-heading"><span class="pill failed">DO NOT RESUBMIT HISTORICAL BYTES</span><span class="pill unknown">Owner-reported claim unverified</span></div><h2>Historical reference &amp; 2026-10-26 lane status.</h2><p>Quoted historical owner claim: <strong>{e(r['quoted_owner_claim'])}</strong> (unverified — not a portal receipt, not HOLDOUT-DTI, not ORGANIZER-CONFIRMED, and not a leaderboard forecast). Latest 2026-10-26 lane: <code>{e(latest_name)}</code> → <strong>{e(latest_status)}</strong>.</p><p class="filename">{e(r['historical_file'])}</p><dl><dt>Historical Raster SHA-256</dt><dd><code>{e(r['raster_sha256'])}</code> (dots: <code>{r['dots']:,}</code>)</dd><dt>Value aliases</dt><dd>{e(aliases)}</dd><dt>Uniqueness vs new GEMSDOE30 CSR-1</dt><dd><strong>{ov:.2f}%</strong> of CSR-1 dots within 3 px (<code>≤ 70%</code> gate); full-footprint Spearman <code>{rho:+.4f}</code></dd><dt>Local format convention</dt><dd>{format_text}</dd><dt>OK to submit?</dt><dd><strong>No — not approved for portal upload.</strong> Resubmitting published historical rasters wastes weekly slots and violates uniqueness rules.</dd></dl><div class="actions"><a class="button secondary" href="{e(r['source_url'])}?raw=true">Inspect historical reference TIFF</a><a class="button secondary" href="priority-executive-summary.html#h33">Back to 9-site table &amp; H33 0.2778 proof</a><a class="text-link" href="{e(r['site_url'])}">Open original {site} site ↗</a></div></section><section class="section"><h2>New validated research download in GEMSDOE30.</h2><p>See <a href="executive-summary.html">Executive submission guide (CSR-1)</a> for today’s newly generated, all-finite <code>[0, 1]</code> GeoTIFF (<strong>OK to download: YES · OK to submit: NO</strong>) and <a href="{BASE}fleet-audit.json">fleet-audit.json</a> for exact SHA-256 lineage proofs.</p></section>'''
        result[f"priority-{site}.html"] = frame(f"{site} executive review", body, "Nine-site review")
    return result
