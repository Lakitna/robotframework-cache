*** Settings ***
Library    CacheLibrary    robocache-A01.json

*** Test Cases ***
Fetches expected data from file
    ${value} =  Cache Retrieve Value    some-string-value
    Should Be Equal    ${value}    Lorum ipsum dolor sit amet conscuer
