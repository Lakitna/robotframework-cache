from typing import Literal, TypeAlias, TypedDict

try:
    from robot.api.typing import Secret
except ImportError:
    # Before Robot 7.4
    Secret: TypeAlias = None


CacheKey: TypeAlias = str
CacheValue: TypeAlias = str | bool | int | float | list | dict | Secret
CacheValueType: TypeAlias = Literal["COLLECTION", "VALUE"]
CACHE_VALUE_TYPES: tuple[CacheValueType, ...] = ("COLLECTION", "VALUE")


class CacheEntry(TypedDict):
    """
    Base data struct for cache entry
    """

    value: CacheValue
    expires: str


CacheContents: TypeAlias = dict[CacheValueType, dict[CacheKey, CacheEntry]]
