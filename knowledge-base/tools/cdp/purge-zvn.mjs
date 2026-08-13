import { withPage, call } from './api.mjs';
console.log(JSON.stringify(await withPage(async (p) => {
  const out = { deleted: [], remaining: [] };
  const r = await call(p, 'GET', '/wm/customerTypes?query=[]&offset=0&limit=500&siteId=SG&subsites=----');
  for (const row of (r.data || [])) {
    if (/^ZV/.test(String(row.customerType || row.resourceId || ''))) {
      const st = (await call(p, 'DELETE', `/wm/customerTypes/${encodeURIComponent(row.resourceId)}`)).status;
      out.deleted.push(`${row.resourceId}:${st}`);
    }
  }
  const after = await call(p, 'GET', '/wm/customerTypes?query=[]&offset=0&limit=500&siteId=SG&subsites=----');
  out.remaining = (after.data || []).filter(x => /^ZV/.test(String(x.customerType || ''))).map(x => x.resourceId);
  return out;
}), null, 1));
