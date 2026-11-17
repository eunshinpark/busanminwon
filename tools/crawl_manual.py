"""부산민원120 민원편람(목록+상세) 수집 -> data/manual.json. 요청 사이 0.4초 대기, 상세는 data/cache에 캐시."""
import re, html, json, time, os, urllib.request
BASE='https://www.busan.go.kr'
UA='Mozilla/5.0 (X11; Linux x86_64) minwon-index/1.0'
ROOT=os.path.join(os.path.dirname(__file__),'..','data')
CACHE=os.path.join(ROOT,'cache')
def get(url):
    for i in range(4):
        try:
            r=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ko'})
            return urllib.request.urlopen(r,timeout=30).read().decode('utf8','replace')
        except Exception as e:
            time.sleep(1.5*(i+1)); err=e
    raise err
def cached(key,url):
    p=os.path.join(CACHE,key)
    if os.path.exists(p): return open(p,encoding='utf8').read()
    s=get(url); open(p,'w',encoding='utf8').write(s); time.sleep(0.4); return s
txt=lambda s: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
items=[]
page=1
while True:
    s=cached(f'list{page}.html',f'{BASE}/minwon/manual?curPage={page}')
    tot=int(re.search(r'totalNum">(\d+)',s).group(1)); pages=int(re.search(r'</b>/(\d+)page',s).group(1))
    for tr in re.findall(r'<tr>\s*<!-- 순번 -->.*?</tr>',s,flags=re.S):
        tds=[txt(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,flags=re.S)]
        m=re.search(r'href="/minwon/manual/(\d+)',tr)
        if m and len(tds)>=8:
            items.append(dict(id=m.group(1),title=tds[1],dept=tds[3],date=tds[4],category=tds[6],field=tds[7]))
    print('list',page,'/',pages,len(items),flush=True)
    if page>=pages: break
    page+=1
for n,it in enumerate(items):
    s=cached(f'd{it["id"]}.html',f'{BASE}/minwon/manual/{it["id"]}')
    ph=re.search(r'전화번호</span></dt>\s*<dd>(.*?)</dd>',s,flags=re.S)
    it['phone']=txt(ph.group(1)) if ph else ''
    it['url']=f'{BASE}/minwon/manual/{it["id"]}'
    it['files']=[dict(name=txt(n_),url=BASE+html.unescape(u)) for u,n_ in re.findall(r'<a href="(/comm/getFile\?[^"]+)"[^>]*>(.*?)</a>',s,flags=re.S)]
    if n%50==0: print('detail',n,len(items),flush=True)
json.dump(items,open(os.path.join(ROOT,'manual.json'),'w',encoding='utf8'),ensure_ascii=False,indent=0)
print('done',len(items),'items; total reported',tot)
