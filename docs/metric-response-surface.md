# GEMS metric response surface: conditional D2.8 analysis and the 0.3195 snapshot

**Scope correction (2026-10-03):** the user-supplied 0.2600 is not authenticated to the named D2.8 TIFF. The official leaderboard showed `wbg1` at 0.2600 (rank 15) and DARD at 0.3195 (rank 1), without TIFF names or hashes. The GEMSDOE25 page currently calls D2.8 unscored/not slot-approved. This document separates verified metric algebra, local proxy measurements, and conditional score claims; it does **not** explain or assert that D2.8 earned 0.2600.

## 1. Official scoring geometry and score attribution

The [official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) specifies a distance-weighted Tversky index with triangular support `R=300 m`, `α=0.2`, `β=0.8`, and 100 m pixels. The [official public leaderboard snapshot](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) read on 2026-10-03 showed DARD 0.3195 and `wbg1` 0.2600. The owner-maintained D2.8 page calls the file unscored/not slot-approved; no receipt or exact-file crosswalk was found. See [`leaderboard-analysis.md`](leaderboard-analysis.md) and [`research/why-d28-scored-026.md`](research/why-d28-scored-026.md).

## 2. Local D2.8 forensic facts and proxy scopes

The exact local D2.8 NaN-outside TIFF has SHA-256 `91eae1ca42ec845eaa8c2ba32da49806e24751743459b8a10017c479bbe639b8`. It is a one-band float32, 3730 × 3292, EPSG:32611, 100 m raster. It contains 44,090 positive binary pixels in the footprint; all are isolated 8-neighbour dots and none overlaps a catalogue label. The recent scoring-mask audit found 8,266 dots inside its 3-pixel catalogue buffer and 35,824 outside. A separate direct Euclidean distance-to-catalogue calculation reports 19.5214% (about 8,607 of 44,090) within 300 m; this is a different proximity construction, not a contradictory count. Median distance is about 1.5 km. These facts describe the artifact, not hidden-fault discovery.

Different proxy protocols produce different local DTIs and must not be conflated:

| Protocol | Truth/scoring scope | D2.8 DTI | Evidence |
| --- | --- | ---: | --- |
| Full-catalogue emitter comparison | All 60,988 catalogue positives | **0.1617719829** | [`emitter-comparison.json`](research/emitter-comparison.json) |
| Catalogue checkerboard hide-and-recover | 30,865 held-out catalogue pixels; known components masked | **0.1509524764** | [`emission-anatomy.json`](research/emission-anatomy.json) |
| Independent SGMC component holdout | Five repeats; mean over SGMC hidden components | **0.07060919** (values 0.07260906, 0.07182390, 0.06866501, 0.06639569, 0.07355228) | [`novelty-holdout.json`](research/novelty-holdout.json) |

None is a competition score. The full-catalogue and checkerboard catalogue frames use different truths/masks; the SGMC frame is an independent but imperfect map compilation. The archived zero-outside sidecar records unchanged in-footprint values and a passing whole-raster finite diagnostic, but the file fails the published null/NaN-outside format check. The linked NaN-outside copy passes the repository's published-format check. The exact artifact behind the earlier `[0,1]` error remains unidentified, and local validation does not establish organizer acceptance.

## 3. Exact metric algebra

With `T=TP_w`, `F=FP_w`, and scored truth count `G`, the official metric simplifies (using `FN_w=G−T`) to

```
DTI = T / (0.2*T + 0.2*F + 0.8*G)
```

For a new unit prediction with kernel credit `k` on an otherwise-uncovered truth pixel, TP increases by `k` and FP by `1−k`. The denominator increases by 0.2, so the exact marginal condition is

```
k > 0.2 * current_DTI
```

At 0.2600 this threshold is 0.052; at the official 0.3195 snapshot it is 0.0639. These values are algebraic thresholds, not estimates of any candidate’s feature precision.

Let `c=T/G` denote weighted truth coverage and `ρ=F/G`. Then

```
c = 0.2*s*(ρ + 4) / (1 - 0.2*s)
```

| Target DTI `s` | `c` at `ρ=0` | `ρ=0.5` | `ρ=1` | `ρ=2` | `ρ=5` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.2600 (unverified D2.8 attribution) | 21.9% | 24.7% | 27.4% | 32.9% | 49.4% |
| **0.3195 (official public snapshot)** | **27.3%** | 30.7% | 34.1% | 41.0% | 61.4% |

This table is conditional on a specified `ρ`; it does not reveal the real hidden truth size, the leaderboard’s actual coverage, or the false-positive mass.

## 4. Why sparse emission can help — not why D2.8 scored 0.2600

The official metric credits the maximum nearby probability for each truth pixel, so multiple nearby predictions can be redundant while still paying false-positive mass. Thinning can improve a score if it removes redundant probability without losing too much 300 m coverage. Conversely, aggressive thinning can leave faults uncovered and raise false negatives.

The local bytes verify that D2.8 is a sparse binary subset of its H19-5 parent. Owner/user-reported values 0.1922 → 0.2477 → 0.2600 are consistent with a useful thinning sweep, but none is receipt-linked to these exact bytes in this checkout. The local catalogue and SGMC proxy ordering does not reproduce or validate the reported leaderboard ordering. **The thinning mechanism is plausible; its causal connection to 0.2600 is unverified.**

## 5. Implications for research

1. Target uncatalogued fault geometry using independent observables; do not optimize only against the public catalogue, which the metric masks.
2. Treat all local DTI values as proxy diagnostics. Use spatially blocked, preregistered holds and fresh confirmation before any slot is considered.
3. Report global emitted budget and active count within the scored domain separately. A global-budget match is not an active-count match; the SGMC count-scope limitation is tracked in IR-30-033.
4. Do not build a leaderboard scraper: [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) prohibit automated monitoring/copying.
5. No present candidate is holdout-promoted, and no competition score or improvement is claimed.

## Reproduction

```bash
PYTHONPATH=src python scripts/analyze_emission_anatomy.py --proxy
PYTHONPATH=src python scripts/emitter_comparison.py
PYTHONPATH=src python scripts/novelty_holdout.py --repeats 5
PYTHONPATH=src python scripts/metric_response_surface.py
```

See also [`research/official-rules-review-2026-10-03.md`](research/official-rules-review-2026-10-03.md) and [`research/review-checklist-2026-10-03.md`](research/review-checklist-2026-10-03.md).
