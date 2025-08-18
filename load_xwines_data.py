import os
import boto3
import csv
import json
from pathlib import Path
from decimal import Decimal
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = Path("X-Wines/dataset/last")
REGION = os.getenv('AWS_REGION', 'us-west-2')
TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX', 'wine_skill_')
BATCH_SIZE = 25  # DynamoDB batch write limit

# Initialize AWS clients
session = boto3.Session(profile_name='default')
dynamodb = session.resource('dynamodb', region_name=REGION)

def convert_decimal(obj):
    """Convert Decimal to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 != 0 else int(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def load_wines():
    """Load wines from CSV into DynamoDB."""
    table = dynamodb.Table(f"{TABLE_PREFIX}wines")
    csv_file = DATA_DIR / "XWines_Test_100_wines.csv"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        return False
    
    print(f"Loading wines from {csv_file}...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        items = []
        
        for i, row in enumerate(tqdm(reader, desc="Processing wines")):
            try:
                # Map the CSV fields to our database schema
                item = {
                    'wine_id': int(row['WineID']),
                    'name': row['Name'],
                    'winery': row['Winery'],
                    'region': row['Region'],
                    'country': row['Country'],
                    'type': row['Type'],
                    'alcohol': float(row['Alcohol'].replace(',', '.')) if row['Alcohol'] else 0.0,
                    'year': int(row['Year']) if row['Year'] else 0,
                    'rating': float(row['Rating'].replace(',', '.')) if row['Rating'] else 0.0,
                    'num_reviews': int(row['NumberOfRatings']) if row['NumberOfRatings'] else 0,
                    'price': float(row['Price'].replace(',', '.')) if row['Price'] else 0.0
                }
                
                items.append(item)
                
                # Batch write in chunks of BATCH_SIZE
                if len(items) >= BATCH_SIZE:
                    with table.batch_writer() as batch:
                        for item in items:
                            batch.put_item(Item=item)
                    items = []
            
            except Exception as e:
                print(f"Error processing wine {i+1}: {e}")
                continue
        
        # Write any remaining items
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
    
    print(f"Successfully loaded wines into {table.table_name}")
    return True

def load_ratings():
    """Load ratings from CSV into DynamoDB."""
    table = dynamodb.Table(f"{TABLE_PREFIX}ratings")
    csv_file = DATA_DIR / "XWines_Test_1K_ratings.csv"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        return False
    
    print(f"Loading ratings from {csv_file}...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        items = []
        
        for i, row in enumerate(tqdm(reader, desc="Processing ratings")):
            try:
                item = {
                    'user_id': int(row['UserID']),
                    'wine_id': int(row['WineID']),
                    'rating': float(row['Rating'].replace(',', '.')) if row['Rating'] else 0.0
                }
                
                items.append(item)
                
                # Batch write in chunks of BATCH_SIZE
                if len(items) >= BATCH_SIZE:
                    with table.batch_writer() as batch:
                        for item in items:
                            batch.put_item(Item=item)
                    items = []
            
            except Exception as e:
                print(f"Error processing rating {i+1}: {e}")
                continue
        
        # Write any remaining items
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
    
    print(f"Successfully loaded ratings into {table.table_name}")
    return True

def main():
    """Main function to load data into DynamoDB."""
    print("X-Wines Data Loader")
    print("=" * 40)
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"Error: Data directory not found at {DATA_DIR}")
        print("Please download the X-Wines dataset and extract it to the correct location.")
        print("Expected files:")
        print(f"- {DATA_DIR}/wines.csv")
        print(f"- {DATA_DIR}/ratings.csv")
        return
    
    try:
        # Load wines
        if not load_wines():
            return
        
        # Load ratings
        if not load_ratings():
            return
        
        print("\nData loading completed successfully!")
        
    except Exception as e:
        print(f"\nError during data loading: {e}")
        raise

if __name__ == "__main__":
    main()
