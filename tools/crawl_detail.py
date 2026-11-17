"""민원편람 상세보기 '내용' 본문(관련법규·안내사항·기타사항 등)을 data/cache/d*.html 에서 추출 -> data/manual_detail.json {id: 본문}.
첨부파일은 쓰지 않음. 네트워크 사용 안 함(상세 페이지는 tools/crawl_manual.py 가 캐시)."""
import re, html, json, os, glob
ROOT=os.path.join(os.path.dirname(__file__),'..','data')
def body(s):
    m=re.search(r'<dl class="form-data-content">(.*?)</dl>',s,re.S)
    if not m: return ''
    b=m.group(1); b=re.sub(r'<dt>.*?</dt>','',b,flags=re.S)
    b=re.sub(r'<br\s*/?>','\n',b); b=re.sub(r'</(p|div|tr|li|h\d)>','\n',b); b=re.sub(r'</t[dh]>',' | ',b)
    b=html.unescape(re.sub(r'<[^>]+>','',b)).replace('\xa0',' ').replace('​','')
    L=[re.sub(r'[ \t　]+',' ',l).strip() for l in b.split('\n')]
    return '\n'.join(l for l in L if l and l not in('|','○'))
if __name__=='__main__':
    out={}
    for f in glob.glob(os.path.join(ROOT,'cache','d*.html')):
        t=body(open(f,encoding='utf8').read())
        if t: out[re.search(r'd(\d+)\.html',f).group(1)]=t[:3500]
    json.dump(out,open(os.path.join(ROOT,'manual_detail.json'),'w',encoding='utf8'),ensure_ascii=False)
    L=sorted(len(v) for v in out.values()); print(len(out),'건 / 중앙값',L[len(L)//2],'/ 최대',L[-1])
