# Three-pass review — QPC-1 / 26 October 2026

All three passes were performed; none authorizes upload. No competition slot was
selected, no candidate was perturbed after duplicate-stop, and no leaderboard
monitor or uploader was added.

## Pass 1 — requirements, evidence, and scientific design

- Reread the preserved owner prompt and `AGENTS.md`; the assigned method paragraph
  and private/parallel inventory were not supplied. Marked this autonomous lane
  unassigned and global novelty unknown. GDX-1's 3/3 budget remained exhausted.
- Reviewed the shared holdout, emitter, novelty and writer instead of forking them.
  Verified the owner-pinned data/cache byte derivation, while retaining the explicit
  limitation that owner mirrors are not organizer-authenticated.
- Recorded four ranked hypotheses and primary-source links before implementation;
  selected the catalogue-free two-scale magnetic/gravity proxy and named intrusive
  contacts, dikes and survey seams as non-fault alternatives. Added locality,
  held-out component and per-feature leakage checks.
- Found that FFL's seed-3063 confirmation was the stronger matched **main-branch**
  17-pixel holdout rather than MSDB alone. Amended the preregistration before any
  QPC fitting to require a fixed fold-identical FFL replay and three paired gates;
  counted that replay as experiment two. The amendment and hashes are frozen in
  `started.json`, not rewritten afterward.
- Corrected the shared public registry inventory to include tracked TIFFs under
  `docs/research/` and quarantine, not only downloads. Tested deduplicated source
  aliases and race-safe cache publication. This still cannot certify private,
  outside-tree, original-surface or parallel-branch completeness.

## Pass 2 — execution, duplicate rule, and independent adversarial checks

- The exclusive start lock prevented resume; 2 experiments used 550.904 seconds.
  All 308 feature-alone canaries completed; maximum bidirectional AUC 0.663826.
  The fixed FFL replay matched each historical fold to 1e-6, and MSDB fold/block
  parity held. Results and paired bootstrap intervals are recorded in `results.json`.
- The actual pre-placement score surface was compared before dot placement.
  The final dots triggered **duplicate-stop** at 78.915854% overlap with an
  existing GEMSDOE30 reference. Six reference rows crossed the threshold, including
  encoding aliases. No QPC TIFF was published, no post-stop file validator was
  run, and `validator_output` is null rather than a fabricated pass.
- The independent verifier reopens the saved surface when locally available,
  recomputes all geographic-block scores/CIs, rechecks every canary and the FFL
  fold reproduction, validates the exact registry references and flags, and exits
  0 for a valid negative finding; `--require-promote` exits 2. CI without the
  ignored surface bytes verifies the bound receipt only.
- Synthetic/adversarial tests prove an existing start marker cannot be overwritten,
  an elevated dot overlap cannot be hidden by a falsified decision, a canary alarm
  cannot be forged away, and changed pooled metrics or submission approval fail
  closed. A descriptive `qpc1` readiness message was corrected to name its three
  required controls; no frozen result, plan, runner, or historical receipt changed.
- The malformed GEMSDOE31 reference remains unknown. Different TIFF bytes or a
  locally different mechanism do not override the duplicate rule or establish
  global uniqueness.

## Pass 3 — parallel work, publishing, reproducibility, and security

- Rechecked open PRs rather than assuming `main` covered concurrent work. Before
  opening this PR, 25 public open heads existed across the nine repositories;
  their trees were not systematically scanned. Unmerged GEMSDOE30 PR #41 reports
  HOLDOUT-DTI 0.18668700 [0.17332555, 0.20031682], evaluator
  `component-holdout-v3-blockstats-20261025`, 60,988 positives, but uses a 20 px
  guard and different visible/training sets. The record is not independently
  reproduced or a proven paired comparator. Its TIFFs were not in the frozen
  registry. The [post-stop inventory](parallel-inventory.json) preserves the
  immutable source identity; a future shared snapshot now enumerates open PR
  heads as **unscanned**, not as cleared evidence.
- Rebuilt deterministic Pages with one prominent **NOT APPROVED FOR SUBMISSION**
  decision and one research-only download: the earlier GDX-1 file, explicitly
  labeled as prior and not QPC. The current guide supplies that artifact's exact
  name and ≤140-character note without suggesting an upload. The nine-site table
  now names all nine files, distinguishes unverified owner claims from unknown
  estimates, shows directional relationships, and does not imply global novelty.
- Updated the repository-derived status feed and GitHub workflow to verify QPC
  evidence without contacting DrivenData. Checked link targets/unique IDs, the
  complete-owner-prompt preservation test, deterministic site rebuild, negative
  selector exit code, and priority-site/source limitations.
- **Preview incident:** a generic static server was briefly started before the
  existing restricted server was noticed; it could have served private paths.
  It was stopped immediately. Its access log contained only root-page requests;
  there was no observed request for a private path. The replacement
  `scripts/serve_research_site.py` returned HTTP 200 for public pages and 403 for
  `.git/config`, raw labels, and the ignored QPC surface. This observation does
  not prove the absence of any unlogged access.
- Final local commands: `.venv/bin/python -m pytest -q` → **360 passed, 5 skipped**
  (optional torch training tests), 2 rasterio deprecation warnings, 7 subtests
  passed; `.venv/bin/python scripts/verify_quadrature_phase_run.py` → valid
  negative; `.venv/bin/python scripts/build_research_site.py --check` → passed;
  `git diff --check` → passed. The preview and workflow checks are not organizer
  portal acceptance or an independent evaluation of unmerged branches.

## Remaining blockers

The assigned lane, authenticated data provenance, complete parallel registry and
original continuous surfaces, malformed reference, independent confirmation,
current competition eligibility/receipts and separate slot selection remain unresolved.
The requested unique, high-performing submission TIFF was **not achieved**. The
correct outcome is the auditable negative result and a protected competition slot.
