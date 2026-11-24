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
        <div class="tpk-img"><img src="{IMG.format(img)}" alt="{name} - باقات الديكور والتشطيب"></div>
        <div class="tpk-role">{role}</div>
        <div class="tpk-name">{name}</div>
        <div class="tpk-foot"><div><div class="tpk-price"><b>{price}</b> ريال</div><div class="tpk-qty">الوحدة: {uw} · العدد: {qty}</div></div><button type="button" class="tpk-add" onclick="texaAddOne({pid},{qty})">أضف للسلة</button></div>
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
      <button type="button" class="tpk-addall" onclick="texaAddPkg([{addarr}])">أضف الباقة كاملة للسلة</button>
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
.texa-pkg{--navy:#16213e;--orange:#cc5500;--orangeD:#b64d00;--gold:#e9b84a;--goldL:#f2c86f;max-width:none;margin:0;padding:0;font-family:Inter,sans-serif;direction:rtl;box-sizing:border-box;color:#1c1c1c;line-height:1.8;font-size:15.5px;}
.texa-pkg *{box-sizing:border-box;font-family:Inter,sans-serif;}
.texa-pkg .tpk-lead{font-size:17.92px;line-height:35.84px;font-weight:400;color:#1e1e1e;margin:0 0 18px;padding:0 18px;max-width:none;width:100%;}
.texa-pkg .tpk-h1{font-size:40px;font-weight:500;color:#1e1e1e;line-height:52px;margin:25px 0 0;padding:0 18px;}
.texa-pkg .tpk-strong{display:block;font-weight:700;font-size:17.92px;color:#1e1e1e;}
.texa-pkg .tpk-pack{margin:0 0 26px;background:transparent;}
.texa-pkg .tpk-phead{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;background:#cc5500;color:#fff;padding:20px 28px;border-radius:14px;margin:0 18px;box-shadow:0 6px 18px rgba(204,85,0,.22);}
.texa-pkg .tpk-pchip{display:inline-block;background:#fff;color:#cc5500;font-weight:800;font-size:13px;padding:5px 14px;border-radius:30px;margin-bottom:8px;}
.texa-pkg .tpk-phead h2{color:#fff;font-size:30px;font-weight:900;margin:0;line-height:1.15;}
.texa-pkg .tpk-pprice{font-size:16px;color:#fff;margin-top:4px;font-weight:600;}
.texa-pkg .tpk-pprice b{font-size:28px;color:#fff;font-weight:900;}
.texa-pkg .tpk-pprice small{display:block;font-size:12.5px;color:#ffe3cf;margin-top:2px;font-weight:400;}
.texa-pkg .tpk-addall{background:#fff;color:#1c1c1c;border:0;cursor:pointer;font-weight:800;font-size:15px;padding:13px 26px;border-radius:30px;white-space:nowrap;transition:background .15s;}
.texa-pkg .tpk-addall:hover{background:#fbeee4;}
.texa-pkg .tpk-row{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;padding:20px 18px 0;}
.texa-pkg .tpk-card{border:0;border-radius:0;padding:0;background:transparent;display:flex;flex-direction:column;text-align:right;}
.texa-pkg .tpk-img{position:relative;overflow:hidden;aspect-ratio:1;background:#f3f1ed;}
.texa-pkg .tpk-img img{width:100%;height:100%;object-fit:cover;display:block;}
.texa-pkg .tpk-badge{position:absolute;top:10px;right:10px;background:var(--navy);color:#fff;font-size:12px;font-weight:800;padding:4px 11px;border-radius:20px;}
.texa-pkg .tpk-role{font-size:13px;line-height:15px;color:var(--orange);font-weight:600;margin-top:16px;}
.texa-pkg .tpk-name{font-weight:500;color:#1e1e1e;font-size:20px;line-height:30px;margin:2px 0 0;min-height:60px;}
.texa-pkg .tpk-foot{display:flex;flex-direction:column;align-items:stretch;gap:12px;margin-top:0;}
.texa-pkg .tpk-price{color:#cc0008;font-size:20px;font-weight:800;line-height:23px;}
.texa-pkg .tpk-price b{font-size:20px;font-weight:800;color:#cc0008;}
.texa-pkg .tpk-qty{font-size:13px;line-height:15px;color:#484848;font-weight:400;margin-top:4px;}
.texa-pkg .tpk-add{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;background:#16213d;color:#e8b33d;border:0;cursor:pointer;font-weight:600;font-size:15.87px;line-height:26px;padding:16px 24px;border-radius:10px;}
.texa-pkg .tpk-add::before{content:"";width:17px;height:17px;flex:0 0 17px;background:currentColor;-webkit-mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7 18a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm10 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM3 2h2.6l.9 3H21l-2.2 8.2a2 2 0 0 1-1.9 1.5H8.4a2 2 0 0 1-1.9-1.5L4.1 4H3z'/%3E%3C/svg%3E") center/contain no-repeat;mask:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7 18a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm10 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM3 2h2.6l.9 3H21l-2.2 8.2a2 2 0 0 1-1.9 1.5H8.4a2 2 0 0 1-1.9-1.5L4.1 4H3z'/%3E%3C/svg%3E") center/contain no-repeat;}
.texa-pkg .tpk-add:hover{filter:brightness(1.15);}
.texa-pkg .tpk-sec{margin-top:40px;padding:0 18px;}
.texa-pkg .tpk-sec h2{font-size:28px;font-weight:500;line-height:40px;color:#1e1e1e;margin:0 0 10px;}
.texa-pkg .tpk-sec p{font-size:17.92px;line-height:35.84px;color:#1e1e1e;margin:0 0 12px;}
.texa-pkg .tpk-sec a{color:#cc5500;text-decoration:underline;}
.texa-pkg .tpk-faq details{background:#fff;border:1px solid #eee;border-radius:12px;padding:0 18px;margin-bottom:10px;}
.texa-pkg .tpk-faq summary{cursor:pointer;font-weight:600;color:#1c1c1c;font-size:15.5px;padding:14px 0;list-style:none;}
.texa-pkg .tpk-faq summary::-webkit-details-marker{display:none;}
.texa-pkg .tpk-faq summary::before{content:"\\002B";color:var(--orange);font-weight:900;margin-left:10px;}
.texa-pkg .tpk-faq details[open] summary::before{content:"\\2212";}
.texa-pkg .tpk-faq p{padding:0 0 16px;margin:0;color:#3a4256;font-size:15.5px;}
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
{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":"https://texadecore.store/"},{"@type":"ListItem","position":2,"name":"باقات الديكور والتشطيب","item":"https://texadecore.store/باقات-الديكور-والتشطيب/"}]},
{"@type":"Service","name":"باقات الديكور والتشطيب من تكسا","serviceType":"توريد وتركيب ديكور الغرف","provider":{"@type":"HomeGoodsStore","name":"تِكسا للديكور","url":"https://texadecore.store/","telephone":"+966591409002","areaServed":{"@type":"Country","name":"المملكة العربية السعودية"}},"offers":{"@type":"Offer","priceCurrency":"SAR","price":"3142","availability":"https://schema.org/InStock","url":"https://texadecore.store/باقات-الديكور-والتشطيب/"}},
{"@type":"ItemList","name":"منتجات باقات الديكور والتشطيب","itemListElement":[__ITEMS__]},
{"@type":"FAQPage","mainEntity":[
{"@type":"Question","name":"كم تكلفة باقات الديكور والتشطيب من تكسا؟","acceptedAnswer":{"@type":"Answer","text":"تبدأ باقات الغرفة الكاملة من أقل من 3,399 ريال شامل الضريبة لغرفة بمقاس 5×5 متر تقريبًا، وتشمل الأرضية والجدار المميز وورق الجدران والنعلة."}},
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
  <h1 class="tpk-h1">باقات الديكور والتشطيب من تكسا</h1>
  <p class="tpk-lead"><strong class="tpk-strong">سهّلناها عليك! بدل ما تحتار بين مئات الخيارات، جهّزنا لك باقات غرفة كاملة منسّقة وجاهزة</strong>باقات الديكور والتشطيب من تكسا تخلّيك تختار باقتك وتطلبها بضغطة وحدة، وبأقل الأسعار في السعودية. كل باقة لغرفة 5×5 متر تقريبًا وتجمع أرضية باركيه SPC ضد الماء، جدار مميز من بديل الشيبورد، ورق جدران كوري، ونعلة فايبر، بألوان نسّقها مختصّو الديكور. اضغط «أضف الباقة كاملة للسلة» وتنضاف منتجاتها الأربعة دفعة واحدة. قيمة المنتجات شاملة الضريبة حتى نفاذ الكمية.</p>
{chr(10).join(blocks)}
  <div class="tpk-sec">
    <h2>ليه تختار باقات الديكور والتشطيب من تكسا؟</h2>
    <p>فكرة <strong>باقات الديكور والتشطيب</strong> إننا نسهّل عليك قرار الشراء: كل باقة مصمّمة لتغطي غرفة كاملة من الأرض إلى الجدران بألوان متناسقة، بدل ما تختار كل منتج لوحده وتخاف ما يتناسق. <a href="https://texadecore.store/product-category/الباركيه/">باركيه SPC</a> مقاوم للماء والخدش يناسب المناخ السعودي، و<a href="https://texadecore.store/product-category/بديل-الشيبورد/">بديل الشيبورد</a> يعطي الجدار المميز دفء الخشب، و<a href="https://texadecore.store/product-category/ورق-الجدران/">ورق الجدران</a> الكوري يكمّل باقي الجدران، و<a href="https://texadecore.store/product-category/نعلات/">النعلات</a> تعطي تشطيبًا نظيفًا. باقات الديكور والتشطيب تناسب ديكورات غرف النوم والمجالس وتشطيب الشقق، مع توريد وتركيب احترافي ورفع مقاسات وأسعار واضحة شاملة الضريبة. وتقدر تشوف كمان <a href="https://texadecore.store/عروض-التشطيبات-والديكور/">عروض التشطيبات والديكور</a>.</p>
  </div>
  <div class="tpk-sec">
    <h2>أسئلة شائعة عن باقات الديكور والتشطيب</h2>
    <div class="tpk-faq">
      <details><summary>كم تكلفة باقات الديكور والتشطيب من تكسا؟</summary><p>تبدأ الباقات من أقل من 3,399 ريال شامل الضريبة لغرفة 5×5 متر تقريبًا، وتشمل الأرضية والجدار المميز وورق الجدران والنعلة. القيمة تمثّل المنتجات، وتختلف حسب مقاس غرفتك وعدد الجدران.</p></details>
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
