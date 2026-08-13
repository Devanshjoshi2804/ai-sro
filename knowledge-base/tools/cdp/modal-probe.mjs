/*
 * Detect the failure mode where Save is absorbed with no request and no visible error: an ExtJS
 * modal that does not appear in accessibility snapshots but blocks the page with a mask.
 */
import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton, setFields } from './ext.mjs';
import { SPECS } from './capture2.mjs';
const key = process.argv[2];
const spec = SPECS[key];
const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages().find(p=>p.url().includes('jdadelivers')) || b.contexts()[0].pages()[0];
const reqs = [];
page.on('request', r => { if (/\/data\/WM\/wm\//.test(r.url()) && !/webPerformance/.test(r.url())) reqs.push(r.method()+' '+r.url().split('/wm/')[1].split('?')[0]); });
const frame = await goto(page, spec.route);
await resetToGrid(page, frame); await page.waitForTimeout(1200);
await clickButton(frame, page, { itemId: 'addButton' }); await page.waitForTimeout(3500);
const applied = await setFields(page, spec.fields, spec.pickFirst, spec.relax, spec.relaxRadio);
await page.waitForTimeout(600);
const before = reqs.length;
await clickButton(frame, page, { itemId: 'saveButton' }).catch(e => null);
await page.waitForTimeout(4500);
const after = await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  const floating = w.Ext.ComponentQuery.query('[floating]').filter(c => c.isVisible && c.isVisible());
  return {
    floatingCount: floating.length,
    dialogs: floating.map(c => ({ xtype: c.xtype, title: c.title || null,
      text: (c.el && c.el.dom ? c.el.dom.innerText : '').replace(/\s+/g,' ').slice(0,220) })),
    masks: document.querySelectorAll('.x-mask').length + w.document.querySelectorAll('.x-mask').length,
  };
});
// Dismiss any modal so the app is not left blocked for the next run.
await page.evaluate(() => {
  const w = document.querySelector('iframe').contentWindow;
  w.Ext.ComponentQuery.query('[floating]').filter(c => c.isVisible && c.isVisible())
    .forEach(c => { try { c.close ? c.close() : c.hide(); } catch (e) {} });
}).catch(() => {});
console.log(JSON.stringify({ spec: key, applied: applied.applied, invalid: applied.invalid,
  requestsBeforeSave: before, requestsAfterSave: reqs.length, newRequests: reqs.slice(before), ...after }, null, 1));
await b.close();
