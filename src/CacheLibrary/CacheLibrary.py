import os
import json
from datetime import datetime, timedelta
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from pabot.pabotlib import PabotLib
from robot.api.deco import library
from typing import Dict, List, TypedDict, Union
from contextlib import contextmanager


CacheKey = str
CacheValue = Union[str, bool, int, float, List, Dict]
class CacheEntry(TypedDict):
    value: CacheValue
    expires: str
CacheContents = Dict[CacheKey, CacheEntry]

@library(scope="GLOBAL", version="1.0.0", auto_keywords=True, doc_format='ROBOT')
class CacheLibrary:
    """
    Cache values during a Robotframework test run as well as between test runs.

    = Pabot =

    CacheLibrary supports Pabot, but requires the `--pabotlib` command line option.

    CacheLibrary will even keep its cool when you run many tests that constantly write to the cache.
    To achieve this, only one test can write to the cache at a time. This does mean that your tests
    will slow down when you constantly write to the cache. CacheLibrary is a write-once, read-often
    solution.

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
    |     ${cache_key} =    Set Variable    api-session
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

    def __init__(self, file_path="robotframework-cache.json", file_size_warning_bytes=500000):
        self.pabotlib = PabotLib()
        self.file_path = file_path
        self.file_size_warning_bytes = file_size_warning_bytes

    def cache_retrieve_value(self, key: CacheKey) -> CacheValue:
        """
        Retrieve a value from the cache.

        Will return the value stored in the cache, or `None` if it does not exist.

        | `key` | Name of the stored value |

        = Examples =

        == Basic usage ==

        Retrieve a value from the cache

        |    ${session_token} =    Cache Retrieve Value    user-session
        """
        cache = self._open_cache_file()

        if key not in cache.keys():
            return None

        entry = cache[key]
        if self._entry_is_expired(entry):
            self.cache_remove_value(key)
            return None

        return entry["value"]

    def cache_store_value(self, key: CacheKey, value: CacheValue, expire_in_seconds=3600) -> None:
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

        | `key`                    | Name of the value to be stored                 |
        | `value`                  | Value to be stored                             |
        | `expire_in_seconds=3600` | After how many seconds the value should expire |

        = Examples =

        == Basic usage ==

        Store a value in the cache

        |    Cache Store Value    user-session    ${session_token}

        --------------------

        == Control expiration ==

        Store a value in the cache and set it to expire in 1 minute

        |    Cache Store Value    user-session    ${session_token}    expire_in_seconds=60
        """
        with self._lock("cachelib-edit"):
            cache = self._open_cache_file()

            expires = (datetime.now() + timedelta(seconds=expire_in_seconds)).isoformat()
            cache_entry: CacheEntry = {
                "value": value,
                "expires": expires,
            }

            cache[key] = cache_entry
            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache)
        self._store_json_file(self.file_path, cache)

    def cache_remove_value(self, key: CacheKey) -> None:
        """
        Remove a value from the cache.

        | `key` | Name of the stored value |

        = Examples =

        Remove a value from the cache

        |    Cache Remove Value    user-session
        """
        with self._lock("cachelib-edit"):
            cache = self._open_cache_file()

            if key not in cache.keys():
                return

            del cache[key]
            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, cache)
        self._store_json_file(self.file_path, cache)

    def cache_reset(self) -> None:
        """
        Remove all values from the cache.
        """
        with self._lock("cachelib-edit"):
            self.pabotlib.set_parallel_value_for_key(self.parallel_value_key, {})
        self._store_json_file(self.file_path, {})

    def run_keyword_and_cache_output(self, keyword: str, *args, expire_in_seconds=3600) -> CacheValue:
        """
        TODO: Should we keep?

        If possible, return the keyword's output from cache.

        If the value is not stored in cache, run the keyword instead. Then store it's output in
        cache for the next call.

        The keyword name and arguments are used as the cache key. This means that it's quite easy
        to create incorrect caching behavior. You can easily create two keyword calls that
        functionally do the same thing, but are considered different for caching purposes.

        | `keyword`                | The keyword that to be run                     |
        | `*args`                  | Arguments send to the keyword                  |
        | `expire_in_seconds=3600` | After how many seconds the value should expire |

        = Examples =

        == Basic usage ==

        Wrap a keyword with Run Keyword And Cache Output to cache its output.

        |    ${session_token} =    Run Keyword And Cache Output    Get API Session Token

        --------------------

        == With keyword arguments ==

        Wrap a keyword that requires arguments.

        |    ${user_session_token} =    Run Keyword And Cache Output    Login User    ${username}    ${password}

        --------------------

        == Control expiration ==

        Wrap a keyword that requires arguments and set it to expire in 1 minute

        |    ${user_session_token} =    Run Keyword And Cache Output    Login User    ${username}    ${password}    expire_in_seconds=60

        --------------------

        == Recommended usage ==

        Using the caching in a wrapper keyword makes things easier to manage and makes it harder to
        create incorrect caching behaviour.

        | Do A Thing
        |     [Arguments]    ${a}    ${b}    ${c}
        |     ${result} =    Run Keyword And Cache Output    Do The Actual Thing    ${a}    ${b}    ${c}
        |     RETURN    ${result}
        |
        | Do The Actual Thing
        |     [Arguments]    ${a}    ${b}    ${c}
        |     [Tags]    robot:private
        |     # Do something
        |     RETURN    ${output}
        """
        key = "kw-" + keyword.lower().replace(' ', '_') + "-" + "::".join(args)
        cached_value = self.cache_retrieve_value(key)
        if cached_value is not None:
            return cached_value

        new_value = BuiltIn().run_keyword(keyword, *args)

        self.cache_store_value(key, new_value, expire_in_seconds)
        return new_value

    def _open_cache_file(self) -> CacheContents:
        shared_cache = self.pabotlib.get_parallel_value_for_key(self.parallel_value_key)
        # If not set, `shared_cache` will be an empty string.
        if isinstance(shared_cache, dict):
            return shared_cache

        cache_file_contents = self._read_json_file(self.file_path)

        file_size = os.stat(self.file_path).st_size
        if file_size > self.file_size_warning_bytes:
            logger.warn(
                f"Large cache file '{self.file_path}'. File is {round(file_size / 1024, 1)}Kb. "
                + "There might be an issue with the caching mechanism."
            )

        # Filter out expired entries
        cache_contents: CacheContents = {}
        for key, entry in cache_file_contents.items():
            if not self._entry_is_expired(entry):
                cache_contents[key] = entry

        self.pabotlib.set_parallel_value_for_key(
            self.parallel_value_key, cache_contents
        )
        self._store_json_file(self.file_path, cache_contents)
        return cache_contents

    def _read_json_file(self, path: str) -> CacheContents:
        with self._lock(f"file-{path}"):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except:
                # Reset/create the file
                with open(path, "w") as f:
                    f.write("{}")
                return {}

    def _store_json_file(self, path: str, contents: CacheContents) -> None:
        with self._lock(f"file-{path}"):
            with open(path, "w") as f:
                return json.dump(contents, f)

    def _entry_is_expired(self, entry: CacheEntry) -> bool:
        now = datetime.now()
        expires = datetime.fromisoformat(entry["expires"])
        return (expires - now).total_seconds() < 0

    @contextmanager
    def _lock(self, name: str):
        try:
            self.pabotlib.acquire_lock(name)
            yield
        finally:
            self.pabotlib.release_lock(name)
