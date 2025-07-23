/**
 * Wine Service Module
 * Handles all local wine database interactions with proper error handling
 */

const fs = require('fs');
const path = require('path');
const config = require('./config');
const { logger } = require('./utils');

/**
 * Wine Service for searching and managing wine data
 * Uses local curated wine database with smart search capabilities
 */
class WineService {
    constructor() {
        this.wineDatabase = null;
        this.loadWineDatabase();
    }

    /**
     * Load wine database from local JSON file
     */
    loadWineDatabase() {
        try {
            const dbPath = path.join(__dirname, 'wineDatabase.json');
            const rawData = fs.readFileSync(dbPath, 'utf8');
            this.wineDatabase = JSON.parse(rawData);
            logger.info('Wine database loaded successfully', {
                totalWines: this.wineDatabase.wines.length,
                version: this.wineDatabase.metadata.version
            });
        } catch (error) {
            logger.error('Failed to load wine database', { error: error.message });
            throw new Error('Wine database could not be loaded');
        }
    }

    /**
     * Search for wines using smart matching
     * @param {string} searchTerm - Wine name, type, region, or winery
     * @param {Object} filters - Optional filters (type, region, priceRange, etc.)
     * @returns {Promise<Array>} Array of matching wines
     */
    async searchWines(searchTerm, filters = {}) {
        // Input validation
        if (!searchTerm || typeof searchTerm !== 'string' || searchTerm.trim().length === 0) {
            throw new Error('Invalid search term provided');
        }

        const cleanSearchTerm = searchTerm.trim().toLowerCase();
        logger.info('Searching wine database', {
            searchTerm: cleanSearchTerm,
            filters
        });

        try {
            let results = this.wineDatabase.wines.filter(wine => {
                // Search in multiple fields
                const searchFields = [
                    wine.name.toLowerCase(),
                    wine.winery.toLowerCase(),
                    wine.type.toLowerCase(),
                    wine.region.toLowerCase(),
                    wine.country.toLowerCase(),
                    wine.description.toLowerCase()
                ];

                // Check if search term matches any field
                const matchesSearch = searchFields.some(field => 
                    field.includes(cleanSearchTerm)
                );

                if (!matchesSearch) return false;

                // Apply filters
                if (filters.type && !wine.type.toLowerCase().includes(filters.type.toLowerCase())) {
                    return false;
                }
                if (filters.region && !wine.region.toLowerCase().includes(filters.region.toLowerCase())) {
                    return false;
                }
                if (filters.winery && !wine.winery.toLowerCase().includes(filters.winery.toLowerCase())) {
                    return false;
                }
                if (filters.maxPrice && wine.price > filters.maxPrice) {
                    return false;
                }
                if (filters.minRating && wine.rating < filters.minRating) {
                    return false;
                }

                return true;
            });

            // Sort results by relevance (exact matches first, then by rating)
            results = results.sort((a, b) => {
                const aExactMatch = a.name.toLowerCase() === cleanSearchTerm ||
                                  a.type.toLowerCase() === cleanSearchTerm;
                const bExactMatch = b.name.toLowerCase() === cleanSearchTerm ||
                                  b.type.toLowerCase() === cleanSearchTerm;
                
                if (aExactMatch && !bExactMatch) return -1;
                if (!aExactMatch && bExactMatch) return 1;
                
                // Sort by rating if no exact match preference
                return b.rating - a.rating;
            });

            // Limit results to 5 for performance
            results = results.slice(0, 5);

            // Process results to match expected format
            const processedResults = results.map(wine => this.processWineData(wine));

            logger.info('Wine search completed', {
                searchTerm: cleanSearchTerm,
                resultsCount: processedResults.length
            });

            return processedResults;
        } catch (error) {
            logger.error('Wine search failed', {
                searchTerm: cleanSearchTerm,
                error: error.message
            });
            throw new Error('Failed to search wine database');
        }
    }

    /**
     * Process wine data to match expected format
     * @param {Object} wine - Raw wine data from database
     * @returns {Object} Processed wine object
     */
    processWineData(wine) {
        return {
            Id: wine.id,
            Name: wine.name,
            Winery: wine.winery,
            Type: wine.type,
            Region: wine.region,
            Country: wine.country,
            Vintage: wine.vintage,
            Price: wine.price,
            Rating: wine.rating,
            Description: wine.description,
            Alcohol: wine.alcohol,
            Pairings: wine.pairings,
            Occasions: wine.occasions
        };
    }

    /**
     * Get wine recommendations based on food pairing
     * @param {string} foodType - Type of food to pair with
     * @returns {Promise<Array>} Array of recommended wines
     */
    async getWinePairings(foodType) {
        if (!foodType || typeof foodType !== 'string') {
            throw new Error('Invalid food type provided');
        }

        const cleanFoodType = foodType.trim().toLowerCase();
        logger.info('Finding wine pairings', { foodType: cleanFoodType });

        try {
            const results = this.wineDatabase.wines.filter(wine => 
                wine.pairings.some(pairing => 
                    pairing.toLowerCase().includes(cleanFoodType)
                )
            );

            // Sort by rating and limit to 3 recommendations
            const sortedResults = results
                .sort((a, b) => b.rating - a.rating)
                .slice(0, 3)
                .map(wine => this.processWineData(wine));

            logger.info('Wine pairing search completed', {
                foodType: cleanFoodType,
                resultsCount: sortedResults.length
            });

            return sortedResults;
        } catch (error) {
            logger.error('Wine pairing search failed', {
                foodType: cleanFoodType,
                error: error.message
            });
            throw new Error('Failed to find wine pairings');
        }
    }

    /**
     * Get wine recommendations for occasions
     * @param {string} occasion - Type of occasion
     * @returns {Promise<Array>} Array of recommended wines
     */
    async getOccasionWines(occasion) {
        if (!occasion || typeof occasion !== 'string') {
            throw new Error('Invalid occasion provided');
        }

        const cleanOccasion = occasion.trim().toLowerCase();
        logger.info('Finding wines for occasion', { occasion: cleanOccasion });

        try {
            const results = this.wineDatabase.wines.filter(wine => 
                wine.occasions.some(occ => 
                    occ.toLowerCase().includes(cleanOccasion)
                )
            );

            // Sort by rating and limit to 3 recommendations
            const sortedResults = results
                .sort((a, b) => b.rating - a.rating)
                .slice(0, 3)
                .map(wine => this.processWineData(wine));

            logger.info('Occasion wine search completed', {
                occasion: cleanOccasion,
                resultsCount: sortedResults.length
            });

            return sortedResults;
        } catch (error) {
            logger.error('Occasion wine search failed', {
                occasion: cleanOccasion,
                error: error.message
            });
            throw new Error('Failed to find wines for occasion');
        }
    }

    /**
     * Get a random wine recommendation
     * @param {Object} filters - Optional filters
     * @returns {Promise<Object>} Random wine recommendation
     */
    async getRandomWine(filters = {}) {
        logger.info('Getting random wine recommendation', { filters });

        try {
            let wines = this.wineDatabase.wines;

            // Apply filters
            if (filters.type) {
                wines = wines.filter(wine => 
                    wine.type.toLowerCase().includes(filters.type.toLowerCase())
                );
            }
            if (filters.maxPrice) {
                wines = wines.filter(wine => wine.price <= filters.maxPrice);
            }
            if (filters.minRating) {
                wines = wines.filter(wine => wine.rating >= filters.minRating);
            }

            if (wines.length === 0) {
                throw new Error('No wines match the specified criteria');
            }

            // Get random wine
            const randomIndex = Math.floor(Math.random() * wines.length);
            const randomWine = this.processWineData(wines[randomIndex]);

            logger.info('Random wine selected', {
                wineName: randomWine.Name,
                filters
            });

            return randomWine;
        } catch (error) {
            logger.error('Random wine selection failed', {
                filters,
                error: error.message
            });
            throw new Error('Failed to get random wine recommendation');
        }
    }
}

module.exports = WineService;
