*** Settings ***
Library     CacheLibrary    robocache-A06.json    expire_in_seconds=86400


*** Test Cases ***
Fetches data from file
    Cache Store Value    foo    bar
