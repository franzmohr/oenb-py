"""Tests that contact the OeNB's data web service.

They are marked 'live' and are deselected by default. Run them with

    pytest -m live

to see whether the service still answers the way the recorded responses in
'fixtures/' do. A failure here means that the service changed or is unavailable,
not necessarily that the package is broken.
"""

from __future__ import annotations

import pytest

import oenb

pytestmark = pytest.mark.live

ID = "11"
POS = "VDBFKBSC217000"


@pytest.fixture(scope="module")
def client() -> oenb.Client:
    return oenb.Client(timeout=120)


def test_toc(client: oenb.Client) -> None:
    result = client.toc()
    assert list(result.columns) == ["dataset_id", "description"]
    assert ID in set(result["dataset_id"])


def test_dataset(client: oenb.Client) -> None:
    result = client.dataset(ID)
    assert POS in set(result["position_code"])


def test_attributes(client: oenb.Client) -> None:
    result = client.attributes(ID, POS)
    assert list(result.columns) == ["attribute_code", "attribute", "value_code", "value"]
    assert "dval1" in set(result["attribute_code"])


def test_frequency(client: oenb.Client) -> None:
    result = client.frequency(ID, POS)
    assert "M" in set(result["frequency"])


def test_metadata(client: oenb.Client) -> None:
    result = client.metadata(ID, POS)
    assert "title" in set(result["attribute"])


def test_data(client: oenb.Client) -> None:
    result = client.data(
        ID, POS, freq="M", attr={"dval1": "AT"}, starttime="2019-11", endtime="2019-12"
    )
    assert result["period"].tolist() == ["2019-11", "2019-12"]
    assert result["value"].dtype == "float64"
    assert result["value"].tolist() == [20494.0, 19254.0]


def test_a_wrong_position_is_reported_by_the_service(client: oenb.Client) -> None:
    with pytest.raises(oenb.ServiceError) as info:
        client.data(ID, "XX")
    assert "pos" in info.value.service_message
