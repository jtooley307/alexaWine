/**
 * Alexa Wine Skill - Modernized with ASK SDK v3
 * Fixes all critical security, architecture, and robustness issues
 */

const Alexa = require('ask-sdk-core');
const config = require('./config');
const WineService = require('./wineService');
const { logger, slotUtils, sessionUtils } = require('./utils');

// Initialize wine service
const wineService = new WineService();

// ============================================================================
// REQUEST HANDLERS
// ============================================================================

/**
 * Launch Request Handler - When skill is first opened
 */
const LaunchRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
    },
    handle(handlerInput) {
        logger.info('LaunchRequest received');
        
        return handlerInput.responseBuilder
            .speak(config.messages.welcome)
            .reprompt(config.messages.welcomeReprompt)
            .withStandardCard(config.alexa.cardTitle, config.messages.welcome)
            .getResponse();
    }
};

/**
 * Wine Search Intent Handler - Main search functionality
 */
const WineSearchIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'wineSearchIntent';
    },
    async handle(handlerInput) {
        logger.info('WineSearchIntent received');
        
        try {
            const intent = handlerInput.requestEnvelope.request.intent;
            const wineResult = slotUtils.getWineFromIntent(intent, true);
            
            if (!wineResult.success) {
                logger.error('Failed to extract wine from intent', wineResult.error);
                return handlerInput.responseBuilder
                    .speak(config.messages.generalError)
                    .getResponse();
            }

            const searchTerm = wineResult.value;
            logger.info('Searching for wine', { searchTerm });

            // Search for wines using the wine service
            const apiResponse = await wineService.searchWines(searchTerm);
            const wines = wineService.processWineData(apiResponse);

            if (wines.length === 0) {
                return handlerInput.responseBuilder
                    .speak(config.messages.wineNotFound)
                    .getResponse();
            }

            // Store wines in session attributes
            sessionUtils.setWineList(handlerInput.attributesManager, wines);
            sessionUtils.setCurrentWineIndex(handlerInput.attributesManager, 0);

            let speechText;
            if (wines.length === 1) {
                speechText = `I found ${wines[0].name}. What would you like to know about it?`;
            } else {
                speechText = `I found ${wines.length} wines. The first wine is ${wines[0].name}. What would you like to know about it?`;
            }

            return handlerInput.responseBuilder
                .speak(speechText)
                .reprompt('You can ask for the price, rating, location, or description. What would you like to know?')
                .withStandardCard(config.alexa.cardTitle, speechText)
                .getResponse();

        } catch (error) {
            logger.error('Error in WineSearchIntent', error);
            return handlerInput.responseBuilder
                .speak(config.messages.apiError)
                .getResponse();
        }
    }
};

/**
 * Wine Action Detail Intent Handler - Get specific wine details
 */
const WineActionDetailIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'wineActionDetailIntent';
    },
    handle(handlerInput) {
        logger.info('WineActionDetailIntent received');
        
        try {
            const intent = handlerInput.requestEnvelope.request.intent;
            const actionResult = slotUtils.getActionFromIntent(intent);
            
            if (!actionResult.success) {
                return handlerInput.responseBuilder
                    .speak("I didn't understand what you want to know about the wine. You can ask for the price, rating, location, or description.")
                    .reprompt('What would you like to know about the wine?')
                    .getResponse();
            }

            const wines = sessionUtils.getWineList(handlerInput.attributesManager);
            const currentIndex = sessionUtils.getCurrentWineIndex(handlerInput.attributesManager);
            
            if (wines.length === 0 || !wines[currentIndex]) {
                return handlerInput.responseBuilder
                    .speak('Please search for a wine first.')
                    .getResponse();
            }

            const currentWine = wines[currentIndex];
            const action = actionResult.value;
            let speechText = `The ${currentWine.name} `;

            switch (action) {
                case config.detailTypes.PRICE:
                    if (currentWine.price > 0) {
                        speechText += `costs $${currentWine.price.toFixed(2)}`;
                    } else {
                        speechText += 'price is not available';
                    }
                    break;
                case config.detailTypes.RATING:
                    if (currentWine.rating > 0) {
                        speechText += `has a rating of ${currentWine.rating} points`;
                    } else {
                        speechText += 'rating is not available';
                    }
                    break;
                case config.detailTypes.LOCATION:
                    speechText += `is from ${currentWine.location}`;
                    break;
                case config.detailTypes.DESCRIPTION:
                    speechText += `description: ${currentWine.description}`;
                    break;
                default:
                    speechText = "I didn't understand what you want to know about the wine.";
            }

            speechText += '. You can ask for more information or search for another wine. What would you like to do?';

            return handlerInput.responseBuilder
                .speak(speechText)
                .reprompt('What else would you like to know?')
                .withStandardCard(config.alexa.cardTitle, speechText)
                .getResponse();

        } catch (error) {
            logger.error('Error in WineActionDetailIntent', error);
            return handlerInput.responseBuilder
                .speak(config.messages.generalError)
                .getResponse();
        }
    }
};

/**
 * Get Wine Details Intent Handler - Ask what details user wants
 */
const GetWineDetailsIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'getWineDetailsIntent';
    },
    handle(handlerInput) {
        logger.info('GetWineDetailsIntent received');
        
        const wines = sessionUtils.getWineList(handlerInput.attributesManager);
        
        if (wines.length === 0) {
            return handlerInput.responseBuilder
                .speak('Please search for a wine first.')
                .getResponse();
        }

        const speechText = 'What details would you like? You can ask for price, rating, location, or description.';
        
        return handlerInput.responseBuilder
            .speak(speechText)
            .reprompt(speechText)
            .getResponse();
    }
};

/**
 * Next Intent Handler - Move to next wine in results
 */
const NextIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.NextIntent';
    },
    handle(handlerInput) {
        logger.info('NextIntent received');
        
        const wines = sessionUtils.getWineList(handlerInput.attributesManager);
        let currentIndex = sessionUtils.getCurrentWineIndex(handlerInput.attributesManager);
        
        if (wines.length === 0) {
            return handlerInput.responseBuilder
                .speak('Please search for a wine first.')
                .getResponse();
        }

        if (currentIndex < wines.length - 1) {
            currentIndex++;
            sessionUtils.setCurrentWineIndex(handlerInput.attributesManager, currentIndex);
            const speechText = `The next wine is ${wines[currentIndex].name}. What would you like to know about it?`;
            
            return handlerInput.responseBuilder
                .speak(speechText)
                .reprompt('What would you like to know about this wine?')
                .getResponse();
        } else {
            return handlerInput.responseBuilder
                .speak('You are at the end of the list. You can go back to the beginning by saying start over.')
                .reprompt('What would you like to do?')
                .getResponse();
        }
    }
};

/**
 * Previous Intent Handler - Move to previous wine in results
 */
const PreviousIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.PreviousIntent';
    },
    handle(handlerInput) {
        logger.info('PreviousIntent received');
        
        const wines = sessionUtils.getWineList(handlerInput.attributesManager);
        let currentIndex = sessionUtils.getCurrentWineIndex(handlerInput.attributesManager);
        
        if (wines.length === 0) {
            return handlerInput.responseBuilder
                .speak('Please search for a wine first.')
                .getResponse();
        }

        if (currentIndex > 0) {
            currentIndex--;
            sessionUtils.setCurrentWineIndex(handlerInput.attributesManager, currentIndex);
            const speechText = `The previous wine is ${wines[currentIndex].name}. What would you like to know about it?`;
            
            return handlerInput.responseBuilder
                .speak(speechText)
                .reprompt('What would you like to know about this wine?')
                .getResponse();
        } else {
            return handlerInput.responseBuilder
                .speak('You are at the beginning of the list. You can go to the end by saying next.')
                .reprompt('What would you like to do?')
                .getResponse();
        }
    }
};

/**
 * Start Over Intent Handler - Reset to first wine
 */
const StartOverIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StartOverIntent';
    },
    handle(handlerInput) {
        logger.info('StartOverIntent received');
        
        const wines = sessionUtils.getWineList(handlerInput.attributesManager);
        
        if (wines.length === 0) {
            return handlerInput.responseBuilder
                .speak('Please search for a wine first.')
                .getResponse();
        }

        sessionUtils.setCurrentWineIndex(handlerInput.attributesManager, 0);
        const speechText = `Starting over. The first wine is ${wines[0].name}. What would you like to know about it?`;
        
        return handlerInput.responseBuilder
            .speak(speechText)
            .reprompt('What would you like to know about this wine?')
            .getResponse();
    }
};

/**
 * Help Intent Handler
 */
const HelpIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.HelpIntent';
    },
    handle(handlerInput) {
        logger.info('HelpIntent received');
        
        return handlerInput.responseBuilder
            .speak(config.messages.help)
            .reprompt(config.messages.help)
            .getResponse();
    }
};

/**
 * Cancel and Stop Intent Handler
 */
const CancelAndStopIntentHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && (Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.CancelIntent'
                || Alexa.getIntentName(handlerInput.requestEnvelope) === 'AMAZON.StopIntent');
    },
    handle(handlerInput) {
        logger.info('CancelAndStopIntent received');
        
        return handlerInput.responseBuilder
            .speak(config.messages.goodbye)
            .getResponse();
    }
};

/**
 * Session Ended Request Handler
 */
const SessionEndedRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'SessionEndedRequest';
    },
    handle(handlerInput) {
        logger.info('SessionEndedRequest received', {
            reason: handlerInput.requestEnvelope.request.reason
        });
        
        // Any cleanup work goes here
        return handlerInput.responseBuilder.getResponse();
    }
};

/**
 * Generic error handler to capture any syntax or routing errors
 */
const ErrorHandler = {
    canHandle() {
        return true;
    },
    handle(handlerInput, error) {
        logger.error('Error handled', error);
        
        return handlerInput.responseBuilder
            .speak(config.messages.generalError)
            .reprompt('What would you like to do?')
            .getResponse();
    }
};

// ============================================================================
// SKILL BUILDER
// ============================================================================

/**
 * This handler acts as the entry point for your skill, routing all request and response
 * payloads to the handlers above. Make sure any new handlers or interceptors you've
 * defined are included below. The order matters - they're processed top to bottom.
 */
exports.handler = Alexa.SkillBuilders.custom()
    .addRequestHandlers(
        LaunchRequestHandler,
        WineSearchIntentHandler,
        WineActionDetailIntentHandler,
        GetWineDetailsIntentHandler,
        NextIntentHandler,
        PreviousIntentHandler,
        StartOverIntentHandler,
        HelpIntentHandler,
        CancelAndStopIntentHandler,
        SessionEndedRequestHandler
    )
    .addErrorHandlers(ErrorHandler)
    .withSkillId(config.alexa.skillId)
    .lambda();
