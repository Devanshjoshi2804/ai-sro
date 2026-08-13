import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const frame = await goto(page, '#wm.config/wm.config.partners.customers.types////');
await resetToGrid(page, frame); await page.waitForTimeout(1500);
console.log(JSON.stringify(await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const vis=(c)=>{const d=c.getEl&&c.getEl()&&c.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;};
  const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
  const evsrc = (comp, name) => (comp?.events?.[name]?.listeners||[]).map(l=>({scope:l.scope&&l.scope.$className, src:(l.fn||'').toString().slice(0,500)}));
  // which columns render a clickable cell?
  const cols = (g?.columns||[]).slice(0,4).map(c=>({ text:c.text, dataIndex:c.dataIndex, xtype:c.xtype,
    hasRenderer: typeof c.renderer==='function', rendererSrc: typeof c.renderer==='function'? c.renderer.toString().slice(0,300):null }));
  // the Landing view is the controller; list its listeners for record-open style events
  const landing = w.Ext.ComponentQuery.query('panel').filter(p=>/Landing/.test(p.$className||'')).pop();
  return {
    gridCellclick: evsrc(g,'cellclick'),
    gridItemclick: evsrc(g,'itemclick'),
    viewCellclick: evsrc(g?.getView(),'cellclick'),
    columns: cols,
    landingClass: landing?.$className,
    landingEvents: landing?.events? Object.keys(landing.events).filter(e=>/click|copy|select|edit|open|row/i.test(e)):[],
    landingCopied: evsrc(landing,'copied'),
  };
}), null, 1).slice(0,5000));
await b.close();
