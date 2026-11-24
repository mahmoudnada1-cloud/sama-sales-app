<?php
/**
 * Plugin Name: Texa — Home Packages Banner
 * Description: Front page only: shows the packages banner under the welcome text and moves the room-planner banner to just before the marble-alternative offers row. Deactivate to revert.
 * Version: 1.0.1
 * Author: Texa Decor
 */
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action( 'wp_footer', function () {
	if ( ! is_front_page() ) {
		return;
	}
	?>
<div id="texa-pkg-home" dir="rtl" style="display:none">
<style>
#texa-pkg-home{max-width:100%;margin:0 0 22px;font-family:"Noto Sans Arabic","Noto Sans","Segoe UI",sans-serif;box-sizing:border-box}
#texa-pkg-home *{box-sizing:border-box;font-family:inherit}
#texa-pkg-home a.tph{display:grid;grid-template-columns:1fr 1.15fr;gap:28px;align-items:center;background:linear-gradient(120deg,#cc5500 0%,#d9640f 60%,#e07a2c 100%);border-radius:18px;padding:26px 34px;color:#fff;text-decoration:none;overflow:hidden;box-shadow:0 8px 22px rgba(204,85,0,.22)}
#texa-pkg-home .tph-chip{display:inline-block;background:#fff;color:#cc5500;font-weight:800;font-size:13px;padding:5px 14px;border-radius:30px;margin-bottom:12px}
#texa-pkg-home .tph-h{font-size:40px;line-height:1.15;font-weight:900;color:#fff;margin:0}
#texa-pkg-home .tph-pr{font-size:20px;font-weight:700;color:#fff;margin:6px 0 8px}
#texa-pkg-home .tph-pr b{font-size:40px;font-weight:900}
#texa-pkg-home .tph-sub{font-size:15.5px;line-height:1.8;color:#fff3ea;margin:0 0 16px;max-width:520px}
#texa-pkg-home .tph-cta{display:inline-block;background:#fff;color:#1c1c1c;font-weight:800;font-size:15px;padding:12px 28px;border-radius:30px}
#texa-pkg-home .tph-note{font-size:12.5px;color:#ffe3cf;margin-top:12px}
#texa-pkg-home .tph-m{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
#texa-pkg-home .tph-t{position:relative;border-radius:12px;overflow:hidden;height:210px;box-shadow:0 8px 18px rgba(0,0,0,.22)}
#texa-pkg-home .tph-t img{width:100%;height:100%;object-fit:cover;display:block}
#texa-pkg-home .tph-t span{position:absolute;bottom:8px;right:8px;background:#fff;color:#16213e;font-weight:800;font-size:12.5px;padding:4px 11px;border-radius:20px}
@media (max-width:980px){
#texa-pkg-home a.tph{grid-template-columns:1fr;padding:20px 18px;gap:16px}
#texa-pkg-home .tph-h{font-size:28px}
#texa-pkg-home .tph-pr b{font-size:30px}
#texa-pkg-home .tph-m{grid-template-columns:repeat(2,1fr)}
#texa-pkg-home .tph-t{height:130px}
}
</style>
<a class="tph" href="<?php echo esc_url( get_permalink( 35565 ) ); ?>">
	<div>
		<span class="tph-chip">جديد · باقات تِكسا المميزة</span>
		<p class="tph-h">جدّد غرفتك كاملة</p>
		<div class="tph-pr">بأقل من <b>3,399</b> ريال</div>
		<p class="tph-sub">سهّلناها عليك: 5 باقات منسّقة جاهزة لغرفة 5×5 — أرضية باركيه، جدار مميز، ورق جدران، ونعلة. تطلبها بضغطة وحدة.</p>
		<span class="tph-cta">اكتشف الباقات ←</span>
		<div class="tph-note">قيمة المنتجات شاملة الضريبة · حتى نفاذ الكمية</div>
	</div>
	<div class="tph-m">
		<div class="tph-t"><img loading="lazy" src="https://i0.wp.com/texadecore.store/wp-content/uploads/2026/11/jXOJSiwXhXMK.jpg?fit=500%2C500&ssl=1" alt="جدار مميز بديل شيبورد"><span>جدار مميز</span></div>
		<div class="tph-t"><img loading="lazy" src="https://i0.wp.com/texadecore.store/wp-content/uploads/2026/11/ufLYwLuwXlQh.jpg?fit=500%2C500&ssl=1" alt="أرضية باركيه SPC"><span>أرضية باركيه</span></div>
		<div class="tph-t"><img loading="lazy" src="https://i0.wp.com/texadecore.store/wp-content/uploads/2026/11/texa-wp-avenue-77307-2-1.webp?fit=500%2C500&ssl=1" alt="ورق جدران كوري"><span>ورق جدران</span></div>
		<div class="tph-t"><img loading="lazy" src="https://i0.wp.com/texadecore.store/wp-content/uploads/2026/11/zLJKoVoTKGPZ.jpg?fit=500%2C500&ssl=1" alt="نعلة فايبر"><span>نعلة</span></div>
	</div>
</a>
<script>
(function(){
	function run(){
		var b=document.getElementById('texa-pkg-home');
		var a=document.getElementById('txpl-banner');
		var rows=document.getElementById('texa-home-rows');
		if(!b||!a||!rows||!rows.contains(a)||!a.parentNode){return false;}
		if(a.getBoundingClientRect().height<50){return false;}
		var wrap=a.parentNode;
		var aDisp='block';try{aDisp=window.getComputedStyle(a).display||'block';}catch(e){}
		/* 1) packages banner takes the planner's current place */
		wrap.insertBefore(b,a);
		try{b.style.setProperty('order',window.getComputedStyle(a).order,'important');}catch(e){}
		b.style.display='block';
		/* 2) planner moves down, right before the marble-alternative offers row */
		var target=null,hs=rows.querySelectorAll('h2,h3');
		for(var i=0;i<hs.length;i++){
			if(hs[i].textContent.indexOf('عروض بديل الرخام')!==-1&&hs[i].getBoundingClientRect().height>0){
				var n=hs[i];
				while(n.parentNode&&n.parentNode!==rows&&n.parentNode.querySelectorAll('h2,h3').length<2){n=n.parentNode;}
				target=n;break;
			}
		}
		if(target&&target.parentNode){
			target.parentNode.insertBefore(a,target);
			try{a.style.setProperty('order',window.getComputedStyle(target).order,'important');}catch(e){}
			a.style.marginBottom='22px';
			if(aDisp&&aDisp!=='none'){a.style.setProperty('display',aDisp,'important');}
		}
		return true;
	}
	var tries=0;
	function loop(){ if(run()){return;} if(++tries<60){setTimeout(loop,250);} }
	function start(){ setTimeout(loop,300); }
	if(document.readyState==='complete'){start();}else{window.addEventListener('load',start);}
})();
</script>
</div>
	<?php
} );
