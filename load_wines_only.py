import os
import boto3
import csv
from pathlib import Path
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

def load_wines():
    """Load wines from CSV into DynamoDB."""
    table_name = f"{TABLE_PREFIX}wines"
    table = dynamodb.Table(table_name)
    csv_file = DATA_DIR / "XWines_Test_100_wines.csv"
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        return False
    
    print(f"Loading wines from {csv_file}...")
    
    # First, let's check the file content
    with open(csv_file, 'r', encoding='utf-8') as f:
        # Read the first few lines to understand the format
        sample = [next(f) for _ in range(5)]
        print("\nSample data:")
        print(''.join(sample))
        
        # Go back to the start of the file
        f.seek(0)
        
        # Try to read the CSV with different delimiters
        try:
            # Try with semicolon first
            f.seek(0)
            reader = csv.DictReader(f, delimiter=';')
            first_row = next(reader)
            print("\nDetected columns (semicolon-delimited):")
            print(first_row.keys())
            
            # Process all rows
            f.seek(0)
            next(f)  # Skip header
            reader = csv.reader(f, delimiter=';')
            
            items = []
            for i, row in enumerate(tqdm(reader, desc="Processing wines")):
                try:
                    if len(row) < 10:  # Make sure we have enough columns
                        print(f"Skipping malformed row {i+1}: {row}")
                        continue
                        
                    # Map the CSV fields to our database schema
                    item = {
                        'wine_id': int(row[0]),  # WineID
                        'name': row[1],          # Name
                        'winery': row[2],        # Winery
                        'region': row[3],        # Region
                        'country': row[4],       # Country
                        'type': row[5],          # Type
                        'alcohol': float(row[6].replace(',', '.')) if row[6] else 0.0,  # Alcohol
                        'year': int(row[7]) if row[7] else 0,  # Year
                        'rating': float(row[8].replace(',', '.')) if row[8] else 0.0,  # Rating
                        'num_reviews': int(row[9]) if row[9] else 0,  # NumberOfRatings
                        'price': float(row[10].replace(',', '.')) if len(row) > 10 and row[10] else 0.0  # Price
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
                    print(f"Row data: {row}")
                    continue
            
            # Write any remaining items
            if items:
                with table.batch_writer() as batch:
                    for item in items:
                        batch.put_item(Item=item)
            
            print(f"\nSuccessfully loaded wines into {table_name}")
            return True
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return False

def main():
    """Main function to load wines into DynamoDB."""
    print("X-Wines Data Loader - Wines Only")
    print("=" * 40)
    
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
