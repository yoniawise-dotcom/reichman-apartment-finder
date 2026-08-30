from __future__ import annotations
import json
import re
import select
import subprocess
from pathlib import Path
from scoring import enrich

ROOT = Path(__file__).parent
SERVER = ROOT / "vendor" / "yad2-mcp" / "dist" / "index.js"

class MCPClient:
    def __init__(self):
        if not SERVER.exists():
            raise RuntimeError("Yad2 MCP is not installed. Run bash setup_yad2.sh once.")
        self.p = subprocess.Popen(
            ["node", str(SERVER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self.next_id = 1
        self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "reichman-apartment-finder", "version": "0.1.0"},
        }, timeout=45)
        self._send({"jsonrpc":"2.0", "method":"notifications/initialized", "params":{}})

    def _send(self, obj: dict) -> None:
        assert self.p.stdin is not None
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def _request(self, method: str, params: dict, timeout: int = 90) -> dict:
        rid = self.next_id; self.next_id += 1
        self._send({"jsonrpc":"2.0", "id":rid, "method":method, "params":params})
        assert self.p.stdout is not None
        while True:
            ready, _, _ = select.select([self.p.stdout], [], [], timeout)
            if not ready:
                raise TimeoutError(f"Yad2 MCP timed out during {method}")
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("Yad2 MCP stopped unexpectedly")
            msg = json.loads(line)
            if msg.get("id") != rid:
                continue
            if "error" in msg:
                raise RuntimeError(str(msg["error"]))
            return msg.get("result", {})

    def call_tool(self, name: str, arguments: dict) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments}, timeout=120)
        parts = result.get("content", [])
        return "\n".join(p.get("text", "") for p in parts if p.get("type") == "text")

    def close(self) -> None:
        if self.p.poll() is None:
            self.p.terminate()

def _value(block: str, name: str) -> str:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", block)
    return m.group(1).strip() if m else ""

def parse_yad2_markdown(text: str) -> list[dict]:
    rows = []
    blocks = re.split(r"(?=^###\s)", text, flags=re.M)
    for block in blocks:
        if not block.startswith("### "):
            continue
        title = block.splitlines()[0][4:].strip()
        price_m = re.search(r"\*\*Price:\*\*\s*₪([\d,]+)", block)
        details = _value(block, "Details")
        rooms_m = re.search(r"(\d+(?:\.\d+)?)\s*rooms", details)
        sqm_m = re.search(r"(\d+(?:\.\d+)?)m²", details)
        url = _value(block, "URL")
        token = _value(block, "Token")
        desc = _value(block, "Description")
        addr = _value(block, "Address")
        low = (title + " " + desc).lower()
        row = {
            "source":"Yad2", "source_id":token, "url":url or f"yad2://{token}",
            "title":title, "address":addr, "neighborhood":"Herzliya",
            "price":float(price_m.group(1).replace(',','')) if price_m else None,
            "rooms":float(rooms_m.group(1)) if rooms_m else None,
            "sqm":float(sqm_m.group(1)) if sqm_m else None,
            "renovated":int("renovated" in low or "משופ" in block),
            "balcony":int("balcony" in low or "מרפסת" in block),
            "mamad":int("mamad" in low or "ממ״ד" in block or "ממד" in block),
            "parking":int("parking" in low or "חניה" in block),
            "elevator":int("elevator" in low or "מעלית" in block),
            "furnished":int("furnished" in low or "מרוהט" in block),
            "description":desc, "posted":_value(block, "Listed"),
        }
        if row["url"] and (row["rooms"] or 0) >= 4:
            rows.append(enrich(row))
    return rows

def scrape_yad2() -> list[dict]:
    client = MCPClient()
    rows: list[dict] = []
    try:
        for page in (1, 2, 3):
            text = client.call_tool("search_rentals", {
                "city":"6400", "rooms":"4-6", "priceMax":15000,
                "sizeMin":70, "page":page, "pageSize":40,
            })
            page_rows = parse_yad2_markdown(text)
            rows.extend(page_rows)
            if len(page_rows) < 40:
                break
    finally:
        client.close()
    return list({r["url"]: r for r in rows}.values())
