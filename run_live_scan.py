from __future__ import annotations
import json, re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from yad2_client import MCPClient, parse_yad2_markdown

HEADERS={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}
TIMEOUT=25

def get(url):
    r=requests.get(url,headers=HEADERS,timeout=TIMEOUT); r.raise_for_status(); return BeautifulSoup(r.text,"html.parser")

def num(s):
    if not s:return None
    m=re.search(r"([\d,.]+)",s.replace("\u202f","")); return float(m.group(1).replace(",","")) if m else None

def flag(text,*words):
    low=text.lower(); return int(any(w.lower() in low for w in words))

def parse_realta_detail(url):
    soup=get(url); text=" ".join(soup.stripped_strings)
    h1=soup.find("h1"); title=h1.get_text(" ",strip=True) if h1 else "Realta listing"
    pm=re.search(r"([\d,\u202f]+)\s*/\s*(?:לחודש|per month)",text,re.I)
    rm=re.search(r"(\d+(?:\.\d+)?)\s*(?:חדרים|rooms)",text,re.I)
    sm=re.search(r"(\d+(?:\.\d+)?)\s*(?:מ[\"״]?ר|sqm|m²)",text,re.I)
    baths=None
    for pat in [r"(\d+)\s*חדרי\s*רחצה",r"(\d+)\s*bathrooms?",r"(\d+)\s*showers?"]:
        m=re.search(pat,text,re.I)
        if m: baths=int(m.group(1)); break
    original=""
    for a in soup.select("a[href]"):
        label=" ".join(a.stripped_strings)
        if "מודעה המקורית" in label or "original listing" in label.lower():
            original=urljoin(url,a.get("href","")); break
    return {
      "source":"Realta","url":url,"original_url":original,"title":title,
      "price":num(pm.group(1)) if pm else None,"rooms":num(rm.group(1)) if rm else None,
      "sqm":num(sm.group(1)) if sm else None,"bathrooms":baths,
      "furnished":flag(text,"מרוהט","furnished"),"balcony":flag(text,"מרפסת","balcony"),
      "renovated":flag(text,"משופצת","משופץ","renovated"),"parking":flag(text,"חניה","parking"),
      "mamad":flag(text,"ממ״ד","ממד","safe room","mamad"),"description":text[:6000]
    }

def scan_realta():
    urls=[]
    bases=["https://realta.co.il/he/herzliya/","https://realta.co.il/he/herzliya/cottage/","https://realta.co.il/he/herzliya/duplex/","https://realta.co.il/he/herzliya/villa/"]
    for base in bases:
      for p in range(1,13):
        url=base if p==1 else f"{base}?page={p}"
        try:soup=get(url)
        except Exception:break
        found=0
        for a in soup.select("a[href]"):
          href=urljoin(url,a.get("href",""))
          if re.search(r"realta\.co\.il/he/herzliya/[^/]+/\d+/?(?:\?.*)?$",href):
            href=href.split("?")[0]
            if href not in urls:urls.append(href);found+=1
        if found==0 and p>1: break
    out=[]
    for i,u in enumerate(urls,1):
      try:
        r=parse_realta_detail(u)
        if (r.get("rooms") or 0)>=6 and (r.get("price") or 10**9)<=25000: out.append(r)
      except Exception as e: pass
      if i%40==0: time.sleep(.2)
    return out

def scan_janglo():
    urls=[];out=[]
    for p in range(0,12):
      url="https://www.janglo.net/real-estate-rentals/nh"+(f"?page={p}" if p else "")
      try:soup=get(url)
      except Exception:continue
      for a in soup.select('a[href*="/item/"]'):
        href=urljoin(url,a.get("href",""))
        if href not in urls:urls.append(href)
    for u in urls:
      try:
        soup=get(u);text=" ".join(soup.stripped_strings)
        if "herzli" not in text.lower() and "hertzli" not in text.lower():continue
        rm=re.search(r"(\d+(?:\.\d+)?)\s*Rooms",text,re.I); pm=re.search(r"([\d,]+)\s*NIS",text,re.I); sm=re.search(r"(\d+(?:\.\d+)?)\s*m[²2]",text,re.I)
        rooms=num(rm.group(1)) if rm else None;price=num(pm.group(1)) if pm else None
        if (rooms or 0)<6 or (price or 10**9)>25000:continue
        out.append({"source":"Janglo","url":u,"title":soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else "Janglo","price":price,"rooms":rooms,"sqm":num(sm.group(1)) if sm else None,"bathrooms":None,"furnished":flag(text,"furnished"),"balcony":flag(text,"balcony"),"renovated":flag(text,"renovated"),"parking":flag(text,"parking"),"mamad":flag(text,"mamad","safe room"),"description":text[:6000]})
      except Exception: pass
    return out

def scan_homeless():
    out=[]
    try:soup=get("https://www.homeless.co.il/rent/city=%D7%94%D7%A8%D7%A6%D7%9C%D7%99%D7%94")
    except Exception:return out
    for tr in soup.select("tr"):
      text=" ".join(tr.stripped_strings)
      if "הרצליה" not in text:continue
      rm=re.search(r"(?:^|\s)(\d+(?:\.\d+)?)\s*(?:חדרים)?",text); pm=re.search(r"([\d,]{4,})\s*₪",text)
      rooms=num(rm.group(1)) if rm else None;price=num(pm.group(1)) if pm else None
      if (rooms or 0)<6 or (price or 10**9)>25000:continue
      a=tr.find("a",href=True);u=urljoin("https://www.homeless.co.il",a["href"]) if a else ""
      out.append({"source":"Homeless","url":u,"title":text[:180],"price":price,"rooms":rooms,"sqm":None,"bathrooms":None,"furnished":flag(text,"מרוהט"),"balcony":flag(text,"מרפסת"),"renovated":flag(text,"משופ"),"parking":flag(text,"חניה"),"mamad":flag(text,"ממ״ד","ממד"),"description":text})
    return out

def scan_yad2():
    client=MCPClient();out=[]
    try:
      for page in range(1,7):
        text=client.call_tool("search_rentals",{"city":"6400","rooms":"6-12","priceMax":25000,"sizeMin":90,"page":page,"pageSize":40})
        rows=parse_yad2_markdown(text); out.extend(rows)
        if len(rows)<40: break
    finally: client.close()
    for r in out:r["bathrooms"]=None
    return list({r.get("url"):r for r in out}.values())

def main():
    results={}
    for name,fn in [("Realta",scan_realta),("Yad2",scan_yad2),("Janglo",scan_janglo),("Homeless",scan_homeless)]:
      try: results[name]=fn()
      except Exception as e: results[name]={"error":repr(e)}
    flat=[]
    for name,val in results.items():
      if isinstance(val,list): flat.extend(val)
    # crude URL/title/price/rooms dedupe; keep Realta and Yad2 source provenance when distinct
    results["all"]=flat
    with open("scan-results.json","w",encoding="utf-8") as f:json.dump(results,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in results.items() if k!="all"},ensure_ascii=False))
    print(f"TOTAL={len(flat)}")

if __name__=="__main__":main()
