from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from pabot.pabotlib import PabotLib
from robot.errors import RobotError

from CacheLibrary.constants import CacheContents
from CacheLibrary.util.lock import lock


class CacheFile:
    """
    Cache library store.
    """

    file_path: Path

    _process_cache: CacheContents | None = None
    _process_cache_updated: str = ""

    _parallel_value_key_cache = "robotframework-cache"
    _parallel_value_key_updated = "robotframework-cache-updated"

    def __init__(
        self,
        file_path: Path,
        pabotlib: PabotLib,
        *,
        file_cleanup_handler: Callable[[CacheContents], CacheContents] | None = None,
    ) -> None:
        self.file_path = file_path
        self._pabotlib = pabotlib
        self._file_cleanup_handler = file_cleanup_handler

    def get(self) -> CacheContents:
        """Get the full cache"""
        process_cache = self._open_from_process_cache()
        if process_cache:
            return process_cache

        shared_cache = self._open_from_shared_cache()
        if shared_cache:
            return shared_cache

        return self._open_from_file_cache()

    def _open_from_process_cache(self) -> CacheContents | None:
        if self._process_cache is None:
            return None

        shared_cache_updated = self._pabotlib.get_parallel_value_for_key(
            self._parallel_value_key_updated,
        )
        if shared_cache_updated == "":
            # Never set
            return None

        if shared_cache_updated != self._process_cache_updated:
            return None

        return self._process_cache

    def _open_from_shared_cache(self) -> CacheContents | None:
        shared_cache = self._pabotlib.get_parallel_value_for_key(self._parallel_value_key_cache)

        if shared_cache == "":
            # Never set
            return None

        if not isinstance(shared_cache, bytes):
            # Unexpected type
            return None

        shared_cache_updated = self._pabotlib.get_parallel_value_for_key(
            self._parallel_value_key_updated,
        )
        if shared_cache_updated == "" or not isinstance(shared_cache_updated, str):
            shared_cache_updated = str(uuid4())

        decoded = self._decode(shared_cache)
        self._store_in_process_cache(decoded, shared_cache_updated)
        return decoded

    def _open_from_file_cache(self) -> CacheContents:
        cache_contents = self._open_cache_file()
        if not cache_contents:
            return {}

        if not self._file_cleanup_handler:
            return cache_contents

        cache_contents = self._file_cleanup_handler(cache_contents)
        self.store(cache_contents)
        return cache_contents

    def _open_cache_file(self) -> CacheContents:
        try:
            with (
                lock(self._pabotlib, f"cachelib-file-{self.file_path}"),
                self.file_path.open("rb") as f,
            ):
                raw = f.read()

            return self._decode(raw)
        except (RobotError, KeyboardInterrupt, SystemExit):
            raise
        except Exception:  # noqa: BLE001
            # Reset/create the file
            empty_cache = {}
            self.store(empty_cache)
            return empty_cache

    def store(self, contents: CacheContents) -> None:
        """Store contents to the cache file"""
        store_id = str(uuid4())
        self._store_in_process_cache(contents, store_id)

        encoded = self._encode(contents)
        self._store_in_shared_cache(encoded, store_id)
        self._store_in_file_cache(encoded)

    def _store_in_process_cache(self, contents: CacheContents, store_id: str) -> None:
        self._process_cache = contents
        self._process_cache_updated = store_id

    def _store_in_shared_cache(self, encoded_contents: bytes, store_id: str) -> None:
        self._pabotlib.set_parallel_value_for_key(self._parallel_value_key_cache, encoded_contents)
        self._pabotlib.set_parallel_value_for_key(self._parallel_value_key_updated, store_id)

    def _store_in_file_cache(self, encoded_contents: bytes) -> None:
        with (
            lock(self._pabotlib, f"cachelib-file-{self.file_path}"),
            self.file_path.open("wb") as f,
        ):
            f.write(encoded_contents)

    def _encode(self, cache: CacheContents) -> bytes:
        """Encode Python object CacheContents to file contents."""
        raise NotImplementedError

    def _decode(self, raw: bytes) -> CacheContents:
        """Encode file contents to Python object CacheContents."""
        raise NotImplementedError

    def get_size(self) -> int:
        """Get cache size in bytes"""
        return self.file_path.stat().st_size
