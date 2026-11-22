#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نموذج «عائلة المنتج» (v6): وصف المنتج = طبقة خاصة بالمنتج + طبقة عائلة مكتوبة يدوياً مرة واحدة.

لكل عائلة ملفان في data/family-content/ :
  <family_id>.html   طبقة العائلة (ثابتة)
  <family_id>.json   الإعداد: family_id, kind, piece_word, guide_title, needs_confirmation, notes
                     kind ∈ panel | roll | plank_sqm | tile | linear | piece
                     اختياري: waste_pct (نسبة الهدر %، الافتراضي 10)، noun / noun_alt (وصف النوع في فقرة الإجابة)،
                              missing_policy = "skip" (تخطّي المنتج بلا مقاس بدل توليده بلا أرقام)،
                              kw_rule = "v5" (الكلمة المفتاحية كما يخرجها المولّد v5 دون إصلاح نهايتها)

طبقة المنتج مولَّدة من بيانات المنتج نفسه؛ التحليل والحساب مستوردان من build_products.py (لا نسخ).
حتمي: لا عشوائية ولا تاريخ تشغيل. لا يتصل بالموقع ولا يكتب أي سعر.

التشغيل:
  python3 texa/scripts/build_family.py sb-5mm              عائلة واحدة: CSV + الأرقام المقيسة
  python3 texa/scripts/build_family.py sb-5mm --sample [--id=N]   يطبع وصف منتج واحد كاملاً
  python3 texa/scripts/build_family.py sb-5mm --stats      الأرقام فقط بلا كتابة
  python3 texa/scripts/build_family.py --all               كل عائلة لها html+json: CSV لكل عائلة + ملف مراجعة + تقرير
  خيارات: --dir=PATH (مجلد طبقات بديل)  --out=PATH (مجلد مخرجات بديل؛ التقرير يُكتب فيه أيضاً)
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
QA_REPORT = os.path.join(bp.BASE, 'reports', '2026-11-22-family-build-qa.md')
KINDS = ('panel', 'roll', 'plank_sqm', 'tile', 'linear', 'piece')
DENS_LO, DENS_HI = 0.6, 1.2            # هدف الكثافة (يُقاس ولا يُفرض)
EX_WIDTHS = [2.4, 3, 3.6, 4, 4.2, 4.8, 5, 5.4, 6]
EX_HEIGHTS = [2.6, 2.7, 2.8]
FAQ_WIDTHS = [2.5, 3.2, 3.8, 4.5, 5.2, 5.8, 6.5, 7]
FULL_HEIGHT = 2.4                      # لوح بهذا الطول فأكثر يُركَّب واقفاً ويُحسب بالأعمدة
DOOR = 0.9
FORBIDDEN = re.compile(r'ضمان|حريق|اشتعال|شهاد(?:ة|ات)|FDA|(?<![ء-ي])(?:ال|لل|بال)?ربو(?![ء-ي])', re.I)

# مفرد، مثنى، جمع (3–10)، تمييز (11+)، مؤنث؟
NOUN = {
    'لوح': ('لوح', 'لوحان', 'ألواح', 'لوحاً', False), 'لفة': ('لفة', 'لفتان', 'لفات', 'لفة', True),
    'رول': ('رول', 'رولان', 'رولات', 'رولاً', False), 'شريحة': ('شريحة', 'شريحتان', 'شرائح', 'شريحة', True),
    'بلاطة': ('بلاطة', 'بلاطتان', 'بلاطات', 'بلاطة', True), 'عود': ('عود', 'عودان', 'أعواد', 'عوداً', False),
    'قطعة': ('قطعة', 'قطعتان', 'قطع', 'قطعة', True), 'صفيحة': ('صفيحة', 'صفيحتان', 'صفائح', 'صفيحة', True),
    'كرتونة': ('كرتونة', 'كرتونتان', 'كراتين', 'كرتونة', True), 'عمود': ('عمود', 'عمودان', 'أعمدة', 'عموداً', False),
    'نعلة': ('نعلة', 'نعلتان', 'نعلات', 'نعلة', True), 'زاوية': ('زاوية', 'زاويتان', 'زوايا', 'زاوية', True),
    'فاصل': ('فاصل', 'فاصلان', 'فواصل', 'فاصلاً', False), 'كرنيش': ('كرنيش', 'كرنيشان', 'كرانيش', 'كرنيشاً', False),
}

SURFACE = {'plain': 'سطح{h} سادة', 'wood': 'مظهر{h} خشبي', 'fabric': 'ملمس{h} قماشي', 'marble': 'نقشت{h} رخامية معرّقة',
           'stripe': 'نقشت{h} مخططة', 'wave': 'نقشت{h} مودرن', 'stone': 'ملمس{h} حجري', 'herringbone': 'نقشت{h} هرمية',
           'glossy': 'سطح{h} لامع', 'ornament': 'سطح{h} منقوش', 'floral': 'نقشت{h} ورود', 'kids': 'تصميم{h} للأطفال',
           '3d': 'نقشت{h} بارزة (ثري دي)', 'fluted': 'سطح{h} مضلع'}
# مراجعة مكتبة النصائح: نصائح الهرمي في المولّد مكتوبة للأرضيات، وهذه بديلها للجدران.
WALL_PATTERN_TIPS = {
    'herringbone': ['النقشة الهرمية تضيف حركة للجدار فتكفي وحدها عنصر زينة',
                    'اتجاه رؤوس الأسهم في النقشة الهرمية يُوحَّد بين الألواح المتجاورة',
                    'النقشة الهرمية تبرز على جدار تمييز واحد أكثر من تغطية الغرفة كلها'],
}
# نصائح لونية لا تصلح لغير الجدران (أرضيات/قطع تشطيب): تُستبعد بهذه الكلمات
NOT_FLOOR = re.compile(r'جدار|الجدران|خلفية|ستائر')
NOT_TRIM = re.compile(r'الاتساع|جدار|الجدران|خلفية|قاعدة|يوسّع|المساح|الغرفة|المكان|ستائر|أثاث|سجاد|مسطّحة|الضوء')
SENT_SPLIT = re.compile(r'(?<!\d)\.|\.(?!\d)|[؟!\n]')


# ------------------------------------------------------------------ أدوات

def sents(text, minlen=25):
    return [s.strip() for s in SENT_SPLIT.split(text) if len(s.strip()) > minlen]


def words(html_text):
    return len(bp.clean_text(html_text).split())


def noun(word):
    return NOUN.get(word) or (word, None, None, word, word.endswith('ة'))


def cntw(n, P):
    s, d, p, acc, fem = P
    n = int(n)
    if d is None:
        return '%d %s' % (n, s)
    if n == 1:
        return s + (' واحدة' if fem else ' واحد')
    if n == 2:
        return d
    if 3 <= n <= 10:
        return '%d %s' % (n, p)
    return '%d %s' % (n, acc)


def g(fem, m, f):
    return f if fem else m


def name_fem(name):
    w = name.split()[0] if name.split() else ''
    return bool(re.search(r'(ة|ات)$', w)) or w in ('نعله', 'ألواح', 'الواح', 'صفائح', 'زخارف', 'أعواد', 'اعواد', 'فواصل', 'كرانيش',
                                                    'أعمدة', 'اعمدة', 'زوايا', 'أطقم', 'اطقم', 'تيجان', 'براويز', 'حليات')


def ceil(x):
    return int(math.ceil(x - 1e-9))


def calc_link(what):
    return 'أدخل %s في %s لتعرف عددك.' % (what, bp.A(bp.URL_CALC, 'حاسبة الكميات'))


class Base(object):
    """بيانات مشتركة تُحمَّل مرة واحدة."""

    def __init__(self):
        self.links, self.paths, self.root_name = bp.load_cat_links()
        self.usage = {}
        with open(USAGE, encoding='utf-8-sig') as fh:
            for r in csv.DictReader(fh):
                self.usage[int(r['id'])] = (r['proposed_usage'].strip(), r['confidence'].strip(), r['evidence'].strip())
        prods = bp.load_products()
        self.byF = {F['id']: F for F in bp.finalize([bp.extract(p, self.paths) for p in prods])}
        self.fams = {f['family_id']: f for f in json.load(open(FAMILIES, encoding='utf-8'))['families']}
        self.allowed = bp.allowed_links(self.links)


def load_cfg(family_id, fdir):
    path = os.path.join(fdir, family_id + '.json')
    cfg = json.load(open(path, encoding='utf-8'))
    if cfg.get('family_id') != family_id:
        raise ValueError('family_id في %s لا يطابق اسم الملف' % path)
    if cfg.get('kind') not in KINDS:
        raise ValueError('kind غير معروف «%s»؛ المسموح: %s' % (cfg.get('kind'), ' | '.join(KINDS)))
    for k in ('piece_word', 'guide_title'):
        if not isinstance(cfg.get(k), str) or not cfg[k].strip():
            raise ValueError('الحقل %s ناقص في %s' % (k, path))
    w = cfg.get('waste_pct', 10)
    if not isinstance(w, (int, float)) or not 0 <= w <= 30:
        raise ValueError('waste_pct يجب أن يكون رقماً بين 0 و30')
    cfg['_waste'] = w / 100.0
    cfg['_P'] = noun(cfg['piece_word'].strip())
    return cfg

# ------------------------------------------------------------------ محركات الأرقام
# كل محرك يعيد dict(summary, bullets, faq, qty_short, qty_n) أو None إن لم تكفِ بيانات المنتج.


def eng_columns(F, c, cfg, kw):
    """ألواح بطول الجدار تُركَّب واقفة: العدد بحساب الأعمدة."""
    pid, P = F['id'], cfg['_P']
    w, acc, fem = P[0], P[3], P[4]
    f = bp.fnum
    L, W = max(F['dims']), min(F['dims'])
    Ww = bp.pick(EX_WIDTHS, pid, 'fam-w')
    h = bp.pick([x for x in EX_HEIGHTS if x <= L + 1e-9] or [math.floor(L * 10 + 1e-9) / 10.0], pid, 'fam-h')
    q = Ww / W
    n = ceil(q)
    exact = abs(q - round(q)) < 1e-9
    cov = L * W
    A, tot = Ww * h, n * cov
    last_cm, cut_cm = round((W - (n * W - Ww)) * 100, 1), round((L - h) * 100, 1)
    n_txt = cntw(n, P)
    hh = g(fem, 'ه', 'ها')
    summary = 'مقاس%s %s × %s سم، %s ال%s %s %s م²، وجدار %s × %s م يلزمه %s.' % (
        hh, f(W * 100, 1), f(L * 100, 1), g(fem, 'فيغطي', 'فتغطي'), w, g(fem, 'الواحد', 'الواحدة'), f(cov), f(Ww, 1), f(h, 1), n_txt)
    li = ['تغطية ال%s %s: %s × %s سم = %s م².' % (w, g(fem, 'الواحد', 'الواحدة'), f(W * 100, 1), f(L * 100, 1), f(cov))]
    lead = 'مثال بحساب الأعمدة لجدار %s × %s م: %s ÷ %s = ' % (f(Ww, 1), f(h, 1), f(Ww, 1), f(W, 2))
    if exact:
        li.append(lead + '%d بالضبط، فيلزمك %s دون قص في العرض؛ أضف %s %s إن كانت زوايا الجدار غير قائمة.' % (
            n, n_txt, acc, g(fem, 'احتياطياً', 'احتياطية')))
    else:
        li.append(lead + '%s، فيلزمك %s، %s إلى عرض %s سم.' % (f(q, 2), n_txt, g(fem, 'ويُقص الأخير', 'وتُقص الأخيرة'), f(last_cm, 1)))
    li.append('تشتري %s م² لجدار مساحته %s م²، والفرق %s م² يذهب في القص (%s سم من طول كل %s).' % (
        f(tot, 2), f(A, 2), f(tot - A, 2), f(cut_cm, 1), w))
    li.append(calc_link('مقاس جدارك'))
    w2 = bp.pick([x for x in FAQ_WIDTHS if abs(x - Ww) > 0.05], pid, 'fam-w2')
    q2 = w2 / W
    yl = g(fem, 'يلزم', 'تلزم')
    qa = [('كم %s من %s %s لجدار عرضه %s م؟' % (acc, bp.esc(kw), yl, f(w2, 1)),
           '%s: %s ÷ %s = %s ويُقرَّب إلى الأعلى، بشرط ألا يزيد ارتفاع الجدار على %s سم.' % (
               cntw(ceil(q2), P), f(w2, 1), f(W, 2), f(q2, 2), f(L * 100, 1)))]
    v = bp.H(pid, 'fam-q2') % 3
    extra = '%s %s' % (w, g(fem, 'إضافي', 'إضافية'))
    if v == 0:
        h2 = bp.pick([3.0, 3.2], pid, 'fam-h2')
        d = round((h2 - L) * 100, 1)
        if d <= 0:
            v = 2
        elif d <= 20:
            fix = 'يغطيها كرنيش أو نعلة بهذا الارتفاع، أو شريط يُقص من %s' % extra
        else:
            k = int(math.floor(L * 100 / d + 1e-9))
            fix = 'تُكمَّل بشريط يُقص من %s فوق فاصل أفقي، وال%s %s %s %s %d شرائط بهذا الارتفاع عرض كلٍّ منها %s سم' % (
                extra, w, g(fem, 'الإضافي', 'الإضافية'), g(fem, 'الواحد', 'الواحدة'), g(fem, 'يعطي', 'تعطي'), k, f(W * 100, 1))
        if v == 0:
            qa.append(('هل يكفي طول %s ال%s لجدار ارتفاعه %s م؟' % (g(fem, 'هذا', 'هذه'), w, f(h2, 1)),
                       'لا يكفي بقطعة واحدة: طول%s %s سم والجدار %s سم، فتبقى %s سم %s.' % (hh, f(L * 100, 1), f(h2 * 100, 1), f(d, 1), fix)))
    if v == 1:
        ra, rb = bp.pick(bp.ROOMS_FLOOR, pid, 'fam-room')
        Pm = 2 * (ra + rb)
        qa.append(('كم %s %s لتكسية جدران غرفة %s × %s م كلها؟' % (acc, yl, f(ra, 1), f(rb, 1)),
                   'محيط الغرفة %s م، و%s ÷ %s = %s، أي %s قبل خصم الباب والنوافذ. اطرح عرض الفتحات من المحيط ثم أعد القسمة.' % (
                       f(Pm, 1), f(Pm, 1), f(W, 2), f(Pm / W, 2), cntw(ceil(Pm / W), P))))
    elif v == 2:
        k = bp.pick([4, 5, 6, 7, 8], pid, 'fam-k')
        qa.append(('كم متراً من الجدار تغطي %s من%s؟' % (cntw(k, P), hh),
                   '%d × %s = %s م عرضاً بارتفاع حتى %s سم، أي %s م².' % (k, f(W, 2), f(k * W, 2), f(L * 100, 1), f(k * cov, 2))))
    return dict(summary=summary, bullets=li, faq=qa, qty_n=n,
                qty_short='%s لجدار %s × %s م' % (n_txt, f(Ww, 1), f(h, 1)))


def eng_roll(F, c, cfg, kw):
    """ورق الجدران: الحساب بالشرائح، ولا تُخصم الأبواب والنوافذ (قاعدة مقال المتجر)."""
    if F['kind'] != 'wallpaper' or not c.get('calc') or not F.get('dims'):
        return None
    P = cfg['_P']
    w, acc, fem = P[0], P[3], P[4]
    f = bp.fnum
    S = bp.NOUNS['strip']
    L, W = max(F['dims']), min(F['dims'])
    spr = int(math.floor(L / bp.WALL_H + 1e-9))
    if spr < 1:
        return None
    Ww, ra, rb = float(c['Ww']), float(c['ra']), float(c['rb'])
    strips = ceil(Ww / W)
    rolls = ceil(strips / spr)
    Pm = 2 * (ra + rb)
    strips_r = ceil(Pm / W)
    rolls_r = ceil(strips_r / spr)
    Ww2, h2 = float(c['Ww2']), float(c['h2'])
    st2 = ceil(Ww2 / W)
    rolls2 = ceil(st2 / spr)
    sprh = int(math.floor(L / h2 + 1e-9))
    ty, tg = g(fem, 'يعطي', 'تعطي'), g(fem, 'يغطي', 'تغطي')
    summary = 'ال%s %s م × %s سم، %s نحو %s م² و%s %s بارتفاع %s م، وجدار بعرض %s م يلزمه %s.' % (
        w, f(L, 2), f(W * 100, 1), tg, f(L * W), ty, cntw(spr, S), f(bp.WALL_H, 1), f(Ww, 1), cntw(rolls, P))
    li = ['تغطية ال%s: %s م × %s سم = %s م² تقريباً.' % (w, f(L, 2), f(W * 100, 1), f(L * W)),
          'الشرائح: %s ÷ %s = %s، أي %s كاملة من كل %s لجدار ارتفاعه %s م.' % (
              f(L, 2), f(bp.WALL_H, 1), f(L / bp.WALL_H, 2), cntw(spr, S), w, f(bp.WALL_H, 1)),
          'مثال جدار عرضه %s م: %s ÷ %s = %s ← %s، أي %s.' % (f(Ww, 1), f(Ww, 1), f(W, 2), f(Ww / W, 2), cntw(strips, S), cntw(rolls, P)),
          'مثال غرفة %s × %s م: محيطها %s م ← %s ← %s. الحساب بالشرائح، ولا تُخصم الأبواب والنوافذ.' % (
              f(ra, 1), f(rb, 1), f(Pm, 1), cntw(strips_r, S), cntw(rolls_r, P)),
          calc_link('مقاس جدارك')]
    a2 = '%s: %s ÷ %s = %s، والباقي لا يكفي شريحة كاملة.' % (cntw(sprh, S), f(L, 2), f(h2, 1), f(L / h2, 2))
    if sprh < spr:
        a2 += ' هذا أقل من %s عند ارتفاع %s م، فأعد حساب العدد على هذا الأساس.' % (cntw(spr, S), f(bp.WALL_H, 1))
    qa = [('كم %s أحتاج من %s لجدار عرضه %s م؟' % (acc, bp.esc(kw), f(Ww2, 1)),
           '%s: %s ÷ %s = %s ← %s، وكل %s %s %s بارتفاع %s م.' % (
               cntw(rolls2, P), f(Ww2, 1), f(W, 2), f(Ww2 / W, 2), cntw(st2, S), w, ty, cntw(spr, S), f(bp.WALL_H, 1))),
          ('كم شريحة %s ال%s إن كان ارتفاع الجدار %s م؟' % (ty, w, f(h2, 1)), a2)]
    return dict(summary=summary, bullets=li, faq=qa, qty_n=rolls, qty_short='%s لجدار بعرض %s م' % (cntw(rolls, P), f(Ww, 1)))


def eng_area(F, c, cfg, kw):
    """حساب بالمساحة مع نسبة هدر: أرضيات (غرفة) وبلاطات وصفائح وألواح قصيرة (جدار)."""
    pid, P = F['id'], cfg['_P']
    w, acc, fem = P[0], P[3], P[4]
    f = bp.fnum
    floor = F['kind'] == 'floor' or cfg['kind'] == 'plank_sqm'
    d = F.get('dims')
    pa = F.get('piece_area') or (d[0] * d[1] if d else None)
    carton = F.get('carton') if F['kind'] == 'floor' else None
    if not pa and not carton:
        return None
    waste = cfg['_waste']
    wp = f(waste * 100, 1)
    if floor:
        rm = 'مساحة' if F['sub'] in ('exterior', 'hpl') else 'غرفة'
        ra, rb = bp.pick(bp.ROOMS_FLOOR, pid, 'fam-room')
        A = ra * rb
        place, placeq, yl, mine = '%s %s × %s م' % (rm, f(ra, 1), f(rb, 1)), 'ل%s %s × %s م' % (rm, f(ra, 1), f(rb, 1)), 'يلزمها', 'مقاس المكان' if rm == 'مساحة' else 'مقاس غرفتك'
        ra2, rb2 = bp.pick([r for r in bp.ROOMS_FLOOR if r != (ra, rb)], pid, 'fam-room2')
        A2, place2 = ra2 * rb2, 'ل%s %s × %s م' % (rm, f(ra2, 1), f(rb2, 1))
    else:
        Ww, h = bp.pick(EX_WIDTHS, pid, 'fam-w'), bp.pick(EX_HEIGHTS, pid, 'fam-h')
        A = Ww * h
        place, placeq, yl, mine = 'جدار %s × %s م' % (f(Ww, 1), f(h, 1)), 'لجدار %s × %s م' % (f(Ww, 1), f(h, 1)), 'يلزمه', 'مقاس جدارك'
        w2 = bp.pick([x for x in FAQ_WIDTHS if abs(x - Ww) > 0.05], pid, 'fam-w2')
        A2, place2 = w2 * h, 'لجدار %s × %s م' % (f(w2, 1), f(h, 1))
    need, need2 = A * (1 + waste), A2 * (1 + waste)
    U, ucov = (NOUN['كرتونة'], carton) if carton else (P, pa)
    n, n2 = ceil(need / ucov), ceil(need2 / ucov)
    n_txt = cntw(n, U)
    bits, li = [], []
    if d and pa:
        a, b = max(d), min(d)
        bits.append('مقاس ال%s %s × %s سم (%s م²)' % (w, f(a * 100, 1), f(b * 100, 1), f(pa)))
        s = 'مقاس ال%s: %s × %s سم = %s م²' % (w, f(a * 100, 1), f(b * 100, 1), f(pa))
        if pa <= 0.5:
            s += '، أي نحو %s في المتر المربع' % f(1 / pa, 1)
        li.append(s + '.')
    elif pa:
        bits.append('%s ال%s %s %s م²' % (g(fem, 'يغطي', 'تغطي'), w, g(fem, 'الواحد', 'الواحدة'), f(pa)))
        li.append('تغطية ال%s %s: %s م² (حسب وصف المنتج).' % (w, g(fem, 'الواحد', 'الواحدة'), f(pa)))
    if carton:
        bits.append('الكرتونة تغطي %s م²' % f(carton))
        s = 'الكرتونة تغطي %s م²' % f(carton)
        if F.get('pcs_carton'):
            s += '، وفيها %s' % cntw(F['pcs_carton'], P)
        li.append(s + '.')
    summary = '، و'.join(bits) + '، و%s %s %s بعد إضافة %s%% للقص.' % (place, yl, n_txt, wp)
    li.append('مثال %s: المساحة %s م²، ومع %s%% هدر للقص %s م².' % (place, f(A, 2), wp, f(need, 2)))
    li.append('%s ÷ %s = %s ← %s، تغطي %s م².' % (f(need, 2), f(ucov), f(need / ucov, 2), n_txt, f(n * ucov, 2)))
    li.append(calc_link(mine))
    qa = [('كم %s أحتاج من %s %s؟' % (U[3], bp.esc(kw), place2),
           '%s: المساحة %s م²، ومع %s%% هدر %s م²، مقسومة على %s م² لكل %s.' % (
               cntw(n2, U), f(A2, 2), wp, f(need2, 2), f(ucov), U[0]))]
    k = bp.pick([4, 5, 6, 8, 10] if ucov >= 1 else [10, 20, 30, 40, 50], pid, 'fam-k')
    tot = k * ucov
    qa.append(('كم متراً مربعاً تغطي %s من%s؟' % (cntw(k, U), g(name_fem(F['name']), 'ه', 'ها')),
               '%d × %s = %s م²، تكفي مساحة فعلية نحو %s م² بعد حساب هدر %s%%.' % (k, f(ucov), f(tot, 2), f(tot / (1 + waste), 2), wp)))
    return dict(summary=summary, bullets=li, faq=qa, qty_n=n, qty_short='%s %s' % (n_txt, placeq))


def eng_linear(F, c, cfg, kw):
    """قطع طولية: المسافة ÷ طول القطعة + قطعة احتياط."""
    d = F.get('dims')
    if not d:
        return None
    pid, P = F['id'], cfg['_P']
    w, acc, fem = P[0], P[3], P[4]
    f = bp.fnum
    L, W = max(d), min(d)
    if L < 0.5:
        return None
    spare = '%s احتياط' % w
    room = F['sub'] in ('skirting', 'cornice')
    if room:
        ra, rb = bp.pick(bp.ROOMS_FLOOR, pid, 'fam-room')
        Pm = 2 * (ra + rb)
        run = Pm - DOOR if F['sub'] == 'skirting' else Pm
        ex = 'مثال غرفة %s × %s م: المحيط %s م' % (f(ra, 1), f(rb, 1), f(Pm, 1))
        if F['sub'] == 'skirting':
            ex += '، وبعد خصم فتحة باب %s سم %s م' % (f(DOOR * 100), f(run, 1))
        place, placeq = 'غرفة %s × %s م يلزمها' % (f(ra, 1), f(rb, 1)), 'لغرفة %s × %s م' % (f(ra, 1), f(rb, 1))
        ra2, rb2 = bp.pick([r for r in bp.ROOMS_FLOOR if r != (ra, rb)], pid, 'fam-room2')
        P2 = 2 * (ra2 + rb2)
        run2 = P2 - DOOR if F['sub'] == 'skirting' else P2
        place2 = 'لغرفة %s × %s م' % (f(ra2, 1), f(rb2, 1))
        how2 = 'المحيط %s م%s، و' % (f(P2, 1), ('، ناقص %s م للباب' % f(DOOR, 1)) if F['sub'] == 'skirting' else '')
    else:
        run = bp.pick(bp.RUNS, pid, 'fam-run')
        ex = 'مثال: مسافة طولها %s م' % f(run, 1)
        place, placeq = 'كل %s م طولية يلزمها' % f(run, 1), 'لكل %s م طولية' % f(run, 1)
        run2 = bp.pick([r for r in bp.RUNS if r != run], pid, 'fam-run2')
        place2, how2 = 'لمسافة طولها %s م' % f(run2, 1), ''
    n0, n02 = ceil(run / L), ceil(run2 / L)
    n, n2 = n0 + 1, n02 + 1
    n_txt = cntw(n, P)
    summary = 'طول ال%s %s م، و%s %s بينها %s.' % (w, f(L, 2), place, n_txt, spare)
    s = 'المقاس: %s سم (طول)' % f(L * 100, 1)
    if W and W < L:
        s += ' × %s سم' % f(W * 100, 1)
    li = [s + '.', ex + '.',
          '%s ÷ %s = %s ← %s، ومع %s للزوايا والقص %s.' % (f(run, 1), f(L, 2), f(run / L, 2), cntw(n0, P), spare, n_txt),
          calc_link('مقاسك')]
    k = bp.pick([5, 6, 8, 10, 12], pid, 'fam-k')
    qa = [('كم %s أحتاج من %s %s؟' % (acc, bp.esc(kw), place2),
           '%s: %s%s ÷ %s = %s ← %s، ومعها %s.' % (cntw(n2, P), how2, f(run2, 1), f(L, 2), f(run2 / L, 2), cntw(n02, P), spare)),
          ('كم متراً طولياً تغطي %s من%s؟' % (cntw(k, P), g(name_fem(F['name']), 'ه', 'ها')),
           '%d × %s = %s م طولياً.' % (k, f(L, 2), f(k * L, 2)))]
    return dict(summary=summary, bullets=li, faq=qa, qty_n=n, qty_short='%s %s' % (n_txt, placeq))


def numbers(F, c, cfg, kw):
    """يختار المحرك بحسب نوع العائلة، ويعيد (النتيجة، سبب غياب الأرقام)."""
    kind = cfg['kind']
    if kind == 'piece':
        return None, None
    if F.get('dims_conflict') or F.get('stated_conflict'):
        return None, 'conflict'
    r = None
    if kind == 'roll':
        r = eng_roll(F, c, cfg, kw)
    elif kind == 'panel':
        if F['kind'] in ('panel', 'slat', 'small') and F.get('dims'):
            r = eng_columns(F, c, cfg, kw) if max(F['dims']) >= FULL_HEIGHT else eng_area(F, c, cfg, kw)
    elif kind in ('plank_sqm', 'tile'):
        if F['kind'] != 'wallpaper':
            r = eng_area(F, c, cfg, kw)
    elif kind == 'linear':
        r = eng_linear(F, c, cfg, kw)
    return r, (None if r else 'missing')

# ------------------------------------------------------------------ أجزاء طبقة المنتج


def answer_paragraph(F, c, cfg, num):
    name = bp.esc(F['name'])
    P = cfg['_P']
    nn = cfg.get('noun')
    if nn is None and cfg['kind'] == 'panel' and c['thing'].startswith('بديل'):
        nn, alt = '%s جداري من %s' % (P[0], c['thing']), 'تكسية جدران من %s' % c['thing']
    else:
        alt = cfg.get('noun_alt') or nn
    fem = P[4] if nn else name_fem(F['name'])
    h = g(fem, 'ه', 'ها')
    thick_in_name = re.search(r'\d\s*(ملم|مم)', F['name'])
    if nn:
        bits = alt if P[0] in F['name'] else nn
        if c['thick'] and not thick_in_name:
            bits += ' بسماكة %s ملم' % c['thick']
        if c['material']:
            bits += '، خامت%s %s' % (h, bp.esc(c['material']))
        if c['origin']:
            bits += '، ومنشؤ%s %s' % (h, c['origin'])
        s1 = '%s: %s. ' % (name, bits)
    else:
        facts = []
        if c['thick'] and not thick_in_name:
            facts.append('سماكت%s %s ملم' % (h, c['thick']))
        if c['material']:
            facts.append('خامت%s %s' % (h, bp.esc(c['material'])))
        if c['origin']:
            facts.append('منشؤ%s %s' % (h, c['origin']))
        if len(facts) > 1:
            facts[-1] = 'و' + facts[-1]
        s1 = '%s: %s' % (name, ('، '.join(facts) + '. ') if facts else '')
    look = []
    surf = SURFACE.get(F['pattern'])
    if surf:
        look.append(surf.format(h=h))
    if c['cph']:
        look.append('لون%s %s' % (h, bp.esc(c['cph'])))
    s2 = (' و'.join(look) + '. ') if look else ''
    if num:
        s3 = num['summary']
    elif c.get('post_h'):
        s3 = 'ارتفاع%s %s م.' % (h, c['post_h'])
    elif F.get('dims') and c.get('size'):
        s3 = 'مقاس%s %s.' % (h, c['size'])
    else:
        s3 = ''
    s4 = ' %s بـ%s.' % (g(fem, 'يليق', 'تليق'), c['rooms'])
    out = (s1 + s2 + s3).rstrip()
    if out.endswith(':'):
        out = out[:-1] + '.'
    return out + s4


def spec_rows(F, c, usage):
    rows = [r for r in bp.spec_rows(F, c) if r[0] != 'النوع']      # «النوع» واحد في كل العائلة، مكانه طبقة العائلة
    u = usage.get(F['id'])
    if u and u[0] == 'داخلي' and u[1] in ('عالية', 'متوسطة'):
        rows.append(('الاستخدام', 'داخلي (حسب وصف المنتج)'))
    elif u and u[1] == 'عالية' and u[0] in ('خارجي', 'الاثنان'):
        rows.append(('الاستخدام', {'خارجي': 'خارجي', 'الاثنان': 'داخلي وخارجي'}[u[0]] + ' (حسب وصف المنتج)'))
    return rows


def tip_section(F, c):
    """نصيحة التنسيق من مكتبة الألوان في المولّد بعد مراجعتها لكل نوع: جدران / أرضيات / قطع تشطيب / خارجي."""
    pid, pat, kind, sub = F['id'], F['pattern'], F['kind'], F['sub']
    this = bp.THIS[sub]
    types = [t for t in bp.TYPE_TIPS.get(c['tipset']) or bp.TYPE_TIPS['linear'] if not re.search(r'[يت]ليق', t)]
    col = bp.COLOR_TIPS[F['color']] if (c['has_color'] and F['color'] in bp.COLOR_TIPS) else None
    head = bp.pick(bp.TIP_HEADS, pid, 'tip-head').format(cd=c['cd']) if col else 'تنسيق ' + this
    if sub in ('exterior', 'hpl'):
        # واجهات وتكسيات خارجية: نصائح الألوان الداخلية (ستائر، أثاث) لا تنطبق
        a = bp.pick(types, pid, 'tip-t')
        b = bp.pick([t for t in types if t != a] or types, pid, 'tip-t2')
        return 'تنسيق ' + this, bp.esc('%s. %s.' % (a, b))
    if kind in ('linear', 'piece', 'post'):
        sents_ = []
        hs = [t for t in col['h'] if not NOT_TRIM.search(t)] if col else []
        if hs:
            sents_.append('%s %s' % (c['cd'], bp.pick(hs, pid, 'tip-h')))
        else:
            head = 'تنسيق ' + this
        if sub == 'accessory':
            st = bp.pick([bp.SURFACE_DEFAULT['linear'][0], bp.SURFACE_DEFAULT['linear'][2]], pid, 'tip-p')
        else:
            st = bp.pick(bp.SURFACE_DEFAULT['linear' if kind == 'linear' else 'other'], pid, 'tip-p')
        if this.startswith('هذا'):
            st = re.sub(r'^(مقاس|لون|خطّ)ها', r'\1ه', st)
        else:
            st = re.sub(r'^(ملمس|تفاصيل|حضور)ه(?= )', r'\1ها', st)
        sents_.append(st)
        if sub != 'accessory':
            sents_.append(bp.pick(types, pid, 'tip-t'))
        return head, bp.esc('. '.join(sents_) + '.')
    if kind == 'floor':
        pool = bp.PATTERN_TIPS[pat] if pat in ('herringbone', 'wood') else bp.SURFACE_DEFAULT['floor']
        ptip = bp.pick(pool, pid, 'tip-p')
        if col:
            hs = [t for t in col['h'] if not NOT_FLOOR.search(t)] or col['h']
            as_ = [t for t in col['a'] if not NOT_FLOOR.search(t)]
            out = '%s %s. ' % (c['cd'], bp.pick(hs, pid, 'tip-h'))
            if as_:
                out += '%s. ' % bp.pick(as_, pid, 'tip-a')
            return head, bp.esc(out + ptip + '.')
        return head, bp.esc('%s. %s.' % (ptip, bp.pick(types, pid, 'tip-t')))
    # جدران: ألواح وورق وصفائح
    if kind == 'wallpaper':
        pool = bp.PATTERN_TIPS.get(pat) or bp.SURFACE_DEFAULT['wallpaper']
    elif pat == 'kids':
        pool = bp.SURFACE_DEFAULT['other']
    else:
        pool = WALL_PATTERN_TIPS.get(pat) or bp.PATTERN_TIPS.get(pat) or bp.SURFACE_DEFAULT['other']
    ptip = bp.pick(pool, pid, 'tip-p')
    if col:
        out = '%s %s. %s. %s.' % (c['cd'], bp.pick(col['h'], pid, 'tip-h'), bp.pick(col['a'], pid, 'tip-a'), ptip)
    else:
        # لون غير مصنَّف: لا نصيحة لونية عامة؛ نكتفي بما يخص النقشة وتوزيع القطع
        out = '%s. %s.' % (ptip, bp.pick(types, pid, 'tip-t'))
    return head, bp.esc(out)


def faq_plain(F, c, cfg, kw, why):
    """سؤالان نوعيان للمنتج بلا أرقام محسوبة: كيف تُحسب كميته، وما الذي ينقص بياناته."""
    P = cfg['_P']
    w, fem = P[0], P[4]
    calc = bp.A(bp.URL_CALC, 'حاسبة الكميات')
    has_size = bool(F.get('dims') or c.get('post_h'))
    if cfg['kind'] == 'piece':
        a1 = 'الحساب بالعدد لا بالمساحة: عُدّ المواضع التي %s فيها ال%s وأضف %s احتياط.' % (g(fem, 'سيُركَّب', 'ستُركَّب'), w, w)
        if F.get('dims') and c.get('size'):
            a1 += ' مقاس ال%s %s.' % (w, c['size'])
    elif why == 'conflict':
        a1 = 'المقاس مذكور بقيمتين مختلفتين في بيانات هذا المنتج. اسأل فريق تكسا عن المقاس الصحيح، ثم أدخله مع أبعاد مكانك في %s.' % calc
    else:
        what = 'طول' if cfg['kind'] == 'linear' else 'مقاس'
        a1 = '%s ال%s غير مذكور في بيانات هذا المنتج. اطلبه من فريق تكسا، ثم أدخله مع أبعاد مكانك في %s.' % (what, w, calc)
    qa = [('كيف أحسب الكمية من %s؟' % bp.esc(kw), a1)]
    miss = []
    if not has_size and not (cfg['kind'] == 'piece' and re.search(r'\d\s*(?:سم|cm|×|x)', F['name'])):
        miss.append('الطول' if cfg['kind'] == 'linear' else 'المقاس')
    if not c['thick'] and F['kind'] in ('panel', 'slat', 'small', 'floor') and not re.search(r'\d\s*(?:ملم|مم)', F['name']):
        miss.append('السماكة')
    if not c['material']:
        miss.append('الخامة')
    if not F.get('unit_sale'):
        miss.append('وحدة البيع')
    a2 = []
    if miss:
        a2.append('اسأل عن %s، %s في بيانات هذا المنتج.' % (' و'.join(miss), 'فهو غير مذكور' if miss in (['المقاس'], ['الطول']) else 'فهي غير مذكورة'))
    a2.append(('قارن درجة %s بصورة واقعية في ضوء مكانك.' % c['cd']) if c['has_color'] else 'اطلب صورة واقعية للون قبل اعتماده.')
    a2 = ' '.join(a2)
    qa.append(('ما الذي أتأكد منه قبل طلب %s ال%s؟' % (g(fem, 'هذا', 'هذه'), w), a2))
    return qa


def link_line(F, kw, B):
    pid, root = F['id'], F['root']
    rname = B.root_name.get(root)
    subs = []
    for cat in F['cats']:
        p = B.paths.get(cat)
        if not p or p[0] != root or len(p) < 2 or cat.startswith('عروض'):
            continue
        subs.append((-len(p), bp.H(pid, 'lk-' + cat), cat))
    subs = [s[2] for s in sorted(subs)[:2]]
    root_a = bp.A(B.links[rname], rname)
    if subs:
        return 'لخيارات قريبة من %s تصفّح %s، أو ارجع إلى قسم %s.' % (
            bp.esc(kw), ' و'.join(bp.A(B.links[s], s) for s in subs), root_a)
    return 'لخيارات قريبة من %s تصفّح قسم %s.' % (bp.esc(kw), root_a)


def product_layer(F, c, cfg, kw, num, why, usage):
    P = cfg['_P']
    w, fem = P[0], P[4]
    this = '%s ال%s' % (g(fem, 'هذا', 'هذه'), w)
    parts = ['<p class="txa-answer">%s</p>' % answer_paragraph(F, c, cfg, num)]
    if num:
        parts.append('<h2>%s</h2>' % (('أرقام ال%s %s' % (w, bp.esc(F['code']))) if F['code'] else 'أرقام ' + this))
        parts.append('<ul>\n' + '\n'.join('<li>%s</li>' % x for x in num['bullets']) + '\n</ul>')
    rows = spec_rows(F, c, usage)
    parts.append('<h2>مواصفات %s</h2>' % bp.esc(kw))
    parts.append('<table class="txa-specs">\n<tbody>\n' + '\n'.join(
        '<tr><th scope="row">%s</th><td>%s</td></tr>' % (bp.esc(a), bp.esc(b)) for a, b in rows) + '\n</tbody>\n</table>')
    th, tp = tip_section(F, c)
    parts.append('<h2>%s</h2>' % bp.esc(th))
    parts.append('<p>%s</p>' % tp)
    parts.append('<h2>سؤالان عن %s</h2>' % this)
    for q, a in (num['faq'] if num else faq_plain(F, c, cfg, kw, why)):
        parts.append('<h3>%s</h3>' % q)
        parts.append('<p>%s</p>' % a)
    return bp.tidy('\n'.join(parts)), len(rows)

# ------------------------------------------------------------------ بناء العائلة


def product_tests(o, B):
    """اختبارات كل مخرج؛ تعيد قائمة الإخفاقات (فارغة = ناجح)."""
    fails = []
    kw, d = o['kw'], o['description']
    text = bp.clean_text(d)
    blob = '\n'.join([text, o['title'], o['meta'], o['excerpt']])
    bare = blob.replace(o['name'], ' ').replace(bp.clean_name(o['name']), ' ').replace(kw, ' ')
    m = FORBIDDEN.search(bare)
    if m:
        fails.append('كلمة محظورة «%s»' % m.group(0))
    m = bp.PRICE_RE.search(bare)
    if m:
        fails.append('سعر/عملة «%s»' % m.group(0))
    hrefs = re.findall(r'href="([^"]+)"', d)
    bad = [h for h in hrefs if h not in B.allowed]
    if bad or not hrefs:
        fails.append('رابط خارج القائمة المسموحة: %s' % (bad[:1] or 'لا روابط'))
    if not d.rstrip().endswith(bp.MARK):
        fails.append('الوصف لا ينتهي بالعلامة')
    if kw not in o['name']:
        fails.append('الكلمة ليست مقطعاً حرفياً من الاسم')
    if not o['title'].startswith(kw):
        fails.append('العنوان لا يبدأ بالكلمة')
    if kw not in o['meta']:
        fails.append('الكلمة ليست في الوصف التعريفي')
    if not text.startswith(kw):
        fails.append('المحتوى لا يبدأ بالكلمة')
    if not any(kw in h for h in re.findall(r'<h2>(.*?)</h2>', d)):
        fails.append('الكلمة ليست في H2')
    if re.search(r'\{[a-zA-Z_]+\}|%s|%d|None', text):
        fails.append('متغير قالب غير معبأ')
    if len(o['excerpt']) > 160:
        fails.append('الوصف المختصر أطول من 160 حرفاً')
    return fails


def clean_kw(F, kw):
    """يصلح نهاية الكلمة المفتاحية حين تنقطع داخل مقاس: «… 120 ×» تُحذف، و«… 7» تُكمَّل بوحدتها «7 ملم». تبقى مقطعاً حرفياً من الاسم."""
    lab, toks = F['label'].split(), kw.split()
    if lab[:len(toks)] != toks:
        return kw
    n = len(toks)
    while n > 2 and lab[n - 1] in ('×', 'x', 'X', '*'):
        n -= 1
        if n > 2 and re.fullmatch(r'[\d.,]+', lab[n - 1]):
            n -= 1
    if n > 2 and re.fullmatch(r'[\d.,]+', lab[n - 1]) and n < len(lab):
        if lab[n] in ('ملم', 'مم', 'سم', 'م'):
            n += 1
        elif lab[n] in ('×', 'x', 'X', '*'):
            n -= 1
    new = ' '.join(lab[:n])
    return new if (new != kw and len(new) <= bp.KW_MAX_CHARS + 4 and new in F['name']) else kw


def build(B, family_id, fdir=FAMILY_DIR):
    """يبني عائلة واحدة. يرفع ValueError لخطأ على مستوى العائلة (إعداد/طبقة)."""
    fam = B.fams.get(family_id)
    if not fam:
        raise ValueError('family_id غير موجود في families.json')
    cfg = load_cfg(family_id, fdir)
    family_html = open(os.path.join(fdir, family_id + '.html'), encoding='utf-8').read().strip()
    ftext = bp.clean_text(family_html)
    m = FORBIDDEN.search(ftext) or bp.PRICE_RE.search(ftext)
    if m:
        raise ValueError('طبقة العائلة تحوي كلمة محظورة «%s»: …%s…' % (m.group(0), ftext[max(0, m.start() - 40):m.end() + 40].replace('\n', ' ')))
    bad = [h for h in re.findall(r'href="([^"]+)"', family_html) if h not in B.allowed]
    if bad:
        raise ValueError('طبقة العائلة تحوي رابطاً خارج category-links والروابط الثابتة: %s' % bad[0])
    skip_missing = cfg.get('missing_policy') == 'skip'
    outs, review = [], []
    used_titles, used_metas = set(), set()
    tag = {'conflict': 'تعارض', 'missing': 'نقص', 'note': 'ملاحظة'}
    for pid in sorted(fam['product_ids']):
        F = B.byF.get(pid)
        if F is None:
            review.append((pid, '', '', 'مستثنى: غير موجود في البيانات الخام'))
            continue
        if pid in bp.MANUAL_IDS:
            review.append((pid, F['name'], F['url'], 'مستثنى: مكتوب يدوياً؛ لا يُستورد'))
            continue
        if F['excluded']:
            review.append((pid, F['name'], F['url'], 'مستثنى: ' + F['excluded']))
            continue
        c = bp.build_context(F)
        if c['material'] == 'ستيل' and F['sub'] == 'shiplap':            # «استيل» في الاسم لون معدني لا خامة اللوح
            c['material'] = ''
        P = cfg['_P']
        if P[1] and c['u'] != P[0]:       # اسم القطعة المتفق عليه للعائلة في الجدول والوصف التعريفي أيضاً
            c.update(u=P[0], U='ال' + P[0], uacc=P[3], upl=P[2], Upl='ال' + P[2], fem=P[4],
                     one=g(P[4], 'الواحد', 'الواحدة'), yg=g(P[4], 'يغطي', 'تغطي'))
        kw = bp.rm_keyword(F)
        if cfg.get('kw_rule') != 'v5':        # sb-5mm مطبَّق بكلمات v5 كما هي؛ بقية العائلات تُصلَح نهاية الكلمة المقطوعة
            kw = clean_kw(F, kw)
        num, why = numbers(F, c, cfg, kw)
        iss = ['%s: %s' % (tag[l], t) for l, t in sorted(F['issues'], key=lambda t: ('conflict', 'missing', 'note').index(t[0]))]
        if not num and cfg['kind'] != 'piece':
            if skip_missing:
                review.append((pid, F['name'], F['url'], 'لم يُولَّد (missing_policy=skip): ' + (' | '.join(iss) or 'لا مقاس')))
                continue
            iss.insert(0, 'وُلّد بلا قسم الأرقام (%s)' % ('تعارض في المقاس' if why == 'conflict' else 'لا مقاس يكفي لحساب نوع «%s»' % cfg['kind']))
        if num:
            # مثال الكمية نفسه في الوصف المختصر والوصف التعريفي
            c.update(calc=bool(c.get('calc')), qty_short=num['qty_short'], qty_n=num['qty_n'], n=num['qty_n'])
        else:
            c.pop('qty_short', None)
        layer, n_rows = product_layer(F, c, cfg, kw, num, why, B.usage)
        sep = '<h2>%s: %s</h2>' % (bp.esc(kw), bp.esc(cfg['guide_title'].strip()))
        tail = '<p>%s</p>' % link_line(F, kw, B)
        desc = '\n'.join([layer, sep, family_html, tail, bp.MARK])
        title = bp.build_title(F, c, kw, used_titles)
        meta = re.sub(r' {2,}', ' ', bp.build_meta(F, c, kw, used_metas))
        excerpt = re.sub(r' {2,}', ' ', bp.tidy(bp.build_excerpt(F, c, kw)))
        text = bp.clean_text(desc)
        nw = len(text.split())
        kc = text.count(kw)
        o = dict(id=pid, name=F['name'], kw=kw, description=desc, layer=layer, excerpt=excerpt, title=title, meta=meta,
                 image_alt=F['name'], words=nw, layer_words=words(layer), kw_count=kc, density=kc * 100.0 / nw,
                 n_rows=n_rows, slug=F['slug'], issues=F['issues'], usage=B.usage.get(pid, ('', '', '')), F=F, has_num=bool(num))
        fails = product_tests(o, B)
        if fails:
            review.append((pid, F['name'], F['url'], 'لم يُكتب في CSV — فشل اختبار: ' + ' | '.join(fails)))
            continue
        if iss:
            review.append((pid, F['name'], F['url'], ' | '.join(iss)))
        outs.append(o)
    return dict(cfg=cfg, fam=fam, family_html=family_html, outs=outs, review=review)


def measure(res, B):
    outs, fam_html = res['outs'], res['family_html']
    N = len(outs)
    base = dict(family=res['fam']['family_id'], kind=res['cfg']['kind'], family_count=res['fam']['count'], generated=N,
                family_layer_words=words(fam_html), not_generated=sum(1 for r in res['review'] if r[3].startswith(('مستثنى', 'لم يُ'))),
                test_failed=sum(1 for r in res['review'] if 'فشل اختبار' in r[3]))
    if not N:
        return base
    df = Counter()
    per = []
    for o in outs:
        ss = sents(bp.clean_text(o['layer']))
        per.append(ss)
        for s in set(ss):
            df[s] += 1
    thr = max(2, int(math.ceil(N * 0.10)))
    spec10 = [sum(1 for s in ss if df[s] < thr) / max(1, len(ss)) for ss in per]
    uniq = [sum(1 for s in ss if df[s] == 1) / max(1, len(ss)) for ss in per]
    fam_s = set(sents(bp.clean_text(fam_html)))
    whole = []
    for o in outs:
        allss = sents(bp.clean_text(o['description']))
        whole.append(sum(1 for s in allss if s not in fam_s and df.get(s, 0) < thr) / len(allss))

    def checks(o):
        text = bp.clean_text(o['description'])
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
            'روابط داخلية حقيقية فقط': all(h in B.allowed for h in re.findall(r'href="([^"]+)"', o['description'])),
            'بلا أسعار': not any(bp.PRICE_RE.search(x) for x in (text, o['title'], o['meta'], o['excerpt'])),
            'بلا عبارات محظورة': not FORBIDDEN.search(text.replace(o['name'], ' ')),
            'عناوين فرعية ≥4': len(re.findall(r'<h[23]>', o['description'])) >= 4,
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
    tw = sorted(o['words'] for o in outs)
    base.update(
        with_numbers=sum(1 for o in outs if o['has_num']), without_numbers=sum(1 for o in outs if not o['has_num']),
        layer_words=dict(min=lw[0], median=med(lw), max=lw[-1], in_180_260=sum(1 for x in lw if 180 <= x <= 260)),
        total_words=dict(min=tw[0], median=med(tw), max=tw[-1], ge600=sum(1 for x in tw if x >= 600)),
        product_share_of_words_median=round(med([o['layer_words'] / o['words'] for o in outs]) * 100, 1),
        specific_sentences_layer_median_pct=round(med(spec10) * 100, 1),
        specific_sentences_layer_min_pct=round(min(spec10) * 100, 1),
        unique_sentences_layer_median_pct=round(med(uniq) * 100, 1),
        specific_sentences_whole_desc_median_pct=round(med(whole) * 100, 1),
        dup_threshold_products=thr,
        density=dict(min=round(dens[0], 2), median=round(med(dens), 2), max=round(dens[-1], 2),
                     in_range=sum(1 for x in dens if DENS_LO <= x <= DENS_HI)),
        kw_count=dict(Counter(o['kw_count'] for o in outs)),
        distinct_titles=len(set(o['title'] for o in outs)), distinct_metas=len(set(o['meta'] for o in outs)),
        distinct_keywords=len(set(o['kw'] for o in outs)),
        checks={k: '%d/%d' % (agg[k], N) for k in agg}, checks_n=dict(agg), fails={k: v[:12] for k, v in fails.items()},
        usage_rows=dict(Counter('%s/%s' % (o['usage'][0] or '—', o['usage'][1] or '—') for o in outs)),
        top_repeated=[(s, n) for s, n in df.most_common(6)],
    )
    return base


def write_family_csv(res, out_dir):
    path = os.path.join(out_dir, 'products-v6-%s.csv' % res['fam']['family_id'])
    bp.write_csv(path, [[o['id'], o['description'], o['excerpt'], o['title'], o['meta'], o['kw'], o['image_alt']] for o in res['outs']],
                 bp.COLS)
    return path

# ------------------------------------------------------------------ --all


RM_KEYS = ['الكلمة في العنوان', 'العنوان يبدأ بالكلمة', 'طول العنوان ≤60', 'الكلمة في الوصف التعريفي', 'طول الوصف التعريفي 120–160',
           'المحتوى يبدأ بالكلمة حرفياً', 'الكلمة في عنوان فرعي H2', 'المحتوى ≥600 كلمة', 'الكلمة في النص البديل للصورة',
           'الكلمة في الرابط (slug)']


def run_all(B, fdir, out_dir, report_path):
    have = sorted(f[:-5] for f in os.listdir(fdir) if f.endswith('.json') and os.path.exists(os.path.join(fdir, f[:-5] + '.html')))
    orphans = sorted(set(f.rsplit('.', 1)[0] for f in os.listdir(fdir) if f.endswith(('.json', '.html'))) - set(have))
    os.makedirs(out_dir, exist_ok=True)
    stats, failed, review, titles = [], [], [], Counter()
    for fid in have:
        try:
            res = build(B, fid, fdir)
        except (ValueError, KeyError, OSError) as e:
            failed.append((fid, '%s: %s' % (type(e).__name__, e)))
            continue
        write_family_csv(res, out_dir)
        st = measure(res, B)
        st['needs_confirmation'] = res['cfg'].get('needs_confirmation') or []
        stats.append(st)
        for o in res['outs']:
            titles[o['title']] += 1
        review += [(fid,) + r for r in res['review']]
    bp.write_csv(os.path.join(out_dir, 'review-needed-v6.csv'), review, ['family_id', 'id', 'name', 'url', 'reason'])
    missing = sorted(set(B.fams) - set(have))
    L = ['# تقرير بناء العائلات v6 — أرقام مقيسة', '',
         'مولَّد آلياً من `texa/scripts/build_family.py --all`. لا يتصل بالموقع. كل رقم أدناه محسوب من المخرجات نفسها.', '',
         '## الخلاصة', '',
         '- عائلات لها ملفا html+json: **%d** من %d في `families.json`. بُنيت %d، وفشلت %d.' % (len(have), len(B.fams), len(stats), len(failed)),
         '- منتجات كُتبت في ملفات CSV: **%d** (بأرقام %d، بلا قسم أرقام %d).' % (
             sum(s['generated'] for s in stats), sum(s.get('with_numbers', 0) for s in stats), sum(s.get('without_numbers', 0) for s in stats)),
         '- لم تُكتب: %d (يدوية/مستثناة/تخطٍّ)، منها %d بسبب فشل اختبار. التفاصيل في `data/out/review-needed-v6.csv` (%d صفاً).' % (
             sum(s['not_generated'] for s in stats), sum(s['test_failed'] for s in stats), len(review)),
         '- عناوين SEO مكررة بين كل العائلات: %d.' % sum(1 for v in titles.values() if v > 1),
         '- كلمات محظورة أو أسعار في المخرجات المكتوبة: 0 (أي منتج يخالف يُحجب عن CSV ويُسجَّل في ملف المراجعة).', '']
    if failed:
        L += ['## عائلات فشل بناؤها', '', '| العائلة | السبب |', '|---|---|'] + ['| `%s` | %s |' % (a, b.replace('|', '/')) for a, b in failed] + ['']
    L += ['## لكل عائلة', '',
          '| العائلة | النوع | منتجات | كُتب | بأرقام | بلا أرقام | لم يُكتب | كلمات العائلة | وسيط الكلمات | ≥600 | وسيط طبقة المنتج | الكثافة (أدنى–وسيط–أعلى) | ضمن 0.6–1.2 | جمل خاصة بالمنتج (وسيط) | الكلمة في الرابط | محظور |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for s in stats:
        if not s['generated']:
            L.append('| `%s` | %s | %d | 0 | — | — | %d | %d | — | — | — | — | — | — | — | — |' % (
                s['family'], s['kind'], s['family_count'], s['not_generated'], s['family_layer_words']))
            continue
        N = s['generated']
        L.append('| `%s` | %s | %d | %d | %d | %d | %d | %d | %s | %d/%d | %s | %s–%s–%s | %d/%d | %s%% | %d/%d | 0 |' % (
            s['family'], s['kind'], s['family_count'], N, s['with_numbers'], s['without_numbers'], s['not_generated'],
            s['family_layer_words'], bp.fnum(s['total_words']['median'], 0), s['total_words']['ge600'], N,
            bp.fnum(s['layer_words']['median'], 0), s['density']['min'], s['density']['median'], s['density']['max'],
            s['density']['in_range'], N, s['specific_sentences_layer_median_pct'], s['checks_n'].get('الكلمة في الرابط (slug)', 0), N))
    L += ['', '«جمل خاصة بالمنتج» = جمل طبقة المنتج (أطول من 25 حرفاً) التي تظهر حرفياً في أقل من 10% من منتجات العائلة. '
          '«لم يُكتب» = يدوي أو مستثنى أو فشل اختبار أو تخطٍّ بإعداد العائلة.', '',
          '## شروط Rank Math النصية (مجموع كل العائلات)', '', '| الشرط | المستوفي |', '|---|---|']
    tot = sum(s['generated'] for s in stats)
    for k in RM_KEYS:
        L.append('| %s | %d/%d |' % (k, sum(s.get('checks_n', {}).get(k, 0) for s in stats), tot))
    L += ['', 'الاختبارات الملزمة (assert لكل منتج قبل كتابته): لا كلمات محظورة ولا أسعار، كل الروابط من `category-links.json` أو الروابط الثابتة، '
          'الوصف ينتهي بالعلامة، الكلمة مقطع حرفي من الاسم وفي أول العنوان والوصف التعريفي وأول المحتوى وH2. '
          'ما عداها (600 كلمة، الكثافة، الرابط) يُقاس ولا يُفرض.', '']
    low = [(s['family'], s['generated'] - s['total_words']['ge600'], s['total_words']['min']) for s in stats
           if s['generated'] and s['total_words']['ge600'] < s['generated']]
    if low:
        L += ['## عائلات فيها أوصاف دون 600 كلمة', '', '| العائلة | عدد الأوصاف دون 600 | أقل وصف |', '|---|---|---|'] + [
            '| `%s` | %d | %d |' % x for x in low] + ['', 'السبب في الغالب منتج بلا قسم أرقام أو طبقة عائلة قصيرة؛ لم يُحشَ النص لبلوغ الرقم.', '']
    nc = [(s['family'], s['needs_confirmation']) for s in stats if s['needs_confirmation']]
    if nc:
        L += ['## يحتاج تأكيد المالك (من ملفات إعداد العائلات)', '']
        for fid, items in nc:
            L.append('**`%s`**' % fid)
            L += ['- %s' % i for i in items] + ['']
    if missing:
        L += ['## عائلات بلا ملفات بعد (%d)' % len(missing), '', '، '.join('`%s`' % m for m in missing), '']
    if orphans:
        L += ['## ملفات ناقصة الزوج (html بلا json أو العكس)', '', '، '.join('`%s`' % m for m in orphans), '']
    with open(report_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(L) + '\n')
    return stats, failed, review, missing


def main(argv):
    opts = dict(a[2:].split('=', 1) for a in argv if a.startswith('--') and '=' in a)
    flags = {a for a in argv if a.startswith('--') and '=' not in a}
    args = [a for a in argv if not a.startswith('--')]
    fdir = opts.get('dir', FAMILY_DIR)
    out_dir = opts.get('out', bp.OUT_DIR)
    if '--all' in flags:
        B = Base()
        report = QA_REPORT if 'out' not in opts else os.path.join(out_dir, os.path.basename(QA_REPORT))
        stats, failed, review, missing = run_all(B, fdir, out_dir, report)
        for s in stats:
            print('OK   %-20s %-9s wrote=%-4d numbers=%-4s plain=%-4s not_written=%d' % (
                s['family'], s['kind'], s['generated'], s.get('with_numbers', 0), s.get('without_numbers', 0), s['not_generated']))
        for fid, why in failed:
            print('FAIL %-20s %s' % (fid, why))
        print('families=%d built=%d failed=%d products=%d review_rows=%d without_files=%d\nreport=%s' % (
            len(stats) + len(failed), len(stats), len(failed), sum(s['generated'] for s in stats), len(review), len(missing), report))
        return 1 if failed else 0
    if not args:
        raise SystemExit(__doc__)
    family_id = args[0]
    B = Base()
    try:
        res = build(B, family_id, fdir)
    except ValueError as e:
        raise SystemExit('فشل بناء %s: %s' % (family_id, e))
    outs = res['outs']
    if '--sample' in flags or 'id' in opts:
        ids = [int(opts['id'])] if 'id' in opts else []
        o = ([x for x in outs if x['id'] in ids] or
             sorted(outs, key=lambda x: (-x['n_rows'], -int(bool(x['F']['code'])), x['id']))[:1])[0]
        print('ID=%d | %s\nkw=%s | words=%d | layer=%d | density=%.2f%%\nTITLE: %s\nMETA: %s\nSHORT: %s\n' % (
            o['id'], o['name'], o['kw'], o['words'], o['layer_words'], o['density'], o['title'], o['meta'], o['excerpt']))
        print(o['description'])
        return 0
    stats = measure(res, B)
    stats.pop('checks_n', None)
    if '--stats' not in flags:
        os.makedirs(out_dir, exist_ok=True)
        print('wrote %s rows=%d' % (write_family_csv(res, out_dir), len(outs)))
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print('REVIEW')
    for r in res['review']:
        print('  %s | %s | %s' % (r[0], r[1], r[3]))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
