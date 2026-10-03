# H-32-01 geothermal-discharge corridors — registered component-holdout result (2026-10-03)

**Status: gate FAILED — not promoted. No submission slot.** Preregistration:
[`h32-01-preregistration.md`](h32-01-preregistration.md) (frozen before the run). Raw record:
[`h32-01-vent-corridor-holdout.json`](h32-01-vent-corridor-holdout.json) (script
`scripts/vent_corridor_holdout.py`). This is a catalogue-proxy result, **not** a competition
score.

## Gate outcome (all three clauses failed)

| Clause | Requirement | Measured | Verdict |
| --- | --- | --- | --- |
| Screen pooled ΔDTI (spring_buf_r10 − random_near_matched, budget 15,000, split seed 31) | ≥ +0.002 | **−0.01494** | fail |
| Quadrant consistency (screen) | ≥ 3 of 4 quadrants positive | **0 of 4** | fail |
| Confirmation pooled ΔDTI (split seed 41, fresh draws, ≥ 100 °C sensitivity) | > 0 | **−0.01537** | fail |

## Measured numbers (mean over 6 draws; hidden truth = held-out catalogue components)

Screen split (seed 31; 20,870 hidden truth pixels; 512 hot cells ≥ 60 °C):

| Arm | Pool px | b5k S/M/F | b15k S/M/F | b45k S/M/F |
| --- | ---: | --- | --- | --- |
| spring_buf_r3 (300 m halo) | 9,287 | .0041/.0084/.0076 | .0044/.0160/.0134 | .0044/.0166/.0130 |
| **spring_buf_r10 (1 km halo, primary)** | 53,546 | .0064/.0092/.0079 | **.0093/.0243/.0191** | .0088/.0522/.0442 |
| spring_buf_r20 (2 km halo) | 140,620 | .0083/.0087/.0069 | .0170/.0228/.0206 | .0201/.0508/.0447 |
| spring_corr_2_8km (pair corridors) | 47,205 | .0069/.0100/.0077 | .0098/.0230/.0203 | .0086/.0514/.0457 |

(S = spring zone, M = distance-to-known-matched random control, F = far-field random; all at
matched emission budgets. Confirmation split (seed 41, 20,247 hidden pixels) reproduces the
same ordering at every budget; the ≥ 100 °C subset is included in the raw JSON.)

Primary-budget credit accounting (screen, 15,000 emitted pixels):

| Arm | TPw | FPw | credit / emitted px | hidden pixels with credit |
| --- | ---: | ---: | ---: | ---: |
| spring_buf_r10 | 183.6 | 14,788.7 | **0.0122** | 1.7 % |
| random_near_matched | 479.3 | 14,811.3 | **0.0320** | 6.7 % |
| far_random | 376.1 | 14,851.3 | 0.0251 | 5.4 % |

## Mechanism reading

1. **No incremental signal beyond proximity, and worse than random.** The distance-matched
   control holds the generic near-known prior (the ~2.3× effect measured in the relay
   experiment) fixed. Against that control, spring-proximal emission earns **~3× less** hidden
   credit per pixel — in every arm, every budget, both splits, and 0/4 quadrants. Spring
   neighborhoods are *depleted* in hidden catalogue components relative to matched random.
2. **Why this is physically plausible.** The measured 2.3× enrichment of hot cells within 300 m
   of the catalogue says springs sit near *mapped* faults; once the distance profile is matched,
   that enrichment is controlled away. The literature (Faulds et al.) warns that outflow "may
   surface many kilometers away from the deeper source," so spring locations are noisy conduit
   proxies even before the catalogue-proxy question.
3. **Wider haloes narrow but never close the gap** (r20: .0170 vs .0228 at 15k), consistent
   with diffuse proximity information rather than a corridor signature.

## What this does and does not establish

* **Establishes (within the frozen protocol):** hot-spring cluster corridors do **not** beat a
  proximity-matched control for recovering hidden catalogue components. The hypothesis as
  instantiated is falsified on this proxy and must not be promoted to a submission slot.
* **Does not establish:** that discharge data is worthless against the *true* expert-new test
  faults. The catalogue proxy is a necessary-but-biased stand-in (IR-30-017: catalogue-proxy
  DTI ordering inverts the reported leaderboard ordering). A genuinely independent line to the
  hidden set — e.g. the OSTI 1148722 structural inventory or the GDR 616 play-fairway
  favorability layers — could still test a *chemistry-ranked* (H-32-03) or *blind-system* proxy
  not reducible to catalogue geometry.
* **Statistical power:** 6 draws/arm × 2 splits; the effect size (−0.015) is far larger than
  draw noise (stds in the JSON are ≤ 0.002 at the primary budget), so this is not a marginal
  miss.

## Deviations from preregistration

1. **The ≥ 100 °C confirmation sensitivity was not included in the primary run** — review found
   the script's `--confirm-threshold-c` option was defined but unused (both splits ran at the
   ≥ 60 °C primary threshold). The bug is fixed and a supplementary sensitivity run at ≥ 100 °C
   (split seed 41, budget 15,000, 3 draws) is recorded in
   [`h32-01-vent-corridor-holdout-sensitivity100.json`](h32-01-vent-corridor-holdout-sensitivity100.json):
   it agrees with the primary result (pooled Δ **−0.01768**, 0/4 quadrants — the ≥ 100 °C subset
   does *worse*, as expected if spring proximity carries no incremental hidden-fault information).
   This cannot change the promotion decision: the primary confirmation clause already failed by
   −0.01537 at the ≥ 60 °C threshold, and the sensitivity is not a gate clause.
2. No other deviations. Quadrant diagnostics keep cross-quadrant 300 m credit as declared.

## Consequences for the register

* H-32-01 moves to **not promoted as tested** (like H-31-01). The ranked H-32 register in
  [`hypotheses.md`](../hypotheses.md) is updated accordingly.
* The top *runnable* candidate left is **H-32-05 (buried pinch-out edges)** and the H-31-02
  reduced matched-filter scarp arm; both are local-data experiments.
* No weekly submission slot has been used or justified by this work.
