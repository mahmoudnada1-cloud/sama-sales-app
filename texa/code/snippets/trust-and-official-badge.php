<?php
/**
 * تكسا ديكور — إدراج شارة "المتجر الرسمي" في الهيدر وشريط الثقة تحت زر "إضافة إلى السلة"
 *
 * بديل عن اللصق اليدوي لملفي html/official-badge.html و html/trust-strip.html في محرر الموقع.
 * استخدم طريقة واحدة فقط (السنيبت أو اللصق اليدوي) حتى لا يتكرر العنصر.
 *
 * مكان التركيب: wp-admin ← Snippets ← Add New — PHP — "Only run on site front-end".
 *   عند اللصق في Code Snippets احذف السطر الأول "<?php".
 *   يُركَّب معه css/footer-mobile.css (القسمان 2 و 3).
 *
 * البنية التي يعتمد عليها (فُحصت على الموقع الحي 2026-11-21):
 *   - الهيدر: header.wp-block-template-part > .decorati-home > header.site > .header-inner > a.logo
 *   - صفحة المنتج (قالب بلوكات): form.wc-block-add-to-cart-with-options.cart
 * إن لم يجد البنية المتوقعة لا يضيف شيئاً (لا يكسر الصفحة).
 *
 * التحقق: الشارة تظهر بعد الشعار، والشريط تحت نموذج الإضافة للسلة في أي صفحة منتج.
 * التراجع: عطّل السنيبت وامسح الكاش. لا يكتب شيئاً في قاعدة البيانات ولا يعدّل القوالب.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! defined( 'TEXA_TODO_OFFICIAL_PAGE_URL' ) ) {
	// يحتاج تأكيد من المالك: رابط صفحة القنوات الرسمية بعد نشرها. التقارير اقترحت ثلاثة مسارات
	// مختلفة (/official-channels/ و /official-store/ و /القنوات-الرسمية/) والصفحة غير منشورة بعد.
	// ما دامت القيمة فارغة تُعرض الشارة نصاً بلا رابط (حتى لا تقود إلى 404).
	define( 'TEXA_TODO_OFFICIAL_PAGE_URL', '' );

	// يحتاج تأكيد من المالك: تفعيل كل عنصر على حدة.
	define( 'TEXA_SHOW_OFFICIAL_BADGE', true );
	define( 'TEXA_SHOW_TRUST_STRIP', true );

	// مؤكد من تذييل الموقع الحي.
	define( 'TEXA_TRUST_CR_NUMBER', '7055107622' );
	define( 'TEXA_TRUST_RETURNS_PATH', '/سياسة-الاستبدال-والاسترجاع/' );
}

function texa_official_badge_html() {
	$icon  = '<svg aria-hidden="true" focusable="false" width="14" height="14" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm-1.2 14.2-3.5-3.5 1.4-1.4 2.1 2.1 4.5-4.5 1.4 1.4-5.9 5.9Z"/></svg>';
	$label = '<span class="texa-official__label">المتجر الرسمي لتكسا ديكور</span>'
		. '<span class="texa-official__domain" dir="ltr" translate="no">texadecore.store</span>';

	if ( '' !== TEXA_TODO_OFFICIAL_PAGE_URL ) {
		return '<a class="texa-official" href="' . esc_url( TEXA_TODO_OFFICIAL_PAGE_URL ) . '">' . $icon . $label . '</a>';
	}
	return '<span class="texa-official">' . $icon . $label . '</span>';
}

function texa_trust_strip_html() {
	$returns = esc_url( home_url( TEXA_TRUST_RETURNS_PATH ) );

	return '<ul class="texa-trust" aria-label="معلومات الثقة">'
		. '<li class="texa-trust__item"><svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M17 9V7A5 5 0 0 0 7 7v2H5v12h14V9h-2ZM9 7a3 3 0 0 1 6 0v2H9V7Zm3 10.5a2 2 0 1 1 0-4 2 2 0 0 1 0 4Z"/></svg>'
		. '<span>دفع آمن: مدى، Visa، Apple Pay، tabby</span></li>'
		. '<li class="texa-trust__item"><svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M12 5V2L7 6l5 4V7a5 5 0 1 1-5 5H5a7 7 0 1 0 7-7Z"/></svg>'
		. '<a href="' . $returns . '">سياسة الاستبدال والاسترجاع</a></li>'
		. '<li class="texa-trust__item"><svg aria-hidden="true" focusable="false" width="20" height="20" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2 4 5v6c0 5 3.4 9.7 8 11 4.6-1.3 8-6 8-11V5l-8-3Zm-1.2 14.2-3.5-3.5 1.4-1.4 2.1 2.1 4.5-4.5 1.4 1.4-5.9 5.9Z"/></svg>'
		. '<span>منشأة مسجّلة · س.ت <span dir="ltr">' . esc_html( TEXA_TRUST_CR_NUMBER ) . '</span></span></li>'
		. '</ul>';
}

/**
 * @param string $content HTML البلوك بعد العرض.
 * @param array  $block   بيانات البلوك.
 * @return string
 */
function texa_trust_render_block( $content, $block ) {
	if ( ! is_string( $content ) || '' === $content || empty( $block['blockName'] ) ) {
		return $content;
	}

	// 1) الشارة: داخل جزء القالب الذي يحوي الهيدر المخصص، بعد رابط الشعار مباشرة.
	if ( TEXA_SHOW_OFFICIAL_BADGE
		&& 'core/template-part' === $block['blockName']
		&& false !== strpos( $content, '<header class="site">' )
		&& false === strpos( $content, 'class="texa-official"' ) ) {
		$out = preg_replace(
			'#(<a\b[^>]*\bclass="logo"[^>]*>.*?</a>)#s',
			'$1' . str_replace( '$', '\$', texa_official_badge_html() ),
			$content,
			1
		);
		return null === $out ? $content : $out;
	}

	// 2) شريط الثقة: بعد نموذج الإضافة للسلة في صفحة المنتج المفرد فقط.
	if ( TEXA_SHOW_TRUST_STRIP
		&& in_array( $block['blockName'], array( 'woocommerce/add-to-cart-with-options', 'woocommerce/add-to-cart-form' ), true )
		&& function_exists( 'is_product' ) && is_product()
		&& false === strpos( $content, 'class="texa-trust"' ) ) {
		static $texa_trust_done = false;
		if ( $texa_trust_done ) {
			return $content; // مرة واحدة فقط في الصفحة.
		}
		$texa_trust_done = true;
		return $content . texa_trust_strip_html();
	}

	return $content;
}
add_filter( 'render_block', 'texa_trust_render_block', 20, 2 );
