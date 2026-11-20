# Changelog

## 0.1.0 (unreleased)

First release. A Python port of the R package
[oenb](https://github.com/franzmohr/oenb) 0.1.1.

* `oenb.toc()`, `oenb.dataset()`, `oenb.attributes()`, `oenb.frequency()`,
  `oenb.metadata()` and `oenb.data()` query the OeNB's data web service and
  return a `pandas.DataFrame`. The names of the R package are available as
  aliases (`oenb.oenb_toc()`, ...).
* `oenb.Client` holds the settings of the requests: the language, the timeout
  and the `requests.Session` to send them with.
* A failed request raises an exception that inherits from `oenb.OenbError`; a
  query without results warns with `oenb.NoResultsWarning` and returns an empty
  frame.
