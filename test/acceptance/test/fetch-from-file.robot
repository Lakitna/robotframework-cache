*** Settings ***
Library    CacheLibrary    robocache-A-read.json

*** Test Cases ***
Fetches data from file
    ${value} =  Cache Retrieve Value    some-string-value
    log  value=${value}  level=WARN
