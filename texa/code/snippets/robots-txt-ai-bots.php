<?php
/**
 * Snippet: AI Bot Allow Rules — robots.txt
 * الغرض: إضافة قواعد Allow لبوتات الذكاء الاصطناعي في ملف robots.txt
 *
 * مكان التركيب: Code Snippets (wp-admin > Snippets > Add New)
 *   - العنوان: Texa — AI Bot robots.txt Rules
 *   - النوع: Run Everywhere (أو "Run on front-end only")
 *   - الحالة: Active
 *
 * التحقق بعد التركيب:
 *   1. افتح https://texadecore.store/robots.txt في المتصفح
 *   2. تأكد من وجود "User-agent: GPTBot" و "User-agent: ClaudeBot" في النهاية
 *
 * التراجع:
 *   - عطّل الـ Snippet أو احذفه من Code Snippets
 *   - robots.txt سيعود لحالته الأصلية فوراً
 *
 * ملاحظة: هذا الـ filter يُضاف بعد ما يولّد Rank Math robots.txt الخاص به
 */

add_filter( 'robots_txt', 'texa_allow_ai_bots', 20, 2 );

function texa_allow_ai_bots( $output, $public ) {
    // لا تُضاف القواعد إذا كان الموقع مخفياً عن محركات البحث
    if ( '0' === $public ) {
        return $output;
    }

    $ai_rules = "\n# AI Search Engine Crawlers\n";
    $ai_rules .= "User-agent: GPTBot\nAllow: /\n\n";
    $ai_rules .= "User-agent: Google-Extended\nAllow: /\n\n";
    $ai_rules .= "User-agent: PerplexityBot\nAllow: /\n\n";
    $ai_rules .= "User-agent: anthropic-ai\nAllow: /\n\n";
    $ai_rules .= "User-agent: ClaudeBot\nAllow: /\n\n";
    $ai_rules .= "User-agent: cohere-ai\nAllow: /\n\n";
    $ai_rules .= "User-agent: CCBot\nAllow: /\n\n";
    $ai_rules .= "User-agent: Amazonbot\nAllow: /\n\n";

    return $output . $ai_rules;
}
