from __future__ import annotations
import json, re, time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from yad2_client import MCPClient, parse_yad2_markdown

HEADERS={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}
TIMEOUT=25
DEBUG={}

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=TIMEOUT)
    DEBUG.setdefault("http",[]).append({"url":url,"status":r.status_code,"len":len(r.text),"final":r.url})
    r.raise_for_status(); return r,BeautifulSoup(r.text,"html.parser")

def get(url): return fetch(url)[1]

def num(s):
    if not s:return None
    s=s.replace("\u202f","").replace("\xa0","")
    m=re.search(r"([\d,.]+)",s)
    return float(m.group(1).replace(",","")) if m else None

def flag(text,*words):
    low=text.lower(); return int(any(w.lower() in low for w in words))

def parse_realta_detail(url):
    soup=get(url); text=" ".join(soup.stripped_strings)
    html_title=soup.title.get_text(" ",strip=True) if soup.title else ""
    h1=soup.find("h1"); title=h1.get_text(" ",strip=True) if h1 else html_title or "Realta listing"
    # Realta's <title> is very stable: "דירת 6 חדרים ... — 14,000 ש״ח לחודש | Realta"
    rm=(re.search(r"(\d+(?:\.\d+)?)\s*חדרים",html_title) or re.search(r"(\d+(?:\.\d+)?)\s*(?:חדרים|rooms)",text,re.I))
    pm=(re.search(r"[—-]\s*([\d,\u202f\xa0]+)\s*ש[״\"]?ח\s*לחודש",html_title,re.I)
        or re.search(r"([\d,\u202f\xa0]+)\s*/\s*(?:לחודש|per month)",text,re.I))
    sm=(re.search(r"(\d+(?:\.\d+)?)\s*מ[״\"]?ר",text,re.I)
        or re.search(r"(\d+(?:\.\d+)?)\s*(?:sqm|m²)",text,re.I))
    baths=None
    for pat in [r"(\d+)\s*חדרי\s*רחצה",r"(\d+)\s*מקלחות",r"(\d+)\s*bathrooms?",r"(\d+)\s*showers?"]:
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
      "mamad":flag(text,"ממ״ד","ממד","safe room","mamad"),"description":text[:8000]
    }

def scan_realta():
    urls=[]
    bases=[f"https://realta.co.il/he/herzliya/{r}-rooms/" for r in range(6,13)]
    bases += ["https://realta.co.il/he/herzliya/cottage/","https://realta.co.il/he/herzliya/duplex/","https://realta.co.il/he/herzliya/villa/"]
    for base in bases:
      for p in range(1,6):
        url=base if p==1 else f"{base}?page={p}"
        try:soup=get(url)
        except Exception as e:
          DEBUG.setdefault("errors",[]).append(["Realta-index",url,repr(e)]); break
        found=0
        for a in soup.select("a[href]"):
          href=urljoin(url,a.get("href","")); clean=href.split("?")[0]
          if re.search(r"https://realta\.co\.il/he/herzliya/[^/]+/\d+/?$",clean):
            if clean not in urls: urls.append(clean); found+=1
        if found==0 and p>1: break
    out=[]
    for u in urls:
      try:
        r=parse_realta_detail(u)
        if (r.get("rooms") or 0)>=6 and (r.get("price") or 10**9)<=25000: out.append(r)
      except Exception as e: DEBUG.setdefault("errors",[]).append(["Realta-detail",u,repr(e)])
    DEBUG["realta_candidates"]=len(urls)
    DEBUG["realta_parsed"]=len(out)
    return out

def scan_janglo():
    urls=[]; out=[]
    for p in range(0,12):
      url="https://www.janglo.net/real-estate-rentals/nh"+(f"?page={p}" if p else "")
      try:r,soup=fetch(url)
      except Exception as e: DEBUG.setdefault("errors",[]).append(["Janglo-index",url,repr(e)]); continue
      raw=r.text
      candidates=[]
      # Janglo has changed HTML wrappers repeatedly; collect item IDs from raw HTML, not one CSS shape.
      for pat in [r'href=["\']([^"\']*?/item/[A-Za-z0-9]+[^"\']*)["\']', r'(?<![A-Za-z0-9])/item/([A-Za-z0-9]{6,})']:
        for m in re.finditer(pat,raw,re.I):
          href=m.group(1)
          if not href.startswith("http"):
            href=("/item/"+href if not href.startswith("/") and "/item/" not in href else href)
            href=urljoin(url,href)
          candidates.append(href.split("?")[0])
      for href in candidates:
        if href not in urls: urls.append(href)
      DEBUG.setdefault("janglo_pages",[]).append({"url":url,"raw_item_mentions":raw.lower().count("/item/"),"found":len(candidates)})
    for u in urls:
      try:
        soup=get(u); text=" ".join(soup.stripped_strings)
        if "herzli" not in text.lower() and "hertzli" not in text.lower(): continue
        rm=re.search(r"(\d+(?:\.\d+)?)\s*Rooms",text,re.I); pm=re.search(r"([\d,]+)\s*NIS",text,re.I); sm=re.search(r"(\d+(?:\.\d+)?)\s*m[²2]",text,re.I)
        rooms=num(rm.group(1)) if rm else None; price=num(pm.group(1)) if pm else None
        if (rooms or 0)<6 or (price or 10**9)>25000: continue
        baths=None
        for pat in [r"(\d+)\s*(?:full\s*)?(?:bathrooms?|showers?)",r"(\d+)\s*showers?"]:
          m=re.search(pat,text,re.I)
          if m: baths=int(m.group(1)); break
        out.append({"source":"Janglo","url":u,"title":soup.find("h1").get_text(" ",strip=True) if soup.find("h1") else "Janglo","price":price,"rooms":rooms,"sqm":num(sm.group(1)) if sm else None,"bathrooms":baths,"furnished":flag(text,"furnished"),"balcony":flag(text,"balcony"),"renovated":flag(text,"renovated","modern","brand new"),"parking":flag(text,"parking"),"mamad":flag(text,"mamad","safe room","shelter room"),"description":text[:8000]})
      except Exception as e: DEBUG.setdefault("errors",[]).append(["Janglo-detail",u,repr(e)])
    DEBUG["janglo_candidates"]=len(urls); DEBUG["janglo_parsed"]=len(out)
    return out

def scan_zipika():
    url="https://zipika.com/property-search/D651AA6A-D7B9-47CD-89AF-4584E6B84619?cfs=D651AA6A-D7B9-47CD-89AF-4584E6B84619&lng=en"
    try:soup=get(url)
    except Exception as e:
      DEBUG.setdefault("errors",[]).append(["Zipika",repr(e)]); return []
    out=[]
    # Zipika renders complete listing text server-side. Split on listing headings.
    text="\n".join(soup.stripped_strings)
    chunks=re.split(r"(?=Apartment for rent|Housing unit for rent|House for rent|Villa for rent|Duplex for rent|Penthouse for rent)",text,re.I)
    for chunk in chunks:
      rm=re.search(r"-\s*(\d+(?:\.\d+)?)\s*rooms",chunk,re.I)
      pm=re.search(r"Price:\s*([\d,]+)\s*ILS",chunk,re.I)
      if not rm or not pm: continue
      rooms=num(rm.group(1)); price=num(pm.group(1))
      if (rooms or 0)<6 or (price or 10**9)>25000: continue
      addr_m=re.search(r"Address:\s*(.*?)\s*(?:Short details:|פירוט קצר:)",chunk,re.I|re.S)
      sm=re.search(r"(\d+(?:\.\d+)?)\s*m²",chunk,re.I)
      out.append({"source":"Zipika","url":url,"title":chunk.splitlines()[0][:220],"price":price,"rooms":rooms,"sqm":num(sm.group(1)) if sm else None,"bathrooms":None,"furnished":flag(chunk,"furnished","furniture"),"balcony":flag(chunk,"balcony","terrace"),"renovated":flag(chunk,"renovated","modern"),"parking":flag(chunk,"parking"),"mamad":flag(chunk,"secure space","mamad"),"address":addr_m.group(1).strip() if addr_m else "","description":chunk[:8000]})
    DEBUG["zipika_parsed"]=len(out)
    return out

def scan_homeless():
    out=[]
    try:soup=get("https://www.homeless.co.il/rent/city=%D7%94%D7%A8%D7%A6%D7%9C%D7%99%D7%94")
    except Exception:return out
    for tr in soup.select("tr"):
      cells=[" ".join(td.stripped_strings) for td in tr.select("td")]
      if len(cells)<8 or not any("הרצליה" in x for x in cells): continue
      text=" | ".join(cells); rooms=None; price=None
      for c in cells:
        if rooms is None and re.fullmatch(r"\d+(?:\.\d+)?",c):
          v=float(c)
          if 1<=v<=20: rooms=v
        if price is None:
          m=re.search(r"([\d,]{4,})\s*₪",c)
          if m: price=num(m.group(1))
      if (rooms or 0)<6 or (price or 10**9)>25000: continue
      a=tr.find("a",href=True); u=urljoin("https://www.homeless.co.il",a["href"]) if a else ""
      out.append({"source":"Homeless","url":u,"title":text[:180],"price":price,"rooms":rooms,"sqm":None,"bathrooms":None,"furnished":flag(text,"מרוהט"),"balcony":flag(text,"מרפסת"),"renovated":flag(text,"משופ"),"parking":flag(text,"חניה"),"mamad":flag(text,"ממ״ד","ממד"),"description":text})
    return out

def scan_yad2():
    client=MCPClient(); out=[]
    try:
      for room_filter in ("6","7-12"):
        for page in range(1,6):
          try:text=client.call_tool("search_rentals",{"city":"6400","rooms":room_filter,"priceMax":25000,"page":page,"pageSize":40})
          except Exception as e:
            DEBUG.setdefault("yad2_errors",[]).append([room_filter,page,repr(e)]); break
          rows=parse_yad2_markdown(text); out.extend(rows)
          if len(rows)<40: break
    finally: client.close()
    out=[r for r in out if (r.get("rooms") or 0)>=6 and (r.get("price") or 10**9)<=25000]
    for r in out:r["bathrooms"]=None
    DEBUG["yad2_parsed"]=len(out)
    return list({r.get("url"):r for r in out}.values())

def main():
    results={}
    for name,fn in [("Realta",scan_realta),("Yad2",scan_yad2),("Janglo",scan_janglo),("Zipika",scan_zipika),("Homeless",scan_homeless)]:
      try: results[name]=fn()
      except Exception as e: results[name]={"error":repr(e)}; DEBUG.setdefault("errors",[]).append([name,repr(e)])
    flat=[]
    for val in results.values():
      if isinstance(val,list): flat.extend(val)
    results["all"]=flat; results["debug"]=DEBUG
    with open("scan-results.json","w",encoding="utf-8") as f:json.dump(results,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in results.items() if k not in ("all","debug")},ensure_ascii=False))
    print("DEBUG",json.dumps(DEBUG,ensure_ascii=False)[:12000]); print(f"TOTAL={len(flat)}")
if __name__=="__main__": main()
