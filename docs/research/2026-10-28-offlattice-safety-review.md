# Follow-up repository review: off-lattice safety stop

28 October 2026. **Negative; no new TIFF, model fit, holdout score or slot.**

## Pass 1 — implementation and evidence

Read `AGENTS.md`, README's current decision/owner prompt, the current run index,
latest nine-site review, prior preflight and archived off-lattice generator.
The owner prompt is already retained in README; it has not been replaced with a
shortened paraphrase. The four ranked geological hypotheses, layers, mimics,
costs and differences from existing implementations remain in
[the current research review](2026-10-28-review.md#four-candidate-hypotheses--proposals-frozen-before-any-implementation).
They are untested proposals, not validated discoveries. No single method
paragraph assigning a new lane appears in this request. The existing lane and
no-evasion restrictions remain binding.

The off-lattice generator at base commit
`3344c38758a1379f9f7d69b4ef86cb4d7176935a` violated that continuation:

- `lattice_uncovered_mask` uses a previous prediction's distance transform as
  the placement domain. Registry evidence is supposed to reject duplicates,
  not become a geological feature or an optimization target.
- `select_dots` sets every uncovered cell to True. Sorting by geological score
  or changing its seed cannot change the binary support. Thus the assertion
  that geological weighting prioritizes the emitted dots is misleading.
- The declared four weights total one, but the score uses only three weights
  (0.4, 0.3, 0.2). The unused SGMC weight does not affect the output.
- The function called `surface_correlation` measures the *final binary dots*,
  not the independent pre-placement geological surface. Local downloads are
  not the complete registry; their recorded maximum is not global clearance.
- The fetch path can retain a hash-mismatched response after warning. Missing
  external layers silently become zero. These are not trustworthy input gates.
- The archived receipt supplies no HOLDOUT-DTI or feature-alone leakage canary.
  It cannot establish recovery of catalogue-missing faults or a geothermal vent.

Replaced that generator with an unconditional exit-2 stop, matching the existing
stopped CTD/FC CLI policy. Removed callable placement/fetch helpers rather than
leaving a back door. Historical code remains in Git history; historical TIFFs
and receipts were not altered or re-encoded. No claim of novelty is promoted.

## Pass 2 — tests, input provenance and independent remeasurement

Added isolated subprocess tests for empty args, former generation args,
`--help`, and `--force`, plus direct `main()` invocation. These verify exit 2,
explicit NOT OK TO SUBMIT output, no stdout success, and no output files,
without importing scientific dependencies or needing a network.

The first full test pass exposed absent pinned input rasters, not a successful
scientific run. `audit_priority_readiness.py --restore-only` restores the nine
historical files **only**, not the template/lattice prerequisites. Restored
those separately using the shared SHA-256-checked owner-mirror tool:

```sh
python scripts/restore_public_mirrors.py --ids sample_submission labels
python scripts/restore_public_mirrors.py --pins docs/research/2026-10-27-registry-preflight/lattice-pin.json --ids registry_lattice
python scripts/audit_priority_readiness.py --restore-only
python scripts/audit_priority_readiness.py --check
python scripts/verify_registry_preflight.py
python -m pytest -q
```

Offline nine-site remeasurement passes against the archived receipt. All nine
historical leaders fail the literal final-dot overlap rule (>99.90%); five pass
the shared format validator and four fail its outside-footprint convention.
The independent preflight reproduces the minimum 37,441/44,090 overlap and
historical CSR-1's measured 44,084/44,090. These are raster diagnostics, **not
performance scores**. Owner mirrors are not organizer-authenticated inputs.

## Pass 3 — requirement and scientific interpretation review

The executive table still provides exact historical filenames, source links,
format results, uniqueness status and an explicit unavailable estimate for each
of the nine sites. No file meets all requested gates, so no approved download,
new submission identity or note is offered. No weekly slot is consumed.

H33-B2's reported 0.2778 is an unverified owner claim, not an
ORGANIZER-CONFIRMED receipt. Its recorded lineage removes 2,545 near-catalogue
dots from 40,199, leaving 37,654. Reduced false-positive cost with preserved
triangular-kernel coverage is plausible, but the hidden TP/FP/FN decomposition
is unavailable; causality and a higher future score cannot be inferred. The
prompt's different current-best claims cannot establish today's leaderboard.

**Next scientific step:** resolve the registry-policy conflict and assign one
method lane before fitting or placement. Do not shrink the budget or optimize
against coverage holes to evade the literal rule. Then restore/check the full
cached stack, freeze buffered whole-segment folds and controls, derive all
catalogue features only from visible faults, run each feature's AUC canary, and
compare paired pooled HOLDOUT-DTI with a same-protocol best. Promotion requires
both novelty stages and the prescribed improvement gate; slot selection remains
separate. No claim is made that this blocked work fulfills the unique-TIFF goal.

## Source scope and access limitations

- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
  is the official code reference; it does not authenticate historical owner scores.
- [Competition problem/specification](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
  and [data portal](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
  are manual-review references, not newly fetched evidence in this follow-up.
- [Existing official-source check](2026-10-28-official-source-check.json)
  records the preceding audit's source checks; its date/scope have not been
  upgraded to a fresh independent literature review.
- Sandbox outbound hosts are restricted; no DrivenData session or authenticated
  submission receipt is available. The full competition feature cache has not
  been restored in this follow-up, and optional Torch tests may be skipped.
  No scientific experiment or leaderboard estimate is reported.

The success condition for this patch is a verified **negative safety stop**, not
a prize-winning raster. Remaining scientific blockers are explicit, not hidden
behind an inspection-only approval claim.

### Final verification receipt

With pinned prerequisites restored: `pytest -q` completed **437 passed, 5
skipped, 7 subtests passed** (four existing Rasterio deprecation warnings).
All skips concern optional Torch loss tests. `build_research_site.py --check`
passes after deterministic regeneration with a link to this review on the main
and per-site pages. The status feed was regenerated after restoring inputs;
its preflight verifier now reproduces the negative rather than reporting a
missing local template. These checks validate the safety change, not a new
scientific result or competition submission.

### Concurrent upstream addition during PR merge

Main advanced through PR #69 while this patch was being reviewed. Its
`gems30-unique-offlattice-structural-20261028-s8.tif` arrived from upstream,
not from this review. It is retained as historical evidence, but is **not unique**:
its decoded array (including NaNs) and grid match the existing s7 artifact
exactly. The s8 sidecar itself reports 1.0 maximum local dot overlap against s7,
yet its uniqueness boolean ignores that local result. This independently fails
the strict >70% rule. No new holdout is present. Resolved the site conflict by
regenerating from the receipt-driven renderer, removing the misleading new
“unique submission” promotion while preserving all upstream artifact bytes.
