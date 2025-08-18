# DynamoDB Integration for Alexa Wine Skill

This document provides instructions for setting up and using DynamoDB as the database for the Alexa Wine Skill.

## Prerequisites

1. AWS Account with appropriate permissions
2. AWS CLI configured with credentials
3. Python 3.8+
4. Required Python packages (install with `pip install -r requirements.txt`)

## Setup Instructions

### 1. Configure Environment Variables

Copy the example environment file and update it with your AWS credentials:

```bash
cp .env.example .env
```

Edit the `.env` file and update the following variables:

```
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-west-2
DYNAMODB_TABLE_PREFIX=wine_skill_
```

### 2. Download the X-Wines Dataset

Run the following command to download and extract the X-Wines test dataset:

```bash
python setup_dynamodb.py
```

This will:
1. Download the X-Wines test dataset
2. Create the necessary DynamoDB tables
3. Load the data into the tables

### 3. Set Up IAM Permissions

Run the following command to create the necessary IAM role and permissions:

```bash
python setup_iam.py
```

This will create an IAM role with the necessary permissions for your Lambda function to access the DynamoDB tables.

## Using the WineDynamoDBService

The `WineDynamoDBService` class provides methods to interact with the DynamoDB tables:

```python
from wine_dynamodb_service import WineDynamoDBService

# Initialize the service
wine_service = WineDynamoDBService()

# Search for wines
wines = wine_service.search_wines(
    search_term="cabernet",
    wine_type="Red",
    min_rating=4.0,
    max_price=50.0,
    limit=5
)

# Get a wine by ID
wine = wine_service.get_wine_by_id(wine_id=1)

# Get ratings for a wine
ratings = wine_service.get_wine_ratings(wine_id=1, limit=5)

# Get top rated wines
top_wines = wine_service.get_top_rated_wines(limit=5, wine_type="Red")
```

## Integration with Alexa Skill

To use the DynamoDB service in your Alexa Skill, update your Lambda function to use the `WineDynamoDBService`:

```python
from wine_dynamodb_service import WineDynamoDBService

def lambda_handler(event, context):
    wine_service = WineDynamoDBService()
    
    # Example: Search for red wines
    red_wines = wine_service.search_wines(wine_type="Red", limit=5)
    
    # Process and return results...
```

## Example Usage

### Search for Wines

```python
# Search for red wines with rating >= 4.5
wines = wine_service.search_wines(
    wine_type="Red",
    min_rating=4.5,
    limit=5
)

for wine in wines:
    print(f"{wine['name']} - {wine['type']} ({wine['rating']}/5)")
```

### Get Top Rated Wines

```python
# Get top 5 rated wines
top_wines = wine_service.get_top_rated_wines(limit=5)

for i, wine in enumerate(top_wines, 1):
    print(f"{i}. {wine['name']} - {wine['type']} ({wine['rating']}/5)")
```

### Get Wine Ratings

```python
# Get top 3 ratings for a specific wine
ratings = wine_service.get_wine_ratings(wine_id=1, limit=3)

for rating in ratings:
    print(f"Rating: {rating['rating']}/5 by user {rating['user_id']}")
```

## Troubleshooting

### Common Issues

1. **Insufficient Permissions**: Make sure your IAM role has the necessary permissions to access DynamoDB.
2. **Table Not Found**: Ensure the tables exist and the table prefix in your `.env` file matches the one used during setup.
3. **Rate Limiting**: If you encounter rate limiting, consider increasing the provisioned throughput for your tables.

### Logging

Enable debug logging by setting the `LOG_LEVEL` environment variable to `DEBUG`:

```
LOG_LEVEL=debug
```

## Cleanup

To delete the DynamoDB tables and IAM resources, run:

```bash
python cleanup_dynamodb.py
```

**Note**: This will permanently delete all data in the tables.
