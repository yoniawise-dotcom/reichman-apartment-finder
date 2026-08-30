from __future__ import annotations
import re
from scoring import enrich

def parse_manual(raw: str) -> list[dict]:
    """Turn pasted Facebook/WhatsApp text into a searchable record. URLs are detected automatically."""
    raw = raw.strip()
    if not raw:
        return []
    urls = re.findall(r"https?://[^\s]+", raw)
    price_m = re.search(r"(?:₪|NIS|ש[\"׳']?ח)?\s*([\d,]{4,5})", raw, re.I)
    rooms_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:rooms?|חדר(?:ים)?)", raw, re.I)
    sqm_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:sqm|m2|m²|מ[\"״]?ר)", raw, re.I)
    low = raw.lower()
    row = {
        "source":"Manual/Facebook", "source_id":"", "url": urls[0] if urls else f"manual://{abs(hash(raw))}",
        "title": raw.splitlines()[0][:180], "address":"", "neighborhood":"Herzliya",
        "price": float(price_m.group(1).replace(',','')) if price_m else None,
        "rooms": float(rooms_m.group(1)) if rooms_m else None,
        "sqm": float(sqm_m.group(1)) if sqm_m else None,
        "renovated": int("renovated" in low or "משופ" in raw),
        "balcony": int("balcony" in low or "מרפסת" in raw),
        "mamad": int("mamad" in low or "ממ״ד" in raw or "ממד" in raw),
        "parking": int("parking" in low or "חניה" in raw),
        "elevator": int("elevator" in low or "מעלית" in raw),
        "furnished": int("furnished" in low or "מרוהט" in raw),
        "description": raw[:4000], "posted":"",
    }
    return [enrich(row)]
