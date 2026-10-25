# Current owner request — operational record, 2026-10-25

This is a retained consolidated requirements record, **not a verbatim transcript**.
The **complete current owner task text (formatting normalized)** is now preserved in
[README → Current owner prompt](../../../README.md#current-owner-prompt) and
[the task-text file](../texture-displacement/owner-prompt.txt). Read that full record
first each session. Current result and automatic gates are selected by
[docs/current-run.json](../../current-run.json); the prior literal brief remains
historical owner text, not current readiness or an authenticated competition score.

## Non-negotiable priority (owner wording)

> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A
> PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST
> GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO
> DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

## Parallel-run protocol

- Stay in the assigned single-method lane. The current message references a
  method paragraph but does not identify one; do not invent an assignment.
- Stop and log a duplicate if surface/final rank correlation exceeds 0.90 or
  more than 70% of candidate dots are within 3 pixels of any registry raster.
  Check both before placement and after placement.
- Reuse cached features and shared evaluator/writer; fix shared defects once.
- Hide and recover whole fault segments with a buffer, rebuild all
  catalogue-based features from visible faults only, and mask visible faults
  pixel-exactly. Score pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel.
- Report model measurements as HOLDOUT-DTI with evaluator version, withheld
  positives and 95% CI; organizer results as ORGANIZER-CONFIRMED only with a
  submission-page receipt. Projections are never scores. Unverified historical
  owner claims must remain explicitly unverified, not assigned either label.
- Test every feature alone; AUC above 0.90 is a leakage alarm until resolved.
- End with a JSON run card: hypothesis, mechanism, named non-fault mimic,
  HOLDOUT-DTI/CI, registry comparisons, raster hash, validator output,
  submission name, note <=140 characters, verdict promote/negative.
- Stop after three experiments or two hours. Promotion does not allocate a real
  submission slot; a separate selector obeys the current portal weekly cap.

## Scientific and delivery scope

Focus on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Investigate the owner's
reported GEMSDOE32 H33-B2 result, without copying it into a new submission.
The owner cites competing current-leader values; verify rather than choosing one.
Propose 3–5 distinct geological hypotheses before implementation, naming layers,
physical signatures, off-catalogue rationale, differences from existing work,
non-fault confounds, expected utility and cost. Validate the top idea on a
buffered spatial holdout and beat the comparable best before slot consideration.
If new data is needed, identify a free official source and verify obtainability
before calling the idea viable. Research geothermal mechanisms critically; do
not conflate fault mapping with demonstrated vent discovery.

Work autonomously; restore/prepare available data; preserve clean auditable source
tables and knowledge for future sessions. Use official sources with links and
explicit uncertainty. Do not fabricate verification, performance or access.
Make the site clean and easy to use with download/status at the top, unique names,
short notes and an executive submission guide. Validate GeoTIFF band count,
finite in-footprint [0,1] values, CRS, shape and transform against the real template.
Inspection must be automated, not delegated to a human inspector. Actual portal
acceptance and slot allocation remain separate from automated research gates.
Keep a current repository-evidence feed, not an invented live leaderboard feed.

Perform three passes: implement and test; examine bugs/edge cases and fix; recheck
against requirements. Create a PR from the session branch and merge it only after
verification. Report remaining limitations and next-session work honestly.

## Core values

**Maximize P(Win):** prioritize reproducible scientific improvements and preserve
scarce slots, rather than inflating metrics or publishing renamed references.
**Own the Outcome:** own data restoration, evaluation, validation, delivery and
follow-up; document negative results and blockers rather than implying completion.
