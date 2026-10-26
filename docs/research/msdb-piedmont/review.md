# MSDB-1v2 research review — status updated 2026-10-26

## Decision: research download only; NOT APPROVED for contest upload

The existing MSDB-1v2 TIFF is linked for reproducibility, **not as an approved contest submission**. Its local validation does not demonstrate portal acceptance. The research verdict is negative, `submission_approved=false`, no competition slot has been selected or used, and no experiment was run in this 2026-10-26 review.

The externally assigned single-method lane is still missing and must not be invented. The complete parallel-run registry is unresolved. Do not run another experiment or choose a slot until these constraints are resolved. Promotion and actual slot selection are separate decisions.

- **Research TIFF (downloadable; NOT upload-approved):** [`docs/downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif`](../../downloads/gems30-MSDB1-edge44090-20261025-e7856ec3f14a.tif)
- **SHA-256:** `22850984a68c393f60c6cc9aeafd8d74fd8a3479654bdfcfd3626a4b99ff0381`
- **Machine receipts:** [run card](run-card.json) · [readiness](readiness.json) · [pooled/fold results and canaries](results.json) · [local reopened-file validation](validation.json) · [frozen preregistration](preregistration.md)
- **Pages:** [explicit contest submission process](../../../submission-process.html) · [nine-site owner-claim digest](../../../site-summaries.html)

## 1. Existing HOLDOUT-DTI evidence

All values below are catalogue-recovery proxy measurements from evaluator `component-holdout-v3-blockstats-20261025`, using `60,988` withheld positives, buffered whole-component folds, and `2,000` paired geographic-block bootstrap draws. They are **not organizer scores, leaderboard results, or projections**.

| Existing arm / contrast | HOLDOUT-DTI or paired difference | 95% CI | Interpretation |
|---|---:|---:|---|
| `msdb_edge` | `0.170462` | `[0.156227, 0.184168]` | Existing candidate arm |
| `core19` | `0.133628` | `[0.118285, 0.148875]` | Preregistered comparator |
| `msdb_edge − core19` | `+0.036834` | `[+0.022322, +0.050315]` | Positive in all four held-out quadrants |
| `msdb_poisson` | `0.169326` | `[0.154797, 0.183273]` | Existing matched-count placement arm |
| `msdb_edge − msdb_poisson` | `+0.001135` | `[−0.002173, +0.004628]` | **Inconclusive; CI crosses zero. Not equivalence evidence and not a promotion gate.** |
| `msdb_poisson − core19` | `+0.035698` | `[+0.021622, +0.048841]` | Existing representation-ablation contrast; do not infer a contest score |

The readiness gate for paired improvement is against `core19`; it does not test whether `msdb_edge` outperforms `msdb_poisson`. The matched comparison must remain visibly inconclusive in release materials and must not be used as an added promotion gate. No equivalence conclusion follows from an interval that crosses zero.

The existing feature canaries tested 37 features across four folds (148 checks): no AUC exceeded the `0.90` leakage alarm; the maximum recorded univariate AUC was `0.6419`. This is a result for the existing run only, not a waiver of canaries for a new method.

## 2. Current machine gates and novelty limits

- **Local file checks:** the reopened TIFF passed the expected one-band `float32`, EPSG:32611, `3,730 × 3,292`, in-footprint finite `[0,1]`, outside-footprint null, and known-catalogue exclusion checks. These are local format/content checks, not portal validation or acceptance.
- **Recorded run readiness:** nine gates passed and three remain unknown; the overall research verdict is negative and the file is not approved. In particular, lane assignment and complete parallel-session registry are unresolved.
- **Earlier observed registry:** the original experiment receipt reports a limited 165-unique-raster audit. A measured result against that observed set cannot certify global novelty.
- **Post-placement public check:** [`msdb1-postsnapshot-dot-audit.json`](../2026-10-26/msdb1-postsnapshot-dot-audit.json) compares the placed TIFF with 204 non-self aligned public TIFFs. Maximum observed full-footprint Spearman correlation is `0.063378`; maximum directional fraction of candidate dots within 3 pixels is `0.647789` (64.78%), below the 70% duplicate stop. Its authoritative decision is **`blocked-incomplete-evidence`** because the registry is incomplete. The exact MSDB continuous surface was unavailable for this refresh, so the post-snapshot receipt is a dot-only check, not a surface check.
- **What follows:** there is no full-registry or global novelty certificate. For any future candidate, check surface rank-correlation and final dots both before and after placement. Stop and log a duplicate if surface Spearman exceeds `0.90` or more than `70%` of dots are within 3 px of a registered raster.

## 3. GEMSDOE32 H33 and whether a distinct method can beat it

The score ledger records GEMSDOE32 H33/B2 at `0.2778`, **OWNER-REPORTED / UNVERIFIED**. No official submission-page receipt tying that score to a particular TIFF hash was found, so the number is not `ORGANIZER-CONFIRMED` and its score-to-file lineage remains unverified.

The pinned H33 raster has 37,654 positive pixels. The byte-level [`recipe-reconstruction.json`](../2026-10-25/recipe-reconstruction.json) shows that its support is exactly reconstructed from GEMSDOE28 solo d=2.8 (40,199 pixels) by removing the 2,545 pixels within 2 pixels (200 m) of catalogue labels; the reconstruction has zero pixel mismatches. This is evidence of a spacing/pruning lineage, not an independently established geological discovery. The historical H33 audit also reports near-identical support among related GEMSDOE28, GEMSDOE31, GEMSDOE33, and GEMSDOE36 artifacts; see [`h33-historical-duplicate-audit.json`](../h33-historical-duplicate-audit.json).

A genuinely distinct geological method **could** beat the owner-claimed `0.2778` in principle. The repository has no organizer-confirmed result demonstrating that it has. MSDB-1v2's `HOLDOUT-DTI` is a separate catalogue-proxy metric and cannot be compared numerically with the owner-reported contest claim. Re-encoding, thinning, renaming, or slightly shifting H33-like support is not evidence of a distinct method.

The historical D2.8 attribution is also uncertain: a pinned GEMSDOE25 path is byte-aliased under GEMSDOE24, the inspected current GEMSDOE25 snapshot no longer lists that older path, and an owner-page note calls a related file unscored/not slot-approved. Preserve this caveat; do not infer an authenticated score-to-file association from repository paths or filenames.

## 4. Nine requested sites: highest recorded claims

The [Pages score digest](../../../site-summaries.html) and [machine-readable summary](../2026-10-26/site-score-summary.json) give the pinned artifact URL/hash, submission name, newer lower claims where supplied, per-site notes, and attribution caveats. All values in the following table are **OWNER-REPORTED / UNVERIFIED**; none is organizer-confirmed in this review.

| Site | Highest recorded owner claim | Site | Highest recorded owner claim | Site | Highest recorded owner claim |
|---|---:|---|---:|---|---:|
| GEMSDOE24 | `0.2477` | GEMSDOE25 | `0.2600` | GEMSDOE27 | `0.2449` |
| GEMSDOE28 | `0.2710` | GEMSDOE30 | `0.2600` | GEMSDOE31 | `0.2708` |
| GEMSDOE32 | `0.2778` | GEMSDOE33 | `0.2632` | GEMSDOE36 | `0.2750` |

Five newer lower claims were supplied with this review and added to the score ledger as user reports, not receipts: GEMSDOE24 `0.0859`, GEMSDOE25 `0.0742`, GEMSDOE27 `0.2190`, GEMSDOE28 `0.0217`, and GEMSDOE30 `0.1462`. Their scores are unverified even where the pinned public artifact hash is independently available.

No number in this table is HOLDOUT-DTI. Do not merge these owner claims with the MSDB holdout table above.

## 5. Ranked untried hypotheses and source availability

A code, research-artifact, and immutable public nine-site artifact screen was completed before listing these hypotheses. The exact proposed mechanisms are not recorded as executed in the reviewed evidence; this is **not global uniqueness certification**. Full mechanisms, non-fault mimics, nulls, holdout plans, exclusions, and official-source notes are in [`untried-hypotheses.md`](../2026-10-26/untried-hypotheses.md).

1. **SGMC cover-observability prior × independent structural evidence.** USGS publishes state geology/map-unit packages; the original polygons needed for this test are absent locally. The derived SGMC fault raster is not a substitute. Restore and checksum polygons before preregistration.
2. **Lithology-conditioned GeoDAWN K/Th log-ratio residual × fixed along-strike persistence.** USGS GeoDAWN is a public-domain source. The locally restored four-band rasters are owner-derived quantized products, not the raw USGS grids; obtain raw official measurements or quantization metadata before interpreting ratios. RadTC-Fan's TC/elevation feature is already in MSDB-1v2 and is explicitly excluded from the proposed method.
3. **USGS drainage χ disequilibrium and channel steepness (`ksn`) aligned with independent structure.** Public NHD/3DEP endpoints exist. A prior query found NHD products for a test bounding box, not complete study-footprint coverage; the required complete aligned data are not present.

Overlap exclusions: do not relabel `RadTC-Fan` (already in MSDB-1v2), `MT-HF-Saddle` (overlaps heat-flow/conductivity/clay-cap/strain work), or `WL-Strain` (overlaps GEMSDOE27 strain/conductivity) as untried. IHFC heat flow is a possible public source but its in-footprint availability was not checked and the method family overlaps existing work. No shortlist candidate was run or validated.

## 6. Read-first protocol and contest submission process

Before any future experiment, obtain the externally assigned single-method lane and reconcile the complete parallel registry, including continuous surfaces. Then freeze a pre-placement registry, use cached template features and the shared evaluator/writer, hold out whole fault segments with a buffer, derive catalogue-based features from visible faults only, mask visible pixels exactly, and score pooled DTI with alpha `0.2`, beta `0.8`, and a 300 m triangular kernel. Use single-feature leakage canaries; AUC `>0.90` is a leakage alarm until explained. Fix defects in the shared tool, not a private fork.

Respect the active ceiling of three experiments or two hours; neither allowance resets in this review. Do not select or use a competition slot. Check surface and dot novelty both before and after placement, stopping at Spearman `>0.90` or more than `70%` of dots within 3 px of any registered raster. A local holdout win, local TIFF pass, public download, or owner-site score is not organizer approval.

The [submission-process page](../../../submission-process.html) links the official DrivenData problem page and NLR rules and distinguishes a research download from an upload-approved artifact. Confirm live deadlines, eligibility, permitted data, weekly limits, and portal instructions at the official sources before any later authorized submission. This repository review did not refresh the live leaderboard or inspect the private submission page. An organizer receipt tied to exact file bytes is required before any score is labelled `ORGANIZER-CONFIRMED`.

## 7. Historical experiment details and source records

The existing experiment and its historical scientific details remain in the dated [2026-10-25 priority-site review](../2026-10-25/review.md), [run card](run-card.json), [results receipt](results.json), and [preregistration](preregistration.md). The [`data-source-check.md`](../2026-10-26/data-source-check.md) records official source links and the exact availability limits used for this update.

---

**Run-card alignment:** this document records a negative review decision, no new experiment, no slot selection, no organizer-confirmed site score, and no upload approval. The matched `msdb_edge − msdb_poisson` comparison is inconclusive and is not a promotion gate.
