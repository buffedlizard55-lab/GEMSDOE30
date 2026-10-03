# Three-pass review and scientific decision — 2026-10-03

1. **Implementation:** restored immutable owner mirrors, validated metadata/range, prepared data, preregistered four hypotheses and a generic context control, ran four-arm/four-fold real spatial pilot. Published small reference TIFF, not training data.
2. **Bugs/assumptions:** equal model capacity and raw-channel normalization across arms; no labels in engineered features; 800 m buffer covers 500 m filter support plus 300 m metric. Missing features imputed identically, full shared scoring footprint. Template contains 60,988 labelled pixels contrary to absence-template wording; never used its values. Hash integrity does not certify organizer origin. 25 tests pass, diff whitespace check passes.
3. **Acceptance recheck:** failed candidate withheld, no slot. R regional DTI .05769261; G geometry .05769885; C context .05778799; H interaction .05772284. H loses to C by .00006515 (required +.002). R/G best-credit distance counts are identical: **no demonstrated geometry-induced change in near-miss choices in this pilot**. Medical boundary-loss gains do not establish geological gains. Full JSON includes hashes, per-fold diagnostics and FP distance mass. No confirmation triggered.

## Why dotting can help, and what remains unknown

The official DTI uses max nearby confidence per truth pixel, not a sum of overlapping coverage. Removing redundant dots can reduce FP mass while preserving much TP credit. With alpha=.2, beta=.8, the denominator is .2 TP + .2 FP + .8 |G| + epsilon. An added prediction is beneficial only if its marginal coverage credit outweighs its marginal FP cost at the current ratio. This explains a plausible advantage of D2.8 thinning; it does **not prove** which hidden faults were found or that these exact bytes earned .2600. The official leaderboard snapshot shows DARD .3195 and wbg1 .2600 but no file hashes. Owner pages conflict with file-score attribution.

Above .3195 remains an objective, not a supported forecast. Prioritize full-capacity spatial context, component-heldout validation, independent blind-upflow data, and marginal-credit-aware emission after model ranking improves. Do not infer hidden truth counts from leaderboard fits as observations. Catalogue holdout can reward familiar faults and is not the expert new-fault distribution.

## Next session

- Authenticate mirrors against authorized organizer downloads and exact band semantics, especially tc, earthquake and conductive-depth aliases.
- Run the existing paired U-Net pipeline with adequate compute; negative-only soft-Tversky gradients may be weak (epsilon numerator), requiring a preregistered BCE/regional control rather than post-hoc tuning.
- Match a reproducible current-best comparator and fault-component proxy before any slot approval. Catalogue geometry must hide heldout components.
- Retrieve official GDR probe/deposit archives (direct TLS remains blocked), verify coverage/attribution before testing.
- No autonomous DrivenData monitor/upload. GitHub Pages already configured for main/root. Only small audited reference output committed.
