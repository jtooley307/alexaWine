"""
Card utilities for Alexa Wine Skill
Builds Simple and Standard cards with optional images.
"""
from typing import Optional, Dict, Any
from ask_sdk_model.ui import SimpleCard, StandardCard, Image
from config import config

DEFAULT_TITLE = "Wine Assistant"


def build_simple_card(title: Optional[str], text: str) -> SimpleCard:
    return SimpleCard(title or DEFAULT_TITLE, text)


def build_standard_card(
    title: Optional[str],
    text: str,
    small_image_url: Optional[str] = None,
    large_image_url: Optional[str] = None,
):
    # Fallback to default logo if wine image URLs are not provided
    si = small_image_url
    li = large_image_url
    if (not si and not li) and getattr(config, 'CARD_LOGO_URL', ''):
        si = config.CARD_LOGO_URL
        li = config.CARD_LOGO_URL
    if si or li:
        img = Image(small_image_url=si, large_image_url=li)
        return StandardCard(title=title or DEFAULT_TITLE, text=text, image=img)
    return StandardCard(title=title or DEFAULT_TITLE, text=text)


def build_card_body(
    summary: str,
    notes: Optional[str] = None,
    footer: Optional[str] = None,
    wine: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a clean, readable text body for Standard cards.

    - First line: summary sentence(s)
    - Optional line: compact meta (Type • ABV)
    - Optional block: Winemaker's notes
    - Optional footer (next steps)
    """
    lines = []
    if summary:
        lines.append(summary.strip())

    # Compact meta line
    if wine:
        meta_parts = []
        type_ = wine.get('type')
        if isinstance(type_, str) and type_.strip():
            meta_parts.append(type_.strip())
        abv = wine.get('alcohol_content')
        if isinstance(abv, (int, float)):
            meta_parts.append(f"{abv}% ABV")
        elif isinstance(abv, str) and abv.strip():
            # try to normalize numeric strings, else include as-is
            sval = abv.strip().rstrip('%')
            try:
                val = float(sval)
                meta_parts.append(f"{val}% ABV")
            except Exception:
                meta_parts.append(abv.strip())
        if meta_parts:
            lines.append(" • ".join(meta_parts))

    # Notes block
    if isinstance(notes, str) and notes.strip():
        lines.append("")
        lines.append("Winemaker’s notes:")
        lines.append(notes.strip())

    if footer:
        lines.append("")
        lines.append(footer)

    return "\n".join(lines)
