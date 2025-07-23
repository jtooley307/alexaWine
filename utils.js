/**
 * Utility functions for Alexa Wine Skill
 * Includes input validation, logging, and helper functions
 */

const config = require('./config');

/**
 * Logger utility with different log levels
 */
const logger = {
    info: (message, data = null) => {
        if (config.aws.logLevel === 'info' || config.aws.logLevel === 'debug') {
            console.log(`[INFO] ${message}`, data ? JSON.stringify(data) : '');
        }
    },
    error: (message, error = null) => {
        console.error(`[ERROR] ${message}`, error ? error.stack || error : '');
    },
    debug: (message, data = null) => {
        if (config.aws.logLevel === 'debug') {
            console.log(`[DEBUG] ${message}`, data ? JSON.stringify(data) : '');
        }
    }
};

/**
 * Input validation utilities
 */
const validation = {
    /**
     * Validates and sanitizes wine name input
     * @param {string} wineName - The wine name to validate
     * @returns {object} - {isValid: boolean, sanitized: string, error?: string}
     */
    validateWineName: (wineName) => {
        if (!wineName || typeof wineName !== 'string') {
            return { isValid: false, error: 'Wine name is required' };
        }

        // Remove potentially harmful characters and trim
        const sanitized = wineName.trim().replace(/[<>\"'&]/g, '');
        
        if (sanitized.length === 0) {
            return { isValid: false, error: 'Wine name is required' };
        }

        if (sanitized.length > 100) {
            return { isValid: false, error: 'Wine name is too long' };
        }

        return { isValid: true, sanitized };
    },

    /**
     * Validates action type for wine details
     * @param {string} action - The action to validate
     * @returns {object} - {isValid: boolean, sanitized: string, error?: string}
     */
    validateAction: (action) => {
        if (!action || typeof action !== 'string') {
            return { isValid: false, error: 'Action is required' };
        }

        const sanitized = action.toLowerCase().trim();
        const validActions = Object.values(config.detailTypes);

        if (!validActions.includes(sanitized)) {
            return { 
                isValid: false, 
                error: `Invalid action. Valid actions are: ${validActions.join(', ')}` 
            };
        }

        return { isValid: true, sanitized };
    }
};

/**
 * Slot extraction utilities with validation
 */
const slotUtils = {
    /**
     * Safely extracts wine name from intent slots
     * @param {object} intent - The Alexa intent object
     * @param {boolean} useDefault - Whether to use default wine if none provided
     * @returns {object} - {success: boolean, value?: string, error?: string}
     */
    getWineFromIntent: (intent, useDefault = false) => {
        try {
            const wineSlot = intent.slots && intent.slots.Wine;
            
            if (!wineSlot || !wineSlot.value) {
                if (useDefault) {
                    return { 
                        success: true, 
                        value: 'Goldeneye Pinot Noir Confluence 2014' 
                    };
                }
                return { success: false, error: 'No wine specified' };
            }

            const validation_result = validation.validateWineName(wineSlot.value);
            if (!validation_result.isValid) {
                return { success: false, error: validation_result.error };
            }

            return { success: true, value: validation_result.sanitized };
        } catch (error) {
            logger.error('Error extracting wine from intent', error);
            return { success: false, error: 'Failed to process wine name' };
        }
    },

    /**
     * Safely extracts action from intent slots
     * @param {object} intent - The Alexa intent object
     * @returns {object} - {success: boolean, value?: string, error?: string}
     */
    getActionFromIntent: (intent) => {
        try {
            const actionSlot = intent.slots && intent.slots.Action;
            
            if (!actionSlot || !actionSlot.value) {
                return { success: false, error: 'No action specified' };
            }

            const validation_result = validation.validateAction(actionSlot.value);
            if (!validation_result.isValid) {
                return { success: false, error: validation_result.error };
            }

            return { success: true, value: validation_result.sanitized };
        } catch (error) {
            logger.error('Error extracting action from intent', error);
            return { success: false, error: 'Failed to process action' };
        }
    },

    /**
     * Safely extracts date from intent slots
     * @param {object} intent - The Alexa intent object
     * @returns {object} - {success: boolean, displayDate?: string, requestDateParam?: number, error?: string}
     */
    getDateFromIntent: (intent) => {
        try {
            const dateSlot = intent.slots && intent.slots.Date;
            
            if (!dateSlot || !dateSlot.value) {
                // Default to current year
                const now = new Date();
                return {
                    success: true,
                    displayDate: "Today",
                    requestDateParam: now.getFullYear()
                };
            }

            const date = new Date(dateSlot.value);
            if (isNaN(date.getTime())) {
                return { success: false, error: 'Invalid date format' };
            }

            const alexaDateUtil = require('./alexaDateUtil');
            return {
                success: true,
                displayDate: alexaDateUtil.getFormattedDate(date),
                requestDateParam: date.getFullYear()
            };
        } catch (error) {
            logger.error('Error extracting date from intent', error);
            return { success: false, error: 'Failed to process date' };
        }
    }
};

/**
 * Session attribute utilities for state management
 */
const sessionUtils = {
    /**
     * Safely gets wine list from session attributes
     * @param {object} attributesManager - Alexa attributes manager
     * @returns {array} - Array of wines or empty array
     */
    getWineList: (attributesManager) => {
        try {
            const attributes = attributesManager.getSessionAttributes();
            return attributes.wineList || [];
        } catch (error) {
            logger.error('Error getting wine list from session', error);
            return [];
        }
    },

    /**
     * Safely sets wine list in session attributes
     * @param {object} attributesManager - Alexa attributes manager
     * @param {array} wineList - Array of wines to store
     */
    setWineList: (attributesManager, wineList) => {
        try {
            const attributes = attributesManager.getSessionAttributes();
            attributes.wineList = wineList || [];
            attributesManager.setSessionAttributes(attributes);
        } catch (error) {
            logger.error('Error setting wine list in session', error);
        }
    },

    /**
     * Safely gets current wine index from session attributes
     * @param {object} attributesManager - Alexa attributes manager
     * @returns {number} - Current wine index or 0
     */
    getCurrentWineIndex: (attributesManager) => {
        try {
            const attributes = attributesManager.getSessionAttributes();
            return attributes.currentWineIndex || 0;
        } catch (error) {
            logger.error('Error getting current wine index from session', error);
            return 0;
        }
    },

    /**
     * Safely sets current wine index in session attributes
     * @param {object} attributesManager - Alexa attributes manager
     * @param {number} index - Wine index to store
     */
    setCurrentWineIndex: (attributesManager, index) => {
        try {
            const attributes = attributesManager.getSessionAttributes();
            attributes.currentWineIndex = index || 0;
            attributesManager.setSessionAttributes(attributes);
        } catch (error) {
            logger.error('Error setting current wine index in session', error);
        }
    }
};

module.exports = {
    logger,
    validation,
    slotUtils,
    sessionUtils
};
