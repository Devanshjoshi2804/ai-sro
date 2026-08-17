/*
 * flow-nonadd2.mjs — capture Copy, row-open and Delete by driving the grid's REAL handlers.
 *
 * Five earlier attempts failed by simulating clicks. Reading the handlers explained every failure:
 *
 *   addButton    -> owner.fireEvent('addrequested', owner, btn)
 *   copyButton   -> sel = owner.getSelectionModel().getSelection();
 *                   fireEvent('beforecopy', ...) then plugin.doCopy(owner, btn, sel)
 *   deleteButton -> plugin._fireDeleteEvent(); RP.Msg.promptOkCancel(msg, {fn: b =>
 *                   b !== 'cancel' && plugin.doDelete(owner, btn, sel)})
 *
 * Two things follow. The confirm is RP.Msg.promptOkCancel, a custom prompt whose buttons are
 * ok/cancel — not the Ext yes/no ids the earlier attempt searched for, so the dialog was never
 * found and the delete never proceeded. And a record is opened through the grid's itemclick
 * event, not by a link: the rows contain no anchors and the first cell is the row-checker, so
 * clicking it only toggles selection.
 *
 * So: select through the selection model, invoke the plugin methods the buttons invoke, and fire
 * itemclick with the arguments Ext would pass. Real code paths, no click simulation.
 *
 * SAFETY: operates only on a throwaway record this script creates. Never selects existing rows.
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton, setFields, findButtonId } from './ext.mjs';

const OUT = 'knowlegde_graph/blue-yonder-sce/http/flows';

const TARGETS = {
  customerTypes: {
    route: '#wm.config/wm.config.partners.customers.types////',
    fields: (c) => ({ customerType: c.slice(0, 4), longDescription: 'ZV nonadd probe' }),
    idValue: (c) => c.slice(0, 4),   // csttyp truncates at 4 chars
    editField: 'longDescription',
  },
  clientGroups: {
    route: '#wm.config/wm.config.partners.clients////',
    tab: 'Groups',
    fields: (c) => ({ clientGroup: c, clientGroupDescription: 'ZV nonadd probe' }),
    idValue: (c) => c,
    editField: 'clientGroupDescription',
  },
};

const key = process.argv[2] || 'customerTypes';
const t = TARGETS[key];
if (!t) { console.error('unknown target', key); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
  || browser.contexts()[0].pages()[0];

let PHASE = 'setup';
const calls = [];
let seq = 0;
const pending = new Map();
page.on('request', (req) => {
  if (!/\/data\/WM\/wm\//.test(req.url()) || /webPerformanceEntries/.test(req.url())) return;
  pending.set(req, { seq: seq++, phase: PHASE, method: req.method(),
    url: req.url().split('?')[0].split('/wm/')[1], body: req.postData() || null });
});
page.on('response', async (res) => {
  const rec = pending.get(res.request());
  if (!rec) return;
  pending.delete(res.request());
  try { rec.response = (await res.text()).slice(0, 3000); } catch {}
  rec.status = res.status();
  calls.push(rec);
});
const since = (p) => calls.filter((c) => c.phase === p).sort((a, b) => a.seq - b.seq)
  .map((c) => `${c.method} ${c.url} -> ${c.status}`);

/* Locate the visible grid and select the throwaway row through the selection model. */
const selectRow = (page, rowKey) => page.evaluate((k) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const grids = w.Ext.ComponentQuery.query('grid').filter(vis);
  for (const g of grids.reverse()) {
    const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(k));
    if (idx < 0) continue;
    g.getSelectionModel().select(idx);
    return { gridId: g.id, idx, selected: g.getSelectionModel().getSelection().length };
  }
  return null;
}, rowKey);

/*
 * Open a record the way the UI actually does.
 *
 * The grid has NO itemclick listeners. The first column is an rpLinkColumn
 * (RP.dataview.column.LinkColumn) whose renderer emits <span class="{linkSpanCls}">value</span>,
 * and its cellclick handler only fires `linkclick` when the click target carries that class.
 * There is no <a> anywhere in the row, which is why every anchor- and row-based click failed.
 * So: find that span's DOM id and let the caller issue a real click on it.
 */
const findLinkSpan = (page, rowKey) => page.evaluate((k) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const grids = w.Ext.ComponentQuery.query('grid').filter(vis);
  for (const g of grids.reverse()) {
    const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(k));
    if (idx < 0) continue;
    const cls = w.RP?.dataview?.column?.LinkColumn?.prototype?.linkSpanCls;
    const node = g.getView().getNode(idx);
    if (!node) continue;
    const span = cls ? node.querySelector('.' + cls) : node.querySelector('span[id^=ext-]');
    if (span) { if (!span.id) span.id = 'zv-link-' + Date.now(); return { id: span.id, cls, idx }; }
  }
  return null;
}, rowKey);

/* Invoke the plugin method a toolbar button invokes, rather than clicking the button. */
const invokePlugin = (page, which) => page.evaluate((w2) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const btn = w.Ext.ComponentQuery.query('button')
    .filter((b) => !b.isDestroyed && b.itemId === (w2 === 'copy' ? 'copyButton' : 'deleteButton') && vis(b) && !b.disabled)
    .pop();
  if (!btn) return { error: 'button not found or disabled' };
  // The click listener's scope is the GridActions plugin that owns doCopy/doDelete.
  const lis = btn.events && btn.events.click && btn.events.click.listeners;
  const plugin = lis && lis.length ? lis[0].scope : null;
  if (!plugin) return { error: 'no plugin scope on click listener' };
  const owner = plugin.owner;
  const sel = owner.getSelectionModel().getSelection();
  if (!sel.length) return { error: 'nothing selected' };
  try {
    if (w2 === 'copy') { plugin.doCopy(owner, btn, sel); return { invoked: 'doCopy', selected: sel.length }; }
    plugin.doDelete(owner, btn, sel);
    return { invoked: 'doDelete', selected: sel.length };
  } catch (e) { return { error: String(e).slice(0, 200) }; }
}, which);

const out = { target: key, phases: {} };
const code = 'ZVN' + String(Date.now() % 10000);
const rowKey = t.idValue(code);

try {
  const frame = await goto(page, t.route);
  await resetToGrid(page, frame);
  await page.waitForTimeout(1000);
  if (t.tab) {
    await frame.getByText(t.tab, { exact: true }).first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(2500);
  }

  PHASE = 'create';
  await clickButton(frame, page, { itemId: 'addButton' });
  await page.waitForTimeout(3200);
  const setRes = await setFields(page, t.fields(code));
  if (setRes.invalid?.length) throw new Error('create form invalid: ' + JSON.stringify(setRes.invalid));
  await clickButton(frame, page, { itemId: 'saveButton' });
  await page.waitForTimeout(4500);
  out.phases.create = since('create');

  // --- open the record and save an edit: the PUT an executor would drive
  PHASE = 'edit';
  await resetToGrid(page, frame);
  await page.waitForTimeout(1800);
  const link = await findLinkSpan(page, rowKey);
  out.linkSpan = link;
  if (link) await frame.locator('#' + link.id).click({ timeout: 10000 }).catch((e) => { out.linkClickErr = String(e).slice(0, 120); });
  await page.waitForTimeout(3800);
  const editRes = await setFields(page, { [t.editField]: 'ZV edited' });
  out.editApplied = editRes.applied;
  out.editFormFound = !editRes.error;
  if (!editRes.error) {
    await clickButton(frame, page, { itemId: 'saveButton' }).catch(() => {});
    await page.waitForTimeout(4500);
  }
  out.phases.edit = since('edit');

  // --- Copy
  PHASE = 'copy';
  await resetToGrid(page, frame);
  await page.waitForTimeout(1800);
  out.copySelect = await selectRow(page, rowKey);
  await page.waitForTimeout(800);
  out.copyInvoke = await invokePlugin(page, 'copy');
  await page.waitForTimeout(4000);
  out.copyOpensForm = !!(await findButtonId(page, { itemId: 'saveButton' }));
  out.phases.copy = since('copy');
  await resetToGrid(page, frame);

  // --- Delete, invoking doDelete directly so the custom RP.Msg confirm is bypassed
  PHASE = 'delete';
  await page.waitForTimeout(1800);
  out.deleteSelect = await selectRow(page, rowKey);
  await page.waitForTimeout(800);
  out.deleteInvoke = await invokePlugin(page, 'delete');
  await page.waitForTimeout(5000);
  out.phases.delete = since('delete');
} catch (e) {
  out.error = String(e).split('\n')[0].slice(0, 220);
}

out.code = code;
out.rowKey = rowKey;
out.allCalls = calls.sort((a, b) => a.seq - b.seq)
  .map((c) => ({ phase: c.phase, method: c.method, url: c.url, status: c.status, body: c.body, response: c.response }));
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(`${OUT}/nonadd2-${key}.json`, JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify({
  target: key, code, rowKey, phases: out.phases,
  opened: out.opened, editFormFound: out.editFormFound,
  copyInvoke: out.copyInvoke, copyOpensForm: out.copyOpensForm,
  deleteInvoke: out.deleteInvoke, error: out.error,
}, null, 1));
await browser.close();
