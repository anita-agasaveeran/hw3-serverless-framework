# Orders Service – Serverless Patterns Workshop Module 3

The Orders microservice from Module 3 of the AWS [Serverless Patterns workshop](https://catalog.workshops.aws/serverless-patterns/en-US/module3/sam-python/setup) (SAM, Python). Customers can place, view, edit, and cancel restaurant orders through a REST API protected by the Cognito user pool from the Users service (`../users`).

## Architecture

```
Client ──(Cognito ID token)──▶ API Gateway (Prod) ──▶ Lambda functions ──▶ DynamoDB
                                     │                      │
                          Cognito authorizer         PyUtils layer + Powertools layer
                        (Users module user pool)     (logging, metrics, idempotency)
```

Everything is defined in [`template.yaml`](template.yaml) and deployed as the `ws-serverless-patterns-orders` stack. The stack takes the Users stack's Cognito **UserPool ID** as a parameter and uses it for its API authorizer.

| Resource | Type | Purpose |
|---|---|---|
| `WorkshopApiGateway` | API Gateway | `Prod` stage, Cognito authorizer as the default, X-Ray tracing |
| `OrdersTable` | DynamoDB | Orders, keyed by `userId` (hash) and `orderId` (range) |
| `IdempotencyTable` | DynamoDB | Powertools idempotency records (TTL on `expiration`) |
| `PyUtils` | Lambda layer | Shared `get_order()` helper in `src/layers/utils.py` |
| 5 functions | Lambda (Python 3.12) | One per API operation (see below) |

## API

All routes require an `Authorization` header with a Cognito ID token.

| Method | Path | Function | Behavior |
|---|---|---|---|
| `POST` | `/orders` | `AddOrderFunction` | Creates an order with status `PLACED`. It's idempotent on `orderId`. |
| `GET` | `/orders` | `ListOrdersFunction` | Lists the caller's orders |
| `GET` | `/orders/{orderId}` | `GetOrderFunction` | Returns one order |
| `PUT` | `/orders/{orderId}` | `EditOrderFunction` | Updates an order |
| `DELETE` | `/orders/{orderId}` | `CancelOrderFunction` | Sets status to `CANCELED` if the order is `PLACED` and under 10 minutes old. Otherwise it returns `400`. |

Orders are queried by the caller's Cognito `sub`, so users can only see their own orders.

## Patterns covered

- **Composite-key data model:** each user's orders sit under one partition key.
- **Shared code in a Lambda layer:** `PyUtils` is used by the get, edit, and cancel functions.
- **Business rules enforced in DynamoDB:** cancel is a single `update_item` with a `ConditionExpression`, so the status and age checks and the update happen atomically.
- **Idempotency:** Powertools `@idempotent_function`. Repeated POSTs with the same `orderId` return the same result and don't create duplicates.
- **Observability:** Powertools structured JSON logging (`service: orders`), custom CloudWatch metrics (`SuccessfulOrder`, `OrderTotal` in the `ServerlessWorkshop` namespace), and X-Ray tracing.

## Project layout

```
orders/
├── template.yaml
├── samconfig.toml
├── src/
│   ├── api/order/
│   │   ├── create/create_order.py
│   │   ├── get/get_order.py
│   │   ├── list/list_orders.py
│   │   ├── edit/edit_order.py
│   │   └── cancel/cancel_order.py
│   └── layers/utils.py
└── tests/
    ├── requirements.txt
    ├── integration/    # conftest.py fixtures + test_api.py
    └── unit/
```

## Prerequisites

- The Users stack (`ws-serverless-patterns`) is already deployed from the parent folder
- AWS CLI with credentials (`aws login`)
- AWS SAM CLI (`brew install aws-sam-cli`)
- Python 3.12 (`brew install python@3.12`). It must match the Lambda runtime or `sam build` fails.

## Deploy

From this folder:

```bash
sam build
sam deploy --guided --stack-name ws-serverless-patterns-orders
```

When prompted for `UserPool`, enter the `UserPool` output of the nested users stack. After the first guided deploy, `sam build && sam deploy` is enough because the settings are saved in `samconfig.toml`.

## Run the integration tests

The tests create a Cognito test user, call the live API, and clean up after themselves.

```bash
# one-time setup (from the repo root)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r module-3/ws-serverless-patterns/orders/tests/requirements.txt "botocore[crt]"

# each new terminal, from this folder
source ../../../.venv/bin/activate
export USERS_STACK_NAME=<nested users stack name, e.g. ws-serverless-patterns-users-XXXX>
export ORDERS_STACK_NAME=ws-serverless-patterns-orders

pytest tests/integration -v
```

Expected result: **8 passed**.

## Notes and gotchas (running locally instead of the workshop IDE)

- The workshop commands assume the browser-based workshop IDE and `~/workshop`. On a Mac, run them from this repo instead, and install `wget` (`brew install wget`), because `module3_setup.sh` uses it.
- `USERS_STACK_NAME` must be the **nested** users stack. The parent stack has no outputs.
- `botocore[crt]` is required for boto3 to use credentials from `aws login`.
- In zsh, `cmd="pytest ..."; $cmd` doesn't split words. Run `pytest` directly in loops or use `${=cmd}`.
- Right after a deploy, new API routes can take a few seconds to go live. If tests fail immediately after `sam deploy`, rerun them.
- In the "Cancel an Order" step, the workshop's `cd .../cancel` is a typo. `cancel_order.py` belongs in `src/api/order/cancel/` in this folder.

## Cleanup

```bash
sam delete --stack-name ws-serverless-patterns-orders
```
