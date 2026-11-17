"""표준 라이브러리만 사용하는 웹서버:  python3 app/server.py [포트]"""
import json, os, re, sqlite3, sys, time, mimetypes, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))
from app import engine, llm, categories
WEB=os.path.join(os.path.dirname(__file__),'..','web')
CATOF={i['id']:categories.categorize(i) for i in engine.ITEMS}
DB=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','data','history.db')
CID=re.compile(r'^[A-Za-z0-9_-]{16,64}$'); KEEP=50
def _db():
    c=sqlite3.connect(DB,timeout=5); c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,cid TEXT NOT NULL,q TEXT NOT NULL,ts INTEGER NOT NULL)')
    c.execute('CREATE INDEX IF NOT EXISTS ix_hist ON history(cid,ts)'); return c
def hist_add(cid,q):
    q=q.strip()[:200]
    if not (CID.match(cid or '') and q): return
    with _db() as c:
        c.execute('DELETE FROM history WHERE cid=? AND q=?',(cid,q)); c.execute('INSERT INTO history(cid,q,ts) VALUES(?,?,?)',(cid,q,int(time.time())))
        c.execute('DELETE FROM history WHERE cid=? AND id NOT IN (SELECT id FROM history WHERE cid=? ORDER BY id DESC LIMIT ?)',(cid,cid,KEEP))
def hist_get(cid,n=10):
    if not CID.match(cid or ''): return []
    with _db() as c: return [r[0] for r in c.execute('SELECT q FROM history WHERE cid=? ORDER BY id DESC LIMIT ?',(cid,n))]
def view_add(iid):
    with _db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS item_views(item_id TEXT PRIMARY KEY,n INTEGER NOT NULL DEFAULT 0)')
        c.execute('INSERT INTO item_views(item_id,n) VALUES(?,1) ON CONFLICT(item_id) DO UPDATE SET n=n+1',(str(iid),))
SL_DAYS=90
_PII=[(re.compile(r'[\w.+-]+@[\w-]+(\.[\w-]+)+'),'[메일]'),(re.compile(r'\d[\d\- ]{5,}\d'),'[숫자]')]
def mask(q):
    for rg,t in _PII: q=rg.sub(t,q)
    return q
def _sl(c):
    c.execute('CREATE TABLE IF NOT EXISTS search_log(id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER NOT NULL,q TEXT NOT NULL,conf TEXT,s1 REAL,s2 REAL,top TEXT,clicked TEXT,helpful INTEGER,ai INTEGER NOT NULL DEFAULT 0)')
    c.execute('CREATE INDEX IF NOT EXISTS ix_sl_ts ON search_log(ts)')
def log_add(q,r):
    """검색 1건 기록(사용자 식별자 없음, 전화·메일 마스킹). 검색 품질 분석용. 90일 지난 행은 삭제."""
    try:
        res=r.get('results') or []; sc=[x['score'] for x in res[:2]]+[0,0]
        with _db() as c:
            _sl(c); now=int(time.time())
            cur=c.execute('INSERT INTO search_log(ts,q,conf,s1,s2,top) VALUES(?,?,?,?,?,?)',(now,mask(q)[:200],r.get('confidence'),sc[0],sc[1],json.dumps([x['id'] for x in res[:3]])))
            if cur.lastrowid%200==0: c.execute('DELETE FROM search_log WHERE ts<?',(now-SL_DAYS*86400,))
            return cur.lastrowid
    except Exception as e: print('log error',type(e).__name__,str(e)[:100],flush=True)
def log_set(lid,**kw):
    try:
        lid=int(lid)
        with _db() as c:
            _sl(c)
            for k,v in kw.items(): c.execute(f'UPDATE search_log SET {k}=? WHERE id=?',(v,lid))
    except Exception as e: print('log error',type(e).__name__,str(e)[:100],flush=True)
def hot_ids(n=5):
    try:
        with _db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS item_views(item_id TEXT PRIMARY KEY,n INTEGER NOT NULL DEFAULT 0)')
            return [r[0] for r in c.execute('SELECT item_id FROM item_views WHERE n>=2 ORDER BY n DESC,item_id LIMIT ?',(n,))]
    except Exception: return []
def hist_rows(cid,n=50):
    if not CID.match(cid or ''): return []
    with _db() as c: return [dict(q=r[0],ts=r[1]) for r in c.execute('SELECT q,ts FROM history WHERE cid=? ORDER BY id DESC LIMIT ?',(cid,n))]
def hist_del(cid,q):
    if CID.match(cid or ''):
        with _db() as c: c.execute('DELETE FROM history WHERE cid=? AND q=?',(cid,q))
def hist_clear(cid):
    if CID.match(cid or ''):
        with _db() as c: c.execute('DELETE FROM history WHERE cid=?',(cid,))
class H(BaseHTTPRequestHandler):
    def _json(self,obj,code=200):
        b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u=urllib.parse.urlparse(self.path); qs=urllib.parse.parse_qs(u.query)
        if u.path=='/api/search':
            q=(qs.get('q',[''])[0])[:500]
            if not q.strip(): return self._json(dict(results=[]))
            r=engine.answer(q); r['lid']=log_add(q,r)
            if r.get('results'):
                try:
                    hist_add(qs.get('cid',[''])[0],q)
                    if r.get('confidence')!='low': view_add(r['results'][0]['id'])
                except Exception as e: print('history error',type(e).__name__,str(e)[:100],flush=True)
            return self._json(r)
        if u.path=='/api/history':
            try:
                try: n=min(50,max(1,int(qs.get('n',['10'])[0])))
                except ValueError: n=10
                rows=hist_rows(qs.get('cid',[''])[0],n); return self._json(dict(items=[r['q'] for r in rows],rows=rows))
            except Exception as e: print('history error',type(e).__name__,str(e)[:100],flush=True); return self._json(dict(items=[]))
        if u.path=='/api/ai':
            q=(qs.get('q',[''])[0])[:500].strip()
            if not llm.enabled(): return self._json(dict(enabled=False))
            if not q: return self._json(dict(enabled=True,error='empty'))
            ip=self.headers.get('X-Real-IP') or self.client_address[0]
            if not llm.allowed(ip): return self._json(dict(enabled=True,error='한 시간 이용 한도를 넘었습니다. 잠시 후 다시 시도해 주세요.'),429)
            try:
                a=engine.answer(q)
                if a['confidence']=='low': return self._json(dict(enabled=True,skipped=True))
                if qs.get('lid',[''])[0].isdigit(): log_set(qs['lid'][0],ai=1)
                return self._json(dict(enabled=True,**llm.generate(q,a['results'])))
            except Exception as e:
                print('ai error',type(e).__name__,str(e)[:200],flush=True); return self._json(dict(enabled=True,error='AI 응답을 받지 못했습니다. 아래 기본 안내를 이용해 주세요.'),502)
        if u.path=='/api/meta':
            nm={str(i['id']):i['name'] for i in engine.ITEMS}
            return self._json(dict(types=engine.DB['types'],meta=engine.DB['meta'],count=len(engine.ITEMS),ai=llm.enabled(),windows=engine.DB['windows'],popular=[nm[x] for x in hot_ids(5) if x in nm]))
        if u.path=='/api/browse':
            t=qs.get('type',[''])[0]; d=qs.get('dept',[''])[0]
            kw=qs.get('kw',[''])[0][:100].lower().split()
            try: off=max(0,int(qs.get('offset',['0'])[0])); lim=min(100,max(1,int(qs.get('limit',['300'])[0])))
            except ValueError: off,lim=0,300
            ok=lambda i:(not t or i['type']==t) and (not d or i['dept']==d) and all(w in (i['name']+' '+i['dept']+' '+i['typeName']).lower() for w in kw)
            r=[i for i in engine.ITEMS if ok(i)]
            if qs.get('slim'): return self._json(dict(results=[dict(id=i['id'],name=i['name'],bureau=i['bureau'],dept=i['dept'],typeName=i['typeName'],period=i['period'],cat=CATOF.get(i['id'],'일반·행정'),onestop=bool(i.get('onestop')),file=bool(i.get('manual',{}).get('files'))) for i in r],total=len(r),cats=categories.CATS,hot=hot_ids()))
            return self._json(dict(results=[engine.card(i,0) for i in r[off:off+lim]],total=len(r)))
        if u.path=='/api/item':
            it=next((i for i in engine.ITEMS if str(i['id'])==qs.get('id',[''])[0]),None)
            if it:
                try: view_add(it['id'])
                except Exception: pass
            return self._json(engine.card(it,0)) if it else self._json(dict(error='not found'),404)
        p=os.path.normpath(os.path.join(WEB,'index.html' if u.path=='/' else u.path.lstrip('/')))
        if not p.startswith(os.path.abspath(WEB)) or not os.path.isfile(p): self.send_error(404); return
        b=open(p,'rb').read(); self.send_response(200); self.send_header('Content-Type',(mimetypes.guess_type(p)[0] or 'text/plain')+'; charset=utf-8' if p.endswith(('.html','.js','.css')) else (mimetypes.guess_type(p)[0] or 'application/octet-stream'))
        self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        u=urllib.parse.urlparse(self.path)
        if u.path=='/api/history/clear':
            try:
                n=min(int(self.headers.get('Content-Length') or 0),1024); cid=(json.loads(self.rfile.read(n) or b'{}') or {}).get('cid','')
                hist_clear(cid); return self._json(dict(ok=True))
            except Exception as e: print('history error',type(e).__name__,str(e)[:100],flush=True); return self._json(dict(ok=False),400)
        if u.path=='/api/history/delete':
            try:
                n=min(int(self.headers.get('Content-Length') or 0),2048); d=json.loads(self.rfile.read(n) or b'{}') or {}
                hist_del(d.get('cid',''),str(d.get('q',''))[:200]); return self._json(dict(ok=True))
            except Exception as e: print('history error',type(e).__name__,str(e)[:100],flush=True); return self._json(dict(ok=False),400)
        if u.path=='/api/feedback':
            try:
                n=min(int(self.headers.get('Content-Length') or 0),1024); d=json.loads(self.rfile.read(n) or b'{}') or {}
                lid=int(d.get('lid')); kind=d.get('kind')
                if kind=='click' and re.fullmatch(r'\d{1,8}',str(d.get('id',''))): log_set(lid,clicked=str(d['id']))
                elif kind=='helpful' and d.get('v') in (0,1,True,False): log_set(lid,helpful=int(d['v']))
                else: return self._json(dict(ok=False),400)
                return self._json(dict(ok=True))
            except Exception: return self._json(dict(ok=False),400)
        self.send_error(404)
    def log_message(self,*a): pass
if __name__=='__main__':
    port=int(sys.argv[1]) if len(sys.argv)>1 else 8000
    WEB=os.path.abspath(WEB)
    print(f'http://localhost:{port}'); ThreadingHTTPServer(('127.0.0.1',port),H).serve_forever()
