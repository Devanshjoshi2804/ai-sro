import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';
const targets = [
  ['Allocation Rules', '#wm.config/Allocation-Rules////'],
  ['MLS Catalog', '#wm.config/wm.config.advanced.mlscatalog////'],
];
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
for (const [label, hash] of targets) {
  await dismissBlocking(page);
  await page.evaluate(()=>{window.location.hash='#wm.config/wm.config.partners.customers.types////';});
  await page.waitForTimeout(3000);
  await page.evaluate((h)=>{window.location.hash=h;}, hash);
  await page.waitForTimeout(12000);   // generous: these may be heavy builders
  const r = await page.evaluate(() => {
    const w = document.querySelector('iframe')?.contentWindow;
    const doc = document.querySelector('iframe')?.contentDocument;
    const vis = c => { const d=c.getEl&&c.getEl()&&c.getEl().dom; const x=d&&d.getBoundingClientRect(); return x&&x.width>0&&x.height>0; };
    return {
      title: document.title,
      body: (doc?.body?.innerText||'').replace(/\s+/g,' ').slice(0,220),
      extComponents: w?.Ext ? w.Ext.ComponentQuery.query('component').filter(vis).length : null,
      panels: w?.Ext ? w.Ext.ComponentQuery.query('panel').filter(vis).length : null,
      iframes: doc ? doc.querySelectorAll('iframe').length : null,
    };
  });
  console.log(label, '->', JSON.stringify(r, null, 1));
}
await b.close();
