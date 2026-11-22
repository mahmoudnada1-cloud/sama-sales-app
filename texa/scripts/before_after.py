#!/usr/bin/env python3
"""Compare the catalogue snapshot taken before any change (data/raw) with the live catalogue (data/live-after)."""
import json,glob,re,html,collections,statistics,sys,os
B=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(d):
    out={}
    for f in glob.glob(f'{B}/data/{d}/p*.json'):
        for p in json.load(open(f)): out[p['id']]=p
    return out
def txt(h): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',h or ''))).strip()
CL={
 'ادعاء FDA':r'FDA|هيئة الغذاء|إدارة الغذاء',
 'ادعاء الربو والإكزيما':r'الربو|الإكزيما|الأكزيما|الاكزيما',
 'ضمان على المنتج':r'(?<![لو])(?:ال|ب)ضمان|ضمان \d|ضمان على|سنوات ضد عيوب',
 'مقاوم للحريق':r'(?:مقاوم|مقاومة|ضد|يقاوم)\s*(?:لل|ال)?(?:حريق|اشتعال|لهب)',
 'ثبات اللون / لا يبهت':r'ثبات (?:ال)?لون|ثبات لوني|مقاوم للبهتان|لا تبهت|لا يبهت',
 'ادعاء صحي آخر':r'آمن(?:ة|اً)? (?:تمام[اً]+ )?(?:على الأطفال|للأطفال|ومناسب للأطفال|وصحي)|الأمراض التنفسية|حساسية الجلد|مضاد للبكتيريا|الفورمالدهايد',
 'سعر مكتوب داخل الوصف':r'\d+\s*(?:ريال|﷼|ر\.س)',
 'عبارة داخلية أمام العميل':r'حسب وصف المنتج|في بيانات المتجر|بقيم مختلفة في بيانات',
}
def measure(P,ids):
    r=collections.OrderedDict(); T={i:txt(P[i]['description']) for i in ids}; H={i:P[i]['description'] or '' for i in ids}
    w=[len(T[i].split()) for i in ids]
    r['وسيط عدد كلمات الوصف']=int(statistics.median(w))
    r['منتجات وصفها 600 كلمة أو أكثر']=sum(x>=600 for x in w)
    r['منتجات فيها جدول مواصفات']=sum('<table' in H[i] for i in ids)
    r['منتجات فيها أسئلة وأجوبة']=sum(bool(re.search(r'<h3[^>]*>[^<]*؟',H[i])) or 'أسئلة شائعة' in T[i] for i in ids)
    r['منتجات فيها رابط داخلي']=sum('href=' in H[i] for i in ids)
    r['منتجات فيها دليل العائلة']=sum('txa-family' in H[i] for i in ids)
    r['منتجات فيها مساحة تغطية محسوبة (م²)']=sum(bool(re.search(r'م²',T[i])) for i in ids)
    r['منتجات فيها قسم يصلح/لا يصلح والعيوب']=sum('عيوب' in T[i] for i in ids)
    for k,p in CL.items(): r[k]=sum(bool(re.search(p,T[i]+' '+txt(P[i]['short_description']))) for i in ids)
    r['منتجات فيها صورة بلا نص بديل']=sum(any(not (im.get('alt') or '').strip() for im in P[i]['images']) for i in ids)
    r['منتجات بلا أي تقييم']=sum((P[i].get('review_count') or 0)==0 for i in ids)
    r['منتجات بصورة واحدة فقط']=sum(len(P[i]['images'])==1 for i in ids)
    sent=collections.Counter(); per={}
    for i in ids:
        ss=[s.strip() for s in re.split(r'[.؟!\n]| {2,}',T[i]) if len(s.strip())>40]; per[i]=ss
        for s in set(ss): sent[s]+=1
    ratios=[sum(1 for s in ss if sent[s]>=20)/len(ss) for ss in per.values() if ss]
    r['وسيط نسبة الجمل المكررة في 20 منتجاً أو أكثر']=f'{statistics.median(ratios)*100:.0f}%'
    return r
if __name__=='__main__':
    A=load('raw'); L=load('live-after'); ids=sorted(set(A)&set(L))
    print('before',len(A),'after',len(L),'common',len(ids),'only before',len(set(A)-set(L)),'only after',len(set(L)-set(A)))
    chg=collections.Counter(); bad=collections.defaultdict(list)
    for i in ids:
        a,l=A[i],L[i]
        for k,f in (('name',lambda p:p['name']),('price',lambda p:p['prices']['price']),('regular_price',lambda p:p['prices']['regular_price']),('sale_price',lambda p:p['prices']['sale_price']),('stock',lambda p:p['is_in_stock']),('categories',lambda p:sorted(c['id'] for c in p['categories'])),('images',lambda p:[x['id'] for x in p['images']]),('permalink',lambda p:p['permalink']),('sku',lambda p:p['sku']),('description',lambda p:p['description']),('short_description',lambda p:p['short_description'])):
            if f(a)!=f(l): chg[k]+=1; bad[k].append(i)
    print('changed fields:',dict(chg))
    for k in ('name','price','regular_price','sale_price','stock','categories','images','permalink','sku'):
        if bad[k]: print('  ',k,bad[k][:15])
    b=measure(A,ids); a=measure(L,ids)
    out={'common':len(ids),'changed':dict(chg),'changed_ids':{k:v for k,v in bad.items() if k not in('description','short_description')},'before':b,'after':a}
    json.dump(out,open(f'{B}/data/out/before-after.json','w'),ensure_ascii=False,indent=1)
    for k in b: print(f'{k} | {b[k]} | {a[k]}')
