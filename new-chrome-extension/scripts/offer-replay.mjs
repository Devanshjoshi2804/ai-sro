// The offer, replayed against the corpus's own evidence.
//
// `make offer-replay` has the rig write each proven job's demonstrated gestures
// beside the shapes it serves; this feeds them, one at a time, through the same
// `tailWith` and `match` the service worker runs on every gesture, and reports
// at which gesture each job would have been offered and whether the offer
// named the job the operator was actually doing. No browser, no model: the
// number the design leaves to a person is measured here on what the rig holds.
//
// Run: node scripts/offer-replay.mjs path/to/replay.json
import { readFileSync } from "node:fs";
import { K_OFFER_AFTER, match, tailWith } from "../src/background/recognise.js";

const path = process.argv[2];
if (!path) {
  console.error("usage: node scripts/offer-replay.mjs replay.json");
  process.exit(2);
}
const { shapes, jobs } = JSON.parse(readFileSync(path, "utf8"));

const rows = [];
for (const job of jobs) {
  let tail = [];
  let offered = null;
  for (const [i, entry] of job.gestures.entries()) {
    tail = tailWith(tail, entry);
    const found = match(tail, shapes, { origin: entry.triple[0] });
    if (found) {
      offered = { at: i + 1, k: found.k, workflowId: found.workflowId, title: found.title };
      break;
    }
  }
  rows.push({ job, offered });
}

const width = Math.max(...rows.map((r) => r.job.title.length), 8);
console.log(`${"job".padEnd(width)}  gestures  offered at  k  named`);
console.log("-".repeat(width + 40));
let right = 0;
let wrong = 0;
let never = 0;
for (const { job, offered } of rows) {
  if (!offered) {
    never += 1;
    console.log(`${job.title.padEnd(width)}  ${String(job.gestures.length).padStart(8)}  never`);
    continue;
  }
  const ok = offered.workflowId === job.id;
  if (ok) right += 1;
  else wrong += 1;
  console.log(
    `${job.title.padEnd(width)}  ${String(job.gestures.length).padStart(8)}  ${String(offered.at).padStart(10)}  ${offered.k}  ${ok ? "itself" : `WRONG: ${offered.title}`}`,
  );
}
console.log("-".repeat(width + 40));
console.log(
  `${jobs.length} jobs replayed against ${shapes.length} served shapes at K_OFFER_AFTER = ${K_OFFER_AFTER}: ${right} offered as themselves, ${wrong} offered as another job, ${never} never offered`,
);
