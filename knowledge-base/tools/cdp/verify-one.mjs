import { withPage, lifecycle } from './api.mjs';
const [coll, id, field] = process.argv.slice(2);
console.log(JSON.stringify(await withPage((p) => lifecycle(p, coll, id, field)), null, 1));
