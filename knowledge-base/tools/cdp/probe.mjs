import { chromium } from 'playwright';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
await page.evaluate(()=>{window.location.hash='#wm.config/wm.config.warehouse.warehouse////';});
await page.waitForTimeout(2000);
await page.evaluate((h)=>{window.location.hash=h;}, process.argv[2] || '#wm.config/wm.config.partners.clients////');
await page.waitForTimeout(6000);
const fr = page.frames().find(f=>f.url().includes('jdadelivers') && f!==page.mainFrame()) || page.mainFrame();
console.log('HASH:', await page.evaluate(()=>window.location.hash).catch(()=>'?'));
console.log('TEXT:', (await fr.locator('body').innerText().catch(()=>'')).replace(/\s+/g,' ').slice(0,500));
const btns = await page.evaluate(()=>{
  const f=document.querySelector('iframe'); const w=f.contentWindow;
  return w.Ext.ComponentQuery.query('button').filter(x=>!x.isDestroyed && x.isVisible && x.isVisible())
    .map(x=>({text:x.text, itemId:x.itemId, disabled:x.disabled}));
});
console.log('BUTTONS:', JSON.stringify(btns));
await b.close();
