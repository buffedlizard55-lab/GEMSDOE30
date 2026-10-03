# H-33-01 verdict — placement-policy holdout (run 2026-10-03, post IR-30-031 fix)

**Decision: Not promoted. The incumbent whole-domain model-score emission stands, and the
band-stratified placement line is closed.** Machine-readable results:
[`h33-01-placement-policy-holdout.json`](h33-01-placement-policy-holdout.json);
frozen design: [`h33-01-preregistration.md`](h33-01-preregistration.md) (text unchanged, as
required — everything below is report, not amendment).

Frame: novelty holdout (expert Qfaults minus catalogue, 300 m buffer), seed 30, 5 repeats as
the sign-stability unit (the frame has no quadrant folds — frozen in the prereg). Emission
scorer is the IR-30-031-corrected score-first greedy (`poisson_disk_select_ordered`).

## 1. What the run measured about its own design (the uncomfortable part first)

The frozen budget B = 80,000 exceeds what the 0.4-thresholded, 4 px-thinned pools can supply.
Measured pool capacities (whole scan, no cap):

| pool | spaced candidates |
|---|---|
| near (3–6 px from catalogue) | 12,021 |
| mid (6–12 px) | 14,451 |
| far (> 12 px) | 42,101 |
| union of bands | 68,573 |
| full-domain, score-first | 62,057 |
| full-domain, legacy raster order | 74,523 |

Consequence, exactly as the shortfall rule anticipated: **every quota arm at the gate budget
exhausts its pools and emits the identical 68,573-dot union** (per-repeat DTIs identical to 5
decimals; `capacity.gate_arms_collapse_identical = true`). A collapsed arm (68,573 dots) versus
the exactly-80,000-dot blind control is **not count-matched**, so it violates the frozen
construction ("arms fill the exact budget B") and the repo's standing same-count standard. The
harness therefore marked the gate **VOID** (`gates_void_reason` in the JSON) rather than
adjudicating — the G1/G2/G3 numbers are recorded but the screen cannot pass or fail on them,
no confirmation run was executed (G4 = null), and the decision follows the preregistered
failure path: *not promoted*. The G1 mean of +0.0122 (5/5) under collapse illustrates exactly
why the guard matters: purity won on a 14 % count deficit; that is not a placement result.

This was a **design undercount by this line's author (the agent), discovered mid-run, not
hidden** — recorded as [IR-30-032](../irregularities.md). The 200 k score cap that the first
launch attempt carried was also an unpreregistered artefact (it made capacities look smaller
still); it was removed to restore the frozen "full thinned pool" semantics, with `max_kept`
early-stopping added as a pure speed device (prefix-equivalence proven by test).

## 2. The substantive evidence: count-matched budgets

The preregistered sensitivity budget (40,000) sits just under capacity, so **every arm there is
fully count-matched at 40,000 dots** and the comparison is valid, if not gated. Diagnostics at
12,000 (all arms realisable, including P100) and 30,000 (P75/P100 partly capacity-bound) were
run as explicitly un-gated support. Means over 5 repeats (in-domain Qfaults DTI):

| arm | B40,000 | B30,000 | B12,000 |
|---|---|---|---|
| **f_nat — whole-domain score-first (incumbent)** | **0.07608** | 0.06469 | 0.03688 |
| P0 (mid+far only) | 0.07213 | 0.06329 | **0.03634** |
| P25 | 0.07250 | **0.06550** | 0.03493 |
| P50 | 0.07237 | 0.06385 | 0.03604 |
| P75 | 0.07237 | 0.06103 | 0.03442 |
| P100 (near-band only) | 0.07237 | 0.06112 | 0.03184 |
| P_rank (pure proximity ranking) | 0.03660 | 0.03134 | 0.01852 |
| blind_random_B | 0.05634 | 0.04792 | 0.02372 |
| rand_P0 / rand_P25 / rand_P50 / rand_P75 / rand_P100 | .0569/.0603/.0585/.0553/.0479 | .0497/.0495/.0497/.0497/.0441 | .0244/.0251/.0260/.0266/.0262 |
| f_nat_legacy (raster order) | 0.06371 | 0.06200 | 0.04246 |
| historical_d28 (35,824 dots — *not* count-matched) | 0.07061 | 0.07061 | 0.07061 |

Key paired deltas (5 repeats):

- P25 vs blind at B30k: **+0.0176, 5/5**; P0 vs its own uniform stratified control rand_P0 at
  B12k: +0.0120, 5/5; score-ranking inside bands is worth roughly +100 % over uniform placement.
- **Any band split vs whole-domain f_nat at 40k: −0.0036 to −0.0040 in mean** (the sensitivity
  run stores means and per-arm summaries, not per-repeat pairings against `f_nat`, so no
  win-share is claimed there) — stratification never beats the incumbent, and the best
  diagnostic margin (P25 over f_nat at 30k, +0.0008) is noise-sized and reverses to −0.0036
  once counts are matched at 40k.
- **Proximity-first is catastrophic as a policy**: P_rank −0.0519 vs the collapsed union at 80k
  and 0.0366 vs 0.0761 at 40k; uniform-in-near (rand_P100) also loses to blind at 40k. The
  H-33 physical premise — that the *enrichment* near mapped faults earns credit — is falsified
  for placement: enrichment helps the score field (already exploited by the incumbent), but
  spending budget *by proximity ranking* loses to spending it by model score across the whole
  domain.
- Visit order (post-fix vs legacy) flips with budget: fixed order wins at 30k/40k
  (+0.0027/+0.0124), legacy wins at 12k/80k (+0.0056/+0.0089). Consistent with IR-30-031's
  caveat: **order effects are frame- and budget-specific; no order claim is supported.**

## 3. What this says about the 0.2600 artefact

`historical_d28` holds 0.07061 at 35,824 dots; at matched 40k counts the incumbent emits
0.07608 and every stratified arm is below it. Dot-count-adjusted, D2.8's clustered-near-catalogue
placement is **parity-or-slightly-worse than plain whole-domain score-first thinning on this
frame** — reinforcing the why-d28 analysis that its real edge is not placement geometry, while
the strong negative is specifically *proximity-ranked* placement, which D2.8 (score-ranked with
a near-band enrichment in its field) does not actually do.

## 4. Consequences registered (no gate was used; nothing here re-fits the frozen rule)

1. **Placement-policy line: CLOSED with a negative result.** Whole-domain score-first
   Poisson-disk emission is near-optimal among all stratifications tried; the next registered
   experiment must change the lever (score-field quality on the learning side, or dense-dot
   hybrid), not placement.
2. **Method rule going forward (now in the protocol ledger as IR-30-032):** every emission
   experiment counts its realised pool capacities at the *frozen* threshold/spacing **before**
   fixing gate budgets; arms that cannot fill B are a construction failure, detected here only
   mid-run.
3. **No submission slot was spent or is justified by H-33-01.**

Elapsed 302 s; harness [scripts/placement_policy_holdout.py](../../scripts/placement_policy_holdout.py)
(commit this session); tests `tests/test_placement_policy.py` + ordering tests in
`tests/test_emission.py`; full suite 80 passed + 11 subtests.
