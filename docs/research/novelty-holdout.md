# Independent-inventory emitter holdout — global budget is not active-domain count

**Status: completed, five repeats; no competition score and no slot used.** The historical comparison used a fixed *global* emission budget. After the competition-style masked scoring domain is applied, active prediction counts differ. The archived result is therefore a **global-budget comparison, not an active-scored-domain-count-matched comparison**. The previously reported +25.1% DTI difference remains the arithmetic of that frozen screen; it must not be presented as an equal-active-count placement effect. Raw values are in [`novelty-holdout.json`](novelty-holdout.json). Do not rerun or tune against these already-inspected SGMC labels.

## Why this frame exists

The competition truth is private and consists of expert-labelled new faults; known USGS/INGENIOUS pixels are masked out of scoring. A local frame built only from that catalogue therefore cannot establish novelty. The independent-inventory proxy used here is the USGS State Geologic Map Compilation (SGMC) fault linework (Nevada + California, public domain), which is not the source of the competition catalogue and overlaps it only partially (24.94% of its footprint pixels lie within 300 m of a catalogue fault against an 8.61% base rate). SGMC is an imperfect proxy, not competition truth.

## Protocol and count scopes

1. Rasterise the SGMC fault linework onto the competition grid (100 m, EPSG:32611): 21,160 features and 82,151 pixels in the footprint. Provenance: [`external_receipt.json`](../../data/external/external_receipt.json).
2. At each of five repeats, hide a random 30% of connected components, dilate the visible catalogue components by 3 px, and exclude that dilation from the scored domain.
3. Score each emitter on the same masked domain with the exact triangular 300 m DTI (`α=0.2`, `β=0.8`).
4. The archived “matched” random controls match the emitter’s **global** count before the score-domain mask. The mask can remove different numbers of candidate and random pixels from scoring. Accordingly, report **both** the global budget and the active pixels in the scored domain. An equal global budget is not an equal active count and does not isolate placement at equal active mass.

## Result (five repeats; DTI means over repeats)

`Global N` is the number of generated positive pixels over the full valid footprint before the SGMC scoring mask. `Active N` is the number of those pixels left inside the score domain; it is the `emitted_pixels` field in each repeat of the JSON artifact.

| emitter | what it is | Global N | Active N in scored domain | mean DTI | range |
|---|---|---:|---:|---:|---|
| `cand_t04s4` | UNet OOF field, threshold 0.4, 4 px Poisson spacing | 80,392 | **80,388** | **0.09526** | 0.08380–0.10483 |
| `blind_random_80392` | uniform random control | 80,392 | **73,843** | **0.07617** | 0.07268–0.07967 |
| `blind_random_85526` | uniform random control | 85,526 | **78,512** | 0.08110 | 0.07851–0.08630 |
| `cand_gbm` | sibling-branch GBM candidate TIFF | 90,358 | **75,001** | **0.07279** | 0.06848–0.07885 |
| `blind_random_75001` | uniform random control | 75,001 | **68,848** | **0.07460** | 0.07237–0.07612 |
| `cand_hedge` | `cand_t04s4` plus SGMC off-catalogue dots | 85,526 | **85,526** | 0.18343 | 0.17391–0.19114 |
| `lattice` | blind 3 px lattice | 574,329 | **527,504** | 0.09395 | 0.08901–0.09966 |
| `model_probability_dots` | 3 px Poisson over the OOF field | 568,942 | **506,746** | 0.09498 | 0.08966–0.10078 |
| `historical_artefact` | D2.8 raster; file-score link unresolved | 44,090 | **35,824** | 0.07061 | 0.06640–0.07355 |
| `visible_inventory_dots` | visible SGMC traces (sanity arm) | varies by draw | **3,507 mean** (3,472–3,576) | 0.00121 | 0.00101–0.00168 |

The source TIFF/global counts come from the fixed emitter artifact or the published candidate raster; the active counts and scores are recorded in `novelty-holdout.json`. The `blind_random_*` global budget is the suffix value used by its deterministic generator. Do not substitute an active count for a global count when describing these runs.

## What the numbers do and do not establish

- `cand_t04s4` versus `blind_random_80392`: equal global budget (80,392), but **80,388 versus 73,843 active scored-domain pixels**. The mean DTI difference is +0.01909 (about +25.1% relative), but it is **not active-count matched**. The candidate receives 6,545 more active predictions in the scored domain, so the difference cannot be attributed solely to better placement at equal active mass.
- `cand_gbm` versus `blind_random_75001`: neither scope is matched: candidate **90,358 global / 75,001 active**, random **75,001 global / 68,848 active**. The lower candidate mean (0.07279 versus 0.07460) is a raw diagnostic, not a matched-count result.
- `cand_hedge` uses SGMC itself as an input while SGMC components define the held-out truth. Its 0.18343 mean is **tautological**, not independent validation or evidence of a hidden-fault gain.
- The D2.8 mean of 0.07061 is a local SGMC proxy only. It is not the reported 0.2600 competition value; the exact score-to-file link remains unresolved.
- The historical `cand_t04s4` mask is absent from this checkout, and a fresh-seed paired confirmation against that baseline was not performed. No candidate is promoted.

A future spatial comparison should prespecify and report both the global emission budget and the active scored-domain count, use an active-count-matched control when the estimand is placement at equal scored mass, and use an uninspected validation frame. **No active-count-matched rerun is authorized on the SGMC labels already inspected in this experiment.**

## Reproduce the frozen score artifact (not a new tuning run)

```bash
PYTHONPATH=src python3 scripts/novelty_holdout.py --repeats 5 \
  --extra-emitter "cand_gbm=docs/downloads/GEMSDOE30_oof-gbm-adaptive-r5_20261003T170425181215Z_aedb3d13.tif" \
  --extra-emitter "cand_hedge=docs/downloads/gemsdoe30-sgmc-hedge-d10-85k-20261003-ac08b41e.tif" \
  --extra-emitter "cand_t04s4=runs/candidates/model_t04_s4.npy" \
  --extra-emitter "blind_random_75001=runs/candidates/blind_random_75001.npy" \
  --extra-emitter "blind_random_80392=runs/candidates/blind_random_80392.npy" \
  --extra-emitter "blind_random_85526=runs/candidates/blind_random_85526.npy"
```

The command documents provenance only. It must **not** be rerun against the already-inspected SGMC labels to seek a new result. The random masks were drawn deterministically from the full in-footprint index list with `rng = np.random.default_rng(1000 + n)` without replacement.
