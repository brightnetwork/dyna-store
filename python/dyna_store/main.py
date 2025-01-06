from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from datetime import datetime, timezone
from typing import Any, NewType, TypeVar

import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

Id = NewType("Id", str)  # :$metadataId-$dynamicData
DynamicData = NewType("DynamicData", str)
MetadataId = NewType("MetadataId", str)
Value = str | int | float | datetime | None | dict[str, "Value"]
Metadata = dict[str, Value]

BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


T = TypeVar("T")


def b62_encode_str(str_: str) -> str:
    return base64.b32encode(str_.encode("utf-8")).decode("utf-8")


def b62_decode_str(str_: str) -> str:
    return base64.b32decode(str_).decode("utf-8")


def b62_encode_int(num: int) -> str:
    if num == 0:
        return BASE62[0]
    arr: list[str] = []
    arr_append = arr.append  # Extract bound-method for faster access.
    _divmod = divmod  # Access to locals is faster.
    base = len(BASE62)
    while num:
        num, rem = _divmod(num, base)
        arr_append(BASE62[rem])
    arr.reverse()
    return "".join(arr)


def b62_encode_np_float_32(num: np.float32) -> str:
    bytes_ = num.tobytes()
    int_ = np.frombuffer(bytes_, dtype=np.int32)[0]
    return b62_encode_int(int_)


def b62_decode_int(string: str) -> int:
    base = len(BASE62)
    strlen = len(string)
    num = 0

    idx = 0
    for idx, char in enumerate(string):
        power = strlen - (idx + 1)
        num += BASE62.index(char) * (base**power)

    return num


def b62_decode_np_float_32(num: str) -> np.float32:
    int_ = b62_decode_int(num)
    return np.frombuffer(np.int32(int_).tobytes(), dtype=np.float32)[0]


class DynaStore:
    def __init__(self, *, hcf: Sequence[str] = []):
        self._high_cardinality_fields = set(hcf)
        self.init()

    def init(self) -> None:
        pass

    def save_metadata(self, _metadata: Metadata) -> MetadataId:
        raise NotImplementedError

    def load_metadata(self, _id: MetadataId) -> Metadata:
        raise NotImplementedError

    def parse_id(self, id_: Id) -> tuple[MetadataId, DynamicData]:
        s = id_.split("-")
        if len(s) != 2:  # noqa: PLR2004
            raise ValueError(id_)
        return MetadataId(s[0]), DynamicData(s[1])

    def create_id(self, metadata_id: MetadataId, dynamic_data: DynamicData) -> Id:
        return Id(f"{metadata_id}-{dynamic_data}")

    def parse(self, id_: str) -> dict[str, Value]:
        metadata_id, id = self.parse_id(Id(id_))
        metadata = self.load_metadata(metadata_id)

        to_return: dict[str, Value] = {}
        for field_name in metadata:
            value = metadata.get(field_name)
            if isinstance(value, dict) and value.get("__hcf", None):
                encoded_value = id[value["i"] : value["i"] + value["l"]]  # type: ignore
                decoded_value: Value = None
                match value["t"]:
                    case "int":
                        decoded_value = b62_decode_int(encoded_value)
                    case "datetime":
                        decoded_value = datetime.fromtimestamp(
                            b62_decode_int(encoded_value), tz=timezone.utc
                        )
                    case "str":
                        decoded_value = b62_decode_str(encoded_value)
                    case "NoneType":
                        decoded_value = None
                    case "float":
                        decoded_value = float(b62_decode_np_float_32(encoded_value))
                    case _:
                        raise ValueError(value["t"])
                to_return[field_name] = decoded_value
            else:
                to_return[field_name] = value

        return to_return

    def create(self, **fields: Value) -> Id:
        metadata: Metadata = {}
        id = DynamicData("")
        index = 0

        for key, value in fields.items():
            value_: Any = value
            if key in self._high_cardinality_fields:
                type_ = type(value).__name__
                match type_:
                    case "int":
                        encoded = b62_encode_int(value_)
                    case "datetime":
                        encoded = b62_encode_int(int(value_.timestamp()))
                    case "str":
                        encoded = b62_encode_str(value_)
                    case "float":
                        encoded = b62_encode_np_float_32(np.float32(value_))
                    case "NoneType":
                        encoded = ""
                    case _:
                        raise ValueError(f"Unsupported type {type_}")
                metadata[key] = {
                    "__hcf": 1,  # high cardinality field
                    "i": index,
                    "l": len(encoded),
                    "t": type_,
                }
                index += len(encoded)
                id = DynamicData(id + encoded)
            else:
                metadata[key] = value_
        metadata_id = self.save_metadata(metadata)
        return self.create_id(metadata_id, id)
