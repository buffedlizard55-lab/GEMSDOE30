"""Tests for the H-34-01 concealment prior (:mod:`gemsdoe30.concealment`).

The prior is the only place in the repository that encodes a *geological
interpretation* of an external archive rather than a measurement, so its contract has
to be pinned: an SGMC age string maps to one cover class by an explicit, monotone age
rule; a playa/lake setting escalates that class regardless of the mapped age; and the
weight that multiplies the evidence field is strictly positive and never able to
erase evidence.
"""

from __future__ import annotations

import numpy as np
import pytest

from gemsdoe30.concealment import (
    COVER_CLASS_TABLE,
    NODATA,
    classify_age,
    classify_units,
    cover_class,
    cover_weight,
    is_concealing_setting,
)


@pytest.mark.parametrize("age", ["Q", "Qa", "Qls", "Qf", "Qu", "Q  ", "q"])
def test_quaternary_age_strings_map_to_class_three(age):
    assert classify_age(age) == 3


@pytest.mark.parametrize("age", ["QT", "TQ", "QTs"])
def test_quaternary_tertiary_mixtures_are_basin_fill_not_bedrock(age):
    assert classify_age(age) == 2


@pytest.mark.parametrize("age", ["T", "Tv", "Ts", "Tb", "Tertiary", "Neogene", "Miocene"])
def test_tertiary_units_map_to_class_two(age):
    assert classify_age(age) == 2


@pytest.mark.parametrize("age", ["K", "Kv", "J", "Jtr", "Tr", "Mz", "Cretaceous", "Jurassic"])
def test_mesozoic_units_map_to_class_one(age):
    assert classify_age(age) == 1


@pytest.mark.parametrize("age", ["Pz", "pC", "Ar", "Z", "P", "C", "D", "S", "O", "", None, "  "])
def test_older_or_unknown_units_get_no_boost(age):
    assert classify_age(age) == 0


def test_spelled_out_ages_are_recognised():
    assert classify_age("Quaternary alluvium") == 3
    assert classify_age("Precambrian granite") == 0
    assert classify_age("Undivided Mesozoic rocks") == 1


@pytest.mark.parametrize(
    "text",
    ["playa", "Playa deposit", "dry lake", "SALT FLAT", "lacustrine clay", "evaporite"],
)
def test_concealing_settings_are_detected(text):
    assert is_concealing_setting(text)


def test_playa_escalates_an_otherwise_old_age_to_the_strongest_class():
    assert cover_class("Pz", "playa deposit") == 4
    assert cover_class("Qa", "alluvial fan") == 3
    assert cover_class("K", "marine shale") == 1
    assert cover_class("Qp", "playa lake") == 4


def test_classify_units_aligns_columns_and_rejects_ragged_input():
    classes = classify_units(["Qa", "Pz", "T"], [["alluvium", "playa", "basalt"]])
    assert classes == [3, 4, 2]
    with pytest.raises(ValueError):
        classify_units(["Qa", "Pz"], [["alluvium"]])


def test_cover_weight_is_monotone_positive_and_neutral_without_data():
    classes = np.array([[0, 1], [2, NODATA]], dtype=np.uint8)
    weight = cover_weight(classes, gamma=1.0)
    assert weight.tolist() == [[1.0, 1.25], [1.5, 1.0]]
    assert float(weight.min()) == 1.0
    # A hard ceiling of 1 + gamma keeps the prior from erasing or inventing evidence.
    assert float(cover_weight(np.array([[4]], dtype=np.uint8), gamma=1.0)[0, 0]) == 2.0
    assert float(cover_weight(np.array([[4]], dtype=np.uint8), gamma=0.5)[0, 0]) == 1.5
    # A value that is neither a documented class nor NODATA is a data error, not a
    # silent max-boost: the fetch script and this module must agree on the class table.
    with pytest.raises(ValueError):
        cover_weight(np.array([[99]], dtype=np.uint8), gamma=1.0)


def test_cover_weight_rejects_negative_gamma_and_bad_shape():
    with pytest.raises(ValueError):
        cover_weight(np.zeros((2, 2), dtype=np.uint8), gamma=-0.1)
    with pytest.raises(ValueError):
        cover_weight(np.zeros((2, 2, 2), dtype=np.uint8))


def test_class_table_documents_every_class_the_weight_can_emit():
    assert set(COVER_CLASS_TABLE) == {0, 1, 2, 3, 4}
    assert NODATA not in COVER_CLASS_TABLE
