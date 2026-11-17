import zipfile, re, sys, json
import xml.etree.ElementTree as etree
NS={'hp':'http://www.hancom.co.kr/hwpml/2011/paragraph'}
def text(el):
    return ''.join(t.text or '' for t in el.iter('{%s}t'%NS['hp']))
def cell_text(tc):
    ps=tc.findall('.//hp:p',NS)
    return '\n'.join(text(p) for p in ps if tc.find('hp:subList',NS) is not None)
z=zipfile.ZipFile(sys.argv[1])
root=etree.fromstring(z.read('Contents/section0.xml'))
out=[]
for ti,tbl in enumerate(root.iter('{%s}tbl'%NS['hp'])):
    rows=[]
    for tr in tbl.findall('hp:tr',NS):
        row=[]
        for tc in tr.findall('hp:tc',NS):
            sl=tc.find('hp:subList',NS)
            row.append('\n'.join(text(p) for p in sl.findall('hp:p',NS)))
        rows.append(row)
    out.append(rows)
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False)
for i,t in enumerate(out): print(i,len(t),[len(r) for r in t[:3]])
