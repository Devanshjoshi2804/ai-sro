/*
 * capture-action-pair.mjs — capture a REAL operational write and its inverse, back to back.
 *
 * Operational writes are the most valuable thing left to learn and the most dangerous to probe, so
 * the ones worth doing first are the ones that undo each other: Suspend/Resume, Apply/Release.
 * Running the pair means the system ends where it started, and two verbs get recorded instead of one.
 *
 * The protocol is the same one that caught every earlier silent failure:
 *   read the record's state -> do A -> record every request -> read state -> do B -> record -> read
 * and then compare the first and last states. A 200 is not the finding; the state change is.
 *
 * If B produces no request, the run says so loudly: the record is left in the state A put it in, and
 * that is an operational consequence someone has to undo.
 *
 *   node tools/cdp/capture-action-pair.mjs --route "#wm.picking/wm.workqueue////" \
 *     --a "Suspend Work" --b "Resume Work" --resource work --id workRequestId --watch workRequestStatus
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const TELEMETRY = /webPerformanceEntries|rpux\/persistence|serverStatus/;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > -1 ? process.argv[i + 1] : d; };
const route = arg('route');
const actionA = arg('a');
const actionB = arg('b');
const resource = arg('resource');
const idField = arg('id');
const watch = arg('watch');
const dry = process.argv.includes('--dry');
if (!route || !actionA || !actionB || !resource || !idField) {
  console.error('usage: --route <hash> --a "<action>" --b "<inverse>" --resource <res> --id <idField> [--watch <field>] [--dry]');
  process.exit(1);
}
const OUT = `${KG}/http/flows/${actionA.replace(/\W+/g, '')}-${actionB.replace(/\W+/g, '')}.json`;

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

let bucket = [];
page.on('requestfinished', async (req) => {
  if (req.method() === 'GET' || !/\/data\/WM\//.test(req.url()) || TELEMETRY.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null; try { body = await res?.json(); } catch {}
  bucket.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, '').split('&_dc')[0],
    request_headers: strip(req.headers()),
    request_body: (() => { try { return JSON.parse(req.postData() || 'null'); } catch { return req.postData()?.slice(0, 3000) ?? null; } })(),
    status: res?.status(), response_body: body,
  });
});

const api = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  const r = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } });
  const t = await r.text();
  let j = null; try { j = JSON.parse(t); } catch {}
  return { status: r.status, body: j, sessionExpired: !j && /b2clogin|<html/i.test(t) };
}, { url, base: BASE });

/* Read the record straight from the API, so the state is not the grid's opinion of itself. */
const stateOf = async (id) => {
  const q = encodeURIComponent(JSON.stringify([{ column: idField, operator: 'EQ', value: isNaN(Number(id)) ? id : Number(id) }]));
  const r = await api(`/wm/${resource}?query=${q}&offset=0&limit=5&siteId=SG&subsites=----`);
  const row = (r.body?.data ?? [])[0];
  return { status: r.status, found: !!row, watched: row && watch ? row[watch] : undefined, row_keys: row ? Object.keys(row).length : 0 };
};

/* Open the Actions menu and fire one item; poll, because the menu renders late. */
async function fireAction(frame, text) {
  await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const b = window.Ext.ComponentQuery.query('button').filter(vis)
      .find((x) => /actionsBtn$/i.test(x.itemId || '') || /^Actions$/i.test(String(x.text || '').trim()));
    if (b && b.menu && b.showMenu) b.showMenu();
  }).catch(() => {});
  /*
   * CLICK the menu item's element. `fireHandler()` is a NO-OP on these items — Suspend Work reported
   * "fired", raised no dialog, sent no request and left the record untouched, because the handler
   * lives on the menu's click event rather than on the item. Same lesson as the grid link columns.
   */
  for (let i = 0; i < 6; i++) {
    await page.waitForTimeout(2000);
    const domId = await frame.evaluate((t) => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
      const it = window.Ext.ComponentQuery.query('menu').filter(vis).flatMap((m) => m.query('menuitem'))
        .find((x) => !x.disabled && clean(x.text) === t);
      return it && it.getEl() ? it.getEl().dom.id : null;
    }, text).catch(() => null);
    if (domId) {
      await frame.locator('#' + domId).click({ timeout: 5000 }).catch(() => {});
      return true;
    }
  }
  return false;
}

/*
 * Confirm whatever the action raises.
 *
 * Some actions open a PICKER — Assign User shows a grid of every warehouse user — and there is no
 * submit button until a row is chosen. So: select the first row of any grid inside the dialog, then
 * look for the submit. Without this the run reported "dialog with no submit button" and moved on,
 * leaving the picker open for the next action to misread.
 */
async function confirmDialog(frame) {
  await page.waitForTimeout(4000);
  /*
   * Select inside the picker and CONFIRM the selection took. Assign User's Select button is disabled
   * until a row is chosen, and one earlier run selected into a grid that had not finished loading its
   * 249 users — the button stayed disabled and the action looked impossible.
   */
  for (let i = 0; i < 5; i++) {
    const sel = await frame.evaluate(() => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
      if (!win) return 0;
      const grid = win.query('grid').find((g) => g.getStore && g.getStore().getCount() > 0);
      if (!grid) return 0;
      grid.getSelectionModel().select(0);
      return grid.getSelectionModel().getSelection().length;
    }).catch(() => 0);
    if (sel) break;
    await page.waitForTimeout(2000);
  }
  await page.waitForTimeout(1500);
  /*
   * A picker with no submit button commits on DOUBLE-CLICK of the row. Assign User has no OK at all —
   * the grid of users IS the control — so without this the action can only ever be cancelled.
   */
  const rowEl = await frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
    if (!win) return null;
    const hasSubmit = win.query('button').some((b) => /^(yes|ok|apply|save|confirm|assign|suspend|resume|release)$/i.test(String(b.text || '').trim()));
    if (hasSubmit) return null;
    const grid = win.query('grid').find((g) => g.getStore && g.getStore().getCount() > 0);
    if (!grid) return null;
    const node = grid.getView().getNode(0);
    return node && node.id ? { id: node.id, chose: grid.getStore().getAt(0).data } : null;
  }).catch(() => null);
  if (rowEl) {
    console.log(`  picker has no submit button; double-clicking row: ${JSON.stringify(rowEl.chose).slice(0, 120)}`);
    await frame.locator('#' + rowEl.id).dblclick({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(4000);
  }
  return frame.evaluate(() => {
    const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
    const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
    const buttons = window.Ext.ComponentQuery.query('button').filter(vis);
    const fire = (b) => { b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b); };
    const text = win && win.getEl && win.getEl() ? win.getEl().dom.innerText.replace(/\s+/g, ' ').trim().slice(0, 200) : '';
    // "Select" belongs in this list: the picker dialogs commit through a Select button, not an OK.
    const go = (win ? win.query('button') : buttons)
      .filter((b) => !b.disabled)
      .find((b) => /^(yes|ok|apply|save|confirm|select|assign|suspend|resume|release)$/i.test(String(b.text || '').trim()));
    if (go) { fire(go); return `submitted via "${String(go.text).trim()}" :: ${text}`; }
    // Nothing to submit with: close it so the NEXT action does not inherit this dialog.
    if (win) {
      const shut = win.query('button').find((b) => /^(cancel|close|no)$/i.test(String(b.text || '').trim()));
      if (shut) fire(shut); else win.close();
      return `dialog with no submit button, closed :: ${text}`;
    }
    return 'no dialog — the action may have acted directly';
  }).catch(() => 'error');
}

const selectRow = async (id) => {
  for (const fr of page.frames()) {
    const r = await fr.evaluate(({ field, want }) => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const grid = window.Ext.ComponentQuery.query('grid').filter(vis).find((g) => g.getStore().getCount() > 0);
      if (!grid) return null;
      const st = grid.getStore();
      let idx = want == null ? 0 : st.findBy((rec) => String(rec.get(field)) === String(want));
      if (idx < 0) return { missing: true };
      grid.getSelectionModel().select(idx);
      const rec = st.getAt(idx);
      return { rows: st.getCount(), id: rec.get(field), snapshot: Object.fromEntries(Object.entries(rec.data).filter(([, v]) => v != null && v !== '' && typeof v !== 'object').slice(0, 10)) };
    }, { field: idField, want: id }).catch(() => null);
    if (r && !r.missing) return { frame: fr, ...r };
  }
  return null;
};

try {
  await page.goto(PORTAL + route, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(17000);

  const first = await selectRow(null);
  if (!first) { console.error('no populated grid on this screen'); process.exit(1); }
  const id = first.id;
  console.log(`grid rows ${first.rows} · target ${idField}=${id}`);
  console.log('row:', JSON.stringify(first.snapshot));

  const before = await stateOf(id);
  console.log('BEFORE:', JSON.stringify(before));
  if (dry) { console.log('\n--dry: nothing fired.'); process.exit(0); }

  /* --- A --- */
  bucket = [];
  if (!await fireAction(first.frame, actionA)) { console.error(`could not fire ${actionA}`); process.exit(1); }
  const dialogA = await confirmDialog(first.frame);
  await page.waitForTimeout(7000);
  const reqA = bucket.slice();
  console.log(`\n${actionA}: ${dialogA}`);
  for (const r of reqA) console.log(`  ${r.method} ${r.url} -> ${r.status}`);
  const mid = await stateOf(id);
  console.log('AFTER A:', JSON.stringify(mid));

  /* --- B, the inverse --- */
  await page.goto(PORTAL + route, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(16000);
  const again = await selectRow(id);
  bucket = [];
  let dialogB = 'row not found for the inverse action';
  const reqB = [];
  if (again) {
    if (await fireAction(again.frame, actionB)) {
      dialogB = await confirmDialog(again.frame);
      await page.waitForTimeout(7000);
      reqB.push(...bucket);
    } else dialogB = `could not fire ${actionB}`;
  }
  console.log(`\n${actionB}: ${dialogB}`);
  for (const r of reqB) console.log(`  ${r.method} ${r.url} -> ${r.status}`);
  const after = await stateOf(id);
  console.log('AFTER B:', JSON.stringify(after));

  for (const [phase, reqs] of [[actionA, reqA], [actionB, reqB]]) {
    for (const r of reqs) {
      const res = (r.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1] || resource;
      fs.appendFileSync(path.join(EX, `${res}.jsonl`), JSON.stringify({
        ts: new Date().toISOString(), tool: 'tools/cdp/capture-action-pair.mjs',
        case: phase.toLowerCase().replace(/\s+/g, '-'),
        request: { method: r.method, url: r.url.replace('/data/WM', '').split('?')[0], query: Object.fromEntries(new URLSearchParams(r.url.split('?')[1] || '')), headers: r.request_headers, body: r.request_body },
        response: { status: r.status, body: r.response_body },
        notes: `"${phase}" driven through the UI on ${resource} ${idField}=${id}. Captured as one half of a reversible pair with "${phase === actionA ? actionB : actionA}".`,
      }) + '\n');
    }
  }

  const reversed = watch ? before.watched === after.watched : null;
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify({
    generated_by: 'tools/cdp/capture-action-pair.mjs',
    screen_route: route, resource, id_field: idField, id, watched_field: watch,
    action_a: actionA, action_b: actionB,
    before, after_a: mid, after_b: after, reversed,
    dialog_a: dialogA, dialog_b: dialogB,
    requests_a: reqA, requests_b: reqB,
  }, null, 2) + '\n');
  console.log(`\nwatched ${watch}: ${JSON.stringify(before.watched)} -> ${JSON.stringify(mid.watched)} -> ${JSON.stringify(after.watched)} · reversed: ${reversed}`);
  if (reqA.length && !reqB.length) console.error(`\n!! ${actionA} was applied and ${actionB} produced NO request. The record is still in the changed state.`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
