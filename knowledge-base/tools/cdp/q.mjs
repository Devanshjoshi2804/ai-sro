import { withPage, call } from './api.mjs';
const r = await withPage((p) => call(p, 'GET', '/wm/equipmentTypes?query=[]&offset=0&limit=200&siteId=SG&subsites=----'));
const rows = Array.isArray(r.data) ? r.data : [];
const used = new Set(rows.map(x => Number(x.voiceCode)).filter(n => !Number.isNaN(n)));
let free = null;
for (let i = 1; i < 1000; i++) if (!used.has(i)) { free = i; break; }
console.log(JSON.stringify({ total: rows.length, usedCount: used.size, maxUsed: Math.max(...used), firstFree: free }, null, 1));
