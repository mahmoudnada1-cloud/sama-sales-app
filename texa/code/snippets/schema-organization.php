<?php
/**
 * Snippet: Organization Schema Enrichment (Rank Math JSON-LD)
 * الغرض: إثراء بيانات Organization schema بالمعلومات القانونية والتواصل
 *
 * مكان التركيب: Code Snippets (wp-admin > Snippets > Add New)
 *   - العنوان: Texa — Organization Schema Enrichment
 *   - النوع: Run Everywhere
 *   - الحالة: Active
 *
 * التحقق بعد التركيب:
 *   1. افتح https://texadecore.store/ في المتصفح
 *   2. انظر في source الصفحة وابحث عن "@type":"Organization"
 *   3. أو استخدم: https://search.google.com/test/rich-results
 *   4. تأكد من وجود legalName وtelephone وhasCredential
 *
 * التراجع:
 *   - عطّل الـ Snippet أو احذفه من Code Snippets
 *
 * ملاحظة: هذا الـ snippet يتطلب Rank Math SEO مفعّل
 */

// ثوابت بيانات المؤسسة — أكدها المالك 22 نوفمبر 2026
define( 'TEXA_ORG_ID',          'https://texadecore.store/#organization' );
define( 'TEXA_ORG_LEGAL_NAME',  'شركة ميراس جروث هولدينج شركة شخص واحد ذ.م.م' );
define( 'TEXA_ORG_CR_NUMBER',   '7055107622' );
define( 'TEXA_ORG_VAT_ID',      '314997835900003' );
define( 'TEXA_ORG_INSTAGRAM',   'https://www.instagram.com/texa_decor_sa/' );
define( 'TEXA_ORG_TIKTOK',      'https://www.tiktok.com/@texa_decor_sa' );
define( 'TEXA_ORG_PHONE',       '+966591409002' );
define( 'TEXA_ORG_EMAIL',       'texadecore@gmail.com' );
define( 'TEXA_ORG_CITY',        'جدة' );
define( 'TEXA_ORG_COUNTRY',     'SA' );
define( 'TEXA_NAP_CONFIRMED',   true );

/**
 * Returns the enrichment fields to merge into Organization schema.
 *
 * @return array
 */
function texa_org_schema_fields() {
    return array(
        '@id'         => TEXA_ORG_ID,
        'legalName'   => TEXA_ORG_LEGAL_NAME,
        'telephone'   => TEXA_ORG_PHONE,
        'email'       => TEXA_ORG_EMAIL,
        'address'     => array(
            '@type'            => 'PostalAddress',
            'addressLocality'  => TEXA_ORG_CITY,
            'addressCountry'   => TEXA_ORG_COUNTRY,
        ),
        'sameAs'      => array(
            TEXA_ORG_INSTAGRAM,
            TEXA_ORG_TIKTOK,
        ),
        'hasCredential' => array(
            array(
                '@type'       => 'EducationalOccupationalCredential',
                'name'        => 'سجل تجاري',
                'credentialCategory' => 'CommercialRegistration',
                'identifier'  => TEXA_ORG_CR_NUMBER,
                'recognizedBy' => array(
                    '@type' => 'GovernmentOrganization',
                    'name'  => 'وزارة التجارة، المملكة العربية السعودية',
                ),
            ),
        ),
        'vatID'       => TEXA_ORG_VAT_ID,
    );
}

/**
 * Filter: Merge organization data into Rank Math JSON-LD output.
 *
 * @param array $data   The JSON-LD entities array from Rank Math.
 * @param object $jsonld The Rank Math JsonLD object.
 * @return array
 */
function texa_org_schema_filter( $data, $jsonld ) {
    if ( empty( $data ) || ! is_array( $data ) ) {
        return $data;
    }

    $fields = texa_org_schema_fields();

    foreach ( $data as $key => $entity ) {
        if ( ! isset( $entity['@type'] ) ) {
            continue;
        }

        $type = (array) $entity['@type'];

        // Match Organization, Store, HomeGoodsStore, LocalBusiness, etc.
        $is_org = false;
        foreach ( $type as $t ) {
            if ( false !== strpos( $t, 'Organization' )
                || false !== strpos( $t, 'Business' )
                || false !== strpos( $t, 'Store' )
            ) {
                $is_org = true;
                break;
            }
        }

        if ( ! $is_org ) {
            continue;
        }

        // Merge: existing values in $data take priority EXCEPT for the
        // fields we explicitly want to set/enrich.
        foreach ( $fields as $field => $value ) {
            if ( 'sameAs' === $field ) {
                // Merge sameAs arrays; deduplicate.
                $existing = isset( $entity['sameAs'] ) ? (array) $entity['sameAs'] : array();
                $data[ $key ]['sameAs'] = array_values( array_unique(
                    array_merge( $existing, (array) $value )
                ) );
            } else {
                // Only overwrite if currently empty / unset.
                if ( empty( $entity[ $field ] ) ) {
                    $data[ $key ][ $field ] = $value;
                }
            }
        }
    }

    return $data;
}

add_filter( 'rank_math/json_ld', 'texa_org_schema_filter', 99, 2 );
