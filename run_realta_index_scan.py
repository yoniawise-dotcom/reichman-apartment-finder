from __future__ import annotations
import json, re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}
TIMEOUT=25

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=TIMEOUT)
    r.raise_for_status()
    return r,BeautifulSoup(r.text,"html.parser")

def clean_num(s):
    if not s:return None
    s=s.replace("\u202f","").replace("\xa0","").replace(" ","").replace(",","")
    m=re.search(r"\d+(?:\.\d+)?",s)
    return float(m.group()) if m else None

def parse_card_text(text, forced_rooms=None):
    pm=re.search(r"([0-9][0-9,\u202f\xa0 ]*)\s*/\s*לחודש",text)
    rm=re.search(r"(\d+(?:\.\d+)?)\s*חדרים",text)
    sm=re.search(r"(\d+(?:\.\d+)?)\s*מ[״\"]?ר",text)
    return {
        "price":clean_num(pm.group(1)) if pm else None,
        "rooms":clean_num(rm.group(1)) if rm else forced_rooms,
        "sqm":clean_num(sm.group(1)) if sm else None,
    }

def feature(text,*words):
    low=text.lower();return int(any(w.lower() in low for w in words))

def detail(url):
    _,soup=fetch(url)
    text=" ".join(soup.stripped_strings)
    h1=soup.find("h1")
    title=h1.get_text(" ",strip=True) if h1 else "Realta listing"
    vals=parse_card_text(text)
    original=""
    for a in soup.select("a[href]"):
        lbl=" ".join(a.stripped_strings)
        if "מודעה המקורית" in lbl or "original listing" in lbl.lower():
            original=urljoin(url,a.get("href",""));break
    return {
        "source":"Realta","url":url,"original_url":original,"title":title,
        **vals,
        "furnished":feature(text,"מרוהט","furnished"),
        "balcony":feature(text,"מרפסת","balcony"),
        "renovated":feature(text,"משופצת","משופץ","renovated"),
        "parking":feature(text,"חניה","parking"),
        "mamad":feature(text,"ממ״ד","ממד","safe room","mamad"),
        "elevator":feature(text,"מעלית","elevator"),
        "description":text[:8000]
    }

def main():
    cards={}
    debug=[]
    room_bases=[(f"https://realta.co.il/he/herzliya/{n}-rooms/",float(n)) for n in range(6,13)]
    other=[("https://realta.co.il/he/herzliya/cottage/",None),("https://realta.co.il/he/herzliya/duplex/",None),("https://realta.co.il/he/herzliya/villa/",None),("https://realta.co.il/he/herzliya/garden-apartment/",None),("https://realta.co.il/he/herzliya/penthouse/",None)]
    for base,forced_rooms in room_bases+other:
        for page in range(1,8):
            url=base if page==1 else f"{base}?page={page}"
            try:_,soup=fetch(url)
            except Exception as e:
                debug.append({"page":url,"error":repr(e)});break
            matched=0
            for a in soup.select("a[href]"):
                href=urljoin(url,a.get("href","")); href=href.split("?")[0]
                if not re.search(r"https://realta\.co\.il/he/herzliya/[^/]+/\d+/?$",href):continue
                # Usually the whole listing card is clickable. If not, walk up a few ancestors.
                texts=[" ".join(a.stripped_strings)]
                node=a
                for _ in range(4):
                    node=node.parent
                    if node is None:break
                    t=" ".join(node.stripped_strings)
                    if t and t not in texts:texts.append(t)
                best={"price":None,"rooms":forced_rooms,"sqm":None};best_text=""
                for t in texts:
                    v=parse_card_text(t,forced_rooms)
                    if v["price"] is not None and (v["rooms"] or 0)>=6:
                        best=v;best_text=t;break
                if href not in cards or (cards[href].get("price") is None and best["price"] is not None):
                    cards[href]={"url":href,**best,"card_text":best_text[:1000]}
                matched+=1
            debug.append({"page":url,"matched_links":matched,"total_links":len(soup.select('a[href]'))})
            if matched==0 and page>1:break
    candidates=[]
    for c in cards.values():
        if (c.get("rooms") or 0)>=6 and c.get("price") is not None and c["price"]<=25000:
            candidates.append(c)
    rows=[]
    for i,c in enumerate(candidates,1):
        try:r=detail(c["url"])
        except Exception as e:
            r={"source":"Realta","url":c["url"],"title":"Realta listing","original_url":"","furnished":0,"balcony":0,"renovated":0,"parking":0,"mamad":0,"elevator":0,"description":"","detail_error":repr(e)}
        # Card values are the source of truth for filtering; detail values fill gaps only.
        for k in ("price","rooms","sqm"):
            if c.get(k) is not None:r[k]=c[k]
        r["card_text"]=c.get("card_text","")
        rows.append(r)
        if i%30==0:time.sleep(.2)
    rows.sort(key=lambda x:(x.get("price") or 999999)/(max((x.get("rooms") or 1)-1,1)))
    out={"rows":rows,"debug":{"unique_urls":len(cards),"candidates_under_25k":len(candidates),"pages":debug,"sample_cards":list(cards.values())[:20]}}
    with open("realta-results.json","w",encoding="utf-8") as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps({"unique_urls":len(cards),"candidates_under_25k":len(candidates),"rows":len(rows)},ensure_ascii=False))
    for r in rows[:25]:print(r.get("price"),r.get("rooms"),r.get("sqm"),r.get("furnished"),r.get("renovated"),r.get("balcony"),r.get("title"),r.get("url"))

if __name__=="__main__":main()
