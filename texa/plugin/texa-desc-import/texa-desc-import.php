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
const TXA_DI_BUDGET = 20; // Seconds of work per batch; the rest of the batch waits for the next run.
const TXA_DI_MAXLOG = 200;
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
			'unchanged'  => 0,
			'last_secs'  => 0,
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

/** True only when a batch is waiting in the queue (a batch that is running right now does not count). */
function txa_di_has_pending() {
	if ( function_exists( 'as_get_scheduled_actions' ) && class_exists( 'ActionScheduler_Store' ) ) {
		$ids = as_get_scheduled_actions(
			array(
				'hook'     => TXA_DI_HOOK,
				'group'    => 'txa-di',
				'status'   => ActionScheduler_Store::STATUS_PENDING,
				'per_page' => 1,
			),
			'ids'
		);
		return ! empty( $ids );
	}
	return (bool) wp_next_scheduled( TXA_DI_HOOK );
}

/**
 * Queues the next batch. $from_batch = true is used by the running batch itself: Action Scheduler
 * reports the running batch as "scheduled", so in that case only a waiting batch blocks a new one.
 */
function txa_di_schedule( $delay, $from_batch = false ) {
	if ( $from_batch ? txa_di_has_pending() : txa_di_is_scheduled() ) {
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
	// At most one check per minute, so ordinary page views do not pay for a queue lookup.
	if ( get_transient( 'txa_di_tick' ) ) {
		return;
	}
	set_transient( 'txa_di_tick', 1, MINUTE_IN_SECONDS );
	$state = txa_di_state();
	if ( txa_di_pending_files( $state ) ) {
		txa_di_schedule( 20 );
	}
}
add_action( 'action_scheduler_init', 'txa_di_ensure' );

register_deactivation_hook( __FILE__, 'txa_di_unschedule' );

/**
 * Reads rows [offset, offset+limit) of one bundled CSV. Every data line in the range yields exactly
 * one entry (null when its column count is wrong), so offsets always match line positions.
 */
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
		if ( $i >= $offset ) {
			$rows[] = ( is_array( $header ) && count( $row ) === count( $header ) ) ? array_combine( $header, $row ) : null;
		}
		++$i;
	}
	fclose( $fh );
	return array( 'rows' => $rows, 'eof' => $eof );
}

/** Returns 'updated', 'unchanged', or 'skipped: <reason>'. Throws only on unexpected errors. */
function txa_di_apply_row( $row ) {
	$id = isset( $row['ID'] ) ? absint( $row['ID'] ) : 0;
	if ( ! $id || 'product' !== get_post_type( $id ) ) {
		return 'skipped: not a product';
	}
	$product = wc_get_product( $id );
	if ( ! $product ) {
		return 'skipped: product not loadable';
	}
	$desc  = isset( $row['Description'] ) ? (string) $row['Description'] : '';
	$short = isset( $row['Short description'] ) ? (string) $row['Short description'] : '';
	if ( '' === trim( $desc ) || false === strpos( $desc, 'txa-desc-v4' ) ) {
		return 'skipped: description missing or not v4';
	}
	$metas = array(
		'rank_math_title'         => isset( $row['Meta: rank_math_title'] ) ? (string) $row['Meta: rank_math_title'] : '',
		'rank_math_description'   => isset( $row['Meta: rank_math_description'] ) ? (string) $row['Meta: rank_math_description'] : '',
		'rank_math_focus_keyword' => isset( $row['Meta: rank_math_focus_keyword'] ) ? (string) $row['Meta: rank_math_focus_keyword'] : '',
	);

	// Current values, read before anything is changed on the object.
	$backup = array(
		'description'       => $product->get_description( 'edit' ),
		'short_description' => $product->get_short_description( 'edit' ),
		'saved_at'          => gmdate( 'c' ),
	);
	foreach ( array_keys( $metas ) as $key ) {
		$backup[ $key ] = get_post_meta( $id, $key, true );
	}

	$product->set_description( wp_kses_post( $desc ) );
	$product->set_short_description( sanitize_text_field( $short ) );
	$meta_changed = false;
	foreach ( $metas as $key => $value ) {
		$value = sanitize_text_field( $value );
		if ( '' !== $value && (string) $backup[ $key ] !== $value ) {
			$product->update_meta_data( $key, $value );
			$meta_changed = true;
		}
	}
	if ( ! $meta_changed && ! $product->get_changes() ) {
		return 'unchanged'; // Already applied (re-run): no save, no new modified date.
	}

	// WooCommerce re-aligns stock fields on every save. Refuse the product if that would write
	// anything besides the two description fields, so price and stock data are never touched here.
	$probe = clone $product;
	if ( is_callable( array( $probe, 'validate_props' ) ) ) {
		$probe->validate_props();
	}
	$extra = array_diff( array_keys( $probe->get_changes() ), array( 'description', 'short_description' ) );
	if ( $extra ) {
		return 'skipped: save would also change ' . implode( ',', $extra );
	}

	// Back up once, before the first change to this product. No stored backup = no change.
	if ( ! metadata_exists( 'post', $id, TXA_DI_BACKUP ) ) {
		$json = wp_json_encode( $backup );
		if ( ! is_string( $json ) || '' === $json || ! add_post_meta( $id, TXA_DI_BACKUP, wp_slash( $json ), true ) ) {
			return 'skipped: backup could not be stored';
		}
	}

	// Background runs have no logged-in user, so WordPress would re-filter the product NAME on save
	// (a bare "&" becomes "&amp;"). The name is not ours to change: switch that one filter off for this save.
	$title_kses = has_filter( 'title_save_pre', 'wp_filter_kses' );
	if ( false !== $title_kses ) {
		remove_filter( 'title_save_pre', 'wp_filter_kses', $title_kses );
	}
	try {
		$product->save();
	} finally {
		if ( false !== $title_kses ) {
			add_filter( 'title_save_pre', 'wp_filter_kses', $title_kses );
		}
	}
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
		$started = microtime( true );
		$budget  = (float) apply_filters( 'txa_di_time_budget', TXA_DI_BUDGET );
		$done    = 0;
		foreach ( $chunk['rows'] as $row ) {
			// Stop early on a slow server; the unprocessed rows are picked up by the next batch.
			if ( $done > 0 && ( microtime( true ) - $started ) > $budget ) {
				break;
			}
			$row_id = ( is_array( $row ) && isset( $row['ID'] ) ) ? absint( $row['ID'] ) : 0;
			if ( ! is_array( $row ) ) {
				$result = 'skipped: malformed CSV line (data row ' . ( $state['offset'] + $done + 1 ) . ' of ' . $state['file'] . ')';
			} else {
				try {
					$result = txa_di_apply_row( $row );
				} catch ( Throwable $e ) {
					$result = 'error: ' . $e->getMessage();
				}
			}
			if ( 'updated' === $result ) {
				++$state['updated'];
			} elseif ( 'unchanged' === $result ) {
				$state['unchanged'] = ( isset( $state['unchanged'] ) ? (int) $state['unchanged'] : 0 ) + 1;
			} else {
				++$state['skipped'];
				if ( count( $state['errors'] ) < TXA_DI_MAXLOG ) {
					$state['errors'][] = $row_id . ' ' . $result;
				}
			}
			++$done;
		}
		$state['last_secs'] = round( microtime( true ) - $started, 1 );
		$state['offset']   += $done;
		if ( $chunk['eof'] && count( $chunk['rows'] ) === $done ) {
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
		txa_di_schedule( TXA_DI_GAP, true );
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
			'unchanged'  => isset( $state['unchanged'] ) ? $state['unchanged'] : 0,
			'last_secs'  => isset( $state['last_secs'] ) ? $state['last_secs'] : 0,
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
		// One status post, rewritten on every batch: do not pile up a revision per batch.
		add_filter( 'wp_revisions_to_keep', '__return_zero', 99 );
		wp_update_post( wp_slash( $post ) );
		remove_filter( 'wp_revisions_to_keep', '__return_zero', 99 );
		return;
	}
	$id = wp_insert_post( wp_slash( $post ) );
	if ( $id && ! is_wp_error( $id ) ) {
		$state['report_id'] = (int) $id;
		update_option( TXA_DI_STATE, $state, false );
	}
}
