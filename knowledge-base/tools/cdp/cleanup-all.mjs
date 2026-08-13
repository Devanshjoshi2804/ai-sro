/* Tear down everything the capture runs created, cascades in reverse dependency order. */
import { withPage, call, sweep } from './api.mjs';
const del = async (p, path) => (await call(p, 'DELETE', path)).status;
console.log(JSON.stringify(await withPage(async (p) => {
  const out = {};
  // clients cascade: packingConfigurations -> clientWarehouse -> clients -> addresses
  const cl = await call(p, 'GET', '/wm/clients/ZVCL1');
  if (cl.kind === 'OK') {
    const addrId = cl.data?.addressId;
    for (const [coll, key] of [['packingConfigurations', 'clientId'], ['clientWarehouse', 'clientId']]) {
      const r = await call(p, 'GET', `/wm/${coll}?query=[]&offset=0&limit=300&siteId=SG&subsites=----`);
      const hit = (r.data || []).find(x => x[key] === 'ZVCL1');
      if (hit) out[coll] = await del(p, `/wm/${coll}/${encodeURIComponent(hit.resourceId)}`);
    }
    out.clients = await del(p, '/wm/clients/ZVCL1');
    if (addrId) out.clients_address = await del(p, `/wm/addresses/${encodeURIComponent(addrId)}`);
  }
  // supplier + customer each own an address created by their cascade
  for (const [coll, id] of [['suppliers', '----*!ZVS1'], ['customers', '----*!ZVCU1']]) {
    const r = await call(p, 'GET', `/wm/${coll}/${encodeURIComponent(id)}`);
    if (r.kind !== 'OK') continue;
    const addrId = r.data?.addressId;
    out[coll] = await del(p, `/wm/${coll}/${encodeURIComponent(id)}`);
    if (addrId) out[coll + '_address'] = await del(p, `/wm/addresses/${encodeURIComponent(addrId)}`);
  }
  out.printers = await del(p, '/wm/printers/' + encodeURIComponent('ZVP1*!SG'));
  // voice device and cross-reference are not in the sweep's collection list
  const dv = await call(p, 'GET', '/wm/devices?query=[]&offset=0&limit=600&siteId=SG&subsites=----');
  for (const row of (dv.data || [])) if (/^ZV/.test(String(row.deviceCode || ''))) out['device_' + row.deviceCode] = await del(p, `/wm/devices/${encodeURIComponent(row.resourceId)}`);
  const cx = await call(p, 'GET', '/wm/carrierCrossReferences?query=[]&offset=0&limit=400&siteId=SG&subsites=----');
  for (const row of (cx.data || [])) if (/ZV/.test(JSON.stringify(row))) out['ccr_' + row.resourceId] = await del(p, `/wm/carrierCrossReferences/${encodeURIComponent(row.resourceId)}`);
  out.remaining = await sweep(p);
  return out;
}), null, 1));
