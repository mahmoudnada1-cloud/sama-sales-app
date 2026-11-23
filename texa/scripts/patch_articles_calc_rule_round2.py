# -*- coding: utf-8 -*-
"""2026-11-22 round 2: older posts. Old block markup (as read from the live site, verified by the
block SHA-1 the site reports) -> new block markup. Writes data/backup/post-<id>-before-calc-rule.json
(changed blocks only: index, old hash, old markup) and data/out/calc-rule-patch-round2.json.
Giant HTML blocks live in patch_round2_big.py."""
import json, hashlib, glob, collections, math, sys
B = '/home/user/sama-sales-app/texa/'
sha = lambda s: hashlib.sha1(s.encode()).hexdigest()
def P(h): return f'<!-- wp:paragraph -->\n<p>{h}</p>\n<!-- /wp:paragraph -->'
def sub(block, old, new):
    assert block.count(old) == 1, old
    return block.replace(old, new)
CALC = 'https://texadecore.store/quantity-calculator/'
# calculator
def strips(w): return math.ceil(round(w * 1.07 / 1.06, 6))
def wall(w, per=5): return math.ceil(strips(w) / per)
assert (strips(6), wall(6), strips(4), wall(4), wall(5), strips(3), wall(3)) == (7, 2, 5, 1, 2, 4, 1)
assert round(6 * 1.07 / 1.06, 2) == 6.06 and 2 * wall(3) + 2 * wall(4) == 4 and 2 * wall(4) + 2 * wall(5) == 6
# current prices (newer snapshot)
d = []
for f in glob.glob(B + 'data/live-after2/p*.json'): d += json.load(open(f))
C = lambda p: [c['name'] for c in p['categories']]; PR = lambda p: int(p['prices']['price'])
wp = [PR(p) for p in d if 'ورق جدران' in C(p)]; kids = [PR(p) for p in d if 'ورق جدران أطفال' in C(p)]
mode = lambda v: collections.Counter(v).most_common(1)[0][0]
assert (len(wp), min(wp), max(wp), mode(wp)) == (1391, 75, 229, 179)
assert (len(kids), min(kids), max(kids), mode(kids)) == (53, 174, 229, 229), (len(kids), min(kids), max(kids), mode(kids))

POSTS = {}   # id -> list of (index, type, expected_old_hash or None, old, new)

# ---------------- 18250 majlis-decor-2026
o0 = P('<strong>الإجابة المختصرة:</strong> ورق الجدران لا يُسعَّر كله بوحدة واحدة، وهذا أول ما يربك حساب المجلس. <strong>الأنواع الكورية تُباع بالرول</strong> — والرول 15.6 متر × 106 سم ويغطي نحو 16.5 متر مربع — <strong>أما الأمريكي والطباعة فبالمتر الطولي</strong>. والمقروء من المتجر في 4 نوفمبر 2026: الأرضية <strong>64 ريالًا</strong> (ورق أمريكي قماشي، بالمتر الطولي) والسقف <strong>245 ريالًا</strong> (كوري، بالرول)، شاملًا الضريبة، بين 1,363 تصميمًا. وجدار المجلس 6 × 2.8 متر يحتاج <strong>رولين كوريَّين</strong>، لأن عرض الرول 106 سم فيغطّي ستة أشرطة بارتفاع 2.8 متر — بدون الغراء وبدون هدر مطابقة النقشة.')
n0 = sub(o0, 'لأن عرض الرول 106 سم فيغطّي ستة أشرطة بارتفاع 2.8 متر', 'لأنه يأخذ سبعة أشرطة بعد هدر القص 7% والرول يعطي خمسة أشرطة بارتفاع 2.8 متر')
o7 = P('قس أطوال الجدران وارتفاعها أولًا، <strong>ثم حوّلها إلى وحدة البيع لا إلى المتر المربع</strong>. للكوري: اقسم عرض الجدار على 106 سم لتعرف عدد الأشرطة، ثم اقسم طول الرول (15.6 متر) على ارتفاع الجدار لتعرف كم شريطًا يعطيه الرول الواحد. فجدار 4 أمتار بارتفاع 3 أمتار يحتاج أربعة أشرطة، والرول يعطي خمسة بهذا الارتفاع، <strong>أي رول واحد</strong>. أما الأمريكي والطباعة فالحساب فيهما بالمتر الطولي مباشرة. وأضف 10% للقص ومطابقة النقشة في الحالتين.')
n7 = P('قس أطوال الجدران وارتفاعها أولًا، <strong>ثم حوّلها إلى وحدة البيع لا إلى المتر المربع</strong>. للكوري، ولكل جدار على حدة: اضرب عرض الجدار في 1.07 (هدر قص 7%) واقسمه على 106 سم وقرّب لأعلى لتعرف عدد الأشرطة، ثم اقسم طول الرول (15.6 متر) على ارتفاع الجدار زائدًا 10 سم وقرّب لأسفل لتعرف كم شريطًا يعطيه الرول الواحد. فجدار 4 أمتار بارتفاع 3 أمتار يحتاج خمسة أشرطة، والرول يعطي خمسة بهذا الارتفاع، <strong>أي رول واحد</strong>، وجدار 5 أمتار يحتاج رولين. واجمع رولات الجدران، ولا تخصم الأبواب والنوافذ الصغيرة. أما الأمريكي والطباعة فالحساب فيهما بالمتر الطولي مباشرة مع إضافة 10% للقص.')
POSTS[18250] = [(0, 'core/paragraph', '3e934c607e993355e00c033752cd598ec527bdd5', o0, n0), (7, 'core/paragraph', 'e7b3506c321965b07dccfd34ffff7f76bc0d8e16', o7, n7)]

# ---------------- 26925 wallpaper-riyadh-price-guide
o13 = P('<strong>والمقارنة الصحيحة بعدد الرولات لا بسعر متر مربع نظريٍ</strong>، لأن المتجر يبيع الرول الكامل ولا يبيع مترًا منه. والطريقة: اقسم عرض الجدار على عرض الرول (106 سم) لتعرف عدد الأشرطة، واقسم طول الرول (15.6 متر) على ارتفاع الجدار لتعرف كم شريطًا يعطيه الرول الواحد، ثم اقسم الأول على الثاني وقرّب لأعلى. فجدار المجلس 6 × 2.8 متر يحتاج ستة أشرطة، والرول يعطي خمسة بهذا الارتفاع، <strong>أي رولان</strong>. وتكلفتهما عند أرخص ساده (109 ريالات) <strong>218 ريالًا</strong>، وعند أغلاه (245 ريالًا) <strong>490 ريالًا</strong> — بدون الغراء وبدون هدر مطابقة النقشة.')
n13 = sub(sub(o13, 'والطريقة: اقسم عرض الجدار على عرض الرول (106 سم) لتعرف عدد الأشرطة، واقسم طول الرول (15.6 متر) على ارتفاع الجدار لتعرف',
    f'والطريقة هي طريقة <a href="{CALC}">حاسبة الكميات</a>: اضرب عرض الجدار في 1.07 (هدر قص 7%) واقسمه على عرض الرول (106 سم) وقرّب لأعلى لتعرف عدد الأشرطة، واقسم طول الرول (15.6 متر) على ارتفاع الجدار زائدًا 10 سم وقرّب لأسفل لتعرف'),
    'يحتاج ستة أشرطة', 'يحتاج سبعة أشرطة')
def OL(items): return '<!-- wp:list {"ordered":true} -->\n<ol>' + '\n\n'.join(f'<!-- wp:list-item -->\n<li>{i}</li>\n<!-- /wp:list-item -->' for i in items) + '</ol>\n<!-- /wp:list -->'
o15 = OL(['<strong>احسب المساحة:</strong> اضرب عرض كل جدار في ارتفاعه واجمع النواتج.',
          '<strong>اطرح الفتحات الكبيرة:</strong> باب أو نافذة تزيد مساحتها على مترين مربعين تُطرح؛ وما دون ذلك يُترك احتياطًا.',
          '<strong>أضف الهدر:</strong> عشرة في المئة للنقشات السادة، وخمسة عشر إلى عشرين للنقشات التي تحتاج مطابقة كالورود والخطوط العريضة.',
          '<strong>اقسم على 13:</strong> أي على التغطية الصافية للرول، ثم قرّب العدد إلى أعلى.'])
n15 = OL(['<strong>احسب أشرطة كل جدار على حدة:</strong> اضرب عرض الجدار بالمتر في 1.07 (هدر قص 7%) واقسمه على 1.06، وقرّب لأعلى.',
          '<strong>احسب ما يعطيه الرول:</strong> اقسم 15.6 على ارتفاع الجدار زائدًا 10 سم، وقرّب لأسفل: خمسة أشرطة لارتفاع حتى 3 أمتار، وأربعة لما فوقه حتى 3.8 متر.',
          '<strong>احسب الرولات:</strong> اقسم أشرطة الجدار على أشرطة الرول وقرّب لأعلى، ثم اجمع رولات الجدران.',
          '<strong>لا تخصم الأبواب والنوافذ الصغيرة:</strong> ما يتوفر منها يبقى احتياطًا، والنقشات التي تحتاج مطابقة كالورود والخطوط العريضة قد تحتاج رولًا إضافيًا.'])
o16 = P('<strong>مثال مجلس:</strong> جدار بعرض ستة أمتار وارتفاع ثلاثة = 18 مترًا مربعًا. مع هدر خمسة عشر في المئة تصبح 20.7 مترًا مربعًا. وبالقسمة على 13 تحصل على 1.6، فالمطلوب <strong>رولان</strong>. وتكلفة الورق عند 109 ريالات للرول = <strong>218 ريالًا</strong>، وعند 174 ريالًا = <strong>348 ريالًا</strong>، وعند 245 ريالًا = <strong>490 ريالًا</strong>. واللاصق وأجرة التركيب غير داخلين في هذه الأرقام.')
n16 = sub(o16, 'جدار بعرض ستة أمتار وارتفاع ثلاثة = 18 مترًا مربعًا. مع هدر خمسة عشر في المئة تصبح 20.7 مترًا مربعًا. وبالقسمة على 13 تحصل على 1.6، فالمطلوب',
          'جدار بعرض ستة أمتار وارتفاع ثلاثة: 6 × 1.07 ÷ 1.06 = 6.06، أي سبعة أشرطة. والرول يعطي خمسة أشرطة بهذا الارتفاع، فالمطلوب')
o29 = P('غرفة بمساحة جدران 40 مترًا مربعًا تحتاج نحو 46 مترًا مربعًا بعد إضافة هدر خمسة عشر في المئة، أي <strong>أربعة رولات</strong> بالقسمة على التغطية الصافية 13 مترًا مربعًا. وتكلفة الورق عند 109 ريالات للرول <strong>436 ريالًا</strong>، وعند 245 ريالًا <strong>980 ريالًا</strong> — بدون الغراء وأجرة التركيب.')
n29 = sub(sub(o29, 'غرفة بمساحة جدران 40 مترًا مربعًا تحتاج نحو 46 مترًا مربعًا بعد إضافة هدر خمسة عشر في المئة، أي <strong>أربعة رولات</strong> بالقسمة على التغطية الصافية 13 مترًا مربعًا.',
          'غرفة 3 × 4 أمتار بارتفاع حتى 3 أمتار: كل جدار من الأربعة يحتاج رولًا واحدًا (أربعة أشرطة للجدار 3 أمتار وخمسة للجدار 4 أمتار)، أي <strong>أربعة رولات</strong>. وغرفة 4 × 5 أمتار تحتاج ستة.'),
          'وتكلفة الورق عند 109 ريالات', 'وتكلفة الرولات الأربعة عند 109 ريالات')
o42 = P('<em>جميع الأسعار والأعداد مقروءة من المتجر في 4 نوفمبر 2026، شاملة ضريبة القيمة المضافة، والمعروض لا المشطوب، وقابلة للتغيير. <strong>والسعر الملزم هو المعروض على صفحة المنتج وقت الطلب، ومعه وحدة البيع.</strong></em>')
n42 = sub(o42, 'وقابلة للتغيير. <strong>', 'وقابلة للتغيير. وفي قراءة 22 نوفمبر 2026 يضم قسم ورق الجدران 1,391 تصميمًا بين 75 و229 ريالًا للرول. <strong>')
POSTS[26925] = [(13, 'core/paragraph', '76930533551f5f83d007ae5443d696448113a8e5', o13, n13), (15, 'core/list', 'c0a43b351455a3fe1c26b671585277c990ed7281', o15, n15),
                (16, 'core/paragraph', '097b7de3829d53a35f8c57dba62f3f3aaa3504a1', o16, n16), (29, 'core/paragraph', 'e6c3a7c409dfbcaaefbc0ab77ed35d0836bcd498', o29, n29),
                (42, 'core/paragraph', '9a71895b7825febf582029a5d7c59b7df1e47ad0', o42, n42)]

# ---------------- shared Arabic template blocks (17663, 17642, 17300, 18247)
t_intro_o = P('<strong>الإجابة المختصرة:</strong> سعر ورق الجدران في السعودية <strong>من 64 إلى 240 ريالًا للمتر</strong>، والأشيع 166 ريالًا للمتر، شاملًا الضريبة. السعر المعروض للمتر، و720 تصميمًا متوفرًا الآن.')
t_intro_n = P('<strong>الإجابة المختصرة:</strong> سعر ورق الجدران في تكسا ديكور <strong>من 75 إلى 229 ريالًا للرول</strong>، والأشيع 179 ريالًا للرول، شاملًا الضريبة (قراءة 22 نوفمبر 2026). السعر المعروض على صفحة المنتج هو سعر الرول لا المتر، وفي القسم 1,391 تصميمًا.')
t_price_o = P('من 64 إلى 240 ريالًا للمتر شاملًا الضريبة، والأشيع 166 ريالًا. السعر المعروض على صفحة المنتج هو سعر المتر.')
t_price_n = P('من 75 إلى 229 ريالًا للرول شاملًا الضريبة، والأشيع 179 ريالًا (قراءة 22 نوفمبر 2026). السعر المعروض على صفحة المنتج هو سعر الرول لا المتر، والرول الكوري القياسي 15.6 متر × 106 سم.')
t_qty_o = P('اجمع أطوال الجدران بالأمتار واضرب في الارتفاع، ثم أضف 10% للقص ومطابقة النقشة. جدار 4 أمتار بارتفاع 3 أمتار يحتاج نحو 13 مترًا.')
t_qty_n = P('ورق الجدران يُحسب بالرول لا بالمتر. لكل جدار على حدة: اضرب عرضه في 1.07 (هدر قص 7%) واقسمه على 1.06 وقرّب لأعلى لتعرف عدد الأشرطة، والرول 15.6 متر يعطي خمسة أشرطة لارتفاع حتى 3 أمتار. فجدار 4 أمتار بارتفاع 3 أمتار يحتاج خمسة أشرطة أي رولًا واحدًا، وجدار 5 أمتار يحتاج رولين. واجمع رولات الجدران، ولا تخصم الأبواب والنوافذ الصغيرة.')
U = 'https://texadecore.store/product-category/'
WPC = U + '%D9%88%D8%B1%D9%82-%D8%A7%D9%84%D8%AC%D8%AF%D8%B1%D8%A7%D9%86/'; KID = U + '%D9%88%D8%B1%D9%82-%D8%AC%D8%AF%D8%B1%D8%A7%D9%86-%D8%A7%D8%B7%D9%81%D8%A7%D9%84/'; PAN = U + '%D8%A7%D9%84%D8%A8%D8%A7%D9%86%D9%88%D9%87%D8%A7%D8%AA-%D9%88%D8%A7%D9%84%D8%B2%D8%AE%D8%A7%D8%B1%D9%81/'
def TB(head, rows, nl='\n'):
    return f'<!-- wp:table -->{nl}<figure class="wp-block-table"><table><thead><tr>' + ''.join(f'<th>{c}</th>' for c in head) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows) + f'</tbody></table></figure>{nl}<!-- /wp:table -->'
def t_table_o(nl='\n'): return TB(['النوع', 'ريال للمتر', 'الأشيع', 'المتوفر'], [[f'<a href="{WPC}">ورق جدران</a>', '64 – 240', '166', '720 تصميمًا'], [f'<a href="{KID}">ورق جدران أطفال</a>', '174 – 240', '240', '40 تصميمًا'], ['ورق جدران أمريكي', '64 – 240', '166', '10 تصاميم'], [f'<a href="{PAN}">البانوهات والزخارف</a>', '7 – 181', '46', '90 قطعة']], nl)
t_table_n = TB(['النوع', 'السعر (ريال)', 'الأشيع', 'المتوفر'], [[f'<a href="{WPC}">ورق جدران</a>', '75 – 229 للرول', '179', '1,391 تصميمًا (22 نوفمبر 2026)'], [f'<a href="{KID}">ورق جدران أطفال</a>', '174 – 229 للرول', '229', '53 تصميمًا (22 نوفمبر 2026)'], [f'<a href="{PAN}">البانوهات والزخارف</a>', '7 – 181', '46', '90 قطعة']])
POSTS[18247] = [(0, 'core/paragraph', '870829f809d976ade487eb60319bbab75563470c', t_intro_o, t_intro_n), (5, 'core/paragraph', '689a7969d0710895f95138697ada5186a4cb139e', t_price_o, t_price_n), (7, 'core/paragraph', 'd7547c91918e7e7ee8222d2cb1a2a30c0a3860a9', t_qty_o, t_qty_n)]

# ---------------- shared English template blocks (18255, 17641)
e_intro_o = P('<strong>Short answer:</strong> wallpaper in Saudi Arabia costs <strong>SAR 64 to SAR 240 per metre</strong>, most commonly SAR 166, VAT included. The price shown is per metre, and 720 designs are in stock.')
e_intro_n = P('<strong>Short answer:</strong> wallpaper at Texa Decor costs <strong>SAR 75 to SAR 229 per roll</strong>, most commonly SAR 179, VAT included (read on 22 November 2026). The price shown is per roll, not per metre, and 1,391 designs are listed.')
e_table_o = TB(['Type', 'SAR per metre', 'Most common', 'In stock'], [[f'<a href="{WPC}">Wallpaper</a>', '64 – 240', '166', '720 designs'], [f'<a href="{KID}">Kids wallpaper</a>', '174 – 240', '240', '40 designs'], ['American wallpaper', '64 – 240', '166', '10 designs'], [f'<a href="{PAN}">Panels and mouldings</a>', '7 – 181', '46', '90 items']])
e_table_n = TB(['Type', 'Price (SAR)', 'Most common', 'In stock'], [[f'<a href="{WPC}">Wallpaper</a>', '75 – 229 per roll', '179', '1,391 designs (22 November 2026)'], [f'<a href="{KID}">Kids wallpaper</a>', '174 – 229 per roll', '229', '53 designs (22 November 2026)'], [f'<a href="{PAN}">Panels and mouldings</a>', '7 – 181', '46', '90 items']])
POSTS[18255] = [(0, 'core/paragraph', 'bb1e2865fce01136454887e2e139d801d24ea029', e_intro_o, e_intro_n)]

# ---------------- 26937 wallpaper-prices-riyadh-en
def OLe(items): return OL(items)
e15_o = OL(['<strong>Measure the area:</strong> multiply each wall’s width by its height, then add the results.',
            '<strong>Deduct large openings:</strong> subtract any door or window over 2 m²; leave smaller ones in as a margin.',
            '<strong>Add waste:</strong> 10% for plain patterns, 15 to 20% for designs needing pattern matching such as florals and wide stripes.',
            '<strong>Divide by 13:</strong> the net coverage per roll — then round up.'])
e15_n = OL(['<strong>Count the strips for each wall separately:</strong> multiply the wall’s width in metres by 1.07 (7% cutting waste), divide by 1.06 (the roll width) and round up.',
            '<strong>Count the strips one roll gives:</strong> divide 15.6 by the wall height plus 10 cm and round down: five strips for walls up to 3 m high, four above that up to 3.8 m.',
            '<strong>Work out the rolls:</strong> divide the wall’s strips by the strips per roll and round up, then add the walls together.',
            '<strong>Leave small doors and windows in:</strong> do not deduct them. Designs needing pattern matching, such as florals and wide stripes, may need an extra roll.'])
e16_o = P('<strong>Worked example — a majlis wall:</strong> 6 m wide × 3 m high is 18 m². With 15% waste that becomes 20.7 m². Divided by 13 that is 1.6, so you need <strong>two rolls</strong>. The wallpaper cost is <strong>SAR 210</strong> at SAR 105 per roll, <strong>SAR 408</strong> at SAR 204, and <strong>SAR 480</strong> at SAR 240. Adhesive and fitting labour are additional.')
e16_n = sub(e16_o, '6 m wide × 3 m high is 18 m². With 15% waste that becomes 20.7 m². Divided by 13 that is 1.6, so you need', '6 m wide × 3 m high: 6 × 1.07 ÷ 1.06 = 6.06, so seven strips. A roll gives five strips at that height, so you need')
e29_o = P('A room with 40 m² of wall area needs about 46 m² once 15% waste is added, which is four rolls at a net coverage of 13 m² each. At SAR 105 per roll the wallpaper comes to about SAR 420.')
e29_n = P('A 3 × 4 m room with walls up to 3 m high needs one roll per wall, which is four rolls; a 4 × 5 m room needs six. At SAR 105 per roll, four rolls come to about SAR 420.')
E26937 = [('core/list', e15_o, e15_n), ('core/paragraph', e16_o, e16_n), ('core/paragraph', e29_o, e29_n)]

if __name__ == '__main__':
    out = {}
    for pid, blocks in POSTS.items():
        for i, t, h, o, n in blocks:
            assert h is None or sha(o) == h, (pid, i, sha(o))
            assert o != n and n.count('<!-- wp:') == n.count('<!-- /wp:')
        json.dump(dict(id=pid, site='texadecore.store', note='Changed blocks only (old markup, SHA-1 verified against the live block hash before the edit). Full pre-edit content is in the WordPress revisions.',
                       blocks=[dict(index=i, type=t, old_hash=sha(o), old=o) for i, t, h, o, n in blocks]),
                  open(f'{B}data/backup/post-{pid}-before-calc-rule.json', 'w'), ensure_ascii=False, indent=1)
        out[pid] = [dict(index=i, type=t, old_hash=sha(o), new_hash=sha(n), new=n) for i, t, h, o, n in blocks]
        print(pid, [(i, sha(n)[:8]) for i, t, h, o, n in blocks])
    json.dump(out, open(B + 'data/out/calc-rule-patch-round2.json', 'w'), ensure_ascii=False, indent=1)
    print('template hashes', sha(t_intro_o), sha(t_price_o), sha(t_qty_o), sha(t_table_o()), sha(t_table_o('\r\n')), sha(e_intro_o), sha(e_table_o))
    print('26937', [sha(o) for t, o, n in E26937])
    if len(sys.argv) > 1:
        for b in out[int(sys.argv[1])]: print(b['index'], b['old_hash']); print(b['new']); print()
