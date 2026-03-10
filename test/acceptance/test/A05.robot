*** Settings ***
Library     CacheLibrary    robocache-A05.json


*** Test Cases ***
Fetches data from file
    ${value} =    Cache Retrieve Value    expired_value
    Should Be Equal    ${value}    ${None}
