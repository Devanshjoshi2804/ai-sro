import { chromium } from 'playwright';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
console.log('frames attached:', page.frames().length);
const visible = await page.evaluate(() => {
  const ifr = [...document.querySelectorAll('iframe')];
  return { total: ifr.length, shown: ifr.filter(f => { const r = f.getBoundingClientRect(); return r.width>0 && r.height>0; }).length };
}).catch(e => ({error:String(e).slice(0,80)}));
console.log('top-level iframes:', JSON.stringify(visible));
// NOTE: do not close - browser.close() over CDP closes pages a concurrent run is using.
process.exit(0);
