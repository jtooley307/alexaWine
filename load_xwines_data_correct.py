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

def parse_wine_row(row):
    """Parse a row from the X-Wines dataset into a DynamoDB item."""
    try:
        # Convert numeric values to Decimal for DynamoDB
        from decimal import Decimal
        
        def to_decimal(value, default=Decimal('0.0')):
            try:
                if not value:
                    return default
                return Decimal(str(float(value)))
            except (ValueError, TypeError):
                return default
                
        def to_int(value, default=0):
            try:
                if not value or not str(value).strip():
                    return default
                return int(Decimal(str(value)))
            except (ValueError, TypeError):
                return default
        
        # Parse the row
        item = {
            'wine_id': to_int(row[0]),  # WineID
            'name': row[1],            # Name
            'type': row[2],            # Type (Red, White, etc.)
            'grape': row[3],           # Grape/Varietal
            'grapes': json.loads(row[4].replace("'", '"')),  # List of grapes
            'pairings': json.loads(row[5].replace("'", '"')),  # Food pairings
            'alcohol': to_decimal(row[6]),  # Alcohol percentage
            'body': row[7],            # Body type
            'sweetness': row[8],       # Sweetness level
            'country_code': row[9],    # Country code
            'country': row[10],        # Country name
            'vintage': to_int(row[11]),  # Vintage year
            'region': row[12],         # Region
            'winery_id': row[13],      # Winery ID
            'winery': row[14],         # Winery name
            'website': row[15] if len(row) > 15 else '',  # Website
        }
        
        # Handle available vintages if present
        if len(row) > 16 and row[16].strip():
            try:
                vintages = json.loads(row[16].replace("'", '"'))
                # Convert any numeric years to strings to avoid float issues
                item['available_vintages'] = [str(v) if isinstance(v, (int, float)) else v for v in vintages]
            except (json.JSONDecodeError, TypeError):
                item['available_vintages'] = []
        else:
            item['available_vintages'] = []
            
        return item
    except Exception as e:
        print(f"Error parsing row: {row}")
        print(f"Error details: {e}")
        return None

def load_wines():
    """Load wines from CSV into DynamoDB."""
    table_name = f"{TABLE_PREFIX}wines"
    table = dynamodb.Table(table_name)
    csv_file = DATA_DIR / "XWines_Test_100_wines.csv"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        return False
    
    print(f"Loading wines from {csv_file}...")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')
        items = []
        
        # Skip header
        next(reader, None)
        
        for i, row in enumerate(tqdm(reader, desc="Processing wines")):
            try:
                if not row or len(row) < 10:
                    print(f"Skipping malformed row {i+1}")
                    continue
                    
                wine_item = parse_wine_row(row)
                if wine_item:
                    items.append(wine_item)
                
                # Batch write in chunks of BATCH_SIZE
                if len(items) >= BATCH_SIZE:
                    with table.batch_writer() as batch:
                        for item in items:
                            batch.put_item(Item=item)
                    items = []
            
            except Exception as e:
                print(f"Error processing wine {i+1}: {e}")
                print(f"Row data: {row}")
                continue
        
        # Write any remaining items
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
    
    print(f"\nSuccessfully loaded wines into {table_name}")
    return True

def main():
    """Main function to load data into DynamoDB."""
    print("X-Wines Data Loader - Corrected Format")
    print("=" * 50)
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"Error: Data directory not found at {DATA_DIR}")
        print("Please ensure the X-Wines dataset is in the correct location.")
        return
    
    try:
        # Load wines
        if load_wines():
            print("\nData loading completed successfully!")
            
    except Exception as e:
        print(f"\nError during data loading: {e}")
        raise

if __name__ == "__main__":
    main()
