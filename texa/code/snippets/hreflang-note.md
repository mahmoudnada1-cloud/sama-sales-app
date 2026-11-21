# hreflang: العربية فقط، بلا en ولا x-default

## ما تم التحقق منه (الموقع الحي 2026-11-21)

- **إضافة الترجمة: TranslatePress** — مؤكد من مصدر الصفحة: مسار `wp-content/plugins/translatepress-multilingual/`، صنف `translatepress-ar` على `<body>`، وأصناف `trp-language-switcher`. لا أثر لـ WPML ولا Polylang. (النسخة المجانية أم المدفوعة: غير معروف من الواجهة العامة.)
- الرئيسية العربية تخرج وسماً واحداً فقط، وصيغته هي صيغة TranslatePress:
  `<link rel="alternate" hreflang="ar" href="https://texadecore.store/"/>`
- `<html dir="rtl" lang="ar">` و canonical = `https://texadecore.store/` — سليمان.
- زرّا اللغة في الهيدر (`a.texa-lang-btn.texa-lang-en` / `.texa-lang-ar`) **بلا `href` في HTML**؛ يملؤهما سكربت `setupLang()` بعد التحميل. الزاحف الذي لا ينفّذ JavaScript لا يجد منهما رابطاً إلى `/en/`.
- **لم أتمكن من فحص `/en/`**: الخادم أعاد 429 (Too Many Requests) بعد أربع صفحات. فلا أعرف هل تخرج النسخة الإنجليزية وسوم hreflang، وما قيمة `lang` و canonical فيها.

## التشخيص

TranslatePress يطبع تلقائياً وسم hreflang لكل لغة **منشورة للزوار**. ظهور العربية وحدها يعني أحد أمرين — يُحسم من wp-admin لا بالتخمين:

| # | الاحتمال | كيف تتحقق | الإصلاح |
|---|---|---|---|
| 1 | الإنجليزية مضافة لكنها **غير مفعّلة للزوار** (عمود "Active" غير محدد — يظهر مع إضافة Multiple Languages؛ اللغة غير المفعّلة يراها المدير فقط ولا يخرج لها hreflang) | الإعدادات ← TranslatePress ← General ← جدول All Languages. وافتح `/en/` في نافذة خاصة (بدون تسجيل دخول) | حدّد Active للإنجليزية ثم Save Changes |
| 2 | كود مخصص يحذف الوسوم (فلتر `trp_hreflang`، أو إزالة الإجراء الذي يطبعها في `wp_head`) | Snippets: ابحث عن `hreflang` و `trp_hreflang` | عدّل أو عطّل الكود |
| 3 | النسخة الإنجليزية لا يولّدها TranslatePress أصلاً (مسار `/en/` من مصدر آخر) | هل `/en/` مدرجة في جدول اللغات بالـslug ‏`en`؟ | يُبحث حسب المصدر الفعلي |

## الإصلاح في TranslatePress

1. نسخة احتياطية، ويفضّل Staging.
2. **الإعدادات ← TranslatePress ← General**: تأكد أن الإنجليزية في All Languages بالـslug ‏`en` ومفعّلة، وأن Default Language = العربية.
3. **الإعدادات ← TranslatePress ← Advanced** (قسم الخيارات المتفرقة/Miscellaneous — اسم القسم قد يختلف حسب الإصدار، يحتاج تحقق):
   - **Set x-default hreflang** ← اختر **العربية** (اللغة الافتراضية والسوق الأساسي).
   - **Remove duplicate hreflang**: TranslatePress يطبع للإنجليزية وسمين (`en-US` و `en`). الأنسب للسعودية إبقاء الوسم المستقل عن المنطقة (`en`) وإزالة وسم البلد (`en-US`)، فالجمهور ليس أمريكياً. للعربية الوسم `ar` كما هو.
4. Save، ثم امسح كل طبقات الكاش.

## الناتج المطلوب في `<head>` (في النسختين)

```html
<link rel="alternate" hreflang="ar" href="https://texadecore.store/"/>
<link rel="alternate" hreflang="en" href="https://texadecore.store/en/"/>
<link rel="alternate" hreflang="x-default" href="https://texadecore.store/"/>
```

الشروط: الوسوم متبادلة (نفس المجموعة في العربية والإنجليزية)، وكل نسخة canonical لنفسها (`/en/` لا تشير إلى العربية)، و`<html lang="en">` في الإنجليزية.

## لا أنصح بطباعة الوسوم يدوياً بسنيبت

إن فُعّلت اللغة لاحقاً تتكرر الوسوم وتتعارض، والروابط العربية المرمّزة تحتاج دالة TranslatePress نفسها لتحويل المسار. لذلك لم أجهّز كوداً لهذا البند؛ الإصلاح من الإعدادات.

## بند مرتبط (صغير)

أضف `href` حقيقياً لزرّي اللغة في HTML الهيدر (`/en/` للإنجليزي و`/` للعربي كقيمة أولية)، والسكربت يعدّلهما بعد التحميل كما يفعل الآن. مكانه: المظهر ← المحرر ← أجزاء القالب ← Header.

## التحقق

1. مصدر الرئيسية ومصدر `/en/`: ثلاثة وسوم `hreflang` متطابقة.
2. صفحة قسم وصفحة منتج: الروابط تشير إلى الصفحة المقابلة لا إلى الرئيسية.
3. Search Console ← فحص عنوان URL لـ`/en/`: canonical الذي اختاره جوجل هو `/en/`.

## التراجع

أعد الإعدادات إلى قيمها السابقة (صوّرها قبل التغيير) وامسح الكاش.
