"""
Wine API Service Module
Uses local wine database as primary source with SampleAPIs as fallback
"""

import requests
import json
import os
import time
from typing import Dict, List, Any, Optional
from config import config
from utils import logger_util

class WineAPIService:
    """
    Two-tier wine data service:
    1. Primary: Local curated wine database (wineDatabase.json)
    2. Fallback: SampleAPIs for additional wine data
    """
    
    def __init__(self):
        """Initialize the wine API service with local database and SampleAPIs fallback"""
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.wine_database = None
        self.load_local_database()
        
        # SampleAPIs endpoints (fallback)
        self.sample_apis = {
            'reds': 'https://api.sampleapis.com/wines/reds',
            'whites': 'https://api.sampleapis.com/wines/whites',
            'sparkling': 'https://api.sampleapis.com/wines/sparkling',
            'rose': 'https://api.sampleapis.com/wines/rose',
            'dessert': 'https://api.sampleapis.com/wines/dessert',
            'port': 'https://api.sampleapis.com/wines/port'
        }
        
        logger_util.info('Wine API Service initialized with local database + SampleAPIs fallback')
    
    def load_local_database(self) -> None:
        """Load wine database from local JSON file"""
        try:
            db_path = os.path.join(os.path.dirname(__file__), 'wineDatabase.json')
            with open(db_path, 'r', encoding='utf-8') as file:
                self.wine_database = json.load(file)
            
            logger_util.info('Local wine database loaded successfully', {
                'total_wines': len(self.wine_database.get('wines', [])),
                'version': self.wine_database.get('metadata', {}).get('version', 'unknown')
            })
        except Exception as error:
            logger_util.error('Failed to load local wine database', error)
            self.wine_database = {'wines': [], 'metadata': {'version': 'error'}}
    
    def search_wines(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for wines using two-tier approach:
        1. Local database (primary)
        2. SampleAPIs (fallback)
        
        Args:
            search_term: Wine name, type, region, or winery
            filters: Optional filters (type, region, price_range, etc.)
            
        Returns:
            List of matching wines
        """
        try:
            # Tier 1: Search local database first
            local_results = self._search_local_database(search_term, filters)
            
            if local_results:
                logger_util.info(f'Found {len(local_results)} wines in local database')
                return local_results[:config.WINE_API_MAX_RESULTS]
            
            # Tier 2: Fall back to SampleAPIs
            logger_util.info('No local results found, trying SampleAPIs fallback')
            api_results = self._search_sample_apis(search_term, filters)
            
            if api_results:
                logger_util.info(f'Found {len(api_results)} wines from SampleAPIs')
                return api_results[:config.WINE_API_MAX_RESULTS]
            
            logger_util.warning('No wines found in local database or SampleAPIs')
            return []
            
        except Exception as error:
            logger_util.error('Wine search failed', error)
            return []
    
    def _search_local_database(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Search the local wine database"""
        if not self.wine_database or not self.wine_database.get('wines'):
            return []
        
        clean_search_term = search_term.strip().lower()
        results = []
        
        for wine in self.wine_database['wines']:
            # Search in multiple fields
            search_fields = [
                wine.get('name', '').lower(),
                wine.get('winery', '').lower(),
                wine.get('type', '').lower(),
                wine.get('region', '').lower(),
                wine.get('country', '').lower(),
                wine.get('description', '').lower()
            ]
            
            # Check if search term matches any field
            if any(clean_search_term in field for field in search_fields):
                # Apply filters if provided
                if self._wine_matches_filters(wine, filters):
                    # Normalize wine data format
                    normalized_wine = self._normalize_local_wine_data(wine)
                    results.append(normalized_wine)
        
        # Sort by relevance (exact matches first, then by rating)
        results.sort(key=lambda w: (
            -(w.get('name', '').lower() == clean_search_term or w.get('type', '').lower() == clean_search_term),
            -w.get('rating', 0)
        ))
        
        return results
    
    def _search_sample_apis(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """Search SampleAPIs as fallback"""
        all_results = []
        
        # Determine which endpoints to search based on wine type filter
        endpoints_to_search = self.sample_apis.values()
        if filters and filters.get('type'):
            wine_type = filters['type'].lower()
            if wine_type in self.sample_apis:
                endpoints_to_search = [self.sample_apis[wine_type]]
        
        for endpoint in endpoints_to_search:
            try:
                # Check cache first
                cache_key = f"{endpoint}_{search_term}_{str(filters)}"
                if cache_key in self.cache:
                    cache_entry = self.cache[cache_key]
                    if time.time() - cache_entry['timestamp'] < self.cache_timeout:
                        all_results.extend(cache_entry['data'])
                        continue
                
                # Make API request
                response = requests.get(endpoint, timeout=config.WINE_API_TIMEOUT)
                response.raise_for_status()
                wines = response.json()
                
                # Filter results
                filtered_wines = []
                clean_search_term = search_term.strip().lower()
                
                for wine in wines:
                    if isinstance(wine, dict):
                        # Check if wine matches search term
                        wine_name = wine.get('wine', wine.get('name', '')).lower()
                        wine_winery = wine.get('winery', '').lower()
                        
                        if (clean_search_term in wine_name or 
                            clean_search_term in wine_winery or
                            clean_search_term in wine.get('location', '').lower()):
                            
                            # Apply additional filters
                            if self._api_wine_matches_filters(wine, filters):
                                normalized_wine = self._normalize_api_wine_data(wine)
                                filtered_wines.append(normalized_wine)
                
                # Cache results
                self.cache[cache_key] = {
                    'data': filtered_wines,
                    'timestamp': time.time()
                }
                
                all_results.extend(filtered_wines)
                
            except Exception as error:
                logger_util.warning(f'SampleAPI request failed for {endpoint}', error)
                continue
        
        return all_results
    
    def _wine_matches_filters(self, wine: Dict, filters: Optional[Dict]) -> bool:
        """Check if local database wine matches filters"""
        if not filters:
            return True
        
        # Type filter
        if filters.get('type') and filters['type'].lower() not in wine.get('type', '').lower():
            return False
        
        # Region filter
        if filters.get('region') and filters['region'].lower() not in wine.get('region', '').lower():
            return False
        
        # Price range filter
        if filters.get('max_price') and wine.get('price', 0) > filters['max_price']:
            return False
        if filters.get('min_price') and wine.get('price', 999) < filters['min_price']:
            return False
        
        # Rating filter
        if filters.get('min_rating') and wine.get('rating', 0) < filters['min_rating']:
            return False
        
        return True
    
    def _api_wine_matches_filters(self, wine: Dict, filters: Optional[Dict]) -> bool:
        """Check if SampleAPI wine matches filters"""
        if not filters:
            return True
        
        # Basic filtering for API wines (limited data available)
        if filters.get('region'):
            location = wine.get('location', '').lower()
            if filters['region'].lower() not in location:
                return False
        
        return True
    
    def _normalize_local_wine_data(self, wine: Dict) -> Dict:
        """Normalize local database wine data to standard format"""
        return {
            'Name': wine.get('name', 'Unknown Wine'),
            'Winery': wine.get('winery', 'Unknown Winery'),
            'Type': wine.get('type', 'Unknown Type'),
            'Region': wine.get('region', 'Unknown Region'),
            'Country': wine.get('country', 'Unknown Country'),
            'Price': wine.get('price', 0),
            'Rating': wine.get('rating', 0),
            'Description': wine.get('description', 'No description available'),
            'Pairings': wine.get('pairings', []),
            'Occasions': wine.get('occasions', []),
            'Vintage': wine.get('vintage', 'N/A'),
            'AlcoholContent': wine.get('alcoholContent', 'N/A'),
            'Source': 'local_database'
        }
    
    def _normalize_api_wine_data(self, wine: Dict) -> Dict:
        """Normalize SampleAPI wine data to standard format"""
        return {
            'Name': wine.get('wine', wine.get('name', 'Unknown Wine')),
            'Winery': wine.get('winery', 'Unknown Winery'),
            'Type': wine.get('type', 'Unknown Type'),
            'Region': wine.get('location', 'Unknown Region'),
            'Country': wine.get('location', '').split(',')[-1].strip() if wine.get('location') else 'Unknown Country',
            'Price': 0,  # SampleAPIs doesn't provide pricing
            'Rating': wine.get('rating', {}).get('average', 0) if isinstance(wine.get('rating'), dict) else 0,
            'Description': f"A wine from {wine.get('winery', 'Unknown Winery')} in {wine.get('location', 'Unknown Region')}",
            'Pairings': [],  # Not available in SampleAPIs
            'Occasions': [],  # Not available in SampleAPIs
            'Vintage': 'N/A',  # Not available in SampleAPIs
            'AlcoholContent': 'N/A',  # Not available in SampleAPIs
            'Source': 'sample_apis'
        }
