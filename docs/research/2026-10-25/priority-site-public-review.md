# Priority-site public registry refresh — metadata and provenance review

**Retrieved:** 2026-10-25T23:43:57Z

**Decision:** **NO NEW TIFF; NOT APPROVED FOR SUBMISSION.**

This is a source-registry synchronization and metadata inspection only. It is not a
model experiment, a holdout result, a leaderboard read, a submission, or a basis for
moving the duplicate-stopped TDX-C2 dots. The current decision remains the
machine-bound [TDX-C2 negative run card](../texture-controls/run-card.json): it
failed its matched-control gate and 79.090497% of its dots were within three pixels
of a registered G30-S19 raster (mandatory limit: 70%).

## What was verified from bytes

The shared tool [`scripts/sync_priority_registry.py`](../../../scripts/sync_priority_registry.py)
resolved each named repository's current `main` commit through the GitHub API, listed
all `docs/downloads/**/*.tif[f]` blobs at that immutable commit, then downloaded each
such TIFF through its immutable `ref`, Git-blob-SHA-1 checked it, SHA-256 checked the
local cached byte stream, and tested its GeoTIFF grid against the pinned sample
template. The complete machine-readable receipt is
[`priority-site-public-snapshot.json`](priority-site-public-snapshot.json).

This refresh does **not** certify a complete parallel registry: it covers only the
nine requested public repositories and only TIFFs published under `docs/downloads/`.
It has no organizer authentication, no private lanes, and no evidence that an
owner-reported score belongs to a particular TIFF.

| Requested site | Immutable `main` commit inspected | Published TIFF source blobs | Path-level continuous-surface candidates | What the count means |
|---|---|---:|---:|---|
| [GEMSDOE24](https://github.com/buffedlizard55-lab/GEMSDOE24/tree/fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1) | `fc2bc6f350bf5c6ce8da5d7a2ab03578ea1259d1` | 24 | 1 | Public `docs/downloads` TIFFs, not scores |
| [GEMSDOE25](https://github.com/buffedlizard55-lab/GEMSDOE25/tree/e40b9b5e3871cb34d138f586bde97f5099658d01) | `e40b9b5e3871cb34d138f586bde97f5099658d01` | 28 | 0 | Same scope |
| [GEMSDOE27](https://github.com/buffedlizard55-lab/GEMSDOE27/tree/cd6bdab32e82c4fd3bcf4ba15294cb11903e84eb) | `cd6bdab32e82c4fd3bcf4ba15294cb11903e84eb` | 29 | 0 | Same scope |
| [GEMSDOE28](https://github.com/buffedlizard55-lab/GEMSDOE28/tree/e6321461066f89080e3b1bb670d3951ab20d3638) | `e6321461066f89080e3b1bb670d3951ab20d3638` | 35 | 0 | Same scope |
| [GEMSDOE30](https://github.com/buffedlizard55-lab/GEMSDOE30/tree/3edad3641bcc3d72bd3cd05b77b719297617841c) | `3edad3641bcc3d72bd3cd05b77b719297617841c` | 18 | 0 | Same scope |
| [GEMSDOE31](https://github.com/buffedlizard55-lab/GEMSDOE31/tree/1ffc7ad5467a9860f7eb1554c5888d0bfd15db1e) | `1ffc7ad5467a9860f7eb1554c5888d0bfd15db1e` | 24 | 4 | Same scope |
| [GEMSDOE32](https://github.com/buffedlizard55-lab/GEMSDOE32/tree/5786b21a1674b26ee525e8e9bf048e2e0f50fc0e) | `5786b21a1674b26ee525e8e9bf048e2e0f50fc0e` | 35 | 0 | Same scope |
| [GEMSDOE33](https://github.com/buffedlizard55-lab/GEMSDOE33/tree/f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6) | `f618cc54773bd9b4d6c2b3ebf78103a05cc10cb6` | 8 | 0 | Same scope |
| [GEMSDOE36](https://github.com/buffedlizard55-lab/GEMSDOE36/tree/c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16f) | `c5a8ae7da3bd2fcff5aa5855afd44c7a3346c16f` | 4 | 0 | Same scope |
| **All nine** | nine pinned commits above | **205** | **5** | **190** distinct, aligned TIFF byte sequences; **1** deliberately excluded off-grid format-test file |

There were 14 source aliases among the 204 aligned source blobs. Byte aliases are
not independent submissions, geological hypotheses, or independent evidence.

## Surface discovery: a partial blocker reduction, not a comparison

To support the required *pre-placement* surface check in future work, the refresh
also searched only plausible binary-array paths (NPY/NPZ/Zarr) and names indicating
a prediction/surface/probability. It fetched and inspected **metadata only** for the
five hits. No values were ranked, correlated, included in a model, or used to alter
any candidate.

| Source | Public object | Metadata result | Status for a future surface comparison |
|---|---|---|---|
| GEMSDOE24 | `evidence/experiments/h24-2a-clipped-road-v1/prediction-4945c83d6f09.tif` | One float32 band, 3,730 × 3,292, EPSG:32611, grid matches the template | **Unknown**: provenance, leakage audit, lane permission and intended scale are not established |
| GEMSDOE31 | `evidence/h31_a/pilot/oof_residuals.npz` | Residual coordinate/value vectors, length 11,194; no template-shaped array | **Not a full surface**; **unknown** eligibility |
| GEMSDOE31 | `evidence/oof/oof_B_19_plus_lidar_u16.npz` | `probability_u16`, 3,730 × 3,292 | **Unknown** eligibility; exact scaling/provenance must be audited before use |
| GEMSDOE31 | `evidence/oof/oof_D_19_plus_lidar_radiometric_u16.npz` | `probability_u16`, 3,730 × 3,292 | **Unknown** eligibility; exact scaling/provenance must be audited before use |
| GEMSDOE31 | `evidence/oof_residuals.npz` | Residual coordinate/value vectors, length 60,988; no template-shaped array | **Not a full surface**; **unknown** eligibility |

The three template-shaped public artifacts reduce the *discovery* gap but do **not**
retroactively complete the registry for TDX-C2: TDX-C2 is already stopped, its own
continuous surface is quarantined, and the public objects do not establish all
parallel lanes. A future preregistration must freeze a separately authorized,
value-domain-validated surface registry **before** it emits dots.

## Why the historical H33 / B2 family may have appeared strong

The supplied statement that `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored
**0.2778** is an **OWNER-REPORTED, UNVERIFIED historical claim**. No submission-page
receipt, file hash/score pairing, or organizer record was available in this session;
it is neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED.

The prior byte-level forensic result remains reproducible and is the defensible
answer to “why might it work”:

1. GEMSDOE28's selected base contains 40,199 active pixels; H33/B2 contains
   37,654.
2. The H33/B2 support equals that GEMSDOE28 support after removing every active
   pixel at catalogue distance ≤2 pixels; the reconstruction has **zero support
   mismatches**. See the frozen
   [`recipe-reconstruction.json`](recipe-reconstruction.json) and the detailed
   [current review](../texture-controls/review.md).
3. Under the 300 m triangular max-credit metric, nearby dots do not add unlimited
   truth credit: a truth pixel takes the maximum kernel-weighted nearby prediction.
   Deleting a redundant catalogue-flank dot can therefore reduce false-positive
   mass while retaining most maximum credit. It can improve a distance-weighted
   Tversky score *if* saved penalty exceeds lost credit.
4. That is an **emission-pruning mechanism**, not evidence that B2 discovered a
   new fault-generating geological process. It can also remove genuine splays or
   extensions, and catalogue-derived holdouts are structurally unable to validate
   the desired off-catalogue target population.

Thus, it is scientifically plausible that B2's sparse placement helped a hidden
metric, but the supplied score attribution and any claim that a new method will
beat it remain unproven. In particular, re-encoding, copying, collar-pruning, or
slightly shifting B2 would not satisfy the requested unique-submission protocol.

## Frozen untried mechanisms: no new experiment in this stopped lane

The latest TDX-C2 preregistration already ranked three distinct mechanisms that
were **not executed** because the first fixed experiment hit the duplicate stop:

1. **Signed-lag run continuity** — magnetic anomaly/RTP and gravity-edge tangents;
   seek along-edge persistence of the *sign* of an offset. It targets covered
   through-going breaks beyond mapped ends. A curved intrusive contact or
   flight-line artefact is the principal mimic.
2. **Opposite-flank reciprocity** — the same magnetic/gravity layers; require
   forward/reverse profile offsets of equal magnitude and opposite sign. It seeks
   a buried structural displacement rather than one-way texture similarity. A
   repeated stratigraphic magnetic band is the principal mimic.
3. **Off-edge localization** — compare lag gain on a gravity edge with matched
   profiles displaced to either side. It targets a local buried break, not broad
   lithologic texture contrast. A magnetic source-depth transition is the
   principal mimic.

They remain **proposals**, not active experiments or candidate TIFFs. Their full
layer definitions, controls, canaries, costs, and required HOLDOUT-DTI gate are
frozen in [`../texture-controls/preregistration.md`](../texture-controls/preregistration.md).
They cannot be run until an external lane is assigned, a fresh untouched spatial
holdout is reserved, the current-best checkpoint is rerun under the same protocol,
and the surface registry is frozen before placement. The current two-hour/three-
experiment budget was not reopened.

## Tooling fix and reproducibility

The registry tool previously defaulted a refresh to a frozen historical registry
path. That could silently destroy the exact registry hash that binds an experiment's
novelty receipt. It now fails before network access unless a fresh snapshot receives
an explicit output outside the frozen TDX-1 and TDX-C2 registry paths. It also keeps
surface discovery narrow and, when requested, labels fetched surface metadata
**unknown** rather than treating it as a comparison-ready raster. Regression tests
cover both controls.

```bash
# Restore only a frozen historic registry; do not rewrite it.
.venv/bin/python scripts/sync_priority_registry.py --restore-only \
  --output docs/research/texture-controls/registry.json

# Make a new public-source snapshot. Use a new dated filename, never a frozen receipt.
.venv/bin/python scripts/sync_priority_registry.py \
  --template data/raw/sample_submission.tif \
  --output docs/research/registry-snapshots/priority-sites-YYYYMMDD.json \
  --inspect-surfaces
```

## Limits and next action

- The official DrivenData pages, organizer submission receipt, raw organizer data
  provenance, private expert labels, full parallel registry and assigned lane are
  unavailable here. The GitHub mirrors are public project evidence, not official
  competition confirmation.
- The local format validator checks an exact file; it cannot prove private portal
  acceptance. No current file is approved for upload.
- No score projection is made. Existing performance numbers remain in their run
  cards as **HOLDOUT-DTI** with their evaluator, withheld-positive count and 95% CI.

**Next non-submission action:** have a future lane preregister a specific physical
mechanism and an untouched spatial test, then audit the three public template-shaped
surfaces' value scaling and provenance before using any one in a pre-placement
registry. Do not rerun TDX-C2, manufacture a near-duplicate, or spend a competition
slot on a negative/unknown decision.
