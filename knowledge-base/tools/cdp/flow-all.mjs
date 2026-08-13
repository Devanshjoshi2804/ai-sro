/*
 * flow-all.mjs — run the full UI lifecycle (create -> open+edit -> copy -> delete) across every
 * grid screen, capturing the real request/response for each step.
 *
 * The interaction mechanics were worked out once on customerTypes and are framework-level, so
 * they hold for every grid in this app:
 *
 *   - Rows contain NO anchors. The first column is an rpLinkColumn whose renderer emits
 *     <span class="rpux-link-grid-column-link">. Its cellclick fires `linkclick` only when the
 *     event target carries that class, so a record is opened by clicking THAT SPAN.
 *   - The first cell is the row-checker; clicking it only toggles selection.
 *   - The grid has no itemclick listeners, so firing itemclick achieves nothing.
 *   - Toolbar buttons have no handler. Their click listeners are scoped to a
 *     WM.plugins.grid.GridActions plugin: copyButton -> plugin.doCopy(owner, btn, sel),
 *     deleteButton -> RP.Msg.promptOkCancel(...) -> plugin.doDelete(owner, btn, sel).
 *   - doDelete is store.remove() + store.sync(): the DELETE comes from the STORE.
 *   - doCopy is record.copy() + fireEvent('copied'): client-side only, it cannot emit a request.
 *
 * SAFETY: every screen creates its own throwaway record and acts only on that row. Existing
 * records are never selected, so Copy and Delete cannot touch real data. The lifecycle ends in
 * a delete, so a successful run leaves nothing behind; a failed run is caught by the sweep.
 *
 *   node tools/cdp/flow-all.mjs            # every screen
 *   node tools/cdp/flow-all.mjs carriers   # one screen
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { goto, resetToGrid, clickButton, setFields, findButtonId, dismissBlocking } from './ext.mjs';

const OUT = 'knowlegde_graph/blue-yonder-sce/http/flows';

/*
 * Field names are the JSON model names from index/form-models.json, not labels.
 * `idValue` accounts for server-side truncation: several codes are cut short, and searching the
 * grid store for the untruncated value silently finds nothing and skips every later phase.
 */
export const SCREENS = {
  customerTypes: {
    route: '#wm.config/wm.config.partners.customers.types////',
    fields: (c) => ({ customerType: c.slice(0, 4), longDescription: 'ZV flow' }),
    idValue: (c) => c.slice(0, 4), editField: 'longDescription',
  },
  transportModes: {
    route: '#wm.config/wm.config.partners.carriers.transportmodes////',
    fields: (c) => ({ transportMode: c.slice(0, 3), transportModeDescription: 'ZV flow' }),
    idValue: (c) => c.slice(0, 3), editField: 'transportModeDescription',
  },
  carriers: {
    route: '#wm.config/wm.config.partners.carriers.main////',
    fields: (c) => ({ carrierCode: c, carrierName: 'ZV flow' }),
    // 1581 rows: a new code lands outside the loaded page, so sort it to the top first.
    sortBy: 'carrierCode',
    idValue: (c) => c, editField: 'carrierName',
  },
  businessUnits: {
    route: '#wm.config/wm.config.warehouse.businessunits////',
    fields: (c) => ({ businessUnit: c, businessUnitDescription: 'ZV flow' }),
    idValue: (c) => c, editField: 'businessUnitDescription',
  },
  levelTypes: {
    route: '#wm.config/wm.config.warehouse.locations.leveltypes////',
    fields: (c) => ({ levelTypeName: c, levelTypeDescription: 'ZV flow', totalLevelUnits: '1' }),
    idValue: (c) => c, editField: 'levelTypeDescription',
  },
  equipmentTypes: {
    route: '#wm.config/wm.config.equipment.equipment.warehouseequipmenttype////',
    // voiceCode is numeric, 2 chars, and must be globally unique across equipment types.
    fields: (c, i) => ({ vehicleTypeId: c, longDescription: 'ZV flow', voiceCode: String(11 + (i % 80)), vehicleLimit: '1' }),
    idValue: (c) => c, editField: 'longDescription',
  },
  printers: {
    route: '#wm.config/wm.config.equipment.hardware.printers////',
    // "Printer Name" is printerAddress and "Printer Description" is printerName - inverted labels.
    fields: (c) => ({ printerAddress: c.slice(0, 10), printerName: 'ZVflow' }),
    pickFirst: ['printerType'], relaxRadio: ['Printer Status'],
    idValue: (c) => c.slice(0, 10), editField: 'printerName',
  },
  workstations: {
    route: '#wm.config/wm.config.equipment.hardware.workstations////',
    fields: (c) => ({ deviceCode: c, deviceName: 'ZV flow' }),
    idValue: (c) => c, editField: 'deviceName',
  },
  voiceDevices: {
    route: '#wm.config/wm.config.equipment.hardware.voicedevices////',
    fields: (c) => ({ deviceCode: c, deviceName: 'ZV flow' }),
    pickFirst: ['localeId'],
    // This screen's save is genuinely slow - it sits on "Saving..." far longer than any other.
    // The default wait cut it off mid-flight, which is what produced the earlier 404 reading.
    saveWaitMs: 30000,
    idValue: (c) => c, editField: 'deviceName',
  },
  clientGroups: {
    route: '#wm.config/wm.config.partners.clients////',
    tab: 'Groups',
    fields: (c) => ({ clientGroup: c, clientGroupDescription: 'ZV flow' }),
    idValue: (c) => c, editField: 'clientGroupDescription',
  },
};

/*
 * There are TWO link mechanisms in this app, and only one was known before:
 *
 *   rpLinkColumn   -> <span class="rpux-link-grid-column-link">, grid cellclick handled by
 *                     RP.dataview.column.LinkColumn  (customerTypes, carriers, clientGroups, ...)
 *   templatecolumn -> element with class "wm-grid-navigate-link-column", and NO cellclick
 *                     listener on the grid at all      (printers, workstations, voiceDevices)
 *
 * Searching only for the first class is why edit coverage failed on the hardware screens.
 */
const LINK_SELECTORS = ['.rpux-link-grid-column-link', '.wm-grid-navigate-link-column'];

const findLinkSpan = (page, rowKey) => page.evaluate(({ k, sels }) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  for (const g of w.Ext.ComponentQuery.query('grid').filter(vis).reverse()) {
    const store = g.getStore();
    const idx = store.findBy((rec) => JSON.stringify(rec.data).includes(k));
    if (idx < 0) continue;
    const node = g.getView().getNode(idx);
    if (!node) continue;
    for (const sel of sels) {
      const el = node.querySelector(sel);
      if (el) { if (!el.id) el.id = 'zv-link-' + Date.now(); return { id: el.id, idx, via: sel }; }
    }
  }
  return null;
}, { k: rowKey, sels: LINK_SELECTORS });

/*
 * Bring a freshly created row into the loaded page.
 *
 * Grid stores hold one page. On a large collection (carriers has 1581 rows) a new record lands
 * outside it, so the row is never found and the edit phase is skipped - the same pagination trap
 * that made the cleanup sweep report a clean environment while records were live. Sorting
 * descending by the key column pulls a ZV-prefixed code to the top.
 */
/*
 * Bring a freshly created row into the loaded page on a SERVER-PAGED grid.
 *
 * The carriers grid shows "Page 1 of 64, Displaying 1-25 of 1581": the store holds one 25-row
 * page and the server does the paging. Neither sorting nor filtering the loaded page can surface
 * a record that is not in it - both were tried and both failed. Existing codes are numeric
 * ("001", "005"), so a ZV-prefixed code sorts after all of them and lands on the LAST page.
 * Jump there first, then walk backwards as a fallback.
 */
const bringRowIntoView = (page, dataIndex, value) => page.evaluate(async ({ di, val }) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const g = w.Ext.ComponentQuery.query('grid').filter(vis).pop();
  if (!g) return { done: false, reason: 'no grid' };
  const st = g.getStore();
  const total = st.getTotalCount ? st.getTotalCount() : st.getCount();
  const pageSize = st.pageSize || 25;
  const lastPage = Math.max(1, Math.ceil(total / pageSize));
  const load = (n) => new Promise((res) => { st.loadPage(n, { callback: () => res() }); setTimeout(res, 6000); });
  const found = () => st.findBy((r) => JSON.stringify(r.data).includes(val)) >= 0;
  const tried = [];
  for (const n of [lastPage, lastPage - 1, lastPage - 2]) {
    if (n < 1) continue;
    await load(n);
    tried.push(n);
    if (found()) return { done: true, method: 'loadPage', page: n, total, lastPage, tried };
  }
  return { done: false, method: 'loadPage', total, lastPage, tried };
}, { di: dataIndex, val: value });

const selectRow = (page, rowKey) => page.evaluate((k) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  for (const g of w.Ext.ComponentQuery.query('grid').filter(vis).reverse()) {
    const idx = g.getStore().findBy((rec) => JSON.stringify(rec.data).includes(k));
    if (idx < 0) continue;
    g.getSelectionModel().select(idx);
    return { idx, selected: g.getSelectionModel().getSelection().length };
  }
  return null;
}, rowKey);

/* Invoke the plugin method the toolbar button invokes, rather than clicking the button. */
const invokePlugin = (page, which) => page.evaluate((w2) => {
  const w = document.querySelector('iframe').contentWindow;
  const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
  const btn = w.Ext.ComponentQuery.query('button')
    .filter((b) => !b.isDestroyed && b.itemId === (w2 === 'copy' ? 'copyButton' : 'deleteButton') && vis(b) && !b.disabled).pop();
  if (!btn) return { error: 'button missing or disabled' };
  const plugin = btn.events?.click?.listeners?.[0]?.scope;
  if (!plugin) return { error: 'no plugin scope' };
  const owner = plugin.owner;
  const sel = owner.getSelectionModel().getSelection();
  if (!sel.length) return { error: 'nothing selected' };
  try {
    if (w2 === 'copy') { plugin.doCopy(owner, btn, sel); return { invoked: 'doCopy' }; }
    plugin.doDelete(owner, btn, sel);
    return { invoked: 'doDelete' };
  } catch (e) { return { error: String(e).slice(0, 160) }; }
}, which);

async function runScreen(page, frame, name, idx) {
  const s = SCREENS[name];
  const out = { screen: name, phases: {} };
  const code = 'ZV' + String(Date.now() % 100000).slice(-4) + (idx || '');
  const rowKey = s.idValue(code);
  out.code = code; out.rowKey = rowKey;

  const calls = [];
  let seq = 0; let PHASE = 'setup';
  const pending = new Map();
  const onReq = (req) => {
    if (!/\/data\/WM\/wm\//.test(req.url()) || /webPerformanceEntries/.test(req.url())) return;
    pending.set(req, { seq: seq++, phase: PHASE, method: req.method(), url: req.url().split('?')[0].split('/wm/')[1], body: req.postData() || null });
  };
  const onRes = async (res) => {
    const rec = pending.get(res.request());
    if (!rec) return;
    pending.delete(res.request());
    rec.status = res.status();
    try { rec.response = (await res.text()).slice(0, 2000); } catch {}
    calls.push(rec);
  };
  page.on('request', onReq); page.on('response', onRes);
  const since = (p) => calls.filter((c) => c.phase === p).sort((a, b) => a.seq - b.seq).map((c) => `${c.method} ${c.url} -> ${c.status}`);

  try {
    frame = await goto(page, s.route);
    await resetToGrid(page, frame);
    await page.waitForTimeout(1000);
    if (s.tab) {
      await frame.getByText(s.tab, { exact: true }).first().click({ timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(2500);
    }

    PHASE = 'create';
    await clickButton(frame, page, { itemId: 'addButton' });
    await page.waitForTimeout(3200);
    const setRes = await setFields(page, s.fields(code, idx), s.pickFirst, s.relax, s.relaxRadio);
    out.createApplied = setRes.applied;
    if (setRes.invalid?.length) { out.createInvalid = setRes.invalid; throw new Error('create form invalid'); }
    await clickButton(frame, page, { itemId: 'saveButton' });
    await page.waitForTimeout(s.saveWaitMs || 4500);
    // A blocking exception modal here means the save failed; record it rather than pressing on.
    const afterCreate = await dismissBlocking(page);
    if (afterCreate.cleared.length) out.createBlocked = afterCreate.cleared;
    out.phases.create = since('create');

    PHASE = 'edit';
    await resetToGrid(page, frame);
    await page.waitForTimeout(1800);
    let link = await findLinkSpan(page, rowKey);
    if (!link && s.sortBy) {
      out.broughtIntoView = await bringRowIntoView(page, s.sortBy, rowKey);
      await page.waitForTimeout(3500);
      link = await findLinkSpan(page, rowKey);
    }
    out.linkFound = !!link;
    out.linkVia = link && link.via;
    if (link) await frame.locator('#' + link.id).click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(3600);
    const editRes = await setFields(page, { [s.editField]: 'ZV edited' });
    out.editFormFound = !editRes.error;
    if (!editRes.error) {
      await clickButton(frame, page, { itemId: 'saveButton' }).catch(() => {});
      await page.waitForTimeout(4200);
    }
    out.phases.edit = since('edit');

    PHASE = 'copy';
    await resetToGrid(page, frame);
    await page.waitForTimeout(1600);
    out.copySelect = await selectRow(page, rowKey);
    await page.waitForTimeout(700);
    out.copyInvoke = await invokePlugin(page, 'copy');
    await page.waitForTimeout(3000);
    out.phases.copy = since('copy');
    await resetToGrid(page, frame);

    PHASE = 'delete';
    await page.waitForTimeout(1600);
    out.deleteSelect = await selectRow(page, rowKey);
    await page.waitForTimeout(700);
    out.deleteInvoke = await invokePlugin(page, 'delete');
    await page.waitForTimeout(4500);
    out.phases.delete = since('delete');
  } catch (e) {
    out.error = String(e).split('\n')[0].slice(0, 200);
  } finally {
    page.off('request', onReq); page.off('response', onRes);
  }
  out.allCalls = calls.sort((a, b) => a.seq - b.seq).map((c) => ({ phase: c.phase, method: c.method, url: c.url, status: c.status, body: c.body }));
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(`${OUT}/lifecycle-${name}.json`, JSON.stringify(out, null, 2) + '\n');
  return out;
}

/*
 * Detect the app's session-expiry state.
 *
 * A previous full run died at the 5th screen because the session timed out: every later screen
 * then failed with "Target page/context closed" and "Failed to fetch", which reads like a harness
 * bug rather than a logout. Checking explicitly turns 6 misleading failures into 1 clear stop,
 * and prevents a create landing without its matching delete.
 */
const sessionExpired = (page) => page.evaluate(() => {
  const t = document.body ? document.body.innerText : '';
  return /Session Expired|you were automatically logged out|Please login again/i.test(t);
}).catch(() => true);

const only = process.argv[2];
const names = only ? [only] : Object.keys(SCREENS);
const browser = await chromium.connectOverCDP('http://localhost:9222');
const page = browser.contexts()[0].pages().find((p) => p.url().includes('jdadelivers')) || browser.contexts()[0].pages()[0];
const summary = {};
for (let i = 0; i < names.length; i++) {
  const n = names[i];
  if (await sessionExpired(page)) {
    process.stderr.write(`\nSESSION EXPIRED before ${n} — stopping so no record is created without its delete.\n`);
    summary.__halted = `session expired before ${n}; remaining: ${names.slice(i).join(', ')}`;
    break;
  }
  process.stderr.write(`\n### ${n}\n`);
  // Never inherit a previous screen's modal.
  await dismissBlocking(page);
  const r = await runScreen(page, null, n, i);
  summary[n] = {
    create: r.phases.create || [], edit: r.phases.edit || [],
    copy: r.phases.copy || [], delete: r.phases.delete || [],
    linkFound: r.linkFound, editFormFound: r.editFormFound,
    error: r.error, createInvalid: r.createInvalid,
  };
  process.stderr.write('   ' + JSON.stringify(summary[n]).slice(0, 300) + '\n');
}
console.log(JSON.stringify(summary, null, 1));
await browser.close();
