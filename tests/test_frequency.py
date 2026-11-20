"""Tests of oenb.frequency()."""

from __future__ import annotations

import pytest

import oenb


def test_the_request_asks_the_datafrequency_endpoint(recorded) -> None:
    client = recorded("frequency")
    client.frequency("11", "VDBFKBSC217000")
    assert client.transport.endpoint == "datafrequency"
    assert client.transport.requests[-1][1] == [
        ("lang", "EN"),
        ("hierid", "11"),
        ("pos", "VDBFKBSC217000"),
    ]


def test_the_frequencies_and_periods_are_returned(recorded) -> None:
    result = recorded("frequency").frequency("11", "VDBFKBSC217000")
    assert list(result.columns) == ["frequency", "available_period"]
    assert result["frequency"].tolist() == ["A", "M"]
    assert result.loc[result["frequency"] == "A", "available_period"].iloc[0] == "1998 - 2025"


def test_each_choice_is_listed_once(recorded) -> None:
    """The service reports a frequency once per combination of the attributes."""
    result = recorded("frequency_repeated").frequency("14", "VDBMSKREDITE")
    assert not result.duplicated().any()
    assert set(result["frequency"]) == {"A", "M"}
    assert len(result) == 7


def test_an_answer_without_frequencies_warns_and_returns_no_rows(recorded) -> None:
    client = recorded("data_empty")
    with pytest.warns(oenb.NoResultsWarning, match="No frequencies"):
        result = client.frequency("11", "VDBFKBSC217000")
    assert result.empty
    assert list(result.columns) == ["frequency", "available_period"]
