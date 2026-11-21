const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs');
const OUT = process.argv[2];
const jobs = JSON.parse(process.argv[3]);
const VP = { mobile: { width: 390, height: 844 }, desktop: { width: 1440, height: 900 } };
const UA_M = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1';
(async () => {
  const browser = await chromium.launch();
  const log = [];
  for (const j of jobs) for (const dev of (j.devs || ['mobile', 'desktop'])) {
    const ctx = await browser.newContext({ viewport: VP[dev], locale: 'ar-SA', ...(dev === 'mobile' ? { isMobile: true, hasTouch: true, deviceScaleFactor: 2 } : {}) });
    const page = await ctx.newPage();
    const rec = { name: j.name, dev, url: j.url, at: new Date().toISOString() };
    try {
      const r = await page.goto(j.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      rec.status = r && r.status(); rec.finalUrl = page.url();
      await page.waitForLoadState('load', { timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(2500);
      rec.title = await page.title();
      await page.screenshot({ path: `${OUT}/${j.name}-${dev}.png` });
      // scroll through to trigger lazy load, then footer
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      rec.pageHeight = h;
      for (let y = 0; y < h; y += 1500) { await page.evaluate(v => window.scrollTo(0, v), y); await page.waitForTimeout(150); }
      if (j.footer) {
        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
        await page.waitForTimeout(1500);
        await page.screenshot({ path: `${OUT}/${j.footer}-${dev}.png` });
        rec.footerText = await page.evaluate(() => { const f = document.querySelector('footer, .elementor-location-footer, #colophon'); return f ? f.innerText.replace(/\n{2,}/g, '\n').slice(0, 3000) : null; });
        rec.footerImgs = await page.evaluate(() => { const f = document.querySelector('footer, .elementor-location-footer, #colophon'); return f ? [...f.querySelectorAll('img')].map(i => (i.alt || '') + ' | ' + (i.currentSrc || i.src).split('/').pop().slice(0, 80)) : null; });
        rec.footerLinks = await page.evaluate(() => { const f = document.querySelector('footer, .elementor-location-footer, #colophon'); return f ? [...f.querySelectorAll('a')].map(a => a.innerText.trim().slice(0, 30) + ' -> ' + decodeURI(a.href)).slice(0, 80) : null; });
      }
      if (j.mid) { await page.evaluate(v => window.scrollTo(0, v), j.mid); await page.waitForTimeout(1200); await page.screenshot({ path: `${OUT}/${j.name}-scroll-${dev}.png` }); }
      if (j.extract) rec.extract = await page.evaluate(j.extract);
    } catch (e) { rec.error = String(e).slice(0, 300); }
    log.push(rec); await ctx.close();
  }
  await browser.close();
  console.log(JSON.stringify(log, null, 1));
})();
