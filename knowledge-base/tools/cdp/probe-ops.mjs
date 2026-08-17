import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const routes = JSON.parse((await import('node:fs')).readFileSync('tools/cdp/tier2-routes.json','utf8'));
const target = routes.receiving.find(r=>/Inbound Shipments|Appointments|Work Queue/i.test(r.text)) || routes.receiving[1];
await dismissBlocking(page);
await page.evaluate(()=>{window.location.hash='#wm.config/wm.config.partners.customers.types////';});
await page.waitForTimeout(2500);
await page.evaluate((h)=>{window.location.hash=h;}, target.href);
await page.waitForTimeout(12000);
console.log('target:', target.text, target.href);
for (const fr of page.frames()) {
  const r = await fr.evaluate(() => {
    if (!window.Ext) return null;
    const vis = c => { const d=c.getEl&&c.getEl()&&c.getEl().dom; const x=d&&d.getBoundingClientRect(); return x&&x.width>0&&x.height>0; };
    const all = window.Ext.ComponentQuery.query('component').filter(vis);
    const byType = {};
    all.forEach(c => { byType[c.xtype] = (byType[c.xtype]||0)+1; });
    return { url: location.href.slice(0,70), total: all.length,
      top: Object.entries(byType).sort((a,b)=>b[1]-a[1]).slice(0,12) };
  }).catch(()=>null);
  if (r && r.total) console.log(JSON.stringify(r,null,1));
}
await b.close();
