"""Exceptions and warnings raised by :mod:`oenb`.

Every exception of the package inherits from :class:`OenbError`, so that calling
code can react to a failure without matching the text of a message.
"""

from __future__ import annotations

__all__ = [
    "InvalidArgumentError",
    "NoResultsWarning",
    "OenbError",
    "ServiceError",
    "ServiceUnavailableError",
    "UnparsableResponseError",
]


class OenbError(Exception):
    """Base class of all errors raised by this package."""


class InvalidArgumentError(OenbError, ValueError):
    """An argument was rejected before any request was sent."""


class RequestError(OenbError):
    """Base class of errors that concern a request that was sent.

    Attributes:
        url: The request that was sent.
    """

    def __init__(self, message: str, url: str) -> None:
        super().__init__(message)
        self.url = url


class ServiceUnavailableError(RequestError):
    """The web service could not be reached. Retrying later may help."""


class UnparsableResponseError(RequestError):
    """The response of the web service was not valid XML."""


class ServiceError(RequestError):
    """The web service rejected the query.

    Attributes:
        url: The request that was sent.
        service_message: The explanation reported by the web service.
    """

    def __init__(self, message: str, url: str, service_message: str) -> None:
        super().__init__(message, url)
        self.service_message = service_message


class NoResultsWarning(UserWarning):
    """The web service answered, but its answer contains nothing for the query.

    The function returns an empty :class:`pandas.DataFrame` with the documented
    columns. Use :func:`warnings.simplefilter` with ``"error"`` to turn this
    warning into an exception.
    """
