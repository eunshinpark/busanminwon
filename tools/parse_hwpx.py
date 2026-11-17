"""민원목록 hwpx -> data/minwon.json (병합셀 forward-fill, 사전심사표 분리)"""
import zipfile, re, json, sys, os
import xml.etree.ElementTree as ET
NS='{http://www.hancom.co.kr/hwpml/2011/paragraph}'
def ps(el): return ''.join(t.text or '' for t in el.iter(NS+'t'))
def tables(path):
    root=ET.fromstring(zipfile.ZipFile(path).read('Contents/section0.xml'))
    for tbl in root.iter(NS+'tbl'):
        yield [[ '\n'.join(ps(p) for p in tc.find(NS+'subList').findall(NS+'p')) for tc in tr.findall(NS+'tc')] for tr in tbl.findall(NS+'tr')]
def clean(s): return re.sub(r'[　\s]+',' ',s).strip()
def nm(s): return re.sub(r'\s+',' ',s.replace('　',' ')).strip()
def run(path,out):
    T=list(tables(path)); items=[]; pre=[]
    bureau=dept=''
    for ti,t in enumerate(T):
        if ti==0: continue
        if ti==7:
            d=''
            for r in t[2:]:
                if len(r)==5:
                    if clean(r[0]): d=clean(r[0])
                    r=r[1:]
                pre.append(dict(dept=d,name=clean(r[0]),legal=clean(r[1]),pre=clean(r[2]),after=clean(r[3]) if len(r)>3 else ''))
            continue
        main = ti==1
        for r in t[1:]:
            if main: b,d,no,name,fee,per,note=r
            else:
                if len(r)==6: d,no,name,fee,per,note=r; b=''
                elif len(r)==5: d='';no,name,fee,per,note=r; b=''
                else: continue
            if main and clean(b): bureau=clean(b).replace(' ','')
            if not main: bureau=''
            if clean(d): dept=clean(d).replace(' ','')
            if not clean(name): continue
            if all(len(w)==1 for w in name.split()): name=name.replace(' ','')
            items.append(dict(group='본청' if main else '직속기관·사업소',bureau=bureau,dept=dept,no=clean(no),name=clean(name),fee=clean(fee),period=clean(per),note=clean(note)))
    for i,it in enumerate(items): it['id']=i+1
    json.dump(dict(items=items,presurvey=pre),open(out,'w',encoding='utf8'),ensure_ascii=False,indent=0)
    print(len(items),'items',len(pre),'presurvey')
if __name__=='__main__': run(sys.argv[1],sys.argv[2])
