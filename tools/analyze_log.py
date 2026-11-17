"""검색 품질 분석: python3 tools/analyze_log.py [일수=30]  (data/history.db 의 search_log)"""
import sqlite3, json, os, sys, time, collections
ROOT=os.path.join(os.path.dirname(__file__),'..'); days=int(sys.argv[1]) if len(sys.argv)>1 else 30
db=json.load(open(os.path.join(ROOT,'data','db.json'),encoding='utf8')); NM={str(i['id']):i['name'] for i in db['items']}
c=sqlite3.connect(os.path.join(ROOT,'data','history.db'))
try: rows=c.execute('SELECT q,conf,s1,s2,top,clicked,helpful,ai FROM search_log WHERE ts>=?',(int(time.time())-days*86400,)).fetchall()
except sqlite3.OperationalError: sys.exit('search_log 가 아직 없습니다(검색 기록 없음).')
n=len(rows); print(f'최근 {days}일 검색 {n}건')
if not n: sys.exit()
cf=collections.Counter(r[1] for r in rows); print('신뢰도:',{k:f'{v}({v*100//n}%)' for k,v in cf.items()})
fb=[r for r in rows if r[6] is not None]; print(f'도움됨 응답 {len(fb)}건: 👍{sum(r[6] for r in fb)} 👎{len(fb)-sum(r[6] for r in fb)}')
def show(t,L,f):
    print(f'\n■ {t} ({len(L)})')
    for x in L[:30]: print('  ',f(x))
cnt=lambda L: collections.Counter(r[0] for r in L).most_common()
show('못 찾은 질문(low) — 동의어/키워드 보강 1순위',cnt([r for r in rows if r[1]=='low']),lambda x:f'{x[1]}회  {x[0]}')
show('👎 아니에요 — 1위 결과가 틀린 질문',[r for r in rows if r[6]==0],lambda r:f'{r[0]}  → 1위: '+NM.get(str((json.loads(r[4]) or [''])[0]),'-'))
def wrongclick(r):
    t=json.loads(r[4]) if r[4] else []; return r[5] and t and r[5]!=str(t[0])
show('1위 말고 다른 후보를 고른 질문 — 순위가 틀렸을 가능성',[r for r in rows if wrongclick(r)],lambda r:f'{r[0]}  → 1위 {NM.get(str(json.loads(r[4])[0]),"-")} / 선택 {NM.get(r[5],r[5])}')
show('아슬아슬(1·2위 격차 작음, low 제외)',[r for r in rows if r[1]!='low' and r[2] and r[3] and r[2]<1.15*r[3]],lambda r:f'{r[0]}  ({r[2]:.2f} vs {r[3]:.2f})')
print(f'\nAI 사용 {sum(r[7] for r in rows)}건')
