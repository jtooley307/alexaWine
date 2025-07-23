/**
 * Wine Service Tests
 * Tests for local wine database service
 */

const WineService = require('../wineService');
const fs = require('fs');

// Mock fs module for testing
jest.mock('fs');

describe('WineService', () => {
    let wineService;
    let mockWineData;

    beforeEach(() => {
        // Mock wine database data
        mockWineData = {
            wines: [
                {
                    id: '1',
                    name: 'Caymus Cabernet Sauvignon 2021',
                    winery: 'Caymus Vineyards',
                    type: 'Cabernet Sauvignon',
                    region: 'Napa Valley',
                    country: 'United States',
                    vintage: 2021,
                    price: 89.99,
                    rating: 92,
                    description: 'Rich and full-bodied with dark fruit flavors',
                    alcohol: 14.5,
                    pairings: ['steak', 'lamb', 'beef'],
                    occasions: ['dinner party', 'celebration']
                },
                {
                    id: '2',
                    name: 'Willamette Valley Pinot Noir 2021',
                    winery: 'Willamette Valley Vineyards',
                    type: 'Pinot Noir',
                    region: 'Willamette Valley',
                    country: 'United States',
                    vintage: 2021,
                    price: 32.99,
                    rating: 90,
                    description: 'Silky and complex with cherry notes',
                    alcohol: 13.0,
                    pairings: ['salmon', 'duck', 'pork'],
                    occasions: ['date night', 'wine tasting']
                }
            ],
            metadata: {
                totalWines: 2,
                version: '1.0'
            }
        };

        // Mock fs.readFileSync to return our mock data
        fs.readFileSync.mockReturnValue(JSON.stringify(mockWineData));
        
        // Create wine service instance
        wineService = new WineService();
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('constructor', () => {
        test('should initialize and load wine database', () => {
            expect(wineService.wineDatabase).toBeDefined();
            expect(wineService.wineDatabase.wines).toHaveLength(2);
            expect(fs.readFileSync).toHaveBeenCalledWith(
                expect.stringContaining('wineDatabase.json'),
                'utf8'
            );
        });

        test('should throw error if database cannot be loaded', () => {
            fs.readFileSync.mockImplementation(() => {
                throw new Error('File not found');
            });
            
            expect(() => new WineService()).toThrow('Wine database could not be loaded');
        });
    });

    describe('searchWines', () => {
        test('should reject invalid search term', async () => {
            await expect(wineService.searchWines('')).rejects.toThrow('Invalid search term provided');
            await expect(wineService.searchWines(null)).rejects.toThrow('Invalid search term provided');
            await expect(wineService.searchWines(123)).rejects.toThrow('Invalid search term provided');
        });

        test('should search wines by name', async () => {
            const results = await wineService.searchWines('Caymus');
            expect(results).toHaveLength(1);
            expect(results[0].Name).toBe('Caymus Cabernet Sauvignon 2021');
        });

        test('should search wines by type', async () => {
            const results = await wineService.searchWines('Pinot Noir');
            expect(results).toHaveLength(1);
            expect(results[0].Type).toBe('Pinot Noir');
        });

        test('should search wines by region', async () => {
            const results = await wineService.searchWines('Napa Valley');
            expect(results).toHaveLength(1);
            expect(results[0].Region).toBe('Napa Valley');
        });

        test('should return empty array for no matches', async () => {
            const results = await wineService.searchWines('NonExistentWine');
            expect(results).toHaveLength(0);
        });

        test('should apply type filter', async () => {
            const results = await wineService.searchWines('Cabernet', { type: 'Cabernet' });
            expect(results).toHaveLength(1);
            expect(results[0].Type).toBe('Cabernet Sauvignon');
        });

        test('should apply price filter', async () => {
            const results = await wineService.searchWines('Pinot', { maxPrice: 50 });
            expect(results).toHaveLength(1);
            expect(results[0].Price).toBeLessThanOrEqual(50);
        });

        test('should sort by rating', async () => {
            const results = await wineService.searchWines('Vineyards');
            expect(results).toHaveLength(2);
            expect(results[0].Rating).toBeGreaterThanOrEqual(results[1].Rating);
        });
    });

    describe('processWineData', () => {
        test('should process wine data correctly', () => {
            const rawWine = mockWineData.wines[0];
            const processed = wineService.processWineData(rawWine);
            
            expect(processed.Id).toBe('1');
            expect(processed.Name).toBe('Caymus Cabernet Sauvignon 2021');
            expect(processed.Winery).toBe('Caymus Vineyards');
            expect(processed.Type).toBe('Cabernet Sauvignon');
            expect(processed.Region).toBe('Napa Valley');
            expect(processed.Price).toBe(89.99);
            expect(processed.Rating).toBe(92);
        });
    });

    describe('getWinePairings', () => {
        test('should find wines for food pairing', async () => {
            const results = await wineService.getWinePairings('steak');
            expect(results).toHaveLength(1);
            expect(results[0].Name).toBe('Caymus Cabernet Sauvignon 2021');
        });

        test('should return empty array for unknown food', async () => {
            const results = await wineService.getWinePairings('pizza');
            expect(results).toHaveLength(0);
        });

        test('should reject invalid food type', async () => {
            await expect(wineService.getWinePairings('')).rejects.toThrow('Invalid food type provided');
            await expect(wineService.getWinePairings(null)).rejects.toThrow('Invalid food type provided');
        });
    });

    describe('getOccasionWines', () => {
        test('should find wines for occasion', async () => {
            const results = await wineService.getOccasionWines('celebration');
            expect(results).toHaveLength(1);
            expect(results[0].Name).toBe('Caymus Cabernet Sauvignon 2021');
        });

        test('should return empty array for unknown occasion', async () => {
            const results = await wineService.getOccasionWines('unknown');
            expect(results).toHaveLength(0);
        });

        test('should reject invalid occasion', async () => {
            await expect(wineService.getOccasionWines('')).rejects.toThrow('Invalid occasion provided');
            await expect(wineService.getOccasionWines(null)).rejects.toThrow('Invalid occasion provided');
        });
    });

    describe('getRandomWine', () => {
        test('should return a random wine', async () => {
            const result = await wineService.getRandomWine();
            expect(result).toBeDefined();
            expect(result.Name).toBeDefined();
            expect(['Caymus Cabernet Sauvignon 2021', 'Willamette Valley Pinot Noir 2021']).toContain(result.Name);
        });

        test('should apply price filter', async () => {
            const result = await wineService.getRandomWine({ maxPrice: 50 });
            expect(result.Price).toBeLessThanOrEqual(50);
        });

        test('should apply type filter', async () => {
            const result = await wineService.getRandomWine({ type: 'Pinot' });
            expect(result.Type).toContain('Pinot');
        });

        test('should throw error if no wines match criteria', async () => {
            await expect(wineService.getRandomWine({ maxPrice: 10 })).rejects.toThrow('Failed to get random wine recommendation');
        });
    });
});
