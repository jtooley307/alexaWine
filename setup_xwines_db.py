import os
import sqlite3
import pandas as pd
from pathlib import Path
import gdown
import zipfile

# Configuration
DATA_DIR = Path("data/xwines")
DB_PATH = DATA_DIR / "xwines.db"
ALT_DATASET_DIR = Path("X-Wines/Dataset/last")

# Create data directory
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Google Drive file IDs for the dataset
FILE_IDS = {
    "test": "1LqguJNV-aKh1PuWMVx5ELA61LPfGfuu_",  # Google Drive folder ID for test dataset
}

def download_dataset(version="test"):
    """Download the X-Wines dataset from Google Drive."""
    # Local fallback: if repo dataset exists, use it
    if ALT_DATASET_DIR.exists():
        print(f"Using local X-Wines dataset at: {ALT_DATASET_DIR}")
        return ALT_DATASET_DIR

    print(f"Downloading X-Wines {version} dataset...")
    
    # Output paths
    zip_path = DATA_DIR / f"xwines_{version}.zip"
    
    # Download the zip file
    url = f"https://drive.google.com/uc?id={FILE_IDS[version]}"
    gdown.download(url, str(zip_path), quiet=False)
    
    # Extract the files
    print("Extracting files...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATA_DIR / version)
    
    print(f"Dataset downloaded and extracted to: {DATA_DIR/version}")
    return DATA_DIR / version

def setup_database(data_dir):
    """Set up SQLite database and load the CSV files."""
    print("Setting up SQLite database...")
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    print("Creating database tables...")
    
    # Wines table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS wines (
        wine_id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT,
        country TEXT,
        region TEXT,
        winery TEXT,
        rating REAL,
        num_reviews INTEGER,
        price REAL,
        vintage INTEGER,
        alcohol REAL,
        body TEXT,
        acidity TEXT,
        sweetness TEXT,
        tannin TEXT,
        food_pairing TEXT,
        description TEXT
    )
    ''')
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
    ''')
    
    # Ratings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ratings (
        user_id INTEGER,
        wine_id INTEGER,
        rating REAL,
        date TEXT,
        PRIMARY KEY (user_id, wine_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (wine_id) REFERENCES wines(wine_id)
    )
    ''')
    
    # Load data from CSV files
    print("Loading data into database...")
    
    # Load wines
    wines_file = data_dir / "wines.csv"
    if wines_file.exists():
        df_wines = pd.read_csv(wines_file)
        df_wines.to_sql('wines', conn, if_exists='replace', index=False)
        print(f"Loaded {len(df_wines)} wines")
    else:
        # Transform from repository CSV schema if present
        repo_csv = ALT_DATASET_DIR / "XWines_Test_100_wines.csv"
        if repo_csv.exists():
            df_src = pd.read_csv(repo_csv)
            # Map and normalize columns to our wines schema
            def to_str(x):
                return None if pd.isna(x) else str(x)

            df_wines = pd.DataFrame({
                'wine_id': df_src.get('WineID'),
                'name': df_src.get('WineName').apply(to_str),
                'type': df_src.get('Type').apply(to_str),
                'country': df_src.get('Country').apply(to_str),
                'region': df_src.get('RegionName').apply(to_str),
                'winery': df_src.get('WineryName').apply(to_str),
                'rating': None,
                'num_reviews': None,
                'price': None,
                'vintage': None,
                'alcohol': df_src.get('ABV'),
                'body': df_src.get('Body').apply(to_str),
                'acidity': df_src.get('Acidity').apply(to_str),
                'sweetness': None,
                'tannin': None,
                'food_pairing': df_src.get('Harmonize').apply(to_str),
                'description': (
                    df_src.get('Elaborate').astype(str).fillna('') + ' | Grapes: ' +
                    df_src.get('Grapes').astype(str).fillna('') + ' | Vintages: ' +
                    df_src.get('Vintages').astype(str).fillna('')
                ).apply(lambda s: s.strip(' |'))
            })
            # Ensure primary key uniqueness and correct dtypes
            df_wines = df_wines.dropna(subset=['wine_id']).drop_duplicates(subset=['wine_id'])
            df_wines['wine_id'] = df_wines['wine_id'].astype(int)
            df_wines.to_sql('wines', conn, if_exists='replace', index=False)
            print(f"Loaded {len(df_wines)} wines from repo CSV {repo_csv}")
    
    # Load users (if available)
    users_file = data_dir / "users.csv"
    if users_file.exists():
        df_users = pd.read_csv(users_file)
        df_users.to_sql('users', conn, if_exists='replace', index=False)
        print(f"Loaded {len(df_users)} users")
    
    # Load ratings
    ratings_file = data_dir / "ratings.csv"
    if ratings_file.exists():
        df_ratings = pd.read_csv(ratings_file)
        df_ratings.to_sql('ratings', conn, if_exists='replace', index=False)
        print(f"Loaded {len(df_ratings)} ratings")
    
    # Create indexes for better query performance
    print("Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wines_type ON wines(type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_wines_country ON wines(country)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_wine_id ON ratings(wine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON ratings(user_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database setup complete: {DB_PATH}")

def main():
    # Download the test dataset
    data_dir = download_dataset("test")
    
    # Set up the database
    setup_database(data_dir)
    
    print("\nX-Wines database setup complete!")
    print(f"Database location: {DB_PATH.absolute()}")

if __name__ == "__main__":
    main()
