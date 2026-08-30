from __future__ import annotations
import json,re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
H={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/151 Safari/537.36"}
def get(url):
 r=requests.get(url,headers=H,timeout=20);r.raise_for_status();r.encoding='utf-8';return BeautifulSoup(r.text,'html.parser')
def nu(s):
 if not s:return None
 s=s.replace('\u202f','').replace('\xa0','').replace(' ','').replace(',','');m=re.search(r'\d+(?:\.\d+)?',s);return float(m.group()) if m else None
def vals(t,forced=None):
 p=re.search(r'([0-9][0-9,\u202f\xa0 ]*)\s*/\s*לחודש',t);q=re.search(r'(\d+(?:\.\d+)?)\s*חדרים',t);z=re.search(r'(\d+(?:\.\d+)?)\s*מ[״\"]?ר',t)
 return nu(p.group(1)) if p else None,nu(q.group(1)) if q else forced,nu(z.group(1)) if z else None
def main():
 rows={};dbg=[]
 bases=[(f'https://realta.co.il/he/herzliya/{n}-rooms/',float(n)) for n in range(6,13)]
 bases += [(x,None) for x in ['https://realta.co.il/he/herzliya/cottage/','https://realta.co.il/he/herzliya/duplex/','https://realta.co.il/he/herzliya/villa/','https://realta.co.il/he/herzliya/garden-apartment/','https://realta.co.il/he/herzliya/penthouse/']]
 for base,forced in bases:
  for pg in range(1,8):
   u=base if pg==1 else f'{base}?page={pg}'
   try:s=get(u)
   except Exception as e:dbg.append([u,repr(e)]);break
   found=0
   for a in s.select('a[href]'):
    href=urljoin(u,a.get('href','')).split('?')[0]
    if not re.search(r'https://realta\.co\.il/he/herzliya/(?!page/)[^/]+/\d+/?$',href):continue
    t=' '.join(a.stripped_strings)
    p,r,m=vals(t,forced)
    if p is None or r is None:
     # Card content can be a sibling inside the same small wrapper.
     node=a.parent
     for _ in range(2):
      if node is None:break
      tt=' '.join(node.stripped_strings);pp,rr,mm=vals(tt,forced)
      if pp is not None and rr is not None:p,r,m,t=pp,rr,mm,tt;break
      node=node.parent
    if p is not None and r is not None:
     found+=1
     cur=rows.get(href)
     if cur is None or len(t)<len(cur.get('card_text','')):
      rows[href]={'source':'Realta','url':href,'price':p,'rooms':r,'sqm':m,'card_text':t[:1200]}
   dbg.append([u,found])
   if found==0 and pg>1:break
 out=[x for x in rows.values() if x['rooms']>=6 and x['price']<=25000]
 out.sort(key=lambda x:x['price']/max(x['rooms']-1,1))
 json.dump({'rows':out,'debug':{'found':len(rows),'kept':len(out),'pages':dbg}},open('realta-fast-results.json','w'),ensure_ascii=False,indent=2)
 print('FOUND',len(rows),'KEPT',len(out))
 for x in out:print(x['price'],x['rooms'],x.get('sqm'),x['card_text'][:180],x['url'])
if __name__=='__main__':main()
