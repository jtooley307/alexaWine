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
    
    # Open Wine API Configuration
    WINE_API_BASE_URL = os.getenv('WINE_API_BASE_URL', 'https://api.sampleapis.com/wines')
    WINE_API_TIMEOUT = 10  # 10 second timeout
    WINE_API_MAX_RESULTS = 5
    # Note: Open wine APIs typically don't require API keys
    
    # Alexa Skill Configuration
    ALEXA_SKILL_ID = os.getenv('ALEXA_SKILL_ID', 'amzn1.ask.skill.db86c0db-cfb9-426f-99c5-dfc8406bd56f')
    ALEXA_CARD_TITLE = "Wine Assistant, your Sommelier"
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'info')
    
    # Skill Messages
    MESSAGES = {
        'welcome': "You can ask Wine Assistant for wine information. Say, Find a wine by its winery and name.",
        'welcome_reprompt': 'You can ask me about a wine, then get details about the wine. What are you interested in?',
        'help': "Here are some things you can say: Find a wine by giving its name. Tell me its rating, price, location, or description. What would you like to do?",
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
