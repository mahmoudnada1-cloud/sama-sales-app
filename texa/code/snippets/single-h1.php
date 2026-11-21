<?php
/**
 * تكسا ديكور — H1 واحد في الصفحة الرئيسية (حل مؤقت إلى أن يُعدَّل المصدر)
 *
 * اقرأ single-h1.md أولاً: وسما H1 الزائدان ليسا ودجت Heading في Elementor، بل يخرجان من
 * الإضافة المخصصة texa-home-rows ومن قسم section.texa-seo-intro، فلا يمكن تغييرهما من قائمة
 * "HTML Tag" في Elementor. الحل الدائم تعديل المصدر؛ هذا السنيبت بديل لا يلمس ملفات الإضافة.
 *
 * مكان التركيب: wp-admin ← Snippets ← Add New — PHP — "Only run on site front-end".
 *   عند اللصق في Code Snippets احذف السطر الأول "<?php".
 *   يُركَّب معه css/single-h1.css (وإلا يفقد العنوان تنسيقه، لأن CSS الحالي يستهدف h1.txhr-welcome).
 *
 * ماذا يفعل: يعدّل HTML الصفحة الرئيسية فقط قبل إرساله (output buffer)، ولا يكتب في قاعدة البيانات.
 * التحقق: في مصدر الصفحة الرئيسية عدد "<h1" خارج وسوم script يساوي 1.
 * التراجع: عطّل السنيبت واحذف CSS المرافق ثم امسح الكاش.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! defined( 'TEXA_TODO_H1_MODE' ) ) {
	/*
	 * يحتاج تأكيد من المالك (مع خبير SEO):
	 *  'demote_welcome'      (الافتراضي، بلا تغيير مرئي):
	 *        "أهلاً بك في تكسا للديكور السعودية" يصبح H2، ويبقى H1 الوحيد هو
	 *        "تكسا ديكور - ورق جدران وتكسيات وأرضيات وبديل رخام في السعودية".
	 *        تنبيه: هذا الـH1 مخفي حالياً بـ CSS (.texa-seo-intro{display:none!important})،
	 *        فيبقى H1 الصفحة غير مرئي للزائر إلى أن يُعالج (انظر single-h1.md).
	 *  'visible_keyword_h1'  (تغيير مرئي):
	 *        العنوان الظاهر نفسه يصبح H1 بنص "تكسا ديكور - ورق جدران ..." بدل عبارة الترحيب،
	 *        والـH1 المخفي يتحول إلى فقرة. النتيجة: H1 واحد ظاهر يبدأ باسم العلامة.
	 */
	define( 'TEXA_TODO_H1_MODE', 'demote_welcome' );
}

function texa_single_h1_buffer( $html ) {
	if ( ! is_string( $html ) || '' === $html ) {
		return $html;
	}

	$welcome_re = '#<h1(\s[^>]*\bclass="[^"]*\btxhr-welcome\b[^"]*"[^>]*)>(.*?)</h1>#su';
	$intro_re   = '#(<section\b[^>]*\bclass="[^"]*\btexa-seo-intro\b[^"]*"[^>]*>\s*<div\b[^>]*>\s*)<h1(\b[^>]*)>(.*?)</h1>#su';

	if ( 'visible_keyword_h1' === TEXA_TODO_H1_MODE ) {
		if ( ! preg_match( $intro_re, $html, $m ) || ! preg_match( $welcome_re, $html ) ) {
			return $html; // البنية تغيّرت: لا نعدّل شيئاً.
		}
		$headline = $m[3];
		$out      = preg_replace( $intro_re, '$1<p class="texa-seo-intro-title"$2>$3</p>', $html, 1 );
		$out      = null === $out ? $html : $out;
		$out2     = preg_replace_callback(
			$welcome_re,
			function ( $w ) use ( $headline ) {
				return '<h1' . $w[1] . '>' . $headline . '</h1>';
			},
			$out
		);
		return null === $out2 ? $html : $out2;
	}

	// الافتراضي: عبارة الترحيب تصبح H2.
	$out = preg_replace( $welcome_re, '<h2$1>$2</h2>', $html );
	return null === $out ? $html : $out;
}

function texa_single_h1_start() {
	if ( is_admin() || is_feed() || ! is_front_page() ) {
		return;
	}
	// لا يعمل داخل محرر Elementor أو المعاينة.
	if ( isset( $_GET['elementor-preview'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended
		return;
	}
	ob_start( 'texa_single_h1_buffer' );
}
add_action( 'template_redirect', 'texa_single_h1_start', 1 );
