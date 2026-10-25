# Lane G30-S20 — why H33 scored 0.2778, and a replicated better belief that is *not* dot-unique

**Session:** 2026-10-25, branch `arena/15a1706d-gemsdoe30`, lane **G30-S20**
(discovery-channel habitat: 19-band derivatives + 1 m-DEM lidar scarp
morphology + GeoDAWN radiometrics, EDGE emission; oriented line coherence
tested and rejected). **Every number below is labelled HOLDOUT-DTI**
(evaluator `component-holdout-v2-footprint-20261025`, pooled DTI, α=0.2,
β=0.8, 300 m triangular kernel), **OWNER-REPORTED** (prompt, no organizer
receipt), or an **official snapshot** fetched this session. Nothing is
ORGANIZER-CONFIRMED and no projection is written as a score.

## Verdict first

| Question | Answer |
|---|---|
| Was a new unique-named TIF generated? | **Yes** — `gemsdoe30-g30s20-disc-60000dots-20261025T224159Z-24de17a6fa-zeros.tif`, SHA-256 `1b07820d…299cd6`, 60,000 dots, format-validated (below). |
| Is it OK to **download**? | **Yes** (education / selector review). |
| Is it OK to **submit as a new unique submission**? | **❌ NO — duplicate-stop.** 89.58 % of its dots fall within 3 px of the unsubmitted G30-S19 Candidate C's dots, breaching the frozen 70 % parallel-lane novelty gate. Candidate C remains this project's only “OK to submit” file. Do not submit S20 *as an additional unique entry*, and never submit both as separate discoveries. |
| Did the science work? | **Yes.** The S20 belief beat the exact Candidate-C recipe head-to-head on two independent component holdouts (+0.0066 and +0.0126 HOLDOUT-DTI, paired bootstrap CIs excluding 0). S20 is Candidate C's validated *successor*, not an independent lane. If the owner-as-selector wishes to retire C in favour of S20 as a **single-file replacement**, that is their allocation decision to make explicitly (see §5); this lane cannot certify it as unique, and no slot was used here. |

## 1. Why and how did `h33-h33-2-b2-…-zeros` reach 0.2778 (OWNER-REPORTED)?

**What the file is (measured, prior session, re-verified pins this session).**
The GEMSDOE32 winner's 37,654-dot support is *exactly* GEMSDOE28's
solo-d2.8 support (40,199 dots) with every dot at catalogue distance
≤2 px (≤200 m) deleted — zero mismatching pixels
(`docs/research/2026-10-25/recipe-reconstruction.json`; registry pins for
all nine focus sites re-restored and SHA-verified this session). The whole
high-scoring focus family is one belief surface (`H19-5`) refined by
emission only: 0.1922 → d1.5 Poisson thinning 0.2477 → d2.8 thinning
0.2600–0.2710 → >2 px flank prune 0.2778, with the GEMSDOE36
“Anderson/geothermal PINN” (0.2750) at Spearman 0.984 and 100 % of H33 dots
within 3 px (all scores OWNER-REPORTED; correlations measured locally).

**Why pruning helps this metric (algebra, official definitions).** With
`DTI = TPw / (TPw + 0.2·FPw + 0.8·FNw)` and `FNw = G − TPw`, the denominator
is `0.2·TPw + 0.2·FPw + 0.8·G`. TP credit for a truth pixel is the **max**
of `p(x)·k(d)` over predictions within 300 m, so a second dot next to an
existing one adds ≈0 TP but up to a full unit of FP mass; and known
USGS/INGENIOUS pixels are masked out of scoring, so dots hugging catalogue
traces are nearly pure waste. Deleting 6.3 % of dots (the catalogue-flank
ones) therefore cuts FPw while barely touching TPw. Thinning (d1.5→d2.8)
does the same to dot-crowding redundancy. **H33 is an emission-efficiency
result, not a geological discovery result.** Three consequences follow:

1. Further pruning of this family is exhausted *and* is a duplicate by
   construction (Spearman 0.968 / 100 % ≤3 px vs its parent).
2. The blanket ≤2 px prune also deletes genuine short splays/extensions —
   which the organizer explicitly counts as “new” faults — so it is a
   leaderboard trade-off, not a free win.
3. Beating 0.2778 requires raising **coverage per FP unit** with a better
   belief surface. From `c = s·(0.2f + 0.8)/(1 − 0.2s)` (c = TPw/G,
   f = FPw/G; pure algebra): at s = 0.4413 (the live leader, official
   snapshot 2026-10-25) with f = 2 you already need c ≈ 0.58; with f = 5,
   c ≈ 0.87. The leaders are not winning by emission tricks — their
   beliefs are fundamentally more precise. (The prompt's “0.3195 highest”
   was the verified leader on 2026-10-03; fetched today, #1 is **0.4413**,
   #2 0.3916, #3 0.3904.)

**Can we beat 0.2778?** Nobody can know locally — the hidden expert-labelled
faults are not the catalogue, the public score is only a spatial chunk of
the test region, and the final prize re-scores against an *expanded* label
set built partly from submissions themselves (official problem page). The
strongest legitimate local evidence is a preregistered, leakage-checked,
replicated head-to-head win over the best existing recipe on identical
hide-and-recover folds. That is what S20 set out to produce — and did.

## 2. What S20 tested (frozen before any result)

Five ranked hypotheses are in [hypotheses.md](hypotheses.md); the lane is
Rank 1. Full frozen design: [preregistration.md](preregistration.md).
In one line: **does adding (a) sub-100 m scarp morphology from 1 m DEMs
(USGS 3DEP-derived 12-band stack: slope-excess, step, crest/base Laplacian
dipole `√(lapneg·lappos)`, `step×coherence`, circular strike) and
(b) GeoDAWN radiometrics (K/Th/U/TC, Th/K, U/K, U/Th, TMI↑150 m + two
gradient magnitudes) to the G30-S19 habitat GBM — with no catalogue-distance
inputs ever — recover withheld whole fault components better than the
identical GBM without them; and does a fixed oriented line-coherence
reweighting (`√(B·Lmax)`, 16 orientations × 900 m) help further?**
Named non-fault mimic: fluvial terrace risers / Lahontan paleo-shoreline
scarps + lithologic radiometric contacts. Preflight verified band order,
grid and SHA pins ([preflight.json](preflight.json)): lidar covers
75.37 % of the footprint, radiometrics 99.975 %.

**Leakage canaries (before any training):** all 69 features clean on both
seeds (max non-distance AUC: `lid_upface_max` 0.5808 seed 31 — the strongest
single feature in the combined stack; distance features reach 0.76–0.77
but are excluded from every model). No AUC >0.90 or <0.10
([seed 31](canaries-seed31.json), [seed 47](canaries-seed47.json)).

## 3. Results — HOLDOUT-DTI, matched 60,000 dots (primary endpoint)

| Arm | Seed 31 (20,870 withheld) | Seed 47 (20,364 withheld) |
|---|---:|---:|
| A — habitat only (= Candidate C recipe) | 0.22304 [0.20517, 0.23959] | 0.22444 [0.20594, 0.24320] |
| **B — + lidar scarp + radiometrics** | **0.22960 [0.21025, 0.24536]** | **0.23707 [0.21808, 0.25652]** |
| C — B + line coherence | 0.22518 | 0.23329 |
| D — A + line coherence (diagnostic) | 0.21933 | 0.22225 |
| **Δ (B − A), paired** | **+0.00655 [0.00067, 0.01245]** | **+0.01263 [0.00616, 0.01990]** |

CIs: 500-resample bootstrap over the 1,085 hidden components, FP mass held
fixed (conditional CI). Receipts: [seed 31](holdout-seed31.json),
[seed 47](holdout-seed47.json). Secondary endpoint (EDGE self-stop) agrees
in sign on both seeds (B: 0.22878 / 0.23618 vs A: 0.22273 / 0.22437). At 60 k dots on seed 31, B
gains +191.8 TP weight while *reducing* FP weight by 158.4 — the new
channels both find more withheld fault and suppress look-alikes, which is
the discovery-channel mechanism working as hypothesised (terrace/shoreline
and contact mimics are partly *separable* once scarp morphology and
radiometric composition must agree with the geophysical habitat).

**Two verification anchors.** (i) Arm A **reproduces the prior session's
S19 result to every recorded digit** (62,779 self-stop dots, DTI
0.22272559591471125, identical TP/FP weights) through an independently
written sampling/gathering path — the comparator is the real Candidate-C
recipe, not a weakened copy. (ii) The suspicious-looking identity of the
bootstrap component count (1,085 on both seeds) is *expected*: the split
hides `floor(n/2)` components per 3.2 km tile, so the hidden-component
count is seed-invariant even though the hidden pixels differ
(20,870 vs 20,364). Checked in `split_components` source, Pass 2.

**Line coherence: negative sub-result (a deliverable).** The frozen
900 m line-mean reweighting *hurt* both beliefs on seed 31 (B: −0.0044,
A: −0.0037) and again left C below B on seed 47. Interpretation: the GBM's
derivative/local-std/structure-tensor features plus EDGE's own
redundancy-aware greedy placement already extract the available local
coherence; a further 900 m geometric-mean smoothing mainly demotes short
genuine segments and fault tips. `line_coherent_belief` remains in
`src/gemsdoe30/fields.py` (unit-tested) for future lanes, unused by the
candidate.

**Gate audit vs the frozen preregistration:** E1 Δ ≥ +0.005 ✔ (+0.00655);
E2 replication Δ > 0 ✔ (+0.01263); canaries ✔ (69/69, both seeds);
validator ✔ (below); **novelty ✘** (§4). One failed gate ⇒ verdict
**negative (duplicate-stop)**, however good the science is.

## 4. Novelty — passed everywhere except against its own predecessor

Continuous belief surface before placement: max Spearman vs any registry
raster **0.158** (gate 0.90) ✔. Final dots: vs the nine pinned
priority-site winners, max ≤3 px overlap **44.9 %** (GEMSDOE24 family),
vs the 0.2778 H33 winner **36.8 %** (ρ = 0.030) ✔; vs every other local
download ≤ 64.8 % ✔ — **except Candidate C: 89.58 % within 3 px**
(dot ρ = 0.215; exact same-pixel overlap only 22.4 %; median
nearest-neighbour distance 1 px; symmetric C-within-3 px-of-S20 = 90.6 %).
Receipts: [novelty.json](novelty.json),
[independent-reread.json](independent-reread.json).

This is exactly what “successor, not sibling” looks like: two EDGE
emissions along the same fault ridges interleave dots within the 300 m
metric kernel even when only a fifth land on the same pixel. The frozen
rule does not distinguish “copied another site's scored submission” from
“improved yesterday's unsubmitted candidate”, and this lane will not
re-interpret it after seeing the number. Logged as duplicate-stop.

## 5. The generated TIF and exactly how a submission decision works

- **S20 file (DO NOT SUBMIT as unique):**
  `gemsdoe30-g30s20-disc-60000dots-20261025T224159Z-24de17a6fa-zeros.tif`
  (SHA-256 `1b07820d0066e56442ade4f4a3880af92f50b4ca9cac528ccf59696ec5299cd6`;
  NaN twin `12bd6196…9b22`, identical inside the footprint).
  Note (66 chars): `G30-S20 19-band+lidar scarp+GeoDAWN rad GBM + EDGE 60k off-cat>2px`.
- **Validator (shared writer + independent re-read):** single-band
  float32, EPSG:32611, 3730×3292, transform
  `(100, 0, 243350, 0, −100, 4508550)`; values exactly {0, 1};
  zeros-twin: **all 12,279,160 cells finite in [0, 1]** (the historical
  portal range error cannot be triggered by its values); NaN-twin:
  0 NaN inside the footprint, NaN outside (published format);
  60,000 dots, **0 on the catalogue, 0 within 2 px**, median dot distance
  to catalogue 5 px, 21.7 % of dots >1 km from any catalogue trace.
  Receipts: `format-checks/*.json`, sidecar JSONs in `docs/downloads/`.
- **If the owner submits Candidate C (current recommendation):** follow
  [executive-summary.html](../../../executive-summary.html) — download the
  `-zeros` file named there, DrivenData → New submission → choose file →
  paste its note → save the organizer receipt next to its run card.
- **Selector option the owner may take explicitly (not made here):**
  retire Candidate C and submit S20 *instead* as a single-file replacement.
  Justification on record: replicated head-to-head superiority on identical
  folds, and S20 *is* dot-unique against every actually-scored registry
  raster (Candidate C itself has never been uploaded — no slot used, no
  organizer score). Cost of that choice: S20 must never be described as
  an independent/unique discovery relative to C, and submitting both
  across weeks would waste slots on near-identical coverage. Whichever
  file is uploaded, record its SHA-256 + receipt; only then does any
  number become ORGANIZER-CONFIRMED.

## 6. Irregularities flagged for owner review

- **IR-S20-01 — Lane self-assigned.** The prompt's “single method
  paragraph” is again not identifiable in the received text; Lane G30-S20
  was self-assigned and frozen in the preregistration before experiments.
- **IR-S20-02 — Owner-mirror data.** Training rasters and the two external
  stacks are hash-pinned owner mirrors (official origins: DrivenData
  competition files; USGS 3DEP; USGS GeoDAWN DOI 10.5066/P93LGLVQ, marked
  CC0 on the official USGS page fetched this session). Hashes prove
  consistency, not organizer authentication or redistribution rights.
  Replace with the owner's authorized DrivenData download before upload.
- **IR-S20-03 — Requested filenames absent.** `evaluate_holdout.py` /
  `submission_writer.py` / “template's cached feature stack” do not exist
  under those names; the shared repo equivalents
  (`src/gemsdoe30/{holdout,submission,emitter_opt,fields}.py`,
  `scripts/lane_g30s19.py` stack builder) were reused, no private fork.
- **IR-S20-04 — Template contradicts the problem page (re-verified).**
  `sample_submission.tif` is described officially as predicting “total
  fault absence”, but measured this session its in-footprint values are
  *identical to the labels* (60,988 ones, 5,167,373/5,167,373 agreement).
  Only its footprint/grid was used; its values are never a feature or a
  prediction anywhere in this lane.
- **IR-S20-05 — Duplicate-stop against an unsubmitted predecessor.**
  Whether Candidate C belongs in “the registry” is a governance question
  the frozen gate answered conservatively (yes). If the owner rules that
  only scored/parallel-lane rasters count, S20 passes novelty against all
  of them; the verdict would flip on that ruling alone. Recorded, not
  self-granted.
- **IR-S20-06 — Surface-stage novelty timing.** The surface-stage
  statistic was computed on the frozen pre-emission belief after E3
  production (belief saved before EDGE), not as a hard stop before E3's
  emission; nothing was tuned after seeing novelty (E3 runs regardless
  for the education file, per the owner's unique-TIF requirement).
- **IR-S20-07 — Holdout remains a biased proxy.** Stand-in “new faults”
  are catalogue components; the organizer scores expert-labelled
  off-catalogue faults and masks catalogue pixels. Lidar/radiometric
  channels could be over- *or* under-valued by this frame (catalogue
  faults were themselves partly mapped from topography/geophysics;
  expert new faults are plausibly scarp-enriched). HOLDOUT-DTI superiority
  is necessary, not sufficient. Antidote available to the owner: one
  feedback-slot upload with the receipt recorded.
- **IR-S20-08 — No lidar-vs-radiometric ablation.** The 3-experiment
  budget was spent on E1/E2/E3; canary AUCs (lidar singles 0.55–0.58 vs
  radiometric singles 0.43–0.55) *suggest* lidar carries more of the gain,
  but that is not an ablation and is not claimed as attribution.

## 7. Verification log (line by line)

| Claim | Check | Receipt / source |
|---|---|---|
| Metric α=0.2 β=0.8 R=300 m; format EPSG:32611/100 m/float32/[0,1], null outside; experts labelled hidden faults; chunked public/private; final-round expanded labels | Read official problem page in full this session | <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> |
| Live leader 0.4413; 0.3195 stale | Fetched official leaderboard this session; 2026-10-03 snapshot in ledger | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> |
| GeoDAWN origin + CC0; GDR 1391 INGENIOUS + CC BY 4.0 | Fetched official USGS / GDR pages this session | <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and> · <https://gdr.openei.org/submissions/1391> |
| Training/external bytes = pins | SHA-256 at restore; `prepare_data.py` reproduced dataset signature `291d3467…` | [preflight.json](preflight.json), `data/processed/manifest.json` (worktree) |
| H33 = pruned GEMSDOE28 support | Prior byte reconstruction; registry re-restored + re-hashed this session | `docs/research/2026-10-25/recipe-reconstruction.json`, `docs/research/priority-site-pins.json` |
| Canaries 69/69 clean ×2 seeds | Computed before training | [canaries-seed31.json](canaries-seed31.json), [canaries-seed47.json](canaries-seed47.json) |
| Holdout Δ = +0.00655 / +0.01263 | Shared evaluator, paired sample, component bootstrap | [holdout-seed31.json](holdout-seed31.json), [holdout-seed47.json](holdout-seed47.json) |
| Arm A = Candidate-C recipe | Exact reproduction of S19's recorded DTI/TP/FP/dots | This file §3; `docs/research/2026-10-25/lane-g30s19-holdout.json` |
| File contract + hashes | Shared validator (both encodings) + independent rasterio re-read + sidecar hash match | `format-checks/`, [independent-reread.json](independent-reread.json) |
| Novelty numbers | Shared `gemsdoe30.novelty.compare` on surface + dots, 24 references | [novelty.json](novelty.json) |
| Tests | `.venv/bin/python -m pytest -q` | **137 passed, 5 skipped** (torch absent) this session |

**Reproduce:** `python3 -m venv .venv && .venv/bin/pip install numpy scipy
scikit-learn rasterio pytest shapely pyproj && .venv/bin/python
scripts/restore_public_mirrors.py && .venv/bin/python
scripts/restore_public_mirrors.py --pins <filtered extra pins> &&
.venv/bin/python scripts/prepare_data.py && .venv/bin/python
scripts/lane_g30s20.py preflight|canary --seed 31|holdout --seed 31|canary
--seed 47|holdout --seed 47 --focus B_combined|final --recipe
B_combined|novelty` (CPU-only; ~45 min total on 2 cores; ~8 GB of
git-ignored work arrays).

## 8. Limitations and next steps (in order)

1. **Governance ruling needed (owner):** does the novelty registry include
   unsubmitted same-project candidates? The answer decides S20-vs-C as the
   single feedback/final file (IR-S20-05).
2. **One organizer receipt** (owner's account, official training files):
   the only way to convert any HOLDOUT-DTI claim into evidence about the
   hidden test and to settle portal NaN-outside behaviour. Costs a weekly
   slot; not spent here.
3. **Lidar-only vs radiometric-only ablation** under a fresh
   preregistration (was IR-S20-08) — cheap now that stacks are cached;
   would tell the next lane where to invest.
4. **Patch-CNN belief (organizer's reference-solution family)** remains
   the largest unexplored gap to the 0.39–0.44 leaders; needs GPU time
   this sandbox does not have. The S20 feature stack (especially the
   lidar dipole/step channels) is ready to serve as CNN inputs.
5. **Complete parallel registry**: novelty was certified only against
   9 pinned + 15 local rasters; other sessions' *surfaces* remain
   unavailable (surface stage used registry dots as reference).

*Budget used: 3 experiments (E1, E2, E3) as preregistered. Negative
sub-results recorded: line coherence (both seeds), S20 uniqueness vs
Candidate C. No submission slot used; nothing uploaded.*

## Post-merge addendum (PR #29 conflict resolution, 2026-10-25 late)

Between this lane's branch point and its PR, a concurrent session merged
PR #28 (TDX-1 gravity-normal magnetic texture-lag lane — an implementation
of this document's deferred hypothesis 2) with a generated research-site
builder (`scripts/build_research_site.py`) that renders `index.html` /
`executive-summary.html` from `docs/current-run.json` and is test-locked to
exactly one (negative) artifact download. Merge resolution therefore kept
main's generated landing pages un-forked: the S20 verdict block added by
this lane's session commit remains in that commit's history, while on
merged `main` the S20 verdict is published in the README's "Parallel lane
addendum", in `run-card.json`, and in the regenerated `docs/status.json`
(`lane_g30s20_run_card`); the landing fronts TDX-1's do-not-submit
decision. The S20 verdict itself is unchanged. A post-merge cross-lane
novelty check (both lanes ran blind to each other) found 32.7 % of S20 dots
within 3 px of TDX-1 dots — no cross-lane duplication
([`novelty-cross-lane-tdx1.json`](novelty-cross-lane-tdx1.json)). TDX-1's
own negative (HOLDOUT-DTI 0.07284 vs core19 0.13982, evaluator
`component-holdout-v3-blockstats-20261025`) also closes deferred
hypothesis 2 as a standalone belief: the texture-lag signal exists but was
far weaker than the 19-band habitat.
