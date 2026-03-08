*** Settings ***
Library     CacheLibrary    robocache-A04.json


*** Test Cases ***
Fetches data from file
    ${value} =    Cache Retrieve Value    some-string-value
    Should Be Equal    ${value}    ${None}
