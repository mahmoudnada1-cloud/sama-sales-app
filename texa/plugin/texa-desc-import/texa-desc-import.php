<?php
/**
 * Plugin Name: Texa Description Import (temporary)
 * Description: One-off tool. Applies prepared product descriptions and Rank Math fields from bundled CSV files in small background batches, keeping a per-product backup. Deactivate to stop. Delete when finished.
 * Version: 1.0.0
 * Author: Texa Decor web team
 * Requires Plugins: woocommerce
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const TXA_DI_STATE  = 'txa_di_state';
const TXA_DI_HOOK   = 'txa_di_run_batch';
const TXA_DI_BATCH  = 40;
const TXA_DI_GAP    = 45;
const TXA_DI_BACKUP = '_txa_v4_backup';

/** CSV files bundled with this plugin, in a stable order. Nothing outside this folder is ever read. */
function txa_di_files() {
	$files = glob( __DIR__ . '/data/products-import-*.csv' );
	if ( ! is_array( $files ) ) {
		return array();
	}
	sort( $files );
	return array_map( 'basename', $files );
}

function txa_di_state() {
	$state = get_option( TXA_DI_STATE );
	if ( ! is_array( $state ) ) {
		$state = array(
			'files_done' => array(),
			'file'       => '',
			'offset'     => 0,
			'updated'    => 0,
			'skipped'    => 0,
			'errors'     => array(),
			'status'     => 'idle',
			'started'    => gmdate( 'c' ),
			'last_run'   => '',
			'report_id'  => 0,
		);
	}
	return $state;
}

function txa_di_pending_files( $state ) {
	return array_values( array_diff( txa_di_files(), $state['files_done'] ) );
}

function txa_di_is_scheduled() {
	if ( function_exists( 'as_has_scheduled_action' ) ) {
		return as_has_scheduled_action( TXA_DI_HOOK, null, 'txa-di' );
	}
	return (bool) wp_next_scheduled( TXA_DI_HOOK );
}

function txa_di_schedule( $delay ) {
	if ( txa_di_is_scheduled() ) {
		return;
	}
	if ( function_exists( 'as_schedule_single_action' ) ) {
		as_schedule_single_action( time() + $delay, TXA_DI_HOOK, array(), 'txa-di' );
	} else {
		wp_schedule_single_event( time() + $delay, TXA_DI_HOOK );
	}
}

function txa_di_unschedule() {
	if ( function_exists( 'as_unschedule_all_actions' ) ) {
		as_unschedule_all_actions( TXA_DI_HOOK, null, 'txa-di' );
	}
	wp_clear_scheduled_hook( TXA_DI_HOOK );
}

/** Keeps the job alive: if files remain and nothing is queued, queue the next batch. */
function txa_di_ensure() {
	if ( ! function_exists( 'wc_get_product' ) ) {
		return;
	}
	$state = txa_di_state();
	if ( txa_di_pending_files( $state ) ) {
		txa_di_schedule( 20 );
	}
}
add_action( 'action_scheduler_init', 'txa_di_ensure' );

register_deactivation_hook( __FILE__, 'txa_di_unschedule' );

/** Reads rows [offset, offset+limit) of one bundled CSV. */
function txa_di_read_rows( $file, $offset, $limit ) {
	$path = __DIR__ . '/data/' . basename( $file );
	$rows = array();
	$fh   = fopen( $path, 'r' );
	if ( ! $fh ) {
		return null;
	}
	$bom = fread( $fh, 3 );
	if ( "\xEF\xBB\xBF" !== $bom ) {
		rewind( $fh );
	}
	$header = fgetcsv( $fh, 0, ',', '"', '' );
	$i      = 0;
	$eof    = true;
	while ( false !== ( $row = fgetcsv( $fh, 0, ',', '"', '' ) ) ) {
		if ( $i >= $offset + $limit ) {
			$eof = false;
			break;
		}
		if ( $i >= $offset && is_array( $header ) && count( $row ) === count( $header ) ) {
			$rows[] = array_combine( $header, $row );
		}
		++$i;
	}
	fclose( $fh );
	return array( 'rows' => $rows, 'eof' => $eof );
}

function txa_di_apply_row( $row ) {
	$id = isset( $row['ID'] ) ? absint( $row['ID'] ) : 0;
	if ( ! $id || 'product' !== get_post_type( $id ) ) {
		return 'skipped';
	}
	$product = wc_get_product( $id );
	if ( ! $product ) {
		return 'skipped';
	}
	$desc  = isset( $row['Description'] ) ? (string) $row['Description'] : '';
	$short = isset( $row['Short description'] ) ? (string) $row['Short description'] : '';
	if ( '' === trim( $desc ) || false === strpos( $desc, 'txa-desc-v4' ) ) {
		return 'skipped';
	}
	$metas = array(
		'rank_math_title'         => isset( $row['Meta: rank_math_title'] ) ? (string) $row['Meta: rank_math_title'] : '',
		'rank_math_description'   => isset( $row['Meta: rank_math_description'] ) ? (string) $row['Meta: rank_math_description'] : '',
		'rank_math_focus_keyword' => isset( $row['Meta: rank_math_focus_keyword'] ) ? (string) $row['Meta: rank_math_focus_keyword'] : '',
	);

	// Back up the current values once, before the first change to this product.
	if ( ! metadata_exists( 'post', $id, TXA_DI_BACKUP ) ) {
		$backup = array(
			'description'       => $product->get_description( 'edit' ),
			'short_description' => $product->get_short_description( 'edit' ),
			'saved_at'          => gmdate( 'c' ),
		);
		foreach ( array_keys( $metas ) as $key ) {
			$backup[ $key ] = get_post_meta( $id, $key, true );
		}
		add_post_meta( $id, TXA_DI_BACKUP, wp_slash( wp_json_encode( $backup ) ), true );
	}

	$product->set_description( wp_kses_post( $desc ) );
	$product->set_short_description( sanitize_text_field( $short ) );
	foreach ( $metas as $key => $value ) {
		if ( '' !== $value ) {
			$product->update_meta_data( $key, sanitize_text_field( $value ) );
		}
	}
	$product->save();
	return 'updated';
}

function txa_di_run_batch() {
	if ( ! function_exists( 'wc_get_product' ) ) {
		return;
	}
	$state   = txa_di_state();
	$pending = txa_di_pending_files( $state );
	if ( ! $pending ) {
		$state['status'] = 'done';
		update_option( TXA_DI_STATE, $state, false );
		txa_di_report( $state );
		return;
	}
	if ( ! in_array( $state['file'], $pending, true ) ) {
		$state['file']   = $pending[0];
		$state['offset'] = 0;
	}
	$state['status'] = 'running';

	$chunk = txa_di_read_rows( $state['file'], $state['offset'], TXA_DI_BATCH );
	if ( null === $chunk ) {
		$state['errors'][]     = 'cannot open ' . $state['file'];
		$state['files_done'][] = $state['file'];
	} else {
		foreach ( $chunk['rows'] as $row ) {
			try {
				$result = txa_di_apply_row( $row );
			} catch ( Throwable $e ) {
				$result = 'error';
				if ( count( $state['errors'] ) < 50 ) {
					$state['errors'][] = ( isset( $row['ID'] ) ? absint( $row['ID'] ) : 0 ) . ': ' . $e->getMessage();
				}
			}
			if ( 'updated' === $result ) {
				++$state['updated'];
			} else {
				++$state['skipped'];
			}
		}
		$state['offset'] += TXA_DI_BATCH;
		if ( $chunk['eof'] ) {
			$state['files_done'][] = $state['file'];
			$state['file']         = '';
			$state['offset']       = 0;
		}
	}
	$state['last_run'] = gmdate( 'c' );
	if ( ! txa_di_pending_files( $state ) ) {
		$state['status'] = 'done';
	}
	update_option( TXA_DI_STATE, $state, false );
	txa_di_report( $state );
	if ( 'done' !== $state['status'] ) {
		txa_di_schedule( TXA_DI_GAP );
	}
}
add_action( TXA_DI_HOOK, 'txa_di_run_batch' );

/** Progress is written to one private post so it can be read without any new endpoint. */
function txa_di_report( $state ) {
	$body = wp_json_encode(
		array(
			'status'     => $state['status'],
			'updated'    => $state['updated'],
			'skipped'    => $state['skipped'],
			'files_done' => $state['files_done'],
			'current'    => $state['file'],
			'offset'     => $state['offset'],
			'errors'     => $state['errors'],
			'last_run'   => $state['last_run'],
		),
		JSON_UNESCAPED_UNICODE
	);
	$post = array(
		'post_title'   => 'txa-import-status',
		'post_content' => $body,
		'post_status'  => 'private',
		'post_type'    => 'post',
	);
	if ( ! empty( $state['report_id'] ) && get_post( $state['report_id'] ) ) {
		$post['ID'] = (int) $state['report_id'];
		wp_update_post( wp_slash( $post ) );
		return;
	}
	$id = wp_insert_post( wp_slash( $post ) );
	if ( $id && ! is_wp_error( $id ) ) {
		$state['report_id'] = (int) $id;
		update_option( TXA_DI_STATE, $state, false );
	}
}
