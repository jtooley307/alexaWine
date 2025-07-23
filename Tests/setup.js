/**
 * Test setup file for Jest
 * Sets up environment variables and common test utilities
 */

// Set test environment variables
process.env.WINE_API_KEY = 'test-api-key';
process.env.WINE_API_BASE_URL = 'https://test-api.example.com';
process.env.ALEXA_SKILL_ID = 'amzn1.ask.skill.test-skill-id';
process.env.AWS_REGION = 'us-east-1';
process.env.LOG_LEVEL = 'error'; // Suppress logs during testing

// Mock console methods to avoid cluttering test output
global.console = {
  ...console,
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
  debug: jest.fn()
};

// Common test utilities
global.createMockHandlerInput = (intentName, slots = {}) => {
  return {
    requestEnvelope: {
      request: {
        type: 'IntentRequest',
        intent: {
          name: intentName,
          slots: slots
        }
      }
    },
    responseBuilder: {
      speak: jest.fn().mockReturnThis(),
      reprompt: jest.fn().mockReturnThis(),
      withStandardCard: jest.fn().mockReturnThis(),
      getResponse: jest.fn().mockReturnValue({
        outputSpeech: { ssml: '<speak>test response</speak>' }
      })
    },
    attributesManager: {
      getSessionAttributes: jest.fn().mockReturnValue({}),
      setSessionAttributes: jest.fn()
    }
  };
};

global.createMockLaunchRequest = () => {
  return {
    requestEnvelope: {
      request: {
        type: 'LaunchRequest'
      }
    },
    responseBuilder: {
      speak: jest.fn().mockReturnThis(),
      reprompt: jest.fn().mockReturnThis(),
      withStandardCard: jest.fn().mockReturnThis(),
      getResponse: jest.fn().mockReturnValue({
        outputSpeech: { ssml: '<speak>test response</speak>' }
      })
    },
    attributesManager: {
      getSessionAttributes: jest.fn().mockReturnValue({}),
      setSessionAttributes: jest.fn()
    }
  };
};
