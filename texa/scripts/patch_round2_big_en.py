# -*- coding: utf-8 -*-
"""Round 2, post 18254 (how-to-calculate-quantities-en): old wp:html block 2 as read live, and the new one."""
import json, hashlib, sys
B = '/home/user/sama-sales-app/texa/'
sha = lambda s: hashlib.sha1(s.encode()).hexdigest()
def sub(block, old, new):
    assert block.count(old) == 1, old
    return block.replace(old, new)
TD = '<td style="padding:11px 14px;border:1px solid #e5e5e5;color:#333;vertical-align:top;">'
TH = '<th style="padding:12px 14px;border:1px solid #e5e5e5;text-align:start;font-weight:700;color:#1e1e1e;background:#f2f2f0;">'
def row(cells, alt=False): return ('<tr style="background:#fafafa;">' if alt else '<tr>') + ''.join(TD + c + '</td>' for c in cells) + '</tr>'
S = 'https://texadecore.store/'
o2 = '\n'.join([
'<!-- wp:html -->',
'<h2>Why every decor project starts with arithmetic</h2>',
'<p>The most common question we get before a purchase isn\'t about colour or price. It\'s "how much do I need?" And getting it wrong costs twice over: order too little and the second order may come from a different batch with a slightly different shade; order far too much and you have money sitting in boxes that will never be opened.</p>',
'<p>The calculation itself is simple. A tape measure and a sheet of paper will do it.</p>',
'<h2>How to calculate each type</h2>',
'<h3>Flooring: parquet and carpet</h3>',
'<p>Work out the floor area: <strong>length × width</strong> in metres. If the room is irregular, split it into rectangles and add the areas together. Then add a waste allowance, and check the product page for the <strong>coverage per box in square metres</strong> — we publish it in the specifications of every product — and divide your total area by it to get the number of boxes.</p>',
'<h3>Walls: wallpaper and cladding</h3>',
'<p>Work out each wall: <strong>width × height</strong>, then add up the walls you\'re covering. Subtract doors and large windows only; leave small openings in the calculation as a safety margin. Then check the roll or panel coverage on the product page.</p>',
'<h3>Skirting boards and trims</h3>',
'<p>Skirting is measured by length, not area: add up the room\'s perimeter and subtract the width of the doorways.</p>',
'<h2>Quick comparison table</h2>',
'<div data-txd-table="1" style="overflow-x:auto;margin-top:28px;margin-bottom:28px;max-width:1100px;margin-inline-start:0 !important;margin-inline-end:auto !important;"><table style="width:100%;border-collapse:collapse;margin:0;font-size:15px;line-height:1.7;border:1px solid #e5e5e5;"><thead><tr>' + ''.join(TH + c + '</th>' for c in ['Product', 'Measured in', 'Formula', 'Watch out for']) + '</tr></thead><tbody>',
row(['Parquet', 'Square metres', 'Length × width', 'Box coverage varies between products']),
row(['Wallpaper', 'Square metres', 'Width × height per wall', 'Large repeats need more waste for matching'], True),
row(['Wall cladding', 'Square metres', 'Width × height', 'Subtract doors and large windows only']),
row(['Skirting', 'Linear metres', 'Perimeter − doorway widths', 'Corners need extra pieces'], True),
row(['Marble alternative', 'Square metres', 'Width × height', 'Panel size determines the joint layout']),
'</tbody></table></div>',
'<h2>The five most common mistakes</h2>',
'<ul><li>Measuring from the furniture instead of wall to wall.</li>',
'<li>Assuming the room is a perfect rectangle — measure length and width in at least two places.</li>',
'<li>Allowing no waste at all, then having to order one extra box from a different colour batch.</li>',
'<li>Subtracting every small opening until the quantity falls short.</li>',
'<li>Working from the architect\'s drawing instead of measuring the finished room.</li></ul>',
'<h2>A worked example: a 4 × 5 metre room</h2>',
'<p>Take a bedroom 5 metres long, 4 metres wide and 3 metres high, with one door and one window.</p>',
f'<p><strong>The floor:</strong> 5 × 4 = 20 m². Open the product page for whatever you\'ve chosen — say <a href="{S}product/باركيه-صيني-هرمي-رمادي-دافئ-8-ملم/">Chinese herringbone parquet in warm grey, 8 mm</a> — read the coverage per box from the specifications, and divide 20 by it after adding your waste allowance.</p>',
f'<p><strong>One feature wall:</strong> if the wall behind the bed is 4 metres wide and 3 metres high, that\'s 12 m². Choose your wallpaper against that figure — for example <a href="{S}product/ورق-جدران-وردي-فاتح-لامع-ساده-كوري/">Korean plain wallpaper in light pink</a> or <a href="{S}product/ورق-حائط-رخامي-رمادي-كوري/">Korean grey marble-effect wallpaper</a>.</p>',
'<p><strong>Skirting:</strong> perimeter = (5 + 4) × 2 = 18 linear metres, minus the width of the doorway.</p>',
'<p>Three formulas, two minutes with a calculator.</p>',
'<h2>Why choose Texa Decor?</h2>',
f'<p>We offer a <strong>measuring service</strong> before purchase — our team comes out, measures, and specifies the exact quantity, which removes the problem at its source. Browse <a href="{S}product-category/الباركيه/">parquet</a>, <a href="{S}product-category/ورق-الجدران/">wallpaper</a> or <a href="{S}product-category/تكسيات-حائط/">wall cladding</a>, then contact us to book a visit.</p>',
'<h2>Frequently asked questions</h2>',
'<p><strong>How much waste allowance should I add?</strong></p>',
'<p>It varies with the laying pattern, the room shape and the size of the repeat. Straight laying in a regular room needs the least; herringbone or a large pattern repeat needs more. Contact us after measuring and we\'ll work out the right allowance for your project.</p>',
'<p><strong>Where do I find the coverage per box or roll?</strong></p>',
'<p>On the product page itself, in the specifications section, alongside the thickness, material and country of origin.</p>',
'<p><strong>Should I order the whole quantity at once?</strong></p>',
'<p>Yes, and strongly so. Ordering in two goes can mean a slight shade difference between batches, and that difference is obvious once everything is installed.</p>',
'<h2>One last tip</h2>',
'<p>Keep one full box back after installation. Floors and cladding get scratched or chipped over time, and having pieces from the same batch means an invisible repair rather than a patch in a slightly different shade.</p>',
'<!-- /wp:html -->'])
n2 = o2
for a, b in [
 ('<p>Work out each wall: <strong>width × height</strong>, then add up the walls you\'re covering. Subtract doors and large windows only; leave small openings in the calculation as a safety margin. Then check the roll or panel coverage on the product page.</p>',
  '<p>For cladding, work out each wall: <strong>width × height</strong>, then add up the walls you\'re covering. Subtract doors and large windows only; leave small openings in the calculation as a safety margin. Then check the panel coverage on the product page.</p>\n<p>Wallpaper is counted in <strong>rolls</strong>, not square metres. For each wall separately, multiply the width in metres by 1.07 (7% cutting waste), divide by 1.06 (the roll width) and round up: that is the number of strips. A 15.6 m Korean roll gives five strips for walls up to 3 m high and four above that up to 3.8 m. Divide the wall\'s strips by the strips per roll, round up, then add the walls together. Do not deduct small doors and windows.</p>'),
 (TD + 'Wallpaper</td>' + TD + 'Square metres</td>' + TD + 'Width × height per wall</td>', TD + 'Wallpaper</td>' + TD + 'Rolls</td>' + TD + '(Width × 1.07) ÷ 1.06 m = strips per wall; a roll gives 5 strips up to 3 m high</td>'),
 ('that\'s 12 m². Choose your wallpaper against that figure — for example', 'that\'s 4 × 1.07 ÷ 1.06 = 4.04, so five strips, and one Korean roll gives five strips at that height: one roll. Choose your wallpaper — for example'),
]: n2 = sub(n2, a, b)
EXP = '7cbc18b08771079625454d18ed824fb0d77e490c'
if __name__ == '__main__':
    ok = sha(o2) == EXP
    print('old hash ok:', ok, 'new hash', sha(n2))
    if ok:
        json.dump(dict(id=18254, site='texadecore.store', note='Changed block only (old markup, SHA-1 verified against the live block hash before the edit).',
                       blocks=[dict(index=2, type='core/html', old_hash=sha(o2), old=o2)]), open(B + 'data/backup/post-18254-before-calc-rule.json', 'w'), ensure_ascii=False, indent=1)
    if len(sys.argv) > 1: print(n2)
