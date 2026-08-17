/*
 * write-battery.mjs — prove the write contract of a resource, or say why it could not be proven.
 *
 * `coverage.json` reports write_apis complete on 9 of 85 creatable screens. The blocker was never
 * the lifecycle — `probe-resource.mjs` already runs one — it was knowing WHICH resource a screen
 * writes to, and with WHAT body. Both are now answerable from captured evidence:
 *
 *   body      <- index/create-candidates.json, derived from the real Add form's field model
 *   resource  <- index/read-shapes.json, by matching the payload's keys against the fields a
 *                resource actually returns
 *
 * The resource match is the part worth being strict about. Writing a Customer Type body into the
 * wrong table would create a real row somewhere nobody is looking. So a resource is accepted only
 * when it returns the payload's keys, and a screen whose match is weak is REPORTED as unresolved
 * rather than attempted.
 *
 * Every run creates one throwaway record and ends by proving it gone with a RECORD-MISSING 404.
 * A create that cannot be cleaned up is printed as a loud LEAK line, not swallowed.
 *
 *   node tools/cdp/write-battery.mjs --dry            what would be attempted, and against what
 *   node tools/cdp/write-battery.mjs "Hold Types"     one screen
 *   node tools/cdp/write-battery.mjs --all 10         the first 10 resolvable screens
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const SENSITIVE = /^(cookie|set-cookie|authorization|csrf-encrypt-token|x-csrf.*|proxy-authorization)$/i;
const strip = (h) => Object.fromEntries(Object.entries(h || {}).filter(([k]) => !SENSITIVE.test(k)));

const candidates = JSON.parse(fs.readFileSync(`${KG}/index/create-candidates.json`, 'utf8')).candidates;
const shapes = JSON.parse(fs.readFileSync(`${KG}/index/read-shapes.json`, 'utf8')).resources;
const screens = JSON.parse(fs.readFileSync(`${KG}/index/app-map.json`, 'utf8')).screens;
const byLabel = new Map(screens.map((s) => [s.label, s]));
/*
 * "Already proven" means a create was actually recorded — not that a file exists. Every resource
 * gained a .jsonl when read shapes were captured, so file existence stopped meaning anything.
 */
const done = new Set(fs.readdirSync(path.join(HTTP_DIR, 'exchanges')).filter((f) =>
  fs.readFileSync(path.join(HTTP_DIR, 'exchanges', f), 'utf8').split('\n').filter(Boolean).some((l) => {
    try { const r = JSON.parse(l); return /^create-valid/.test(r.case) && r.response?.status >= 200 && r.response?.status < 300; }
    catch { return false; }
  })).map((f) => f.replace('.jsonl', '')));

/*
 * Which resource does this screen write to?
 *
 * Score every resource the screen is known to READ by how many of the candidate payload's keys it
 * returns. A resource that returns all of them is almost certainly the one the form saves to; a
 * resource that returns none is a lookup feeding a dropdown. Ties break toward the resource whose
 * name the screen's route mentions.
 */
function resolveResource(cand) {
  const screen = byLabel.get(cand.screen);
  const keys = Object.keys(cand.payload);
  if (!screen || !keys.length) return null;

  /*
   * Candidates come from three places, widest first:
   *   - `screen.reads`, the calls recorded when the screen was first mapped
   *   - `screen.resources`, which now includes everything observed on the wire
   *   - the resource whose NAME matches the screen's label
   *
   * The third matters more than it looks. "Customer Types" resolved to `customers` at 1 of 2 keys
   * and was refused, while `customerTypes` — the obvious answer, already proven elsewhere in this
   * base — was never considered, because the screen's own reads list did not name it.
   */
  const nameKey = cand.screen.toLowerCase().replace(/[^a-z]/g, '');
  const byName = Object.keys(shapes).filter((r) => {
    const n = r.toLowerCase();
    return n === nameKey || n === nameKey.replace(/s$/, '') || n + 's' === nameKey;
  });
  const read = [...new Set([
    ...(screen.reads || []).map((r) => {
      const m = String(r.url).match(/\/data\/WM\/wm\/([A-Za-z0-9]+)(\/|\?|$)/);
      return m ? m[1] : null;
    }).filter(Boolean),
    ...(screen.resources || []),
    ...byName,
  ])];

  const scored = read.map((name) => {
    const shape = shapes[name];
    if (!shape || shape.status !== 200) return { name, score: 0, of: keys.length, why: 'no recorded 200 shape' };
    const fields = new Set(shape.fields.map((f) => f.field));
    const hit = keys.filter((k) => fields.has(k)).length;
    return { name, score: hit, of: keys.length, empty_sample: shape.rows_returned === 0 };
  }).sort((a, b) => b.score - a.score);

  const best = scored[0];
  if (!best || best.score === 0) return { unresolved: 'no read resource returns any of the payload keys', scored };
  if (scored[1] && scored[1].score === best.score) {
    return { unresolved: `ambiguous: ${best.name} and ${scored[1].name} match equally`, scored };
  }
  /*
   * Partial matches are refused. A body whose keys the target does not return is a body for some
   * other table, and the cost of being wrong is a real row created where nobody is looking —
   * `RF Devices -> rfVendors` scored 1 of 8 and would have been exactly that mistake.
   */
  if (best.score < keys.length) {
    /*
     * A resource whose sample came back EMPTY cannot match any key — it has no fields to match
     * against. `businessUnits` and `levelTypes` failed here purely because earlier cleanups left
     * their tables empty. Where the resource's name is the screen's name, the wrong-table risk this
     * strictness exists to prevent does not apply, so accept it and record which rule was used.
     */
    const named = scored.find((x) => byName.includes(x.name) && x.empty_sample);
    if (named) return { resource: named.name, match: 'name match; the collection is empty so no key could be compared', scored: scored.slice(0, 3) };
    return { unresolved: `partial match only: ${best.name} returns ${best.score} of ${keys.length} payload keys`, scored };
  }
  return { resource: best.name, match: `${best.score}/${best.of} payload keys`, scored: scored.slice(0, 3) };
}

const exchange = (page, method, urlPath, body) => page.evaluate(
  async ({ method, urlPath, body, base }) => {
    const f = document.querySelector('iframe');
    const w = f && f.contentWindow && f.contentWindow.Ext ? f.contentWindow : window;
    const tok = w.Ext?.Ajax?.defaultHeaders?.['CSRF-ENCRYPT-TOKEN'];
    const headers = { Accept: 'application/json' };
    if (body) headers['Content-Type'] = 'application/json';
    if (method !== 'GET' && tok) headers['CSRF-ENCRYPT-TOKEN'] = tok;
    let res, text = '';
    try {
      res = await w.fetch(base + urlPath, { method, credentials: 'include', headers, body: body ? JSON.stringify(body) : undefined });
      text = await res.text();
    } catch (e) { return { networkError: String(e).slice(0, 160), requestHeaders: headers }; }
    const rh = {}; res.headers.forEach((v, k) => { rh[k] = v; });
    let kind = 'OK';
    if (res.status === 404) kind = /"url"\s*:\s*"\/ws\//.test(text) ? 'ROUTE-MISSING' : /"errors"\s*:/.test(text) ? 'RECORD-MISSING' : 'UNKNOWN-404';
    else if (res.status < 200 || res.status >= 300) kind = 'HTTP-' + res.status;
    let parsed = null; try { parsed = JSON.parse(text); } catch {}
    return { requestHeaders: headers, status: res.status, statusText: res.statusText, responseHeaders: rh, body: parsed, bodyRaw: parsed ? null : text.slice(0, 2000), kind };
  }, { method, urlPath, body, base: BASE });

async function probe(page, resource, caseName, method, urlPath, body, notes) {
  const r = await exchange(page, method, urlPath, body);
  const rec = {
    ts: new Date().toISOString(), tool: 'tools/cdp/write-battery.mjs', case: caseName,
    request: { method, url: urlPath.split('?')[0], headers: strip(r.requestHeaders), body: body ?? null },
    response: r.networkError ? { networkError: r.networkError }
      : { status: r.status, statusText: r.statusText, headers: strip(r.responseHeaders), body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
    notes: notes || null,
  };
  fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${resource}.jsonl`), JSON.stringify(rec) + '\n');
  console.log(`    ${caseName.padEnd(18)} ${method.padEnd(6)} -> ${r.status ?? 'ERR'} ${r.kind ?? ''}`);
  return rec;
}

/* A short unique token, stamped so a leaked record is identifiable in the UI later. */
const stamp = () => 'ZV' + String(Date.now() % 100000);

const formModels = new Map(JSON.parse(fs.readFileSync(`${KG}/index/form-models-all.json`, 'utf8'))
  .forms.filter((f) => f.fields).map((f) => [f.label, f.fields]));

/*
 * The required-only body is not always enough. `countTypes` refused one with
 * `422 Missing argument: Different User (diff_usr_flg)` — a checkbox the form marks optional and the
 * server does not. The 422 cannot be used to fix it either: it names the DB column, and the body
 * wants a camelCase key that is not derivable from it.
 *
 * So the fallback sends EVERY field the captured form model knows about, each at its type's neutral
 * default. Still nothing invented — the keys all come from the live form; only the values are ours.
 */
function fullPayload(cand, mark) {
  const fields = formModels.get(cand.screen);
  if (!fields) return null;
  const body = { ...cand.payload };
  for (const f of fields) {
    if (!f.field || f.field in body) continue;
    switch (f.type) {
      // `rpToggle` is this app's own switch xtype and is the one that mattered: the countTypes 422
      // named `diff_usr_flg`, whose body key is the rpToggle `differentUserFlag`.
      case 'checkbox': case 'checkboxfield': case 'radiogroup': case 'rpToggle': body[f.field] = false; break;
      case 'numberfield': body[f.field] = 0; break;
      case 'textfield': case 'textarea':
        // Only fill a free-text field if it is required; an optional one is safer left out.
        if (f.required) body[f.field] = f.maxLength && f.maxLength < mark.length ? mark.slice(0, f.maxLength) : mark;
        break;
      default: break;   // combos, lookups and composites stay out: a value there is a foreign key.
    }
  }
  return Object.keys(body).length > Object.keys(cand.payload).length ? body : null;
}

async function battery(page, cand, resource) {
  const coll = `/wm/${resource}`;
  const mark = stamp();
  /*
   * Re-token every generated string so repeated runs never collide with their own leftovers.
   * Tight fields matter here: `uoms.codeValue` has maxLength 2, so the generator had emitted the
   * bare literal "ZV" — identical on every run, and a guaranteed duplicate rather than a throwaway.
   * A short field gets the marker's last characters, which still vary per run.
   */
  const fields = new Map((formModels.get(cand.screen) || []).map((f) => [f.field, f]));
  const body = Object.fromEntries(Object.entries(cand.payload).map(([k, v]) => {
    if (typeof v !== 'string' || !/^ZV/.test(v)) return [k, v];
    const max = fields.get(k)?.maxLength;
    return [k, max && max < mark.length ? mark.slice(-max) : mark];
  }));

  let created = await probe(page, resource, 'create-valid', 'POST', coll, body,
    `Throwaway record for ${cand.screen}. Payload from the captured Add-form model; the cycle ends by deleting it and proving it gone.`);

  // A 422 naming a missing argument means the server wants more than the form marks required.
  if (created.response?.status === 422 && /Missing argument/i.test(JSON.stringify(created.response.body || ''))) {
    const full = fullPayload(cand, mark);
    if (full) {
      console.log(`    retrying with the full form model (${Object.keys(full).length} keys, was ${Object.keys(body).length})`);
      created = await probe(page, resource, 'create-valid-full-model', 'POST', coll, full,
        'The required-only body was refused with "Missing argument"; this sends every key the captured form model knows, at neutral defaults.');
    }
  }

  /*
   * Still refused. The remaining "Missing argument" fields are all DISCRIMINATORS the form never
   * shows because the screen already knows them: `wh_id`, `reagrp`, `colnam`. They are not
   * derivable from the error — it names the DB column — and inventing them is the habit that
   * produced every falsified claim here.
   *
   * So take them from a record that already exists. One GET of the collection gives a real row;
   * every scalar field of it that the payload does not already set is copied in, except the
   * identity fields. The resulting body is not a guess: it is an existing record with our own
   * natural key, and it is recorded as sampled-row derived so nobody mistakes it for a minimal one.
   */
  /*
   * `Missing argument: Column (colnam)` means this is not a table at all — it is a VIEW over
   * /wm/codes, partitioned by columnName. `uoms` proved it: POST /wm/codes with columnName `uomcod`
   * returns 201, and the new record is immediately readable at /wm/uoms/{id}. So the create for
   * such a screen belongs to codes, and the resource under test is where you read it back.
   */
  if (created.response?.status === 422 && /\(colnam\)/i.test(JSON.stringify(created.response.body || ''))) {
    const sample = await exchange(page, 'GET', `${coll}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`);
    const partition = (Array.isArray(sample.body?.data) ? sample.body.data[0] : null)?.columnName;
    if (partition) {
      const codeBody = {
        codeValue: body[Object.keys(body)[0]], columnName: partition,
        longDescription: mark, shortDescription: mark.slice(-4), sortSequence: 99, requiredFlag: 0,
      };
      console.log(`    this resource is a /wm/codes view (columnName=${partition}); creating through codes`);
      created = await probe(page, resource, 'create-valid-via-codes', 'POST', '/wm/codes', codeBody,
        `${resource} is a read view over /wm/codes partition "${partition}". The create goes to codes; the record is then readable under ${coll}.`);
      if (created.response?.status === 201) {
        const rid = created.response.body?.data?.resourceId;
        await probe(page, resource, 'read-created-through-view', 'GET', `${coll}/${encodeURIComponent(rid)}`, undefined,
          'Proves the view and the underlying partition are the same record.');
        await probe(page, resource, 'delete-via-codes', 'DELETE', `/wm/codes/${encodeURIComponent(rid)}`);
        const gone = await probe(page, resource, 'confirm-gone', 'GET', `/wm/codes/${encodeURIComponent(rid)}`, undefined,
          'MUST be RECORD-MISSING.');
        console.log(`    VERDICT: ${gone.response?.kind === 'RECORD-MISSING' ? 'PASS (via codes)' : 'INCONCLUSIVE'}`);
        return { screen: cand.screen, resource, backing: 'codes:' + partition, verdict: gone.response?.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE' };
      }
    }
  }

  /*
   * Any 422 is worth one attempt from a real record, not only a "Missing argument" one. movementPaths
   * refused with "The Source Move Zone and destination Move Zone must be different" — the generator
   * had filled both foreign keys with the same token, because it has no way to know two fields must
   * differ or that either is a zone code at all. An existing row satisfies both constraints for free.
   */
  if (created.response?.status === 422) {
    const sample = await exchange(page, 'GET', `${coll}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`);
    const row = Array.isArray(sample.body?.data) ? sample.body.data[0] : null;
    if (row) {
      /*
       * Do not borrow the sampled row's IDENTITY, or the create is a duplicate of it — which is
       * what `pickMethods` and `releaseRules` answered with a 409. The record's own resourceId
       * names the key parts, joined by `*!`, so any field carrying one of those values is dropped
       * unless we set it ourselves.
       */
      const keyParts = new Set(String(row.resourceId || '').split('*!'));
      /*
       * Start from the REAL row, not from the generated body. Starting from the generated one meant
       * every key it already held was skipped as "already present", so the row's valid values never
       * arrived — movementPaths kept both zone codes set to the same token and failed identically.
       */
      const borrowed = {};
      for (const [k, v] of Object.entries(row)) {
        if (keyParts.has(String(v)) && !(k in body)) continue;
        // `*_uri` fields are links to a sub-collection of the record we sampled. Copying one made
        // the server answer 500 — the new record was being told it owned another record's children.
        if (k === 'resourceId' || k.endsWith('_uri')) continue;
        if (v === null || typeof v === 'object') continue;
        borrowed[k] = v;
      }
      /*
       * Re-impose the generated values ONLY on the fields that identify the record — its first key
       * and anything name- or description-like. Re-imposing all of them put the token back into
       * `sourceMovementZoneCode` and `destinationMovementZoneCode`, so the borrowed row's two valid
       * distinct zones were overwritten with the same value and the 422 came back unchanged. Every
       * other field keeps the real record's value, which is the entire point of borrowing one.
       */
      const identifying = new Set([Object.keys(body)[0], ...Object.keys(body).filter((k) => /name|description/i.test(k) && !/zone|type|group|method|status/i.test(k))]);
      for (const k of Object.keys(body)) if (identifying.has(k) || !(k in borrowed)) borrowed[k] = body[k];
      console.log(`    retrying with discriminators borrowed from a real row (${Object.keys(borrowed).length} keys)`);
      created = await probe(page, resource, 'create-valid-sampled-row', 'POST', coll, borrowed,
        'The form model was not enough: the server demanded discriminator columns the screen supplies implicitly (wh_id, reagrp, colnam). These values are copied from an existing record rather than invented.');
    }
  }

  const id = created.response?.body?.data?.resourceId;
  if (!id) {
    console.log(`    ! no resourceId returned (status ${created.response?.status}) — nothing to verify or clean up`);
    return { screen: cand.screen, resource, verdict: 'CREATE-FAILED', status: created.response?.status ?? null };
  }
  const idPath = `${coll}/${encodeURIComponent(id)}`;

  /*
   * On several resources a duplicate create SUCCEEDS — addresses, pickMethods and distributionTypes
   * all answered 201 to the same body twice. The battery used to move on and delete only the first
   * record, leaving the second behind for a marker scan to find later. Clean up whatever the
   * duplicate created, right here.
   */
  const dup = await probe(page, resource, 'create-duplicate', 'POST', coll, body, 'Uniqueness contract at the API layer.');
  if (dup.response?.status >= 200 && dup.response?.status < 300) {
    let dupId = dup.response.body?.data?.resourceId;
    if (!dupId) {
      const scan = await exchange(page, 'GET', `${coll}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`);
      const rows = (Array.isArray(scan.body?.data) ? scan.body.data : []).filter((x) => JSON.stringify(x).includes(mark));
      dupId = rows.length > 1 ? rows[rows.length - 1].resourceId : null;
    }
    if (dupId) {
      await probe(page, resource, 'cleanup-duplicate', 'DELETE', `${coll}/${encodeURIComponent(dupId)}`, undefined,
        'This resource accepted a duplicate create, so the extra record is removed immediately rather than left for a later scan.');
    }
  }
  await probe(page, resource, 'create-empty', 'POST', coll, {}, 'Which fields the SERVER enforces, as opposed to the form.');
  const read = await probe(page, resource, 'read-created', 'GET', idPath, undefined, 'A create is never proven by its own response.');

  // Mutate a string field that is not part of the id, and confirm by re-reading rather than by the PUT's status.
  const rec = read.response?.body?.data;
  const mutable = rec && Object.keys(rec).find((k) => typeof rec[k] === 'string' && k !== 'resourceId'
    && !Object.keys(body).slice(0, 1).includes(k) && /desc|name|text/i.test(k));
  if (rec && mutable) {
    const put = { ...rec, [mutable]: 'ZV updated' };
    delete put.self_uri;
    await probe(page, resource, 'update-valid', 'PUT', idPath, put);
    const after = await probe(page, resource, 'read-updated', 'GET', idPath, undefined, 'A 200 on PUT does not mean the field persisted.');
    console.log(`    persisted(${mutable})=${after.response?.body?.data?.[mutable] === 'ZV updated'}`);
  }

  await probe(page, resource, 'delete-valid', 'DELETE', idPath);
  await probe(page, resource, 'delete-again', 'DELETE', idPath, undefined, 'Idempotency is per-resource here, not universal.');
  const gone = await probe(page, resource, 'confirm-gone', 'GET', idPath, undefined,
    'MUST be RECORD-MISSING; a ROUTE-MISSING here would mean the cycle proved nothing.');

  const verdict = gone.response?.kind === 'RECORD-MISSING' ? 'PASS' : `INCONCLUSIVE (${gone.response?.kind})`;
  if (verdict !== 'PASS') console.log(`    LEAK RISK: ${resource} ${id} may still exist — verdict ${verdict}`);
  console.log(`    VERDICT: ${verdict}`);
  return { screen: cand.screen, resource, id, verdict };
}

/* --- plan --- */
const args = process.argv.slice(2);
const dry = args.includes('--dry');
const all = args.includes('--all');
const nameArg = args.find((a) => !a.startsWith('--') && !/^\d+$/.test(a));
const cap = Number(args.find((a) => /^\d+$/.test(a))) || Infinity;

const plan = [];
for (const c of candidates) {
  if (!c.ready) continue;
  if (nameArg && c.screen !== nameArg) continue;
  const m = resolveResource(c);
  plan.push({ cand: c, ...(m || { unresolved: 'no screen record' }) });
}
const runnable = plan.filter((p) => p.resource && !done.has(p.resource) || (p.resource && nameArg));
const skipped = plan.filter((p) => p.unresolved);

console.log(`${plan.length} ready candidates · ${plan.length - skipped.length} resolved to a resource · ${skipped.length} unresolved`);
for (const p of plan.filter((x) => x.resource).slice(0, 60)) {
  console.log(`  ${p.cand.screen.padEnd(34)} -> ${p.resource.padEnd(28)} ${p.match}${done.has(p.resource) ? '  [already has exchanges]' : ''}`);
}
if (skipped.length) {
  console.log('\nunresolved:');
  for (const p of skipped) console.log(`  ${p.cand.screen.padEnd(34)} ${p.unresolved}`);
}
if (dry) process.exit(0);

const targets = (nameArg ? plan.filter((p) => p.resource) : runnable).slice(0, all || nameArg ? cap : 1);
if (!targets.length) { console.log('\nnothing to run'); process.exit(0); }

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
const results = [];
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);
  for (const t of targets) {
    console.log(`\n${t.cand.screen} -> /wm/${t.resource}  (${t.match})`);
    results.push(await battery(page, t.cand, t.resource));
  }
} finally {
  await page.close().catch(() => {});
}
fs.appendFileSync(`${HTTP_DIR}/write-battery-runs.jsonl`,
  results.map((r) => JSON.stringify({ ts: new Date().toISOString(), ...r })).join('\n') + '\n');
console.log('\n' + JSON.stringify(results.reduce((a, r) => (a[r.verdict] = (a[r.verdict] || 0) + 1, a), {}), null, 1));
process.exit(0);
