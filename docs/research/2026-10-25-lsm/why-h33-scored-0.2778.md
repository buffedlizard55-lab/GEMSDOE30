# Why GEMSDOE32 `h33-h33-2-b2-…-zeros` scored 0.2778, and what it would take to beat it

**Status:** analysis, 2026-10-25; retrospective evidence correction added 2026-10-30.

> **2026-10-30 correction — do not read the projections below as measured hidden-label contributions.** The historical values are owner-reported and no submission-page receipt links them to these exact TIFFs. The arithmetic in §§3–5 is conditional projection, not a score, hidden-truth measurement, or causal identification of H33-B2's advantage. A fresh read of DrivenData staff reply [11516/4](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4) confirms that the known-fault mask is pixel-exact, and that an unmasked prediction near a known trace but far from new-fault truth is fully penalized. The same reply also says new-fault truth may lie within 300 m of known traces and may be a correction or modification to an existing trace. Thus deleting H33-B2's catalogue-adjacent dots could reduce FP mass, but could also remove TP credit; the hidden labels and exact submission receipts needed to distinguish those effects are unavailable. The only established H33 mechanism is exact byte-mask pruning lineage. The separate 2026-10-30 public-board snapshot shows 0.4544 at rank 1 and 0.3195 at rank 50, placing the owner-reported 0.2778 below the visible top-50 cutoff; no row is attributed to this TIFF. See the [dated snapshot](../2026-10-30-leaderboard-snapshot.json) and [2026-10-30 review](../2026-10-30-session-review.md#h33-b2-what-its-reported-value-can-and-cannot-mean).

**Scores are labelled by source:**
- **Owner-reported (unverified):** every leaderboard number here, unless marked otherwise. No organizer receipt exists for any repository raster.
- **Projection:** derived quantities.
- **Verified:** byte identities, reproducible with `python scripts/leaderboard_calibration.py` and the lineage check in §1.

## 1. What the file is: a byte-exact pruning trajectory, not a new signal

All identities below were checked inside the template footprint:

| Step | Raster | Rule (distance *d* to the nearest catalogue pixel) | Dots | Owner-reported |
|---|---|---|---:|---:|
| 0 | GEMSDOE19 `h19-5-powerlaw-budget-multiline-corroborated` | continuous binary support | 121,131 px | 0.1922 |
| 1 | GEMSDOE24/25/30 D2.8 | Poisson-disk 280 m thinning of step 0 (D2.8 ⊂ h19-5 support: **verified**) | 44,090 | 0.2600 |
| 2 | GEMSDOE28 `r1-solo-d2-8` (= GEMSDOE31 solo-d28, identical) | D2.8 ∧ *d* > 1 px (**verified**) | 40,199 | 0.2708 |
| 3 | **GEMSDOE32 H33-B2** | r1 ∧ *d* > 2 px (**verified**); values {0,1} inside, 0 outside | **37,654** | **0.2778** |
| 3′ | GEMSDOE36 `anderson-geothermal-pinn` | H33 + 1,200 extra dots (**verified** superset) | 38,854 | 0.2750 |

The h19-5 belief supplies the signal. Every step after that removes dots; no step adds evidence.

## 2. Mechanism, from the published metric

The organizer pools TP, FP and FN over all public-test pixels and computes one Tversky index ([staff answer, forum t/11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550)):

DTI = T / (0.2T + 0.2F + 0.8G),

where *k*(*d*) = max(1 − *d*/300 m, 0). Known-fault pixels are masked **pixel-exactly**. Staff says an unmasked prediction near a known trace but far from new-fault truth is **fully penalised** ([staff reply 11516/4](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)). That reply also says new-fault truth may lie within 300 m of known traces and can include corrections or modifications. The rule therefore does not reveal whether a particular H33-deleted pixel was FP-only or could have earned TP.

For a binary dot, the TP credit is the *maximum* of *p*·*k* over nearby predictions, so credit never stacks. An isolated dot therefore collects at most about 3 TP per straight truth line, and integrates πR²/3 ≈ 9.42 px² of kernel. A dot raises the score only if its expected TP gain exceeds about 0.2s/(1 − 0.2s)·(1 − k̄) ≈ 0.059 at s ≈ 0.27. Below that rate, a dot costs more FP than it earns in TP.

## 3. Calibrating the hidden truth from a label-blind raster (projection)

The owner-scored GEMSDOE13 `r13-lattice-s5` is an **exact 5-px square lattice**: every positive pixel has row ≡ col ≡ 0 (mod 5), and it covers 4.004 % of the footprint (**verified**). A uniform lattice cannot know where faults are, so its score depends on the truth almost only through the truth's pixel density ρ.

| Input or result | Value |
|---|---:|
| Line coverage per truth pixel, *c* (measured on catalogue-line geometry) | 0.3742 |
| κ (Σ*k* per truth pixel) | 0.0988 |
| λ (dots per scored pixel) | 0.04005 |
| Owner-reported lattice score | 0.0904 |
| **Implied ρ** (projection) | **0.244 %** |
| ρ range for ±10 % error in *c* | 0.217–0.278 % |

The derivation, written out:
- The lattice score satisfies s = cρ/(0.2cρ + 0.2λ − 0.2κρ + 0.8ρ).
- This gives the implied density ρ = 0.2λs/(c − 0.2cs + 0.2κs − 0.8s).
- The density 0.244 % is about **21 % of the catalogue's density**.
- If the whole footprint were test area, that would be about **12.5 k hidden new-fault pixels**.

With ρ fixed, each isolated-dot raster's reported score converts into implied TP mass, coverage T/G, and hit rate per dot. This uses T = s(0.2N + 0.8ρA)/(1 − 0.2s + 0.2s/3), where Σ*k* ≈ T/3 for isolated dots (accurate to about ±10 % for dots 0–2 px from a line).

| Raster | Owner-reported | Dots | Implied coverage T/G | Implied hits per dot |
|---|---:|---:|---:|---:|
| d1.5 | 0.2477 | 60,069 | 0.452 | 0.094 |
| D2.8 | 0.2600 | 44,090 | 0.406 | 0.115 |
| r1-solo | 0.2708 | 40,199 | 0.406 | 0.126 |
| **H33-B2** | **0.2778** | **37,654** | **0.405** | **0.134** |
| PINN (H33 + 1,200) | 0.2750 | 38,854 | 0.406 | 0.130 |
| Uniform random dots | — | — | — | **0.023** (9.42ρ) |

**Interpretation.** D2.8, r1, H33, prethin and PINN all cover the *same* ≈ 40.5 % of the hidden truth. They differ only in wasted dots. H33's dots are about **5.8× more productive than random dots**. All of that productivity was already present in the h19-5 support.

## 4. The leaderboard differentials (projection)

Each nested pair isolates the implied hit rate of exactly the dots that changed:

| Change | Score change | Dots changed (distance to catalogue) | Implied hit rate of the changed dots |
|---|---:|---|---:|
| D2.8 → r1: drop *d* = 1 px | +0.0108 | −3,891 (all at 1 px) | **0.000** |
| r1 → H33: drop *d* ∈ {√2, 2} | +0.0070 | −2,545 (≤2 px) | **0.004** |
| d1.5 → gap-closure | −0.0028 | +1,259 (mostly 3–10 px) | **≈ 0** |
| H33 → PINN | −0.0028 | +1,200 (3–30 px) | **0.013** (below random) |
| r1 → rung30 / hf-euler (re-thinning) | +0.0002 / −0.0001 | ±10–12 k | 0.055–0.057 (net) |

**Retrospective answer (2026-10-30): why the reported H33-B2 value might be higher is not identified.**
- The original model's claim that h19-5 support found about 40% of hidden faults and was 5.8× more efficient than random placement is an **algebraic projection** from owner-reported scores, not a measured hidden-label result.
- The proposed D2.8 thinning explanation (including the projected reduction in FP mass) is plausible but not attributable without organizer receipts and hidden labels.
- H33-B2 removes 6,436 dots within 200 m of known faults, but the prior statement that these dots earned almost no TP and paid only FP cost is **not established**. Staff confirms penalties for unmasked predictions far from new truth, while also confirming that new truth can occur within 300 m of known traces and can correct existing traces. The deleted dots could remove either FP mass or TP credit.
- The exact byte-mask pruning lineage is verified; the owner-reported 0.2778 and any causal score contribution are not. H33-B2 is the highest historical value in the nine-site owner-claim table, but it is not verified or attributable to a submission receipt.

**Cautions for interpreting earlier proximity analyses:**
1. **Neither benefit nor harm from catalogue proximity is established for H33-B2.** The historical public-score differences for the ≤200 m band, 300 m–1 km gap closure, and PINN additions are owner-reported and lack submission-page receipts. The old catalogue hide-and-recover proxy hides components near visible ones, so it can reward proximity by construction; that does not establish hidden-test behavior. New-fault truth may also lie within 300 m of a known trace.
   - G30-S19's `0.2230` proxy HOLDOUT-DTI is not leaderboard evidence (IR-30-079); it is a catalogue-recovery proxy with its own proximity bias.
   - Any claims in the following numeric target table remain conditional projections, not measured competition scores or forecasts.
2. **The lever is localisation quality per dot, not more pruning.** At H33's 37,654 dots and ρ = 0.244 %, the required hit rate is h = s(0.2n + 0.8ρ)/(n(1 − 0.1333s)):

| Target (owner-reported leaderboard points) | Required hits per dot | Required coverage |
|---|---:|---:|
| 0.2778 (H33) | 0.134 | 0.405 |
| 0.3000 | 0.145 | 0.44 |
| 0.3195 (2026-10-03 snapshot of DARD) | 0.155 | 0.47 |
| 0.3300 (current #20 cluster) | 0.160 | 0.48 |
| 0.3904–0.3916 (#2–#3) | 0.191 | 0.57 |
| 0.4413 (#1, xiaofanhu) | 0.218 | 0.66 |

**A cap on pruning alone.** Suppose the same 40.5 % coverage were kept with only productive dots, so that N → T/3. The score could not exceed **≈ 0.46**. Reaching that would need a label oracle. Practical gains must come from a better-localised belief.

## 5. Can a unique method beat 0.2778?

**Feasibility.** Yes, it is feasible in principle. The live leaderboard (fetched 2026-10-25) has at least 50 entries at or above 0.2818, and #1 at 0.4413. The question is whether a *particular* new belief reaches about 0.145+ hits per dot.

**What the repository can measure.** No offline frame measures the expert-new-fault hit rate directly. This lane therefore:
1. uses **no catalogue-proximity input**, so the near-catalogue mode the leaderboard shows is unproductive cannot be learned;
2. adds 1 m-LiDAR scarp morphology. This is evidence an expert mapper can see, and the h19-5 support does not use it: h19-5's LiDAR-coverage fraction of 0.764 equals the domain's 0.754;
3. requires the candidate to beat the current spatially blocked holdout best (core19) under identical folds, budget and emission;
4. reports an independent-inventory frame (SGMC faults absent from the catalogue) as confirmation;
5. keeps only the two leaderboard-proven emission rules: no dots within 2 px of the catalogue, and an operating point near 38 k dots.

**Results.** See `run-card.json` and `review.md`. A pass is *evidence*, not a forecast. Expected-score statements remain projections until an organizer receipt exists.

## 6. Caveats

- **Owner scores are unverified.** A misattributed lattice score would rescale ρ. The relative conclusions in §4 depend on ratios and survive moderate rescaling.
- **Public vs private split.** The public split is unknown chunks of the region; ρ is the public-chunk density. Staff will not disclose the chunking (forum t/11550). Properties used here are generic (density, the ≤2 px band) and should transfer. Nothing location-specific is fitted.
- **Sample size.** Hit rates of small changed sets (1–4 k dots) carry sampling noise of roughly ±0.01–0.02. The "≈ 0" results are robust in sign, not in decimals.
