"""The public functions of the package.

Data are identified by the ID of a data set and the position code of a series
within it. Neither can be guessed, so a query is usually built in four steps:

1. :func:`toc` lists the data sets. Its column ``dataset_id`` is the ``id``
   argument of all other functions.
2. :func:`dataset` lists the series of a data set. Its column ``position_code``
   is the ``pos`` argument of the functions below.
3. :func:`attributes` and :func:`frequency` list the choices that narrow a
   query; :func:`metadata` describes a series, for example its unit and source.
4. :func:`data` downloads the observations.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import pandas as pd
import requests

from . import _parse
from ._client import BASE_URL, DEFAULT_TIMEOUT, Transport, as_sequence, check_lang, no_results

__all__ = ["Client", "attributes", "data", "dataset", "frequency", "metadata", "toc"]

Value = str | int | float
Many = Value | Iterable[Value]


class Client:
    """A client for the OeNB's data web service.

    The module-level functions use a client with the default settings. Create one
    of your own to change the timeout of a request, to reuse a
    :class:`requests.Session`, or to query the service in German by default::

        from oenb import Client

        client = Client(lang="DE", timeout=120)
        toc = client.toc()

    Args:
        lang: Preferred language of the descriptions in a result, ``"EN"`` or
            ``"DE"``. It is the default of every method and can be overridden per
            call.
        timeout: Timeout of a request, in seconds. ``None`` waits indefinitely.
        session: A :class:`requests.Session` to send the requests with.
        base_url: Base URL of the web service. Mainly useful for testing.
    """

    def __init__(
        self,
        lang: str = "EN",
        timeout: float | None = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
        base_url: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.lang = check_lang(lang)
        if transport is not None:
            self.transport = transport
        else:
            self.transport = Transport(
                base_url=BASE_URL if base_url is None else base_url,
                timeout=timeout,
                session=session,
            )

    def _lang(self, lang: str | None) -> str:
        return check_lang(self.lang if lang is None else lang)

    def toc(self, lang: str | None = None) -> pd.DataFrame:
        """Download the table of contents of the web service.

        Args:
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        Returns:
            A frame with one row per data set and the columns

            ``dataset_id``
                the ID of the data set, which is the ``id`` argument of the other
                functions.
            ``description``
                the title of the data set.

        Raises:
            ServiceUnavailableError: The service could not be reached.
            ServiceError: The service rejected the query.

        Warns:
            NoResultsWarning: The service did not return any data sets. The result
                is a frame without rows.
        """
        language = self._lang(lang)
        root = self.transport.fetch("content", [("lang", language)])
        result = _parse.parse_toc(root)
        if result.empty:
            no_results("The data web service of the OeNB did not return any data sets.")
        return result

    def dataset(self, id: Value, lang: str | None = None) -> pd.DataFrame:
        """Download a description of the contents of a data set.

        Args:
            id: ID of the data set of interest. See :func:`toc` to obtain it.
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        Returns:
            A frame with one row per series of the data set and the columns

            ``position_code``
                the position code of the series, which is the ``pos`` argument of
                the other functions.
            ``description``
                the title of the series.

        Warns:
            NoResultsWarning: The data set contains no series. The result is a
                frame without rows.
        """
        language = self._lang(lang)
        root = self.transport.fetch("content", [("lang", language), ("hierid", id)])
        result = _parse.parse_dataset(root, language)
        if result.empty:
            no_results(
                f'No indicators were found for data set "{id}". '
                "See oenb.toc() for available data set IDs."
            )
        return result

    def attributes(self, id: Value, pos: Value, lang: str | None = None) -> pd.DataFrame:
        """Get the potential attributes of a series.

        Args:
            id: ID of the data set of interest.
            pos: Position code of the series of interest. See :func:`dataset` to
                obtain it.
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        Returns:
            A frame with one row per available value of an attribute and the
            columns

            ``attribute_code``
                the code of the attribute, such as ``"dval1"``. It is a key of the
                ``attr`` argument of :func:`data`.
            ``attribute``
                the description of the attribute.
            ``value_code``
                the code of the value, such as ``"AT"``. It is a value of the
                ``attr`` argument of :func:`data`.
            ``value``
                the description of the value.

            Each value of an attribute is listed once. An attribute for which the
            service reports no value has one row with ``value_code`` and ``value``
            set to ``None``.

        Warns:
            NoResultsWarning: No attributes were found. The result is a frame
                without rows.
        """
        language = self._lang(lang)
        root = self.transport.fetch("content", [("lang", language), ("hierid", id), ("pos", pos)])
        result = _parse.parse_attributes(root)
        if result.empty:
            no_results(
                f'No attributes were found for position "{pos}" in data set "{id}". '
                "See oenb.dataset() for the position codes of a data set."
            )
        return result

    def frequency(self, id: Value, pos: Value, lang: str | None = None) -> pd.DataFrame:
        """Get the available frequencies and periods of a series.

        Args:
            id: ID of the data set of interest.
            pos: Position code of the series of interest.
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        Returns:
            A frame with the columns

            ``frequency``
                the code of a frequency, such as ``"M"``. It is a value of the
                ``freq`` argument of :func:`data`.
            ``available_period``
                the period for which data are available, as the web service
                describes it, for example ``"1998 - 2025"``.

            Each combination of a frequency and a period is listed once.

        Warns:
            NoResultsWarning: No frequencies were found. The result is a frame
                without rows.
        """
        language = self._lang(lang)
        root = self.transport.fetch(
            "datafrequency", [("lang", language), ("hierid", id), ("pos", pos)]
        )
        result = _parse.parse_frequency(root)
        if result.empty:
            no_results(
                f'No frequencies were found for position "{pos}" in data set "{id}". '
                "See oenb.dataset() for the position codes of a data set."
            )
        return result

    def metadata(self, id: Value, pos: Value, lang: str | None = None) -> pd.DataFrame:
        """Get the metadata of a series.

        Args:
            id: ID of the data set of interest.
            pos: Position code of the series of interest.
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        Returns:
            A frame with one row per field of the metadata and the columns

            ``attribute``
                the name of the field, for example ``"title"``, ``"unit"``,
                ``"source"`` or ``"last_update"``.
            ``description``
                the content of the field.

            The fields are those that the web service reports for the series.
            Fields that contain further fields are not included.

        Warns:
            NoResultsWarning: No metadata were found. The result is a frame
                without rows.
        """
        language = self._lang(lang)
        root = self.transport.fetch("meta", [("lang", language), ("hierid", id), ("pos", pos)])
        result = _parse.parse_metadata(root)
        if result.empty:
            no_results(
                f'No metadata were found for position "{pos}" in data set "{id}". '
                "See oenb.dataset() for the position codes of a data set."
            )
        return result

    def data(
        self,
        id: Value,
        pos: Many,
        freq: Many | None = None,
        attr: Mapping[str, Value] | None = None,
        starttime: Value | None = None,
        endtime: Value | None = None,
        lang: str | None = None,
    ) -> pd.DataFrame:
        """Download observations of one or more series.

        Args:
            id: ID of the data set of interest.
            pos: Position code of a series, or a sequence of position codes.
            freq: Frequency of the data. Where available, possible values are
                ``"D"``, ``"M"``, ``"Q"``, ``"H"`` and ``"A"`` for daily, monthly,
                quarterly, semi-annual and annual data. See :func:`frequency` to
                obtain the possible choices.
            attr: Further attributes of the series, for example
                ``{"dval1": "AT"}``. See :func:`attributes` to obtain the possible
                choices.
            starttime: Start of the series, see below.
            endtime: End of the series, see below.
            lang: Preferred language of the output, ``"EN"`` or ``"DE"``.

        ``starttime`` and ``endtime`` can have the format ``YYYY-MM-DD`` or
        ``YYYYMMDD`` for daily data, ``YYYY-MM`` or ``YYYYMM`` for monthly data,
        and ``YYYY`` for annual data. For semi-annual data ``YYYY-06`` refers to
        the first half of year ``YYYY`` and ``YYYY-12`` to the second. Similarly,
        for quarterly data ``YYYY-03``, ``YYYY-06``, ``YYYY-09`` and ``YYYY-12``
        refer to the first, second, third and fourth quarter of year ``YYYY``.

        Returns:
            A frame with one row per observation. The columns are those that the
            web service reports, typically

            ``period``
                the period of the observation, such as ``"2019-11"``.
            ``pos``, ``postitle``
                the position code and the title of the series.
            ``attr1``, ``attr1dim``, ``attr2``, ...
                the value of each attribute and the name of that attribute.
                ``attrN`` corresponds to the attribute ``dvalN`` of
                :func:`attributes`. Series with several values of an attribute
                have one row per value and period.
            ``freq``
                the frequency of the observation.
            ``unitmult``, ``unittext``
                the unit of the values, for example ``"6"`` and
                ``"in millions Euro"``.
            ``value``
                the numeric value, in the unit reported in ``unittext``. It is not
                rescaled.

            ``period`` is always the first column and ``value`` the last.

        Warns:
            NoResultsWarning: The query did not return any data. The result is a
                frame without rows and the columns ``period`` and ``value``.
        """
        language = self._lang(lang)
        params: list[tuple[str, Value]] = [("lang", language), ("hierid", id)]
        params.extend(("pos", value) for value in as_sequence(pos))
        params.extend(("freq", value) for value in as_sequence(freq))
        if attr is not None:
            params.extend((key, value) for key, value in attr.items())
        if starttime is not None:
            params.append(("starttime", starttime))
        if endtime is not None:
            params.append(("endtime", endtime))

        root = self.transport.fetch("data", params)
        result = _parse.parse_data(root)
        if result.empty:
            no_results(
                "The query did not return any data. See oenb.frequency() and "
                "oenb.attributes() for the available periods and attributes of a series."
            )
        return result


_default: Client | None = None


def _client() -> Client:
    """Return the client that the module-level functions use."""
    global _default
    if _default is None:
        _default = Client()
    return _default


def toc(lang: str = "EN") -> pd.DataFrame:
    """Download the table of contents of the web service.

    See :meth:`Client.toc`.
    """
    return _client().toc(lang=lang)


def dataset(id: Value, lang: str = "EN") -> pd.DataFrame:
    """Download a description of the contents of a data set.

    See :meth:`Client.dataset`.
    """
    return _client().dataset(id, lang=lang)


def attributes(id: Value, pos: Value, lang: str = "EN") -> pd.DataFrame:
    """Get the potential attributes of a series.

    See :meth:`Client.attributes`.
    """
    return _client().attributes(id, pos, lang=lang)


def frequency(id: Value, pos: Value, lang: str = "EN") -> pd.DataFrame:
    """Get the available frequencies and periods of a series.

    See :meth:`Client.frequency`.
    """
    return _client().frequency(id, pos, lang=lang)


def metadata(id: Value, pos: Value, lang: str = "EN") -> pd.DataFrame:
    """Get the metadata of a series.

    See :meth:`Client.metadata`.
    """
    return _client().metadata(id, pos, lang=lang)


def data(
    id: Value,
    pos: Many,
    freq: Many | None = None,
    attr: Mapping[str, Value] | None = None,
    starttime: Value | None = None,
    endtime: Value | None = None,
    lang: str = "EN",
) -> pd.DataFrame:
    """Download observations of one or more series.

    See :meth:`Client.data`.
    """
    return _client().data(
        id,
        pos,
        freq=freq,
        attr=attr,
        starttime=starttime,
        endtime=endtime,
        lang=lang,
    )
