<?php
/**
 * تكسا ديكور — إكمال Schema الكيان (Organization / OnlineStore)
 *
 * مكان التركيب: wp-admin ← Snippets ← Add New (إضافة Code Snippets)
 *   - النوع: PHP (Functions) — التشغيل: "Run snippet everywhere".
 *   - عند اللصق في Code Snippets احذف السطر الأول "<?php".
 *
 * ماذا يفعل:
 *   يكمل عقدة Organization التي يخرجها Rank Math حالياً (‎@id = https://texadecore.store/#organization)
 *   عبر الفلتر rank_math/json_ld، بدل طباعة عقدة ثانية (حتى لا يظهر كيانان متعارضان).
 *   العقدة الحالية (فُحصت على الموقع الحي 2026-11-21) فيها: name و url و logo فقط.
 *   لا يغيّر: name، url، logo، ولا أي عقدة أخرى (WebSite / WebPage / Product).
 *
 * مصدر القيم: كل القيم "المؤكدة" أدناه مقروءة من تذييل الموقع الحي نفسه بتاريخ 2026-11-21
 *   (الاسم القانوني، السجل التجاري، الرقم الضريبي، رابط wa.me، البريد، العنوان، ساعات العمل،
 *   روابط إنستغرام وتيك توك). لا توجد هنا أي قيمة مخمّنة.
 *
 * ===================== تنبيه: تعارض NAP — يُحسم قبل تفعيل بيانات الاتصال =====================
 * رصد تقريرا SEO و GEO تعارضاً بين الموقع والحسابات:
 *   - المدينة: الموقع يقول "جدة 22335"، وبايو إنستغرام ونبذة صفحة فيسبوك يقولان "الرياض".
 *   - الهاتف: الموقع 0591409002، ومنشور إنستغرام يعرض رقم خدمة عملاء 8002460004،
 *     ومقتطف آخر يعرض 966541231412 و 966561659080 (غير مؤكد أنها للمتجر).
 *   - فيسبوك: صفحتان (61595643200616 في التذييل، و 61591825643165 في article:author لصفحة من نحن).
 * وضع عنوان وهاتف في Schema يخالفان ما في الحسابات وملف جوجل يزيد تشتت الكيان.
 * لذلك telephone و address و contactPoint لا تُطبع إلا بعد تغيير TEXA_NAP_CONFIRMED إلى true،
 * أي بعد أن يقرر المالك المدينة والرقم المعتمدين ويوحّدهما في الحسابات.
 * باقي الحقول (الاسم البديل، الاسم القانوني، السجل، الضريبي، sameAs) تُطبع فور التفعيل.
 * ==============================================================================================
 *
 * التحقق: افتح مصدر الصفحة الرئيسية وابحث عن rank-math-schema، أو اختبرها في
 *   https://validator.schema.org و https://search.google.com/test/rich-results
 * التراجع: عطّل السنيبت (Deactivate) ثم امسح الكاش. لا يكتب شيئاً في قاعدة البيانات.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/* ------------------------------------------------------------------------------------------
 * 1) قيم مؤكدة من الموقع الحي (التذييل) — 2026-11-21
 * ---------------------------------------------------------------------------------------- */
if ( ! defined( 'TEXA_ORG_ID' ) ) {
	define( 'TEXA_ORG_ID', 'https://texadecore.store/#organization' );
	define( 'TEXA_ORG_LEGAL_NAME', 'شركة ميراس جروث هولدينج شركة شخص واحد ذ.م.م' );
	define( 'TEXA_ORG_CR_NUMBER', '7055107622' );        // السجل التجاري
	define( 'TEXA_ORG_VAT_ID', '314997835900003' );      // الرقم الضريبي
	define( 'TEXA_ORG_INSTAGRAM', 'https://www.instagram.com/texa.decor/' );
	define( 'TEXA_ORG_TIKTOK', 'https://www.tiktok.com/@texa.decor' );

	// بيانات الاتصال كما هي منشورة في التذييل — لا تُطبع قبل TEXA_NAP_CONFIRMED = true.
	define( 'TEXA_ORG_PHONE', '+966591409002' );         // من رابط wa.me/966591409002
	define( 'TEXA_ORG_EMAIL', 'texadecore@gmail.com' );
	define( 'TEXA_ORG_STREET', 'حي النزلة الشرقية' );
	define( 'TEXA_ORG_CITY', 'جدة' );
	define( 'TEXA_ORG_POSTCODE', '22335' );
	define( 'TEXA_ORG_COUNTRY', 'SA' );

	/* --------------------------------------------------------------------------------------
	 * 2) قرارات وقيم تحتاج تأكيد من المالك — القيمة الفارغة '' لا تُطبع إطلاقاً
	 * ------------------------------------------------------------------------------------ */

	// يحتاج تأكيد من المالك: هل حُسم تعارض NAP (جدة/الرياض، وأي رقم هو المعتمد)؟
	// اجعلها true فقط بعد توحيد المدينة والرقم في الموقع والحسابات، وعدّل القيم أعلاه إن تغيّرت.
	define( 'TEXA_NAP_CONFIRMED', false );

	// يحتاج تأكيد من المالك: أي صفحتي فيسبوك هي الرسمية؟
	// التذييل يربط https://www.facebook.com/profile.php?id=61595643200616
	// وصفحة "من نحن" تشير إلى id=61591825643165. ضع الرابط الصحيح هنا بعد الحسم.
	define( 'TEXA_TODO_FACEBOOK_URL', '' );

	// يحتاج تأكيد من المالك: روابط لا نعرف إن كانت موجودة. لا تُخترع — اتركها فارغة حتى تتوفر.
	define( 'TEXA_TODO_GOOGLE_BUSINESS_URL', '' );   // رابط ملف النشاط التجاري على جوجل
	define( 'TEXA_TODO_SBC_VERIFY_URL', '' );        // رابط التوثيق في المركز السعودي للأعمال
	define( 'TEXA_TODO_LINKEDIN_URL', '' );          // يوجد ملف باسم "تكسا ديكور Texadecore" غير مؤكد أنه للمتجر
	define( 'TEXA_TODO_YOUTUBE_URL', '' );
	define( 'TEXA_TODO_X_URL', '' );
	define( 'TEXA_TODO_SNAPCHAT_URL', '' );

	// يحتاج تأكيد من المالك: بريد على نطاق العلامة بدل Gmail. إن وُضع هنا استُخدم بدل TEXA_ORG_EMAIL.
	define( 'TEXA_TODO_BRAND_EMAIL', '' );

	// يحتاج تأكيد من المالك: هل ساعات العمل (السبت–الخميس 9:00–18:00 كما في التذييل) هي ساعات خدمة العملاء؟
	define( 'TEXA_TODO_HOURS_CONFIRMED', false );

	// ملاحظة: hasMerchantReturnPolicy (مدة الاسترجاع 7 أيام) غير مضاف عمداً:
	// يحتاج تأكيد من المالك أن المدة تنطبق على كل المنتجات. و AggregateRating غير مضاف (لا تقييمات حقيقية).
}

/**
 * الحقول التي تُضاف إلى عقدة Organization.
 *
 * @return array
 */
function texa_org_schema_fields() {
	$same_as = array_values(
		array_filter(
			array(
				TEXA_ORG_INSTAGRAM,
				TEXA_ORG_TIKTOK,
				TEXA_TODO_FACEBOOK_URL,
				TEXA_TODO_GOOGLE_BUSINESS_URL,
				TEXA_TODO_SBC_VERIFY_URL,
				TEXA_TODO_LINKEDIN_URL,
				TEXA_TODO_YOUTUBE_URL,
				TEXA_TODO_X_URL,
				TEXA_TODO_SNAPCHAT_URL,
			)
		)
	);

	$fields = array(
		'@type'         => array( 'Organization', 'OnlineStore' ),
		'alternateName' => array( 'Texa Decor', 'تكسا للديكور' ),
		'legalName'     => TEXA_ORG_LEGAL_NAME,
		'description'   => 'تكسا ديكور متجر سعودي أونلاين لورق الجدران والباركيه والتكسيات وبديل الرخام وبديل الخشب، مع خدمة قياس وتركيب وشحن لجميع مدن المملكة.',
		'vatID'         => TEXA_ORG_VAT_ID,
		'identifier'    => array(
			'@type'      => 'PropertyValue',
			'propertyID' => 'CR',
			'name'       => 'السجل التجاري',
			'value'      => TEXA_ORG_CR_NUMBER,
		),
		'areaServed'    => array(
			'@type' => 'Country',
			'name'  => 'SA',
		),
		'sameAs'        => $same_as,
	);

	if ( TEXA_NAP_CONFIRMED ) {
		$email = '' !== TEXA_TODO_BRAND_EMAIL ? TEXA_TODO_BRAND_EMAIL : TEXA_ORG_EMAIL;

		$fields['telephone'] = TEXA_ORG_PHONE;
		$fields['email']     = $email;
		$fields['address']   = array(
			'@type'           => 'PostalAddress',
			'streetAddress'   => TEXA_ORG_STREET,
			'addressLocality' => TEXA_ORG_CITY,
			'postalCode'      => TEXA_ORG_POSTCODE,
			'addressCountry'  => TEXA_ORG_COUNTRY,
		);

		$contact = array(
			'@type'             => 'ContactPoint',
			'contactType'       => 'customer service',
			'telephone'         => TEXA_ORG_PHONE,
			'email'             => $email,
			'availableLanguage' => array( 'ar', 'en' ),
		);
		if ( TEXA_TODO_HOURS_CONFIRMED ) {
			$contact['hoursAvailable'] = array(
				'@type'     => 'OpeningHoursSpecification',
				'dayOfWeek' => array( 'Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday' ),
				'opens'     => '09:00',
				'closes'    => '18:00',
			);
		}
		$fields['contactPoint'] = $contact;
	}

	return $fields;
}

/**
 * يكمل عقدة Organization الموجودة في مخرجات Rank Math.
 * إن لم توجد العقدة (تغيّر إعداد Rank Math مثلاً) لا يفعل شيئاً.
 *
 * @param array $data عقد JSON-LD قبل الطباعة.
 * @return array
 */
function texa_org_schema_filter( $data ) {
	if ( ! is_array( $data ) ) {
		return $data;
	}

	foreach ( $data as $key => $node ) {
		if ( ! is_array( $node ) || empty( $node['@id'] ) || TEXA_ORG_ID !== $node['@id'] ) {
			continue;
		}
		// عقد الإحالة ({"@id": ...} فقط) تُترك كما هي.
		if ( empty( $node['@type'] ) ) {
			continue;
		}
		// القيم الحالية (name / url / logo) تبقى؛ حقولنا تُضاف أو تستبدل ما يقابلها فقط.
		$data[ $key ] = array_merge( $node, texa_org_schema_fields() );
		break;
	}

	return $data;
}
add_filter( 'rank_math/json_ld', 'texa_org_schema_filter', 99 );
