import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
await goto(page, '#wm.config/wm.config.partners.customers.types////');
await resetToGrid(page, await (async()=>page.frames().find(f=>f.url().includes('jdadelivers')&&f!==page.mainFrame()))());
await page.waitForTimeout(1500);
console.log(JSON.stringify(await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const vis=(c)=>{const d=c.getEl&&c.getEl()&&c.getEl().dom;const r=d&&d.getBoundingClientRect();return r&&r.width>0&&r.height>0;};
  const btn = w.Ext.ComponentQuery.query('button').filter(x=>!x.isDestroyed&&x.itemId==='copyButton'&&vis(x)).pop();
  const plugin = btn && btn.events?.click?.listeners?.[0]?.scope;
  const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
  const itemclick = (g?.events?.itemclick?.listeners||[]).map(l=>({
    scope: l.scope && l.scope.$className, src: (l.fn||'').toString().slice(0,900)}));
  return {
    pluginClass: plugin && plugin.$className,
    doCopySrc: plugin && typeof plugin.doCopy === 'function' ? plugin.doCopy.toString().slice(0,900) : null,
    doDeleteSrc: plugin && typeof plugin.doDelete === 'function' ? plugin.doDelete.toString().slice(0,700) : null,
    gridItemclick: itemclick,
    ownerClass: plugin && plugin.owner && plugin.owner.$className,
    ownerEvents: plugin && plugin.owner && plugin.owner.events ? Object.keys(plugin.owner.events).filter(e=>/copy|edit|modify|request|select/i.test(e)) : [],
  };
}), null, 1).slice(0,5000));
await b.close();
