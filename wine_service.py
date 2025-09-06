"""
Wine Service Module
Handles wine data retrieval from OpenSearch and local database.
"""

import os
import json
from typing import Dict, List, Any, Optional
from config import config
from utils import logger_util
from wine_api_service import WineAPIService
try:
    # Optional import; only used when USE_DYNAMODB is enabled
    from wine_dynamodb_service import WineDynamoDBService
except Exception:
    WineDynamoDBService = None  # type: ignore
try:
    # Optional import; only used when USE_LOCAL_VECTOR_SEARCH is enabled
    import local_vector_search
except Exception:
    local_vector_search = None  # type: ignore
try:
    # Optional import; used when USE_OPENSEARCH is enabled
    import opensearch_search
except Exception:
    opensearch_search = None  # type: ignore

class WineService:
    """
    Wine Service for searching and managing wine data
    Uses OpenSearch (if enabled) and local database via WineAPIService
    """
    
    def __init__(self, data_dir: str = None):
        """Initialize wine service with API integration and optional DynamoDB backend"""
        self.wine_api = WineAPIService()
        self.dynamo = None
        self.wine_database: Dict[str, Any] = {'wines': []}
        # Load local wine database on init for tests and fallback behavior
        self.load_wine_database(data_dir)
        if getattr(config, 'USE_DYNAMODB', False) and WineDynamoDBService is not None:
            try:
                self.dynamo = WineDynamoDBService()
                logger_util.info('Wine Service initialized with DynamoDB backend enabled')
            except Exception as e:
                logger_util.error('Failed to initialize DynamoDB backend; falling back to API/local DB', e)
        else:
            logger_util.info('Wine Service initialized (OpenSearch/local DB)')

    def load_wine_database(self, data_dir: Optional[str] = None) -> None:
        """Load local wine database JSON into memory for fallback/tests."""
        try:
            base_dir = data_dir or os.path.dirname(__file__)
            db_path = os.path.join(base_dir, 'wine_data.json')
            with open(db_path, 'r', encoding='utf-8') as f:
                self.wine_database = json.load(f)
        except Exception:
            # Default to empty database on failure
            self.wine_database = {'wines': []}

    def search_wines(self, search_term: str, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search for wines using DynamoDB (optional), local vector search (optional),
        OpenSearch (if enabled), and finally local database via WineAPIService.
        
        Args:
            search_term: Wine name, type, region, or winery to search for
            filters: Optional filters to apply to the search (e.g., type, max_price, min_rating)
            
        Returns:
            List of matching wines with standardized fields
        """
        if not search_term or not search_term.strip():
            raise ValueError("Invalid search term provided")
            
        try:
            # If DynamoDB is enabled, try it first
            if self.dynamo is not None:
                limit = getattr(config, 'WINE_API_MAX_RESULTS', 5)
                dyn_filters = filters or {}
                dyn_results = self.dynamo.search_wines(
                    search_term=search_term,
                    wine_type=dyn_filters.get('type'),
                    country=dyn_filters.get('country'),
                    min_rating=dyn_filters.get('min_rating'),
                    max_price=dyn_filters.get('max_price'),
                    limit=limit
                )
                results = [self.process_wine_data(w) for w in dyn_results]
                if results:
                    logger_util.info(f"Found {len(results)} wines in DynamoDB for: {search_term}")
                    return results

            # Optionally, try local vector search next
            if getattr(config, 'USE_LOCAL_VECTOR_SEARCH', False) and local_vector_search is not None:
                k = getattr(config, 'WINE_API_MAX_RESULTS', 5)
                lv_results = local_vector_search.search_wines(search_term, k=k)
                if lv_results:
                    logger_util.info(f"Found {len(lv_results)} wines via local vector search for: {search_term}")
                    return [self.process_wine_data(w) for w in lv_results]

            # Optionally, try OpenSearch (vector/hybrid/BM25)
            if getattr(config, 'USE_OPENSEARCH', False) and opensearch_search is not None:
                try:
                    size = getattr(config, 'WINE_API_MAX_RESULTS', 5)
                    results: List[Dict[str, Any]] = []
                    if getattr(config, 'USE_VECTOR_SEARCH', False):
                        if getattr(config, 'USE_HYBRID_SEARCH', True):
                            results = opensearch_search.search_hybrid(search_term, size=size, k=size)
                        else:
                            results = opensearch_search.search_vector(search_term, k=size)
                    else:
                        results = opensearch_search.search_text(search_term, size=size)
                    if results:
                        logger_util.info(f"Found {len(results)} wines via OpenSearch for: {search_term}")
                        return [self.process_wine_data(w) for w in results]
                except Exception as oe:
                    logger_util.error(f"OpenSearch query failed: {oe}")

            # Delegate search to WineAPIService which handles local database search
            api_results = self.wine_api.search_wines(search_term, filters)
            if not api_results:
                # Fallback: search local database if available
                local_results = self._search_local_database(search_term, filters)
                if local_results:
                    logger_util.info(f"Found {len(local_results)} wines in local DB for: {search_term}")
                    return [self.process_wine_data(w) for w in local_results]
                logger_util.info(f"No wines found for search term: {search_term}")
                return []

            logger_util.info(f"Found {len(api_results)} wines for search term: {search_term}")
            return [self.process_wine_data(w) for w in api_results]

        except Exception as e:
            logger_util.error(f"Error searching for wines: {str(e)}")
            return []

    def process_wine_data(self, wine: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize wine dict to lowercase keys expected by handlers."""
        # Support both lowercase and TitleCase keys from different sources
        name = wine.get('name') or wine.get('Name') or 'Unknown Wine'
        wtype = wine.get('type') or wine.get('Type') or 'Unknown Type'
        winery = wine.get('winery') or wine.get('Winery') or 'Unknown Winery'
        region = wine.get('region') or wine.get('Region') or 'Unknown Region'
        country = wine.get('country') or wine.get('Country') or 'Unknown Country'
        price = wine.get('price') if 'price' in wine else wine.get('Price')
        rating = wine.get('rating') if 'rating' in wine else wine.get('Rating')
        description = wine.get('description') or wine.get('Description') or 'No description available.'
        # Winemaker tasting notes normalization
        tasting_notes = (
            wine.get('tasting_notes')
            or wine.get('tastingNotes')
            or (wine.get('raw_data', {}) or {}).get('tasting_notes')
            or (wine.get('raw_data', {}) or {}).get('tastingNotes')
        )
        pairings = wine.get('pairings') or wine.get('Pairings') or []
        source = wine.get('source', 'unknown')

        formatted_wine: Dict[str, Any] = {
            'name': name,
            'type': wtype,
            'winery': winery,
            'region': region,
            'country': country,
            'price': price,
            'rating': rating,
            'description': description,
            'tasting_notes': tasting_notes or description,
            'pairings': pairings,
            'source': source
        }

        # Add any additional fields if present
        # Prefer raw_data subkeys but also check top-level
        raw_data = wine.get('raw_data', {}) if isinstance(wine.get('raw_data', {}), dict) else {}
        vintage = raw_data.get('vintage') or wine.get('vintage')
        alcohol_content = raw_data.get('alcohol_content') or wine.get('alcohol_content') or wine.get('alcohol')
        image_url = raw_data.get('imageUrl') or wine.get('image_url') or wine.get('imageUrl')
        if vintage is not None:
            formatted_wine['vintage'] = vintage
        if alcohol_content is not None:
            formatted_wine['alcohol_content'] = alcohol_content
        if image_url is not None:
            formatted_wine['image_url'] = image_url

        # Preserve relevance score if upstream search attached it (e.g., OpenSearch)
        rel = wine.get('_relevance') or (raw_data.get('_relevance') if isinstance(raw_data, dict) else None)
        if rel is not None:
            try:
                formatted_wine['_relevance'] = float(rel)
            except Exception:
                pass

        return formatted_wine

    def _search_local_database(self, search_term: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Simple local search over self.wine_database['wines'] with basic filters."""
        try:
            wines = self.wine_database.get('wines', []) if isinstance(self.wine_database, dict) else []
        except Exception:
            wines = []
        if not wines:
            return []
        term = search_term.lower()
        results: List[Dict[str, Any]] = []
        for w in wines:
            fields = [
                str(w.get('name', '')).lower(),
                str(w.get('winery', '')).lower(),
                str(w.get('type', '')).lower(),
                str(w.get('region', '')).lower(),
            ]
            if any(term in f for f in fields):
                # Apply optional filters
                if filters:
                    max_price = filters.get('max_price')
                    min_rating = filters.get('min_rating')
                    w_price = w.get('price') or w.get('Price')
                    w_rating = w.get('rating') or w.get('Rating')
                    if max_price is not None and w_price is not None and float(w_price) > float(max_price):
                        continue
                    if min_rating is not None and w_rating is not None and float(w_rating) < float(min_rating):
                        continue
                results.append(w)
                if len(results) >= getattr(config, 'WINE_API_MAX_RESULTS', 5):
                    break
        return results
