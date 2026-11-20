"""Tests of oenb.toc()."""

from __future__ import annotations

import pytest

import oenb


def test_the_request_asks_the_content_endpoint_for_the_language(recorded) -> None:
    client = recorded("toc")
    client.toc()
    assert client.transport.endpoint == "content"
    assert client.transport.requests[-1][1] == [("lang", "EN")]


def test_the_language_of_a_call_overrides_the_default(recorded) -> None:
    client = recorded("toc", lang="EN")
    client.toc(lang="DE")
    assert client.transport.requests[-1][1] == [("lang", "DE")]


def test_an_unsupported_language_is_rejected_before_a_request(recorded) -> None:
    client = recorded("toc")
    with pytest.raises(oenb.InvalidArgumentError):
        client.toc(lang="FR")
    assert client.transport.requests == []


def test_the_data_sets_are_returned(recorded) -> None:
    result = recorded("toc").toc()
    assert list(result.columns) == ["dataset_id", "description"]
    assert len(result) == 40
    assert result.iloc[0].tolist() == ["1", "OeNB, Eurosystem and monetary indicators"]
    assert "11" in set(result["dataset_id"])


def test_entities_in_a_description_are_resolved(recorded) -> None:
    result = recorded("toc").toc()
    description = result.loc[result["dataset_id"] == "3101", "description"].iloc[0]
    assert description == "Balance Sheet and Profit & Loss Account - Selected Data"


def test_an_answer_without_data_sets_warns_and_returns_no_rows(recorded) -> None:
    client = recorded(None)
    with pytest.warns(oenb.NoResultsWarning, match="did not return any data sets"):
        result = client.toc()
    assert result.empty
    assert list(result.columns) == ["dataset_id", "description"]
