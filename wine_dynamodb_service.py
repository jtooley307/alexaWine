import os
import boto3
from typing import Dict, List, Optional, Union
from decimal import Decimal
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
REGION = os.getenv('AWS_REGION', 'us-west-2')
TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX', 'wine_skill_')
ENDPOINT_URL = os.getenv('DYNAMODB_ENDPOINT_URL')

# Initialize DynamoDB client (support local endpoint for tests)
if ENDPOINT_URL:
    dynamodb = boto3.resource('dynamodb', region_name=REGION, endpoint_url=ENDPOINT_URL)
else:
    dynamodb = boto3.resource('dynamodb', region_name=REGION)

class WineDynamoDBService:
    """Service for interacting with the Wine DynamoDB tables."""
    
    def __init__(self):
        self.wines_table = dynamodb.Table(f"{TABLE_PREFIX}wines")
        self.ratings_table = dynamodb.Table(f"{TABLE_PREFIX}ratings")
        
    def get_wine_by_id(self, wine_id: int) -> Optional[Dict]:
        """Get a wine by its ID."""
        try:
            response = self.wines_table.get_item(Key={'wine_id': wine_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Error getting wine {wine_id}: {e}")
            return None
    
    def search_wines(
        self,
        search_term: str = None,
        wine_type: str = None,
        country: str = None,
        min_rating: float = None,
        max_price: float = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search for wines based on various criteria."""
        try:
            # Start with a scan operation
            filter_expressions = []
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            # Add filters based on provided criteria
            if search_term:
                filter_expressions.append("contains(#name, :search_term)")
                expression_attribute_names["#name"] = "name"
                # Do not lowercase; match stored casing in table (e.g., "Origem Merlot")
                expression_attribute_values[":search_term"] = search_term
            
            if wine_type:
                filter_expressions.append("#type = :wine_type")
                expression_attribute_names["#type"] = "type"
                expression_attribute_values[":wine_type"] = wine_type
            
            if country:
                filter_expressions.append("contains(#country, :country)")
                expression_attribute_names["#country"] = "country"
                expression_attribute_values[":country"] = country
            
            if min_rating is not None:
                filter_expressions.append("#rating >= :min_rating")
                expression_attribute_names["#rating"] = "rating"
                expression_attribute_values[":min_rating"] = Decimal(str(min_rating))
            
            if max_price is not None:
                filter_expressions.append("#price <= :max_price")
                expression_attribute_names["#price"] = "price"
                expression_attribute_values[":max_price"] = Decimal(str(max_price))
            
            # Decide strategy: prefer Query on GSIs when possible
            # - Exact name match -> Query NameIndex
            # - wine_type -> Query TypeIndex (with optional rating range)
            # - country -> Query CountryIndex (with optional rating range)
            # Otherwise -> Scan with contains() filters (paginated)

            # Helper to convert items
            def _convert(items: List[Dict]) -> List[Dict]:
                out: List[Dict] = []
                for item in items:
                    wine: Dict[str, Union[int, float, str]] = {}
                    for k, v in item.items():
                        if isinstance(v, Decimal):
                            wine[k] = int(v) if v % 1 == 0 else float(v)
                        else:
                            wine[k] = v
                    out.append(wine)
                return out

            # 1) Try exact name query if search_term provided
            if search_term:
                try:
                    response = self.wines_table.query(
                        IndexName='NameIndex',
                        KeyConditionExpression='#name = :name',
                        ExpressionAttributeNames={'#name': 'name'},
                        ExpressionAttributeValues={':name': search_term},
                        Limit=limit
                    )
                    items = _convert(response.get('Items', []))
                    if items:
                        # Apply additional filters client-side if needed (price, rating, country/type contains)
                        filtered: List[Dict] = []
                        for w in items:
                            if min_rating is not None and float(w.get('rating', 0)) < float(min_rating):
                                continue
                            if max_price is not None and w.get('price') is not None and float(w.get('price')) > float(max_price):
                                continue
                            if wine_type and wine_type not in str(w.get('type', '')):
                                continue
                            if country and country not in str(w.get('country', '')):
                                continue
                            filtered.append(w)
                            if len(filtered) >= limit:
                                break
                        if filtered:
                            filtered.sort(key=lambda x: x.get('rating', 0), reverse=True)
                            return filtered[:limit]
                except ClientError as e:
                    logger.error(f"NameIndex query failed: {e}")

            # 2) TypeIndex query when wine_type provided
            if wine_type:
                try:
                    key_expr = '#type = :t'
                    expr_names = {'#type': 'type'}
                    expr_vals: Dict[str, Union[str, Decimal]] = {':t': wine_type}
                    if min_rating is not None:
                        key_expr = key_expr + ' AND #rating >= :minr'
                        expr_names['#rating'] = 'rating'
                        expr_vals[':minr'] = Decimal(str(min_rating))
                    response = self.wines_table.query(
                        IndexName='TypeIndex',
                        KeyConditionExpression=key_expr,
                        ExpressionAttributeNames=expr_names,
                        ExpressionAttributeValues=expr_vals,
                        ScanIndexForward=False,  # high rating first
                        Limit=limit
                    )
                    items = _convert(response.get('Items', []))
                    if items:
                        # Optional filters
                        filtered: List[Dict] = []
                        for w in items:
                            if max_price is not None and w.get('price') is not None and float(w.get('price')) > float(max_price):
                                continue
                            if country and country not in str(w.get('country', '')):
                                continue
                            if search_term and search_term not in str(w.get('name', '')):
                                continue
                            filtered.append(w)
                            if len(filtered) >= limit:
                                break
                        if filtered:
                            filtered.sort(key=lambda x: x.get('rating', 0), reverse=True)
                            return filtered[:limit]
                except ClientError as e:
                    logger.error(f"TypeIndex query failed: {e}")

            # 3) CountryIndex query when country provided
            if country:
                try:
                    key_expr = '#country = :c'
                    expr_names = {'#country': 'country'}
                    expr_vals: Dict[str, Union[str, Decimal]] = {':c': country}
                    if min_rating is not None:
                        key_expr = key_expr + ' AND #rating >= :minr'
                        expr_names['#rating'] = 'rating'
                        expr_vals[':minr'] = Decimal(str(min_rating))
                    response = self.wines_table.query(
                        IndexName='CountryIndex',
                        KeyConditionExpression=key_expr,
                        ExpressionAttributeNames=expr_names,
                        ExpressionAttributeValues=expr_vals,
                        ScanIndexForward=False,
                        Limit=limit
                    )
                    items = _convert(response.get('Items', []))
                    if items:
                        filtered: List[Dict] = []
                        for w in items:
                            if max_price is not None and w.get('price') is not None and float(w.get('price')) > float(max_price):
                                continue
                            if wine_type and wine_type not in str(w.get('type', '')):
                                continue
                            if search_term and search_term not in str(w.get('name', '')):
                                continue
                            filtered.append(w)
                            if len(filtered) >= limit:
                                break
                        if filtered:
                            filtered.sort(key=lambda x: x.get('rating', 0), reverse=True)
                            return filtered[:limit]
                except ClientError as e:
                    logger.error(f"CountryIndex query failed: {e}")

            # 4) Fallback: Scan with contains filters (paginated)
            scan_kwargs: Dict[str, any] = {}
            
            if filter_expressions:
                # When filtering, do NOT set Limit directly because it limits evaluated (pre-filter) items.
                # Instead, paginate until we collect up to `limit` matched items.
                scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
                scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
                if expression_attribute_names:
                    scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names

                wines: List[Dict] = []
                last_evaluated_key = None
                while True:
                    if last_evaluated_key:
                        scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
                    response = self.wines_table.scan(**scan_kwargs)
                    for item in response.get('Items', []):
                        wine: Dict[str, Union[int, float, str]] = {}
                        for k, v in item.items():
                            if isinstance(v, Decimal):
                                wine[k] = int(v) if v % 1 == 0 else float(v)
                            else:
                                wine[k] = v
                        wines.append(wine)
                        if len(wines) >= limit:
                            break
                    if len(wines) >= limit:
                        break
                    last_evaluated_key = response.get('LastEvaluatedKey')
                    if not last_evaluated_key:
                        break
            else:
                # No filter: it's safe to use Limit directly
                scan_kwargs['Limit'] = limit
                response = self.wines_table.scan(**scan_kwargs)
                wines = []
                for item in response.get('Items', []):
                    wine: Dict[str, Union[int, float, str]] = {}
                    for k, v in item.items():
                        if isinstance(v, Decimal):
                            wine[k] = int(v) if v % 1 == 0 else float(v)
                        else:
                            wine[k] = v
                    wines.append(wine)
            
            # Sort by rating (highest first)
            wines.sort(key=lambda x: x.get('rating', 0), reverse=True)
            
            return wines[:limit]
            
        except ClientError as e:
            logger.error(f"Error searching wines: {e}")
            return []
    
    def get_wine_ratings(self, wine_id: int, limit: int = 10) -> List[Dict]:
        """Get ratings for a specific wine."""
        try:
            response = self.ratings_table.query(
                IndexName='WineRatingsIndex',
                KeyConditionExpression='wine_id = :wine_id',
                ExpressionAttributeValues={
                    ':wine_id': wine_id
                },
                Limit=limit,
                ScanIndexForward=False  # Sort by rating (highest first)
            )
            
            # Convert Decimal to float for JSON serialization
            ratings = []
            for item in response.get('Items', []):
                rating = {}
                for k, v in item.items():
                    if isinstance(v, Decimal):
                        # Check if it's an integer value
                        if v % 1 == 0:
                            rating[k] = int(v)
                        else:
                            rating[k] = float(v)
                    else:
                        rating[k] = v
                ratings.append(rating)
            
            return ratings
            
        except ClientError as e:
            logger.error(f"Error getting ratings for wine {wine_id}: {e}")
            return []
    
    def get_top_rated_wines(self, limit: int = 10, wine_type: str = None) -> List[Dict]:
        """Get top rated wines, optionally filtered by type."""
        try:
            if wine_type:
                # Use the TypeIndex GSI
                response = self.wines_table.query(
                    IndexName='TypeIndex',
                    KeyConditionExpression='#type = :wine_type',
                    ExpressionAttributeNames={
                        '#type': 'type',
                        '#rating': 'rating'
                    },
                    ExpressionAttributeValues={
                        ':wine_type': wine_type.lower()
                    },
                    Limit=limit,
                    ScanIndexForward=False  # Sort by rating (highest first)
                )
            else:
                # Just get top rated overall
                response = self.wines_table.scan(
                    Limit=limit,
                    Select='ALL_ATTRIBUTES'
                )
                
                # Sort by rating (highest first)
                items = sorted(
                    response.get('Items', []),
                    key=lambda x: x.get('rating', 0),
                    reverse=True
                )
                response['Items'] = items[:limit]
            
            # Convert Decimal to float for JSON serialization
            wines = []
            for item in response.get('Items', []):
                wine = {}
                for k, v in item.items():
                    if isinstance(v, Decimal):
                        # Check if it's an integer value
                        if v % 1 == 0:
                            wine[k] = int(v)
                        else:
                            wine[k] = float(v)
                    else:
                        wine[k] = v
                wines.append(wine)
            
            return wines
            
        except ClientError as e:
            logger.error(f"Error getting top rated wines: {e}")
            return []

# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize the service
    wine_service = WineDynamoDBService()
    
    # Example searches
    print("Searching for red wines with rating >= 4.5")
    wines = wine_service.search_wines(
        wine_type="Red",
        min_rating=4.5,
        limit=5
    )
    
    for i, wine in enumerate(wines, 1):
        print(f"{i}. {wine.get('name')} - {wine.get('type')} ({wine.get('rating')}/5)")
    
    if wines:
        wine_id = wines[0]['wine_id']
        print(f"\nTop ratings for {wines[0]['name']}:")
        ratings = wine_service.get_wine_ratings(wine_id, limit=3)
        for rating in ratings:
            print(f"- {rating.get('rating')}/5 by user {rating.get('user_id')}")
    
    print("\nTop 5 rated wines overall:")
    top_wines = wine_service.get_top_rated_wines(limit=5)
    for i, wine in enumerate(top_wines, 1):
        print(f"{i}. {wine.get('name')} - {wine.get('type')} ({wine.get('rating')}/5)")
