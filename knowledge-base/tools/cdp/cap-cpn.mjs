/*
 * cap-cpn.mjs — Carrier PRO Number, the screen whose lookups never bind.
 *
 * Its Carrier field is a carrierLookup whose store is EMPTY until a search runs, so no value can
 * validate and Save produces no error, no modal and no request — strictly quieter than any other
 * failure on this app. The fix is to load the store first, then set the model value from a real
 * record, which is what a user's search does implicitly.
 */
import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton, setFields } from './ext.mjs';
import fs from 'node:fs';

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find(p => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];
const out = { spec: 'carrierProNumbers', resource: 'carrierProNumbers', requests: [] };
page.on('request', (r) => {
  if (r.method() !== 'GET' && !/webPerformanceEntries/.test(r.url()) && /\/data\/WM\/wm\//.test(r.url()))
    out.requests.push({ method: r.method(), url: r.url().split('?')[0], body: r.postData() });
});
try {
  const frame = await goto(page, '#wm.config/wm.config.partners.carriers.carrierpronumber////');
  await resetToGrid(page, frame); await page.waitForTimeout(1200);
  out.add = await clickButton(frame, page, { itemId: 'addButton' });
  await page.waitForTimeout(3800);

  // Load the lookup's store, then bind a real carrier from it.
  out.load = await page.evaluate(async () => {
    const w = document.querySelector('iframe').contentWindow;
    const forms = w.Ext.ComponentQuery.query('form').filter(x => {
      const d = x.getEl && x.getEl() && x.getEl().dom; const r = d && d.getBoundingClientRect();
      return r && r.width > 0;
    });
    const form = forms[forms.length - 1].getForm();
    const fld = form.findField('carrier');
    const store = fld.getStore();
    await new Promise((res) => { store.load({ callback: () => res() }); setTimeout(res, 8000); });
    if (!store.getCount()) return { loaded: 0 };
    const rec = store.getAt(0);
    fld.forceSelection = false;
    fld.setValue(rec.get('carrierCode'));
    if (typeof fld.validate === 'function') fld.validate();
    return { loaded: store.getCount(), picked: fld.getValue() };
  });

  Object.assign(out, await setFields(page, {
    addressName: { addressName: 'ZV Pro Addr', addressLine1: '1 ZV Street', addressCity: 'Testville', addressState: 'GA', addressPostalCode: '30301', countryName: 'USA' },
  }, [], ['addressName']));

  await page.waitForTimeout(800);
  if (out.invalid?.length) out.note = 'invalid before Save; not saving';
  else { out.save = await clickButton(frame, page, { itemId: 'saveButton' }); await page.waitForTimeout(5000); }
  out.ok = out.requests.some(r => r.method === 'POST');
} catch (e) { out.error = String(e).split('\n')[0].slice(0, 180); }
fs.writeFileSync('knowlegde_graph/blue-yonder-sce/index/captures/carrierProNumbers.json', JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify({ ok: out.ok, load: out.load, invalid: out.invalid, note: out.note, error: out.error,
  posts: out.requests.filter(r => r.method === 'POST').map(r => r.url.split('/wm/')[1]) }, null, 1));
await browser.close();
