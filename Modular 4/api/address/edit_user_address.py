import os
import boto3

TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    detail = event.get("detail", {})

    user_id = detail.get("userId")
    address_id = detail.get("addressId")

    if not user_id:
        raise ValueError("Missing userId")

    if not address_id:
        raise ValueError("Missing addressId")

    table.delete_item(
        Key={
            "user_id": user_id,
            "address_id": address_id
        }
    )

    return {
        "statusCode": 200,
        "body": "Address deleted successfully"
    }