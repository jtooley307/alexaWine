import os
import boto3
import json
import gdown
import zipfile
from pathlib import Path
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = Path("data/xwines")
REGION = os.getenv('AWS_REGION', 'us-west-2')
TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX', 'xwines_')

# Create data directory
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Initialize DynamoDB client with default session
session = boto3.Session(profile_name='default')
dynamodb = session.resource('dynamodb', region_name=REGION)

# Table definitions
TABLES = {
    'wines': {
        'KeySchema': [
            {'AttributeName': 'wine_id', 'KeyType': 'HASH'},
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'wine_id', 'AttributeType': 'N'},
            {'AttributeName': 'type', 'AttributeType': 'S'},
            {'AttributeName': 'country', 'AttributeType': 'S'},
            {'AttributeName': 'rating', 'AttributeType': 'N'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'TypeIndex',
                'KeySchema': [
                    {'AttributeName': 'type', 'KeyType': 'HASH'},
                    {'AttributeName': 'rating', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            },
            {
                'IndexName': 'CountryIndex',
                'KeySchema': [
                    {'AttributeName': 'country', 'KeyType': 'HASH'},
                    {'AttributeName': 'rating', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    },
    'ratings': {
        'KeySchema': [
            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
            {'AttributeName': 'wine_id', 'KeyType': 'RANGE'}
        ],
        'AttributeDefinitions': [
            {'AttributeName': 'user_id', 'AttributeType': 'N'},
            {'AttributeName': 'wine_id', 'AttributeType': 'N'},
            {'AttributeName': 'rating', 'AttributeType': 'N'}
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'WineRatingsIndex',
                'KeySchema': [
                    {'AttributeName': 'wine_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'rating', 'KeyType': 'RANGE'}
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    }
}

def download_dataset():
    """Prepare the data directory for X-Wines dataset."""
    print("Preparing X-Wines dataset directory...")
    
    # Create data directory
    data_dir = DATA_DIR / "xwines"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nPlease manually download the X-Wines dataset from:")
    print("https://drive.google.com/drive/folders/1LqguJNV-aKh1PuWMVx5ELA61LPfGfuu_")
    print("\nAfter downloading, extract the files to:")
    print(f"{data_dir}")
    print("\nRequired files:")
    print("- wines.csv")
    print("- users.csv")
    print("- ratings.csv")
    
    return data_dir

def create_tables():
    """Create DynamoDB tables."""
    existing_tables = dynamodb.meta.client.list_tables()['TableNames']
    
    for table_name, table_schema in TABLES.items():
        full_table_name = f"{TABLE_PREFIX}{table_name}"
        
        if full_table_name in existing_tables:
            print(f"Table {full_table_name} already exists. Skipping creation.")
            continue
            
        try:
            print(f"Creating table {full_table_name}...")
            table = dynamodb.create_table(
                TableName=full_table_name,
                KeySchema=table_schema['KeySchema'],
                AttributeDefinitions=table_schema['AttributeDefinitions'],
                GlobalSecondaryIndexes=table_schema.get('GlobalSecondaryIndexes', []),
                ProvisionedThroughput=table_schema['ProvisionedThroughput']
            )
            
            # Wait for the table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=full_table_name)
            print(f"Table {full_table_name} created successfully.")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                print(f"Table {full_table_name} already exists.")
            else:
                print(f"Error creating table {full_table_name}: {e}")
                raise

def load_data(data_dir):
    """Load data from CSV files into DynamoDB tables."""
    import pandas as pd
    
    # Wines table
    wines_file = data_dir / "wines.csv"
    if wines_file.exists():
        print(f"Loading wines from {wines_file}...")
        df_wines = pd.read_csv(wines_file)
        
        # Convert DataFrame to list of dictionaries
        wines = df_wines.to_dict('records')
        
        # Convert numeric fields to appropriate types
        for wine in wines:
            for key in ['wine_id', 'vintage', 'num_reviews']:
                if key in wine and pd.notna(wine[key]):
                    wine[key] = int(wine[key])
            
            for key in ['rating', 'price', 'alcohol']:
                if key in wine and pd.notna(wine[key]):
                    wine[key] = float(wine[key])
        
        # Batch write to DynamoDB
        table = dynamodb.Table(f"{TABLE_PREFIX}wines")
        with table.batch_writer() as batch:
            for wine in wines:
                batch.put_item(Item=wine)
        
        print(f"Loaded {len(wines)} wines into DynamoDB")
    
    # Ratings table
    ratings_file = data_dir / "ratings.csv"
    if ratings_file.exists():
        print(f"Loading ratings from {ratings_file}...")
        df_ratings = pd.read_csv(ratings_file)
        
        # Convert DataFrame to list of dictionaries
        ratings = df_ratings.to_dict('records')
        
        # Convert numeric fields to appropriate types
        for rating in ratings:
            for key in ['user_id', 'wine_id']:
                if key in rating and pd.notna(rating[key]):
                    rating[key] = int(rating[key])
            
            if 'rating' in rating and pd.notna(rating['rating']):
                rating['rating'] = float(rating['rating'])
        
        # Batch write to DynamoDB (in chunks of 25 for batch write limit)
        table = dynamodb.Table(f"{TABLE_PREFIX}ratings")
        for i in range(0, len(ratings), 25):
            with table.batch_writer() as batch:
                for rating in ratings[i:i+25]:
                    batch.put_item(Item=rating)
        
        print(f"Loaded {len(ratings)} ratings into DynamoDB")

def main():
    try:
        # Download the dataset
        data_dir = download_dataset()
        
        # Create tables
        create_tables()
        
        # Load data
        load_data(data_dir)
        
        print("\nDynamoDB setup complete!")
        print(f"Tables created: {[f'{TABLE_PREFIX}{name}' for name in TABLES.keys()]}")
        
    except Exception as e:
        print(f"Error setting up DynamoDB: {e}")
        raise

if __name__ == "__main__":
    main()
