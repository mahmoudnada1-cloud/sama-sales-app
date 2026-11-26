// Texa carousel builder — renders 1080x1350 brand slides from a JSON spec.
// usage: node build.mjs <spec.json> <outdir>
import pw from '/opt/node-tools/node_modules/playwright/index.js';
const { chromium } = pw;
import fs from 'fs';

const R = '/home/user/sama-sales-app/texa-carousels/';
const b64 = (f) => fs.readFileSync(R + f).toString('base64');
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const outdir = process.argv[3];
fs.mkdirSync(outdir, { recursive: true });

const C = { cream: '#faf9f7', navy: '#16213d', orange: '#cc5500', gold: '#e8b33d', grey: '#5b6478', line: '#e7ded2', white: '#fff' };
const font = (w) => `@font-face{font-family:Tj;src:url(data:font/woff2;base64,${b64(`ar-${w}.woff2`)}) format('woff2');font-weight:${w};}@font-face{font-family:Tj;src:url(data:font/woff2;base64,${b64(`la-${w}.woff2`)}) format('woff2');font-weight:${w};unicode-range:U+0000-024F;}`;
const LOGO = `data:image/png;base64,${b64('logo.png')}`;
const accent = spec.accent || C.orange;

const css = `
${font(500)}${font(700)}${font(900)}
*{margin:0;box-sizing:border-box;font-family:Tj,sans-serif}
body{width:1080px;height:1080px;background:${C.cream};color:${C.navy};direction:rtl;overflow:hidden;position:relative}
.pad{position:absolute;inset:0;padding:64px 80px 92px;display:flex;flex-direction:column}
.logo{width:120px;height:120px;object-fit:contain;background:#fff;border-radius:34px;padding:14px;box-shadow:0 10px 26px rgba(22,33,61,.12)}
.foot{position:absolute;left:0;right:0;bottom:40px;display:flex;align-items:center;justify-content:space-between;padding:0 90px;direction:ltr}
.foot .site{font-weight:700;font-size:34px;color:${C.navy}}
.foot .pg{font-weight:900;font-size:30px;color:#fff;background:${C.navy};border-radius:999px;padding:8px 22px}
.badge{min-width:92px;height:92px;border-radius:24px;background:${C.navy};color:${C.gold};font-weight:900;font-size:52px;display:flex;align-items:center;justify-content:center}
.kick{display:inline-block;background:${accent};color:#fff;font-weight:900;font-size:40px;padding:12px 34px;border-radius:999px}
.hl{color:${accent}}
.pillbig{display:inline-block;background:${accent};color:#fff;font-weight:900;border-radius:26px;padding:6px 34px;line-height:1.5}
.navybtn{display:inline-block;background:${C.navy};color:${C.gold};font-weight:900;font-size:44px;padding:24px 58px;border-radius:999px}
.swipe{position:absolute;bottom:120px;left:80px;display:flex;align-items:center;gap:16px;color:${C.grey};font-weight:700;font-size:40px;direction:ltr}
.swipe .arrow{width:72px;height:72px;border-radius:50%;background:${accent};color:#fff;display:flex;align-items:center;justify-content:center;font-size:44px}
.wm{position:absolute;font-weight:900;color:rgba(204,85,0,.06);font-size:520px;line-height:1;left:-40px;bottom:-120px}
</style>`;

function slideHTML(s, i, n) {
  const pg = `${i + 1}/${n}`;
  const foot = `<div class="foot"><span class="site">texadecore.store</span><span class="pg">${pg}</span></div>`;
  const footCta = `<div class="foot"><span class="site">texadecore.store&nbsp;&nbsp;·&nbsp;&nbsp;واتساب 0591409002</span><span class="pg">${pg}</span></div>`;
  const logoName = `<div style="display:flex;flex-direction:column;align-items:flex-start;gap:14px"><img class="logo" src="${LOGO}"><span style="font-weight:900;font-size:40px;color:${C.navy}">تِكسا للديكور</span></div>`;
  if (s.type === 'cover') {
    return `<div class="pad">${logoName}
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:34px">
        <div><span class="kick">${s.kick || 'دليل تِكسا'}</span></div>
        <div style="font-weight:900;font-size:80px;line-height:1.28">${s.title}</div>
        ${s.sub ? `<div style="font-weight:700;font-size:40px;color:${C.grey};line-height:1.55">${s.sub}</div>` : ''}
      </div></div>
      <div class="swipe"><span class="arrow">←</span><span>اسحب</span></div>${foot}`;
  }
  if (s.type === 'cta') {
    return `<div class="pad">${logoName}
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:36px">
        <div style="font-weight:900;font-size:68px;line-height:1.3">${s.title}</div>
        <div style="font-weight:700;font-size:42px;color:${C.grey};line-height:1.6">${s.sub || ''}</div>
        <div style="display:flex;flex-direction:column;gap:26px;margin-top:10px">
          ${(s.points || []).map((p) => `<div style="display:flex;align-items:center;gap:22px;font-weight:700;font-size:42px"><span style="color:${accent};font-size:38px">✓</span><span>${p}</span></div>`).join('')}
        </div>
        <div style="margin-top:20px"><span class="navybtn">${s.button || 'اطلب الحين'}</span></div>
      </div></div>${footCta}`;
  }
  // content
  return `<div class="pad"><div style="display:flex;align-items:center;justify-content:space-between">
      <div class="badge">${s.num}</div><img class="logo" src="${LOGO}" style="width:110px;height:110px"></div>
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:40px">
        <div style="font-weight:900;font-size:64px;line-height:1.3" class="hl">${s.title}</div>
        <div style="font-weight:700;font-size:48px;line-height:1.65;color:${C.navy}">${s.body}</div>
        ${s.note ? `<div style="font-weight:700;font-size:40px;color:${C.grey};line-height:1.6">${s.note}</div>` : ''}
      </div></div>${foot}`;
}

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1080, height: 1080 } });
const n = spec.slides.length;
for (let i = 0; i < n; i++) {
  await page.setContent(`<!doctype html><html><head><meta charset=utf8><style>${css}</style></head><body>${slideHTML(spec.slides[i], i, n)}</body></html>`);
  await page.waitForTimeout(250);
  await page.screenshot({ path: `${outdir}/slide_${String(i + 1).padStart(2, '0')}.png` });
}
await browser.close();
console.log('rendered', n, 'slides ->', outdir);
