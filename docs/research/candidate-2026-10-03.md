# Candidate file build record — 2026-10-03 (un-promoted research artifact)

**File:** `docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13.tif`
**SHA-256:** `f5d137b9c010873f0b4fc11e841d923f359d33c7272ded0da9ac9b7c1efc7cc2`
**Manifest:** `docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13.json`
**Status:** format-validated locally (11/11 checks); **not holdout-promoted**; no competition score
claimed; no submission slot used or recommended.

## What it is

A full-grid binary emission built from the metric-emission experiment's four out-of-fold surfaces.
Each fold's surface was produced by a HistGradientBoosting classifier fit on the *other three*
spatial quadrants (300 m training-exclusion buffer) over the competition bands plus the local
external layers; the OOF grid therefore has every pixel predicted by a model that never saw its
quadrant (coverage gaps: 0 of 5,167,373 valid pixels).

Emission rule: adaptive Poisson-disk thinning (exclusion radius 5 px shrinking with confidence,
gamma = 1.0, floor 0.25) over the top 480,000 candidate pixels — the rule the experimental protocol
selected in **4/4 leave-one-fold-out folds** within its family.

| Property | Value |
| --- | ---: |
| Emitted dots | 90,358 |
| Emitted share of the valid footprint | 1.75 % |
| Nearest-neighbour spacing (p10 / median / p90) | 2.00 / 2.83 / 3.16 px = 200 / 283 / 316 m |
| Dots within 300 m of a catalogue fault | 17.7 % (base rate 8.6 % → 2.1× enrichment) |
| In-footprint values | {0.0, 1.0}, all finite |
| Outside-footprint values | NaN (7,111,787 cells) |
| CRS / grid | EPSG:32611, 100 m, 3730×3292, template transform preserved |

## Why it is not promoted

The preregistered metric-emission gate (see
[`metric-emission-holdout-results.md`](metric-emission-holdout-results.md)) requires an absolute
pooled cross-validated proxy gain of **≥ 0.005** over *both* the dense and uniform baselines. The
adaptive family's margin over uniform is **+0.0025** (0.18927 vs 0.18675), below the gate, and the
paired boundary-loss line failed its fresh-seed confirmation (ΔDTI +0.0001, 2/4 folds). The
catalogue proxy used for selection is also known to *invert* the owner's reported score ordering
(see [`emission-anatomy.json`](emission-anatomy.json)), so no catalogue-proxy number may be read as
a competition score.

## Reproduce

```bash
PYTHONPATH=src python - <<'PY'
import numpy as np, pathlib
from gemsdoe30.cv import spatial_quadrant_masks
from gemsdoe30.emission import adaptive_disk_select
data = pathlib.Path('data/processed')
valid = np.load(data/'valid.npy') & np.load(data/'label_valid.npy')
oof = np.full(valid.shape, np.nan, np.float32)
for fold in range(4):
    _, block = spatial_quadrant_masks(valid, fold, buffer_m=300.0)
    surf = np.load(f'runs/metric-emission/fold{fold}/surface.npy')
    oof[block & valid] = surf[block & valid]
emission = adaptive_disk_select(oof, 5.0, gamma=1.0, mask=valid, limit=480_000)
np.save('runs/metric-emission/candidate-mask.npy', emission.astype(np.float32))
PY
PYTHONPATH=src python scripts/build_submission.py \
  --probabilities runs/metric-emission/candidate-mask.npy \
  --name oof-gbm-adaptive-r5 \
  --note "GEMSDOE30 4-fold OOF GBM surface; adaptive Poisson-disk dots (500 m min spacing); proxy gate failed vs uniform - not holdout-promoted"
```

The build is deterministic apart from the timestamped filename; the array hash recorded in the
manifest is `be95b5871d4d4664533cc3b5804b03d23be05581cdb3ca6189eaf45b9cd8c18f`.
