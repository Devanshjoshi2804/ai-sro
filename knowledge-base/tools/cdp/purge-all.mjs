/* Remove every ZV-prefixed record this tooling may have left, across all touched collections. */
import { withPage, call } from './api.mjs';
const COLS = [
  ['customerTypes','customerType'], ['transportModes','transportMode'], ['carriers','carrierCode'],
  ['businessUnits','businessUnit'], ['levelTypes','levelTypeName'], ['equipmentTypes','vehicleTypeId'],
  ['printers','printerAddress'], ['devices','deviceCode'], ['clientGroups','clientGroup'],
  ['locationTypes','locationType'], ['clients','clientId'], ['suppliers','supplierNumber'],
  ['customers','customerNumber'], ['carrierCrossReferences','carrier'],
];
/*
 * Page through the WHOLE collection.
 *
 * A single limit=500 read reported a clean environment while two ZV carriers were live, because
 * that collection holds 1581 rows and the leftovers sat past the first page. This is the third
 * distinct way this cleanup check has produced a false negative - after an enumerated marker list
 * that went stale, and after omitting a collection the harness was actively writing to. Treat any
 * "clean" result from a single unpaged read as unproven.
 */
const scan = async (p, c) => {
  const rows = [];
  for (let off = 0; off < 5000; off += 500) {
    const q = c === 'transportModes'
      ? `?query=[]&offset=${off}&limit=500`
      : `?query=[]&offset=${off}&limit=500&siteId=SG&subsites=----`;
    const r = await call(p, 'GET', `/wm/${c}${q}`);
    if (r.kind !== 'OK' || !Array.isArray(r.data) || !r.data.length) break;
    rows.push(...r.data);
    if (r.data.length < 500) break;   // some collections ignore limit and return everything
  }
  return rows;
};

console.log(JSON.stringify(await withPage(async (p) => {
  const out = { deleted: [], remaining: [] };
  for (const [c, keyField] of COLS) {
    const rows = await scan(p, c);
    for (const row of rows) {
      const v = String(row[keyField] ?? '');
      if (!/^ZV/.test(v)) continue;
      const st = (await call(p, 'DELETE', `/wm/${c}/${encodeURIComponent(row.resourceId)}`)).status;
      out.deleted.push(`${c}/${row.resourceId}:${st}`);
      // a supplier/customer/client owns an address created alongside it
      if (row.addressId) {
        const ast = (await call(p, 'DELETE', `/wm/addresses/${encodeURIComponent(row.addressId)}`)).status;
        out.deleted.push(`addresses/${row.addressId}:${ast}`);
      }
    }
  }
  for (const [c, keyField] of COLS) {
    for (const row of await scan(p, c)) {
      if (/^ZV/.test(String(row[keyField] ?? ''))) out.remaining.push(`${c}/${row.resourceId}`);
    }
  }
  out.strayAddresses = (await scan(p, 'addresses'))
    .filter((x) => /^ZV/.test(String(x.addressName || ''))).map((x) => x.addressId);
  return out;
}), null, 1));
