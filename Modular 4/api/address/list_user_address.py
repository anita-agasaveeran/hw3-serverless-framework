import os
import json
import boto3

TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    user_id = (
        event
        .get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
        .get("sub")
    )

    if not user_id:
        return {
            "statusCode": 401,
            "body": json.dumps({
                "message": "Unauthorized"
            })
        }

    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key(
            "user_id"
        ).eq(user_id)
    )

    favorites = response.get("Items", [])

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "favorites": favorites
        })
    }