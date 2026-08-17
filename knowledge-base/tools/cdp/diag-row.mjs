import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const frame = await goto(page, '#wm.config/wm.config.partners.customers.types////');
await resetToGrid(page, frame); await page.waitForTimeout(1500);
// inspect the first row's DOM to learn how a record is opened
const info = await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const grids = w.Ext.ComponentQuery.query('grid').filter(g=>{const d=g.getEl&&g.getEl()&&g.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;});
  const g = grids[grids.length-1];
  if (!g) return {error:'no grid'};
  const node = g.getView().getNode(0);
  return {
    gridId: g.id, storeCount: g.getStore().getCount(),
    rowId: node?.id,
    rowHTML: node ? node.innerHTML.slice(0,400) : null,
    anchors: node ? node.querySelectorAll('a').length : 0,
    hasItemClickListener: !!(g.hasListener && g.hasListener('itemclick')),
    events: g.events ? Object.keys(g.events).filter(e=>/click|select/i.test(e)) : [],
  };
});
console.log(JSON.stringify(info,null,1));
await b.close();
