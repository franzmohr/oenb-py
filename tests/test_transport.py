"""Tests of the requests that the package sends and of its error handling."""

from __future__ import annotations

import pytest
import requests
import responses

import oenb
from oenb._client import BASE_URL, as_sequence, check_lang, collapse, encode

from .conftest import fixture_path


class TestArguments:
    @pytest.mark.parametrize("lang", ["EN", "DE"])
    def test_supported_language_is_accepted(self, lang: str) -> None:
        assert check_lang(lang) == lang

    @pytest.mark.parametrize("lang", ["en", "FR", "", None, 1])
    def test_unsupported_language_is_rejected(self, lang: object) -> None:
        with pytest.raises(oenb.InvalidArgumentError, match="not supported"):
            check_lang(lang)  # type: ignore[arg-type]

    def test_invalid_argument_is_a_value_error(self) -> None:
        assert issubclass(oenb.InvalidArgumentError, ValueError)

    def test_reserved_characters_are_encoded(self) -> None:
        assert encode("a b&c=d/e") == "a%20b%26c%3Dd%2Fe"

    def test_numbers_are_encoded_as_text(self) -> None:
        assert encode(11) == "11"

    @pytest.mark.parametrize("value", [None, float("nan")])
    def test_missing_values_are_rejected(self, value: object) -> None:
        with pytest.raises(oenb.InvalidArgumentError, match="missing values"):
            encode(value)  # type: ignore[arg-type]

    def test_a_string_is_a_single_value(self) -> None:
        assert as_sequence("M") == ["M"]

    def test_a_list_is_kept(self) -> None:
        assert as_sequence(["M", "A"]) == ["M", "A"]

    def test_nothing_becomes_an_empty_list(self) -> None:
        assert as_sequence(None) == []

    def test_bytes_are_rejected(self) -> None:
        """Bytes are iterable; expanding them would query for their code points."""
        with pytest.raises(oenb.InvalidArgumentError, match="not bytes"):
            as_sequence(b"M")  # type: ignore[arg-type]

    def test_whitespace_is_collapsed(self) -> None:
        assert collapse("\n  a  b \n") == "a b"
        assert collapse(None) == ""


class TestUrl:
    def test_the_query_is_built_from_the_parameters(self) -> None:
        url = oenb.Transport().build_url("data", [("lang", "EN"), ("hierid", "11")])
        assert url == f"{BASE_URL}/data?lang=EN&hierid=11"

    def test_a_parameter_can_be_repeated(self) -> None:
        url = oenb.Transport().build_url("data", [("pos", "A"), ("pos", "B")])
        assert url == f"{BASE_URL}/data?pos=A&pos=B"

    def test_a_base_url_without_a_trailing_slash_is_used_as_given(self) -> None:
        url = oenb.Transport(base_url="http://example.org/svc/").build_url("meta", [])
        assert url == "http://example.org/svc/meta"


class TestFetch:
    @responses.activate
    def test_a_response_is_parsed(self) -> None:
        responses.add(responses.GET, f"{BASE_URL}/content", body="<xml><a/></xml>")
        root = oenb.Transport().fetch("content", [("lang", "EN")])
        assert root.tag == "xml"

    @responses.activate
    def test_the_user_agent_names_the_package(self) -> None:
        responses.add(responses.GET, f"{BASE_URL}/content", body="<xml/>")
        oenb.Transport().fetch("content", [])
        assert responses.calls[0].request.headers["User-Agent"] == f"oenb-python/{oenb.__version__}"

    @responses.activate
    def test_an_unreachable_service_raises(self) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/content",
            body=requests.ConnectionError("no route to host"),
        )
        with pytest.raises(oenb.ServiceUnavailableError, match="could not be reached") as info:
            oenb.Transport().fetch("content", [("lang", "EN")])
        assert info.value.url == f"{BASE_URL}/content?lang=EN"

    @responses.activate
    def test_a_server_error_raises(self) -> None:
        responses.add(responses.GET, f"{BASE_URL}/content", status=503)
        with pytest.raises(oenb.ServiceUnavailableError):
            oenb.Transport().fetch("content", [])

    @responses.activate
    def test_an_unparsable_response_raises(self) -> None:
        responses.add(responses.GET, f"{BASE_URL}/content", body="<xml><unclosed>")
        with pytest.raises(oenb.UnparsableResponseError, match="could not be parsed"):
            oenb.Transport().fetch("content", [])

    @responses.activate
    def test_an_error_of_the_service_is_passed_on(self) -> None:
        responses.add(
            responses.GET,
            f"{BASE_URL}/data",
            body=fixture_path("error").read_bytes(),
        )
        with pytest.raises(oenb.ServiceError) as info:
            oenb.Transport().fetch("data", [("pos", "XX")])
        assert info.value.service_message == 'Wrong Value for param "pos" (XX)'
        assert info.value.url == f"{BASE_URL}/data?pos=XX"

    @responses.activate
    def test_an_errors_element_without_a_message_is_ignored(self) -> None:
        responses.add(responses.GET, f"{BASE_URL}/data", body="<xml><errors>  </errors></xml>")
        assert oenb.Transport().fetch("data", []).tag == "xml"

    @responses.activate
    def test_an_errors_element_inside_the_response_is_not_an_error(self) -> None:
        body = "<OeNBData><data><errors>not mine</errors></data></OeNBData>"
        responses.add(responses.GET, f"{BASE_URL}/data", body=body)
        assert oenb.Transport().fetch("data", []).tag == "OeNBData"

    def test_every_error_of_the_package_has_a_common_base(self) -> None:
        for error in (
            oenb.InvalidArgumentError,
            oenb.ServiceError,
            oenb.ServiceUnavailableError,
            oenb.UnparsableResponseError,
        ):
            assert issubclass(error, oenb.OenbError)
