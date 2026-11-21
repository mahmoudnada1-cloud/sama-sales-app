<?php
/**
 * تكسا ديكور — إيقاف مؤقت لـ FAQ Schema الخاطئ في الصفحة الرئيسية
 *
 * استخدمه فقط إن تعذّر إصلاح المصدر من واجهة Rank Math (انظر fix-faq-schema-note.md).
 * مكان التركيب: wp-admin ← Snippets ← Add New — PHP — "Only run on site front-end".
 *   عند اللصق في Code Snippets احذف السطر الأول "<?php".
 *
 * الوضع الحالي (فُحص 2026-11-21): عقدة WebPage في الرئيسية نوعها ["WebPage","FAQPage"] وفيها
 * mainEntity بأربعة أسئلة عن بدائل الخشب والأثاث الخارجي والراتان، وهي غير ظاهرة في نص الصفحة.
 * هذا السنيبت يعيد العقدة إلى WebPage فقط ويحذف mainEntity، في الصفحة الرئيسية وحدها.
 *
 * التحقق: مصدر الصفحة الرئيسية لا يحوي "FAQPage" بعد مسح الكاش.
 * التراجع: عطّل السنيبت. ويُحذف نهائياً بعد إصلاح المصدر.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function texa_remove_home_faq_schema( $data ) {
	if ( ! is_array( $data ) || ! is_front_page() ) {
		return $data;
	}

	foreach ( $data as $key => $node ) {
		if ( ! is_array( $node ) || empty( $node['@type'] ) ) {
			continue;
		}

		// حالة 1: عقدة FAQPage مستقلة.
		if ( 'FAQPage' === $node['@type'] ) {
			unset( $data[ $key ] );
			continue;
		}

		// حالة 2 (الحالية): FAQPage مدموجة مع WebPage.
		if ( is_array( $node['@type'] ) && in_array( 'FAQPage', $node['@type'], true ) ) {
			$types = array_values( array_diff( $node['@type'], array( 'FAQPage' ) ) );
			$node['@type'] = 1 === count( $types ) ? $types[0] : $types;
			unset( $node['mainEntity'] );
			$data[ $key ] = $node;
		}
	}

	return $data;
}
add_filter( 'rank_math/json_ld', 'texa_remove_home_faq_schema', 98 );
