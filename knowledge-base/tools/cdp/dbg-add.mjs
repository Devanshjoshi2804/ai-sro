import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
await dismissBlocking(page);
await page.evaluate(()=>{window.location.hash='#wm.config/wm.config.warehouse.warehouse////';});
await page.waitForTimeout(2000);
await page.evaluate(()=>{window.location.hash='#wm.config/wm.config.partners.customers.types////';});
await page.waitForTimeout(6000);
console.log('frames:', page.frames().length);
// which frames have Ext and an addButton?
for (const fr of page.frames()) {
  const r = await fr.evaluate(() => {
    if (!window.Ext) return null;
    const vis=(c)=>{const d=c.getEl&&c.getEl()&&c.getEl().dom;const x=d&&d.getBoundingClientRect();return x&&x.width>0&&x.height>0;};
    const btns = window.Ext.ComponentQuery.query('button').filter(x=>!x.isDestroyed&&vis(x));
    return { url: location.href.slice(-45), buttons: btns.map(x=>x.itemId||x.text).filter(Boolean).slice(0,10),
             addVisible: btns.filter(x=>x.itemId==='addButton').length, forms: window.Ext.ComponentQuery.query('form').filter(vis).length };
  }).catch(()=>null);
  if (r) console.log(JSON.stringify(r));
}

await b.close();
