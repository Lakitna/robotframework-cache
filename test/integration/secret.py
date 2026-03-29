from dataclasses import dataclass

from robot.api.deco import keyword


@dataclass
class FakeSecret:
    """
    Fake Secret.

    Used only when running with a Robot version that does not support Secrets.
    """

    value: str = ""


try:
    from robot.api.types import Secret  # pyright: ignore[reportRedeclaration]
except ImportError:
    # Before Robot 7.4
    Secret = FakeSecret


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
    """Return true when the current Robot version supports Secrets (>= 7.4)"""
    return Secret.__name__ != "FakeSecret"
