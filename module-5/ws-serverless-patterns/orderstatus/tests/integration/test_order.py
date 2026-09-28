import json
import requests
import boto3
import datetime
import time

def test_order_status(global_config,capsys):
    

    response = get_order_status(
        global_config["Module3ApiEndpoint"],
        global_config["regularUserIdToken"],
        global_config['order']['data']['orderId'],
    )

    assert response.status_code == 200
    assert json.loads(response.content) == global_config['order']['data'] 


def test_order_update_process(global_config,capsys):
    order = global_config['order'] 
    order['data']['status'] = 'IN-PROCESS'
    eb_client = boto3.client('events')
    response = eb_client.put_events(
        Entries=[
            {
                'Time': datetime.datetime.now(),
                'Source': 'restaurant',
                'DetailType': 'order.updated',
                'EventBusName': global_config['RestaurantBusName'],
                'Detail': json.dumps(order),
            }
        ]
    )
    assert response['FailedEntryCount'] == 0
    time.sleep(3)  # Simulate an SLA for receiving a response
    # make another call to APIGW to get the status to see if the event now matches.
    response = get_order_status(
        global_config["Module3ApiEndpoint"],
        global_config["regularUserIdToken"],
        order['data']['orderId'],
    )

    assert json.loads(response.content) == json.loads(json.dumps((order['data'])))

# helper function to execute order status api
def get_order_status(endpoint, token, orderId):
    response = requests.get(
        endpoint + f'/orders/{orderId}', headers={"Authorization": token}
    )
    return response