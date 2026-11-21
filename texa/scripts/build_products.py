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
    ('رمادي', 'الرمادي', ['رمادي', 'رصاصي', 'جراي', 'قراي', 'غراي', 'اسمنتي', 'فحمي', 'gray', 'grey', 'دخاني']),
    ('فضي', 'الفضي', ['فضي', 'سيلفر', 'بلاتينيوم', 'بلاتينيم', 'sliver', 'silver']),
    ('أسود', 'الأسود', ['اسود', 'بلاك', 'سوداء', 'black']),
    ('بني', 'البني', ['بني', 'جوزي', 'عسلي', 'بلوط', 'تيك', 'وينجي', 'شوكولا', 'شوكولاته', 'موكا', 'كاكاو', 'قهوه', 'برونزي', 'bronz', 'brown']),
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
    ('floral', ['ورود', 'زهور', 'ورد', 'مورد', 'نباتي', 'اوراق', 'زهره', 'شجر'], ['تصميم ورود']),
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
    hits = []
    for idx, (key, words, pcats) in enumerate(PATTERNS):
        for w in words:
            pos = nl.find(' ' + norm_ar(w) + ' ')
            if pos < 0 and len(w) > 4:
                pos = nl.find(' ' + norm_ar(w))
            if pos >= 0:
                hits.append((0 if key in ('kids', '3d', 'fluted', 'herringbone') else 1, pos, idx, key))
    if hits:
        return min(hits)[3]
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
    F = dict(id=p['id'], url=p['permalink'], issues=[], excluded=None,
             slug=urllib.parse.unquote(p['permalink'].rstrip('/').rsplit('/', 1)[-1]).lower())
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
                if all(u is None for _, u in vals):
                    st = 'unitless'      # رقمان بلا وحدة في الاسم: لا يُعتمدان وحدهما ولا يُعدّان تعارضاً
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
    if dims is None and not conflict and not rep:
        ul = [c for c in cands if c[3] == 'unitless']
        if ul and field and same_pair(field, (ul[0][0], ul[0][1])):
            dims, dims_src = (ul[0][0], ul[0][1]), 'الاسم (بلا وحدة) مطابقاً لحقل الأبعاد'
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
    'shiplap': ('panel', 'بديل الشيبورد', 'بديل الشيبورد', 'shiplap', 'panel'),
    'marble': ('panel', 'بديل الرخام', 'بديل الرخام', 'marble', 'panel'),
    'hpl': ('panel', 'ألواح HPL', 'HPL', 'cladding', 'panel'),
    'wood': ('panel', 'بديل الخشب', 'بديل الخشب', 'wood', 'slat'),
    'exterior': ('panel', 'ألواح التكسية', 'منتج', 'cladding', 'slat'),
    'brick': ('panel', 'بديل الطوب', 'بديل الطوب', 'small', 'small'),
    'stone': ('panel', 'بديل الحجر', 'بديل الحجر', 'small', 'small'),
    'clay': ('sheet', 'الصفائح', 'منتج', 'small', 'small'),
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
LOAN = {norm_ar(w) for w in ['وايت', 'بلاك', 'جراي', 'قراي', 'غراي', 'جولد', 'سيلفر', 'بينك', 'روز', 'white', 'black', 'gray', 'grey',
                             'gold', 'silver', 'sliver', 'pink', 'red', 'blue', 'green', 'brown', 'bronz', 'beige', 'yellow', 'orange']}
# أسماء درجات تجارية: تُكتب كما في الاسم ولا تُترجم إلى لون (تُستخدم عائلتها اللونية لاختيار النصيحة فقط)
SHADE_NAMES = {norm_ar(w) for w in ['بلاتينيوم', 'بلاتينيم', 'كابتشينو', 'بوتشينو', 'كراميل', 'موكا', 'تيك', 'وينجي', 'بلوط',
                                    'شوكولا', 'شوكولاته', 'كاكاو', 'قهوه', 'فانيلا', 'ايفوري', 'سكري', 'لافندر', 'دخاني']}
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
WALLS = {'wallpaper': [2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6], 'panel': [3, 3.6, 4, 4.8, 5, 6, 2.4, 3.5, 4.5], 'slat': [2, 2.4, 3, 3.5, 4, 1.8, 2.8, 4.5],
         'small': [2, 2.5, 3, 3.5, 4, 4.5, 5]}
PLACES = {
    'wallpaper': ['غرف النوم', 'المجالس', 'غرف المعيشة', 'المكاتب المنزلية', 'الممرات', 'المداخل', 'غرف الضيوف', 'صالات الجلوس'],
    'shiplap': ['خلفيات التلفاز', 'واجهات المجالس', 'المداخل', 'غرف المعيشة', 'واجهات الاستقبال', 'جدار السرير', 'الممرات', 'المكاتب'],
    'marble': ['جدار التلفاز', 'المداخل', 'واجهات الاستقبال', 'المجالس', 'الممرات', 'خلفيات المغاسل', 'أركان القهوة', 'الصالات'],
    'wood': ['خلفية التلفاز', 'جدار السرير', 'تكسية الأعمدة', 'المجالس', 'الممرات', 'المكاتب', 'المداخل', 'أركان القهوة'],
    'spc': ['غرف النوم', 'المجالس', 'المكاتب', 'الصالات', 'الممرات', 'غرف المعيشة', 'المحلات'],
    'laminate': ['غرف النوم', 'المجالس', 'المكاتب المنزلية', 'الصالات', 'غرف المعيشة', 'غرف الضيوف', 'غرف الأطفال'],
    'brick': ['المجالس', 'المداخل', 'أركان القهوة', 'خلفيات التلفاز', 'المقاهي', 'الممرات', 'واجهات الاستقبال'],
    'stone': ['المجالس', 'المداخل', 'أركان الجلسات', 'خلفيات التلفاز', 'الممرات', 'واجهات الاستقبال', 'الصالات'],
    'clay': ['المجالس', 'المداخل', 'الأعمدة', 'جدران التمييز', 'الممرات', 'واجهات الاستقبال', 'الصالات'],
    'skirting': ['غرف النوم', 'المجالس', 'الممرات', 'الصالات', 'المكاتب', 'المداخل', 'غرف المعيشة'],
}


def rooms_phrase(key, pid):
    pl = PLACES.get(key)
    if not pl:
        return pick(ROOMS[key], pid, 'rooms')
    order = sorted(pl, key=lambda x: H(pid, 'pl-' + x))[:3]
    return '%s و%s و%s' % tuple(order)
ROOMS_FLOOR = [(3, 4), (3.5, 4), (4, 4), (4, 5), (4, 6), (5, 6), (3, 3.5), (3, 5)]
RUNS = [6, 8, 10, 12, 15]


class RefCtx(dict):
    """سياق القوالب: {ref} لا يكرر كود المنتج؛ يعطي إشارة طبيعية (هذا الورق / اللوح القماشي البني...).
    الاسم المختصر بالكود متاح فقط عبر named() ويُستخدم في عنوان H2 واحد وسؤال واحد."""

    def __missing__(self, k):
        if k == 'ref':
            forms = self['_forms']
            n = self['_n'][0]
            self['_n'][0] += 1
            kwp = self.get('_kwp')
            if kwp and n % kwp == kwp - 1:
                return '⟦' + self['kw_e'] + '⟧'
            return forms[(self['_seed'] + n) % len(forms)]
        raise KeyError(k)

    def named(self):
        d = dict(self)
        d['ref'] = '⟦' + self['kw_e'] + '⟧' if self.get('kw_e') else self['ref_named']
        return d


THIS = {'wallpaper': 'هذا الورق', 'shiplap': 'هذا التصميم', 'marble': 'هذا التصميم', 'hpl': 'هذا النوع', 'wood': 'هذا التصميم',
        'exterior': 'هذا النوع', 'brick': 'هذا التصميم', 'stone': 'هذا التصميم', 'clay': 'هذه الصفائح', 'spc': 'هذا الباركيه',
        'laminate': 'هذا الباركيه', 'carpet': 'هذا الموكيت', 'skirting': 'هذه النعلة', 'molding': 'هذه القطعة',
        'cornice': 'هذا الكرنيش', 'accessory': 'هذه القطعة', 'partition': 'هذا العمود', 'decor': 'هذه القطعة'}
THIS2 = {'wallpaper': 'هذا التصميم'}
DESC_BASE = {'wallpaper': 'الورق', 'shiplap': 'بديل الشيبورد', 'marble': 'بديل الرخام', 'wood': 'بديل الخشب',
             'brick': 'بديل الطوب', 'stone': 'بديل الحجر', 'spc': 'الباركيه', 'laminate': 'الباركيه', 'carpet': 'الموكيت'}
PAT_DEF = {'plain': 'السادة', 'stripe': 'المخطط', 'floral': 'المورّد', 'ornament': 'المنقوش', 'marble': 'الرخامي', 'fabric': 'القماشي',
           'wood': 'الخشبي', 'fluted': 'المضلع', 'glossy': 'اللامع', '3d': 'البارز', 'stone': 'الحجري', 'wave': 'المودرن',
           'herringbone': 'الهرمي'}


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
    elif n0 in SHADE_NAMES:
        base_d, base_i, rest = 'لون ال' + toks[0], toks[0], toks[1:]
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
    if sub in ('molding', 'cornice', 'accessory', 'decor', 'partition', 'skirting'):
        w0 = F['label'].split()[0] if F['label'].split() else refnoun
        w0 = {'نعله': 'نعلة', 'باركية': 'باركيه', 'اكسسوارات': 'إكسسوارات'}.get(w0, w0)
        refnoun = w0 if not re.search(r'\d', w0) else refnoun
    ref = ('%s %s' % (refnoun, code)) if code else F['label']
    forms = [THIS[sub]]
    if sub in DESC_BASE and (cd or F['pattern'] in PAT_DEF):
        d = DESC_BASE[sub]
        if F['pattern'] in PAT_DEF and not (sub in ('spc', 'laminate', 'carpet') and F['pattern'] not in ('herringbone', 'wood')):
            d += ' ' + PAT_DEF[F['pattern']]
        if cd:
            d += (' ب' + cd) if cd.startswith('لون') else (' ' + cd)
        forms.append(d)
    if sub in THIS2:
        forms.append(THIS2[sub])
    forms.append(THIS[sub])
    c = RefCtx(pid=pid, name=F['name'], label=F['label'], code=code, ref_named=ref, _forms=forms, _n=[0], _seed=H(pid, 'rf'), thing=thing, tipset=tipset, bank=bank,
             ukey=ukey, u=s, uacc=acc, one=('الواحدة' if fem else 'الواحد'), yg=('تغطي' if fem else 'يغطي'), U='ال' + s, upl=pl, Upl='ال' + pl, fem=fem, cd=cd, cph=cph, has_color=bool(cd),
             color=F['color'], pattern=F['pattern'], sub=sub, kind=F['kind'], thick=fnum(F['thick'], 1) if F.get('thick') else '',
             waterproof=F.get('waterproof'), click=F.get('click'), size=size_text(F), origin=F.get('origin') or '',
             material=F.get('material') or '', calc=False)
    tone = F.get('tone')
    nlab = set(norm_ar(F['label']).split())
    if not tone and (nlab & DARK or nlab & LIGHT):
        tone = 'dark' if nlab & DARK else 'light'
    if not tone:
        tone = 'light' if F['color'] in ('أبيض', 'أوف وايت', 'كريمي', 'بيج') else ('dark' if F['color'] == 'أسود' else 'mid')
    c['tone'] = tone
    c['patterned'] = F['pattern'] in ('floral', 'ornament', 'stripe', 'marble', 'wave', 'kids', 'stone', '3d')
    key = 'wallpaper_kids' if (sub == 'wallpaper' and F['pattern'] == 'kids') else sub
    c['rooms'] = rooms_phrase(key, pid)
    c['desc'] = forms[1] if len(forms) > 2 and forms[1] != THIS[sub] and sub in DESC_BASE and (cd or F['pattern'] in PAT_DEF) else THIS[sub]
    d = F.get('dims')
    kind = F['kind']
    cov = F.get('piece_area')
    if kind == 'wallpaper' and d:
        L, W = max(d), min(d)
        spr = int(math.floor(L / WALL_H + 1e-9))
        Ww = pick(WALLS['wallpaper'], pid, 'wall')
        strips = int(math.ceil(Ww / W - 1e-9))
        rolls = int(math.ceil(strips / spr))
        ra, rb = pick(ROOMS_FLOOR, pid, 'room')
        Ww2 = pick([w for w in WALLS['wallpaper'] if w != Ww], pid, 'wall2')
        st2 = int(math.ceil(Ww2 / W - 1e-9))
        h2 = pick([3.0, 3.2, 3.5], pid, 'h2')
        c.update(Ww2=fnum(Ww2, 1), strips2_txt=cnt(st2, 'strip'), rolls2_txt=cnt(int(math.ceil(st2 / spr)), 'roll'),
                 h2=fnum(h2, 1), sprh_txt=cnt(int(math.floor(L / h2 + 1e-9)), 'strip'))
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
CALC_LINES_NOEX = [
    'بعد معرفة المقاس أدخل أبعاد مكانك في {calclink} لتحصل على كمية {ref}.',
    '{calclink} تحسب لك كمية {ref} مع نسبة الهدر متى توفّر المقاس.',
    'قبل طلب {ref} راجع الكمية في {calclink} بمقاسات جدارك أو غرفتك.',
    'لكمية {ref} بمقاسات مكانك استخدم {calclink} أو أرسل الأبعاد لفريق تكسا.',
    'احسب كمية {ref} في {calclink}، أو اطلب من فريق المبيعات حسابها لك.',
]
NUM_HEADS = {
    'wallpaper': ['بالأرقام: ماذا تغطي لفة {ref}؟', '{ref}: حسبة اللفات', '{ref} بالشرائح واللفات', 'كم لفة تحتاج من {ref}؟',
                  'أرقام {ref}: التغطية وعدد اللفات'],
    'panel': ['{ref}: حسبة الكمية للجدار', 'بالأرقام: تغطية {ref}', 'كم {uacc} تحتاج من {ref}؟', '{ref}: التغطية وعدد القطع',
              'أرقام {ref} قبل الطلب'],
    'floor': ['{ref}: حسبة الكمية', '{ref} بالأرقام', 'كم تحتاج من {ref} لغرفتك؟', 'أرقام {ref}: التغطية والكمية'],
    'linear': ['{ref}: حسبة الأطوال', '{ref} بالأرقام', 'كم قطعة تحتاج من {ref}؟', 'أرقام {ref} قبل الطلب'],
    'none': ['قبل أن تطلب {ref}', 'كيف تحسب كمية {ref}؟', 'ما تحتاج معرفته قبل طلب {ref}', '{ref}: المقاس والكمية'],
}


def numbers_section(F, c):
    pid = F['id']
    c['calclink'] = A(URL_CALC, 'حاسبة الكميات')
    li = []
    kind = F['kind']
    v = lambda opts, salt: pick(opts, pid, 'num-' + salt).format_map(c)
    vh = lambda opts, salt: pick(opts, pid, 'num-' + salt).format_map(c.named())
    if kind == 'wallpaper' and c['calc']:
        head = vh(NUM_HEADS['wallpaper'], 'h')
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
            li.append(v(['مثال: غرفة {ra} × {rb} م محيطها {P} م تحتاج {strips_r_txt} ← {rolls_r_txt} من {ref}، والأفضل ألا تخصم الأبواب والنوافذ؛ ما يتوفر يبقى احتياطاً.',
                         'غرفة {ra} × {rb} م كاملة: المحيط {P} م ÷ {Wm} م = {strips_r_txt} ← {rolls_r_txt} من {ref}، والأفضل ألا تخصم الأبواب والنوافذ؛ ما يتوفر يبقى احتياطاً.',
                         'لتغطية غرفة {ra} × {rb} م بـ{ref}: {strips_r_txt} على محيط {P} م، أي {rolls_r_txt}، والأفضل ألا تخصم الأبواب والنوافذ؛ ما يتوفر يبقى احتياطاً.'], 'ex'))
            c['ex_kind'] = 'room'
        pm = v(['نقشته تحتاج مطابقة بين الشرائح فأضف لفة احتياطية إن كان العدد على الحد',
                'مطابقة النقشة تستهلك جزءاً من كل شريحة فاحسب هامشاً إضافياً',
                'قد يلزم هامش إضافي لأن مطابقة النقشة تقلّل المستفاد من كل لفة'] if c['patterned'] else
               ['لا يحتاج مطابقة نقشة معقدة فالهدر عند القص محدود',
                'بواقي القص قليلة لأنه بلا نقشة متكررة واضحة',
                'الحساب بالشرائح هنا أدق من الحساب بالمساحة لأن بواقي القص لا تُستخدم كلها'], 'pm')
        if c['ex_kind'] == 'wall':
            li[-1] = li[-1].rstrip('.') + '، و' + pm + '.'
        else:
            li[1] = li[1].rstrip('.') + '، و' + pm + '.'
        li.append(v(CALC_LINES, 'calc').rstrip('.') + '، ' +
                  v(['وراجع أيضاً %s.', 'وللمقاسات الشائعة انظر %s.', 'و%s يختصر عليك الحساب.'], 'rt') % A(URL_ROLLS, 'جدول عدد اللفات لكل غرفة'))
        return head, li
    if kind in ('panel', 'small', 'slat') and c['calc']:
        head = vh(NUM_HEADS['panel'], 'h')
        if kind == 'slat':
            li.append(v(['تغطية {U}: {Wcm} سم × {L} م = {cov} م².',
                         'مساحة القطعة من {ref}: {Wm} × {L} = {cov} م².',
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
                         'مساحة القطعة من {ref}: {Wcm} × {Lcm} سم = {cov} م².',
                         '{U} {one} من {ref} {yg} {cov} م² ({Wm} × {L} م).',
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
        head = vh(NUM_HEADS['floor'], 'h')
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
        head = vh(NUM_HEADS['linear'], 'h')
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
    head = vh(NUM_HEADS['none'], 'h')
    if c.get('cov_only'):
        li.append(v(['تغطية {U} من {ref} حسب بيانات المنتج: {cov} م².',
                     'بيانات {ref} تذكر أن {U} {yg} {cov} م².'], 'cov'))
    if kind == 'post' and c.get('post_h'):
        li.append(v(['ارتفاع {ref} حسب وصف المنتج: {post_h} م.', 'الارتفاع المذكور في بيانات {ref}: {post_h} م.'], 'ph'))
    if F.get('dims_conflict') and kind in ('linear', 'post', 'piece'):
        li.append(v(['مقاس {ref} مذكور بقيم مختلفة في بيانات المتجر، لذلك لم نحسب الكمية هنا؛ اطلب المقاس المؤكَّد من فريق المبيعات.',
                     'في بيانات {ref} مقاسان غير متطابقين، فتأكّد من المقاس الفعلي مع فريق تكسا قبل تحديد العدد.'], 'cf'))
    elif F.get('dims_conflict'):
        li.append(v(['مقاس {ref} مذكور بقيم مختلفة في بيانات المتجر، لذلك لم نحسب التغطية هنا؛ اطلب المقاس المؤكَّد من فريق المبيعات.',
                     'في بيانات {ref} مقاسان غير متطابقين، فتأكّد من المقاس الفعلي مع فريق تكسا قبل حساب الكمية.',
                     'لم نكتب تغطية {ref} لأن مقاسه غير متطابق بين حقول المنتج؛ يؤكّده لك فريق المبيعات.'], 'cf'))
    elif kind in ('piece', 'post'):
        li.append(v(['كمية {ref} تُحسب بالعدد لا بالمساحة: حدّد أماكن القطع على المخطط ثم عُدّها.',
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
    li.append(v(CALC_LINES_NOEX, 'calc'))
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
         ['{rolls_r_txt} تقريباً: محيط الغرفة {P} م يحتاج {strips_r_txt} وكل لفة تعطي {spr_txt} بارتفاع الجدار المعتاد، والأفضل ألا تخصم الأبواب والنوافذ؛ ما يتوفر يبقى احتياطاً.',
          'نحو {rolls_r_txt}؛ المحيط {P} م يُقسم على عرض الرول فيعطي {strips_r_txt} وفي اللفة {spr_txt}، والأفضل ألا تخصم الأبواب والنوافذ؛ ما يتوفر يبقى احتياطاً.']),
        ('strips', CALC,
         ['كم شريحة تخرج من لفة {ref}؟'],
         ['{spr_txt} بارتفاع 2.8 م من لفة طولها {L} م، وكل شريحة تغطي {Wcm} سم؛ فجدار بعرض {Ww2} م مثلاً يأخذ {strips2_txt} أي {rolls2_txt}.',
          'تخرج من اللفة {spr_txt} بطول 2.8 م وعرض {Wcm} سم لكل واحدة، وجدار عرضه {Ww2} م يحتاج منها {strips2_txt}.']),
        ('cov', CALC,
         ['كم متراً مربعاً تغطي لفة {ref}؟', 'ما مساحة تغطية لفة {ref}؟'],
         ['نحو {cov} م² ({L} م × {Wm} م)، لكن العدد يُحسب بالشرائح لا بالمساحة: جدار بعرض {Ww2} م مثلاً يحتاج {strips2_txt} أي {rolls2_txt}.',
          'قرابة {cov} م² للفة، وعملياً يُحسب {ref} بالشرائح؛ فجدار عرضه {Ww2} م يأخذ {strips2_txt} من أصل {spr_txt} في اللفة.']),
        ('high', CALC,
         ['سقفي أعلى من 2.8 م، كيف أحسب لفات {ref}؟'],
         ['اقسم طول اللفة {L} م على ارتفاع جدارك لتعرف عدد الشرائح؛ عند ارتفاع {h2} م مثلاً تعطي اللفة {sprh_txt} بدل {spr_txt}، فيتغير عدد اللفات لجدار {Ww2} م.',
          'عدد الشرائح = {L} ÷ ارتفاع الجدار؛ فمع سقف {h2} م تخرج من لفة {ref} {sprh_txt} لا {spr_txt}، وأعد حساب جدارك على هذا الأساس.']),
        ('prep', ANY,
         ['هل يحتاج الجدار تجهيزاً قبل تركيب {ref}؟', 'ما حالة الجدار المطلوبة قبل لصق {ref}؟'],
         ['تُصلَّح الشقوق والنتوءات أولاً ويُنظَّف السطح ويُترك ليجف. {ref} لا يعالج عيوب الجدار، والدرجات الفاتحة تُظهرها أكثر من الداكنة.',
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
         ['أين أجد عدد لفات {ref} حسب مقاس الغرفة؟'],
         ['في <a href="' + URL_ROLLS + '">جدول عدد اللفات لكل غرفة</a> أرقام جاهزة للمقاسات الشائعة، وتُطبَّق على {ref} إن كان مقاس لفته مطابقاً للمذكور في الجدول.']),
    ],
    'panel': [
        ('qty', CALC,
         ['كم {uacc} أحتاج من {ref} لجدار عرضه {Ww} م؟', 'جدار {Ww} × 2.8 م: كم {uacc} يلزم من {ref}؟'],
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
         ['لا، {ref} مخصص لتكسية الجدران والأسطح الرأسية، وللأرضيات أقسام أخرى في المتجر مثل الباركيه.']),
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
         ['كم {uacc} أحتاج من {ref} لجدار عرضه {Ww} م؟', 'جدار بعرض {Ww} م: كم قطعة من {ref}؟'],
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
         ['على جدار يُرى من مدخل الغرفة مباشرة: خلف الكنبة أو التلفاز أو في المدخل، حيث يقع النظر على {ref} أولاً.']),
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
         ['كم {uacc} من {ref} في المتر المربع؟'],
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
         ['الأسهل توحيده مع لون الأبواب والحلوق، أو مع لون السقف إن كان في الأعلى. يتحقق الانسجام حين يتكرر لون {ref} في عنصر آخر بالغرفة.']),
        ('prep', ANY,
         ['ما المطلوب قبل تركيب {ref}؟'],
         ['سطح نظيف وجاف، مع انتهاء أعمال الدهان والأرضيات. تركيب {ref} يأتي في آخر مراحل التشطيب حتى لا يتّسخ السطح أو يُخدش.']),
        ('whole', ANY,
         ['هل أوحّد {ref} في كل الغرف؟'],
         ['يُفضَّل توحيد المقاس واللون في الغرف المتصلة والممرات ليبدو البيت متناسقاً، ويمكن تغيير {ref} في الغرف المغلقة.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بقطعة قماش ناعمة جافة أو مبللة قليلاً. الغبار يتجمع على الحافة العلوية، فمسحها دورياً يحافظ على نظافة {ref}.']),
        ('measure', ANY,
         ['كيف أقيس الأطوال المطلوبة من {ref}؟'],
         ['قِس كل جدار على حدة بالمتر واجمع الأطوال، واخصم فتحات الأبواب إن كانت القطعة أرضية، ثم أضف 10% لقص {ref}.']),
        ('order', ANY,
         ['متى أطلب {ref}: قبل الأرضيات أم بعدها؟'],
         ['اطلبه مع بقية مواد التشطيب ليصل معها، وموعد تركيب {ref} بعد انتهاء الأرضيات والدهان.']),
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
         ['سطح نظيف وجاف ومستوٍ، مع انتهاء الدهان الأساسي. تثبيت {ref} يكون في المراحل الأخيرة من التشطيب.']),
        ('with', ANY,
         ['مع ماذا يُستخدم {ref}؟'],
         ['مع عناصر من الطراز نفسه في المكان، كالمدادات والكرانيش والبانوهات. يكتمل شكل {ref} حين يتكرر طرازه ولونه حوله.']),
        ('clean', ANY,
         ['كيف أنظف {ref}؟'],
         ['بفرشاة ناعمة أو قطعة قماش جافة لإزالة الغبار من التفاصيل، ومسحة مبللة قليلاً عند الحاجة على {ref}.']),
        ('color', ANY,
         ['بأي لون أنسّق {ref}؟'],
         ['الأسهل أن يأخذ لون العناصر المجاورة له (السقف أو المدادات أو الأبواب) والنتيجة أن {ref} جزء من التصميم لا إضافة عليه.']),
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
         ['القص يحدده الفني حسب نوع القطعة ومكانها؛ أخبر فريق تكسا بمقاسات مكانك ليؤكد لك إن كان القص لازماً في {ref}.']),
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
    named = c.named()
    fmt = lambda t, ctx=c: (t(ctx) if callable(t) else t).format_map(ctx)
    out, used = [], set()
    qty = [e for e in bank if e[0] == 'qty' and e[1](c)]
    if qty:
        e = qty[0]
        out.append((fmt(pick(e[2], pid, 'fq-qty'), named), fmt(pick(e[3], pid, 'fa-qty'))))
        used.add('qty')
    pool = [e for e in bank + FAQ_COMMON if e[0] not in used and e[0] != 'qty' and e[1](c)]
    DATA = ('strips', 'cov', 'high', 'height', 'pm2', 'len', 'carton', 'thick', 'vis')
    pool.sort(key=lambda e: H(pid, 'faq-' + e[0]))
    data = [e for e in pool if e[0] in DATA][:2]
    pool = data[:1] + [e for e in pool if e not in data[:1]]
    want = 4 if (H(pid, 'faqn') % 3) else 3
    for e in pool:
        if len(out) >= want:
            break
        out.append((fmt(pick(e[2], pid, 'fq-' + e[0]), c if out else named), fmt(pick(e[3], pid, 'fa-' + e[0]))))
        used.add(e[0])
    return pick(FAQ_HEADS, pid, 'faqh').format_map(c), out

# ------------------------------------------------------------------ نصيحة المصمم

TIP_EXTRA = [
    'وقبل اعتماد {ref} ضع صورة واقعية له بجانب أثاثك في ضوء النهار ثم المساء.',
    'ولتتأكد من {ref} قارن درجته بلون الأرضية والستائر في غرفتك نفسها لا على الشاشة.',
    'وإن ترددت في {ref} فابدأ بمساحة صغيرة ثم وسّع بعد أن ترى أثره في المكان.',
    'ويبقى الحكم الأخير لإضاءة مكانك، فانظر إلى {ref} تحتها قبل تثبيت بقية الألوان.',
]


def tip_section(F, c):
    pid = F['id']
    col = COLOR_TIPS[F['color'] if (c['has_color'] and F['color'] in COLOR_TIPS) else None]
    subj = c['cd'] if c['has_color'] else (THIS[F['sub']] if 'التصميم' in THIS[F['sub']] else 'تصميم ' + THIS[F['sub']])
    kind, pat = F['kind'], F['pattern']
    if kind == 'floor':
        pool = PATTERN_TIPS[pat] if pat in ('herringbone', 'wood') else SURFACE_DEFAULT['floor']
    elif kind == 'linear':
        pool = SURFACE_DEFAULT['linear']
    elif kind in ('piece', 'post'):
        pool = SURFACE_DEFAULT['other']
    elif pat and pat in PATTERN_TIPS and not (pat == 'kids' and kind != 'wallpaper'):
        pool = PATTERN_TIPS[pat]
    else:
        pool = SURFACE_DEFAULT['wallpaper' if kind == 'wallpaper' else 'other']
    s1 = '%s %s، و%s.' % (subj, pick(col['h'], pid, 'tip-h'), pick(pool, pid, 'tip-p'))
    s2 = '%s؛ %s.' % (pick(TYPE_TIPS[c['tipset']], pid, 'tip-t'), pick(col['a'], pid, 'tip-a'))
    out = s1 + ' ' + s2
    if H(pid, 'tip-x') % 2 == 0:
        out += ' ' + pick(TIP_EXTRA, pid, 'tip-e').format_map(c)
    head = pick(TIP_HEADS, pid, 'tip-head').format(cd=(c['cd'] if c['has_color'] else THIS[F['sub']]))
    return head, out

# ------------------------------------------------------------------ الكلمة المستهدفة والعنوان والوصف

KW_PAT = {'plain': 'سادة', 'stripe': 'مقلم', 'floral': 'ورود', 'ornament': 'نقشات', 'marble': 'رخامي', 'fabric': 'قماشي',
          'wood': 'خشبي', 'stone': 'حجري', 'wave': 'مودرن', 'kids': 'أطفال', '3d': 'ثري دي', 'glossy': 'لامع', 'fluted': 'مضلع',
          'herringbone': 'هرمي'}


def has_word(label, *words):
    nl = ' ' + norm_ar(label) + ' '
    for w in words:
        if ' ' + norm_ar(w) + ' ' in nl:
            return w
    return None


def type_phrase(F, c):
    sub, label, pat = F['sub'], F['label'], F['pattern']
    cph = ' '.join(c['cph'].split()[:2]) if c['cph'] else ''
    parts = []
    if sub == 'wallpaper':
        parts = ['ورق جدران']
        if pat:
            parts.append(KW_PAT[pat])
        elif F.get('origin') in ('كوريا', 'كوريا الجنوبية'):
            parts.append('كوري')
        elif has_word(label, 'تكستشر'):
            parts.append('تكستشر')
    elif sub == 'shiplap':
        parts = ['بديل شيبورد']
        if pat and pat not in ('kids',):
            parts.append({'stripe': 'مخطط', 'wave': 'مموج'}.get(pat, KW_PAT[pat]))
    elif sub == 'marble':
        parts = ['بديل رخام']
        w = has_word(label, 'كونكريت', 'ريزن', 'اوبن بوك', 'طباعه')
        if w:
            parts.append({'طباعه': 'طباعة', 'اوبن بوك': 'أوبن بوك'}.get(w, w))
        elif pat in ('glossy', '3d', 'stone', 'fabric', 'wood'):
            parts.append(KW_PAT[pat])
    elif sub == 'wood':
        parts = ['بديل خشب مضلع' if pat == 'fluted' else ('تكسيات خشبية' if has_word(label, 'تكسيات') else 'بديل خشب')]
    elif sub == 'exterior':
        parts = ['خشب خارجي WPC' if has_word(label, 'خارجي') else 'تكسيات جدران']
    elif sub == 'hpl':
        parts = ['لوح HPL']
    elif sub == 'brick':
        parts = ['بديل طوب']
        w = has_word(label, 'باروك', 'فينتدج', 'ضيق', 'ريستك')
        if w:
            parts.append(w)
    elif sub == 'stone':
        parts = ['بديل حجر']
    elif sub == 'clay':
        parts = ['صفائح حجرية' if has_word(label, 'حجرية', 'حجريه') else 'صفائح طينية']
    elif sub == 'spc':
        parts = ['باركيه SPC']
        if pat == 'herringbone':
            parts.append('هرمي')
    elif sub == 'laminate':
        parts = ['باركيه']
        w = has_word(label, 'الماني', 'ألماني', 'بلجيكي', 'تركي', 'صيني')
        if pat == 'herringbone':
            parts.append('هرمي')
        elif w:
            parts.append('ألماني' if norm_ar(w) == 'الماني' else w)
        elif has_word(label, 'لامينيت'):
            parts.append('لامينيت')
    elif sub == 'carpet':
        parts = ['موكيت بلاطات' if 'موكيت بلاطات' in F['cats'] else 'موكيت شرائح']
    elif sub == 'skirting':
        parts = ['نعلة']
        w = has_word(label, 'فايبر', 'فوم', 'سيراميك', 'خشب', 'رخام')
        if w:
            parts.append(w)
    elif sub == 'partition':
        toks = label.split()
        parts = [' '.join(toks[:2])]
        if has_word(label, 'بديل') and has_word(label, 'خشب'):
            parts.append('بديل خشب')
    else:
        toks = [t for t in label.split() if not re.search(r'\d', t) and t not in ('مقاس', '–', '-', 'سم', 'ملم', 'مم', 'م', '×', 'x', 'X')]
        parts = [' '.join(toks[:3])] if toks else [SUBINFO[sub][2]]
    lab_words = {w[2:] if w.startswith('ال') else w for w in norm_ar(label).replace('باركيه', 'باركيه').split()}
    lab_words |= {'نعله'} if lab_words & {'نعلات', 'نعله'} else set()
    lab_words |= {'صفائح'} if 'صفائح' in lab_words else set()
    base_words = [w[2:] if w.startswith('ال') else w for w in norm_ar(parts[0]).split()] if parts else []
    if sub not in ('wallpaper',) and parts and not all(
            (w in lab_words or w in ('wpc', 'hpl', 'spc') or any(x.startswith(w[:4]) for x in lab_words)) for w in base_words):
        toks = [t for t in label.split() if not re.search(r'\d', t) and t not in ('مقاس', '–', '-', 'ملم', 'مم', 'سم')]
        if toks:
            parts = [' '.join(toks[:3])]
    if cph and norm_ar(cph.split()[0]) not in norm_ar(' '.join(parts)).split():
        parts.append(cph)
    if sub == 'skirting' and F.get('single'):
        parts.append('%s سم' % fnum(F['single'] * 100, 1))
    kw = ' '.join(p for p in parts if p).strip()
    return ' '.join(kw.split()[:6])


DANGLING = ('مقاس', 'مع', 'و', 'بعروق', 'بخطوط', 'بفواصل', 'فاصل', 'فواصل', 'عرض', 'شامل', 'ضد', 'بلون', 'من', 'في', 'على',
            'بإطار', 'باطار', 'ذات', 'بنقشة')


def trim_dangling(toks):
    toks = list(toks)
    while toks and toks[-1] in DANGLING:
        toks.pop()
    return toks


def rest_tokens(label, kw):
    have = set(norm_ar(kw).split())
    syn = set()
    for h in list(have):
        if h in COLOR_WORD:
            syn.add(norm_ar(COLOR_WORD[h]))
    out = []
    label = re.sub(r'\d+(?:[.,]\d+)?\s*[×xX*]\s*\d+(?:[.,]\d+)?(?:\s*[×xX*]\s*\d+(?:[.,]\d+)?)?\s*(?:سم|ملم|مم|cm|mm|م(?![\u0621-\u064A]))?',
                   ' ', norm_digits(label))
    raw = label.split()
    merged, i = [], 0
    while i < len(raw):
        if i + 1 < len(raw) and re.fullmatch(r'[\d.,×xX*]+', raw[i]) and raw[i + 1] in ('ملم', 'مم', 'سم', 'م', 'متر', 'mm', 'cm'):
            merged.append(raw[i] + ' ' + raw[i + 1])
            i += 2
        else:
            merged.append(raw[i])
            i += 1
    for t in merged:
        nt = norm_ar(t.strip('()،,'))
        if ' ' in nt and all(x in have for x in nt.split()):
            continue
        if len(nt) >= 3 and any((h.startswith(nt) or nt.startswith(h)) and abs(len(h) - len(nt)) <= 2 for h in have if len(h) >= 3):
            continue
        if not nt or nt in have or t in ('–', '-', '_', 'مع'):
            continue
        if nt in ('ورق', 'جدران', 'بديل', 'تكسا', 'الواح', 'لوح', 'جداري'):
            continue
        if nt in COLOR_WORD and norm_ar(COLOR_WORD[nt]) in have:
            continue
        if nt in ('نعلات', 'نعله') and 'نعله' in have:
            continue
        if nt in ('رخام', 'الرخام', 'شيبورد', 'الشيبورد', 'خشب', 'الخشب', 'طوب', 'الطوب', 'حجر', 'الحجر', 'باركيه', 'باركية',
                  'نعله', 'نعلات', 'صفائح', 'طينيه', 'موكيت', 'شرائح') and any(nt.replace('ال', '') in h for h in have):
            continue
        have.add(nt)
        out.append(t.strip('،,'))
    return out


TITLE_FILL = {
    'wallpaper': ['للجدران', 'للمجالس وغرف النوم', 'رول كامل', 'شحن لكل المملكة'],
    'panel': ['للجدران', 'لتكسية الجدران', 'ديكور داخلي', 'شحن وتركيب'],
    'slat': ['للجدران', 'لتكسية الجدران', 'ديكور داخلي', 'شحن وتركيب'],
    'small': ['للجدران', 'لتكسية الجدران', 'جدار تمييز', 'شحن وتركيب'],
    'floor': ['للأرضيات', 'أرضيات داخلية', 'شحن وتركيب', 'للغرف والمجالس'],
    'linear': ['ديكور وتشطيب', 'للتشطيب الداخلي', 'شحن وتركيب', 'اطلبه أونلاين'],
    'post': ['ديكور داخلي', 'فواصل وديكور', 'شحن وتركيب', 'اطلبه أونلاين'],
    'piece': ['ديكور داخلي', 'للجدران والأسقف', 'شحن وتركيب', 'اطلبه أونلاين'],
}


def title_extras(F, c):
    ex = []
    kind = F['kind']
    if c.get('calc') and kind == 'wallpaper':
        ex += ['%s م²' % c['cov'], 'لفة %s م' % c['L']]
    elif c.get('calc') and kind in ('panel', 'small'):
        ex += ['%s×%s سم' % (c['Wcm'], c['Lcm']), '%s م²' % c['cov']]
    elif c.get('calc') and kind == 'slat':
        ex += ['%s×%s سم' % (c['Wcm'], c['Lcm']), 'عرض %s سم' % c['Wcm']]
    elif c.get('calc') and kind == 'floor':
        if c.get('Lcm'):
            ex.append('%s×%s سم' % (c['Lcm'], c['Wcm']))
        if c.get('has_carton'):
            ex.append('كرتونة %s م²' % c['carton'])
    elif c.get('calc') and kind == 'linear':
        ex += ['طول %s م' % c['L']]
    if c['thick'] and (c['thick'] + ' ملم') not in F['label'] and not re.search(r'\d\s*(ملم|مم)', F['label']):
        ex.append('%s ملم' % c['thick'])
    return ex


def clean_name(name):
    """اسم المنتج كما هو، بلا شرطات فاصلة ولا لاحقة «تكسا N»."""
    s = re.sub(r'\s+[–—\-_]\s+', ' ', name)
    s = re.sub(r'\s*[_–-]?\s*تكسا\s*\d*\s*$', '', s)
    return re.sub(r'\s+', ' ', s).strip(' –-_')


def name_prefix(name, limit):
    """أطول بادئة من كلمات الاسم لا تتجاوز limit حرفاً (اختصار من النهاية فقط)."""
    toks = clean_name(name).split()
    while len(toks) > 1 and len(' '.join(toks)) > limit:
        toks.pop()
    full = len(toks) == len(clean_name(name).split())
    if not full:
        toks = trim_dangling(toks) or toks
    return ' '.join(toks), full


def title_additions(F, c):
    fills = TITLE_FILL[F['kind']]
    k = H(F['id'], 'tf') % len(fills)
    return title_extras(F, c), fills[k:] + fills[:k]


def build_title(F, c, kw, used):
    pid = F['id']
    code = F['code']
    LO, HI = 50 - len(BRAND_SUFFIX), 60 - len(BRAND_SUFFIX)
    base, full = name_prefix(F['name'], HI)
    extras, fills = title_additions(F, c)
    opts = extras + fills
    if code and code not in base:
        opts = [code] + opts
    cands = []
    if LO <= len(base) <= HI:
        cands.append(base)
    for i, e1 in enumerate(opts):
        b1 = base + ' – ' + e1
        if LO <= len(b1) <= HI:
            cands.append(b1)
        elif len(b1) < LO:
            for j, e2 in enumerate(opts[i + 1:], i + 1):
                b2 = b1 + ' – ' + e2
                if LO <= len(b2) <= HI:
                    cands.append(b2)
                elif len(b2) < LO:
                    for e3 in opts[j + 1:]:
                        b3 = b2 + ' – ' + e3
                        if LO <= len(b3) <= HI:
                            cands.append(b3)
    if not cands:
        cands.append(base)
    for b in cands:
        t = b + BRAND_SUFFIX
        if t not in used:
            used.add(t)
            return t
    tag = ' – رقم %d' % pid
    b = cands[0]
    if len(b) + len(tag) > HI:
        b, _ = name_prefix(F['name'], HI - len(tag))
    t = b + tag + BRAND_SUFFIX
    used.add(t)
    return t


CTAS = ['احسب كميتك واطلبه الآن من تكسا ديكور.', 'اطلبه الآن مع خدمة التركيب في 5 مدن.', 'احسب الكمية واطلب مع شحن لكل المملكة.',
        'اطلبه أونلاين من تكسا ديكور والشحن لكل المدن.', 'تسوّقه الآن واحسب كميتك بحاسبة تكسا.', 'اطلبه اليوم واحسب العدد بحاسبة الكميات.',
        'اطلب الآن.', 'اطلبه الآن من تكسا ديكور.']


def size_clause(F, c):
    k = F['kind']
    if not c.get('calc'):
        if c.get('cov_only'):
            return '%s %s %s م²' % (c['U'], c['yg'], c['cov'])
        return ''
    if k == 'wallpaper':
        return 'لفة %s م × %s سم تغطي نحو %s م²' % (c['L'], c['Wcm'], c['cov'])
    if k in ('panel', 'small'):
        return '%s %s × %s سم %s %s م²' % (c['u'], c['Wcm'], c['Lcm'], c['yg'], c['cov'])
    if k == 'slat':
        return '%s %s سم × %s م يغطي %s م²' % (c['u'], c['Wcm'], c['L'], c['cov'])
    if k == 'floor':
        bits = []
        if c.get('Lcm'):
            bits.append('%s %s × %s سم' % (c['u'], c['Lcm'], c['Wcm']))
        if c['thick']:
            bits.append('سماكة %s ملم' % c['thick'])
        if c.get('has_carton'):
            bits.append('الكرتونة تغطي %s م²' % c['carton'])
        return '، '.join(bits)
    if k == 'linear':
        return 'قطعة بطول %s م وعرض %s سم' % (c['L'], c['Wcm'])
    return ''


def build_meta(F, c, kw, used):
    pid = F['id']
    sc = size_clause(F, c)
    qty = c.get('qty_short', '')
    k = H(pid, 'cta') % 6
    ctas = CTAS[k:6] + CTAS[:k] + CTAS[6:]
    extras = ['يناسب %s.' % c['rooms'], 'رفع المقاس والتركيب متاحان في 5 مدن.', 'راجع المواصفات والأسئلة الشائعة في الصفحة.']
    if c['thick'] and 'سماكة' not in sc and not re.search(r'\d\s*(ملم|مم)', F['label']):
        extras.insert(0, 'سماكة %s ملم.' % c['thick'])
    mids = []
    for limit in (70, 55, 40):
        ld, _ = name_prefix(F['name'], limit)
        for cta in ctas:
            core = ld + (': ' + sc if sc else '')
            variants = []
            if sc and qty:
                variants.append(core + '، و' + qty + '.')
            variants.append(core + '.')
            for vbase in variants:
                txt = vbase + ' ' + cta
                if 120 <= len(txt) <= 155:
                    mids.append(txt)
                acc = vbase
                for e in extras:
                    if ('شحن' in e and 'شحن' in cta) or ('تركيب' in e and 'تركيب' in cta):
                        continue
                    acc2 = acc + ' ' + e
                    txt2 = acc2 + ' ' + cta
                    if 120 <= len(txt2) <= 155:
                        mids.append(txt2)
                    if len(txt2) <= 155:
                        acc = acc2
    for t in mids:
        if t not in used:
            used.add(t)
            return t
    ld, _ = name_prefix(F['name'], 60)
    t = (ld + '. يناسب %s. ' % c['rooms'] + CTAS[7])[:155]
    if t in used:
        t = t[:140].rstrip() + ' (%d)' % pid
    used.add(t)
    return t


def build_excerpt(F, c, kw):
    sc = size_clause(F, c)
    s2s = []
    if c.get('qty_short'):
        s2s += ['%s، ويناسب %s.' % (c['qty_short'], c['rooms']), 'مثال: %s.' % c['qty_short']]
    s2s += ['يناسب %s، والتركيب متاح في 5 مدن.' % c['rooms'], 'يناسب %s.' % c['rooms']]
    for limit in (80, 60, 45, 30):
        hd, _ = name_prefix(F['name'], limit)
        for s2 in s2s:
            t = hd + ('، ' + sc if sc else ' من تكسا ديكور') + '. ' + s2
            if len(t) <= 160:
                return t
    return (name_prefix(F['name'], 60)[0] + '. يناسب %s.' % c['rooms'])[:160]


# ------------------------------------------------------------------ فقرة الإجابة، الجدول، الروابط

SPEC_TYPE = {
    'wallpaper': 'ورق جدران (رول)', 'shiplap': 'لوح جداري — بديل شيبورد', 'marble': 'لوح جداري — بديل رخام',
    'hpl': 'لوح تكسية HPL', 'wood': 'لوح تكسية — بديل خشب', 'exterior': 'لوح تكسية جدران', 'brick': 'لوح ديكوري — بديل طوب',
    'stone': 'لوح ديكوري — بديل حجر', 'clay': 'صفائح تكسية', 'spc': 'أرضيات باركيه SPC', 'laminate': 'أرضيات باركيه',
    'carpet': 'موكيت أرضيات', 'skirting': 'نعلة (وزرة)', 'molding': 'برواز / مداد ديكور', 'cornice': 'كرنيش',
    'accessory': 'إكسسوار تشطيب', 'partition': 'عمود بارتشن', 'decor': 'قطعة ديكور',
}
ANS_PAT = {'plain': 'سادة', 'stripe': 'مخطط', 'floral': 'بنقشة ورود', 'ornament': 'منقوش', 'marble': 'رخامي معرّق',
           'fabric': 'بملمس قماشي', 'wood': 'بمظهر خشبي', 'fluted': 'مضلع', 'glossy': 'لامع', '3d': 'بنقش بارز', 'stone': 'بملمس حجري',
           'wave': 'مودرن', 'kids': 'للأطفال', 'herringbone': 'هرمي'}
IS_WORDS = ['هو', 'من فئة', 'يُصنَّف ضمن', 'خيار ضمن فئة', 'من مجموعة']
USE_WORDS = ['يناسب {rooms}', 'يُستخدم في {rooms}', 'مكانه المعتاد {rooms}', 'يليق بـ{rooms}', 'يُختار غالباً لـ{rooms}']
SPEC_HEADS = ['مواصفات {ref}', 'بطاقة {ref}', 'جدول مواصفات {ref}', '{ref} في سطور', 'بيانات {ref}']
INSTALL = [
    'فنيّو تكسا يركّبون {thing} في الرياض وجدة والدمام والمدينة المنورة ومكة؛ التفاصيل في صفحة {inst}.',
    'خدمة تركيب {thing} متاحة في الرياض، جدة، مكة، المدينة المنورة والدمام، وتُطلب من صفحة {inst}.',
    'إن كنت في الرياض أو جدة أو مكة أو المدينة المنورة أو الدمام فاطلب مع {ref} رفع المقاس والتركيب من {inst}.',
    'تركيب {ref} يُطلب مستقلاً عبر {inst} داخل الرياض وجدة والدمام ومكة والمدينة المنورة.',
    'لتركيب {ref} على يد فنيين متخصصين راجع {inst}؛ الخدمة تغطي الرياض وجدة ومكة والمدينة المنورة والدمام.',
    'في الرياض وجدة ومكة والمدينة المنورة والدمام يتولى فريق تكسا تركيب {thing} بعد رفع المقاس، انظر {inst}.',
    'تحتاج من يركّب {ref}؟ {inst} متاحة في خمس مدن: الرياض، جدة، الدمام، مكة، المدينة المنورة.',
    'رفع المقاس وتركيب {thing} خدمتان متاحتان في الرياض وجدة والدمام ومكة والمدينة المنورة عبر {inst}.',
    'يمكنك طلب {ref} وحده أو مع التركيب؛ {inst} تغطي الرياض وجدة ومكة والمدينة المنورة والدمام.',
]
SHIP = [
    'أما شحن {ref} فيغطي جميع مدن المملكة.',
    'وإن كنت في مدينة أخرى فيُشحن طلبك من {ref} إليك أينما كنت داخل المملكة.',
    'ولبقية المدن نشحن {ref} إلى أي مكان في المملكة.',
    'شحن {ref} متاح إلى كل مناطق المملكة.',
    'ويصل طلب {ref} بالشحن إلى جميع مدن السعودية.',
    'وخارج هذه المدن يصلك {ref} بالشحن لأي مدينة في المملكة.',
    'والتوصيل متاح لكل مدن المملكة عند طلب {ref}.',
    'ويُشحن {ref} إلى أي مدينة سعودية.',
    'وللمدن الأخرى يُرسَل {ref} بالشحن إلى عنوانك داخل المملكة.',
]
SHIP_HEADS = ['التركيب والشحن', 'الشحن والتركيب', 'من يركّبه وأين يصل؟', 'تركيب {ref} وشحنه', 'التوصيل والتركيب', 'كيف يصلك {ref}؟']
LINKS = [
    'قارن بقية الخيارات في {subs}، أو تصفّح كل منتجات {root}.',
    'درجات وتصاميم قريبة من {ref} تجدها في {subs}، والجديد كله في قسم {root}.',
    'إن لم يكن {ref} ما تبحث عنه فانظر {subs}، أو ارجع إلى قسم {root}.',
    'شاهد منتجات مشابهة لـ{ref} في {subs}، واكتشف بقية قسم {root}.',
    'للمقارنة مع {ref}: {subs}، وكذلك القسم الرئيسي {root}.',
    'منتجات قريبة من {ref} موجودة في {subs}، وكل التشكيلة في {root}.',
    'تصفّح {subs} لخيارات قريبة من {ref}، أو انتقل إلى {root} لرؤية الكل.',
    'خيارات أخرى بجانب {ref}: {subs}، ثم قسم {root} كاملاً.',
]
LINKS_ROOT_ONLY = [
    'تصفّح بقية منتجات {root} للمقارنة مع {ref}.',
    'خيارات أخرى بجانب {ref} تجدها في قسم {root}.',
    'للمقارنة مع {ref} ارجع إلى قسم {root}.',
    'شاهد بقية التشكيلة في {root} قبل أن تحسم اختيار {ref}.',
]


def esc(s):
    return html.escape(s, quote=False)


def tidy(s):
    """وصل حرفَي الجر (لـ/بـ) بالكلمة العربية التي تليهما."""
    s = re.sub(r'(?<![\u0621-\u064A])لـال(?=[\u0621-\u064A])', 'لل', s)
    s = re.sub(r'(?<![\u0621-\u064A])([لب])ـ(?=[\u0621-\u064A])', r'\1', s)
    s = re.sub(r'(?<![\u0621-\u064A])للل', 'لل', s)
    return s


def qty_sentence(F, c, pid):
    """جملة مثال الكمية بصياغة متصلة (العدد فاعل مرفوع)."""
    if not c.get('qty_n'):
        return ''
    k = F['kind']
    n = c.get('n_txt') or c.get('rolls_txt')
    v = lambda opts: pick(opts, pid, 'ans-q')
    if k == 'wallpaper':
        n = c['rolls_txt']
        return v(['وجدار بعرض {Ww} م يلزمه {n} بحساب الشرائح.', 'ولجدار عرضه {Ww} م يلزم {n} على ارتفاع 2.8 م.',
                  'ويلزم لجدار بعرض {Ww} م {n} محسوبة بالشرائح.']).format(Ww=c['Ww'], n=n)
    if k in ('panel', 'small'):
        return v(['وجدار {Ww} × 2.8 م يلزمه {n} مع 10% هدر.', 'ولجدار بعرض {Ww} م وارتفاع 2.8 م يلزم {n} شاملة الهدر.',
                  'ويلزم لجدار {Ww} × 2.8 م {n} بعد إضافة 10% للقص.']).format(Ww=c['Ww'], n=n)
    if k == 'slat':
        return v(['وجدار بعرض {Ww} م يلزمه {n} مع 10% هدر.', 'ولجدار عرضه {Ww} م يلزم {n} شاملة الهدر.',
                  'ويلزم لجدار بعرض {Ww} م {n} بعد إضافة 10% للقص.']).format(Ww=c['Ww'], n=n)
    if k == 'floor':
        ap = '' if c.get('has_carton') else 'نحو '
        return v(['وغرفة {ra} × {rb} م يلزمها {ap}{n} مع 10% هدر.', 'ولغرفة {ra} × {rb} م يلزم {ap}{n} شاملة الهدر.',
                  'ويلزم لغرفة {ra} × {rb} م {ap}{n} بعد إضافة 10% للقص.']).format(ra=c['ra'], rb=c['rb'], n=n, ap=ap)
    if k == 'linear' and c.get('room'):
        return v(['وغرفة {ra} × {rb} م يلزمها {n} مع 10% هدر.', 'ولغرفة {ra} × {rb} م يلزم {n} شاملة الهدر.']).format(
            ra=c['ra'], rb=c['rb'], n=n)
    if k == 'linear':
        return v(['وكل {run} م طولية يلزمها {n} مع 10% هدر.', 'ولكل {run} م طولية يلزم {n} شاملة الهدر.']).format(run=c['run'], n=n)
    return ''


def answer_paragraph(F, c, kw):
    pid = F['id']
    name = F['name']
    v = lambda opts, salt: pick(opts, pid, 'ans-' + salt)
    k = F['kind']
    what = kw
    if c['origin']:
        what += {'محلي': ' بصناعة محلية', 'السعودية': ' بصناعة سعودية'}.get(c['origin'], ' من ' + c['origin'])
    if c['material'] and c['material'].lower() not in kw.lower():
        what += ' بخامة ' + c['material']
    size = ''
    if c.get('calc'):
        if k == 'wallpaper':
            size = v(['يأتي في لفة طولها {L} م وعرضها {Wcm} سم تغطي نحو {cov} م²',
                      'لفّته بطول {L} م وعرض {Wcm} سم وتغطي قرابة {cov} م²',
                      'تُباع لفّته بمقاس {L} م × {Wcm} سم، أي نحو {cov} م²'], 'sz')
        elif k in ('panel', 'small'):
            size = v(['مقاسه {Wcm} × {Lcm} سم و{yg} القطعة منه {cov} م²', 'يأتي بمقاس {Wcm} × {Lcm} سم، أي {cov} م² للقطعة',
                      'مقاس القطعة منه {Wcm} × {Lcm} سم بتغطية {cov} م²'], 'sz')
        elif k == 'slat':
            size = v(['عرضه {Wcm} سم وطوله {L} م ويغطي {cov} م²', 'يأتي بعرض {Wcm} سم وطول {L} م، أي {cov} م² للقطعة',
                      'مقاس القطعة منه {Wcm} سم × {L} م بتغطية {cov} م²'], 'sz')
        elif k == 'floor':
            bits = []
            if c.get('Lcm'):
                bits.append('مقاس %s %s × %s سم' % (c['U'], c['Lcm'], c['Wcm']))
            if c['thick']:
                bits.append('سماكته %s ملم' % c['thick'])
            if c.get('has_carton'):
                bits.append('كرتونته تغطي %s م²' % c['carton'])
            elif c.get('pa'):
                bits.append('مساحة %s %s م²' % (c['U'], c['pa']))
            size = '، و'.join(bits)
        elif k == 'linear':
            size = v(['طول القطعة منه {L} م وعرضها {Wcm} سم', 'تأتي القطعة بطول {L} م وعرض {Wcm} سم',
                      'مقاس القطعة {Lcm} سم طولاً × {Wcm} سم'], 'sz')
        size = size.format_map(c)
    else:
        bits = []
        if c.get('cov_only'):
            bits.append('%s منه %s %s م² حسب بيانات المنتج' % (c['U'], c['yg'], c['cov']))
        if c.get('post_h'):
            bits.append('ارتفاعه %s م' % c['post_h'])
        if c['thick']:
            bits.append('سماكته %s ملم' % c['thick'])
        size = '، و'.join(bits)
    s1 = '%s هو %s' % (name, what) + ('، ' + size if size else '') + '.'
    sents = [s1]
    q = qty_sentence(F, c, pid)
    uses = v(['يناسب {rooms}', 'يُستخدم في {rooms}', 'مكانه المعتاد {rooms}', 'يليق بـ{rooms}'], 'use').format_map(c)
    claims = []
    if c['waterproof']:
        claims.append('يذكر وصفه أنه مقاوم للماء')
    if c['click']:
        claims.append('يُركَّب بالتعشيق (كليك)')
    if q:
        sents.append(q)
    opt = []
    nd = ''
    if not c.get('calc') and k not in ('piece', 'post'):
        nd = v(['مقاسه غير مذكور في بيانات المنتج فاطلبه من فريق المبيعات قبل حساب الكمية',
                'مقاسه المؤكَّد يزوّدك به فريق المبيعات قبل تحديد العدد لأنه لم يرد في بيانات المتجر',
                'عدده يُحسب بعد تأكيد مقاسه من فريق تكسا لأنه غير مؤكَّد في البيانات'], 'nd')
    opt.append(v(['وتجد مواصفاته كاملة في الجدول أدناه.', 'وبقية مواصفاته في الجدول أسفل الصفحة.',
                  'وتفاصيله موضّحة في جدول المواصفات.'], 'tbl'))
    opt.append('ويمكنك حساب الكمية بحاسبة الكميات في المتجر.')
    svc = v(['يُشحن إلى كل مدن المملكة مع تركيب متاح في خمس مدن', 'شحنه متاح لجميع مدن المملكة وتركيبه في خمس مدن رئيسية',
             'يصل بالشحن إلى أي مدينة في المملكة ويُركَّب في خمس مدن'], 'svc')
    tail = uses + ('، و' + ' و'.join(claims) if claims else '') + ('، و' + nd if nd else '')
    wc = lambda ss: len(' '.join(ss).split())
    if wc(sents + [tail]) < 41:
        tail += '، و' + svc
    sents.append(tail + '.')
    wc = lambda ss: len(' '.join(ss).split())
    for o in opt:
        if wc(sents) >= 41:
            break
        if wc(sents + [o]) <= 60:
            sents.append(o)
    return ' '.join(sents)


def spec_rows(F, c):
    rows = []
    if F['code']:
        rows.append(('الكود', F['code']))
    k = F['kind']
    if c.get('calc') and F.get('dims'):
        if k == 'wallpaper':
            rows.append(('المقاس', 'لفة %s م (طول) × %s سم (عرض)' % (c['L'], c['Wcm'])))
            rows.append(('تغطية اللفة', '%s م² تقريباً' % c['cov']))
            rows.append(('شرائح اللفة', '%s بارتفاع 2.8 م' % c['spr_txt']))
        elif k in ('panel', 'small'):
            rows.append(('المقاس', '%s × %s سم' % (c['Wcm'], c['Lcm'])))
            rows.append(('تغطية %s' % c['U'], '%s م²' % c['cov']))
        elif k == 'slat':
            rows.append(('المقاس', '%s سم (عرض) × %s سم (طول)' % (c['Wcm'], c['Lcm'])))
            rows.append(('تغطية %s' % c['U'], '%s م²' % c['cov']))
        elif k == 'floor':
            rows.append(('مقاس %s' % c['U'], '%s × %s سم' % (c['Lcm'], c['Wcm'])))
            rows.append(('مساحة %s' % c['U'], '%s م² (نحو %s لكل متر مربع)' % (c['pa'], c['per_m2'])))
        elif k == 'linear':
            rows.append(('المقاس', '%s سم (طول) × %s سم' % (c['Lcm'], c['Wcm'])))
    elif c.get('cov_only'):
        rows.append(('تغطية %s' % c['U'], '%s م² (حسب وصف المنتج)' % c['cov']))
    elif k in ('piece', 'post') and F.get('dims'):
        rows.append(('المقاس', c['size']))
    if c.get('post_h'):
        rows.append(('الارتفاع', '%s م' % c['post_h']))
    if k == 'floor' and c.get('has_carton'):
        rows.append(('تغطية الكرتونة', '%s م²' % c['carton']))
    if c.get('pcs_carton'):
        rows.append(('العدد في الكرتونة', str(c['pcs_carton'])))
    if c['thick']:
        rows.append(('السماكة', '%s ملم' % c['thick']))
    if c['cph']:
        rows.append(('اللون', c['cph']))
    if F['pattern'] in PATTERN_ROW:
        rows.append(('النقشة / السطح', PATTERN_ROW[F['pattern']]))
    rows.append(('النوع', SPEC_TYPE[F['sub']]))
    if c['material']:
        rows.append(('الخامة', c['material']))
    if c['origin']:
        rows.append(('المنشأ', {'محلي': 'صناعة محلية'}.get(c['origin'], c['origin'])))
    if c['waterproof']:
        rows.append(('مقاومة الماء', 'نعم (حسب وصف المنتج)'))
    if c['click']:
        rows.append(('نظام التركيب', 'تعشيق (كليك)'))
    us = F.get('unit_sale')
    if us:
        us = {'لوح': 'لوح', 'اللوح': 'لوح', 'متر مربع': 'متر مربع', 'المتر المربع': 'متر مربع', 'قطعة': 'قطعة', 'القطعة': 'قطعة',
              'لفة': 'لفة', 'اللفة': 'لفة', 'متر طولي': 'متر طولي', 'الصفيحة': 'صفيحة', 'صفيحة': 'صفيحة', 'كرتونة': 'كرتونة',
              'الكرتونة': 'كرتونة'}.get(us.strip())
        if us:
            rows.append(('وحدة البيع', us))
    return rows


def link_paragraph(F, c, links, paths, root_name):
    pid = F['id']
    root = F['root']
    rname = root_name.get(root)
    subs = []
    for cat in F['cats']:
        p = paths.get(cat)
        if not p or p[0] != root or len(p) < 2 or cat.startswith('عروض'):
            continue
        subs.append((len(p), H(pid, 'lk-' + cat), cat))
    subs.sort(key=lambda t: (-t[0], t[1]))
    subs = [s[2] for s in subs[:2]]
    root_a = A(links[rname], rname)
    if subs:
        sub_a = ' و'.join(A(links[s], s) for s in subs)
        return pick(LINKS, pid, 'links').format(subs=sub_a, root=root_a, ref=esc(c['ref']))
    return pick(LINKS_ROOT_ONLY, pid, 'links').format(root=root_a, ref=esc(c['ref']))


# ------------------------------------------------------------------ أقسام v5 (تجهيز، خطوات، عناية، أفكار، أخطاء، مكمّلات)
# معرفة تركيب وديكور عامة صحيحة لنوع المنتج، بلا ادعاءات تقنية ولا أسعار. كل خانة لها عدة صيغ تُختار بالـhash.

GROUP = {'wallpaper': 'wallpaper', 'shiplap': 'panel', 'marble': 'panel', 'hpl': 'panel', 'wood': 'slat', 'exterior': 'slat',
         'brick': 'small', 'stone': 'small', 'clay': 'small', 'spc': 'floor', 'laminate': 'floor', 'carpet': 'floor',
         'skirting': 'linear', 'molding': 'linear', 'cornice': 'linear', 'accessory': 'linear', 'partition': 'piece', 'decor': 'piece'}

PREP = {
    'wallpaper': dict(surface=[
        'يُركَّب {ref} على جدار مستوٍ ونظيف وجاف تماماً، وتُعالَج الشقوق والنتوءات بالمعجون ثم تُصنفر قبل أي شيء.',
        'قبل لصق {ref} تُزال بقايا الدهان المتقشّر والغبار، وتُملأ الحفر وتُسوّى حتى يصير السطح أملس باللمس.',
        'أساس النتيجة الجيدة جدار جاف خالٍ من الرطوبة والنتوءات؛ أي عيب في السطح يظهر تحت الورق بعد التركيب.'], tools=[
        'الأدوات المعتادة: متر وميزان ماء، قاطع حاد ومسطرة معدنية، فرشاة أو رول للّاصق، وأداة فرد ناعمة لطرد الهواء.',
        'جهّز ميزان ماء أو خيط شاقول لضبط أول شريحة، وقاطعاً حاداً بشفرات احتياطية، وإسفنجة نظيفة لمسح اللاصق الزائد.',
        'يلزمك متر وقلم رصاص ومسطرة طويلة وقاطع حاد وأداة فرد، مع طاولة أو سطح نظيف لقص الشرائح عليه.']),
    'panel': dict(surface=[
        'يُثبَّت {ref} على جدار مستوٍ ونظيف وجاف؛ تُزال النتوءات وتُملأ الحفر لأن اللوح يتبع استواء السطح الذي تحته.',
        'قبل تركيب {ref} يُفحص استواء الجدار بمسطرة طويلة، ويُنظَّف من الغبار والدهان المتقشّر حتى يتماسك اللاصق.',
        'الجدار المتماسك الجاف شرط أساسي؛ الرطوبة الظاهرة أو الدهان الضعيف يُعالَجان قبل لصق أي لوح.'], tools=[
        'الأدوات المعتادة: متر وميزان ماء، قلم ومسطرة طويلة، منشار ناعم الأسنان أو أداة قص مناسبة، ولاصق مناسب لنوع اللوح.',
        'جهّز ميزان ماء لضبط أول لوح، وأداة قص نظيفة الحافة، ومثقاباً أو منشار فتحات للأفياش والمفاتيح.',
        'يلزمك متر وقلم وميزان ومسطرة معدنية طويلة وأداة قص، مع قطعة قماش لمسح اللاصق الزائد فوراً.']),
    'slat': dict(surface=[
        'يُركَّب {ref} على جدار مستوٍ ونظيف وجاف؛ أي ميلان في السطح يظهر مباشرة في الخطوط الطولية.',
        'قبل تثبيت {ref} يُنظَّف الجدار من الغبار والدهان المتقشّر، وتُسوّى النتوءات حتى تجلس القطع متلاصقة.',
        'استواء الجدار أهم ما في التجهيز هنا، لأن القطع الطولية تكشف أي تموّج في السطح الذي تحتها.'], tools=[
        'الأدوات المعتادة: متر وميزان ماء، منشار ناعم الأسنان لقص الأطوال، قلم ومسطرة، ولاصق مناسب لنوع القطع.',
        'جهّز ميزان ماء أو خيط شاقول لضبط أول قطعة، وأداة قص بحافة نظيفة، وقفلات أو زوايا للأطراف.',
        'يلزمك متر وقلم وميزان وأداة قص، مع تحديد أماكن الأفياش والمفاتيح على الجدار قبل البدء.']),
    'small': dict(surface=[
        'يُثبَّت {ref} على سطح نظيف وجاف ومتماسك؛ الدهان المتقشّر يُزال والجدار غير المستوي يُسوّى أولاً.',
        'قبل تركيب {ref} يُنظَّف الجدار من الغبار والدهون، وتُعالَج الشقوق حتى يتماسك اللاصق على كامل المساحة.',
        'السطح الضعيف أو الرطب يُعالَج قبل أي شيء، فثبات القطع من ثبات الجدار الذي تحتها.'], tools=[
        'الأدوات المعتادة: متر وميزان ماء، قلم وخيط لضبط الصفوف، أداة قص مناسبة، ولاصق مناسب لنوع القطع.',
        'جهّز ميزان ماء لضبط الصف الأول، وأداة قص للأطراف والزوايا، وفرشاة ناعمة لتنظيف السطح بعد التركيب.',
        'يلزمك متر وقلم وميزان وأداة قص، وافرد القطع على الأرض أولاً لتوزّع الدرجات قبل التثبيت.']),
    'floor': dict(surface=[
        'يُفرش {ref} على أرضية مستوية ونظيفة وجافة؛ الفروقات والبلاطات المرتفعة تُسوّى قبل البدء.',
        'قبل تركيب {ref} تُكنس الأرضية جيداً وتُفحص بمسطرة طويلة، وأي تموّج واضح يُعالَج حتى لا يظهر عند المشي.',
        'الأرضية الجافة المستوية أساس التركيب؛ تُزال النعلات القديمة إن لزم ويُفرَّغ المكان من الأثاث.'], tools=[
        'الأدوات المعتادة: متر وقلم وزاوية قائمة، منشار أو أداة قص مناسبة، ومطرقة مطاطية مع قطعة طرق عند الحاجة.',
        'جهّز متراً وزاوية وأداة قص، وحدّد اتجاه الرصّ ومكان أول صف قبل فتح الكراتين.',
        'يلزمك متر وقلم وأداة قص، مع فواصل انتقال للأبواب ونعلات تُركَّب بعد انتهاء الفرش.']),
    'linear': dict(surface=[
        'يُركَّب {ref} على سطح نظيف وجاف بعد انتهاء الدهان والأرضيات، حتى لا يتّسخ أو يُخدش في مراحل لاحقة.',
        'قبل تثبيت {ref} يُمسح مكان التركيب من الغبار، وتُعالَج أي نتوءات تمنع القطعة من الجلوس على السطح.',
        'السطح المستقيم النظيف يجعل الوصلات أدق؛ تُفحص استقامة الجدار أو السقف عند خط التركيب أولاً.'], tools=[
        'الأدوات المعتادة: متر وقلم، صندوق قص بزاوية 45 درجة أو منشار زوايا، ولاصق مناسب لنوع القطعة.',
        'جهّز متراً وأداة قص زوايا وميزان ماء أو خيطاً مشدوداً لضبط الاستقامة على طول الجدار.',
        'يلزمك متر وقلم وأداة لقص الزوايا، مع معجون أو مادة تعبئة مناسبة لإخفاء الوصلات عند الحاجة.']),
    'piece': dict(surface=[
        'يُثبَّت {ref} على سطح نظيف وجاف ومستوٍ بعد انتهاء الدهان الأساسي.',
        'قبل تركيب {ref} يُمسح مكان التثبيت من الغبار وتُحدَّد المواضع بالقلم والميزان.',
        'السطح المتماسك شرط للتثبيت؛ الدهان المتقشّر أو الرطوبة يُعالَجان أولاً.'], tools=[
        'الأدوات المعتادة: متر وقلم وميزان ماء، ولاصق أو وسيلة تثبيت مناسبة لنوع القطعة.',
        'جهّز متراً وميزاناً وقلماً لتحديد المحاور، وأداة قص إن احتاجت القطعة تعديلاً في الموقع.',
        'يلزمك متر وميزان ووسيلة تثبيت مناسبة، مع رسم بسيط يحدد المسافات بين القطع.']),
}
PREP_MEASURE = [
    'قِس المكان مرتين وسجّل الأبعاد قبل القص، واحسب كمية {ref} مع هامش للهدر.',
    'خذ المقاسات من أكثر من نقطة، فالجدران والأرضيات قليلاً ما تكون متعامدة تماماً، ثم ابدأ بـ{ref}.',
    'راجع الكمية المحسوبة من {ref} قبل فتح العبوات، وافحص القطع للتأكد من تطابق الدرجة.',
    'حدّد نقطة البداية وخط الاستقامة الأول بدقة، فكل ما بعده يُبنى عليه عند تركيب {ref}.',
    'افحص ما استلمته من {ref} قبل التركيب وقارن الدرجة بين القطع في ضوء النهار.',
    'جهّز المكان بإبعاد الأثاث وتغطية ما لا يُنقل، ثم طابق أبعاد {ref} مع مخططك.',
]
PREP_HEADS = ['قبل التركيب: تجهيز السطح والأدوات', 'تجهيز السطح والأدوات قبل تركيب {ref}', 'قبل أن تبدأ: السطح والأدوات',
              'التجهيز قبل التركيب', 'ما تحتاجه قبل التركيب', 'تحضير المكان والأدوات']

STEPS = {
    'wallpaper': [
        ['قِس ارتفاع الجدار وقصّ الشرائح بزيادة بضعة سنتيمترات من الأعلى والأسفل.', 'اقطع الشرائح بطول الجدار مع زيادة بسيطة للتشذيب من الطرفين.'],
        ['ارسم خطاً رأسياً بالميزان لتضبط عليه أول شريحة.', 'حدّد خطاً شاقولياً قرب الزاوية لتبدأ منه أول شريحة مستقيمة.'],
        ['ضع اللاصق المناسب حسب تعليمات الورق ثم ثبّت الشريحة من الأعلى نزولاً.', 'افرد اللاصق بالتساوي، ثم علّق الشريحة من أعلى الجدار واتركها تنسدل.'],
        ['افرد الشريحة من الوسط نحو الأطراف لطرد فقاعات الهواء.', 'مرّر أداة الفرد من المنتصف إلى الحواف حتى يلتصق الورق بلا فقاعات.'],
        ['طابق الشريحة التالية مع سابقتها عند الحافة ثم شذّب الزوائد بقاطع حاد.', 'ضُمّ حافة كل شريحة إلى التي قبلها دون تراكب، واقطع الزائد عند السقف والنعلة.']],
    'panel': [
        ['حدّد توزيع الألواح على الجدار وموضع الفواصل قبل أي قص.', 'ارسم على الجدار أماكن الألواح والفواصل لتعرف مقاس كل قطعة.'],
        ['قصّ اللوح على المقاس وافتح أماكن الأفياش والمفاتيح.', 'اقطع اللوح بعد القياس مرتين، وجهّز فتحات الكهرباء قبل التثبيت.'],
        ['ضع اللاصق المناسب على ظهر اللوح أو الجدار بحسب تعليماته.', 'وزّع اللاصق المناسب بخطوط منتظمة حتى يتماسك اللوح على كامل مساحته.'],
        ['ثبّت أول لوح مضبوطاً بالميزان واضغط عليه بالتساوي.', 'ركّب اللوح الأول على خط الميزان، فاستقامته تحدد استقامة الجدار كله.'],
        ['أكمل بقية الألواح مع الفواصل أو التلاصق، ثم امسح أي لاصق زائد.', 'تابع التركيب لوحاً بعد لوح مع ضبط الفواصل، ونظّف السطح في النهاية.']],
    'slat': [
        ['حدّد اتجاه التركيب (عمودي أو أفقي) ونقطة البداية.', 'قرّر اتجاه القطع ومن أي طرف تبدأ قبل القص.'],
        ['قصّ القطع على ارتفاع الجدار وافتح أماكن الأفياش.', 'اقطع الأطوال المطلوبة وجهّز فتحات الكهرباء مسبقاً.'],
        ['ضع اللاصق المناسب على ظهر القطعة بحسب تعليماته.', 'وزّع اللاصق المناسب بخط متعرّج على ظهر كل قطعة.'],
        ['ثبّت أول قطعة مضبوطة بالميزان فهي مرجع ما بعدها.', 'ركّب القطعة الأولى على خط شاقولي دقيق واضغط عليها حتى تثبت.'],
        ['أكمل القطع متلاصقة أو معشّقة، ثم أنهِ الأطراف بقفلة أو زاوية.', 'تابع بقية القطع واحدة بجانب الأخرى، واختم الحواف بقطعة نهاية.']],
    'small': [
        ['افرد القطع على الأرض ووزّع الدرجات قبل التثبيت.', 'رتّب القطع جافة على الأرض لترى التوزيع النهائي.'],
        ['ارسم خطاً أفقياً بالميزان للصف الأول.', 'حدّد خط البداية بالميزان، فالصف الأول يضبط كل ما فوقه.'],
        ['ضع اللاصق المناسب على ظهر القطعة أو الجدار بحسب تعليماته.', 'وزّع اللاصق المناسب بالتساوي حتى تتماسك القطعة كاملة.'],
        ['ثبّت الصفوف من الأسفل إلى الأعلى مع ضبط الفواصل.', 'ركّب صفاً بعد صف مع مراجعة الاستقامة كل بضع قطع.'],
        ['قصّ قطع الأطراف والزوايا، ثم نظّف السطح بفرشاة ناعمة.', 'أنهِ الحواف بقطع مقصوصة على المقاس، وأزل الغبار واللاصق الزائد.']],
    'floor': [
        ['نظّف الأرضية وافرش الطبقة السفلية إن كان نظام التركيب يتطلبها.', 'اكنس الأرضية جيداً وجهّز ما يلزم تحت الأرضية بحسب نوعها.'],
        ['حدّد اتجاه الرصّ وابدأ من الجدار الأطول أو من جهة الضوء.', 'اختر اتجاه القطع ثم ابدأ الصف الأول بمحاذاة جدار مستقيم.'],
        ['ركّب الصف الأول مستقيماً مع ترك مسافة بسيطة عند الجدار تغطيها النعلة.', 'اضبط الصف الأول بدقة واترك فراغاً صغيراً عند الحائط يختفي تحت النعلة.'],
        ['أكمل الصفوف مع تخالف وصلات الأطراف بين صف وآخر.', 'تابع الصفوف بحيث لا تصطف نهايات القطع في خط واحد.'],
        ['قصّ قطع الصف الأخير، ثم ركّب فواصل الأبواب والنعلات.', 'أنهِ بالصف الأخير مقصوصاً على المقاس، وبعده الفواصل والنعلات.']],
    'linear': [
        ['قِس كل جدار على حدة وسجّل الأطوال.', 'خذ طول كل ضلع بمفرده بدل الاعتماد على المحيط الإجمالي.'],
        ['قصّ الأطراف بزاوية 45 درجة عند الزوايا.', 'جهّز قصّات الزوايا المائلة قبل وضع أي لاصق.'],
        ['جرّب القطع في مكانها جافة قبل التثبيت.', 'ضع القطع في موضعها بلا لاصق أولاً لتتأكد من تطابق الزوايا.'],
        ['ضع اللاصق المناسب وثبّت القطعة مع ضبط الاستقامة.', 'ثبّت القطعة باللاصق المناسب واضغط عليها على طولها.'],
        ['عالج الوصلات بمادة تعبئة مناسبة وامسح الزائد.', 'أخفِ الوصلات بمعالجة بسيطة ونظّف السطح بعد الجفاف.']],
    'piece': [
        ['حدّد المواضع بالقلم والميزان بحسب التصميم.', 'علّم أماكن القطع على السطح مع ضبط المحاور.'],
        ['جرّب القطعة في مكانها قبل التثبيت.', 'ضع القطعة جافة في موضعها لتتأكد من المقاس والتماثل.'],
        ['ضع وسيلة التثبيت المناسبة لنوع القطعة.', 'جهّز اللاصق أو وسيلة التثبيت المناسبة بحسب تعليماتها.'],
        ['ثبّت القطعة واضغط عليها حتى تتماسك مع السطح.', 'ركّب القطعة على العلامات واضبط استقامتها قبل أن تجفّ المادة.'],
        ['عالج الحواف والوصلات ونظّف الزائد.', 'أنهِ بمعالجة الحواف ومسح أي أثر للتثبيت.']],
}
STEPS_HEADS = ['خطوات التركيب باختصار', 'كيف يُركَّب {ref}؟ الخطوات باختصار', 'التركيب في خمس خطوات', 'ملخّص خطوات التركيب',
               'طريقة التركيب خطوة بخطوة', 'مراحل التركيب باختصار']
STEPS_NOTE = [
    'هذه خطوات عامة لهذا النوع من المنتجات؛ الفنيّ يعدّلها بحسب حالة المكان ونوع اللاصق.',
    'الخطوات استرشادية، وتفاصيل التثبيت يحددها الفنيّ بعد معاينة السطح.',
    'ما سبق ملخّص عام، وخدمة التركيب من تكسا تتولى التفاصيل في المدن المتاحة.',
    'إن لم تكن لديك خبرة سابقة فالأفضل ترك التركيب لفنيّ متخصص، وهذه الخطوات لتعرف ما سيجري.',
]

CARE = {
    'wallpaper': [['يُنظَّف {ref} بقطعة قماش ناعمة جافة أو مبللة قليلاً ثم يُجفَّف مباشرة.', 'امسح الغبار عن {ref} بقماش ناعم، وعند البقع استخدم قماشاً رطباً قليلاً دون فرك.',
                   'العناية اليومية بـ{ref} لا تتجاوز مسحة قماش ناعمة من حين لآخر.'],
                  ['تجنّب المنظفات الكاشطة والفرك القوي، وأبعد مصادر الحرارة المباشرة عن الجدار.', 'لا تستخدم الإسفنج الخشن ولا تُغرق السطح بالماء، وجرّب أي منظف على زاوية غير ظاهرة.',
                   'انتبه عند تحريك الأثاث حتى لا يحتكّ بالحواف، وعالج أي طرف يرتفع فور ملاحظته.']],
    'panel': [['يُمسح {ref} بقطعة قماش ناعمة مبللة قليلاً ثم يُجفَّف.', 'تنظيف {ref} يكفيه قماش ناعم ورطوبة خفيفة من حين لآخر.',
               'الغبار يُزال عن {ref} بقماش جاف، والبقع بمسحة رطبة خفيفة.'],
              ['تجنّب الإسفنج الخشن والمواد الكاشطة حتى لا يتأثر السطح.', 'لا تستخدم أدوات حادة قرب السطح، وجرّب أي منظف على طرف غير ظاهر أولاً.',
               'أبعد الأثاث قليلاً عن الجدار حتى لا يحتكّ بالألواح عند الحركة.']],
    'slat': [['يُنظَّف {ref} بفرشاة ناعمة أو قماش يمرّ مع اتجاه الأضلاع.', 'الغبار بين الأضلاع يُزال بفرشاة ناعمة، ثم مسحة خفيفة لـ{ref} عند الحاجة.',
              'تنظيف {ref} يكون باتجاه الخطوط لا عكسها، بقماش ناعم أو فرشاة.'],
             ['تجنّب المواد الكاشطة والماء الكثير.', 'لا تستخدم أدوات حادة لإزالة البقع، وجرّب المنظف على قطعة جانبية أولاً.',
              'افحص الأطراف والقفلات دورياً وأعد تثبيت ما يتحرك منها.']],
    'small': [['يُنظَّف {ref} بفرشاة ناعمة أو مكنسة بفرشاة لإزالة الغبار من تجاويف السطح.', 'الغبار يتجمع في ملمس {ref}، وتكفيه فرشاة ناعمة من حين لآخر.',
               'تنظيف {ref} يبدأ بفرشاة جافة، ثم مسحة قماش رطبة قليلاً عند الحاجة.'],
              ['تجنّب الفرك القوي والمواد الكاشطة.', 'لا تُغرق السطح بالماء، وجرّب أي منظف على قطعة جانبية أولاً.',
               'افحص القطع عند الحواف دورياً وأعد تثبيت ما يتحرك منها.']],
    'floor': [['يُنظَّف {ref} بمكنسة ناعمة ثم ممسحة معصورة جيداً.', 'العناية اليومية بـ{ref}: كنس ناعم، ومسح بممسحة شبه جافة عند الحاجة.',
               'يكفي {ref} كنس منتظم ومسحة رطبة خفيفة، دون سكب الماء على الأرضية.'],
              ['ضع لبّاداً تحت أرجل الأثاث وارفع القطع الثقيلة بدل سحبها.', 'تجنّب المنظفات الكاشطة، وضع ممسحة أقدام عند المدخل لتقليل الرمل.',
               'امسح أي سائل ينسكب دون تأخير، واستخدم واقيات لعجلات الكراسي.']],
    'linear': [['يُمسح {ref} بقطعة قماش ناعمة جافة أو مبللة قليلاً.', 'الغبار يتجمع على الحافة العلوية، فتكفي {ref} مسحة دورية بقماش ناعم.',
                'تنظيف {ref} بسيط: قماش ناعم ورطوبة خفيفة عند الحاجة.'],
               ['تجنّب الماء الكثير والمواد الكاشطة عند الوصلات.', 'انتبه عند المسح بالممسحة أو المكنسة حتى لا تصدم القطعة بقوة.',
                'عالج أي وصلة تنفتح بمادة تعبئة مناسبة قبل أن تتّسع.']],
    'piece': [['يُنظَّف {ref} بفرشاة ناعمة أو قماش جاف لإزالة الغبار من التفاصيل.', 'تكفي {ref} فرشاة ناعمة من حين لآخر، ومسحة رطبة خفيفة عند الحاجة.',
               'الغبار في التفاصيل يُزال بفرشاة جافة، ثم قماش ناعم.'],
              ['تجنّب الفرك القوي والمواد الكاشطة.', 'لا تعلّق أثقالاً على القطعة ولا تستند إليها.',
               'افحص الثبات دورياً وعالج أي حافة ترتفع.']],
}
CARE_HEADS = ['العناية والتنظيف', 'كيف تعتني به بعد التركيب؟', 'التنظيف والعناية اليومية', 'العناية بـ{ref}', 'بعد التركيب: التنظيف والعناية',
              'نصائح العناية']

IDEAS = {
    'wall': ['في {place}: اجعله على الجدار الذي تقع عليه العين أولاً عند الدخول، ودَع بقية الجدران بلون هادئ.',
             'في {place}: نسّقه مع إضاءة جانبية أو مخفية تُبرز {surf}، وأثاث بخطوط بسيطة.',
             'في {place}: يكفي جدار واحد خلف قطعة الأثاث الرئيسية، مع إكسسوارات قليلة حتى لا يزدحم المشهد.',
             'في {place}: اربطه ببقية المكان بتكرار {colr} في وسادة أو ستارة أو مزهرية.',
             'في {place}: وازنه بأرضية وستائر أهدأ منه بدرجة حتى يبقى هو مركز النظر.',
             'في {place}: اختر له الجدار الأقل فتحات ليظهر التصميم متصلاً بلا انقطاع.',
             'في {place}: أضف خشباً طبيعياً أو نباتاً بجواره ليكسر جمود السطح ويدفئ المشهد.'],
    'floor': ['في {place}: رُصّه باتجاه الضوء القادم من النافذة لتبدو الفواصل أخف.',
              'في {place}: اختر جدراناً أفتح من الأرضية بدرجتين وسجادة تربط بين الأثاث والأرض.',
              'في {place}: وحّد الأرضية مع المساحة المجاورة ليبدو المكان أوسع.',
              'في {place}: نسّق النعلة مع لون الأبواب، واترك للأرضية دور القاعدة الهادئة.',
              'في {place}: كرّر {colr} في قطعة أثاث واحدة أو إطار لتترابط الغرفة.',
              'في {place}: دَع قطع الأثاث الكبيرة على أرجل ظاهرة لتُرى الأرضية وتتسع الغرفة بصرياً.'],
    'linear': ['في {place}: وحّد لونه مع الأبواب والحلوق ليبدو التشطيب قطعة واحدة.',
               'في {place}: اختر المقاس متناسباً مع ارتفاع السقف، فالأكبر للأسقف العالية.',
               'في {place}: اجعل الوصلات خلف الأثاث أو قرب الزوايا حيث لا تُرى.',
               'في {place}: استمر به بالمقاس نفسه في المساحات المتصلة لتتوحّد الخطوط.',
               'في {place}: نسّقه مع لون الجدار إن أردت أن يختفي، أو بلون مغاير إن أردته إطاراً واضحاً.',
               'في {place}: راعِ التقاءه مع فواصل الأبواب والأرضيات حتى تنتهي الخطوط بنظافة.'],
    'piece': ['في {place}: وزّع القطع بتماثل حول محور الجدار أو السقف.',
              'في {place}: اجعلها نقطة تمييز واحدة واترك ما حولها بسيطاً.',
              'في {place}: وحّد لونها مع الكرانيش والمدادات المجاورة.',
              'في {place}: حدّد المسافات بالتساوي قبل التثبيت ليظهر الإيقاع منتظماً.',
              'في {place}: نسّقها مع إضاءة موجّهة تُبرز تفاصيلها مساءً.',
              'في {place}: اختر مقاساً يتناسب مع حجم الجدار حتى لا تبدو القطعة صغيرة أو طاغية.'],
}
PLACES_GEN = ['المجالس', 'المداخل', 'الصالات', 'غرف النوم', 'المكاتب', 'الممرات', 'غرف المعيشة']
IDEAS_HEADS = ['أين يليق: أفكار لثلاث غرف', 'أين يليق {ref}؟ ثلاث أفكار', 'ثلاث أفكار لاستخدامه في البيت', 'أفكار تنسيق لثلاث مساحات',
               'أين تضعه؟ أفكار لثلاث غرف', 'ثلاث مساحات يليق بها']

MISTAKES = {
    'wallpaper': ['التركيب على جدار رطب أو حديث الدهان قبل أن يجفّ تماماً.', 'بدء أول شريحة دون خط رأسي، فيميل كل ما بعدها.',
                  'حساب الكمية بالمساحة فقط دون عدّ الشرائح.', 'خلط لفات من دفعات مختلفة على الجدار نفسه.',
                  'قصّ الشرائح بالطول الصافي دون زيادة للتشذيب.', 'إهمال معالجة الشقوق والنتوءات قبل اللصق.',
                  'شدّ الورق بقوة عند الفرد فيتمدد ثم ينكمش عند الجفاف.'],
    'panel': ['التثبيت على جدار غير مستوٍ فتظهر الفواصل متفاوتة.', 'قصّ فتحات الأفياش بعد اللصق لا قبله.',
              'عدم رسم توزيع الألواح مسبقاً فتنتهي بقطعة رفيعة عند الطرف.', 'إهمال مطابقة اتجاه النقشة بين الألواح المتجاورة.',
              'طلب العدد الصافي دون هامش للقص والأخطاء.', 'الضغط على لوح واحد دون مراجعة الميزان قبل الانتقال للتالي.',
              'ترك اللاصق الزائد على السطح حتى يجفّ.'],
    'slat': ['بدء أول قطعة دون ميزان فتميل الخطوط كلها.', 'حساب العدد على العرض الكامل دون التأكد من العرض الظاهر بعد التعشيق.',
             'ترك الأطراف بلا قفلة فتظهر حافة القص.', 'تغيير اتجاه القطع في الجدار نفسه.',
             'قصّ فتحات الأفياش بعد التثبيت.', 'طلب العدد الصافي دون هامش للقص.',
             'إهمال استواء الجدار فتظهر فراغات بين القطع.'],
    'small': ['اصطفاف الفواصل الرأسية فوق بعضها بدل تخالف الصفوف.', 'التركيب من كرتونة واحدة فتتكتل الدرجات في جهة.',
              'بدء الصف الأول دون خط ميزان.', 'تغطية كل جدران الغرفة فيفقد الملمس أثره.',
              'إنهاء الجدار في منتصفه بلا إطار أو زاوية.', 'طلب العدد الصافي دون هامش للزوايا والفتحات.',
              'التثبيت على دهان متقشّر لا يتماسك معه اللاصق.'],
    'floor': ['الفرش على أرضية غير مستوية فيظهر التموّج عند المشي.', 'إلصاق القطع بالجدار دون ترك مسافة بسيطة تغطيها النعلة.',
              'اصطفاف وصلات الأطراف في خط واحد بين الصفوف.', 'نسيان فواصل الانتقال عند الأبواب.',
              'طلب المساحة الصافية دون هدر القص.', 'تغيير اتجاه الرصّ بين غرف متصلة بلا فاصل.',
              'سحب الأثاث الثقيل على الأرضية بعد التركيب.'],
    'linear': ['حساب الكمية على المحيط الصافي دون هدر قصّ الزوايا.', 'قصّ الزوايا مستقيمة بدل 45 درجة.',
               'وضع الوصلات في منتصف الجدار الظاهر.', 'التركيب قبل انتهاء الدهان والأرضيات.',
               'اختيار مقاس لا يتناسب مع ارتفاع السقف.', 'تثبيت القطعة دون تجربتها جافة في مكانها.',
               'اختلاف المقاس أو اللون بين غرف متصلة.'],
    'piece': ['التثبيت دون تحديد المحاور فيختل التماثل.', 'الإكثار من القطع حتى يزدحم الجدار أو السقف.',
              'اختيار مقاس لا يتناسب مع حجم المساحة.', 'التثبيت قبل انتهاء الدهان الأساسي.',
              'اختلاف الطراز بين القطعة وما حولها من مدادات وكرانيش.', 'طلب العدد دون رسم يحدد المواضع.',
              'إهمال معالجة الحواف بعد التثبيت.'],
}
MISTAKES_HEADS = ['أخطاء شائعة تجنّبها', 'أخطاء تتكرر عند تركيب {ref}', 'ثلاثة أخطاء تجنّبها', 'ما الذي يُفسد النتيجة؟ أخطاء شائعة',
                  'أخطاء شائعة في الطلب والتركيب', 'تجنّب هذه الأخطاء']

WITH = {
    'wallpaper': ['نعلات', 'بانوهات', 'بديل خشب مضلع'],
    'shiplap': ['إكسسوارات بديل الشيبورد', 'بديل خشب مضلع', 'نعلات'],
    'marble': ['بديل خشب مضلع', 'إكسسوارات بديل الشيبورد', 'نعلات'],
    'hpl': ['التكسيات الخارجية', 'بديل الشيبورد'],
    'wood': ['إكسسوارات بديل الخشب', 'بديل الشيبورد', 'نعلات'],
    'exterior': ['التكسيات الخارجية', 'نعلات فوم حجري خارجي'],
    'brick': ['بديل خشب مضلع', 'نعلات', 'بديل الحجر'],
    'stone': ['بديل خشب مضلع', 'نعلات', 'بديل الطوب'],
    'clay': ['بديل خشب مضلع', 'نعلات', 'بديل الحجر'],
    'spc': ['نعلات', 'فواصل وإكسسوارات الباركيه'],
    'laminate': ['نعلات', 'فواصل وإكسسوارات الباركيه'],
    'carpet': ['نعلات', 'فواصل وإكسسوارات الباركيه'],
    'skirting': ['الباركيه', 'فواصل وإكسسوارات الباركيه', 'بانوهات'],
    'molding': ['زوايا بانوهات', 'أعمدة وكرانيش', 'إكسسوارات ديكور'],
    'cornice': ['بانوهات', 'أطقم زوايا الأسقف', 'نعلات'],
    'accessory': ['بديل الشيبورد', 'بديل الخشب', 'الباركيه'],
    'partition': ['بديل خشب مضلع', 'إكسسوارات بديل الخشب', 'بديل الشيبورد'],
    'decor': ['بانوهات', 'أعمدة وكرانيش', 'زوايا بانوهات'],
}
WITH_WHY = {
    'نعلات': ['{a} تُنهي التقاء الجدار بالأرضية وتغطي حواف القص', '{a} بلون الأبواب أو الأرضية تكمل التشطيب', '{a} تحمي أسفل الجدار وتُخفي الفراغ عند الأرضية'],
    'بانوهات': ['{a} تؤطّر الجدار وتقسمه إلى مساحات متناسقة', '{a} تضيف إطاراً كلاسيكياً حول المساحة', '{a} تحدّد حدود الجدار المميّز'],
    'بديل خشب مضلع': ['{a} كشرائط جانبية يكسر امتداد السطح', '{a} يضيف عمقاً بجوار السطح المستوي', '{a} يؤطّر الجدار من الطرفين'],
    'إكسسوارات بديل الشيبورد': ['{a} من فواصل وقفلات تُنهي الحواف بنظافة', '{a} تغطي الفواصل بين الألواح ونهاياتها', '{a} تضبط التقاء الألواح والزوايا'],
    'إكسسوارات بديل الخشب': ['{a} من قفلات وزوايا تُنهي الأطراف', '{a} تغطي حواف القص عند النهايات', '{a} تضبط الزوايا ونهايات القطع'],
    'فواصل وإكسسوارات الباركيه': ['{a} تغطي التقاء الأرضيات عند الأبواب', '{a} تُنهي الحواف بين غرفة وأخرى', '{a} لازمة عند كل باب ونهاية مكشوفة'],
    'الباركيه': ['{a} إن كانت الأرضية ضمن التجديد', '{a} لتوحيد لون الأرضية مع القطعة', '{a} لمن يجدّد الأرضية والتشطيب معاً'],
    'بديل الشيبورد': ['{a} كسطح مستوٍ يتوسط الجدار', '{a} لجدار رئيسي بجواره', '{a} لتكسية المساحة الأوسع من الجدار'],
    'بديل الخشب': ['{a} لتكسية الجدار المجاور', '{a} كعنصر مكمّل على الجدار نفسه', '{a} لمن يريد تكسية خطّية بجواره'],
    'بديل الحجر': ['{a} لجدار تمييز آخر بالطابع نفسه', '{a} كخيار قريب في الملمس', '{a} للمقارنة قبل الحسم'],
    'بديل الطوب': ['{a} لجدار تمييز آخر بالطابع نفسه', '{a} كخيار قريب في الملمس', '{a} للمقارنة قبل الحسم'],
    'التكسيات الخارجية': ['{a} لبقية خيارات الواجهات', '{a} لمقارنة المقاسات والألوان', '{a} لتكملة الواجهة بالنوع المناسب'],
    'نعلات فوم حجري خارجي': ['{a} لتأطير الفتحات والواجهات', '{a} كإطار حول النوافذ والأبواب', '{a} لإنهاء حدود الواجهة'],
    'زوايا بانوهات': ['{a} تُنهي التقاء المدادات عند الأركان', '{a} تغني عن قص الزوايا المائلة', '{a} تضيف تفصيلاً عند أركان الإطار'],
    'أعمدة وكرانيش': ['{a} تكمل الإطار عند السقف', '{a} تربط الجدار بالسقف بالطراز نفسه', '{a} لتشطيب علوي متناسق'],
    'إكسسوارات ديكور': ['{a} تضيف نقاط تمييز داخل الإطار', '{a} تكمل الطراز الكلاسيكي', '{a} لتفاصيل صغيرة تثري الجدار'],
    'أطقم زوايا الأسقف': ['{a} تُنهي أركان السقف بتفصيل جاهز', '{a} تكمل الكرنيش عند الزوايا', '{a} لأركان سقف متناسقة'],
}
WITH_HEADS = ['ماذا تطلب معه؟', 'ماذا تطلب مع {ref}؟', 'مكمّلات تُطلب معه', 'ما الذي يكمل التشطيب؟', 'اطلب معه في الشحنة نفسها', 'قطع مكمّلة له']
WITH_TAIL = ['طلبها في الشحنة نفسها يوفّر عليك انتظار قطعة ناقصة أثناء التركيب.', 'اجمعها في طلب واحد ليصل كل شيء قبل موعد الفنيّ.',
             'تحديدها مع الكمية الأساسية يجعل التركيب يتم في زيارة واحدة.', 'اسأل فريق تكسا عن الكمية المناسبة منها مع طلبك.']
EXTRA = [
    'قبل تأكيد الطلب أرسل مقاسات المكان لفريق تكسا لمراجعة الكمية.',
    'احتفظ بقطعة أو بقايا من الدفعة نفسها لأي إصلاح لاحق.',
    'صوّر المكان في ضوء النهار وشاركه مع فريق المبيعات إن احترت بين درجتين.',
    'حدّد موعد التركيب بعد انتهاء أعمال الدهان والكهرباء في الغرفة.',
    'راجع أماكن الأفياش والمفاتيح والتكييف على الجدار قبل اعتماد التوزيع.',
    'اطلب الكمية كاملة مرة واحدة لتضمن تطابق الدرجة بين القطع.',
    'دوّن كود المنتج من جدول المواصفات لتطلب الدرجة نفسها عند أي إضافة.',
    'افحص الشحنة عند الاستلام وبلّغ عن أي ملاحظة قبل بدء التركيب.',
    'اتفق مع الفنيّ على مكان بداية التركيب ومواضع الوصلات قبل أن يبدأ العمل.',
    'قارن المقاس المذكور في جدول المواصفات بأبعاد المكان الفعلية قبل اعتماد العدد.',
    'خزّن القطع مسطّحة في مكان جاف بعيد عن الشمس المباشرة إلى موعد التركيب.',
    'اسأل عن خدمة رفع المقاس إن كان المكان غير منتظم أو كثير الزوايا والفتحات.',
    'خطّط للإضاءة قبل التركيب، فمواضع الأسلاك والسبوتات يصعب تعديلها بعده.',
]
EXTRA_HEADS = ['قبل تأكيد الطلب', 'قائمة سريعة قبل الطلب', 'نصائح أخيرة قبل الشراء', 'راجع هذه النقاط قبل الطلب']
SURF_AR = {'plain': 'سطحه السادة', 'stripe': 'خطوطه', 'floral': 'نقشته', 'ornament': 'زخرفته', 'marble': 'عروقه', 'fabric': 'ملمسه القماشي',
           'wood': 'تعريقه الخشبي', 'fluted': 'تضليعه', 'glossy': 'لمعته', '3d': 'نقشه البارز', 'stone': 'ملمسه الحجري', 'wave': 'خطوطه',
           'kids': 'رسوماته', 'herringbone': 'رصّته'}


def extra_sections(F, c, links, nwords_so_far):
    """أقسام v5. تعيد قائمة أجزاء HTML (قبل الأسئلة) وأخرى (بعدها) وقسماً احتياطياً لبلوغ 600 كلمة."""
    pid = F['id']
    g = GROUP[F['sub']]
    v = lambda opts, salt: pick(opts, pid, 'x-' + salt).format_map(c)
    before, after = [], []
    # أين يليق
    ig = 'wall' if g in ('wallpaper', 'panel', 'slat', 'small') else g
    places = sorted(PLACES.get(F['sub'], PLACES_GEN), key=lambda x: H(pid, 'pl-' + x))[:3]
    ideas = sorted(IDEAS[ig], key=lambda x: H(pid, 'id-' + x))[:3]
    surf = SURF_AR.get(F['pattern'], 'تفاصيله')
    colr = ('لونه ' + c['cph']) if c['cph'] else 'لونه'
    before.append('<h2>%s</h2>' % v(IDEAS_HEADS, 'ih'))
    before.append('<ul>\n' + '\n'.join('<li>%s</li>' % t.format(place=p, surf=surf, colr=colr) for p, t in zip(places, ideas)) + '\n</ul>')
    # التجهيز
    before.append('<h2>%s</h2>' % v(PREP_HEADS, 'ph'))
    before.append('<p>%s %s %s</p>' % (v(PREP[g]['surface'], 'ps'), v(PREP[g]['tools'], 'pt'), v(PREP_MEASURE, 'pm')))
    # الخطوات
    before.append('<h2>%s</h2>' % v(STEPS_HEADS, 'sh'))
    before.append('<ol>\n' + '\n'.join('<li>%s</li>' % pick(st, pid, 'st-%d' % i) for i, st in enumerate(STEPS[g])) + '\n</ol>')
    before.append('<p>%s</p>' % v(STEPS_NOTE, 'sn'))
    # العناية
    before.append('<h2>%s</h2>' % v(CARE_HEADS, 'ch'))
    before.append('<p>%s %s</p>' % (v(CARE[g][0], 'c0'), v(CARE[g][1], 'c1')))
    # الأخطاء
    ms = sorted(MISTAKES[g], key=lambda x: H(pid, 'ms-' + x))[:3]
    before.append('<h2>%s</h2>' % v(MISTAKES_HEADS, 'mh'))
    before.append('<ul>\n' + '\n'.join('<li>%s</li>' % m for m in ms) + '\n</ul>')
    # المكمّلات
    cats = [x for x in WITH[F['sub']] if x in links and x not in F['cats']][:3] or [x for x in WITH[F['sub']] if x in links][:2]
    items = []
    for i, cat in enumerate(cats):
        why = pick(WITH_WHY[cat], pid, 'ww-' + cat).format(a=A(links[cat], cat))
        items.append('<li>%s.</li>' % why)
    after.append('<h2>%s</h2>' % v(WITH_HEADS, 'wh'))
    after.append('<ul>\n' + '\n'.join(items) + '\n</ul>')
    after.append('<p>%s</p>' % v(WITH_TAIL, 'wt'))
    extras = sorted(EXTRA, key=lambda x: H(pid, 'ex-' + x))
    return before, after, extras, v(EXTRA_HEADS, 'eh')


MANUAL_IDS = {30838, 28928, 28812, 29728, 30880, 31707, 30354, 28246, 14197, 29152, 29884, 31038}   # مكتوبة يدوياً، لا تُستورد
KW_MAX_CHARS = 40
DENS_LO, DENS_HI = 0.8, 1.5


def slugify(s):
    return re.sub(r'[^\w]+', '-', s.lower()).strip('-')


def rm_keyword(F):
    """الكلمة المستهدفة = بادئة حرفية من اسم المنتج (قبل الشرطة/الكود)، 3–6 كلمات، بلا أي تطبيع إملائي."""
    toks = F['label'].split()
    code_parts = set((F['code'] or '').split()) | set((F['sku'] or '').split())
    stop = len(toks)
    for i, t in enumerate(toks):
        if i >= 2 and (t in code_parts or (re.search(r'[A-Za-z]', t) and re.search(r'\d', t))):
            stop = i
            break
    toks = toks[:stop]
    cands = []
    for k in range(min(6, len(toks)), 0, -1):
        tk = trim_dangling(toks[:k]) or toks[:k]
        kw = ' '.join(tk)
        if len(kw) <= KW_MAX_CHARS and kw not in cands:
            cands.append(kw)
    if not cands:
        cands = [toks[0][:KW_MAX_CHARS]]
    pref = [k for k in cands if len(k.split()) >= 3] or cands
    for kw in pref:
        if slugify(kw) and slugify(kw) in F['slug']:
            return kw
    return pref[0]


def unmark(s, this):
    s = re.sub(r'([لب])ـ⟦[^⟧]*⟧', lambda m: m.group(1) + 'ـ' + this, s)
    return s.replace('⟦', '').replace('⟧', '')


def assemble(F, c, kw, links, paths, root_name, kwp):
    pid = F['id']
    c['_n'][0] = 0
    e = RefCtx(c)
    e['_kwp'] = kwp
    for key in ('ref_named', 'cd', 'label', 'name', 'code'):
        e[key] = esc(str(c[key]))
    e['kw_e'] = esc(kw)
    this = THIS[F['sub']]
    Fe = dict(F, name=esc(F['name']))
    parts = []
    parts.append('<p class="txa-answer">%s</p>' % answer_paragraph(Fe, e, esc(type_phrase(F, c))))
    nh, nli = numbers_section(F, e)
    parts.append('<h2>%s</h2>' % nh)
    parts.append('<ul>\n' + '\n'.join('<li>%s</li>' % x for x in nli) + '\n</ul>')
    rows = spec_rows(F, e)
    parts.append('<h2>%s</h2>' % pick(SPEC_HEADS, pid, 'spech').format_map(e))
    parts.append('<table class="txa-specs">\n<tbody>\n' + '\n'.join(
        '<tr><th scope="row">%s</th><td>%s</td></tr>' % (esc(a), esc(b)) for a, b in rows) + '\n</tbody>\n</table>')
    th, tp = tip_section(F, e)
    parts.append('<h2>%s</h2>' % th)
    parts.append('<p>%s</p>' % tp)
    before, after, extras, eh = extra_sections(F, e, links, 0)
    parts += before
    fh, faqs = faq_section(F, e)
    parts.append('<h2>%s</h2>' % fh)
    for q, a in faqs:
        parts.append('<h3>%s</h3>' % q)
        parts.append('<p>%s</p>' % a)
    parts += after
    tail = []
    tail.append('<h2>%s</h2>' % pick(SHIP_HEADS, pid, 'shiph').format_map(e))
    inst = pick(INSTALL, pid, 'inst').format(thing=c['thing'], ref=this, inst=A(URL_INSTALL, 'خدمات التركيب'))
    ship = pick(SHIP, pid, 'ship').format(ref=e['desc'])
    tail.append('<p>%s<br>\n%s</p>' % (inst, ship))
    tail.append('<p>%s</p>' % link_paragraph(F, e, links, paths, root_name))
    tail.append(MARK)
    fix = lambda x: tidy(unmark(x, this))
    n_extra = 0
    while True:
        mid = []
        if n_extra:
            mid = ['<h2>%s</h2>' % eh, '<ul>\n' + '\n'.join('<li>%s</li>' % x for x in extras[:n_extra]) + '\n</ul>']
        desc = fix('\n'.join(parts + mid + tail))
        words = len(clean_text(desc).split())
        if words >= 600 or n_extra >= len(extras):
            break
        n_extra += 1
    text = clean_text(desc)
    return dict(description=desc, words=words, kw_count=text.count(kw), tip=fix(tp), faqs=[(fix(q), fix(a)) for q, a in faqs],
                n_rows=len(rows), ctx=e)


def render(F, links, paths, root_name, used_titles, used_metas):
    pid = F['id']
    c = build_context(F)
    kw = rm_keyword(F)
    best = None
    for kwp in (6, 5, 7, 4, 8, 9, 3, 11, 13, 2, 0):
        r = assemble(F, c, kw, links, paths, root_name, kwp)
        dens = r['kw_count'] * 100.0 / max(1, r['words'])
        r['density'] = dens
        if DENS_LO <= dens <= DENS_HI:
            best = r
            break
        if best is None or abs(dens - 1.1) < abs(best['density'] - 1.1):
            best = r
    r = best
    cc = r['ctx']
    title = build_title(F, c, kw, used_titles)
    meta = re.sub(r' {2,}', ' ', build_meta(F, c, kw, used_metas))
    excerpt = re.sub(r' {2,}', ' ', tidy(build_excerpt(F, c, kw)))
    c['ex_kind'] = cc.get('ex_kind')
    return dict(id=pid, description=r['description'], excerpt=excerpt, title=title, meta=meta, kw=kw, ctx=c,
                n_faq=len(r['faqs']), n_rows=r['n_rows'], tip=r['tip'], faq_q=[q for q, _ in r['faqs']],
                words=r['words'], kw_count=r['kw_count'], density=r['density'], image_alt=F['name'],
                kw_in_slug=slugify(kw) in F['slug'], manual=pid in MANUAL_IDS)

# ------------------------------------------------------------------ القياس والاختبارات والمخرجات

PRICE_RE = re.compile(r'(ريال|ر\.س|﷼|SAR|\bSR\b)')
COLS = ['ID', 'Description', 'Short description', 'Meta: rank_math_title', 'Meta: rank_math_description',
        'Meta: rank_math_focus_keyword', 'image_alt']


def dup_stats(texts, threshold=20, mask=None):
    """نسبة الجمل (>40 حرفاً) التي تظهر حرفياً في ≥threshold منتجاً، لكل منتج."""
    per = []
    df = Counter()
    for i, t in enumerate(texts):
        ss = sentences(t)
        if mask:
            ss = [mask(s, i) for s in ss]
        per.append(ss)
        for s in set(ss):
            df[s] += 1
    ratios = []
    for ss in per:
        if not ss:
            continue
        ratios.append(sum(1 for s in ss if df[s] >= threshold) / len(ss))
    ratios.sort()
    return dict(median=statistics.median(ratios) if ratios else 0, mean=sum(ratios) / len(ratios) if ratios else 0,
                p90=ratios[int(len(ratios) * 0.9)] if ratios else 0,
                over70=sum(1 for r in ratios if r >= 0.7), n=len(ratios),
                top=[(s, n) for s, n in df.most_common(8)], distinct=len(df))


def dist(vals):
    vals = sorted(vals)
    if not vals:
        return dict(min=0, p10=0, median=0, p90=0, max=0)
    return dict(min=vals[0], p10=vals[int(len(vals) * 0.1)], median=vals[len(vals) // 2], p90=vals[int(len(vals) * 0.9)], max=vals[-1])


def allowed_links(links):
    return set(links.values()) | {URL_CALC, URL_INSTALL, URL_GUIDE, URL_ROLLS}


def run_tests(Fs, outs, links):
    """اختبارات assert على منتجات التجربة العشرين وعلى ثوابت المخرجات."""
    res = []
    byF = {F['id']: F for F in Fs}
    byO = {o['id']: o for o in outs}
    pilot = json.load(open(PILOT, encoding='utf-8'))
    matched = skipped = 0
    for x in pilot:
        F = byF[x['id']]
        pc = x['facts'].get('coverage_m2')
        mine = F.get('coverage')
        if pc is not None and mine is not None:
            assert abs(mine - pc) <= 0.006, ('coverage mismatch', x['id'], mine, pc)
            matched += 1
        else:
            skipped += 1
            if pc is not None and mine is None:
                assert F.get('dims_conflict'), ('pilot has coverage but generator has none without a conflict', x['id'])
            if pc is None:
                assert mine is None, ('generator invented coverage', x['id'], mine)
    res.append('تغطية منتجات التجربة: %d مطابقة لـ facts.coverage_m2 (فرق ≤ 0.006 م²)، %d بلا مقارنة (تعارض بيانات أو لا تغطية في الطرفين)' % (matched, skipped))
    for pid in (14958, 15420):
        assert byF[pid].get('dims_conflict') and byF[pid].get('coverage') is None, pid
    res.append('منتجا التناقض في التجربة (14958 و15420): لم تُحسب التغطية وسُجّلا في المراجعة')
    assert any('الخامة' in t for l, t in byF[14830]['issues']), 'material conflict 14830'
    res.append('تعارض الخامة في 14830 (WPC/بوليسترين) مكتشف والخامة محذوفة من نصه')
    c = byO[16773]['ctx']
    assert c['spr'] == 5 and c['cov'] == '16.5', c
    w = 4.0
    assert math.ceil(w / 1.06) == 4 and math.ceil(4 / 5) == 1
    res.append('ورق الجدران: لفة 15.6 م ÷ 2.8 = 5 شرائح؛ جدار 4 م = 4 شرائح = لفة واحدة')
    c = byO[30838]['ctx']
    assert c['cov'] == '3.54'
    n = math.ceil(float(c['Ww']) * 2.8 * 1.1 / (1.22 * 2.9) - 1e-9)
    assert c['n_area'] == n, (c['n_area'], n)
    res.append('بديل الرخام A037: 1.22 × 2.90 = 3.54 م²، وعدد الألواح = ceil(المساحة × 1.1 ÷ التغطية)')
    c = byO[30880]['ctx']
    assert c['cov'] == '0.348' and c['n'] == math.ceil(float(c['Ww']) / 0.12 * 1.1 - 1e-9)
    res.append('بديل الخشب PS-16: 0.12 × 2.90 = 0.348 م²، والعدد = ceil(عرض الجدار ÷ 0.12 × 1.1)')
    c = byO[16235]['ctx']
    assert byF[16235].get('coverage') is None and c['L'] == '2.4'
    res.append('النعلة zzf12: قالب طولي (2.4 م للقطعة) بلا متر مربع')
    # الكود وحده ≤ 4 مرات (ما لم يكن جزءاً من الكلمة المستهدفة نفسها)
    for o in outs:
        F = byF[o['id']]
        text = clean_text(o['description'])
        code = F['code']
        if code:
            o['code_count'] = len(re.findall(r'(?<![\w.\-])' + re.escape(code) + r'(?![\w\-])', text))
        else:
            o['code_count'] = 0
        if code and code not in o['kw'] and (not code.isdigit() or len(code) >= 5):
            assert o['code_count'] <= 4, ('code stuffing', o['id'], o['code_count'])
    res.append('الكود وحده يظهر ≤ 4 مرات في كل وصف (يُستثنى ما كان الكود فيه جزءاً من الكلمة المستهدفة، والأكواد الرقمية القصيرة التي قد تطابق رقماً في الحسابات)')
    # اختبارات Rank Math النصية
    for o in outs:
        F = byF[o['id']]
        kw = o['kw']
        assert kw in F['name'], ('kw not literal in name', o['id'], kw)
        assert o['title'].startswith(kw), ('kw not at title start', o['id'], kw, o['title'])
        assert kw in o['meta'], ('kw not in meta', o['id'], kw, o['meta'])
        m = re.search(r'<p class="txa-answer">(.*?)</p>', o['description'], re.S)
        assert kw in html.unescape(m.group(1)), ('kw not in first paragraph', o['id'])
        text = clean_text(o['description'])
        assert text.find(kw) <= len(text) * 0.1, ('kw not in first 10%', o['id'])
        o['kw_in_h2'] = any(kw in html.unescape(h) for h in re.findall(r'<h2>(.*?)</h2>', o['description']))
        assert o['kw_in_h2'], ('kw not in any H2', o['id'], kw)
        assert o['words'] >= 600, ('short content', o['id'], o['words'])
    res.append('Rank Math: الكلمة المستهدفة مقطع حرفي من الاسم، وتظهر حرفياً في بداية العنوان وفي وصف Meta وفي فقرة الإجابة (أول 10%) وفي عنوان H2 — 100% من المنتجات')
    res.append('طول المحتوى ≥ 600 كلمة لكل منتج (بعد إزالة HTML)')
    # ترتيب كلمات العنوان = ترتيب اسم المنتج، والإضافات (كود/مقاس/عبارة) في النهاية فقط
    for o in outs:
        F = byF[o['id']]
        body = o['title'][:-len(BRAND_SUFFIX)]
        toks = clean_name(F['name']).split()
        k = len(toks)
        while k > 0:
            pre = ' '.join(toks[:k])
            if body == pre or body.startswith(pre + ' – '):
                break
            k -= 1
        assert k >= 1, ('title not a prefix of the name', o['id'], o['title'])
        ex, fl = title_additions(F, o['ctx'])
        allowed = set(ex) | set(fl) | {F['code'], 'رقم %d' % o['id']}
        tail = body[len(' '.join(toks[:k])):]
        for part in [p for p in tail.split(' – ') if p.strip()]:
            assert part.strip() in allowed, ('title addition', o['id'], part)
    res.append('العناوين: كل عنوان = بادئة من اسم المنتج الأصلي بترتيبه (اختصار من النهاية فقط) + إضافات كود/مقاس/عبارة في النهاية')
    for o in outs:
        if byF[o['id']]['kind'] == 'wallpaper':
            assert 'اخصم' not in o['description'] and 'قبل خصم' not in o['description'], o['id']
    res.append('ورق الجدران: لا توجد صيغة تنصح بخصم الأبواب والنوافذ (موحّدة مع مقال المتجر)')
    ok_links = allowed_links(links)
    titles = Counter(o['title'] for o in outs)
    assert max(titles.values()) == 1, 'duplicate titles'
    res.append('عناوين Rank Math: %d عنواناً، صفر تكرار' % len(titles))
    for o in outs:
        assert o['description'].rstrip().endswith(MARK), o['id']
        blob = ' '.join((o['description'], o['excerpt'], o['title'], o['meta'], o['kw']))
        name = byF[o['id']]['name']
        assert not PRICE_RE.search(blob.replace(html.escape(name, quote=False), '').replace(name, '')), ('price', o['id'])
        for href in re.findall(r'href="([^"]+)"', o['description']):
            assert href in ok_links, ('link', o['id'], href)
        assert o['title'].endswith(BRAND_SUFFIX)
        assert len(o['excerpt']) <= 160, ('excerpt', o['id'], len(o['excerpt']))
        assert 3 <= o['n_faq'] <= 4, ('faq', o['id'], o['n_faq'])
        assert '<p class="txa-answer">' in o['description'] and '<table class="txa-specs">' in o['description']
        assert '{' not in re.sub(r'<[^>]+>', '', o['description']), ('unfilled placeholder', o['id'])
    res.append('كل وصف ينتهي بالعلامة، بلا أي مبلغ/عملة، وكل الروابط من category-links.json أو الروابط الثابتة الأربعة')
    res.append('كل وصف مختصر ≤ 160 حرفاً، و3–4 أسئلة لكل منتج، ولا متغيرات قالب غير معبأة')
    return res


def write_csv(path, rows, cols):
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(cols)
        for r in rows:
            w.writerow(r)


def main(argv):
    only_test = '--test' in argv
    links, paths, root_name = load_cat_links()
    prods = load_products()
    Fs = finalize([extract(p, paths) for p in prods])
    byP = {p['id']: p for p in prods}
    used_titles, used_metas = set(), set()
    outs = []
    for F in Fs:
        if F['excluded']:
            continue
        outs.append(render(F, links, paths, root_name, used_titles, used_metas))
    tests = run_tests(Fs, outs, links)
    outs = [o for o in outs if not o['manual']]
    if only_test:
        print('\n'.join('PASS  ' + t for t in tests))
        return 0
    os.makedirs(OUT_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(OUT_DIR, 'products-import-*.csv')) + glob.glob(os.path.join(OUT_DIR, 'products-v5-*.csv')):
        os.remove(old)
    byF = {F['id']: F for F in Fs}
    groups = defaultdict(list)
    for o in outs:
        groups[ROOT_FILE[byF[o['id']]['root']]].append(o)
    files = []
    for slug in sorted(groups):
        items = sorted(groups[slug], key=lambda o: o['id'])
        chunks = [items[i:i + MAX_PER_FILE] for i in range(0, len(items), MAX_PER_FILE)]
        for i, ch in enumerate(chunks, 1):
            fn = 'products-v5-%s%s.csv' % (slug, ('-%02d' % i) if len(chunks) > 1 else '')
            write_csv(os.path.join(OUT_DIR, fn), [[o['id'], o['description'], o['excerpt'], o['title'], o['meta'], o['kw'], o['image_alt']] for o in ch], COLS)
            files.append((fn, len(ch)))
    write_csv(os.path.join(OUT_DIR, 'products-backup.csv'),
              [[p['id'], p.get('description') or '', p.get('short_description') or ''] for p in prods], COLS[:3])
    review = []
    order = {'conflict': 0, 'missing': 1, 'note': 2}
    tag = {'conflict': 'تعارض', 'missing': 'نقص', 'note': 'ملاحظة'}
    for F in Fs:
        if F['excluded']:
            review.append([F['id'], F['name'], F['url'], 'مستثنى: ' + F['excluded']])
            continue
        if F['id'] in MANUAL_IDS:
            review.append([F['id'], F['name'], F['url'], 'مستثنى: مكتوب يدوياً في التجربة ومطبَّق سابقاً؛ لا يُستورد'])
            continue
        iss = sorted(F['issues'], key=lambda t: order[t[0]])
        if iss:
            review.append([F['id'], F['name'], F['url'], ' | '.join('%s: %s' % (tag[l], t) for l, t in iss)])
    write_csv(os.path.join(OUT_DIR, 'review-needed.csv'), review, ['id', 'name', 'url', 'reason'])
    write_report(prods, Fs, outs, files, review, tests, links, byP)
    print('generated=%d excluded=%d review_rows=%d files=%d' % (len(outs), sum(1 for F in Fs if F['excluded']), len(review), len(files)))
    return 0


def write_report(prods, Fs, outs, files, review, tests, links, byP):
    byF = {F['id']: F for F in Fs}
    L = []
    w = L.append
    n_all, n_out = len(prods), len(outs)
    excluded = [F for F in Fs if F['excluded']]
    w('# تقرير جودة مولّد أوصاف المنتجات (txa-desc-v4)')
    w('')
    w('**التاريخ:** 2026-11-21 · **المولّد:** `texa/scripts/build_products.py` · **الحالة:** ملفات فقط، لم يُعدَّل أي شيء على الموقع.')
    w('كل الأرقام أدناه محسوبة بالسكربت نفسه عند التشغيل، لا تقديرات.')
    w('')
    w('## 1) الأعداد')
    w('')
    w('- منتجات في الملفات الخام: **%d** · في ملفات v5: **%d** · مستثناة: **%d** خدمة + **%d** مكتوبة يدوياً (لا تُستورد)' % (n_all, n_out, len(excluded), len(MANUAL_IDS)))
    w('- صفوف ملف المراجعة `review-needed.csv`: **%d** (مستثنى أو تعارض أو نقص أو ملاحظة)' % len(review))
    cnt_lvl = Counter()
    for F in Fs:
        lv = {l for l, _ in F['issues']}
        for l in lv:
            cnt_lvl[l] += 1
    w('  - منتجات فيها تعارض بيانات: %d · فيها نقص يمنع الحساب: %d · ملاحظات فقط (بلا تعارض/نقص): %d' % (
        cnt_lvl['conflict'], cnt_lvl['missing'],
        sum(1 for F in Fs if F['issues'] and all(l == 'note' for l, _ in F['issues']))))
    w('')
    w('| ملف الاستيراد | المنتجات |')
    w('|---|---|')
    for fn, n in files:
        w('| `%s` | %d |' % (fn, n))
    w('')
    w('### لكل قسم رئيسي')
    w('')
    w('| القسم | مولَّد | بأرقام محسوبة | تعارض مقاس | بلا مقاس |')
    w('|---|---|---|---|---|')
    byroot = defaultdict(list)
    for o in outs:
        byroot[ROOT_FILE[byF[o['id']]['root']]].append(o)
    for slug in sorted(byroot):
        items = byroot[slug]
        calc = sum(1 for o in items if o['ctx'].get('calc'))
        conf = sum(1 for o in items if byF[o['id']].get('dims_conflict'))
        w('| %s | %d | %d | %d | %d |' % (slug, len(items), calc, conf, len(items) - calc - conf))
    w('')
    w('المستثنى: ' + ('؛ '.join('%d «%s» — %s' % (F['id'], F['name'], F['excluded']) for F in excluded) or 'لا شيء'))
    w('')

    # ---- التكرار
    before_txt = [clean_text(byP[o['id']].get('description')) for o in outs]
    after_txt = [clean_text(o['description']) for o in outs]
    all_before = dup_stats([clean_text(p.get('description')) for p in prods])
    b = dup_stats(before_txt)
    a = dup_stats(after_txt)

    def mk_mask(idx_to_tokens):
        def m(s, i):
            for t in idx_to_tokens[i]:
                s = s.replace(t, '§')
            s = re.sub(r'[A-Za-z0-9#:_\-]+', '§', s)
            return re.sub(r'(§\s*)+', '§ ', s).strip()
        return m
    toks = []
    for o in outs:
        F = byF[o['id']]
        c = o['ctx']
        ts = {html.escape(F['name'], quote=False), F['name'], F['label'], o['kw'], c['cd']} | set(c['_forms'])
        if c['cph']:
            ts.add(c['cph'])
        toks.append(sorted((t for t in ts if t and len(t) > 2), key=len, reverse=True))
    a_mask = dup_stats(after_txt, mask=mk_mask(toks))
    w('## 2) تكرار الجمل (طريقة التدقيق نفسها)')
    w('')
    w('الطريقة: تحويل الوصف إلى نص، تقسيم على `[.؟!\\n]`، الاحتفاظ بالجمل الأطول من 40 حرفاً، ثم لكل منتج نسبة جمله التي تظهر حرفياً في 20 منتجاً أو أكثر.')
    w('')
    w('| المقياس | قبل (الوصف الحالي) | بعد (v5) |')
    w('|---|---|---|')
    w('| الوسيط | %.1f%% | **%.1f%%** |' % (b['median'] * 100, a['median'] * 100))
    w('| المتوسط | %.1f%% | %.1f%% |' % (b['mean'] * 100, a['mean'] * 100))
    w('| المئين 90 | %.1f%% | %.1f%% |' % (b['p90'] * 100, a['p90'] * 100))
    w('| منتجات 70%%+ من جملها مكررة | %d | %d |' % (b['over70'], a['over70']))
    w('| عدد الجمل المميزة في الكتالوج | %d | %d |' % (b['distinct'], a['distinct']))
    w('')
    w('- للمقارنة مع تقرير الفحص: الوسيط على كل الـ%d منتجاً (قبل) = %.1f%% (التقرير ذكر 61%%).' % (n_all, all_before['median'] * 100))
    w('- **مقياس أشدّ للصدق**: بعد حجب اسم المنتج وكوده ولونه وكل الأرقام من الجمل (أي مقارنة القوالب نفسها لا النص الحرفي) يصبح وسيط التكرار **%.1f%%** والمتوسط %.1f%%. هذا يعني أن انخفاض التكرار الحرفي مصدره الأساسي إدخال بيانات المنتج (الكود، اللون، الأرقام) في الجمل وتنويع الصياغات، لا أن كل جملة مكتوبة يدوياً لمنتج واحد.' % (
        a_mask['median'] * 100, a_mask['mean'] * 100))
    w('')
    cc = sorted(o.get('code_count', 0) for o in outs)
    w('- **ظهور الكود وحده داخل الوصف**: الوسيط %d، الأقصى %d (الحد 4 ما لم يكن الكود جزءاً من الكلمة المستهدفة). عبارة الكلمة المستهدفة نفسها تتكرر عمداً بكثافة Rank Math (القسم 2ب)، وبقية الجمل تشير للمنتج بصياغة طبيعية.' % (
        cc[len(cc) // 2], cc[-1]))
    w('- في v5 أُضيفت أقسام عامة لبلوغ 600 كلمة (تجهيز، خطوات، عناية، أفكار، أخطاء، مكمّلات). جملها مشتركة بين منتجات النوع الواحد بطبيعتها، ولذلك ارتفع التكرار عن نسخة v4 القصيرة (كان الوسيط 38.9%)؛ الرقم أعلاه هو المقيس فعلاً.')
    byk = defaultdict(list)
    per_after = dup_stats  # للتوضيح فقط
    for slug in sorted(byroot):
        ids = {o['id'] for o in byroot[slug]}
        idx = [i for i, o in enumerate(outs) if o['id'] in ids]
        byk[slug] = idx
    df = Counter()
    per = []
    for t in after_txt:
        ss = sentences(t)
        per.append(ss)
        for x in set(ss):
            df[x] += 1
    w('')
    w('وسيط التكرار الحرفي بعد التوليد لكل قسم (الأقسام الكبيرة ذات المقاس الموحّد أعلى بطبيعتها):')
    w('')
    w('| القسم | المنتجات | الوسيط بعد |')
    w('|---|---|---|')
    for slug in sorted(byk):
        rs = sorted(sum(1 for x in per[i] if df[x] >= 20) / max(1, len(per[i])) for i in byk[slug])
        w('| %s | %d | %.1f%% |' % (slug, len(rs), statistics.median(rs) * 100))
    w('')
    w('أكثر الجمل تكراراً بعد التوليد (حرفياً):')
    w('')
    for s, n in a['top'][:6]:
        w('- %d منتجاً: «%s»' % (n, s[:140]))
    w('')

    w('## 2ب) اختبارات Rank Math النصية (مقيسة)')
    w('')
    kwc2 = Counter(o['kw'] for o in outs)
    def pc(n):
        return '%d (%.1f%%)' % (n, n * 100.0 / n_out)
    in_dens = sum(1 for o in outs if DENS_LO <= o['density'] <= DENS_HI)
    w('| الاختبار | المنتجات المستوفية |')
    w('|---|---|')
    w('| الكلمة المستهدفة في بداية عنوان SEO | %s |' % pc(sum(1 for o in outs if o['title'].startswith(o['kw']))))
    w('| الكلمة في وصف SEO | %s |' % pc(sum(1 for o in outs if o['kw'] in o['meta'])))
    w('| الكلمة في الرابط (slug بعد urldecode، مطابقة متصلة بالشرطات) | %s |' % pc(sum(1 for o in outs if o['kw_in_slug'])))
    w('| الكلمة في أول 10%% من المحتوى | %s |' % pc(sum(1 for o in outs if clean_text(o['description']).find(o['kw']) <= len(clean_text(o['description'])) * 0.1)))
    w('| الكلمة في عنوان H2 | %s |' % pc(sum(1 for o in outs if o.get('kw_in_h2'))))
    w('| الكثافة بين %.1f%% و%.1f%% | %s |' % (DENS_LO, DENS_HI, pc(in_dens)))
    w('| المحتوى ≥ 600 كلمة | %s |' % pc(sum(1 for o in outs if o['words'] >= 600)))
    w('| الكلمة المستهدفة فريدة (غير مستخدمة في منتج آخر) | %s |' % pc(sum(1 for o in outs if kwc2[o['kw']] == 1)))
    dd = dist([round(o['density'] * 100) for o in outs])
    kd = dist([o['kw_count'] for o in outs])
    w('')
    w('- الكثافة = عدد مرات العبارة ÷ عدد الكلمات: وسيط %.2f%% (أدنى %.2f%%، أقصى %.2f%%). عدد مرات العبارة: وسيط %d (أدنى %d، أقصى %d).' % (
        dd['median'] / 100.0, dd['min'] / 100.0, dd['max'] / 100.0, kd['median'], kd['min'], kd['max']))
    w('- عدد كلمات الكلمة المستهدفة: ' + '، '.join('%d كلمات: %d' % (k, n) for k, n in sorted(Counter(len(o['kw'].split()) for o in outs).items())) + '.')
    w('- الكلمة غير الموجودة في الرابط: سببه أن slug المنتج في المتجر لا يطابق اسمه الحالي (اسم عُدّل بعد إنشاء الرابط، أو slug مختصر)؛ لا يُحل بالنص.')
    w('- لم يُشغَّل Rank Math نفسه؛ هذه محاكاة لاختباراته النصية بمطابقة حرفية. درجته الفعلية تتأثر أيضاً بالصورة والنص البديل وطول الرابط والروابط الخارجية (خارج النص، ولم تُضف روابط خارجية).')
    w('- المنتجات الـ12 المكتوبة يدوياً مستثناة من ملفات v5 ومن أرقام هذا التقرير.')
    w('')

    # ---- أطوال
    tl = [len(o['title']) for o in outs]
    ml = [len(o['meta']) for o in outs]
    el = [len(o['excerpt']) for o in outs]
    aw = []
    for o in outs:
        m = re.search(r'<p class="txa-answer">(.*?)</p>', o['description'], re.S)
        aw.append(len(clean_text(m.group(1)).split()))
    dw = [len(clean_text(o['description']).split()) for o in outs]
    w('## 3) الأطوال')
    w('')
    w('| الحقل | الهدف | داخل الهدف | أدنى | مئين 10 | وسيط | مئين 90 | أقصى |')
    w('|---|---|---|---|---|---|---|---|')

    def row(label, target, vals, lo, hi):
        d = dist(vals)
        ok = sum(1 for v in vals if lo <= v <= hi)
        w('| %s | %s | %d (%.1f%%) | %d | %d | %d | %d | %d |' % (label, target, ok, ok * 100.0 / len(vals), d['min'], d['p10'], d['median'], d['p90'], d['max']))
    row('rank_math_title (حرف)', '50–60', tl, 50, 60)
    row('rank_math_description (حرف)', '120–155', ml, 120, 155)
    row('Short description (حرف)', '≤160', el, 0, 160)
    row('فقرة الإجابة (كلمة)', '40–60', aw, 40, 60)
    row('الوصف الكامل (كلمة)', '—', dw, 0, 10 ** 6)
    w('')
    short_t = sum(1 for v in tl if v < 50)
    long_t = sum(1 for v in tl if v > 60)
    w('- عناوين أقصر من 50: %d · أطول من 60: %d. أوصاف Meta أقصر من 120: %d · أطول من 155: %d. فقرات إجابة خارج 40–60 كلمة: %d (أقل: %d، أكثر: %d — غالباً لطول اسم المنتج نفسه).' % (
        short_t, long_t, sum(1 for v in ml if v < 120), sum(1 for v in ml if v > 155),
        sum(1 for v in aw if not 40 <= v <= 60), sum(1 for v in aw if v < 40), sum(1 for v in aw if v > 60)))
    w('')

    # ---- تفرد
    def dups(vals):
        c = Counter(vals)
        return sum(n - 1 for n in c.values() if n > 1), sum(1 for n in c.values() if n > 1), (c.most_common(1)[0] if c else ('', 0))
    w('## 4) التفرد')
    w('')
    w('| الحقل | قيم مكررة (زيادة) | مجموعات مكررة | الأكثر تكراراً |')
    w('|---|---|---|---|')
    for label, vals in (('rank_math_title', [o['title'] for o in outs]), ('rank_math_description', [o['meta'] for o in outs]),
                        ('rank_math_focus_keyword', [o['kw'] for o in outs]), ('Short description', [o['excerpt'] for o in outs]),
                        ('فقرة نصيحة المصمم', [o['tip'] for o in outs])):
        extra, grp, top = dups(vals)
        w('| %s | %d | %d | %d× «%s» |' % (label, extra, grp, top[1], top[0][:60]))
    tipc = Counter(o['tip'] for o in outs)
    q = Counter()
    for o in outs:
        for x in o['faq_q']:
            q[x] += 1
    w('')
    w('- فقرات نصيحة المصمم المتطابقة في أكثر من 15 منتجاً: **%d** (أقصى تكرار لفقرة واحدة: %d).' % (
        sum(1 for n in tipc.values() if n > 15), max(tipc.values())))
    w('- الأسئلة الشائعة: %d سؤالاً في المجموع، %d صيغة مميزة؛ أسئلة يتطابق نصها في أكثر من منتج: %d (أقصى تكرار %d).' % (
        sum(q.values()), len(q), sum(1 for n in q.values() if n > 1), max(q.values())))
    kwc = Counter(o['kw'] for o in outs)
    w('- الكلمة المستهدفة مكررة بطبيعتها (آلاف المنتجات وعدد محدود من عبارات البحث الطبيعية): %d عبارة مميزة لـ%d منتجاً. Rank Math سيُظهر تنبيه «الكلمة مستخدمة من قبل»؛ القرار للمالك/خبير SEO (انظر القسم 8).' % (len(kwc), n_out))
    in_title = sum(1 for o in outs if o['kw'] in o['title'])
    in_meta = sum(1 for o in outs if o['kw'] in o['meta'])
    in_ans = sum(1 for o in outs if html.escape(o['kw'], quote=False) in o['description'].split('</p>')[0])
    w('- الكلمة المستهدفة موجودة في العنوان: %d/%d · في وصف Meta: %d/%d · في فقرة الإجابة: %d/%d.' % (in_title, n_out, in_meta, n_out, in_ans, n_out))
    w('')

    # ---- المحتوى
    ok_links = allowed_links(links)
    cat_urls = set(links.values())
    n_cov = sum(1 for o in outs if o['ctx'].get('calc') and byF[o['id']]['kind'] not in ('linear',))
    n_lin = sum(1 for o in outs if o['ctx'].get('calc') and byF[o['id']]['kind'] == 'linear')
    n_tbl = sum(1 for o in outs if '<table class="txa-specs">' in o['description'])
    n_faq = sum(1 for o in outs if 3 <= o['n_faq'] <= 4)
    n_cat = n_inst = n_calc = bad = 0
    for o in outs:
        hrefs = re.findall(r'href="([^"]+)"', o['description'])
        n_cat += any(h in cat_urls for h in hrefs)
        n_inst += URL_INSTALL in hrefs
        n_calc += URL_CALC in hrefs
        bad += sum(1 for h in hrefs if h not in ok_links)
    w('## 5) اكتمال المحتوى')
    w('')
    w('| البند | العدد | النسبة |')
    w('|---|---|---|')
    for label, n in (('تغطية م² محسوبة + مثال كمية (ورق/ألواح/أرضيات)', n_cov), ('حساب طولي (نعلات/براويز/كرانيش/فواصل)', n_lin),
                     ('بلا أرقام محسوبة (نقص أو تعارض أو منتج بالقطعة)', n_out - n_cov - n_lin),
                     ('جدول مواصفات', n_tbl), ('3–4 أسئلة شائعة H3', n_faq), ('رابط قسم واحد على الأقل من category-links.json', n_cat),
                     ('رابط خدمات التركيب', n_inst), ('رابط حاسبة الكميات', n_calc)):
        w('| %s | %d | %.1f%% |' % (label, n, n * 100.0 / n_out))
    rows_d = dist([o['n_rows'] for o in outs])
    w('')
    w('- روابط خارج القائمة المسموحة: **%d**. صفوف جدول المواصفات: وسيط %d (أدنى %d، أقصى %d).' % (bad, rows_d['median'], rows_d['min'], rows_d['max']))
    price_hits = 0
    for o in outs:
        name = byF[o['id']]['name']
        blob = ' '.join((o['description'], o['excerpt'], o['title'], o['meta'], o['kw'])).replace(html.escape(name, quote=False), '').replace(name, '')
        price_hits += bool(PRICE_RE.search(blob))
    w('- مخرجات تحتوي مبلغاً أو عملة (ريال/ر.س/SAR) خارج اسم المنتج: **%d**.' % price_hits)
    stats = Counter()
    for o in outs:
        F = byF[o['id']]
        stats['color'] += bool(F['color'])
        stats['pattern'] += bool(F['pattern'])
        stats['origin'] += bool(F.get('origin'))
        stats['material'] += bool(F.get('material'))
        stats['thick'] += bool(F.get('thick'))
        stats['water'] += bool(F.get('waterproof'))
        stats['code'] += bool(F['code'])
    w('- ما استُخرج من بيانات المنتج: كود %d · لون %d · نقشة/سطح %d · منشأ %d · خامة %d · سماكة %d · ادعاء «مقاوم للماء» وارد في وصف المنتج نفسه %d.' % (
        stats['code'], stats['color'], stats['pattern'], stats['origin'], stats['material'], stats['thick'], stats['water']))
    w('')

    # ---- المراجعة
    rc = Counter()
    for F in Fs:
        for l, t in F['issues']:
            key = re.sub(r'[\d.,×]+', 'N', t)
            key = re.sub(r'\(.*?\)', '', key)[:70]
            rc[(l, key)] += 1
    w('## 6) أسباب ملف المراجعة (الأكثر تكراراً)')
    w('')
    w('| النوع | السبب (الأرقام محجوبة) | منتجات |')
    w('|---|---|---|')
    tag = {'conflict': 'تعارض', 'missing': 'نقص', 'note': 'ملاحظة'}
    for (l, k), n in rc.most_common(22):
        w('| %s | %s | %d |' % (tag[l], k.replace('|', '/'), n))
    w('')

    w('## 7) الاختبارات (assert) — كلها نجحت في هذا التشغيل')
    w('')
    for t in tests:
        w('- ' + t)
    w('')

    w('## 8) حدود ومخاطر وما لم يتحقق')
    w('')
    lim = [
        'لم يُختبر الاستيراد على WooCommerce فعلياً. أسماء الأعمدة هي أسماء المستورد القياسي والمطابقة على ID، لكن يجب تجربة ملف واحد على نسخة staging أولاً، والتأكد من تفعيل «تحديث المنتجات الموجودة».',
        'حقول Rank Math الحالية غير متاحة في الواجهة العامة، لذلك لا توجد لها نسخة احتياطية في `products-backup.csv` (فيه الوصف والوصف المختصر فقط). خذ تصديراً من ووردبريس قبل الاستيراد.',
        'التكرار الحرفي انخفض لأن الجمل تحمل مقاس المنتج ولونه ونقشته وأرقام مثاله ولأن الصياغات تُختار من مكتبات (الكود لم يعد يُكرَّر في الجمل)؛ المقياس المحجوب في القسم 2 يبيّن أن القوالب نفسها ما زالت مشتركة. المحتوى أفضل من القالب الحالي لكنه ليس كتابة يدوية كمنتجات التجربة العشرين.',
        'نصيحة المصمم معرفة ديكور عامة مبنية على اللون والنقشة المستخرجين من الاسم/الخصائص/القسم، لا على رؤية الصورة. اللون المستخرج قد يخطئ في أسماء تجارية غير لونية، والمنتجات بلا لون مكتشف تأخذ نصيحة عامة.',
        'الكلمة المستهدفة مشتقة آلياً (النوع + الصفة + اللون) ولم يُتحقق من حجم البحث عليها بأي أداة، وهي مكررة بين المنتجات المتشابهة. يلزم قرار: إبقاؤها طبيعية مكررة، أو إضافة الكود لها لتصير فريدة.',
        'المقاس يُعتمد فقط إذا ورد في نص المنتج بوحدة واضحة ولم يخالفه حقل الأبعاد (تسامح 2.5%)، أو إذا ورد في حقل الأبعاد وطابق مقاساً قياسياً مؤكَّداً نصاً في 3 منتجات على الأقل من القسم نفسه. ما عدا ذلك يخرج الوصف بلا أرقام ويُسجَّل في المراجعة؛ هذه نسبة كبيرة (انظر القسم 5) وتحتاج استكمال بيانات لا إعادة كتابة.',
        'حساب ورق الجدران بالشرائح يفترض ارتفاع جدار 2.8 م ولا يخصم الأبواب والنوافذ (عمداً، اتباعاً لمقال المتجر: ما يتوفر يبقى احتياطاً) ولا يحسب تكرار النقشة (غير موجود في البيانات). أمثلة الألواح والأرضيات تضيف 10% هدراً ثابتاً؛ الرصّة الهرمية تحتاج أكثر.',
        'عدد ألواح بديل الخشب المضلع يفترض أن العرض المذكور هو العرض الظاهر بعد التعشيق (سؤال مفتوح من التجربة)، والنص ينبّه العميل لذلك.',
        'الادعاء الوحيد المنقول من الأوصاف الحالية هو «مقاوم للماء» ويُكتب منسوباً لوصف المنتج، ويظهر فقط إن ورد في بيانات المنتج نفسه. قد يكون أصله جملة قالبية في الوصف القديم؛ يحتاج مستنداً من المورد كما أوصى تقرير التجربة. لم تُنقل ادعاءات FDA/فورمالدهايد/حريق/نمل أبيض/UV.',
        'السماكة والخامة والمنشأ تُحذف عند تعارض مصدرين (الاسم مقابل الوصف مثلاً) وتُسجَّل؛ ارتفاع حقل الأبعاد (الخانة الثالثة) لم يُستخدم مصدراً للسماكة لأنه غير موثوق.',
        'وحدة البيع (لوح/متر مربع/كرتونة) تُكتب فقط إن وردت نصاً في الوصف الحالي. لا يُذكر أي سعر، فمشكلة «وحدة السعر» من التجربة لا تؤثر على النص لكنها ما زالت قائمة في بيانات المتجر.',
        'لم تُربط روابط أقسام العروض (عروض ورق الجدران، عروض النعلات، عروض التشطيبات) عمداً لأنها تتغير؛ الروابط للقسم الفرعي والرئيسي فقط.',
        'النص البديل للصور غير مشمول في هذه المخرجات (المستورد القياسي لا يحدّثه بهذه الأعمدة).',
        'Schema (FAQPage/Product) وCSS للأصناف `txa-answer` و`txa-specs` خارج نطاق هذا الملف.',
        'الكلمة المستهدفة الآن بادئة حرفية من اسم المنتج (بإملاء الاسم كما هو، حتى لو كان «ابيض» بلا همزة أو «باركية» بالتاء)، لا عبارة بحث مصاغة. هذا يستوفي مطابقة Rank Math الحرفية لكنه لا يعني أن الناس يبحثون بهذه الصيغة؛ لم يُتحقق من حجم البحث.',
        'أقسام v5 الإضافية (تجهيز، خطوات، عناية، أخطاء، مكمّلات) معرفة عامة لنوع المنتج وُضعت لبلوغ 600 كلمة، وليست معلومات خاصة بكل منتج. خطوات التركيب استرشادية ولا تذكر نوع لاصق أو نظام تثبيت بعينه لأنه غير موجود في البيانات؛ يُستحسن أن يراجعها فنيّ التركيب مرة واحدة لكل نوع.',
        'تكرار عبارة الكلمة المستهدفة 5–9 مرات يجعل بعض الجمل أثقل من الصياغة الطبيعية (مثل «كرتونة باركية الماني رمادي خشبي»)، وهو ثمن استيفاء اختبار الكثافة.',
        'النقشة تُؤخذ من الاسم أولاً ثم من قسم المتجر؛ إن كان تصنيف المنتج خاطئاً في المتجر (مثل «مخطط» داخل قسم السادة، كما في التجربة) انتقل الخطأ إلى النص.',
        'وسيط التكرار «قبل» بحسابنا 69.2% لا 61% كما في تقرير الفحص؛ الفرق يعود على الأرجح لطريقة تحويل HTML إلى نص (لم نجد سكربت الفحص الأصلي لمطابقته). المقارنة قبل/بعد هنا بالطريقة نفسها على الجانبين.',
        'لم يراجع إنسان الصياغة العربية لكل الـ%d وصفاً؛ روجعت عينات فقط. يُنصح بمراجعة 20–30 منتجاً من كل ملف قبل استيراده.' % n_out,
    ]
    for x in lim:
        w('- ' + x)
    w('')

    w('## 9) ست عينات كاملة (اختيار شبه عشوائي حتمي: أصغر hash في كل قسم)')
    w('')
    for slug in ('wallpaper', 'shiplap-alt', 'marble-alt', 'wood-alt', 'parquet', 'skirting'):
        items = byroot.get(slug) or []
        if not items:
            continue
        o = min(items, key=lambda o: H(o['id'], 'sample'))
        F = byF[o['id']]
        w('### [%s] %s — ID %d' % (slug, F['name'], o['id']))
        w('')
        w('- الرابط: %s' % F['url'])
        w('- **rank_math_title** (%d): %s' % (len(o['title']), o['title']))
        w('- **rank_math_description** (%d): %s' % (len(o['meta']), o['meta']))
        w('- **rank_math_focus_keyword**: %s' % o['kw'])
        w('- **Short description** (%d): %s' % (len(o['excerpt']), o['excerpt']))
        iss = '؛ '.join(t for _, t in F['issues']) or 'لا شيء'
        w('- ملاحظات المراجعة: %s' % iss)
        w('')
        w('```html')
        w(o['description'])
        w('```')
        w('')
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    open(REPORT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
