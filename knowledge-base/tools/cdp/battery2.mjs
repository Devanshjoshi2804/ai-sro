/*
 * battery2.mjs — battery for resources that need prerequisites or leave dependents behind.
 *
 * battery.mjs handles standalone master data. The resources here cannot be exercised in
 * isolation: a supplier needs an address to point at, a clientWarehouse row needs a client to
 * belong to, and creating a client through the API leaves three dependent rows that must be torn
 * down in reverse order. Each fixture therefore declares:
 *
 *   setup(page)      -> ctx   create prerequisites, return whatever make() needs
 *   make(stamp, ctx) -> body  the create payload, built from real captured UI requests
 *   teardown(page,ctx)        remove prerequisites, and any dependents the create spawned
 *
 * Payload templates come from index/write-endpoints.json, which now stores bodies captured from
 * the real UI rather than prose. Fields that vary per run are overridden here.
 *
 *   node tools/cdp/battery2.mjs <resource>
 *   node tools/cdp/battery2.mjs all
 */
import fs from 'node:fs';
import { connect, probe, summarize, exchange } from './http-record.mjs';

const LEDGER = JSON.parse(fs.readFileSync('knowlegde_graph/blue-yonder-sce/index/write-endpoints.json', 'utf8'));
const tmpl = (resource) => {
  const e = LEDGER.find((x) => x.method === 'POST' && x.resource === resource);
  return e && e.payload ? JSON.parse(JSON.stringify(e.payload)) : {};
};

/* Raw call helper for setup/teardown steps, which are plumbing and not themselves probes. */
const call = async (page, method, url, body) => exchange(page, method, url, body);

const firstOf = async (page, url, pick) => {
  const r = await call(page, 'GET', url);
  const rows = r.body?.data;
  return Array.isArray(rows) && rows.length ? pick(rows[0]) : null;
};

const newAddress = async (page, name, clientId) => {
  const body = { ...tmpl('addresses'), addressName: name, clientId: clientId || '----', addressType: 'CLI' };
  const r = await call(page, 'POST', '/wm/addresses', body);
  return r.body?.data?.addressId || r.body?.data?.resourceId || null;
};

const del = (page, url) => call(page, 'DELETE', url);

export const RESOURCES = {
  addresses: {
    coll: '/wm/addresses', mut: 'addressLine1',
    make: (s) => ({ ...tmpl('addresses'), addressName: 'ZV ' + s, clientId: '----', addressType: 'CLI' }),
    // A duplicate address name is NOT expected to conflict; addresses are keyed by a server id.
    dupNote: 'Addresses use a server-assigned id, so a repeated name is a second valid record, not a conflict.',
  },

  suppliers: {
    coll: '/wm/suppliers', mut: 'consignmentType',
    setup: async (page) => ({ addressId: await newAddress(page, 'ZV Batt Sup Addr') }),
    make: (s, i, ctx) => ({ ...tmpl('suppliers'), supplierNumber: s, clientId: '----', addressId: ctx.addressId }),
    teardown: async (page, ctx) => { if (ctx.addressId) await del(page, `/wm/addresses/${ctx.addressId}`); },
  },

  customers: {
    coll: '/wm/customers', mut: 'departmentNumber',
    setup: async (page) => ({
      addressId: await newAddress(page, 'ZV Batt Cust Addr'),
      customerType: await firstOf(page, '/wm/customerTypes?query=[]&offset=0&limit=1&siteId=SG&subsites=----', (r) => r.customerType || r.resourceId),
    }),
    make: (s, i, ctx) => ({ ...tmpl('customers'), customerNumber: s, clientId: '----', addressId: ctx.addressId, customerType: ctx.customerType }),
    teardown: async (page, ctx) => { if (ctx.addressId) await del(page, `/wm/addresses/${ctx.addressId}`); },
  },

  clients: {
    coll: '/wm/clients', mut: 'bolaPrefix',
    setup: async (page) => ({ addressId: await newAddress(page, 'ZV Batt Client Addr') }),
    make: (s, i, ctx) => ({ ...tmpl('clients'), clientId: s, addressId: ctx.addressId }),
    // A client created through the API does not spawn dependents the way the UI cascade does,
    // but sweep them defensively in case the server adds them.
    teardownCreated: async (page, id) => {
      for (const coll of ['packingConfigurations', 'clientWarehouse']) {
        const r = await call(page, 'GET', `/wm/${coll}?query=[]&offset=0&limit=300&siteId=SG&subsites=----`);
        const hit = (r.body?.data || []).find((x) => x.clientId === id);
        if (hit) await del(page, `/wm/${coll}/${encodeURIComponent(hit.resourceId)}`);
      }
    },
    teardown: async (page, ctx) => { if (ctx.addressId) await del(page, `/wm/addresses/${ctx.addressId}`); },
  },

  clientWarehouse: {
    coll: '/wm/clientWarehouse', mut: 'printVisibilityMessage',
    setup: async (page) => {
      const addressId = await newAddress(page, 'ZV Batt CW Addr');
      const clientId = 'ZVCW' + String(Date.now() % 1000);
      await call(page, 'POST', '/wm/clients', { ...tmpl('clients'), clientId, addressId });
      return { addressId, clientId };
    },
    make: (s, i, ctx) => ({ ...tmpl('clientWarehouse'), clientId: ctx.clientId, warehouseId: 'SG', displayClientId: ctx.clientId }),
    teardown: async (page, ctx) => {
      if (ctx.clientId) await del(page, `/wm/clients/${encodeURIComponent(ctx.clientId)}`);
      if (ctx.addressId) await del(page, `/wm/addresses/${ctx.addressId}`);
    },
  },

  packingConfigurations: {
    coll: '/wm/packingConfigurations', mut: null,
    setup: async (page) => {
      const addressId = await newAddress(page, 'ZV Batt PC Addr');
      const clientId = 'ZVPC' + String(Date.now() % 1000);
      await call(page, 'POST', '/wm/clients', { ...tmpl('clients'), clientId, addressId });
      return { addressId, clientId };
    },
    make: (s, i, ctx) => ({ ...tmpl('packingConfigurations'), clientId: ctx.clientId, warehouseId: 'SG' }),
    teardown: async (page, ctx) => {
      if (ctx.clientId) await del(page, `/wm/clients/${encodeURIComponent(ctx.clientId)}`);
      if (ctx.addressId) await del(page, `/wm/addresses/${ctx.addressId}`);
    },
  },

  devices: {
    coll: '/wm/devices', mut: 'deviceName',
    make: (s) => ({ ...tmpl('devices'), deviceCode: s, deviceName: 'ZV BATT', deviceClass: 'W', warehouseId: 'SG' }),
  },

  printers: {
    coll: '/wm/printers', mut: 'printerName',
    // printerAddress maxLength is 10; the label "Printer Name" maps to printerAddress.
    make: (s) => ({ ...tmpl('printers'), printerAddress: s.slice(0, 10), printerName: 'ZVBATT', warehouseId: 'SG' }),
  },

  carrierProNumbers: {
    coll: '/wm/carrierProNumbers', mut: 'prefix',
    setup: async (page) => ({
      addressId: await firstOf(page, '/wm/addresses?query=[]&offset=0&limit=1&siteId=SG&subsites=----', (r) => r.addressId || r.resourceId),
      carrier: await firstOf(page, '/wm/carriers?query=[]&offset=0&limit=1&siteId=SG&subsites=----', (r) => r.carrierCode || String(r.resourceId).split('*!')[0]),
    }),
    make: (s, i, ctx) => ({ addressId: ctx.addressId, carrier: ctx.carrier, poolPointAddressId: s,
      checkDigitMethod: '', format: '', numberLength: '10', nextValue: '', prefix: '', separator: '' }),
    // Prerequisites here are pre-existing real records, so nothing to tear down.
  },

  carrierCrossReferences: {
    coll: '/wm/carrierCrossReferences', mut: 'serviceTitle',
    setup: async (page) => ({
      carrier: await firstOf(page, '/wm/carriers?query=[]&offset=0&limit=1&siteId=SG&subsites=----', (r) => r.carrierCode || String(r.resourceId).split('*!')[0]),
    }),
    make: (s, i, ctx) => ({ ...tmpl('carrierCrossReferences'), carrier: ctx.carrier, serviceLevel: s.slice(0, 6), destinationName: 'TANDATA',
      crossReference: `${ctx.carrier}|${s.slice(0, 6)} - TANDATA` }),
  },
};

const stamp = (i) => 'ZV' + String(Date.now() % 100000).padStart(5, '0') + (i || '');

export async function runResource(page, name, idx = 0) {
  const r = RESOURCES[name];
  if (!r) throw new Error('unknown resource ' + name);
  const results = [];
  const P = (o) => probe(page, { resource: name, ...o }).then((rec) => { results.push(rec); return rec; });

  let ctx = {};
  if (r.setup) ctx = await r.setup(page);

  try {
    await P({ caseName: 'route-exists', method: 'GET', urlPath: `${r.coll}?query=[]&offset=0&limit=1&siteId=SG&subsites=----`,
      notes: 'ROUTE-MISSING here would mean the endpoint does not exist at all.' });
    await P({ caseName: 'read-collection', method: 'GET', urlPath: `${r.coll}?query=[]&offset=0&limit=2&siteId=SG&subsites=----`,
      notes: 'Compare data.length against limit=2; several collections ignore limit entirely.' });
    await P({ caseName: 'read-missing', method: 'GET', urlPath: `${r.coll}/ZZDOESNOTEXIST0001`,
      notes: 'A 400 here means the id shape is malformed for this resource; 404 RECORD-MISSING means well-formed but absent.' });

    const code = stamp(idx);
    const body = r.make(code, idx, ctx);
    const created = await P({ caseName: 'create-valid', method: 'POST', urlPath: r.coll, body,
      notes: 'Payload template captured from the real UI Add form.' });
    const id = created.response?.body?.data?.resourceId ?? created.response?.body?.resourceId ?? null;

    const dup = await P({ caseName: 'create-duplicate', method: 'POST', urlPath: r.coll, body,
      notes: r.dupNote || 'Uniqueness contract at the API layer, independent of any client-side gate.' });
    /*
     * Some resources have no natural key (addresses are keyed by a server-assigned id), so the
     * "duplicate" probe SUCCEEDS and creates a second real record. That record is not the one
     * tracked for teardown below, so it must be removed here or the probe silently leaks.
     */
    const dupId = dup.response?.body?.data?.resourceId ?? dup.response?.body?.resourceId ?? null;
    if (dup.response?.status === 201 && dupId) {
      await del(page, `${r.coll}/${encodeURIComponent(dupId)}`);
    }
    await P({ caseName: 'create-empty', method: 'POST', urlPath: r.coll, body: {},
      notes: 'Which fields the SERVER enforces, as opposed to the form.' });

    if (id) {
      const idPath = `${r.coll}/${encodeURIComponent(id)}`;
      const read = await P({ caseName: 'read-created', method: 'GET', urlPath: idPath,
        notes: 'A create is never proven by its own response.' });
      const rec = read.response?.body?.data;
      if (rec && r.mut) {
        const put = { ...rec, [r.mut]: 'ZVUPD' };
        delete put.self_uri;
        await P({ caseName: 'update-valid', method: 'PUT', urlPath: idPath, body: put });
        const after = await P({ caseName: 'read-updated', method: 'GET', urlPath: idPath,
          notes: 'A 200 on PUT does not mean the field persisted; join-view resources drop columns they do not own.' });
        const got = after.response?.body?.data?.[r.mut];
        after.notes += ` | persisted=${got === 'ZVUPD'}`;
      }
      await P({ caseName: 'delete-valid', method: 'DELETE', urlPath: idPath });
      await P({ caseName: 'delete-again', method: 'DELETE', urlPath: idPath, notes: 'Idempotency of DELETE.' });
      await P({ caseName: 'confirm-gone', method: 'GET', urlPath: idPath,
        notes: 'MUST be RECORD-MISSING; ROUTE-MISSING would mean the cycle proved nothing.' });
      if (r.teardownCreated) await r.teardownCreated(page, id);
    }
  } finally {
    if (r.teardown) await r.teardown(page, ctx);
  }
  return results;
}

const arg = process.argv[2];
const isEntry = process.argv[1] && process.argv[1].endsWith('battery2.mjs');
if (isEntry && arg) {
  const names = arg === 'all' ? Object.keys(RESOURCES) : [arg];
  const { browser, page } = await connect();
  const summary = {};
  for (let i = 0; i < names.length; i++) {
    const n = names[i];
    process.stderr.write(`\n### ${n}\n`);
    try {
      const res = await runResource(page, n, i);
      res.forEach((rec) => process.stderr.write('   ' + summarize(rec) + '\n'));
      summary[n] = res.map((rec) => `${rec.case}=${rec.response.status ?? 'ERR'}${rec.response.kind && rec.response.kind !== 'OK' ? '/' + rec.response.kind : ''}`);
    } catch (e) {
      summary[n] = ['ERROR: ' + String(e).slice(0, 140)];
      process.stderr.write('   ERROR ' + String(e).slice(0, 180) + '\n');
    }
  }
  console.log(JSON.stringify(summary, null, 1));
  await browser.close();
}
