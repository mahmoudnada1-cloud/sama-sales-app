# Articles round 3-C — 720 designs, October dates, panels row (2026-11-23)

Site: texadecore.store. Posts touched: 17663, 17642, 17300, 17641 (EN), 18247. All remain `publish`.
Nothing else touched (no products, pages, plugins, titles, slugs, excerpts or meta).
Owner approval: "كمل على الأسعار القديمة و720 تصميم".

## Source of numbers
Snapshot `texa/data/live-after2/p*.json` (4,191 products, read 22 November 2026), recomputed by category name:

| Category | Count | In stock | Min–max SAR | Most common |
|---|---|---|---|---|
| ورق جدران | 1,391 | 1,341 | 75–229 | 179 (355 products) |
| ورق جدران أطفال | 53 | 11 | 174–229 | 229 (42) |
| البانوهات والزخارف | 184 | 184 | 9–213 | 23 (16) |

## Method
Block-by-block with `wpcom-post-sections-replace` under modified/content/block hash locks.
No whole-content rewrite was needed: every stale passage sat in a block, including in 17300
(which also holds classic HTML; that part was not touched).

## Changes (same wording in each post unless noted)

| Block | Before | After |
|---|---|---|
| Image caption (link text) | واحد من «720 تصميمًا متوفرًا» | واحد من «أكثر من 1,300 تصميم متوفر» |
| Price heading | أسعار ورق الجدران — أكتوبر 2026، شاملة الضريبة | أسعار ورق الجدران — 22 نوفمبر 2026، شاملة الضريبة |
| Table, panels row | 7 – 181 / 46 / 90 قطعة | 9 – 213 / 23 / 184 منتجًا (22 نوفمبر 2026) |
| Browse list, first item | ورق جدران — 720 تصميمًا | ورق جدران — أكثر من 1,300 تصميم |
| Footer note | …متحقق منها من المتجر في أكتوبر 2026… | …متحقق منها من المتجر في 22 نوفمبر 2026… |

English post 17641: "720 designs in stock" → "more than 1,300 designs in stock"; "Wallpaper prices — October 2026"
→ "— 22 November 2026"; panels row "7 – 181 / 46 / 90 items" → "9 – 213 / 23 / 184 products (22 November 2026)";
"Wallpaper — 720 designs" → "Wallpaper — more than 1,300 designs"; footer "October 2026" → "22 November 2026".

Per post:
- 17663: caption, heading, table, browse list, footer (5 blocks).
- 17642: caption, heading, table, browse list, footer (5 blocks).
- 17300: caption, heading, table, browse list, footer (5 blocks). Classic HTML untouched.
- 17641 (EN): caption, heading, table, browse list, footer (5 blocks), English only.
- 18247: caption and footer only (2 blocks). This post has no price table and no browse list.

Each "720" mention counted wallpaper designs (it links to the wallpaper category), so all were replaced; the caption
says "in stock/متوفر" and 1,341 are in stock, so "more than 1,300" holds for both listed and in-stock counts.

## Removed
Nothing. No table row had to be dropped; the panels row matched the category البانوهات والزخارف exactly.
The two wallpaper rows were left as corrected last round (they match the snapshot).

## Excerpt / rank_math_description
Checked on all five: none carries 720, an October date or a price, so none was changed.

## Verification
- Raw re-read of 17641 and section re-list: edited blocks carry the new text, untouched blocks keep their old hashes.
- Live public pages of 17663, 17642, 17300, 18247 fetched after the edits and compared line by line with
  `texa/data/backup/post-<id>-before-round3.json`: the only backup lines missing from the live pages are the
  stale ones listed above (7 per post, 2 for 18247). No "720 تصميم", no "أكتوبر 2026" left; table shows 9 – 213 / 23 / 184.
- Status `publish` confirmed on all five.

## Not fixed / to decide
1. English post 17641 is not reachable by the public: its URL `/2026/08/01/luxury-wallpaper-choosing-guide/`
   (and `?p=17641`) redirects to the Arabic post 17642. So the English edit was verified from the stored content only.
   For the same reason `backup/post-17641-before-round3.json` contains the Arabic page, not the English one;
   the English "before" exists only as a WordPress revision.
2. Table column header "المتوفر / In stock" shows listed counts: wallpaper 1,391 (1,341 in stock) and kids
   wallpaper 53 (only 11 in stock). Left as is because those rows were out of scope; renaming the header to
   "عدد التصاميم / Designs listed" or using in-stock counts would make it exact.
3. The price heading still reads "أسعار ورق الجدران" although the table has a panels row (unchanged, as before).
4. 17300 classic FAQ (not touched): "كم سعر متر ورق جدران؟" says a per-metre price cannot be given, which sits
   awkwardly with the per-roll prices above it, and another answer mentions "ضمان على العمل".
