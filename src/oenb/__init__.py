"""oenb: tools for the data web service of the Oesterreichische Nationalbank.

Access the statistical data of the Oesterreichische Nationalbank (OeNB) through
its data web service, https://www.oenb.at/en/Statistics/User-Defined-Tables/webservice.html.
The package passes on what the web service returns. It does not rescale, repair
or reinterpret the data.

A query is usually built in four steps::

    import oenb

    toc = oenb.toc()                                  # the data sets
    series = oenb.dataset("11")                        # the series of a data set
    oenb.attributes("11", "VDBFKBSC217000")            # the choices of a query
    oenb.frequency("11", "VDBFKBSC217000")
    x = oenb.data("11", "VDBFKBSC217000", freq="M",
                  attr={"dval1": "AT"}, starttime="2019-01")

All functions return a :class:`pandas.DataFrame` of object columns, except for
the column ``value`` of :func:`data`, which is numeric. A result without rows
comes with a :class:`NoResultsWarning` saying why. A failed request raises an
:class:`OenbError`.

The names of the R package of the same name are available as aliases, so that
code can be ported without renaming the calls: ``oenb_toc``, ``oenb_dataset``,
``oenb_attributes``, ``oenb_frequency``, ``oenb_metadata`` and ``oenb_data``.
"""

from __future__ import annotations

__version__ = "0.1.0"

from ._client import BASE_URL, LANGUAGES, Transport
from ._exceptions import (
    InvalidArgumentError,
    NoResultsWarning,
    OenbError,
    RequestError,
    ServiceError,
    ServiceUnavailableError,
    UnparsableResponseError,
)
from .api import Client, attributes, data, dataset, frequency, metadata, toc

# Aliases that mirror the names of the R package.
oenb_attributes = attributes
oenb_data = data
oenb_dataset = dataset
oenb_frequency = frequency
oenb_metadata = metadata
oenb_toc = toc

__all__ = [
    "BASE_URL",
    "LANGUAGES",
    "Client",
    "InvalidArgumentError",
    "NoResultsWarning",
    "OenbError",
    "RequestError",
    "ServiceError",
    "ServiceUnavailableError",
    "Transport",
    "UnparsableResponseError",
    "__version__",
    "attributes",
    "data",
    "dataset",
    "frequency",
    "metadata",
    "oenb_attributes",
    "oenb_data",
    "oenb_dataset",
    "oenb_frequency",
    "oenb_metadata",
    "oenb_toc",
    "toc",
]
