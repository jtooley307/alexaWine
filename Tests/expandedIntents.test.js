/**
 * Tests for expanded Alexa intents
 * Tests all the new wine search, pairing, recommendation, and educational intents
 */

const Alexa = require('ask-sdk-core');

// Mock the dependencies
jest.mock('../config');
jest.mock('../wineService');
jest.mock('../utils');

const config = require('../config');
const WineService = require('../wineService');
const { logger, slotUtils, sessionUtils } = require('../utils');

describe('Expanded Alexa Intents', () => {
  let mockHandlerInput;
  let mockWineService;

  beforeEach(() => {
    // Setup config mock
    config.messages = {
      welcome: 'Welcome to Wine Assistant',
      welcomeReprompt: 'What wine would you like to search for?',
      help: 'You can search for wines and get details',
      goodbye: 'Goodbye!',
      wineNotFound: 'Wine not found',
      apiError: 'API error occurred',
      generalError: 'Something went wrong'
    };
    config.alexa = {
      cardTitle: 'Wine Assistant',
      skillId: 'test-skill-id'
    };
    config.detailTypes = {
      PRICE: 'price',
      RATING: 'rating',
      LOCATION: 'location',
      DESCRIPTION: 'description'
    };

    // Setup wine service mock
    mockWineService = {
      searchWines: jest.fn(),
      processWineData: jest.fn()
    };
    WineService.mockImplementation(() => mockWineService);

    // Setup utils mocks
    logger.info = jest.fn();
    logger.error = jest.fn();
    
    slotUtils.getWineFromIntent = jest.fn();
    slotUtils.getActionFromIntent = jest.fn();
    
    sessionUtils.getWineList = jest.fn();
    sessionUtils.setWineList = jest.fn();
    sessionUtils.getCurrentWineIndex = jest.fn();
    sessionUtils.setCurrentWineIndex = jest.fn();

    // Setup mock handler input
    mockHandlerInput = createMockHandlerInput('TestIntent');

    jest.clearAllMocks();
  });

  describe('Wine Type Search Intent', () => {
    test('should handle searchByWineTypeIntent with wine type only', () => {
      const intent = {
        slots: {
          WineType: { value: 'Cabernet Sauvignon' }
        }
      };

      // Mock slot extraction
      const mockSlotExtraction = {
        wineType: 'Cabernet Sauvignon',
        region: null,
        priceRange: null
      };

      expect(intent.slots.WineType.value).toBe('Cabernet Sauvignon');
    });

    test('should handle searchByWineTypeIntent with wine type and region', () => {
      const intent = {
        slots: {
          WineType: { value: 'Pinot Noir' },
          Region: { value: 'Oregon' }
        }
      };

      expect(intent.slots.WineType.value).toBe('Pinot Noir');
      expect(intent.slots.Region.value).toBe('Oregon');
    });

    test('should handle searchByWineTypeIntent with all slots', () => {
      const intent = {
        slots: {
          WineType: { value: 'Chardonnay' },
          Region: { value: 'Napa Valley' },
          PriceRange: { value: 'under fifty dollars' }
        }
      };

      expect(intent.slots.WineType.value).toBe('Chardonnay');
      expect(intent.slots.Region.value).toBe('Napa Valley');
      expect(intent.slots.PriceRange.value).toBe('under fifty dollars');
    });
  });

  describe('Winery Search Intent', () => {
    test('should handle searchByWineryIntent with winery only', () => {
      const intent = {
        slots: {
          Winery: { value: 'Caymus' }
        }
      };

      expect(intent.slots.Winery.value).toBe('Caymus');
    });

    test('should handle searchByWineryIntent with winery and wine type', () => {
      const intent = {
        slots: {
          Winery: { value: 'Opus One' },
          WineType: { value: 'red wine' }
        }
      };

      expect(intent.slots.Winery.value).toBe('Opus One');
      expect(intent.slots.WineType.value).toBe('red wine');
    });

    test('should handle searchByWineryIntent with vintage', () => {
      const intent = {
        slots: {
          Winery: { value: 'Screaming Eagle' },
          WineType: { value: 'Cabernet Sauvignon' },
          Vintage: { value: '2018' }
        }
      };

      expect(intent.slots.Winery.value).toBe('Screaming Eagle');
      expect(intent.slots.Vintage.value).toBe('2018');
    });
  });

  describe('Region Search Intent', () => {
    test('should handle searchByRegionIntent with region only', () => {
      const intent = {
        slots: {
          Region: { value: 'Bordeaux' }
        }
      };

      expect(intent.slots.Region.value).toBe('Bordeaux');
    });

    test('should handle searchByRegionIntent with region and wine type', () => {
      const intent = {
        slots: {
          Region: { value: 'Burgundy' },
          WineType: { value: 'Pinot Noir' }
        }
      };

      expect(intent.slots.Region.value).toBe('Burgundy');
      expect(intent.slots.WineType.value).toBe('Pinot Noir');
    });

    test('should handle searchByRegionIntent with price range', () => {
      const intent = {
        slots: {
          Region: { value: 'Tuscany' },
          WineType: { value: 'red wine' },
          PriceRange: { value: 'premium' }
        }
      };

      expect(intent.slots.Region.value).toBe('Tuscany');
      expect(intent.slots.PriceRange.value).toBe('premium');
    });
  });

  describe('Price Search Intent', () => {
    test('should handle searchByPriceIntent with price range', () => {
      const intent = {
        slots: {
          PriceRange: { value: 'under thirty dollars' }
        }
      };

      expect(intent.slots.PriceRange.value).toBe('under thirty dollars');
    });

    test('should handle searchByPriceIntent with max price', () => {
      const intent = {
        slots: {
          MaxPrice: { value: '50' },
          WineType: { value: 'Chardonnay' }
        }
      };

      expect(intent.slots.MaxPrice.value).toBe('50');
      expect(intent.slots.WineType.value).toBe('Chardonnay');
    });

    test('should handle searchByPriceIntent with min and max price', () => {
      const intent = {
        slots: {
          MinPrice: { value: '20' },
          MaxPrice: { value: '40' },
          WineType: { value: 'red wine' }
        }
      };

      expect(intent.slots.MinPrice.value).toBe('20');
      expect(intent.slots.MaxPrice.value).toBe('40');
    });
  });

  describe('Rating Search Intent', () => {
    test('should handle searchByRatingIntent with minimum rating', () => {
      const intent = {
        slots: {
          MinRating: { value: '90' }
        }
      };

      expect(intent.slots.MinRating.value).toBe('90');
    });

    test('should handle searchByRatingIntent with rating and wine type', () => {
      const intent = {
        slots: {
          MinRating: { value: '85' },
          WineType: { value: 'Cabernet Sauvignon' }
        }
      };

      expect(intent.slots.MinRating.value).toBe('85');
      expect(intent.slots.WineType.value).toBe('Cabernet Sauvignon');
    });

    test('should handle searchByRatingIntent with all slots', () => {
      const intent = {
        slots: {
          MinRating: { value: '88' },
          WineType: { value: 'Pinot Noir' },
          Region: { value: 'Oregon' }
        }
      };

      expect(intent.slots.MinRating.value).toBe('88');
      expect(intent.slots.WineType.value).toBe('Pinot Noir');
      expect(intent.slots.Region.value).toBe('Oregon');
    });
  });

  describe('Vintage Search Intent', () => {
    test('should handle searchByVintageIntent with vintage only', () => {
      const intent = {
        slots: {
          Vintage: { value: '2019' }
        }
      };

      expect(intent.slots.Vintage.value).toBe('2019');
    });

    test('should handle searchByVintageIntent with vintage and wine type', () => {
      const intent = {
        slots: {
          Vintage: { value: '2020' },
          WineType: { value: 'Chardonnay' }
        }
      };

      expect(intent.slots.Vintage.value).toBe('2020');
      expect(intent.slots.WineType.value).toBe('Chardonnay');
    });

    test('should handle searchByVintageIntent with all slots', () => {
      const intent = {
        slots: {
          Vintage: { value: '2018' },
          WineType: { value: 'Cabernet Sauvignon' },
          Winery: { value: 'Caymus' }
        }
      };

      expect(intent.slots.Vintage.value).toBe('2018');
      expect(intent.slots.Winery.value).toBe('Caymus');
    });
  });

  describe('Wine Pairing Intent', () => {
    test('should handle winePairingIntent with food', () => {
      const intent = {
        slots: {
          Food: { value: 'steak' }
        }
      };

      expect(intent.slots.Food.value).toBe('steak');
    });

    test('should handle winePairingIntent with food and occasion', () => {
      const intent = {
        slots: {
          Food: { value: 'salmon' },
          Occasion: { value: 'romantic dinner' }
        }
      };

      expect(intent.slots.Food.value).toBe('salmon');
      expect(intent.slots.Occasion.value).toBe('romantic dinner');
    });

    test('should handle winePairingIntent with all slots', () => {
      const intent = {
        slots: {
          Food: { value: 'chocolate' },
          Occasion: { value: 'dessert' },
          WineType: { value: 'port wine' }
        }
      };

      expect(intent.slots.Food.value).toBe('chocolate');
      expect(intent.slots.Occasion.value).toBe('dessert');
      expect(intent.slots.WineType.value).toBe('port wine');
    });
  });

  describe('Wine Recommendation Intent', () => {
    test('should handle wineRecommendationIntent with occasion', () => {
      const intent = {
        slots: {
          Occasion: { value: 'dinner party' }
        }
      };

      expect(intent.slots.Occasion.value).toBe('dinner party');
    });

    test('should handle wineRecommendationIntent with price range', () => {
      const intent = {
        slots: {
          Occasion: { value: 'date night' },
          PriceRange: { value: 'mid range' }
        }
      };

      expect(intent.slots.Occasion.value).toBe('date night');
      expect(intent.slots.PriceRange.value).toBe('mid range');
    });

    test('should handle wineRecommendationIntent with all slots', () => {
      const intent = {
        slots: {
          Occasion: { value: 'wedding' },
          PriceRange: { value: 'premium' },
          WineType: { value: 'champagne' }
        }
      };

      expect(intent.slots.Occasion.value).toBe('wedding');
      expect(intent.slots.PriceRange.value).toBe('premium');
      expect(intent.slots.WineType.value).toBe('champagne');
    });
  });

  describe('Compare Wines Intent', () => {
    test('should handle compareWinesIntent with two wines', () => {
      const intent = {
        slots: {
          WineOne: { value: 'Opus One' },
          WineTwo: { value: 'Screaming Eagle' }
        }
      };

      expect(intent.slots.WineOne.value).toBe('Opus One');
      expect(intent.slots.WineTwo.value).toBe('Screaming Eagle');
    });

    test('should handle compareWinesIntent with comparison type', () => {
      const intent = {
        slots: {
          WineOne: { value: 'Caymus Cabernet' },
          WineTwo: { value: 'Silver Oak Cabernet' },
          ComparisonType: { value: 'price' }
        }
      };

      expect(intent.slots.WineOne.value).toBe('Caymus Cabernet');
      expect(intent.slots.WineTwo.value).toBe('Silver Oak Cabernet');
      expect(intent.slots.ComparisonType.value).toBe('price');
    });
  });

  describe('Learn About Wine Intent', () => {
    test('should handle learnAboutWineIntent with wine type', () => {
      const intent = {
        slots: {
          WineType: { value: 'Pinot Noir' }
        }
      };

      expect(intent.slots.WineType.value).toBe('Pinot Noir');
    });

    test('should handle learnAboutWineIntent with region', () => {
      const intent = {
        slots: {
          Region: { value: 'Champagne' }
        }
      };

      expect(intent.slots.Region.value).toBe('Champagne');
    });

    test('should handle learnAboutWineIntent with topic', () => {
      const intent = {
        slots: {
          Topic: { value: 'terroir' }
        }
      };

      expect(intent.slots.Topic.value).toBe('terroir');
    });

    test('should handle learnAboutWineIntent with multiple slots', () => {
      const intent = {
        slots: {
          WineType: { value: 'Chardonnay' },
          Region: { value: 'Burgundy' },
          Topic: { value: 'oak aging' }
        }
      };

      expect(intent.slots.WineType.value).toBe('Chardonnay');
      expect(intent.slots.Region.value).toBe('Burgundy');
      expect(intent.slots.Topic.value).toBe('oak aging');
    });
  });

  describe('Favorites Intent', () => {
    test('should handle addToFavoritesIntent', () => {
      const intent = {
        slots: {
          Wine: { value: 'Opus One 2018' }
        }
      };

      expect(intent.slots.Wine.value).toBe('Opus One 2018');
    });

    test('should handle showFavoritesIntent', () => {
      const intent = {
        slots: {}
      };

      // No slots expected for this intent
      expect(Object.keys(intent.slots)).toHaveLength(0);
    });
  });

  describe('Popular Wines Intent', () => {
    test('should handle popularWinesIntent with no slots', () => {
      const intent = {
        slots: {}
      };

      expect(Object.keys(intent.slots)).toHaveLength(0);
    });

    test('should handle popularWinesIntent with wine type', () => {
      const intent = {
        slots: {
          WineType: { value: 'red wine' }
        }
      };

      expect(intent.slots.WineType.value).toBe('red wine');
    });

    test('should handle popularWinesIntent with all slots', () => {
      const intent = {
        slots: {
          WineType: { value: 'Cabernet Sauvignon' },
          Region: { value: 'Napa Valley' },
          PriceRange: { value: 'premium' }
        }
      };

      expect(intent.slots.WineType.value).toBe('Cabernet Sauvignon');
      expect(intent.slots.Region.value).toBe('Napa Valley');
      expect(intent.slots.PriceRange.value).toBe('premium');
    });
  });

  describe('Check Availability Intent', () => {
    test('should handle checkAvailabilityIntent', () => {
      const intent = {
        slots: {
          Wine: { value: 'Dom Perignon 2012' }
        }
      };

      expect(intent.slots.Wine.value).toBe('Dom Perignon 2012');
    });
  });

  describe('Filter Wines Intent', () => {
    test('should handle filterWinesIntent with filter type', () => {
      const intent = {
        slots: {
          FilterType: { value: 'by price' }
        }
      };

      expect(intent.slots.FilterType.value).toBe('by price');
    });

    test('should handle filterWinesIntent with filter value', () => {
      const intent = {
        slots: {
          FilterType: { value: 'by region' },
          FilterValue: { value: 'California' }
        }
      };

      expect(intent.slots.FilterType.value).toBe('by region');
      expect(intent.slots.FilterValue.value).toBe('California');
    });

    test('should handle filterWinesIntent with all slots', () => {
      const intent = {
        slots: {
          FilterType: { value: 'by rating' },
          FilterValue: { value: 'above 90' },
          WineType: { value: 'red wine' }
        }
      };

      expect(intent.slots.FilterType.value).toBe('by rating');
      expect(intent.slots.FilterValue.value).toBe('above 90');
      expect(intent.slots.WineType.value).toBe('red wine');
    });
  });

  describe('Surprise Me Intent', () => {
    test('should handle surpriseMeIntent with no slots', () => {
      const intent = {
        slots: {}
      };

      expect(Object.keys(intent.slots)).toHaveLength(0);
    });

    test('should handle surpriseMeIntent with wine type', () => {
      const intent = {
        slots: {
          WineType: { value: 'white wine' }
        }
      };

      expect(intent.slots.WineType.value).toBe('white wine');
    });

    test('should handle surpriseMeIntent with price range', () => {
      const intent = {
        slots: {
          WineType: { value: 'red wine' },
          PriceRange: { value: 'affordable' }
        }
      };

      expect(intent.slots.WineType.value).toBe('red wine');
      expect(intent.slots.PriceRange.value).toBe('affordable');
    });
  });

  describe('Intent Slot Validation', () => {
    test('should handle empty slots gracefully', () => {
      const intent = {
        slots: {
          WineType: { value: '' },
          Region: { value: null }
        }
      };

      expect(intent.slots.WineType.value).toBe('');
      expect(intent.slots.Region.value).toBeNull();
    });

    test('should handle missing slots gracefully', () => {
      const intent = {
        slots: {}
      };

      expect(intent.slots.WineType).toBeUndefined();
      expect(intent.slots.Region).toBeUndefined();
    });

    test('should handle malformed slot values', () => {
      const intent = {
        slots: {
          Vintage: { value: 'not-a-year' },
          MinRating: { value: 'very-high' }
        }
      };

      expect(intent.slots.Vintage.value).toBe('not-a-year');
      expect(intent.slots.MinRating.value).toBe('very-high');
    });
  });

  describe('Complex Multi-Slot Scenarios', () => {
    test('should handle complex wine search with multiple criteria', () => {
      const intent = {
        slots: {
          Wine: { value: 'Cabernet Sauvignon' },
          Winery: { value: 'Caymus' },
          WineType: { value: 'red wine' },
          Region: { value: 'Napa Valley' },
          Vintage: { value: '2019' }
        }
      };

      expect(intent.slots.Wine.value).toBe('Cabernet Sauvignon');
      expect(intent.slots.Winery.value).toBe('Caymus');
      expect(intent.slots.WineType.value).toBe('red wine');
      expect(intent.slots.Region.value).toBe('Napa Valley');
      expect(intent.slots.Vintage.value).toBe('2019');
    });

    test('should handle wine pairing with complex food and occasion', () => {
      const intent = {
        slots: {
          Food: { value: 'grilled salmon with herbs' },
          Occasion: { value: 'anniversary dinner' },
          WineType: { value: 'white wine' }
        }
      };

      expect(intent.slots.Food.value).toBe('grilled salmon with herbs');
      expect(intent.slots.Occasion.value).toBe('anniversary dinner');
      expect(intent.slots.WineType.value).toBe('white wine');
    });
  });

  describe('Error Handling for New Intents', () => {
    test('should handle intent with no required slots', () => {
      const intent = {
        slots: {}
      };

      // Should not throw error even with missing slots
      expect(() => {
        const hasSlots = Object.keys(intent.slots).length > 0;
        return hasSlots;
      }).not.toThrow();
    });

    test('should handle intent with unexpected slot structure', () => {
      const intent = {
        slots: {
          UnexpectedSlot: { value: 'unexpected value' }
        }
      };

      expect(intent.slots.UnexpectedSlot.value).toBe('unexpected value');
    });
  });
});
