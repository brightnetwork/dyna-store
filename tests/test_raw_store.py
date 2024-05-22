import pytest

from dyna_store import DynaStore


def test_not_implemented_error():
    dyna_store = DynaStore(hcf=["data"])
    with pytest.raises(NotImplementedError):
        dyna_store.create(data=1)

    with pytest.raises(NotImplementedError):
        dyna_store.parse("abc-def")
