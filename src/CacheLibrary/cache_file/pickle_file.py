import pickle
from typing import cast

from CacheLibrary.constants import CacheContents
from CacheLibrary.util.dotdict import dotdict_to_dict

from .base import CacheFile


class PickleCacheFile(CacheFile):
    """
    Cache library store for .pkl files.
    """

    def _decode(self, raw: bytes) -> CacheContents:
        decoded = pickle.loads(raw)  # noqa: S301

        if not isinstance(decoded, dict):
            msg = "Failed to decode .pkl file: " + self.file_path.as_posix()
            raise TypeError(msg)

        return cast(CacheContents, decoded)

    def _encode(self, cache: CacheContents) -> bytes:
        cache = dotdict_to_dict(cache)

        return pickle.dumps(cache)
