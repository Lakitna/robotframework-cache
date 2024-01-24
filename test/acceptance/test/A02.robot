*** Settings ***
Library    CacheLibrary    robocache-A02.json

*** Test Cases ***
Fetches data from file
    Cache Store Value    some-value    Hello, world!
