<?php
/**
 * Plugin Name: Texa Description Import (temporary)
 * Description: One-off tool. Applies prepared product descriptions and Rank Math fields from bundled CSV files in small background batches, keeping a per-product backup. Deactivate to stop. Delete when finished.
 * Version: 1.1.0
 * Author: Texa Decor web team
 * Requires Plugins: woocommerce
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

const TXA_DI_STATE  = 'txa_di_state';
const TXA_DI_HOOK   = 'txa_di_run_batch';
const TXA_DI_BATCH  = 100;
const TXA_DI_GAP    = 45;
const TXA_DI_BUDGET = 20;  // Seconds of work per batch; the rest of the batch waits for the next run.
const TXA_DI_STALL  = 300; // Seconds without a finished batch before a page view runs one itself.
const TXA_DI_LOCK   = 120; // A running batch holds a lock for at most this long.
const TXA_DI_MAXLOG = 200;
const TXA_DI_BACKUP = '_txa_v4_backup'; // Written once per product, before its very first change. Never replaced.
const TXA_DI_ALT    = '_wp_attachment_image_alt';

/** Current time. Filterable only so the offline test harness can move the clock. */
function txa_di_now() {
	return (int) apply_filters( 'txa_di_now', time() );
}

/** CSV files bundled with this plugin, in a stable order. Nothing outside this folder is ever read. */
function txa_di_files() {
	$files = glob( __DIR__ . '/data/products-v5-*.csv' );
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
			'alts_set'   => 0,
			'last_secs'  => 0,
			'beat'       => 0,
			'inline'     => 0,
			'next'       => '',
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

/** True when a batch is waiting in the queue. A batch that is (or only looks) "in progress" does not count. */
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
 * Queues the next batch unless one is already waiting. Used by the batch itself and by the keep-alive
 * check, with the same rule: files remain + nothing waiting = queue one.
 * Returns a short note for the status report.
 */
function txa_di_schedule( $delay, $by ) {
	if ( txa_di_has_pending() ) {
		return 'already waiting (seen by ' . $by . ' ' . gmdate( 'H:i:s', txa_di_now() ) . ')';
	}
	$due = txa_di_now() + $delay;
	if ( function_exists( 'as_schedule_single_action' ) ) {
		$id = (int) as_schedule_single_action( $due, TXA_DI_HOOK, array(), 'txa-di' );
	} else {
		$id = false === wp_schedule_single_event( $due, TXA_DI_HOOK ) ? 0 : 1;
	}
	return ( $id ? 'queued #' . $id : 'QUEUE FAILED' ) . ' by ' . $by . ' due ' . gmdate( 'H:i:s', $due );
}

function txa_di_unschedule() {
	if ( function_exists( 'as_unschedule_all_actions' ) ) {
		as_unschedule_all_actions( TXA_DI_HOOK, null, 'txa-di' );
	}
	wp_clear_scheduled_hook( TXA_DI_HOOK );
	delete_transient( 'txa_di_lock' );
	delete_transient( 'txa_di_tick' );
	delete_option( 'txa_di_watch' );
}

/**
 * Keeps the job alive. Two independent paths, checked at most once a minute:
 * 1. files remain and no batch is waiting or running -> queue one in Action Scheduler;
 * 2. files remain but no batch has finished for TXA_DI_STALL seconds (the queue is not being run)
 *    -> run one batch directly at the end of this request, after the page has been sent.
 */
function txa_di_ensure() {
	if ( ! function_exists( 'wc_get_product' ) ) {
		return;
	}
	if ( get_transient( 'txa_di_tick' ) ) {
		return;
	}
	set_transient( 'txa_di_tick', 1, MINUTE_IN_SECONDS );
	$state = txa_di_state();
	if ( ! txa_di_pending_files( $state ) ) {
		if ( false !== get_option( 'txa_di_watch' ) ) {
			delete_option( 'txa_di_watch' ); // Nothing left to do: a later package starts with a fresh stall clock.
		}
		return;
	}
	if ( get_transient( 'txa_di_lock' ) ) {
		return; // A batch is running right now; it queues the next one itself.
	}
	$now   = txa_di_now();
	$watch = get_option( 'txa_di_watch' ); // Kept apart from the job state, so this check never overwrites a batch's progress.
	if ( ! is_array( $watch ) ) {
		$watch = array( 'since' => $now, 'note' => '' ); // First sighting: start the stall clock, give the queue its chance.
	}
	$watch['note'] = txa_di_schedule( 20, 'keep-alive' );
	$last          = max( (int) $watch['since'], isset( $state['beat'] ) ? (int) $state['beat'] : 0 );
	if ( ( $now - $last ) > TXA_DI_STALL && ( ! is_user_logged_in() || current_user_can( 'manage_woocommerce' ) ) ) {
		$watch['note'] .= '; stalled ' . ( $now - $last ) . 's, running one batch directly';
		add_action( 'shutdown', 'txa_di_run_inline', 999 );
	}
	update_option( 'txa_di_watch', $watch, false );
}
add_action( 'action_scheduler_init', 'txa_di_ensure' );

/** Fallback path: one batch at the very end of an ordinary request, when the queue has gone quiet. */
function txa_di_run_inline() {
	ignore_user_abort( true );
	if ( function_exists( 'fastcgi_finish_request' ) ) {
		fastcgi_finish_request(); // The visitor already has the page; the batch costs them nothing.
	}
	txa_di_run_batch( 'inline' );
}

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
	if ( '' === trim( $desc ) || ! preg_match( '/txa-desc-v\d/', $desc ) ) {
		return 'skipped: description missing or without txa-desc marker';
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
		txa_di_fill_alt( $product, $row );
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
	txa_di_fill_alt( $product, $row );
	return 'updated';
}

/**
 * Gives the product's featured image the prepared alt text, only when that image has none.
 * An existing alt text is never replaced. Images filled here are marked with _txa_alt_set for rollback.
 */
function txa_di_fill_alt( $product, $row ) {
	$alt = isset( $row['image_alt'] ) ? sanitize_text_field( (string) $row['image_alt'] ) : '';
	$img = is_callable( array( $product, 'get_image_id' ) ) ? absint( $product->get_image_id() ) : 0;
	if ( '' === $alt || ! $img || 'attachment' !== get_post_type( $img ) ) {
		return;
	}
	if ( '' !== trim( (string) get_post_meta( $img, TXA_DI_ALT, true ) ) ) {
		return;
	}
	if ( update_post_meta( $img, TXA_DI_ALT, wp_slash( $alt ) ) ) {
		add_post_meta( $img, '_txa_alt_set', gmdate( 'c' ), true );
		$GLOBALS['txa_di_alts'] = ( isset( $GLOBALS['txa_di_alts'] ) ? (int) $GLOBALS['txa_di_alts'] : 0 ) + 1;
	}
}

/**
 * Entry point for both the queue and the fallback. Only one batch runs at a time: a second caller
 * leaves at once, and the lock frees itself after TXA_DI_LOCK seconds if a run is killed.
 */
function txa_di_run_batch( $via = 'queue' ) {
	if ( ! function_exists( 'wc_get_product' ) || get_transient( 'txa_di_lock' ) ) {
		return;
	}
	set_transient( 'txa_di_lock', 1, TXA_DI_LOCK );
	$GLOBALS['txa_di_alts'] = 0;
	try {
		txa_di_do_batch( 'inline' === $via ? 'inline' : 'queue' );
	} finally {
		delete_transient( 'txa_di_lock' );
	}
}

function txa_di_do_batch( $via ) {
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
	$state['alts_set'] = ( isset( $state['alts_set'] ) ? (int) $state['alts_set'] : 0 ) + ( isset( $GLOBALS['txa_di_alts'] ) ? (int) $GLOBALS['txa_di_alts'] : 0 );
	if ( 'inline' === $via ) {
		$state['inline'] = ( isset( $state['inline'] ) ? (int) $state['inline'] : 0 ) + 1;
	} else {
		$state['beat'] = txa_di_now(); // Only the queue resets the stall clock; while it stays quiet the fallback keeps working.
	}
	if ( ! txa_di_pending_files( $state ) ) {
		$state['status'] = 'done';
		$state['next']   = '';
	} else {
		// Files remain: always leave a batch waiting. The outcome is written into the report.
		$state['next'] = txa_di_schedule( TXA_DI_GAP, 'batch' );
	}
	update_option( TXA_DI_STATE, $state, false );
	txa_di_report( $state );
}
add_action( TXA_DI_HOOK, 'txa_di_run_batch', 10, 0 );

/** Progress is written to one private post so it can be read without any new endpoint. */
function txa_di_report( $state ) {
	$body = wp_json_encode(
		array(
			'status'     => $state['status'],
			'updated'    => $state['updated'],
			'skipped'    => $state['skipped'],
			'unchanged'  => isset( $state['unchanged'] ) ? $state['unchanged'] : 0,
			'alts_set'   => isset( $state['alts_set'] ) ? $state['alts_set'] : 0,
			'last_secs'  => isset( $state['last_secs'] ) ? $state['last_secs'] : 0,
			'next'       => isset( $state['next'] ) ? $state['next'] : '',
			'inline'     => isset( $state['inline'] ) ? $state['inline'] : 0,
			'wp_cron'    => ( defined( 'DISABLE_WP_CRON' ) && DISABLE_WP_CRON ) ? 'off (host cron)' : 'on',
			'keep_alive' => is_array( get_option( 'txa_di_watch' ) ) ? get_option( 'txa_di_watch' )['note'] : '',
			'pending'    => txa_di_pending_files( $state ),
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
