<?php
/**
 * Plugin Name: Texa Decor — Address as Jeddah only
 * Description: Shows the store address as the city only (Jeddah), without district or postal code, in the footer and in page content, as requested by the owner. Changes the displayed text only; writes nothing to the database.
 * Version: 1.1.0
 * Author: Texa Decor
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

function txa_fa_clean( $html ) {
	if ( ! is_string( $html ) || ( false === strpos( $html, 'النزلة' ) && false === strpos( $html, 'Nazlah' ) ) ) {
		return $html;
	}
	return str_replace(
		array(
			'حي النزلة الشرقية، جدة 22335',
			'An Nazlah Ash Sharqiyah Dist., Jeddah 22335',
		),
		array(
			'جدة',
			'Jeddah',
		),
		$html
	);
}
add_filter( 'render_block', 'txa_fa_clean', 20 );
add_filter( 'the_content', 'txa_fa_clean', 99 );
