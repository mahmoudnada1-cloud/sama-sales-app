# -*- coding: utf-8 -*-
IMG="https://i0.wp.com/texadecore.store/wp-content/uploads/2026/11/{}?fit=600%2C600&ssl=1"
P={
 'f_oak':(34466,'الأرضية','باركيه SPC بلوط فاتح',65,'ريال/م²',27,'ufLYwLuwXlQh.jpg'),
 'f_gray':(34470,'الأرضية','باركيه SPC بني رمادي',65,'ريال/م²',27,'oiEqcYmttoUR.jpg'),
 'f_beige':(34462,'الأرضية','باركيه SPC بيج',65,'ريال/م²',27,'GndFbVEUynDN.jpg'),
 'p_oak':(34548,'الجدار المميز','بديل شيبورد خشبي بلوط فاتح',125,'ريال/لوح',5,'jXOJSiwXhXMK.jpg'),
 'p_gray':(34552,'الجدار المميز','بديل شيبورد سادة رمادي',125,'ريال/لوح',5,'hSkCbVjMesDL.jpg'),
 'p_brown':(34546,'الجدار المميز','بديل شيبورد سادة بني رمادي',125,'ريال/لوح',5,'cbPyLYxKoopk.jpg'),
 'p_fab':(29775,'الجدار المميز','بديل شيبورد كريمي قماشي',123,'ريال/لوح',5,'texa-chip5-ms-1068-1.webp'),
 'w_off':(32411,'ورق الجدران','ورق جدران كوري أوف وايت',189,'ريال/لفة',3,'texa-wp-avenue-77307-2-1.webp'),
 'w_gray':(32405,'ورق الجدران','ورق جدران كوري رمادي فضي',189,'ريال/لفة',3,'texa-wp-artbook-57233-5-1.webp'),
 'w_blue':(30502,'ورق الجدران','ورق جدران كوري مربعات أزرق',179,'ريال/لفة',3,'texa-wp-oasis-81433-2-1.webp'),
 's_sil':(34576,'النعلة','نعلة فايبر معدنية فضي',25,'ريال/قطعة',9,'zLJKoVoTKGPZ.jpg'),
}
PACKS=[
 (1,'الباقة الدافئة','دافئ خشبي بلوط',['f_oak','p_oak','w_off','s_sil']),
 (2,'الباقة الرمادية','رمادي مودرن',['f_gray','p_gray','w_gray','s_sil']),
 (3,'الباقة الفاتحة','فاتح فخم',['f_oak','p_gray','w_off','s_sil']),
 (4,'الباقة البيج','بيج هادئ',['f_beige','p_fab','w_off','s_sil']),
 (5,'الباقة الكحلية','كحلي جريء',['f_gray','p_brown','w_blue','s_sil']),
]

def card(key):
    pid,role,name,price,unit,qty,img=P[key]
    uw=unit.split('/')[-1] if '/' in unit else 'قطعة'
    return f'''      <div class="tpk-card">
        <div class="tpk-img"><img src="{IMG.format(img)}" alt="{name}"></div>
        <div class="tpk-role">{role}</div>
        <div class="tpk-name">{name}</div>
        <div class="tpk-foot"><div><div class="tpk-price"><b>{price}</b> ريال</div><div class="tpk-qty">الوحدة: {uw} · العدد: {qty}</div></div><button type="button" class="tpk-add" onclick="texaAddOne({pid},{qty})">أضف</button></div>
      </div>'''

blocks=[]
for num,title,theme,keys in PACKS:
    items=[P[k] for k in keys]
    subtotal=sum(p[3]*p[5] for p in items)
    addarr=','.join('[%d,%d]'%(p[0],p[5]) for p in items)
    cards='\n'.join(card(k) for k in keys)
    blocks.append(f'''  <div class="tpk-pack">
    <div class="tpk-phead">
      <div class="tpk-pinfo">
        <span class="tpk-pchip">باقة {num} · غرفة كاملة</span>
        <div class="tpk-pprice">بأقل من <b>3,399</b> ريال <small>قيمة المنتجات شاملة الضريبة · حتى نفاذ الكمية</small></div>
      </div>
      <button type="button" class="tpk-addall" onclick="texaAddPkg([{addarr}])">أضف الباقة كاملة للسلة 🛒</button>
    </div>
    <div class="tpk-row">
{cards}
    </div>
  </div>''')

# schema products (distinct)
prod_items=[]
seen=set()
pos=0
for num,title,theme,keys in PACKS:
    for k in keys:
        pid,role,name,price,unit,qty,img=P[k]
        if pid in seen: continue
        seen.add(pid); pos+=1
        prod_items.append('{"@type":"ListItem","position":%d,"item":{"@type":"Product","name":"%s","sku":"%d","image":"%s","offers":{"@type":"Offer","priceCurrency":"SAR","price":"%d","availability":"https://schema.org/InStock"}}}'%(pos,name,pid,IMG.format(img),price))
itemlist=','.join(prod_items)

CSS='''<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;600;700;800;900&display=swap');
.texa-pkg{--navy:#16213e;--orange:#cc5500;--orangeD:#b64d00;--gold:#e9b84a;--goldL:#f2c86f;max-width:none;margin:0;padding:0;font-family:"Noto Sans Arabic","Noto Sans","Segoe UI",sans-serif;direction:rtl;box-sizing:border-box;color:#1c1c1c;line-height:1.8;font-size:15.5px;}
.texa-pkg *{box-sizing:border-box;font-family:"Noto Sans Arabic","Noto Sans","Segoe UI",sans-serif;}
.texa-pkg .tpk-lead{font-size:15.5px;font-weight:400;color:#211d17;margin:0 0 18px;padding:14px 18px 0;max-width:none;width:100%;}
.texa-pkg .tpk-pack{margin:0 0 26px;background:transparent;}
.texa-pkg .tpk-phead{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;background:#cc5500;color:#fff;padding:20px 28px;border-radius:14px;margin:0 18px;box-shadow:0 6px 18px rgba(204,85,0,.22);}
.texa-pkg .tpk-pchip{display:inline-block;background:#fff;color:#cc5500;font-weight:800;font-size:13px;padding:5px 14px;border-radius:30px;margin-bottom:8px;}
.texa-pkg .tpk-phead h2{color:#fff;font-size:30px;font-weight:900;margin:0;line-height:1.15;}
.texa-pkg .tpk-pprice{font-size:16px;color:#fff;margin-top:4px;font-weight:600;}
.texa-pkg .tpk-pprice b{font-size:28px;color:#fff;font-weight:900;}
.texa-pkg .tpk-pprice small{display:block;font-size:12.5px;color:#ffe3cf;margin-top:2px;font-weight:400;}
.texa-pkg .tpk-addall{background:#fff;color:#1c1c1c;border:0;cursor:pointer;font-weight:800;font-size:15px;padding:13px 26px;border-radius:30px;white-space:nowrap;transition:background .15s;}
.texa-pkg .tpk-addall:hover{background:#fbeee4;}
.texa-pkg .tpk-row{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding:16px 18px 0;}
.texa-pkg .tpk-card{border:1px solid #eee;border-radius:14px;padding:12px;background:#fff;display:flex;flex-direction:column;}
.texa-pkg .tpk-img{position:relative;border-radius:10px;overflow:hidden;height:230px;background:#f3f1ed;}
.texa-pkg .tpk-img img{width:100%;height:100%;object-fit:cover;display:block;}
.texa-pkg .tpk-badge{position:absolute;top:10px;right:10px;background:var(--navy);color:#fff;font-size:12px;font-weight:800;padding:4px 11px;border-radius:20px;}
.texa-pkg .tpk-role{font-size:12.5px;color:var(--orange);font-weight:600;margin-top:12px;}
.texa-pkg .tpk-name{font-weight:600;color:#1c1c1c;font-size:15.5px;margin:3px 0 0;line-height:1.4;min-height:42px;}
.texa-pkg .tpk-foot{display:flex;align-items:center;justify-content:space-between;margin-top:10px;}
.texa-pkg .tpk-price{color:#c8102e;font-size:13px;}
.texa-pkg .tpk-price b{font-size:20px;font-weight:800;color:#c8102e;}
.texa-pkg .tpk-qty{font-size:12.5px;color:#8a8372;font-weight:500;margin-top:2px;}
.texa-pkg .tpk-add{background:#16213e;color:#e9b84a;border:0;cursor:pointer;font-weight:800;font-size:14.5px;padding:9px 18px;border-radius:11px;transition:all .15s;}
.texa-pkg .tpk-add:hover{background:#0f1830;}
.texa-pkg .tpk-sec{margin-top:40px;padding:0 18px;}
.texa-pkg .tpk-sec h2{font-size:26px;font-weight:900;color:var(--navy);margin:0 0 14px;}
.texa-pkg .tpk-sec p{font-size:15.5px;color:#211d17;margin:0 0 12px;}
.texa-pkg .tpk-faq details{background:#fff;border:1px solid #eee;border-radius:12px;padding:0 18px;margin-bottom:10px;}
.texa-pkg .tpk-faq summary{cursor:pointer;font-weight:600;color:#1c1c1c;font-size:15.5px;padding:14px 0;list-style:none;}
.texa-pkg .tpk-faq summary::-webkit-details-marker{display:none;}
.texa-pkg .tpk-faq summary::before{content:"\\002B";color:var(--orange);font-weight:900;margin-left:10px;}
.texa-pkg .tpk-faq details[open] summary::before{content:"\\2212";}
.texa-pkg .tpk-faq p{padding:0 0 16px;margin:0;color:#3a4256;font-size:15.5px;}
.texa-pkg .tpk-foot{flex-direction:column;align-items:stretch;gap:10px;margin-top:6px;}
.texa-pkg .tpk-price b{font-size:22px;}
.texa-pkg .tpk-add{width:100%;padding:13px 18px;font-size:0;border-radius:11px;}
.texa-pkg .tpk-add::after{content:"\\1F6D2\\00A0\\00A0أضف للسلة";font-size:15px;font-weight:800;}
@media (max-width:980px){
  .texa-pkg .tpk-phead{padding:16px;margin:0 12px;}
  .texa-pkg .tpk-phead h2{font-size:24px;}
  .texa-pkg .tpk-addall{width:100%;}
  .texa-pkg .tpk-row{display:flex;flex-wrap:nowrap;overflow-x:auto;gap:12px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;padding:16px 16px 20px;scrollbar-width:thin;}
  .texa-pkg .tpk-card{flex:0 0 70%;max-width:70%;scroll-snap-align:start;}
}
@media (max-width:480px){.texa-pkg .tpk-card{flex-basis:78%;max-width:78%;}}
</style>'''

JS='''<script>
function texaAdd(items){var chain=Promise.resolve();items.forEach(function(it){chain=chain.then(function(){var f=new FormData();f.append('product_id',it[0]);f.append('quantity',it[1]);return fetch('/?wc-ajax=add_to_cart',{method:'POST',body:f,credentials:'same-origin'}).catch(function(){});});});chain.then(function(){window.location.href='/cart/';});}
function texaAddPkg(items){texaAdd(items);}
function texaAddOne(id,q){texaAdd([[id,q]]);}
</script>'''

SCHEMA='''<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":"https://texadecore.store/"},{"@type":"ListItem","position":2,"name":"باقات الغرفة الكاملة","item":"https://texadecore.store/room-packages/"}]},
{"@type":"Service","name":"باقات تجديد الغرف الكاملة","serviceType":"توريد وتركيب ديكور الغرف","provider":{"@type":"HomeGoodsStore","name":"تِكسا للديكور","url":"https://texadecore.store/","telephone":"+966591409002","areaServed":{"@type":"Country","name":"المملكة العربية السعودية"}},"offers":{"@type":"Offer","priceCurrency":"SAR","price":"3142","availability":"https://schema.org/InStock","url":"https://texadecore.store/room-packages/"}},
{"@type":"ItemList","name":"منتجات باقات الغرفة الكاملة","itemListElement":[__ITEMS__]},
{"@type":"FAQPage","mainEntity":[
{"@type":"Question","name":"كم تكلفة تجديد غرفة كاملة مع تِكسا؟","acceptedAnswer":{"@type":"Answer","text":"تبدأ باقات الغرفة الكاملة من أقل من 3,399 ريال شامل الضريبة لغرفة بمقاس 5×5 متر تقريبًا، وتشمل الأرضية والجدار المميز وورق الجدران والنعلة."}},
{"@type":"Question","name":"كم عدد الباقات المتاحة؟","acceptedAnswer":{"@type":"Answer","text":"خمس باقات منسّقة بألوان مختلفة، وكل باقة تشمل أربعة منتجات أساسية."}},
{"@type":"Question","name":"هل يشمل العرض التركيب؟","acceptedAnswer":{"@type":"Answer","text":"نعم، تِكسا للديكور توفّر توريد وتركيب احترافي مع رفع المقاسات. السعر المعروض هو قيمة المنتجات."}},
{"@type":"Question","name":"هل الباركيه مناسب للمناخ السعودي؟","acceptedAnswer":{"@type":"Answer","text":"نعم، باركيه SPC مقاوم للماء والرطوبة والخدش ولا يتقوّس كالخشب الطبيعي."}},
{"@type":"Question","name":"إلى متى يستمر العرض؟","acceptedAnswer":{"@type":"Answer","text":"العرض ساري حتى نفاذ الكمية على التشكيلة المختارة من منتجات الباقات."}}
]}
]}
</script>'''.replace('__ITEMS__',itemlist)

html=f'''<!-- wp:html -->
<section class="texa-pkg" dir="rtl">
{CSS}
  <p class="tpk-lead">سهّلناها عليك! بدل ما تحتار بين مئات الخيارات، جهّزنا لك باقات غرفة كاملة منسّقة وجاهزة — تختار باقتك وتطلبها بضغطة وحدة، وبأقل الأسعار في السعودية. كل باقة من تِكسا للديكور لغرفة 5×5 متر تقريبًا وتجمع أرضية باركيه SPC ضد الماء، جدار مميز من بديل الشيبورد، ورق جدران كوري، ونعلة فايبر، بألوان نسّقها مختصّو الديكور. اضغط «أضف الباقة كاملة للسلة» وتنضاف منتجاتها الأربعة دفعة واحدة. قيمة المنتجات شاملة الضريبة حتى نفاذ الكمية.</p>
{chr(10).join(blocks)}
  <div class="tpk-sec">
    <h2>ليه تختار باقات تِكسا للديكور؟</h2>
    <p>فكرة الباقات إننا نسهّل عليك قرار الشراء: كل باقة مصمّمة لتغطي غرفة كاملة من الأرض إلى الجدران بألوان متناسقة، بدل ما تختار كل منتج لوحده وتخاف ما يتناسق. باركيه SPC مقاوم للماء والخدش يناسب المناخ السعودي، وبديل الشيبورد يعطي الجدار المميز دفء الخشب، وورق الجدران الكوري يكمّل باقي الجدران، والنعلة تعطي تشطيبًا نظيفًا. توريد وتركيب احترافي مع رفع المقاسات، وأسعار واضحة شاملة الضريبة.</p>
  </div>
  <div class="tpk-sec">
    <h2>أسئلة شائعة عن باقات الغرفة الكاملة</h2>
    <div class="tpk-faq">
      <details><summary>كم تكلفة تجديد غرفة كاملة مع تِكسا؟</summary><p>تبدأ الباقات من أقل من 3,399 ريال شامل الضريبة لغرفة 5×5 متر تقريبًا، وتشمل الأرضية والجدار المميز وورق الجدران والنعلة. القيمة تمثّل المنتجات، وتختلف حسب مقاس غرفتك وعدد الجدران.</p></details>
      <details><summary>كم عدد الباقات المتاحة؟</summary><p>خمس باقات منسّقة بألوان مختلفة — وكل باقة تشمل أربعة منتجات أساسية.</p></details>
      <details><summary>هل يشمل العرض التركيب؟</summary><p>نعم، تِكسا للديكور توفّر توريد وتركيب احترافي مع رفع المقاسات. السعر المعروض هو قيمة المنتجات.</p></details>
      <details><summary>هل الباركيه مناسب للمناخ السعودي؟</summary><p>نعم، باركيه SPC مقاوم للماء والرطوبة والخدش ولا يتقوّس كالخشب الطبيعي.</p></details>
      <details><summary>إلى متى يستمر العرض؟</summary><p>العرض ساري حتى نفاذ الكمية على التشكيلة المختارة من منتجات الباقات.</p></details>
    </div>
  </div>
{JS}
</section>
{SCHEMA}
<!-- /wp:html -->'''

open('/home/user/sama-sales-app/texa-packages/texa-packages-landing.html','w').write(html)
print('written', len(html), 'bytes; subtotals:',[(n,sum(P[k][3]*P[k][5] for k in ks)) for n,t,th,ks in PACKS])
