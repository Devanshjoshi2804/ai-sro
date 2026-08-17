/*
 * read-action-form.mjs — open any operational action's form, read it, cancel it.
 *
 * There are 95 named operational verbs and not one of them had a payload model. The Approve form
 * showed why that matters: three fields, one of them a side effect (`generateCycleCount`) and one a
 * required combo containing two options whose own labels say DO NOT USE. Reading a form is the
 * cheapest way to learn what an action needs, and it is free of consequence.
 *
 * The tool selects a grid row (actions are usually disabled without one), fires the menu item, reads
 * whatever dialog appears, and cancels. It listens for non-GET traffic throughout and reports it, so
 * a form that submits something on open cannot pass unnoticed.
 *
 *   node tools/cdp/read-action-form.mjs "Inventory" "Adjust Inventory"
 *   node tools/cdp/read-action-form.mjs "Inventory" --all
 */
import fs from 'node:fs';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const OUT = `${KG}/index/operational-forms.json`;
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----';

const [label, ...rest] = process.argv.slice(2);
const all = rest.includes('--all');
const routeArgIdx = rest.indexOf('--route');
const wanted = rest.filter((r, i) => !r.startsWith('--') && i !== routeArgIdx + 1);
if (!label || (!all && !wanted.length)) { console.error('usage: read-action-form.mjs "<screen>" "<action>" | "<screen>" --all'); process.exit(1); }

const menus = JSON.parse(fs.readFileSync(`${KG}/index/actions-menus.json`, 'utf8')).screens[label];
if (!menus) { console.error(`no captured Actions menu for ${label}`); process.exit(1); }
/*
 * Six screens are called "Inventory" — one per area, plus a Special Pack variant — and the captured
 * menu belongs to whichever was crawled. `--route` picks the one you mean; without it the actions
 * can come back "disabled" simply because the wrong copy of the screen was opened.
 */
const routeIdx = process.argv.indexOf('--route');
const route = routeIdx > -1 ? process.argv[routeIdx + 1] : menus.hash;
const items = menus.menus.flatMap((m) => m.items || [])
  .map((i) => ({ ...i, clean: String(i.text || '').replace(/&#160;/g, '').replace(/\s+/g, ' ').trim() }))
  .filter((i) => i.clean && !i.disabled && (all || wanted.includes(i.clean)));
if (!items.length) { console.error('no matching enabled action'); process.exit(1); }
console.log(`${label}: ${items.length} action(s) to read`);

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
let writes = [];
page.on('requestfinished', (req) => {
  if (req.method() !== 'GET' && /\/data\/WM\//.test(req.url())) {
    writes.push(`${req.method()} ${req.url().replace(/^https?:\/\/[^/]+/, '').split('?')[0]}`);
  }
});

const clean = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { forms: {} };

try {
  for (const item of items) {
    writes = [];
    await page.goto(PORTAL + route, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
    await page.waitForTimeout(15000);

    /* Select a row — most actions stay disabled without one — then open the Actions menu. */
    let frame = null;
    for (const fr of page.frames()) {
      const ok = await fr.evaluate(() => {
        if (!window.Ext) return false;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const grid = window.Ext.ComponentQuery.query('grid').filter(vis).find((g) => g.getStore().getCount() > 0);
        if (grid) grid.getSelectionModel().select(0);
        const btn = window.Ext.ComponentQuery.query('button').filter(vis)
          .find((b) => /actionsBtn$/i.test(b.itemId || '') || /^Actions$/i.test(String(b.text || '').trim()));
        if (!btn) return false;
        /*
         * A menu button opens on showMenu(), not on its handler — firing the handler left
         * `open_menus: 0` and every action looked disabled. Fall back to a real DOM click.
         */
        if (btn.menu && btn.showMenu) { btn.showMenu(); return true; }
        return btn.getEl() ? { domId: btn.getEl().dom.id } : false;
      }).catch(() => false);
      if (ok === true) { frame = fr; break; }
      if (ok && ok.domId) { await fr.locator('#' + ok.domId).click({ timeout: 5000 }).catch(() => {}); frame = fr; break; }
    }
    if (!frame) { console.log(`  ${item.clean}: no Actions button`); continue; }
    await page.waitForTimeout(2000);

    const fired = await frame.evaluate((text) => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const strip = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
      const it = window.Ext.ComponentQuery.query('menu').filter(vis).flatMap((m) => m.query('menuitem'))
        .find((i) => !i.disabled && strip(i.text) === text);
      if (!it) return false;
      it.fireHandler ? it.fireHandler() : it.handler && it.handler.call(it.scope || it, it);
      return true;
    }, item.clean).catch(() => false);
    if (!fired) {
      // Say WHY. "not found or disabled" hid whether the menu even opened.
      const seen = await frame.evaluate(() => {
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const strip = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
        const menus = window.Ext.ComponentQuery.query('menu').filter(vis);
        return { open_menus: menus.length, items: menus.flatMap((m) => m.query('menuitem')).map((i) => strip(i.text) + (i.disabled ? ' (disabled)' : '')) };
      }).catch(() => null);
      console.log(`  ${item.clean}: not fired — ${JSON.stringify(seen)?.slice(0, 400)}`);
      continue;
    }
    await page.waitForTimeout(5000);

    const form = await frame.evaluate(() => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const strip = (s) => String(s || '').replace(/<[^>]*>/g, ' ').replace(/&#160;/g, ' ').replace(/\s+/g, ' ').trim();
      /*
       * Not every action opens a window. Several push a CARD into the deck instead — the same
       * pattern as the composite Add screens — so a missing window is not evidence that the action
       * fired immediately. Look for a card with fields before concluding anything.
       */
      const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
      if (!win) {
        const fields = window.Ext.ComponentQuery.query('field').filter(vis)
          .filter((f) => f.name && !/^rpuxFilter|search/i.test(f.name));
        const back = window.Ext.ComponentQuery.query('button').filter(vis).some((b) => b.itemId === 'wm-cardDeck-back-button');
        if (fields.length) {
          return {
            rendered_as: back ? 'card in the deck' : 'inline panel',
            fields: fields.map((f) => ({
              field: f.name, label: strip(f.fieldLabel), type: f.xtype, required: f.allowBlank === false,
              value: f.getValue ? f.getValue() : undefined,
              options: f.getStore && f.getStore() && f.getStore().getCount && f.getStore().getCount() > 0 && f.getStore().getCount() <= 30
                ? f.getStore().getRange().map((r) => ({ v: r.get(f.valueField || 'code'), t: r.get(f.displayField || 'description') })) : undefined,
            })),
            buttons: window.Ext.ComponentQuery.query('button').filter(vis).map((b) => ({ text: strip(b.text), itemId: b.itemId, disabled: !!b.disabled })).slice(0, 20),
          };
        }
        return { no_dialog_and_no_fields: true, note: 'nothing rendered that this tool can read; whether the action did anything is answered by writes_observed, not by this' };
      }
      return {
        title: strip(win.title),
        text: win.getEl && win.getEl() ? win.getEl().dom.innerText.replace(/\s+/g, ' ').trim().slice(0, 240) : '',
        fields: win.query('field').filter(vis).map((f) => ({
          field: f.name, label: strip(f.fieldLabel), type: f.xtype,
          required: f.allowBlank === false,
          value: f.getValue ? f.getValue() : undefined,
          maxLength: f.maxLength && f.maxLength < 1e6 ? f.maxLength : undefined,
          options: f.getStore && f.getStore() && f.getStore().getCount && f.getStore().getCount() > 0 && f.getStore().getCount() <= 30
            ? f.getStore().getRange().map((r) => ({ v: r.get(f.valueField || 'code'), t: r.get(f.displayField || 'description') })) : undefined,
        })),
        buttons: win.query('button').filter(vis).map((b) => ({ text: strip(b.text), itemId: b.itemId, disabled: !!b.disabled })),
      };
    }).catch(() => null);

    /* Always leave without committing. */
    const closed = await frame.evaluate(() => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const win = window.Ext.ComponentQuery.query('window,messagebox').filter(vis).pop();
      if (!win) return 'no window';
      const cancel = win.query('button').find((b) => /^(cancel|close|no)$/i.test(String(b.text || '').trim()));
      if (cancel) { cancel.fireHandler ? cancel.fireHandler() : cancel.handler && cancel.handler.call(cancel.scope || cancel, cancel); return 'cancelled'; }
      win.close();
      return 'closed';
    }).catch(() => 'error');
    await page.waitForTimeout(2500);

    const key = `${label} > ${item.clean}`;
    store.forms[key] = { ...form, closed_with: closed, writes_observed: writes.slice() };
    const n = form?.fields?.length ?? 0;
    const shape = form?.no_dialog_and_no_fields ? 'nothing readable rendered'
      : form?.rendered_as ? `${form.rendered_as}, ${n} field(s)`
      : `window "${form?.title}", ${n} field(s)`;
    console.log(`  ${item.clean.padEnd(30)} ${shape} · closed=${closed} · writes: ${writes.length ? writes.join(', ') : 'NONE'}`);

    store.generated_by = 'tools/cdp/read-action-form.mjs';
    store.readOnly = 'each form is opened, read and cancelled; writes_observed records any traffic that escaped that intent';
    fs.writeFileSync(OUT, JSON.stringify(store, null, 2) + '\n');
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
