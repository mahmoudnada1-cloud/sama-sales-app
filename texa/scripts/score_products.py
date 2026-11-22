#!/usr/bin/env python3
"""درجة SEO ودرجة GEO لكل منتج من الكتالوج الحي (data/live-after) + الكلمات والعناوين المطبّقة.
درجة SEO هنا تقدير بقائمة فحص على غرار اختبارات Rank Math، وليست الرقم الذي يعرضه Rank Math في المحرر."""
import csv, glob, html, json, os, re, statistics, collections, urllib.parse, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import before_after as ba
csv.field_size_limit(10 ** 9)
B = ba.B
txt = ba.txt
CLAIMS = [v for k, v in ba.CL.items() if k not in ('سعر مكتوب داخل الوصف', 'عبارة داخلية أمام العميل', 'ثبات اللون / لا يبهت')]

SEO = [('kw_title', 'الكلمة المفتاحية في عنوان SEO', 10), ('kw_title_start', 'الكلمة في أول العنوان', 3),
       ('kw_meta', 'الكلمة في الوصف التعريفي', 8), ('kw_url', 'الكلمة في الرابط', 8),
       ('kw_first', 'الكلمة في أول 10% من الوصف', 8), ('kw_content', 'الكلمة في الوصف', 5),
       ('len', 'طول الوصف (600 كلمة = كامل)', 10), ('kw_h', 'الكلمة في عنوان فرعي', 6),
       ('kw_alt', 'الكلمة في النص البديل للصورة', 5), ('density', 'كثافة الكلمة 0.5–2.5%', 6),
       ('internal', 'رابط داخلي', 6), ('external', 'رابط خارجي', 5), ('title_len', 'طول العنوان ≤ 60 حرفاً', 5),
       ('meta_len', 'طول الوصف التعريفي 120–160', 5), ('short_par', 'فقرات قصيرة', 5), ('kw_unique', 'كلمة مفتاحية غير مكررة في منتج آخر', 5)]
GEO = [('answer', 'فقرة إجابة مباشرة في أول الوصف', 12), ('specs', 'جدول مواصفات', 12), ('numbers', 'أرقام محسوبة (تغطية/كمية)', 12),
       ('faq', 'أسئلة وأجوبة', 12), ('limits', 'أين يصلح وأين لا يصلح والعيوب', 10), ('claims', 'بلا ادعاءات غير موثقة', 10),
       ('internal', 'رابط داخلي للقسم', 6), ('alt', 'نص بديل لكل الصور', 6), ('images', 'صورتان أو أكثر', 8), ('reviews', 'تقييم واحد على الأقل', 12)]


def geo(p):
    H = p['description'] or ''; T = txt(H); S = txt(p['short_description'])
    first = re.match(r'\s*<p[^>]*>(.*?)</p>', H, re.S)
    r = {'answer': bool(first and len(txt(first.group(1)).split()) >= 15),
         'specs': '<table' in H, 'numbers': 'م²' in T or bool(re.search(r'\d+ ÷ \d', T)),
         'faq': len(re.findall(r'<h3[^>]*>[^<]*؟', H)) >= 2 or 'أسئلة شائعة' in T,
         'limits': 'عيوب' in T, 'claims': not any(re.search(c, T + ' ' + S) for c in CLAIMS),
         'internal': 'href="https://texadecore.store' in H,
         'alt': bool(p['images']) and all((im.get('alt') or '').strip() for im in p['images']),
         'images': len(p['images']) >= 2, 'reviews': (p.get('review_count') or 0) > 0}
    return r


def seo(p, m, kw_count):
    kw = (m.get('kw') or '').strip(); H = p['description'] or ''; T = txt(H); W = T.split(); n = len(W)
    title, meta = m.get('title', ''), m.get('meta', '')
    slug = urllib.parse.unquote(p['permalink'].rstrip('/').rsplit('/', 1)[-1]).replace('-', ' ')
    r = dict.fromkeys([k for k, _, _ in SEO], 0.0)
    if not kw:
        return r
    c = T.count(kw); d = c * 100.0 / n if n else 0
    heads = ' '.join(txt(x) for x in re.findall(r'<h[2-4][^>]*>(.*?)</h[2-4]>', H, re.S))
    pars = [len(txt(x).split()) for x in re.findall(r'<p[^>]*>(.*?)</p>', H, re.S)]
    alts = ' '.join((im.get('alt') or '') for im in p['images'])
    r.update(kw_title=kw in title, kw_title_start=kw in title[:max(len(title) // 2, len(kw))], kw_meta=kw in meta,
             kw_url=kw in slug, kw_first=kw in ' '.join(W[:max(n // 10, 40)]), kw_content=c > 0,
             len=1 if n >= 600 else 0.6 if n >= 400 else 0.3 if n >= 250 else 0, kw_h=kw in heads, kw_alt=kw in alts,
             density=0.5 <= d <= 2.5, internal='href="https://texadecore.store' in H,
             external=bool(re.search(r'href="https?://(?!texadecore\.store)', H)), title_len=0 < len(title) <= 60,
             meta_len=120 <= len(meta) <= 160, short_par=bool(pars) and max(pars) <= 120, kw_unique=kw_count[kw] == 1)
    return {k: float(v) for k, v in r.items()}


def total(r, spec):
    return round(sum(r[k] * w for k, _, w in spec))


def main():
    L = ba.load('live-after'); A = ba.load('raw')
    metas = {}
    for r in csv.DictReader(open(f'{B}/plugin/texa-desc-import/data/products-v5-200-all-families.csv', encoding='utf-8-sig')):
        metas[int(r['ID'])] = dict(kw=r['Meta: rank_math_focus_keyword'], title=r['Meta: rank_math_title'], meta=r['Meta: rank_math_description'])
    kwc = collections.Counter(m['kw'].strip() for m in metas.values())
    rows = []; fails = {'seo': collections.Counter(), 'geo': collections.Counter()}
    for i in sorted(L):
        p = L[i]; g = geo(p); gb = geo(A[i]) if i in A else None
        s = seo(p, metas[i], kwc) if i in metas else None
        for k, v in g.items():
            if not v: fails['geo'][k] += 1
        if s:
            for k, v in s.items():
                if v < 1: fails['seo'][k] += 1
        rows.append(dict(id=i, name=p['name'], url=urllib.parse.unquote(p['permalink']), cats=[c['id'] for c in p['categories']],
                         seo=total(s, SEO) if s else None, geo=total(g, GEO), geo_before=total(gb, GEO) if gb else None,
                         words=len(txt(p['description']).split()),
                         seo_missing='، '.join(n for k, n, _ in SEO if s and s[k] < 1) if s else 'خارج النموذج',
                         geo_missing='، '.join(n for k, n, _ in GEO if not g[k])))
    with open(f'{B}/data/out/product-scores.csv', 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh); w.writerow(['ID', 'المنتج', 'الرابط', 'SEO %', 'GEO % قبل', 'GEO % بعد', 'عدد الكلمات', 'ينقص SEO', 'ينقص GEO'])
        for r in rows: w.writerow([r['id'], r['name'], r['url'], r['seo'], r['geo_before'], r['geo'], r['words'], r['seo_missing'], r['geo_missing']])
    links = json.load(open(f'{B}/data/category-links.json'))
    cname = {}
    for p in L.values():
        for c in p['categories']: cname[c['id']] = c['name']
    def depth(n):
        u = links.get(n, ''); path = urllib.parse.unquote(u).split('/product-category/')[-1].strip('/').split('/') if u else []
        return path
    cats = []
    for cid, n in cname.items():
        rs = [r for r in rows if cid in r['cats']]
        ss = [r['seo'] for r in rs if r['seo'] is not None]
        path = depth(n)
        cats.append(dict(id=cid, name=n, level='رئيسي' if len(path) <= 1 else 'فرعي', parent_slug=path[0] if len(path) > 1 else '',
                         products=len(rs), seo=round(statistics.mean(ss)) if ss else None, seo_min=min(ss) if ss else None,
                         geo=round(statistics.mean(r['geo'] for r in rs)), geo_before=round(statistics.mean(r['geo_before'] for r in rs if r['geo_before'] is not None))))
    cats.sort(key=lambda c: -c['products'])
    S = [r['seo'] for r in rows if r['seo'] is not None]; G = [r['geo'] for r in rows]; Gb = [r['geo_before'] for r in rows if r['geo_before'] is not None]
    band = lambda xs: {'90-100': sum(x >= 90 for x in xs), '80-89': sum(80 <= x < 90 for x in xs), '70-79': sum(70 <= x < 80 for x in xs), '<70': sum(x < 70 for x in xs)}
    out = dict(products=len(rows), seo=dict(mean=round(statistics.mean(S), 1), median=statistics.median(S), min=min(S), max=max(S), bands=band(S)),
               geo=dict(mean=round(statistics.mean(G), 1), median=statistics.median(G), min=min(G), max=max(G), bands=band(G)),
               geo_before=dict(mean=round(statistics.mean(Gb), 1), median=statistics.median(Gb), bands=band(Gb)),
               seo_fail={n: fails['seo'][k] for k, n, _ in SEO}, geo_fail={n: fails['geo'][k] for k, n, _ in GEO},
               seo_weights={n: w for _, n, w in SEO}, geo_weights={n: w for _, n, w in GEO}, categories=cats)
    json.dump(out, open(f'{B}/data/out/product-scores-summary.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'categories'}, ensure_ascii=False, indent=1))
    print(sum(c['level'] == 'رئيسي' for c in cats), 'main', [c['name'] for c in cats if c['level'] == 'رئيسي'])


if __name__ == '__main__':
    main()
