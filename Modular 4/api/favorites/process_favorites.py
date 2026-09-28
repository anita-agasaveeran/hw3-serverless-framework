import os
import boto3

TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    for record in event.get("Records", []):

        message_attributes = record.get(
            "messageAttributes",
            {}
        )

        command_attribute = message_attributes.get(
            "CommandName",
            {}
        )

        user_attribute = message_attributes.get(
            "UserId",
            {}
        )

        command_name = command_attribute.get(
            "stringValue"
        )

        user_id = user_attribute.get(
            "stringValue"
        )

        restaurant_id = record.get(
            "body"
        )

        if not user_id or not restaurant_id:
            continue

        if command_name == "AddFavorite":
            table.put_item(
                Item={
                    "user_id": user_id,
                    "restaurant_id": restaurant_id
                }
            )

        elif command_name == "DeleteFavorite":
            table.delete_item(
                Key={
                    "user_id": user_id,
                    "restaurant_id": restaurant_id
                }
            )

    return {
        "statusCode": 200
    }