# Module 4 - Async Services with OpenAPI specification

## Prerequisites

1. Complete module 2 or Deploy the SAM application in the `start_state` directory
2. Ensure your terminal can authenticate and use the SAM CLI and the AWS CLI.

## Deploy the completed module

1. Find the Cognito User Pool Id from Module 2.
   1. Navigate to CloudFormation
   2. Select the `serverless-workshop` stack
   3. Navigate to the **Outputs** tab
   4. Find the `UserPool` key and copy the value.
2. Open a terminal window to the `module4/sam-python` directory
3. Run `sam build`. When completed...
4. Run `sam deploy --guided`. Accept all default values **except** when prompted for `Parameter UserPool`. Enter the Cognito User Pool Id value from above.

## Run the integration tests

1. Set two environment variables:

```
export USERS_STACK_NAME=ws-serverless-patterns-users
export USERPROFILE_STACK_NAME=ws-serverless-patterns-userprofile
```

2. Install the python testing module
   1. Run the following command in your command line: `pip install -U pytest`
   2. Check that you installed a working version: `pytest --version`

3. Run the tests

```
python -m pytest tests/integration -v
```

#### Example output from a successful execution of the tests

```
===================================== test session starts ======================================
platform darwin -- Python 3.9.5, pytest-7.2.0, pluggy-1.0.0 -- /Users/xxxx/.pyenv/versions/3.9.5/bin/python
cachedir: .pytest_cache
rootdir: /Users/xxxx/dev/serverless-workshop-code/module4/sam-python/tests/integration, configfile: pyproject.toml
plugins: mock-3.7.0, Faker-8.12.1
collected 10 items

tests/integration/test_api_gateway_favorites.py::test_access_to_the_favorites_without_authentication
---------------------------------------- live log setup ----------------------------------------
2022-11-17 15:34:46 [    INFO] Clearing DynamoDb tables (conftest.py:96)
PASSED                                                                                   [ 10%]
tests/integration/test_api_gateway_favorites.py::test_add_user_favorite PASSED           [ 20%]
tests/integration/test_api_gateway_favorites.py::test_security_of_user_favorites PASSED  [ 30%]
tests/integration/test_api_gateway_favorites.py::test_delete_user_favorite PASSED        [ 40%]
tests/integration/test_api_gateway_user_addresses.py::test_access_to_the_addresses_without_authentication PASSED [ 50%]
tests/integration/test_api_gateway_user_addresses.py::test_add_user_address_with_invalid_fields PASSED [ 60%]
tests/integration/test_api_gateway_user_addresses.py::test_add_user_address PASSED       [ 70%]
tests/integration/test_api_gateway_user_addresses.py::test_update_user_address PASSED    [ 80%]
tests/integration/test_api_gateway_user_addresses.py::test_security_of_user_addresses PASSED [ 90%]
tests/integration/test_api_gateway_user_addresses.py::test_delete_user_address PASSED    [100%]

===================================== 10 passed in 20.39s ======================================
```
