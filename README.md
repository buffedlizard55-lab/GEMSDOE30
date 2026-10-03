# GEMSDOE30 — DOE GEMS fault-discovery research

> **Complete persistent project brief — read the literal owner brief in the section *Read first — owner brief (verbatim)* and this section before every project session.** These are the standing scope, scientific, operational, and integrity requirements from the project request—not a session-status summary. Preserve every acceptance criterion when changing this brief. Keep `docs/score-ledger.csv`, `docs/irregularities.md`, and the linked official sources in sync when updating claims.

## Read first — owner brief (verbatim)

<details>
<summary><b>Literal owner brief (click to expand; re-read at the start of every session)</b></summary>

> **Objective and standing request.** Review the repo. There should be an easy to download
> submission tif file as described by the prompt. Read the entire prompt.
>
> **Metric-shaped loss.** Train against a loss shaped like the metric's own geometry. The
> competition scores within a 300 m kernel, not by exact pixel overlap — but plain cross-entropy
> or Dice optimizes for exact overlap, a different target than what's actually being rewarded.
> Kervadec, Bouchtiba, Desrosiers, Granger, Dolz, and Ben Ayed's boundary loss (2018) was built
> for precisely this kind of mismatch on other severely unbalanced segmentation problems:
> instead of summing over regions — which the paper shows produces loss contributions differing
> by orders of magnitude between a rare positive class and the dominant background — it computes
> a distance metric over contours, rewarding proximity to the true boundary, and the paper reports
> measurable gains in both accuracy and training stability under exactly this kind of imbalance.
> Implement a version using a distance transform built on the actual 300 m kernel radius, combine
> it with the existing regional loss rather than replacing it (as the original paper recommends),
> and check on holdout that it changes which near-misses the model is willing to make — it should
> start rewarding a prediction that lands close to, not exactly on, a held-out fault, since that's
> the credit the real metric already gives.
>
> **Highest-score study (the core question).** WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE
> HIGHEST SCORE FROM THE GEMSDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS
> `https://buffedlizard55-lab.github.io/GEMSDOE25/` — `dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600`.
> Why and how did this get the highest score and are we able to generate a submission that scores
> higher than 0.26? Answer using PhD-level experience, knowledge and judgement. The leaderboard is
> `https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/`.
> **0.3195 is the highest score right now**, so design a new strategy, research, testing, analysis
> and submission system that is unique and can score higher than 0.3195.
>
> **Hypotheses before implementation.** Generate 3–5 candidate geological hypotheses we haven't
> tried yet, each naming: the specific layer(s) involved, the physical signature being targeted
> (e.g. an edge-detection or curvature transform), why it should catch a fault missing from the
> USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already
> implemented in this repo. Rank them by expected DTI improvement and implementation cost.
> Validate the top candidate on our spatially-blocked holdout set before touching a weekly
> submission slot — do not spend a submission slot on an idea that hasn't beaten the current
> holdout best. If a candidate can't be validated without new external data, name the specific
> free, official source needed and check it's obtainable before proposing the idea as viable.
>
> **Integrity and verification.** Work line by line verifying from official verified trusted
> sources, provide links for manual review. There should be no manual input, work on your own to
> complete tasks. Flag any irregularities for review. No hallucinations. Verify no hallucinations.
> The goal of this project is to get a full list that follows our requirements.
>
> **Deep research.** We need to start doing heavy and deep research into the part of the project
> that matters most: the scientific discovery of geothermal vents. Store all information and
> knowledge gathered from official verified sources. Think outside the box but stay grounded in
> proper scientific research; we are aiming for a top prize that many others compete for, so it is
> important to be contrarian but smart. Find data sources others overlook. Do deep research and
> critical thinking and come up with new hypotheses to test.
>
> **Site and submission.** The site should be able to generate a TIF file required for submission:
> as easy as clicking a file to submit into the competition. This must be obvious at the very
> beginning of the site / in the executive summary. *(A previous attempt returned the portal error
> "Predicted values must be in range [0, 1]".)* Give it a unique name and a short comment to help
> tell submissions apart (e.g. "clustering with k=25"). Create an executive-summary subpage that
> explains exactly how to make a submission. Include a clean, user-friendly, simple GitHub Pages
> site with all relevant information in an easy-to-read format with official verified links, kept
> up to date automatically instead of by manual checking.
>
> **Competition facts to respect.** Overview and problem description
> `https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/`; about page
> `page/968`; data tab `/data/`; rules PDF `https://docs.nlr.gov/docs/fy26osti/96647.pdf`;
> reference solution `https://github.com/drivendataorg/gems-prize-reference-solution`; GDR 1391
> `https://gdr.openei.org/submissions/1391`.
>
> **Reported submission history supplied by the owner** (all owner/user-reported and unverified;
> retained in `docs/score-ledger.csv`): GEMSDOE `gems-submission-20260925T001403Z-7f00890a` 0.1563;
> 6GEMSDOE `gems6_hgb88-topk03_33cec71ff0` 0.0286; GEMSDOE3 `pindrop-v4-nodes-20260925T152420Z-f347b70daa`
> 0.1193, `pindrop-v4-discovery-20260925T152423Z-37f9d5b855` 0.0830, `pindrop-v4-ridge-20260925T152422Z-4e03fc9705`
> 0.1152; GEMSDOE2 `gemsdoe2-dual-family-union-20260925T160406Z-f68e590f` 0.1560; GEMSDOE4
> `gems-submission-20260926T163915Z-237f0063` 0.0343; 5GEMSDOE `gems-submission-20260926T175114Z-7f00890a`
> 0.1563; 7GEMSDOE `lidarscarp-ridge-top2pct-36c3a3f341c8` 0.1461; 8GEMSDOE `Hedge-v2_submission` 0.1563;
> GEMSDOE9 `2314b599` 0.0107; 11GEMSDOE `gems-structural-area06-v1` 0.0202; 12GEMSDOE
> `r7-nms3-dem10-scarp_0c9199f14e62` 0.1294 (and `_allfinite` 0.1294); 15GEMSDOE
> `gems-tso1-20260929T005627Z-conj_alteration_mag` 0.0782; 14GEMSDOE
> `GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f` 0.0020; 17GEMSDOE
> `17GEMSDOE_F-ensemble-2pct_20260930T050626Z` 0.0187; 18GEMSDOE `H19-C_20260930T212401Z_c11e495e` 0.0297;
> 19GEMSDOE `h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan` 0.1894,
> `h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan` 0.1922; GEMSDOE10
> `h16-continuation-20260927T065521077735Z-3431b83c7c` 0.0461, `h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686` 0.0921,
> `H25-ctx-ridge-20260927T232947704150Z-6452ae1d00` 0.1280, `h28-dotted-ridge-20260928T020256236880Z-6452ae1d00` 0.1839;
> 13GEMSDOE `20261001_r13-lattice-s5_v2_nan-outside` 0.0904; 16GEMSDOE
> `h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan` 0.1855, `h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan` 0.0976,
> `h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan` 0.0360; GEMSDOE21 `h19-4-reference-20260930-691e4dfa` 0.1894;
> 20GEMSDOE `h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan` 0.1890,
> `h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan` 0.1859; GEMSDOE22
> `h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan` 0.1002, `h23-b-dti-optimal-emission-10pct-20261002-86176698-nan` 0.0748;
> GEMSDOE23 `h30-arrangement-matched-habitat-20261002-0d4e02e8-nan` 0.1352; GEMSDOE24
> `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` 0.2477; GEMSDOE25
> `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` 0.2600; GEMSDOE26
> `dilcond-oof-v1-20261003-47629f496133-nan` 0.1223; GEMSDOE27
> `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` 0.2449; 28–33GEMSDOE scores not yet supplied.
>
> **Core values.** *Maximize P(Win)* — weigh tradeoffs, assess risk, choose the path that
> maximizes the probability of winning. *Own the Outcome* — own results end to end, act without
> waiting for permission, treat failure and success as signals. Work in three cumulative passes:
> implement and verify; review for bugs, missing requirements and edge cases; re-check the whole
> implementation against the original request and fix what remains. Then open a pull request from
> `arena/01a10289-gemsdoe30` and merge it to `main`, and state what work remains and what limits it.

The distilled, non-negotiable acceptance criteria that follow from this brief are in
**Mission and non-negotiable requirements** below; if the two ever disagree, the literal brief above
wins and the distilled list must be corrected.

</details>

> **Branch note:** the brief above names the branch of the session in which it
> was first recorded (`arena/01a10289-gemsdoe30`). Each Arena session is assigned
> its own branch; work for the current session happens on `arena/01a10315-gemsdoe30`
> (previous sessions: `arena/01a102bf-gemsdoe30`, `arena/01a10311-gemsdoe30`),
> and pull requests are opened from whichever branch the session is assigned.
> The brief's verbatim wording is preserved above unchanged.

## Mission and non-negotiable requirements

1. **Objective and historical review:** build an auditable, scientifically grounded workflow to identify previously unmapped geological faults in the DOE GEMS / GeoDAWN region and pursue a result above the user-reported 0.3195 public-leader score. Study the reported GEMSDOE25 D2.8 result and historical submissions; authenticate score-to-file attribution using a submission receipt, ID, hash, or equivalent evidence rather than assuming a score belongs to a named TIFF. Treat public leaderboard snapshots as dynamic feedback, not the private test set or the final award decision. Develop a defensible path to improvement, but never promise a score or prize.
2. **Metric-aware learning:** the official public metric is a distance-weighted Tversky index with a triangular 300 m support kernel on 100 m pixels, `alpha=0.2`, `beta=0.8`. Prefer training objectives that represent this geometry. Pair any distance/boundary term with a regional loss; compare them under a spatially blocked holdout and report how their near-miss behavior changes. A synthetic unit probe is not a real holdout result.
3. **Submission first:** when a scientifically promoted candidate exists, make a single-band float32 GeoTIFF with probabilities in `[0,1]`, on the exact sample-template CRS, shape, bounds, and transform; put null/NaN only outside the valid footprint. Check for NaN/Inf *inside* the footprint, which can trigger the portal's “Predicted values must be in range [0, 1]” error. Make the download and the submission instructions obvious at the top of the site. Give every run a unique filename and a short paste-ready submission note.
4. **No slot without evidence:** pre-register 3–5 genuinely distinct geological hypotheses. Each must state the exact layers, physical signature, why it could indicate a fault absent from USGS/INGENIOUS, what makes it different from prior work, likely DTI change and cost, official data source/license/access status, and a falsifiable holdout gate. Validate the leading candidate against the current spatial-holdout best, with confirmation, before spending a weekly submission slot. No holdout pass means no slot. Beyond the private holdout, require **three types of verification**, each with a pre-stated promotion criterion — spatial block-validation, probability calibration, and feature-perturbation stability — plus a qualitative note showing where a learned change helps and where it fails; the standing protocol is [docs/research/verification-protocol.md](docs/research/verification-protocol.md).
5. **Research and provenance:** use free, publicly accessible, official or otherwise authoritative data where allowed. Verify claims against the relevant official/primary source line by line where possible; store exact citations/URLs, access and licensing checks, source hashes, experiment protocols, results, and irregularities. Distinguish official facts from user-supplied claims, owner-mirror evidence, hypotheses, and model estimates. Record unavailable files, failed downloads, and other blockers. Never invent a score, source, file hash, access result, or holdout result.
6. **Competition integrity:** respect the rules and source terms. Do not bypass the DrivenData login, collect or store account credentials, submit files, or consume competition slots on the user's behalf. Public leaderboard values are time-stamped snapshots; do not build a robot/spider that monitors DrivenData.
7. **Autonomous execution and accountability:** complete what can be done without asking for manual input; identify hard blockers rather than disguising them. Review work in three cumulative passes: implement and verify; inspect bugs/edge cases; re-check against this brief and fix. Flag every unresolved irregularity.
8. **Core values:** **Maximize P(Win)** by choosing evidence-driven work with a plausible path to generalization, not by chasing attractive but unverified claims. **Own the Outcome** end-to-end: record failures, fix defects, keep the user-facing path usable, and state what remains blocked.
9. **Project governance:** use this repository as the research and submission-tooling home. Keep private/large competition data and generated rasters out of Git. The final competition entry must satisfy all eligibility, documentation, AI-disclosure, and submission rules; confirm current requirements with the organizer when ambiguous.
10. **Delivery:** complete the requested code, documentation, and user-facing site work autonomously where possible. When asked, open a pull request from the assigned project branch and merge it to `main` if GitHub permissions and repository policy allow; report any failure and never claim a PR or merge that did not occur.

## Latest session outcome — supersedes older blocked-status paragraphs below

Read the standing brief above every session. On 2026-10-03 we autonomously restored SHA-256-pinned **owner mirrors** via GitHub API and prepared the real 3730×3292 grid (5,167,373 valid pixels, 60,988 catalogue positives). This resolves local data placement, **not organizer authenticity**. `python scripts/restore_public_mirrors.py` reproduces restoration; immutable pins are in `docs/research/mirror-pins.json`. The mirrored template contains labels: footprint only, never use its values as model features/predictions.

A preregistered four-arm CPU pilot ran all four 800 m-buffered spatial folds. See [protocol](docs/research/pilot-preregistration.md), [complete results](docs/research/pilot-results.json), [data audit](docs/research/data-audit.json). The top runnable strain/conductance interaction **failed its screen** against the same-run context control. No model candidate promoted; no competition slot used. This limited pointwise pilot is not a full-capacity U-Net or a comparison against the archived best.

The D2.8 historical research TIFF is now a **local one-click download** on the site, independently format-checked against the mirrored template. It remains score-attribution-unverified and not slot-approved. 44 tests pass on this image (torch 2.14.1 and scipy 1.17.1 installed). Previous status text below describes the baseline, not today's restored state.

Later on 2026-10-03 the metric-aware emission line was exercised end to end: `src/gemsdoe30/emission.py` gained a masked-domain scorer fix and a count-matched candidate pool, `tests/test_emission.py` (19 tests) passes, and `scripts/emission_holdout.py` ran three count-matched arms on the four 300 m-buffered quadrants. **All three arms failed their registered gate** (adaptive minus uniform pooled ΔDTI +0.0008 to +0.0016, positive in only 1–2 of 4 folds): uniform Poisson-disk thinning stays the default, no candidate promoted, no slot used. Suite now collects 44 tests; 39 pass on this image and 5 torch-gated tests skip. Numbers: [emission-holdout-results.json](docs/research/emission-holdout-results.json). The owner-artifact audit in [artifact-structure.json](docs/research/artifact-structure.json) also records that catalogue-proxy DTI ordering is *inverted* relative to the owner-reported leaderboard ordering, consistent with the official rule that the Initial Prize Round scores only the private set of new expert-labelled faults.

Later still on 2026-10-03 three more real-data experiments completed. **(1) Paired regional-vs-boundary
loss ablation** — four 300 m-buffered spatial quadrants, identical recipes except the loss, screen
budget (2 × 20 steps, seed 30): pooled exact full-grid OOF DTI **0.062042 → 0.063990** (Δ **+0.001948**,
+3.14 % relative), 3/4 folds positive, fold 3 regressing −0.0009; the number of catalogue-truth pixels
left on partial-distance credit halved (80 → 40). **Confirmed only in part.** The fresh-seed confirmation (seed 31, identical protocol) reproduced the
behavioural effect — partial-distance truth coverage fell 1,889 → 724 — but **not** the DTI gain:
pooled ΔDTI **+0.000115** with only **2/4** folds positive (folds 0 and 3 flip sign versus the screen),
against the required 3/4. Verdict: **the boundary term changes near-miss allocation as designed but
does not reliably raise the proxy DTI at this budget; not promoted, no candidate file, no slot.**
Evidence: [loss-ablation-holdout.md](docs/research/loss-ablation-holdout.md),
[loss-ablation-holdout.json](docs/research/loss-ablation-holdout.json),
[seed-31 confirmation](docs/research/loss-ablation-holdout-seed31.json). **(2) Preregistered
metric-algebra emission holdout** — the registered gate **failed**: pooled cross-validated proxy DTI
`uniform` 0.18675, `adaptive` 0.18927, `dense` 0.13455, `metric` (greedy marginal rule) 0.13313; the
metric rule needed ≥ +0.005 versus both dense and uniform and came out −0.0014 and −0.0536, below
uniform in every fold, and adaptive's +0.0025 edge over uniform is under the threshold. No emission
family promoted. Mechanism: the greedy rule hit its candidate-pool cap (exactly 120,000 px per fold)
at 0.033–0.043 credit/px while uniform thinning emitted 3–6× fewer pixels at 2.4–4.7× the credit —
"thin, don't flood" again, matching the owner's sparse dotted masks. Evidence:
[metric-emission-holdout-results.md](docs/research/metric-emission-holdout-results.md) +
[metric-emission-holdout-results.json](docs/research/metric-emission-holdout-results.json).
**(3) H-31-01 relay-connector component holdout** — the connector geometry earned only **+1.2 %**
credit per emitted pixel over a proximity-matched control and fell below the unrestricted near-known
annulus, so the hypothesis is **not promoted as tested**; the dominant effect is the generic proximity
prior (~2.3× far-field). Evidence:
[relay-connector-holdout.json](docs/research/relay-connector-holdout.json). No GEMSDOE30 submission
TIFF exists, no slot has been used, and **no score is claimed** for any of this work.

### Session 2 (later on 2026-10-03) — portal-safe fix, vent research base, H-32 register, H-32-01 gate

1. **The portal "[0, 1]" rejection is root-caused and fixed.** Measured: the official sample template
   itself encodes **7,111,787 NaN cells outside the footprint** and both published downloads matched
   that mask exactly — so a NaN-unaware elementwise range check fails any template-conformant file.
   The GEMSDOE25 page independently reached the same inference and ships a zeros-outside fallback
   (byte-verified). This site now publishes **portal-safe `-zeros.tif` variants as the primary
   downloads** (finite 0.0 outside; `nodata=None`; in-footprint bytes identical to the NaN copies;
   all 12 strict checks pass including `portal_range_all_pixels` over 12,279,160 cells). New tooling:
   `scripts/make_portal_safe.py`, `write_submission_file(outside_value=0.0)`,
   `convert_to_portal_safe`, `validate_submission.py --portal-safe`, `tests/test_portal_safe.py`.
   **Upload the `-zeros.tif` file.**
2. **Verified knowledge base** (`docs/research/geothermal-vents-knowledge.md`): the official rules
   PDF was read line-by-line — training labels = INGENIOUS Great Basin compilation (DOI
   10.15121/1881483); **test labels = expert-new faults** (NLR/USGS, Qfaults + new); metric penalizes
   FN > FP; 3 submissions/week, one final entry across both prize rounds; **Phase 1 $50k split equally
   among top 5 on the private subset; Phase 2 $250k on the expert-revised label set**; finalists must
   ship reproducible code; AI use must be disclosed; eligibility is U.S.-only with certification under
   penalty of perjury (IR-30-020); deadline wording conflict confirmed in the PDF itself (IR-30-008).
   DOE/OSTI Faulds literature verified: step-overs/relay ramps host ~32 % of Great Basin geothermal
   systems, ~39 % of systems are blind (up to 75 % of resources), outflow can surface km from the
   source structure. Local GDR data measured: 27,092 wellspring rows (512 hot cells ≥ 60 °C, 256 ≥
   100 °C), 21 volcanic vents with **0 of 21 within 300 m of the catalogue**, 1,126 Qfaults traces
   (55 % of in-footprint centroids within 300 m of catalogue — circularity warning IR-30-021).
3. **Five never-tried H-32 hypotheses** registered and ranked (`docs/hypotheses.md` +
   `docs/hypotheses.html`): discharge corridors (H-32-01), un-catalogued Qfaults completion
   (H-32-04, validation-limited), buried pinch-out edges (H-32-05), geothermometer discordance
   (H-32-03), vent feeder alignments (H-32-02).
4. **H-32-01 ran its preregistered spatial component holdout and FAILED all three gate clauses** —
   pooled ΔDTI spring − proximity-matched control **−0.01494** (screen) and **−0.01537**
   (confirmation), **0/4** quadrants; spring zones earn ~3× less hidden credit per emitted pixel
   than matched random (0.0122 vs 0.0320 at 15k px), consistently across 4 zone arms × 3 budgets ×
   2 splits. Not promoted, no slot. Evidence:
   [h32-01-vent-corridor-holdout.md](docs/research/h32-01-vent-corridor-holdout.md) +
   [JSON](docs/research/h32-01-vent-corridor-holdout.json) +
   [preregistration](docs/research/h32-01-preregistration.md). Review found and fixed an unused
   `--confirm-threshold-c` flag; the supplementary ≥ 100 °C sensitivity run is recorded separately.
5. **Status feed automation:** `scripts/build_status.py` regenerates `docs/status.json` from the
   machine-readable artifacts (gate JSONs, download manifests, mirror pins, score ledger) — no more
   hand-edited status. The score ledger gained `evidence_class`/`as_of_utc` columns and six
   **official-snapshot** rows from the 2026-10-03 leaderboard read (DARD 0.3195 rank 1 … wbg1 0.2600
   rank 15). Suite now collects **60 tests**, all passing on this image.

### Independent session, same day — full-budget ablation, emitter frames, external-data bridge

A second autonomous session (`arena/01a102a1-gemsdoe30`, PR #8) ran three further real holdouts on
the same prepared grid. Where the two sessions overlap they **agree**, and where they differ the
difference is budget, not method.

**(A) The paired boundary-loss ablation at full budget.** Eight checkpoints, seed 30, **6 × 100
steps × batch 4 × 96 px (600 optimizer steps per fold)** — 15× the screen budget above. Pooled
exact full-grid OOF DTI **0.105026 (regional) → 0.097119 (combined)**, Δ **−0.00791**, positive in
**1 of 4** folds. Near-miss allocation again changed exactly as designed, and this time the direction
is measurable in both terms: truth pixels resolved exactly fell 48,491 → 47,964, the 200–300 m
near-miss bin rose 5,070 → 5,829, and far-field `FP_w` rose 1,044,121 → 1,151,942. The exchange rate
is roughly **1 unit of new near-miss credit per 85 units of new distant false-positive mass**, against
a metric that prices them at 1 : 0.2. Mechanism: `FP_w = Σ p(x)(1 − max_g k(d))` is linear in total
emitted mass over a 5.17 M-pixel footprint, so a boundary term built from the same kernel mostly
pushes probability inward *everywhere*. **Combined verdict across all three runs: the geometry term
reliably changes near-miss behaviour and never reliably raises the proxy DTI. Not promoted.**
Evidence: [loss-ablation-verdict.md](docs/research/loss-ablation-verdict.md) (+ `runs/loss-ablation/holdout.json`).

**(B) Emitter frames — how the mass is placed beats how it is learned.** The same out-of-fold
probability field scores **0.09712** submitted as a dense field and **0.25461** after 400 m
Poisson-disk sparsification: a **2.6×** difference from the emission operator alone, and the largest
single effect measured in either session. Against the internal blind lattice the learned field wins by
**+3.4 %** on the catalogue frame (0.25461 vs 0.24634 at 4 px). A second frame was then built that the
catalogue cannot provide: the USGS SGMC fault inventory, split by connected component with 30 % hidden,
scored under the organizer's masking rule. On that frame the **budget-matched** control is the
decisive one — uniform random dots at the *same* dot count, not a differently dense lattice. At 5
repeats: our model-dot set (80,392 dots) scores **0.09526** against blind random at 80,392 dots
**0.07617** (**+25.1 %**) and against the 3 px probability lattice with 6.6× more dots (0.09395)
**+1.4 %**; the sibling-branch GBM candidate (75,001 in-domain dots) scores **0.07279** against blind
random at 75,001 dots **0.07460** (**−2.4 %**), i.e. below chance on this frame. Evidence:
[emitter-holdout.md](docs/research/emitter-holdout.md),
[novelty-holdout.md](docs/research/novelty-holdout.md),
`docs/research/{emitter-comparison,novelty-holdout,discovery-shift}.json`.
**Correction recorded for the audit trail:** an earlier draft of this section quoted "+4.4 % over a
blind lattice" for the model dots. That comparison used a lattice with 527,504 dots against an
80,392-dot candidate — unmatched budgets. The same-run budget-matched numbers above replace it, and
the direction of the conclusion survives only because the matched control is a *random* dot set
rather than a lattice; on the earlier unmatched comparison the sign alternates with the lattice's
spacing (74,288-dot lattice 0.08442, 97,028-dot lattice 0.09873).

**(C) A working official-data bridge.** A GitHub Actions runner downloads official layers,
SHA-256-verifies them, rasterises them onto the competition grid and commits the result back
(`data/external/external_receipt.json`). Verified: USGS SGMC `NV.zip` 69,056,094 B and `CA.zip`
24,977,406 B, plus GDR 1391 paleo-geothermal, Quaternary volcanics and 2 m temperature probes. The
SGMC derivation holds **21,160 features / 82,151 px** in the footprint, **75.1 % of them more than
300 m from every catalogue fault**. Falsification: **+2.9× enrichment** over chance against the
catalogue (positive) versus a **low-power** lidar corroboration test (AUC 0.520; the positive control
scores only 0.522) — recorded as inconclusive, not as a pass. Open irregularity: the Ingenious
Quaternary-fault v2 shapefile downloaded but rasterised to **zero** features inside the grid.

**(D) Metric theory.** Adding one prediction pixel whose triangular kernel credit against an
uncovered truth pixel is `k` changes the DTI denominator by exactly `0.2` and the numerator by `k`, so
**a dot helps iff `k > 0.2 × DTI`** — about **5.2 %** at the incumbent's operating point, and
**independent of the size of the hidden truth set**. This is why broad hedging across weak hypotheses
is near-optimal here, and why the SGMC layer is worth a bounded bet even though no local frame can
score it. Derivation and measured response surface: [metric-response-surface.md](docs/metric-response-surface.md).

**(E) Second published candidate, with a measured comparison.** `docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif`
(SHA-256 `fed5232e…66da`; 85,526 dots; **zero** dots on the masked catalogue) adds a bounded SGMC hedge
(worst case ≤ 3 % of the DTI denominator) to the model's off-catalogue dots. Both published candidates
were scored on the independent-inventory frame, 5 repeats: the SGMC-hedged candidate **0.18343** (the
SGMC arms are tautological there — hidden components of the same inventory — so this is not evidence),
the sibling GBM candidate **0.07279**, blind random at the same count 0.07460, the 0.2600 artefact
0.07061. **The GBM candidate's 75,001 dots are therefore worth less than 75,001 blind random dots on
an independent fault inventory, while our 80,392-dot model set is worth +25 % over its own matched
control.** Reported rather than hidden because it should decide which file, if any, is submitted.
**Neither candidate has a leaderboard score and no slot has been used.**

### Session 4 (2026-10-03, branch `arena/01a10315-gemsdoe30`) — data blocker closed, H-32-05 falsified

**The standing "single remaining blocker to training is data placement" is closed, and the claim that
the brief's central loss deliverable was "verified working here on CPU" was not true until this
session.** Both were re-checked from scratch rather than trusted:

1. **Data placement — resolved without manual input.** Raw `curl` to `drivendata.org` and
   `dropbox.com` fails in this sandbox (TLS EOF), but `gh api` reaches the pinned owner mirrors. The
   three core rasters were fetched from the pinned refs and reassembled, then **SHA-256-verified
   against `docs/research/mirror-pins.json`**: `4371c82e…43123bc5` (418,912,844 B, 5 parts),
   `7ba308cc…5ae4093`, `2176d08e…54d35cbc`. `download_competition_data.sh` exits 0;
   `prepare_data.py` reproduces **`dataset_signature 291d3467…dee855ed`, byte-identical to the
   signature earlier sessions recorded** — the independent proof that this is the same data
   (5,167,373 valid pixels, 60,988 catalogue positives, 19 bands, EPSG:32611, 100 m). Training then
   ran on real data on CPU (`train_model.py --fold 0 --loss combined`, ~0.55 s/step).
   Mirrors remain **not organizer-authenticated** (IR-30-001 unchanged). See IR-30-024.
2. **Boundary-loss verification gap — closed.** With no torch installed, the 5 boundary-loss tests in
   `tests/test_optional_loss.py` were **skipping**, so the deliverable the brief centres on had never
   executed here. torch 2.14.1 installed; the suite now runs them: **67 passed, 11 subtests, 0
   skipped** — including the check that the geometry term equals `1 − distance_weighted_tversky(…)`
   to 10 decimal places and that near-misses are ranked by 300 m kernel distance. See IR-30-030.
3. **H-32-05 (buried range-front pinch-out edges) — preregistered, run, falsified.** Design frozen in
   [h32-05-preregistration.md](docs/research/h32-05-preregistration.md) *before* the run, on the real
   `depth_to_base_surf` / `iso_grav_anom_hg` / `tmi_hg` bands, with USGS-cited physics
   ([OFR 2005-1154](https://pubs.usgs.gov/of/2005/1154/of2005-1154.pdf),
   [OFR 2000-189](https://pubs.usgs.gov/of/2000/0189/pdf/of00-189.pdf),
   [USGS 70259621](https://pubs.usgs.gov/publication/70259621)). Registered gate **failed every
   scoring clause**: screen Δ −0.02614 vs matched random (needed ≥ +0.002), 0/4 quadrants,
   confirmation Δ −0.02591. The pre-declared *transform clause* passed (+0.0012 / +0.0034: the
   basement-surface **edge** does beat its raw **magnitude**), but the whole family sits ~10× below
   the random controls. **Not promoted; no slot spent.** [Result](docs/research/h32-05-basement-edge-holdout.md).
   Declared design defect: the `coherence ≥ 0.5` floor accepted 99.65 % of pixels, so the
   oriented-edge variant was never fairly tested (IR-30-029).
4. **Three real bugs found and fixed** while verifying, each with a reproduction: the status feed
   looked for mirrors in the wrong directory so it always reported "no data" (IR-30-025); 9 of 22
   scripts could not run on an uninstalled checkout even though the docs say to run them that way
   (IR-30-026, fixed and re-verified with the package uninstalled); and
   `fetch_external_layers.py` clobbered a committed audit receipt on *any* invocation, including
   `--help` (IR-30-027 — an accidental `--help` cost a 783-line deletion, restored from git; in-flight
   evidence now goes to a sidecar and the canonical receipt needs `--allow-overwrite`).
5. **Reading of three consecutive falsifications (H-31-01, H-32-01, H-32-05) against the same
   `random_near_matched` control (~0.029 DTI):** the binding constraint on this proxy is **where a
   fixed emission budget is placed relative to mapped structure**, not which scalar field ranks the
   pixels. The next registered experiment should be a placement-policy test, not a new detector.

## Current verified state — 2026-10-03

- The recorded baseline commit for this checkout already contains the model/loss, tests, training/inference/validation scripts, and site scaffold. The Git history available here is shallow/grafted to that commit, so earlier claims about a prior README-only state cannot be independently verified from this repository. At the start of this review there were **no competition rasters, sample template, checkpoints, real holdout predictions, or generated GEMSDOE30 TIFFs**. The rasters have since been restored from SHA-256-pinned owner mirrors (not organizer-authenticated) and real-data training, OOF prediction, stitching and scoring all run locally; what remains blocked is organizer-authenticated data and the hidden expert labels.
- The DrivenData data page redirects an unauthenticated visitor to its login page. No DrivenData credentials/session or competition rasters are available here, and the shell cannot retrieve the public owner-mirror TIFFs in this environment. The safe data preflight is `bash scripts/download_competition_data.sh`; it reports missing inputs and does **not** attempt a login bypass.
- The official leaderboard was read on **2026-10-03**: the displayed leader was **DARD, 0.3195**. It is a live, changeable public score; it is not private-test performance. The supplied claim that the linked GEMSDOE25 D2.8 TIFF scored 0.2600 is **not authenticated to that exact file**: the GEMSDOE25 landing page currently describes that TIFF as unscored/not slot-approved, while the public leaderboard contains a 0.2600 row for participant `wbg1` at rank 15. See [analysis](docs/leaderboard-analysis.md) and [irregularities](docs/irregularities.md).
- The 300 m loss geometry and spatial-holdout pipeline are implemented. **44 tests pass** with NumPy, SciPy, rasterio, PyTorch, and pytest installed; the geometry term matches the independent metric on a masked grid, and a seam regression test confirms the pooled OOF score keeps 100 m near-miss credit across quadrants. Review fixed quadrant-component pooling, prevents fold-specific checkpoints from being relabeled across OOF folds, and checks prediction/checkpoint hashes and experiment recipes. A disposable synthetic 64×64 smoke passed paired four-fold training/inference, OOF stitching/evaluation, full-fit inference, and exact-template TIFF validation. Real-data spatial holdouts have now run (four-arm pilot, metric-emission holdout, paired loss ablation) and are recorded above; the loss screen is positive but unconfirmed, and **no candidate file has been promoted, no score is claimed, and no GEMSDOE30 TIFF has been produced.**
- The site exposes a one-click link to the pre-existing GEMSDOE25 research TIFF, clearly labeled external, unscored, and not slot-approved. It is not represented as this repository's model output or as an approved competition submission. A genuine GEMSDOE30 download will be generated only after data placement, training, holdout promotion, and exact-template validation.

## Start here

1. Read the [executive summary and submission guide](executive-summary.html).
2. Read the styled [leaderboard/file attribution analysis](docs/leaderboard-analysis.html), [ranked hypotheses](docs/hypotheses.html), [loss design](docs/loss-design.html), and [irregularity register](docs/irregularities.html).
3. Review the styled [official/primary source register](docs/sources.html); full claim-by-claim notes remain in `docs/sources.md`. Before any eventual entry, review the [working AI-use disclosure draft](docs/ai-disclosure-draft.md) against every team member's actual use.
4. Install the optional geospatial/training stack and run the test suite (optional geospatial and loss-gradient tests run when their dependencies are installed):

   ```bash
   python -m pip install -e '.[train,test]'
   python -m unittest discover -s tests -v
   python scripts/loss_geometry_probe.py
   ```

5. Place the competition files, downloaded through an authorized competition session, in `data/raw/` as `training_features.tif`, `labels.tif`, and `sample_submission.tif`. Then run:

   ```bash
   bash scripts/download_competition_data.sh
   python scripts/prepare_data.py
   ```

   **Status (verified 2026-10-03, this session): this step is complete and reproducible without any
   manual input.** `python scripts/restore_public_mirrors.py` fetches the SHA-256-pinned owner
   mirrors through the GitHub API and reassembles `training_features.tif` from its five parts; all
   three core rasters then hash-match `docs/research/mirror-pins.json` exactly
   (`4371c82e…43123bc5` / `7ba308cc…5ae4093` / `2176d08e…54d35cbc`), `download_competition_data.sh`
   exits 0, and `prepare_data.py` reproduces `dataset_signature 291d3467…dee855ed` — identical to the
   signature recorded by earlier sessions, which is the independent check that the mirror is the same
   data. `docs/status.json → data_placement` re-verifies placement and hashes on every regeneration.
   These remain **owner mirrors, not organizer-authenticated files**.

   The preparation script fails closed on CRS, transform, shape, label encoding, or footprint mismatch. It records SHA-256 values for the three source rasters and a dataset signature in the prepared manifest, then writes raw features and masks under the Git-ignored `data/processed/`. Each training run fits and stores its own robust normalization statistics using training-fold pixels only, never held-out pixels; the checkpoint is bound to that prepared dataset signature.

6. Run the *paired* loss experiment on all four buffered spatial folds with the same seed and optimization settings in both arms. For each fold `F` in `0 1 2 3`, run:

   ```bash
   python scripts/train_model.py --fold F --loss regional --output runs/fF-regional.pt
   python scripts/train_model.py --fold F --loss combined --output runs/fF-combined.pt
   python scripts/infer_model.py --checkpoint runs/fF-regional.pt --fold F --predictions-only --output runs/fF-regional.npy
   python scripts/infer_model.py --checkpoint runs/fF-combined.pt --fold F --predictions-only --output runs/fF-combined.npy
   ```

   Keep each inference `.json` sidecar beside its `.npy`. The stitcher checks prediction-array and checkpoint SHA-256 values, explicit checkpoint/fold identity, the source-bound prepared-grid/dataset signature, identical training recipes, and held-out-only masks before it creates a hashed OOF mosaic. The evaluator verifies both OOF manifests and paired recipes. It computes the exact pooled DTI once over the complete stitched OOF grid (retaining cross-quadrant 300 m interactions); fold-isolated values are diagnostics only. Then compare both arms with the exact metric and near-miss diagnostics:

   ```bash
   python scripts/stitch_oof_predictions.py --fold0 runs/f0-regional.npy --fold1 runs/f1-regional.npy --fold2 runs/f2-regional.npy --fold3 runs/f3-regional.npy --output runs/regional-oof.npy
   python scripts/stitch_oof_predictions.py --fold0 runs/f0-combined.npy --fold1 runs/f1-combined.npy --fold2 runs/f2-combined.npy --fold3 runs/f3-combined.npy --output runs/combined-oof.npy
   python scripts/evaluate_loss_ablation.py --regional runs/regional-oof.npy --combined runs/combined-oof.npy
   ```

   Repeat the complete paired design with preregistered fresh seeds for confirmation. Do not treat one fold or the synthetic probe as confirmation.

7. Only after a candidate clears the frozen holdout and confirmation gates should it be fit on all permitted training labels. `scripts/infer_model.py` or `scripts/build_submission.py` writes a uniquely named, template-matched TIFF and a JSON sidecar. The builder and validator add `src/` automatically when run directly from this checkout (package installation is not required for this format step). For the portal, build with the default `--outside zeros`, then run `python scripts/validate_submission.py FILE.tif --template data/raw/sample_submission.tif --portal-safe`; this strict check rejects NaN/Inf anywhere in the raster and must pass before any human upload. Upload the `-zeros.tif` artifact, not the legacy NaN-outside research copy.

## Useful links

- [DrivenData competition homepage](https://www.drivendata.org/competitions/306/competition-doe-gems/) — navigate to Problem Description, About, Data, and Leaderboard. The requested direct pages are documented in `docs/sources.md`.
- [Official GEMS rules PDF (NLR, September 2026)](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN data release, DOI 10.5066/P93LGLVQ](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7)
- [DOE Geothermal Data Repository: INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391)
- [Kervadec et al., Boundary loss (2018 preprint; PMLR proceedings 2019)](https://proceedings.mlr.press/v102/kervadec19a.html)

## Repository map

- `index.html`, `executive-summary.html`, `docs/assets/site.css` — GitHub Pages landing page and submission instructions; the landing page links the external reference TIFF, not an approved GEMSDOE30 result.
- `docs/ai-disclosure-draft.md` — truthful current-session starting point for the rules-required entrant narrative; must be updated and reviewed before any entry.
- `src/gemsdoe30/metric.py` — reference DTI implementation; vectorized with NumPy/SciPy when installed, dependency-free for small tests.
- `src/gemsdoe30/losses.py` — regional soft-Tversky plus the 300 m metric-geometry term, inspired by (not a verbatim copy of) Kervadec et al.
- `src/gemsdoe30/cv.py`, `analysis.py` — buffered spatial blocks, exact full-grid OOF scoring, fold-isolated diagnostics, and near-miss profiles.
- `src/gemsdoe30/normalization.py` — deterministic robust scaling fit separately on each training-fold mask and saved in each checkpoint to prevent held-out feature leakage.
- `src/gemsdoe30/submission.py` — strict GeoTIFF writer/validator and sidecar.
- `scripts/` — data preflight, preparation, paired training arms, inference, validation, and probes.
- `docs/` — source ledger, reported-score ledger, hypothesis register, results interpretation, and irregularities.
- `data/raw/`, `data/processed/`, `outputs/`, `runs/` — local-only data and outputs; ignored by Git.

Later on 2026-10-03 a first GEMSDOE30 candidate file was built and published for download: a **4-fold out-of-fold GBM surface** (each pixel predicted by a model that never saw its quadrant; fold models from the metric-emission experiment) emitted with the LOFO-selected adaptive Poisson-disk rule (radius 5 px, gamma 1, pool 480k) → 90,358 dots, median nearest-neighbour spacing 2.83 px, 17.7 % within 300 m of the catalogue (2.1× the 8.6 % base rate). Local format validation passes all 11 checks (5,167,373 in-footprint values in [0,1], NaN outside, EPSG:32611, 100 m, template transform preserved). **It is not holdout-promoted** — its family beat uniform by only +0.0025 against a required +0.005 — and the site labels it accordingly with a paste-ready note. Artifacts: [candidate TIFF](docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-nan.tif), [manifest](docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-nan.json), [build record](docs/research/candidate-2026-10-03.md).

## Current next steps and limits

1. **Upload path is fixed — use it.** The portal-safe `-zeros.tif` variants are the primary downloads for all three published TIFFs (GBM candidate, measured variant, external D2.8) and the site's submission guide walks through the upload with paste-ready notes. The scientific gates are unchanged: **no candidate is holdout-promoted**; submitting an un-promoted file is the owner's decision, and the file's note must say exactly that.
2. **H-32-01 and H-32-05 are both falsified on the proxy**; the remaining runnable local candidate is the **H-31-02 reduced matched-filter scarp arm** on the local 12-channel scarp stack (the raw 3DEP 1 m arm still needs the ~9 GB tile transfer off-sandbox). **The higher-value next experiment, argued from three consecutive falsifications (H-31-01, H-32-01, H-32-05) against the same `random_near_matched` control, is a *placement-policy* test — how to allocate a fixed emission budget between near-catalogue and off-catalogue space — rather than another detector.** H-32-04 cannot be validated on the catalogue proxy at all (IR-30-021) and needs the OSTI 1148722 / GDR 616 inventories retrieved and checksummed first. The independent-inventory idea behind the measured variant's novelty frame is the *shape* of evidence that should gate future claims (see item 7).
3. **Boundary loss remains not promoted — and its retry criterion has now been executed.** The recorded retry (larger budget + preregistered boundary-weight sweep + emitted-mask scoring) ran as a fold-0 screen ([loss-weight-sweep.md](docs/research/loss-weight-sweep.md), 2026-10-03): dense scoring prefers plain `regional` at every weight; emitted-mask scoring prefers `combined-100` by only +0.0010 on one fold — the scorings disagree, so no weight is selected for confirmation and the line stays closed. The near-miss behavioural effect the brief asked for *is* demonstrated (partial-distance truth coverage 1,889 → 724); the metric gain is not. Any future loss work should start from the standing [verification-protocol.md](docs/research/verification-protocol.md) (three checks with pre-stated criteria) and a new mechanism, not more λ tuning.
4. **Build/validate rule unchanged:** an exact-grid, holdout-promoted candidate only after its family beats the same-run best by the frozen margin with fresh-seed confirmation. Both published un-promoted candidates — the GBM surface (`…aedb3d13-nan.tif`, SHA-256 `f5d137b9…c7cc2`, 90,358 dots) and the measured SGMC-hedge variant (`…ac08b41e.tif`, SHA-256 `fed5232e…66da`, 85,526 dots) — plus their portal-safe variants are research artifacts with honest notes.
5. **Feed:** `scripts/build_status.py` keeps `docs/status.json` current automatically. The leaderboard itself can only be refreshed by dated manual reads (DrivenData ToS prohibit automated monitoring) — recorded in `docs/score-ledger.csv` with `evidence_class=official-snapshot`.
6. **Limits that only the owner/organizer can lift:** organizer-authenticated data (IR-30-001); the hidden expert labels (the real target); score-to-file attribution for the D2.8 artifact (IR-30-002); entrant eligibility under rules §1.3 (IR-30-020); the deadline-time discrepancy (IR-30-008); final AI-disclosure narrative sign-off.
7. *(from the independent 2026-10-03 session's emitter work)* The budget-matched blind-random control is the standard for any emitter claim in this repository: a learned emitter must beat uniform random dots **at the same emitted count on the same frame and the same run**, because the previous lattice control changed sign with lattice spacing. Under that standard, only the UNet out-of-fold dot set clears it (+25.1 %); the HistGradientBoosting-derived candidate does not (−2.4 %), and no emitter has yet been tested against the *clustered* geometry the official hidden fault set is expected to have.
