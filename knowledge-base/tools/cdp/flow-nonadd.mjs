/*
 * flow-nonadd.mjs — trace the UI flows that have never been captured: Copy, row-edit, Delete.
 *
 * Every recipe in this repo documents the Add button and then says "Copy — not captured" and
 * "Delete — not captured via UI click; direct-API equivalent tested". Those are the two most
 * commonly used buttons after Add, and an executor driving the UI has no idea what they fire.
 * The direct-API equivalent is not proof: the UI Delete could fire a batch call, a different
 * path, or several calls in an order that matters.
 *
 * SAFETY: the flow creates its own throwaway record first and operates only on that row. It
 * never selects a pre-existing record, so Copy and Delete cannot touch real data.
 *
 *   node tools/cdp/flow-nonadd.mjs clientGroups
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton, setFields, findButtonId } from './ext.mjs';

const OUT = 'knowlegde_graph/blue-yonder-sce/http/flows';

const TARGETS = {
  clientGroups: {
    route: '#wm.config/wm.config.partners.clients////',
    coll: '/wm/clientGroups',
    // Groups is a tab on the Clients screen, so the tab must be selected before the grid appears.
    tab: 'Groups',
    fields: (code) => ({ clientGroup: code, clientGroupDescription: 'ZV nonadd probe' }),
    idValue: (code) => code,
    editField: 'clientGroupDescription',
  },
  customerTypes: {
    route: '#wm.config/wm.config.partners.customers.types////',
    coll: '/wm/customerTypes',
    fields: (code) => ({ customerType: code.slice(0, 4), longDescription: 'ZV nonadd probe' }),
    // csttyp truncates at 4 chars, so the row's actual key is NOT the full generated code.
    // Searching the grid store for the untruncated value finds nothing and silently skips
    // the edit/copy/delete phases - which is what happened on the first run.
    idValue: (code) => code.slice(0, 4),
    editField: 'longDescription',
  },
};

const key = process.argv[2] || 'customerTypes';
const t = TARGETS[key];
if (!t) { console.error('unknown target', key); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers'))
  || browser.contexts()[0].pages()[0];

const calls = [];
let seq = 0;
const pending = new Map();
page.on('request', (req) => {
  if (!/\/data\/WM\/wm\//.test(req.url()) || /webPerformanceEntries/.test(req.url())) return;
  pending.set(req, { seq: seq++, phase: PHASE,
    method: req.method(), url: req.url().split('?')[0].split('/wm/')[1], body: req.postData() || null });
});
page.on('response', async (res) => {
  const rec = pending.get(res.request());
  if (!rec) return;
  pending.delete(res.request());
  let body = null;
  try { body = (await res.text()).slice(0, 4000); } catch {}
  rec.status = res.status();
  rec.response = body;
  calls.push(rec);
});

let PHASE = 'setup';
const since = (p) => calls.filter((c) => c.phase === p)
  .sort((a, b) => a.seq - b.seq)
  .map((c) => `${c.method} ${c.url} -> ${c.status}`);

const out = { target: key, phases: {} };
const code = 'ZVN' + String(Date.now() % 10000);
const rowKey = (t.idValue || ((c) => c))(code);

try {
  const frame = await goto(page, t.route);
  await resetToGrid(page, frame);
  await page.waitForTimeout(1000);
  if (t.tab) {
    await frame.getByText(t.tab, { exact: true }).first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(2500);
  }

  // --- create a throwaway row so Copy/Delete never touch real data
  PHASE = 'create';
  await clickButton(frame, page, { itemId: 'addButton' });
  await page.waitForTimeout(3200);
  const setRes = await setFields(page, t.fields(code));
  out.createFields = setRes.applied;
  if (setRes.invalid?.length) throw new Error('create form invalid: ' + JSON.stringify(setRes.invalid));
  await clickButton(frame, page, { itemId: 'saveButton' });
  await page.waitForTimeout(4500);
  out.phases.create = since('create');

  // --- row click -> edit form -> change a field -> Save   (the PUT an executor would drive)
  PHASE = 'edit';
  await page.waitForTimeout(1500);
  /*
   * Open the row by clicking its actual grid row node. Matching on visible text fails here: the
   * grid virtualises rows, the code appears inside a link cell rather than as a standalone text
   * node, and several cached grids hold rows with the same text.
   */
  const rowNode = await page.evaluate((c) => {
    const w = document.querySelector('iframe').contentWindow;
    const grids = w.Ext.ComponentQuery.query('grid').filter((g) => {
      const d = g.getEl && g.getEl() && g.getEl().dom; const r = d && d.getBoundingClientRect();
      return r && r.width > 0 && r.height > 0;
    });
    for (const g of grids.reverse()) {
      const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(c));
      if (idx < 0) continue;
      const node = g.getView().getNode(idx);
      if (node && node.id) return node.id;
      const cell = node && node.querySelector('a, .x-grid-cell-inner');
      if (cell) { cell.click(); return 'clicked-directly'; }
    }
    return null;
  }, rowKey);
  out.rowNode = rowNode;
  /*
   * Clicking the row itself only selects it. A record is opened by the anchor in its first cell,
   * so target that; fall back to the row node if the grid renders no link.
   */
  /*
   * The grid renders no anchors; records open via the grid's own itemclick/cellclick listeners.
   * The FIRST cell is the row-checker, so clicking it only toggles selection - which is why
   * clicking the row produced no navigation. Click the second cell, which carries real data.
   */
  if (rowNode && rowNode !== 'clicked-directly') {
    await frame.locator(`#${rowNode} td:nth-child(2)`).click({ timeout: 10000 }).catch(async () => {
      await frame.locator('#' + rowNode).click({ timeout: 5000 }).catch(() => {});
    });
  }
  await page.waitForTimeout(3500);
  const editRes = await setFields(page, { [t.editField]: 'ZV edited' });
  out.editFields = editRes.applied;
  await clickButton(frame, page, { itemId: 'saveButton' }).catch(() => {});
  await page.waitForTimeout(4500);
  out.phases.edit = since('edit');

  // --- Copy: select the row's checkbox, then click Copy
  PHASE = 'copy';
  await resetToGrid(page, frame);
  await page.waitForTimeout(1500);
  const rowSel = await page.evaluate((c) => {
    const w = document.querySelector('iframe').contentWindow;
    const grids = w.Ext.ComponentQuery.query('grid').filter((g) => {
      const d = g.getEl && g.getEl() && g.getEl().dom; const r = d && d.getBoundingClientRect();
      return r && r.width > 0 && r.height > 0;
    });
    for (const g of grids.reverse()) {
      const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(c));
      if (idx >= 0) { g.getSelectionModel().select(idx); return { grid: g.id, idx }; }
    }
    return null;
  }, rowKey);
  out.rowSelected = rowSel;
  await page.waitForTimeout(1200);
  const copyBtn = await findButtonId(page, { itemId: 'copyButton' });
  out.copyButtonAvailable = !!copyBtn;
  if (copyBtn) {
    await frame.locator('#' + copyBtn.id).click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(4000);
    out.phases.copy = since('copy');
    out.copyOpensForm = !!(await findButtonId(page, { itemId: 'saveButton' }));
    await resetToGrid(page, frame);
  } else {
    out.phases.copy = ['copy button not enabled for this selection'];
  }

  // --- Delete via the real UI button (recipes only ever tested the API equivalent)
  PHASE = 'delete';
  await page.waitForTimeout(1500);
  await page.evaluate((c) => {
    const w = document.querySelector('iframe').contentWindow;
    const grids = w.Ext.ComponentQuery.query('grid').filter((g) => {
      const d = g.getEl && g.getEl() && g.getEl().dom; const r = d && d.getBoundingClientRect();
      return r && r.width > 0 && r.height > 0;
    });
    for (const g of grids.reverse()) {
      const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(c));
      if (idx >= 0) { g.getSelectionModel().select(idx); return true; }
    }
    return false;
  }, rowKey);
  await page.waitForTimeout(1200);
  const delBtn = await findButtonId(page, { itemId: 'deleteButton' });
  out.deleteButtonAvailable = !!delBtn;
  if (delBtn) {
    await frame.locator('#' + delBtn.id).click({ timeout: 6000 }).catch(() => {});
    await page.waitForTimeout(2000);
    // A confirm dialog is expected; answer Yes.
    const yes = await findButtonId(page, { itemId: 'yes' });
    out.deleteConfirmDialog = !!yes;
    if (yes) { await frame.locator('#' + yes.id).click({ timeout: 5000 }).catch(() => {}); }
    await page.waitForTimeout(4500);
    out.phases.delete = since('delete');
  }
} catch (e) {
  out.error = String(e).split('\n')[0].slice(0, 220);
}

out.code = code;
out.rowKey = rowKey;
out.allCalls = calls.sort((a, b) => a.seq - b.seq).map((c) => ({ phase: c.phase, method: c.method, url: c.url, status: c.status, body: c.body }));
fs.mkdirSync(OUT, { recursive: true });
fs.writeFileSync(`${OUT}/nonadd-${key}.json`, JSON.stringify(out, null, 2) + '\n');
console.log(JSON.stringify({
  target: key, code, rowKey, phases: out.phases,
  copyButtonAvailable: out.copyButtonAvailable, copyOpensForm: out.copyOpensForm,
  deleteButtonAvailable: out.deleteButtonAvailable, deleteConfirmDialog: out.deleteConfirmDialog,
  error: out.error,
}, null, 1));
await browser.close();
