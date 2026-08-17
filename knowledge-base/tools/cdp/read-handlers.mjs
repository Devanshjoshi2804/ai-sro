/* Read the grid's real event handlers instead of guessing at clicks. */
import { chromium } from 'playwright';
import { goto, resetToGrid } from './ext.mjs';
const b = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const frame = await goto(page, process.argv[2] || '#wm.config/wm.config.partners.customers.types////');
await resetToGrid(page, frame); await page.waitForTimeout(1500);
console.log(JSON.stringify(await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d=c.getEl&&c.getEl()&&c.getEl().dom; const r=d&&d.getBoundingClientRect(); return r&&r.width>0&&r.height>0; };
  const grids = w.Ext.ComponentQuery.query('grid').filter(vis);
  const g = grids[grids.length-1];
  if (!g) return { error: 'no grid' };
  const dump = (comp, names) => {
    const out = {};
    for (const n of names) {
      const ev = comp.events && comp.events[n];
      if (!ev || !ev.listeners) { out[n] = null; continue; }
      out[n] = ev.listeners.map(l => {
        const fn = l.fn || l.fireFn;
        const src = typeof fn === 'function' ? fn.toString() : String(fn);
        return { scopeType: l.scope && l.scope.$className, src: src.slice(0, 700) };
      });
    }
    return out;
  };
  const view = g.getView();
  // Buttons carry their own handlers; read those too rather than clicking blind.
  const btns = {};
  for (const b of w.Ext.ComponentQuery.query('button').filter(x => !x.isDestroyed && ['copyButton','deleteButton','addButton'].includes(x.itemId) && vis(x))) {
    btns[b.itemId] = {
      hasHandler: typeof b.handler === 'function',
      handlerSrc: typeof b.handler === 'function' ? b.handler.toString().slice(0, 700) : null,
      clickListeners: (b.events && b.events.click && b.events.click.listeners || []).map(l => (l.fn||'').toString().slice(0,500)),
    };
  }
  return {
    gridId: g.id, gridClass: g.$className,
    gridEvents: dump(g, ['itemclick','cellclick','beforeitemclick','selectionchange','itemdblclick']),
    viewEvents: dump(view, ['itemclick','cellclick','itemdblclick']),
    controllerHint: g.up && g.up('panel') && g.up('panel').$className,
    buttons: btns,
  };
}), null, 1).slice(0, 6000));
await b.close();
