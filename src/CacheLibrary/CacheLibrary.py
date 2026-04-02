import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pabot.pabotlib import PabotLib
from robot.api import logger
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from .__version__ import __version__
from .cache_file.base import CacheFile
from .cache_file.json_file import JsonCacheFile
from .cache_file.pickle_file import PickleCacheFile
from .constants import (
    CACHE_VALUE_TYPES,
    CacheContents,
    CacheEntry,
    CacheKey,
    CacheValue,
    CacheValueType,
)
from .util.lock import lock

KwName: TypeAlias = str
KwArgs: TypeAlias = Any


@library(scope="GLOBAL", version=__version__, doc_format="ROBOT")
class CacheLibrary:
    """
    Cache values during a Robotframework test run as well as between test runs.

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

    = Pabot =

    CacheLibrary works with Pabot.

    - Pabot @ <2.2.0 is not supported
    - Pabot @ >=2.2.0 and <4 requires the `--pabotlib` command line argument.
    - Pabot @ >=4 won't work with the `--no-pabotlib` command line argument.

    CacheLibrary will even keep its cool when you run many tests that constantly write to the cache.
    To achieve this, only one test can write to the cache at a time. This does mean that your tests
    will slow down when you constantly write to the cache. CacheLibrary works best when you
    write sometimes and read often.
    """

    cache_file: CacheFile

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
        self.file_size_warning_bytes = file_size_warning_bytes
        self.default_expire_in_seconds = default_expire_in_seconds
        self.pabotlib = PabotLib()

        path = Path(file_path)

        if path.suffix == ".json":
            self.cache_file = JsonCacheFile(
                path,
                self.pabotlib,
                file_cleanup_handler=self._cleanup_cache,
            )
        elif path.suffix == ".pkl":
            self.cache_file = PickleCacheFile(
                path,
                self.pabotlib,
                file_cleanup_handler=self._cleanup_cache,
            )
        else:
            msg = (
                f"Unexpected cache file extension '{path.suffix}'. Expected one of '.json', '.pkl'"
            )
            raise ValueError(msg)

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
        cache = self.cache_file.get()
        cache = self._ensure_complete_cache(cache)["VALUE"]

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

        | `key`               | Name of the collection                                                       |
        | `pick=first`        | How to pick a value from the collection. Can be 'first', 'last', or 'random' |
        | `remove_value=True` | Should the value be removed from the collection                              |

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
        cache = self.cache_file.get()
        cache = self._ensure_complete_cache(cache)["COLLECTION"]

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

        The value must be storable as JSON or Pickle. Supported values include (but are not limited
        to):

        - String
        - Integer
        - Float
        - Boolean
        - Dictionary
        - List
        - Secret
        - Complex Python objects

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
        entry = self._store_cache_entry(key, value, "VALUE", expire_in_seconds)
        logger.info(f"Stored value for '{key}'. Expires {entry['expires']}")

    @keyword(tags=["collection"])
    def cache_store_collection(
        self,
        key: CacheKey,
        *values: CacheValue,
        expire_in_seconds: int | Literal["default"] = "default",
    ):
        """
        Store a collection of values in the cache.

        All values in the collection must be storable as JSON or Pickle. Supported values include
        (but are not limited to):

        - String
        - Integer
        - Float
        - Boolean
        - Dictionary
        - List
        - Secret
        - Complex Python objects

        | `key`                       | Name of the collection to be stored                      |
        | `*values`                   | Values to be stored. Can be multiple.                    |
        | `expire_in_seconds=default` | After how many seconds the full collection should expire |

        = Examples =

        == Basic usage ==

        Store a collection of values in the cache

        |  VAR  @{users} =    Alice    Bob    Pekka    Miikka
        |  Cache Store Collection    usernames    @{usernames}

        --------------------

        == Control expiration ==

        Store a collection of values in the cache and set them to expire in 1 minute. All values
        will expire at the same time.

        |  VAR  @{users} =    Alice    Bob    Pekka    Miikka
        |  Cache Store Collection    usernames    @{usernames}    expire_in_seconds=60
        """
        entry = self._store_cache_entry(key, list(values), "COLLECTION", expire_in_seconds)
        logger.info(
            f"Stored collection for '{key}' with {len(values)} values. Expires {entry['expires']}",
        )

    def _store_cache_entry(
        self,
        key: CacheKey,
        value: CacheValue,
        value_type: CacheValueType,
        expire_in_seconds: int | Literal["default"],
    ) -> CacheEntry:
        if expire_in_seconds == "default":
            expire_in_seconds = self.default_expire_in_seconds

        expires = datetime.now() + timedelta(seconds=expire_in_seconds)
        cache_entry = CacheEntry(
            value=value,
            expires=expires.isoformat(),
        )

        with self.edit_cache() as cache:
            cache[value_type][key] = cache_entry

            self.cache_file.store(cache)
        return cache_entry

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

        Requires `index` or `value`, but not both.

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
        with self.edit_cache() as cache:
            entry = cache["COLLECTION"].get(key, None)
            if not entry:
                return

            values = entry["value"]
            if not isinstance(values, list):
                return

            self._remove_value_from_collection(key, values, index=index, value=value)

            self.cache_file.store(cache)

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
            if type(value).__name__ == "Secret":
                msg = (
                    "Removing Secret from collection by value is not supported. "
                    "Remove by index instead"
                )
                raise ValueError(msg)

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

        msg = "No index and no value. I don't know what to remove from cached collection."
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
        with self.edit_cache() as cache:
            if key not in cache[value_type]:
                return

            del cache[value_type][key]

            self.cache_file.store(cache)

    @keyword
    def cache_reset(self) -> None:
        """
        Remove all values from the cache.
        """
        empty_cache = self._ensure_complete_cache({})
        with self.edit_cache():
            self.cache_file.store(empty_cache)

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

    def _cleanup_cache(self, cache: CacheContents) -> CacheContents:
        file_size = self.cache_file.get_size()
        if file_size > self.file_size_warning_bytes:
            logger.warn(
                f"Large cache file '{self.cache_file.file_path}'. "
                f"File is {round(file_size / 1024, 1)}Kb. "
                "There might be an issue with the caching mechanism.",
            )

        # Remove expired entries
        cleaned_cache: CacheContents = self._ensure_complete_cache({})
        for value_type, contents in cache.items():
            for key, entry in contents.items():
                if self._entry_is_expired(entry):
                    continue
                cleaned_cache[value_type][key] = entry

        return cleaned_cache

    def _entry_is_expired(self, entry: CacheEntry) -> bool:
        now = datetime.now()
        expires = datetime.fromisoformat(entry["expires"])
        return (expires - now).total_seconds() < 0

    @contextmanager
    def edit_cache(self):
        """Lock the cache for editing. Yields recent cache."""
        with lock(self.pabotlib, "cachelib-edit"):
            cache = self.cache_file.get()
            cache = self._ensure_complete_cache(cache)
            yield cache
