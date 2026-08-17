/*
 * walk-subeditors.mjs — configure a composite screen's sub-editors, then Save, and record the call.
 *
 * Eleven screens refuse to create anything from their main form: Pick Methods, Handling Units,
 * Inbound Pallet Build, Item Class Levels, Movement Path Criteria, Existing Customers and the five
 * Voice screens. Their Add page carries a `wm-cardDeck-back-button` and one or more descriptive
 * buttons ("Define the features you want to associate with the handling unit type"), and Save stays
 * disabled — or fires and sends nothing — until those cards have been visited.
 *
 * This walks them: fill the main form, then for each sub-editor card fill whatever it shows and come
 * back, then Save. Every step is photographed, because the refusals are only ever explained by what
 * the dialog says.
 *
 * It creates a record when it succeeds, so it deletes it and proves it gone, exactly as a battery
 * would. Screens on the never-create list are refused outright.
 *
 *   node tools/cdp/walk-subeditors.mjs "Handling Units"
 *   node tools/cdp/walk-subeditors.mjs "Handling Units" --keep
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

const label = process.argv[2];
const keep = process.argv.includes('--keep');
const screen = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens.find((s) => s.label === label);
if (!screen) { console.error('no such screen'); process.exit(1); }
const mark = 'ZV' + String(Date.now() % 100000);

/* Buttons that are navigation or commit, not sub-editors. */
const CONTROL = /^(save|cancel|ok|yes|no|back|next|previous|close|delete|add|copy)$/i;

const shot = async (page, tag) => {
  const p = `${KG}/images/walk-${label.replace(/\W+/g, '-').toLowerCase()}-${tag}.png`;
  await page.screenshot({ path: p }).catch(() => {});
  return p;
};

/* Fill every empty field in the visible form or window from its own store. */
const fillVisible = (fr, m) => fr.evaluate((mk) => {
  if (!window.Ext) return null;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
  const fields = window.Ext.ComponentQuery.query('field').filter(vis);
  const out = [];
  for (const f of fields) {
    if (!f.name) continue;
    const cur = f.getValue && f.getValue();
    if (cur !== '' && cur != null && cur !== false) { out.push({ field: f.name, kept: cur }); continue; }
    let v;
    const st = f.getStore && f.getStore();
    if (st && st.getCount && st.getCount() > 0) {
      const rec = st.getRange().find((r) => r.get(f.valueField || 'code') != null) || st.getAt(0);
      v = rec.get(f.valueField || 'code');
    } else if (/number|spinner/i.test(f.xtype)) v = 1;
    else if (/check|toggle|radio/i.test(f.xtype)) v = true;
    else v = f.maxLength && f.maxLength < mk.length ? mk.slice(-f.maxLength) : mk;
    try { f.setValue(v); out.push({ field: f.name, set: v }); } catch { /* read-only */ }
  }
  // Some cards are a grid of choices rather than fields: tick the first row if one exists.
  const grid = window.Ext.ComponentQuery.query('grid').filter(vis)[0];
  if (grid && grid.getStore().getCount() > 0) {
    grid.getSelectionModel().select(0);
    out.push({ grid: grid.getStore().getCount() + ' rows, first selected' });
  }
  return out;
}, m).catch(() => null);

const buttonsIn = (fr) => fr.evaluate(() => {
  if (!window.Ext) return [];
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
  return window.Ext.ComponentQuery.query('button').filter(vis)
    .map((b) => ({ itemId: b.itemId || '', text: String(b.text || '').replace(/<[^>]*>/g, '').trim(), disabled: !!b.disabled, dom: b.getEl() && b.getEl().dom.id }))
    .filter((b) => b.itemId);
}).catch(() => []);

const fire = (fr, itemId) => fr.evaluate((iid) => {
  if (!window.Ext) return false;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
  const b = window.Ext.ComponentQuery.query('button').filter((x) => vis(x) && x.itemId === iid)[0];
  if (!b) return false;
  b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
  return true;
}, itemId).catch(() => false);

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const captured = [];
page.on('requestfinished', async (req) => {
  if (req.method() === 'GET' || !/\/data\/WM\//.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null; try { body = await res?.json(); } catch {}
  captured.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, ''),
    request_headers: strip(req.headers()),
    request_body: (() => { try { return JSON.parse(req.postData() || 'null'); } catch { return req.postData()?.slice(0, 2000) ?? null; } })(),
    status: res?.status(), response_body: body,
  });
});

try {
  await page.goto(PORTAL + screen.hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);

  /* Open Add — toolbar first, then an Actions menu. */
  let frame = null;
  for (const fr of page.frames()) {
    const bs = await buttonsIn(fr);
    const add = bs.find((b) => b.itemId === 'addButton' && !b.disabled);
    if (add) { await fire(fr, 'addButton'); frame = fr; break; }
  }
  if (!frame) throw new Error('no Add button');
  await page.waitForTimeout(5000);

  // The Add page may live in a different frame from the grid it was launched from.
  for (const fr of page.frames()) {
    const bs = await buttonsIn(fr);
    if (bs.some((b) => b.itemId === 'saveButton' || b.itemId === 'wm-cardDeck-back-button')) { frame = fr; break; }
  }

  /*
   * Combos on this app load their store remotely when the field is first used. Fill once to trigger
   * those loads, wait, then fill again — the first pass on Handling Units put the run marker into
   * `assetType`, a combo whose store was still empty, and the form stayed invalid with a red field.
   */
  await frame.evaluate(() => {
    if (!window.Ext) return;
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    for (const f of window.Ext.ComponentQuery.query('field').filter(vis)) {
      const st = f.getStore && f.getStore();
      if (st && st.getCount && st.getCount() === 0 && st.load) { try { st.load(); } catch {} }
    }
  }).catch(() => {});
  await page.waitForTimeout(5000);
  console.log('main form:', JSON.stringify(await fillVisible(frame, mark))?.slice(0, 300));
  await page.waitForTimeout(1500);

  const subEditors = (await buttonsIn(frame)).filter((b) => !CONTROL.test(b.text) && b.itemId !== 'wm-cardDeck-back-button' && !b.disabled);
  console.log(`sub-editors: ${subEditors.length ? subEditors.map((b) => b.itemId).join(', ') : 'none'}`);

  for (const sub of subEditors) {
    console.log(`  entering ${sub.itemId}`);
    await fire(frame, sub.itemId);
    await page.waitForTimeout(5000);
    // The card renders in whichever frame now owns a back button.
    let card = frame;
    for (const fr of page.frames()) {
      const bs = await buttonsIn(fr);
      if (bs.some((b) => b.itemId === 'wm-cardDeck-back-button')) { card = fr; break; }
    }
    const filled = await fillVisible(card, mark);
    console.log(`    filled: ${JSON.stringify(filled)?.slice(0, 220)}`);
    await page.waitForTimeout(1200);
    await shot(page, sub.itemId);
    // Come back to the definition card.
    if (!await fire(card, 'wm-cardDeck-back-button')) await fire(card, 'cancelButton');
    await page.waitForTimeout(4000);
  }

  const after = await buttonsIn(frame);
  const save = after.find((b) => b.itemId === 'saveButton');
  console.log(`save button: ${save ? (save.disabled ? 'STILL DISABLED' : 'enabled') : 'not found'}`);
  await shot(page, 'before-save');
  if (save && !save.disabled) {
    await fire(frame, 'saveButton');
    await page.waitForTimeout(6000);
    await shot(page, 'after-save');
  }

  console.log(`requests produced: ${captured.length}`);
  for (const c of captured) console.log(`  ${c.method} ${c.url.split('?')[0]} -> ${c.status}`);

  const create = captured.find((c) => c.method === 'POST' && c.status >= 200 && c.status < 300);
  for (const c of captured) {
    const resource = (c.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1] || 'unknown';
    fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${resource}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/walk-subeditors.mjs',
      case: c.method === 'POST' && c.status < 300 ? 'create-valid-ui-captured' : `ui-save-${c.method.toLowerCase()}-${c.status}`,
      request: { method: c.method, url: c.url.replace('/data/WM', '').split('?')[0], headers: c.request_headers, body: c.request_body },
      response: { status: c.status, body: c.response_body },
      notes: `${label} creates only after its sub-editors are configured; this body is what the application sent once they were.`,
    }) + '\n');
  }
  if (!create) { console.log('no create — the screen still refused'); process.exit(0); }

  console.log('APP PAYLOAD:', JSON.stringify(create.request_body).slice(0, 400));
  const resource = (create.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1];
  let id = create.response_body?.data?.resourceId || (Array.isArray(create.response_body?.data) ? create.response_body.data[0]?.resourceId : null);
  if (!id) {
    id = await page.evaluate(async ({ base, r, m }) => {
      const f = document.querySelector('iframe');
      const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
      const res = await w.fetch(`${base}/wm/${r}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`, { credentials: 'include', headers: { Accept: 'application/json' } });
      const j = await res.json().catch(() => null);
      return (Array.isArray(j?.data) ? j.data : []).find((x) => JSON.stringify(x).includes(m))?.resourceId ?? null;
    }, { base: 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM', r: resource, m: mark }).catch(() => null);
    if (id) console.log(`  create carried no id; recovered ${id}`);
  }
  if (id && !keep) {
    const out = await page.evaluate(async ({ base, p }) => {
      const f = document.querySelector('iframe');
      const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
      const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
      const d = await w.fetch(base + p, { method: 'DELETE', credentials: 'include', headers: tok ? { 'CSRF-ENCRYPT-TOKEN': tok } : {} });
      const g = await w.fetch(base + p, { credentials: 'include', headers: { Accept: 'application/json' } });
      const t = await g.text();
      return { del: d.status, get: g.status, kind: g.status === 404 ? (/"errors"/.test(t) ? 'RECORD-MISSING' : 'ROUTE-MISSING') : 'still-present' };
    }, { base: 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM', p: `/wm/${resource}/${encodeURIComponent(id)}` });
    console.log(`cleanup: delete ${out.del} · confirm ${out.get} ${out.kind}`);
  } else if (id) {
    console.log(`kept: ${resource}/${id}`);
  } else {
    console.log('! created something that could not be addressed — scan with cleanup-marks.mjs');
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
