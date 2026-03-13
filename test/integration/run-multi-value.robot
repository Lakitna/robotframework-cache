*** Settings ***
Library             Collections
Library             Process
Library             FakerLibrary
Library             pabot.PabotLib
Library             CacheLibrary

# Clean up the data created by these tests
Suite Setup         Run Only Once    Cache Reset
Suite Teardown      Run On Last Process    Cache Reset


*** Variables ***
${ITERATIONS}               50
@{SUPPORTED_PRIMITIVES}
...                         str
...                         bool
...                         int
...                         float


*** Test Cases ***
Retrieve one value from set at a time
    ${input} =    Evaluate    list(range(10))
    Cache Store Collection    set-data-${TEST_NAME}    @{input}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${0}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${1}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${2}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${3}

Sets and values used together
    ${input} =    Evaluate    list(range(10))
    Cache Store Value    val-data-${TEST_NAME}    ${input}
    Cache Store Collection    set-data-${TEST_NAME}    @{input}

    ${retrieved_val} =    Cache Retrieve Value    val-data-${TEST_NAME}
    ${retrieved_set_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}

    Lists Should Be Equal    ${retrieved_val}    ${input}
    Should Be Equal As Integers    ${retrieved_set_val}    ${0}

Sets can't be retrieved as value
    ${input} =    Evaluate    list(range(10))
    Cache Store Collection    set-data-${TEST_NAME}    @{input}

    ${retrieved_val} =    Cache Retrieve Value    set-data-${TEST_NAME}
    Should Be Equal    ${retrieved_val}    ${None}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal    ${retrieved_val}    ${0}

Values can't be retrieved as set
    ${input} =    Evaluate    list(range(10))
    Cache Store Value    val-data-${TEST_NAME}    ${input}

    ${retrieved_val} =    Cache Retrieve Value    val-data-${TEST_NAME}
    Should Be Equal    ${retrieved_val}    ${input}

    ${retrieved_val} =    Cache Retrieve Value From Collection    val-data-${TEST_NAME}
    Should Be Equal    ${retrieved_val}    ${None}

Returns None when the set is empty
    ${input} =    Evaluate    list(range(3))
    Cache Store Collection    set-data-${TEST_NAME}    @{input}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${0}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${1}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal As Integers    ${retrieved_val}    ${2}

    ${retrieved_val} =    Cache Retrieve Value From Collection    set-data-${TEST_NAME}
    Should Be Equal    ${retrieved_val}    ${None}

Returns None when the set does not exist
    ${retrieved_val} =    Cache Retrieve Value From Collection    i-do-not-exist
    Should Be Equal    ${retrieved_val}    ${None}

Store and retrieve random string data
    ${len} =    FakerLibrary.Pyint    min_value=1    max_value=100

    ${value_set} =    Create List
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pystr    min_chars=${len}    max_chars=${len}
        Append To List    ${value_set}    ${input}
    END
    Cache Store Collection    random-strings    @{value_set}

    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${retrieved} =    Cache Retrieve Value From Collection    random-strings    pick=first    remove_value=True
        Should Be Equal    ${retrieved}    ${value_set}[${i}]
    END

Store and retrieve random int data
    ${value_set} =    Create List
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pyint
        Append To List    ${value_set}    ${input}
    END
    Cache Store Collection    random-ints    @{value_set}

    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${retrieved} =    Cache Retrieve Value From Collection    random-ints    pick=first    remove_value=True
        Should Be Equal    ${retrieved}    ${value_set}[${i}]
    END

Store and retrieve random float data
    ${value_set} =    Create List
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pyfloat
        Append To List    ${value_set}    ${input}
    END
    Cache Store Collection    random-floats    @{value_set}

    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${retrieved} =    Cache Retrieve Value From Collection    random-floats    pick=first    remove_value=True
        Should Be Equal    ${retrieved}    ${value_set}[${i}]
    END

Store and retrieve random dict sdata
    ${value_set} =    Create List
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pydict    value_types=${SUPPORTED_PRIMITIVES}
        Append To List    ${value_set}    ${input}
    END
    Cache Store Collection    random-dicts    @{value_set}

    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${retrieved} =    Cache Retrieve Value From Collection    random-dicts    pick=first    remove_value=True
        Should Be Equal    ${retrieved}    ${value_set}[${i}]
    END

Store and retrieve random list data
    ${value_set} =    Create List
    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${input} =    FakerLibrary.Pylist    value_types=${SUPPORTED_PRIMITIVES}
        Append To List    ${value_set}    ${input}
    END
    Cache Store Collection    random-lists    @{value_set}

    FOR    ${i}    IN RANGE    ${ITERATIONS}
        ${retrieved} =    Cache Retrieve Value From Collection    random-lists    pick=first    remove_value=True
        Should Be Equal    ${retrieved}    ${value_set}[${i}]
    END
