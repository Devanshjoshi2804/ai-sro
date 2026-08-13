/* The Carrier PRO Number Add form cannot be made valid (its lookups never bind), so the create
 * payload is proven directly against the API instead, end to end. */
import { withPage, call } from './api.mjs';
console.log(JSON.stringify(await withPage(async (p) => {
  const out = {};
  const addr = await call(p, 'GET', '/wm/addresses?query=[]&offset=0&limit=1&siteId=SG&subsites=----');
  const car = await call(p, 'GET', '/wm/carriers?query=[]&offset=0&limit=1&siteId=SG&subsites=----');
  const addressId = addr.data?.[0]?.addressId || addr.data?.[0]?.resourceId;
  const carrier = car.data?.[0]?.carrierCode || String(car.data?.[0]?.resourceId || '').split('*!')[0];
  out.using = { addressId, carrier };
  const body = { addressId, carrier, poolPointAddressId: 'ZVPP1',
    checkDigitMethod: '', format: '', numberLength: '10', nextValue: '', prefix: '', separator: '' };
  const c = await call(p, 'POST', '/wm/carrierProNumbers', body);
  out.create = c.status + '/' + c.kind;
  if (c.kind !== 'OK') { out.err = c.text.slice(0, 200); return out; }
  const id = c.data?.resourceId;
  out.resourceId = id;
  const g1 = await call(p, 'GET', `/wm/carrierProNumbers/${encodeURIComponent(id)}`);
  out.read = g1.status + '/' + g1.kind;
  const put = { ...g1.data, prefix: 'ZVX' }; delete put.self_uri; delete put.carrierInfo;
  const pu = await call(p, 'PUT', `/wm/carrierProNumbers/${encodeURIComponent(id)}`, put);
  const g2 = await call(p, 'GET', `/wm/carrierProNumbers/${encodeURIComponent(id)}`);
  out.put = pu.status + ' persisted:' + (g2.data?.prefix === 'ZVX');
  const d = await call(p, 'DELETE', `/wm/carrierProNumbers/${encodeURIComponent(id)}`);
  out.del = d.status;
  const g3 = await call(p, 'GET', `/wm/carrierProNumbers/${encodeURIComponent(id)}`);
  out.afterDelete = g3.status + '/' + g3.kind;
  out.verdict = g3.kind === 'RECORD-MISSING' ? 'PASS' : g3.kind;
  out.body = body;
  return out;
}), null, 1));
