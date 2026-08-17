/*
 * replay-battery.mjs — finish the failure battery for any resource whose create is already proven.
 *
 * Seven resources have a recorded, successful create — most captured from the application's own Save
 * — but no `create-duplicate`, `create-empty` or `confirm-gone`, so they still count as incomplete.
 * Nothing needs deriving for them: the exact body that worked is in the evidence store. Replay it
 * with a fresh marker and run the cases that are missing.
 *
 * This is the cheapest remaining coverage: no form model, no resource resolution, no guessing.
 *
 *   node tools/cdp/replay-battery.mjs --dry
 *   node tools/cdp/replay-battery.mjs                 every resource with a gap
 *   node tools/cdp/replay-battery.mjs noteTypes
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const EX = path.join(HTTP_DIR, 'exchanges');
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const REQUIRED = ['create-duplicate', 'create-empty', 'confirm-gone'];

/*
 * `workOperations` is excluded by name: its DELETE answers 200 and does not delete, proven four
 * ways, so replaying a create there leaves a second permanent row nobody can remove.
 */
const NEVER = {
  workOperations: 'DELETE is a proven no-op on this resource; a replayed create would be permanent.',
  holdDefinitions: 'Create-only for this user: DELETE answers 422 on a permission check and PUT does not persist, so anything created here stays.',
  packingConfigurations: 'Its create answers 201 but the record is then unreadable — absent from the collection and 500 on GET by id — so a replay produces something that cannot be verified or deleted.',
};

const plan = [];
for (const file of fs.readdirSync(EX)) {
  const resource = file.replace('.jsonl', '');
  const rows = fs.readFileSync(path.join(EX, file), 'utf8').split('\n').filter(Boolean)
    .map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
  const ok = rows.filter((r) => /^create-valid/.test(r.case || '') && r.response?.status >= 200 && r.response?.status < 300).pop();
  if (!ok || !ok.request?.body) continue;
  const cases = new Set(rows.map((r) => r.case));
  const missing = REQUIRED.filter((c) => !cases.has(c));
  if (!missing.length) continue;
  plan.push({ resource, url: ok.request.url, body: ok.request.body, missing, skip: NEVER[resource] });
}

const dry = process.argv.includes('--dry');
const only = process.argv.slice(2).find((a) => !a.startsWith('--'));
const targets = plan.filter((p) => !only || p.resource === only);

console.log(`${targets.length} resource(s) with a proven create and a missing case`);
for (const t of targets) console.log(`  ${t.resource.padEnd(28)} missing ${t.missing.join(',')}${t.skip ? '   SKIPPED: ' + t.skip : ''}`);
if (dry) process.exit(0);

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
    return { status: res.status, body: parsed, bodyRaw: parsed ? null : text.slice(0, 600), kind };
  }, { method, urlPath, body, base: BASE });

async function probe(page, resource, caseName, method, urlPath, body, notes) {
  const r = await call(page, method, urlPath, body);
  fs.appendFileSync(path.join(EX, `${resource}.jsonl`), JSON.stringify({
    ts: new Date().toISOString(), tool: 'tools/cdp/replay-battery.mjs', case: caseName,
    request: { method, url: urlPath.split('?')[0], headers: { accept: 'application/json' }, body: body ?? null },
    response: { status: r.status, body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
    notes: notes || null,
  }) + '\n');
  const err = (r.body?.errors || []).map((e) => e.userMessage).join('; ');
  console.log(`  ${caseName.padEnd(20)} ${method.padEnd(6)} -> ${r.status} ${r.kind}${err ? ' :: ' + err.replace(/\s+/g, ' ').slice(0, 70) : ''}`);
  return r;
}

/* Refresh the marker in a proven body so a replay never collides with the record it came from. */
function remark(body, mark) {
  const out = Array.isArray(body) ? body.map((x) => remark(x, mark)) : { ...body };
  if (Array.isArray(body)) return out;
  for (const [k, v] of Object.entries(out)) {
    if (typeof v === 'string' && /ZV\d+/.test(v)) out[k] = v.replace(/ZV\d+/g, mark.slice(0, v.match(/ZV\d+/)[0].length));
  }
  return out;
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  for (const t of targets) {
    /*
     * `create-empty` is a POST {} — it creates nothing anywhere, so it can be recorded even on the
     * resources this tool must never create in. Do it first and standalone; if it was the only gap,
     * the resource is finished without a record ever being made.
     */
    if (t.missing.includes('create-empty')) {
      await probe(page, t.resource, 'create-empty', 'POST', t.url.startsWith('/wm/') ? t.url : `/wm/${t.resource}`, {},
        'An empty body creates nothing; it records which fields the SERVER enforces.');
      t.missing = t.missing.filter((c) => c !== 'create-empty');
      if (!t.missing.length) { console.log(`  ${t.resource}: complete — create-empty was the only gap`); continue; }
    }
    if (t.skip) { console.log(`\n${t.resource}: skipped — ${t.skip}`); continue; }
    const mark = 'ZV' + String(Date.now() % 100000);
    const body = remark(t.body, mark);
    const coll = t.url.startsWith('/wm/') ? t.url : `/wm/${t.resource}`;
    console.log(`\n${t.resource} — replaying the proven body against ${coll}`);

    const created = await probe(page, t.resource, 'create-valid-replay', 'POST', coll, body,
      'The exact body that already worked for this resource, with a fresh marker. Nothing derived.');
    if (!(created.status >= 200 && created.status < 300)) { console.log('  create refused on replay — leaving the rest unrecorded'); continue; }

    if (t.missing.includes('create-duplicate')) {
      const dup = await probe(page, t.resource, 'create-duplicate', 'POST', coll, body, 'Uniqueness contract at the API layer.');
      if (dup.status >= 200 && dup.status < 300) {
        const scan = await call(page, 'GET', `${coll}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`);
        const rows = (Array.isArray(scan.body?.data) ? scan.body.data : []).filter((x) => JSON.stringify(x).includes(mark));
        if (rows.length > 1) await probe(page, t.resource, 'cleanup-duplicate', 'DELETE', `${coll}/${encodeURIComponent(rows.pop().resourceId)}`, undefined,
          'This resource accepted a duplicate; the extra record is removed immediately.');
      }
    }
    if (t.missing.includes('create-empty')) await probe(page, t.resource, 'create-empty', 'POST', coll, {}, 'Which fields the SERVER enforces.');

    /* Address the record however it can be addressed — the id is often not in the create response. */
    let id = created.body?.data?.resourceId || (Array.isArray(created.body?.data) ? created.body.data[0]?.resourceId : null);
    if (!id) {
      const scan = await call(page, 'GET', `${coll}?query=[]&offset=0&limit=400&siteId=SG&subsites=----`);
      id = (Array.isArray(scan.body?.data) ? scan.body.data : []).find((x) => JSON.stringify(x).includes(mark))?.resourceId;
      if (id) console.log(`  create carried no id; recovered ${id} from the collection`);
    }
    if (!id) { console.log('  ! cannot address the replayed record — scan with cleanup-marks.mjs'); continue; }

    await probe(page, t.resource, 'delete-valid', 'DELETE', `${coll}/${encodeURIComponent(id)}`);
    const gone = await probe(page, t.resource, 'confirm-gone', 'GET', `${coll}/${encodeURIComponent(id)}`, undefined, 'MUST be RECORD-MISSING.');
    console.log(`  VERDICT: ${gone.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + gone.kind + ') — the record may still exist'}`);
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
