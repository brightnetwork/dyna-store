from __future__ import annotations

import hashlib
import json

from .main import DynaStore, Metadata, MetadataId

MD5_HASH_LENGTH = 10


class InMemoryDynaStore(DynaStore):
    def init(self) -> None:
        self.db: dict[MetadataId, Metadata] = {}

    def save_metadata(self, metadata: Metadata) -> MetadataId:
        metadata_str = json.dumps(metadata)
        hash_ = hashlib.md5(metadata_str.encode()).hexdigest()[:MD5_HASH_LENGTH]  # noqa: S324
        id_ = MetadataId(hash_)
        self.db[id_] = metadata
        return id_

    def load_metadata(self, id_: MetadataId) -> Metadata:
        return Metadata(**self.db[id_])
