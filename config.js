/**
 * Configuration module for Alexa Wine Skill
 * Handles environment variables and configuration constants
 */

const config = {
    // Wine.com API Configuration
    wineApi: {
        key: process.env.WINE_API_KEY || '70b1bd8e9178f2b0abaf033e2a6c4067', // fallback for migration
        baseUrl: process.env.WINE_API_BASE_URL || 'https://services.wine.com/api/beta2/service.svc/JSON',
        timeout: 5000, // 5 second timeout
        maxResults: 5
    },

    // Alexa Skill Configuration
    alexa: {
        skillId: process.env.ALEXA_SKILL_ID || 'amzn1.ask.skill.db86c0db-cfb9-426f-99c5-dfc8406bd56f',
        cardTitle: "Wine Assistant, your Sommelier"
    },

    // AWS Configuration
    aws: {
        region: process.env.AWS_REGION || 'us-east-1',
        logLevel: process.env.LOG_LEVEL || 'info'
    },

    // Skill Messages
    messages: {
        welcome: "You can ask Wine Assistant for wine information. Say, Find a wine by its winery and name.",
        welcomeReprompt: 'You can ask me about a wine, then get details about the wine. What are you interested in?',
        help: "Here are some things you can say: Find a wine by giving its name. Tell me its rating, price, location, or description. What would you like to do?",
        goodbye: "Happy to help, goodbye!",
        shutdown: "Ok see you again soon.",
        wineNotFound: "I'm sorry, I couldn't find that wine. Please try a different wine name or check the spelling.",
        apiError: "I'm having trouble connecting to the wine database right now. Please try again in a moment.",
        generalError: "I'm sorry, something went wrong. Please try again."
    },

    // Wine detail types
    detailTypes: {
        PRICE: 'price',
        RATING: 'rating', 
        LOCATION: 'location',
        DESCRIPTION: 'description'
    }
};

module.exports = config;
