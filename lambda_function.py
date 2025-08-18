"""
Alexa Wine Skill - Python Implementation
Modernized with ASK SDK for Python with all security and robustness improvements
"""

import os
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

# ============================================================================
# Optional Bedrock NLG for natural combined responses
# ============================================================================
USE_BEDROCK_NLG = os.getenv("USE_BEDROCK_NLG", "false").lower() == "true"
BEDROCK_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-west-2"))
BEDROCK_TEXT_MODEL_ID = os.getenv("BEDROCK_TEXT_MODEL_ID", "amazon.titan-text-lite-v1")

def _generate_detail_with_bedrock(wine: dict, action: str) -> str:
    """Generate a concise, friendly response combining key attributes.
    Uses AWS Bedrock text generation if enabled. Returns empty string on failure.
    """
    if not USE_BEDROCK_NLG:
        return ""
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        # Condense attributes for prompt
        fields = {
            "name": wine.get("name"),
            "winery": wine.get("winery"),
            "type": wine.get("type"),
            "vintage": wine.get("vintage"),
            "region": wine.get("region"),
            "country": wine.get("country"),
            "price": wine.get("price"),
            "rating": wine.get("rating"),
            "alcohol": wine.get("alcohol_content"),
            "description": wine.get("description"),
        }
        # Build a short, spoken-friendly instruction
        system = (
            "You are an Alexa voice assistant. Generate a short, natural sentence "
            "for a user asking about a wine. Keep it under 30 words, speak-friendly, "
            "no markup, no bullet lists."
        )
        user = (
            f"Action: {action}.\n"
            f"Attributes: {json.dumps({k:v for k,v in fields.items() if v is not None})}"
        )
        # Titan Text models accept inputText and optional config
        body = json.dumps({
            "inputText": f"{system}\n\n{user}",
            "textGenerationConfig": {
                "maxTokenCount": 128,
                "temperature": 0.3,
                "topP": 0.9
            }
        })
        resp = client.invoke_model(modelId=BEDROCK_TEXT_MODEL_ID, body=body)
        payload = resp.get("body")
        if hasattr(payload, "read"):
            payload = payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = json.loads(payload) if isinstance(payload, str) else payload
        # Try common Bedrock result shapes
        text = ""
        if isinstance(data, dict):
            if "results" in data and data["results"]:
                cand = data["results"][0]
                text = cand.get("outputText") or cand.get("text", "")
            elif "outputText" in data:
                text = data.get("outputText", "")
        if isinstance(text, str):
            # Clean up excessive whitespace
            text = " ".join(text.strip().split())
            return text[:300]
        return ""
    except Exception as e:
        try:
            logger_util.error("Bedrock NLG failed", e)
        except Exception:
            pass
        return ""

# New: summary generator that combines winery, rating, location, and description
def _generate_summary_with_bedrock(wine: dict) -> str:
    if not USE_BEDROCK_NLG:
        return ""
    try:
        import boto3, json as _json
        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        fields = {
            "name": wine.get("name"),
            "winery": wine.get("winery"),
            "type": wine.get("type"),
            "vintage": wine.get("vintage"),
            "region": wine.get("region"),
            "country": wine.get("country"),
            "rating": wine.get("rating"),
            "price": wine.get("price"),
            "description": wine.get("description")
        }
        system = (
            "You are an Alexa voice assistant. Create a speak-friendly, concise summary (<= 40 words). "
            "Must include: wine name and winery, rating if available, and a short tasting description. "
            "Also include origin (region/country) when present. If description is missing, infer a natural tasting note from type, region, and common style. "
            "Do not mention missing data. No markup, no lists."
        )
        user = f"Attributes: {_json.dumps({k:v for k,v in fields.items() if v is not None})}"
        body = _json.dumps({
            "inputText": f"{system}\n\n{user}",
            "textGenerationConfig": {"maxTokenCount": 128, "temperature": 0.3, "topP": 0.9}
        })
        resp = client.invoke_model(modelId=BEDROCK_TEXT_MODEL_ID, body=body)
        payload = resp.get("body")
        if hasattr(payload, "read"):
            payload = payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = json.loads(payload) if isinstance(payload, str) else payload
        text = ""
        if isinstance(data, dict):
            if "results" in data and data["results"]:
                text = data["results"][0].get("outputText") or data["results"][0].get("text", "")
            elif "outputText" in data:
                text = data.get("outputText", "")
        if isinstance(text, str):
            return " ".join(text.strip().split())[:300]
        return ""
    except Exception as e:
        try:
            logger_util.error("Bedrock NLG summary failed", e)
        except Exception:
            pass
        return ""

def _fallback_summary(w: dict) -> str:
    parts = []
    name = w.get('name', 'This wine')
    winery = w.get('winery')
    rating = w.get('rating')
    region = w.get('region')
    country = w.get('country')
    desc = w.get('description')
    if winery:
        parts.append(f"{name} by {winery}.")
    else:
        parts.append(f"{name}.")
    loc = ", ".join([p for p in [region, country] if p])
    if loc:
        parts.append(f"From {loc}.")
    if rating is not None:
        parts.append(f"Rated {rating} out of 5.")
    if desc:
        parts.append(desc)
    return " ".join(parts)

# Concise summary for navigation responses (no tasting notes/description)
def _concise_summary_no_tasting(w: dict) -> str:
    parts = []
    name = w.get('name', 'This wine')
    winery = w.get('winery')
    rating = w.get('rating')
    region = w.get('region')
    country = w.get('country')
    if winery:
        parts.append(f"{name} by {winery}.")
    else:
        parts.append(f"{name}.")
    # Location: prefer region/state; avoid adding United States when region present
    loc = None
    if region and country:
        if str(country).lower() in ["united states", "usa", "u.s.a."]:
            loc = region
        else:
            # Keep both for non-US countries
            loc = f"{region}, {country}"
    elif region:
        loc = region
    elif country:
        loc = country
    if loc:
        parts.append(f"{loc}.")
    if rating is not None:
        parts.append(f"Rated {rating}.")
    return " ".join(parts)

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
        print("=== WINE SEARCH INTENT HANDLER TRIGGERED ===")
        
        try:
            # Get the semantic search term from slots with backward compatibility
            slots = handler_input.request_envelope.request.intent.slots
            print(f"[DEBUG] Raw slots: {slots}")
            # Prefer new 'Query' (AMAZON.SearchQuery) slot
            search_term = None
            if slots:
                if 'Query' in slots and getattr(slots['Query'], 'value', None):
                    search_term = slots['Query'].value
                elif 'Wine' in slots and getattr(slots['Wine'], 'value', None):
                    search_term = slots['Wine'].value
                elif 'WineType' in slots and getattr(slots['WineType'], 'value', None):
                    search_term = slots['WineType'].value
                elif 'Region' in slots and getattr(slots['Region'], 'value', None):
                    search_term = slots['Region'].value
                elif 'Winery' in slots and getattr(slots['Winery'], 'value', None):
                    search_term = slots['Winery'].value

            if not search_term:
                return (handler_input.response_builder
                        .speak("I didn't catch your request. Try asking something like, 'spicy red from Portugal' or 'best California Zinfandel'.")
                        .ask("What kind of wine are you looking for?")
                        .response)
            
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
            
            # Build single-shot summary for the first wine (no tasting notes)
            first = wines[0]
            summary = _concise_summary_no_tasting(first)
            if len(wines) == 1:
                lead = f"I found {first['name']}. "
            else:
                lead = f"I found {len(wines)} wines. First is {first['name']}. "
            speech_text = lead + summary
            return (handler_input.response_builder
                    .speak(speech_text)
                    .ask('Say next, previous, or search again.')
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
        # Support both legacy and new unified detail intent
        return (
            is_intent_name("wineActionDetailIntent")(handler_input) or
            is_intent_name("wineDetailIntent")(handler_input)
        )
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('WineActionDetailIntent received')
        
        try:
            intent = handler_input.request_envelope.request.intent
            action_result = slot_utils.get_action_from_intent(intent.to_dict())
            
            if not action_result['success']:
                logger_util.error('Failed to extract action from intent', action_result.get('error'))
                return (handler_input.response_builder
                        .speak('I didn\'t catch that. Say \"tell me more\", or say next, previous, or search again.')
                        .ask('Say next, previous, or search again.')
                        .response)
            
            action = action_result['value']
            wines = session_utils.get_wine_list(handler_input.attributes_manager)
            current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
            
            if not wines or current_index >= len(wines):
                return (handler_input.response_builder
                        .speak('Please search for a wine first.')
                        .response)
            
            current_wine = wines[current_index]
            
            # Legacy path retained for compatibility; not prompted anymore
            if action == config.DETAIL_TYPES['PRICE']:
                price_val = current_wine.get('price')
                if price_val is not None:
                    speech_text = f"The price of {current_wine['name']} is ${float(price_val):.2f}."
                else:
                    speech_text = f"I don't have a price for {current_wine['name']}."
            elif action == config.DETAIL_TYPES['RATING']:
                rating_val = current_wine.get('rating')
                if rating_val is not None:
                    speech_text = f"The rating of {current_wine['name']} is {rating_val} out of 5 stars."
                else:
                    speech_text = f"I don't have a rating for {current_wine['name']}."
            elif action == config.DETAIL_TYPES['LOCATION']:
                speech_text = f"{current_wine['name']} is from {current_wine.get('region', 'an unknown region')}, {current_wine.get('country', 'an unknown country')}."
            elif action == config.DETAIL_TYPES['DESCRIPTION']:
                speech_text = f"Here's the description of {current_wine['name']}: {current_wine.get('description', 'No description available.')}"
            else:
                speech_text = "I didn't catch that. Say 'tell me more', or say next, previous, or search again."

            # Optionally refine with Bedrock NLG for a more natural single-sentence response
            nlg_text = _generate_detail_with_bedrock(current_wine, action)
            if nlg_text:
                speech_text = nlg_text
            
            return (handler_input.response_builder
                    .speak(speech_text)
                    .ask('Say next, previous, or search again.')
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
        nlg = _generate_summary_with_bedrock(current_wine)
        summary = nlg or _fallback_summary(current_wine)
        speech_text = summary
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('Say next, previous, or search again.')
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
            current = wines[current_index]
            summary = _concise_summary_no_tasting(current)
            speech_text = f"You're already at the last wine. {summary}"
        else:
            new_index = current_index + 1
            session_utils.set_current_wine_index(handler_input.attributes_manager, new_index)
            current = wines[new_index]
            summary = _concise_summary_no_tasting(current)
            speech_text = f"Next: {summary}"
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('Say next, previous, or search again.')
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
            current = wines[0]
            summary = _concise_summary_no_tasting(current)
            speech_text = f"You're at the first wine. {summary}"
        else:
            new_index = current_index - 1
            session_utils.set_current_wine_index(handler_input.attributes_manager, new_index)
            current = wines[new_index]
            summary = _concise_summary_no_tasting(current)
            speech_text = f"Previous: {summary}"
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('Say next, previous, or search again.')
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
        # Do not provide a summary on start over per UX requirement
        speech_text = "Starting over."
        
        return (handler_input.response_builder
                .speak(speech_text)
                .ask('Say next, previous, or search again.')
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
