/* Enumerate the sub-navigation of a Tier 2/3 area. Read-only. */
import { chromium } from 'playwright';
import { appFrame, dismissBlocking } from './ext.mjs';
import { SCREENS } from './trace-readonly.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const out = {};
const names = process.argv[2] ? [process.argv[2]] : Object.keys(SCREENS);
for (const n of names) {
  await dismissBlocking(page);
  await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
  await page.waitForTimeout(2000);
  await page.evaluate((h) => { window.location.hash = h; }, SCREENS[n]);
  await page.waitForTimeout(6500);
  out[n] = await page.evaluate(() => {
    const w = document.querySelector('iframe')?.contentWindow || window;
    const items = [];
    // Sub-nav renders as menu items / tabs carrying the route they activate.
    if (w.Ext) {
      for (const c of w.Ext.ComponentQuery.query('menuitem, tab, button')) {
        if (c.isDestroyed) continue;
        const txt = String(c.text || '').replace(/<[^>]*>/g, '').trim();
        if (!txt) continue;
        const href = c.href || c.hrefTarget || (c.initialConfig && (c.initialConfig.route || c.initialConfig.hash)) || null;
        const route = c.route || (c.initialConfig && c.initialConfig.viewRef) || null;
        items.push({ text: txt.slice(0, 40), xtype: c.xtype, href, route });
      }
    }
    // Also read anchors in the top nav, which carry real hashes.
    const anchors = [...document.querySelectorAll('a[href*="#"]')].map(a => ({ text: a.innerText.trim().slice(0,40), href: a.getAttribute('href') }))
      .filter(a => a.text);
    return { items: items.slice(0, 40), anchors: anchors.slice(0, 40), hash: location.hash.slice(0, 80) };
  });
  console.error(n, '->', (out[n].items||[]).length, 'items,', (out[n].anchors||[]).length, 'anchors');
}
console.log(JSON.stringify(out, null, 1));
await b.close();
