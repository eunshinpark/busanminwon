"""민원유형 27종(코드표) + 이름/자유문장 기반 자동분류"""
import re
TYPES={'02':'허가','03':'면허','04':'신고','05':'승인','06':'인정','07':'검사','08':'등록','09':'확인','10':'증명','11':'이의','12':'보고','13':'교부','14':'추천','15':'진정','16':'질의','17':'건의','18':'신청','19':'요구','20':'청원','21':'검정','22':'특허','23':'지정','24':'시험','25':'신고수리','26':'제출','27':'인증','28':'청구','99':'기타'}
# 유형 -> 이름/문장에서 찾을 어간들
KEYS={
 '13':['재발급','재교부','교부','발급','재발행'],
 '25':['신고수리'],'11':['이의'],'20':['청원'],'15':['진정'],'17':['건의','제안'],
 '16':['질의','문의','궁금','알고 싶','알려'],'28':['청구'],'22':['특허'],'03':['면허'],
 '02':['허가'],'05':['승인','인가'],'06':['인정'],'21':['검정'],'07':['검사'],'24':['시험'],
 '27':['인증'],'23':['지정'],'14':['추천'],'10':['증명'],'09':['확인'],'08':['등록'],
 '04':['신고','폐업','휴업','영업재개','지위승계'],'12':['보고','통보'],'26':['제출'],'19':['요구'],
 '18':['신청','지원','의뢰'],
}
GENERIC={'18','19','16'}  # 다른 키워드가 있으면 뒤로 미루는 일반어
def _norm(s): return re.sub(r'\s+','',s)
def classify_name(name):
    """민원사무명(공식 명칭) 분류. (code, 근거) 반환"""
    n=_norm(name)
    # 재발급/재교부는 항상 '교부'
    m=re.search(r'재발급|재교부|재발행|교부(?!금)',n)
    if m: return '13', m.group()
    hits=[]
    for code,ks in KEYS.items():
        for k in ks:
            for m in re.finditer(re.escape(k),n): hits.append((m.start(),code,k))
    if not hits: return '99',''
    strong=[h for h in hits if h[1] not in GENERIC]
    pool=strong or hits
    # 명칭은 끝부분의 행위어가 핵심 -> 가장 뒤에 나온 키워드, 같은 위치면 긴 키워드
    pool.sort(key=lambda h:(h[0]+len(h[2]),len(h[2])))
    p=pool[-1]; return p[1],p[2]
def classify_text(text,top=3):
    """자유 문장 분류 -> [(code, score, 근거)]"""
    t=_norm(text); sc={}
    for code,ks in KEYS.items():
        for k in ks:
            if _norm(k) in t:
                w=0.4 if code in GENERIC else 1.0
                if code=='13' and k=='발급': w=0.7
                sc.setdefault(code,[0,[]]); sc[code][0]+=w; sc[code][1].append(k)
    if re.search(r'어떻게|방법|절차|궁금|문의|알려|되나요|인가요',t):
        sc.setdefault('16',[0,[]]); sc['16'][0]+=0.3; sc['16'][1].append('문의형 표현')
    if re.search(r'불편|개선|바랍니다|바라|제안',t):
        sc.setdefault('17',[0,[]]); sc['17'][0]+=0.5; sc['17'][1].append('건의형 표현')
    if re.search(r'억울|부당|잘못|시정|처분.*불복',t):
        sc.setdefault('11',[0,[]]); sc['11'][0]+=0.5; sc['11'][1].append('불복형 표현')
    if not sc: return [('99',0.0,[])]
    tot=sum(v[0] for v in sc.values())
    out=sorted(((c,v[0]/tot,v[1]) for c,v in sc.items()),key=lambda x:-x[1])
    return out[:top]
