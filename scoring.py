from __future__ import annotations

def enrich(row: dict) -> dict:
    rooms = float(row.get("rooms") or 0)
    bedrooms = max(1, int(rooms) - 1) if rooms >= 2 else 1
    price = float(row.get("price") or 0)
    ppb = round(price / bedrooms) if price else None
    row["bedrooms"] = bedrooms
    row["price_per_bedroom"] = ppb

    # V1 score: intentionally simple and transparent.
    score = 50.0
    if ppb:
        if 2000 <= ppb <= 2600: score += 25
        elif 2600 < ppb <= 3000: score += 15
        elif ppb < 2000: score += 18
        else: score -= min(25, (ppb - 3000) / 100)
    if row.get("renovated"): score += 8
    if row.get("balcony"): score += 5
    if row.get("mamad"): score += 5
    if row.get("parking"): score += 3
    if row.get("elevator"): score += 2
    if (row.get("sqm") or 0) >= 100: score += 5
    row["score"] = round(max(0, min(100, score)), 1)
    return row
