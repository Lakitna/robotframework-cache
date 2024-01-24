*** Settings ***
Library             Process
Library             FakerLibrary
Library             pabot.PabotLib
Library             CacheLibrary

# Prevent the random data created by these tests to interfere with other tests
Suite Setup         Run Only Once    Cache Reset
Suite Teardown      Run On Last Process    Cache Reset

*** Test Cases ***
Only runs the keyword once when called twice with arg
    ${result} =  Run Keyword And Cache Output    Add One To Number    1
    Should Be Equal    ${result}    ${2}

    ${result} =  Run Keyword And Cache Output    Add One To Number    1
    Should Be Equal    ${result}    ${2}

Only runs the keyword once when called twice with kwarg
    ${result} =  Run Keyword And Cache Output    Add One To Number    input=1
    Should Be Equal    ${result}    ${2}

    ${result} =  Run Keyword And Cache Output    Add One To Number    input=1
    Should Be Equal    ${result}    ${2}

Only runs the keyword again when args change
    ${result} =  Run Keyword And Cache Output    Add One To Number    1
    Should Be Equal    ${result}    ${2}

    ${result} =  Run Keyword And Cache Output    Add One To Number    2
    Should Be Equal    ${result}    ${3}

Only runs the keyword once when called twice without arg
    ${first_result} =  Run Keyword And Cache Output    FakerLibrary.Random Number
    ${second_result} =  Run Keyword And Cache Output    FakerLibrary.Random Number
    Should Be Equal    ${second_result}    ${first_result}

*** Keywords ***
Add One To Number
    [Arguments]    ${input}
    ${output} =  Evaluate    int(${input}) + int(1)
    RETURN  ${output}
