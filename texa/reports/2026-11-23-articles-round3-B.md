# Articles round 3-B — stale prices and counts (2026-11-23)

Site: texadecore.store. Posts touched: 18250, 18255, 17238, 17240 only. All four remain `publish`.
Source of figures: `texa/data/live-after2/p*.json` (snapshot of 22 November 2026, 4,191 unique products).
Method: block-level edits with `wpcom-post-sections-replace` under modified/content/block hash locks. No whole-post update was made, and no excerpt, meta, title or slug was changed.

## Figures used (recomputed from the snapshot)

| Category | Listed | In stock | Min–max (SAR) | Most common |
| --- | --- | --- | --- | --- |
| ورق جدران | 1,391 | 1,341 | 75–229 | 179 (355 products) |
| تصميم ساده | 821 | 813 | 75–229 | 189 (213 products) |
| ورق جدران أطفال | 53 | 11 | 174–229 | 229 (42 products) |

No product in the snapshot has "أمريكي/امريكي" in its name or short description, and no wallpaper product is sold per linear metre. The only "طباعه" products are 22 marble-alternative items, not wallpaper.

Arithmetic: 229 ÷ 16.5 = 13.9 (stated as "about 14 per m² at the top price"); 179 ÷ 16.5 = 10.8 (stated as "about 11").
Calculator checks: wall 4 m = ceil(4.28 ÷ 1.06) = 5 strips = 1 roll; 5 m = 6 strips = 2 rolls; 6 m = 7 strips = 2 rolls; 15.6 ÷ (3.0 + 0.1) = 5 strips per roll.

## Post 18250 (majlis-decor-2026, Arabic) — 5 blocks

- Block 0 (lead): "64 ريالًا (ورق أمريكي، بالمتر الطولي) … 245 ريالًا … 1,363 تصميمًا … 4 نوفمبر" replaced by: sold per roll, 75–229 per roll, most common 179, 1,391 designs, read 22 November 2026. Removed the sentence that American and print wallpaper are sold per linear metre. The 6 × 2.8 m wall example (7 strips, 2 rolls) was kept; it matches the calculator.
- Block 1 (image caption): "1,363 تصميمًا، والكوري منها يُباع بالرول" → "1,391 تصميمًا، ويُباع بالرول".
- Block 5 (FAQ price answer): same figures as the lead; removed "الوحدة تختلف باختلاف النوع … والأمريكي والطباعة بالمتر الطولي".
- Block 7 (FAQ quantity answer): removed "للكوري،" and the final sentence about American/print being calculated per linear metre plus 10%. Method and examples unchanged (4 m = 1 roll, 5 m = 2 rolls).
- Block 14 (footer): "4 نوفمبر 2026" → "22 نوفمبر 2026"; "أعداد المتوفر" → "أعداد التصاميم" because the article now cites listed designs.
- Unchanged: the large HTML block (hash fc0b68d9… identical before and after), headings, other FAQ answers, excerpt, rank_math_description (neither carries a number or date).

## Post 18255 (majlis-decor-2026-en, English) — 1 block

- Block 1 (image caption): "720 designs in stock" → "1,341 designs in stock".
- The lead already carried 75–229 per roll, 179, 22 November 2026 and 1,391 designs; left as is. HTML block hash d84f9f35… identical before and after.

## Post 17238 (دليل اختيار ورق الجدران, Arabic) — 6 blocks

- Block 0 (lead): "من 64 ريالًا للمتر إلى 240 ريالًا للرول … 720 تصميمًا … ما عدا الأمريكي والطباعة فالسعر بالمتر … نحو 15 ريالًا للمتر المربع" replaced by 75–229 per roll, most common 179, 1,391 designs, read 22 November 2026, price is per roll, about 14 SAR/m² at the top price. The "13–14 مترًا صافيًا بعد الهدر" coverage claim was replaced by the calculator statement (5 strips per roll up to 3 m; wall 4 m = 1 roll, 5 or 6 m = 2 rolls).
- Block 1 (image caption): "720 تصميمًا متوفرًا" → "1,341 تصميمًا متوفرًا".
- Block 3 (table heading): "أكتوبر 2026" → "22 نوفمبر 2026" (every remaining row was recomputed).
- Block 4 (price table):
  - Row "كل الأنواع": 64–240 / حسب النوع / 720 → 75–229 / للرول / 1,391 designs, most common 179.
  - Row "ورق جدران قماشي أمريكي — 64 للمتر الطولي": removed.
  - Row "سادة كوري — 240, كان 245" → "ورق جدران سادة": 75–229 per roll, 821 designs, most common 189.
  - Row "أطفال كوري — 240, كان 291" → "ورق جدران أطفال": 174–229 per roll, 53 listed, 11 in stock.
  - Caption: 23 October → 22 November; "الرول بـ240 … نحو 15 ريالًا" → roll at 179 ≈ 11 SAR/m².
- Block 6 (browse list): "ورق جدران — 720 تصميمًا" → "1,391 تصميمًا". Other three list items and all links unchanged.
- Block 7 (footer): "متحقق منها من المتجر في أكتوبر 2026" → "مقروءة من المتجر في 22 نوفمبر 2026".

## Post 17240 (wallpaper-buying-guide, English) — 6 blocks

Same six edits as 17238, in English: lead, caption (1,341 designs in stock), table heading (22 November 2026), table (American fabric row removed; Plain 75–229, 821 designs, most common 189; Kids 174–229, 53 listed, 11 in stock), browse list (1,391 designs), footer.

## Removed

- American wallpaper price row (SAR 64 per linear metre) from both tables (17238, 17240).
- Every sentence stating that American/print wallpaper is priced or calculated per linear metre (18250 ×3, 17238 ×1, 17240 ×1).
- "was 245" / "was 291" notes in both tables.
- No row had to be dropped for an unmatched unit or category; the tables contain wallpaper rows only.

## Not fixed — needs a decision

These passages carry no price, count or date, so they were left alone. They sit in classic (non-block) HTML that the section tools cannot reach, and changing them means rewriting the whole post content.

1. 17238 and 17240, section "أنواع ورق الجدران المتوفرة / Types of Wallpaper Available": the text says Texa Decor's range includes "ورق الجدران الأمريكي / American Wallpaper" and "ورق الجدران الطباعي المخصص / Custom Printed Wallpaper". The snapshot has neither.
2. 17238 and 17240 FAQ: "ما الفرق بين الورق الأمريكي والورق العادي؟ / What is the difference between American wallpaper and standard wallpaper?"; 17240 FAQ "best types of wallpaper" also names American wallpaper.
3. Excerpts: 17238 "الفرق بين الكوري والأمريكي", 17240 "Korean rolls versus American vinyl".
4. 17240 FAQ "best wallpaper brands" mentions "a workmanship guarantee" (pre-existing warranty wording).
5. 17238/17240 classic paragraph "أسعار ورق الجدران في الرياض… / Wallpaper Prices in Riyadh…" says to request a custom quote; it has no figures and was not touched.

## Verification

- Re-read 17238 and 17240 in full (raw, edit context) after the last edit; listed sections of all four posts.
- No remaining "64", "240", "245", "291", "720", "1,363", "أكتوبر", "October", "4 نوفمبر", "للمتر الطولي" or "per linear metre" in 17238, 17240, or the edited blocks of 18250 and 18255.
- Untouched blocks keep their original block hashes (18250 HTML block, 18255 HTML block and lead, 17238/17240 group block and "Browse" heading).
- Classic HTML in 17238 and 17240 reads identical to the pre-edit raw content in the re-read; it could not be hash-checked because the section tools do not expose a hash for classic content.
- Replaced blocks in 17238/17240 now use LF line endings inside the block where the originals had CRLF; this is whitespace only.
- The public REST endpoint returned 401 from this environment, so the rendered public pages were not fetched; verification is against the stored raw content.
- All `_content_warnings` arrays were empty.

## Rollback

WordPress revisions exist for every edit. Rendered backups: `texa/data/backup/post-<id>-before-round3.json`. Note that 18250 and 18255 had already been modified at 03:06–03:07 on 23 November, after those backups were saved (00:59).
