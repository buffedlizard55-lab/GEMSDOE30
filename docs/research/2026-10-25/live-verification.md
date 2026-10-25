# Live verification of official competition facts — 2026-10-25

Fetched in this session with the page-retrieval tool (the bash sandbox cannot reach drivendata.org; the retrieval tool can).
Each claim below is tied to the text retrieved. Anything not on these pages is marked unverified.

## Sources retrieved

| Source | Retrieved | Used for | Link |
|---|---|---|---|
| Problem description (competition page 967) | 2026-10-25, 2 chunks | Metric, kernel, α/β, submission format | [page/967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| Public leaderboard | 2026-10-25, chunk 0 | Current public top scores | [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| Official rules PDF (NLR, Sept 2026) | 2026-10-25, chunks 0–1 | Prize structure, eligibility, single entry | [96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf) |

Not retrieved this session: the data page (login-walled), the submission page, the user forum, the about page (page 968), the reference notebook (not re-read; earlier session cites commit `aebe92f7`).

## 1. Metric — checked against the repository implementation

The problem page defines, for prediction p(x) ∈ [0,1], ground truth g, kernel k(d) = max(1 − d/R, 0), R = 300 m:

* TP_w = Σ_{g∈G} max_{x: d(x,g)≤R} p(x) k(d(x,g))
* FP_w = Σ_{x: p(x)>0} p(x) [1 − max_{g∈G} k(d(x,g))]
* FN_w = Σ_{g∈G} [1 − max_{x: d≤R} p(x) k(d(x,g))]
* DTI(α, β) = TP_w / (TP_w + α FP_w + β FN_w + ε), with α = 0.2, β = 0.8.

Repository check: `src/gemsdoe30/holdout.py::masked_dti` and `masked_dti_by_blocks` compute TP as the max-kernel credit on truth, FP as p·min(d/R, 1) = p·[1 − k(d)] for d ≤ R and p otherwise, and FN as G − TP. These are the same quantities. `src/gemsdoe30/emission.py::dti_from_components` evaluates TP/(α TP + α FP + (1−α) G + ε), which is algebraically identical to TP/(TP + αFP + βFN + ε) because FN = G − TP and β = 1 − α. **Consistent.**

**Irregularity — known-fault mask not stated.** The problem page does not say that known (catalogue) pixels are excluded from FP_w. The repository's holdout scores on the domain minus visible catalogue, following its own documented reading (`docs/irregularities.md`). **Flag for review: confirm the masking rule on the rules/forum before relying on any holdout value.**

## 2. Public leaderboard — retrieved 2026-10-25

| Rank | Participant | Best public DW-Tversky |
|---|---|---:|
| #1 | xiaofanhu | **0.4413** |
| #2 | cfld__ | 0.3916 |
| #3 | Batik Shirt Brothers | 0.3904 |
| #4 | BrandenKMurray | 0.3724 |
| #5 | No Fault of Our Own | 0.3539 |
| #8 | DARD | 0.3398 |

(Source: [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/), read 2026-10-25.)

**Label:** PUBLIC LEADERBOARD value (organizer-hosted table, read by tool). It is **not** an ORGANIZER-CONFIRMED value in the project's sense, which requires a submission-page receipt for a specific file.

**Irregularity — conflicting "highest score" statements.** The owner's messages cite both **0.4413** and **0.3195** as the current high. The live table shows 0.4413 at rank 1 today. `docs/research/sources.md` records a **2026-10-03** snapshot in which DARD was displayed at **0.3195** at rank 1. Both values are real for their dates; the leaderboard is not a fixed snapshot. Flag: any "current" claim must carry its retrieval date.

**Irregularity — DARD row.** The 2026-10-03 snapshot shows DARD at #1 with 0.3195; today DARD is #8 with 0.3398. Those are different dates and a different best-public metric value, not a contradiction within one table; do not assume a consistent history without the leaderboard's own version record.

## 3. Rules — retrieved 2026-10-25

* **Single entry.** "Participants will submit a single entry, which will be evaluated in two prize phases" (§1.1). The problem page says the same: "Competitors must choose a single submission for scoring across both rounds before the deadline" (page 967, "Competition structure").
* **Phase 1:** $50,000 split equally among the top five on the private test set. **Phase 2:** $250,000 among the top five on the expanded label set (§1.1, §1.3).
* **Eligibility:** U.S.-based entities; individuals must be a U.S. citizen or permanent resident (§1.3). Eligibility is subject to verification, and a penalty-of-perjury certification is required at registration. **Whether any person is eligible is for the user to determine; this repository does not assess it.**
* **Dates:** the rules defer to gems.drivendata.org for the timeline (§1.2). Dates were not confirmed here. The repository's earlier note on a deadline wording conflict is recorded in `docs/research/geothermal-vents-knowledge.md`.

## 4. What this changes in the project

* The scoring metric matches the repository's implementation (§1). The holdout numbers are therefore interpretable under the same formula, subject to the mask question.
* The public top score is 0.4413. Nothing in this session reproduces or approaches that value; the new candidate's holdout result is negative (see `candidate-residual-gate.md`).
* No value in this file is a submission result. Organizer-confirmed scores still require a submission-page receipt.
