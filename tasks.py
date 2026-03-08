from collections.abc import Callable
from pathlib import Path
from typing import Any

from invoke import Collection, Context, task  # pyright: ignore[reportPrivateImportUsage]


##########################
# Version management tasks
@task
def set_version(c: Context, version: str):
    _run_multiple_tasks(
        c,
        (
            set_version_pyproject,
            set_version_python,
        ),
        version,
    )


@task
def set_version_pyproject(c: Context, version: str):
    print("Update version in pyproject.toml")
    c.run(f"uv version {version}")


@task
def set_version_python(_: Context, version: str):
    print("Update version in __version__.py")

    version_file_path = Path("./src/robotframework_cache/__version__.py")
    with version_file_path.open(mode="w") as f:
        f.write(f'__version__ = "{version}"\n')

    print(f"Replaced {version_file_path.as_posix()}")


#############
# Build tasks
@task
def build(c: Context):
    _run_multiple_tasks(
        c,
        (
            lint,
            test,
            build_source,
            build_docs,
        ),
    )


@task
def build_source(c: Context):
    c.run("uv build --clear")


@task
def build_docs(c: Context):
    c.run("uv run libdoc src/CacheLibrary docs/index.html")


##########
# QA tasks
@task
def lint(c: Context):
    c.run("uv run ruff check")


@task
def test(c: Context):
    _run_multiple_tasks(
        c,
        (
            test_integration_sync,
            test_integration_parallel_suite_level,
            test_integration_parallel_test_level,
            test_acceptance_parallel_test_level,
            test_acceptance_parallel_test_level,
            test_acceptance_parallel_test_level,
        ),
    )


@task
def test_integration(c: Context):
    _run_multiple_tasks(
        c,
        (
            test_integration_sync,
            test_integration_parallel_suite_level,
            test_integration_parallel_test_level,
        ),
    )


@task
def test_integration_sync(c: Context):
    print("Integration tests: Synchronous")
    c.run("uv run robot test/integration")


@task
def test_integration_parallel_suite_level(c: Context):
    print("Integration tests: Parallel, Suite level split")
    c.run("uv run pabot --pabotlib test/integration")


@task
def test_integration_parallel_test_level(c: Context):
    print("Integration tests: Parallel, Test level split")
    c.run("uv run pabot --testlevelsplit --pabotlib test/integration")


@task
def test_acceptance(c: Context):
    _run_multiple_tasks(
        c,
        (
            test_acceptance_parallel_test_level,
            test_acceptance_parallel_test_level,
            test_acceptance_parallel_test_level,
        ),
    )


@task
def test_acceptance_sync(c: Context):
    print("Acceptance tests: Synchronous")
    c.run("uv run robot test/acceptance/run.robot")


@task
def test_acceptance_parallel_suite_level(c: Context):
    print("Acceptance tests: Parallel, Suite level split")
    c.run("uv run pabot --pabotlib test/acceptance/run.robot")


@task
def test_acceptance_parallel_test_level(c: Context):
    print("Acceptance tests: Parallel, Test level split")
    c.run("uv run pabot --testlevelsplit --pabotlib test/acceptance/run.robot")


#############
# Task config
ns = Collection(
    build,
    build_source,
    build_docs,
    set_version,
    set_version_pyproject,
    set_version_python,
    lint,
    test,
    test_integration,
    test_integration_sync,
    test_integration_parallel_suite_level,
    test_integration_parallel_test_level,
    test_acceptance,
    test_acceptance_parallel_test_level,
    test_acceptance_parallel_test_level,
    test_acceptance_parallel_test_level,
)
ns.configure(
    {
        "run": {
            "echo": True,
            "echo_format": "> {command}",
        },
    },
)


#########
# Helpers
def _run_multiple_tasks(
    c: Context,
    tasks: tuple[Callable, ...],
    *args: Any,  # noqa: ANN401
    **kwargs: Any,  # noqa: ANN401
) -> None:
    print(f"Running {len(tasks)} tasks...")

    for t in tasks:
        print()
        print("--- task " + t.__name__ + " ---")
        print()

        try:
            t(c, *args, **kwargs)
        except Exception:
            print("FAILED task " + t.__name__)
            raise

    print()
    print("-" * 20)
    print()

    print(f"Ran {len(tasks)} tasks")
