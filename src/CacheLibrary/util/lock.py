from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from pabot.pabotlib import PabotLib


@contextmanager
def lock(pabotlib: PabotLib, name: str) -> Generator[None, Any, None]:
    """Context manager that acquires and releases pabot locks"""
    try:
        pabotlib.acquire_lock(name)
        yield
    finally:
        pabotlib.release_lock(name)
