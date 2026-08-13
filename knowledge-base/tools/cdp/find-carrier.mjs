import { withPage, call } from './api.mjs';
console.log(JSON.stringify(await withPage(async (p) => {
  const hits = [];
  for (let off = 0; off < 2000; off += 500) {
    const r = await call(p, 'GET', `/wm/carriers?query=[]&offset=${off}&limit=500&siteId=SG&subsites=----`);
    const rows = r.data || [];
    if (!rows.length) break;
    for (const x of rows) if (/^ZV/.test(String(x.carrierCode || ''))) hits.push({ id: x.resourceId, code: x.carrierCode, name: x.carrierName });
  }
  const out = { hits, deleted: [] };
  for (const h of hits) out.deleted.push(`${h.id}:${(await call(p, 'DELETE', `/wm/carriers/${encodeURIComponent(h.id)}`)).status}`);
  return out;
}), null, 1));
