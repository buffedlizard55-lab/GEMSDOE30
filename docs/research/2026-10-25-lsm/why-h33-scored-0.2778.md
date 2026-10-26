# Why GEMSDOE32 `h33-h33-2-b2-…-zeros` scored 0.2778, and what it would take to beat it

**Status:** analysis, 2026-10-25.

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

where *k*(*d*) = max(1 − *d*/300 m, 0). Known-fault pixels are masked **pixel-exactly**. A prediction near a known fault but far from new-fault truth is **fully penalised** ([staff answer, forum t/11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).

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

**Answer: why and how H33 scored 0.2778.**
- The h19-5 "multiline-corroborated" topographic and geophysical lineament support finds about 40 % of the expert-mapped new faults, at about 5.8× the efficiency of random placement.
- Thinning it to isolated, roughly 300 m-spaced binary dots keeps most of that coverage while cutting FP mass about threefold (0.1922 → 0.2600).
- H33 then deleted the 6,436 dots within 200 m of known faults. Those dots earned almost no TP but paid full FP, because staff confirmed near-known predictions are fully penalised. That added +0.0178.
- H33 is the best of these files because it **wastes the fewest dots on the same signal**, not because it has new information.

**Two contrarian implications the earlier sessions missed:**
1. **Proximity to mapped faults is not where the hidden truth is.** Three changes each placed near-catalogue dots, and each earned about random or less on the leaderboard: the ≤200 m band, gap closure at 300 m–1 km, and the PINN's 300 m–3 km additions.
   - Catalogue hide-and-recover proxies hide catalogue components *next to* visible ones, so they reward proximity by construction.
   - G30-S19's "promoted" raster puts 76 % of its dots within 1 km of the catalogue and only 2.4 % beyond 3 km. Its proxy HOLDOUT-DTI of 0.2230 is therefore **not** leaderboard evidence (IR-30-079).
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
