import os
import gdown
import zipfile
from pathlib import Path
from tqdm import tqdm

# Configuration
DATA_DIR = Path("data/xwines")
ZIP_FILE = DATA_DIR / "xwines_test.zip"
EXTRACT_DIR = DATA_DIR / "xwines"

# Create data directory
DATA_DIR.mkdir(parents=True, exist_ok=True)

def download_dataset():
    """Download the X-Wines test dataset."""
    print("Downloading X-Wines test dataset...")
    
    # Google Drive file ID for the test dataset
    file_id = "1LqguJNV-aKh1PuWMVx5ELA61LPfGfuu_"
    url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        gdown.download(url, str(ZIP_FILE), quiet=False)
        print(f"\nDataset downloaded to: {ZIP_FILE}")
        return True
    except Exception as e:
        print(f"\nError downloading dataset: {e}")
        print("\nPlease download the dataset manually from:")
        print("https://drive.google.com/drive/folders/1LqguJNV-aKh1PuWMVx5ELA61LPfGfuu_")
        print(f"\nAnd save it as: {ZIP_FILE}")
        return False

def extract_dataset():
    """Extract the downloaded dataset."""
    if not ZIP_FILE.exists():
        print(f"Error: {ZIP_FILE} not found.")
        return False
    
    print(f"\nExtracting {ZIP_FILE} to {EXTRACT_DIR}...")
    
    try:
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            # Get the total number of files to extract for the progress bar
            total_files = len(zip_ref.namelist())
            
            # Extract with progress bar
            with tqdm(total=total_files, desc="Extracting files", unit="file") as pbar:
                for file in zip_ref.namelist():
                    zip_ref.extract(file, EXTRACT_DIR)
                    pbar.update(1)
        
        print(f"\nDataset extracted to: {EXTRACT_DIR}")
        return True
    except Exception as e:
        print(f"\nError extracting dataset: {e}")
        return False

def main():
    """Main function to download and extract the dataset."""
    print("X-Wines Test Dataset Downloader")
    print("=" * 50)
    
    # Download the dataset
    if not download_dataset():
        return
    
    # Extract the dataset
    if not extract_dataset():
        return
    
    print("\nSetup complete! You can now run the data loading script:")
    print("python load_xwines_data.py")

if __name__ == "__main__":
    main()
