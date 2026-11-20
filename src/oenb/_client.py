"""Requests to the OeNB's data web service and parsing of its responses."""

from __future__ import annotations

import re
import warnings
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from urllib.parse import quote

import requests

from ._exceptions import (
    InvalidArgumentError,
    NoResultsWarning,
    ServiceError,
    ServiceUnavailableError,
    UnparsableResponseError,
)

__all__ = ["BASE_URL", "LANGUAGES", "Transport"]

#: Base URL of the OeNB's data web service.
BASE_URL = "https://www.oenb.at/isadataservice"

#: Languages supported by the web service.
LANGUAGES: tuple[str, ...] = ("DE", "EN")

#: Default timeout of a request, in seconds.
DEFAULT_TIMEOUT = 60.0

_WHITESPACE = re.compile(r"\s+")

QueryValue = str | int | float
Params = Sequence[tuple[str, QueryValue]]


def check_lang(lang: str) -> str:
    """Return ``lang`` if the web service supports it, raise otherwise."""
    if not isinstance(lang, str) or lang not in LANGUAGES:
        raise InvalidArgumentError(
            'Specified language is not supported. Possible values are "DE" and "EN".'
        )
    return lang


def encode(value: QueryValue) -> str:
    """Percent-encode a value that is pasted into a query string.

    Arguments containing reserved characters would otherwise produce a malformed
    URL. ``None`` would silently become the string ``"None"`` and produce a query
    that cannot be answered, so it is rejected instead.
    """
    if value is None or isinstance(value, bool):
        raise InvalidArgumentError("Arguments of a query must not contain missing values.")
    if isinstance(value, float) and value != value:  # NaN
        raise InvalidArgumentError("Arguments of a query must not contain missing values.")
    return quote(str(value), safe="")


def as_sequence(value: QueryValue | Iterable[QueryValue] | None) -> list[QueryValue]:
    """Return ``value`` as a list, treating a string as a single value."""
    if value is None:
        return []
    if isinstance(value, bytes):
        raise InvalidArgumentError("Arguments of a query must be text or numbers, not bytes.")
    if isinstance(value, str) or not isinstance(value, Iterable):
        return [value]
    return list(value)


def collapse(text: str | None) -> str:
    """Collapse runs of whitespace in ``text`` and strip it."""
    if text is None:
        return ""
    return _WHITESPACE.sub(" ", text).strip()


def no_results(message: str, stacklevel: int = 3) -> None:
    """Warn that the answer of the web service contains nothing for the query."""
    warnings.warn(message, NoResultsWarning, stacklevel=stacklevel)


class Transport:
    """Sends requests to the web service and returns the parsed response.

    Args:
        base_url: Base URL of the web service. Mainly useful for testing.
        timeout: Timeout of a request, in seconds.
        session: A :class:`requests.Session` to send the requests with. A session
            of its own is created if none is given.
        user_agent: Value of the ``User-Agent`` header.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: float | None = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        user_agent: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session if session is not None else requests.Session()
        if user_agent is None:
            from . import __version__

            user_agent = f"oenb-python/{__version__}"
        self.user_agent = user_agent

    def build_url(self, endpoint: str, params: Params) -> str:
        """Return the URL of a request to ``endpoint``.

        The query string is built by hand rather than by :mod:`requests`, so that
        a parameter can be repeated - the web service expects several series as
        several ``pos`` parameters - and so that the URL of a failed request can
        be reported verbatim.
        """
        query = "&".join(f"{encode(key)}={encode(value)}" for key, value in params)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return f"{url}?{query}" if query else url

    def fetch(self, endpoint: str, params: Params) -> ET.Element:
        """Download and parse an XML document from the web service.

        Raises:
            ServiceUnavailableError: The service could not be reached.
            UnparsableResponseError: The response was not valid XML.
            ServiceError: The service reported a problem with the query itself.
        """
        url = self.build_url(endpoint, params)
        try:
            response = self.session.get(
                url, timeout=self.timeout, headers={"User-Agent": self.user_agent}
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ServiceUnavailableError(
                "The data web service of the OeNB could not be reached. Please check your "
                f"internet connection and try again later. ({exc})",
                url=url,
            ) from exc

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise UnparsableResponseError(
                "The response of the data web service of the OeNB could not be parsed.",
                url=url,
            ) from exc

        # Only an 'errors' element directly below the root reports a problem with
        # the query. Anchoring the path keeps a node of that name somewhere inside
        # a regular response from being mistaken for one. An element without a
        # message is ignored, so that an empty one cannot raise an error without a
        # reason.
        messages = [collapse("".join(node.itertext())) for node in root.findall("errors")]
        messages = [message for message in messages if message]
        if messages:
            service_message = " ".join(messages)
            raise ServiceError(
                f"The data web service of the OeNB returned an error: {service_message}",
                url=url,
                service_message=service_message,
            )

        return root


def text_of(node: ET.Element | None, child: str = "text") -> str:
    """Return the text of ``node``'s ``child`` element, or of ``node`` itself."""
    if node is None:
        return ""
    found = node.find(child)
    source = node if found is None else found
    return collapse("".join(source.itertext()))
