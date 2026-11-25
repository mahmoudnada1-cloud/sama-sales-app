const { chromium } = require('playwright'); const fs=require('fs');
const R='/home/user/sama-sales-app/texa-ai-video/', F='/home/user/sama-sales-app/texa-offer-videos/public/fonts/';
const b64=f=>fs.readFileSync(f).toString('base64');
const font=w=>`@font-face{font-family:Tj;font-weight:${w};src:url(data:font/woff2;base64,${b64(F+`tajawal-arabic-${w}-normal.woff2`)}) format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+FB50-FDFF,U+FE80-FEFC;}@font-face{font-family:Tj;font-weight:${w};src:url(data:font/woff2;base64,${b64(F+`tajawal-latin-${w}-normal.woff2`)}) format('woff2');}`;
const svg=(n,c)=>fs.readFileSync(R+'logos/'+n+'.svg','utf8').replace('<svg ',`<svg fill="${c}" `);
const gpath=(fs.readFileSync(R+'logos/googlegemini.svg','utf8').match(/ d="([^"]+)"/)||[])[1];
const gem=`<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><defs><clipPath id="gc"><path d="${gpath}"/></clipPath>
<radialGradient id="g1" cx="12" cy="0" r="11" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#EA4335"/><stop offset="1" stop-color="#EA4335" stop-opacity="0"/></radialGradient>
<radialGradient id="g2" cx="0" cy="12" r="11" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#FBBC04"/><stop offset="1" stop-color="#FBBC04" stop-opacity="0"/></radialGradient>
<radialGradient id="g3" cx="12" cy="24" r="11" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#34A853"/><stop offset="1" stop-color="#34A853" stop-opacity="0"/></radialGradient></defs>
<g clip-path="url(#gc)"><rect width="24" height="24" fill="#4285F4"/><rect width="24" height="24" fill="url(#g1)"/><rect width="24" height="24" fill="url(#g2)"/><rect width="24" height="24" fill="url(#g3)"/></g></svg>`;
const L={c:svg('openai','#111'),p:svg('perplexity','#13343b'),g:gem};
const Q='عروض بديل الشيبورد';
const LOGO=`data:image/png;base64,${b64('/home/user/sama-sales-app/texa-offer-videos/public/brand/logo.png')}`;
const card=(id,logo,name,body)=>`<div class="scene" id="${id}"><div class="ask">اسأل <b>${name}</b></div>
<div class="card"><div class="ch"><span class="lg">${logo}</span><span class="nm">${name}</span></div>
<div class="q"><span class="qt"></span><i class="cur"></i></div><div class="dots"><i></i><i></i><i></i></div>
<div class="ans">${body}</div><div class="src">مقتطف من الإجابة</div></div>
<div class="tag">تكسا ديكور قدّامك ✓</div></div>`;
const html=`<html><head><meta charset=utf8><style>${font(500)}${font(700)}${font(900)}
*{box-sizing:border-box;margin:0}body{width:1080px;height:1920px;font-family:Tj;direction:rtl;background:#faf9f7;color:#16213d;overflow:hidden;position:relative}
.top{position:absolute;top:0;left:0;right:0;height:320px;display:flex;align-items:flex-end;justify-content:center}.top img{height:200px;width:200px;object-fit:contain;background:#fff;border-radius:40px;padding:16px;box-shadow:0 14px 34px rgba(22,33,61,.16)}
.bot{position:absolute;bottom:0;left:0;right:0;height:150px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:46px;direction:ltr;background:#16213d;color:#e8b33d}
.scene{position:absolute;top:320px;bottom:150px;left:0;right:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:38px;padding:0 54px;text-align:center;opacity:0}
.big{font-weight:900;font-size:100px;line-height:1.75}.med{font-weight:700;font-size:60px;line-height:1.5;color:#5b6478}
.w{background:#cc5500;color:#fff;padding:0 34px;border-radius:26px;display:inline-block;line-height:1.35}
.ln{display:block;opacity:0}
.ask{font-weight:700;font-size:70px;color:#16213d}.ask b{font-weight:900;color:#cc5500}
.card{background:#fff;color:#1c1c1c;border-radius:40px;width:100%;padding:38px 44px 30px;box-shadow:0 20px 50px rgba(22,33,61,.16);border:2px solid #eee6da;text-align:right}
.ch{display:flex;align-items:center;gap:20px;padding-bottom:26px;border-bottom:2px solid #eee;direction:ltr}
.lg svg{width:76px;height:76px;display:block}.nm{font-weight:900;font-size:52px;color:#111}
.q{margin:30px 0 0;background:#eef3fb;border-radius:36px;padding:20px 38px;font-weight:700;font-size:46px;display:inline-block;min-height:96px}
.cur{display:inline-block;width:4px;height:46px;background:#333;vertical-align:middle;margin-right:6px}
.dots{height:60px;display:flex;gap:14px;align-items:center;margin-top:26px}.dots i{width:18px;height:18px;border-radius:50%;background:#bbb}
.ans{margin-top:-60px;font-size:42px;line-height:1.7;font-weight:500}.ans>*{opacity:0;display:block}
.ans h3{font-size:45px;font-weight:900;margin-bottom:10px}.ans h4{font-size:42px;font-weight:700;margin-top:6px}
.ans li{list-style:none;padding-right:8px}.ans li::before{content:'•';margin-left:16px;color:#888}.hl{background:#ffe2cc;color:#cc5500;font-weight:900;padding:0 14px;border-radius:12px;white-space:nowrap;display:inline-block;line-height:1.5;justify-self:start}
.lk{color:#1558d6;text-decoration:underline;font-weight:700;margin-top:10px}
.row{display:grid!important;grid-template-columns:300px 1fr;border-bottom:2px solid #eee;padding:16px 8px;align-items:center}.row.h{font-weight:900;background:#f6f6f6;border-radius:12px}
.chip{display:inline-block!important;background:#f0f0f0;border-radius:12px;padding:2px 20px;font-size:32px;color:#555;font-family:monospace;margin-top:14px}
.src{font-size:28px;color:#999;margin-top:22px;text-align:left}
.tag{background:#16213d;color:#e8b33d;font-weight:900;font-size:58px;padding:20px 54px;border-radius:26px;opacity:0}
.lgs{display:flex;gap:40px;direction:ltr}.lgs span{background:#fff;box-shadow:0 12px 30px rgba(22,33,61,.14);border:2px solid #eee6da;border-radius:36px;padding:26px;position:relative;display:block}.lgs svg{width:120px;height:120px;display:block}
.lgs em{position:absolute;bottom:-18px;right:-18px;background:#16a34a;color:#fff;width:60px;height:60px;border-radius:50%;font-style:normal;font-weight:900;font-size:38px;display:flex;align-items:center;justify-content:center}
</style></head><body><div class=top><img src="${LOGO}"></div>
<div class="scene" id="s0"><div class="big"><span class="ln">تدوّر على</span><span class="ln"><span class=w>بديل شيبورد</span></span><span class="ln">بسعر أقل</span><span class="ln">وجودة تجمّل؟</span></div></div>
${card('s1',L.c,'ChatGPT',`<h3 style="font-size:39px;white-space:nowrap">🔥 عروض بديل الشيبورد من <span class=hl>تِكسا للديكور</span></h3><h4>لماذا تختار بديل الشيبورد من تِكسا؟</h4><li>مقاس اللوح 120 × 290 سم.</li><li>تشكيلة ألوان وتشطيبات.</li><li>خيارات مناسبة لتجديد جدران المجالس وغرف النوم.</li><span class=lk>عروض بديل الشيبورد – متجر تِكسا للديكور ↗</span>`)}
${card('s2',L.p,'Perplexity',`<h3>عروض مميزة</h3><div class="row h"><span>المتجر</span><span>العرض</span></div><div class=row><span class=hl>تكسا ديكور</span><span>بديل شيبورد بيج لاتيه</span></div><div class=row><span class=hl>تكسا ديكور</span><span>بديل شيبورد بيج كاتشي</span></div><div class=row><span class=hl>تكسا ديكور</span><span>ألوان بني وخشبي وسادة</span></div><span class=chip>texadecore</span>`)}
${card('s3',L.g,'Gemini',`<h3>أبرز العروض في السوق السعودي</h3><li><span class=hl>تكسا ديكور:</span> عروض على الألواح القماشية والخشبية والرخامية…</li><span class=chip style="font-family:Tj">تكسا ديكور Texa Decor</span>`)}
<div class="scene" id="s4"><div class=lgs><span>${L.c}<em>✓</em></span><span>${L.p}<em>✓</em></span><span>${L.g}<em>✓</em></span></div><div class="med ln">وين ما تبحث وتسأل…</div><div class="big ln">تلقى <span class=w>تكسا ديكور</span> قدّامك</div><div class="med ln">وجهتك الأولى لبديل الشيبورد<br>في السعودية</div><div class="tag">اطلب الحين</div><div class="med ln">وخلي ديكورها غير.</div></div>
<div class=bot>texadecore.store</div>
<script>
const Q=${JSON.stringify(Q)},C=[0,3.5,6.36,9.14,11.34,23.35];
const cl=(x)=>Math.max(0,Math.min(1,x)),ez=x=>1-Math.pow(1-cl(x),3);
function show(e,p){e.style.opacity=ez(p);e.style.transform='translateY('+(1-ez(p))*40+'px)';}
window.setT=t=>{for(let i=0;i<5;i++){const s=document.getElementById('s'+i),a=C[i],b=C[i+1],l=t-a;
 const vis=t>=a-0.001&&t<b; s.style.opacity=vis?Math.min(cl(l/0.25),i<4?cl((b-t)/0.2):1):0; if(!vis)continue;
 if(i==0){s.querySelectorAll('.ln').forEach((e,k)=>show(e,(l-[0.05,0.7,1.6,2.3][k])/0.45));}
 else if(i<4){const n=Math.floor(cl((l-0.15)/0.4)*Q.length);s.querySelector('.qt').textContent=Q.slice(0,n);
  s.querySelector('.cur').style.opacity=n<Q.length?1:0;const A=0.8;
  const d=s.querySelector('.dots');d.style.opacity=(l>0.55&&l<A)?1:0;d.querySelectorAll('i').forEach((e,k)=>e.style.transform='translateY('+Math.sin((l*9)-k)*8+'px)');
  [...s.querySelector('.ans').children].forEach((e,k)=>show(e,(l-A-k*0.09)/0.25));
  show(s.querySelector('.src'),(l-A-0.6)/0.3);const tg=s.querySelector('.tag');show(tg,(l-1.3)/0.3);
  s.querySelectorAll('.hl').forEach(e=>{const p=cl((l-1.15)/0.3);e.style.background=p>0?'#cc5500':'#ffe2cc';e.style.color=p>0?'#fff':'#cc5500';});}
 else{show(s.querySelector('.lgs'),(l-0.05)/0.4);s.querySelectorAll('.ln').forEach((e,k)=>show(e,(l-[0.19,1.79,4.87,9.66][k])/0.45));show(s.querySelector('.tag'),(l-7.83)/0.4);}
}};
</script></body></html>`;
(async()=>{const b=await chromium.launch({args:['--no-sandbox']});const p=await b.newPage({viewport:{width:1080,height:1920}});
await p.setContent(html);await p.waitForTimeout(800);
const mode=process.argv[2];
if(mode==='test'){for(const t of [3.2,6.1,9.0,11.2,23.0]){await p.evaluate(t=>setT(t),t);await p.screenshot({path:R+`work/t${t}.png`});}}
else{fs.mkdirSync(R+'frames',{recursive:true});const fps=25,N=Math.round(23.35*fps);for(let i=0;i<N;i++){await p.evaluate(t=>setT(t),i/fps);await p.screenshot({path:R+`frames/f${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:92});}}
await b.close();})();
