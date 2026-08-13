/* Diagnose the two unresolved read-back anomalies from the battery. */
import { connect, exchange } from './http-record.mjs';
import fs from 'node:fs';
const LEDGER = JSON.parse(fs.readFileSync('knowlegde_graph/blue-yonder-sce/index/write-endpoints.json','utf8'));
const tmpl = (r) => { const e = LEDGER.find(x => x.method==='POST' && x.resource===r); return e?.payload ? JSON.parse(JSON.stringify(e.payload)) : {}; };
const { browser, page } = await connect();
const call = (m,u,b) => exchange(page, m, u, b);
const out = {};

// --- Q1: clients POST returns 201 but the resourceId does not resolve on an immediate GET
const addr = await call('POST','/wm/addresses',{...tmpl('addresses'), addressName:'ZV Diag Addr', clientId:'----', addressType:'CLI'});
const addressId = addr.body?.data?.addressId;
const cid = 'ZVD' + String(Date.now()%10000);
const created = await call('POST','/wm/clients',{...tmpl('clients'), clientId:cid, addressId});
out.q1 = { createStatus: created.status, returnedResourceId: created.body?.data?.resourceId,
           returnedClientId: created.body?.data?.clientId, allKeys: Object.keys(created.body?.data||{}).slice(0,12) };
out.q1.getByResourceId = (await call('GET', `/wm/clients/${encodeURIComponent(created.body?.data?.resourceId||'')}`)).kind;
out.q1.getByClientId   = (await call('GET', `/wm/clients/${encodeURIComponent(cid)}`)).kind;
await new Promise(r=>setTimeout(r,4000));
out.q1.getByResourceId_after4s = (await call('GET', `/wm/clients/${encodeURIComponent(created.body?.data?.resourceId||'')}`)).kind;
const list = await call('GET','/wm/clients?query=[]&offset=0&limit=400&siteId=SG&subsites=----');
const row = (list.body?.data||[]).find(x => x.clientId === cid);
out.q1.foundInCollection = !!row;
out.q1.collectionResourceId = row?.resourceId;
// cleanup
await call('DELETE', `/wm/clients/${encodeURIComponent(cid)}`);
if (addressId) await call('DELETE', `/wm/addresses/${addressId}`);
out.q1.cleanup = (await call('GET', `/wm/clients/${encodeURIComponent(cid)}`)).kind;

// --- Q2: packingConfigurations POST returns 201 with no resourceId
const addr2 = await call('POST','/wm/addresses',{...tmpl('addresses'), addressName:'ZV Diag Addr2', clientId:'----', addressType:'CLI'});
const aid2 = addr2.body?.data?.addressId;
const cid2 = 'ZVE' + String(Date.now()%10000);
await call('POST','/wm/clients',{...tmpl('clients'), clientId:cid2, addressId:aid2});
const pc = await call('POST','/wm/packingConfigurations',{...tmpl('packingConfigurations'), clientId:cid2, warehouseId:'SG'});
out.q2 = { status: pc.status, bodyKeys: Object.keys(pc.body?.data||{}), body: pc.body?.data };
const pcl = await call('GET','/wm/packingConfigurations?query=[]&offset=0&limit=400&siteId=SG&subsites=----');
const pcRow = (pcl.body?.data||[]).find(x => x.clientId === cid2);
out.q2.foundInCollection = !!pcRow;
out.q2.actualResourceId = pcRow?.resourceId;
if (pcRow?.resourceId) {
  out.q2.getById = (await call('GET', `/wm/packingConfigurations/${encodeURIComponent(pcRow.resourceId)}`)).kind;
  out.q2.deleteById = (await call('DELETE', `/wm/packingConfigurations/${encodeURIComponent(pcRow.resourceId)}`)).status;
  out.q2.confirmGone = (await call('GET', `/wm/packingConfigurations/${encodeURIComponent(pcRow.resourceId)}`)).kind;
}
await call('DELETE', `/wm/clients/${encodeURIComponent(cid2)}`);
if (aid2) await call('DELETE', `/wm/addresses/${aid2}`);
console.log(JSON.stringify(out,null,1));
await browser.close();
