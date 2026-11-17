"""info0202(원스톱 민원서비스 안내) -> data/onestop.json : 139개 민원명, 창구(번호/전화/처리내용)"""
import re, html, json, os, sys, urllib.request
ROOT=os.path.join(os.path.dirname(__file__),'..','data')
UA='Mozilla/5.0 (X11; Linux x86_64) minwon-index/1.0'
src=os.path.join(ROOT,'cache','info0202.html')
if not os.path.exists(src):
    for i in range(4):
        try:
            s=urllib.request.urlopen(urllib.request.Request('https://www.busan.go.kr/minwon/info0202',headers={'User-Agent':UA}),timeout=30).read().decode('utf8'); break
        except Exception as e: import time; time.sleep(2)
    open(src,'w',encoding='utf8').write(s)
s=open(src,encoding='utf8').read()
T=lambda x: re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip()
tabs=re.findall(r'<table.*?</table>',s,flags=re.S)
names=[]
for tr in re.findall(r'<tr>(.*?)</tr>',tabs[0],flags=re.S):
    td=[T(x) for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,flags=re.S)]
    for i in range(0,len(td)-1,2):
        if td[i].isdigit(): names.append(td[i+1])
wins=[]
for tr in re.findall(r'<tr>(.*?)</tr>',tabs[1],flags=re.S):
    tds=re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tr,flags=re.S)
    if len(tds)<3 or '번 창구' not in T(tds[0]): continue
    lines=[T(x) for x in re.split(r'<br\s*/?>|</li>|</p>',tds[2]) if T(x)]
    wins.append(dict(window=T(tds[0]),phone=T(tds[1]).replace('☎','').strip(),tasks=lines))
json.dump(dict(names=names,windows=wins),open(os.path.join(ROOT,'onestop.json'),'w',encoding='utf8'),ensure_ascii=False,indent=1)
print(len(names),'onestop names',len(wins),'windows'); print(wins[0]); print(wins[-1])
