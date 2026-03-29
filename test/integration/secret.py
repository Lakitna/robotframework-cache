from typing import TypeAlias

from robot.api.deco import keyword

try:
    from robot.api.typing import Secret
except ImportError:
    # Before Robot 7.4
    Secret: TypeAlias = None


@keyword
def convert_to_secret(val: str):
    """Convert a string to a secret"""
    return Secret(val)


@keyword
def should_be_equal_as_secrets(first, second):  # noqa: ANN001
    """
    Assert that 2 secrets contain the same value.

    No type annotations to prevent automatic type conversion.
    """
    assert isinstance(first, Secret), "First is not a Secret"  # noqa: S101
    assert isinstance(second, Secret), "Second is not a Secret"  # noqa: S101
    assert first.value == second.value, "First does not equal Second"  # noqa: S101


@keyword
def is_secret_supported() -> bool:
    return Secret is not None
