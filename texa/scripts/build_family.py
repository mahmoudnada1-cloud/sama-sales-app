#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نموذج «عائلة المنتج» (v6): وصف المنتج = طبقة خاصة بالمنتج + طبقة عائلة مكتوبة يدوياً مرة واحدة.

  طبقة المنتج   مولَّدة من بيانات المنتج نفسه (المقاس، التغطية، اللون، النقشة، أرقام محسوبة).
  طبقة العائلة  ملف HTML ثابت: data/family-content/<family_id>.html
  الناتج        data/out/products-v6-<family_id>.csv   (أعمدة v5 نفسها)

التحليل والحساب مستوردان من build_products.py (لا نسخ). حتمي: لا عشوائية ولا تاريخ تشغيل.
لا يتصل بالموقع ولا يكتب أي سعر.

التشغيل:  python3 texa/scripts/build_family.py sb-5mm            (CSV + الأرقام المقيسة)
          python3 texa/scripts/build_family.py sb-5mm --sample    (يطبع وصف منتج واحد كاملاً)
          python3 texa/scripts/build_family.py sb-5mm --stats     (الأرقام المقيسة JSON)
"""
import csv
import json
import math
import os
import re
import statistics
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_products as bp  # noqa: E402

FAMILIES = os.path.join(bp.BASE, 'data', 'families.json')
FAMILY_DIR = os.path.join(bp.BASE, 'data', 'family-content')
USAGE = os.path.join(bp.BASE, 'data', 'usage-classification.csv')

# إعداد كل عائلة: عنوان الفاصل، واسم المنتج العام في فقرة الإجابة. العائلات المدعومة حالياً ألواح جدارية (kind=panel).
FAMILY_CFG = {
    'sb-5mm': dict(guide='دليل بديل الشيبورد 5 ملم', noun='لوح جداري من بديل الشيبورد', noun_alt='تكسية جدران من بديل الشيبورد'),
}
EXTRA_MANUAL = {28812, 29728}          # مكتوبة يدوياً؛ لا تُستورد
DENS_LO, DENS_HI = 0.6, 1.2            # هدف الكثافة في هذا النموذج (يُقاس ولا يُفرض)
EX_WIDTHS = [2.4, 3, 3.6, 4, 4.2, 4.8, 5, 5.4, 6]
EX_HEIGHTS = [2.6, 2.7, 2.8]
FAQ_WIDTHS = [2.5, 3.2, 3.8, 4.5, 5.2, 5.8, 6.5, 7]

SURFACE = {'plain': 'سطحه سادة', 'wood': 'مظهره خشبي', 'fabric': 'ملمسه قماشي', 'marble': 'نقشته رخامية معرّقة',
           'stripe': 'نقشته مخططة', 'wave': 'نقشته مودرن', 'stone': 'ملمسه حجري', 'herringbone': 'نقشته هرمية',
           'glossy': 'سطحه لامع', 'ornament': 'سطحه منقوش'}
# مراجعة مكتبة النصائح: نصائح الهرمي في المولّد مكتوبة للأرضيات، وهذه بديلها للجدران.
WALL_PATTERN_TIPS = {
    'herringbone': ['النقشة الهرمية تضيف حركة للجدار فتكفي وحدها عنصر زينة',
                    'اتجاه رؤوس الأسهم في النقشة الهرمية يُوحَّد بين الألواح المتجاورة',
                    'النقشة الهرمية تبرز على جدار تمييز واحد أكثر من تغطية الغرفة كلها'],
}
SENT_SPLIT = re.compile(r'(?<!\d)\.|\.(?!\d)|[؟!\n]')


def sents(text, minlen=25):
    return [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) > minlen]


def words(html_text):
    return len(bp.clean_text(html_text).split())


def load_usage():
    out = {}
    with open(USAGE, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            out[int(r['id'])] = (r['proposed_usage'].strip(), r['confidence'].strip(), r['evidence'].strip())
    return out


def example(F):
    """جدار المثال: عرض وارتفاع يتنوعان بحسب رقم المنتج. العدد بحساب الأعمدة (اللوح يُركَّب واقفاً)."""
    pid = F['id']
    L, W = max(F['dims']), min(F['dims'])
    Ww = bp.pick(EX_WIDTHS, pid, 'fam-w')
    hs = [h for h in EX_HEIGHTS if h <= L + 1e-9] or [EX_HEIGHTS[0]]
    h = bp.pick(hs, pid, 'fam-h')
    q = Ww / W
    n = int(math.ceil(q - 1e-9))
    exact = abs(q - round(q)) < 1e-9
    cov = L * W
    return dict(L=L, W=W, Ww=Ww, h=h, q=q, n=n, exact=exact, cov=cov, A=Ww * h, tot=n * cov,
                last_cm=round((W - (n * W - Ww)) * 100, 1), cut_cm=round((L - h) * 100, 1))


def answer_paragraph(F, c, ex, cfg):
    name = bp.esc(F['name'])
    noun = cfg['noun_alt'] if 'لوح' in F['name'] else cfg['noun']
    bits = noun
    if not re.search(r'\d\s*(ملم|مم)', F['name']):
        bits += ' بسماكة %s ملم' % c['thick']
    if c['material']:
        bits += '، خامته %s' % bp.esc(c['material'])
    if c['origin']:
        bits += '، ومنشؤه %s' % {'محلي': 'محلي'}.get(c['origin'], c['origin'])
    s1 = '%s: %s.' % (name, bits)
    surf = SURFACE.get(F['pattern'])
    look = []
    if surf:
        look.append(surf)
    if c['cph']:
        look.append('لونه %s' % bp.esc(c['cph']))
    s2 = (' و'.join(look) + '. ') if look else ''
    s3 = 'مقاسه %s × %s سم، فيغطي اللوح الواحد %s م²، وجدار %s × %s م يلزمه %s.' % (
        bp.fnum(ex['W'] * 100, 1), bp.fnum(ex['L'] * 100, 1), bp.fnum(ex['cov']), bp.fnum(ex['Ww'], 1), bp.fnum(ex['h'], 1),
        bp.cnt(ex['n'], 'panel'))
    s4 = ' يليق بـ%s.' % c['rooms']
    s2 = s2[0].upper() + s2[1:] if s2 else ''
    return s1 + ' ' + s2 + s3 + s4


def numbers_section(F, c, ex):
    f = bp.fnum
    li = ['تغطية اللوح الواحد: %s × %s سم = %s م².' % (f(ex['W'] * 100, 1), f(ex['L'] * 100, 1), f(ex['cov']))]
    n_txt = bp.cnt(ex['n'], 'panel')
    lead = 'مثال بحساب الأعمدة لجدار %s × %s م: %s ÷ %s = ' % (f(ex['Ww'], 1), f(ex['h'], 1), f(ex['Ww'], 1), f(ex['W'], 2))
    if ex['exact']:
        li.append(lead + '%d بالضبط، فيلزمك %s دون قص في العرض؛ أضف لوحاً احتياطياً إن كانت زوايا الجدار غير قائمة.' % (ex['n'], n_txt))
    else:
        li.append(lead + '%s، فيلزمك %s، ويُقص الأخير إلى عرض %s سم.' % (f(ex['q'], 2), n_txt, f(ex['last_cm'], 1)))
    li.append('تشتري %s م² لجدار مساحته %s م²، والفرق %s م² يذهب في القص (%s سم من طول كل لوح).' % (
        f(ex['tot'], 2), f(ex['A'], 2), f(ex['tot'] - ex['A'], 2), f(ex['cut_cm'], 1)))
    li.append('أدخل مقاس جدارك في %s لتعرف عددك.' % bp.A(bp.URL_CALC, 'حاسبة الكميات'))
    head = ('أرقام اللوح %s' % bp.esc(F['code'])) if F['code'] else 'أرقام هذا اللوح'
    return head, li


def spec_rows(F, c, usage):
    rows = [r for r in bp.spec_rows(F, c) if r[0] != 'النوع']      # «النوع» واحد في كل العائلة، مكانه طبقة العائلة
    u = usage.get(F['id'])
    if u and u[0] == 'داخلي' and u[1] in ('عالية', 'متوسطة'):
        rows.append(('الاستخدام', 'داخلي (حسب وصف المنتج)'))
    return rows


def tip_section(F, c):
    pid = F['id']
    pat = F['pattern']
    pool = WALL_PATTERN_TIPS.get(pat) or bp.PATTERN_TIPS.get(pat) or bp.SURFACE_DEFAULT['other']
    ptip = bp.pick(pool, pid, 'tip-p')
    if c['has_color'] and F['color'] in bp.COLOR_TIPS:
        col = bp.COLOR_TIPS[F['color']]
        out = '%s %s. %s. %s.' % (c['cd'], bp.pick(col['h'], pid, 'tip-h'), bp.pick(col['a'], pid, 'tip-a'), ptip)
        head = bp.pick(bp.TIP_HEADS, pid, 'tip-head').format(cd=c['cd'])
    else:
        # لون غير مصنَّف: لا نصيحة لونية عامة؛ نكتفي بما يخص النقشة وتوزيع الألواح
        out = '%s. %s.' % (ptip, bp.pick(bp.TYPE_TIPS[c['tipset']][1:], pid, 'tip-t'))
        head = 'تنسيق هذا التصميم'
    return head, bp.esc(out)


def faq_section(F, c, ex, kw):
    pid = F['id']
    f = bp.fnum
    L, W, cov = ex['L'], ex['W'], ex['cov']
    w2 = bp.pick([w for w in FAQ_WIDTHS if abs(w - ex['Ww']) > 0.05], pid, 'fam-w2')
    q2 = w2 / W
    n2 = int(math.ceil(q2 - 1e-9))
    qa = [('كم لوحاً من %s يلزم لجدار عرضه %s م؟' % (bp.esc(kw), f(w2, 1)),
           '%s: %s ÷ %s = %s ويُقرَّب إلى الأعلى، بشرط ألا يزيد ارتفاع الجدار على %s سم.' % (
               bp.cnt(n2, 'panel'), f(w2, 1), f(W, 2), f(q2, 2), f(L * 100, 1)))]
    v = bp.H(pid, 'fam-q2') % 3
    if v == 0:
        h2 = bp.pick([3.0, 3.2], pid, 'fam-h2')
        d = round((h2 - L) * 100, 1)
        if d <= 20:
            fix = 'يغطيها كرنيش أو نعلة بهذا الارتفاع، أو شريط يُقص من لوح إضافي'
        else:
            k = int(math.floor(L * 100 / d + 1e-9))
            fix = 'تُكمَّل بشريط يُقص من لوح إضافي فوق فاصل أفقي، واللوح الإضافي الواحد يعطي %d شرائط بهذا الارتفاع عرض كلٍّ منها %s سم' % (
                k, f(W * 100, 1))
        qa.append(('هل يكفي طول هذا اللوح لجدار ارتفاعه %s م؟' % f(h2, 1),
                   'لا يكفي بقطعة واحدة: طوله %s سم والجدار %s سم، فتبقى %s سم %s.' % (f(L * 100, 1), f(h2 * 100, 1), f(d, 1), fix)))
    elif v == 1:
        ra, rb = bp.pick(bp.ROOMS_FLOOR, pid, 'fam-room')
        P = 2 * (ra + rb)
        n = int(math.ceil(P / W - 1e-9))
        qa.append(('كم لوحاً يلزم لتكسية جدران غرفة %s × %s م كلها؟' % (f(ra, 1), f(rb, 1)),
                   'محيط الغرفة %s م، و%s ÷ %s = %s، أي %s قبل خصم الباب والنوافذ. اطرح عرض الفتحات من المحيط ثم أعد القسمة.' % (
                       f(P, 1), f(P, 1), f(W, 2), f(P / W, 2), bp.cnt(n, 'panel'))))
    else:
        k = bp.pick([4, 5, 6, 7, 8], pid, 'fam-k')
        qa.append(('كم متراً من الجدار تغطي %d ألواح منه؟' % k,
                   '%d × %s = %s م عرضاً بارتفاع حتى %s سم، أي %s م².' % (k, f(W, 2), f(k * W, 2), f(L * 100, 1), f(k * cov, 2))))
    return 'سؤالان عن هذا اللوح', qa


def link_line(F, kw, links, paths, root_name):
    pid, root = F['id'], F['root']
    rname = root_name.get(root)
    subs = []
    for cat in F['cats']:
        p = paths.get(cat)
        if not p or p[0] != root or len(p) < 2 or cat.startswith('عروض'):
            continue
        subs.append((-len(p), bp.H(pid, 'lk-' + cat), cat))
    subs = [s[2] for s in sorted(subs)[:2]]
    root_a = bp.A(links[rname], rname)
    if subs:
        return 'لخيارات قريبة من %s تصفّح %s، أو ارجع إلى قسم %s.' % (
            bp.esc(kw), ' و'.join(bp.A(links[s], s) for s in subs), root_a)
    return 'لخيارات قريبة من %s تصفّح قسم %s.' % (bp.esc(kw), root_a)


def product_layer(F, c, ex, kw, usage, cfg):
    parts = ['<p class="txa-answer">%s</p>' % answer_paragraph(F, c, ex, cfg)]
    nh, nli = numbers_section(F, c, ex)
    parts.append('<h2>%s</h2>' % nh)
    parts.append('<ul>\n' + '\n'.join('<li>%s</li>' % x for x in nli) + '\n</ul>')
    rows = spec_rows(F, c, usage)
    parts.append('<h2>مواصفات %s</h2>' % bp.esc(kw))
    parts.append('<table class="txa-specs">\n<tbody>\n' + '\n'.join(
        '<tr><th scope="row">%s</th><td>%s</td></tr>' % (bp.esc(a), bp.esc(b)) for a, b in rows) + '\n</tbody>\n</table>')
    th, tp = tip_section(F, c)
    parts.append('<h2>%s</h2>' % bp.esc(th))
    parts.append('<p>%s</p>' % tp)
    fh, qa = faq_section(F, c, ex, kw)
    parts.append('<h2>%s</h2>' % fh)
    for q, a in qa:
        parts.append('<h3>%s</h3>' % q)
        parts.append('<p>%s</p>' % a)
    return bp.tidy('\n'.join(parts)), len(rows)


def build(family_id):
    cfg = FAMILY_CFG.get(family_id)
    if not cfg:
        raise SystemExit('عائلة غير مهيأة في FAMILY_CFG: %s' % family_id)
    fam = [f for f in json.load(open(FAMILIES, encoding='utf-8'))['families'] if f['family_id'] == family_id]
    if not fam:
        raise SystemExit('family_id غير موجود في families.json: %s' % family_id)
    fam = fam[0]
    family_html = open(os.path.join(FAMILY_DIR, family_id + '.html'), encoding='utf-8').read().strip()
    links, paths, root_name = bp.load_cat_links()
    usage = load_usage()
    prods = bp.load_products()
    Fs = bp.finalize([bp.extract(p, paths) for p in prods])
    byF = {F['id']: F for F in Fs}
    manual = set(bp.MANUAL_IDS) | EXTRA_MANUAL
    outs, skipped = [], []
    used_titles, used_metas = set(), set()
    for pid in sorted(fam['product_ids']):
        F = byF.get(pid)
        if F is None:
            skipped.append((pid, '', 'غير موجود في البيانات الخام'))
            continue
        if pid in manual:
            skipped.append((pid, F['name'], 'مكتوب يدوياً؛ لا يُستورد'))
            continue
        if F['excluded'] or F['kind'] != 'panel':
            skipped.append((pid, F['name'], 'ليس لوحاً جدارياً؛ خارج قالب هذه العائلة'))
            continue
        if not F.get('dims'):
            skipped.append((pid, F['name'], 'نقص: ' + ' | '.join(t for _, t in F['issues']) or 'لا مقاس'))
            continue
        c = bp.build_context(F)
        if c['material'] == 'ستيل':            # «استيل» في الاسم لون معدني لا خامة اللوح
            c['material'] = ''
        ex = example(F)
        # مثال الكمية نفسه في الوصف المختصر والميتا
        c.update(Ww=bp.fnum(ex['Ww'], 1), n=ex['n'], n_txt=bp.cnt(ex['n'], 'panel'), qty_n=ex['n'],
                 qty_short='%s لجدار %s × %s م' % (bp.cnt(ex['n'], 'panel'), bp.fnum(ex['Ww'], 1), bp.fnum(ex['h'], 1)))
        kw = bp.rm_keyword(F)
        layer, n_rows = product_layer(F, c, ex, kw, usage, cfg)
        sep = '<h2>%s: %s</h2>' % (bp.esc(kw), cfg['guide'])
        tail = '<p>%s</p>' % link_line(F, kw, links, paths, root_name)
        desc = '\n'.join([layer, sep, family_html, tail, bp.MARK])
        title = bp.build_title(F, c, kw, used_titles)
        meta = re.sub(r' {2,}', ' ', bp.build_meta(F, c, kw, used_metas))
        excerpt = re.sub(r' {2,}', ' ', bp.tidy(bp.build_excerpt(F, c, kw)))
        text = bp.clean_text(desc)
        nw = len(text.split())
        kc = text.count(kw)
        u = usage.get(pid, ('', '', ''))
        outs.append(dict(id=pid, name=F['name'], kw=kw, description=desc, layer=layer, excerpt=excerpt, title=title, meta=meta,
                         image_alt=F['name'], words=nw, layer_words=words(layer), kw_count=kc, density=kc * 100.0 / nw,
                         n_rows=n_rows, slug=F['slug'], issues=F['issues'], usage=u, F=F))
    return dict(cfg=cfg, fam=fam, family_html=family_html, outs=outs, skipped=skipped, links=links, byF=byF)


def measure(res):
    outs, fam_html = res['outs'], res['family_html']
    N = len(outs)
    df = Counter()
    per = []
    for o in outs:
        ss = sents(bp.clean_text(o['layer']))
        per.append(ss)
        for s in set(ss):
            df[s] += 1
    thr = max(2, int(math.ceil(N * 0.10)))
    spec10 = [sum(1 for s in ss if df[s] < thr) / len(ss) for ss in per]
    uniq = [sum(1 for s in ss if df[s] == 1) / len(ss) for ss in per]
    fam_s = set(sents(bp.clean_text(fam_html)))
    whole = []
    for o, ss in zip(outs, per):
        allss = sents(bp.clean_text(o['description']))
        whole.append(sum(1 for s in allss if s not in fam_s and df.get(s, 0) < thr) / len(allss))
    allowed = bp.allowed_links(res['links'])

    def checks(o):
        text = bp.clean_text(o['description'])
        heads = re.findall(r'<h[23]>(.*?)</h[23]>', o['description'])
        hrefs = re.findall(r'href="([^"]+)"', o['description'])
        first = ' '.join(text.split()[:max(1, len(text.split()) // 10)])
        return {
            'الكلمة في العنوان': o['kw'] in o['title'],
            'العنوان يبدأ بالكلمة': o['title'].startswith(o['kw']),
            'طول العنوان ≤60': len(o['title']) <= 60,
            'الكلمة في الوصف التعريفي': o['kw'] in o['meta'],
            'طول الوصف التعريفي 120–160': 120 <= len(o['meta']) <= 160,
            'الكلمة في بداية المحتوى (أول 10%)': o['kw'] in first,
            'المحتوى يبدأ بالكلمة حرفياً': text.startswith(o['kw']),
            'الكلمة في عنوان فرعي H2': any(o['kw'] in h for h in re.findall(r'<h2>(.*?)</h2>', o['description'])),
            'المحتوى ≥600 كلمة': o['words'] >= 600,
            'الكلمة في الرابط (slug)': bp.slugify(o['kw']) in o['slug'],
            'الكلمة في النص البديل للصورة': o['kw'] in o['image_alt'],
            'الكثافة 0.6–1.2%': DENS_LO <= o['density'] <= DENS_HI,
            'روابط داخلية حقيقية فقط': bool(hrefs) and all(h in allowed for h in hrefs),
            'بلا أسعار': not any(bp.PRICE_RE.search(x) for x in (text, o['title'], o['meta'], o['excerpt'])),
            'بلا عبارات محظورة': not re.search(r'ضمان|حريق|اشتعال|شهادة|معتمد', text),
            'عناوين فرعية ≥4': len(heads) >= 4,
        }
    agg = Counter()
    fails = {}
    for o in outs:
        for k, v in checks(o).items():
            agg[k] += bool(v)
            if not v:
                fails.setdefault(k, []).append(o['id'])
    med = statistics.median
    dens = sorted(o['density'] for o in outs)
    lw = sorted(o['layer_words'] for o in outs)
    return dict(
        family=res['fam']['family_id'], family_count=res['fam']['count'], generated=N, skipped=len(res['skipped']),
        family_layer_words=words(fam_html),
        layer_words=dict(min=lw[0], median=med(lw), max=lw[-1], in_180_260=sum(1 for x in lw if 180 <= x <= 260)),
        total_words=dict(min=min(o['words'] for o in outs), median=med([o['words'] for o in outs]), max=max(o['words'] for o in outs)),
        product_share_of_words_median=round(med([o['layer_words'] / o['words'] for o in outs]) * 100, 1),
        specific_sentences_layer_median_pct=round(med(spec10) * 100, 1),
        specific_sentences_layer_min_pct=round(min(spec10) * 100, 1),
        unique_sentences_layer_median_pct=round(med(uniq) * 100, 1),
        specific_sentences_whole_desc_median_pct=round(med(whole) * 100, 1),
        dup_threshold_products=thr,
        density=dict(min=round(dens[0], 2), median=round(med(dens), 2), max=round(dens[-1], 2)),
        kw_count=dict(Counter(o['kw_count'] for o in outs)),
        distinct_titles=len(set(o['title'] for o in outs)), distinct_metas=len(set(o['meta'] for o in outs)),
        distinct_keywords=len(set(o['kw'] for o in outs)),
        distinct_examples=len(set(o['excerpt'].split('. ')[-1] for o in outs)),
        checks={k: '%d/%d' % (agg[k], N) for k in agg}, fails={k: v[:12] for k, v in fails.items()},
        usage_rows=dict(Counter('%s/%s' % (o['usage'][0] or '—', o['usage'][1] or '—') for o in outs)),
        top_repeated=[(s, n) for s, n in df.most_common(6)],
    )


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    if not args:
        raise SystemExit(__doc__)
    family_id = args[0]
    res = build(family_id)
    outs = res['outs']
    if '--sample' in argv:
        ids = [int(a.split('=')[1]) for a in argv if a.startswith('--id=')]
        o = ([x for x in outs if x['id'] in ids] or
             sorted(outs, key=lambda x: (-x['n_rows'], -int(bool(x['F']['code'])), x['id']))[:1])[0]
        print('ID=%d | %s\nkw=%s | words=%d | layer=%d | density=%.2f%%\nTITLE: %s\nMETA: %s\nSHORT: %s\n' % (
            o['id'], o['name'], o['kw'], o['words'], o['layer_words'], o['density'], o['title'], o['meta'], o['excerpt']))
        print(o['description'])
        return 0
    stats = measure(res)
    if '--stats' not in argv:
        os.makedirs(bp.OUT_DIR, exist_ok=True)
        path = os.path.join(bp.OUT_DIR, 'products-v6-%s.csv' % family_id)
        bp.write_csv(path, [[o['id'], o['description'], o['excerpt'], o['title'], o['meta'], o['kw'], o['image_alt']] for o in outs],
                     bp.COLS)
        print('wrote %s rows=%d' % (path, len(outs)))
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print('SKIPPED')
    for s in res['skipped']:
        print('  %s | %s | %s' % s)
    print('ISSUES')
    for o in outs:
        iss = [t for l, t in o['issues'] if l in ('conflict', 'missing')]
        if iss:
            print('  %d | %s | %s' % (o['id'], o['name'], ' | '.join(iss)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
