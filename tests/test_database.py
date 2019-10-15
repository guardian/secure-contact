import unittest
import boto3

from monitor import *

# !! ~~ Only use this module for local testing ~~ !!


# Use the provided CloudFormation template to create the table in AWS environments.
# If you update this then be sure to also update the CloudFormation definition.
def create_table(dynamodb, table_name: str):
    if table_name not in dynamodb.list_tables().get('TableNames'):
        dynamodb.create_table(
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


def update_ttl(dynamodb, table_name: str):
    ttl_status = dynamodb.describe_time_to_live(TableName=table_name)\
        .get('TimeToLiveDescription')\
        .get('TimeToLiveStatus')

    # AWS returns an error if you try to enable ttl if it is already enabled.
    # We therefore need to check the status before trying to enable it... >.<
    if ttl_status != 'ENABLED':
        dynamodb.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'AttributeName': 'ExpirationTime',
                'Enabled': True
            }
        )


def get_table_status(dynamodb, table_name: str):
    table_status = dynamodb.describe_table(TableName=table_name).get('Table').get('TableStatus')
    print("Table status:", table_status)


# If an item that has the same primary key as the new item already exists in the
# specified table then the new item completely replaces the existing item.
def create_records(dynamodb, table_name: str):
    dynamodb.put_item(TableName=table_name, Item=create_item(1570701600, True))
    dynamodb.put_item(TableName=table_name, Item=create_item(1570705800, True))
    dynamodb.put_item(TableName=table_name, Item=create_item(1570666200, True))
    dynamodb.put_item(TableName=table_name, Item=create_item(1570713000, True))
    dynamodb.put_item(TableName=table_name, Item=create_item(1570716000, True))


# !! ~~ Only use this module for local testing ~~ !!
# Comment out the line below then run the suite to create local DynamoDB tables
@unittest.skip('these tests are for DEV only and require local dynamodb to be running')
class TestDatabase(unittest.TestCase):
    def setUp(self) -> None:
        self.table_name = 'MonitorHistory-DEV'
        self.dynamodb = boto3.resource('dynamodb', region_name='eu-west-1', endpoint_url="http://localhost:8000")

        # !! ~~ DELETING THE TABLE ~~ !!
        # Comment the line below to keep the table after tests are done
        self.dynamodb.delete_table(TableName=self.table_name)

        # create DEV table replicating CFN template, and add some sample records
        create_table(self.dynamodb, self.table_name)
        update_ttl(self.dynamodb, self.table_name)
        create_records(self.dynamodb, self.table_name)

    def tearDown(self) -> None:
        pass

    def test_read_from_database(self):
        result = read_from_database(self.dynamodb, self.dynamodb)

        self.assertEqual(result, create_item(1570701600, True))
        self.assertEqual(result, create_item(1570701600, True))

    def test_write_to_database(self):
        result = write_to_database(self.dynamodb, self.dynamodb, True)

        self.assertEqual(result, create_item(1570701600, True))
        self.assertEqual(result, create_item(1570701600, True))


if __name__ == '__main__':
    unittest.main()
