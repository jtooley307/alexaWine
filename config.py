"""
Configuration module for Alexa Wine Skill
Handles environment variables and configuration constants
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for Alexa Wine Skill"""
    
    # Spoonacular integration removed
    
    # Local Database Fallback
    WINE_DATABASE_PATH = os.getenv('WINE_DATABASE_PATH', 'wineDatabase.json')
    
    # API Configuration
    WINE_API_MAX_RESULTS = 5
    
    # Alexa Skill Configuration
    ALEXA_SKILL_ID = os.getenv('ALEXA_SKILL_ID', 'amzn1.ask.skill.db86c0db-cfb9-426f-99c5-dfc8406bd56f')
    ALEXA_CARD_TITLE = "Wine Assistant, your Sommelier"
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    # Optional DynamoDB-backed search
    USE_DYNAMODB = os.getenv('USE_DYNAMODB', 'false').lower() == 'true'
    DYNAMODB_TABLE_PREFIX = os.getenv('DYNAMODB_TABLE_PREFIX', 'wine_skill_')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'info')

    # Local Vector Search (X-Wines) - optional offline semantic search
    USE_LOCAL_VECTOR_SEARCH = os.getenv('USE_LOCAL_VECTOR_SEARCH', 'false').lower() == 'true'
    XWINES_DATA_DIR = os.getenv('XWINES_DATA_DIR', 'data/xwines')
    XWINES_DB_PATH = os.getenv('XWINES_DB_PATH', os.path.join(XWINES_DATA_DIR, 'xwines.db'))
    XWINES_EMB_CSV = os.getenv('XWINES_EMB_CSV', os.path.join(XWINES_DATA_DIR, 'xwines_embeddings.csv'))
    # OpenSearch toggle for BM25 text search when available
    USE_OPENSEARCH = os.getenv('USE_OPENSEARCH', 'false').lower() == 'true'
    # Enable vector (kNN) search in OpenSearch
    USE_VECTOR_SEARCH = os.getenv('USE_VECTOR_SEARCH', 'false').lower() == 'true'
    # Enable hybrid (BM25 + kNN) fusion
    USE_HYBRID_SEARCH = os.getenv('USE_HYBRID_SEARCH', 'true').lower() == 'true'
    # Query-time embedding config (Ollama)
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_EMBED_MODEL = os.getenv('OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    EMBED_DIM = int(os.getenv('EMBED_DIM', '768'))
    
    # Skill Messages
    MESSAGES = {
        'welcome': "You can ask Wine Assistant for wine information. Say, Find me a wine by  describing the type of wine you want.",
        'welcome_reprompt': 'Try: find spicy red from Portugal. After a result, say tell me more, next, previous, or start over.',
        'help': "Try: find Napa Cabernet 2018. After a result, say tell me more for a short summary, or say next, previous, start over, or search again. What would you like to do?",
        'goodbye': "Happy to help, goodbye!",
        'shutdown': "Ok see you again soon.",
        'wine_not_found': "I'm sorry, I couldn't find that wine. Please try a different wine name or check the spelling.",
        'api_error': "I'm having trouble connecting to the wine database right now. Please try again in a moment.",
        'general_error': "I'm sorry, something went wrong. Please try again."
    }
    
    # Wine detail types
    DETAIL_TYPES = {
        'PRICE': 'price',
        'RATING': 'rating',
        'LOCATION': 'location',
        'DESCRIPTION': 'description'
    }

# Create a global config instance
config = Config()
