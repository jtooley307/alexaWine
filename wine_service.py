"""
Wine Service Module
Handles wine data retrieval from external APIs with proper error handling
"""

import random
from typing import Dict, List, Any, Optional
from config import config
from utils import logger_util
from wine_api_service import WineAPIService

class WineService:
    """
    Wine Service for searching and managing wine data
    Uses external wine APIs for live data
    """
    
    def __init__(self):
        """Initialize wine service with API integration"""
        self.wine_api = WineAPIService()
        logger_util.info('Wine Service initialized with API integration')
    
    def search_wines(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for wines using external wine APIs
        
        Args:
            search_term: Wine name, type, region, or winery
            filters: Optional filters (type, region, price_range, etc.)
            
        Returns:
            List of matching wines
        """
        try:
            return self.wine_api.search_wines(search_term, filters)
        except Exception as error:
            logger_util.error('Wine search failed in service layer', error)
            return []
    
    def process_wine_data(self, wine: Dict) -> Dict:
        """
        Process wine data to match expected format
        This method is kept for compatibility but the API service now handles processing
        
        Args:
            wine: Raw wine data
            
        Returns:
            Processed wine object (already processed by API service)
        """
        # The wine data is already processed by the API service
        return wine
    
    def get_wine_pairings(self, food_type: str) -> List[Dict]:
        """
        Get wine recommendations based on food pairing
        
        Args:
            food_type: Type of food to pair with
            
        Returns:
            List of recommended wines
        """
        try:
            # Search for wines that pair well with the food type
            return self.wine_api.search_wines(food_type, {'pairing': food_type})
        except Exception as error:
            logger_util.error('Wine pairing search failed', error)
            return []
    
    def get_occasion_wines(self, occasion: str) -> List[Dict]:
        """
        Get wine recommendations for occasions
        
        Args:
            occasion: Type of occasion
            
        Returns:
            List of recommended wines
        """
        try:
            # Search for wines suitable for the occasion
            return self.wine_api.search_wines(occasion, {'occasion': occasion})
        except Exception as error:
            logger_util.error('Occasion wine search failed', error)
            return []
    
    def get_random_wine(self, filters: Optional[Dict] = None) -> Dict:
        """
        Get a random wine recommendation
        
        Args:
            filters: Optional filters
            
        Returns:
            Random wine recommendation
        """
        try:
            # Get a selection of wines and pick one randomly
            wines = self.wine_api.search_wines('wine', filters)
            if wines:
                return random.choice(wines)
            else:
                # Return a default wine if no results
                return {
                    'Name': 'House Wine',
                    'Winery': 'Local Vineyard',
                    'Type': 'Red Wine',
                    'Region': 'Unknown',
                    'Country': 'Unknown',
                    'Price': 25.00,
                    'Rating': 3.5,
                    'Description': 'A pleasant wine with balanced flavors.',
                    'Pairings': ['cheese', 'bread'],
                    'Occasions': ['dinner'],
                    'Vintage': 'N/A',
                    'AlcoholContent': 'N/A'
                }
        except Exception as error:
            logger_util.error('Random wine selection failed', error)
            # Return default wine on error
            return {
                'Name': 'House Wine',
                'Winery': 'Local Vineyard',
                'Type': 'Red Wine',
                'Region': 'Unknown',
                'Country': 'Unknown',
                'Price': 25.00,
                'Rating': 3.5,
                'Description': 'A pleasant wine with balanced flavors.',
                'Pairings': ['cheese', 'bread'],
                'Occasions': ['dinner'],
                'Vintage': 'N/A',
                'AlcoholContent': 'N/A'
            }
