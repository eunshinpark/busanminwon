"""minwon.json + manual.json + onestop.json -> data/db.json (민원별 부서/수수료/기한/서식/전화/창구/유형)"""
import json, re, os, sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))
from app.types import TYPES, classify_name
R=os.path.join(os.path.dirname(__file__),'..','data')
L=lambda n: json.load(open(os.path.join(R,n),encoding='utf8'))
mw=L('minwon.json'); man=L('manual.json'); one=L('onestop.json')
def key(s): return re.sub(r'[\s\(\)\[\]\.,·‧・/\-_~“”"\'‘’]|신청서?$','',s)
def bg(s):
    k=key(s); return {k[i:i+2] for i in range(len(k)-1)} or {k}
def sim(a,b):
    A,B=bg(a),bg(b); return len(A&B)/max(1,len(A|B))
def best(name,pool,dept=None,th=0.5):
    out=[]
    for p in pool:
        s=sim(name,p['title'] if 'title' in p else p['name'])
        if key(name)==key(p.get('title',p.get('name',''))): s=1.0
        if dept and key(dept)==key(p.get('dept','')): s+=0.08
        out.append((s,p))
    out.sort(key=lambda x:-x[0])
    return out[0] if out and out[0][0]>=th else (0,None)
pre={}
for p in mw['presurvey']:
    pre[key(p['name'])]=dict(legal=p['legal'],pre=p['pre'],after=p['after'])
used=set()
for it in mw['items']:
    code,why=classify_name(it['name']); it['type']=code; it['typeName']=TYPES[code]; it['typeWhy']=why
    s,m=best(it['name'],man,it['dept'],0.55)
    if m:
        it['manual']=dict(title=m['title'],url=m['url'],phone=m['phone'],field=m['field'],category=m['category'],deptManual=m['dept'],match=round(min(s,1),2),
                          files=m['files'])
        used.add(m['id'])
    k=key(it['name'])
    for pk,pv in pre.items():
        if pk==k or sim(pk,it['name'])>=0.8: it['presurvey']=pv
    s,o=(0,None)
    if it['dept']=='통합민원과':
        best_s=0;bn=None
        for n in one['names']:
            sc=1.0 if key(n)==key(it['name']) else sim(n,it['name'])
            if sc>best_s: best_s,bn=sc,n
        it['onestop']=bool(bn and best_s>=0.6)
        # 창구 추정: 창구별 처리내용 문구와의 유사도(+포함 관계)
        cands=[]
        for w in one['windows']:
            for t in w['tasks']:
                a,b=key(t),key(it['name'])
                sc=sim(t,it['name'])+(0.3 if (a and (a in b or b in a)) else 0)
                cands.append((sc,w))
        cands.sort(key=lambda x:-x[0])
        if cands and cands[0][0]>=0.28:
            w=cands[0][1]; it['window']=dict(window=w['window'],phone=w['phone'])
for i,it in enumerate(man): pass
unmatched=[m for m in man if m['id'] not in used]
db=dict(items=mw['items'],types=TYPES,windows=one['windows'],onestop=one['names'],manualUnmatched=[dict(title=m['title'],dept=m['dept'],url=m['url'],phone=m['phone']) for m in unmatched],
        meta=dict(source='1_민원목록_26년3분기.hwpx · 부산민원120 민원편람·원스톱서비스 안내',built=__import__('datetime').date.today().isoformat()))
json.dump(db,open(os.path.join(R,'db.json'),'w',encoding='utf8'),ensure_ascii=False)
n=len(mw['items']); print('items',n,'manual-matched',sum('manual' in i for i in mw['items']),'with files',sum(bool(i.get('manual',{}).get('files')) for i in mw['items']),'phone',sum(bool(i.get('manual',{}).get('phone')) for i in mw['items']),'unmatched manual',len(unmatched),'통합민원과 onestop',sum(i.get('onestop',False) for i in mw['items']),'window',sum('window' in i for i in mw['items']),'presurvey',sum('presurvey' in i for i in mw['items']))
