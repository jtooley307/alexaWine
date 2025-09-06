"""
APL utilities for Alexa Wine Skill
Provides helper functions to detect APL support and build directives using
branded theme tokens.
"""
from typing import Any, Dict, List, Optional
from ask_sdk_model.interfaces.alexa.presentation.apl import (
    RenderDocumentDirective, ExecuteCommandsDirective
)

# Brand theme tokens (derived from provided palette)
THEME = {
    "colors": {
        "bg_primary": "#114B5F",
        "accent": "#F2C14E",
        "surface": "#EFE7D1",
        "header": "#6A8F80",
        "badge": "#F2994A",
        "text": "#1F2937",
        "on_primary": "#FFFFFF",
        "divider": "#D6CFB8"
    },
    "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24},
    "radius": {"sm": 6, "md": 10, "lg": 14},
}


def supports_apl(handler_input) -> bool:
    try:
        interfaces = handler_input.request_envelope.context.system.device.supported_interfaces
        return getattr(interfaces, "alexa_presentation_apl", None) is not None
    except Exception:
        return False


def build_render_directive(document: Dict[str, Any], datasources: Dict[str, Any]) -> RenderDocumentDirective:
    return RenderDocumentDirective(token="wine-ui", document=document, datasources=datasources)


def list_datasource(items: List[Dict[str, Any]], title: str = "Wine Results") -> Dict[str, Any]:
    return {
        "theme": THEME,
        "listData": {
            "title": title,
            "items": items,
        },
    }


def detail_datasource(wine: Dict[str, Any]) -> Dict[str, Any]:
    # Create safe fields with fallbacks
    return {
        "theme": THEME,
        "detail": {
            "name": wine.get("name", "Unknown Wine"),
            "winery": wine.get("winery", "Unknown Winery"),
            "rating": wine.get("rating"),
            "price": wine.get("price"),
            "region": wine.get("region"),
            "country": wine.get("country"),
            "vintage": wine.get("vintage"),
            "description": wine.get("description", "No description available."),
            # Prefer explicit tasting notes field if present; otherwise fall back to description
            "tastingNotes": wine.get("tasting_notes") or wine.get("tastingNotes") or wine.get("description", "No tasting notes available."),
            "imageUrl": wine.get("image_url"),
        },
    }
