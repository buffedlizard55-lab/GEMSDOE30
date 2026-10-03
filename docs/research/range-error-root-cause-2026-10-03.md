# Root cause of the DrivenData portal error "Predicted values must be in range [0, 1]"

**Status:** diagnosed and engineered out on 2026-10-03. This document **supersedes** the
earlier "cause is undiagnosed because its exact file is unknown" wording that appeared in
`index.html`, `executive-summary.html`, and `README.md`.

**Correction of a prior claim.** IR-30-038 asserted that the error could not be diagnosed
without the offending file, and that zero-outside files were "diagnostic-only". The first
half is wrong: the two mechanisms that produce the condition are properties of the
*competition's own input rasters*, so they can be measured directly without the offending
upload. They were measured this session. The second half is a judgement call that the
evidence below reverses.

---

## 1. What the official contract actually says

Verbatim from the competition problem description
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>, "Submission
format", read 2026-10-03):

> - Your submission is in the same projected coordinate reference system as the training data
>   (projected coordinate system for UTM zone 11N, EPSG 32611)
> - Your submission is at the same resolution as the training data (100m)
> - Your submission has the same bounds as the training data, and data outside the bounds is
>   null or nan.
> - Your submission contains a single layer with datatype of 32-bit float (`float32`) with
>   values between 0 and 1 indicating the confidence or probability of fault presence, with
>   higher values indicating higher probability.

The `[0, 1]` requirement is stated for the *values*. The null/nan requirement is stated for
*data outside the bounds*.

## 2. Measured properties of the organizer template

`data/raw/sample_submission.tif`, restored from the pinned owner mirror
(`buffedlizard55-lab/GEMSDOE24@07345ea0604953d7efb858d9cfbc21e20c7aca0b`,
`data/bridge/sample_submission.tif`) and re-verified this session:

| Property | Measured value |
| --- | --- |
| SHA-256 | `2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc` (matches the recorded pin) |
| Bytes | 1,599,597 |
| Bands / dtype | 1 / `float32` |
| CRS | EPSG:32611 |
| Size | 3292 × 3730 (width × height) = 12,279,160 cells |
| Transform | `(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)` |
| Nodata | `nan` |
| Finite cells (the scoring footprint) | **5,167,373** |
| NaN cells | **7,111,787** |
| Distinct finite values | `{0.0: 5,106,385, 1.0: 60,988}` |

`data/raw/labels.tif` (SHA-256 `7ba308cc…5ae4093`, pin-matched) is `int8` with nodata `-1`;
its `-1` mask is **exactly** the template's NaN mask (both 7,111,787 cells) and its `1` mask
is **exactly** the template's `1` mask (both 60,988 cells). So the template is the label
raster re-encoded — only its *footprint* may be used, never its values.

## 3. Mechanism 1 — float32 sentinel pixels inside the scoring footprint

`data/raw/training_features.tif`, SHA-256 `4371c82e…43123bc5`, pin-matched, 418,912,844
bytes, 19 `float32` bands, **nodata declared as `-3.4028234663852886e+38`** (the `float32`
minimum, not NaN).

Measured per band (identical across bands unless noted):

| Quantity | Value |
| --- | --- |
| Sentinel pixels per band | 7,113,308 (band 6 `tc`: 7,113,320) |
| **Sentinel pixels INSIDE the 5,167,373-pixel footprint** | **3,061 per band** (band 6 `tc`: **3,073**) |
| Total sentinel-in-footprint band-pixels across 19 bands | **58,171** |
| Pixels where *at least one* band is sentinel | 7,113,320 |
| …of which inside the footprint | **3,073** |

A pipeline that reads these bands without replacing the sentinel ships cells worth
≈ −3.4 × 10³⁸. That is not in `[0, 1]`, and the portal's message describes exactly that.

## 4. Mechanism 2 — footprint mask mismatch leaves scored pixels as NaN

| Mask source | Valid pixels |
| --- | --- |
| `np.isfinite(sample_submission.tif)` — the correct footprint | **5,167,373** |
| `band 1 (mag_anom) != sentinel` | **5,165,852** |
| Net deficit | 1,521 |
| **Template-valid pixels that band 1 calls invalid** | **3,061** |

So a footprint mask derived from a feature band strands exactly **3,061 scored pixels** as
NaN. NaN is not in `[0, 1]` under any check of the form `((v >= 0) & (v <= 1)).all()`.

Mechanisms 1 and 2 are two faces of the same 3,061-pixel discrepancy: the feature raster's
valid region is *smaller* than the template's, and the difference is filled with the sentinel
rather than with NaN.

## 5. Why zero-outside is the correct default, and what that rests on

Two independent verifications:

1. **The organizer's own reference solution writes an all-finite raster with no nodata tag.**
   `drivendataorg/gems-prize-reference-solution`, notebook
   `unet-mc-cv-reference-solution.ipynb`, cell "Save final prediction in required format":

   ```python
   new_dataset = rasterio.open(fname_out, "w", driver="GTiff", height=..., width=...,
                               count=1, dtype=y_final.dtype,
                               crs=fault_dataset.crs, transform=fault_dataset.transform)
   new_dataset.write(y_final, 1)
   ```

   No `nodata=` argument; `y_final` is a finite sigmoid output. The organizer's example is
   therefore an all-finite, nodata-free raster.

2. **The owner ledger shows the two encodings score identically.**
   `docs/score-ledger.csv` records `r7-nms3-dem10-scarp_0c9199f14e62` = **0.1294** and
   `r7-nms3-dem10-scarp_0c9199f14e62_allfinite` = **0.1294**. Same predictions, two outside
   encodings, identical score — direct evidence that cells outside the template footprint
   carry no scoring weight. (Owner-reported, not organizer-authenticated; see the caveat.)

Given that, zero-outside is strictly better for the stated goal: it cannot trip a
whole-raster range check, and the available evidence says it costs nothing. A NaN-outside
twin with **bit-identical in-footprint values** is also published for anyone who prefers the
literal spec wording.

**Honest limits.** Neither the exact file behind the historical error nor the portal's
validator source was obtained, so the *specific* trigger in that one upload is still
inferred rather than proven. What is proven is that both mechanisms exist in this
competition's inputs, that both produce precisely the reported condition, and that the
shipped file contains neither.

## 6. What the shipped artifact guarantees

Built by `scripts/build_portal_submission.py` and re-verified by an independent read:

| Guarantee | Measured on the shipped bytes |
| --- | --- |
| Grid identical to template (CRS, transform, 3730×3292, 1 band, float32) | true |
| Cells finite | **12,279,160 / 12,279,160** |
| Cells in `[0, 1]` | **12,279,160 / 12,279,160** |
| NaN cells anywhere | **0** |
| Nodata tag | none |
| In-footprint values bit-identical to the source prediction | true |
| Dots on catalogue pixels | **0 of 44,090** |
| SHA-256 | `8cf893ead5667df21d3288a9968c35fd5385c425b029d82ee71d311715b129fd` |

The builder fails closed: it re-reads the file from disk and aborts (exit 1, no sidecar) if
any cell is non-finite or out of range, or if the grid drifted. `tests/test_portal_submission.py`
(5 tests) covers both mechanisms, both outside modes, bit-preservation, and fail-closed
behaviour.

## 7. Verified scoring rule that bears on this

DrivenData staff (`chrisk-dd`), official competition forum thread 11516, 16 Sep 2026 —
<https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>:

> 1. Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from
>    evaluation, so they do not count towards penalty terms.
> 2. Re-evaluation will also mask/exclude the existing USGS/INGENIOUS faults.

Consequence: probability mass on catalogue pixels earns no TP and incurs no FP — it is pure
waste of the emission budget. Measured this session, the shipped file puts **0 of 44,090**
dots on catalogue pixels, while the GEMSDOE30 OOF GBM research artifact wastes **2,517**.

## 8. Links for manual review

- Competition problem description and submission format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Official rules PDF (NLR, September 2026): <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
- Reference solution (all-finite example writer): <https://github.com/drivendataorg/gems-prize-reference-solution>
- Forum thread 11516 (masking of known faults): <https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516>
- Metric definition (distance-weighted Tversky, α=0.2, β=0.8, R=300 m): competition page 967, "Performance metric"
- Mirror pins for every raster cited here: `docs/research/mirror-pins.json`
