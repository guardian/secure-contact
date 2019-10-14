import boto3
import monitor


# NB: Only use these for local testing
# use the provided CloudFormation template to create the table in AWS environments.
# If you update this then be sure to also update the CloudFormation definition.


# setting the endpoint will create the table in the downloadable version of DynamoDB on your machine
def create_table(db_client, table_name: str):
    if table_name not in db_client.list_tables().get('TableNames'):
        db_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'CheckTime',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'Outcome',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'CheckTime',
                    'AttributeType': 'N'
                },
                {
                    'AttributeName': 'Outcome',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 1,
                'WriteCapacityUnits': 1
            }
        )


def update_ttl(db_client, table_name: str):
    ttl_status = db_client.describe_time_to_live(TableName=table_name)\
        .get('TimeToLiveDescription')\
        .get('TimeToLiveStatus')

    if ttl_status != 'ENABLED':
        db_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'AttributeName': 'ExpirationTime',
                'Enabled': True
            }
        )


# If an item that has the same primary key as the new item already exists in the specified table,
# the new item completely replaces the existing item.
def create_records(db_client, table_name: str):
    db_client.put_item(TableName=table_name, Item=monitor.create_item(1570701600, True))
    db_client.put_item(TableName=table_name, Item=monitor.create_item(1570705800, True))
    db_client.put_item(TableName=table_name, Item=monitor.create_item(1570666200, True))
    db_client.put_item(TableName=table_name, Item=monitor.create_item(1570713000, True))
    db_client.put_item(TableName=table_name, Item=monitor.create_item(1570716000, True))


if __name__ == '__main__':
    TABLE_NAME = 'MonitorHistory-DEV'
    CLIENT = boto3.client('dynamodb', region_name='eu-west-1', endpoint_url="http://localhost:8000")

    # Uncomment this line to delete the table if you want to create a new one
    # CLIENT.delete_table(TableName=TABLE_NAME)

    create_table(CLIENT, TABLE_NAME)
    update_ttl(CLIENT, TABLE_NAME)
    create_records(CLIENT, TABLE_NAME)

    table_status = CLIENT.describe_table(TableName=TABLE_NAME).get('Table').get('TableStatus')
    print("Table status:", table_status)
