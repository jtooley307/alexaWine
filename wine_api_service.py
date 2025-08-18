"""
Wine Data Service Module
Provides local database search with simple filtering and caching.
External APIs removed.
"""

import json
import os
import time
from typing import Dict, List, Any, Optional, Tuple
from config import config
from utils import logger_util

class WineAPIService:
    """
    Wine data service backed by a curated local JSON database (wineDatabase.json).
    Caches results for a short duration.
    """
    
    def __init__(self):
        """Initialize the wine data service with local database backend"""
        self.cache = {}
        self.cache_timeout = 3600  # 1 hour cache for API responses
        self.wine_database = None
        self.load_local_database()
        logger_util.info('Wine API Service initialized with local database backend')
    
    def _get_from_cache(self, key: str) -> Any:
        """
        Get a value from the cache if it exists and hasn't expired
        
        Args:
            key: The cache key to look up
            
        Returns:
            The cached value or None if not found or expired
        """
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached['timestamp'] < self.cache_timeout:
                return cached['value']
        return None
    
    # External API integrations removed
    
    def _search_local_database(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search the local wine database with case-insensitive matching
        
        Args:
            search_term: The search term to look for in wine names, types, etc.
            filters: Optional filters to apply to the search
            
        Returns:
            List of matching wine dictionaries
        """
        if not self.wine_database or not self.wine_database.get('wines'):
            logger_util.warning("No wine database loaded or empty database")
            return []
            
        search_terms = [term.lower().strip() for term in search_term.split()]
        results = []
        
        logger_util.debug(f"Searching through {len(self.wine_database['wines'])} wines")
        
        # Print sample wine names for debugging
        sample_wines = self.wine_database['wines'][:3]
        logger_util.debug("Sample wine names:")
        for i, wine in enumerate(sample_wines, 1):
            logger_util.debug(f"  {i}. {wine.get('name')} ({wine.get('type')})")
        
        for wine in self.wine_database['wines']:
            wine_name = str(wine.get('name', '')).lower()
            wine_type = str(wine.get('type', '')).lower()
            
            # Check if any search term matches the wine name or type
            match = any(term in wine_name or term in wine_type for term in search_terms)
            
            if match:
                logger_util.debug(f"Found matching wine: {wine_name}")
                normalized_wine = self._normalize_local_wine_data(wine)
                if self._wine_matches_filters(normalized_wine, filters):
                    results.append(normalized_wine)
        
        logger_util.debug(f"_search_local_database found {len(results)} results")
        return results
    
    # Old Spoonacular-first search removed; use the version below that prefers local DB then SampleAPIs
    
    def _wine_matches_filters(self, wine: Dict, filters: Optional[Dict] = None) -> bool:
        """
        Check if a wine matches the given filters
        
        Args:
            wine: The wine to check
            filters: Optional filters to apply (e.g., {'type': 'red', 'min_rating': 4})
            
        Returns:
            bool: True if the wine matches all filters, False otherwise
        """
        if not filters:
            return True
            
        wine_type = str(wine.get('type', '')).lower()
        try:
            wine_rating = float(wine.get('rating', 0))
        except (TypeError, ValueError):
            wine_rating = 0
            
        logger_util.debug(f"Checking filters for wine: {wine.get('name')}")
        logger_util.debug(f"Wine type: {wine_type}, Rating: {wine_rating}")
            
        # Check wine type filter
        if 'type' in filters and filters['type']:
            filter_type = str(filters['type']).lower()
            if filter_type not in wine_type:
                logger_util.debug(f"Wine type filter failed: {filter_type} not in {wine_type}")
                return False
            
        # Check minimum rating filter
        if 'min_rating' in filters and filters['min_rating'] is not None:
            try:
                min_rating = float(filters['min_rating'])
                if wine_rating < min_rating:
                    logger_util.debug(f"Rating filter failed: {wine_rating} < {min_rating}")
                    return False
            except (TypeError, ValueError):
                logger_util.warning(f"Invalid min_rating filter value: {filters['min_rating']}")
                
        # Check price range filter
        if 'max_price' in filters and filters['max_price'] is not None:
            try:
                wine_price = float(wine.get('price', float('inf')))
                max_price = float(filters['max_price'])
                if wine_price > max_price:
                    logger_util.debug(f"Price filter failed: {wine_price} > {max_price}")
                    return False
            except (TypeError, ValueError):
                logger_util.warning(f"Invalid max_price filter value: {filters['max_price']}")
                
        # Check region filter
        if 'region' in filters and filters['region']:
            region = str(wine.get('region', '')).lower()
            filter_region = str(filters['region']).lower()
            if filter_region not in region:
                logger_util.debug(f"Region filter failed: {filter_region} not in {region}")
                return False
                
        logger_util.debug(f"Wine matches all filters: {wine.get('name')}")
        return True
    
    def _normalize_local_wine_data(self, wine_data: Dict) -> Dict:
        """
        Normalize wine data from local database to match the expected format
        
        Args:
            wine_data: Raw wine data from local database
            
        Returns:
            Normalized wine data with consistent structure
        """
        if not wine_data:
            return {}
            
        # Extract basic wine information from the database fields
        wine = {
            'name': wine_data.get('name', 'Unknown Wine'),
            'type': wine_data.get('type', 'Unknown Type'),
            'winery': wine_data.get('winery', 'Unknown Winery'),
            'region': wine_data.get('region', 'Unknown Region'),
            'country': wine_data.get('country', 'Unknown Country'),
            'price': wine_data.get('price'),
            'rating': wine_data.get('rating'),
            'description': wine_data.get('description', 'No description available.'),
            'vintage': wine_data.get('vintage'),
            'alcohol_content': wine_data.get('alcohol'),
            'alcohol': wine_data.get('alcohol'),  # Keep both for backward compatibility
            'pairings': wine_data.get('pairings', []),
            'source': 'local_database',
            'raw_data': wine_data
        }
        
        # Add image URL if available (not in the current database but keeping for future use)
        if 'image_url' in wine_data:
            wine['image_url'] = wine_data['image_url']
        
        logger_util.debug(f"Normalized wine data: {json.dumps(wine, indent=2, default=str)}")
        return wine
    
    def _set_in_cache(self, key: str, value: Any) -> None:
        """
        Store a value in the cache
        
        Args:
            key: The cache key
            value: The value to cache
        """
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    # Alias for _set_in_cache for backward compatibility
    def _add_to_cache(self, key: str, value: Any) -> None:
        """
        Alias for _set_in_cache for backward compatibility
        
        Args:
            key: The cache key
            value: The value to cache
        """
        self._set_in_cache(key, value)
    
    def load_local_database(self) -> None:
        """Load wine database from local JSON file"""
        try:
            # Try multiple possible locations for the database file
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'wineDatabase.json'),  # Local development
                os.path.join(os.getcwd(), 'wineDatabase.json'),  # Lambda environment
                '/var/task/wineDatabase.json',  # AWS Lambda default deployment path
                '/tmp/wineDatabase.json'  # Lambda /tmp directory
            ]
            
            self.wine_database = None
            loaded_path = None
            
            for db_path in possible_paths:
                try:
                    logger_util.info(f"Attempting to load wine database from: {db_path}")
                    with open(db_path, 'r', encoding='utf-8') as file:
                        self.wine_database = json.load(file)
                    loaded_path = db_path
                    break
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logger_util.warning(f"Failed to load database from {db_path}: {str(e)}")
                    continue
            
            if not self.wine_database:
                logger_util.error("Failed to load wine database from any known location")
                # Initialize with empty database structure to prevent errors
                self.wine_database = {'wines': []}
                return
            
            logger_util.info('Local wine database loaded successfully', {
                'path': loaded_path,
                'total_wines': len(self.wine_database.get('wines', [])),
                'version': self.wine_database.get('metadata', {}).get('version', 'unknown')
            })
        except Exception as error:
            logger_util.error('Failed to load local wine database', error)
            self.wine_database = {'wines': [], 'metadata': {'version': 'error'}}
    
    def search_wines(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for wines in the local database with optional filters.
        """
        if not search_term:
            return []
        search_term = search_term.lower().strip()
        cache_key = f"{search_term}:{json.dumps(filters or {})}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        try:
            results = self._search_local_database(search_term, filters)
            if results:
                self._add_to_cache(cache_key, results)
            return results
        except Exception as e:
            logger_util.error(f"Error searching wines: {str(e)}")
            return []
            
    # Remove noisy duplicate debug-heavy local search; keep the version above
    # (Function removed)
    
    # SampleAPIs search removed
    
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
    
    # SampleAPI helper removed
    
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
    
    # SampleAPI normalization removed
