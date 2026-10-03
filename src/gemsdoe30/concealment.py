"""H-34-01 substrate-concealment prior: map-unit age/lithology -> observability weight.

Why this exists (see ``docs/hypotheses.md`` §H-34 register, rank 1)
------------------------------------------------------------------
Every earlier hypothesis in this repository added *evidence* (scarp, magnetic edge,
corridor, proximity).  None modelled the process that produced the labels.  A
geological map is a mapping-effort product: a trace is drawn where rock is exposed
well enough for a geologist to see and follow it.  Faults under playa, lake beds,
young basin fill and Quaternary cover are therefore under-represented in *any*
surface catalogue, while the organizer's scored faults are by construction the ones
that such a catalogue lacks.  The prior below does not predict where a fault is
visible; it predicts where a *missing* fault is most likely to hide, so that limited
evidence can be spent there.

Class definition (frozen before any experiment, recorded in
``docs/research/h34-01-concealment-preregistration.md``)
--------------------------------------------------------
``0`` pre-Cenozoic / undivided bedrock or unmapped  (no boost)
``1`` Mesozoic to Paleogene indurated units           (weak boost)
``2`` Neogene / Tertiary basin fill and volcanics     (moderate boost)
``3`` Quaternary surficial cover                      (strong boost)
``4`` playa, lake bed, evaporite, salt flat           (strongest boost)

The class is taken from the SGMC map-unit ``AGE`` string, escalated to ``4`` when any
unit text (name, lithology, description) names a playa/lake/evaporite setting.  The
prior itself is a strictly monotone multiplicative weight ``1 + gamma * class / 4``:
a weight of 1 is neutral, and the largest boost with ``gamma = 1`` doubles belief.
It is applied to an existing evidence field, so it can only re-allocate the same
evidence, never create evidence where there is none — which is exactly the property
that makes the mandatory distance-matched control meaningful (see
``docs/research/h34-01-concealment-preregistration.md``).
"""

from __future__ import annotations

from typing import Any, Iterable

NODATA = 255

COVER_CLASS_TABLE = {
    0: "pre-Cenozoic bedrock / undivided / unmapped",
    1: "Mesozoic-Paleogene indurated units",
    2: "Neogene-Tertiary basin fill and volcanics",
    3: "Quaternary surficial cover",
    4: "playa / lake bed / evaporite / salt flat",
}

#: Text fragments that mark a depositional setting that conceals structure.
_PLAYA_TERMS = (
    "playa",
    "dry lake",
    "lake bed",
    "lakebed",
    "lake deposit",
    "lacustrine",
    "salt flat",
    "salina",
    "evaporite",
    "saline",
    "salt pan",
    "lake",
)

#: Map-unit *labels* that are water bodies rather than rocks.  These are matched
#: exactly (never as a substring of a long description) so that a description
#: mentioning, say, ground water cannot escalate a bedrock unit to the strongest
#: concealment class.
_WATER_LABEL_TOKENS = ("WATER", "WTR", "LAKE", "RESERVOIR", "POND", "PLAYA", "ICE", "GLACIER")

#: Mesozoic age markers (spelled out or abbreviated).
_MESOZOIC_TERMS = (
    "cretaceous",
    "jurassic",
    "triassic",
    "mesozoic",
)

#: Tertiary age markers.
_TERTIARY_TERMS = (
    "tertiary",
    "neogene",
    "paleogene",
    "miocene",
    "pliocene",
    "oligocene",
    "eocene",
    "paleocene",
)

#: Quaternary markers spelled out.
_QUATERNARY_TERMS = ("quaternary", "holocene", "pleistocene")


def _normalise(text: Any) -> str:
    """Upper-case, whitespace-collapsed text (``None`` and NaN become empty)."""

    if text is None:
        return ""
    try:
        if text != text:  # NaN
            return ""
    except Exception:  # noqa: BLE001 - non-comparable objects fall through to str()
        pass
    return " ".join(str(text).upper().split())


def _first_token(text: str) -> str:
    """The first alphabetic token of an SGMC age string (``"Qa"`` -> ``"Q"``)."""

    for character in text:
        if character.isalpha():
            letters = []
            for rest in text[text.index(character):]:
                if rest.isalpha():
                    letters.append(rest)
                else:
                    break
            return "".join(letters)
    return ""


def classify_age(age: Any) -> int:
    """Map an SGMC ``AGE`` value to a cover class in ``{0, 1, 2, 3}``.

    The rules are intentionally coarse: at 100 m resolution the difference between
    one Cretaceous unit and another is irrelevant, the difference between bedrock and
    young cover is not.
    """

    text = _normalise(age)
    if not text:
        return 0
    lowered = text.lower()
    for term in _QUATERNARY_TERMS:
        if term in lowered:
            return 3
    # Quaternary-Tertiary or Tertiary-Quaternary mixtures are basin fill first.
    token = _first_token(text)
    if token.startswith("QT") or token.startswith("TQ"):
        return 2
    for term in _TERTIARY_TERMS:
        if term in lowered:
            return 2
    if token.startswith("Q"):
        return 3
    for term in _MESOZOIC_TERMS:
        if term in lowered:
            return 1
    for prefix in ("K", "J", "TR", "TRJ", "TRK", "JK", "MZ"):
        if token.startswith(prefix):
            return 1
    if token.startswith("T"):
        return 2
    return 0


def matched_setting_terms(*texts: Any) -> list[str]:
    """The concealing-setting terms present in any supplied text (deduplicated).

    Exposed so a run can *record* which term escalated a unit, instead of publishing an
    unexplained class-4 share of the map.
    """

    hits: list[str] = []
    for text in texts:
        lowered = _normalise(text).lower()
        if not lowered:
            continue
        for term in _PLAYA_TERMS:
            if term in lowered and term not in hits:
                hits.append(term)
    return hits


def label_is_water(age: Any) -> bool:
    """True when a map-unit label is itself a water body (``water``, ``lake``...)."""

    token = _first_token(_normalise(age))
    return bool(token) and token in _WATER_LABEL_TOKENS


def is_concealing_setting(*texts: Any) -> bool:
    """True when any supplied text names a playa/lake/evaporite setting."""

    return bool(matched_setting_terms(*texts))


def cover_class(age: Any, *unit_texts: Any) -> int:
    """Cover class for one map unit: age class escalated to 4 by its setting text.

    ``unit_texts`` are any other attribute strings that carry the deposit
    description (name, lithology, rock type, descriptive text).  A playa or lake is
    mapped to class 4 regardless of the age string, because an evaporite/water
    setting hides structure even when the mapped age string is older — and the SGMC
    water polygons carry the label ``water`` rather than an age letter, so the label
    itself is scanned too.
    """

    if label_is_water(age) or is_concealing_setting(*unit_texts):
        return 4
    return classify_age(age)


def classify_units(
    age_values: Iterable[Any],
    unit_text_columns: Iterable[Iterable[Any]] = (),
) -> list[int]:
    """Vectorised form of :func:`cover_class` over parallel attribute columns.

    ``age_values`` and every column in ``unit_text_columns`` must share a length;
    column *i* of the result is the class of the map unit described by row *i*.
    """

    ages = list(age_values)
    columns = [list(column) for column in unit_text_columns]
    for column in columns:
        if len(column) != len(ages):
            raise ValueError("attribute columns must share a length")
    return [
        cover_class(ages[index], *[column[index] for column in columns])
        for index in range(len(ages))
    ]


def cover_weight(classes: Any, *, gamma: float = 1.0) -> Any:
    """Multiplicative belief weight ``1 + gamma * class / 4`` for a class raster.

    ``gamma = 1`` maps classes 0..4 to weights 1.00, 1.25, 1.50, 1.75, 2.00.  The
    weight is never zero, so the prior always *re-weights* the evidence field and
    never erases it.  ``NODATA`` (255) maps to a neutral 1.0.  Any other value is a
    data error rather than a class, and raises: a silent clamp would hide a class
    table mismatch between the fetch script and this module.
    """

    import numpy as np

    if gamma < 0:
        raise ValueError("gamma must be non-negative")
    array = np.asarray(classes)
    if array.ndim != 2:
        raise ValueError("classes must be two-dimensional")
    values = np.unique(array)
    allowed = set(range(5)) | {NODATA}
    unexpected = [int(v) for v in values if int(v) not in allowed]
    if unexpected:
        raise ValueError(f"unexpected cover class values: {unexpected}")
    numeric = array.astype(np.float64, copy=False)
    neutral = array == NODATA
    clamped = np.where(neutral, 0.0, np.clip(numeric, 0.0, 4.0))
    return np.where(neutral, 1.0, 1.0 + float(gamma) * clamped / 4.0).astype(np.float32)
