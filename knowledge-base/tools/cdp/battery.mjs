/*
 * battery.mjs — exercise every endpoint across success AND error paths, recording full exchanges.
 *
 * The old ledger recorded only happy paths, and even those as prose. An executor needs to know
 * what failure looks like: which status code, which body shape, whether a cascade partially
 * applied. So each resource runs a fixed battery of probes, and every probe's complete exchange
 * is written to knowlegde_graph/blue-yonder-sce/http/exchanges/<resource>.jsonl.
 *
 * Cases, and what each one is actually testing:
 *   route-exists        GET collection            — distinguishes a dead route from an empty one
 *   read-collection     GET ?limit=2              — also reveals whether limit is honoured at all
 *   read-missing        GET /<nonexistent id>     — establishes the RECORD-MISSING body shape
 *   create-valid        POST <captured payload>   — the payload the real UI sends
 *   create-duplicate    POST the same payload     — uniqueness behaviour: 409 vs 422 vs client-side
 *   create-empty        POST {}                   — which fields the server itself demands
 *   read-created        GET /<new id>             — a create is not proven by its own response
 *   update-valid        PUT mutated record        — and re-read, because 200 does not mean applied
 *   update-missing      PUT to a nonexistent id   — error shape for a bad target
 *   delete-valid        DELETE /<new id>          — teardown
 *   delete-again        DELETE the same id twice  — idempotency behaviour
 *   confirm-gone        GET /<new id>             — must be RECORD-MISSING, never ROUTE-MISSING
 *
 *   node tools/cdp/battery.mjs <resource>
 *   node tools/cdp/battery.mjs all
 */
import fs from 'node:fs';
import { connect, probe, summarize } from './http-record.mjs';

const LEDGER = 'knowlegde_graph/blue-yonder-sce/index/write-endpoints.json';

/*
 * Per-resource knowledge the battery needs: how to build a unique throwaway record, which field
 * is safe to mutate, and how to derive the id. Payload templates come from the ledger, which now
 * carries bodies captured from the real UI.
 */
export const RESOURCES = {
  clientGroups: { coll: '/wm/clientGroups', mut: 'clientGroupDescription',
    make: (s) => ({ clientGroup: s, clientGroupDescription: s + ' d', adjustmentThresholdCost: 0, adjustmentThresholdUnit: 0, self_uri: '', clients_uri: '' }) },
  customerTypes: { coll: '/wm/customerTypes', mut: 'longDescription',
    // csttyp truncates at 4 chars, so the code must stay short.
    make: (s) => ({ customerType: s.slice(0, 4), longDescription: 'ZV battery', shotDescription: '', crossDockFlag: -1, bulkPickingFlag: false, outboundDateWindowUnit: 'MIN' }) },
  transportModes: { coll: '/wm/transportModes', mut: 'transportModeDescription', noSiteScope: true,
    make: (s) => ({ transportMode: s.slice(0, 3), transportModeDescription: 'ZV battery', directFlag: 0, smallPackageFlag: 0, palletBuildConsolidationBy: '', warehouseId: '' }) },
  carriers: { coll: '/wm/carriers', mut: 'carrierName',
    make: (s) => ({ carrierCode: s, carrierName: 'ZV battery' }) },
  businessUnits: { coll: '/wm/businessUnits', mut: 'businessUnitDescription',
    make: (s) => ({ businessUnit: s, businessUnitDescription: 'ZV battery', warehouseId: 'SG', areaCount: 0, itemCount: 0 }) },
  locationTypes: { coll: '/wm/locationTypes', mut: 'longDescription',
    make: (s) => ({ locationType: s, locationTypeCategory: 'STORAGE', longDescription: 'ZV battery' }) },
  levelTypes: { coll: '/wm/levelTypes', mut: 'levelTypeDescription',
    make: (s) => ({ warehouseId: 'SG', levelTypeId: '', levelTypeName: s, levelTypeDescription: 'ZV battery', totalLevelUnits: 1, horizontalAlignmentFlag: false, verticalAlignmentFlag: false, displayPendingIndicatorFlag: false, maxWeight: 0, location: '', usedFlag: false, self_uri: '', maxWeightValidationFlag: false }) },
  equipmentTypes: { coll: '/wm/equipmentTypes', mut: 'longDescription',
    // voiceCode must be numeric, 2 chars, and globally unique across equipment types.
    make: (s, i) => ({ vehicleTypeId: s, longDescription: 'ZV battery', voiceCode: String(11 + (i % 80)), vehicleLimit: '1', location: 0, captureEquipment: false, useWorkAreaMove: false }) },
  // Dead route, kept in the battery precisely so the evidence of its absence is recorded.
  transportEquipmentTypes: { coll: '/wm/transportEquipmentTypes', mut: 'longDescription', expectDead: true,
    make: (s) => ({ code: s, description: 'ZV battery' }) },
};

const stamp = (i) => 'ZV' + String(Date.now() % 100000).padStart(5, '0') + (i || '');
const q = (r, extra = '') => (r.noSiteScope ? `?query=[]&offset=0${extra}` : `?query=[]&offset=0&siteId=SG&subsites=----${extra}`);

export async function runResource(page, name, idx = 0) {
  const r = RESOURCES[name];
  if (!r) throw new Error('unknown resource ' + name);
  const results = [];
  const P = (o) => probe(page, { resource: name, ...o }).then((rec) => { results.push(rec); return rec; });

  await P({ caseName: 'route-exists', method: 'GET', urlPath: r.coll + q(r, '&limit=1'),
    notes: 'ROUTE-MISSING here means the endpoint does not exist at all.' });
  await P({ caseName: 'read-collection', method: 'GET', urlPath: r.coll + q(r, '&limit=2'),
    notes: 'limit is not honoured by every collection; compare data.length against limit=2.' });
  await P({ caseName: 'read-missing', method: 'GET', urlPath: `${r.coll}/ZZDOESNOTEXIST0001`,
    notes: 'Establishes the RECORD-MISSING body shape for this resource.' });

  const code = stamp(idx);
  const body = r.make(code, idx);
  const created = await P({ caseName: 'create-valid', method: 'POST', urlPath: r.coll, body,
    notes: 'Payload as captured from the real UI Add form where one was obtainable.' });

  const id = created.response?.body?.data?.resourceId ?? created.response?.body?.resourceId ?? null;

  await P({ caseName: 'create-duplicate', method: 'POST', urlPath: r.coll, body,
    notes: 'Uniqueness behaviour differs per resource: 409, 422, or a purely client-side gate.' });
  await P({ caseName: 'create-empty', method: 'POST', urlPath: r.coll, body: {},
    notes: 'Reveals which fields the SERVER enforces, as opposed to the form.' });

  if (id) {
    const idPath = `${r.coll}/${encodeURIComponent(id)}`;
    const read = await P({ caseName: 'read-created', method: 'GET', urlPath: idPath,
      notes: 'A create is never proven by its own response.' });
    const rec = read.response?.body?.data;
    if (rec && r.mut) {
      const put = { ...rec, [r.mut]: 'ZV updated' };
      delete put.self_uri;
      await P({ caseName: 'update-valid', method: 'PUT', urlPath: idPath, body: put });
      const after = await P({ caseName: 'read-updated', method: 'GET', urlPath: idPath,
        notes: 'A 200 on PUT does not mean the field persisted; some are silently dropped.' });
      const got = after.response?.body?.data?.[r.mut];
      after.notes += ` | persisted=${got === 'ZV updated'}`;
    }
    await P({ caseName: 'update-missing', method: 'PUT', urlPath: `${r.coll}/ZZDOESNOTEXIST0001`, body: body,
      notes: 'Error shape when the target does not exist.' });
    await P({ caseName: 'delete-valid', method: 'DELETE', urlPath: idPath });
    await P({ caseName: 'delete-again', method: 'DELETE', urlPath: idPath,
      notes: 'Is DELETE idempotent on this deployment?' });
    await P({ caseName: 'confirm-gone', method: 'GET', urlPath: idPath,
      notes: 'MUST be RECORD-MISSING. ROUTE-MISSING here would mean the whole cycle proved nothing.' });
  }
  return results;
}

const arg = process.argv[2];
if (arg) {
  const names = arg === 'all' ? Object.keys(RESOURCES) : [arg];
  const { browser, page } = await connect();
  const summary = {};
  for (let i = 0; i < names.length; i++) {
    const n = names[i];
    process.stderr.write(`\n### ${n}\n`);
    try {
      const res = await runResource(page, n, i);
      res.forEach((rec) => process.stderr.write('   ' + summarize(rec) + '\n'));
      summary[n] = res.map((rec) => `${rec.case}=${rec.response.status ?? 'ERR'}/${rec.response.kind ?? ''}`);
    } catch (e) {
      summary[n] = ['ERROR: ' + String(e).slice(0, 120)];
      process.stderr.write('   ERROR ' + String(e).slice(0, 160) + '\n');
    }
  }
  fs.mkdirSync('knowlegde_graph/blue-yonder-sce/http', { recursive: true });
  console.log(JSON.stringify(summary, null, 1));
  await browser.close();
}
