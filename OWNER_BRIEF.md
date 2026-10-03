# Owner brief (verbatim)

The literal owner brief for this project is reproduced in [`README.md`](README.md) under
**"Read first — owner brief (verbatim)"**. This pointer file exists so that the brief is
findable by name; the README section is the canonical, checked-in copy to re-read at the
start of every session.

Standing operational requirements distilled from it (see the README for the literal text):

1. Study and understand the highest reported score (the GEMSDOE25 "dotted D2.8" file,
   attributed 0.2600), explain why and how it scored what it did, and determine whether a
   higher-scoring submission is possible.
2. Beat the current public leader (0.3195 as read 2026-10-03) with a distinct, researched,
   scientifically grounded approach — not by copying any existing site.
3. Before implementing: generate 3–5 candidate geological hypotheses never tried here, each
   naming the layers, the physical signature, why it can catch a fault missing from the
   USGS/INGENIOUS catalogue rather than one already in it, and how it differs from prior work;
   rank by expected DTI improvement and implementation cost; validate the top candidate on the
   spatially blocked holdout before touching a submission slot; if new external data is needed,
   name the free official source and prove it is obtainable. Beyond the holdout, require three
   types of verification with pre-stated promotion criteria — spatial block-validation,
   probability calibration, feature-perturbation stability — plus a qualitative note on where
   the change helps and fails (docs/research/verification-protocol.md).
4. Verify line by line against official, verified, trusted sources, and provide links for manual
   review. No manual input required of the owner: work autonomously. Flag every irregularity.
   No hallucinations — distinguish official facts, owner/user claims, local measurements,
   hypotheses and estimates at all times.
5. Make a TIF submission trivially easy to download from the site (obvious at the top), with a
   unique name and a paste-ready short note, and explain the exact upload steps — including the
   portal's "Predicted values must be in range [0, 1]" failure mode.
6. Keep an always-current feed/status instead of manual checking, within the competition's terms
   (DrivenData's Terms of Use forbid automated monitoring, so no scraper).
7. Work in three cumulative passes (implement/verify; bug and edge-case review; full-brief
   re-check), then open a pull request from `arena/01a10289-gemsdoe30` and merge it to `main`.
8. Keep the Arena.ai core values in focus: **Maximize P(Win)** and **Own the Outcome**.
