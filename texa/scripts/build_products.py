#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مولّد أوصاف منتجات تكسا ديكور (txa-desc-v4).

يقرأ استجابات WooCommerce Store API الخام من data/raw/p*.json ويكتب:
  data/out/products-import-<القسم>[-NN].csv   ملفات استيراد WooCommerce (UTF-8 BOM)
  data/out/products-backup.csv                 نسخة احتياطية من الوصف الحالي
  data/out/review-needed.csv                   المستثنى/المتعارض/الناقص مع السبب
  reports/2026-11-21-products-generator-qa.md  تقرير الجودة بأرقام مقيسة

حتمي: لا عشوائية ولا تاريخ تشغيل؛ كل اختيار مبني على hash ثابت لرقم المنتج.
لا يتصل بالموقع ولا يعدّل شيئاً عليه. لا يكتب أي سعر في النصوص.

التشغيل:  python3 texa/scripts/build_products.py            (توليد + اختبارات + تقرير)
          python3 texa/scripts/build_products.py --test     (الاختبارات فقط)
"""
import csv
import glob
import hashlib
import html
import json
import math
import os
import re
import statistics
import sys
import urllib.parse
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_GLOB = os.path.join(BASE, 'data', 'raw', 'p*.json')
CAT_LINKS = os.path.join(BASE, 'data', 'category-links.json')
PILOT = os.path.join(BASE, 'data', 'pilot-output.json')
OUT_DIR = os.path.join(BASE, 'data', 'out')
REPORT = os.path.join(BASE, 'reports', '2026-11-21-products-generator-qa.md')

URL_CALC = 'https://texadecore.store/quantity-calculator/'
URL_INSTALL = 'https://texadecore.store/install-services/'
URL_GUIDE = 'https://texadecore.store/buying-guide/'
URL_ROLLS = 'https://texadecore.store/2026/11/21/wallpaper-rolls-per-room-table/'
MARK = '<!-- txa-desc-v4 -->'
BRAND_SUFFIX = ' | تكسا ديكور'
WALL_H = 2.8          # ارتفاع الجدار المعتمد في أمثلة الكميات
WASTE = 1.10          # 10% هدر للألواح والأرضيات
MAX_PER_FILE = 500

# ------------------------------------------------------------------ أدوات عامة

def H(pid, salt):
    """hash حتمي لاختيار الصياغات."""
    return int(hashlib.md5(('%s|%s' % (pid, salt)).encode('utf-8')).hexdigest()[:12], 16)


def pick(seq, pid, salt):
    return seq[H(pid, salt) % len(seq)]


_AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫', '01234567890123456789.')


def norm_digits(s):
    return s.translate(_AR_DIGITS)


def clean_text(h):
    """HTML -> نص، كل عنصر كتلي في سطر."""
    if not h:
        return ''
    h = re.sub(r'<!--.*?-->', ' ', h, flags=re.S)
    h = re.sub(r'<(br|/p|/li|/h\d|/tr|/div|/ul|/ol|/table|/blockquote)[^>]*>', '\n', h, flags=re.I)
    h = re.sub(r'</t[dh]>', ' ', h, flags=re.I)
    h = re.sub(r'<[^>]+>', '', h)
    h = html.unescape(h).replace('\xa0', ' ').replace('‏', '').replace('‎', '')
    h = re.sub(r'[ \t\r]+', ' ', h)
    h = re.sub(r' *\n *', '\n', h)
    return re.sub(r'\n+', '\n', h).strip()


def sentences(text):
    """طريقة التدقيق نفسها: تقسيم على [.؟!\\n] وجمل أطول من 40 حرفاً."""
    out = []
    for s in re.split(r'[.؟!\n]', text):
        s = s.strip()
        if len(s) > 40:
            out.append(s)
    return out


def fnum(x, nd=None):
    """تنسيق رقم: 16.5 / 3.54 / 0.222 بلا أصفار زائدة."""
    if nd is None:
        ax = abs(x)
        nd = 1 if ax >= 10 else (2 if ax >= 1 else 3)
    s = ('%.*f' % (nd, x)).rstrip('0').rstrip('.') if nd else '%d' % round(x)
    return s if s not in ('', '-0') else '0'


def parse_num(s):
    s = s.strip()
    if re.fullmatch(r'\d{1,3},\d{3}', s):
        return float(s.replace(',', ''))
    return float(s.replace(',', '.'))


def norm_ar(s):
    """تطبيع للمقارنة: همزات، تاء مربوطة، ألف مقصورة، تشكيل."""
    s = re.sub(r'[ً-ْـ]', '', s)
    s = re.sub('[أإآٱ]', 'ا', s)
    return s.replace('ة', 'ه').replace('ى', 'ي').lower()

# ------------------------------------------------------------------ الوحدات والمقاسات

NUM = r'(\d+(?:[.,]\d+)?)'
U_AREA = r'(?:م²|م2|م ²|متر\s*مربع|متر\s*مربّع|sqm|m2|m²)'
UNIT = r'(ملم|مم|مللي(?:متر)?|ملي(?:متر)?|mm|MM|سنتيمتر|سنتيميتر|سانتي|سم|cm|CM|أمتار|امتار|متر|م|m)'
_ARL = r'ء-ي'
UNIT_OPT = r'(?:\s*' + UNIT + r'(?![' + _ARL + r'a-zA-Z²2]))?'
ANNOT = r'(?:\s*\(\s*(?:طول|عرض|ارتفاع|الطول|العرض|الارتفاع)\s*\))?'
LBL = r'(?:(?:ال)?(?:طول|عرض|ارتفاع)\s*)?'
SEP = r'\s*[×xX\*✕✖]\s*'
PAIR_RE = re.compile(LBL + NUM + UNIT_OPT + ANNOT + SEP + LBL + NUM + UNIT_OPT + ANNOT +
                     r'(?:' + SEP + LBL + NUM + UNIT_OPT + r')?')
LABELED_RE = re.compile(r'(طول|ارتفاع|عرض)(?:ه|ها)?(?:\s+(?!و?(?:طول|عرض|ارتفاع))[^\d\s:：×*()]{1,12}){0,3}?'
                        r'\s*[:：]?\s*' + NUM + r'\s*' + UNIT + r'(?![' + _ARL + r'a-zA-Z²2])')
THICK_RE = re.compile(r'(?:سماكة|السماكة|سمك|السمك|بسماكة|وسماكة|سماكته|سماكتها)(?:\s+(?:ال)?(?:لوح|قطعة|شريحة))?'
                      r'\s*[:：]?\s*' + NUM + r'\s*(ملم|مم|مللي|ملي|mm|MM|سم|cm)')
NAME_THICK_RE = re.compile(NUM + r'\s*(ملم|مم|mm|MM)(?![' + _ARL + r'a-zA-Z])')


def unit_factor(u):
    if u is None:
        return None
    u = u.lower()
    if u in ('ملم', 'مم', 'mm') or u.startswith('مللي') or u.startswith('ملي'):
        return 0.001
    if u in ('سم', 'cm', 'سنتيمتر', 'سنتيميتر', 'سانتي'):
        return 0.01
    return 1.0

# نطاقات المعقولية (بالمتر): (أدنى طول، أقصى طول، أدنى عرض، أقصى عرض) للضلع الأطول/الأقصر
PLAUS = {
    'wallpaper': (5.0, 30.0, 0.45, 1.40),
    'panel':     (2.0, 3.30, 0.45, 2.60),
    'slat':      (1.8, 4.00, 0.03, 0.44),
    'small':     (0.30, 3.30, 0.15, 1.30),   # بديل طوب/حجر/صفائح
    'floor':     (0.30, 2.30, 0.09, 1.00),
    'linear':    (1.0, 4.00, 0.005, 0.60),
    'post':      (1.5, 4.00, 0.02, 0.60),
    'piece':     (0.05, 4.00, 0.005, 2.60),
}


def plausible(kind, a, b):
    lo, hi = min(a, b), max(a, b)
    r = PLAUS.get(kind)
    if not r:
        return True
    return r[0] <= hi <= r[1] and r[2] <= lo <= r[3]


def same(a, b, tol=0.025):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


def same_pair(p, q, tol=0.025):
    a, b = sorted(p), sorted(q)
    return same(a[0], b[0], tol) and same(a[1], b[1], tol)


DIM_KEYS = ('المقاس', 'الأبعاد', 'الابعاد', 'أبعاد', 'ابعاد', 'المقاسات', 'مقاس', 'الحجم', 'القياس')
CTX_OK = re.compile(r'(مقاس|قياس|أبعاد|ابعاد|الأبعاد|قطعة|لوح|ألواح|لفة|رول|شريحة|بلاطة|صفيحة|حجم|عود|قضيب)')
CTX_BAD = re.compile(r'(جدار|غرفة|غرف|حائط|مساحة|صالة|مجلس|إطار|اطار|÷|=)')


def split_kv(line):
    m = re.match(r'^[\s\-–•✅*·]*([^:：]{2,32})[:：]\s*(.+)$', line)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, line


def raw_pairs(text, strict_ctx=True):
    """يستخرج أزواج (رقم، وحدة) ×(رقم، وحدة) [× ثالث] من نص مع سياقها."""
    found = []
    for line in norm_digits(text).split('\n'):
        key, _ = split_kv(line)
        key_ok = bool(key) and any(k in key for k in DIM_KEYS)
        for m in PAIR_RE.finditer(line):
            ctx = line[max(0, m.start() - 45):m.start()]
            tail = line[m.end():m.end() + 6]
            if re.match(r'\s*' + U_AREA, tail):
                continue
            if strict_ctx and not key_ok:
                if CTX_BAD.search(ctx) or not CTX_OK.search(ctx):
                    continue
            g = m.groups()
            vals = [(g[0], g[1]), (g[2], g[3])]
            if g[4] is not None:
                vals.append((g[4], g[5]))
            found.append((vals, m.group(0)))
    return found


def interpret(vals, kind, allow_unitless=False):
    """يحوّل زوجاً خاماً إلى أمتار. يعيد (a, b, thickness|None, status)
    status: 'ok' | 'repaired' (وحدة غير منطقية أُعيد تفسيرها) | None (مرفوض)."""
    nums = [parse_num(v) for v, _ in vals]
    units = [u for _, u in vals]
    if all(u is None for u in units):
        if not allow_unitless:
            return None
        units = [None] * len(vals)
    else:
        # الوحدة الناقصة تؤخذ من أقرب وحدة على اليمين ثم اليسار
        for i in range(len(units)):
            if units[i] is None:
                nxt = [u for u in units[i + 1:] if u]
                prv = [u for u in units[:i] if u]
                units[i] = nxt[0] if nxt else prv[-1]
    linear = kind in ('linear', 'post')

    def build(fs):
        vs = [n * f for n, f in zip(nums, fs)]
        t = None
        if len(vs) == 3:
            if linear:
                hi = max(vs)
                rest = sorted(vs)[:2]
                return hi, rest[1], None          # الطول × أعرض وجه في المقطع
            lo = min(vs)
            if lo <= 0.06 and vs.count(lo) == 1:
                t = lo
                vs = [v for v in vs if v != lo]
            else:
                vs = vs[:2]
        return vs[0], vs[1], t

    if units[0] is not None:
        fs = [unit_factor(u) for u in units]
        a, b, thick = build(fs)
        if plausible(kind, a, b):
            return a, b, thick, 'ok'
    # إعادة تفسير الوحدة: تُقبل فقط إذا وُجد تفسير واحد معقول لنوع المنتج
    import itertools
    hits = []
    for fs in itertools.product((1.0, 0.01, 0.001), repeat=len(nums)):
        a, b, t = build(list(fs))
        if plausible(kind, a, b) and not any(same(a, h[0], 0.001) and same(b, h[1], 0.001) for h in hits):
            hits.append((a, b, t))
    if len(hits) == 1:
        a, b, t = hits[0]
        return a, b, t, 'repaired'
    return None


def field_dims(p, kind):
    """حقل الأبعاد في WooCommerce (الوحدة المعلنة سنتيمتر)."""
    d = p.get('dimensions') or {}
    try:
        L = float(d.get('length') or 0)
        W = float(d.get('width') or 0)
    except ValueError:
        return None
    if L <= 0 or W <= 0:
        return None
    for f in (0.01, 0.001):
        a, b = L * f, W * f
        if plausible(kind, a, b):
            return (a, b, 'cm' if f == 0.01 else 'mm')
    return ('bad', L, W)

# ------------------------------------------------------------------ التصنيف

ROOT_FILE = {
    'ورق-الجدران': 'wallpaper', 'الباركيه': 'parquet', 'عروض-بديل-الخشب': 'wood-alt',
    'بديل-الشيبورد': 'shiplap-alt', 'بديل-رخام': 'marble-alt', 'نعلات': 'skirting',
    'البانوهات-والزخارف': 'moldings', 'بديل-الطوب': 'brick-alt', 'صفائح-طينية-وحجرية': 'clay-stone-sheets',
    'بديل-الحجر': 'stone-alt', 'التكسيات': 'cladding', 'موكيت': 'carpet', 'اعمدة-بارتشن': 'partition',
}
OFFER_ROOT = 'اشترِ-1-و-احصل-على-1-مجاناً'


def load_cat_links():
    links = json.load(open(CAT_LINKS, encoding='utf-8'))
    paths = {}
    for name, url in links.items():
        path = urllib.parse.unquote(url.split('product-category/')[1]).strip('/').split('/')
        paths[name] = path
    root_name = {}
    for name, path in paths.items():
        if len(path) == 1:
            root_name[path[0]] = name
    return links, paths, root_name


ACC_WORDS = re.compile(r'^\s*(?:إكسسوارات\s+|اكسسوارات\s+)?(قفلة|فاصل|فواصل|إكسسوار|اكسسوار|كورنر|زاوية|زوايا|لاصق|غراء|سيليكون|مسامير)')


def classify(p, paths):
    name = html.unescape(p['name'])
    cats = [c['name'] for c in p['categories']]
    roots = []
    for c in cats:
        if c in paths and paths[c][0] != OFFER_ROOT and paths[c][0] not in roots:
            roots.append(paths[c][0])
    if not roots or re.search(r'^خدمة|خدمة\s+(رفع|تركيب|قياس)', name):
        return None
    cs = set(cats)
    # القسم الرئيسي للملف: جذر أول قسم غير عروض، مع ترجيح الأقسام الأعمق
    root = roots[0]
    nn = norm_ar(name)
    acc = bool(ACC_WORDS.search(name))
    if root == 'ورق-الجدران':
        return dict(kind='wallpaper', sub='wallpaper', root=root)
    if cs & {'فواصل وإكسسوارات الباركيه', 'إكسسوارات بديل الخشب', 'إكسسوارات بديل الشيبورد'} or \
            (acc and root in ('بديل-الشيبورد', 'عروض-بديل-الخشب', 'الباركيه', 'بديل-رخام')):
        return dict(kind='linear', sub='accessory', root=root)
    if root == 'الباركيه':
        if 'spc' in nn or 'اس بي سي' in nn or cs & {'باركيه ضد الماء SPC', 'باركيه ضد الماء SPC (شرائح)', 'باركيه ضد الماء SPC (بلاطات)'}:
            return dict(kind='floor', sub='spc', root=root)
        return dict(kind='floor', sub='laminate', root=root)
    if root == 'موكيت':
        return dict(kind='floor', sub='carpet', root=root)
    if root == 'نعلات':
        return dict(kind='linear', sub='skirting', root=root)
    if root == 'البانوهات-والزخارف':
        if cs & {'زوايا بانوهات', 'أطقم زوايا الأسقف', 'إكسسوارات ديكور'} or re.search(r'(طقم|زاوية|زوايا|وردة|صرة|إكسسوار|اكسسوار)', name):
            return dict(kind='piece', sub='decor', root=root)
        if re.search(r'(عمود|أعمدة|اعمدة|تاج|قاعدة)', name):
            return dict(kind='piece', sub='decor', root=root)
        if re.search(r'(كرنيش|كورنيش|كرانيش)', name):
            return dict(kind='linear', sub='cornice', root=root)
        return dict(kind='linear', sub='molding', root=root)
    if root == 'اعمدة-بارتشن':
        return dict(kind='post', sub='partition', root=root)
    if root == 'عروض-بديل-الخشب':
        return dict(kind='slat', sub='wood', root=root)
    if root == 'بديل-الشيبورد':
        return dict(kind='panel', sub='shiplap', root=root)
    if root == 'بديل-رخام':
        return dict(kind='panel', sub='marble', root=root)
    if root == 'بديل-الطوب':
        return dict(kind='small', sub='brick', root=root)
    if root == 'بديل-الحجر':
        return dict(kind='small', sub='stone', root=root)
    if root == 'صفائح-طينية-وحجرية':
        return dict(kind='small', sub='clay', root=root)
    if root == 'التكسيات':
        if 'hpl' in nn:
            return dict(kind='panel', sub='hpl', root=root)
        return dict(kind='slat', sub='exterior', root=root)
    return dict(kind='piece', sub='decor', root=root)

# ------------------------------------------------------------------ معجم الألوان والنقشات

# (المفتاح القانوني، الصيغة المعرّفة، كلمات الاسم بعد التطبيع)
COLORS = [
    ('أوف وايت', 'الأوف وايت', ['اوف وايت', 'اوف-وايت', 'سكري']),
    ('أبيض', 'الأبيض', ['ابيض', 'وايت', 'بيضاء', 'white']),
    ('كريمي', 'الكريمي', ['كريمي', 'عاجي', 'كريم', 'ايفوري', 'فانيلا']),
    ('بيج', 'البيج', ['بيج', 'رملي', 'بيجي', 'كابتشينو', 'بوتشينو', 'كراميل', 'beige']),
    ('رمادي', 'الرمادي', ['رمادي', 'رصاصي', 'جراي', 'اسمنتي', 'فحمي', 'gray', 'grey', 'دخاني']),
    ('فضي', 'الفضي', ['فضي', 'سيلفر', 'بلاتينيوم', 'بلاتينيم', 'sliver', 'silver']),
    ('أسود', 'الأسود', ['اسود', 'بلاك', 'سوداء', 'black']),
    ('بني', 'البني', ['بني', 'جوزي', 'عسلي', 'بلوط', 'تيك', 'وينجي', 'شوكولا', 'شوكولاته', 'موكا', 'كاكاو', 'قهوه', 'برونزي', 'bronz', 'brown', 'خشبي']),
    ('ذهبي', 'الذهبي', ['ذهبي', 'جولد', 'نحاسي', 'gold']),
    ('أزرق', 'الأزرق', ['ازرق', 'كحلي', 'سماوي', 'تركواز', 'نيلي', 'فيروزي', 'بترولي', 'blue']),
    ('أخضر', 'الأخضر', ['اخضر', 'زيتي', 'زيتوني', 'مريمي', 'فستقي', 'نعناعي', 'green']),
    ('وردي', 'الوردي', ['وردي', 'زهري', 'بينك', 'روز', 'pink']),
    ('أحمر', 'الأحمر', ['احمر', 'عنابي', 'نبيتي', 'طوبي', 'خمري', 'red']),
    ('أصفر', 'الأصفر', ['اصفر', 'خردلي', 'ليموني', 'yellow']),
    ('بنفسجي', 'البنفسجي', ['بنفسجي', 'موف', 'ليلكي', 'لافندر']),
    ('برتقالي', 'البرتقالي', ['برتقالي', 'مشمشي', 'خوخي', 'orange']),
]
COLOR_WORD = {}
for key, _d, words in COLORS:
    for w in words:
        COLOR_WORD[norm_ar(w)] = key
COLOR_DEF = {k: d for k, d, _ in COLORS}
ATTR_COLOR = {norm_ar(k): k for k, _, _ in COLORS}
MODIFIERS = {norm_ar(w) for w in ['فاتح', 'غامق', 'داكن', 'محمر', 'محروق', 'ثلجي', 'دافئ', 'بارد', 'هادئ', 'ناعم', 'مطفي',
                                  'ساطع', 'خافت', 'متوسط', 'مدرج', 'ترابي', 'شاحب', 'عميق', 'قطني', 'لؤلؤي', 'مائل', 'مصفر', 'مخضر', 'مزرق']}
NICE = {'ابيض': 'أبيض', 'اسود': 'أسود', 'ازرق': 'أزرق', 'اخضر': 'أخضر', 'احمر': 'أحمر', 'اصفر': 'أصفر', 'رمادى': 'رمادي',
        'اوف': 'أوف', 'ساده': 'سادة', 'رمادي': 'رمادي'}
DARK = {norm_ar(w) for w in ['غامق', 'داكن', 'محروق', 'فحمي', 'وينجي', 'عميق']}
LIGHT = {norm_ar(w) for w in ['فاتح', 'ثلجي', 'قطني', 'شاحب', 'لؤلؤي']}

PATTERNS = [
    # (المفتاح، كلمات الاسم، أقسام)
    ('kids', ['اطفال', 'كرتون', 'سنوبي', 'ديزني'], ['ورق جدران أطفال']),
    ('3d', ['ثري دي', '3d', 'بارز', 'بارزه', 'ثلاثي الابعاد'], ['بديل رخام ثري دي']),
    ('fluted', ['مضلع', 'اضلاع'], ['بديل خشب مضلع']),
    ('herringbone', ['هرمي'], ['باركيه هرمي', 'بديل شيبورد هرمي']),
    ('floral', ['ورود', 'زهور', 'ورد', 'نباتي', 'اوراق', 'زهره', 'شجر'], ['تصميم ورود']),
    ('stripe', ['مقلم', 'مخطط', 'خطوط', 'مخططه'], ['تصميم ساده مقلم']),
    ('ornament', ['نقشات', 'دمشقي', 'كلاسيك', 'زخرفه', 'اندلسي', 'منقوش'], ['تصميم نقشات', 'تصميم كلاسيك']),
    ('marble', ['رخامي', 'عروق', 'بعروق', 'اوبن بوك', 'ريزن'], ['تصميم رخامي', 'بديل شيبورد رخامي', 'بديل رخام اوبن بوك', 'بديل رخام الريزن']),
    ('fabric', ['قماشي', 'قماش', 'كتان', 'نسيج', 'ليزر'], ['بديل شيبورد قماشي', 'بديل رخام قماش وليزر']),
    ('stone', ['حجري', 'صخري', 'كونكريت', 'اسمنتي', 'طوب', 'حجر', 'تيرازو', 'جرانيتي', 'محبب', 'خشن'],
     ['بديل رخام كونكريت', 'بديل رخام حجري']),
    ('glossy', ['لامع', 'لامعه'], ['بديل رخام لامع']),
    ('wood', ['خشبي', 'خشب', 'بلوط', 'جوزي', 'تيك'], ['بديل شيبورد خشبي']),
    ('wave', ['مموج', 'مودرن', 'هندسي', 'امواج'], ['تصميم مموج', 'تصميم مودرن']),
    ('plain', ['ساده', 'سادة'], ['تصميم ساده', 'بديل شيبورد سادة']),
]

ORIGINS = [
    ('كوريا الجنوبية', ['كوريا الجنوبيه']),
    ('كوريا', ['كوري', 'كوريا', 'كوريه']),
    ('الصين', ['الصين', 'صيني', 'صينيه', 'صين']),
    ('بلجيكا', ['بلجيكا', 'بلجيكي', 'بليجي']),
    ('ألمانيا', ['المانيا', 'الماني']),
    ('تركيا', ['تركيا', 'تركي']),
    ('السعودية', ['السعوديه', 'سعودي']),
    ('محلي', ['محلي', 'وطني']),
]
ORIGIN_KEYS = ('بلد المنشأ', 'بلد المنشا', 'بلد الصنع', 'الصناعة', 'التصنيع', 'المنشأ', 'صنع في')

MATERIALS = [
    ('SPC', r'\bspc\b|اس بي سي'),
    ('WPC', r'\bwpc\b'),
    ('PVC', r'\bpvc\b|بي في سي|بولي فينيل|بولي فينيل كلور'),
    ('بوليسترين (PS)', r'\bps\b|بوليسترين|بولي ستايرين'),
    ('فوم بولي يوريثان (PU)', r'\bpu\b|بولي يوريثان|بولي يوريثين'),
    ('HPL', r'\bhpl\b'),
    ('HDF', r'\bhdf\b'),
    ('MDF', r'\bmdf\b'),
    ('فوم بورد', r'فوم بورد'),
    ('ستيل', r'ستيل|ستانلس'),
    ('ألمنيوم', r'المنيوم|الومنيوم'),
]
MATERIAL_KEYS = ('الخامة', 'المادة الأساسية', 'مادة الصنع', 'الخامات الرئيسية', 'الخامات الأساسية', 'مادة التصنيع', 'النوع', 'الخامات')

# ------------------------------------------------------------------ استخراج الحقائق

CODE_SPLIT = re.compile(r'\s+[–—\-_]\s+')


def split_name(name, sku):
    """(label بلا كود، code)."""
    name = re.sub(r'\s+', ' ', html.unescape(name)).strip()
    parts = CODE_SPLIT.split(name)
    label = parts[0].strip()
    code = ''
    if len(parts) > 1:
        tail = [t for t in parts[1:] if not re.fullmatch(r'تكسا\s*\d*', t.strip())]
        if tail:
            code = tail[0].strip()
    sku = (sku or '').strip()
    if not code and sku and label.endswith(sku) and len(label) > len(sku) + 3:
        label = label[:-len(sku)].strip(' -–_')
        code = sku
    if not code:
        code = sku
    return name, label, code


def find_color(label, attrs, cats):
    toks = label.split()
    ntoks = [norm_ar(t.strip('()،,')) for t in toks]
    runs, i = [], 0
    while i < len(toks):
        two = (ntoks[i] + ' ' + ntoks[i + 1]) if i + 1 < len(toks) else None
        key, span = None, 0
        if two and two in COLOR_WORD:
            key, span = COLOR_WORD[two], 2
        elif ntoks[i] in COLOR_WORD:
            key, span = COLOR_WORD[ntoks[i]], 1
        if key:
            j = i + span
            while j < len(toks) and (ntoks[j] in MODIFIERS or ntoks[j] in COLOR_WORD):
                j += 1
            runs.append((key, i, j))
            i = j
        else:
            i += 1
    # «خشبي» وحدها وصف لا لون إن وُجد لون صريح آخر
    real = [r for r in runs if not (r[2] - r[1] == 1 and ntoks[r[1]] == norm_ar('خشبي'))] or runs
    if real:
        key, a, b = real[0]
        words = [NICE.get(norm_ar(t.strip('()،,')), t.strip('()،,')) for t in toks[a:b]]
        phrase = ' '.join(words)
        tone = 'dark' if any(n in DARK for n in ntoks[a:b]) else ('light' if any(n in LIGHT for n in ntoks[a:b]) else '')
        return key, phrase, tone, 'name'
    for a in attrs:
        if a['name'] == 'لون' and len(a['terms']) == 1:
            k = ATTR_COLOR.get(norm_ar(a['terms'][0]['name']))
            if k:
                return k, k, '', 'attr'
    for c in cats:
        for k, _, _ in COLORS:
            if norm_ar(c).endswith(' ' + norm_ar(k)):
                return k, k, '', 'cat'
    return None, '', '', ''


def find_pattern(label, cats):
    nl = ' ' + norm_ar(label) + ' '
    for key, words, pcats in PATTERNS:
        for w in words:
            if (' ' + norm_ar(w) + ' ') in nl or (' ' + norm_ar(w)) in nl and len(w) > 4:
                return key
    for key, words, pcats in PATTERNS:
        if set(pcats) & set(cats):
            return key
    return None


def find_origin(name, lines):
    found = {}
    nn = ' ' + norm_ar(name) + ' '
    for canon, words in ORIGINS:
        for w in words:
            if ' ' + w + ' ' in nn:
                found.setdefault('name', set()).add(canon)
    for key, val in lines:
        if key and any(norm_ar(k) in norm_ar(key) for k in ORIGIN_KEYS):
            nv = ' ' + norm_ar(re.sub(r'[.،,:()]', ' ', val)) + ' '
            for canon, words in ORIGINS:
                if any(' ' + w + ' ' in nv for w in words):
                    found.setdefault('line', set()).add(canon)
                    break
    allv = set().union(*found.values()) if found else set()
    if 'كوريا الجنوبية' in allv:
        allv.discard('كوريا')
    if 'السعودية' in allv:
        allv.discard('محلي')
    if len(allv) == 1:
        return allv.pop(), None
    if len(allv) > 1:
        return None, 'تعارض في بلد المنشأ: ' + ' / '.join(sorted(allv))
    return None, None


def find_material(name, lines, text):
    found = set()

    def scan(s):
        ns = norm_ar(s)
        for canon, rx in MATERIALS:
            if re.search(rx, ns):
                found.add(canon)
    scan(name)
    for key, val in lines:
        if key and any(norm_ar(k) == norm_ar(key) for k in MATERIAL_KEYS):
            scan(val[:80])
    for m in re.finditer(r'(?:مصنوع(?:ة)?\s+من|مصنّع(?:ة)?\s+من|خامة|بخامة)\s+([^.،\n]{2,40})', text):
        scan(m.group(1))
    for m in re.finditer(r'(?:لوح|ألواح|الواح)\s*\(?\s*([A-Za-z]{2,4})\b', text):
        scan(m.group(1))
    # SPC يحتوي PVC في تركيبه؛ لا يُعد تعارضاً
    if 'SPC' in found:
        found.discard('PVC')
    if len(found) == 1:
        return found.pop(), None
    if len(found) > 1:
        return None, 'تعارض في الخامة: ' + ' / '.join(sorted(found))
    return None, None


WATER_RE = re.compile(r'(مقاوم(?:ة)?\s+للماء|ضد\s+الماء|مقاومة\s+الماء\s*[:：]\s*(?:نعم|100)|لا\s+يتأثر\s+بالماء)')
CLICK_RE = re.compile(r'(كليك|تعشيق)')
CARTON_RE = re.compile(r'(?:(?:تغطي(?:ة)?|يغطي)\s+الكرتون(?:ة)?(?:\s+الواحد(?:ة)?)?|تعبئة\s+الكرتون(?:ة)?|الكرتون(?:ة)?\s+(?:الواحد(?:ة)?\s+)?(?:تغطي|يغطي))\s*[:：]?\s*(?:نحو\s+)?' + NUM + r'\s*' + U_AREA)
UNITCOV_RES = [
    re.compile(r'\(\s*' + NUM + r'\s*' + U_AREA + r'\s*(?:لل?ّ?وح|للفة|للقطعة|للشريحة|للصفيحة)?\s*\)'),
    re.compile(r'(?:الواحد(?:ة)?\s+)?(?:يغطي|تغطي)\s+(?:نحو\s+|حوالي\s+)?' + NUM + r'\s*' + U_AREA),
    re.compile(r'التغطية\s*[:：]\s*(?:نحو\s+|حوالي\s+)?' + NUM + r'\s*' + U_AREA),
    re.compile(r'مساحة\s+(?:القطعة|اللوح|الشريحة)\s+' + NUM + r'\s*' + U_AREA),
]
PCS_CARTON_RE = re.compile(r'(?:العدد\s+بالكرتون(?:ة)?|عدد\s+(?:القطع|الألواح|الشرائح)\s+(?:في|ب)\s*الكرتون(?:ة)?)\s*[:：]?\s*(\d+)')
UNIT_SALE_RE = re.compile(r'(?:الوحدة|وحدة\s+السعر|وحدة\s+البيع)\s*[:：]\s*([^\n.،]{2,20})')
PER_M2_RE = re.compile(r'(السعر\s+(?:المعروض\s+)?لل?متر\s+المربع|بالمتر\s+المربع|وحدة\s+السعر\s*[:：]\s*المتر\s+المربع)')


def extract(p, paths):
    F = dict(id=p['id'], url=p['permalink'], issues=[], excluded=None)
    name, label, code = split_name(p['name'], p.get('sku'))
    F.update(name=name, label=label, code=code, sku=(p.get('sku') or '').strip())
    cats = [c['name'] for c in p['categories']]
    F['cats'] = cats
    cl = classify(p, paths)
    if cl is None:
        F['excluded'] = 'خدمة أو منتج بلا قسم — لا تنطبق عليه قوالب المنتجات'
        F.update(kind='service', sub='service', root=None)
        return F
    F.update(cl)
    kind = F['kind']
    desc = clean_text(p.get('description'))
    desc = re.split(r'\n\s*منتجات ذات صلة', desc)[0]     # قائمة منتجات أخرى ليست من بيانات هذا المنتج
    short = clean_text(p.get('short_description'))
    F['old_desc_text'] = desc
    lines = [split_kv(l) for l in norm_digits(desc).split('\n')]
    F['color'], F['color_phrase'], F['tone'], F['color_src'] = find_color(label, p.get('attributes') or [], cats)
    F['pattern'] = find_pattern(label, cats)

    # ---- المقاس
    cands = []      # (a, b, src, status)
    thick = []      # (mm, src)
    for src, text in (('الاسم', name), ('الوصف', desc), ('الوصف المختصر', short)):
        for vals, raw in raw_pairs(text, strict_ctx=(src != 'الاسم')):
            r = interpret(vals, kind, allow_unitless=(src == 'الاسم'))
            if r:
                a, b, t, st = r
                cands.append((a, b, src, st, raw))
                if t and st == 'ok':
                    thick.append((round(t * 1000, 2), src))
    # قيم موسومة (الطول/العرض/الارتفاع)
    singles = []
    for src, text in (('الوصف', desc), ('الوصف المختصر', short), ('الاسم', name)):
        labeled = []
        for line in norm_digits(text).split('\n'):
            ms = list(LABELED_RE.finditer(line))
            if not ms:
                continue
            if PAIR_RE.search(line) and len(ms) < 2:
                continue
            got = []
            for m in ms:
                ctx = line[max(0, m.start() - 30):m.start()]
                if CTX_BAD.search(ctx):
                    continue
                got.append((m.group(2), m.group(3)))
            if len(got) >= 2:
                r = interpret(got[:2], kind)
                if r:
                    cands.append((r[0], r[1], src, r[3], line.strip()[:60]))
                    continue
            labeled.extend(got)
        vals = []
        for n, u in labeled:
            v = parse_num(n) * unit_factor(u)
            if not any(same(v, x, 0.005) for x in vals):
                vals.append(v)
        rawl = []
        for n, u in labeled:
            if (n, u) not in rawl:
                rawl.append((n, u))
        if len(rawl) == 2:
            r = interpret(rawl, kind)
            if r:
                cands.append((r[0], r[1], src, r[3], 'طول/عرض'))
        elif len(rawl) == 1 and src != 'الاسم':
            singles.append((vals[0], src))
    # مقاس مفرد في الاسم مثل «12 سم»
    m1 = re.search(NUM + r'\s*(سم|cm)(?![' + _ARL + r'])', norm_digits(label))
    name_single = parse_num(m1.group(1)) * 0.01 if (m1 and not PAIR_RE.search(norm_digits(label))) else None

    fd = field_dims(p, kind)
    field = (fd[0], fd[1]) if fd and fd[0] != 'bad' else None
    F['field_bad'] = bool(fd and fd[0] == 'bad')
    ok = [c for c in cands if c[3] == 'ok']
    rep = [c for c in cands if c[3] == 'repaired']
    groups = []
    for c in ok:
        if not any(same_pair((c[0], c[1]), (g[0], g[1])) for g in groups):
            groups.append(c)
    dims, dims_src = None, None
    conflict = None
    if len(groups) > 1:
        conflict = 'مقاسان مختلفان في بيانات المنتج: ' + ' ↔ '.join('%s×%s م (%s)' % (fnum(g[0], 3), fnum(g[1], 3), g[2]) for g in groups[:3])
    elif len(groups) == 1:
        g = groups[0]
        dims, dims_src = (g[0], g[1]), g[2]
        for r in rep:
            if not same_pair((r[0], r[1]), dims):
                conflict = 'مقاس بوحدة غير منطقية في %s (%s) يخالف المقاس الآخر' % (r[2], r[4])
        if field and not same_pair(field, dims):
            conflict = 'المقاس في النص %s×%s م يخالف حقل الأبعاد %s×%s م' % (
                fnum(dims[0], 3), fnum(dims[1], 3), fnum(field[0], 3), fnum(field[1], 3))
        elif fd and fd[0] == 'bad':
            conflict = 'المقاس في النص %s×%s م يخالف حقل الأبعاد (%s × %s سم)' % (
                fnum(dims[0], 3), fnum(dims[1], 3), fnum(fd[1], 1), fnum(fd[2], 1))
    elif rep:
        rg = []
        for c in rep:
            if not any(same_pair((c[0], c[1]), (g[0], g[1])) for g in rg):
                rg.append(c)
        if len(rg) == 1 and field and same_pair(field, (rg[0][0], rg[0][1])):
            dims, dims_src = (rg[0][0], rg[0][1]), 'الوصف (وحدة مصحّحة بمطابقة حقل الأبعاد)'
            F['issues'].append(('note', 'وحدة المقاس في الوصف مكتوبة خطأ (%s) وصُحّحت بمطابقة حقل الأبعاد' % rg[0][4]))
        elif field:
            conflict = 'المقاس في الوصف بوحدة غير منطقية (%s) ولا يطابق حقل الأبعاد %s×%s م' % (
                rg[0][4], fnum(field[0], 3), fnum(field[1], 3))
        else:
            F['issues'].append(('missing', 'المقاس في الوصف بوحدة غير منطقية (%s) ولا مصدر ثانٍ يؤكده' % rg[0][4]))
    if kind == 'post' and dims is None and not conflict:
        hs = []
        for m in LABELED_RE.finditer(norm_digits(desc)):
            if m.group(1) in ('ارتفاع', 'طول'):
                v = parse_num(m.group(2)) * unit_factor(m.group(3))
                if 1.5 <= v <= 4.0 and not any(same(v, h, 0.005) for h in hs):
                    hs.append(v)
        if len(hs) == 1:
            if field and not same(max(field), hs[0]):
                conflict = 'ارتفاع العمود في الوصف %s م يخالف حقل الأبعاد %s م' % (fnum(hs[0], 2), fnum(max(field), 2))
            else:
                F['post_h'] = hs[0]
        elif len(hs) > 1:
            conflict = 'ارتفاع العمود مذكور بقيم مختلفة: ' + ' / '.join(fnum(h, 2) + ' م' for h in hs)
    F['field'] = field
    F['field_only'] = False
    if dims is None and not conflict and field and not rep:
        F['field_only'] = True     # يُحسم في المرور الثاني (مطابقة مقاس مؤكَّد في القسم نفسه)
    # منتج طولي: عرض من الاسم/الوصف + طول من الحقل
    width_single = name_single
    if width_single is None and singles:
        sv = []
        for v, _s in singles:
            if not any(same(v, x) for x in sv):
                sv.append(v)
        if len(sv) == 1:
            width_single = sv[0]
    F['single'] = width_single
    if dims and width_single and kind in ('linear', 'slat', 'post') and width_single < 1.0:
        if not any(same(width_single, d, 0.03) for d in dims) and not thick:
            pass  # مقاس الاسم قد يكون سماكة أو مقاساً تجارياً؛ لا يُعد تعارضاً
    if conflict:
        F['issues'].append(('conflict', conflict))
        dims = None
        F['field_only'] = False
    F['dims'], F['dims_src'] = dims, dims_src
    F['dims_conflict'] = bool(conflict)

    # ---- السماكة
    for src, text in (('الوصف', desc), ('الوصف المختصر', short)):
        for m in THICK_RE.finditer(norm_digits(text)):
            v = parse_num(m.group(1)) * (10 if m.group(2) in ('سم', 'cm') else 1)
            thick.append((round(v, 2), src))
    for m in NAME_THICK_RE.finditer(norm_digits(name)):
        pre = norm_digits(name)[max(0, m.start() - 3):m.start()]
        if re.search(r'[×xX\*]\s*$', pre):
            continue
        thick.append((round(parse_num(m.group(1)), 2), 'الاسم'))
    tv = sorted({t for t, _ in thick if 0.5 <= t <= 60})
    F['thick'] = None
    if len(tv) == 1:
        F['thick'] = tv[0]
    elif len(tv) > 1:
        F['issues'].append(('conflict', 'تعارض في السماكة: ' + ' / '.join('%s ملم (%s)' % (fnum(t, 1), ', '.join(sorted({s for x, s in thick if x == t}))) for t in tv)))

    # ---- التغطية المذكورة
    nd = norm_digits(desc + '\n' + short)
    carton = sorted({round(parse_num(m.group(1)), 3) for m in CARTON_RE.finditer(nd)})
    carton = [c for c in carton if 0.5 <= c <= 6.0]
    F['carton'] = carton[0] if len(carton) == 1 else None
    if len(carton) > 1:
        F['issues'].append(('conflict', 'تغطية الكرتونة مذكورة بقيم مختلفة: ' + ' / '.join(fnum(c, 3) for c in carton)))
    m = PCS_CARTON_RE.search(nd)
    F['pcs_carton'] = int(m.group(1)) if m else None
    stated = set()
    for rx in UNITCOV_RES:
        for m in rx.finditer(nd):
            ctx = nd[max(0, m.start() - 30):m.start()]
            if re.search(r'(جدار|غرفة|كرتون)', ctx):
                continue
            stated.add(round(parse_num(m.group(1)), 3))
    stated = sorted(stated)
    F['stated_cov'] = stated[0] if len(stated) == 1 else None
    if len(stated) > 1:
        F['issues'].append(('conflict', 'تغطية القطعة مذكورة بقيم مختلفة: ' + ' / '.join(fnum(c, 3) for c in stated)))
        F['stated_conflict'] = True

    # ---- خامة، منشأ، ادعاءات واردة في وصف المنتج نفسه
    F['origin'], oc = find_origin(name, lines)
    if oc:
        F['issues'].append(('conflict', oc))
    F['material'], mc = find_material(name, lines, desc)
    if mc:
        F['issues'].append(('conflict', mc))
    full = name + '\n' + desc + '\n' + short
    F['waterproof'] = bool(WATER_RE.search(full)) and kind != 'wallpaper'
    F['click'] = bool(CLICK_RE.search(full)) and kind == 'floor'
    us = UNIT_SALE_RE.search(desc)
    F['unit_sale'] = us.group(1).strip() if us else None
    F['per_m2'] = bool(PER_M2_RE.search(desc + ' ' + short)) or bool(us and 'متر مربع' in us.group(1))
    return F


def finalize(Fs):
    """المرور الثاني: حسم المقاسات الواردة في حقل الأبعاد فقط، وحساب التغطية."""
    confirmed = defaultdict(Counter)
    for F in Fs:
        if F.get('dims') and not F['excluded']:
            lo, hi = sorted(F['dims'])
            confirmed[F['sub']][(round(lo, 3), round(hi, 3))] += 1
    for F in Fs:
        if F['excluded']:
            continue
        if F.get('field_only'):
            lo, hi = sorted(F['field'])
            okk = any(n >= 3 and same(lo, k[0]) and same(hi, k[1]) for k, n in confirmed[F['sub']].items())
            if okk and (F['single'] is None or any(same(F['single'], d, 0.03) for d in F['field']) or F['kind'] not in ('linear', 'post')):
                F['dims'], F['dims_src'] = F['field'], 'حقل الأبعاد (مقاس قياسي مؤكَّد في منتجات القسم)'
            elif F['kind'] in ('linear', 'post') and F['single'] is not None and any(same(F['single'], d, 0.03) for d in F['field']):
                F['dims'], F['dims_src'] = F['field'], 'حقل الأبعاد (العرض مطابق للاسم/الوصف)'
            else:
                F['issues'].append(('missing', 'المقاس موجود في حقل الأبعاد فقط (%s×%s سم) ولا يؤكده نص المنتج ولا مقاس قياسي في القسم؛ لم يُستخدم' % (
                    fnum(F['field'][0] * 100, 1), fnum(F['field'][1] * 100, 1))))
        if F.get('field_bad'):
            F['issues'].append(('note', 'حقل الأبعاد في WooCommerce بقيم غير منطقية لهذا النوع'))
        kind, dims = F['kind'], F.get('dims')
        cov = None
        if dims and kind in ('wallpaper', 'panel', 'slat', 'small', 'floor'):
            cov = dims[0] * dims[1]
            sc = F.get('stated_cov')
            if sc and not same(sc, cov, 0.03):
                F['issues'].append(('conflict', 'التغطية المذكورة %s م² لا تساوي حاصل المقاس %s م²' % (fnum(sc, 3), fnum(cov, 3))))
                cov, F['dims'], dims = None, None, None
                F['dims_conflict'] = True
        elif not dims and F.get('stated_cov') and not F.get('dims_conflict') and not F.get('stated_conflict') \
                and kind in ('wallpaper', 'panel', 'slat', 'small', 'floor'):
            cov = F['stated_cov']
        F['piece_area'] = cov
        if kind == 'floor' and F.get('carton'):
            F['coverage'] = F['carton']       # تغطية الكرتونة هي وحدة الشراء
        else:
            F['coverage'] = cov
        if kind in ('wallpaper', 'panel', 'slat', 'small', 'floor') and F['coverage'] is None and not F.get('dims_conflict'):
            if not any(l == 'missing' for l, _ in F['issues']):
                F['issues'].append(('missing', 'لا يوجد مقاس ولا تغطية في بيانات المنتج؛ الوصف بلا أرقام محسوبة'))
        if kind in ('linear', 'post') and not dims and not F.get('post_h') and not F.get('dims_conflict'):
            if not any(l == 'missing' for l, _ in F['issues']):
                F['issues'].append(('missing', 'طول القطعة غير مذكور؛ الوصف بلا حساب كميات'))
    return Fs


def load_products():
    files = sorted(glob.glob(RAW_GLOB), key=lambda f: int(re.search(r'p(\d+)\.json', f).group(1)))
    prods, seen = [], set()
    for f in files:
        for p in json.load(open(f, encoding='utf-8')):
            if p['id'] not in seen:
                seen.add(p['id'])
                prods.append(p)
    prods.sort(key=lambda p: p['id'])
    return prods

# ------------------------------------------------------------------ مكتبة العبارات: نصيحة المصمم
# الجملة الأولى = (لون × تنسيق) + (نقشة/سطح)، الثانية = (نوع المنتج) + (ما يُتجنّب مع اللون).
# معرفة ديكور عامة فقط، بلا ادعاءات تقنية.

COLOR_TIPS = {
    'بيج': dict(h=[
        'ينسجم مع الخشب الفاتح والأبيض المطفي ولمسات النحاس الهادئة',
        'لون محايد دافئ يتقبّل الأخضر الزيتوني والبني الجوزي وأقمشة الكتان',
        'يهدّئ الغرفة ويمنحها دفئاً، ويتناغم مع الكريمي والعسلي والرمادي الدافئ',
        'قاعدة مريحة للعين تتحمّل وسائد ملوّنة أو سجادة بنقشة جريئة',
        'يعكس الضوء بنعومة فيوسّع الإحساس بالمساحة دون برودة الأبيض'], a=[
        'تجنّب جمعه مع أثاث بيج بالدرجة نفسها حتى لا تتسطّح الغرفة',
        'لا تضعه بجانب أبيض ثلجي لامع فيبدو مصفرّاً بالمقارنة',
        'أضف عنصراً داكناً واحداً على الأقل، كإطار أسود أو طاولة جوزية، ليكسر الهدوء الزائد',
        'ابتعد عن الإضاءة البيضاء الباردة معه فالدافئة تُظهره على حقيقته']),
    'رمادي': dict(h=[
        'يتوازن مع الأبيض والأسود ولمسات الخشب الطبيعي التي تدفئه',
        'خلفية عصرية تُبرز الأثاث الملوّن كالأزرق البترولي أو الخردلي',
        'محايد بارد يليق بالمعدن المطفي والزجاج والجلد الأسود',
        'يمنح المكان هدوءاً رسمياً ويتناغم مع الأوف وايت والبيج الرملي',
        'يتقبّل النباتات الخضراء والأقمشة الوبرية التي تضيف له حياة'], a=[
        'تجنّب الإكثار منه في غرفة قليلة الضوء حتى لا تبدو باردة',
        'لا تجمعه مع إضاءة بيضاء باردة وأرضية رمادية معاً، وأدخل خشباً أو قماشاً دافئاً',
        'ابتعد عن خلط أكثر من درجتين رماديتين في الجدار نفسه',
        'وازنه بلون دافئ واحد على الأقل حتى لا يميل المكان إلى طابع المكاتب']),
    'بني': dict(h=[
        'يمنح دفئاً طبيعياً وينسجم مع البيج والكريمي والأخضر المريمي',
        'قريب من روح الخشب فيليق بالجلد والكتان والنحاس المعتّق',
        'يثبّت المكان بصرياً ويتناغم مع الجدران الفاتحة والأقمشة الطبيعية',
        'يتوازن مع الأوف وايت والرمادي الدافئ ولمسات الأسود المطفي',
        'يضيف عمقاً مريحاً ويتقبّل الأزرق الهادئ والبرتقالي المحروق كلمسات'], a=[
        'تجنّب أثاثاً بنياً بدرجته نفسها حتى لا يذوب في الخلفية',
        'لا تستخدمه في غرفة صغيرة ضعيفة الإضاءة دون أسطح فاتحة تقابله',
        'ابتعد عن جمعه مع ستائر داكنة ثقيلة واختر لها قماشاً فاتحاً',
        'امنحه إضاءة دافئة كافية فالدرجات البنية تبتلع الضوء']),
    'أبيض': dict(h=[
        'يعمل كخلفية تُبرز غيرها: كنبة بلون جريء أو لوحة كبيرة أو ستائر دافئة',
        'يعكس الضوء فيوسّع المساحات الضيقة ويليق بكل ألوان الأثاث',
        'ينسجم مع الخشب الطبيعي والأسود المطفي واللمسات الذهبية الخفيفة',
        'نقيّ ومحايد ويبدو أنعم مع الإضاءة الصفراء الدافئة',
        'يمنح إحساساً بالنظافة والاتساع ويتقبّل أي لون ثانوي تختاره'], a=[
        'تجنّب جمعه مع أثاث أبيض وأسطح فاتحة كثيرة معاً حتى لا تبدو الغرفة مسطّحة',
        'أضف خشباً أو قماشاً بملمس واضح يكسر البياض',
        'لا تعتمد على الإضاءة البيضاء الباردة وحدها معه حتى لا يشبه المكان العيادات',
        'انتبه إلى أن الفاتح يُظهر عيوب السطح غير المستوي أكثر من الداكن']),
    'أوف وايت': dict(h=[
        'أدفأ من الأبيض الصريح وينسجم مع الخشب العسلي ومفروشات الكتان',
        'يحمل مسحة كريمية تجعله أهدأ على العين ويتقبّل الإضاءة الصفراء',
        'يليق بالبيج والجوزي والذهبي المطفي في المجالس وغرف النوم',
        'خلفية ناعمة تتحمّل أثاثاً داكناً دون تباين قاسٍ'], a=[
        'تجنّب وضعه بجوار أبواب أو كرانيش بأبيض ثلجي لامع فسيبدو مصفرّاً',
        'اختر للأسقف والنعلات درجة كريمية قريبة منه لا أبيض بارداً',
        'أضف ملمساً واضحاً في القماش أو الخشب حتى لا يبدو المكان باهتاً']),
    'كريمي': dict(h=[
        'يمنح دفئاً ناعماً وينسجم مع الخشب الجوزي والذهبي المعتّق',
        'قريب من ألوان الرمل والكتان فيليق بالطابع الكلاسيكي والمودرن الدافئ',
        'يتناغم مع البني والزيتوني والوردي المغبرّ',
        'يعكس الضوء بنعومة ويجعل المجالس أكثر ترحيباً'], a=[
        'تجنّب جمعه مع أبيض بارد ناصع فيبدو مصفرّاً بجانبه',
        'لا تُكثر معه من الأصفر والذهبي اللامع حتى لا يثقل المشهد',
        'وازنه بعنصر داكن واضح كإطار أو طاولة حتى لا يبهت المكان']),
    'أسود': dict(h=[
        'يضيف دراما وفخامة ويتألق مع الذهبي والخشب الدافئ والأبيض',
        'يحدّد المساحة بقوة ويليق بالإضاءة المخفية والمعدن المطفي',
        'خلفية جريئة تُبرز الشاشات واللوحات والأرفف المضيئة',
        'ينسجم مع الرمادي والبيج ويمنح المكان طابعاً عصرياً'], a=[
        'تجنّب تغطية الغرفة كلها به، فمساحة واحدة تكفي والباقي فاتح',
        'لا تستخدمه في مساحة صغيرة بلا نافذة أو إضاءة قوية',
        'تذكّر أن الأسطح السوداء تُظهر الغبار وبصمات الأصابع أسرع من غيرها']),
    'ذهبي': dict(h=[
        'يضيف لمسة فخامة ويتألق مع الأبيض والكريمي والأسود',
        'يلتقط الضوء فيبرز تحت الإضاءة الدافئة الموجّهة',
        'ينسجم مع البني الداكن والأخضر الزمردي والرخام الفاتح',
        'يليق بالمجالس وواجهات الاستقبال كعنصر تمييز'], a=[
        'تجنّب الإكثار منه فالقليل منه أفخم من الكثير',
        'لا تجمعه مع فضي لامع في المساحة نفسها',
        'ابتعد عن ألوان صاخبة كثيرة حوله ودَع المحايد يسنده']),
    'فضي': dict(h=[
        'يمنح لمعة باردة عصرية وينسجم مع الرمادي والأبيض والأسود',
        'يليق بالزجاج والكروم والإضاءة البيضاء المحايدة',
        'يعكس الضوء ويضيف إحساساً بالحداثة للمداخل والمكاتب'], a=[
        'تجنّب جمعه مع ذهبي لامع في المساحة نفسها',
        'أدخل خشباً أو قماشاً دافئاً حتى لا يبرد المكان',
        'لا تُكثر من الأسطح العاكسة حوله حتى لا يتشتّت النظر']),
    'أزرق': dict(h=[
        'يبعث على الهدوء وينسجم مع الأبيض والرمادي والخشب الفاتح',
        'يليق بغرف النوم والمكاتب ويتناغم مع البيج الرملي',
        'يتألق مع النحاسي والجوزي كلمسات دافئة تكسر برودته',
        'يوحي بالاتساع والصفاء في درجاته الفاتحة وبالعمق في الداكنة'], a=[
        'تجنّب الدرجات الداكنة منه في غرفة قليلة الضوء دون أسطح فاتحة تقابلها',
        'لا تجمعه مع أحمر صريح بالقوة نفسها',
        'وازنه بعنصر دافئ حتى لا يبرد المكان']),
    'أخضر': dict(h=[
        'يربط المكان بالطبيعة وينسجم مع الخشب والبيج والكريمي',
        'مريح للعين ويليق بالنحاس المعتّق والكتان الطبيعي',
        'يتناغم مع الأوف وايت والبني الجوزي والنباتات الداخلية',
        'يمنح المجالس وغرف النوم هدوءاً مختلفاً عن المحايدات المعتادة'], a=[
        'تجنّب جمعه مع ألوان صريحة كثيرة واكتفِ بمحايدات دافئة حوله',
        'لا تضع بجانبه أحمر قوياً إلا كلمسة صغيرة',
        'اختبر درجته تحت إضاءة غرفتك فالأخضر يتغيّر كثيراً بين النهار والليل']),
    'وردي': dict(h=[
        'يضيف نعومة ودفئاً وينسجم مع الأبيض والرمادي الفاتح',
        'يليق بغرف النوم ويتناغم مع الكريمي والذهبي الهادئ',
        'يتألق مع الخشب الفاتح والأقمشة البيضاء الناعمة'], a=[
        'تجنّب تكراره في الأثاث والستائر معاً حتى لا يطغى',
        'وازنه برمادي أو أبيض ليبقى هادئاً',
        'لا تجمعه مع أحمر أو برتقالي قوي']),
    'أحمر': dict(h=[
        'لون طاقة وجرأة يتألق مع الأبيض والرمادي والأسود',
        'يليق كمساحة تمييز في المجالس والمطاعم ويتناغم مع الخشب الداكن',
        'يدفئ المكان وينسجم مع البيج والذهبي المطفي'], a=[
        'تجنّب تغطية الغرفة كلها به فمساحة واحدة تكفي',
        'لا تستخدمه بكثرة في غرف النوم فهو لون منبّه',
        'ابتعد عن جمعه مع ألوان قوية أخرى ودَع المحايدات تسنده']),
    'أصفر': dict(h=[
        'يبعث البهجة ويتألق مع الرمادي والأبيض',
        'يضيء الزوايا المعتمة وينسجم مع الخشب الفاتح والأزرق الهادئ',
        'يليق بغرف الأطفال والمطابخ كلمسة حيوية'], a=[
        'تجنّب الإكثار منه، فجزء من المساحة يكفي',
        'لا تجمعه مع إضاءة صفراء قوية فيتشبّع اللون',
        'وازنه بمحايد هادئ كالرمادي أو الأوف وايت']),
    'بنفسجي': dict(h=[
        'يمنح طابعاً هادئاً مميزاً وينسجم مع الرمادي والأبيض',
        'يتألق مع الفضي والكريمي ويليق بغرف النوم',
        'يوحي بالنعومة في درجاته الفاتحة وبالفخامة في الداكنة'], a=[
        'تجنّب جمعه مع ألوان دافئة صريحة كثيرة',
        'وازنه بمحايدات فاتحة حتى لا يثقل الغرفة',
        'اختبر درجته تحت إضاءتك فهو حساس للضوء الأصفر']),
    'برتقالي': dict(h=[
        'يضيف حيوية ودفئاً ويتألق مع الرمادي والأبيض والخشب',
        'يليق كلمسة جريئة في غرف المعيشة ويتناغم مع البيج والبني',
        'ينسجم مع الأزرق الداكن كتباين مدروس'], a=[
        'تجنّب الإكثار منه فمساحة واحدة تكفي',
        'لا تجمعه مع أحمر أو وردي قوي',
        'وازنه بمحايدات هادئة حوله']),
    None: dict(h=[
        'يتحدد تنسيقه من درجته الفعلية، فقارن عيّنة منه بلون الأرضية والأثاث قبل الاعتماد',
        'ينسجم غالباً مع المحايدات الهادئة حوله: أبيض مطفي وخشب طبيعي وأقمشة بسيطة',
        'يحتاج أن تراه تحت إضاءة غرفتك ليلاً ونهاراً قبل أن تحسم التنسيق',
        'يُنسَّق بالاعتماد على لونين مرافقين فقط حتى يبقى المشهد هادئاً',
        'يأخذ مكانه الصحيح حين تُبنى عليه ألوان الستائر والمفارش لا العكس'], a=[
        'تجنّب الحكم على اللون من الشاشة وحدها',
        'لا تجمعه مع أكثر من نقشة قوية في الغرفة نفسها',
        'ابدأ بمساحة واحدة إن كنت متردداً ثم وسّع',
        'اطلب صورة واقعية له قبل اعتماد بقية الألوان']),
}

PATTERN_TIPS = {
    'plain': ['سطحه السادة يترك البطولة للأثاث واللوحات',
              'غياب النقشة يجعله خلفية تتحمّل ستائر أو سجاداً بنقشة واضحة',
              'التصميم السادة يسهّل تغيير الأثاث لاحقاً دون إعادة التشطيب',
              'الخلفية السادة تُبرز تفاصيل الجبس والإضاءة المخفية',
              'السادة يناسب تغطية مساحة كاملة دون أن يُتعب العين'],
    'stripe': ['الخطوط الطولية ترفع السقف بصرياً والأفقية توسّع الجدار',
               'التقليم يضيف إيقاعاً هادئاً يليق بالممرات والمداخل',
               'الخطوط تحتاج سطحاً مستوياً لأن أي ميلان يظهر فيها',
               'النقشة المخططة تكفي وحدها فلا تحتاج إكسسوارات كثيرة حولها'],
    'floral': ['نقشة الورود تبرز على جدار واحد خلف السرير أو الكنبة',
               'الأزهار تضيف حيوية وتليق بأثاث بسيط الخطوط',
               'التصميم النباتي يُنسَّق مع وسائد بلون مأخوذ من النقشة نفسها',
               'النقشة الزهرية تحتاج مطابقة دقيقة بين القطع عند التركيب'],
    'ornament': ['النقشة الكلاسيكية تمنح المجالس وقاراً وتليق بالأثاث المنحوت والثريات',
                 'الزخرفة تبرز تحت إضاءة جانبية ناعمة تُظهر تفاصيلها',
                 'النقوش تكفي كعنصر زينة فاختر معها ستائر وسجاداً سادة',
                 'التصميم المنقوش يموّه التفاوت البسيط في السطح أفضل من السادة'],
    'marble': ['العروق الرخامية تمنح فخامة هادئة وتبرز مع الإضاءة المخفية',
               'تعريق الرخام يُنسَّق بحيث يتصل اتجاهه بين القطع المتجاورة',
               'المظهر الرخامي يليق بجدار التلفاز والمداخل وواجهات الاستقبال',
               'العروق عنصر زينة كافٍ فاجعل ما حولها بسيطاً'],
    'fabric': ['الملمس القماشي يظهر على حقيقته مع إضاءة جانبية ترسم ظلالاً خفيفة',
               'السطح النسيجي يضيف دفئاً ويموّه التفاوت البسيط في الجدار',
               'ملمسه القريب من الكتان يليق بغرف النوم والمجالس الهادئة',
               'التكستشر الناعم يغني عن النقشة ويضيف عمقاً دون ضجيج بصري'],
    'wood': ['المظهر الخشبي يضيف دفئاً طبيعياً ويتناغم مع الأقمشة المحايدة',
             'تعريق الخشب يبرز مع إضاءة دافئة موجّهة على السطح',
             'اتجاه العروق يُوحَّد بين القطع ليبدو السطح متصلاً',
             'السطح الخشبي يليق بالمساحات التي تحتاج دفئاً بصرياً'],
    'fluted': ['الأضلاع الطولية تصنع ظلالاً تتغيّر مع الإضاءة وتمنح الجدار عمقاً',
               'التضليع يرفع ارتفاع الجدار بصرياً عند تركيبه عمودياً',
               'الخطوط البارزة تليق بخلفية التلفاز والسرير وتكسية الأعمدة',
               'إضاءة مخفية من الأعلى أو الجانب تُبرز تضليعه بوضوح',
               'إيقاع الأضلاع المتكرر يغني الجدار عن اللوحات والإكسسوارات'],
    'glossy': ['لمعانه يعكس الضوء فيفتح الممر والمدخل',
               'السطح اللامع يعكس السبوتات المباشرة كنقاط وهج فالإضاءة المخفية أنسب له',
               'اللمعة تضيف فخامة وتحتاج حولها أسطحاً مطفية توازنها',
               'السطح العاكس يكبّر المساحة بصرياً إن قابله ضوء طبيعي'],
    '3d': ['النقش البارز يرسم ظلالاً حيّة مع الإضاءة الجانبية',
           'التصميم ثلاثي الأبعاد لوحة فنية بذاتها فاجعله جدار التمييز الوحيد',
           'البروز يحتاج مسافة رؤية كافية ليظهر جماله كاملاً',
           'الإضاءة الموجّهة من الأعلى تضاعف أثر النقش البارز'],
    'stone': ['الملمس الحجري يمنح طابعاً طبيعياً ويليق بالمداخل وجدران التمييز',
              'السطح المحبّب يبرز مع إضاءة مائلة تكشف تضاريسه',
              'المظهر الحجري يتوازن مع الخشب والنباتات والأقمشة الناعمة',
              'خشونة السطح البصرية تحتاج حولها أسطحاً ملساء هادئة'],
    'wave': ['الخطوط العصرية تضيف حركة هادئة تليق بغرف المعيشة والمكاتب',
             'النقشة المودرن تُنسَّق مع أثاث بسيط الخطوط وألوان محدودة',
             'التموّج يمنح الجدار إيقاعاً بصرياً دون حاجة لإكسسوارات كثيرة',
             'التصميم الهندسي يبرز كجدار تمييز واحد'],
    'kids': ['رسوماته تليق بغرف الأطفال وأركان اللعب',
             'التصميم الطفولي يُنسَّق مع أثاث أبيض أو خشبي بسيط',
             'يكفي جدار واحد منه مع ألوان هادئة في بقية الغرفة ليبقى المكان مريحاً للنوم',
             'مفارش بلون مأخوذ من الرسومات تربط الغرفة ببعضها'],
    'herringbone': ['رصّة الهرمي تضيف حركة وفخامة للأرضية',
                    'النمط الهرمي يوجّه النظر باتجاه رؤوس الأسهم فيطيل الغرفة بصرياً',
                    'الهرمي يبرز في المجالس والمداخل الواسعة',
                    'هدر القص في الرصّة الهرمية أعلى من المستقيمة فاحسب له كمية إضافية'],
}
SURFACE_DEFAULT = {
    'wallpaper': ['ملمسه يظهر بأفضل شكل تحت إضاءة دافئة غير مباشرة',
                  'تصميمه يبرز على جدار واحد أكثر من تغطية الغرفة كلها',
                  'تفاصيله تحتاج جداراً مستوياً ومجهّزاً لتظهر كما في الصورة',
                  'نقشته تُختار قبل الستائر لأنها أصعب تغييراً منها'],
    'floor': ['اتجاه الرصّ يُفضَّل أن يوازي مصدر الضوء الرئيسي ليخفي الفواصل',
              'لون الأرضية يُختار قبل الستائر والسجاد لأنه القاعدة التي يُبنى عليها',
              'رصّ الشرائح باتجاه طول الغرفة يجعلها تبدو أطول',
              'درجة الأرضية تحدّد إحساس الغرفة أكثر من أي قطعة أثاث'],
    'linear': ['قطعة التشطيب هذه تحدّد الانتقال بين السطحين وتخفي فواصل القص',
               'مقاسها يُختار متناسباً مع ارتفاع السقف',
               'لونها يُنسَّق مع الأبواب والحلوق ليبدو التشطيب موحّداً',
               'خطّها المستقيم يرتّب نهايات الجدار ويمنحها إطاراً واضحاً'],
    'other': ['ملمسه يبرز مع إضاءة جانبية هادئة',
              'تفاصيله تظهر أفضل على جدار تمييز واحد',
              'يُنسَّق مع أسطح بسيطة حوله ليبقى هو مركز النظر',
              'حضوره يقوى حين تقلّ الإكسسوارات على الجدار نفسه'],
}
TYPE_TIPS = {
    'wallpaper': ['يكفي في ورق الجدران جدار واحد خلف السرير أو الكنبة ليتغيّر إحساس الغرفة',
                  'جرّبه على الجدار المقابل للنافذة حيث يصله الضوء الطبيعي',
                  'ابدأ تركيبه من الزاوية الأقل ظهوراً لتبقى الفواصل بعيدة عن العين',
                  'اختر له ستائر أهدأ منه بدرجة حتى يبقى الجدار هو المشهد',
                  'نسّقه مع نعلة وكرنيش بلون واحد ليبدو التشطيب مكتملاً',
                  'اجعل الجدار المكسوّ به خالياً من الأرفف الكثيرة ليظهر التصميم'],
    'shiplap': ['ألواح الشيبورد تليق بخلفية التلفاز وواجهة المجلس',
                'وزّع الفواصل بين الألواح بالتساوي عن محور الجدار',
                'أضف شريط إضاءة مخفية بين الألواح أو أعلاها ليكتمل المشهد',
                'اجمعه مع ألواح مضلعة أو مرايا كشرائط جانبية لكسر الامتداد',
                'اختر فواصل معدنية بلون قريب من الإكسسوارات في الغرفة'],
    'marble': ['بديل الرخام يليق بجدار التلفاز والمدخل وواجهة الاستقبال',
               'جدار أو جداران منه يكفيان والباقي دهان مطفي يوازنه',
               'طابق اتجاه النقشة بين الألواح المتجاورة قبل اللصق',
               'أحطه بإطار خشبي أو فواصل معدنية رفيعة ليبدو كلوحة',
               'اختر له إضاءة مخفية بدل السبوتات المباشرة'],
    'wood': ['الألواح المضلعة تليق بخلفية السرير والتلفاز وتكسية الأعمدة',
             'ركّبها عمودياً لترفع الجدار بصرياً أو أفقياً لتوسّعه',
             'اجمعها مع لوح سادة أو رخامي في المنتصف لتكسر التكرار',
             'أنهِ الأطراف بقفلة أو زاوية بلون قريب ليبدو القص نظيفاً',
             'شريط إضاءة مخفي بجانبها يضاعف أثر الظلال'],
    'cladding': ['تكسية كهذه تبرز على واجهة واحدة مع أسطح ملساء حولها',
                 'وزّع الفواصل بانتظام ليبدو السطح مقصوداً لا مرقّعاً',
                 'نسّق لونها مع الأبواب والنوافذ القائمة',
                 'اجعل اتجاه الألواح واحداً في الواجهة كلها'],
    'small': ['جدار تمييز واحد منه يكفي في المجلس أو المدخل أو ركن القهوة',
              'أضف رفوفاً خشبية أو نباتات أمامه ليكتمل الطابع الطبيعي',
              'إضاءة مائلة من الأعلى تكشف ملمسه وتضاريسه',
              'اتركه بلا لوحات كثيرة فملمسه هو الزينة',
              'نسّقه مع أرضية هادئة حتى لا يتزاحم ملمسان قويان'],
    'floor': ['اختر النعلة بلون الأبواب أو بلون الأرضية نفسها لتشطيب متصل',
              'الأرضية أكبر سطح في الغرفة فابدأ التنسيق منها',
              'اجعل الجدران أفتح من الأرضية بدرجتين على الأقل',
              'سجادة بلون مأخوذ من الأثاث تربط الأرضية ببقية الغرفة',
              'وحّد الأرضية بين الغرف المتصلة لتبدو المساحة أوسع'],
    'linear': ['قطعة بلون الأبواب والحلوق توحّد التشطيب',
               'المقاس الأكبر يليق بالأسقف العالية والأصغر بالغرف المنخفضة',
               'اقطع الزوايا بزاوية 45 درجة لتلتقي القطع بلا فراغ ظاهر',
               'وحّد المقاس نفسه في الغرف المتصلة ليبدو البيت قطعة واحدة',
               'ابدأ التركيب من الزاوية الأبعد عن الباب لتبقى الوصلات خارج مجال النظر'],
    'piece': ['وزّع القطع بتماثل حول محور الجدار أو السقف',
              'حدّد أماكن القطع بالقلم والميزان قبل التثبيت',
              'قطعة الديكور تبرز حين تكون التفاصيل حولها قليلة',
              'وحّد لونها مع المدادات أو الكرانيش المجاورة'],
}
TIP_HEADS = ['رأي المصمم في {cd}', 'كيف تنسّق {cd}؟', 'تنسيق {cd} بعين المصمم', '{cd}: مع ماذا ينسجم؟',
             'لمسة المصمم: {cd}', 'أفكار تنسيق لـ{cd}']

# ------------------------------------------------------------------ أسماء وأعداد

NOUNS = {  # مفرد، مثنى، جمع (3-10)، تمييز (11+)، مؤنث؟
    'roll': ('لفة', 'لفتان', 'لفات', 'لفة', True),
    'panel': ('لوح', 'لوحان', 'ألواح', 'لوحاً', False),
    'strip': ('شريحة', 'شريحتان', 'شرائح', 'شريحة', True),
    'tile': ('بلاطة', 'بلاطتان', 'بلاطات', 'بلاطة', True),
    'sheet': ('صفيحة', 'صفيحتان', 'صفائح', 'صفيحة', True),
    'piece': ('قطعة', 'قطعتان', 'قطع', 'قطعة', True),
    'carton': ('كرتونة', 'كرتونتان', 'كراتين', 'كرتونة', True),
    'post': ('عمود', 'عمودان', 'أعمدة', 'عموداً', False),
}


def cnt(n, key):
    s, d, p, acc, fem = NOUNS[key]
    n = int(n)
    if n == 1:
        return s + (' واحدة' if fem else ' واحد')
    if n == 2:
        return d
    if 3 <= n <= 10:
        return '%d %s' % (n, p)
    return '%d %s' % (n, acc)


SUBINFO = {
    # sub: (unit key, اسم الشيء معرّفاً، اسم مرجعي قصير، مجموعة عبارات النوع، بنك الأسئلة)
    'wallpaper': ('roll', 'ورق الجدران', 'ورق', 'wallpaper', 'wallpaper'),
    'shiplap': ('panel', 'بديل الشيبورد', 'لوح', 'shiplap', 'panel'),
    'marble': ('panel', 'بديل الرخام', 'لوح', 'marble', 'panel'),
    'hpl': ('panel', 'ألواح HPL', 'لوح', 'cladding', 'panel'),
    'wood': ('panel', 'بديل الخشب', 'لوح', 'wood', 'slat'),
    'exterior': ('panel', 'ألواح التكسية', 'لوح', 'cladding', 'slat'),
    'brick': ('panel', 'بديل الطوب', 'لوح', 'small', 'small'),
    'stone': ('panel', 'بديل الحجر', 'لوح', 'small', 'small'),
    'clay': ('sheet', 'الصفائح', 'صفيحة', 'small', 'small'),
    'spc': ('strip', 'باركيه SPC', 'باركيه', 'floor', 'floor'),
    'laminate': ('strip', 'الباركيه', 'باركيه', 'floor', 'floor'),
    'carpet': ('tile', 'الموكيت', 'موكيت', 'floor', 'floor'),
    'skirting': ('piece', 'النعلات', 'نعلة', 'linear', 'linear'),
    'molding': ('piece', 'البراويز والمدادات', 'قطعة', 'linear', 'linear'),
    'cornice': ('piece', 'الكرانيش', 'كرنيش', 'linear', 'linear'),
    'accessory': ('piece', 'الإكسسوارات', 'قطعة', 'linear', 'linear'),
    'partition': ('post', 'أعمدة البارتشن', 'عمود', 'piece', 'piece'),
    'decor': ('piece', 'قطع الديكور', 'قطعة', 'piece', 'piece'),
}
PATTERN_AR = {'plain': 'سادة', 'stripe': 'مخطط', 'floral': 'بنقشة ورود', 'ornament': 'منقوش', 'marble': 'رخامي',
              'fabric': 'قماشي', 'wood': 'خشبي', 'fluted': 'مضلع', 'glossy': 'لامع', '3d': 'ثري دي', 'stone': 'حجري',
              'wave': 'مودرن', 'kids': 'أطفال', 'herringbone': 'هرمي'}
PATTERN_ROW = {'plain': 'سادة', 'stripe': 'مخطط / مقلم', 'floral': 'ورود', 'ornament': 'نقشات', 'marble': 'رخامي معرّق',
               'fabric': 'ملمس قماشي', 'wood': 'مظهر خشبي', 'fluted': 'مضلع', 'glossy': 'لامع', '3d': 'نقش بارز (ثري دي)',
               'stone': 'ملمس حجري', 'wave': 'مودرن', 'kids': 'تصميم أطفال', 'herringbone': 'هرمي'}
LOAN = {norm_ar(w) for w in ['وايت', 'بلاك', 'جراي', 'جولد', 'سيلفر', 'بينك', 'روز', 'white', 'black', 'gray', 'grey', 'gold',
                             'silver', 'sliver', 'pink', 'red', 'blue', 'green', 'brown', 'bronz', 'beige', 'yellow', 'orange',
                             'بلاتينيوم', 'بلاتينيم', 'كابتشينو', 'بوتشينو', 'كراميل', 'موكا', 'تيك', 'وينجي', 'بلوط', 'خشبي']}
ROOMS = {
    'wallpaper': ['غرف النوم والمجالس وغرف المعيشة', 'المجالس وغرف النوم والمكاتب المنزلية', 'غرف المعيشة والممرات وغرف النوم',
                  'غرف النوم وصالات الجلوس والمداخل', 'المجالس وغرف الضيوف والمكاتب'],
    'wallpaper_kids': ['غرف الأطفال وأركان اللعب', 'غرف نوم الأطفال والحضانات المنزلية'],
    'shiplap': ['خلفيات التلفاز وواجهات المجالس والمداخل', 'جدران المجالس وغرف المعيشة وواجهات الاستقبال',
                'خلف السرير وفي الممرات وجدران المكاتب', 'جدار التلفاز وغرف النوم وصالات الاستقبال'],
    'marble': ['جدار التلفاز والمداخل وواجهات الاستقبال', 'المجالس والممرات وخلفيات المغاسل', 'واجهات المجالس والمداخل والمكاتب',
               'جدران الصالات والمداخل وأركان القهوة'],
    'hpl': ['تكسية الجدران والواجهات', 'الواجهات والجدران التي تحتاج سطحاً متيناً'],
    'wood': ['خلفية التلفاز والسرير وتكسية الأعمدة', 'جدران المجالس والممرات والمكاتب', 'خلف السرير وفي المداخل وواجهات الاستقبال',
             'جدار التلفاز والصالات وأركان القهوة'],
    'exterior': ['الواجهات والأسوار وجلسات الحدائق', 'تكسية الواجهات والمداخل الخارجية'],
    'brick': ['جدران التمييز في المجالس والمداخل وأركان القهوة', 'المقاهي والمداخل وخلفيات التلفاز', 'جدار واحد في الصالة أو المطبخ أو المكتب'],
    'stone': ['المداخل وجدران التمييز وخلفيات التلفاز', 'واجهات المجالس والممرات وأركان الجلسات', 'جدار الصالة والمدخل والاستقبال'],
    'clay': ['جدران التمييز والمداخل والأعمدة', 'المجالس والممرات وواجهات الاستقبال', 'جدار واحد في الصالة أو المدخل أو المكتب'],
    'spc': ['غرف النوم والمجالس والمكاتب', 'الصالات وغرف النوم والممرات', 'غرف المعيشة والمكاتب والمحلات'],
    'laminate': ['غرف النوم والمجالس والمكاتب', 'الصالات وغرف النوم وغرف الأطفال', 'غرف المعيشة والمكاتب المنزلية'],
    'carpet': ['المكاتب وقاعات الاجتماعات والممرات', 'المكاتب وغرف الألعاب والاستقبال'],
    'skirting': ['أسفل الجدران في الغرف والممرات والصالات', 'التقاء الجدار بالأرضية في الغرف والمجالس والمكاتب'],
    'molding': ['بانوهات الجدران وإطارات المجالس وغرف النوم', 'تأطير الجدران والأسقف في الصالات والمجالس'],
    'cornice': ['التقاء الجدار بالسقف في المجالس والصالات وغرف النوم', 'أسقف المجالس والمداخل وغرف المعيشة'],
    'accessory': ['إنهاء الحواف والوصلات بين القطع', 'نهايات الألواح وزواياها ووصلاتها'],
    'partition': ['الفواصل بين الصالة والمدخل أو بين المجلس والمقلط', 'تقسيم المساحات المفتوحة وخلفيات الجلسات'],
    'decor': ['تفاصيل الجدران والأسقف في المجالس والصالات', 'زوايا البانوهات والأسقف ونقاط التمييز'],
}
WALLS = {'wallpaper': [3, 3.5, 4, 4.5, 5, 6], 'panel': [3, 3.6, 4, 4.8, 5, 6, 2.4], 'slat': [2, 2.4, 3, 3.5, 4, 1.8],
         'small': [2.5, 3, 3.5, 4, 5]}
ROOMS_FLOOR = [(3, 4), (3.5, 4), (4, 4), (4, 5), (4, 6), (5, 6), (3, 3.5), (3, 5)]
RUNS = [6, 8, 10, 12, 15]


def color_def(F):
    """(معرّف، نكرة) لعبارة اللون كما تظهر في النص."""
    if not F['color']:
        return '', ''
    if F['color_src'] != 'name':
        return COLOR_DEF[F['color']], F['color']
    toks = F['color_phrase'].split()
    n0 = norm_ar(toks[0])
    two = norm_ar(' '.join(toks[:2]))
    if two in COLOR_WORD and len(toks) >= 2:
        base_d, base_i, rest = COLOR_DEF[F['color']], F['color'], toks[2:]
    elif n0 in LOAN or re.search('[a-zA-Z]', toks[0]):
        base_d, base_i, rest = COLOR_DEF[F['color']], F['color'], toks[1:]
    else:
        base_i = NICE.get(n0, toks[0])
        base_d, rest = 'ال' + base_i, toks[1:]
    d, i = [base_d], [base_i]
    for t in rest:
        nt = norm_ar(t)
        if nt in MODIFIERS and nt != norm_ar('مائل'):
            d.append('ال' + t)
            i.append(t)
        else:
            break
    return ' '.join(d), ' '.join(i)


def size_text(F):
    d = F.get('dims')
    if not d:
        return ''
    a, b = d
    kind = F['kind']
    if kind == 'wallpaper':
        L, W = max(a, b), min(a, b)
        return '%s م × %s سم' % (fnum(L, 2), fnum(W * 100, 1))
    if kind in ('linear', 'post'):
        L, W = max(a, b), min(a, b)
        return '%s سم (طول) × %s سم' % (fnum(L * 100, 1), fnum(W * 100, 1))
    if max(a, b) > 3.5:
        return '%s × %s م' % (fnum(a, 2), fnum(b, 2))
    return '%s × %s سم' % (fnum(a * 100, 1), fnum(b * 100, 1))


def build_context(F):
    pid = F['id']
    sub = F['sub']
    ukey, thing, refnoun, tipset, bank = SUBINFO[sub]
    if sub in ('spc', 'laminate') and F.get('dims') and max(F['dims']) / min(F['dims']) < 2.6:
        ukey = 'tile'
    if sub == 'spc' and 'باركيه ضد الماء SPC (بلاطات)' in F['cats']:
        ukey = 'tile'
    if sub == 'clay' and 'صفائح حجرية' in F['cats'] and 'صفائح طينية' not in F['cats']:
        thing = 'الصفائح الحجرية'
    elif sub == 'clay':
        thing = 'الصفائح الطينية'
    s, du, pl, acc, fem = NOUNS[ukey]
    cd, cph = color_def(F)
    code = F['code']
    ref = ('%s %s' % (refnoun, code)) if code else F['label']
    c = dict(pid=pid, name=F['name'], label=F['label'], code=code, ref=ref, thing=thing, tipset=tipset, bank=bank,
             ukey=ukey, u=s, U='ال' + s, upl=pl, Upl='ال' + pl, fem=fem, cd=cd or ref, cph=cph, has_color=bool(cd),
             color=F['color'], pattern=F['pattern'], sub=sub, kind=F['kind'], thick=fnum(F['thick'], 1) if F.get('thick') else '',
             waterproof=F.get('waterproof'), click=F.get('click'), size=size_text(F), origin=F.get('origin') or '',
             material=F.get('material') or '', calc=False)
    tone = F.get('tone')
    if not tone:
        tone = 'light' if F['color'] in ('أبيض', 'أوف وايت', 'كريمي', 'بيج') else ('dark' if F['color'] == 'أسود' else 'mid')
    c['tone'] = tone
    c['patterned'] = F['pattern'] in ('floral', 'ornament', 'stripe', 'marble', 'wave', 'kids', 'stone', '3d')
    key = 'wallpaper_kids' if (sub == 'wallpaper' and F['pattern'] == 'kids') else sub
    c['rooms'] = pick(ROOMS[key], pid, 'rooms')
    d = F.get('dims')
    kind = F['kind']
    cov = F.get('piece_area')
    if kind == 'wallpaper' and d:
        L, W = max(d), min(d)
        spr = int(math.floor(L / WALL_H + 1e-9))
        Ww = pick(WALLS['wallpaper'], pid, 'wall')
        strips = int(math.ceil(Ww / W - 1e-9))
        rolls = int(math.ceil(strips / spr))
        ra, rb = pick(ROOMS_FLOOR[:6], pid, 'room')
        P = 2 * (ra + rb)
        strips_r = int(math.ceil(P / W - 1e-9))
        rolls_r = int(math.ceil(strips_r / spr))
        c.update(calc=True, L=fnum(L, 2), Wm=fnum(W, 2), Wcm=fnum(W * 100, 1), cov=fnum(L * W), spr=spr, spr_txt=cnt(spr, 'strip'),
                 Ww=fnum(Ww, 1), q=fnum(Ww / W, 2), strips=strips, strips_txt=cnt(strips, 'strip'), rolls=rolls, rolls_txt=cnt(rolls, 'roll'),
                 ra=fnum(ra, 1), rb=fnum(rb, 1), P=fnum(P, 1), strips_r_txt=cnt(strips_r, 'strip'), rolls_r=rolls_r,
                 rolls_r_txt=cnt(rolls_r, 'roll'), spr32=cnt(int(math.floor(L / 3.2 + 1e-9)), 'strip'),
                 qty_short='%s لجدار بعرض %s م' % (cnt(rolls, 'roll'), fnum(Ww, 1)),
                 qty_n=rolls, cov_num=L * W)
    elif kind in ('panel', 'small') and d:
        L, W = max(d), min(d)
        cov = L * W
        walls = WALLS['panel' if kind == 'panel' else 'small']
        start = H(pid, 'wall') % len(walls)
        order = walls[start:] + walls[:start]
        full = L >= WALL_H - 1e-9 and kind == 'panel'
        chosen = None
        for Ww in order:
            n_area = int(math.ceil(Ww * WALL_H * WASTE / cov - 1e-9))
            n_col = int(math.ceil(Ww / W - 1e-9)) if full else None
            if n_col is None or n_col == n_area:
                chosen = (Ww, n_area, n_col)
                break
        if chosen is None:
            Ww = order[0]
            chosen = (Ww, int(math.ceil(Ww * WALL_H * WASTE / cov - 1e-9)), int(math.ceil(Ww / W - 1e-9)))
        Ww, n_area, n_col = chosen
        n = max(n_area, n_col or 0)
        A = Ww * WALL_H
        c.update(calc=True, L=fnum(L, 2), Wm=fnum(W, 2), Lcm=fnum(L * 100, 1), Wcm=fnum(W * 100, 1), cov=fnum(cov), Ww=fnum(Ww, 1),
                 A=fnum(A, 2), need=fnum(A * WASTE, 2), n=n, n_txt=cnt(n, ukey), n_area=n_area, n_col=n_col, full=full,
                 q=fnum(Ww / W, 2), per_m2=fnum(1 / cov, 1 if cov < 1 else 2),
                 qty_short='%s لجدار %s × %s م' % (cnt(n, ukey), fnum(Ww, 1), fnum(WALL_H, 1)), qty_n=n, cov_num=cov)
    elif kind == 'slat' and d:
        L, W = max(d), min(d)
        cov = L * W
        Ww = pick(WALLS['slat'], pid, 'wall')
        full = L >= WALL_H - 1e-9
        base = Ww / W
        n = int(math.ceil(base * WASTE - 1e-9)) if full else int(math.ceil(Ww * WALL_H * WASTE / cov - 1e-9))
        c.update(calc=True, L=fnum(L, 2), Wm=fnum(W, 3), Lcm=fnum(L * 100, 1), Wcm=fnum(W * 100, 1), cov=fnum(cov), Ww=fnum(Ww, 1),
                 n=n, n_txt=cnt(n, ukey), full=full, q=fnum(base, 1), per_m=fnum(1 / W, 1), A=fnum(Ww * WALL_H, 2),
                 need=fnum(Ww * WALL_H * WASTE, 2),
                 qty_short='%s لجدار بعرض %s م' % (cnt(n, ukey), fnum(Ww, 1)), qty_n=n, cov_num=cov)
    elif kind == 'floor' and (F.get('coverage')):
        ra, rb = pick(ROOMS_FLOOR, pid, 'room')
        A = ra * rb
        need = A * WASTE
        carton = F.get('carton')
        pa = F.get('piece_area')
        c.update(calc=True, ra=fnum(ra, 1), rb=fnum(rb, 1), A=fnum(A, 2), need=fnum(need, 2), carton=fnum(carton) if carton else '',
                 pa=fnum(pa) if pa else '', has_carton=bool(carton), has_pa=bool(pa))
        if d:
            L, W = max(d), min(d)
            c.update(Lcm=fnum(L * 100, 1), Wcm=fnum(W * 100, 1), L=fnum(L, 3), Wm=fnum(W, 3), per_m2=fnum(1 / pa, 1))
        if carton:
            nc = int(math.ceil(need / carton - 1e-9))
            c.update(n=nc, n_txt=cnt(nc, 'carton'), qty_short='%s لغرفة %s × %s م' % (cnt(nc, 'carton'), fnum(ra, 1), fnum(rb, 1)),
                     cov=fnum(carton), cov_num=carton, qty_n=nc)
        else:
            npcs = int(math.ceil(need / pa - 1e-9))
            c.update(n=npcs, n_txt=cnt(npcs, ukey), qty_short='نحو %s لغرفة %s × %s م' % (cnt(npcs, ukey), fnum(ra, 1), fnum(rb, 1)),
                     cov=fnum(pa), cov_num=pa, qty_n=npcs)
        if F.get('pcs_carton'):
            c['pcs_carton'] = F['pcs_carton']
    elif kind == 'linear' and d:
        L, W = max(d), min(d)
        c.update(L=fnum(L, 2), Lcm=fnum(L * 100, 1), Wcm=fnum(W * 100, 1), calc=True)
        if sub in ('skirting', 'cornice'):
            ra, rb = pick(ROOMS_FLOOR, pid, 'room')
            P = 2 * (ra + rb)
            run = P - 0.9 if sub == 'skirting' else P
            n = int(math.ceil(run * WASTE / L - 1e-9))
            c.update(ra=fnum(ra, 1), rb=fnum(rb, 1), P=fnum(P, 1), run=fnum(run, 1), need=fnum(run * WASTE, 2), n=n, n_txt=cnt(n, 'piece'),
                     room=True, qty_short='%s لغرفة %s × %s م' % (cnt(n, 'piece'), fnum(ra, 1), fnum(rb, 1)), qty_n=n)
        else:
            run = pick(RUNS, pid, 'run')
            n = int(math.ceil(run * WASTE / L - 1e-9))
            c.update(run=fnum(run, 1), need=fnum(run * WASTE, 2), n=n, n_txt=cnt(n, 'piece'), room=False,
                     qty_short='%s لكل %s م طولية' % (cnt(n, 'piece'), fnum(run, 1)), qty_n=n)
    elif kind == 'post' and F.get('post_h'):
        c.update(post_h=fnum(F['post_h'], 2))
    elif kind in ('wallpaper', 'panel', 'slat', 'small') and cov:
        # تغطية مذكورة في الوصف بلا مقاس
        c.update(cov=fnum(cov), cov_only=True, cov_num=cov)
    return c

# ------------------------------------------------------------------ قسم الأرقام

def A(url, text):
    return '<a href="%s">%s</a>' % (url, text)


CALC_LINES = [
    'الأرقام تقديرية؛ أدخل مقاسات مكانك في {calclink} لتحصل على عدد {ref} بدقة.',
    'هذه حسبة استرشادية لـ{ref}، و{calclink} تعطيك الكمية حسب مقاساتك الفعلية.',
    'قبل طلب {ref} راجع الكمية في {calclink} بمقاسات جدارك أو غرفتك.',
    'العدد يتغيّر مع الفتحات والزوايا، فاحسب كمية {ref} في {calclink}.',
    'لكمية {ref} بمقاسات مكانك استخدم {calclink}، والأرقام أعلاه للاسترشاد.',
    'جرّب {calclink} بأبعاد مكانك؛ قد يختلف عدد {ref} عن المثال أعلاه.',
]
NUM_HEADS = {
    'wallpaper': ['بالأرقام: ماذا تغطي لفة {ref}؟', 'حسبة اللفات لـ{ref}', '{ref} بالشرائح واللفات', 'كم لفة تحتاج من {ref}؟',
                  'أرقام {ref}: التغطية وعدد اللفات'],
    'panel': ['حسبة الألواح لـ{ref}', 'بالأرقام: تغطية {ref}', 'كم {u} تحتاج من {ref}؟', '{ref}: التغطية وعدد القطع',
              'أرقام {ref} قبل الطلب'],
    'floor': ['حسبة الكمية لـ{ref}', '{ref} بالأرقام', 'كم تحتاج من {ref} لغرفتك؟', 'أرقام {ref}: التغطية والكمية'],
    'linear': ['حسبة الأطوال لـ{ref}', '{ref} بالأرقام', 'كم قطعة تحتاج من {ref}؟', 'أرقام {ref} قبل الطلب'],
    'none': ['قبل أن تطلب {ref}', 'كيف تحسب كمية {ref}؟', 'ما تحتاج معرفته قبل طلب {ref}', '{ref}: المقاس والكمية'],
}


def numbers_section(F, c):
    pid = F['id']
    c['calclink'] = A(URL_CALC, 'حاسبة الكميات')
    li = []
    kind = F['kind']
    v = lambda opts, salt: pick(opts, pid, 'num-' + salt).format(**c)
    if kind == 'wallpaper' and c['calc']:
        head = v(NUM_HEADS['wallpaper'], 'h')
        li.append(v(['تغطية اللفة: {L} م × {Wm} م = {cov} م² تقريباً.',
                     'اللفة الواحدة من {ref}: {L} م طولاً × {Wm} م عرضاً، أي نحو {cov} م².',
                     'مساحة لفة {ref}: {L} × {Wm} = {cov} م² تقريباً.',
                     'طول اللفة {L} م وعرضها {Wcm} سم، فتغطي قرابة {cov} م².'], 'cov'))
        li.append(v(['من لفة {ref} تخرج {spr_txt} بارتفاع 2.8 م، وكل شريحة تغطي {Wcm} سم من عرض الجدار.',
                     'عدد الشرائح في اللفة: {L} ÷ 2.8 = {spr_txt} كاملة حتى ارتفاع 2.8 م، وعرض كل شريحة {Wcm} سم.',
                     'تُقص لفة {ref} إلى {spr_txt} بطول 2.8 م، وما يتبقى منها يصلح فوق الأبواب وتحت النوافذ.',
                     'لفة {ref} تعطي {spr_txt} لجدار ارتفاعه حتى 2.8 م، بعرض {Wcm} سم للشريحة.'], 'spr'))
        if H(pid, 'ex') % 2 == 0:
            li.append(v(['مثال: جدار عرضه {Ww} م يحتاج {strips_txt} ({Ww} ÷ {Wm} = {q} وتُقرَّب للأعلى) ← {rolls_txt} من {ref}.',
                         'جدار بعرض {Ww} م: {Ww} ÷ {Wm} = {q}، أي {strips_txt} ← {rolls_txt} من {ref}.',
                         'لجدار {Ww} م من {ref}: عدد الشرائح {strips_txt}، وعدد اللفات {rolls_txt}.'], 'ex'))
            c['ex_kind'] = 'wall'
        else:
            li.append(v(['مثال: غرفة {ra} × {rb} م محيطها {P} م تحتاج {strips_r_txt} ← {rolls_r_txt} من {ref}، قبل خصم الأبواب والنوافذ.',
                         'غرفة {ra} × {rb} م كاملة: المحيط {P} م ÷ {Wm} م = {strips_r_txt} ← {rolls_r_txt} من {ref} قبل خصم الفتحات.',
                         'لتغطية غرفة {ra} × {rb} م بـ{ref}: {strips_r_txt} على محيط {P} م، أي {rolls_r_txt} قبل خصم الأبواب والنوافذ.'], 'ex'))
            c['ex_kind'] = 'room'
        if c['patterned']:
            li.append(v(['نقشة {ref} تحتاج مطابقة بين الشرائح، فأضف لفة احتياطية إن كان العدد على الحد.',
                         'مطابقة النقشة تستهلك جزءاً من كل شريحة؛ احسب لـ{ref} هامشاً إضافياً.',
                         'في التصاميم المنقوشة مثل {ref} قد يقل عدد الشرائح المستفاد منها في اللفة بسبب مطابقة النقشة.'], 'pm'))
        else:
            li.append(v(['تصميم {ref} لا يحتاج مطابقة نقشة معقدة، فالهدر عند القص محدود.',
                         'لأن {ref} بلا نقشة متكررة واضحة فبواقي القص قليلة.',
                         'الحساب بالشرائح لـ{ref} أدق من الحساب بالمساحة، لأن بواقي القص لا تُستخدم كلها.'], 'pm'))
        li.append(v(CALC_LINES, 'calc') + ' ' +
                  v(['وراجع أيضاً %s.', 'وللمقاسات الشائعة انظر %s.', 'و%s يختصر عليك الحساب.'], 'rt') % A(URL_ROLLS, 'جدول عدد اللفات لكل غرفة'))
        return head, li
    if kind in ('panel', 'small', 'slat') and c['calc']:
        head = v(NUM_HEADS['panel'], 'h')
        if kind == 'slat':
            li.append(v(['تغطية {U}: {Wcm} سم × {L} م = {cov} م².',
                         'مساحة {u} واحد من {ref}: {Wm} × {L} = {cov} م².',
                         '{U} من {ref} بعرض {Wcm} سم وطول {L} م، فيغطي {cov} م².'], 'cov'))
            li.append(v(['كل متر من عرض الجدار يحتاج نحو {per_m} {u} من {ref}.',
                         'المتر الواحد من عرض الجدار = {per_m} {u} تقريباً بعرض {Wcm} سم.',
                         'عدد القطع في المتر العرضي: 1 ÷ {Wm} = {per_m} تقريباً.'], 'pm'))
            if c['full']:
                li.append(v(['مثال: جدار عرضه {Ww} م ÷ {Wm} م = {q}، ومع 10% هدر ← {n_txt} من {ref}.',
                             'جدار بعرض {Ww} م من {ref}: {q} قطعة قبل الهدر، و{n_txt} بعد إضافة 10%.',
                             'لجدار {Ww} م: ({Ww} ÷ {Wm}) × 1.1 ← {n_txt} من {ref}.'], 'ex'))
                li.append(v(['طول {L} م يكسو الجدار من الأرض إلى السقف دون وصلة حتى هذا الارتفاع.',
                             'بطول {L} م يغطي {ref} ارتفاع الجدار المعتاد بقطعة واحدة.',
                             'لا تحتاج وصلة أفقية في {ref} ما دام ارتفاع جدارك لا يتجاوز {L} م.'], 'full'))
            else:
                li.append(v(['مثال: جدار {Ww} × 2.8 م = {A} م²، ومع 10% هدر {need} م² ← {n_txt} من {ref}.',
                             'لجدار {Ww} م بارتفاع 2.8 م: {need} م² بعد الهدر ÷ {cov} = {n_txt} من {ref}.'], 'ex'))
            li.append(v(['العدد يفترض أن {Wcm} سم هو العرض الظاهر بعد التعشيق؛ تأكّد منه لـ{ref} قبل الطلب.',
                         'إن كان لـ{ref} لسان تعشيق فالعرض الظاهر أقل قليلاً من {Wcm} سم ويزيد العدد.',
                         'تحقّق من العرض الفعلي بعد التركيب لـ{ref}، فالحسبة مبنية على {Wcm} سم كاملة.'], 'vis'))
        else:
            li.append(v(['تغطية {U}: {Wm} م × {L} م = {cov} م².',
                         'مساحة {u} {ref}: {Wcm} × {Lcm} سم = {cov} م².',
                         '{U} الواحد من {ref} يغطي {cov} م² ({Wm} × {L} م).',
                         'مقاس {ref} هو {Wcm} × {Lcm} سم، أي {cov} م² للقطعة.'], 'cov'))
            if kind == 'small':
                li.append(v(['المتر المربع يحتاج نحو {per_m2} قطعة من {ref}.',
                             'كل متر مربع من الجدار = {per_m2} قطعة تقريباً من {ref}.',
                             'عدد القطع في المتر المربع: 1 ÷ {cov} = {per_m2} تقريباً.'], 'pm2'))
            li.append(v(['مثال: جدار {Ww} م × 2.8 م = {A} م²، ومع 10% هدر {need} م² ← {n_txt} من {ref}.',
                         'جدار {Ww} × 2.8 م مساحته {A} م²؛ بعد إضافة 10% يصير {need} م²، أي {n_txt} من {ref}.',
                         'لجدار بعرض {Ww} م وارتفاع 2.8 م: {need} م² مع الهدر ÷ {cov} م² = {n_txt} من {ref}.'], 'ex'))
            if kind == 'panel' and c['full']:
                if c['n_col'] == c['n_area']:
                    li.append(v(['بحساب الأعمدة: {Ww} ÷ {Wm} = {q} ← العدد نفسه، {n_txt} متجاورة.',
                                 'والتحقق بعدد الأعمدة يعطي النتيجة نفسها: {Ww} م ÷ {Wm} م = {q} وتُقرَّب للأعلى.',
                                 'طريقة ثانية للتأكد: عرض الجدار ÷ عرض {U} = {q}، أي {n_txt}.'], 'col'))
                else:
                    li.append(v(['بحساب الأعمدة {Ww} ÷ {Wm} = {q}؛ اعتمدنا العدد الأكبر من الطريقتين لـ{ref}.',
                                 'طريقتا المساحة والأعمدة تختلفان هنا قليلاً، فأخذنا الأكبر: {n_txt} من {ref}.'], 'col'))
                li.append(v(['طول {L} م يكسو الجدار من الأرض إلى السقف بلا فاصل أفقي حتى هذا الارتفاع.',
                             'بارتفاع {L} م يغطي {ref} الجدار المعتاد بقطعة واحدة دون وصلة أفقية.',
                             'لا تحتاج وصلة أفقية في {ref} ما دام ارتفاع جدارك لا يتجاوز {L} م.'], 'full'))
            elif kind == 'panel':
                li.append(v(['طول {U} {L} م؛ الجدار الأعلى منه يحتاج وصلة أفقية أو إطاراً يغطيها.',
                             'ارتفاع {ref} هو {L} م، فخطّط لمكان الوصلة إن كان جدارك أعلى.'], 'full'))
            else:
                li.append(v(['إن كانت حواف {ref} متداخلة فالتغطية الفعلية أقل قليلاً ويزيد العدد.',
                             'عدد قطع {ref} يزيد مع كثرة الزوايا والفتحات، فأضف هامشاً عند الحاجة.',
                             'الحسبة تفترض تلاصق القطع؛ أي تداخل في حواف {ref} يرفع العدد قليلاً.'], 'ov'))
        li.append(v(CALC_LINES, 'calc'))
        return head, li
    if kind == 'floor' and c['calc']:
        head = v(NUM_HEADS['floor'], 'h')
        if c.get('has_pa') and c.get('Lcm'):
            li.append(v(['مساحة {U}: {Lcm} × {Wcm} سم = {pa} م²، أي نحو {per_m2} {u} لكل متر مربع.',
                         '{U} الواحدة من {ref} تغطي {pa} م²، والمتر المربع يحتاج {per_m2} تقريباً.',
                         'مقاس {u} {ref}: {Lcm} × {Wcm} سم؛ كل متر مربع = {per_m2} {u} تقريباً.'], 'pa'))
        if c.get('has_carton'):
            li.append(v(['الكرتونة من {ref} تغطي {carton} م² حسب بيانات المنتج.',
                         'تغطية الكرتونة: {carton} م² من {ref}.',
                         'كل كرتونة {ref} تفرش {carton} م² من الأرضية.'], 'ct'))
            li.append(v(['مثال: غرفة {ra} × {rb} م = {A} م²، ومع 10% هدر {need} م² ← {n_txt} من {ref}.',
                         'غرفة {ra} × {rb} م مساحتها {A} م²؛ بعد إضافة 10% يلزم {need} م²، أي {n_txt} من {ref}.',
                         'لغرفة {ra} × {rb} م: {need} م² مع الهدر ÷ {carton} م² للكرتونة = {n_txt} من {ref}.'], 'ex'))
        else:
            li.append(v(['مثال: غرفة {ra} × {rb} م = {A} م²، ومع 10% هدر {need} م² ← نحو {n_txt} من {ref}.',
                         'غرفة {ra} × {rb} م مساحتها {A} م²؛ بعد إضافة 10% يلزم {need} م²، أي قرابة {n_txt} من {ref}.',
                         'لغرفة {ra} × {rb} م: {need} م² مع الهدر ÷ {pa} م² = نحو {n_txt} من {ref}.'], 'ex'))
            li.append(v(['تغطية الكرتونة غير مذكورة في بيانات {ref}؛ اطلب الكمية بالمتر المربع ويُقرَّب العدد لأقرب كرتونة.',
                         'عدد القطع في كرتونة {ref} غير مذكور، فالكمية النهائية تُقرَّب لأقرب كرتونة عند الطلب.'], 'noct'))
        li.append(v(CALC_LINES, 'calc'))
        return head, li
    if kind == 'linear' and c['calc']:
        head = v(NUM_HEADS['linear'], 'h')
        li.append(v(['طول القطعة {L} م وعرضها {Wcm} سم.',
                     'القطعة الواحدة من {ref}: {Lcm} سم طولاً × {Wcm} سم.',
                     'مقاس {ref}: {L} م للقطعة، بعرض {Wcm} سم.'], 'sz'))
        if c['room']:
            if F['sub'] == 'skirting':
                li.append(v(['مثال: غرفة {ra} × {rb} م محيطها {P} م؛ بعد خصم باب 0.9 م يبقى {run} م، ومع 10% هدر {need} م ← {n_txt} من {ref}.',
                             'غرفة {ra} × {rb} م: ({P} − 0.9) × 1.1 = {need} م طولي ÷ {L} م = {n_txt} من {ref}.',
                             'لغرفة {ra} × {rb} م تحتاج {need} م طولي بعد خصم الباب وإضافة الهدر، أي {n_txt} من {ref}.'], 'ex'))
            else:
                li.append(v(['مثال: غرفة {ra} × {rb} م محيط سقفها {P} م، ومع 10% هدر {need} م ← {n_txt} من {ref}.',
                             'سقف غرفة {ra} × {rb} م: {P} × 1.1 = {need} م طولي ÷ {L} م = {n_txt} من {ref}.'], 'ex'))
        else:
            li.append(v(['مثال: لكل {run} م طولية تحتاج {need} م مع 10% هدر ← {n_txt} من {ref}.',
                         'إن كان مجموع الأطوال المطلوبة {run} م فالعدد ({run} × 1.1) ÷ {L} = {n_txt} من {ref}.',
                         'قِس مجموع الأطوال ثم أضف 10%؛ عند {run} م مثلاً تحتاج {n_txt} من {ref}.'], 'ex'))
        li.append(v(['قص الزوايا بزاوية 45 درجة يستهلك جزءاً من كل قطعة، ولهذا أُضيف الهدر لـ{ref}.',
                     'كل زاوية تعني قصّتين مائلتين، فلا تحسب {ref} على المحيط الصافي فقط.',
                     'الوصلات تُجعل في الأماكن الأقل ظهوراً، وبواقي {ref} القصيرة تصلح للجوانب الصغيرة.'], 'cut'))
        li.append(v(CALC_LINES, 'calc'))
        return head, li
    # بلا أرقام محسوبة
    head = v(NUM_HEADS['none'], 'h')
    if c.get('cov_only'):
        li.append(v(['تغطية {U} من {ref} حسب بيانات المنتج: {cov} م².',
                     'بيانات {ref} تذكر أن {U} يغطي {cov} م².'], 'cov'))
    if kind == 'post' and c.get('post_h'):
        li.append(v(['ارتفاع {ref} حسب وصف المنتج: {post_h} م.', 'يأتي {ref} بارتفاع {post_h} م حسب بياناته.'], 'ph'))
    if F.get('dims_conflict'):
        li.append(v(['مقاس {ref} مذكور بقيم مختلفة في بيانات المتجر، لذلك لم نحسب التغطية هنا؛ اطلب المقاس المؤكَّد من فريق المبيعات.',
                     'في بيانات {ref} مقاسان غير متطابقين، فتأكّد من المقاس الفعلي مع فريق تكسا قبل حساب الكمية.',
                     'لم نكتب تغطية {ref} لأن مقاسه غير متطابق بين حقول المنتج؛ يؤكّده لك فريق المبيعات.'], 'cf'))
    elif kind in ('piece', 'post'):
        li.append(v(['{ref} يُحسب بالعدد لا بالمساحة: حدّد أماكن القطع على المخطط ثم عُدّها.',
                     'كمية {ref} تتبع التصميم؛ ارسم توزيع القطع على الجدار أو السقف واحسب عددها.',
                     'ابدأ بتحديد المواضع على الطبيعة، فعدد {ref} يتحدد من التصميم لا من مساحة الغرفة.'], 'pc'))
    elif not c.get('cov_only'):
        li.append(v(['مقاس {ref} غير مذكور في بيانات المنتج؛ اطلبه من فريق المبيعات قبل حساب الكمية.',
                     'لا يوجد مقاس مؤكَّد لـ{ref} في صفحة المنتج حالياً، فاسأل عنه قبل تحديد العدد.',
                     'بيانات {ref} لا تتضمن المقاس، لذلك لم نحسب له تغطية؛ يزوّدك به فريق تكسا.'], 'nd'))
    if kind in ('wallpaper', 'panel', 'slat', 'small'):
        li.append(v(['طريقة الحساب: مساحة الجدار = العرض × الارتفاع، ثم أضف 10% للقص، واقسم الناتج على تغطية {U} من {ref}.',
                     'لحساب {ref}: اضرب عرض الجدار في ارتفاعه، زد 10% هدراً، ثم اقسم على تغطية القطعة الواحدة.',
                     'قِس عرض الجدار وارتفاعه بالمتر؛ حاصل ضربهما مع 10% إضافية هو المساحة المطلوبة من {ref}.'], 'how'))
    elif kind == 'floor':
        li.append(v(['طريقة الحساب: مساحة الغرفة = الطول × العرض، ثم أضف 10% للقص عند الأطراف لتعرف كمية {ref}.',
                     'لحساب {ref}: اضرب طول الغرفة في عرضها وزد 10% هدراً، ثم اطلب الكمية بالمتر المربع.',
                     'قِس الغرفة بالمتر؛ حاصل الضرب مع 10% إضافية هو المساحة المطلوبة من {ref}.'], 'how'))
    elif kind == 'linear':
        li.append(v(['طريقة الحساب: اجمع الأطوال المطلوبة بالمتر وأضف 10% للقص، ثم اقسم على طول قطعة {ref}.',
                     'لحساب {ref}: قِس مجموع الأطوال، زد 10% للزوايا والقص، واقسم على طول القطعة.'], 'how'))
    li.append(v(CALC_LINES, 'calc'))
    return head, li

# ------------------------------------------------------------------ بنك الأسئلة الشائعة
# كل عنصر: (المفتاح، الشرط، صيغ السؤال، صيغ الجواب). الأرقام من المنتج نفسه.

def _t(c, light, dark, mid):
    return {'light': light, 'dark': dark, 'mid': mid}[c['tone']]


CALC = lambda c: c['calc']
ANY = lambda c: True
COLORED = lambda c: c['has_color']

FAQ_COMMON = [
    ('spare', ANY,
     ['هل أطلب كمية احتياطية من {ref}؟', 'هل يلزم شراء قطعة زائدة من {ref}؟'],
     ['يُستحسن ذلك إن كان العدد المحسوب على الحد؛ القطع من الدفعة نفسها تتطابق في الدرجة، وطلب {ref} لاحقاً قد يأتي بفرق لوني بسيط.',
      'نعم إن كان القص كثيراً أو العدد على الحد، فالحصول على {ref} بالدرجة نفسها لاحقاً غير مضمون بين دفعة وأخرى.']),
    ('calc', ANY,
     ['كيف أحسب كمية {ref} لمقاساتي؟', 'أين أحسب العدد الدقيق من {ref}؟'],
     ['أدخل أبعاد مكانك في <a href="' + URL_CALC + '">حاسبة الكميات</a> فتعطيك كمية {ref} مع نسبة الهدر، أو أرسل المقاسات لفريق تكسا ليحسبها لك.',
      'استخدم <a href="' + URL_CALC + '">حاسبة الكميات</a> في المتجر؛ تكتب العرض والارتفاع فتعرف كم تحتاج من {ref}.']),
    ('guide', ANY,
     ['كيف أتأكد أن {ref} هو الاختيار المناسب؟', 'محتار بين {ref} وخيارات أخرى، من أين أبدأ؟'],
     ['قارن بين الخامات والمقاسات في <a href="' + URL_GUIDE + '">أدلة الشراء</a>، ثم ارجع إلى {ref} وطابق مقاسه مع مكانك.',
      'ابدأ من <a href="' + URL_GUIDE + '">أدلة الشراء</a> لتعرف الفروق بين الأنواع، ثم احسم قرارك في {ref} بحسب المساحة والاستخدام.']),
    ('real', ANY,
     ['هل لون {ref} في الواقع كما يظهر في الصورة؟'],
     ['الدرجة تتأثر بالشاشة وبإضاءة الغرفة؛ اطلب من فريق تكسا صورة واقعية لـ{ref} وقارنها بألوان مكانك قبل تأكيد الطلب.']),
]

FAQ = {
    'wallpaper': [
        ('qty', lambda c: c['calc'] and c.get('ex_kind') == 'room',
         ['كم لفة من {ref} أحتاج لجدار عرضه {Ww} م؟', 'جدار بعرض {Ww} م: كم لفة يحتاج من {ref}؟'],
         ['{rolls_txt}. الجدار يحتاج {strips_txt} لأن الشريحة تغطي {Wcm} سم من عرضه، ولفة {ref} تعطي {spr_txt} بارتفاع حتى 2.8 م.',
          '{rolls_txt}؛ عرض الجدار {Ww} م ÷ عرض الرول {Wm} م = {q} أي {strips_txt}، ومن لفة {ref} تخرج {spr_txt} حتى ارتفاع 2.8 م.']),
        ('qty', lambda c: c['calc'] and c.get('ex_kind') == 'wall',
         ['كم لفة من {ref} تكفي غرفة {ra} × {rb} م؟', 'غرفة {ra} × {rb} م كاملة: كم لفة من {ref}؟'],
         ['{rolls_r_txt} تقريباً: محيط الغرفة {P} م يحتاج {strips_r_txt}، وكل لفة من {ref} تعطي {spr_txt} حتى ارتفاع 2.8 م. اخصم الأبواب والنوافذ الكبيرة فقد ينقص العدد.',
          'نحو {rolls_r_txt}؛ المحيط {P} م ÷ عرض الرول {Wm} م = {strips_r_txt}، ولفة {ref} فيها {spr_txt} بارتفاع 2.8 م. العدد قبل خصم الفتحات.']),
        ('strips', CALC,
         ['كم شريحة تخرج من لفة {ref}؟'],
         ['{spr_txt} بارتفاع 2.8 م من لفة {ref} التي طولها {L} م، وكل شريحة تغطي {Wcm} سم من عرض الجدار.']),
        ('cov', CALC,
         ['كم متراً مربعاً تغطي لفة {ref}؟', 'ما مساحة تغطية لفة {ref}؟'],
         ['نحو {cov} م² ({L} م × {Wm} م). عملياً يُحسب عدد لفات {ref} بالشرائح لا بالمساحة، لأن بواقي القص لا تُستخدم كلها.']),
        ('high', CALC,
         ['سقفي أعلى من 2.8 م، كيف أحسب لفات {ref}؟'],
         ['اقسم طول اللفة {L} م على ارتفاع جدارك لتعرف عدد الشرائح؛ عند ارتفاع 3.2 م مثلاً تعطي لفة {ref} {spr32} بدل {spr_txt}.']),
        ('prep', ANY,
         ['هل يحتاج الجدار تجهيزاً قبل تركيب {ref}؟', 'ما حالة الجدار المطلوبة قبل لصق {ref}؟'],
         ['نعم؛ تُصلَّح الشقوق والنتوءات ويُنظَّف السطح ويُترك ليجف. {ref} لا يعالج عيوب الجدار، والدرجات الفاتحة تُظهرها أكثر من الداكنة.',
          'جدار مستوٍ ونظيف وجاف تماماً. أي شق أو نتوء يُعالَج أولاً، لأن {ref} يتبع شكل السطح الذي تحته.']),
        ('diy', ANY,
         ['هل أستطيع تركيب {ref} بنفسي؟'],
         ['ممكن لجدار صغير مستوٍ إن توفرت أدوات القص والفرد. الجدران الكبيرة والزوايا تحتاج خبرة، وتركيب {ref} متاح من فنيي تكسا في خمس مدن.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟', 'ما طريقة العناية بـ{ref}؟'],
         ['امسح {ref} بقطعة قماش ناعمة جافة أو مبللة قليلاً ثم جفّفه مباشرة، وتجنّب الفرك القوي والمنظفات الكاشطة.',
          'بمسحة قماش ناعمة، مع تجربة أي منظف على زاوية غير ظاهرة من {ref} أولاً، وإبعاده عن الحرارة المباشرة.']),
        ('bed', COLORED,
         ['هل يناسب {cd} غرف النوم؟'],
         [lambda c: _t(c, 'يناسبها جداً؛ الدرجات الفاتحة مثل {cd} تهدّئ الغرفة وتوسّعها، ويُستحسن معها إضاءة دافئة في {ref}.',
                       'يناسب جدار السرير وحده؛ الدرجات الداكنة مثل {cd} تمنح احتواءً ودفئاً، وبقية جدران الغرفة تبقى فاتحة مع {ref}.',
                       'نعم، خصوصاً خلف السرير؛ {cd} يمنح الغرفة شخصية واضحة، ووازنه بمفارش فاتحة مع {ref}.')]),
        ('small', ANY,
         ['هل يصلح {ref} للغرف الصغيرة؟'],
         [lambda c: _t(c, 'يصلح؛ الألوان الفاتحة تعكس الضوء فتبدو الغرفة أوسع، ويمكن تغطية الجدران كلها بـ{ref}.',
                       'يصلح لجدار واحد فقط في الغرفة الصغيرة، مع جدران فاتحة تقابل {ref} حتى لا تضيق المساحة بصرياً.',
                       'يصلح، والأفضل في الغرفة الصغيرة جدار واحد من {ref} مع بقية الجدران بلون فاتح.')]),
        ('one', ANY,
         ['أيهما أفضل: جدار واحد من {ref} أم الغرفة كاملة؟'],
         [lambda c: ('النقشة الواضحة تليق بجدار تمييز واحد خلف السرير أو الكنبة، وتغطية الغرفة كلها بـ{ref} قد تُتعب العين.'
                     if c['patterned'] else
                     'التصميم الهادئ يتحمّل تغطية الغرفة كاملة، وجدار واحد من {ref} يكفي إن أردت تغييراً سريعاً بأقل عدد لفات.')]),
        ('match', lambda c: c['patterned'],
         ['هل نقشة {ref} تحتاج مطابقة عند التركيب؟'],
         ['نعم، تُطابَق النقشة بين كل شريحة والتي تليها، وهذا يستهلك جزءاً من الطول؛ لذلك يُحسب لـ{ref} هامش إضافي.']),
        ('light', COLORED,
         ['أي إضاءة تُظهر {cd} بأفضل شكل؟'],
         ['الإضاءة الدافئة غير المباشرة تُظهر {cd} أنعم من الضوء الأبيض البارد؛ جرّب {ref} تحت إضاءة غرفتك ليلاً قبل الاعتماد.']),
        ('table', ANY,
         ['أين أجد عدد اللفات حسب مقاس الغرفة؟'],
         ['في <a href="' + URL_ROLLS + '">جدول عدد اللفات لكل غرفة</a> أرقام جاهزة للمقاسات الشائعة، وتُطبَّق على {ref} إن كان مقاس لفته مطابقاً للمذكور في الجدول.']),
    ],
    'panel': [
        ('qty', CALC,
         ['كم {u} من {ref} أحتاج لجدار عرضه {Ww} م؟', 'جدار {Ww} × 2.8 م: كم {u} يلزم من {ref}؟'],
         ['{n_txt}: مساحة الجدار {A} م²، ومع 10% هدر {need} م²، و{U} من {ref} يغطي {cov} م².',
          '{n_txt} تقريباً؛ {Ww} × 2.8 = {A} م²، تصير {need} م² بعد الهدر، وتُقسم على {cov} م² لكل {u} من {ref}.']),
        ('cov', CALC,
         ['كم متراً مربعاً يغطي {u} {ref}؟', 'ما مساحة {U} الواحد من {ref}؟'],
         ['{cov} م² ({Wm} م × {L} م). اقسم مساحة جدارك مع 10% هدر على هذا الرقم لتعرف عدد {ref}.']),
        ('height', lambda c: c['calc'] and c.get('full') is not None,
         ['هل يغطي {ref} الجدار من الأرض إلى السقف؟'],
         [lambda c: ('نعم حتى ارتفاع {L} م بقطعة واحدة دون وصلة أفقية، وهذا يغطي أغلب الجدران السكنية مع {ref}.' if c.get('full') else
                     'طول {ref} هو {L} م؛ إن كان جدارك أعلى فستحتاج وصلة أفقية تُخفى بفاصل أو إطار.')]),
        ('joint', ANY,
         ['كيف تُعالَج الفواصل بين قطع {ref}؟'],
         ['إما بفاصل رفيع (بروفايل) بين القطعتين، أو بتلاصقهما مع مطابقة اتجاه النقشة. يُتفق على الطريقة قبل قص {ref} لأنها تغيّر التوزيع.',
          'بفواصل معدنية أو بلاستيكية رفيعة، أو بتركيب متلاصق إن كانت الحواف مستقيمة. توزيع الفواصل يُرسم أولاً ثم يُقص {ref} عليه.']),
        ('prep', ANY,
         ['ما تجهيز الجدار المطلوب قبل تركيب {ref}؟'],
         ['سطح مستوٍ ونظيف وجاف. النتوءات تُزال والحفر تُملأ، لأن {ref} يُثبَّت على الجدار مباشرة ويتبع استواءه.']),
        ('floor', lambda c: c['sub'] in ('shiplap', 'marble'),
         ['هل يصلح {ref} للأرضيات؟'],
         ['لا، {ref} لوح تكسية للجدران والأسطح الرأسية، وللأرضيات أقسام أخرى في المتجر مثل الباركيه.']),
        ('wet', lambda c: c['waterproof'],
         ['هل يُركَّب {ref} في المطبخ أو قرب المغاسل؟'],
         ['وصف المنتج يذكر أنه مقاوم للماء، فيصلح للجدران المعرّضة للرطوبة العادية. أما مناطق الماء المباشر فاسأل فريق تكسا عنها قبل طلب {ref}.']),
        ('one', ANY,
         ['هل أكسو الغرفة كلها بـ{ref} أم جداراً واحداً؟'],
         [lambda c: _t(c, 'الدرجة الفاتحة تتحمّل أكثر من جدار، لكن جدار تمييز واحد من {ref} مع دهان هادئ يبقى الأكثر توازناً.',
                       'الدرجة الداكنة تليق بجدار تمييز واحد؛ تغطية الغرفة كلها بـ{ref} تُثقلها ما لم تكن واسعة ومضاءة جيداً.',
                       'جدار أو جداران من {ref} يكفيان غالباً، والباقي دهان بدرجة هادئة مأخوذة من ألوانه.')]),
        ('thick', lambda c: bool(c['thick']),
         ['هل سماكة {thick} ملم في {ref} مناسبة لتكسية الجدار؟'],
         ['السماكة هنا لتكسية ديكورية تُثبَّت على جدار قائم مستوٍ، لا لتحمّل أوزان. المهم مع {ref} استواء السطح الذي تحته.']),
        ('mix', ANY,
         ['هل يُدمج {ref} مع ألواح مضلعة أو مرايا؟'],
         ['نعم، وهو تنسيق شائع: {ref} في الوسط وشرائط مضلعة أو مرايا على الجانبين، بشرط أن تبقى الألوان في عائلة واحدة.']),
        ('light', ANY,
         ['أي إضاءة تناسب جداراً من {ref}؟'],
         [lambda c: ('الإضاءة المخفية أو الجانبية أنسب من السبوتات المباشرة التي تنعكس على السطح اللامع في {ref} كنقاط وهج.' if c['pattern'] == 'glossy' else
                     'إضاءة جانبية أو مخفية من الأعلى تُبرز ملمس {ref} وتفاصيله أكثر من الإضاءة المسطّحة من منتصف السقف.')]),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بقطعة قماش ناعمة مبللة قليلاً ثم تجفيف، وتجنّب الإسفنج الخشن والمنظفات الكاشطة حتى لا يتأثر سطح {ref}.']),
        ('tv', ANY,
         ['هل يصلح {ref} لخلفية التلفاز؟'],
         ['يصلح، وهو من أكثر استخداماته. حدّد مكان الشاشة والأفياش قبل التركيب لتُقص فتحاتها في {ref} بدقة.']),
        ('cut', ANY,
         ['كيف تُقص فتحات الأفياش في {ref}؟'],
         ['تُعلَّم مواضع الأفياش والمفاتيح على {ref} بعد القياس من الجدار، ثم تُقص قبل التثبيت؛ القياس مرتين يوفّر قطعة كاملة.']),
    ],
    'slat': [
        ('qty', CALC,
         ['كم {u} من {ref} أحتاج لجدار عرضه {Ww} م؟', 'جدار بعرض {Ww} م: كم قطعة من {ref}؟'],
         ['{n_txt} تقريباً: كل متر من عرض الجدار يحتاج {per_m} قطعة بعرض {Wcm} سم، مع 10% هدر للقص في {ref}.',
          'نحو {n_txt}؛ عرض الجدار {Ww} م ÷ عرض القطعة {Wm} م، ثم 10% إضافية لقص {ref}.']),
        ('cov', CALC,
         ['كم يغطي {U} الواحد من {ref}؟'],
         ['{cov} م² ({Wcm} سم × {L} م)، أي نحو {per_m} قطعة لكل متر من عرض الجدار عند تركيب {ref} عمودياً.']),
        ('dir', ANY,
         ['هل يُركَّب {ref} عمودياً أم أفقياً؟'],
         ['العمودي يرفع الجدار بصرياً وهو الأشيع، والأفقي يوسّعه. اختر اتجاهاً واحداً لـ{ref} في الجدار كله.',
          'كلاهما ممكن من ناحية الشكل: عمودياً لإحساس بالارتفاع وأفقياً لإحساس بالاتساع، والأهم ثبات اتجاه {ref} في المساحة نفسها.']),
        ('height', lambda c: c['calc'],
         ['هل يكفي طول {ref} لارتفاع الجدار؟'],
         [lambda c: ('طوله {L} م، فيغطي الجدار حتى هذا الارتفاع بقطعة واحدة دون وصلة في {ref}.' if c.get('full') else
                     'طوله {L} م؛ للجدار الأعلى توضع وصلة {ref} في موضع قليل الظهور أو تُغطّى بفاصل.')]),
        ('edge', ANY,
         ['كيف تُنهى أطراف {ref}؟'],
         ['بقفلة نهاية أو زاوية بلون قريب تغطي حافة القص، فيبدو طرف {ref} مقصوداً لا مبتوراً.']),
        ('prep', ANY,
         ['ما تجهيز الجدار قبل تركيب {ref}؟'],
         ['جدار مستوٍ ونظيف وجاف. أي ميلان يظهر في الخطوط الطولية، فتُضبط أول قطعة من {ref} بالميزان ثم يُبنى عليها.']),
        ('light', ANY,
         ['كيف أُبرز تضليع {ref} بالإضاءة؟'],
         ['بشريط إضاءة مخفي أعلى الجدار أو بجانبه؛ الضوء المائل يرسم ظلالاً بين أضلاع {ref}، والإضاءة الأمامية المسطّحة تخفيها.']),
        ('mix', ANY,
         ['هل يُدمج {ref} مع بديل الرخام أو الشيبورد؟'],
         ['نعم؛ يوضع لوح سادة أو رخامي في الوسط وشرائط {ref} على الجانبين، مع إبقاء الألوان في عائلة واحدة.']),
        ('part', ANY,
         ['هل أغطي الجدار كله بـ{ref} أم جزءاً منه؟'],
         [lambda c: _t(c, 'الدرجة الفاتحة تتحمّل تغطية الجدار كاملاً، وشريط جانبي من {ref} يكفي إن أردت لمسة فقط.',
                       'الدرجة الداكنة أجمل كشريط أو جدار تمييز واحد؛ تغطية مساحة كبيرة بـ{ref} تحتاج غرفة مضاءة جيداً.',
                       'كلاهما وارد: جدار كامل خلف التلفاز أو السرير، أو شرائط جانبية من {ref} تؤطّر لوحاً أوسط.')]),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بفرشاة ناعمة أو قطعة قماش تمرّ مع اتجاه الأضلاع لإزالة الغبار بينها، ثم مسحة خفيفة مبللة عند الحاجة لـ{ref}.']),
        ('tv', ANY,
         ['هل يصلح {ref} لخلفية التلفاز؟'],
         ['يصلح، وهو من أشهر استخداماته. حدّد مكان الشاشة والأفياش أولاً لتُقص قطع {ref} حولها بدقة.']),
        ('vis', CALC,
         ['هل عرض {Wcm} سم في {ref} هو العرض الظاهر بعد التركيب؟'],
         ['الحسبة هنا مبنية على {Wcm} سم كاملة. إن كان لـ{ref} لسان تعشيق فالعرض الظاهر أقل قليلاً، فتأكّد منه قبل تحديد العدد.']),
        ('col', ANY,
         ['هل يصلح {ref} لتكسية الأعمدة؟'],
         ['يصلح شكلاً، وتُحسب كميته من محيط العمود مقسوماً على عرض القطعة. الزوايا تُنهى بقطعة زاوية ليبدو {ref} متصلاً.']),
    ],
    'small': [
        ('qty', CALC,
         ['كم قطعة من {ref} أحتاج لجدار عرضه {Ww} م؟', 'جدار {Ww} × 2.8 م: كم قطعة يلزم من {ref}؟'],
         ['{n_txt}: مساحة الجدار {A} م²، ومع 10% هدر {need} م²، والقطعة من {ref} تغطي {cov} م².',
          '{n_txt} تقريباً؛ {Ww} × 2.8 = {A} م²، تصير {need} م² بعد الهدر، وتُقسم على {cov} م² لقطعة {ref}.']),
        ('pm2', CALC,
         ['كم قطعة من {ref} في المتر المربع؟'],
         ['نحو {per_m2} قطعة، لأن القطعة الواحدة من {ref} مقاسها {Wcm} × {Lcm} سم وتغطي {cov} م².']),
        ('one', ANY,
         ['هل أكسو الغرفة كلها بـ{ref}؟'],
         ['الأجمل جدار تمييز واحد؛ الملمس القوي في {ref} يفقد أثره إن تكرر على كل الجدران، ويُتعب العين في الغرف الصغيرة.']),
        ('stagger', lambda c: c['sub'] == 'brick',
         ['كيف تُرصّ قطع {ref} ليبدو الجدار طبيعياً؟'],
         ['تُرصّ الصفوف متخالفة كالطوب الحقيقي حتى لا تصطف الفواصل الرأسية فوق بعضها، وتُوزَّع قطع {ref} من أكثر من كرتونة.']),
        ('corner', ANY,
         ['كيف تُعالَج الزوايا والأطراف في {ref}؟'],
         ['تُقص القطع عند الزاوية وتُلاقى بعناية أو تُغطّى بقطعة زاوية؛ يُفضّل أن ينتهي {ref} عند زاوية أو إطار لا في منتصف الجدار.']),
        ('prep', ANY,
         ['ما تجهيز الجدار قبل تركيب {ref}؟'],
         ['سطح نظيف وجاف ومتماسك. الدهان المتقشّر يُزال، والجدار غير المستوي يُسوّى قبل تثبيت {ref}.']),
        ('light', ANY,
         ['أي إضاءة تُبرز ملمس {ref}؟'],
         ['ضوء مائل من الأعلى (سبوتات قريبة من الجدار أو شريط مخفي) يكشف تضاريس {ref}، أما الإضاءة الأمامية فتسطّحه.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بفرشاة ناعمة أو مكنسة بفرشاة لإزالة الغبار من تجاويف السطح، ثم مسحة قماش مبللة قليلاً عند الحاجة على {ref}.']),
        ('cov', CALC,
         ['ما مساحة القطعة الواحدة من {ref}؟'],
         ['{cov} م² ({Wcm} × {Lcm} سم). العدد الفعلي من {ref} يزيد قليلاً مع الزوايا والفتحات.']),
        ('mix', ANY,
         ['مع ماذا يُنسَّق جدار من {ref}؟'],
         ['مع خشب طبيعي ونباتات وأقمشة سادة. ملمس {ref} قوي، فاجعل بقية الجدران والأرضية هادئة.']),
        ('where', ANY,
         ['أين يظهر {ref} بأفضل شكل؟'],
         ['على جدار يُرى من مدخل الغرفة مباشرة: خلف الكنبة أو التلفاز أو في المدخل، حيث يكون {ref} أول ما تقع عليه العين.']),
        ('batch', ANY,
         ['هل تختلف درجة {ref} بين قطعة وأخرى؟'],
         ['التفاوت البسيط جزء من المظهر الطبيعي لهذا النوع؛ افرد قطع {ref} على الأرض ووزّعها قبل التثبيت ليتجانس الجدار.']),
    ],
    'floor': [
        ('qty', CALC,
         ['كم أحتاج من {ref} لغرفة {ra} × {rb} م؟', 'غرفة {ra} × {rb} م: ما كمية {ref} المطلوبة؟'],
         [lambda c: ('{n_txt}: مساحة الغرفة {A} م²، ومع 10% هدر {need} م²، وكرتونة {ref} تغطي {carton} م².' if c.get('has_carton') else
                     'نحو {n_txt}، أي {need} م²: مساحة الغرفة {A} م² مع 10% هدر، وكل {u} من {ref} تغطي {pa} م².')]),
        ('pm2', lambda c: c['calc'] and c.get('per_m2'),
         ['كم {u} من {ref} في المتر المربع؟'],
         ['نحو {per_m2}، لأن مقاس {U} {Lcm} × {Wcm} سم ومساحتها {pa} م² في {ref}.']),
        ('dir', ANY,
         ['بأي اتجاه يُرصّ {ref}؟'],
         ['الأشيع أن تُرصّ الشرائح باتجاه الضوء القادم من النافذة أو باتجاه طول الغرفة؛ هكذا تبدو فواصل {ref} أخف والغرفة أطول.']),
        ('sub', ANY,
         ['ما حالة الأرضية المطلوبة تحت {ref}؟'],
         ['سطح مستوٍ ونظيف وجاف. الفروقات والبلاطات المرتفعة تُسوّى أولاً، لأن أي تموّج تحت {ref} يظهر عند المشي.']),
        ('skirt', ANY,
         ['هل أحتاج نعلة مع {ref}؟'],
         ['نعم، النعلة تغطي الفراغ عند التقاء الأرضية بالجدار وتُنهي المظهر. اختر لونها من لون الأبواب أو من درجة {ref} نفسها.']),
        ('thick', lambda c: bool(c['thick']),
         ['ماذا تعني سماكة {thick} ملم في {ref}؟'],
         ['هي سماكة القطعة نفسها. قبل طلب {ref} تأكّد أن ارتفاع الأرضية الجديدة لا يعيق فتح الأبواب، وقد يلزم قصّ أسفل الباب.']),
        ('wet', lambda c: c['waterproof'],
         ['هل يصلح {ref} للمطبخ؟'],
         ['وصف المنتج يذكر أنه مقاوم للماء، فيصلح للمطابخ والممرات. للحمامات ومناطق الماء الدائم اسأل فريق تكسا عن معالجة الأطراف قبل طلب {ref}.']),
        ('small', COLORED,
         ['هل تصغّر أرضية بلون {cph} الغرفة؟'],
         [lambda c: _t(c, 'بالعكس؛ الأرضية الفاتحة تعكس الضوء وتوسّع الغرفة، ويكتمل أثر {ref} مع جدران فاتحة.',
                       'تجعلها أدفأ وأكثر احتواءً، وقد تبدو أصغر إن كانت الجدران داكنة أيضاً. مع جدران فاتحة يثبّت {ref} المكان دون أن يضيّقه.',
                       'ليس بالضرورة؛ الدرجة المتوسطة في {ref} متوازنة، وتبدو الغرفة أوسع كلما كانت الجدران أفتح من الأرضية.')]),
        ('dust', ANY,
         ['هل يُظهر {ref} الغبار والخدوش الصغيرة؟'],
         [lambda c: _t(c, 'الدرجات الفاتحة تخفي الغبار جيداً وتُظهر البقع الداكنة أكثر؛ {ref} عملي للاستخدام اليومي مع تنظيف منتظم.',
                       'الدرجات الداكنة تُظهر الغبار والوبر أسرع من الفاتحة، فيحتاج {ref} مسحاً متكرراً ليبقى مظهره مرتباً.',
                       'الدرجات المتوسطة والمعرّقة هي الأكثر تسامحاً مع الغبار، و{ref} منها.')]),
        ('trans', ANY,
         ['كيف يُنهى {ref} عند الأبواب وبين الغرف؟'],
         ['بفاصل انتقال يغطي التقاء الأرضيتين عند الباب. إن فرشت {ref} في غرف متصلة فحدّد مواضع الفواصل قبل البدء.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بمكنسة ناعمة ثم ممسحة معصورة جيداً. تجنّب سكب الماء والمنظفات الكاشطة، وضع لبّاداً تحت أرجل الأثاث فوق {ref}.']),
        ('carton', lambda c: c.get('has_carton'),
         ['كم تغطي كرتونة {ref}؟'],
         ['{carton} م² حسب بيانات المنتج. اقسم مساحة غرفتك مع 10% هدر على هذا الرقم لتعرف عدد كراتين {ref}.']),
        ('herring', lambda c: c['pattern'] == 'herringbone',
         ['هل يحتاج {ref} الهرمي كمية أكبر؟'],
         ['نعم غالباً؛ القص المائل عند الأطراف في الرصّة الهرمية يرفع الهدر عن 10%، فاسأل الفني عن النسبة المناسبة لـ{ref} في غرفتك.']),
        ('furn', COLORED,
         ['أي أثاث يناسب أرضية {cd}؟'],
         [lambda c: _t(c, 'الأرضية الفاتحة تتقبّل أغلب الألوان؛ أثاث بدرجة أغمق منها يثبّت المشهد فوق {ref}.',
                       'أثاث فاتح أو متوسط يبرز فوقها بوضوح؛ تجنّب أثاثاً بدرجة {ref} نفسها حتى لا يختفي.',
                       'اختر أثاثاً أفتح أو أغمق منها بدرجتين؛ المهم ألا يطابق {ref} تماماً.')]),
    ],
    'linear': [
        ('qty', lambda c: c['calc'] and c.get('room'),
         ['كم قطعة من {ref} تكفي غرفة {ra} × {rb} م؟', 'غرفة {ra} × {rb} م: كم قطعة من {ref}؟'],
         ['{n_txt}: المطلوب {need} م طولي بعد إضافة 10% هدر، وطول قطعة {ref} {L} م.']),
        ('qty', lambda c: c['calc'] and not c.get('room'),
         ['كم قطعة من {ref} أحتاج لكل {run} م طولية؟'],
         ['{n_txt}: ({run} × 1.1) ÷ {L} م لقطعة {ref}، ويُقرَّب للأعلى.']),
        ('len', CALC,
         ['ما طول القطعة الواحدة من {ref}؟'],
         ['{L} م ({Lcm} سم) وعرضها {Wcm} سم. قِس مجموع الأطوال في مكانك واقسمه على طول {ref} مع 10% هدر.']),
        ('corner', ANY,
         ['كيف تلتقي قطع {ref} عند الزوايا؟'],
         ['بقصّ طرفي القطعتين بزاوية 45 درجة لتتطابقا. هذا القص يستهلك جزءاً من الطول، ولهذا يُضاف هدر عند حساب {ref}.']),
        ('joint', ANY,
         ['أين توضع الوصلات بين قطع {ref}؟'],
         ['في الأماكن الأقل ظهوراً: خلف الأثاث أو قرب الزوايا. الوصلة المائلة بين قطعتي {ref} أقل وضوحاً من القص المستقيم.']),
        ('size', lambda c: c['sub'] in ('skirting', 'cornice'),
         ['كيف أختار المقاس المناسب من {ref} لغرفتي؟'],
         ['بحسب ارتفاع السقف: المقاسات الأكبر تليق بالأسقف العالية والمجالس، والأصغر بالغرف منخفضة السقف. قارن {ref} بارتفاع جدارك قبل الطلب.']),
        ('color', ANY,
         ['بأي لون أنسّق {ref}؟'],
         ['الأسهل توحيده مع لون الأبواب والحلوق، أو مع لون السقف إن كان في الأعلى. ينسجم {ref} حين يتكرر لونه في عنصر آخر بالغرفة.']),
        ('prep', ANY,
         ['ما المطلوب قبل تركيب {ref}؟'],
         ['سطح نظيف وجاف، مع انتهاء أعمال الدهان والأرضيات. يُركَّب {ref} في آخر مراحل التشطيب حتى لا يتّسخ أو يُخدش.']),
        ('whole', ANY,
         ['هل أوحّد {ref} في كل الغرف؟'],
         ['يُفضَّل توحيد المقاس واللون في الغرف المتصلة والممرات ليبدو البيت متناسقاً، ويمكن تغيير {ref} في الغرف المغلقة.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بقطعة قماش ناعمة جافة أو مبللة قليلاً. الغبار يتجمع على الحافة العلوية، فمسحها دورياً يُبقي {ref} نظيفاً.']),
        ('measure', ANY,
         ['كيف أقيس الأطوال المطلوبة من {ref}؟'],
         ['قِس كل جدار على حدة بالمتر واجمع الأطوال، واخصم فتحات الأبواب إن كانت القطعة أرضية، ثم أضف 10% لقص {ref}.']),
        ('order', ANY,
         ['متى أطلب {ref}: قبل الأرضيات أم بعدها؟'],
         ['اطلبه مع بقية مواد التشطيب ليصل معها، ويُركَّب {ref} بعد انتهاء الأرضيات والدهان.']),
    ],
    'piece': [
        ('count', ANY,
         ['كيف أحدد عدد القطع من {ref}؟'],
         ['من التصميم لا من المساحة: ارسم توزيع القطع على الجدار أو السقف وعدّها، وأضف قطعة احتياطية من {ref} إن كان القص كثيراً.']),
        ('sym', ANY,
         ['كيف أوزّع {ref} ليبدو متناسقاً؟'],
         ['بالتماثل حول محور الجدار أو السقف، ومسافات متساوية بين القطع. تُعلَّم مواضع {ref} بالقلم والميزان قبل التثبيت.']),
        ('prep', ANY,
         ['ما المطلوب قبل تثبيت {ref}؟'],
         ['سطح نظيف وجاف ومستوٍ، مع انتهاء الدهان الأساسي. يُثبَّت {ref} في المراحل الأخيرة من التشطيب.']),
        ('with', ANY,
         ['مع ماذا يُستخدم {ref}؟'],
         ['مع عناصر من الطراز نفسه في المكان، كالمدادات والكرانيش والبانوهات. يكتمل شكل {ref} حين يتكرر طرازه ولونه حوله.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بفرشاة ناعمة أو قطعة قماش جافة لإزالة الغبار من التفاصيل، ومسحة مبللة قليلاً عند الحاجة على {ref}.']),
        ('color', ANY,
         ['بأي لون أنسّق {ref}؟'],
         ['الأسهل أن يأخذ لون العناصر المجاورة له (السقف أو المدادات أو الأبواب) فيبدو {ref} جزءاً من التصميم لا إضافة عليه.']),
        ('where', ANY,
         ['أين يظهر {ref} بأفضل شكل؟'],
         ['في المجالس والمداخل والصالات حيث تُرى التفاصيل من مسافة قريبة. قليل من {ref} في مكانه أجمل من كثير موزّع بلا خطة.']),
        ('measure', ANY,
         ['ماذا أقيس قبل طلب {ref}؟'],
         ['أبعاد المكان الذي ستُركَّب فيه القطعة والمسافات حولها، ثم طابقها مع مقاس {ref} في جدول المواصفات أو مع فريق المبيعات.']),
        ('order', ANY,
         ['متى يُركَّب {ref} ضمن مراحل التشطيب؟'],
         ['بعد انتهاء اللياسة والدهان الأساسي وقبل اللمسة الأخيرة من الدهان إن لزم، حتى تُعالَج حواف {ref} مع السطح.']),
        ('cut', ANY,
         ['هل يُقص {ref} في الموقع؟'],
         ['القص يحدده الفني حسب نوع القطعة ومكانها؛ أخبر فريق تكسا بمقاسات مكانك ليؤكد لك إن كان {ref} يحتاج قصاً.']),
        ('gap', lambda c: c['sub'] == 'partition',
         ['كم المسافة المناسبة بين أعمدة {ref}؟'],
         ['تُحدَّد بحسب درجة الحجب المطلوبة: مسافات أضيق لخصوصية أكثر وأوسع لانفتاح أكثر. عدد {ref} = عرض الفتحة ÷ (عرض العمود + المسافة).']),
        ('plan', ANY,
         ['هل أحتاج مخططاً قبل طلب {ref}؟'],
         ['رسم بسيط بالمقاسات يكفي؛ يحدد عدد القطع ومواضعها ويمنع طلب كمية ناقصة أو زائدة من {ref}.']),
    ],
}
FAQ_HEADS = ['أسئلة شائعة عن {ref}', 'قبل أن تطلب {ref}', 'أسئلة العملاء حول {ref}', '{ref}: أسئلة وأجوبة',
             'ما يُسأل عنه كثيراً في {ref}', 'استفسارات متكررة عن {ref}']


def faq_section(F, c):
    pid = F['id']
    bank = FAQ[c['bank']]
    fmt = lambda t: (t(c) if callable(t) else t).format(**c)
    out, used = [], set()
    qty = [e for e in bank if e[0] == 'qty' and e[1](c)]
    if qty:
        e = qty[0]
        out.append((fmt(pick(e[2], pid, 'fq-qty')), fmt(pick(e[3], pid, 'fa-qty'))))
        used.add('qty')
    pool = [e for e in bank + FAQ_COMMON if e[0] not in used and e[0] != 'qty' and e[1](c)]
    pool.sort(key=lambda e: H(pid, 'faq-' + e[0]))
    want = 4 if (H(pid, 'faqn') % 3) else 3
    for e in pool:
        if len(out) >= want:
            break
        out.append((fmt(pick(e[2], pid, 'fq-' + e[0])), fmt(pick(e[3], pid, 'fa-' + e[0]))))
        used.add(e[0])
    return pick(FAQ_HEADS, pid, 'faqh').format(**c), out
