"""Tests of oenb.data()."""

from __future__ import annotations

import pandas as pd
import pytest

import oenb


class TestQuery:
    def test_the_request_holds_every_choice(self, recorded) -> None:
        client = recorded("data")
        client.data(
            "11",
            "VDBFKBSC217000",
            freq="M",
            attr={"dval1": "AT"},
            starttime="2019-11",
            endtime="2019-12",
        )
        assert client.transport.endpoint == "data"
        assert client.transport.requests[-1][1] == [
            ("lang", "EN"),
            ("hierid", "11"),
            ("pos", "VDBFKBSC217000"),
            ("freq", "M"),
            ("dval1", "AT"),
            ("starttime", "2019-11"),
            ("endtime", "2019-12"),
        ]

    def test_a_choice_that_is_not_made_is_left_out(self, recorded) -> None:
        client = recorded("data")
        client.data("11", "VDBFKBSC217000")
        assert client.transport.requests[-1][1] == [
            ("lang", "EN"),
            ("hierid", "11"),
            ("pos", "VDBFKBSC217000"),
        ]

    def test_several_series_are_requested_as_several_parameters(self, recorded) -> None:
        client = recorded("data")
        client.data("11", ["A", "B"], freq=["M", "A"])
        assert client.transport.url.endswith("?lang=EN&hierid=11&pos=A&pos=B&freq=M&freq=A")

    def test_several_attributes_are_requested_as_several_parameters(self, recorded) -> None:
        client = recorded("data")
        client.data("11", "A", attr={"dval1": "AT", "dval3": "U2"})
        assert client.transport.url.endswith("&dval1=AT&dval3=U2")

    def test_a_missing_value_in_a_choice_is_rejected(self, recorded) -> None:
        client = recorded("data")
        with pytest.raises(oenb.InvalidArgumentError, match="missing values"):
            client.data("11", "A", attr={"dval1": None})  # type: ignore[dict-item]


class TestResult:
    def test_the_observations_are_returned(self, recorded) -> None:
        result = recorded("data").data("11", "VDBFKBSC217000")
        assert len(result) == 2
        assert result["period"].tolist() == ["2019-11", "2019-12"]
        assert result["value"].tolist() == [20494.0, 19254.0]

    def test_the_period_comes_first_and_the_value_last(self, recorded) -> None:
        result = recorded("data").data("11", "VDBFKBSC217000")
        assert result.columns[0] == "period"
        assert result.columns[-1] == "value"

    def test_the_value_is_numeric_even_for_whole_numbers(self, recorded) -> None:
        result = recorded("data_many_attributes").data("55", "VDBDFU55--KSALD--KUP")
        assert result["value"].dtype == "float64"
        assert result["value"].tolist() == [0.0, -4422.0, -1911.0, -416.0]

    def test_the_attributes_of_a_series_are_columns(self, recorded) -> None:
        result = recorded("data").data("11", "VDBFKBSC217000")
        assert list(result.columns) == [
            "period",
            "pos",
            "postitle",
            "attr1",
            "attr1dim",
            "attr2",
            "attr2dim",
            "attr3",
            "attr3dim",
            "attr4",
            "attr4dim",
            "freq",
            "unitmult",
            "unittext",
            "value",
        ]
        assert result["attr1"].iloc[0] == "AT"
        assert result["attr1dim"].iloc[0] == "PRODUZENT"
        assert result["unittext"].iloc[0] == "in millions Euro"

    def test_the_tenth_attribute_comes_after_the_second(self, recorded) -> None:
        """Sorting the names would put 'attr10' between 'attr1' and 'attr2'."""
        result = recorded("data_many_attributes").data("55", "VDBDFU55--KSALD--KUP")
        attributes = [column for column in result.columns if column.startswith("attr")]
        assert attributes == [
            f"attr{number}{suffix}" for number in range(1, 11) for suffix in ("", "dim")
        ]
        assert list(result.columns[-4:]) == ["freq", "unitmult", "unittext", "value"]

    def test_a_series_with_several_values_of_an_attribute_has_one_row_per_value(
        self, recorded
    ) -> None:
        result = recorded("data_many_attributes").data("55", "VDBDFU55--KSALD--KUP")
        assert result["period"].tolist() == ["2024"] * 4
        assert result["attr4"].tolist() == ["ABN", "KN", "000", "C19-22N"]

    def test_the_index_is_a_range(self, recorded) -> None:
        result = recorded("data_many_attributes").data("55", "VDBDFU55--KSALD--KUP")
        assert result.index.tolist() == [0, 1, 2, 3]

    def test_a_query_without_results_warns_and_returns_no_rows(self, recorded) -> None:
        client = recorded("data_empty")
        with pytest.warns(oenb.NoResultsWarning, match="did not return any data"):
            result = client.data("11", "VDBFKBSC217000", starttime="1899-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert list(result.columns) == ["period", "value"]
