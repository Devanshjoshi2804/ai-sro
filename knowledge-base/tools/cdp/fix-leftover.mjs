import { withPage, call } from './api.mjs';
console.log(JSON.stringify(await withPage(async (p) => {
  const out = {};
  const id = '----*!ZV070902';
  const r = await call(p, 'GET', `/wm/customers/${encodeURIComponent(id)}`);
  if (r.kind === 'OK') {
    const addrId = r.data?.addressId;
    out.customer = (await call(p, 'DELETE', `/wm/customers/${encodeURIComponent(id)}`)).status;
    if (addrId) out.address = (await call(p, 'DELETE', `/wm/addresses/${encodeURIComponent(addrId)}`)).status;
  } else out.customer = 'already gone: ' + r.kind;
  out.confirm = (await call(p, 'GET', `/wm/customers/${encodeURIComponent(id)}`)).kind;
  // any other ZV customers or stray addresses
  const cs = await call(p, 'GET', '/wm/customers?query=[]&offset=0&limit=400&siteId=SG&subsites=----');
  out.strayCustomers = (cs.data || []).filter(x => /ZV\d/.test(JSON.stringify(x))).map(x => x.resourceId);
  const ad = await call(p, 'GET', '/wm/addresses?query=[]&offset=0&limit=500&siteId=SG&subsites=----');
  out.strayAddresses = (ad.data || []).filter(x => /ZV /.test(String(x.addressName || ''))).map(x => ({ id: x.addressId, n: x.addressName }));
  return out;
}), null, 1));
