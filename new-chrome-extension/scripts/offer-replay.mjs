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

/** Each job's gestures through the matcher, stopping at the first offer --
 * which is the one the operator would have seen. `{ job, offered }` per job,
 * `offered` null when nothing ever matched. */
export function replay(shapes, jobs) {
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
  return rows;
}

/** The counts the summary line carries. */
export function tally(rows) {
  const out = { right: 0, wrong: 0, never: 0 };
  for (const { job, offered } of rows) {
    if (!offered) out.never += 1;
    else if (offered.workflowId === job.id) out.right += 1;
    else out.wrong += 1;
  }
  return out;
}

function main(path) {
  const { shapes, jobs } = JSON.parse(readFileSync(path, "utf8"));
  const rows = replay(shapes, jobs);
  const width = Math.max(...rows.map((r) => r.job.title.length), 8);
  console.log(`${"job".padEnd(width)}  gestures  offered at  k  named`);
  console.log("-".repeat(width + 40));
  for (const { job, offered } of rows) {
    const count = String(job.gestures.length).padStart(8);
    if (!offered) {
      console.log(`${job.title.padEnd(width)}  ${count}  never`);
      continue;
    }
    const named = offered.workflowId === job.id ? "itself" : `WRONG: ${offered.title}`;
    console.log(
      `${job.title.padEnd(width)}  ${count}  ${String(offered.at).padStart(10)}  ${offered.k}  ${named}`,
    );
  }
  console.log("-".repeat(width + 40));
  const { right, wrong, never } = tally(rows);
  console.log(
    `${jobs.length} jobs replayed against ${shapes.length} served shapes at K_OFFER_AFTER = ${K_OFFER_AFTER}: ${right} offered as themselves, ${wrong} offered as another job, ${never} never offered`,
  );
}

// Only when run as a script; the test imports the functions above.
if (process.argv[1] && process.argv[1].endsWith("offer-replay.mjs")) {
  const path = process.argv[2];
  if (!path) {
    console.error("usage: node scripts/offer-replay.mjs replay.json");
    process.exit(2);
  }
  main(path);
}
