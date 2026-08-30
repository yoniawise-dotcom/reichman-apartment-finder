# Reichman Apartment Finder

A deliberately tiny, free apartment hunter for finding a **whole apartment near Reichman University** and splitting it between roommates.

Target: roughly **₪2,000–3,000 per bedroom**, usually 4–6 Israeli rooms (3–5 bedrooms).

## Start today

```bash
git clone https://github.com/yoniawise-dotcom/reichman-apartment-finder.git
cd reichman-apartment-finder
bash start.sh
```

On first launch it creates a local Python environment, installs four small packages, and opens Streamlit in your browser.

## What works in V1

- Realta public Herzliya 4/5/6-room pages + details
- Optional direct Yad2 integration through `Guy2co/yad2-mcp`
- Janglo Netanya/Herzliya rentals (Herzliya + 4+ room filter)
- Best-effort Zipika public search
- Local SQLite database
- Automatic rent-per-bedroom calculation
- Simple quality/value score
- Filters for total rent, rooms, size, and price per bedroom
- Manual Facebook/WhatsApp/Telegram importer
- Tiny Chrome extension that copies visible login-only posts/listings
- Direct links to all sources so a website markup change never blocks apartment hunting

## Facebook/private groups

Chrome → `chrome://extensions` → enable **Developer mode** → **Load unpacked** → choose the `extension/` folder.

Then open a listing/post, click the extension, **Copy visible listing**, and paste it into the first tab of the app.

This intentionally reads only the page you already have open; it does not try to bypass Facebook access controls.

## Yad2

The finder keeps Yad2 optional because Yad2 has aggressive bot protection and its page behavior changes often.

To install the open-source MCP project we found:

```bash
bash setup_yad2.sh
```

That clones `Guy2co/yad2-mcp`, installs its Node dependencies, installs its Chromium browser, and builds it under `vendor/yad2-mcp`.

After installation, restart the app, tick **Yad2** under Refresh sources, and it calls `search_rentals` for Herzliya (city code 6400), 4–6 rooms, up to ₪15,000 and imports the results into SQLite.

## Why this is intentionally simple

The goal is to use it immediately, not spend days maintaining a scraping platform. Each source is isolated in `sources.py`. If a site's HTML changes, the other sources and manual importer continue working.

## Files

- `app.py` — entire UI
- `sources.py` — Realta/Janglo/Zipika collectors
- `yad2_client.py` — optional Yad2 MCP bridge
- `db.py` — SQLite
- `scoring.py` — simple transparent scoring
- `manual.py` — pasted private listing parser
- `extension/` — optional Chrome copier
- `setup_yad2.sh` — optional Yad2 MCP setup

## Important

Websites can change markup or block automated requests. This tool is best-effort and meant for personal apartment discovery. Respect each site's terms and access controls.
