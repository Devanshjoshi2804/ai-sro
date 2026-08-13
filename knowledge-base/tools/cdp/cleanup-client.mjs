/* Reverse-order teardown of the 4-resource Clients create cascade. */
import { withPage, call } from './api.mjs';
const cid = process.argv[2] || 'ZVCL1';
console.log(JSON.stringify(await withPage(async (p) => {
  const out = {};
  const cw = await call(p, 'GET', `/wm/clientWarehouse?query=[]&offset=0&limit=300&siteId=SG&subsites=----`);
  const pc = await call(p, 'GET', `/wm/packingConfigurations?query=[]&offset=0&limit=300&siteId=SG&subsites=----`);
  const cl = await call(p, 'GET', `/wm/clients/${encodeURIComponent(cid)}`);
  const addrId = cl.data?.addressId;
  const pcHit = (pc.data || []).find(x => x.clientId === cid);
  const cwHit = (cw.data || []).find(x => x.clientId === cid);
  if (pcHit) out.packingConfigurations = (await call(p, 'DELETE', `/wm/packingConfigurations/${encodeURIComponent(pcHit.resourceId)}`)).status;
  if (cwHit) out.clientWarehouse = (await call(p, 'DELETE', `/wm/clientWarehouse/${encodeURIComponent(cwHit.resourceId)}`)).status;
  out.clients = (await call(p, 'DELETE', `/wm/clients/${encodeURIComponent(cid)}`)).status;
  if (addrId) out.addresses = (await call(p, 'DELETE', `/wm/addresses/${encodeURIComponent(addrId)}`)).status;
  out.clientGone = (await call(p, 'GET', `/wm/clients/${encodeURIComponent(cid)}`)).kind;
  if (addrId) out.addressGone = (await call(p, 'GET', `/wm/addresses/${encodeURIComponent(addrId)}`)).kind;
  return out;
}), null, 1));
