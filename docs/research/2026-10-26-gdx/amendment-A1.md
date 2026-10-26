# A1 — technical recovery, NOT a tuning experiment

Declared after the saved full-fit surface audit, **before any dot placement,
holdout canary, or DTI was computed**. Original code and failure receipt are
preserved at Git commit `00b8509`; preregistration remains byte-unchanged.

The frozen registry has 328 aligned TIFF byte identities. Exactly one cannot
be compared on the full footprint: GEMSDOE31
`docs/downloads/gemsdoe31-csdu-stepover-8cf9dc27-nan.tif`, SHA-256
`774c7c5aa3784d7c52dc67870e1cc8b0e0a34d1697092ad9f3b08c33dcaf2546`,
at source commit `78f9bf3ae82e5c78ca348aa37c0660c339e72f0e`.
Current byte inspection found **2,610,312 non-finite cells inside** the official
owner-mirror template footprint. No imputation or reference replacement is
permitted. The other 327 surface comparisons exist; none is a duplicate.

The experiment runner's error guard paused before dots. It originally treated
any invalid reference as a technical stop; this amendment changes **only that
stop policy**: allow an exploratory, non-promotable continuation with this one
pinned invalid reference explicitly retained as unresolved evidence. A malformed
reference is not a measured duplicate and does not prove novelty either.

Recovery contract:

1. Reuse the exact saved `outputs/geothermal-chemistry/gdx1-surface.tif` whose
   SHA is in `novelty-surface.json`; **no refit**, no re-normalization, no new
   seed, method, feature, halo, budget, threshold, model, or emitted-dot change.
2. Verify cache, saved extra-feature hash, transform hash, registry hash and
   original preregistration. Preserve the first surface receipt unchanged.
3. Require 327 comparisons, the exact one missing hash above, and no other
   errors at BOTH stages. Any observed duplicate still stops permanently.
4. Continue only the frozen candidate, controls and 46px whole-component
   holdout, then the 17px raw-comparator parity check. Unresolved invalid
   reference plus absent original surfaces/global registry remain UNKNOWN
   novelty gates. **No upload approval, no slot, no global uniqueness claim.**
5. Conservatively count failed first attempt + recovery + parity as **3 of 3**
   experiments; elapsed budget is measured from the original started timestamp,
   including the pause. No fourth experiment, parameter rescue or fresh seed.
6. Publish a file only as research/audit if no valid observed reference triggers
   duplicate-stop and the shared file validator passes. Do not label the file
   a high-scoring or submission-ready artifact, regardless of the holdout point.

Shared tooling repair: `scripts/check_novelty.py` will include the reference
path in comparison errors so the next such failure is auditable without manual
set differencing. Invalid cells remain errors; correlation is never computed
only on a convenient finite subset. The complete original task is not satisfied
if no uniquely certified, high-scoring file can be promoted.
