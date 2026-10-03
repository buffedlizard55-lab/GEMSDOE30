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

> **Branch note:** the literal owner brief above preserves the branch name recorded in the original request. This Arena session is fixed to `arena/01a103c1-gemsdoe30`; all changes, commits, pushes, and any PR from this session remain on that assigned branch. The brief's verbatim wording is preserved above unchanged.

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

## Current reviewed state — 2026-10-03 (after synchronizing with current `main`)

This is the authoritative current status; later dated experiment records below are supporting evidence, and older session narratives are history. The cumulative reviews are [the scientific/repository review](docs/research/review-checklist-2026-10-03.md) and [the current submission-format correction review](docs/research/submission-format-review-2026-10-03.md).

- **Data and sources:** the local grid, labels, template, and derived feature stacks are restored from SHA-256-pinned owner mirrors, not organizer-authenticated. The DrivenData data tab redirects to login; no credentials or bypass were used. Selected official GDR 1391 archives were downloaded and checksum-verified through the public runner bridge; a CRS/encoding ingestion defect was fixed in `scripts/fetch_external_layers.py`. Qfaults rasterization now produces local features, but its provenance overlaps the training catalogue and it is not independent truth. See [source register](docs/sources.md), `data/external/external_receipt.json`, and [irregularities](docs/irregularities.md).
- **Metric-shaped loss:** the 300 m geometry term remains paired with regional soft-Tversky. It changes near-miss allocation, but the fresh-seed confirmation was +0.000115 with 2/4 folds positive; a separate larger-budget confirmation was −0.00791 with 1/4 positive. The weight-sweep scorings disagreed. No boundary-loss setting is promoted.
- **H-31-02b / H-33-01 / H-32-05b:** the reduced-stack H-31-02b scarp screen failed its spatial-best and feature-perturbation gates. H-33-01's 80k gate was void at 68,573 active dots vs 80,000; its 40k sensitivity was active-count matched by code review but is not a promotion result. H-32-05b's 1.5 km p90 basement-edge variant improved on its own ablation but stayed below its spacing-and-distance-matched control. None is promoted.
- **H-31-02r promising but withheld:** the preregistered 1 m LiDAR scarp-dipole + 500 m strike-continuity transform beats its `step_max` ablation by 22.4%/20.2% on catalogue screen/confirmation and beats spacing/distance-matched controls on four independent USGS SGMC frames. However, the catalogue-component spatial check is negative (0.03323 vs 0.03585, Δ −0.00261; 2/4 quadrants); the three-check evaluation is split by frame, and the SGMC top-decile calibration-ratio criterion passes only 2/4 folds. The predeclared dual-frame promotion gate therefore fails. This is a promising measured feature, **not a promoted entry**; do not retune against the already-inspected SGMC labels. Evidence: [registered results](docs/research/h33-01-placement-and-scarp-holdout.md), [three-check results](docs/research/verification-checks-results.md), and IR-30-035.
- **Five genuinely untried geological hypotheses:** current shortlist and source/access/falsifiable gates are in [docs/hypotheses.md](docs/hypotheses.md) and [the review note](docs/research/untried-hypotheses-review-2026-10-03.md). H-31-04's GeoDAWN band-lineage/schema check is the lowest-cost new-hypothesis action; no unvalidated candidate gets a weekly slot.
- **Scores and TIFFs:** the dated public snapshot showed DARD 0.3195 and `wbg1` 0.2600 (rank 15); neither leaderboard row identifies a TIFF hash. The D2.8 local artifact's claimed 0.2600 remains unlinked and its owner page labels it unscored/not slot-approved. The published competition format requires null/NaN outside the data bounds; the site now links the NaN-outside research TIFFs and sidecars, locally checked against the available template. Zero-outside variants are retained only as explicitly nonstandard diagnostics and are not linked as submission files. The exact artifact behind the earlier `[0,1]` error is unknown, so its cause remains undiagnosed. No file was uploaded; no weekly slot has been used.
- **Submission-format correction:** `submission.py` and the CLI now default to the published NaN-outside contract; whole-raster finite checks and zero-outside writes are labeled diagnostic-only. Sidecars separately record published-format results and strict whole-raster diagnostics. See [the three-pass correction review](docs/research/submission-format-review-2026-10-03.md).
- **Session 30 (branch `arena/01a103f1-gemsdoe30`), metric-exact emitter and the catalogue-frame inversion:** `src/gemsdoe30/emitter_opt.py` (EDGE) emits the expected-marginal-credit greedy support of a belief field and stops at the published marginal threshold. In the registered component-holdout comparison (`docs/research/emitter-opt-holdout.json`, `…-convergence.json`, protocol in `emitter-opt-preregistration.md`) it beat every belief-ordered emission family on the same field: **0.19125 vs 0.13848** (+0.05277) on the proximity field, **0.18368 vs 0.14014** (+0.04354) on the hybrid field, **0.15784 vs 0.14015** (+0.01768) on external evidence — and it **lost** on the leak-contaminated GBM field (0.11834 vs 0.13326), which is reported in the same document. `IR-30-039` records the measured **sign inversion** between the full-catalogue proxy and the owner-reported leaderboard ordering of the `dot_thin` family; the consequence is that catalogue-derived frames can no longer adjudicate emission design (they remain mandatory degenerate-failure screens). The new `gemsdoe30-edge-hybrid-80k-02845bd4-nan.tif` download is published-format-validated, unpromoted, and 0 of its 80,000 dots lie on the training catalogue. See `docs/research/score-ceiling-analysis.md` for the 0.3195 coverage arithmetic.
- **Rules and verification:** all seven parsed chunks of the September 2026 official rules PDF were reviewed. The homepage/rules deadline-time conflict, eligibility, and final entrant-approved AI disclosure remain open. Final verification is recorded in the review checklist. PR [#15](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/15) was merged to `main` at `44403fd67a92fd5b7658233e62af5b1d45811d1b` on 2026-10-03 21:50:40 UTC; its branch head was `e3967c590b43c65b4f3433f46d50d2781c286fdd`. Documentation-only PR [#16](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/16) then recorded that merge in the review log; it merged to `main` at this session's base `1e377d4556445a3e9a80b64e129e36ed82e9a93f` on 2026-10-03 21:51:57 UTC.

## Historical session record — retained as an audit trail (superseded where noted)

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

### Session 2 (later on 2026-10-03) — historical range-error hypothesis, vent research base, H-32 register, H-32-01 gate

1. **Historical range-error investigation — unresolved and superseded by the format correction below.** The official sample template contains **7,111,787 NaN cells outside the footprint**. The earlier session hypothesized that a whole-array `[0,1]` check might reject NaNs; this was never verified and does **not** diagnose the reported error. The exact offending upload remains unknown. That hypothesis previously led to finite-zero-outside diagnostic copies; they do not match the published null/NaN-outside convention and are no longer presented as submission-format downloads. No upload was made. The current builder defaults to NaN outside; finite-all-cells checking and `scripts/make_portal_safe.py` remain diagnostic only.
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

**(B) Emitter frames — historical diagnostics with an active-count correction.** The same out-of-fold
probability field scored **0.09712** as a dense field and **0.25461** after 400 m Poisson-disk
sparsification in the earlier catalogue proxy; this is an emission-operator diagnostic, not a
competition score. The SGMC comparison's archived `cand_t04s4` arm and blind-random arm each had
80,392 *global* dots, scoring **0.09526** and **0.07617** (+25.1 %) respectively; the 3 px lattice
scored 0.09395. However, active scored-domain counts were **72,310 candidate / 73,843 random /
80,388 archived**, so these were global-budget matched, **not active-count matched** (IR-30-037).
They do not describe the later 85,526-dot linked SGMC-hedge TIFF. The GBM diagnostic was likewise
not active-count matched: GBM had 90,358 global / 75,001 active dots, while its random control had
75,001 global / 68,848 active dots (DTI 0.07279 vs 0.07460). Do not interpret either comparison as
proof of a candidate advantage; no GEMSDOE30 score or promoted candidate results. Evidence:
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

**(E) Second published research TIFF and count-scope correction.** `docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif`
(SHA-256 `fed5232e…66da`; 85,526 dots; **zero** dots on the masked catalogue) adds a bounded SGMC
hedge (worst case ≤ 3 % of the DTI denominator) to model dots. Its 0.18343 SGMC mean is tautological
because the SGMC inventory is both an input to this TIFF and the scored inventory; it is not validation.
The earlier GBM diagnostic was 0.07279 vs 0.07460 random, but the active scored-domain counts were
75,001 vs 68,848 (despite matching 75,001 global random dots), so it is not an active-count-matched
comparison. The archived +25.1 % `cand_t04s4` result described above belongs to a different arm, not
to this 85,526-dot TIFF, and its active counts also differed. No file has a leaderboard score or is
promoted, and no weekly slot has been used.

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

### Session 5 (2026-10-03, this branch `arena/01a10330-gemsdoe30`) — emitter-order fix, score ledger, H-33-01 run to verdict

1. **IR-30-031: real library bug found and fixed.** `poisson_disk_select`/`adaptive_disk_select`
   documented a descending-score greedy but built `np.lexsort((-values, rows, cols))` — and
   `np.lexsort` keys on the **last** array, so visits were column-major (raster order), not
   score-first. Fixed at all three occurrences, regression tests added (`ScoreFirstVisitOrderTests`,
   `OrderedSelectionTests`, plus a `max_kept` prefix-equivalence test), and the affected-artifact
   caveat recorded in [docs/irregularities.md](docs/irregularities.md). Historical *relative*
   conclusions stand (arms and controls shared the same rule); prior absolute numbers are now
   labelled "measured under raster-order visiting".
2. **H-33-01 (placement policy) — preregistered, run, decided.** Frozen design in
   [h33-01-preregistration.md](docs/research/h33-01-preregistration.md) before any score was seen;
   harness `scripts/placement_policy_holdout.py` (tests: `tests/test_placement_policy.py`).
   The gate-budget screen (80,000 dots) hit a capacity wall — the 0.4-thresholded, 4 px-thinned
   pools hold only 68,573 dots, so every quota arm collapsed to the same union; the harness
   **voided** the gate instead of adjudicating a non-count-matched comparison, and the registered
   verdict is **not promoted** (IR-30-032 records the design undercount and the new pre-flight
   capacity rule). The count-matched 40 k sensitivity run is the substantive evidence:
   whole-domain score-first thinning **0.07608** beats blind random **+35 %** and beats **every**
   band-stratified arm (0.0721–0.0725), while pure proximity ranking is catastrophic (0.03660).
   Verdict: **the placement-policy line is closed** — placement is exhausted as a lever; the next
   registered experiment must improve the score field itself. Full numbers:
   [h33-01-placement-policy-holdout.md](docs/research/h33-01-placement-policy-holdout.md) ·
   [JSON](docs/research/h33-01-placement-policy-holdout.json).
3. **Regional OOF mosaic regenerated post-fix and verified**: `runs/oof/regional-oof.npy`,
   5,167,373 finite pixels (= template count), range [0, 1], mean 0.23551, 23.67 % > 0.4,
   scope sidecar matches the frozen 4-fold plan.
4. **Score ledger refreshed** with dated `official-snapshot` rows (2026-10-03 manual read, twice,
   consistent): leader DARD **0.3195**; `wbg1` 0.2600 at rank 15 confirmed; a rank-19 row of
   0.2449 numerically equals the owner-reported GEMSDOE27 score — recorded as coincidence, not
   attribution. No GEMSDOE30 file has been scored; target **> 0.3195** is not yet reached.
5. Full suite at that review: **80 passed + 11 subtests, 0 skipped**. The three then-current zero-outside diagnostic downloads passed 12/12 *finite-all-cells* checks; this was an internal diagnostic, not published-format compliance or portal acceptance. The NaN-outside source TIFFs and restored labels/template matched their SHA-256 pins byte-for-byte. The latest submission-format correction and sidecar rechecks are recorded below and supersede any earlier “portal-safe” wording.

## Superseded baseline snapshot — before owner-mirror restoration (historical)

The following notes describe an earlier checkout state and are retained as an audit trail only; they are superseded by **Current reviewed state** above and the later experiment records below.

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

7. Only after a candidate clears the frozen holdout and confirmation gates should it be fit on all permitted training labels. `scripts/infer_model.py` or `scripts/build_submission.py` writes a uniquely named, template-matched TIFF and a JSON sidecar. The builder defaults to the published null/NaN-outside convention; it accepts `--note` or `--comment` for the paste-ready submission note. Run `python scripts/validate_submission.py FILE.tif --template data/raw/sample_submission.tif` for the published-format local check. `--finite-all-cells` is a stricter whole-raster diagnostic (with legacy alias `--portal-safe`), not an organizer requirement or acceptance claim. Building zero outside requires `--outside zeros --allow-nonstandard-zero-outside` and is diagnostic only; do not use it as the submission format unless the organizer explicitly clarifies the rule. The exact file behind the prior `[0,1]` error remains unidentified, so its cause is undiagnosed. Local validation is not promotion or upload approval; the authorized entrant must review current official instructions before any manual submission.

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
- `src/gemsdoe30/submission.py` — published-format GeoTIFF writer/validator (NaN outside by default) and auditable sidecar; strict finite-all-cells checking is diagnostic only.
- `scripts/` — data preflight, preparation, paired training arms, inference, validation, and probes.
- `docs/` — source ledger, reported-score ledger, hypothesis register, results interpretation, and irregularities.
- `data/raw/`, `data/processed/`, `outputs/`, `runs/` — local-only data and outputs; ignored by Git.

Later on 2026-10-03 a first GEMSDOE30 candidate file was built and published for download: a **4-fold out-of-fold GBM surface** (each pixel predicted by a model that never saw its quadrant; fold models from the metric-emission experiment) emitted with the LOFO-selected adaptive Poisson-disk rule (radius 5 px, gamma 1, pool 480k) → 90,358 dots, median nearest-neighbour spacing 2.83 px, 17.7 % within 300 m of the catalogue (2.1× the 8.6 % base rate). Local format validation passes all 11 checks (5,167,373 in-footprint values in [0,1], NaN outside, EPSG:32611, 100 m, template transform preserved). **It is not holdout-promoted** — its family beat uniform by only +0.0025 against a required +0.005 — and the site labels it accordingly with a paste-ready note. Artifacts: [candidate TIFF](docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-nan.tif), [manifest](docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13-nan.json), [build record](docs/research/candidate-2026-10-03.md).

## Session 6 update (2026-10-03, branch `arena/01a10349-gemsdoe30`) — 1 m LiDAR scarp dipole (`H-31-02r`), 1.5 km coherent basement step ridge (`H-32-05b`), 6.38× clumping audit (`IR-30-033`), and three-check verification

Following the Session 4–5 next steps above, we preregistered
([`docs/research/h33-01-placement-and-scarp-preregistration.md`](docs/research/h33-01-placement-and-scarp-preregistration.md))
and executed (`scripts/placement_and_scarp_holdout.py` and `scripts/run_verification_checks.py`)
the spacing-matched placement-policy decomposition (`H-33-01`), the reduced 1 m LiDAR scarp dipole +
500 m strike continuity arm (`H-31-02r`), the 1.5 km `p90` coherent basement step ridge re-test
(`H-32-05b`), and the full three-check verification protocol across both the **Catalogue
Component-Holdout Proxy** and the **Independent USGS SGMC Fault Inventory** (both unclustered and
5 km clustered frames):

1. **Methodological discovery (`IR-30-033`) — 6.38× clumping confounder in legacy top-N holdouts:**
   `scripts/basement_edge_holdout.py` and `scripts/vent_corridor_holdout.py` emitted un-thinned
   `top_n_emission` blobs (`median_nn_px = 1.0 px`, `99.95 % ≤ 3 px`) while scoring them against
   dispersed `random_near_matched` dots (`median_nn_px = 5.10–8.94 px`). Under the 300 m (`3 px`)
   max-pooled kernel, clumped pixels cannibalize each other's true-positive footprint: on the exact
   same `depth_to_base_surf + iso_grav_anom_hg` feature surface, applying `r = 3.0 px` Poisson-disk
   thinning raises DTI from **`0.00373 → 0.02380`** (**6.38× multiplier** on screen, `4.88×` on
   confirm). All arms in `scripts/placement_and_scarp_holdout.py` enforce `r = 3.0 px` Poisson-disk
   spacing.
2. **Placement-policy decomposition (`H-33-01`):** On held-out catalogue components at `N = 15,000`
   Poisson-thinned dots, near-splay placement (`300–1,500 m` from known faults) achieves **`0.07234`**
   (screen) and **`0.07434`** (confirm) — **2.7×** uniform-domain placement (`0.02674` / `0.02694`)
   and **18.6×** far-basin placement (`> 5,000 m`, `0.00389` / `0.00326`). The `60/25/15 %`
   power-law hedge beats uniform placement on catalogue screen (`+0.02930`), catalogue confirm
   (`+0.01962`), and unclustered SGMC (`+0.00413`), but splits sign across the two 5 km clustered
   SGMC seeds (`−0.00274` on seed 31, `+0.00632` on seed 41; `promoted = false`).
3. **1 m LiDAR scarp dipole + 500 m strike continuity (`H-31-02r`):**
   * Beats its `step_max_only` ablation on both catalogue splits (`0.03323` vs `0.02715`, **+22.4 %**
     screen; `0.03066` vs `0.02551`, **+20.2 %** confirm; `transform_clause_pass = true`).
   * Crushes the spacing+distance-matched control on the **independent USGS SGMC fault inventory**
     by **+86.1 %** (`0.05913` vs `0.03178`, `4/4` quadrants) on seed 31 and **+82.8 %** (`0.05308`
     vs `0.02903`) on seed 41 in the unclustered frame, and by **+91.6 %** (`0.02916` vs `0.01522`)
     on seed 31 and **+60.5 %** (`0.01652` vs `0.01029`) on seed 41 in the 5 km clustered frame.
   * Check 2 calibration slopes are in range (**`0.9009`** catalogue; **`0.9101`** SGMC), and the
     catalogue top-decile ratio passes in **4/4** folds; the SGMC top-decile ratio passes only **2/4**,
     so the calibration gate is not satisfied across both frames. **Check 3** passes (permuting 1 m
     LiDAR channels on held-out SGMC removes **57.0 %** of gain; permuting full topography removes
     **97.2 %**; unrelated `iso_grav_anom_hg` retains **100.0 %**; `4/4` quadrants positive).
   * Check 1 is split by frame: catalogue proxy ΔDTI is `−0.00073` in the three-check protocol
     (`−0.00261` in the registered placement report; both `2/4` quadrants), while the SGMC frame is
     `+0.03670` (`4/4`). Real bedrock/range-front scarps outside the Quaternary catalogue are
     penalized by the catalogue proxy (`IR-30-035`). Per the pre-stated dual-frame/three-check gate,
     it is **withheld from weekly-slot promotion**.
   * Full evidence: [`docs/research/h33-01-placement-and-scarp-holdout.md`](docs/research/h33-01-placement-and-scarp-holdout.md) ·
     [`docs/research/verification-checks-results.md`](docs/research/verification-checks-results.md).
4. **1.5 km coherent basement step ridge (`H-32-05b`, fixing `IR-30-029`):** Computing the structure
   tensor on `dbs_edge` at a 1.5 km (`15 × 15 px`) scale (`median = 0.2588`, `p90 = 0.6545`) selects
   **10.00 %** (`516,432 / 5,164,312`) of footprint pixels (vs `99.65 %` in `IR-30-029`). The `p90`
   gate improves the Poisson-thinned basement step score on both catalogue screen (`0.02380 → 0.02574`)
   and confirm (`0.02566 → 0.02933`), but still trails the spacing+distance-matched control
   (`0.03660` / `0.03655`, `0/4` quadrants; `promoted = false`).

## Session 30 update (2026-10-03, branch `arena/01a103f1-gemsdoe30`) — metric-exact emitter (`EDGE`), catalogue-frame inversion (`IR-30-039`), H-34 register

**What was built.** `src/gemsdoe30/emitter_opt.py` (EDGE) and `src/gemsdoe30/fields.py` (belief
fields), with `scripts/emitter_opt_holdout.py` (registered comparison), `scripts/build_edge_candidate.py`
(candidate builder) and two test modules (`tests/test_emitter_opt.py`, `tests/test_fields.py`). EDGE
ranks candidate dots by the exact expected marginal credit
`dT(x) = Σ_δ π(x+δ)·max(0, k(δ) − C(x+δ))` and stops when `dT ≤ 0.2s/(1−0.2s)·dF`, i.e. at the exact
marginal condition of the published index. Bookkeeping is verified against an independent from-scratch
credit pass (relative error 1.95e-7); prefixes of the acceptance order reproduce the recorded cumulative
statistics.

**Registered result (frame fixed before running, `docs/research/emitter-opt-preregistration.md`).** Whole
8-connected catalogue components split seed 31 into a stand-in hidden half (20,870 px) and a known half
(40,118 px, masked from every metric term); four spatial quadrant folds; leave-one-fold-out parameter
choice per family. Pooled cross-validated DTI at each family's held-out choice:

| field | EDGE | best other family | margin | folds won |
| --- | ---: | ---: | ---: | ---: |
| proximity (known traces) | **0.19125** | adaptive 0.13848 | **+0.05277** | 4/4 |
| hybrid (proximity ∧ external evidence) | **0.18368** | adaptive 0.14014 | **+0.04354** | 3/4 |
| external (USGS SGMC + GDR layers) | **0.15784** | adaptive 0.14015 | **+0.01768** | 3/4 |
| gbm (leak-contaminated) | 0.11834 | adaptive **0.13326** | −0.01491 | 0/4 |

Uniform thinning (≈0.125), dense quantile emission (0.060–0.074) and the previously shipped
belief-ordered marginal rule (0.031–0.060) were beaten decisively in the same runs. The registered gate
(≥ +0.005 over the best other family, ≥ 3/4 folds) is met on all three legitimate fields and fails on the
leak-contaminated one, which is reported rather than hidden. Absolute values are **not comparable** with
the earlier registered 0.18675/0.18927 pair (different frame; its `data/processed/*.npy` inputs are absent
here). Registered limits: the stand-in hidden truth is half the same catalogue, so the margins are proxy
margins; the candidate should be taken at the measured prefix plateau, not at `accepted` (the proximity
peak is interior at 100,000 dots while the marginal rule kept accepting to the 160,000 cap).

**Candidate artifact (unpromoted).** `docs/downloads/gemsdoe30-edge-hybrid-80k-02845bd4-nan.tif`
(SHA-256 `f87d3fc008230ec12a2b2ad260de643d15b8e474135d28020dafd2c784d2cbd5`, 592,782 B): 80,000 dots,
binary, **0 on the training catalogue**, published-format validation passed, sidecar with the full
provenance. It is linked first on the site with an explicit "unpromoted" label; no slot was used.

**IR-30-039 — the catalogue proxy is inverted.** On hash-verified bytes: full-catalogue proxy DTI is
0.16635 (parent, 121,131 dots), 0.17193 (d1.5, 60,069) and 0.16177 (d2.8, 44,090) while the
owner-reported scores for the same three artifacts rise 0.1922 → 0.2477 → 0.2600. The official metric
deletes USGS/INGENIOUS pixels from every term, so a catalogue frame pays for exactly the dots the
competition removes. Consequences recorded in `docs/irregularities.md` and
`docs/research/score-ceiling-analysis.md`: catalogue frames stay as screens, never as promotion evidence;
the archived negatives under that frame are screen failures inside a biased frame, while the independent
SGMC-novelty results in those reports stand.

**Highest-score study (`docs/research/score-ceiling-analysis.md`).** The 0.3195 gap is a coverage gap,
quantified from the metric alone: at `s = 0.3195` a dot must sit within ≈280 m of a scored truth pixel
(`k > 0.0683`), and with the owner-model hidden mass the leader's statistics need `T = 3,466 + 0.0683·F`;
with perfect knowledge the same metric ceilings near 0.78. Also derived: a binary 0/1 raster strictly
dominates any graded map of the same support, so every submission must be sparse binary dots.

**H-34 register (`docs/hypotheses.md` §H-34, `docs/hypotheses.html`).** Four new ranked candidates that
target faults a surface catalogue cannot contain: **H-34-01** substrate-concealment prior from USGS SGMC
map-unit polygons (data on disk, next action); **H-34-02** potential-field depth lineaments (GeoDAWN tilt +
Euler deconvolution); **H-34-03** drainage χ/ksn (USGS NHD + 3DEP, blocked until the clipped product is on
disk); **H-34-04** heat-flow anomalies and borehole-gradient discontinuities (IHFC release 2024, power-check
first). Each names layers, physical signature, why it evades USGS/INGENIOUS, its difference from existing
work, expected index gain versus cost, an official free source verified this session (source register
addendum), and a falsifiable blocked-holdout gate. None is validated; none may consume a slot.

**Operations.** `.github/workflows/status-feed.yml` regenerates `docs/status.json` from repository
artifacts and re-runs the format checks on every relevant push and weekly (no DrivenData access, no
scraper). `IR-30-040` fixed the external-layer bridge trigger (it pointed at a stale branch name);
`IR-30-041` records the emitter-truncation semantics and the convergence re-run. Test suite:
**107 passed, 5 skipped (torch absent), 7 subtests passed**.

## Current next steps and limits

1. **No file is promoted and no weekly slot is justified.** The site prominently links the NaN-outside research TIFFs, which pass the repository's local checks against the published null/NaN-outside convention. Zero-outside variants are archived only as nonstandard diagnostics; they are not format-conformant under the published rule and are not linked as submission files. The exact file behind the previous `[0,1]` error is unknown, so the cause remains undiagnosed. No file was uploaded here.
2. **H-31-02r is the strongest measured new feature signal, but not a submission candidate.** Its spatial evidence is split between the incomplete catalogue proxy and independent SGMC frames, and the SGMC calibration-ratio criterion misses its fold threshold in 2/4 folds. The predeclared dual-frame gate withholds promotion. Do not rerun or retune on the inspected SGMC labels. A future OOF model integration would need a frozen design and validation independent of those inspected labels; absent that, do not spend a slot. Full results: [placement/scarp holdout](docs/research/h33-01-placement-and-scarp-holdout.md) and [three-check review](docs/research/verification-checks-results.md).
3. **Boundary-loss line remains closed.** The 300 m geometry term remains paired with regional loss and changes near-miss allocation, but seed-31 and larger-budget confirmations do not establish a DTI gain; weight-sweep scoring criteria disagreed. Do not restart λ tuning without a materially new, preregistered mechanism and independent validation.
4. **Untried geology:** the five current candidates, exact layers/signatures, planning priors/costs, official source/access checks, and falsifiable gates are in [docs/hypotheses.md](docs/hypotheses.md) and [the bounded novelty audit](docs/research/untried-hypotheses-review-2026-10-03.md). H-31-04's GeoDAWN lineage/schema audit is the lowest-cost next *new-hypothesis* action; H-31-03 needs full-ROI NHD/DEM coverage; H-32-04 needs an independent inventory such as OSTI 1148722 or GDR 616, not Qfaults alone.
5. **Scores and sources:** the public snapshot showed DARD 0.3195 and `wbg1` 0.2600; no row identifies a TIFF hash, so D2.8's score attribution remains unresolved. The official data page is login-gated; pinned owner mirrors are not organizer-authenticated. No credentials, login bypass, or automated DrivenData monitoring are used.
6. **Rules:** eligibility, the 5:00 p.m. ET vs 11:59 p.m. UTC deadline discrepancy, and entrant-approved AI disclosure need authorized sign-off or organizer clarification. See [official-rules review](docs/research/official-rules-review-2026-10-03.md) and IR-30-008/020.
7. **Experiment integrity:** report global and active scored-domain counts separately; equal global counts are not active-count matched. Preflight realized capacity before freezing budgets; enforce 300 m spacing where needed; do not treat catalogue/SGMC proxy scores as private competition scores.
8. **Status:** `scripts/build_status.py` regenerates `docs/status.json`; refresh the public leaderboard only through a permitted, dated manual route (no scraper). Record the final test/link audit, current branch PR, and merge outcome in [the cumulative review checklist](docs/research/review-checklist-2026-10-03.md) after each is actually verified.
