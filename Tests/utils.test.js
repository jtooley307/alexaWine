/**
 * Tests for utils.js module
 */

const { logger, validation, slotUtils, sessionUtils } = require('../utils');

describe('Utils Module', () => {
  
  describe('Logger', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    test('should log info messages', () => {
      logger.info('test message', { data: 'test' });
      // Since LOG_LEVEL is 'error' in test, info should not log
      expect(console.log).not.toHaveBeenCalled();
    });

    test('should log error messages', () => {
      const error = new Error('test error');
      logger.error('test error message', error);
      expect(console.error).toHaveBeenCalledWith('[ERROR] test error message', error.stack);
    });
  });

  describe('Validation', () => {
    describe('validateWineName', () => {
      test('should validate correct wine name', () => {
        const result = validation.validateWineName('Cabernet Sauvignon');
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBe('Cabernet Sauvignon');
      });

      test('should reject empty wine name', () => {
        const result = validation.validateWineName('');
        expect(result.isValid).toBe(false);
        expect(result.error).toBe('Wine name is required');
      });

      test('should reject null wine name', () => {
        const result = validation.validateWineName(null);
        expect(result.isValid).toBe(false);
        expect(result.error).toBe('Wine name is required');
      });

      test('should sanitize harmful characters', () => {
        const result = validation.validateWineName('Wine<script>alert("xss")</script>');
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBe('Winescriptalert(xss)/script');
      });

      test('should reject wine name that is too long', () => {
        const longName = 'a'.repeat(101);
        const result = validation.validateWineName(longName);
        expect(result.isValid).toBe(false);
        expect(result.error).toBe('Wine name is too long');
      });
    });

    describe('validateAction', () => {
      test('should validate correct action', () => {
        const result = validation.validateAction('price');
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBe('price');
      });

      test('should validate case insensitive action', () => {
        const result = validation.validateAction('PRICE');
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBe('price');
      });

      test('should reject invalid action', () => {
        const result = validation.validateAction('invalid');
        expect(result.isValid).toBe(false);
        expect(result.error).toContain('Invalid action');
      });

      test('should reject empty action', () => {
        const result = validation.validateAction('');
        expect(result.isValid).toBe(false);
        expect(result.error).toBe('Action is required');
      });
    });
  });

  describe('SlotUtils', () => {
    describe('getWineFromIntent', () => {
      test('should extract wine from valid intent', () => {
        const intent = {
          slots: {
            Wine: { value: 'Chardonnay' }
          }
        };
        const result = slotUtils.getWineFromIntent(intent);
        expect(result.success).toBe(true);
        expect(result.value).toBe('Chardonnay');
      });

      test('should return default wine when no slot and useDefault is true', () => {
        const intent = { slots: {} };
        const result = slotUtils.getWineFromIntent(intent, true);
        expect(result.success).toBe(true);
        expect(result.value).toBe('Goldeneye Pinot Noir Confluence 2014');
      });

      test('should return error when no slot and useDefault is false', () => {
        const intent = { slots: {} };
        const result = slotUtils.getWineFromIntent(intent, false);
        expect(result.success).toBe(false);
        expect(result.error).toBe('No wine specified');
      });

      test('should handle malformed intent gracefully', () => {
        const intent = null;
        const result = slotUtils.getWineFromIntent(intent);
        expect(result.success).toBe(false);
        expect(result.error).toBe('Failed to process wine name');
      });
    });

    describe('getActionFromIntent', () => {
      test('should extract action from valid intent', () => {
        const intent = {
          slots: {
            Action: { value: 'price' }
          }
        };
        const result = slotUtils.getActionFromIntent(intent);
        expect(result.success).toBe(true);
        expect(result.value).toBe('price');
      });

      test('should return error when no action slot', () => {
        const intent = { slots: {} };
        const result = slotUtils.getActionFromIntent(intent);
        expect(result.success).toBe(false);
        expect(result.error).toBe('No action specified');
      });
    });

    describe('getDateFromIntent', () => {
      test('should return current year when no date slot', () => {
        const intent = { slots: {} };
        const result = slotUtils.getDateFromIntent(intent);
        expect(result.success).toBe(true);
        expect(result.displayDate).toBe('Today');
        expect(result.requestDateParam).toBe(new Date().getFullYear());
      });

      test('should parse valid date', () => {
        const intent = {
          slots: {
            Date: { value: '2023-06-15' }
          }
        };
        const result = slotUtils.getDateFromIntent(intent);
        expect(result.success).toBe(true);
        expect(result.requestDateParam).toBe(2023);
      });

      test('should handle invalid date', () => {
        const intent = {
          slots: {
            Date: { value: 'invalid-date' }
          }
        };
        const result = slotUtils.getDateFromIntent(intent);
        expect(result.success).toBe(false);
        expect(result.error).toBe('Invalid date format');
      });
    });
  });

  describe('SessionUtils', () => {
    let mockAttributesManager;

    beforeEach(() => {
      mockAttributesManager = {
        getSessionAttributes: jest.fn().mockReturnValue({}),
        setSessionAttributes: jest.fn()
      };
    });

    describe('getWineList', () => {
      test('should return wine list from session', () => {
        const wineList = [{ name: 'Test Wine' }];
        mockAttributesManager.getSessionAttributes.mockReturnValue({ wineList });
        
        const result = sessionUtils.getWineList(mockAttributesManager);
        expect(result).toEqual(wineList);
      });

      test('should return empty array when no wine list', () => {
        mockAttributesManager.getSessionAttributes.mockReturnValue({});
        
        const result = sessionUtils.getWineList(mockAttributesManager);
        expect(result).toEqual([]);
      });

      test('should handle errors gracefully', () => {
        mockAttributesManager.getSessionAttributes.mockImplementation(() => {
          throw new Error('Session error');
        });
        
        const result = sessionUtils.getWineList(mockAttributesManager);
        expect(result).toEqual([]);
      });
    });

    describe('setWineList', () => {
      test('should set wine list in session', () => {
        const wineList = [{ name: 'Test Wine' }];
        const attributes = {};
        mockAttributesManager.getSessionAttributes.mockReturnValue(attributes);
        
        sessionUtils.setWineList(mockAttributesManager, wineList);
        
        expect(attributes.wineList).toEqual(wineList);
        expect(mockAttributesManager.setSessionAttributes).toHaveBeenCalledWith(attributes);
      });

      test('should handle errors gracefully', () => {
        mockAttributesManager.getSessionAttributes.mockImplementation(() => {
          throw new Error('Session error');
        });
        
        // Should not throw
        expect(() => {
          sessionUtils.setWineList(mockAttributesManager, []);
        }).not.toThrow();
      });
    });

    describe('getCurrentWineIndex', () => {
      test('should return current wine index from session', () => {
        mockAttributesManager.getSessionAttributes.mockReturnValue({ currentWineIndex: 2 });
        
        const result = sessionUtils.getCurrentWineIndex(mockAttributesManager);
        expect(result).toBe(2);
      });

      test('should return 0 when no index set', () => {
        mockAttributesManager.getSessionAttributes.mockReturnValue({});
        
        const result = sessionUtils.getCurrentWineIndex(mockAttributesManager);
        expect(result).toBe(0);
      });
    });

    describe('setCurrentWineIndex', () => {
      test('should set current wine index in session', () => {
        const attributes = {};
        mockAttributesManager.getSessionAttributes.mockReturnValue(attributes);
        
        sessionUtils.setCurrentWineIndex(mockAttributesManager, 3);
        
        expect(attributes.currentWineIndex).toBe(3);
        expect(mockAttributesManager.setSessionAttributes).toHaveBeenCalledWith(attributes);
      });
    });
  });
});
