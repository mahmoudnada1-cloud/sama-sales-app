# -*- coding: utf-8 -*-
"""2026-11-22: make the three wallpaper articles match the quantity calculator.

Calculator rule (source of truth, /quantity-calculator/):
  strips per wall  = ceil(width x 1.07 / 1.06)          (7% cutting waste)
  strips per roll  = floor(15.6 / (height + 0.10))       (5 up to 3.0 m, 4 above that up to 3.8 m)
  rolls per wall   = ceil(strips / strips per roll)
  room             = each wall separately, then summed; small doors/windows not deducted

Input : data/backup/post-<id>-before-calc-rule.json (verified copies of the live posts)
        data/live-after/p*.json (current prices) + data/products-slim.json (which 1,296 ids
        state the 15.6 m x 106 cm size on their own page; later descriptions repeat that size
        as family text, so the size test must use the original descriptions)
Output: content/article-1.json, content/article-3.json, content/article-rolls-table.json
        data/out/calc-rule-patch.json (changed blocks, used to update the live posts block by block)
build_articles.py still encodes the OLD rule and old prices: do not republish its output.
"""
import json, re, glob, math, hashlib, collections, statistics as st
B = '/home/user/sama-sales-app/texa/'
sha = lambda s: hashlib.sha1(s.encode()).hexdigest()
n = lambda x: f'{x:,}'

# ---------- calculator
def strips(w): return math.ceil(round(w * 1.07 / 1.06, 6))
def per_roll(h): return math.floor(round(15.6 / (h + 0.10), 6))
def wall(w, h=3.0): return math.ceil(strips(w) / per_roll(h))
def room(a, b, h=3.0): return 2 * wall(a, h) + 2 * wall(b, h)
assert per_roll(2.8) == per_roll(3.0) == 5 and per_roll(3.05) == per_roll(3.2) == per_roll(3.8) == 4 and per_roll(3.81) == 3
assert [wall(w) for w in (3, 4, 4.9, 5, 6)] == [1, 1, 1, 2, 2]
assert [room(*r) for r in ((3, 4), (4, 4), (4, 5), (5, 6))] == [4, 4, 6, 8]
assert wall(4.95) == 1 and wall(4.96) == 2          # one roll covers a wall up to 4.95 m -> "حتى 4.9 م"

# ---------- block helpers (same serialisation as the live posts)
def P(h): return f'<!-- wp:paragraph -->\n<p>{h}</p>\n<!-- /wp:paragraph -->'
def TB(head, rows):
    th = ''.join(f'<th>{c}</th>' for c in head)
    tb = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<!-- wp:table -->\n<figure class="wp-block-table"><table><thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></figure>\n<!-- /wp:table -->'
def LI(items, ordered=False, sep=''):
    tag = 'ol' if ordered else 'ul'
    at = ' {"ordered":true}' if ordered else ''
    li = sep.join(f'<!-- wp:list-item -->\n<li>{i}</li>\n<!-- /wp:list-item -->' for i in items)
    return f'<!-- wp:list{at} -->\n<{tag} class="wp-block-list">{li}</{tag}>\n<!-- /wp:list -->'
def blocks(content): return re.split(r'\n\n(?=<!-- wp:(?!list-item))', content)
def sub(block, old, new):
    assert block.count(old) == 1, old
    return block.replace(old, new)
CALC = 'https://texadecore.store/quantity-calculator/'

# ---------- current prices
live = {}
for f in glob.glob(B + 'data/live-after/p*.json'):
    for p in json.load(open(f)): live[p['id']] = p
slim = json.load(open(B + 'data/products-slim.json'))
To = lambda p: p['name'] + ' ' + p['short'] + ' ' + p['desc']
wp = [p for p in slim if 'ورق جدران' in p['cats']]
std_ids = [p['id'] for p in wp if re.search(r'15[.,]6', To(p)) and '106' in To(p)]
assert len(wp) == 1391 and len(std_ids) == 1296
assert sum('ورق جدران' in [c['name'] for c in p['categories']] for p in live.values()) == 1391
std = [live[i] for i in std_ids]
PR = lambda p: int(p['prices']['price']); CN = lambda p: [c['name'] for c in p['categories']]
pr = [PR(p) for p in std]
LO, HI, MED = min(pr), max(pr), int(st.median(pr))
assert (LO, HI, MED) == (75, 229, 179)
allpr = [PR(p) for p in live.values() if 'ورق جدران' in CN(p)]; assert (min(allpr), max(allpr)) == (75, 229)
cnt = collections.Counter(pr)
N75 = cnt[75]; assert N75 == 255 and cnt[99] == 0 and cnt[179] + cnt[189] == 523
assert (round(LO / 16.5, 1), round(HI / 16.5, 1)) == (4.5, 13.9)

out = {}
def finish(pid, old_blocks, new_blocks, extra):
    ch = [dict(index=i, old_hash=sha(a), new_hash=sha(b), old=a, new=b) for i, (a, b) in enumerate(zip(old_blocks, new_blocks)) if a != b]
    content = '\n\n'.join(new_blocks)
    assert len(old_blocks) == len(new_blocks)
    assert len(re.findall(r'<!-- wp:', content)) == len(re.findall(r'<!-- /wp:', content))
    assert '—' not in content
    out[pid] = dict(content_hash=sha(content), changed=ch, **extra)
    return content

# ================= 35055 rolls table
bk = json.load(open(B + 'data/backup/post-35055-before-calc-rule.json'))
ob = blocks(bk['content']); assert len(ob) == 26
nb = list(ob)
nb[0] = sub(ob[0], 'الجدار الواحد حتى عرض 5 أمتار يكفيه <strong>رول واحد</strong>.', 'الجدار الواحد حتى عرض 4.9 م يكفيه <strong>رول واحد</strong>، وجدار بعرض 5 م يحتاج رولين.')
nb[2] = P(f'الأرقام محسوبة بطريقة <a href="{CALC}">حاسبة الكميات</a> لرول مقاسه 15.6 م × 106 سم، وهو مقاس أغلب ورق الجدران الكوري في تكسا ديكور: كل جدار يُحسب على حدة مع هدر قص 7%، ثم تُجمع رولات الجدران. الأبواب والنوافذ الصغيرة لا تُخصم حتى يبقى معك احتياط للقص.')
rooms = [(3, 3, ''), (3, 4, ''), (4, 4, ''), (4, 5, ''), (5, 5, ''), (5, 6, ''), (6, 8, ' (مجلس)')]
nb[3] = TB(['مقاس الغرفة', 'شرائح كل جدار', 'الرولات (ارتفاع حتى 3 م)', 'الرولات (ارتفاع فوق 3 م حتى 3.8 م)'],
           [[f'{a} × {b} م{t}', ' + '.join(str(strips(x)) for x in (a, a, b, b)), str(room(a, b, 3.0)), str(room(a, b, 3.2))] for a, b, t in rooms])
nb[5] = TB(['عرض الجدار', 'عدد الشرائح', 'الرولات (ارتفاع حتى 3 م)'], [[f'{w} م', str(strips(w)), str(wall(w))] for w in (2, 3, 4, 5, 6)])
nb[7] = LI([
 '<strong>احسب شرائح كل جدار على حدة:</strong> اضرب عرض الجدار بالمتر في 1.07 (هدر قص 7%) واقسم الناتج على 1.06 (عرض الرول)، ثم قرّب للأعلى.',
 '<strong>احسب كم شريحة يعطيك الرول:</strong> أضف 10 سم إلى ارتفاع الجدار هامشاً للقص، ثم اقسم 15.6 على الناتج وقرّب للأسفل. ارتفاع حتى 3 م يعطي 5 شرائح، وارتفاع فوق 3 م حتى 3.8 م يعطي 4 شرائح.',
 '<strong>احسب الرولات:</strong> اقسم شرائح الجدار على شرائح الرول الواحد وقرّب للأعلى، ثم اجمع رولات الجدران كلها.',
], ordered=True, sep='\n\n')
assert (round(4 * 1.07 / 1.06, 2), round(5 * 1.07 / 1.06, 2), strips(4), strips(5), room(4, 5, 2.8)) == (4.04, 5.05, 5, 6, 6)
nb[8] = P('<strong>مثال:</strong> غرفة 4 × 5 م بارتفاع 2.8 م. الجدار بعرض 4 م: 4 × 1.07 ÷ 1.06 = 4.04، أي 5 شرائح ورول واحد. الجدار بعرض 5 م: 5 × 1.07 ÷ 1.06 = 5.05، أي 6 شرائح ورولان. المجموع 1 + 1 + 2 + 2 = <strong>6 رولات</strong>.')
nb[12] = sub(ob[12], '<strong>إذا كان عدد الشرائح يملأ الرولات تماماً:</strong> مثل 15 شريحة على 3 رولات، فأي خطأ قص واحد يوقف العمل.',
             '<strong>إذا كانت شرائح الجدار تملأ الرول تماماً:</strong> مثل جدار بعرض 4 م يأخذ الشرائح الخمس كلها من رول واحد، فأي خطأ قص واحد يوقف العمل.')
nb[15] = sub(ob[15], 'وخامة جدار واحد حتى 5 أمتار بين', 'وخامة جدار واحد حتى 4.9 م بين')
nb[18] = sub(ob[18], 'أي يغطي جداراً عرضه 5.3 م.', 'أي يغطي بعد احتساب هدر القص جداراً عرضه حتى 4.9 م.')
assert (room(4, 5, 3.0), room(4, 5, 3.2)) == (6, 8)
nb[20] = P('6 رولات إذا كان ارتفاع الجدار حتى 3 أمتار، و8 رولات إذا كان الارتفاع فوق 3 م حتى 3.8 م.')
assert room(4, 4, 2.8) == 4 and 4 * LO == 300 and 4 * HI == 916     # unchanged statements in blocks 0, 10, 15, excerpt, meta
c55 = finish(35055, ob, nb, dict(excerpt=None, rank_math_description=None))
json.dump(dict(title=bk['title'], slug=bk['slug'], excerpt=bk['excerpt'], **bk['meta'], content=c55),
          open(B + 'content/article-rolls-table.json', 'w'), ensure_ascii=False, indent=1)

# ================= 35057 wallpaper vs paint (content/article-1.json)
bk = json.load(open(B + 'data/backup/post-35057-before-calc-rule.json'))
ob = blocks(bk['content']); assert len(ob) == 27
nb = list(ob)
nb[0] = sub(ob[0], 'تغطية جدار واحد حتى عرض 5 أمتار بورق', 'تغطية جدار واحد حتى عرض 4.9 م بورق')
rows = []
for label, r in [('جدار واحد بعرض 3 م', wall(3)), ('جدار واحد بعرض 4 م', wall(4)), ('جدار واحد بعرض 5 م', wall(5)), ('جدار واحد بعرض 6 م', wall(6)),
                 ('غرفة 3 × 4 م', room(3, 4)), ('غرفة 4 × 4 م', room(4, 4)), ('غرفة 4 × 5 م', room(4, 5)), ('غرفة 5 × 6 م', room(5, 6))]:
    rows.append([label, str(r), f'{n(r * LO)} ريالاً', f'{n(r * MED)} ريالاً', f'{n(r * HI)} ريالاً'])
nb[3] = TB(['المساحة', 'عدد الرولات', 'بأقل سعر (75)', 'بالسعر الأوسط (179)', 'بأعلى سعر (229)'], rows)
nb[14] = sub(ob[14], 'هذا الجدار حتى عرض 5 أمتار يكفيه رول واحد', 'هذا الجدار حتى عرض 4.9 م يكفيه رول واحد')
nb[16] = sub(sub(ob[16],
    'قِس عرض الجدران التي ستغطيها بالمتر واقسمه على 1.06 وقرّب للأعلى: هذا عدد الشرائح.',
    'لكل جدار على حدة: اضرب عرضه بالمتر في 1.07 (هدر قص 7%) واقسم الناتج على 1.06 وقرّب للأعلى: هذا عدد شرائحه.'),
    'اقسم عدد الشرائح على 5 (لارتفاع حتى 3 م) وقرّب للأعلى: هذا عدد الرولات.',
    'اقسم شرائح الجدار على 5 (لارتفاع حتى 3 م) وقرّب للأعلى، ثم اجمع رولات الجدران: هذا عدد الرولات.')
nb[19] = sub(ob[19], 'وأن جداراً واحداً يكلّف رولاً واحداً.', 'وأن جداراً واحداً حتى عرض 4.9 م يكلّف رولاً واحداً.')
nb[21] = P(f'رول واحد إذا كان عرض الجدار حتى 4.9 م وارتفاعه حتى 3 أمتار، أي من {LO} إلى {HI} ريالاً للخامة. جدار بعرض 5 أو 6 أمتار يحتاج رولين.')
assert '1,296 تصميماً من أصل 1,391' in ob[2] and 'والسعر الأوسط 179' in ob[2]      # still true with current prices
ex57 = sub(bk['excerpt'], 'جدار واحد بورق الجدران الكوري يحتاج رولاً واحداً', 'جدار واحد حتى عرض 4.9 م بورق الجدران الكوري يحتاج رولاً واحداً')
rm57 = sub(bk['meta']['rank_math_description'], 'جدار واحد يكفيه رول واحد', 'جدار حتى 4.9 م يكفيه رول واحد')
c57 = finish(35057, ob, nb, dict(excerpt=ex57, rank_math_description=rm57))
a1 = json.load(open(B + 'content/article-1.json'))
a1.update(content=c57, excerpt=ex57, rank_math_description=rm57)
a1['facts'] = ['2026-11-22: الكميات مطابقة لحاسبة الكميات (هدر 7%، كل جدار على حدة). انظر scripts/patch_articles_calc_rule.py و reports/2026-11-22-articles-calc-rule.md'] + [r[0] + ': ' + r[1] + ' رول' for r in rows]
json.dump(a1, open(B + 'content/article-1.json', 'w'), ensure_ascii=False, indent=1)

# ================= 35056 prices (content/article-3.json)
bk = json.load(open(B + 'data/backup/post-35056-before-calc-rule.json'))
ob = blocks(bk['content']); assert len(ob) == 30
nb = list(ob)
D_OLD, D_NEW = '21 نوفمبر 2026', '22 نوفمبر 2026'
nb[0] = sub(ob[0], f'الأسعار محدّثة بتاريخ {D_OLD}', f'الأسعار محدّثة بتاريخ {D_NEW}')
tiers = [(75, 75), (109, 135), (166, 178), (179, 189), (196, 229)]
assert all(any(a <= x <= b for a, b in tiers) for x in pr)
trows = []
for a, b in tiers:
    k = sum(a <= x <= b for x in pr)
    trows.append([f'{a} ريالاً' if a == b else f'{a}–{b} ريالاً', n(k), f'{round(a / 16.5, 1)}' + ('' if a == b else f'–{round(b / 16.5, 1)}') + ' ريالاً'])
assert sum(int(r[1].replace(',', '')) for r in trows) == 1296
nb[3] = TB(['سعر الرول', 'عدد التصاميم', 'سعر المتر المربع تقريباً'], trows)
in75 = [p for p in std if PR(p) == 75]
three = sum(any(c in CN(p) for c in ('تصميم ورود', 'تصميم نقشات', 'تصميم كلاسيك')) for p in in75)
assert three / N75 > 0.5, three                      # "أغلبها ورود ونقشات وكلاسيك" still holds
assert round(523 / 1296 * 100) == 40
nb[4] = sub(ob[4], 'فئة 75 ريالاً تضم 229 تصميماً', f'فئة 75 ريالاً تضم {N75} تصميماً')
L = json.load(open(B + 'data/category-links.json'))
def crow(cat, label):
    v = [PR(p) for p in std if cat in CN(p)]; c = collections.Counter(v).most_common(2)
    top = f'{c[0][0]} ريالاً' if (len(c) == 1 or c[0][1] - c[1][1] > 2) else f'{min(c[0][0], c[1][0])} و{max(c[0][0], c[1][0])} ريالاً'
    return [f'<a href="{L[cat]}">{label}</a>', str(len(v)), f'{min(v)}–{max(v)} ريالاً', top]
designs = [('تصميم ساده', 'سادة'), ('تصميم نقشات', 'نقشات'), ('تصميم ورود', 'ورود'), ('تصميم ساده مقلم', 'سادة مقلّم'), ('تصميم مودرن', 'مودرن'), ('تصميم رخامي', 'رخامي'), ('ورق جدران أطفال', 'أطفال'), ('تصميم كلاسيك', 'كلاسيك')]
colors = [('ورق جدران بيج', 'بيج'), ('ورق جدران رمادي', 'رمادي'), ('ورق جدران أزرق', 'أزرق'), ('ورق جدران وردي', 'وردي'), ('ورق جدران أخضر', 'أخضر'), ('ورق جدران أحمر', 'أحمر')]
nb[6] = TB(['التصميم', 'عدد التصاميم', 'مدى السعر للرول', 'السعر الأكثر شيوعاً'], [crow(*x) for x in designs])
nb[9] = TB(['اللون', 'عدد التصاميم', 'مدى السعر للرول', 'السعر الأكثر شيوعاً'], [crow(*x) for x in colors])
# statements in the unchanged notes (blocks 7, 10, 28) re-checked against current prices
def cs(cat): return [PR(p) for p in std if cat in CN(p)]
k, f_, cl, mar = cs('ورق جدران أطفال'), cs('تصميم ورود'), cs('تصميم كلاسيك'), cs('تصميم رخامي')
assert (k.count(229), len(k), f_.count(75), len(f_), cl.count(75), len(cl), min(mar), max(mar)) == (41, 52, 85, 96, 37, 49, 166, 204)
assert all((min(cs(c)), max(cs(c))) == (75, 229) for c, _ in colors[:5])
rest = [PR(live[p['id']]) for p in wp if p['id'] not in set(std_ids)]; assert len(rest) == 95 and min(rest) >= 75 and max(rest) <= 229
nb[12] = sub(ob[12], 'الجدار الواحد حتى عرض 5 أمتار وارتفاع 3 أمتار يكفيه رول واحد', 'الجدار الواحد حتى عرض 4.9 م وارتفاع 3 أمتار يكفيه رول واحد')
crows = [['جدار واحد حتى 4.9 م', 1]] + [[f'غرفة {a} × {b} م', room(a, b)] for a, b in ((3, 4), (4, 4), (5, 6))]
nb[13] = TB(['المساحة', 'عدد الرولات', 'بسعر 75', 'بسعر 189', 'بسعر 229'], [[lab, str(r)] + [f'{n(r * x)} ريالاً' for x in (75, 189, 229)] for lab, r in crows])
nb[22] = sub(ob[22], f'(أسعار {D_OLD})', f'(أسعار {D_NEW})')
nb[26] = sub(ob[26], '229 تصميماً بسعر 75 ريالاً للرول', f'{N75} تصميماً بسعر 75 ريالاً للرول')
ex56 = sub(bk['excerpt'], f'محدّثة {D_OLD}', f'محدّثة {D_NEW}')
rm56 = sub(bk['meta']['rank_math_description'], f'محدّثة {D_OLD}', f'محدّثة {D_NEW}')
c56 = finish(35056, ob, nb, dict(excerpt=ex56, rank_math_description=rm56))
a3 = json.load(open(B + 'content/article-3.json'))
a3.update(content=c56, excerpt=ex56, rank_math_description=rm56)
a3['facts'] = ['2026-11-22: أُعيد حساب الأعداد من data/live-after (26 تصميماً انتقلت من 99 إلى 75) والكميات مطابقة لحاسبة الكميات. انظر scripts/patch_articles_calc_rule.py',
               'الفئات السعرية: ' + '؛ '.join(f'{r[0]}: {r[1]}' for r in trows), f'في فئة 75: {three} من {N75} في أقسام الورود/النقشات/الكلاسيك']
json.dump(a3, open(B + 'content/article-3.json', 'w'), ensure_ascii=False, indent=1)

json.dump(out, open(B + 'data/out/calc-rule-patch.json', 'w'), ensure_ascii=False, indent=1)
for pid, o in out.items():
    print(pid, 'new content_hash', o['content_hash'], 'changed blocks', [c['index'] for c in o['changed']])
print('three-cat share of 75 tier:', three, '/', N75)
