/*
 * map-forms.mjs — Phase 0b: capture the Add-form model for every screen that can create.
 *
 * app-map.json records what each screen SHOWS. This records what each screen can CREATE: the
 * exact field model behind its Add button — JSON field name, visible label, required flag, type,
 * maxLength, and the options of small combos.
 *
 * That mapping is the thing that cannot be obtained any other way. A failed create returns a 422
 * naming the missing DB COLUMN, but the API rejects that name in the body and wants a camelCase
 * key that is not derivable from it (column `lngdsc` -> key `businessUnitDescription`). Reading
 * the form model gives label, key and constraints together, for free.
 *
 * STRICTLY READ-ONLY: opens Add, reads the model, then Cancels. It never fills a field, never
 * clicks Save, and never invokes a grid-action plugin.
 *
 *   node tools/cdp/map-forms.mjs                 every creatable screen
 *   node tools/cdp/map-forms.mjs configuration   one tier
 *   node tools/cdp/map-forms.mjs partners        one area
 */
import fs from 'node:fs';
import { chromium } from 'playwright';
import { dismissBlocking } from './ext.mjs';

/*
 * Frame-aware button lookup.
 *
 * ext.mjs resolves buttons through document.querySelector('iframe') - the FIRST iframe only.
 * The portal nests up to six, and on many screens the toolbar lives in a different one, so every
 * Add click timed out. Search each frame for a visible, enabled button and click it in the frame
 * that actually owns it.
 */
async function clickIn(page, itemId, timeout = 12000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (const fr of page.frames()) {
      const id = await fr.evaluate((iid) => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        const b = window.Ext.ComponentQuery.query('button')
          .filter((x) => !x.isDestroyed && x.itemId === iid && !x.disabled && vis(x)).pop();
        return b && b.getEl() ? b.getEl().dom.id : null;
      }, itemId).catch(() => null);
      if (id) {
        await fr.locator('#' + id).click({ timeout: 5000 }).catch(() => {});
        return { frame: fr, id };
      }
    }
    await page.waitForTimeout(600);
  }
  return null;
}

const KG = 'knowlegde_graph/blue-yonder-sce';
const MAP = `${KG}/index/app-map.json`;
const OUT = `${KG}/index/form-models-all.json`;

const screens = JSON.parse(fs.readFileSync(MAP, 'utf8')).screens;
const filter = process.argv[2];
const targets = screens.filter((s) => s.can_create && !s.error
  && (!filter || s.tier === filter || s.area === filter));

/*
 * Read the Add form's model.
 *
 * Two failures forced this to be deterministic rather than best-effort:
 *  - the same screen (Clients) returned 28 fields on one run and 14 on another, because the
 *    frame soup means "the last visible form" can be a sub-form or a leftover from another screen;
 *  - a fixed sleep after clicking Add is not a render signal, so some screens reported no form
 *    at all while the real one was still drawing.
 *
 * So: poll until a visible form actually appears, prefer the frame whose URL carries this
 * screen's route, and among candidates take the one with the most fields. Report which frame and
 * how many candidates there were, so an inconsistent capture is visible in the record instead of
 * silently overwriting a good one.
 */
async function readForm(page, routeHint, timeoutMs = 14000) {
  const deadline = Date.now() + timeoutMs;
  let best = null;
  while (Date.now() < deadline) {
    const candidates = [];
    for (const fr of page.frames()) {
      const r = await fr.evaluate(() => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
        const forms = window.Ext.ComponentQuery.query('form').filter(vis);
        if (!forms.length) return null;
        return {
          url: location.href,
          forms: forms.map((fm) => {
            const items = fm.getForm().getFields().items;
            return {
              field_count: items.length,
              fields: items.map((x) => ({
                field: x.name, label: x.fieldLabel, required: x.allowBlank === false, type: x.xtype,
                maxLength: x.maxLength && x.maxLength < 1e6 ? x.maxLength : undefined,
                options: x.getStore && x.getStore() && x.getStore().getCount && x.getStore().getCount() > 0 && x.getStore().getCount() <= 15
                  ? x.getStore().getRange().map((rr) => rr.get(x.valueField || 'code')).filter(Boolean).slice(0, 15)
                  : undefined,
              })),
            };
          }),
        };
      }).catch(() => null);
      if (r) for (const f of r.forms) candidates.push({ ...f, frameUrl: r.url });
    }
    const withFields = candidates.filter((c) => c.field_count > 0);
    if (withFields.length) {
      // Prefer a frame whose URL carries this screen's route, then the richest form.
      const key = (routeHint || '').replace(/^#/, '').split('/').pop().replace(/\/+$/, '');
      const onRoute = key ? withFields.filter((c) => c.frameUrl.includes(key)) : [];
      const pool = onRoute.length ? onRoute : withFields;
      pool.sort((a, b) => b.field_count - a.field_count);
      best = { ...pool[0], candidate_count: withFields.length, matched_route_frame: onRoute.length > 0 };
      break;
    }
    await page.waitForTimeout(700);
  }
  return best;
}

const browser = await chromium.connectOverCDP('http://localhost:9222');
const ctx = browser.contexts()[0];
let page = ctx.pages().find((p) => p.url().includes('jdadelivers')) || ctx.pages()[0];

/*
 * The SPA attaches ONE IFRAME PER SCREEN VISITED and never releases them: after a full crawl the
 * page was carrying 333 live frames, of which exactly one was visible. That accumulation is what
 * degrades the app, wedges its view layer, and eventually crashed the renderer.
 *
 * So reset periodically. A soft in-page reload keeps the OIDC session (only a hard reload dropped
 * it), and every frame-scanning helper gets dramatically faster afterwards.
 */
/*
 * Reopen a working page in the SAME browser context after a crash.
 *
 * A crashed renderer leaves a page object that throws on every call, and the previous run exited
 * 0 after screen 5 while silently failing the rest. Recreating the page inside the same context
 * keeps the session cookies, so this costs nothing; restarting Chrome would cost a manual login.
 */
async function revivePage(ctx, page) {
  try { await page.title(); return page; } catch { /* crashed */ }
  const fresh = await ctx.newPage();
  await fresh.goto('https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////',
    { waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {});
  await fresh.waitForTimeout(8000);
  for (const p of ctx.pages()) { if (p !== fresh) await p.close().catch(() => {}); }
  process.stderr.write('  [revive] opened a fresh page after a crash\n');
  return fresh;
}

async function resetFramesIfNeeded(page, limit = 30) {
  if (page.frames().length < limit) return false;
  const before = page.frames().length;
  /*
   * Reset EARLY. Letting frames pile up to 333 crashed the renderer during the reload itself,
   * and the browser had to be restarted - which loses the session, because it is held in a
   * session cookie that does not survive a Chrome restart. Resetting at ~30 keeps each reload
   * cheap and the app healthy.
   */
  await page.evaluate(() => { window.location.reload(); }).catch(() => {});
  await page.waitForTimeout(9000);
  for (let i = 0; i < 20 && page.frames().length < 2; i++) await page.waitForTimeout(700);
  process.stderr.write(`  [reset] frames ${before} -> ${page.frames().length}\n`);
  return true;
}

const existing = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { forms: [] };
const byHash = new Map(existing.forms.map((f) => [f.hash, f]));

console.error(`capturing Add-form models for ${targets.length} creatable screens`);
let i = 0;
for (const t of targets) {
  i++;
  const rec = { hash: t.hash, label: t.label, area: t.area, tier: t.tier };
  try {
    page = await revivePage(ctx, page);
    await resetFramesIfNeeded(page);
    await dismissBlocking(page);
    await page.evaluate(() => { window.location.hash = '#wm.config/wm.config.warehouse.warehouse////'; });
    await page.waitForTimeout(1200);
    await page.evaluate((h) => { window.location.hash = h; }, t.hash);
    await page.waitForTimeout(t.tier === 'operational' ? 6000 : 3500);
    for (let k = 0; k < 10 && page.frames().length < 2; k++) await page.waitForTimeout(500);

    // Leave any form a previous screen left open, then open Add.
    await clickIn(page, 'cancelButton', 3000);
    await page.waitForTimeout(900);
    const added = await clickIn(page, 'addButton', 14000);
    if (!added) throw new Error('no Add button found in any frame');
    await page.waitForTimeout(3500);

    const form = await readForm(page, t.hash);
    if (!form) { rec.error = 'no form rendered after Add'; }
    else {
      rec.field_count = form.field_count;
      rec.fields = form.fields;
      rec.required = form.fields.filter((f) => f.required);
      rec.candidate_forms = form.candidate_count;
      rec.matched_route_frame = form.matched_route_frame;
    }
    // Leave without saving so nothing is created and the next screen starts clean.
    await clickIn(page, 'cancelButton', 6000);
    await page.waitForTimeout(1200);
    await dismissBlocking(page);
  } catch (e) {
    rec.error = String(e).split('\n')[0].slice(0, 140);
  }
  byHash.set(t.hash, rec);
  process.stderr.write(`  [${i}/${targets.length}] ${t.area}/${t.label}: `
    + (rec.error ? 'ERR ' + rec.error : `${rec.field_count} fields, ${rec.required.length} required`) + '\n');
  if (i % 10 === 0) fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/map-forms.mjs', readOnly: true, forms: [...byHash.values()] }, null, 2) + '\n');
}
fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/map-forms.mjs', readOnly: true, forms: [...byHash.values()] }, null, 2) + '\n');
const all = [...byHash.values()];
const failed = all.filter((f) => f.error).length;
// A run that stops early must not look like success; the previous one exited 0 after 5 of 84.
if (failed > targets.length / 2) process.exitCode = 1;
console.log(JSON.stringify({
  captured: all.filter((f) => !f.error).length,
  failed: all.filter((f) => f.error).length,
  totalFields: all.reduce((a, f) => a + (f.field_count || 0), 0),
  totalRequired: all.reduce((a, f) => a + (f.required?.length || 0), 0),
}, null, 1));
await browser.close();
