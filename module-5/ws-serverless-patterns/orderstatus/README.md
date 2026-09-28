# Order Status Service – Serverless Patterns Workshop Module 5 (Polling)

The Order Status service from Module 5 of the AWS [Serverless Patterns workshop](https://catalog.workshops.aws/serverless-patterns/en-US/module5/sam-python/polling) (SAM, Python). It shows the **polling pattern**: a restaurant publishes order updates to an EventBridge bus, a Lambda function writes the new status to the Orders table, and the client polls the Orders API until the status it wants appears.

## Architecture

```
Restaurant ──put-events──▶ EventBridge bus "Orders-dev"
                                   │  rule: source=restaurant, detail-type=order.updated
                                   ▼
                        UpdateOrderStatusFunction ──UpdateItem──▶ OrdersTable (Orders service)
                                                                        ▲
Client ──(Cognito ID token)──▶ GET /orders/{orderId} (Orders API) ──────┘
          polls every 2s until status == IN-PROCESS  (polling-api.sh)
```

Everything is defined in [`template.yaml`](template.yaml) and deployed as the `ws-serverless-patterns-polling` stack.

| Resource | Type | Purpose |
|---|---|---|
| `RestaurantBus` | EventBridge event bus | `Orders-${Stage}` (`Orders-dev`) receives restaurant order events |
| `UpdateOrderStatusFunction` | Lambda (Python 3.12) | Triggered by `order.updated` events from source `restaurant`. It sets `data.status` on the matching order. |

**Parameters**

| Parameter | Value |
|---|---|
| `OrdersTablename` | The `OrdersTable` output of the Module 5 nested orders stack |
| `UserPool` | The Cognito user pool ID from the users stack |
| `Stage` | `dev` (default) |

**Outputs:** `RestaurantBusName`, `OrdersTablename`, `UserPool`

This service has no API of its own. Clients read order status through the existing Orders API (`GET /orders/{orderId}`), and the function updates the Orders service's table directly.

## How the update works

[`src/api/update_order_status.py`](src/api/update_order_status.py) reads `event.detail.data` and runs:

```
UpdateItem  Key = { userId, orderId }
            SET data.status = :status
```

`userId` must be the order owner's **Cognito user name**. This pool signs users in with email, so the user name is the UUID `sub`, not the email address. `orderId` must be an existing order. If no item matches, DynamoDB returns `ValidationException: The document path provided in the update expression is invalid for update`. The function logs that error, and the status doesn't change.

## Project layout

```
orderstatus/
├── template.yaml
├── samconfig.toml
├── polling-api.sh                 # polls GET /orders/{id} until status == IN-PROCESS
├── src/api/update_order_status.py
├── events/
│   ├── event-new-order.json       # body for POST /orders (orderId O2)
│   ├── test-order-update.json     # put-events entry that sets O2 to IN-PROCESS
│   ├── test-order-event.json
│   └── event-update-order.json    # sample EventBridge event for sam local invoke
└── tests/integration/             # conftest.py, test_order.py, order.json
```

## Deploy

From this folder:

```bash
sam build
sam deploy --guided --stack-name ws-serverless-patterns-polling
```

When prompted, set `OrdersTablename` to the Module 5 orders table and `UserPool` to the users stack's pool ID. The values are saved in `samconfig.toml`, so after the first deploy `sam build && sam deploy` is enough.

## Poll the API (workshop walkthrough)

**1. Get an ID token** from the users stack's `CognitoAuthCommand`. Quote the parameters so zsh doesn't expand characters like `*`:

```bash
export ID_TOKEN=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH \
  --client-id <UserPoolClient> \
  --auth-parameters 'USERNAME=<email>,PASSWORD=<password>' \
  --query 'AuthenticationResult.IdToken' --output text)
```

**2. Set the Orders API URL.** Use the `Module3ApiEndpoint` output of the **nested Module 5 orders stack** (`ws-serverless-patterns-orders-<id>`). It ends in `/dev/`, which `${URL}orders/...` relies on.

```bash
export URL=https://<api-id>.execute-api.us-east-1.amazonaws.com/dev/
```

**3. Create the test order:**

```bash
curl -X POST -H "Authorization:$ID_TOKEN" -d @events/event-new-order.json $URL/orders
```

**4. Start polling** in terminal 1:

```bash
sh ./polling-api.sh ${URL}orders/O2 $ID_TOKEN
# Still waiting for IN-PROCESS status
```

**5. Simulate the restaurant update** in terminal 2. First set `userId` in `events/test-order-update.json` to your Cognito user name (the UUID).

```bash
aws events put-events --entries file://events/test-order-update.json
# FailedEntryCount: 0
```

Terminal 1 then prints **"Order status matches desired result of IN-PROCESS. Polling is complete!"**

### Replay the demo

After the order reaches `IN-PROCESS`, the poller finishes immediately. To reset the order to `PLACED`, send the same event with the status changed:

```bash
sed 's/IN-PROCESS/PLACED/' events/test-order-update.json > /tmp/reset-order.json
aws events put-events --entries file:///tmp/reset-order.json
```

Don't delete `O2` and POST it again. The create-order function is idempotent on `orderId`, so a repeated POST returns the saved response without writing the order.

## Run the integration tests

The tests create a Cognito user, seed an order, publish an `order.updated` event, and check the new status through the API.

```bash
source ../../../.venv/bin/activate
export ORDER_STATUS_STACK_NAME=ws-serverless-patterns-polling
export ORDERS_STACK_NAME=<nested Module 5 orders stack, e.g. ws-serverless-patterns-orders-XXXX>
export CLIENT_ID=<UserPoolClient from the users stack>

pytest tests/integration -v
```

Expected result: **2 passed**. The test setup clears the orders table, so create `O2` again before repeating the manual walkthrough.

## Notes and gotchas

- **"The Orders stack":** use the **nested** Module 5 orders stack. If a standalone Module 3 `ws-serverless-patterns-orders` stack still exists, its API writes to a different table, which this function never updates.
- **Endpoint output name:** the Module 5 orders template outputs `Module3ApiEndpoint`, not `OrdersServiceEndpoint`. `tests/integration/test_order.py` was updated to read `Module3ApiEndpoint`.
- **`KeyError: 'status'` in the poller:** the GET request returned an error instead of an order. Usually the URL is wrong (for example, a missing trailing `/`), the order doesn't exist, or the token has expired. ID tokens last 1 hour.
- **Status never changes:** check the `UpdateOrderStatusFunction` logs in CloudWatch. A `ValidationException` there means the event's `userId` or `orderId` doesn't match any order. A leftover `<your-user-name>` placeholder causes this too.

## Cleanup

```bash
sam delete --stack-name ws-serverless-patterns-polling
```
