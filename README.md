# hw3-serverless-framework

CMPE 272 Homework 3: working through the AWS [Serverless Patterns workshop](https://catalog.workshops.aws/serverless-patterns/en-US) using **AWS SAM** and **Python 3.12**. Across the modules, the project builds a serverless food-ordering backend. It has a Users service protected by Amazon Cognito, an Orders service, and event-driven order status updates.

## Modules

| Module | Pattern | Folder | Status |
|---|---|---|---|
| 2 | Synchronous invocation: REST API → Lambda → DynamoDB | [`module-2/`](module-2/ws-serverless-patterns) | ✅ |
| 3 | Orders service: layers, idempotency, observability | [`module-3/`](module-3/ws-serverless-patterns) | ✅ |
| 4 | *To be added* | `module-4/` | ⏳ |
| 5 | Polling: EventBridge → Lambda, client polls for status | [`module-5/`](module-5/ws-serverless-patterns) | ✅ |

Each module folder is a self-contained `ws-serverless-patterns/` project (the workshop's start state plus my changes), so it can be built and deployed on its own.

---

### Module 2 – Synchronous Invocation

[`module-2/ws-serverless-patterns/users`](module-2/ws-serverless-patterns/users)

A Users microservice: API Gateway → Lambda → DynamoDB, secured with a Cognito user pool and a custom Lambda **authorizer** that restricts routes by user and admin group.

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/users` | List users (admins only) |
| `POST` | `/users` | Create a user (admins only) |
| `GET` / `PUT` / `DELETE` | `/users/{userid}` | Read, update, or delete a user. Users can only reach their own record; admins can reach any. |

Includes unit tests with mocked AWS services and integration tests against the deployed API.

### Module 3 – Orders Service

[`module-3/ws-serverless-patterns/orders`](module-3/ws-serverless-patterns/orders) · [README](module-3/ws-serverless-patterns/orders/README.md)

An Orders API (`POST`/`GET /orders`, `GET`/`PUT`/`DELETE /orders/{orderId}`) that uses the Users service's Cognito pool for its authorizer. It demonstrates:

- A composite-key DynamoDB table (`userId` + `orderId`)
- Shared code in a Lambda layer
- Business rules enforced with a DynamoDB `ConditionExpression` (cancel only a `PLACED` order that's under 10 minutes old)
- Idempotent order creation with Powertools
- Structured logging, custom CloudWatch metrics, and X-Ray tracing

### Module 4 – *To be added*

<!-- TODO: add Module 4 summary, folder link, and README link -->

_Coming soon._

### Module 5 – Polling

[`module-5/ws-serverless-patterns/orderstatus`](module-5/ws-serverless-patterns/orderstatus) · [README](module-5/ws-serverless-patterns/orderstatus/README.md)

A restaurant publishes `order.updated` events to an EventBridge bus (`Orders-dev`). A Lambda function writes the new status to the Orders table. The client runs `polling-api.sh` against `GET /orders/{orderId}` until the status becomes `IN-PROCESS`.

---

## Prerequisites

- An AWS account and AWS CLI v2 (`aws login`)
- AWS SAM CLI (`brew install aws-sam-cli`)
- Python **3.12** (`brew install python@3.12`), to match the Lambda runtime
- `wget` (`brew install wget`), used by the workshop setup scripts

## Common workflow

```bash
# deploy a stack (first time with --guided; settings saved to samconfig.toml)
cd module-N/ws-serverless-patterns/<service>
sam build
sam deploy --guided

# integration tests (one shared venv at the repo root)
python3.12 -m venv .venv            # from the repo root, once
source .venv/bin/activate
pip install -r <service>/tests/requirements.txt "botocore[crt]"
pytest tests/integration -v
```

Each service's README lists the environment variables its tests need (stack names, Cognito client ID).

## Running locally vs. the workshop IDE

The workshop assumes its browser-based IDE and `~/workshop`. I ran everything from a Mac terminal, which needed a few adjustments:

- Install Python 3.12 alongside newer versions, or `sam build` fails runtime validation.
- Install `botocore[crt]` in the venv so boto3 can use credentials from `aws login`.
- The users service is a **nested** stack, so its outputs (`UserPool`, `CognitoAuthCommand`, `APIEndpoint`) appear on `ws-serverless-patterns-users-<id>`, not on the parent stack.
- In zsh, quote Cognito auth parameters (`'USERNAME=...,PASSWORD=...'`) so characters like `*` aren't expanded.
- The Cognito pool signs users in with email, so a user's Cognito **user name** is a UUID (`sub`), which is what order records are keyed by.

## Cleanup

Delete the stacks when you're done to avoid charges:

```bash
sam delete --stack-name ws-serverless-patterns-polling
sam delete --stack-name ws-serverless-patterns
```
