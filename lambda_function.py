"""
Alexa Wine Skill - Python Implementation
Modernized with ASK SDK for Python with all security and robustness improvements
"""

import json
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard

from config import config
from wine_service import WineService
from utils import logger_util, slot_utils, session_utils

# Initialize wine service
wine_service = WineService()

# ============================================================================
# REQUEST HANDLERS
# ============================================================================

class LaunchRequestHandler(AbstractRequestHandler):
    """Launch Request Handler - When skill is first opened"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('LaunchRequest received')
        
        return (handler_input.response_builder
                .speak(config.MESSAGES['welcome'])
                .ask(config.MESSAGES['welcome_reprompt'])
                .set_card(SimpleCard(config.ALEXA_CARD_TITLE, config.MESSAGES['welcome']))
                .response)

class WineSearchIntentHandler(AbstractRequestHandler):
    """Wine Search Intent Handler - Main search functionality"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("wineSearchIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('WineSearchIntent received')
        
        try:
            intent = handler_input.request_envelope.request.intent
            wine_result = slot_utils.get_wine_from_intent(intent.to_dict(), True)
            
            if not wine_result['success']:
                logger_util.error('Failed to extract wine from intent', wine_result.get('error'))
                return (handler_input.response_builder
                        .speak(config.MESSAGES['general_error'])
                        .response)
            
            search_term = wine_result['value']
            logger_util.info('Searching for wine', {'search_term': search_term})
            
            # Search for wines using the wine service
            wines = wine_service.search_wines(search_term)
            
            if not wines:
                return (handler_input.response_builder
                        .speak(config.MESSAGES['wine_not_found'])
                        .response)
            
            # Store wines in session attributes
            session_utils.set_wine_list(handler_input.attributes_manager, wines)
            session_utils.set_current_wine_index(handler_input.attributes_manager, 0)
            
            if len(wines) == 1:
                speech_text = f"I found {wines[0]['Name']}. What would you like to know about it?"
            else:
                speech_text = f"I found {len(wines)} wines. The first wine is {wines[0]['Name']}. What would you like to know about it?"
            
            return (handler_input.response_builder
                    .speak(speech_text)
                    .ask('You can ask for the price, rating, location, or description. What would you like to know?')
                    .set_card(SimpleCard(config.ALEXA_CARD_TITLE, speech_text))
                    .response)
        
        except Exception as error:
            logger_util.error('Error in WineSearchIntent', error)
            return (handler_input.response_builder
                    .speak(config.MESSAGES['api_error'])
                    .response)

class WineActionDetailIntentHandler(AbstractRequestHandler):
    """Wine Action Detail Intent Handler - Get specific wine details"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("wineActionDetailIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('WineActionDetailIntent received')
        
        try:
            intent = handler_input.request_envelope.request.intent
            action_result = slot_utils.get_action_from_intent(intent.to_dict())
            
            if not action_result['success']:
                logger_util.error('Failed to extract action from intent', action_result.get('error'))
                return (handler_input.response_builder
                        .speak('I didn\'t understand what you want to know. You can ask for price, rating, location, or description.')
                        .ask('What would you like to know about this wine?')
                        .response)
            
            action = action_result['value']
            wines = session_utils.get_wine_list(handler_input.attributes_manager)
            current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
            
            if not wines or current_index >= len(wines):
                return (handler_input.response_builder
                        .speak('Please search for a wine first.')
                        .response)
            
            current_wine = wines[current_index]
            
            # Generate response based on action
            if action == config.DETAIL_TYPES['PRICE']:
                speech_text = f"The price of {current_wine['Name']} is ${current_wine['Price']:.2f}."
            elif action == config.DETAIL_TYPES['RATING']:
                speech_text = f"The rating of {current_wine['Name']} is {current_wine['Rating']} out of 5 stars."
            elif action == config.DETAIL_TYPES['LOCATION']:
                speech_text = f"{current_wine['Name']} is from {current_wine['Region']}, {current_wine['Country']}."
            elif action == config.DETAIL_TYPES['DESCRIPTION']:
                speech_text = f"Here's the description of {current_wine['Name']}: {current_wine['Description']}"
            else:
                speech_text = "I'm sorry, I don't understand that request. You can ask for price, rating, location, or description."
            
            return (handler_input.response_builder
                    .speak(speech_text)
                    .ask('What else would you like to know about this wine?')
                    .set_card(SimpleCard(config.ALEXA_CARD_TITLE, speech_text))
                    .response)
        
        except Exception as error:
            logger_util.error('Error in WineActionDetailIntent', error)
            return (handler_input.response_builder
                    .speak(config.MESSAGES['general_error'])
                    .response)

class GetWineDetailsIntentHandler(AbstractRequestHandler):
    """Get Wine Details Intent Handler - Ask what details user wants"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("getWineDetailsIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('GetWineDetailsIntent received')
        
        wines = session_utils.get_wine_list(handler_input.attributes_manager)
        current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
        
        if not wines or current_index >= len(wines):
            return (handler_input.response_builder
                    .speak('Please search for a wine first.')
                    .response)
        
        current_wine = wines[current_index]
        speech_text = f"What would you like to know about {current_wine['Name']}? You can ask for the price, rating, location, or description."
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('What would you like to know?')
                .response)

class NextIntentHandler(AbstractRequestHandler):
    """Next Intent Handler - Move to next wine in results"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.NextIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('NextIntent received')
        
        wines = session_utils.get_wine_list(handler_input.attributes_manager)
        current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
        
        if not wines:
            return (handler_input.response_builder
                    .speak('Please search for a wine first.')
                    .response)
        
        if current_index >= len(wines) - 1:
            speech_text = f"You're already at the last wine. The current wine is {wines[current_index]['Name']}. What would you like to know about it?"
        else:
            new_index = current_index + 1
            session_utils.set_current_wine_index(handler_input.attributes_manager, new_index)
            speech_text = f"The next wine is {wines[new_index]['Name']}. What would you like to know about it?"
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('What would you like to know about this wine?')
                .response)

class PreviousIntentHandler(AbstractRequestHandler):
    """Previous Intent Handler - Move to previous wine in results"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.PreviousIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('PreviousIntent received')
        
        wines = session_utils.get_wine_list(handler_input.attributes_manager)
        current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
        
        if not wines:
            return (handler_input.response_builder
                    .speak('Please search for a wine first.')
                    .response)
        
        if current_index <= 0:
            speech_text = f"You're already at the first wine. The current wine is {wines[0]['Name']}. What would you like to know about it?"
        else:
            new_index = current_index - 1
            session_utils.set_current_wine_index(handler_input.attributes_manager, new_index)
            speech_text = f"The previous wine is {wines[new_index]['Name']}. What would you like to know about it?"
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('What would you like to know about this wine?')
                .response)

class StartOverIntentHandler(AbstractRequestHandler):
    """Start Over Intent Handler - Reset to first wine"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.StartOverIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('StartOverIntent received')
        
        wines = session_utils.get_wine_list(handler_input.attributes_manager)
        
        if not wines:
            return (handler_input.response_builder
                    .speak('Please search for a wine first.')
                    .response)
        
        session_utils.set_current_wine_index(handler_input.attributes_manager, 0)
        speech_text = f"Starting over. The first wine is {wines[0]['Name']}. What would you like to know about it?"
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('What would you like to know about this wine?')
                .response)

class HelpIntentHandler(AbstractRequestHandler):
    """Help Intent Handler"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('HelpIntent received')
        
        return (handler_input.response_builder
                .speak(config.MESSAGES['help'])
                .ask(config.MESSAGES['help'])
                .response)

class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Cancel and Stop Intent Handler"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('CancelAndStopIntent received')
        
        return (handler_input.response_builder
                .speak(config.MESSAGES['goodbye'])
                .response)

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Session Ended Request Handler"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('SessionEndedRequest received', {
            'reason': handler_input.request_envelope.request.reason
        })
        
        # Any cleanup work goes here
        return handler_input.response_builder.response

# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handler to capture any syntax or routing errors"""
    
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True
    
    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger_util.error('Error handled', exception)
        
        return (handler_input.response_builder
                .speak(config.MESSAGES['general_error'])
                .ask('What would you like to do?')
                .response)

# ============================================================================
# SKILL BUILDER
# ============================================================================

# Create skill builder
sb = SkillBuilder()

# Add request handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(WineSearchIntentHandler())
sb.add_request_handler(WineActionDetailIntentHandler())
sb.add_request_handler(GetWineDetailsIntentHandler())
sb.add_request_handler(NextIntentHandler())
sb.add_request_handler(PreviousIntentHandler())
sb.add_request_handler(StartOverIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Add exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Set skill ID
sb.skill_id = config.ALEXA_SKILL_ID

# Lambda handler
lambda_handler = sb.lambda_handler()
