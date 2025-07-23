/**
 * Tests for config.js module
 */

const config = require('../config');

describe('Config Module', () => {
  test('should have wine API configuration', () => {
    expect(config.wineApi).toBeDefined();
    expect(config.wineApi.key).toBe('test-api-key');
    expect(config.wineApi.baseUrl).toBe('https://test-api.example.com');
    expect(config.wineApi.timeout).toBe(5000);
    expect(config.wineApi.maxResults).toBe(5);
  });

  test('should have alexa configuration', () => {
    expect(config.alexa).toBeDefined();
    expect(config.alexa.skillId).toBe('amzn1.ask.skill.test-skill-id');
    expect(config.alexa.cardTitle).toBe('Wine Assistant, your Sommelier');
  });

  test('should have AWS configuration', () => {
    expect(config.aws).toBeDefined();
    expect(config.aws.region).toBe('us-east-1');
    expect(config.aws.logLevel).toBe('error');
  });

  test('should have all required messages', () => {
    expect(config.messages).toBeDefined();
    expect(config.messages.welcome).toBeDefined();
    expect(config.messages.welcomeReprompt).toBeDefined();
    expect(config.messages.help).toBeDefined();
    expect(config.messages.goodbye).toBeDefined();
    expect(config.messages.wineNotFound).toBeDefined();
    expect(config.messages.apiError).toBeDefined();
    expect(config.messages.generalError).toBeDefined();
  });

  test('should have detail types', () => {
    expect(config.detailTypes).toBeDefined();
    expect(config.detailTypes.PRICE).toBe('price');
    expect(config.detailTypes.RATING).toBe('rating');
    expect(config.detailTypes.LOCATION).toBe('location');
    expect(config.detailTypes.DESCRIPTION).toBe('description');
  });

  test('messages should be strings and not empty', () => {
    Object.values(config.messages).forEach(message => {
      expect(typeof message).toBe('string');
      expect(message.length).toBeGreaterThan(0);
    });
  });
});
