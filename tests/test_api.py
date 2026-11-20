"""Tests of the module-level functions and of the client."""

from __future__ import annotations

import pytest
import requests

import oenb
from oenb import api

from .conftest import RecordingTransport


@pytest.fixture
def default(monkeypatch: pytest.MonkeyPatch):
    """Make the module-level functions answer with a recorded response."""

    def use(fixture: str) -> RecordingTransport:
        transport = RecordingTransport(fixture)
        monkeypatch.setattr(api, "_default", oenb.Client(transport=transport))
        return transport

    return use


class TestModuleFunctions:
    def test_toc(self, default) -> None:
        transport = default("toc")
        assert len(oenb.toc()) == 40
        assert transport.requests[-1] == ("content", [("lang", "EN")])

    def test_dataset(self, default) -> None:
        transport = default("dataset")
        assert len(oenb.dataset("11")) == 20
        assert transport.endpoint == "content"

    def test_attributes(self, default) -> None:
        transport = default("attributes")
        assert len(oenb.attributes("11", "VDBFKBSC217000")) == 4
        assert transport.endpoint == "content"

    def test_frequency(self, default) -> None:
        transport = default("frequency")
        assert len(oenb.frequency("11", "VDBFKBSC217000")) == 2
        assert transport.endpoint == "datafrequency"

    def test_metadata(self, default) -> None:
        transport = default("metadata")
        assert len(oenb.metadata("11", "VDBFKBSC217000")) == 10
        assert transport.endpoint == "meta"

    def test_data(self, default) -> None:
        transport = default("data")
        result = oenb.data(
            "11", "VDBFKBSC217000", freq="M", attr={"dval1": "AT"}, starttime="2019-11"
        )
        assert len(result) == 2
        assert transport.endpoint == "data"

    def test_the_language_reaches_the_request(self, default) -> None:
        transport = default("dataset_de")
        oenb.dataset("11", lang="DE")
        assert transport.requests[-1][1] == [("lang", "DE"), ("hierid", "11")]

    def test_the_default_client_is_created_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(api, "_default", None)
        assert api._client() is api._client()


class TestAliases:
    @pytest.mark.parametrize(
        ("alias", "function"),
        [
            ("oenb_toc", oenb.toc),
            ("oenb_dataset", oenb.dataset),
            ("oenb_attributes", oenb.attributes),
            ("oenb_frequency", oenb.frequency),
            ("oenb_metadata", oenb.metadata),
            ("oenb_data", oenb.data),
        ],
    )
    def test_the_names_of_the_r_package_are_available(self, alias: str, function) -> None:
        assert getattr(oenb, alias) is function

    def test_the_public_names_are_exported(self) -> None:
        for name in oenb.__all__:
            assert hasattr(oenb, name)


class TestClient:
    def test_the_language_of_the_client_is_the_default_of_a_call(self) -> None:
        client = oenb.Client(lang="DE", transport=RecordingTransport("dataset_de"))
        client.dataset("11")
        assert client.transport.requests[-1][1] == [("lang", "DE"), ("hierid", "11")]

    def test_an_unsupported_language_is_rejected_on_creation(self) -> None:
        with pytest.raises(oenb.InvalidArgumentError):
            oenb.Client(lang="FR")

    def test_the_settings_reach_the_transport(self) -> None:
        session = requests.Session()
        client = oenb.Client(timeout=5, session=session, base_url="http://example.org")
        assert client.transport.timeout == 5
        assert client.transport.session is session
        assert client.transport.build_url("meta", []) == "http://example.org/meta"

    def test_the_default_base_url_is_the_web_service(self) -> None:
        assert oenb.Client().transport.base_url == oenb.BASE_URL
        assert oenb.BASE_URL == "https://www.oenb.at/isadataservice"

    def test_the_package_has_a_version(self) -> None:
        assert oenb.__version__.count(".") == 2
