import { withPage, call } from './api.mjs';
console.log(JSON.stringify(await withPage(async (p) => {
  const out = {};
  for (const [c, q] of [['devices','?query=[]&offset=0&limit=600&siteId=SG&subsites=----'],
                        ['carrierCrossReferences','?query=[]&offset=0&limit=400&siteId=SG&subsites=----'],
                        ['addresses','?query=[]&offset=0&limit=500&siteId=SG&subsites=----']]) {
    const r = await call(p, 'GET', `/wm/${c}${q}`);
    out[c] = (r.data || []).filter(x => /ZV[A-Z]?\d|ZV Cap/.test(JSON.stringify(x)))
      .map(x => ({ id: x.resourceId, name: x.deviceCode || x.addressName || x.carrier }));
  }
  return out;
}), null, 1));
