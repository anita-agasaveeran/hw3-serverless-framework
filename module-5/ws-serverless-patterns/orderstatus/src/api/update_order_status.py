import json
import os
import boto3
from decimal import Decimal


ORDERS_TABLE = os.environ['ORDERS_TABLE_NAME']
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(ORDERS_TABLE)

def lambda_handler(event, context):
    response = None
    try:

        status_code = 200
        
        order_data = event['detail']['data']
        
        status = order_data['status']
        orderId = order_data['orderId']
        userId = order_data['userId']

        key={ 
        'userId': userId,
        'orderId': orderId}

        update_expression = "SET #data.#status = :status"
        expression_attribute_values = {':status': status}
        expression_attribute_names = {'#status': 'status', '#data': 'data'}

        response = ddbTable.update_item(
           Key=key,
           UpdateExpression=update_expression,
           ExpressionAttributeValues=expression_attribute_values,
           ExpressionAttributeNames=expression_attribute_names
        )
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))

    return {
        'statusCode': status_code,
        'body' :  response
    
    }
