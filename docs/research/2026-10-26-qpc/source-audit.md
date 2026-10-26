# QPC-1 source and knowledge audit — 26 October 2026 UTC

This is a scientific and provenance audit, not a statement that a file is approved for
competition submission. The separately frozen [preregistration](preregistration.md),
[registry](registry.json) and eventual run card are authoritative for execution and evidence.

| Primary source | What it supports | What it does **not** establish |
|---|---|---|
| [USGS, Great Basin play-fairway study](https://www.usgs.gov/publications/discovering-blind-geothermal-systems-great-basin-region-integrated-geologic-and) | Multiple lines of structural, gravity, magnetic, thermal and geochemical evidence were combined; blind geothermal systems were investigated in Nevada, including drilling at two study areas. | A QPC anomaly is a geothermal vent, a proven fault, or an improved competition score. |
| [USGS, Granite Springs geophysical characterization](https://www.usgs.gov/publications/a-geophysical-characterization-structure-and-geology-northern-granite-springs-valley) | Gravity/magnetic interpretation can illuminate basin structure, faults and other geologic boundaries; dikes are a competing geological explanation. | Coincident gradients uniquely identify fault displacement. |
| [USGS, Saltus and Blakely on non-uniqueness](https://pubs.usgs.gov/publication/70032258) | Mathematically different subsurface models can explain similar potential fields; geological constraints and uncertainty are essential. | A purely numerical filter can resolve geological non-uniqueness. |
| [USGS GeoDAWN airborne magnetic and radiometric release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | A free USGS geophysical release relevant to the region exists; its documented distribution and reuse terms apply to that release. | The owner-mirrored competition channels were independently regenerated from those official grids or their physical units authenticated. |
| [DOE GDR 1391 / INGENIOUS](https://gdr.openei.org/submissions/1391) | The geothermal compilation and associated well/spring information are published under the stated CC BY 4.0 terms; attribution is required. | A local pinned owner CSV is an organizer-authenticated dataset or that records denote confirmed fault locations. It is **not** an input to QPC-1. |
| [Organizer's reference code, fixed commit](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | Public reference features and loss implementation are inspectable. | Reproducing that code confirms private labels, the hidden evaluator, or any portal score. |
| [Official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [September 2026 DOE/NLR rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | The published competition specifies a one-band float32 GeoTIFF, 100 m grid, EPSG:32611, predictions in [0,1], and null/NaN outside; the public metric uses a 300 m triangular distance kernel. The rules describe eligibility, limited feedback, and reproducibility obligations. | A local format pass proves portal acceptance; an owner-reported number is a submission-page receipt. Entrants must check the current rules, platform deadline and slot state themselves. |
| [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) | Terms restrict automated access/monitoring and manual monitoring/copying without prior written consent. | Permission to scrape the competition or build an automated leaderboard monitor. The repository status feed is derived only from this repository, not DrivenData. |

## Input lineage and scope

The experimental QPC transform uses the pinned owner mirror of the 19-band competition
feature stack, specifically its reduced-to-pole magnetic band (zero-based index 1) and
isostatic-gravity band (index 12), in addition to the 19-band base model. A separate pinned
owner mirror supplies the 17-channel LiDAR descriptor **only** for the fixed historical FFL
comparator replay. The labels and template are also pinned owner mirrors. Their SHA-256
identities, cache reconstruction checks, and registry commit pins are documented in the
preregistration and generated receipts. Integrity pinning prevents unnoticed byte changes; it
does **not** prove chain of custody from the organizer, correctness of band labels/units, or
license permission for every mirror. The organizer data page was login-gated; no credentials
were obtained or requested.

The QPC channels are co-located, dimensionless high-pass/gradient **proxies** at 1- and
3-pixel scales, not a literal Hilbert-transform phase calculation, independent confirmation of
hydrothermal flow, or a uniquely determined 3-D geological model. Lithologic contacts,
dikes, survey seams and near-surface cover can mimic fault-related responses. The fixed
within-field persistence control is intended to distinguish cross-field evidence from ordinary
single-field structure; it cannot eliminate all confounding.

The comparator FFL-1 was previously duplicate-stopped and is replayed only for a matched
research comparison. A post-stop inventory found unmerged [PR #41](https://github.com/buffedlizard55-lab/GEMSDOE30/pull/41)
with a potentially higher reported proxy but a 20 px guard and different visible/training
sets; it was neither independently reproduced nor included in the frozen registry. See
[parallel-inventory.json](parallel-inventory.json) and the 25 unscanned public PR heads in
[parallel-heads-inventory.json](parallel-heads-inventory.json). Mapped-fault holdout recovery, conditioned
on the available catalogue, is not an estimate of the hidden leaderboard. Original continuous
surfaces, malformed reference values, TIFFs outside the enumerated public paths, and private
or parallel work remain incompletely observed. No TIFF is certified globally unique from the
public snapshot.

## Score and error discipline

A HOLDOUT-DTI value must carry its evaluator version, positives and 95% confidence interval.
An organizer-confirmed score requires the user's actual submission-page receipt. Historical
owner claims are explicitly unverified, even when displayed next to a filename. There is no
defensible numerical leaderboard estimate from this evidence.

The reported portal error “Predicted values must be in range [0, 1]” has no associated file
hash or portal receipt here. Local validation checks every finite footprint value and NaN
placement against the pinned template, but cannot reconstruct the original rejection or prove
portal acceptance. Re-encoding a prior file is not a new hypothesis or an authorized fallback.
