import boto3

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
                    'AttributeName': 'timestamp',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'outcome',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'timestamp',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'outcome',
                    'AttributeType': 'B'
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
                'AttributeName': 'TTLTimestamp',
                'Enabled': True
            }
        )


if __name__ == '__main__':
    TABLE_NAME = 'MonitorHistory-Dev'
    CLIENT = boto3.client('dynamodb', region_name='eu-west-1', endpoint_url="http://localhost:8000")

    create_table(CLIENT, TABLE_NAME)
    update_ttl(CLIENT, TABLE_NAME)

    table_status = CLIENT.describe_table(TableName=TABLE_NAME)
    print("Table status:", table_status)
