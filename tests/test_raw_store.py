import pytest
from pydantic import BaseModel

from dyna_store import (
    DynaStore,
    HighCardinality,
)


def test_not_implemented_error():
    class TestModel(BaseModel):
        data: HighCardinality[int]

    dyna_store = DynaStore(TestModel)
    with pytest.raises(NotImplementedError):
        dyna_store.create(TestModel(data=1))

    with pytest.raises(NotImplementedError):
        dyna_store.parse("abc-def")
