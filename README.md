# Robot Framework Cache Library

Caching mechanism for Robot Framework tests. Works within a single test run and across multiple test
runs. Works with Pabot, though it requires `--pabotlib`.

## Why

In one word: Performance.

When testing, we sometimes want to reuse work we did in a different test. Examples of this include
API gateway sessions, user sessions, and expensive calculations. If we can reuse this work, we don't
need to spend time redoing it every test.

Sometimes we even want to reuse the work we did in a previous test run. This allows us to speed up
our workflow when writing tests.

CacheLibrary solves these problems by providing a caching mechanism that's stored both in memory and
in a file.

## Pabot

CacheLibrary works with Pabot, but requires the `--pabotlib` command line argument.

Supporting Pabot is achieved by a combination of [locks](https://pabot.org/PabotLib.html#locks)
and [parallel variables](https://pabot.org/PabotLib.html#valuetransfer). This makes CacheLibrary
stable when run in parallel without losing stored values.

All CacheLibrary tests are run with Pabot to ensure that the above statements are true.

## Installation

1. Install CacheLibrary with pip. Run the following command:

    ```shell
    pip install robotframework-cache
    ```

2. Import it from your `.robot` or `.resource` file. Add the following line to the `Settings`
    section:

    ```robotframework
    Library    CacheLibrary
    ```

3. Add the cache file to `.gitignore`. If you use the default file path, add the following to your
    `.gitignore`:

    ```plain
    robotframework-cache.json
    ```

## Examples

### Basic usage

Store a value, and retrieve it later

```robotframework
Cache Store Value    foo    Hello, world

# Do something interesting

${value} =    Cache Retrieve Value    foo
Should Be Equal    ${value}    Hello, world
```

### Caching output of a keyword

The keyword below fetches or reuses a session token.

Everwhere you need the session token, you can use this keyword. CacheLibrary will ensure that
you're only requesting a new session token once. After which it will reuse the session token.

CacheLibrary will even do this across test runs. This way, you don't have to request the session
token every time you run a test. This can be a great help while making or debugging a test.

```robotframework
Get Api Session Token
    ${cache_key} =    Set Variable    api-session
    ${cached_token} =    Cache Retrieve value    ${cache_key}
    IF    $cached_token is not $None
        RETURN    ${cached_token}
    END

    # Request a new session token

    Cache Store Value    ${cache_key}    ${new_token}
    RETURN    ${new_token}
```

Alternatively, you can use the convenience keyword `Run Keyword And Cache Output` to do the same
thing:

```robotframework
Get Api Session Token
    ${token} =    Run Keyword And Cache Output    Get Api Session Token Uncached
    RETURN    ${token}

Get Api Session Token Uncached
    [Tags]    robot:private

    # Request a new session token

    RETURN    ${new_token}
```

### Retention of cached values

When storing a value in the cache, you also define how long it should remain valid.

```robotframework
Cache Store Value    key=amazing    value=beautiful    expire_in_seconds=10
```

The value `beautiful` will expire 10 seconds from the moment it's stored.

If you try to retrieve an expired value with `Cache Retrieve Value` it will return `None` like it
would if it was never stored.

The default retention is 3600 seconds (1 hour).

### Changing the cache file path

When importing the library, you can provide an alternative cache file path.

```robotframework
Library    CacheLibrary    file_path=alternative-cache-file.json
```

### Cache too big warnings

A big cache file can indicate an issue with CacheLibary or with how it's used. To help you spot
these issues, CacheLibrary will warn you if the cache file is very big. By default it will warn if
the file is larger than 500Kb.

You can change this threshold when importing the library. For example, changing it to 1Mb:

```robotframework
Library    CacheLibrary    file_size_warning_bytes=1000000
```

## Resetting the cache

If you need to reset the cache for any reason, simply remove or empty the cache file
(default: `robotframework-cache.json`).

Alternatively, you can use the keyword `Cache Reset` for the same purpose.

## Contributing

Contributions are always welcome :)

## Testing CacheLibrary

1. Install the dependencies with `poetry`.

    ```shell
    poetry install --with test
    ```

2. Run the following commands in the repository root.

    ```shell
    robot test/integration
    robot test/acceptance/run.robot

    pabot --pabotlib test/integration
    pabot --pabotlib test/acceptance/run.robot

    pabot --testlevelsplit --pabotlib test/integration
    pabot --testlevelsplit --pabotlib test/acceptance/run.robot
    ```
