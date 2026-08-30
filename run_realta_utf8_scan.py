from __future__ import annotations
import json,re,time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}

def soup_for(url):
    r=requests.get(url,headers=HEADERS,timeout=25)
    r.raise_for_status()
    r.encoding="utf-8"
    return BeautifulSoup(r.text,"html.parser")

def n(s):
    if not s:return None
    s=s.replace("\u202f","").replace("\xa0","").replace(" ","").replace(",","")
    m=re.search(r"\d+(?:\.\d+)?",s)
    return float(m.group()) if m else None

def flag(text,*words):
    low=text.lower();return int(any(w.lower() in low for w in words))

def parse_detail(url):
    soup=soup_for(url);text=" ".join(soup.stripped_strings)
    h1=soup.find("h1");title=h1.get_text(" ",strip=True) if h1 else "Realta listing"
    rm=re.search(r"(\d+(?:\.\d+)?)\s*חדרים",text)
    pm=re.search(r"([0-9][0-9,\u202f\xa0 ]*)\s*/\s*לחודש",text)
    sm=re.search(r"(\d+(?:\.\d+)?)\s*מ[״\"]?ר",text)
    original=""
    for a in soup.select("a[href]"):
        label=" ".join(a.stripped_strings)
        if "מודעה המקורית" in label:
            original=urljoin(url,a.get("href",""));break
    return {
      "source":"Realta","url":url,"original_url":original,"title":title,
      "price":n(pm.group(1)) if pm else None,"rooms":n(rm.group(1)) if rm else None,"sqm":n(sm.group(1)) if sm else None,
      "furnished":flag(text,"מרוהט"),"balcony":flag(text,"מרפסת"),"renovated":flag(text,"משופצת","משופץ"),
      "parking":flag(text,"חניה"),"mamad":flag(text,"ממ״ד","ממד"),"elevator":flag(text,"מעלית"),
      "description":text[:10000]
    }

def main():
    urls=[];pages=[]
    bases=[f"https://realta.co.il/he/herzliya/{i}-rooms/" for i in range(6,13)]
    bases += ["https://realta.co.il/he/herzliya/cottage/","https://realta.co.il/he/herzliya/duplex/","https://realta.co.il/he/herzliya/villa/","https://realta.co.il/he/herzliya/garden-apartment/","https://realta.co.il/he/herzliya/penthouse/"]
    for base in bases:
      for page in range(1,8):
        u=base if page==1 else f"{base}?page={page}"
        try:soup=soup_for(u)
        except Exception as e:pages.append({"url":u,"error":repr(e)});break
        found=0
        for a in soup.select("a[href]"):
            href=urljoin(u,a.get("href",""));href=href.split("?")[0]
            if re.search(r"https://realta\.co\.il/he/herzliya/(?!page/)[^/]+/\d+/?$",href):
                if href not in urls:urls.append(href);found+=1
        pages.append({"url":u,"found":found})
        if found==0 and page>1:break
    rows=[];errors=[]
    for i,u in enumerate(urls,1):
        try:r=parse_detail(u)
        except Exception as e:errors.append([u,repr(e)]);continue
        if (r.get("rooms") or 0)>=6 and r.get("price") is not None and r["price"]<=25000:rows.append(r)
        if i%30==0:time.sleep(.1)
    # URL-level dedupe and sort by approximate price per bedroom.
    rows=list({r["url"]:r for r in rows}.values())
    rows.sort(key=lambda r:(r["price"] or 999999)/max((r["rooms"] or 1)-1,1))
    with open("realta-utf8-results.json","w",encoding="utf-8") as f:
        json.dump({"rows":rows,"debug":{"discovered":len(urls),"kept":len(rows),"errors":errors,"pages":pages}},f,ensure_ascii=False,indent=2)
    print("DISCOVERED",len(urls),"KEPT",len(rows))
    for r in rows:print(r["price"],r["rooms"],r.get("sqm"),r["furnished"],r["renovated"],r["balcony"],r["title"],r["url"])

if __name__=="__main__":main()
