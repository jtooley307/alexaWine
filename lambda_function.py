# Curated region-to-terroir hints (lightweight, extend as needed)
TERROIR_HINTS = {
    'willamette valley': 'cool-climate red fruit, forest floor',
    'sonoma coast': 'coastal salinity and citrus zest',
    'russian river': 'fog-kissed acidity and ripe berry tones',
    'napa': 'plush ripe fruit with warm valley depth',
    'chablis': 'chalky limestone tension and saline drive',
    'sancerre': 'flinty minerality and bright citrus',
    'burgundy': 'earth, violets, and fine-grained tannins',
    'barolo': 'tar, roses, and firm tannins',
    'barbaresco': 'rose, red cherry, and polished tannins',
    'rioja': 'tempranillo spice with gentle American oak',
    'douro': 'schistous minerality and dark fruit',
    'vinho verde': 'lively acidity and slight spritz',
    'chianti': 'sangiovese cherry and savory herbs',
    'tuscany': 'sun-warmed fruit with Mediterranean herbs',
    'mosel': 'slatey minerality and crystalline acidity',
    'alsace': 'stone fruit purity with spice lift',
    'marlborough': 'gooseberry, passionfruit, and brisk acidity',
    'central otago': 'dark cherry and alpine herb freshness',
    'barossa': 'ripe blackberry and warm spice',
    'mclaren vale': 'plum richness with coastal freshness',
    'etna': 'volcanic ash, red citrus, and fine tannin',
    'priorat': 'licorella slate, dense fruit, and graphite',
}

def _terroir_hint(region: str | None, country: str | None) -> str:
    try:
        keyspace = []
        if region and isinstance(region, str):
            keyspace.append(region.lower())
        if country and isinstance(country, str):
            keyspace.append(country.lower())
        for key, hint in TERROIR_HINTS.items():
            for piece in keyspace:
                if key in piece:
                    return hint
        return ""
    except Exception:
        return ""

def _varietal_hint(grapes: str | None) -> str:
    try:
        if grapes and isinstance(grapes, str):
            grapes = grapes.lower()
            for key, hint in VARIETAL_HINTS.items():
                if key in grapes:
                    return hint
        return ""
    except Exception:
        return ""

# Lightweight extraction of pairing/meal terms from a search request
PAIRING_SYNONYMS = {
    'chicken': {'chicken', 'poultry'},
    'beef': {'beef', 'steak'},
    'fish': {'fish', 'seafood', 'white fish'},
    'salmon': {'salmon'},
    'pasta': {'pasta'},
    'cheese': {'cheese', 'cheeses'},
    'spicy': {'spicy', 'hot'},
}
MEAL_TYPES = {'dinner', 'lunch', 'brunch', 'dessert'}

PAIRING_BOOSTS = {
    'chicken': ['Chardonnay', 'Sauvignon Blanc', 'Rosé', 'Pinot Noir', 'Grenache'],
    'beef': ['Cabernet Sauvignon', 'Malbec', 'Syrah', 'Bordeaux', 'Zinfandel'],
    'fish': ['Sauvignon Blanc', 'Albariño', 'Chablis', 'Pinot Grigio', 'Champagne'],
    'salmon': ['Pinot Noir', 'Chardonnay'],
    'pasta': ['Chianti', 'Sangiovese', 'Barbera', 'Pinot Grigio'],
    'cheese': ['Chardonnay', 'Sauvignon Blanc', 'Chianti', 'Port'],
    'spicy': ['Riesling', 'Gewürztraminer', 'Zinfandel', 'Syrah'],
    'dessert': ['Moscato', 'Port', 'Sauternes', 'Late Harvest', 'Ice Wine', 'Sweet Riesling'],
}

def _extract_pairing_terms(intent_dict: dict) -> tuple[str | None, str | None]:
    """Return (food, meal_type) if detected from slots or utterance text."""
    try:
        slots = intent_dict.get('slots') or {}
        # collect slot values
        values = []
        for s in slots.values():
            v = (s or {}).get('value')
            if isinstance(v, str):
                values.append(v)
        # include name of intent (may include words) and any resolution values
        q = " ".join(values).lower()
    except Exception:
        q = ""
    # detect meal type
    meal = None
    for mt in MEAL_TYPES:
        if re.search(rf"\b{re.escape(mt)}\b", q):
            meal = mt
            break
    # detect food term
    food = None
    for key, syns in PAIRING_SYNONYMS.items():
        for s in syns:
            if re.search(rf"\b{re.escape(s)}\b", q):
                food = key
                break
        if food:
            break
    return food, meal

def _score_wine_for_pairing(wine: dict, food: str | None, meal: str | None) -> int:
    if not food and not meal:
        return 0
    text_fields = []
    for k in ('name', 'type', 'grapes', 'description', 'tasting_notes'):
        v = wine.get(k)
        if isinstance(v, str):
            text_fields.append(v.lower())
    pair_list = wine.get('pairings') or []
    if isinstance(pair_list, list):
        text_fields.extend([str(p).lower() for p in pair_list])
    text = " \n".join(text_fields)
    score = 0
    if food:
        boosts = PAIRING_BOOSTS.get(food, [])
        for b in boosts:
            if b.lower() in text:
                score += 2
        # direct food mention in pairings/notes
        if food in text:
            score += 3
    if meal == 'dessert':
        for b in PAIRING_BOOSTS.get('dessert', []):
            if b.lower() in text:
                score += 2
        if 'sweet' in text or 'dessert' in text:
            score += 1
    return score
"""
Alexa Wine Skill - Python Implementation
Modernized with ASK SDK for Python with all security and robustness improvements
"""

import os
import json
import re
import random
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler, AbstractRequestInterceptor
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard
from card_utils import build_standard_card, build_simple_card, build_card_body
from apl_utils import (
    supports_apl,
    build_render_directive,
    list_datasource,
    detail_datasource,
    THEME,
)

from config import config
from wine_service import WineService
from utils import logger_util, slot_utils, session_utils, ssml_escape

# ============================================================================
# Optional Bedrock NLG for natural combined responses
# ============================================================================
USE_BEDROCK_NLG = os.getenv("USE_BEDROCK_NLG", "false").lower() == "true"
BEDROCK_REGION = os.getenv("BEDROCK_REGION", os.getenv("AWS_REGION", "us-west-2"))
BEDROCK_TEXT_MODEL_ID = os.getenv("BEDROCK_TEXT_MODEL_ID", "amazon.titan-text-lite-v1")

# Standard next-step hints shown on cards
NEXT_STEPS = "Next: say 'tell me more', 'next', 'previous', or 'search again'."

def _generate_detail_with_bedrock(wine: dict, action: str) -> str:
    """Generate a concise, friendly response combining key attributes.
    Uses AWS Bedrock text generation if enabled. Returns empty string on failure.
    """
    if not USE_BEDROCK_NLG:
        logger_util.info('Bedrock NLG disabled via USE_BEDROCK_NLG=false')
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
        logger_util.info('Bedrock NLG request (detail)', {
            'model': BEDROCK_TEXT_MODEL_ID,
            'region': BEDROCK_REGION,
            'content_type': 'application/json'
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
                cand = data["results"][0]
                text = cand.get("outputText") or cand.get("text", "")
            elif "outputText" in data:
                text = data.get("outputText", "")
        if isinstance(text, str):
            cleaned = _clean_bedrock_text(text)[:300]
            if _is_bad_nlg(cleaned):
                return ""
            return cleaned
        return ""
    except Exception as e:
        try:
            logger_util.error("Bedrock NLG failed", e)
        except Exception:
            pass
        return ""

# Heuristic: identify placeholder tasting notes that are not user-friendly
def _is_placeholder_notes(note: str | None) -> bool:
    if not note:
        return True
    s = str(note).strip().lower()
    if not s or len(s) < 5:
        return True
    placeholders = {
        "assemblage/blend",
        "assemblage/portuguese white blend",
        "assemblage/portuguese red blend",
        "varietal/100%",
        "assemblage",
        "blend",
    }
    return s in placeholders

def _sanitize_notes(text: str | None) -> str:
    """Remove placeholder-like tokens and collapse whitespace."""
    if not text or not isinstance(text, str):
        return ""
    s = " ".join(text.strip().split())
    # Strip known placeholder fragments if they appear embedded
    for token in [
        "assemblage/blend",
        "assemblage/portuguese white blend",
        "assemblage/portuguese red blend",
        "varietal/100%",
        "assemblage",
        "blend",
    ]:
        s = s.replace(token, "").strip()
    # Remove any accidental double spaces produced by removal
    s = " ".join(s.split())
    return s

# Guardrails for Bedrock outputs: cleaner and bad-output detector
def _clean_bedrock_text(text: str) -> str:
    """Lightweight cleanup: collapse whitespace only (no guardrails)."""
    return " ".join(str(text).strip().split())

def _is_bad_nlg(text: str | None) -> bool:
    """Guardrails disabled by request: never block model output here."""
    return False

# Build the correct Bedrock request body for the configured model
def _bedrock_text_body(prompt: str, max_tokens: int = 256, temperature: float = 0.5, top_p: float = 0.9) -> tuple[str, dict]:
    """Return (content_type, body_dict) for bedrock-runtime.invoke_model based on model id.
    - Anthropic Claude 3 models expect the Messages API schema.
    - Amazon Titan text models expect inputText + textGenerationConfig.
    """
    mid = (BEDROCK_TEXT_MODEL_ID or "").lower()
    if mid.startswith("anthropic."):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ],
                }
            ],
        }
        return "application/json", body

# Try to extract a vineyard hint from the wine's name, e.g., "XYZ Vineyard"
def _extract_vineyard_hint(name: str | None) -> str:
    try:
        if not name or not isinstance(name, str):
            return ""
        import re as _re
        m = _re.search(r"\b([A-Za-z][\w'\-]*(?:\s+[A-Za-z][\w'\-]*)*)\s+Vineyard\b", name, _re.IGNORECASE)
        if m:
            # Return with capital V Vineyard suffix normalized
            core = m.group(1).strip()
            return f"{core} Vineyard"
        return ""
    except Exception:
        return ""
    # Default: Titan text
    body = {
        "inputText": prompt,
        "textGenerationConfig": {
            "temperature": temperature,
            "topP": top_p,
            "maxTokenCount": max_tokens,
        },
    }
    return "application/json", body

# Simple heuristic fallback tasting notes when Bedrock is unavailable or filtered
def _heuristic_tasting_notes(wine: dict) -> str:
    """Lightweight fallback tasting note with no generic pairing line."""
    wtype = (wine.get('type') or '').lower()
    if 'red' in wtype:
        base = "Ripe berry and plum, gentle spice, and soft tannins"
    elif 'ros' in wtype or 'rose' in wtype:
        base = "Fresh strawberry and melon with a crisp, dry finish"
    elif 'sparkling' in wtype or 'champagne' in wtype:
        base = "Bright citrus and green apple, lively bubbles, clean finish"
    else:  # white or unknown
        base = "Citrus and green apple with a refreshing, clean finish"
    # Do not append region/country here; summary already conveys origin
    return base + "."

# Generate a concise winemaker-style tasting notes string with Bedrock
def _generate_tasting_notes_with_bedrock(wine: dict) -> str:
    """Return a short, polished tasting-notes string using Bedrock NLG.
    Falls back to empty string on failure or when USE_BEDROCK_NLG is false.
    """
    if not USE_BEDROCK_NLG:
        logger_util.info('Bedrock NLG disabled via USE_BEDROCK_NLG=false')
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
            "grapes": wine.get("grapes"),
            "description": wine.get("description"),
        }
        # Vineyard hint (from explicit field or parsed from name)
        vineyard = wine.get('vineyard') or _extract_vineyard_hint(wine.get('name'))
        terroir = _terroir_hint(fields.get('region'), fields.get('country'))
        varietal = _varietal_hint(fields.get('type'), fields.get('grapes'))
        # Build human-readable wine details list for the prompt
        def _fmt(v):
            if v is None:
                return ""
            if isinstance(v, (list, tuple)):
                return ", ".join(str(x) for x in v if x)
            return str(v)
        details = (
            f"- Name: {_fmt(fields.get('name'))}\n"
            f"- Type: {_fmt(fields.get('type'))}\n"
            f"- Winery: {_fmt(fields.get('winery'))}\n"
            f"- Region: {_fmt(fields.get('region'))}\n"
            f"- Country: {_fmt(fields.get('country'))}\n"
            f"- Alcohol content: {_fmt(wine.get('alcohol_content'))}\n"
            f"- Vineyard: {_fmt(vineyard)}\n"
            f"- Terroir_hint: {_fmt(terroir)}\n"
            f"- Varietal_hint: {_fmt(varietal)}\n"
            f"- Description: {_fmt(fields.get('description'))}\n"
            f"- Tasting_notes: {_fmt(wine.get('tasting_notes'))}\n"
            f"- Pairings: {_fmt(wine.get('pairings'))}"
        )

        # Prompt: single-paragraph, 1–3 sentence winery-style tasting notes, concise and professional
        title = " ".join([p for p in [fields.get('winery') or '', fields.get('name') or ''] if p]).strip() or (fields.get('name') or fields.get('winery') or 'This wine')
        place = fields.get('region') or fields.get('country') or ''
        system = (
            "You are a winemaker writing concise tasting notes. Use professional wine terminology and keep it accessible. "
            "Avoid flowery exaggeration. 1–3 sentences. Output a single paragraph with no line breaks."
        )
        # Keep our hints but in a compact instruction
        user = (
            f"Write winemaker-style tasting notes for the wine: {title}. "
            + (f"Region: {place}. " if place else "")
            + "Mention appearance, aroma, palate, and finish succinctly. "
              "If provided, subtly weave vineyard personality, terroir and varietal cues, and use the vintage to hint at ripeness/structure. "
              "Avoid placeholder terms (e.g., 'Assemblage/Blend') and raw field labels."
        )
        prompt = f"System: {system}\n\nUser: {user}\n\nWine details:\n{details}\n\nOutput: 1–3 sentences in one paragraph, authentic winemaker style."
        ctype, body_obj = _bedrock_text_body(prompt, max_tokens=220, temperature=0.5, top_p=0.9)
        logger_util.info('Bedrock NLG request (tasting_notes)', {
            'model': BEDROCK_TEXT_MODEL_ID,
            'region': BEDROCK_REGION,
            'content_type': ctype
        })
        print(f"=== BEDROCK TASTING NOTES CALL model={BEDROCK_TEXT_MODEL_ID} region={BEDROCK_REGION}")
        resp = client.invoke_model(
            modelId=BEDROCK_TEXT_MODEL_ID,
            body=_json.dumps(body_obj),
            contentType=ctype,
            accept="application/json",
        )
        payload = resp.get("body")
        if hasattr(payload, "read"):
            payload = payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = _json.loads(payload)
        text = ""
        if isinstance(data, dict):
            # Anthropic Messages API: content is a list of {type: 'text', text: '...'} chunks
            if isinstance(data.get("content"), list):
                for chunk in data["content"]:
                    if isinstance(chunk, dict) and chunk.get("type") in ("text", "output_text"):
                        text += str(chunk.get("text", "")) + " "
                text = text.strip()
            # Titan-style outputs
            if not text:
                if "results" in data and data["results"]:
                    text = data["results"][0].get("outputText") or data["results"][0].get("text", "")
                elif "outputText" in data:
                    text = data.get("outputText", "")
        if isinstance(text, str):
            cleaned = _clean_bedrock_text(text)[:500]
            if _is_bad_nlg(cleaned):
                return ""
            # If too short, retry once with slightly higher temperature to encourage richness
            if len(cleaned) < 60:
                print("=== BEDROCK TASTING NOTES SHORT; RETRYING WITH TEMPERATURE 0.7 ===")
                ctype2, body_obj2 = _bedrock_text_body(prompt, max_tokens=240, temperature=0.7, top_p=0.9)
                resp2 = client.invoke_model(
                    modelId=BEDROCK_TEXT_MODEL_ID,
                    body=_json.dumps(body_obj2),
                    contentType=ctype2,
                    accept="application/json",
                )
                payload2 = resp2.get("body")
                if hasattr(payload2, "read"):
                    payload2 = payload2.read()
                if isinstance(payload2, (bytes, bytearray)):
                    payload2 = payload2.decode("utf-8")
                data2 = _json.loads(payload2)
                text2 = ""
                if isinstance(data2, dict):
                    if isinstance(data2.get("content"), list):
                        for chunk in data2["content"]:
                            if isinstance(chunk, dict) and chunk.get("type") in ("text", "output_text"):
                                text2 += str(chunk.get("text", "")) + " "
                        text2 = text2.strip()
                    if not text2:
                        if "results" in data2 and data2["results"]:
                            text2 = data2["results"][0].get("outputText") or data2["results"][0].get("text", "")
                        elif "outputText" in data2:
                            text2 = data2.get("outputText", "")
                cleaned2 = _clean_bedrock_text(text2)[:500] if isinstance(text2, str) else ""
                if cleaned2 and not _is_bad_nlg(cleaned2):
                    print("=== BEDROCK TASTING NOTES RETRY OK ===")
                    return cleaned2
                print("=== BEDROCK TASTING NOTES RETRY EMPTY OR BAD; USING FIRST CLEANED ===")
            else:
                print("=== BEDROCK TASTING NOTES OK")
            return cleaned
        return ""
    except Exception as e:
        try:
            logger_util.error("Bedrock tasting notes failed", e)
        except Exception:
            pass
        print(f"=== BEDROCK TASTING NOTES ERROR: {e}")
        return ""

# New: summary generator that combines winery, rating, location, and description
def _generate_summary_with_bedrock(wine: dict) -> str:
    if not USE_BEDROCK_NLG:
        logger_util.info('Bedrock NLG disabled via USE_BEDROCK_NLG=false')
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
            "Write a concise, natural 1–2 sentence wine summary suitable for speech (<= 40 words). "
            "Include: wine name and winery; rating if available; origin (region/country) when present; and a short tasting cue. "
            "No preamble, no roles, no apologies, no instructions, no lists, no markup, and do not repeat field labels."
        )
        user = f"User: Wine details: {_json.dumps({k:v for k,v in fields.items() if v is not None})}"
        ctype, body_obj = _bedrock_text_body(f"{system}\n\n{user}", max_tokens=128, temperature=0.3, top_p=0.9)
        logger_util.info('Bedrock NLG request (summary)', {
            'model': BEDROCK_TEXT_MODEL_ID,
            'region': BEDROCK_REGION,
            'content_type': ctype
        })
        print(f"=== BEDROCK SUMMARY CALL model={BEDROCK_TEXT_MODEL_ID} region={BEDROCK_REGION}")
        resp = client.invoke_model(
            modelId=BEDROCK_TEXT_MODEL_ID,
            body=_json.dumps(body_obj),
            contentType=ctype,
            accept="application/json",
        )
        payload = resp.get("body")
        if hasattr(payload, "read"):
            payload = payload.read()
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8")
        data = json.loads(payload) if isinstance(payload, str) else payload
        text = ""
        if isinstance(data, dict):
            # Anthropic Messages API: content chunks
            if isinstance(data.get("content"), list):
                for chunk in data["content"]:
                    if isinstance(chunk, dict) and chunk.get("type") in ("text", "output_text"):
                        text += str(chunk.get("text", "")) + " "
                text = text.strip()
            # Titan-style outputs
            if not text:
                if "results" in data and data["results"]:
                    text = data["results"][0].get("outputText") or data["results"][0].get("text", "")
                elif "outputText" in data:
                    text = data.get("outputText", "")
        if isinstance(text, str):
            cleaned = _clean_bedrock_text(text)[:500]
            if _is_bad_nlg(cleaned):
                return ""
            print("=== BEDROCK SUMMARY OK")
            return cleaned
        return ""
    except Exception as e:
        try:
            logger_util.error("Bedrock NLG summary failed", e)
        except Exception:
            pass
        print(f"=== BEDROCK SUMMARY ERROR: {e}")
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
        clean_desc = _sanitize_notes(desc)
        if clean_desc and not _is_placeholder_notes(clean_desc):
            parts.append(clean_desc)
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
        
        # APL welcome/empty screen if device supports APL
        try:
            if supports_apl(handler_input):
                base_dir = os.path.dirname(__file__)
                with open(os.path.join(base_dir, 'apl', 'empty.json'), 'r', encoding='utf-8') as f:
                    document = json.load(f)
                datasources = {"theme": THEME}
                handler_input.response_builder.add_directive(
                    build_render_directive(document, datasources)
                )
        except Exception as e:
            logger_util.error('Failed to render APL welcome', e)

        return (handler_input.response_builder
                .speak(ssml_escape(config.MESSAGES['welcome']))
                .ask(config.MESSAGES['welcome_reprompt'])
                .set_card(build_standard_card(
                    config.ALEXA_CARD_TITLE,
                    f"{config.MESSAGES['welcome']}\n\n{config.MESSAGES['welcome_reprompt']}"
                ))
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
            # Extract pairing context (food/meal) for re-ranking and APL title
            try:
                intent_dict = handler_input.request_envelope.request.intent.to_dict()
                food, meal = _extract_pairing_terms(intent_dict)
            except Exception:
                food, meal = None, None
            
            # Search for wines using the wine service
            wines = wine_service.search_wines(search_term)
            # If pairing context present, re-rank results to surface better matches
            if wines and (food or meal):
                scored = [(w, _score_wine_for_pairing(w, food, meal)) for w in wines]
                scores = [s for _, s in scored]
                if any(s > 0 for s in scores):
                    wines = [w for w, _ in sorted(scored, key=lambda t: t[1], reverse=True)]
                else:
                    # All ties (e.g., score 0): randomly sample from the highest relevance tier
                    # 1) Determine highest _relevance among results
                    rels = [float(w.get('_relevance', 0.0) or 0.0) for w in wines]
                    max_rel = max(rels) if rels else 0.0
                    tol = 1e-6
                    top_group = [w for w in wines if abs(float(w.get('_relevance', 0.0) or 0.0) - max_rel) < tol]
                    pick = min(5, len(top_group) if top_group else len(wines))
                    chosen = random.sample(top_group if top_group else wines, k=pick)
                    # 2) If fewer than 5 chosen, top-up from next relevance tiers in order
                    if pick < 5:
                        # Sort remaining by _relevance desc, keep those not already chosen
                        remaining = [w for w in wines if w not in chosen]
                        remaining.sort(key=lambda x: float(x.get('_relevance', 0.0) or 0.0), reverse=True)
                        for w in remaining:
                            if len(chosen) >= 5:
                                break
                            chosen.append(w)
                    wines = chosen
            
            if not wines:
                return (handler_input.response_builder
                        .speak(ssml_escape(config.MESSAGES['wine_not_found']))
                        .set_card(build_standard_card(
                            config.ALEXA_CARD_TITLE,
                            f"{config.MESSAGES['wine_not_found']}\n\nTry: find Napa Cabernet 2018, or say 'search again'."
                        ))
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
            # Add APL list when supported
            try:
                if supports_apl(handler_input):
                    base_dir = os.path.dirname(__file__)
                    with open(os.path.join(base_dir, 'apl', 'list.json'), 'r', encoding='utf-8') as f:
                        document = json.load(f)
                    # Map wines to APL items
                    items = []
                    for w in wines:
                        items.append({
                            "name": w.get('name'),
                            "winery": w.get('winery'),
                            "rating": w.get('rating'),
                            "imageUrl": w.get('image_url')
                        })
                    list_title = "Wine Results"
                    if food or meal:
                        list_title = f"Wine Pairings for {food or meal}"
                    datasources = list_datasource(items, title=list_title)
                    handler_input.response_builder.add_directive(
                        build_render_directive(document, datasources)
                    )
            except Exception as e:
                logger_util.error('Failed to render APL list', e)

            # Initial card: keep concise; do NOT include winemaker notes here
            logger_util.info('Initial card: tasting notes omitted')
            card_text = build_card_body(
                summary=speech_text,
                notes=None,
                footer=NEXT_STEPS,
                wine=wines[0]
            )

            return (handler_input.response_builder
                    .speak(ssml_escape(speech_text))
                    .ask('Say next, previous, or search again.')
                    .set_card(build_standard_card(
                        config.ALEXA_CARD_TITLE,
                        card_text
                    ))
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
        print("=== WINE ACTION DETAIL INTENT HANDLER TRIGGERED ===")
        
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
            effective_wine = dict(current_wine)
            
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

            # Determine which details to speak based on action
            if action in ['price', 'rating', 'location', 'description']:
                detail_text = wine_service.get_detail_text(effective_wine, action)
            else:
                detail_text = _generate_detail_with_bedrock(effective_wine, action) or _fallback_summary(effective_wine)

            speech_text = detail_text

            # APL detail when supported
            try:
                if supports_apl(handler_input):
                    base_dir = os.path.dirname(__file__)
                    with open(os.path.join(base_dir, 'apl', 'detail.json'), 'r', encoding='utf-8') as f:
                        document = json.load(f)
                    datasources = detail_datasource(effective_wine)
                    handler_input.response_builder.add_directive(
                        build_render_directive(document, datasources)
                    )
            except Exception as e:
                logger_util.error('Failed to render APL detail', e)

            # Build card text (prefer Bedrock tasting notes; then heuristic; lastly existing)
            img = effective_wine.get('image_url')
            existing_tn = effective_wine.get('tasting_notes')
            if _is_placeholder_notes(existing_tn):
                existing_tn = ""
            tn_source = 'bedrock'
            # 1) Try Bedrock first
            try:
                tn_gen = _generate_tasting_notes_with_bedrock(effective_wine)
            except Exception:
                tn_gen = ""
            if isinstance(tn_gen, str) and tn_gen.strip() and not _is_placeholder_notes(tn_gen):
                tn_final = _sanitize_notes(tn_gen)
                tn_source = 'bedrock'
            else:
                # 2) Heuristic fallback
                tn_final = _heuristic_tasting_notes(effective_wine)
                tn_source = 'heuristic'
                # 3) As a last resort, use existing notes if non-empty and not placeholder
                if not tn_final and isinstance(existing_tn, str) and existing_tn.strip():
                    tn_final = _sanitize_notes(existing_tn)
                    tn_source = 'existing'
            logger_util.info('Detail card tasting notes', {
                'wine': effective_wine.get('name'),
                'source': tn_source
            })
            card_text = build_card_body(
                summary=speech_text,
                notes=_sanitize_notes(tn_final) if tn_final else None,
                footer=NEXT_STEPS,
                wine=effective_wine
            )
            
            return (handler_input.response_builder
                .speak(ssml_escape(speech_text))
                .ask(ssml_escape('Say next, previous, or search again.'))
                .set_card(build_standard_card(
                    config.ALEXA_CARD_TITLE,
                    card_text,
                    small_image_url=img,
                    large_image_url=img
                ))
                .response)
        
        except Exception as error:
            logger_util.error('Error in WineActionDetailIntent', error)
            return (handler_input.response_builder
                    .speak(ssml_escape(config.MESSAGES['general_error']))
                    .response)

class GetWineDetailsIntentHandler(AbstractRequestHandler):
    """Get Wine Details Intent Handler - Ask what details user wants"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("getWineDetailsIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('GetWineDetailsIntent received')
        print("=== GET WINE DETAILS INTENT HANDLER TRIGGERED ===")
        
        wines = session_utils.get_wine_list(handler_input.attributes_manager)
        current_index = session_utils.get_current_wine_index(handler_input.attributes_manager)
        
        if not wines or current_index >= len(wines):
            return (handler_input.response_builder
                .speak(ssml_escape('Please search for a wine first.'))
                .response)
        
        current_wine = wines[current_index]
        # Start with a shallow copy; we'll compute tasting notes later (prefer Bedrock) once
        effective_wine = dict(current_wine)
        nlg = _generate_summary_with_bedrock(effective_wine)
        summary = nlg or _fallback_summary(effective_wine)
        speech_text = summary

        # Render APL detail view if available
        try:
            if supports_apl(handler_input):
                base_dir = os.path.dirname(__file__)
                with open(os.path.join(base_dir, 'apl', 'detail.json'), 'r', encoding='utf-8') as f:
                    document = json.load(f)
                datasources = detail_datasource(effective_wine)
                handler_input.response_builder.add_directive(
                    build_render_directive(document, datasources)
                )
        except Exception as e:
            logger_util.error('Failed to render APL detail (GetWineDetails)', e)

        # Build card text (prefer Bedrock tasting notes; fallback to existing then heuristic)
        img = effective_wine.get('image_url')
        existing_tn = effective_wine.get('tasting_notes')
        if _is_placeholder_notes(existing_tn):
            existing_tn = ""
        tn_source = 'bedrock'
        # 1) Try Bedrock first
        try:
            tn_gen = _generate_tasting_notes_with_bedrock(effective_wine)
        except Exception:
            tn_gen = ""
        if isinstance(tn_gen, str) and tn_gen.strip() and not _is_placeholder_notes(tn_gen):
            tn_final = tn_gen.strip()
            tn_source = 'bedrock'
        else:
            # 2) Heuristic fallback
            tn_final = _heuristic_tasting_notes(effective_wine)
            tn_source = 'heuristic'
            # 3) As a last resort, use existing notes if non-empty and not placeholder
            if not tn_final and isinstance(existing_tn, str) and existing_tn.strip():
                tn_final = _sanitize_notes(existing_tn)
                tn_source = 'existing'
        logger_util.info('GetWineDetails card tasting notes', {
            'wine': effective_wine.get('name'),
            'source': tn_source
        })
        card_text = build_card_body(
            summary=summary,
            notes=_sanitize_notes(tn_final) if tn_final else None,
            footer=NEXT_STEPS,
            wine=effective_wine
        )
        
        return (handler_input.response_builder
            .speak(ssml_escape(speech_text))
            .ask(ssml_escape('Say next, previous, or search again.'))
            .set_card(build_standard_card(
                config.ALEXA_CARD_TITLE,
                card_text,
                small_image_url=img,
                large_image_url=img
            ))
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
                .speak(ssml_escape(config.MESSAGES['help']))
                .ask(config.MESSAGES['help'])
                .set_card(build_standard_card(
                    config.ALEXA_CARD_TITLE,
                    f"{config.MESSAGES['help']}\n\n{NEXT_STEPS}"
                ))
                .response)

class CancelAndStopIntentHandler(AbstractRequestHandler):
    """Cancel and Stop Intent Handler"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        logger_util.info('CancelAndStopIntent received')
        
        return (handler_input.response_builder
                .speak(ssml_escape(config.MESSAGES['goodbye']))
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
                .speak(ssml_escape(config.MESSAGES['general_error']))
                .ask('What would you like to do?')
                .response)

# ============================================================================
# SKILL BUILDER
# ============================================================================

# Create skill builder
sb = SkillBuilder()

class RequestLogInterceptor(AbstractRequestInterceptor):
    """Logs every incoming request's type and intent (if applicable)."""
    def process(self, handler_input: HandlerInput) -> None:
        try:
            req = handler_input.request_envelope.request
            rtype = type(req).__name__
            payload = {'type': rtype}
            # IntentRequest has 'intent' attribute
            intent = getattr(req, 'intent', None)
            if intent is not None and hasattr(intent, 'name'):
                payload['intent'] = intent.name
            logger_util.info('Incoming request', payload)
        except Exception as e:
            logger_util.error('RequestLogInterceptor failure', e)

# Varietal-to-signature cues (extendable)
VARIETAL_HINTS = {
    'cabernet sauvignon': 'cassis, blackberry, graphite, cedar, firm tannins',
    'pinot noir': 'red cherry, rose petals, forest floor, silky tannins',
    'chardonnay': 'apple, citrus, stone fruit; texture from lees or oak when present',
    'syrah': 'blackberry, black pepper, olive tapenade, smoked meat',
    'zinfandel': 'brambly berry, black pepper, warm spices',
    'sauvignon blanc': 'gooseberry, citrus zest, fresh herbs, brisk acidity',
    'merlot': 'plum, cocoa, soft tannins, supple mid-palate',
    'malbec': 'violet, dark plum, cocoa-dusted tannins',
    'riesling': 'lime, white peach, slatey minerality; vibrant acidity',
    'grenache': 'red raspberry, white pepper, Mediterranean herbs',
    'sangiovese': 'maraschino cherry, dried herbs, sanguine tannins',
    'tempranillo': 'red cherry, tobacco leaf, gentle spice',
    'nebbiolo': 'tar and roses, red cherry, firm tannins',
    'red blend': 'ripe red and black berries, baking spices, supple tannins',
    'blend': 'mixed-berry fruit, spice accents, rounded tannins'
}

def _varietal_hint(wtype: str | None, grapes: str | list | None) -> str:
    try:
        keys = []
        if isinstance(wtype, str):
            keys.append(wtype.lower())
        if isinstance(grapes, list):
            keys.extend([str(g).lower() for g in grapes])
        elif isinstance(grapes, str):
            keys.extend([g.strip().lower() for g in grapes.split(',')])
        for k in keys:
            for vkey, hint in VARIETAL_HINTS.items():
                if vkey in k:
                    return hint
        return ""
    except Exception:
        return ""

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

# Global request interceptor for visibility in logs
sb.add_global_request_interceptor(RequestLogInterceptor())

# Add exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Set skill ID
sb.skill_id = config.ALEXA_SKILL_ID

# Lambda handler
lambda_handler = sb.lambda_handler()
