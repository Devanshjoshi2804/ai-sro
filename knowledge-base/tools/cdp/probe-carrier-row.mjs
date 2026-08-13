import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const code = process.argv[2];
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const frame = await goto(page, '#wm.config/wm.config.partners.carriers.main////');
await resetToGrid(page, frame); await page.waitForTimeout(2000);
console.log(JSON.stringify(await page.evaluate((c) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis=(x)=>{const d=x.getEl&&x.getEl()&&x.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;};
  const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
  if(!g) return {error:'no grid'};
  const st = g.getStore();
  const before = { count: st.getCount(), total: st.getTotalCount ? st.getTotalCount() : null,
                   idx: st.findBy(r=>JSON.stringify(r.data).includes(c)) };
  st.sort('carrierCode','DESC');
  return { before, sorters: st.getSorters ? st.getSorters().length : null,
           firstAfterSortAttempt: st.getAt(0) ? st.getAt(0).get('carrierCode') : null };
}, code),null,1));
await page.waitForTimeout(3000);
console.log(JSON.stringify(await page.evaluate((c) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis=(x)=>{const d=x.getEl&&x.getEl()&&x.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;};
  const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
  const st = g.getStore();
  return { count: st.getCount(), first3: [0,1,2].map(i=>st.getAt(i)&&st.getAt(i).get('carrierCode')),
           idx: st.findBy(r=>JSON.stringify(r.data).includes(c)) };
}, code),null,1));
await b.close();
