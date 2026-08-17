/*
 * create-composite.mjs — prove the create contract of the two resources a flat payload cannot make.
 *
 * `pickMethods` and `releaseRules` refused every generated body. Driving the UI explained the first
 * one: the Add screen answers Save with **"Release rules are required for a pick method"** and sends
 * no request at all. A pick method is not a row — it is a row plus a nested `pickReleaseRules[]`,
 * which the generic battery never sent because it skipped arrays.
 *
 * `releaseRules` failed for a different reason of my own making: its id is the compound
 * `countZoneId*!releaseTypeId*!warehouseId`, and the battery's "don't copy the sampled row's
 * identity" rule dropped `warehouseId` with it — the very field the 422 kept asking for.
 *
 * So both bodies are built from a REAL record: copy it, drop the server-assigned ids, and vary only
 * the one key part that is safe to vary. Nothing here is invented; the shape comes from a record the
 * application itself created.
 *
 *   node tools/cdp/create-composite.mjs pickMethods
 *   node tools/cdp/create-composite.mjs releaseRules
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const mark = 'ZV' + String(Date.now() % 100000);

const call = (page, method, urlPath, body) => page.evaluate(
  async ({ method, urlPath, body, base }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;
    let res, text = '';
    try { res = await w.fetch(base + urlPath, { method, credentials: 'include', headers, body: body ? JSON.stringify(body) : undefined }); text = await res.text(); }
    catch (e) { return { networkError: String(e).slice(0, 160) }; }
    let parsed = null; try { parsed = JSON.parse(text); } catch {}
    let kind = 'OK';
    if (res.status === 404) kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
    return { requestHeaders: headers, status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 800), kind };
  }, { method, urlPath, body, base: BASE });

async function probe(page, resource, caseName, method, urlPath, body, notes) {
  const r = await call(page, method, urlPath, body);
  fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${resource}.jsonl`), JSON.stringify({
    ts: new Date().toISOString(), tool: 'tools/cdp/create-composite.mjs', case: caseName,
    request: { method, url: urlPath.split('?')[0], headers: { accept: 'application/json' }, body: body ?? null },
    response: { status: r.status, body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
    notes: notes || null,
  }) + '\n');
  const err = (r.body?.errors || []).map((e) => e.userMessage).join('; ');
  console.log(`  ${caseName.padEnd(26)} ${method.padEnd(6)} -> ${r.status} ${r.kind}${err ? ' :: ' + err.slice(0, 90) : ''}`);
  return r;
}

/* Fields the server owns. Copying any of them makes the create a duplicate or an orphan link. */
const SERVER_OWNED = (k) => k === 'resourceId' || k.endsWith('_uri') || /Id$/.test(k) && false;

const BUILDERS = {
  /*
   * A pick method carries its release rules inline. The sample's rules are reused with their own
   * ids stripped: `pickReleaseRuleId` and `pickMethodId` belong to the record we copied.
   */
  pickMethods: (row) => {
    const body = {};
    for (const [k, v] of Object.entries(row)) {
      if (k === 'resourceId' || k.endsWith('_uri') || k === 'pickMethodId') continue;
      if (k === 'pickReleaseRules') continue;
      body[k] = v;
    }
    body.pickMethodName = mark;
    body.description = mark;
    body.pickReleaseRules = (row.pickReleaseRules || []).slice(0, 1).map((r) => {
      const out = {};
      for (const [k, v] of Object.entries(r)) {
        if (k === 'resourceId' || k.endsWith('_uri') || k === 'pickReleaseRuleId' || k === 'pickMethodId') continue;
        out[k] = v;
      }
      return out;
    });
    return body;
  },
  /*
   * The id is countZoneId*!releaseTypeId*!warehouseId. Only `releaseTypeId` may vary: the other two
   * are foreign keys to a real count zone and a real warehouse, and inventing either would either
   * fail or attach the rule to something that does not exist.
   */
  releaseRules: (row) => {
    const body = {};
    for (const [k, v] of Object.entries(row)) {
      if (k === 'resourceId' || k.endsWith('_uri')) continue;
      body[k] = v;
    }
    body.releaseTypeId = mark.slice(-2);
    return body;
  },
};

/*
 * A movement path IS its (source zone, load level, destination zone) triple — resourceId is
 * `destZoneId*!loadLevel*!sourceZoneId`. Copying a row and renaming it produces a duplicate, and
 * dropping the two zone ids as "identity" made the server see no zones at all and answer
 * "The Source Move Zone and destination Move Zone must be different". So a new path needs a new
 * PAIR of real zones, taken from /wm/movementZones.
 */
BUILDERS.movementPaths = async (row, call, page) => {
  const zres = await call(page, 'GET', '/wm/movementZones?query=[]&offset=0&limit=25&siteId=SG&subsites=----');
  const zones = (Array.isArray(zres.body?.data) ? zres.body.data : []);
  const used = new Set([String(row.sourceMovementZone), String(row.destinationMovementZone)]);
  const pick = zones.filter((z) => !used.has(String(z.movementZoneId ?? z.resourceId)));
  if (pick.length < 2) return null;
  const [a, b] = pick;
  const body = {};
  for (const [k, v] of Object.entries(row)) {
    if (k === 'resourceId' || k.endsWith('_uri') || v === null || typeof v === 'object') continue;
    body[k] = v;
  }
  body.sourceMovementZone = a.movementZoneId ?? a.resourceId;
  body.destinationMovementZone = b.movementZoneId ?? b.resourceId;
  body.sourceMovementZoneCode = a.movementZoneCode ?? a.code;
  body.destinationMovementZoneCode = b.movementZoneCode ?? b.code;
  body.movementPathName = mark;
  return body;
};

/*
 * The general case, which the three hand-written builders above are special cases of: copy a real
 * record, drop what the server owns, and vary the ONE key part that identifies it.
 *
 * The identity is read from resourceId, whose parts are joined by `*!`. A part that matches a scope
 * field — warehouseId, clientId, buildingId, siteId — is a foreign key to the environment and must
 * be kept verbatim; that was the releaseRules lesson. Whatever is left is the record's own name.
 */
const SCOPE = new Set(['warehouseId', 'clientId', 'buildingId', 'siteId', 'subsite']);
function defaultBuilder(row) {
  const parts = String(row.resourceId ?? '').split('*!');
  const body = {};
  for (const [k, v] of Object.entries(row)) {
    if (k === 'resourceId' || k.endsWith('_uri') || typeof v === 'object') continue;
    body[k] = v;
  }
  // Fields carrying a key part, minus the scope keys, are the identity we are allowed to change.
  const identity = Object.keys(body).filter((k) => !SCOPE.has(k) && parts.includes(String(body[k])) && typeof body[k] === 'string');
  if (!identity.length) return null;
  for (const k of identity) {
    const cur = String(body[k]);
    body[k] = cur.length <= mark.length ? mark.slice(-cur.length) : mark;
  }
  // Give any description-like field the marker too, so the row is findable in the UI afterwards.
  for (const k of Object.keys(body)) if (/description|name/i.test(k) && typeof body[k] === 'string' && !identity.includes(k)) body[k] = mark;
  return body;
}

const resource = process.argv[2];
const builder = BUILDERS[resource] || defaultBuilder;
if (!resource) { console.error('usage: create-composite.mjs <resource>'); process.exit(1); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  const sample = await call(page, 'GET', `/wm/${resource}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`);
  const row = Array.isArray(sample.body?.data) ? sample.body.data[0] : null;
  if (!row) throw new Error('no existing record to model the body on');

  const built = builder(row, call, page);
  const body = built instanceof Promise ? await built : built;
  if (!body) throw new Error('could not build a body — not enough distinct source data');
  console.log(`\n${resource}: body modelled on ${row.resourceId}`);
  console.log(JSON.stringify(body).slice(0, 500));

  const created = await probe(page, resource, 'create-valid-composite', 'POST', `/wm/${resource}`, body,
    'Body copied from an existing record with server-owned ids removed and one key part varied. Flat generated payloads were refused; for pickMethods the UI refuses too, with "Release rules are required for a pick method".');
  /*
   * A 201 with an empty body still created something. Treating a missing resourceId as "nothing
   * created" left a real movementPaths row behind, found afterwards by a marker scan. Recover the id
   * from the collection before deciding anything.
   */
  let id = created.body?.data?.resourceId;
  if (!id && created.status >= 200 && created.status < 300) {
    const scan = await call(page, 'GET', `/wm/${resource}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`);
    id = (Array.isArray(scan.body?.data) ? scan.body.data : []).find((x) => JSON.stringify(x).includes(mark))?.resourceId;
    console.log(`  201 carried no resourceId; recovered ${id} from the collection`);
  }
  if (!id) { console.log(`  create returned ${created.status} and no addressable record — nothing to verify`); process.exit(0); }

  const idPath = `/wm/${resource}/${encodeURIComponent(id)}`;
  await probe(page, resource, 'create-duplicate', 'POST', `/wm/${resource}`, body, 'Uniqueness contract.');
  const read = await probe(page, resource, 'read-created', 'GET', idPath, undefined, 'A create is never proven by its own response.');
  if (resource === 'pickMethods') {
    const rules = read.body?.data?.pickReleaseRules;
    console.log(`  nested rules persisted: ${Array.isArray(rules) ? rules.length : 'none'}`);
  }
  await probe(page, resource, 'delete-valid', 'DELETE', idPath);
  const gone = await probe(page, resource, 'confirm-gone', 'GET', idPath, undefined, 'MUST be RECORD-MISSING.');
  console.log(`  VERDICT: ${gone.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + gone.kind + ') — record may still exist'}`);
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
