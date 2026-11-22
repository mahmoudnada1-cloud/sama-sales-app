<?php
/**
 * Plugin Name: Texa Decor — Family Guide (single source)
 * Description: Shows each product family's buying guide on the product page from one stored copy per family, instead of a copy saved inside every product description. Read-only: writes nothing to the database.
 * Version: 1.0.0
 * Author: Texa Decor
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Loads one of the bundled data files (a PHP file returning an array). Returns array() on any problem.
 */
function txa_fg_data( $name ) {
	static $cache = array();
	if ( ! isset( $cache[ $name ] ) ) {
		$file           = __DIR__ . '/data/' . $name . '.php';
		$data           = is_readable( $file ) ? include $file : array();
		$cache[ $name ] = is_array( $data ) ? $data : array();
	}
	return $cache[ $name ];
}

/**
 * The guide block for one product: heading + family guide. Empty string when the product has none.
 */
function txa_fg_html( $product_id ) {
	$product_id = (int) $product_id;
	$map        = txa_fg_data( 'map' );
	if ( ! $product_id || empty( $map[ $product_id ] ) || ! is_array( $map[ $product_id ] ) ) {
		return '';
	}
	list( $family, $keyword ) = $map[ $product_id ];
	$guides = txa_fg_data( 'guides' );
	if ( empty( $guides[ $family ] ) || ! is_array( $guides[ $family ] ) ) {
		return '';
	}
	list( $title, $html ) = $guides[ $family ];
	if ( '' === trim( (string) $html ) ) {
		return '';
	}
	return '<h2>' . esc_html( $keyword . ': ' . $title ) . "</h2>\n" . $html;
}

/**
 * Adds the guide to the description of the product being viewed, in its original place
 * (before the closing links paragraph). Descriptions that still hold their own copy are left alone.
 */
function txa_fg_append( $content ) {
	if ( is_admin() || ! is_string( $content ) || ! function_exists( 'is_singular' ) || ! is_singular( 'product' ) ) {
		return $content;
	}
	$id = (int) get_the_ID();
	if ( ! $id || (int) get_queried_object_id() !== $id ) {
		return $content; // Related products and other loops on the page stay short.
	}
	$mark = strpos( $content, '<!-- txa-desc-v' );
	if ( false === $mark || false !== strpos( $content, 'txa-family' ) ) {
		return $content;
	}
	$guide = txa_fg_html( $id );
	if ( '' === $guide ) {
		return $content;
	}
	$head = substr( $content, 0, $mark );
	$at   = strrpos( $head, '<p>' );
	if ( false === $at ) {
		$at = $mark;
	}
	return substr( $content, 0, $at ) . $guide . "\n" . substr( $content, $at );
}
add_filter( 'the_content', 'txa_fg_append', 5 );

/**
 * Product editor: lets Rank Math's content analysis count the guide the visitor sees on the page.
 */
function txa_fg_rank_math( $hook ) {
	if ( 'post.php' !== $hook || ! function_exists( 'get_current_screen' ) ) {
		return;
	}
	$screen = get_current_screen();
	if ( ! $screen || 'product' !== $screen->post_type ) {
		return;
	}
	$id    = isset( $_GET['post'] ) ? absint( $_GET['post'] ) : 0; // phpcs:ignore WordPress.Security.NonceVerification.Recommended
	$guide = txa_fg_html( $id );
	if ( '' === $guide ) {
		return;
	}
	wp_register_script( 'txa-fg-rank-math', false, array( 'wp-hooks' ), '1.0.0', true );
	wp_enqueue_script( 'txa-fg-rank-math' );
	wp_add_inline_script(
		'txa-fg-rank-math',
		'(function(){if(!window.wp||!wp.hooks)return;var g=' . wp_json_encode( "\n" . $guide ) . ';wp.hooks.addFilter("rank_math_content","texa/family-guide",function(c){c=String(c||"");return c.indexOf("txa-family")>-1?c:c+g;});})();'
	);
}
add_action( 'admin_enqueue_scripts', 'txa_fg_rank_math' );
