*** Settings ***
Library         Collections
Library         Process
Library         FakerLibrary
Library         pabot.PabotLib
Library         CacheLibrary

# Clean up the data created by these tests
Suite Setup     Run Only Once    Cache Reset


*** Variables ***
${ITERATIONS}                   50
@{SUPPORTED_PRIMITIVES}
...                             str
...                             bool
...                             int
...                             float
@{COMPLEX_COLLECTION_TYPES}
...                             str
...                             bool
...                             int
...                             float
...                             list
...                             dict


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

Remove value by index
    ${value_set} =    Generate Complex Collection    size=${ITERATIONS}

    Cache Store Collection    set-data-${TEST_NAME}    @{value_set}

    ${bad_index} =    Evaluate    ${ITERATIONS} + 1
    Run Keyword And Expect Error
    ...    Could not remove value from collection. Index out of range. Index ${bad_index} does not exist in cache collection 'set-data-Remove value by index'. Expected index between 0 and ${{ ${ITERATIONS} - 1 }}. IndexError: pop index out of range
    ...    Cache Remove Value From Collection
    ...    set-data-${TEST_NAME}
    ...    index=${bad_index}

    FOR    ${value}    IN    @{value_set}
        ${retrieved} =    Cache Retrieve Value From Collection
        ...    set-data-${TEST_NAME}
        ...    pick=first
        ...    remove_value=False
        Should Be Equal    ${retrieved}    ${value}

        Cache Remove Value From Collection    set-data-${TEST_NAME}    index=0
    END

    # Should now be empty
    ${retrieved} =    Cache Retrieve Value From Collection
    ...    set-data-${TEST_NAME}
    ...    remove_value=False
    Should Be Equal    ${retrieved}    ${None}

Remove value by value
    ${value_set} =    Generate Complex Collection    size=${ITERATIONS}

    Cache Store Collection    set-data-${TEST_NAME}    @{value_set}

    ${bad_value} =    Set Variable    abcdefghijklmnopqrstuvwxyz
    Run Keyword And Expect Error
    ...    Could not remove value from collection. Value not in collection. Value '${bad_value}' does not exist in cache collection 'set-data-${TEST_NAME}'. ValueError: list.remove(x): x not in list
    ...    Cache Remove Value From Collection
    ...    set-data-${TEST_NAME}
    ...    value=${bad_value}

    FOR    ${value}    IN    @{value_set}
        ${retrieved} =    Cache Retrieve Value From Collection
        ...    set-data-${TEST_NAME}
        ...    pick=first
        ...    remove_value=False
        Should Be Equal    ${retrieved}    ${value}

        Cache Remove Value From Collection    set-data-${TEST_NAME}    value=${retrieved}
    END

    # Should now be empty
    ${retrieved} =    Cache Retrieve Value From Collection
    ...    set-data-${TEST_NAME}
    ...    remove_value=False
    Should Be Equal    ${retrieved}    ${None}

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

Store and retrieve random dict data
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


*** Keywords ***
Generate Complex Collection
    [Arguments]    ${size}    ${types}=${COMPLEX_COLLECTION_TYPES}
    ${collection} =    Create List
    ${types} =    FakerLibrary.Random Elements    ${types}    length=${size}

    FOR    ${type}    IN    @{types}
        IF    '${type}' == 'str'
            ${val} =    FakerLibrary.Pystr
        ELSE IF    '${type}' == 'int'
            ${val} =    FakerLibrary.Pyint
        ELSE IF    '${type}' == 'float'
            ${val} =    FakerLibrary.Pyfloat
        ELSE IF    '${type}' == 'bool'
            ${val} =    FakerLibrary.Pybool
        ELSE IF    '${type}' == 'list'
            ${val} =    FakerLibrary.Pylist    value_types=${SUPPORTED_PRIMITIVES}
        ELSE IF    '${type}' == 'dict'
            ${val} =    FakerLibrary.Pydict    value_types=${SUPPORTED_PRIMITIVES}
        ELSE
            Fail    Unsupported type '${type}'
        END

        Append To List    ${collection}    ${val}
    END

    RETURN    ${collection}
