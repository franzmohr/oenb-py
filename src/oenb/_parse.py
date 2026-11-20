"""Parsers that turn a response of the web service into a data frame.

Each function takes the root element of a parsed response and returns a
:class:`pandas.DataFrame`. The parsers pass on what the web service returns:
they do not rescale, repair or reinterpret the data.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence

import pandas as pd

from ._client import collapse, text_of

__all__ = [
    "parse_attributes",
    "parse_data",
    "parse_dataset",
    "parse_frequency",
    "parse_metadata",
    "parse_toc",
]

#: Name of the group of a data set that holds every series.
ALL_DATA = {"EN": "all data", "DE": "alle Daten"}

# Columns of the result of oenb.data() that hold an attribute of a series. The
# web service used to name them 'dvalN' and now names them 'attrN'; both are
# recognised so that the column order does not depend on the format of the day.
_ATTRIBUTE = re.compile(r"^(?:attr|dval)(\d+)(dim)?$")


def empty(columns: Sequence[str]) -> pd.DataFrame:
    """Return an empty frame with ``columns``, so that code expecting one works."""
    result: pd.DataFrame = pd.DataFrame({column: pd.Series(dtype="object") for column in columns})
    return result


def frame(rows: Sequence[Sequence[object]], columns: Sequence[str]) -> pd.DataFrame:
    """Return a frame of ``rows`` with ``columns`` and object dtype."""
    if not rows:
        return empty(columns)
    result: pd.DataFrame = pd.DataFrame(list(rows), columns=list(columns), dtype="object")
    return result


def parse_toc(root: ET.Element) -> pd.DataFrame:
    """Parse a response of the ``content`` endpoint without a data set ID."""
    rows = [(element.get("id", ""), text_of(element)) for element in root.iter("element")]
    return frame(rows, ["dataset_id", "description"])


def parse_dataset(root: ET.Element, lang: str) -> pd.DataFrame:
    """Parse a response of the ``content`` endpoint for one data set."""
    group = ALL_DATA[lang]
    rows = [
        (position.get("id", ""), text_of(position))
        for position in root.findall(f".//group[@name='{group}']//position")
    ]
    return frame(rows, ["position_code", "description"])


def parse_attributes(root: ET.Element) -> pd.DataFrame:
    """Parse a response of the ``content`` endpoint for one series.

    The structure of the series lists its attributes, the available data list the
    values that each attribute takes. The values of an attribute are reported once
    per combination of the attributes, so the same value arrives many times over.
    Each value is listed once.
    """
    columns = ["attribute_code", "attribute", "value_code", "value"]

    structure = [
        (dimension.get("nr", ""), text_of(dimension))
        for dimension in root.findall(".//structure/dimension")
    ]

    values: dict[str, list[tuple[str, str]]] = {}
    found_value = False
    for dimension in root.findall(".//data/dimension"):
        nr = dimension.get("nr", "")
        for value in dimension.findall("auspraegung"):
            found_value = True
            entry = (value.get("code", ""), text_of(value))
            seen = values.setdefault(nr, [])
            if entry not in seen:
                seen.append(entry)

    if not structure or not found_value:
        return empty(columns)

    rows: list[tuple[str, str, str | None, str | None]] = []
    for nr, attribute in structure:
        entries = values.get(nr)
        if entries:
            rows.extend((f"dval{nr}", attribute, code, text) for code, text in entries)
        else:
            # An attribute of the structure for which the service reports no
            # value. Its row is kept, so that the result lists every attribute of
            # the series, as the structure does.
            rows.append((f"dval{nr}", attribute, None, None))
    return frame(rows, columns)


def parse_frequency(root: ET.Element) -> pd.DataFrame:
    """Parse a response of the ``datafrequency`` endpoint.

    The service reports a frequency once per combination of the attributes of a
    series. Each combination of a frequency and a period is listed once.
    """
    rows: list[tuple[str, str]] = []
    for periods in root.iter("periods"):
        entry = (periods.get("frequency", ""), text_of(periods, "available"))
        if entry not in rows:
            rows.append(entry)
    return frame(rows, ["frequency", "available_period"])


def parse_metadata(root: ET.Element) -> pd.DataFrame:
    """Parse a response of the ``meta`` endpoint.

    Only the single-valued fields of the metadata block describe the series.
    Nested elements such as ``data_available`` or ``releases`` are skipped: their
    content would contribute the name of a child instead of the name of a field.
    """
    columns = ["attribute", "description"]
    meta = root.find(".//meta")
    if meta is None:
        return empty(columns)
    rows = [(field.tag, collapse(field.text)) for field in meta if len(field) == 0]
    return frame(rows, columns)


def _order_columns(columns: Sequence[str]) -> list[str]:
    """Return ``columns`` with the attributes of a series grouped and in order.

    The attributes are ordered by their number rather than by their name. Sorting
    the names would put ``attr10`` between ``attr1`` and ``attr2`` and separate an
    attribute from the column that describes it, because ``attr10`` comes before
    ``attr2`` alphabetically. Columns that are not attributes keep the place the
    web service gives them, before or after the block of attributes.
    """
    marks = [index for index, column in enumerate(columns) if _ATTRIBUTE.match(column)]
    if not marks:
        return list(columns)

    def key(index: int) -> tuple[int, int, str]:
        match = _ATTRIBUTE.match(columns[index])
        assert match is not None
        return (int(match.group(1)), 1 if match.group(2) else 0, columns[index])

    head = list(columns[: marks[0]])
    tail = list(columns[marks[-1] + 1 :])
    middle = [columns[index] for index in sorted(marks, key=key)]
    return head + middle + tail


def parse_data(root: ET.Element) -> pd.DataFrame:
    """Parse a response of the ``data`` endpoint.

    Every attribute that the service reports for a series becomes a column.
    ``period`` is always the first column and ``value`` the last. The values are
    reported in the unit given by ``unitmult`` and ``unittext`` and are not
    rescaled.
    """
    columns: list[str] = []
    rows: list[dict[str, object]] = []
    for series in root.iter("dataSet"):
        attributes = {key.lower(): value for key, value in series.attrib.items()}
        for key in attributes:
            if key not in columns:
                columns.append(key)
        for observation in series.findall("values/obs"):
            row: dict[str, object] = {"period": observation.get("periode", "")}
            row.update(attributes)
            row["value"] = observation.get("value")
            rows.append(row)

    if not rows:
        return empty(["period", "value"])

    order = ["period", *_order_columns(columns), "value"]
    result: pd.DataFrame = pd.DataFrame(rows, columns=order, dtype="object")
    # Always a float, so that the dtype of the column does not depend on whether
    # the values of a query happen to be whole numbers.
    result["value"] = pd.to_numeric(result["value"], errors="coerce").astype("float64")
    result = result.reset_index(drop=True)
    return result
