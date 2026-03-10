*** Settings ***
Library     Collections
Library     DateTime
Library     OperatingSystem
Library     Process
Library     FakerLibrary


*** Variables ***
${DEFAULT_EXPIRES_IN_SECONDS}       ${3600}


*** Test Cases ***
A01 Fetches cache from file
    ${file_cache_path} =    Set Variable    robocache-A01.json

    ${cache} =    Create Dictionary    some-string-value=Lorum ipsum dolor sit amet conscuer
    Create Cache File With Content    ${file_cache_path}    ${cache}

    Run Test File With Robot    A01.robot

    [Teardown]    Remove File    ${file_cache_path}

A02 Creates a new cache file if it does not exist
    ${file_cache_path} =    Set Variable    robocache-A02.json

    Run Test File With Robot    A02.robot

    File Should Exist    ${file_cache_path}
    ${contents} =    Get File    ${file_cache_path}
    Should Contain    ${contents}    "some-value": {
    Should Contain    ${contents}    "value": "Hello, world!"

    [Teardown]    Remove File    ${file_cache_path}

A03 Resets the cache file when adding and the cache file is not json
    ${file_cache_path} =    Set Variable    robocache-A03.json

    Create File    ${file_cache_path}    <this> is #not# json!

    Run Test File With Robot    A03.robot

    File Should Exist    ${file_cache_path}
    ${contents} =    Get File    ${file_cache_path}
    Should Contain    ${contents}    "some-value": {
    Should Contain    ${contents}    "value": "Hello, world!"

    [Teardown]    Remove File    ${file_cache_path}

A04 Resets the cache file when fetching and the cache file is not json
    ${file_cache_path} =    Set Variable    robocache-A04.json

    Create File    ${file_cache_path}    <this> is #not# json!

    Run Test File With Robot    A04.robot

    File Should Exist    ${file_cache_path}
    ${contents} =    Get File    ${file_cache_path}
    Should Be Equal    ${contents}    \{\}

    [Teardown]    Remove File    ${file_cache_path}

A05 Removes expired values from the cache file
    ${file_cache_path} =    Set Variable    robocache-A05.json

    ${cache} =    Create Dictionary    expired_value=123
    Create Cache File With Content    ${file_cache_path}    ${cache}
    ...    expiration=1970-01-01T00:00:00.000000

    Run Test File With Robot    A05.robot

    File Should Exist    ${file_cache_path}
    ${contents} =    Get File    ${file_cache_path}
    Should Be Equal    ${contents}    \{\}

    [Teardown]    Remove File    ${file_cache_path}

A06 Overwrites default expiration time during import
    ${file_cache_path} =    Set Variable    robocache-A06.json

    Run Test File With Robot    A06.robot

    File Should Exist    ${file_cache_path}
    ${contents} =    Get File    ${file_cache_path}
    ${cache_content} =    Evaluate    json.loads('${contents}')    modules=json

    ${expires_date} =    Set Variable    ${cache_content['foo']['expires']}
    ${expires_date} =    DateTime.Convert Date    ${expires_date}
    ${now} =    DateTime.Get Current Date
    ${expires_in} =    DateTime.Subtract Date From Date    ${expires_date}    ${now}    result_format=number

    Should Be True
    ...    ${{ ${expires_in} > ${DEFAULT_EXPIRES_IN_SECONDS} }}
    ...    msg=Expiration time should be greater than default expiration time | Expected ${expires_in} to be greater than ${DEFAULT_EXPIRES_IN_SECONDS}

    [Teardown]    Remove File    ${file_cache_path}


*** Keywords ***
Create Cache File With Content
    [Arguments]    ${file_name}    ${key_value_pairs}    ${expiration}=${None}
    IF    '${expiration}' == '${None}'
        ${expiration} =    Evaluate
        ...    (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        ...    modules=datetime
    END

    ${cache_entries} =    Create Dictionary
    FOR    ${key}    ${value}    IN    &{key_value_pairs}
        ${entry} =    Create Dictionary
        ...    value=${value}
        ...    expires=${expiration}
        Set To Dictionary    ${cache_entries}    ${key}=${entry}
    END

    ${cache_file_content} =    Evaluate    json.dumps(${cache_entries})    modules=json
    Create File    ${file_name}    ${cache_file_content}

Run Test File With Robot
    [Arguments]    ${path}
    ${path} =    Normalize Path    ${CURDIR}/test/${path}

    ${result} =    Run Process
    ...    uv run robot --output NONE --log NONE --report NONE ${path}
    ...    shell=${True}

    IF    ${result.rc} != 0
        log    ${result.stdout}    level=WARN
        log    ${result.stderr}    level=ERROR

        Fail    Acceptance test failed. Details above.
    END
