import { withPage, call, lifecycle } from './api.mjs';
const [coll, matchField, matchVal, putField] = process.argv.slice(2);
console.log(JSON.stringify(await withPage(async (p) => {
  const q = `${coll}?query=[]&offset=0&limit=200&siteId=SG&subsites=----`;
  const r = await call(p, 'GET', q);
  const rows = Array.isArray(r.data) ? r.data : [];
  const hit = rows.find(x => String(x[matchField]) === matchVal);
  if (!hit) return { found: false, rows: rows.length };
  return { found: true, resourceId: hit.resourceId, ...(await lifecycle(p, coll, hit.resourceId, putField)) };
}), null, 1));
