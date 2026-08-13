/*
 * cap.mjs — capture create payloads using the component-resolving helpers in ext.mjs.
 * Usage: node tools/cdp/cap.mjs <spec>
 */
import { chromium } from 'playwright';
import { clickButton, setFields, activeForm, goto, resetToGrid } from './ext.mjs';
import { SPECS } from './capture2.mjs';

const key = process.argv[2];
const spec = SPECS[key];
if (!spec) { console.error('unknown spec', key); process.exit(1); }

const browser = await chromium.connectOverCDP('http://localhost:9222');
const page = browser.contexts()[0].pages().find(p => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];
const out = { spec: key, resource: spec.resource, requests: [] };
page.on('request', (r) => {
  if (r.method() !== 'GET' && !/webPerformanceEntries/.test(r.url()) && /\/data\/WM\/wm\//.test(r.url()))
    out.requests.push({ method: r.method(), url: r.url().split('?')[0], body: r.postData() });
});
try {
  const frame = await goto(page, spec.route);
  // A previous run may have left an Add form open; the SPA restores it and there is no Add button.
  out.reset = await resetToGrid(page, frame);
  await page.waitForTimeout(1500);
  out.add = await clickButton(frame, page, { itemId: 'addButton' });
  await page.waitForTimeout(3800);
  Object.assign(out, await setFields(page, spec.fields, spec.pickFirst, spec.relax, spec.relaxRadio));
  /*
   * Dependent combos: a child store (Service Level) only loads after its parent (Carrier) is
   * chosen, so a single pass finds it empty and the field stays required. Pick in phases,
   * waiting for each store to populate.
   */
  for (const phase of spec.pickPhases || []) {
    await page.waitForTimeout(2600);
    const r = await setFields(page, {}, phase, spec.relax, spec.relaxRadio);
    out['phase_' + phase.join('_')] = r;
    // Re-read validity AFTER each phase: the first pass ran before dependent stores loaded.
    if (r && r.invalid) out.invalid = r.invalid;
  }
  await page.waitForTimeout(700);
  if (out.invalid?.length) out.note = 'invalid before Save; not saving';
  else { out.save = await clickButton(frame, page, { itemId: 'saveButton' }); await page.waitForTimeout(5000); }
  out.ok = out.requests.some(r => r.method === 'POST');
} catch (e) { out.error = String(e).split('\n')[0].slice(0, 180); }
// Persist every capture: truncated console output has already cost one full re-run.
import fs from 'node:fs';
fs.mkdirSync('knowlegde_graph/blue-yonder-sce/index/captures', { recursive: true });
fs.writeFileSync(`knowlegde_graph/blue-yonder-sce/index/captures/${key}.json`, JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify({ spec: key, ok: out.ok, error: out.error, note: out.note,
  invalid: out.invalid, posts: out.requests.filter(r => r.method === 'POST').map(r => r.url.split('/wm/')[1]) }, null, 1));
await browser.close();
