# oenb

Tools to access data from the data web service of the
[Oesterreichische Nationalbank (OeNB)](https://www.oenb.at/en/Statistics/User-Defined-Tables/webservice.html).

This is the Python counterpart of the R package
[oenb](https://github.com/franzmohr/oenb). It passes on what the web service
returns: it does not rescale, repair or reinterpret the data. No registration or
API key is required.

## Installation

```bash
pip install oenb
```

Or from a clone of this repository:

```bash
pip install -e ".[dev]"
```

## Workflow

Data are identified by the ID of a data set and the position code of a series
within it. Neither can be guessed, so a query is usually built in four steps.

```python
import oenb

# 1. The data sets. Column 'dataset_id' is the 'id' argument below.
toc = oenb.toc()

# 2. The series of a data set. Column 'position_code' is the 'pos' argument.
series = oenb.dataset(id="11")

# 3. The choices that narrow a query, and a description of the series.
oenb.attributes(id="11", pos="VDBFKBSC217000")
oenb.frequency(id="11", pos="VDBFKBSC217000")
oenb.metadata(id="11", pos="VDBFKBSC217000")

# 4. The observations.
x = oenb.data(
    id="11",
    pos="VDBFKBSC217000",
    freq="M",
    attr={"dval1": "AT"},
    starttime="2019-11",
    endtime="2019-12",
)
```

```
    period             pos                              postitle attr1 ... freq          unittext    value
0  2019-11  VDBFKBSC217000  Loans to euro area residents - total    AT ...    M  in millions Euro  20494.0
1  2019-12  VDBFKBSC217000  Loans to euro area residents - total    AT ...    M  in millions Euro  19254.0
```

The choices of step 3 map onto the arguments of `oenb.data` as follows:

* `attr` is a dictionary whose keys are values of the column `attribute_code`
  of `oenb.attributes` (`"dval1"`, `"dval2"`, ...) and whose values are taken
  from its column `value_code`, for example `attr={"dval1": "AT"}`.
* `freq` is a value of the column `frequency` of `oenb.frequency`, for example
  `"M"`.
* In the result of `oenb.data` the attribute `dvalN` is reported in the column
  `attrN`, and `attrNdim` names it.

`pos` and `freq` of `oenb.data` also accept a list, to request several series at
once.

## Results

Every function returns a `pandas.DataFrame` of object columns, except for the
column `value` of `oenb.data`, which is numeric. Values are reported in the unit
given by the columns `unittext` and `unitmult` and are not rescaled. The columns
of each result are described in the docstring of the function.

The argument `lang` selects the language of the descriptions in a result,
`"EN"` (default) or `"DE"`.

## Errors and empty results

A failed request raises an exception, a query without results warns and returns
an empty frame. Every exception inherits from `oenb.OenbError`, so that code can
react to a failure without matching the text of a message.

| Condition | Meaning |
| --- | --- |
| `ServiceUnavailableError` | The web service could not be reached. Retrying later may help. |
| `UnparsableResponseError` | The response of the web service was not valid XML. |
| `ServiceError` | The web service rejected the query. Its explanation is in the field `service_message`. |
| `InvalidArgumentError` | An argument was rejected before any request was sent. It is also a `ValueError`. |
| `NoResultsWarning` | The web service answered, but its answer contains nothing for the query. The result is a frame without rows. |

All exceptions except `InvalidArgumentError` have a field `url` holding the
request that was sent.

```python
import warnings

import oenb

# Tell an unavailable service apart from a query without results.
try:
    with warnings.catch_warnings():
        warnings.simplefilter("error", oenb.NoResultsWarning)
        x = oenb.data(id="11", pos="VDBFKBSC217000", starttime="1899-01", endtime="1899-12")
except oenb.NoResultsWarning:
    ...  # adjust the query
except oenb.ServiceUnavailableError:
    ...  # try again later
```

## Settings

The module-level functions use a client with the default settings. Create a
client of your own to change the timeout of a request, to reuse a
`requests.Session`, or to query the service in German by default.

```python
from oenb import Client

client = Client(lang="DE", timeout=120)
toc = client.toc()
```

## Differences from the R package

The functions, their arguments and the columns of their results are those of the
R package. Three things follow Python conventions instead:

* The functions are `oenb.toc()`, `oenb.dataset()`, ... rather than
  `oenb_toc()`, `oenb_dataset()`, ... The R names are available as aliases
  (`oenb.oenb_toc`, ...), so that ported code does not have to be renamed.
* Where the R package signals a condition and returns `NULL`, this package
  raises an exception; `oenb.data` returns an empty frame instead of `NULL` when
  a query has no results.
* A field of the metadata whose content is empty is reported as an empty string
  rather than dropped, and runs of whitespace inside a description are collapsed
  to a single space.

## Tests

```bash
pytest
```

The test suite runs against recorded responses of the web service in
`tests/fixtures/` and needs no internet connection. The tests that contact the
service are marked `live` and are deselected by default:

```bash
pytest -m live
```

## License

GPL-2.0-or-later, as the R package. See [LICENSE](LICENSE).
