<?php
/**
 * Snippet: llms.txt Custom Preamble (Rank Math)
 * الغرض: إضافة محتوى مخصص لهوية المؤسسة وخدماتها في ملف llms.txt
 *
 * ملاحظة: Rank Math يولّد /llms.txt تلقائياً بالمقالات والصفحات.
 * هذا الـ snippet يُضيف معلومات الهوية والخدمات في أعلى الملف.
 *
 * مكان التركيب: Code Snippets (wp-admin > Snippets > Add New)
 *   - العنوان: Texa — llms.txt Custom Preamble
 *   - النوع: Run Everywhere
 *   - الحالة: Active
 *
 * التحقق بعد التركيب:
 *   1. افتح https://texadecore.store/llms.txt
 *   2. تأكد من وجود "# تكسا ديكور" في أعلى الملف
 *
 * التراجع:
 *   - عطّل الـ Snippet أو احذفه من Code Snippets
 */

add_action( 'template_redirect', 'texa_llms_txt_custom', 1 );

function texa_llms_txt_custom() {
    // تحقق من أننا في صفحة /llms.txt
    $request = isset( $_SERVER['REQUEST_URI'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ) ) : '';

    if ( '/llms.txt' !== rtrim( strtok( $request, '?' ), '/' ) ) {
        return;
    }

    // اسمح لـ Rank Math بتوليد المحتوى الأصلي أولاً، ثم أضف رأس الملف
    // (يعمل باعتراض الـ output buffer)
    ob_start( 'texa_prepend_llms_preamble' );
}

function texa_prepend_llms_preamble( $buffer ) {
    $preamble = <<<'LLMS'
# تكسا ديكور — Texa Decor
> متجر إلكتروني سعودي متخصص في ديكور الجدران والأرضيات، يخدم جميع مناطق المملكة العربية السعودية.
> موقع الويب: https://texadecore.store

## الهوية
- **الاسم التجاري**: تكسا ديكور (Texa Decor)
- **الكيان القانوني**: شركة ميراس جروث هولدينج شركة شخص واحد ذ.م.م
- **السجل التجاري**: 7055107622
- **الرقم الضريبي**: 314997835900003
- **المقر الرئيسي**: جدة، المملكة العربية السعودية
- **الهاتف/واتساب**: +966 59 140 9002
- **البريد الإلكتروني**: texadecore@gmail.com
- **انستغرام**: https://www.instagram.com/texa_decor_sa/
- **تيك توك**: https://www.tiktok.com/@texa_decor_sa

## المنتجات الرئيسية
- **ورق الجدران**: كوري، مودرن، +850 منتج — /product-category/wallpaper/
- **باركيه وأرضيات**: SPC مقاوم للماء، هرمي، خشبي — /product-category/flooring/
- **تكسيات الجدران**: داخلية وخارجية، بديل الحجر، الرخام، الطوب
- **أرضيات إيبوكسي وموكيت**

## الخدمات
- **خدمات التركيب**: الرياض، جدة، الدمام، المدينة المنورة، مكة — /install-services/
- **خدمة رفع المقاس**: 150 ر.س — زيارة فني منزلك لأخذ القياسات
- **حاسبة الكميات**: احسب كمية ورق الجدران والأرضيات — /quantity-calculator/
- **دليل الشراء**: /buying-guide/

## أسئلة شائعة
- **هل يشمل السعر الضريبة؟** نعم، جميع الأسعار شاملة ضريبة القيمة المضافة (15%).
- **ما سياسة الشحن؟** شحن لجميع مناطق المملكة، الوقت المعتاد 3-7 أيام عمل.
- **هل يمكن الاستبدال والإرجاع؟** نعم، خلال 7 أيام من الاستلام وفق الشروط.
- **كيف أحسب الكمية؟** استخدم حاسبتنا على /quantity-calculator/ أو تواصل معنا.
- **هل تتوفر خدمات تركيب؟** نعم، في الرياض وجدة والدمام والمدينة ومكة.

---

LLMS;

    return $preamble . $buffer;
}
