from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt, StrictStr

from dyna_store import (
    HighCardinality,
    InMemoryDynaStore,
    LowCardinality,
    MetadataId,
)


def test_cardinality_annotation_is_required():
    class TestModel(BaseModel):
        data: int

    dyna_store = InMemoryDynaStore(TestModel)
    with pytest.raises(ValueError, match="missing cardinality metadata"):
        dyna_store.create(TestModel(data=1))


def test_simple_case():
    class TestModel(BaseModel):
        low: LowCardinality[int]
        high: HighCardinality[int]

    dyna_store = InMemoryDynaStore(TestModel)
    id = dyna_store.create(TestModel(low=1, high=0))
    assert id == "6efcd187bd-a"
    metadata = dyna_store.parse(id)
    assert metadata.low == 1
    assert metadata.high == 0


class Recommendation(BaseModel):
    # All types must be annotated with their cardinality.
    user_id: HighCardinality[int]
    timestamp: HighCardinality[datetime]
    algorithm: LowCardinality[StrictStr]
    job_id: HighCardinality[StrictInt | None] = None
    score: HighCardinality[StrictFloat | None] = None
    rank: HighCardinality[StrictInt | None] = None
    promoted: LowCardinality[StrictBool | None] = False
    campaign_id: HighCardinality[StrictStr | None] = None


def test_more_complex_case():
    store = InMemoryDynaStore(Recommendation)
    user_id = 435543
    now = datetime(2023, 12, 1, 14, 2, 4, tzinfo=timezone.utc)
    fields = Recommendation(user_id=user_id, timestamp=now, algorithm="stub-algo")
    id = store.create(fields)
    assert id == "2f12bea798-bZs3b1jefU"
    assert store.parse(id) == fields

    fields = Recommendation(
        user_id=user_id,
        timestamp=now,
        algorithm="stub-algo",
        score=0.1232432,
        campaign_id="cid",
    )
    id = store.create(fields)
    assert id == "8f359c5f16-bZs3b1jefUbixG42cid"
    assert store.parse(id).user_id == fields.user_id
    assert store.parse(id).timestamp == fields.timestamp
    assert store.parse(id).algorithm == fields.algorithm
    assert store.parse(id).campaign_id == fields.campaign_id
    assert abs(store.parse(id).score - fields.score) < 1e-6  # type: ignore


def test_invalid_id():
    class TestModel(BaseModel):
        data: HighCardinality[int]

    store = InMemoryDynaStore(TestModel)
    id_ = "abc:def"
    with pytest.raises(ValueError, match=id_):
        store.parse(id_)


def test_invalid_field():
    class TestModel(BaseModel):
        data: HighCardinality[dict]

    store = InMemoryDynaStore(TestModel)
    with pytest.raises(ValueError, match="Unsupported type"):
        store.create(TestModel(data={"a": 1}))


def test_invalid_meta():
    class TestModel(BaseModel):
        data: HighCardinality[int]

    store = InMemoryDynaStore(TestModel)
    store.db[MetadataId("abc")] = {
        "data": {"__hcf": 1, "i": 0, "l": 1, "t": "bad-type"}
    }
    with pytest.raises(ValueError, match="bad-type"):
        store.parse("abc-1")
