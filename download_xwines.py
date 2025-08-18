import os
import zipfile
import requests
from pathlib import Path

def download_file(url, local_path):
    """Download a file from a URL to a local path."""
    Path(os.path.dirname(local_path)).mkdir(parents=True, exist_ok=True)
    
    # Stream the download to handle large files
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def extract_zip(zip_path, extract_to):
    """Extract a zip file to the specified directory."""
    Path(extract_to).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

if __name__ == "__main__":
    # Base URL for the X-Wines dataset
    base_url = "https://github.com/rogerioxavier/X-Wines/raw/main/Dataset/"
    
    # Test dataset files
    test_files = [
        "XWines_Test_100Wines_1k_Ratings.zip",
        "XWines_Test_100Wines_1k_Ratings_README.txt"
    ]
    
    # Create data directory
    data_dir = Path("data/xwines")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Download and extract the test dataset
    for file in test_files:
        file_url = base_url + file
        local_path = data_dir / file
        
        print(f"Downloading {file}...")
        download_file(file_url, local_path)
        
        if file.endswith('.zip'):
            print(f"Extracting {file}...")
            extract_to = data_dir / "extracted"
            extract_zip(local_path, extract_to)
            print(f"Extracted to: {extract_to}")
    
    print("\nDownload and extraction complete!")
    print("Files downloaded to:", data_dir.absolute())
