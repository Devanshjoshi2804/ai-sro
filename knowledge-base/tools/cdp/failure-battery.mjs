/*
 * failure-battery.mjs — close the failure-mode gap, and refuse to close it where that would be reckless.
 *
 * Ten resources block the failure_modes dimension on 42 screens. They need three recorded cases:
 * `create-empty`, `create-duplicate`, `confirm-gone`. They are not all equal:
 *
 *   safe        the record is a small config row we have already created and deleted cleanly
 *   empty-only  a POST {} is harmless anywhere — it creates nothing and reveals what the server
 *               enforces — but a duplicate or a delete cycle on this resource is not acceptable
 *   refused     stated with a reason instead of attempted
 *
 * `warehouses` is the site record this whole session runs inside. `locations` holds 61,912 live rows
 * and creates through a wizard. `buildings` is the parent of every location. `workOperations` cannot
 * be deleted at all — its DELETE answers 200 and does nothing — so creating a duplicate there means
 * leaving a second permanent row behind. For those four, `create-empty` is recorded and the rest is
 * documented as refused, which is a better artifact than a number that was bought with damage.
 *
 *   node tools/cdp/failure-battery.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';

const KG = 'knowlegde_graph/blue-yonder-sce';
const HTTP_DIR = `${KG}/http`;
const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/data/WM';
const PORTAL = 'https://bf56-kms-wms-web-np2.jdadelivers.com/portal?siteId=SG&subsite=----#wm.config/wm.config.warehouse.warehouse////';
const mark = () => 'ZV' + String(Date.now() % 100000);

const REFUSED = {
  warehouses: 'This is the site record the session itself runs inside. A duplicate or a delete cycle here would break every other capture.',
  locations: '61,912 live rows, and creates go through a multi-step wizard whose payload depends on the location type. Not something to duplicate blind.',
  buildings: 'Parent of every location and aisle in the site. A throwaway building risks orphaning children if the delete half fails.',
  workOperations: 'Its DELETE answers 200 and does not delete — proven. A duplicate create here leaves a second permanent row that nobody can remove.',
};

/* Resources whose full cycle is safe: small config rows, already created and deleted cleanly here. */
const SAFE = {
  itemClasses: { coll: '/wm/itemClasses', body: (m) => ({ itemClassName: m, longDescription: m }) },
  itemStyleAttributes: { coll: '/wm/itemStyleAttributes', body: (m) => ({ attributeColumnName: 'prtcolor', attributeCodeName: m, longDescription: m }) },
};

const EMPTY_ONLY = ['pickMethods', 'releaseRules', 'uoms', 'customers', ...Object.keys(REFUSED)];

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
  fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${resource}.jsonl`), JSON.stringify({
    ts: new Date().toISOString(), tool: 'tools/cdp/failure-battery.mjs', case: caseName,
    request: { method, url: urlPath.split('?')[0], headers: { accept: 'application/json' }, body: body ?? null },
    response: { status: r.status, body: r.body, bodyRaw: r.bodyRaw, kind: r.kind },
    notes: notes || null,
  }) + '\n');
  const err = (r.body?.errors || []).map((e) => e.userMessage).join('; ');
  console.log(`  ${resource.padEnd(22)} ${caseName.padEnd(18)} -> ${r.status} ${r.kind}${err ? ' :: ' + err.slice(0, 70) : ''}`);
  return r;
}

const browser = await chromium.connectOverCDP(process.env.CDP_URL || 'http://localhost:9222');
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
try {
  await page.goto(PORTAL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(9000);

  console.log('\ncreate-empty — harmless everywhere: it creates nothing and shows what the server enforces');
  for (const r of [...EMPTY_ONLY, ...Object.keys(SAFE)]) {
    await probe(page, r, 'create-empty', 'POST', `/wm/${r}`, {},
      'An empty body. Records which fields the SERVER enforces, as opposed to the form.');
  }

  console.log('\nfull cycle on the resources where it is safe');
  for (const [r, spec] of Object.entries(SAFE)) {
    const m = mark();
    const body = spec.body(m);
    const created = await probe(page, r, 'create-valid', 'POST', spec.coll, body, 'Throwaway record; deleted and proven gone below.');
    /*
     * These resources answer 201 with an EMPTY body — no resourceId. The id is the natural key we
     * sent, which the collection confirms, so read it back from the collection rather than guessing
     * the separator for a compound id.
     */
    let id = created.body?.data?.resourceId;
    if (!id) {
      const scan = await call(page, 'GET', `${spec.coll}?query=[]&offset=0&limit=200&siteId=SG&subsites=----`);
      const row = (Array.isArray(scan.body?.data) ? scan.body.data : []).find((x) => JSON.stringify(x).includes(m));
      id = row?.resourceId;
      console.log(`    201 carried no resourceId; recovered ${id} from the collection`);
    }
    await probe(page, r, 'create-duplicate', 'POST', spec.coll, body, 'Uniqueness contract at the API layer.');
    if (!id) { console.log(`    ! cannot address the new ${r} record — leaving it would be a leak, scan with cleanup-marks.mjs`); continue; }
    const idPath = `${spec.coll}/${encodeURIComponent(id)}`;
    await probe(page, r, 'delete-valid', 'DELETE', idPath);
    const gone = await probe(page, r, 'confirm-gone', 'GET', idPath, undefined, 'MUST be RECORD-MISSING.');
    console.log(`    ${r}: ${gone.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + gone.kind + ') — may still exist'}`);
  }

  /*
   * customers already has a proven create and delete but no `confirm-gone`, which is the only case
   * that actually proves a delete. Redo the tail of its cycle on a throwaway record.
   */
  /*
   * uoms is a read view over /wm/codes partition `uomcod`, so its duplicate contract belongs to
   * codes. Recorded under uoms because that is the resource whose coverage the case answers.
   */
  console.log('\nuoms — closing create-duplicate through the partition it actually lives in');
  const um = mark().slice(-2);
  const codeBody = { codeValue: um, columnName: 'uomcod', longDescription: 'ZV probe', shortDescription: 'ZV', sortSequence: 99, requiredFlag: 0 };
  const u1 = await probe(page, 'uoms', 'create-valid-via-codes', 'POST', '/wm/codes', codeBody,
    'uoms has no create of its own; POST /wm/uoms answers 422 Missing argument: Column (colnam).');
  if (u1.status === 201) {
    await probe(page, 'uoms', 'create-duplicate', 'POST', '/wm/codes', codeBody, 'Uniqueness contract, exercised through codes.');
    const uid = u1.body?.data?.resourceId;
    await probe(page, 'uoms', 'delete-via-codes', 'DELETE', `/wm/codes/${encodeURIComponent(uid)}`);
    const g = await probe(page, 'uoms', 'confirm-gone', 'GET', `/wm/codes/${encodeURIComponent(uid)}`, undefined, 'MUST be RECORD-MISSING.');
    console.log(`    uoms: ${g.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + g.kind + ')'}`);
  }

  console.log('\ncustomers — closing the missing confirm-gone');
  const m = mark();
  /*
   * A customer is not a standalone row: the create was refused with `Invalid argument: client_id`.
   * Take a real customer and vary only its number, the same rule that unlocked releaseRules.
   */
  const csample = await call(page, 'GET', '/wm/customers?query=[]&offset=0&limit=1&siteId=SG&subsites=----');
  const crow = Array.isArray(csample.body?.data) ? csample.body.data[0] : null;
  const cbody = crow
    ? Object.fromEntries(Object.entries(crow).filter(([k]) => k !== 'resourceId' && !k.endsWith('_uri')))
    : { customerNumber: m, customerName: m };
  if (crow) { cbody.customerNumber = m; if ('customerName' in cbody) cbody.customerName = m; }
  const cust = await probe(page, 'customers', 'create-valid', 'POST', '/wm/customers', cbody,
    'Throwaway record to record the one case customers was missing. Body modelled on a real customer with only the number varied — a flat {customerNumber, customerName} is refused with "Invalid argument: client_id".');
  /*
   * customers answers 201 with an empty body too. The first version treated a missing resourceId as
   * "create refused", printed `create refused (201)` and walked away from a record it had just
   * created — a leak found by a marker scan afterwards. Recover the id the same way as the safe
   * cycle above, and only then decide whether anything needs cleaning.
   */
  let cid = cust.body?.data?.resourceId;
  if (!cid && cust.status >= 200 && cust.status < 300) {
    const scan = await call(page, 'GET', '/wm/customers?query=[]&offset=0&limit=400&siteId=SG&subsites=----');
    cid = (Array.isArray(scan.body?.data) ? scan.body.data : []).find((x) => JSON.stringify(x).includes(m))?.resourceId;
    console.log(`    201 carried no resourceId; recovered ${cid} from the collection`);
  }
  if (cid) {
    await probe(page, 'customers', 'delete-valid', 'DELETE', `/wm/customers/${encodeURIComponent(cid)}`);
    const gone = await probe(page, 'customers', 'confirm-gone', 'GET', `/wm/customers/${encodeURIComponent(cid)}`, undefined, 'MUST be RECORD-MISSING.');
    console.log(`    customers: ${gone.kind === 'RECORD-MISSING' ? 'PASS' : 'INCONCLUSIVE (' + gone.kind + ')'}`);
  } else {
    console.log(`    create refused (${cust.status}) — confirm-gone stays unrecorded rather than faked`);
  }

  /* What is deliberately not attempted, written into the store so the gap has a reason attached. */
  for (const [r, why] of Object.entries(REFUSED)) {
    fs.appendFileSync(path.join(HTTP_DIR, 'exchanges', `${r}.jsonl`), JSON.stringify({
      ts: new Date().toISOString(), tool: 'tools/cdp/failure-battery.mjs', case: 'failure-battery-refused',
      request: null, response: null,
      notes: `create-duplicate and the delete cycle were NOT attempted on this resource. ${why}`,
    }) + '\n');
    console.log(`  refused: ${r.padEnd(16)} ${why.slice(0, 90)}`);
  }
} finally {
  await page.close().catch(() => {});
}
process.exit(0);
