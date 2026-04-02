from typing import cast

import jsonpickle

from CacheLibrary.constants import CacheContents
from CacheLibrary.util.dotdict import dotdict_to_dict

from .base import CacheFile


class JsonCacheFile(CacheFile):
    """
    Cache library store for .json files.
    """

    def _decode(self, raw: bytes) -> CacheContents:
        decoded = jsonpickle.decode(raw, on_missing="error")  # noqa: S301

        if not isinstance(decoded, dict):
            msg = "Failed to decode .json file: " + self.file_path.as_posix()
            raise TypeError(msg)

        return cast(CacheContents, decoded)

    def _encode(self, cache: CacheContents) -> bytes:
        cache = dotdict_to_dict(cache)

        encoded = jsonpickle.encode(cache)
        if isinstance(encoded, str):
            return encoded.encode("utf-8")
        if isinstance(encoded, bytes):
            return encoded

        msg = f"Failed to encode cache. Got type '{type(encoded)}'. This should never happen."
        raise ValueError(msg)
