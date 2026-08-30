from __future__ import annotations
import re
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from scoring import enrich
from yad2_client import scrape_yad2

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}
TIMEOUT = 20

def _get(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def _num(text: str | None) -> float | None:
    if not text: return None
    m = re.search(r"([\d,.]+)", text.replace("\u202f", ""))
    return float(m.group(1).replace(",", "")) if m else None

def _flag(text: str, *words: str) -> int:
    low = text.lower()
    return int(any(w.lower() in low for w in words))

def scrape_realta(max_detail: int = 100) -> list[dict]:
    """Scrape Realta's public Herzliya 4/5/6-room pages + detail pages."""
    detail_urls: list[str] = []
    for rooms in (4, 5, 6):
        url = f"https://realta.co.il/en/herzliya/{rooms}-rooms/"
        soup = _get(url)
        for a in soup.select("a[href]"):
            href = urljoin(url, a.get("href", ""))
            if re.search(r"realta\.co\.il/en/herzliya/[^/]+/\d+/?$", href):
                if href not in detail_urls: detail_urls.append(href)
    rows: list[dict] = []
    for url in detail_urls[:max_detail]:
        try:
            soup = _get(url)
            text = " ".join(soup.stripped_strings)
            title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "Realta listing"
            price_m = re.search(r"([\d,\u202f]+)\s*/\s*per month", text, re.I)
            rooms_m = re.search(r"(\d+(?:\.\d+)?)\s*rooms", text, re.I)
            sqm_m = re.search(r"(\d+(?:\.\d+)?)\s*sqm", text, re.I)
            address = title.split(" - ", 1)[1] if " - " in title else title
            h1 = soup.find("h1")
            neighborhood = ""
            if h1:
                nxt = h1.find_next()
                neighborhood = nxt.get_text(" ", strip=True) if nxt else ""
            row = {
                "source": "Realta", "source_id": url.rstrip("/").split("/")[-1], "url": url,
                "title": title, "address": address, "neighborhood": neighborhood,
                "price": _num(price_m.group(1)) if price_m else None,
                "rooms": _num(rooms_m.group(1)) if rooms_m else None,
                "sqm": _num(sqm_m.group(1)) if sqm_m else None,
                "renovated": _flag(text, "Renovated"), "balcony": _flag(text, "Balcony"),
                "mamad": _flag(text, "Safe Room", "Mamad"), "parking": _flag(text, "Parking"),
                "elevator": _flag(text, "Elevator"), "furnished": _flag(text, "Furnished"),
                "description": text[:4000], "posted": "",
            }
            rows.append(enrich(row))
            time.sleep(0.05)
        except Exception:
            continue
    return rows

def scrape_janglo(max_pages: int = 2) -> list[dict]:
    """Scrape Janglo Netanya/Herzliya results, keeping Herzliya listings only."""
    rows: list[dict] = []
    detail_urls: list[str] = []
    for page in range(max_pages):
        url = "https://www.janglo.net/real-estate-rentals/nh" + (f"?page={page}" if page else "")
        soup = _get(url)
        for a in soup.select('a[href*="/item/"]'):
            href = urljoin(url, a.get("href", ""))
            if href not in detail_urls: detail_urls.append(href)
    for url in detail_urls:
        try:
            soup = _get(url)
            text = " ".join(soup.stripped_strings)
            if "herzli" not in text.lower() and "hertzli" not in text.lower():
                continue
            title = soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "Janglo listing"
            price_m = re.search(r"([\d,]+)\s*NIS", text, re.I)
            rooms_m = re.search(r"(\d+(?:\.\d+)?)\s*Rooms", text, re.I)
            sqm_m = re.search(r"(\d+(?:\.\d+)?)\s*m[²2]", text, re.I)
            row = {
                "source": "Janglo", "source_id": url.rstrip("/").split("/")[-1], "url": url,
                "title": title, "address": "", "neighborhood": "Herzliya",
                "price": _num(price_m.group(1)) if price_m else None,
                "rooms": _num(rooms_m.group(1)) if rooms_m else None,
                "sqm": _num(sqm_m.group(1)) if sqm_m else None,
                "renovated": _flag(text, "renovated", "newly renovated"), "balcony": _flag(text, "balcony"),
                "mamad": _flag(text, "mamad", "shelter room", "safe room"), "parking": _flag(text, "parking"),
                "elevator": _flag(text, "elevator"), "furnished": _flag(text, "furnished"),
                "description": text[:4000], "posted": "",
            }
            if (row["rooms"] or 0) >= 4:
                rows.append(enrich(row))
        except Exception:
            continue
    return rows

def scrape_zipika() -> list[dict]:
    """Best-effort public Zipika search scraper. If markup changes, use manual import in the app."""
    url = "https://zipika.com/property-search"
    soup = _get(url)
    rows: list[dict] = []
    seen = set()
    for a in soup.select("a[href]"):
        href = urljoin(url, a.get("href", ""))
        label = " ".join(a.stripped_strings)
        if "herzli" not in label.lower() and "הרצל" not in label:
            continue
        if href in seen: continue
        seen.add(href)
        price_m = re.search(r"(?:₪|NIS)?\s*([\d,]{4,})", label, re.I)
        rooms_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:rooms|חדר)", label, re.I)
        row = {
            "source":"Zipika", "source_id": href.rstrip("/").split("/")[-1], "url":href,
            "title": label[:180] or "Zipika listing", "address":"", "neighborhood":"Herzliya",
            "price": _num(price_m.group(1)) if price_m else None,
            "rooms": _num(rooms_m.group(1)) if rooms_m else None, "sqm":None,
            "renovated":_flag(label,"renovated","משופצת"), "balcony":_flag(label,"balcony","מרפסת"),
            "mamad":_flag(label,"mamad","ממ״ד","ממד"), "parking":_flag(label,"parking","חניה"),
            "elevator":_flag(label,"elevator","מעלית"), "furnished":_flag(label,"furnished","מרוהט"),
            "description":label, "posted":"",
        }
        if not row["rooms"] or row["rooms"] >= 4:
            rows.append(enrich(row))
    return rows

SOURCES = {"Realta": scrape_realta, "Yad2": scrape_yad2, "Janglo": scrape_janglo, "Zipika": scrape_zipika}
