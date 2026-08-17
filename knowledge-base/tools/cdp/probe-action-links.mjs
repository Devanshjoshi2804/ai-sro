/*
 * probe-action-links.mjs — the operational verbs are published by the records themselves.
 *
 * Tracing a trailer turned up links no catalogue contains: `checkIn_uri`, `dispatch_uri`,
 * `close_uri`, `closeWithWorkQueue_uri`. They are not sub-collections — a GET returns 404 or 405.
 * `closeWithWorkQueue_uri` answering **405** is the tell: the route exists and GET is not how you
 * use it. These are the operational actions this base has never been able to find, because they
 * appear in no endpoint catalogue and no screen map — the server names them, per record.
 *
 * This asks each link what it is, without performing anything: an OPTIONS request, and a GET whose
 * status and `Allow` header are recorded. Nothing is POSTed. Discovering that a verb exists is
 * useful on its own; using it is a separate, approved decision.
 *
 *   node tools/cdp/probe-action-links.mjs trailers
 *   node tools/cdp/probe-action-links.mjs trailers shipments outboundLoads
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/action-links.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';

const targets = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (!targets.length) { console.error('usage: probe-action-links.mjs <resource>...'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

/* GET and OPTIONS only. The Allow header on a 405 is what names the verb. */
const probe = (url, method) => page.evaluate(async ({ url, method, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { method, credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  const headers = {}; res.headers.forEach((v, k) => { headers[k] = v; });
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  return {
    status: res.status, allow: headers.allow || headers.Allow || null,
    body: parsed, bodyRaw: parsed ? null : text.slice(0, 200),
    sessionExpired: !parsed && /b2clogin|<html|Sign in/i.test(text),
  };
}, { url, method, base: BASE });

const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { resources: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(11000);

  for (const resource of targets) {
    const list = await probe(`/wm/${resource}?query=[]&offset=0&limit=50&siteId=SG&subsites=----`, 'GET');
    if (list?.sessionExpired) { console.error('SESSION EXPIRED — nothing recorded.'); process.exit(2); }
    const rows = Array.isArray(list.body?.data) ? list.body.data : [];
    // The record with the most links published on it — a sparse row hides half the verbs.
    const row = rows.slice().sort((a, b) =>
      Object.keys(b).filter((k) => k.endsWith('_uri')).length - Object.keys(a).filter((k) => k.endsWith('_uri')).length)[0];
    if (!row) { console.log(`${resource}: no rows`); continue; }

    const links = Object.entries(row).filter(([k, v]) => k.endsWith('_uri') && k !== 'self_uri' && typeof v === 'string');
    const actions = [];
    const collections = [];

    console.log(`\n${resource} ${row.resourceId ?? ''} — ${links.length} published links`);
    for (const [name, uri] of links) {
      const p2 = uri.replace(/^https?:\/\/[^/]+\/data\/WM/, '');
      const g = await probe(`${p2}?siteId=SG&subsites=----`, 'GET');
      const o = await probe(`${p2}?siteId=SG&subsites=----`, 'OPTIONS');
      const verbs = o.allow || g.allow || null;

      const entry = { link: name, path: p2, get_status: g.status, options_status: o.status, allow: verbs };
      /*
       * A 405 on GET means the route is real and GET is not its verb — that is an ACTION. A 200 is a
       * sub-collection. A 404 is ambiguous: this record may simply have nothing there.
       */
      entry.kind = g.status === 405 ? 'action (GET not allowed)'
        : g.status === 200 ? 'sub-collection'
        : g.status === 404 ? 'nothing here for this record, or action requiring another verb'
        : `unclear (${g.status})`;
      (entry.kind.startsWith('action') ? actions : collections).push(entry);

      fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
        ts: new Date().toISOString(), tool: 'tools/cdp/probe-action-links.mjs', case: `link-${name.replace('_uri', '')}`,
        request: { method: 'GET', url: p2, headers: { accept: 'application/json' } },
        response: { status: g.status, headers: verbs ? { allow: verbs } : {}, body: g.body, bodyRaw: g.bodyRaw },
        notes: `A link the ${resource} record publishes as ${name}. Probed with GET and OPTIONS only — no action was performed.`,
      }) + '\n');
      console.log(`  ${name.replace('_uri', '').padEnd(32)} GET ${g.status}  OPTIONS ${o.status}  ${verbs ? 'allow: ' + verbs : ''}  ${entry.kind}`);
    }

    store.resources[resource] = { sampled_record: row.resourceId ?? null, actions, sub_collections: collections };
    fs.writeFileSync(OUT, JSON.stringify({
      generated_by: 'tools/cdp/probe-action-links.mjs',
      what_this_is: 'Links each record publishes as *_uri. Some are sub-collections; some are OPERATIONS the endpoint catalogue does not contain. Probed with GET and OPTIONS only.',
      ...store,
    }, null, 2) + '\n');
  }

  const all = Object.values(store.resources);
  console.log(`\n${all.reduce((a, r) => a + r.actions.length, 0)} action link(s), ${all.reduce((a, r) => a + r.sub_collections.length, 0)} other link(s) across ${all.length} resource(s)`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
