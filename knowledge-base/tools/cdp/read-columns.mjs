/* Read the grid column configuration for a screen: which column opens a record, and how. */
import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const routes = {
  carriers: '#wm.config/wm.config.partners.carriers.main////',
  printers: '#wm.config/wm.config.equipment.hardware.printers////',
  workstations: '#wm.config/wm.config.equipment.hardware.workstations////',
  voiceDevices: '#wm.config/wm.config.equipment.hardware.voicedevices////',
  customerTypes: '#wm.config/wm.config.partners.customers.types////',
};
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const out = {};
for (const [name, route] of Object.entries(routes)) {
  const frame = await goto(page, route);
  await resetToGrid(page, frame); await page.waitForTimeout(1800);
  out[name] = await page.evaluate(() => {
    const w = document.querySelector('iframe').contentWindow;
    const vis=(c)=>{const d=c.getEl&&c.getEl()&&c.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;};
    const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
    if (!g) return { error: 'no visible grid' };
    const cols = (g.columns||[]).slice(0,5).map(c=>({ text:c.text, dataIndex:c.dataIndex, xtype:c.xtype }));
    const node = g.getView().getNode(0);
    const spanCls = w.RP?.dataview?.column?.LinkColumn?.prototype?.linkSpanCls;
    const classesInRow = node ? [...new Set([...node.querySelectorAll('*')].flatMap(e=>[...e.classList]))].filter(c=>/link|click|action/i.test(c)) : [];
    return {
      gridClass: g.$className, rows: g.getStore().getCount(),
      columns: cols, linkSpanCls: spanCls,
      rowHasLinkSpan: node ? !!node.querySelector('.'+spanCls) : null,
      clickishClassesInRow: classesInRow,
      cellclickListeners: (g.events?.cellclick?.listeners||[]).map(l=>l.scope&&l.scope.$className),
      itemclickListeners: (g.events?.itemclick?.listeners||[]).map(l=>l.scope&&l.scope.$className),
    };
  });
  console.error(name, '->', JSON.stringify(out[name]).slice(0,200));
}
console.log(JSON.stringify(out,null,1));
await b.close();
