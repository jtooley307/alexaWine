import boto3
from botocore.exceptions import ClientError
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
REGION = os.getenv('AWS_REGION', 'us-west-2')
TABLE_NAME = 'wine_skill_wines'

# Initialize AWS clients
session = boto3.Session(profile_name='default')
dynamodb = session.resource('dynamodb', region_name=REGION)
client = session.client('dynamodb', region_name=REGION)

def wait_for_table_active():
    """Wait for the table to be in ACTIVE state."""
    while True:
        response = client.describe_table(TableName=TABLE_NAME)
        status = response['Table']['TableStatus']
        if status == 'ACTIVE':
            break
        print(f"Waiting for table to be active... Current status: {status}")
        time.sleep(5)

def update_table_indexes():
    """Update the DynamoDB table with the required indexes."""
    try:
        # First, get the current table description
        table = dynamodb.Table(TABLE_NAME)
        
        # Define the attribute definitions
        attribute_definitions = [
            {'AttributeName': 'wine_id', 'AttributeType': 'N'},
            {'AttributeName': 'name', 'AttributeType': 'S'},
            {'AttributeName': 'type', 'AttributeType': 'S'},
            {'AttributeName': 'grape', 'AttributeType': 'S'},
            {'AttributeName': 'body', 'AttributeType': 'S'},
            {'AttributeName': 'country', 'AttributeType': 'S'},
            {'AttributeName': 'region', 'AttributeType': 'S'},
            {'AttributeName': 'winery', 'AttributeType': 'S'}
        ]
        
        # Define the new GSIs
        global_secondary_index_updates = [
            {
                'Create': {
                    'IndexName': 'NameIndex',
                    'KeySchema': [{'AttributeName': 'name', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            },
            {
                'Create': {
                    'IndexName': 'GrapeIndex',
                    'KeySchema': [{'AttributeName': 'grape', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            },
            {
                'Create': {
                    'IndexName': 'BodyIndex',
                    'KeySchema': [{'AttributeName': 'body', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            },
            {
                'Create': {
                    'IndexName': 'RegionIndex',
                    'KeySchema': [{'AttributeName': 'region', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            },
            {
                'Create': {
                    'IndexName': 'WineryIndex',
                    'KeySchema': [{'AttributeName': 'winery', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
                }
            }
        ]
        
        # List of indexes to create (in order of priority)
        indexes_to_create = [
            {
                'IndexName': 'GrapeIndex',
                'KeySchema': [{'AttributeName': 'grape', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'BodyIndex',
                'KeySchema': [{'AttributeName': 'body', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'RegionIndex',
                'KeySchema': [{'AttributeName': 'region', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            },
            {
                'IndexName': 'WineryIndex',
                'KeySchema': [{'AttributeName': 'winery', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
            }
        ]
        
        # Get existing indexes
        existing_indexes = client.describe_table(TableName=TABLE_NAME)['Table'].get('GlobalSecondaryIndexes', [])
        existing_index_names = [idx['IndexName'] for idx in existing_indexes]
        
        # Process one index at a time
        for index in indexes_to_create:
            index_name = index['IndexName']
            
            if index_name in existing_index_names:
                print(f"Index {index_name} already exists. Skipping...")
                continue
                
            print(f"\nAttempting to create index: {index_name}")
            
            try:
                # Prepare the update request
                update_request = {
                    'Create': index
                }
                
                # Update the table with the new index
                client.update_table(
                    TableName=TABLE_NAME,
                    AttributeDefinitions=attribute_definitions,
                    GlobalSecondaryIndexUpdates=[update_request]
                )
                
                # Wait for the update to complete
                print(f"Waiting for {index_name} to be created...")
                wait_for_table_active()
                print(f"✅ Successfully created index: {index_name}")
                
                # Update the list of existing indexes
                existing_index_names.append(index_name)
                
                # Add a delay before the next operation
                print("Waiting 60 seconds before next operation to avoid rate limiting...")
                time.sleep(60)  # Increased delay to 60 seconds to avoid rate limiting
                
            except client.exceptions.LimitExceededException:
                print(f"❌ Hit limit for concurrent index creation. Please wait and run this script again to create remaining indexes.")
                return False
                
            except client.exceptions.ResourceInUseException:
                print(f"ℹ️  Index {index_name} is already being created. Please wait and run this script again to check progress.")
                return False
                
            except Exception as e:
                print(f"❌ Error creating index {index_name}: {str(e)}")
                print("Continuing with next index...")
                time.sleep(10)  # Short delay before continuing
                continue
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'LimitExceededException':
                    print(f"Hit limit for concurrent index creation. Please wait and try again.")
                    print(f"You'll need to run this script again to create the remaining indexes.")
                    return False
                elif 'already exists' in str(e):
                    print(f"Index {index_name} already exists. Skipping...")
                    continue
                else:
                    print(f"Error creating index {index_name}: {e}")
                    print("Continuing with next index...")
                    continue
        
        print("All indexes have been created successfully!")
        return True
        
    except ClientError as e:
        print(f"Error updating table: {e}")
        return False

def main():
    """Main function to update the table indexes."""
    print("Updating DynamoDB Table Indexes")
    print("=" * 50)
    
    try:
        if update_table_indexes():
            print("\nTable indexes have been updated successfully!")
        else:
            print("\nFailed to update some indexes. Please check the logs and try again.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        raise

if __name__ == "__main__":
    main()
