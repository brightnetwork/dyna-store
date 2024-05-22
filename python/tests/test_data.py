import json
from datetime import datetime
from pathlib import Path

from dyna_store.main import DynaStore, Metadata, MetadataId

with Path("../tests/data.json").open() as f:
    data = json.load(f)


class Store(DynaStore):
    def load_metadata(self, id_: MetadataId) -> Metadata:
        return data["templates"][id_]


def test_parse_is_parsing_as_expected():
    for id_, expected in data["ids"].items():
        actual = Store().parse(id_)
        if "timestamp" in expected and isinstance(expected["timestamp"], str):
            expected["timestamp"] = datetime.fromisoformat(expected["timestamp"])

        assert {k: v for k, v in actual.items() if not isinstance(v, float)} == {
            k: v for k, v in expected.items() if not isinstance(v, float)
        }

        for k, v in actual.items():
            if isinstance(v, float):
                assert abs(v - expected[k]) < 1e-6
