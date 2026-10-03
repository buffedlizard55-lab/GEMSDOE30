# Generative-AI disclosure — working draft

**Status:** not an entrant-approved final statement. The official GEMS rules permit generative-AI use
but require a narrative describing the extent of use and how it contributed to the submission. The
current wording below covers the Arena repository sessions through 2026-10-03; the entrant must
update it for every team member, tool, source, experiment, and submission element before filing.

**Official reference:** [GEMS Prize Official Rules, §3.2](https://docs.nlr.gov/docs/fy26osti/96647.pdf).
The rules place this narrative outside the word count and make the entrant responsible for accuracy,
authenticity, and authorship representations.

## Current-session facts to preserve

- An AI coding assistant in Arena Agent Mode reviewed and edited repository code, tests, HTML, and
  research documentation across five sessions through 2026-10-03.
- Work included:
  1. Implementing and testing the 300 m kernel-aligned boundary-aware objective (`src/gemsdoe30/losses.py`)
     combined with regional soft-Tversky loss, plus exact full-grid out-of-fold DTI aggregation (`src/gemsdoe30/cv.py`).
  2. Restoring SHA-256-pinned owner-mirror rasters (`scripts/restore_public_mirrors.py`), running paired
     4-fold spatial holdout loss ablations, metric-emission holdouts, and spacing-and-distance-matched
     geological hypothesis holdouts (`H-31-01`, `H-31-02r`, `H-32-01`, `H-32-05`, `H-32-05b`, `H-33-01`).
  3. Implementing the three-check verification protocol (`src/gemsdoe30/verification.py` and
     `scripts/run_verification_checks.py`: spatial block-validation, 4-fold OOF isotonic probability
     calibration, feature-perturbation stability, and a qualitative block atlas).
  4. Producing portal-safe (`-zeros.tif`) and template-conformant (`-nan.tif`) GeoTIFF artifacts in
     `docs/downloads/` and validating them against the competition grid (`scripts/validate_submission.py --portal-safe`).
- Rasters used in these sessions were restored from SHA-256-pinned owner mirrors and are not
  organizer-authenticated in this sandbox. No platform upload was performed by the AI agent.

## Paste-ready starting draft

> Generative AI was used through Arena Agent Mode to assist with repository code development, testing,
> geological hypothesis preregistration, spatial holdout evaluation, three-check verification
> (spatial block-validation, out-of-fold isotonic calibration, and held-out feature-perturbation
> stability), portal-safe GeoTIFF generation/validation, and documentation. All experiments were run on
> SHA-256-verified competition grid mirrors and public USGS/DOE GDR datasets, and all candidate rasters
> were checked against the competition grid contract (`EPSG:32611`, 100 m, `float32`, values in `[0, 1]`).
> The entrant independently reviewed and takes full responsibility for the final submission, its
> scientific claims, and this disclosure.

**Before use:** the final sentence is appropriate only if the entrant has in fact independently
reviewed and accepts responsibility for all submission elements. Expand or correct the description to
cover all actual AI use by the entrant/team.
