import json
import random
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, TypeAlias, TypedDict

from pabot.pabotlib import PabotLib
from robot.api import logger
from robot.api.deco import keyword, library
from robot.errors import RobotError
from robot.libraries.BuiltIn import BuiltIn

from .__version__ import __version__

CacheKey: TypeAlias = str
CacheValue: TypeAlias = str | bool | int | float | list | dict
CacheValueType: TypeAlias = Literal["COLLECTION", "VALUE"]
CACHE_VALUE_TYPES: tuple[CacheValueType, ...] = ("COLLECTION", "VALUE")


class CacheEntry(TypedDict):
    """
    Base data struct for cache entry
    """

    value: CacheValue
    expires: str


CacheContents: TypeAlias = dict[CacheValueType, dict[CacheKey, CacheEntry]]

KwName: TypeAlias = str
KwArgs: TypeAlias = Any


@library(scope="GLOBAL", version=__version__, doc_format="ROBOT")
class CacheLibrary:
    """
    Cache values during a Robotframework test run as well as between test runs.

    = Pabot =

    CacheLibrary works with Pabot.

    - Pabot @ <2.2.0 is not supported
    - Pabot @ >=2.2.0 and <4 requires the `--pabotlib` command line argument.
    - Pabot @ >=4 won't work with the `--no-pabotlib` command line argument.

    CacheLibrary will even keep its cool when you run many tests that constantly write to the cache.
    To achieve this, only one test can write to the cache at a time. This does mean that your tests
    will slow down when you constantly write to the cache. CacheLibrary works best when you
    write sometimes and read often.

    = Examples =

    == Basic usage ==

    Store a value, and retrieve it later

    |    Cache Store Value    foo    Hello, world
    |
    |    # Do something interesting
    |
    |    ${value} =    Cache Retrieve Value    foo
    |    Should Be Equal    ${value}    Hello, world

    --------------------

    == Caching output of a keyword ==

    The keyword below fetches or reuses a session token.

    Everwhere you need the session token, you can use this keyword. CacheLibrary will ensure that
    you're only requesting a new session token once. After which it will reuse the session token.

    In fact, CacheLibrary will do this even across multiple test runs. This way, you don't have to
    request the session token every time when you're making/debugging a test.

    | Get Api Session Token
    |     VAR  ${cache_key} =    api-sessions
    |     ${cached_token} =    Cache Retrieve value    ${cache_key}
    |     IF    $cached_token is not $None
    |         RETURN    ${cached_token}
    |     END
    |
    |     # Request a new session token
    |
    |     Cache Store Value    ${cache_key}    ${new_token}
    |     RETURN    ${new_token}
    """

    parallel_value_key = "robotframework-cache"

    def __init__(
        self,
        file_path: str = "robotframework-cache.json",
        file_size_warning_bytes: int = 500000,
        default_expire_in_seconds: int = 3600,
    ) -> None:
        """
        | `file_path`                      | Path to the cache file. Relative to where Robot Frameworks working directory                   |
        | `file_size_warning_bytes`        | Log warning when the cache exceeds this size                                                   |
        | `default_expire_in_seconds=3600` | After how many seconds should a stored value expire. Can be overwritten when a value is stored |
        """  # noqa: D205, E501
        self.pabotlib = PabotLib()
        self.file_path = Path(file_path)
        self.file_size_warning_bytes = file_size_warning_bytes
        self.default_expire_in_seconds = default_expire_in_seconds

    @keyword(tags=["value"])
    def cache_retrieve_value(self, key: CacheKey) -> CacheValue | None:
        """
        Retrieve a value from the cache.

        Will return the value stored in the cache, or `None` if it does not exist.

        | `key` | Name of the stored value |

        = Examples =

        == Basic usage ==

        Retrieve a value from the cache

        |  ${session_token} =    Cache Retrieve Value    user-session
        """
        cache = self._open_cache_file()["VALUE"]

        if key not in cache:
            return None

        entry = cache[key]
        if self._entry_is_expired(entry):
            self.cache_remove_value(key)
            return None

        return entry["value"]

    @keyword(tags=["collection"])
    def cache_retrieve_value_from_collection(
        self,
        key: CacheKey,
        pick: Literal["first", "last", "random"] = "first",
        remove_value: bool = True,  # noqa: FBT001, FBT002
    ) -> CacheValue | None:
        """
        Retrieve a value from a cached collection.

        Will return a single value from a collection stored in the cache, or `None` if there is no
        value.

        | `key`               | Name of the collection                          |
        | `pick=first`        | How to pick a value from the collection         |
        | `remove_value=True` | Should the value be removed from the collection |

        = Examples =

        == Basic usage ==

        Retrieve the first value from a cached collection.

        |  ${user} =    Cache Retrieve Value From Collection    user-accounts

        --------------------

        == Pick random value ==

        Retrieve a random value from a cached collection. Don't remove the value from the
        collection.

        |  ${user} =    Cache Retrieve Value From Collection    user-accounts    pick=random    remove_value=${False}
        """  # noqa: E501
        cache = self._open_cache_file()["COLLECTION"]

        if key not in cache:
            return None

        entry = cache[key]
        if self._entry_is_expired(entry):
            self.cache_remove_collection(key)
            return None

        values = entry["value"]
        if not isinstance(values, list) or len(values) == 0:
            self.cache_remove_collection(key)
            return None

        index = None
        if pick == "first":
            index = 0
        elif pick == "last":
            index = -1
        elif pick == "random":
            index = random.randint(0, len(values) - 1)  # noqa: S311
        else:
            msg = f"Unexpected pick '{pick}'. Expected one of 'first', 'last', or 'random'."
            raise ValueError(msg)

        value = values[index]
        if remove_value:
            self.cache_remove_value_from_collection(key, index=index)

        return value

    @keyword(tags=["value"])
    def cache_store_value(
        self,
        key: CacheKey,
        value: CacheValue,
        expire_in_seconds: int | Literal["default"] = "default",
    ) -> None:
        """
        Store a value in the cache.

        The value to be stored must be able to be stored in JSON. Supported values include (but are
        not limited to):

        - String
        - Integer
        - Float
        - Boolean
        - Dictionary
        - List

        | `key`                       | Name of the value to be stored                 |
        | `value`                     | Value to be stored                             |
        | `expire_in_seconds=default` | After how many seconds the value should expire |

        = Examples =

        == Basic usage ==

        Store a value in the cache

        |  Cache Store Value    user-session    ${session_token}

        --------------------

        == Control expiration ==

        Store a value in the cache and set it to expire in 1 minute

        |  Cache Store Value    user-session    ${session_token}    expire_in_seconds=60
        """
        self._store_cache_entry(key, value, "VALUE", expire_in_seconds)

    @keyword(tags=["collection"])
    def cache_store_collection(
        self,
        key: CacheKey,
        *values: CacheValue,
        expire_in_seconds: int | Literal["default"] = "default",
    ):
        """
        Store a collection of values in the cache.

        All values in the collection must be able to be stored in JSON. Supported values include
        (but are not limited to):

        - String
        - Integer
        - Float
        - Boolean
        - Dictionary
        - List

        | `key`                       | Name of the collection to be stored                      |
        | `*values`                   | Values to be stored. Can be multiple.                    |
        | `expire_in_seconds=default` | After how many seconds the full collection should expire |

        = Examples =

        == Basic usage ==

        Store a collection of values in the cache

        |  VAR  @{users} =    Henk    Harry    Herman
        |  Cache Store Collection    usernames    @{usernames}

        --------------------

        == Control expiration ==

        Store a collection of values in the cache and set them to expire in 1 minute. All values
        will expire at the same time.

        |  VAR  @{users} =    Henk    Harry    Herman
        |  Cache Store Collection    usernames    @{usernames}    expire_in_seconds=60
        """
        self._store_cache_entry(key, list(values), "COLLECTION", expire_in_seconds)

    def _store_cache_entry(
        self,
        key: CacheKey,
        value: CacheValue,
        value_type: CacheValueType,
        expire_in_seconds: int | Literal["default"],
    ) -> None:
        if expire_in_seconds == "default":
            expire_in_seconds = self.default_expire_in_seconds

        expires = (datetime.now() + timedelta(seconds=expire_in_seconds)).isoformat()
        cache_entry: CacheEntry = {
            "value": value,
            "expires": expires,
        }

        with self._lock("cachelib-edit"):
            cache = self._open_cache_file()
            cache[value_type][key] = cache_entry

            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache)
        self._store_json_file(self.file_path, cache)

    @keyword(tags=["collection"])
    def cache_remove_value_from_collection(
        self,
        key: CacheKey,
        *,
        index: int | None = None,
        value: CacheValue | None = None,
    ) -> None:
        """
        Remove a value from a cached collection.

        | `key`   | Name of the stored collection    |
        | `index` | Index of the value to be removed |
        | `value` | Exact value to be removed        |

        = Examples =

        == Remove with index ==

        Remove a value from a cached collection using index.

        |  Cache Remove Value From Collection    user-sessions    index=3

        --------------------

        == Remove with value ==

        Remove a value from a cached collection using the value. Must be the exact value.

        |  ${session} =    Cache Retrieve Value From Collection    user-sessions    remove_value=${False}
        |  Cache Remove Value From Collection    user-sessions    value=${session}
        """  # noqa: E501
        with self._lock("cachelib-edit"):
            cache = self._open_cache_file()
            collection_cache = cache["COLLECTION"]

            if key not in collection_cache:
                return

            values = collection_cache[key]["value"]
            if not isinstance(values, list):
                return

            values = self._remove_value_from_collection(key, values, index=index, value=value)

            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache)
        self._store_json_file(self.file_path, cache)

    def _remove_value_from_collection(
        self,
        col_name: CacheKey,
        col_values: list[CacheValue],
        *,
        index: int | None = None,
        value: CacheValue | None = None,
    ) -> list[CacheValue]:
        if index is not None and value is not None:
            msg = "Got both index and value. Pick one. Can't use both at the same time."
            raise ValueError(msg)

        if index is not None:
            try:
                col_values.pop(index)
            except IndexError as e:
                msg = (
                    "Could not remove value from collection. Index out of range. "
                    f"Index {index} does not exist in cache collection '{col_name}'. "
                    f"Expected index between 0 and {len(col_values) - 1}. "
                    f"{type(e).__name__}: {e}"
                )
                raise AssertionError(msg) from e
            else:
                return col_values

        if value is not None:
            try:
                col_values.remove(value)
            except ValueError as e:
                msg = (
                    "Could not remove value from collection. Value not in collection. "
                    f"Value '{value}' does not exist in cache collection '{col_name}'. "
                    f"{type(e).__name__}: {e}"
                )
                raise AssertionError(msg) from e
            else:
                return col_values

        msg = "No index and no value. I don't know what value to remove cached collection."
        raise ValueError(msg)

    @keyword(tags=["value"])
    def cache_remove_value(self, key: CacheKey) -> None:
        """
        Remove a value from the cache.

        | `key` | Name of the stored value |

        = Examples =

        Remove a value from the cache

        |  Cache Remove Value    user-session
        """
        self._remove_cache_entry(key, "VALUE")

    @keyword(tags=["collection"])
    def cache_remove_collection(self, key: CacheKey) -> None:
        """
        Remove a collection from the cache.

        Removes the entire collection, including all values.

        | `key` | Name of the stored collection |

        = Examples =

        Remove a collection from the cache

        |  Cache Remove Collection    test-users
        """
        self._remove_cache_entry(key, "COLLECTION")

    def _remove_cache_entry(
        self,
        key: CacheKey,
        value_type: CacheValueType,
    ) -> None:
        with self._lock("cachelib-edit"):
            cache = self._open_cache_file()

            if key not in cache[value_type]:
                return

            del cache[value_type][key]
            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache)
        self._store_json_file(self.file_path, cache)

    @keyword
    def cache_reset(self) -> None:
        """
        Remove all values from the cache.
        """
        empty_cache = self._ensure_complete_cache({})
        with self._lock("cachelib-edit"):
            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, empty_cache)
        self._store_json_file(self.file_path, empty_cache)

    @keyword(tags=["value"])
    def run_keyword_and_cache_output(
        self,
        keyword: KwName,
        *args: KwArgs,
        expire_in_seconds: int | Literal["default"] = "default",
    ) -> CacheValue:
        """
        If possible, return the keyword's output from cache.

        If the value is not stored in cache, run the keyword instead. Then store it's output in
        cache for the next call.

        The keyword name and arguments are used as the cache key. This means that it's quite easy
        to create incorrect caching behavior. You can easily create two keyword calls that
        functionally do the same thing, but are considered different for caching purposes.

        | `keyword`                   | The keyword that to be run                     |
        | `*args`                     | Arguments send to the keyword                  |
        | `expire_in_seconds=default` | After how many seconds the value should expire |

        = Examples =

        == Basic usage ==

        Wrap a keyword with Run Keyword And Cache Output to cache its output.

        |  ${session_token} =    Run Keyword And Cache Output    Get API Session Token

        --------------------

        == With keyword arguments ==

        Wrap a keyword that requires arguments.

        |  ${user_session_token} =    Run Keyword And Cache Output    Login User    ${username}    ${password}

        --------------------

        == Control expiration ==

        Wrap a keyword that requires arguments and set it to expire in 1 minute

        |  ${user_session_token} =    Run Keyword And Cache Output
        |  ...  Login User    ${username}    ${password}    expire_in_seconds=60

        --------------------

        == Recommended usage ==

        Using the caching in a wrapper keyword makes things easier to manage and makes it harder to
        create incorrect caching behaviour.

        |  Do A Thing
        |      [Arguments]    ${a}    ${b}    ${c}
        |      ${result} =    Run Keyword And Cache Output    Do The Actual Thing    ${a}    ${b}    ${c}
        |      RETURN    ${result}
        |
        |  Do The Actual Thing
        |      [Arguments]    ${a}    ${b}    ${c}
        |      [Tags]    robot:private
        |      # Do something
        |      RETURN    ${output}
        """  # noqa: E501
        key = "kw-" + keyword.lower().replace(" ", "_") + "-" + "::".join([str(a) for a in args])
        cached_value = self.cache_retrieve_value(key)
        if cached_value is not None:
            return cached_value

        new_value: CacheValue = BuiltIn().run_keyword(  # pyright: ignore[reportAssignmentType]
            keyword,  # pyright: ignore[reportArgumentType]
            *args,
        )

        self.cache_store_value(key, new_value, expire_in_seconds)
        return new_value

    def _ensure_complete_cache(self, cache: CacheContents) -> CacheContents:
        for value_type in CACHE_VALUE_TYPES:
            cache.setdefault(value_type, {})
        return cache

    def _open_cache_file(self) -> CacheContents:
        shared_cache = self.pabotlib.get_parallel_value_for_key(self.parallel_value_key)
        # If not set, `shared_cache` will be an empty string.
        if isinstance(shared_cache, dict):
            return shared_cache

        cache_file_contents = self._read_json_file(self.file_path)

        file_size = self.file_path.stat().st_size
        if file_size > self.file_size_warning_bytes:
            logger.warn(
                f"Large cache file '{self.file_path}'. File is {round(file_size / 1024, 1)}Kb. "
                "There might be an issue with the caching mechanism.",
            )

        cache_contents: CacheContents = self._ensure_complete_cache({})
        for value_type, contents in cache_file_contents.items():
            for key, entry in contents.items():
                if self._entry_is_expired(entry):
                    continue
                cache_contents[value_type][key] = entry

        self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache_contents)
        self._store_json_file(self.file_path, cache_contents)
        return cache_contents

    def _read_json_file(self, path: Path) -> CacheContents:
        with self._lock(f"cachelib-file-{path}"):
            try:
                with path.open("r", encoding="utf8") as f:
                    return json.load(f)
            except (RobotError, KeyboardInterrupt, SystemExit):
                raise
            except Exception:  # noqa: BLE001
                # Reset/create the file
                empty_cache = self._ensure_complete_cache({})
                with path.open("w", encoding="utf8") as f:
                    json.dump(empty_cache, f)
                return empty_cache

    def _store_json_file(self, path: Path, contents: CacheContents) -> None:
        with self._lock(f"cachelib-file-{path}"), path.open("w", encoding="utf8") as f:
            return json.dump(contents, f)

    def _entry_is_expired(self, entry: CacheEntry) -> bool:
        now = datetime.now()
        expires = datetime.fromisoformat(entry["expires"])
        return (expires - now).total_seconds() < 0

    @contextmanager
    def _lock(self, name: str) -> Generator[None, Any, None]:
        try:
            self.pabotlib.acquire_lock(name)
            yield
        finally:
            self.pabotlib.release_lock(name)
