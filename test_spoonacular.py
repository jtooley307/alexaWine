"""
Test script for Spoonacular API integration
"""
import os
import sys
import json
import logging
import pytest
from wine_service import WineService

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the wine service
wine_service = WineService()

# Always skip this module during pytest runs; it is a script-style manual test
pytestmark = pytest.mark.skip("Skipping script-style Spoonacular test during pytest run")

def test_search(wine_name):
    print(f"\nSearching for: {wine_name}")
    print("-" * 50)
    
    # Print the first few wines from the database for debugging
    try:
        with open('wineDatabase.json', 'r') as f:
            db = json.load(f)
            print("\nSample wine database entries:")
            for i, wine in enumerate(db.get('wines', [])[:3], 1):
                print(f"{i}. {wine.get('name', 'Unknown')} - {wine.get('type', 'Unknown')}")
                print(f"   Data: {json.dumps(wine, indent=2, default=str)}")
    except Exception as e:
        logger.error(f"Error loading wine database: {e}")
    
    # Perform the search
    results = wine_service.search_wines(wine_name)
    
    # Display results
    if not results:
        print("No results found.")
        return
        
    print(f"\nFound {len(results)} results:")
    for i, wine in enumerate(results, 1):
        print(f"\n{'='*80}")
        print(f"{i}. {wine.get('name', 'Unknown Wine')}")
        print(f"{'='*80}")
        print(f"Type: {wine.get('type', 'Unknown Type')}")
        print(f"Winery: {wine.get('winery', 'Unknown Winery')}")
        print(f"Region: {wine.get('region', 'Unknown Region')}, {wine.get('country', 'Unknown Country')}")
        
        if 'vintage' in wine and wine['vintage'] is not None:
            print(f"Vintage: {wine['vintage']}")
            
        if 'price' in wine and wine['price'] is not None:
            print(f"Price: ${wine['price']:.2f}")
            
        if 'rating' in wine and wine['rating'] is not None:
            print(f"Rating: {wine['rating']}/100")
            
        if 'alcohol' in wine and wine['alcohol'] is not None:
            print(f"Alcohol: {wine['alcohol']}%")
            
        if 'description' in wine and wine['description']:
            print(f"\nDescription: {wine['description']}")
            
        if 'pairings' in wine and wine['pairings']:
            print(f"\nFood Pairings: {', '.join(wine['pairings'])}")
            
        if 'occasions' in wine and wine['occasions']:
            print(f"Suggested Occasions: {', '.join(wine['occasions'])}")
            
        print(f"\nSource: {wine.get('source', 'unknown')}")
        
        # Print raw data for debugging (truncated)
        raw_data = wine.get('raw_data', {})
        if raw_data:
            print("\nRaw data (truncated):")
            print(json.dumps(raw_data, indent=2, default=str)[:300] + ("..." if len(json.dumps(raw_data, default=str)) > 300 else ""))
        else:
            print("\nNo raw data available")

if __name__ == "__main__":
    # Default test searches if no arguments provided
    test_searches = ["Pinot Noir", "Chardonnay", "Cabernet"]
    
    if len(sys.argv) > 1:
        test_searches = [" ".join(sys.argv[1:])]
    
    for search_term in test_searches:
        test_search(search_term)
