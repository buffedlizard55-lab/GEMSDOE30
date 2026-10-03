# Irregularity and limitation register

Last reviewed: **2026-10-03**. “Fixed” means the repository now mitigates the tooling defect; it does not authenticate competition data or establish score gains.

| ID | Severity | Status | Observation / evidence | Action or consequence |
| --- | --- | --- | --- | --- |
| IR-30-001 | Critical | **Open — data access** | No competition rasters, sample template, checkpoints, or GEMSDOE30 predictions are present in the current checkout. The official data page redirects an unauthenticated visitor to the DrivenData login page. The recorded baseline commit already contains the model/loss, tests, scripts, and site; the available Git history is shallow/grafted, so any earlier README-only state cannot be checked here. | The local preflight and preparation scripts exist, but the preflight cannot download login-gated files. Real-data training and holdout scoring remain blocked until the official inputs are downloaded through an authorized session and placed in `data/raw/`; no credential handling or login bypass was attempted. |
| IR-30-002 | Critical | **Open — score/file mismatch** | The user-supplied history assigns 0.2600 to GEMSDOE25's D2.8 filename. The linked GEMSDOE25 landing/executive pages currently call that TIFF unscored/not slot-approved. The live leaderboard displayed 0.2600 for `wbg1` at rank 15, without a file name/hash. | Do not state that the named TIFF earned 0.2600 unless a DrivenData submission receipt/ID or verifiable exact-file association is supplied. Preserve both assertions in `docs/leaderboard-analysis.md` and `docs/score-ledger.csv`. |
| IR-30-003 | High | **Open — leaderboard target** | The live public leaderboard displayed 0.3195 for DARD at rank 1 on 2026-10-03. This is above the reported 0.2600 and does not reveal private-test performance. | State the date and public/private distinction. No claim that this repository can beat either score. |
| IR-30-004 | High | **Open — no real validation** | The 300 m loss and end-to-end training/inference plumbing passed unit tests and a disposable synthetic 64×64 four-fold smoke, but no competition rasters, real checkpoint, or real spatially held-out predictions are present. | Synthetic tests are labeled as software-only; the holdout comparison CLI is ready for authorized data, but no measured gain or change in real fault misses is claimed. |
| IR-30-005 | High | **Open — no new submission raster** | No competition template, trained probabilities, or prediction raster is present. A fabricated grid/file would not be a valid competition output. | The site links to the external GEMSDOE25 research TIFF only as a download convenience and states that its owner page marks it unscored/not slot-approved. No GEMSDOE30 TIFF is published. |
| IR-30-006 | Medium | **Open — external binary verification** | GDR 1391 and the USGS 3-D temperature catalog pages expose public-access/license statements and data links, but linked archives are not locally verified. On 2026-10-03, direct shell `curl --head --location` checks to the GDR 1391 2 m probe, paleogeothermal, and Quaternary-volcanics ZIPs all failed with `SSL_ERROR_SYSCALL`; no bytes or checksums were obtained. Prior shell TLS failures to Dropbox/GitHub Pages also remain. | Candidates requiring those files are conditional until download succeeds and bytes, metadata, license, and geospatial alignment are verified. Catalog-page access alone is not evidence of local data viability. |
| IR-30-007 | High | **Open — automated leaderboard feed** | DrivenData Terms of Use prohibit using an automatic process/robot/spider to access the site for monitoring or copying. | Do not build a scheduled DrivenData scraper. Keep a time-stamped snapshot and source link; refresh only by a permitted route. This prevents a fully automated live leaderboard feed. |
| IR-30-008 | Medium | **Open — deadline time** | The current competition homepage states 2026-12-03 11:59 p.m. UTC; the September 2026 rules PDF's Appendix A.1 states a 5:00 p.m. ET submission deadline time. | Confirm the controlling cutoff with the organizer; do not rely on one interpretation for final delivery. |
| IR-30-009 | Medium | **Open — novelty not exhaustive** | Public GEMSDOE24–27 pages contain extensive owner-reported experiments, but their code/evidence is not mirrored or rerun in this checkout. The available Git history is shallow/grafted and the historical site list contains additional projects. | Hypotheses are labeled “not found in inspected summaries,” not globally novel. Audit actual layer manifests and earlier project code before preregistration. |
| IR-30-010 | Medium | **Disclosed — boundary loss terminology** | Kervadec et al. propose a signed-distance boundary loss for medical segmentation. This implementation instead uses the exact GEMS triangular kernel in a differentiable DTI-shaped geometry term plus regional soft-Tversky. | Call it “Kervadec-inspired / metric-aligned,” not an exact reproduction or established transfer of their reported gains. Only a real paired spatial holdout can establish value here. |
| IR-30-011 | Medium | **Open — local proxy limitations** | Spatially holding out known catalogue faults does not recreate the sponsor's expert-labeled new faults. Public leaderboard tuning can also overfit a public set. | Report the proxy honestly, keep blocks/seeds frozen, use fresh-seed confirmation, and never equate a proxy DTI with the competition score. |
| IR-30-012 | Low | **Fixed — range validation** | The user's previous upload rejection was “Predicted values must be in range [0, 1]”; the linked GEMSDOE25 page attributes an earlier failure to NaN inside the valid footprint. The portal validator is not public, so the specific historical cause is owner-reported. | Writer validates all in-footprint values before output; validator checks float32, one band, EPSG:32611, 100 m grid, exact shape/transform, finite `[0,1]` inside and null/NaN/nodata outside. This is a local contract check, not organizer acceptance. |
| IR-30-013 | Low | **Open — template contract** | User brief uses default input names `labels.tif` and `sample_submission.tif`; the public problem page confirms label rasters and a sample submission but does not expose this unauthenticated checkout's exact filenames/metadata. | Treat names as project defaults, inspect downloaded files, and require exact template alignment rather than trusting filenames. |
| IR-30-014 | High | **Fixed — exact OOF aggregation** | Review found that the earlier holdout comparator summed components from four independently masked quadrants. That drops valid true-positive and nearest-truth false-positive interactions across the 300 m fold boundaries. No real holdout result had been run or published from this checkout. | `compare_spatial_holdout` now computes the promotion score once over the complete stitched OOF grid. Fold-isolated scores are labeled diagnostics only. The evaluator requires hashes/provenance sidecars, a shared training recipe, the 300 m protocol, and exact fold coverage. A synthetic boundary-crossing regression test covers the prior failure mode. |
| IR-30-015 | High | **Fixed — checkpoint/fold identity** | Review found that inference recorded the requested fold but did not bind that label to the fold used to train the checkpoint. A wrong-fold or full-data checkpoint could therefore be mislabeled as OOF, leaking held-out labels into evaluation. | Checkpoints now store their fold identity; inference rejects fold mismatches, stitching validates that identity and both prediction/checkpoint hashes, and the evaluator checks fold receipts. A regression test covers relabel attempts, and the synthetic end-to-end smoke passes. No competition-data checkpoint or real holdout existed in this checkout. |
| IR-30-016 | Medium | **Fixed — source-bound dataset identity** | The earlier prepared manifest stored a grid/mask identity but no cryptographic identities for the source feature, label, and template TIFFs. Models with geometrically identical but byte-different inputs could not be distinguished in the OOF provenance. | Data preparation now records each source raster's SHA-256 and a canonical dataset signature; checkpoints carry that signature, and inference/stitch/evaluation compare it with the prepared manifest. Band descriptions and dtypes are recorded for later feature audit. This is reproducibility metadata, not proof that the source files are official or independently licensed. |

## Escalation / next action

Data placement is no longer the blocker (owner mirrors restored and prepared; organizer
authentication still open — IR-30-001). The current next actions are: (1) run the H-32-01
vent-corridor holdout to its preregistered gate and record the verdict; (2) acquire the named
free external archives (3DEP 1 m tiles for H-31-02, OSTI 1148722/GDR 616 for H-32-04
validation, GDR 1391 ZIPs) off-sandbox, checksum and align them; (3) retry the boundary loss
only with a larger budget and weight sweep per `loss-ablation-holdout.md`; (4) keep uploads on
the portal-safe `-zeros.tif` convention (IR-30-019). Do not spend any weekly slot on an
unvalidated candidate.

## Latest-session superseding evidence

IR-30-001/004/006: owner mirrors now restored through GitHub API and hashes verified, real four-arm pilot completed; organizer authentication and official external archive transfer remain unresolved. IR-30-005: local historical D2.8 reference published, **no new promoted model output**. IR-30-NEW: mirrored sample template has 60,988 ones equal to catalogue labels; never use these template values for learning or output. See `research/session-review.md` and full results. Older absence claims are baseline history, superseded by this paragraph.

IR-30-017 (new, Medium, **open — proxy truth vs scored truth**): the official problem page states that the Initial Prize Round is scored against a *private set of new expert-labelled faults*, not the public catalogue, and the owner-artifact audit shows catalogue-proxy DTI ordering inverted relative to the owner-reported leaderboard ordering (see `research/artifact-structure.json`). Implication: catalogue-based holdouts can only ever be a proxy and must not be used to rank submission candidates; report proxy and reported values in separate columns. IR-30-011 is the standing limitation for this. IR-30-018 (new, Low, **closed — no promotion**): the count-matched adaptive-vs-uniform emission experiment failed its gate in all three arms (`research/emission-holdout-results.json`); uniform Poisson-disk thinning stays the default and no slot was spent. IR-30-010 still stands: the implemented geometry term is metric-aligned and Kervadec-inspired, not a verbatim boundary loss.

## 2026-10-03 second session additions

| ID | Severity | Status | Observation / evidence | Action or consequence |
| --- | --- | --- | --- | --- |
| IR-30-019 | High | **Fixed — portal-safe convention** | The user's upload of a downloaded site file was rejected with "Predicted values must be in range [0, 1]". Measured this session: the official sample template itself encodes 7,111,787 NaN cells outside the footprint, and both published downloads matched that mask exactly — so a NaN-unaware elementwise range check fails any template-conformant file, including the official format. The GEMSDOE25 page independently infers the same root cause and ships a zeros-outside fallback (verified byte-level: finite 0.0 outside, `nodata=None`). | Portal-safe variants now published as the primary downloads (`-zeros.tif`; in-footprint bytes identical to the NaN copies; `validate_submission.py --portal-safe` checks all 12,279,160 cells finite in [0,1]). Upload instructions say explicitly: upload the `-zeros.tif` file. Organizer acceptance remains unverified (no upload is performed by this project). |
| IR-30-020 | High | **Open — entrant eligibility** | Rules §1.3 (verified 2026-10-03): individuals must be U.S. citizens/permanent residents; entities U.S.-incorporated; certification is made under penalty of perjury at registration; FFRDC/DOE/FCOC/MFTRP exclusions apply. | The owner/operator must verify eligibility before any entry; this repository cannot certify it. Disclose generative-AI use in the narrative per §3.2 (`ai-disclosure-draft.md`). |
| IR-30-021 | Medium | **Open — Qfaults circularity** | Rules §2/§3.3: training labels come from the INGENIOUS Great Basin compilation (which compiles USGS Quaternary faults); the scored test labels are expert-new faults. Measured: 55 % of in-footprint `gdr_qfaults_traces.csv` centroids lie within 300 m of catalogue truth. | Any Qfaults-derived hypothesis (H-32-04) cannot be validated on the catalogue-proxy holdout (it would re-test the masked catalogue); it needs an independent fault inventory (OSTI 1148722 / GDR 616) or a submission slot. Recorded in `hypotheses.md` H-32 register. |
| IR-30-022 | Low | **Closed — rules URL verified** | The cited `https://docs.nlr.gov/docs/fy26osti/96647.pdf` is real: `docs.nlr.gov` is the prize administrator's domain (National Laboratory of the Rockies); the PDF serves the September 2026 official rules. A `docs.nrel.gov` variant does not resolve. | No action; citation retained as-is. |

Superseding evidence: IR-30-012's "Fixed — range validation" status is **superseded** by IR-30-019: validating
in-footprint values alone did not prevent the portal rejection, because the NaN *outside* convention the
template itself uses is what an elementwise range check trips on. IR-30-004/005 remain open in their
scientific sense (no promoted model) but the "no GEMSDOE30 TIFF" claim is superseded by the published,
clearly-labelled un-promoted candidate (2026-10-03, prior session) and its portal-safe variant (this session).

### IR-30-023 — Emission scorer degenerated to a score-blind lattice (found and fixed same day)
- **Category:** methodological defect in experiment tooling (docs/research/loss-weight-sweep.md).
- **What:** `scripts/score_sweep_arm.py`'s first version thinned an all-positive
  probability surface at radius 3 px with no candidate pool. Every pixel is a
  candidate, so the greedy radius packing produces the same geometric lattice
  regardless of scores — two different fold-0 models emitted byte-identical
  269,600-dot masks and identical DTI (0.179973894…). Cross-arm comparison made
  the defect visible immediately.
- **Evidence:** `runs/loss-weight-sweep/fold0-{regional,combined-025}-score.json`
  pre-fix (identical emitted blocks) vs post-fix; reproducible in one command:
  `poisson_disk_select(a, 3.0)` vs `poisson_disk_select(b, 3.0)` on any two
  distinct all-positive surfaces.
- **Resolution:** Fixed 2026-10-03. Candidates are now the top-480k scored
  pixels (the real family's pool cap) and scoring is restricted to the evaluated
  fold-quadrant. All four sweep arms re-scored with the corrected scorer before
  any comparison; `docs/research/loss-weight-sweep.json` carries a
  `scoring_note`. **Consequence:** the sweep's correct reading is
  scorings-disagree / no-weight-selected (the flawed run would have "selected"
  whichever arm the lattice tied on).
- **Follow-up rule:** any emission experiment must verify that emitted masks
  differ across score surfaces before interpreting them (cheap sanity assert:
  two arms' dot masks must not be identical when their score surfaces differ).
