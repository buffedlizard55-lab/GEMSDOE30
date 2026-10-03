# Highest-score study: why the 0.2600 dotted file is shaped that way, whether >0.26 is reachable, and the system most likely to beat 0.3195

**Date:** 2026-10-03 · **Author:** Arena session 30 · **Status:** analysis + one registered experiment,
no new submission slot requested.

Evidence labels are used throughout, because nothing here is an organizer-confirmed score:

* **[OFFICIAL]** — read from a DrivenData/USGS/DOE page or product; link given.
* **[MEASURED]** — computed in this checkout from hash-pinned bytes; the command is in §8.
* **[MEASURED, leak-contaminated]** — computed on a field or frame that contains the held-out
  information; usable for *relative* comparisons only.
* **[OWNER-REPORT]** — the owner's own page or brief; no organizer receipt.
* **[MODEL]** — an owner-page model estimate conditioned on unverified anchors.

---

## 0. Executive answer

1. **Why `dotted-h19-5-d2-8` is the highest-scoring artifact.** It is not a better model. It is the
   *same* model emission thinned by a distance rule until the metric's marginal arithmetic saturates:
   `d2.8` is `dot_thin(H19-5, 2.8 px)` — 44,090 dots, 36 % of the 121,131-dot parent, and **0 of its
   dots lie on the training catalogue** (measured). The published index is
   `DTI = T / (0.2(T+F) + 0.8G)` and a prediction on a *known* fault pixel is masked out of every
   metric term, so the winning artifact had to be (i) binary, (ii) sparse, (iii) off-catalogue.
   The reported score 0.2600 is recorded in `docs/score-ledger.csv` as **user-reported, with a
   conflicting owner-page statement that it is unscored/not slot-approved** [OWNER-REPORT]; it is not
   an organizer-verified receipt.
2. **Why the local proxies could never have found that shape.** On the *same bytes*, a full-catalogue
   proxy frame (all 60,988 catalogue pixels as truth) ranks the three thinning steps
   `d1.5 = 0.17193 > h19-5 = 0.16635 > d2.8 = 0.16177` — the **opposite** order to the reported
   leaderboard sequence 0.2477 > 0.1922 for the two it overlaps and the reported 0.2600 at the top.
   The proxy rewards dots placed on the catalogue; the competition deletes exactly those pixels
   before scoring. This is the measured explanation for the failed 30-arm catalogue-gap factorial
   [OWNER-REPORT] and for the repository's own standing rule that catalogue holdouts are a
   *necessary* sanity frame, never a promotion frame.
3. **Is >0.26 achievable?** Yes, and the requirement is arithmetic, not speculative. At
   `s = 0.3195` a dot pays for itself iff its kernel credit exceeds `0.2s/(1−0.2s) = 0.0683`, i.e.
   iff it lands within ≈ 280 m of a scored truth pixel, and with the owner-model hidden mass
   `N̂ ≈ 12,691 px` [MODEL] the leader's statistics need `T = 3,466 + 0.0683·F` — between roughly
   **one dot in eight and one dot in five landing within 300 m of a hidden fault**, or a weighted
   coverage of **27 % of the hidden truth at zero false-positive mass, 34 % at parity**.
4. **What the project's own measurements say about the gap.** In the same-frame, leave-one-fold-out
   comparison registered and run this session, an exact marginal-credit emitter (EDGE) beat every
   belief-ordered emission family on all three belief fields, by **+0.049** (proximity), **+0.018**
   (external evidence) and **+0.044** (hybrid) index points, winning ≥ 3 of 4 spatial folds each.
   Emission, in other words, is now demonstrably solvable; the binding constraint is the *coverage*
   of faults that the catalogue does not contain.
5. **The system to beat 0.3195** (§6) is therefore: EDGE emission over a belief field built from
   *concealment* evidence (where a surface catalogue cannot see) fused with near-trace structural and
   external-evidence priors, validated on spatially blocked holdouts, with the coverage arithmetic of
   §4 used as the acceptance test instead of any catalogue proxy.

---

## 1. The metric, exactly

[OFFICIAL] The problem description fixes a 300 m triangular kernel, α = 0.2, β = 0.8 and 100 m pixels
(<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>). Writing
`T = TP_w`, `F = FP_w`, `G` = scored truth pixels and `FN_w = G − T`,

```
DTI = T / (alpha*(T + F) + beta*G),   alpha = 0.2, beta = 0.8.                    (1)
```

**[OFFICIAL]** Known USGS/INGENIOUS pixels are removed from scoring (community thread 11516, cited in
`docs/hypotheses.md`); the reference implementation zeroes predictions outside the scored domain
before the kernel is applied. **Consequence:** a dot on a known fault is free but worthless, and it
cannot radiate credit into the scored domain.

Three exact corollaries drive everything below.

**(i) Binary beats calibrated.** For a support set scaled by λ ∈ (0,1] the index is
`DTI(λ) = λT / (αλ(T+F) + 0.8G)` and `dDTI/dλ = 0.8·T·G / (αλ(T+F) + 0.8G)² > 0`: a graded
probability map is *strictly dominated by its own thresholded support*. Every competitive artifact
must be a binary 0/1 dot raster. The repository's download set already respects this: the OOF GBM
file's unique positive value is exactly `{1.0}` [MEASURED].

**(ii) The marginal-inclusion rule.** Adding a dot of credit `k` raises `T` by `k` and the denominator
by `α`, so it pays iff

```
k > alpha*s / (1 - alpha*s),        s = current index.                            (2)
```

| `s` | 0.10 | 0.20 | 0.26 | **0.3195** | 0.40 |
| --- | --- | --- | --- | --- | --- |
| required credit `k` | 0.0204 | 0.0417 | 0.0549 | **0.0683** | 0.0870 |
| implied maximum distance for a dot to pay | 294 m | 288 m | 284 m | **280 m** | 274 m |

A dot at distance `d` from the nearest scored truth carries `k = 1 − d/300 m`. **Credit is nearly
free anywhere inside the kernel and worthless outside it**; the metric is a *distance* filter, not a
precision filter. This is the mechanism the owner's `dot_thin` sweep d≈2.4 px located empirically
[OWNER-REPORT] and the reason EDGE's stopping rule is stated in exactly these terms.

**(iii) False positives cost a quarter of false negatives** (α = 0.2 vs β = 0.8), which is why
fine-grained dot *placement* is worth more than any amount of probability calibration.

---

## 2. What the reported-best artifact actually is

All rows [MEASURED] on the hash-pinned grid (`data/raw/labels.tif`,
`data/raw/sample_submission.tif`), scoring domain = template footprint (5,167,373 px).

| Artifact | positive px | dots on the training catalogue | full-catalogue proxy DTI |
| --- | ---: | ---: | ---: |
| `gems19-h19-5-powerlaw-…-nan.tif` (parent) | 121,131 | 0 | 0.1663512 |
| `gems24-h25-1-dotted-h19-5-d1-5-…-nan.tif` | 60,069 | 0 | 0.1719287 |
| `gems24-h25-1-dotted-h19-5-d2-8-…-nan.tif` | 44,090 | 0 | 0.1617720 |
| `GEMSDOE30_oof-gbm-adaptive-r5_…-nan.tif` | 90,358 | 2,517 | 0.1902044 |
| `gemsdoe30-sgmc-hedge-d10-85k-…-nan.tif` | 85,526 | 0 | 0.0017506 |

Two checks give confidence in the protocol: the `d2.8` proxy value reproduces the repository's
recorded `0.1617719829` to seven decimals, and the OOF GBM file is confirmed *strictly binary*
(`np.unique` of positives = `{1.0}`), i.e. the project has been emitting in the metric-optimal shape
all along.

**The reported rank order and the proxy order disagree, and not by noise.** With 121,131 → 60,069 →
44,090 dots the reported scores rise (0.1922 → 0.2477 → 0.2600 [OWNER-REPORT]) while the proxy falls
from 0.17193 to 0.16177. The cause is structural, not statistical: the proxy's truth *is* the
catalogue, so it pays for exactly the dots the official metric deletes, while the hidden truth
(the competition's "new faults") is a different inventory whose spatial relation to the catalogue is
unknown — the organizers explicitly declined to describe it (thread 11527).

**Implication for the archive's failure record.** Every catalogue-gap hypothesis in
`docs/hypotheses.md` was evaluated against an inventory that cannot represent the target. Their
negative results (H-31-02b, H-33-01, H-32-05b, H-31-02r) remain valid as *screen* failures under that
frame, but they are not evidence about the hidden fault population. Conversely, the two artifacts
whose numbers *are* catalogue-independent — the SGMC hedge (0.00175 catalogue-proxy, because all its
dots deliberately avoid the catalogue) and `d2.8` (0.16177) — are precisely the ones whose reported
scores are competitive [OWNER-REPORT]. This is the cleanest available statement of the project's
central measurement problem.

---

## 3. How much hidden truth a 0.32+ artifact must cover

Equation (1) inverts without any data beyond α and β. With `x = T/G` (weighted coverage of hidden
truth) and `ρ = F/G` (false-positive mass per truth pixel),

```
x = s*(0.2*rho + 0.8) / (1 - 0.2*s).                                              (3)
```

| target `s` | ρ = 0 | ρ = 0.5 | ρ = 1 | ρ = 2 | ρ = 4 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.26 | 21.9 % | 24.7 % | 27.4 % | 32.9 % | 43.9 % |
| **0.3195** | **27.3 %** | 30.7 % | **34.1 %** | 41.0 % | 54.6 % |
| 0.36 | 31.0 % | 34.9 % | 38.8 % | 46.6 % | 62.1 % |
| 0.40 | 34.8 % | 39.1 % | 43.5 % | 52.2 % | 69.6 % |

Under the owner-model hidden mass `N̂ = 12,691 px` [MODEL], `s = 0.3195` is equivalent to

```
T = 3,466 + 0.0683 * F      (weighted credit versus emitted false-positive mass),
```

so the leader's file must be carrying **3.5k–6.5k weighted truth credit** — that is, of its emitted
dots, roughly **one in eight to one in five sits within 300 m of a hidden fault**, at a mean credit
per dot of ≈ 0.11–0.15 (compare the parent's 12,199.64/121,131 = 0.101 measured **on the catalogue**,
which is the only per-dot credit number we can measure and is *not* the hidden-truth number).

**Is there room?** Yes, by a wide margin. With `G = 12,691` and perfect knowledge, dots every ≈ 3 px
along the hidden traces (≈ 4,200 dots) give `T ≈ 0.8G`, `F ≈ 4,200`, hence `DTI ≈ 0.78`. The
0.26 → 0.3195 gap is therefore **not** an emission-quality gap; it is a coverage gap of roughly
+25 % relative weighted coverage of hidden faults. That is the only quantity worth optimizing now.

---

## 4. What changed today: emission is no longer the bottleneck

`src/gemsdoe30/emitter_opt.py` (**EDGE**) emits the *expected-marginal-credit* greedy support of a
belief field: candidates are ranked by

```
dT(x) = sum_delta  pi(x+delta) * max(0, k(delta) - C(x+delta)),
```

the exact expected credit a new dot would add given the credit `C` already delivered by the accepted
set, and the sweep stops at the exact marginal condition (2). Its bookkeeping is verified against an
independent from-scratch credit pass (relative error 1.95e-7, `tests/test_emitter_opt.py`), and
prefixes of the acceptance order reproduce the recorded cumulative statistics.

**Registered experiment, run 2026-10-03** (`scripts/emitter_opt_holdout.py`; frame: whole 8-connected
catalogue components split seed 31 into a stand-in hidden half (20,870 px) and a known half
(40,118 px, masked from every metric term), four spatial quadrant folds, leave-one-fold-out
parameter choice per family, pooled cross-validated index at each fold's held-out choice):

| belief field | EDGE | best other family | margin | EDGE folds won |
| --- | ---: | ---: | ---: | ---: |
| `proximity` (exp(−d/1 km) to known traces, 3 km cut) | **0.18754** | adaptive 0.13848 | **+0.04906** | 4/4 |
| `external` (USGS SGMC + GDR paleo/probes/volcanics, exp(−d/0.7 km), 2.1 km cut) | **0.15784** | adaptive 0.14015 | **+0.01768** | 3/4 |
| `hybrid` (geometric mean of the two) | **0.18368** | adaptive 0.14014 | **+0.04354** | 3/4 |

Uniform thinning, dense quantile thresholding and the previously shipped belief-ordered marginal rule
were all beaten decisively in the same runs (`uniform` ≈ 0.125, `dense` 0.060–0.074, `metric`
0.031–0.060). The emitter's parameters were selected out-of-fold; the numbers above are
cross-validated, not in-sample.

**Interpretation limits, stated plainly.**

* The stand-in hidden truth is *half the catalogue*, so this frame cannot measure coverage of faults
  the catalogue lacks — it measures only whether a rule places dots where a *withheld piece of the
  same fault system* lies. The margins are large, but they are proxy margins.
* The 80,000-dot cap bound the sweeps on two fields, so these are *lower bounds* on what EDGE
  reaches; a convergence run with a 160,000-dot cap is registered separately
  (`docs/research/emitter-opt-holdout-convergence.json`).
* **These absolute values are not comparable with the project's earlier registered numbers**
  (uniform 0.18675 / adaptive 0.18927 from `scripts/metric_emission_holdout.py`), which used a
  different frame (per-fold GBM surfaces plus quadrant scoring) whose inputs (`data/processed/*.npy`)
  are not present in this sandbox. Same-frame comparisons are the only valid ones here; on the
  earlier frame's own terms, no equivalence is claimed.
* No slot is requested on the strength of this experiment: it clears the same-frame gate
  (≥ +0.005 and ≥ 3/4 folds) but cannot be compared to the cross-frame best.

---

## 5. The strategy most likely to beat 0.3195

**The target is not a better detector; it is coverage of faults that a surface catalogue cannot
contain.** Three moves, in order of expected value:

1. **Add a concealment prior (H-34-01).** A catalogue records where rock is exposed enough to map a
   trace; faults under basin fill, young volcanic cover and valley floors are missing from *any*
   surface inventory. A belief field that multiplies near-trace structural priors by a concealment
   weight derived from the USGS SGMC map-unit polygons (age + lithology) is the only mechanism in the
   register that changes *where* dots go rather than *how* they are placed. Data: already downloaded,
   public domain, on disk (`data/external/`), fetch verified.
2. **Emit with EDGE at the exact marginal stopping point.** Measured above; it converts a belief field
   into the metric-optimal sparse support and removes the last degree of freedom that was costing the
   project score (thinning radius, budget, order).
3. **Hedge the belief across quantiles, not across space.** Because the marginal bar at `s ≈ 0.32` is
   only `k > 0.068`, a dot that has a ≥ 7 % chance of sitting within 280 m of *any* hidden fault pays
   for itself. Under that arithmetic, spending the budget on the top belief decile alone is dominated
   by spreading it over the top two or three deciles *unless* the field's top decile is far more
   accurate than its calibration suggests. Register this as a decision rule, not an intuition: the
   next EDGE run should sweep a "quantile floor" parameter (guaranteed dots per belief stratum) with
   leave-one-fold-out selection, exactly as the thinning radius was swept here.

An honest statement of the ceiling: if the hidden faults are simply not near the catalogue at all,
none of the above beats a well-thinned model emission, and 0.3195 may reflect a private data source
the organizers acknowledge exists but will not describe (thread 11527). The concealment prior is the
only lever under our control that is *orthogonal* to that risk: it improves coverage precisely where
a catalogue-driven field is blind.

---

## 6. Falsification and next actions

* **Falsifies move 1:** concealment-weighted EDGE fails to beat the count- and distance-matched
  control by ≥ +0.005 with ≥ 3/4 positive folds. Then concealment adds nothing and the budget moves
  to potential-field depth lineaments (H-34-02) or wellbore heat flow (H-34-03).
* **Falsifies move 3:** the quantile-floor sweep selects a *narrower* allocation out-of-fold. Then the
  field is better calibrated than the hedging arithmetic assumes and the budget should concentrate.
* **Falsifies the whole approach:** the convergence run (160k cap) shows EDGE's pooled CV *falling*
  well below the 80k operating point, which would mean the belief fields are the limiting factor
  rather than the emitter — in which case the next spend is data, not code.

---

## 7. Reproduce

```bash
# metric algebra
python - <<'PY'
def x(s, r): return s*(0.2*r+0.8)/(1-0.2*s)
for s in (0.26, 0.3195, 0.36, 0.40):
    print(s, [round(100*x(s, r), 1) for r in (0, 0.5, 1, 2, 4)])
print([round(0.2*s/(1-0.2*s), 4) for s in (0.10, 0.20, 0.26, 0.3195, 0.40)])
PY

# artifact measurements and the registered emitter comparison
PYTHONPATH=src python scripts/emitter_comparison.py         # full-catalogue proxy DTIs
PYTHONPATH=src python scripts/emitter_opt_holdout.py        # EDGE vs all families, LOO folds
PYTHONPATH=src python -m pytest tests/test_emitter_opt.py   # emitter invariants
```

Machine-readable results: `docs/research/emitter-opt-holdout.json`,
`docs/research/emitter-opt-holdout-convergence.json`, `docs/research/emitter-comparison.json`.

## 8. Sources

* Metric constants and kernel, official problem description:
  <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
* Official rules (PDF): <https://docs.nlr.gov/docs/fy26osti/96647.pdf>
* Public leaderboard snapshot read 2026-10-03 (leader 0.3195): `docs/score-ledger.csv`,
  <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
* Known-fault masking and the "new fault may be new geometry of an existing system" clarification:
  community threads 11516 / 11536 / 11527, cited in `docs/hypotheses.md`.
* Owner-reported scores and the `dot_thin` sweep (evidence class `owner-report`, not authenticated):
  <https://buffedlizard55-lab.github.io/GEMSDOE25/> and `docs/score-ledger.csv` row
  `GEMSDOE25 / dotted-h19-5-d2-8-20261002-e56ea318af89-nan`, whose own notes record the conflict
  ("conflicting owner page says unscored/not slot-approved").
* Repository artifacts measured above: `docs/downloads/*.tif` (hashes in their JSON sidecars),
  `docs/research/emitter-opt-holdout.json`.
