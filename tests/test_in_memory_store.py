from datetime import datetime, timezone
from typing import Any

import pytest

from dyna_store import (
    InMemoryDynaStore,
    MetadataId,
)


def test_simple_case():
    dyna_store = InMemoryDynaStore(hcf=["high"])
    id = dyna_store.create(low=1, high=0)
    assert id == "6efcd187bd-a"
    metadata = dyna_store.parse(id)
    assert metadata.get("low") == 1
    assert metadata.get("high") == 0


class Recommendation:
    # All types must be annotated with their cardinality.
    user_id: int
    timestamp: datetime
    algorithm: str
    job_id: int | None = None
    score: float | None = None
    rank: int | None = None
    promoted: float | None = False
    campaign_id: str | None = None


def test_more_complex_case():
    store = InMemoryDynaStore(hcf=["user_id", "timestamp", "score"])
    user_id = 435543
    now = datetime(2023, 12, 1, 14, 2, 4, tzinfo=timezone.utc)
    data: dict[str, Any] = {
        "user_id": user_id,
        "timestamp": now,
        "algorithm": "stub-algo",
    }
    id = store.create(**data)
    assert id == "058e7a7ff3-bZs3b1jefU"
    assert store.parse(id) == data

    data = {
        "user_id": user_id,
        "timestamp": now,
        "algorithm": "stub-algo",
        "score": 0.1232432,
        "campaign_id": "cid",
    }
    id = store.create(**data)
    assert id == "e4286ec165-bZs3b1jefUbixG42"
    assert store.parse(id).get("user_id") == data.get("user_id")
    assert store.parse(id).get("timestamp") == data.get("timestamp")
    assert store.parse(id).get("algorithm") == data.get("algorithm")
    assert store.parse(id).get("campaign_id") == data.get("campaign_id")
    assert abs(store.parse(id).get("score") - data.get("score")) < 1e-6  # type: ignore


def test_invalid_id():
    store = InMemoryDynaStore(hcf=[])
    id_ = "abc:def"
    with pytest.raises(ValueError, match=id_):
        store.parse(id_)


def test_invalid_field():
    store = InMemoryDynaStore(hcf=["data"])
    with pytest.raises(ValueError, match="Unsupported type"):
        store.create(data={"a": 1})


def test_invalid_meta():
    store = InMemoryDynaStore(hcf=["data"])
    store.db[MetadataId("abc")] = {
        "data": {"__hcf": 1, "i": 0, "l": 1, "t": "bad-type"}
    }
    with pytest.raises(ValueError, match="bad-type"):
        store.parse("abc-1")
