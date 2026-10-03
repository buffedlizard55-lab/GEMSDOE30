# Conditional analysis of the D2.8 score claim and the 0.3195 public leader

**Status (2026-10-03): score-to-file attribution unresolved.** The named D2.8 TIFF has been downloaded through the pinned owner mirror, hash-verified, and inspected locally. The owner-maintained GEMSDOE25 page describes it as *unscored/not slot-approved*. The official leaderboard separately shows `wbg1` at 0.2600 (rank 15) and DARD at 0.3195 (rank 1), but neither row names a TIFF or hash. No submission receipt, submission ID, or official hash-to-score crosswalk links D2.8 to 0.2600. This note therefore analyzes the bytes and gives **conditional metric algebra**; it does not explain or verify an official score for this file.

Evidence labels: **[OFFICIAL]** primary organizer/USGS source; **[MEASURED]** local bytes or local proxy computation; **[CLAIM]** owner/user report without an official receipt; **[CONDITIONAL]** algebra that applies only if its explicit assumptions are true.

## 1. Score and leaderboard facts

- **[OFFICIAL, snapshot 2026-10-03]** The public table displayed DARD at 0.3195 (rank 1) and `wbg1` at 0.2600 (rank 15): [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The public leaderboard is dynamic and is not the private or final prize score.
- **[CLAIM]** The project brief assigns 0.2600 to `dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`.
- **[OWNER PAGE]** The [GEMSDOE25 landing page](https://buffedlizard55-lab.github.io/GEMSDOE25/) calls the named D2.8 file unscored/not slot-approved and calls 0.2510 a conditional model expectation, not a score.
- **Conclusion:** the 0.2600 leaderboard row is real as a participant snapshot, but it is not attributable to this TIFF on available evidence. The 0.3195 public leader is a separate and higher target. No GEMSDOE30 file has a competition score.

## 2. What the local D2.8 bytes show

Local file: `docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`

SHA-256: `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`

- One float32 band, 3730 × 3292, EPSG:32611, 100 m grid matching the locally pinned sample template.
- 44,090 positive binary pixels inside the footprint; each is an isolated 8-neighbour dot. None overlaps a known catalogue label.
- 8,266 pixels fall inside the experiment’s 3-pixel catalogue buffer; 35,824 are outside it. A **separate direct Euclidean distance-to-catalogue calculation** reports 19.5214% (about 8,607 of 44,090) within 300 m. These counts use different constructions and are not interchangeable or contradictory. Median dot-to-catalogue distance is about 1.5 km. These are raster properties, not proof that any dot is a fault.
- The portal-safe zeros-outside sidecar reports local format checks passed and the same in-footprint predictions. “Format validation passed” is not an organizer score or portal-acceptance receipt; the official example uses NaN outside the footprint, and acceptance of the zero-outside fallback remains unverified.

### Proxy measurements — different targets, not competition scores

| Local protocol | D2.8 result | Interpretation |
| --- | ---: | --- |
| Full-catalogue emitter comparison | DTI **0.1617719829** | Scores against all 60,988 catalogue pixels; structurally biased because the organizer masks known catalogue faults. |
| Catalogue checkerboard hide-and-recover | DTI **0.1509524764** | A separate split with 30,865 held-out catalogue truth pixels and known-catalogue mask; not numerically interchangeable with the full-catalogue frame. |
| Five-repeat SGMC component holdout | **0.07260906, 0.07182390, 0.06866501, 0.06639569, 0.07355228**; mean **0.07060919** | Independent but imperfect inventory proxy; not the expert-labelled competition test. |

The different catalogue proxy values reflect different truth masks and scoring protocols, not a competition-score discrepancy. The SGMC frame and every catalogue frame remain local proxies. The reproduced metrics and counts are recorded in [`emitter-comparison.json`](emitter-comparison.json), [`emission-anatomy.json`](emission-anatomy.json), and [`novelty-holdout.json`](novelty-holdout.json).

## 3. Exact metric algebra (independent of D2.8 attribution)

The public problem description specifies a distance-weighted Tversky index with triangular kernel `k(d)=max(1-d/R,0)`, `R=300 m`, `α=0.2`, and `β=0.8`: [official problem page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

Let `T=TP_w`, `F=FP_w`, and `G` be the scored truth-pixel count. Since `FN_w=G−T`,

```
DTI = T / (0.2*T + 0.2*F + 0.8*G)
```

For an added unit prediction with kernel credit `k` against an otherwise-uncovered truth pixel, TP credit rises by `k`, FP mass by `1−k`, and the denominator rises by exactly 0.2. The addition improves the current score `s` iff

```
k > 0.2 * s
```

Thus the exact algebraic thresholds are 0.052 at `s=0.2600` and 0.0639 at `s=0.3195`. They describe a hypothetical marginal prediction at those score levels; they do not estimate whether any proposed geological feature meets the threshold.

If `c=T/G` is weighted truth coverage and `ρ=F/G`, then

```
c = 0.2*s*(ρ + 4) / (1 - 0.2*s)
```

| Target DTI | Required `c` if `ρ=0` | if `ρ=0.5` | if `ρ=1` | if `ρ=2` |
| ---: | ---: | ---: | ---: | ---: |
| 0.2600 (reported claim only) | 21.9% | 24.7% | 27.4% | 32.9% |
| 0.3195 (official public snapshot) | 27.3% | 30.7% | 34.1% | 41.0% |

These are conditional design thresholds. The hidden truth size, actual weighted coverage, and false-positive mass are unavailable, so the table cannot recover the real leader’s recall or predict a future score.

## 4. What can be said about thinning

**[MEASURED]** The D2.8 raster is a sparse binary subset of its H19-5 parent mask. Under the published metric, an additional prediction near an already-covered truth may add little new TP credit while still adding FP mass; thinning can therefore help when it removes redundant predictions without losing too much 300 m coverage.

**[CLAIM, not verified]** The reported H19-5 → D1.5 → D2.8 score sequence (0.1922 → 0.2477 → 0.2600) is consistent with a useful thinning sweep, but no official receipt links those values to these exact local bytes. The local catalogue and SGMC proxy results do not reproduce or validate that sequence. Therefore “dotting caused the D2.8 score” is a plausible mechanism, not an established explanation.

## 5. Research decision

- Keep 0.3195 as the dated official public-leader snapshot; keep the 0.2600 D2.8 assignment as an unresolved user/owner claim.
- Do not treat the local 0.16177, 0.15095, or 0.07061 proxy DTIs as leaderboard scores or compare them directly with 0.2600/0.3195.
- No candidate is promoted. H-31-02b failed its registered primary spatial and strike-perturbation gates; its SGMC screen passed only at the frozen global budget and is not active-count matched. No weekly slot was used.
- A stronger claim requires an official score receipt/hash crosswalk or an independent, fresh, preregistered spatial holdout—not another fit to the same inspected SGMC labels.

## Reproduction and sources

- Metric and historical artifact analyses: [`../metric-response-surface.md`](../metric-response-surface.md)
- Local leaderboard/file analysis: [`../leaderboard-analysis.md`](../leaderboard-analysis.md)
- Official rules and access review: [`official-rules-review-2026-10-03.md`](official-rules-review-2026-10-03.md)
- Official metric: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- Official leaderboard: <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- Official rules: <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
