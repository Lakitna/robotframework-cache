*** Settings ***
Library             Process
Library             FakerLibrary
Library             pabot.PabotLib
Library             CacheLibrary

# Clean up the random data created by these tests
Suite Setup         Run Only Once    Cache Reset
Suite Teardown      Run On Last Process    Cache Reset

*** Variables ***
${ITERATIONS}       50
@{SUPPORTED_PRIMITIVES}
...  str
...  bool
...  int
...  float

*** Test Cases ***
Store and retrieve random string data
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${len} =    FakerLibrary.Pyint    min_value=1    max_value=100
        ${key} =    FakerLibrary.Pystr    min_chars=${len}    max_chars=${len}
        ${input} =    FakerLibrary.Pystr    min_chars=${len}    max_chars=${len}
        Cache Store value    ${key}    ${input}

        ${retrieved} =    Cache Retrieve value    ${key}
        Should Be Equal    ${retrieved}    ${input}
    END

Store and retrieve random int data
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${len} =    FakerLibrary.Pyint    min_value=1    max_value=100
        ${key} =    FakerLibrary.Pystr    min_chars=${len}    max_chars=${len}
        ${input} =    FakerLibrary.Pyint
        Cache Store value    ${key}    ${input}

        ${retrieved} =    Cache Retrieve value    ${key}
        Should Be Equal    ${retrieved}    ${input}
    END

Store and retrieve random float data
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pyfloat
        Cache Store value    random-float    ${input}

        ${retrieved} =    Cache Retrieve value    random-float
        Should Be Equal    ${retrieved}    ${input}
    END

Store and retrieve random dict data
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pydict    value_types=${SUPPORTED_PRIMITIVES}
        Cache Store value    random-dict    ${input}

        ${retrieved} =    Cache Retrieve value    random-dict
        Should Be Equal    ${retrieved}    ${input}
    END

Store and retrieve random list data
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pylist    value_types=${SUPPORTED_PRIMITIVES}
        Cache Store value    random-list    ${input}

        ${retrieved} =    Cache Retrieve value    random-list
        Should Be Equal    ${retrieved}    ${input}
    END

Store and retrieve specific characters and keywords that break some implementations
    ${set} =    Create List
    ...  ${True}
    ...  ${False}
    ...  ${EMPTY}
    ...  "
    ...  '
    ...  `
    ...  (
    ...  )
    ...  {
    ...  }
    ...  [
    ...  ]
    ...  :
    ...  ,

    FOR    ${i}    ${input}    IN ENUMERATE    @{set}
        Cache Store value    set    ${input}

        ${retrieved} =    Cache Retrieve value    set
        Should Be Equal    ${retrieved}    ${input}
    END

Retrieve when not stored
    ${retrieved} =    Cache Retrieve value    does-not-exist
    Should Be Equal    ${retrieved}    ${None}

Remove stored data
    Cache Store value    random-data    amazing data
    ${preRemove} =    Cache Retrieve value    random-data
    Cache Remove value    random-data
    ${postRemove} =    Cache Retrieve value    random-data

    Should Not Be Equal    ${preRemove}    ${postRemove}
    Should Be Equal    ${preRemove}    amazing data
    Should Be Equal    ${postRemove}    ${None}
