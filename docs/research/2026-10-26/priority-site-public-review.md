# Priority-site public evidence refresh — 2026-10-26

**Decision:** no new experiment; no competition file approved; no slot selected.

## Public artifacts and score claims

The immutable machine inventory in [`priority-site-public-snapshot.json`](priority-site-public-snapshot.json) now covers current `main` commits from all nine requested owner repositories: **220** published TIFF blobs, **205** unique aligned byte sequences, and **1** deliberately excluded off-grid format-test TIFF. The inventory is public GitHub evidence only. It is not the full parallel-run registry, does not identify every original continuous surface, does not authenticate any organizer result, and cannot prove that a reported score belongs to the same bytes as a named raster.

The per-site highest recorded owner claims and newer lower claims are in [`site-score-summary.json`](site-score-summary.json), rendered as the [Pages site-score digest](../../site-summaries.html). The repository found **zero official submission-page receipts** tying those claims to exact files. Every value is therefore labelled **OWNER-REPORTED / UNVERIFIED**; none is `ORGANIZER-CONFIRMED`. The current task's newer score claims were added to `docs/score-ledger.csv` as user-supplied claims, not verified submissions.

## H33 and D2.8 lineage

The stored `GEMSDOE32` `H33/B2` claim is 0.2778, owner-reported and not receipt-confirmed. The pinned H33 raster has 37,654 positive pixels. [`recipe-reconstruction.json`](../2026-10-25/recipe-reconstruction.json) records a byte-level support reconstruction: it equals the GEMSDOE28 d=2.8 raster after deleting 2,545 pixels within 2 pixels (200 m) of catalogue labels, with zero pixel mismatches. The H33 duplicate audit records 100% of H33 dots within 3 pixels of GEMSDOE28 d=2.8 and GEMSDOE31 d=2.8, and also 100% of H33 dots near GEMSDOE36's Anderson-PINN raster; GEMSDOE33 H33D has 99.984% of H33 dots within 3 pixels.

This demonstrates a **spacing/pruning lineage**, not an independently established geological discovery. It does not prove the reported 0.2778 was returned for those exact bytes: there is no official receipt/hash-score binding. A distinct geological method could beat the claim in principle, but the repository contains no organizer-confirmed evidence that one has done so. Catalogue-proxy `HOLDOUT-DTI` values are not comparable with the owner claim.

The D2.8 attribution chain is also imperfect. A historically pinned GEMSDOE25 path yields the same D2.8 bytes/alias found under GEMSDOE24, while the current GEMSDOE25 main snapshot lists a newer H66 file rather than that old D2.8 path. The ledger further records an owner-page statement that a related D2.8 copy was unscored/not slot-approved. Preserve this uncertainty; do not claim a verified score-to-file lineage.

## Post-placement public TIFF check for the existing GEMSDOE30 MSDB-1v2 artifact

The existing MSDB-1v2 file (`SHA-256 22850984a68c393f60c6cc9aeafd8d74fd8a3479654bdfcfd3626a4b99ff0381`) was compared **after it had already been placed** against the other **204** unique aligned TIFFs in the 2026-10-26 nine-repository snapshot. The maximum observed full-footprint Spearman correlation was **0.063378**; the maximum directional fraction of candidate dots within 3 pixels was **0.647789** (64.78%), against a GEMSDOE28 H37-1 probe-union-pool raster. No duplicate threshold was crossed in this observed public TIFF set.

Machine receipt: [`msdb1-postsnapshot-dot-audit.json`](msdb1-postsnapshot-dot-audit.json). Its decision is deliberately **`blocked-incomplete-evidence`**, not a novelty pass: this check is post-placement, excludes the candidate's own byte-identical entry, covers only public published TIFFs, and cannot account for private parallel runs or missing continuous surfaces. The run's earlier pre-placement surface check covered a smaller registry; the present refresh did not compare the MSDB continuous surface because its exact surface artifact is unavailable. No retroactive pre-placement certificate is possible.

## Newly visible surface-path metadata

The current snapshot contains five path candidates: one GEMSDOE24 prediction-named float32 GeoTIFF on the competition grid and four GEMSDOE31 NPZ files, two of which contain template-shaped `uint16` probability arrays. Only metadata was inspected. No values were ranked, correlated, or used. Model provenance, leakage status, encoding, lane permission, and eligibility for a future pre-placement registry remain **unknown**. See the machine receipt for exact paths and blockers.

## Site-by-site immutable source inventory

| Site | Current-main commit | Published TIFF blobs | Candidate surface paths |
|---|---|---:|---:|
| GEMSDOE24 | `fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1` | 24 | 1 |
| GEMSDOE25 | `0a45b3ca6403f7e8d4deac5d8b208797d5e8f477` | 32 | 0 |
| GEMSDOE27 | `927322eadbde56be42ae129ccdfb9b37540d8e60` | 29 | 0 |
| GEMSDOE28 | `10c26af3dc4d45292189734b0b696c7afb24ffb1` | 35 | 0 |
| GEMSDOE30 | `c6d5710324ee31b82fcf8489b9f65d070da9eaf8` | 19 | 0 |
| GEMSDOE31 | `1aebc0b80570406b9eca6c56eed915b8d064e3b2` | 30 | 4 |
| GEMSDOE32 | `7a97c5a88936a3fdb99d0358c3b85d739a714631` | 37 | 0 |
| GEMSDOE33 | `b542e5ce4186b54dbd07a6a6e8756be676a3f088` | 10 | 0 |
| GEMSDOE36 | `d519364018a2b9ce864565beb9080e32227e7a36` | 4 | 0 |

## Scope limits

- The owner sites are not organizer sources. Public GitHub artifacts, owner pages, and user-supplied numbers do not establish portal acceptance.
- The full parallel registry, assigned lane, private sessions, and most original continuous surfaces are not available.
- All local TIFF format checks are local checks only; they are never described as organizer acceptance.
- Candidate generation is not authorized by this inventory. Do not run another experiment or select a competition slot until the lane and registry constraints are resolved.
