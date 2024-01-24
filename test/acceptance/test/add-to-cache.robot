*** Settings ***
Library    CacheLibrary    robocache-A-add.json

*** Test Cases ***
Fetches data from file
    Cache Store Value    some-value    Hello, world!
