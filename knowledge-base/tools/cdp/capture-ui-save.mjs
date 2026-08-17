/*
 * capture-ui-save.mjs — fill a screen's Add form, click Save, and record the request the APP makes.
 *
 * WHY: `pickMethods` and `releaseRules` refuse every payload derived from their own form model —
 * required-only, full-model-with-defaults, and discriminators borrowed from a real row all come back
 * 422 or 500. At that point continuing to synthesise bodies is guessing, and guessing is what
 * produced every falsified claim in this base. The application knows the correct body. Watch it.
 *
 * The form is filled from each field's OWN store (first real option) rather than from anything
 * invented, then Save is clicked and every non-GET request to /data/WM is captured with its body and
 * its response. The record created is then deleted and proven gone, exactly as a battery would.
 *
 *   node tools/cdp/capture-ui-save.mjs "Pick Methods"
 *   node tools/cdp/capture-ui-save.mjs "Count Release Rules" --keep     leave the record in place
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

/* Click a button by itemId or visible text, in whichever frame owns it. */
async function click(page, match, timeout = 12000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    for (const fr of page.frames()) {
      const id = await fr.evaluate((m) => {
        if (!window.Ext) return null;
        const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const r = d && d.getBoundingClientRect(); return r && r.width > 0 && r.height > 0; };
        const re = new RegExp(m, 'i');
        const b = window.Ext.ComponentQuery.query('button')
          .filter((x) => !x.isDestroyed && !x.disabled && vis(x) && (re.test(x.itemId || '') || re.test(String(x.text || '').replace(/<[^>]*>/g, '').trim())))
          .pop();
        return b && b.getEl() ? b.getEl().dom.id : null;
      }, match).catch(() => null);
      if (id) { await fr.locator('#' + id).click({ timeout: 5000 }).catch(() => {}); return true; }
    }
    await page.waitForTimeout(600);
  }
  return false;
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const captured = [];
page.on('requestfinished', async (req) => {
  if (req.method() === 'GET' || !/\/data\/WM\//.test(req.url())) return;
  const res = await req.response().catch(() => null);
  let body = null;
  try { body = await res?.json(); } catch { body = (await res?.text().catch(() => ''))?.slice(0, 600) ?? null; }
  captured.push({
    method: req.method(), url: req.url().replace(/^https?:\/\/[^/]+/, ''),
    request_headers: strip(req.headers()), request_body: (() => { try { return JSON.parse(req.postData() || 'null'); } catch { return req.postData()?.slice(0, 2000) ?? null; } })(),
    status: res?.status(), response_body: body,
  });
});

try {
  await page.goto(PORTAL + screen.hash, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(12000);
  if (!await click(page, '^addButton$|^Add$')) throw new Error('no Add button');
  await page.waitForTimeout(4000);

  /*
   * Fill from the live form. Every value comes from the field itself: a combo takes the first entry
   * of its own store, a text field takes the run marker trimmed to its maxLength, a number takes 1.
   * Nothing is invented, and combos are no longer skipped — here the app will validate them for us.
   */
  let filled = null;
  for (const fr of page.frames()) {
    const r = await fr.evaluate((m) => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const forms = window.Ext.ComponentQuery.query('form').filter(vis);
      const win = window.Ext.ComponentQuery.query('window').filter(vis).pop();
      const fields = forms.length
        ? forms.sort((a, b) => b.getForm().getFields().items.length - a.getForm().getFields().items.length)[0].getForm().getFields().items
        : (win ? win.query('field').filter(vis) : []);
      if (!fields || !fields.length) return null;
      const out = [];
      for (const f of fields) {
        if (!f.name || (f.getValue && f.getValue() !== '' && f.getValue() != null && f.getValue() !== false)) { out.push({ field: f.name, kept: true, value: f.getValue && f.getValue() }); continue; }
        let v;
        const st = f.getStore && f.getStore();
        if (st && st.getCount && st.getCount() > 0) {
          const rec = st.getRange().find((r) => r.get(f.valueField || 'code') != null) || st.getAt(0);
          v = rec.get(f.valueField || 'code');
        } else if (/number|spinner/i.test(f.xtype)) v = 1;
        else if (/check|toggle|radio/i.test(f.xtype)) v = false;
        else v = f.maxLength && f.maxLength < m.length ? m.slice(-f.maxLength) : m;
        try { f.setValue(v); } catch (e) { out.push({ field: f.name, error: String(e).slice(0, 80) }); continue; }
        out.push({ field: f.name, xtype: f.xtype, set: v });
      }
      return out;
    }, mark).catch(() => null);
    if (r && r.length) { filled = { frame: fr, fields: r }; break; }
  }
  if (!filled) throw new Error('no form rendered after Add');
  console.log(`filled ${filled.fields.length} fields`);
  for (const f of filled.fields) console.log(`   ${String(f.field).padEnd(28)} ${f.kept ? 'kept ' + JSON.stringify(f.value) : f.error ? 'ERR ' + f.error : JSON.stringify(f.set)}`);

  await page.waitForTimeout(1200);
  /*
   * Save is not always called Save. Five screens failed with "no Save button" while showing a filled
   * form: their commit control is a different itemId or word entirely. Widen the match, then fall
   * back to any enabled button whose itemId mentions save/submit/apply.
   */
  // Save can enable late: the form validates asynchronously after the last field is set, so a short
  // window reported "no Save button" on a screen whose Save was enabled a moment later.
  if (!await click(page, '^saveButton$|^Save$|^OK$|^Apply$|^Submit$|^Create$|^Finish$|^Done$|save.*Btn$|.*saveBtn$', 20000)
    && !await click(page, 'save|submit|apply', 6000)
    /*
     * Last resort: fire the component's own handler. On Existing Customers the diagnostic listed an
     * enabled `saveButton|Save` that the element click never found — the deck renders it outside the
     * frame the fields live in — and firing the handler is how the app itself invokes it.
     */
    && !await filled.frame.evaluate(() => {
      if (!window.Ext) return false;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      // No isDestroyed/disabled filter here on purpose: this path exists because those flags were
      // disagreeing with what the same query reported a second later, and the app's own handler is
      // harmless to call — if the form is not ready the app simply refuses, which is itself evidence.
      const b = window.Ext.ComponentQuery.query('button').filter((x) => vis(x)
        && (/^saveButton$/i.test(x.itemId || '') || /^save$/i.test(String(x.text || '').replace(/<[^>]*>/g, '').trim())))[0];
      if (!b) return false;
      b.fireHandler ? b.fireHandler() : b.handler && b.handler.call(b.scope || b, b);
      return true;
    }).catch(() => false)) {
    const buttons = await filled.frame.evaluate(() => {
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      return window.Ext.ComponentQuery.query('button').filter(vis)
        .map((b) => `${b.itemId || '?'}|${String(b.text || '').replace(/<[^>]*>/g, '').trim()}${b.disabled ? ' (disabled)' : ''}`);
    }).catch(() => []);
    throw new Error('no Save button; visible buttons were: ' + buttons.join(' , ').slice(0, 300));
  }
  await page.waitForTimeout(4000);
  /*
   * Photograph whatever the Save raised BEFORE dismissing it. The first version confirmed the
   * dialog away and then asked what it had said, which is how "Error :: [object Object]" became the
   * only surviving evidence of a refusal.
   */
  const raised = `${KG}/images/ui-save-${label.replace(/\W+/g, '-').toLowerCase()}-after-save.png`;
  await page.screenshot({ path: raised }).catch(() => {});
  console.log('after-save screenshot:', raised);
  // Some screens raise a confirmation or a validation dialog after Save.
  await click(page, '^(Yes|OK|Confirm)$', 3000);
  await page.waitForTimeout(4000);

  /* A Save that produces no request is either a click that missed or a form the app refused. */
  if (!captured.length) {
    const why = await filled.frame.evaluate(() => {
      if (!window.Ext) return null;
      const vis = (c) => { const d = c.getEl && c.getEl() && c.getEl().dom; const x = d && d.getBoundingClientRect(); return x && x.width > 0 && x.height > 0; };
      const form = window.Ext.ComponentQuery.query('form').filter(vis)[0];
      const invalid = form ? form.getForm().getFields().items.filter((f) => f.isValid && !f.isValid())
        .map((f) => ({ field: f.name, error: (f.getErrors && f.getErrors()[0]) || 'invalid' })) : [];
      return {
        form_still_open: !!form,
        valid: form ? form.getForm().isValid() : null,
        invalid,
        buttons: window.Ext.ComponentQuery.query('button').filter(vis)
          .map((b) => ({ itemId: b.itemId, text: String(b.text || '').replace(/<[^>]*>/g, '').trim(), disabled: !!b.disabled })),
        // `msg` is sometimes an object, which printed as "[object Object]" and hid the real reason.
        // Read what the dialog actually renders.
        messages: window.Ext.ComponentQuery.query('messagebox,window').filter(vis).map((w) => {
          const el = w.getEl && w.getEl() && w.getEl().dom;
          return String(w.title || '') + ' :: ' + (el ? el.innerText.replace(/\s+/g, ' ').trim().slice(0, 400) : '');
        }),
      };
    }).catch(() => null);
    console.log('\nno request fired — form state:', JSON.stringify(why, null, 1));
    // The dialog's own text came back empty, so keep the pixels: this is the only record of why.
    const shot = `${KG}/images/ui-save-${label.replace(/\W+/g, '-').toLowerCase()}.png`;
    await page.screenshot({ path: shot, fullPage: false }).catch(() => {});
    console.log('screenshot:', shot);
  }

  console.log(`\nrequests the Save produced (${captured.length}):`);
  for (const c of captured) console.log(`  ${c.method} ${c.url.split('?')[0]} -> ${c.status}`);

  const create = captured.find((c) => c.method === 'POST' && c.status >= 200 && c.status < 300);
  for (const c of captured) {
    const resource = (c.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1] || 'unknown';
    fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${resource}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/capture-ui-save.mjs',
      case: c.method === 'POST' && c.status < 300 ? 'create-valid-ui-captured' : `ui-save-${c.method.toLowerCase()}-${c.status}`,
      request: { method: c.method, url: c.url.replace('/data/WM', '').split('?')[0], query: Object.fromEntries(new URLSearchParams(c.url.split('?')[1] || '')), headers: c.request_headers, body: c.request_body },
      response: { status: c.status, body: c.response_body },
      notes: `Body produced by the application itself on ${label} > Add > Save. Every synthesised payload for this resource was refused; this is what the screen actually sends.`,
    }) + '\n');
  }

  if (create) {
    console.log('\nAPP PAYLOAD:', JSON.stringify(create.request_body, null, 1));
    /*
     * Teach app-map which resource this screen WRITES to. Several screens save to a resource they
     * never read — Storage Velocity and Hold Types both write to `codes` — so coverage kept scoring
     * them as having no known write endpoint while their payload sat recorded in the store.
     */
    const wrote = (create.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1];
    if (wrote) {
      const mapPath = `${KG}/index/app-map.json`;
      const map = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
      const sc = map.screens.find((x) => x.hash === screen.hash);
      if (sc && !(sc.resources || []).includes(wrote)) {
        sc.resources = [...(sc.resources || []), wrote];
        sc.writes_observed = [...new Set([...(sc.writes_observed || []), wrote])];
        fs.writeFileSync(mapPath, JSON.stringify(map, null, 2) + '\n');
        console.log(`  recorded on the screen map: ${label} writes to ${wrote}`);
      }
    }
    /*
     * Recover the id even when the 201 carries nothing useful. Several resources answer with an
     * empty body, and a batch create answers with an array — treating either as "no id" would leave
     * the record this capture just made sitting in the system.
     */
    const resource = (create.url.match(/\/data\/WM\/wm\/([A-Za-z0-9]+)/) || [])[1];
    let id = create.response_body?.data?.resourceId
      || (Array.isArray(create.response_body?.data) ? create.response_body.data[0]?.resourceId : null);
    if (!id && resource) {
      const found = await page.evaluate(async ({ base, r, m }) => {
        const f = document.querySelector('iframe');
        const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
        const res = await w.fetch(`${base}/wm/${r}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`,
          { credentials: 'include', headers: { Accept: 'application/json' } });
        const j = await res.json().catch(() => null);
        const rows = Array.isArray(j?.data) ? j.data : [];
        return rows.find((x) => JSON.stringify(x).includes(m))?.resourceId ?? null;
      }, { base: 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM', r: resource, m: mark }).catch(() => null);
      if (found) { id = found; console.log(`  201 carried no addressable id; recovered ${id} from the collection`); }
    }
    if (id && !keep) {
      const del = await page.evaluate(async ({ base, p }) => {
        const f = document.querySelector('iframe');
        const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
        const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
        const d = await w.fetch(base + p, { method: 'DELETE', credentials: 'include', headers: tok ? { 'CSRF-ENCRYPT-TOKEN': tok } : {} });
        const g = await w.fetch(base + p, { credentials: 'include', headers: { Accept: 'application/json' } });
        const t = await g.text();
        return { del: d.status, get: g.status, kind: g.status === 404 ? (/"errors"/.test(t) ? 'RECORD-MISSING' : 'ROUTE-MISSING') : 'still-present' };
      }, { base: 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM', p: `/wm/${resource}/${encodeURIComponent(id)}` });
      console.log(`cleanup: delete ${del.del} · confirm ${del.get} ${del.kind}`);
    } else if (id) {
      console.log(`kept: ${resource}/${id}`);
    }
  } else {
    console.log('\nno successful POST — the Save did not create anything');
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
