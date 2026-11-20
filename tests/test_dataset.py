"""Tests of oenb.dataset()."""

from __future__ import annotations

import pytest

import oenb


def test_the_request_names_the_data_set(recorded) -> None:
    client = recorded("dataset")
    client.dataset("11")
    assert client.transport.endpoint == "content"
    assert client.transport.requests[-1][1] == [("lang", "EN"), ("hierid", "11")]


def test_an_id_with_reserved_characters_is_encoded(recorded) -> None:
    client = recorded("dataset")
    client.dataset("a b&c")
    assert client.transport.url.endswith("?lang=EN&hierid=a%20b%26c")


def test_the_series_of_a_data_set_are_returned(recorded) -> None:
    result = recorded("dataset").dataset("11")
    assert list(result.columns) == ["position_code", "description"]
    assert len(result) == 20
    assert result.iloc[0].tolist() == [
        "VDBFKBSC217000",
        "Loans to euro area residents - total",
    ]


def test_the_german_group_is_read_for_german(recorded) -> None:
    result = recorded("dataset_de", lang="DE").dataset("11")
    assert len(result) == 20
    assert result.iloc[0]["position_code"] == "VDBFKBSC217000"
    assert result.iloc[0]["description"].startswith("Aktiva - Kredite")


def test_a_group_in_the_other_language_is_not_read(recorded) -> None:
    """The German response has no group 'all data', so an English call finds nothing."""
    client = recorded("dataset_de")
    with pytest.warns(oenb.NoResultsWarning):
        assert client.dataset("11").empty


def test_a_data_set_without_series_warns_and_returns_no_rows(recorded) -> None:
    client = recorded("dataset_empty")
    with pytest.warns(oenb.NoResultsWarning, match='data set "11"'):
        result = client.dataset("11")
    assert result.empty
    assert list(result.columns) == ["position_code", "description"]
