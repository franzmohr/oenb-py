"""Tests of oenb.metadata()."""

from __future__ import annotations

import pytest

import oenb


def test_the_request_asks_the_meta_endpoint(recorded) -> None:
    client = recorded("metadata")
    client.metadata("11", "VDBFKBSC217000")
    assert client.transport.endpoint == "meta"
    assert client.transport.requests[-1][1] == [
        ("lang", "EN"),
        ("hierid", "11"),
        ("pos", "VDBFKBSC217000"),
    ]


def test_the_fields_of_the_metadata_are_returned(recorded) -> None:
    result = recorded("metadata").metadata("11", "VDBFKBSC217000")
    assert list(result.columns) == ["attribute", "description"]
    fields = dict(zip(result["attribute"], result["description"], strict=False))
    assert fields["title"] == "Loans to euro area residents - total"
    assert fields["unit"] == "Euro"
    assert fields["source"] == "OeNB"
    assert fields["frequency"] == "month"
    assert fields["last_update"] == "2026-09-14 07:01:37"


def test_nested_fields_are_skipped(recorded) -> None:
    """'data_available' and 'releases' hold further fields, not a value."""
    result = recorded("metadata").metadata("11", "VDBFKBSC217000")
    assert "data_available" not in set(result["attribute"])
    assert "releases" not in set(result["attribute"])
    assert len(result) == 10


def test_a_nested_field_with_one_entry_is_skipped_too(recorded) -> None:
    result = recorded("metadata_single").metadata("18", "VDBWWIRESTOTHFCA")
    assert "data_available" not in set(result["attribute"])
    assert result.loc[result["attribute"] == "title", "description"].iloc[0] == (
        "Other Foreign Currency Assets"
    )


def test_the_last_update_of_the_header_is_not_reported(recorded) -> None:
    """Only the metadata block describes the series; the header describes the response."""
    result = recorded("metadata").metadata("11", "VDBFKBSC217000")
    assert (result["attribute"] == "last_update").sum() == 1
    assert "prepared" not in set(result["attribute"])


def test_an_answer_without_metadata_warns_and_returns_no_rows(recorded) -> None:
    client = recorded("data_empty")
    with pytest.warns(oenb.NoResultsWarning, match="No metadata"):
        result = client.metadata("11", "VDBFKBSC217000")
    assert result.empty
    assert list(result.columns) == ["attribute", "description"]
