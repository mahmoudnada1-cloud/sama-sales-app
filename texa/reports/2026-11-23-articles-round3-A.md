# Articles round 3 — A: wallpaper price guide (posts 26925 AR, 26937 EN)

Date: 2026-11-23. Site: texadecore.store. Both posts stayed `publish`.
Method: block-by-block with `wpcom-post-sections-replace` / `-remove` under hash locks; excerpt, title and meta via `wpcom-mcp-posts-update`. No classic (non-block) HTML in either post.
Backups: `texa/data/backup/post-26925-before-round3.json`, `post-26937-before-round3.json`, plus WordPress revisions.

## Facts used (recomputed from `texa/data/live-after2/p*.json`, snapshot 22 Nov 2026)

| Category | Designs | In stock | Range (SAR/roll) | Most common |
|---|---|---|---|---|
| ورق جدران (all) | 1,391 | 1,341 | 75–229 | 179 (355 designs) |
| تصميم ساده | 821 | 813 | 75–229 | 189 (213), then 179 (188) |
| ورق جدران أطفال | 53 | 11 | 174–229 | 229 (42) |

Price distribution (all wallpaper): 75×255, 109×84, 135×75, 166×52, 174×72, 178×38, 179×355, 189×262, 196×23, 199×39, 204×86, 229×50.
No product or category with "أمريكي" or "طباعة" wallpaper exists in the snapshot (0 matches in names, descriptions, categories).

Arithmetic used: 2 rolls = 150 / 358 / 458 (at 75 / 179 / 229); 2×174 = 348; 4 rolls = 300 / 716 / 916; 821÷1,391 = 59%.
EN m² figures: ÷16.5 → 4.55 / 10.85 / 13.88 (174 → 10.55); ÷13 → 5.77 / 13.77 / 17.62.

## Post 26925 (Arabic) — before → after per block (original indexes)

| # | Block | Before | After |
|---|---|---|---|
| 0 | lead paragraph | 64–245, 1,363 designs, 4 Nov; "except American and print, per linear metre" | 75–229 per roll, 1,391 designs, 22 Nov, most common 179; "price is per full roll, not per metre"; names Texa Decor as the source |
| 4 | list | item 2 = exception: American/print priced per metre, quoting the American product page | item 2 = Korean roll size 15.6 m × 106 cm = 16.5 m² (stated in product specs) |
| 5 | paragraph | "64 on an American product" / "245 on a Korean product … dearer than marble" | "229 on a Korean roll" mistaken for a metre; "75 per roll" vs a per-metre quote; marble comparison dropped |
| 7 | H2 | "… — نوفمبر 2026" | "… — 22 نوفمبر 2026" |
| 8 | paragraph | read on 4 Nov | read on 22 Nov |
| 9 | table | rows: all 1,363 / 64–245; plain 739 / 109–245 / 218–490; kids 104 / 174–240 / 348–480; American 10 / 64 per metre | rows: all 1,391 / 75–229 (mode 179) / 150–458; plain 821 / 75–229 (mode 189) / 150–458; kids 53 (11 in stock) / 174–229 / 348–458; American row removed; caption dated 22 Nov |
| 10 | paragraph | plain 739 of 1,363 "about half", 109–245 not 64–245; "in all Korean types" | plain 821 of 1,391 (~59%), same 75–229 range, mode 189 vs 179 |
| 13 | paragraph | two rolls = 218 (at 109) / 490 (at 245) | two rolls = 150 (75) / 358 (179) / 458 (229), dated 22 Nov; calculator rule text unchanged |
| 16 | worked example | 218 / 348 / 490 at 109 / 174 / 245 | 150 / 358 / 458 at 75 / 179 / 229, dated |
| 17 | paragraph | "starts from 218"; "cheapest way to change a room in the Kingdom, far cheaper than wood alternative" | "starts from 150 before adhesive and fitting"; unverifiable "cheapest" claims removed; wood-alternative link and unit comparison kept |
| 18 | image caption | "1,363 designs, the Korean ones sold by roll" | "1,391 designs sold by roll" |
| 20 | room table | kids "104 designs"; row "bathrooms and kitchens → American water-resistant" | kids "53 listed, 11 in stock on 22 Nov"; bathrooms row removed |
| 21 | paragraph | American wallpaper for bathrooms, SAR 64/metre, hospital/hotel, mould/bacteria/UV claims | **removed** |
| 27 | FAQ answer | per roll except American/print; 4 Nov, 64–245; 218 / 490 | per roll; 22 Nov, 75–229, mode 179; 150 / 358 / 458 |
| 29 | FAQ answer | 4 rolls = 436 (109) / 980 (245) | 4 rolls = 300 / 716 / 916 |
| 34–35 | FAQ "which wallpaper for bathrooms?" + answer (American, 64/metre, ten designs, mould/bacteria) | — | **removed** (heading and answer) |
| 36 | FAQ H3 | "… between 64 and 245?" | "… between 75 and 229 per roll?" |
| 37 | FAQ answer | "the two ends are different units (64 = American metre, 245 = Korean roll)"; plain 109–245; "embossed costs more than plain" | one unit (roll); price distribution 255@75, 355@179, 262@189, 50@229; plain covers the same 75–229; unverified "embossed dearer" claim removed |
| 41 | closing paragraph | 1,363 / 64–245; plain 739 / 109–245; kids 104 / 174–240; American link, 64 per metre | 1,391 / 75–229; plain 821 / 75–229; kids 53 / 174–229; American sentence and link removed |
| 42 | footer note | read 4 Nov, plus an added "22 Nov reading" sentence | single reading date 22 Nov |
| excerpt | | Nov 2026, 64–245, 1,363, "except American and print" | 22 Nov, 75–229 per roll, 1,391, mode 179, per full roll |
| meta `rank_math_description` | | per roll for Korean, per metre for American/print; 1,363; 4 Nov | per full roll; 1,391 designs 75–229; two rolls for 6 × 2.8 m; 22 Nov |

Unchanged: title, `rank_math_title`, blocks 1–3, 6, 11–12, 14–15, 19, 22–26, 28, 30–33, 38–40.

## Post 26937 (English) — before → after per block (original indexes)

| # | Block | Before | After |
|---|---|---|---|
| 0 | lead paragraph | SAR 64–240, 720 designs, October 2026; except American/print per metre; "SAR 6 to 15 per m²" | SAR 75–229 per roll, 1,391 designs, 22 Nov, mode 179; full roll not metre; 6 × 2.8 m wall = two rolls |
| 3 | list | item 2 = American/print exception | item 2 = roll size 15.6 m × 106 cm = 16.5 m² |
| 4 | paragraph | SAR 64 American / SAR 204 Korean / marble | SAR 229 roll mistaken for a metre; SAR 75 per roll vs per-metre quote |
| 6 | H2 | "— October 2026" | "— 22 November 2026" |
| 7 | paragraph | 22 October | 22 November |
| 8 | table | all 720 / 64–240 / 6–15; plain 476 / 105–204 / 6–12; kids 40 / 174–240 / 11–15; American 10 / 64 | all 1,391 / 75–229 (mode 179) / 4.5–13.9; plain 821 / 75–229 (mode 189) / 4.5–13.9; kids 53 (11 in stock) / 174–229 / 10.5–13.9; American row removed |
| 9 | paragraph | 476 of 720, two-thirds; 105–204 not 64–240; add SAR 2–3/m² for waste | 821 of 1,391 (~59%), same range, mode 189 vs 179; add SAR 1–4/m²; note that rolls are sold whole |
| 12 | paragraph | 105 → 6.40 / 8; 204 → 12.40 / 15.70 | 75 → 4.55 / 5.77; 179 → 10.85 / 13.77; 229 → 13.88 / 17.62 |
| 15 | worked example | 210 / 408 / 480 at 105 / 204 / 240 | 150 / 358 / 458 at 75 / 179 / 229, dated |
| 16 | paragraph | "starts at roughly SAR 200"; "cheapest way … several times the cost per m²" | "starts at SAR 150 before adhesive and fitting"; unverifiable cost claims removed; cladding link kept |
| 17 | image caption | 720 designs | 1,391 designs |
| 19 | room table | kids "40 designs"; bathrooms row (American) | kids "53 listed, 11 in stock on 22 Nov"; bathrooms row removed |
| 20 | paragraph | American wallpaper for bathrooms, SAR 64/metre, hospital/hotel claims | **removed** |
| 26 | FAQ answer | SAR 6–15 / 8–18 per m²; except American/print | SAR 4.5–14 / about 6–18 per m², from 75–229 per roll on 22 Nov; per roll |
| 28 | FAQ answer | four rolls ≈ SAR 420 at 105 | SAR 300 / 716 / 916 at 75 / 179 / 229 |
| 33–34 | FAQ "Which wallpaper is suitable for bathrooms?" + answer | — | **removed** |
| 35 | FAQ H3 | "… from SAR 64 to SAR 240?" | "… from SAR 75 to SAR 229 per roll?" |
| 36 | FAQ answer | different units (American metre vs Korean roll); embossed dearer | one unit; price distribution; plain covers the same range |
| 40 | closing paragraph | 720 / 64–240; plain 476 / 105–204; kids 40 / 174–240; American 64 per metre | 1,391 / 75–229; plain 821 / 75–229; kids 53 / 174–229; American sentence and link removed |
| 41 | footer note | 22 October | 22 November ("prices and counts") |
| title | | "… 2026: SAR 64 to 240, and the Unit That Changes Every Calculation" | "… 2026: SAR 75 to 229 per Roll, and the Unit That Changes Every Calculation" |
| excerpt | | October 2026, 64–240, 720, except American/print | 22 Nov, 75–229 per roll, 1,391, mode 179, per full roll |

Unchanged: slug (`wallpaper-prices-riyadh-en`), `rank_math_title`, `rank_math_description` (carries no numbers or dates), and all other blocks.

## Verification after edit (re-read of raw content, both posts)

- No remaining "245", "240", "1,363", "720", "739", "476", "104", "64", "أمريكي"/"American", "الطباعة"/"print wallpaper", "October", "4 نوفمبر", "22 October".
- Every price statement carries "22 نوفمبر 2026" / "22 November 2026".
- Cost arithmetic rechecked: 150 / 358 / 458 / 348 / 300 / 716 / 916; m² figures rechecked.
- Roll counts follow the calculator rule: wall 6 m = 7 strips ÷ 5 = 2 rolls; room 3 × 4 = 4; room 4 × 5 = 6.
- Block comments balanced; the three removals per post left only blank lines.
- Status `publish` on both.

## Left as is (not verified against the catalogue, outside the price brief)

- Room-table wording "قابل للمسح / wipeable", "فينيل مقاوم للاحتكاك / scuff-resistant vinyl", and "13 to 14 m² net per roll" — pre-existing descriptive claims, not checked against product pages.
- General market paragraphs (block 1, the "SAR 5 per metre" section) still mention per-metre quoting by other sellers; that is about the market, not this store.
- Bathrooms/kitchens now have no recommendation in either post, because the only product named for them no longer exists in the catalogue.
- The EN post keeps its square-metre conversion section (AR dropped it in an earlier round); figures were updated rather than removed.
