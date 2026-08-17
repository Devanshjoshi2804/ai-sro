/*
 * trace-entity.mjs — take one real record and find everything else that refers to it.
 *
 * The graph's relationships come from Configuration flows: addresses -> clients -> suppliers. The
 * operational side has none, because nothing here ever followed a real shipment or trailer through
 * the system. That was impossible before the filter grammar; now it is a query.
 *
 * Method, entirely evidence-driven: take a row, and for every OTHER resource that declares a
 * filterable column of the same name, ask it for rows carrying this row's value. A hit is a join
 * that works, recorded with the column, the value and the row count. A miss is recorded too — on a
 * filterable column a zero is meaningful, which is exactly why the filterability map had to exist
 * before this could be trusted.
 *
 * Read-only.
 *
 *   node tools/cdp/trace-entity.mjs trailers
 *   node tools/cdp/trace-entity.mjs shipments --keys shipmentId,clientId
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const EX = `${KG}/http/exchanges`;
const OUT = `${KG}/index/entity-traces.json`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';

const filterable = JSON.parse(fs.readFileSync(`${KG}/index/filterable-columns.json`, 'utf8')).resources;

const resource = process.argv[2];
if (!resource) { console.error('usage: trace-entity.mjs <resource> [--keys a,b]'); process.exit(1); }
/*
 * `indexOf('--keys')` returns -1 when the flag is absent, and argv[-1+1] is the node binary path —
 * so every run without --keys quietly filtered on "/usr/local/bin/node" and followed nothing.
 */
const keysIdx = process.argv.indexOf('--keys');
const keyArg = (process.argv.find((a) => a.startsWith('--keys=')) || '').split('=')[1]
  || (keysIdx > -1 ? process.argv[keysIdx + 1] : '');
const wantedKeys = keyArg ? keyArg.split(',') : null;

/* Values that identify nothing: flags, site codes, the blank client, tiny numbers. */
const boring = new Set(['SG', '----', 'Y', 'N', '0', '1', '', 'true', 'false']);
const useless = (v) => v === null || typeof v === 'boolean' || typeof v === 'object'
  || boring.has(String(v)) || String(v).length < 3;

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();

const get = (url) => page.evaluate(async ({ url, base }) => {
  const f = document.querySelector('iframe');
  const w = f && f.contentWindow && f.contentWindow.fetch ? f.contentWindow : window;
  let res, text = '';
  try { res = await w.fetch(base + url, { credentials: 'include', headers: { Accept: 'application/json' } }); text = await res.text(); }
  catch (e) { return { networkError: String(e).slice(0, 120) }; }
  let parsed = null; try { parsed = JSON.parse(text); } catch {}
  return { status: res.status, body: parsed, sessionExpired: !parsed && /b2clogin|<html|Sign in/i.test(text) };
}, { url, base: BASE });

const store = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : { traces: {} };

try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(11000);

  /*
   * Take the RICHEST row, not the first. The first trailer in the table had every id field null,
   * so the trace had nothing to follow and reported zero joins — a fact about that row, which would
   * have read as a fact about the resource.
   */
  const base1 = await get(`/wm/${resource}?query=[]&offset=0&limit=50&siteId=SG&subsites=----`);
  if (base1?.sessionExpired) { console.error('SESSION EXPIRED — nothing recorded.'); process.exit(2); }
  const candidates = Array.isArray(base1.body?.data) ? base1.body.data : [];
  if (!candidates.length) { console.log(`${resource}: nothing to trace`); process.exit(0); }
  const idish = (k) => /(^|[a-z])(id|code|number|name)$/i.test(k) && !/desc/i.test(k);
  const row = candidates.slice().sort((a, b) =>
    Object.keys(b).filter((k) => idish(k) && !useless(b[k])).length
    - Object.keys(a).filter((k) => idish(k) && !useless(a[k])).length)[0];

  /* The values worth chasing: this row's own identifying fields. */
  const keys = (wantedKeys || Object.keys(row).filter(idish))
    .filter((k) => k in row && !useless(row[k]));
  console.log(`tracing ${resource} ${row.resourceId ?? ''} by: ${keys.map((k) => `${k}=${JSON.stringify(row[k])}`).join(', ')}\n`);

  const hits = [];
  const misses = [];
  for (const key of keys) {
    const value = row[key];
    // Only ask resources that DECLARE this column filterable — anywhere else a zero means nothing.
    const askable = Object.entries(filterable)
      .filter(([name, spec]) => name !== resource && spec.filterable?.includes(key))
      .map(([name]) => name);

    for (const other of askable) {
      const q = encodeURIComponent(JSON.stringify([{ column: key, operator: 'EQ', value }]));
      const r = await get(`/wm/${other}?query=${q}&offset=0&limit=50&siteId=SG&subsites=----`);
      const rows = Array.isArray(r.body?.data) ? r.body.data : [];
      const rec = { from: resource, to: other, via: key, value: String(value), rows: rows.length, status: r.status };
      (rows.length ? hits : misses).push(rec);
      if (rows.length) {
        console.log(`  ${key.padEnd(16)} -> ${other.padEnd(28)} ${rows.length} row(s)`);
        fs.appendFileSync(path.join(EX, `${other}.jsonl`), JSON.stringify({
          ts: new Date().toISOString(), tool: 'tools/cdp/trace-entity.mjs', case: `join-from-${resource}-via-${key}`,
          request: { method: 'GET', url: `/wm/${other}`, query: { query: JSON.stringify([{ column: key, operator: 'EQ', value }]), limit: '50' }, headers: { accept: 'application/json' } },
          response: { status: r.status, body: rows.length > 2 ? { rows_returned: rows.length, data: rows.slice(0, 2) } : r.body },
          notes: `Following a real ${resource} record into ${other} by ${key}. Both sides declare ${key} filterable, so the row count is meaningful in either direction.`,
        }) + '\n');
      }
    }
  }

  /*
   * The record also publishes its own relationships: every `*_uri` field is a sub-collection the
   * app itself links to. Following them needs no filterability at all and is stronger evidence than
   * a value match — the server is naming the relationship.
   */
  const subs = [];
  for (const [k, v] of Object.entries(row)) {
    if (!k.endsWith('_uri') || typeof v !== 'string' || k === 'self_uri') continue;
    const p2 = v.replace(/^https?:\/\/[^/]+\/data\/WM/, '');
    const r = await get(`${p2}?query=[]&offset=0&limit=5&siteId=SG&subsites=----`);
    const rows = Array.isArray(r.body?.data) ? r.body.data : r.body?.data ? [r.body.data] : [];
    subs.push({ link: k, path: p2, status: r.status, rows: rows.length });
    console.log(`  ${k.padEnd(34)} ${r.status} ${rows.length} row(s)`);
    if (r.status === 200) {
      fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
        ts: new Date().toISOString(), tool: 'tools/cdp/trace-entity.mjs', case: `sub-collection-${k.replace('_uri', '')}`,
        request: { method: 'GET', url: p2, query: { limit: '5' }, headers: { accept: 'application/json' } },
        response: { status: r.status, body: rows.length > 2 ? { rows_returned: rows.length, data: rows.slice(0, 2) } : r.body },
        notes: `A sub-collection this ${resource} record links to by ${k}. The relationship is declared by the server, not inferred.`,
      }) + '\n');
    }
  }

  store.traces[resource] = {
    sub_collections: subs,
    traced_record: row.resourceId ?? null,
    keys_followed: keys,
    joins_that_returned_rows: hits,
    joins_that_returned_nothing: misses.map((m) => `${m.to} via ${m.via}`),
  };
  fs.writeFileSync(OUT, JSON.stringify({ generated_by: 'tools/cdp/trace-entity.mjs', ...store }, null, 2) + '\n');
  console.log(`\n${hits.length} join(s) returned rows, ${misses.length} returned none (both sides filterable, so the misses are real)`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
