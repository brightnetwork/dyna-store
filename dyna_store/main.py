from __future__ import annotations

import enum
import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Generic, NewType, TypeVar

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

Id = NewType("Id", str)  # :$metadataId-$dynamicData
DynamicData = NewType("DynamicData", str)
MetadataId = NewType("MetadataId", str)
Value = str | int | float | datetime | None
Metadata = dict[str, Value | dict[str, Any]]

BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


T = TypeVar("T")
V = TypeVar("V", bound=BaseModel)


class Cardinality(enum.Enum):
    LOW = 1
    HIGH = 2


LowCardinality = Annotated[T, Cardinality.LOW]
HighCardinality = Annotated[T, Cardinality.HIGH]


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


class DynaStore(Generic[V]):
    def __init__(self, model: type[V]):
        self._model = model
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

    def parse(self, id_: str) -> V:
        metadata_id, id = self.parse_id(Id(id_))
        metadata = self.load_metadata(metadata_id)

        to_return: dict[str, Any] = {}
        for field_name in metadata:
            value = metadata.get(field_name)
            if value is not None:
                if isinstance(value, dict) and value.get("__hcf", None):
                    encoded_value = id[value["i"] : value["i"] + value["l"]]
                    decoded_value: Value = None
                    match value["t"]:
                        case "int":
                            decoded_value = b62_decode_int(encoded_value)
                        case "datetime":
                            decoded_value = datetime.fromtimestamp(
                                b62_decode_int(encoded_value), tz=timezone.utc
                            )
                        case "str":
                            decoded_value = encoded_value
                        case "NoneType":
                            decoded_value = None
                        case "float":
                            decoded_value = float(b62_decode_np_float_32(encoded_value))
                        case _:
                            raise ValueError(value["t"])
                    to_return[field_name] = decoded_value
                else:
                    to_return[field_name] = value

        return self._model(**to_return)

    def create(self, fields: V) -> Id:
        metadata: Metadata = {}
        id = DynamicData("")
        index = 0

        for field_name, field in fields.model_fields.items():
            cardinality = None
            for m in field.metadata:
                if isinstance(m, Cardinality):
                    cardinality = m
                    break

            if not cardinality:
                raise ValueError(f"Field {field_name} is missing cardinality metadata")

            match cardinality:
                case Cardinality.LOW:
                    metadata[field_name] = getattr(fields, field_name)
                case Cardinality.HIGH:
                    value = getattr(fields, field_name)
                    type_ = type(value).__name__
                    match type_:
                        case "int":
                            encoded = b62_encode_int(value)
                        case "datetime":
                            encoded = b62_encode_int(int(value.timestamp()))
                        case "str":
                            encoded = value
                        case "float":
                            encoded = b62_encode_np_float_32(np.float32(value))
                        case "NoneType":
                            encoded = ""
                        case _:
                            raise ValueError(f"Unsupported type {type_}")
                    metadata[field_name] = {
                        "__hcf": 1,  # high cardinality field
                        "i": index,
                        "l": len(encoded),
                        "t": type_,
                    }
                    index += len(encoded)
                    id = DynamicData(id + encoded)

        metadata_id = self.save_metadata(metadata)
        return self.create_id(metadata_id, id)
