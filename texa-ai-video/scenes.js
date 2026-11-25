const { chromium } = require('playwright'); const fs=require('fs'); const path=require('path');
const F='/home/user/sama-sales-app/texa-offer-videos/public/fonts/';
const b64=f=>fs.readFileSync(f).toString('base64');
const font=w=>`@font-face{font-family:Tj;font-weight:${w};src:url(data:font/woff2;base64,${b64(F+`tajawal-arabic-${w}-normal.woff2`)}) format('woff2');unicode-range:U+0600-06FF,U+200C-200E,U+2010-2011,U+204F,U+2E41,U+FB50-FDFF,U+FE80-FEFC;}@font-face{font-family:Tj;font-weight:${w};src:url(data:font/woff2;base64,${b64(F+`tajawal-latin-${w}-normal.woff2`)}) format('woff2');}`;
const img=n=>`data:image/png;base64,${b64('/home/user/sama-sales-app/texa-ai-video/work/'+n+'.png')}`;
const css=`${font(500)}${font(700)}${font(900)}
*{box-sizing:border-box;margin:0}body{width:1080px;height:1920px;font-family:Tj;direction:rtl;background:#cc5500;color:#fff;display:flex;flex-direction:column;overflow:hidden}
.top{height:190px;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:64px;letter-spacing:1px}
.bot{height:170px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:50px;direction:ltr;background:#a94600}
.mid{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:0 50px;gap:44px;text-align:center}
.big{font-weight:900;font-size:104px;line-height:1.35}.med{font-weight:700;font-size:62px;line-height:1.5}
.ask{background:#fff;color:#cc5500;font-weight:900;font-size:76px;padding:22px 60px;border-radius:60px}
.card{background:#fff;border-radius:36px;padding:26px;box-shadow:0 24px 60px rgba(0,0,0,.35);width:100%}.card img{width:100%;display:block;border-radius:18px}
.tag{background:#16213e;color:#e9b84a;font-weight:900;font-size:58px;padding:20px 50px;border-radius:24px}
.w{background:#fff;color:#cc5500;padding:6px 34px;border-radius:26px;display:inline-block}`;
const wrap=m=>`<html><head><meta charset=utf8><style>${css}</style></head><body><div class=top>تكسا ديكور</div><div class=mid>${m}</div><div class=bot>texadecore.store</div></body></html>`;
const S=[
 `<div class=big>تدوّر على<br><span class=w>بديل شيبورد</span><br>بسعر أقل<br>وجودة عالية؟</div>`,
 `<div class=ask>اسأل ChatGPT</div><div class=card><img src="${img('chatgpt')}"></div><div class=tag>تكسا ديكور قدّامك ✓</div>`,
 `<div class=ask>اسأل Perplexity</div><div class=card><img src="${img('perplexity')}"></div><div class=tag>تكسا ديكور قدّامك ✓</div>`,
 `<div class=ask>اسأل Gemini</div><div class=card><img src="${img('gemini')}"></div><div class=tag>تكسا ديكور قدّامك ✓</div>`,
 `<div class=med>وين ما تسأل…</div><div class=big>تلقى <span class=w>تكسا ديكور</span> قدّامك</div><div class=med>خيارك الأول لبديل الشيبورد<br>في السعودية</div><div class=tag>اطلب الحين</div>`];
(async()=>{const b=await chromium.launch({args:['--no-sandbox']});const p=await b.newPage({viewport:{width:1080,height:1920}});
for(let i=0;i<S.length;i++){await p.setContent(wrap(S[i]));await p.waitForTimeout(500);await p.screenshot({path:`/home/user/sama-sales-app/texa-ai-video/work/s${i+1}.png`});}
await b.close();})();
