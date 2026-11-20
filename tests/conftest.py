"""Helpers for testing against recorded responses of the OeNB's data web service.

The files in ``fixtures/`` are verbatim responses of the web service. Using them
keeps the test suite independent of an internet connection and makes a future
change of the service's output format visible as a failing test.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

import pytest

from oenb import BASE_URL, Client, Transport

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_path(name: str) -> Path:
    """Return the path of a recorded response."""
    return FIXTURES / f"{name}.xml"


def fixture_root(name: str) -> ET.Element:
    """Parse a recorded response the way the transport would."""
    return ET.fromstring(fixture_path(name).read_bytes())


class RecordingTransport(Transport):
    """A transport that answers with a recorded response instead of a request.

    It records what was requested, so that both the parsing of a response and the
    building of a query can be tested without contacting the web service.
    """

    def __init__(self, fixture: str | None = None) -> None:
        super().__init__(session=None)
        self.fixture = fixture
        self.requests: list[tuple[str, list[tuple[str, object]]]] = []

    def fetch(self, endpoint: str, params: Sequence[tuple[str, object]]) -> ET.Element:
        # The URL is built the way the real transport builds it, so that the
        # arguments of a query are validated and encoded here as well.
        self.build_url(endpoint, params)
        self.requests.append((endpoint, list(params)))
        if self.fixture is None:
            return ET.fromstring(b"<OeNBData><data/></OeNBData>")
        return fixture_root(self.fixture)

    @property
    def endpoint(self) -> str:
        """The endpoint of the last request."""
        return self.requests[-1][0]

    @property
    def url(self) -> str:
        """The URL of the last request, as the real transport would build it."""
        endpoint, params = self.requests[-1]
        return self.build_url(endpoint, params)


@pytest.fixture
def transport() -> RecordingTransport:
    """A transport that answers every request with an empty response."""
    return RecordingTransport()


@pytest.fixture
def recorded():
    """A factory for a client that answers with a given recorded response."""

    def make(fixture: str | None = None, lang: str = "EN") -> Client:
        return Client(lang=lang, transport=RecordingTransport(fixture))

    return make


@pytest.fixture
def base_url() -> str:
    """The base URL of the web service."""
    return BASE_URL
