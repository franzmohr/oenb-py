"""Tests of oenb.attributes()."""

from __future__ import annotations

import pytest

import oenb


def test_the_request_names_the_series(recorded) -> None:
    client = recorded("attributes")
    client.attributes("11", "VDBFKBSC217000")
    assert client.transport.endpoint == "content"
    assert client.transport.requests[-1][1] == [
        ("lang", "EN"),
        ("hierid", "11"),
        ("pos", "VDBFKBSC217000"),
    ]


def test_every_attribute_and_its_value_are_returned(recorded) -> None:
    result = recorded("attributes").attributes("11", "VDBFKBSC217000")
    assert list(result.columns) == ["attribute_code", "attribute", "value_code", "value"]
    assert len(result) == 4
    assert result["attribute_code"].tolist() == ["dval1", "dval2", "dval3", "dval4"]
    assert result.iloc[0].tolist() == ["dval1", "Data producer", "AT", "Austria"]


def test_hidden_attributes_are_included(recorded) -> None:
    result = recorded("attributes").attributes("11", "VDBFKBSC217000")
    assert "dval4" in set(result["attribute_code"])


def test_each_value_is_listed_once(recorded) -> None:
    """The service reports a value once per combination of the attributes."""
    result = recorded("attributes_repeated").attributes("14", "VDBMSKREDITE")
    assert len(result) == 17
    assert not result.duplicated().any()

    maturity = result[result["attribute_code"] == "dval4"]
    assert maturity["value_code"].tolist() == ["A", "F", "I", "J"]
    assert set(maturity["attribute"]) == {"Maturity"}


def test_the_attributes_keep_the_order_of_the_structure(recorded) -> None:
    result = recorded("attributes_repeated").attributes("14", "VDBMSKREDITE")
    numbers = [int(code.removeprefix("dval")) for code in result["attribute_code"]]
    assert numbers == sorted(numbers)
    assert numbers[0] == 1
    assert numbers[-1] == 9


def test_an_answer_without_attributes_warns_and_returns_no_rows(recorded) -> None:
    client = recorded("dataset")  # a response that holds no structure
    with pytest.warns(oenb.NoResultsWarning, match='position "VDBFKBSC217000"'):
        result = client.attributes("11", "VDBFKBSC217000")
    assert result.empty
    assert list(result.columns) == ["attribute_code", "attribute", "value_code", "value"]
