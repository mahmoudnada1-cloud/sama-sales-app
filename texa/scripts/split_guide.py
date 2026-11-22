#!/usr/bin/env python3
"""يفصل دليل العائلة عن وصف كل منتج: الدليل يُحفظ مرة واحدة لكل عائلة في إضافة texa-family-guide،
والوصف يبقى فيه الجزء الخاص بالمنتج فقط. المصدر: ملف CSV الذي طُبّق على المتجر + ملفات products-v6-<family>.csv."""
import csv, glob, json, os, re, sys, collections
csv.field_size_limit(10 ** 9)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'plugin/texa-desc-import/data/products-v5-200-all-families.csv')
OUT_CSV = os.path.join(ROOT, 'data/out/products-v5-300-guide-split.csv')
PDIR = os.path.join(ROOT, 'plugin/texa-family-guide/data')
MARK_OLD, MARK_NEW = '<!-- txa-desc-v4 -->', '<!-- txa-desc-v5 -->'


def php_str(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "\\'") + "'"


def main():
    fam_of = {}
    for f in glob.glob(os.path.join(ROOT, 'data/out/products-v6-*.csv')):
        fam = os.path.basename(f)[len('products-v6-'):-4]
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            fam_of[int(r['ID'])] = fam
    rows = list(csv.DictReader(open(SRC, encoding='utf-8-sig')))
    guides = collections.defaultdict(collections.Counter)
    out, pmap, bad = [], {}, []
    for r in rows:
        pid = int(r['ID']); d = r['Description']; fam = fam_of.get(pid)
        cfg = json.load(open(os.path.join(ROOT, 'data/family-content', fam + '.json'))) if fam else None
        if not fam or not d.rstrip().endswith(MARK_OLD):
            bad.append((pid, 'no family or marker')); continue
        gt = cfg['guide_title'].strip()
        m = None
        for m in re.finditer(r'<h2>([^<]*?): ' + re.escape(gt) + r'</h2>\n', d):
            pass
        body = d.rstrip()[:-len(MARK_OLD)].rstrip()
        t = body.rfind('\n<p>')
        if not m or t < m.end():
            bad.append((pid, 'separator or tail not found')); continue
        layer, kw, guide, tail = d[:m.start()].rstrip(), m.group(1), body[m.end():t].strip(), body[t:].strip()
        if 'txa-family' not in guide or 'txa-family' in layer or 'txa-specs' not in layer:
            bad.append((pid, 'unexpected split')); continue
        guides[fam][guide] += 1
        pmap[pid] = (fam, kw)
        nr = dict(r); nr['Description'] = '\n'.join([layer, tail, MARK_NEW]); out.append(nr)
    multi = {f: len(c) for f, c in guides.items() if len(c) > 1}
    print('rows', len(rows), 'split', len(out), 'bad', len(bad), bad[:5], 'families', len(guides), 'families with >1 guide text', multi)
    if bad or multi:
        sys.exit(1)
    os.makedirs(PDIR, exist_ok=True)
    with open(os.path.join(PDIR, 'guides.php'), 'w', encoding='utf-8') as fh:
        fh.write("<?php\nif ( ! defined( 'ABSPATH' ) ) { exit; }\nreturn array(\n")
        for fam in sorted(guides):
            gt = json.load(open(os.path.join(ROOT, 'data/family-content', fam + '.json')))['guide_title'].strip()
            fh.write('\t%s => array( %s, %s ),\n' % (php_str(fam), php_str(gt), php_str(next(iter(guides[fam])))))
        fh.write(");\n")
    with open(os.path.join(PDIR, 'map.php'), 'w', encoding='utf-8') as fh:
        fh.write("<?php\nif ( ! defined( 'ABSPATH' ) ) { exit; }\nreturn array(\n")
        for pid in sorted(pmap):
            fh.write('\t%d => array( %s, %s ),\n' % (pid, php_str(pmap[pid][0]), php_str(pmap[pid][1])))
        fh.write(");\n")
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(out)
    wc = lambda h: len(re.sub(r'<[^>]+>', ' ', h).split())
    ws = sorted(wc(r['Description']) for r in out)
    print('product-layer words: median', ws[len(ws) // 2], 'min', ws[0], 'max', ws[-1], '| csv MB', round(os.path.getsize(OUT_CSV) / 1e6, 1))


if __name__ == '__main__':
    main()
