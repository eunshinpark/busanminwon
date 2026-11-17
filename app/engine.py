"""민원 검색/안내 엔진: 문자 bigram TF-IDF + 동의어 확장 + 유형 분류 + 답변 초안"""
import json, math, os, re, sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'..'))
from app.types import TYPES, classify_text
DB=json.load(open(os.path.join(os.path.dirname(__file__),'..','data','db.json'),encoding='utf8'))
ITEMS=DB['items']
_ph={}
for _i in ITEMS:
    _p=_i.get('manual',{}).get('phone','')
    if _p: _ph.setdefault(_i['dept'],{}).setdefault(_p,0); _ph[_i['dept']][_p]+=1
DEPT_PHONE={d:max(v,key=v.get) for d,v in _ph.items()}
STOP=re.compile(r'(많이|어요|너무|엄청|나왔|나옴|나와요|나오|이상해|이상하|하고\s*싶|하려고|하려는데|하려면|하는\s*방법|어떻게|알려\s*주세요|알려주세요|궁금합니다|궁금해요|문의|민원|부탁|드립니다|입니다|해요|하나요|인가요|되나요|합니다|싶어요|싶습니다|좀|저는|제가|우리|회사|업체|에서|으로|에게|이|가|은|는|을|를|의|도|와|과)')
SYN={'많이 나':'이의신청','많이나':'이의신청','과다':'이의신청','잘못 나':'이의신청','틀리':'이의신청','억울':'이의신청','부당':'이의신청','요금폭탄':'상수도요금 이의신청','택시':'개인택시 여객자동차','버스':'여객자동차','렌트카':'자동차대여','렌터카':'자동차대여','분실':'재발급','잃어':'재발급','잃어버':'재발급','재발행':'재발급','재교부':'재발급',
     '폐업':'폐업신고','휴업':'휴업신고','자동차':'자동차','엘리베이터':'승강기','엘베':'승강기','소방':'소방','헬스장':'체육시설업','수영장':'체육시설업','골프':'체육시설업',
     '건설면허':'건설업등록','공사업체':'공사업','전기공사':'전기공사업','통신공사':'정보통신공사업','노조':'노동조합','수도요금':'상수도요금','수도':'상수도','물값':'상수도요금',
     '묘지':'묘지 장사','납골':'봉안','장례':'장례','어업':'어업','어선':'어선','낚시':'낚시','항만':'항만','공유수면':'공유수면','건축사':'건축사','측량':'측량','다단계':'다단계판매업',
     '정수기':'정수기','생수':'먹는샘물','신문사':'신문사업','인터넷신문':'인터넷신문','요양보호사':'요양보호사','안마':'안마사','공원':'공원','도서관':'도서관','박물관':'박물관','미술관':'미술관',
     '쓰레기':'폐기물','폐기물':'폐기물','환경':'환경','소음':'소음','대기':'대기','위험물':'위험물','주유소':'석유판매업','택배':'물류','주택':'주택','아파트':'공동주택','재개발':'정비사업','재건축':'정비사업'}
def toks(s):
    s=re.sub(r'[^0-9A-Za-z가-힣]','',s); return [s[i:i+2] for i in range(len(s)-1)] or ([s] if s else [])
def doc_text(it):
    m=it.get('manual',{})
    return it['name']+' '+it['name']+' '+it['dept']+' '+it['bureau']+' '+it['typeName']+' '+m.get('title','')+' '+m.get('field','')+' '+m.get('category','')
DT=[toks(doc_text(i)) for i in ITEMS]
DF={}
for t in DT:
    for g in set(t): DF[g]=DF.get(g,0)+1
N=len(ITEMS); IDF=lambda g: math.log((N+1)/(DF.get(g,0)+0.5))
NAMEKEY=[re.sub(r'[^0-9A-Za-z가-힣]','',i['name']) for i in ITEMS]
def expand(q):
    ex=q
    for k,v in SYN.items():
        if k in q: ex+=' '+v
    return ex
def intent_terms(q):
    return {w for k,v in SYN.items() if k in q for w in v.split() if w.endswith('이의신청')}   # 동의어가 가리키는 구체 민원어(예: 이의신청)
def search(q,k=5):
    qc=re.sub(STOP,' ',q); qx=expand(qc)+' '+' '.join(intent_terms(q)); it_=intent_terms(q)
    qt=set(toks(qx)); qk=re.sub(r'[^0-9A-Za-z가-힣]','',qc)
    if not qt: return []
    res=[]
    for i,(it,dt) in enumerate(zip(ITEMS,DT)):
        ds=set(dt); hit=qt&ds
        if not hit: continue
        sc=sum(IDF(g) for g in hit)/ (sum(IDF(g) for g in qt)+1e-9)       # 질의 커버리지
        nk=NAMEKEY[i]; sc2=sum(IDF(g) for g in hit if g in set(toks(it['name'])))/(sum(IDF(g) for g in set(toks(it['name'])))+1e-9)
        score=0.6*sc+0.4*sc2
        if any(w in nk for w in it_): score+=0.15
        if nk and (nk in qk or (len(qk)>=4 and qk in nk)): score+=0.35
        res.append((score,i))
    res.sort(key=lambda x:-x[0]); return res[:k]
def fmt_fee(f): return f or '정보 없음'
def card(it,score):
    m=it.get('manual',{})
    files=m.get('files',[])
    return dict(id=it['id'],name=it['name'],score=round(score,3),group=it['group'],bureau=it['bureau'],dept=it['dept'],phone=m.get('phone','') or DEPT_PHONE.get(it['dept'],''),
        fee=it['fee'],period=it['period'],note=it['note'],type=it['type'],typeName=it['typeName'],typeWhy=it['typeWhy'],
        manualUrl=m.get('url',''),manualField=m.get('field',''),files=files,window=it.get('window'),onestop=it.get('onestop',False),presurvey=it.get('presurvey'),
        manualMatch=m.get('match',0))
def draft(q,top,typ):
    if not top: return ''
    t=top
    lines=[f"안녕하십니까. 부산광역시 민원 담당입니다.",f"문의하신 「{t['name']}」 건은 {t['dept']}"+(f"(☎ {t['phone']})" if t['phone'] else '')+"에서 담당하고 있습니다.",
           f"- 민원유형: {t['typeName']}",f"- 처리기간: {t['period']}",f"- 수수료: {t['fee']}"]
    if t['files']: lines.append("- 신청서식: 부산민원120 민원편람에서 내려받으실 수 있습니다. ("+t['manualUrl']+")")
    if t['window']: lines.append(f"- 방문·접수: 통합민원과 {t['window']['window']} (☎ {t['window']['phone']})")
    lines.append("법령 개정 등으로 내용이 달라질 수 있으니 접수 전 담당 부서에 확인해 주시기 바랍니다. 감사합니다.")
    return '\n'.join(lines)
def answer(q,k=5):
    q=q.strip(); r=search(q,k); cards=[card(ITEMS[i],s) for s,i in r]
    cl=classify_text(q)
    topcard=cards[0] if cards else None
    sc2=cards[1]['score'] if len(cards)>1 else 0
    clear=bool(topcard) and topcard['score']>=0.15 and topcard['score']>=1.25*sc2   # 점수는 낮아도 2위와 격차가 뚜렷하면 신뢰
    conf='high' if topcard and topcard['score']>=0.7 else 'mid' if topcard and (topcard['score']>=0.3 or clear) else 'low'
    return dict(query=q,confidence=conf,results=cards,
        inputType=[dict(code=c,name=TYPES[c],ratio=round(p,2),why=w) for c,p,w in cl],
        draft=draft(q,topcard,None) if conf!='low' else '',
        notice='' if conf!='low' else '이 목록(부산시 본청·직속기관·사업소 민원 544건)에서 정확히 일치하는 민원을 찾지 못했습니다. 구·군청 소관(예: 음식점·미용업 영업신고, 주민등록 등)일 수 있으니 부산시 120콜센터(지역번호 051 + 120)로 문의해 주세요.')
