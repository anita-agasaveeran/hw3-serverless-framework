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

    update_expression = """
        SET line1 = :line1,
            line2 = :line2,
            city = :city,
            stateProvince = :stateProvince,
            postal = :postal
    """

    expression_values = {
        ":line1": detail.get("line1"),
        ":line2": detail.get("line2"),
        ":city": detail.get("city"),
        ":stateProvince": detail.get("stateProvince"),
        ":postal": detail.get("postal")
    }

    table.update_item(
        Key={
            "user_id": user_id,
            "address_id": address_id
        },
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values
    )

    return {
        "statusCode": 200,
        "body": "Address updated successfully"
    }